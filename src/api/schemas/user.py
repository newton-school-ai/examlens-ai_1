"""Pydantic schemas for users, authentication, and tokens."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from src.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRole = UserRole.STUDENT


class UserCreate(UserBase):
    google_id: str
    auth_provider: str = "google"


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class GoogleAuthRequest(BaseModel):
    code: str
