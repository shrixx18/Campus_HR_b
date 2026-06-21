import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from campushire_common.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.STUDENT


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    name: str | None = None
    cgpa: float | None = None
    branch: str | None = None
    year: int | None = None
    phone: str | None = None
    skills: list[str] | None = None


class ProfileResponse(BaseModel):
    user_id: uuid.UUID
    name: str | None = None
    cgpa: float | None = None
    branch: str | None = None
    year: int | None = None
    phone: str | None = None
    skills: list[str] | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ValidateTokenResponse(BaseModel):
    user_id: uuid.UUID
    role: UserRole
