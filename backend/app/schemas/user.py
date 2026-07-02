from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validators import validate_password_strength
from app.models.user import Role


class UserBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    role: Role = Role.SECRETARIA
    is_active: bool = True
    guardian_id: int | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    role: Role | None = None
    is_active: bool | None = None
    guardian_id: int | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_password_strength(value)


class UserRead(UserBase):
    id: int
    permissions: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
