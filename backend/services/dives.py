import secrets
import uuid
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from exceptions import ConflictError, NotFoundError
from models.entities import (
    Dive,
    DiveOfficer,
    GearCategory,
    Inventory,
    Officer,
    Signup,
    SignupStatus,
    SuitSize,
)
from schemas.payloads import DiveCreate, DiveUpdate, InventoryInput, SignupCreate, SignupUpdate


def public_id() -> str:
    return secrets.token_urlsafe(7).replace("-", "").replace("_", "")[:9]


def get_dive(db: Session, dive_id: uuid.UUID, *, lock: bool = False) -> Dive:
    query = select(Dive).where(Dive.id == dive_id)
    if lock:
        query = query.with_for_update()
    dive = db.scalar(query)
    if not dive:
        raise NotFoundError("Dive not found")
    return dive


def get_public_dive(db: Session, value: str, *, lock: bool = False) -> Dive:
    query = select(Dive).where(Dive.public_id == value)
    if lock:
        query = query.with_for_update()
    dive = db.scalar(query)
    if not dive:
        raise NotFoundError("Dive not found")
    return dive


def counts(db: Session, dive_id: uuid.UUID) -> dict[str, int]:
    rows = db.execute(
        select(Signup.status, func.count()).where(Signup.dive_id == dive_id).group_by(Signup.status)
    ).all()
    result = {status.value: 0 for status in SignupStatus}
    result.update({status.value: count for status, count in rows})
    return result


def public_view(db: Session, dive: Dive) -> dict:
    signup_counts = counts(db, dive.id)
    remaining = max(dive.capacity - signup_counts["confirmed"], 0)
    return {
        "public_id": dive.public_id,
        "title": dive.title,
        "description": dive.description,
        "location": dive.location,
        "starts_at": dive.starts_at,
        "capacity": dive.capacity,
        "remaining": remaining,
        "next_status": "confirmed" if remaining else "waitlisted",
    }


def create_signup(db: Session, dive_public_id: str, payload: SignupCreate) -> dict:
    dive = get_public_dive(db, dive_public_id, lock=True)
    starts_at = dive.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)
    if starts_at <= datetime.now(UTC):
        raise ConflictError("This dive has already occurred")
    email = str(payload.email).strip().lower()
    if db.scalar(select(Signup.id).where(Signup.dive_id == dive.id, Signup.email == email)):
        raise ConflictError("This email is already signed up for the dive")
    confirmed_count = db.scalar(
        select(func.count())
        .select_from(Signup)
        .where(Signup.dive_id == dive.id, Signup.status == SignupStatus.confirmed)
    )
    signup_status = (
        SignupStatus.confirmed if confirmed_count < dive.capacity else SignupStatus.waitlisted
    )
    queue_order = (
        db.scalar(select(func.max(Signup.queue_order)).where(Signup.dive_id == dive.id)) or 0
    ) + 1
    signup = Signup(
        dive_id=dive.id,
        name=payload.name,
        email=email,
        status=signup_status,
        queue_order=queue_order,
        needs_carpool=payload.needs_carpool,
        pickup_location=payload.pickup_location,
        needs_gear=payload.needs_gear,
        suit_size=payload.suit_size,
        shoe_size=payload.shoe_size,
    )
    db.add(signup)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("This email is already signed up for the dive") from error
    db.refresh(signup)
    position = None
    if signup.status == SignupStatus.waitlisted:
        position = db.scalar(
            select(func.count())
            .select_from(Signup)
            .where(
                Signup.dive_id == dive.id,
                Signup.status == SignupStatus.waitlisted,
                Signup.queue_order <= signup.queue_order,
            )
        )
    return {"id": signup.id, "status": signup.status.value, "waitlist_position": position}


def set_assignments(db: Session, dive: Dive, officer_ids: list[uuid.UUID]) -> None:
    unique_ids = set(officer_ids)
    if unique_ids:
        found = set(db.scalars(select(Officer.id).where(Officer.id.in_(unique_ids))).all())
        if found != unique_ids:
            raise NotFoundError("One or more officers were not found")
    dive.assignments.clear()
    dive.assignments.extend(DiveOfficer(officer_id=officer_id) for officer_id in unique_ids)


def create_dive(db: Session, payload: DiveCreate) -> Dive:
    value = public_id()
    while db.scalar(select(Dive.id).where(Dive.public_id == value)):
        value = public_id()
    dive = Dive(
        public_id=value,
        title=payload.title,
        description=payload.description,
        location=payload.location,
        starts_at=payload.starts_at,
        capacity=payload.capacity,
    )
    db.add(dive)
    db.flush()
    set_assignments(db, dive, payload.officer_ids)
    db.commit()
    return dive


def update_dive(db: Session, dive: Dive, payload: DiveUpdate) -> Dive:
    values = payload.model_dump(exclude_unset=True, exclude={"officer_ids"})
    for key, value in values.items():
        setattr(dive, key, value.strip() if isinstance(value, str) else value)
    if payload.officer_ids is not None:
        set_assignments(db, dive, payload.officer_ids)
    db.commit()
    return dive


def serialize_signup(signup: Signup) -> dict:
    return {
        "id": signup.id,
        "name": signup.name,
        "email": signup.email,
        "status": signup.status.value,
        "needs_carpool": signup.needs_carpool,
        "pickup_location": signup.pickup_location,
        "needs_gear": signup.needs_gear,
        "suit_size": signup.suit_size.value if signup.suit_size else None,
        "shoe_size": signup.shoe_size,
        "created_at": signup.created_at,
    }


def gear_report(db: Session, signups: list[Signup]) -> list[dict]:
    inventory = list(
        db.scalars(select(Inventory).order_by(Inventory.category, Inventory.min_shoe_size))
    )
    confirmed = [
        item for item in signups if item.status == SignupStatus.confirmed and item.needs_gear
    ]
    waitlisted = [
        item for item in signups if item.status == SignupStatus.waitlisted and item.needs_gear
    ]
    report: list[dict] = []

    for size in SuitSize:
        item = next(
            (
                row
                for row in inventory
                if row.category == GearCategory.wetsuit and row.suit_size == size
            ),
            None,
        )
        report.append(
            _gear_row(
                "wetsuit",
                size.value,
                item.quantity if item else 0,
                sum(signup.suit_size == size for signup in confirmed),
                sum(signup.suit_size == size for signup in waitlisted),
            )
        )

    fin_inventory = [row for row in inventory if row.category == GearCategory.fins]
    fin_ranges: dict[tuple[float, float], int] = {}
    for item in fin_inventory:
        key = (item.min_shoe_size, item.max_shoe_size)
        fin_ranges[key] = fin_ranges.get(key, 0) + item.quantity
    ranges = [(*size_range, quantity) for size_range, quantity in fin_ranges.items()]
    confirmed_by_range, confirmed_unmatched = _allocate_fins(ranges, confirmed)
    waitlisted_by_range, waitlisted_unmatched = _allocate_fins(ranges, waitlisted)
    for index, (minimum, maximum, quantity) in enumerate(ranges):
        label = f"US {minimum:g}–{maximum:g}"
        report.append(
            _gear_row(
                "fins",
                label,
                quantity,
                confirmed_by_range[index],
                waitlisted_by_range[index],
            )
        )
    for unmatched, status_label in (
        (confirmed_unmatched, "confirmed"),
        (waitlisted_unmatched, "waitlisted"),
    ):
        for shoe_size, needed in unmatched.items():
            existing = next(
                (
                    row
                    for row in report
                    if row["category"] == "fins" and row["label"] == f"US {shoe_size:g}"
                ),
                None,
            )
            if not existing:
                existing = _gear_row("fins", f"US {shoe_size:g}", 0, 0, 0)
                report.append(existing)
            existing[f"{status_label}_needed"] = needed
            existing["shortage"] = existing["confirmed_needed"] > existing["available"]

    for category, label in ((GearCategory.mask, "Masks"), (GearCategory.weight_set, "Weight sets")):
        item = next((row for row in inventory if row.category == category), None)
        report.append(
            _gear_row(
                category.value, label, item.quantity if item else 0, len(confirmed), len(waitlisted)
            )
        )
    return report


def _allocate_fins(ranges: list[tuple[float, float, int]], signups: list[Signup]):
    remaining = [quantity for _, _, quantity in ranges]
    assigned = [0] * len(ranges)
    unmatched = Counter()
    for signup in sorted(signups, key=lambda item: item.shoe_size):
        compatible = [
            index
            for index, (minimum, maximum, _) in enumerate(ranges)
            if remaining[index] and minimum <= signup.shoe_size <= maximum
        ]
        if not compatible:
            unmatched[signup.shoe_size] += 1
            continue
        selected = min(compatible, key=lambda index: (ranges[index][1], ranges[index][0]))
        remaining[selected] -= 1
        assigned[selected] += 1
    return assigned, unmatched


def _gear_row(category: str, label: str, available: int, confirmed: int, waitlisted: int) -> dict:
    return {
        "category": category,
        "label": label,
        "available": available,
        "confirmed_needed": confirmed,
        "waitlisted_needed": waitlisted,
        "shortage": confirmed > available,
    }


def detail_view(db: Session, dive: Dive) -> dict:
    loaded = db.scalar(
        select(Dive)
        .where(Dive.id == dive.id)
        .options(
            selectinload(Dive.signups),
            selectinload(Dive.assignments).selectinload(DiveOfficer.officer),
        )
    )
    signups = sorted(loaded.signups, key=lambda signup: (signup.status.value, signup.queue_order))
    confirmed_count = sum(signup.status == SignupStatus.confirmed for signup in signups)
    active_officers = [
        assignment.officer for assignment in loaded.assignments if assignment.officer.active
    ]
    gear = gear_report(db, signups)
    starts_at = loaded.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)
    is_upcoming = starts_at > datetime.now(UTC)
    warnings = []
    if is_upcoming and len(active_officers) < 2:
        warnings.append("Fewer than two active officers are assigned")
    if is_upcoming and confirmed_count > loaded.capacity:
        warnings.append("Confirmed participants exceed capacity")
    if is_upcoming and any(row["shortage"] for row in gear):
        warnings.append("Loaner gear demand exceeds inventory")
    return {
        "id": loaded.id,
        "public_id": loaded.public_id,
        "title": loaded.title,
        "description": loaded.description,
        "location": loaded.location,
        "starts_at": loaded.starts_at,
        "capacity": loaded.capacity,
        "confirmed_count": confirmed_count,
        "waitlist_count": sum(signup.status == SignupStatus.waitlisted for signup in signups),
        "officers": [{"id": officer.id, "name": officer.name} for officer in active_officers],
        "assigned_officer_ids": [assignment.officer_id for assignment in loaded.assignments],
        "confirmed": [
            serialize_signup(item) for item in signups if item.status == SignupStatus.confirmed
        ],
        "waitlisted": [
            serialize_signup(item) for item in signups if item.status == SignupStatus.waitlisted
        ],
        "gear": gear,
        "warnings": warnings,
    }


def update_signup(db: Session, signup: Signup, payload: SignupUpdate) -> Signup:
    values = payload.model_dump(exclude={"status"})
    values["email"] = str(payload.email).lower()
    for key, value in values.items():
        setattr(signup, key, value)
    db.commit()
    return signup


def promote_signup(db: Session, signup_id: uuid.UUID) -> Signup:
    signup = db.scalar(select(Signup).where(Signup.id == signup_id).with_for_update())
    if not signup:
        raise NotFoundError("Signup not found")
    dive = get_dive(db, signup.dive_id, lock=True)
    if signup.status != SignupStatus.waitlisted:
        raise ConflictError("Only waitlisted signups can be promoted")
    first = db.scalar(
        select(Signup)
        .where(Signup.dive_id == dive.id, Signup.status == SignupStatus.waitlisted)
        .order_by(Signup.queue_order)
    )
    if first.id != signup.id:
        raise ConflictError("Promote waitlisted members in signup order")
    current = db.scalar(
        select(func.count())
        .select_from(Signup)
        .where(Signup.dive_id == dive.id, Signup.status == SignupStatus.confirmed)
    )
    if current >= dive.capacity:
        raise ConflictError("The dive is at capacity")
    signup.status = SignupStatus.confirmed
    db.commit()
    return signup


def save_inventory(db: Session, payload: InventoryInput) -> Inventory:
    rows = list(db.scalars(select(Inventory).where(Inventory.category == payload.category)))
    if payload.category == GearCategory.wetsuit and any(
        row.suit_size == payload.suit_size for row in rows
    ):
        raise ConflictError("That wetsuit size already exists")
    if payload.category in {GearCategory.mask, GearCategory.weight_set} and rows:
        raise ConflictError("That unsized inventory category already exists")
    item = Inventory(**payload.model_dump())
    db.add(item)
    db.commit()
    return item
