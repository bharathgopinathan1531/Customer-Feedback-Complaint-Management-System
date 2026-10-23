from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerProfileCreate(BaseModel):
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)


class CustomerProfileUpdate(BaseModel):
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)


class CustomerProfileResponse(BaseModel):
    id: int
    user_id: int
    phone: str | None
    address: str | None
    city: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerListItem(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    is_active: bool
    phone: str | None
    address: str | None
    city: str | None

    model_config = ConfigDict(from_attributes=True)


class CustomerStatusUpdate(BaseModel):
    is_active: bool
