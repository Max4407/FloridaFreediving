import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class SignupStatus(str, enum.Enum):
    confirmed = "confirmed"
    waitlisted = "waitlisted"


class SuitSize(str, enum.Enum):
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"


class GearCategory(str, enum.Enum):
    wetsuit = "wetsuit"
    fins = "fins"
    mask = "mask"
    weight_set = "weight_set"


class Dive(Base):
    __tablename__ = "dives"
    __table_args__ = (CheckConstraint("capacity > 0", name="ck_dive_capacity_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(300))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    capacity: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    signups: Mapped[list["Signup"]] = relationship(
        back_populates="dive", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["DiveOfficer"]] = relationship(
        back_populates="dive", cascade="all, delete-orphan"
    )


class Signup(Base):
    __tablename__ = "signups"
    __table_args__ = (
        UniqueConstraint("dive_id", "email", name="uq_signup_dive_email"),
        CheckConstraint(
            "shoe_size IS NULL OR (shoe_size >= 1 AND shoe_size <= 18)", name="ck_shoe"
        ),
        Index("ix_signup_queue", "dive_id", "status", "queue_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dives.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320))
    status: Mapped[SignupStatus] = mapped_column(Enum(SignupStatus))
    queue_order: Mapped[int] = mapped_column(Integer)
    needs_carpool: Mapped[bool] = mapped_column(Boolean, default=False)
    pickup_location: Mapped[str | None] = mapped_column(String(300))
    needs_gear: Mapped[bool] = mapped_column(Boolean, default=False)
    suit_size: Mapped[SuitSize | None] = mapped_column(Enum(SuitSize))
    shoe_size: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    dive: Mapped[Dive] = relationship(back_populates="signups")


class Officer(Base):
    __tablename__ = "officers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    assignments: Mapped[list["DiveOfficer"]] = relationship(back_populates="officer")


class DiveOfficer(Base):
    __tablename__ = "dive_officers"

    dive_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dives.id", ondelete="CASCADE"), primary_key=True
    )
    officer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("officers.id", ondelete="RESTRICT"), primary_key=True
    )
    dive: Mapped[Dive] = relationship(back_populates="assignments")
    officer: Mapped[Officer] = relationship(back_populates="assignments")


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity"),
        CheckConstraint(
            "min_shoe_size IS NULL OR max_shoe_size IS NULL OR min_shoe_size <= max_shoe_size",
            name="ck_fin_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category: Mapped[GearCategory] = mapped_column(Enum(GearCategory), index=True)
    suit_size: Mapped[SuitSize | None] = mapped_column(Enum(SuitSize))
    min_shoe_size: Mapped[float | None] = mapped_column(Float)
    max_shoe_size: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer, default=0)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ip_hash: Mapped[str] = mapped_column(String(64), index=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
