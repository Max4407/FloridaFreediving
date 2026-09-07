import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from models.entities import GearCategory, SignupStatus, SuitSize


class LoginInput(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class SignupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    needs_carpool: bool = False
    pickup_location: str | None = Field(default=None, max_length=300)
    needs_gear: bool = False
    suit_size: SuitSize | None = None
    shoe_size: float | None = None

    @field_validator("name", "pickup_location")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @field_validator("shoe_size")
    @classmethod
    def valid_shoe_size(cls, value: float | None) -> float | None:
        if value is not None and (value < 1 or value > 18 or value * 2 != int(value * 2)):
            raise ValueError("shoe size must be 1–18 in half-size increments")
        return value

    @model_validator(mode="after")
    def validate_conditionals(self):
        if self.needs_carpool and not self.pickup_location:
            raise ValueError("pickup location is required when carpooling")
        if not self.needs_carpool:
            self.pickup_location = None
        if self.needs_gear and (self.suit_size is None or self.shoe_size is None):
            raise ValueError("suit and shoe size are required when renting gear")
        if not self.needs_gear:
            self.suit_size = None
            self.shoe_size = None
        return self


class SignupUpdate(SignupCreate):
    status: SignupStatus | None = None


class DiveCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=5000)
    location: str = Field(min_length=1, max_length=300)
    starts_at: datetime
    capacity: int = Field(gt=0, le=500)
    officer_ids: list[uuid.UUID] = []

    @field_validator("title", "description", "location")
    @classmethod
    def strip_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("starts_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            value = value.replace(tzinfo=ZoneInfo("America/New_York"))
        return value


class DiveUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, min_length=1, max_length=300)
    starts_at: datetime | None = None
    capacity: int | None = Field(default=None, gt=0, le=500)
    officer_ids: list[uuid.UUID] | None = None

    @field_validator("starts_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            value = value.replace(tzinfo=ZoneInfo("America/New_York"))
        return value


class OfficerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class OfficerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    active: bool | None = None


class InventoryInput(BaseModel):
    category: GearCategory
    suit_size: SuitSize | None = None
    min_shoe_size: float | None = None
    max_shoe_size: float | None = None
    quantity: int = Field(ge=0, le=10000)

    @model_validator(mode="after")
    def validate_shape(self):
        if self.category == GearCategory.wetsuit:
            if (
                self.suit_size is None
                or self.min_shoe_size is not None
                or self.max_shoe_size is not None
            ):
                raise ValueError("wetsuits require only a suit size")
        elif self.category == GearCategory.fins:
            if (
                self.suit_size is not None
                or self.min_shoe_size is None
                or self.max_shoe_size is None
            ):
                raise ValueError("fins require only a shoe-size range")
            if self.min_shoe_size > self.max_shoe_size:
                raise ValueError("minimum shoe size must not exceed maximum")
            for size in (self.min_shoe_size, self.max_shoe_size):
                if size < 1 or size > 18 or size * 2 != int(size * 2):
                    raise ValueError("fin sizes must be 1–18 in half-size increments")
        elif any(
            value is not None for value in (self.suit_size, self.min_shoe_size, self.max_shoe_size)
        ):
            raise ValueError("masks and weight sets do not have sizes")
        return self
