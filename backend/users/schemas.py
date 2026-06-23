"""Pydantic schemas for the users domain."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from users.models import UserRole


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    password: str


class UserProfileUpdate(BaseModel):
    """Self-service profile fields a user may change (Phase 6: SMS contact)."""

    phone: str | None = Field(default=None, max_length=20)


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str | None = None
    is_active: bool
    created_at: datetime
