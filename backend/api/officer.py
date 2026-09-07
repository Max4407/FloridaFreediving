import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from exceptions import ConflictError, NotFoundError
from models.entities import Dive, Inventory, Officer, Signup
from schemas import (
    DiveCreate,
    DiveUpdate,
    InventoryInput,
    OfficerCreate,
    OfficerUpdate,
    SignupUpdate,
)
from services.auth import requireOfficer
from services.dives import (
    create_dive,
    detail_view,
    get_dive,
    promote_signup,
    save_inventory,
    serialize_signup,
    update_dive,
    update_signup,
)

router = APIRouter(prefix="/api/officer", tags=["officer"], dependencies=[Depends(requireOfficer)])


def not_found(error: NotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))


@router.get("/dives")
def list_dives(
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    db: Session = Depends(get_db),
):
    query = select(Dive).order_by(Dive.starts_at)
    if starts_after:
        query = query.where(Dive.starts_at >= starts_after)
    if starts_before:
        query = query.where(Dive.starts_at < starts_before)
    return [detail_view(db, dive) for dive in db.scalars(query)]


@router.post("/dives", status_code=201)
def add_dive(payload: DiveCreate, db: Session = Depends(get_db)):
    try:
        dive = create_dive(db, payload)
        return detail_view(db, dive)
    except NotFoundError as error:
        db.rollback()
        raise not_found(error) from error


@router.get("/dives/{dive_id}")
def read_dive(dive_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return detail_view(db, get_dive(db, dive_id))
    except NotFoundError as error:
        raise not_found(error) from error


@router.patch("/dives/{dive_id}")
def edit_dive(dive_id: uuid.UUID, payload: DiveUpdate, db: Session = Depends(get_db)):
    try:
        return detail_view(db, update_dive(db, get_dive(db, dive_id), payload))
    except NotFoundError as error:
        db.rollback()
        raise not_found(error) from error


@router.delete("/dives/{dive_id}", status_code=204)
def remove_dive(dive_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        db.delete(get_dive(db, dive_id))
        db.commit()
        return Response(status_code=204)
    except NotFoundError as error:
        raise not_found(error) from error


@router.patch("/signups/{signup_id}")
def edit_signup(signup_id: uuid.UUID, payload: SignupUpdate, db: Session = Depends(get_db)):
    signup = db.get(Signup, signup_id)
    if not signup:
        raise HTTPException(status_code=404, detail="Signup not found")
    try:
        return serialize_signup(update_signup(db, signup, payload))
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="That email is already signed up") from error


@router.delete("/signups/{signup_id}", status_code=204)
def remove_signup(signup_id: uuid.UUID, db: Session = Depends(get_db)):
    signup = db.get(Signup, signup_id)
    if not signup:
        raise HTTPException(status_code=404, detail="Signup not found")
    db.delete(signup)
    db.commit()
    return Response(status_code=204)


@router.post("/signups/{signup_id}/promote")
def promote(signup_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return serialize_signup(promote_signup(db, signup_id))
    except NotFoundError as error:
        raise not_found(error) from error
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/officers")
def list_officers(db: Session = Depends(get_db)):
    return [
        {"id": item.id, "name": item.name, "active": item.active}
        for item in db.scalars(select(Officer).order_by(Officer.name))
    ]


@router.post("/officers", status_code=201)
def add_officer(payload: OfficerCreate, db: Session = Depends(get_db)):
    officer = Officer(name=payload.name)
    db.add(officer)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Officer name already exists") from error
    return {"id": officer.id, "name": officer.name, "active": officer.active}


@router.patch("/officers/{officer_id}")
def edit_officer(officer_id: uuid.UUID, payload: OfficerUpdate, db: Session = Depends(get_db)):
    officer = db.get(Officer, officer_id)
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(officer, key, value.strip() if isinstance(value, str) else value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Officer name already exists") from error
    return {"id": officer.id, "name": officer.name, "active": officer.active}


def inventory_json(item: Inventory) -> dict:
    return {
        "id": item.id,
        "category": item.category.value,
        "suit_size": item.suit_size.value if item.suit_size else None,
        "min_shoe_size": item.min_shoe_size,
        "max_shoe_size": item.max_shoe_size,
        "quantity": item.quantity,
    }


@router.get("/inventory")
def list_inventory(db: Session = Depends(get_db)):
    return [
        inventory_json(item) for item in db.scalars(select(Inventory).order_by(Inventory.category))
    ]


@router.post("/inventory", status_code=201)
def add_inventory(payload: InventoryInput, db: Session = Depends(get_db)):
    try:
        return inventory_json(save_inventory(db, payload))
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.put("/inventory/{item_id}")
def edit_inventory(item_id: uuid.UUID, payload: InventoryInput, db: Session = Depends(get_db)):
    item = db.get(Inventory, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    other_rows = list(
        db.scalars(
            select(Inventory).where(Inventory.id != item_id, Inventory.category == payload.category)
        )
    )
    if payload.category.value == "wetsuit" and any(
        row.suit_size == payload.suit_size for row in other_rows
    ):
        raise HTTPException(status_code=409, detail="That wetsuit size already exists")
    if payload.category.value in {"mask", "weight_set"} and other_rows:
        raise HTTPException(status_code=409, detail="That category already exists")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return inventory_json(item)


@router.delete("/inventory/{item_id}", status_code=204)
def remove_inventory(item_id: uuid.UUID, db: Session = Depends(get_db)):
    item = db.get(Inventory, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    db.delete(item)
    db.commit()
    return Response(status_code=204)
