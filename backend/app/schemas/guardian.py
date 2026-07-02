from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validators import validate_cpf


class GuardianBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    cpf: str | None = Field(default=None, max_length=14)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    kinship: str | None = Field(default=None, max_length=80)

    @field_validator("cpf")
    @classmethod
    def validate_document(cls, value: str | None) -> str | None:
        return validate_cpf(value)


class GuardianCreate(GuardianBase):
    student_ids: list[int] = Field(default_factory=list)


class GuardianUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    cpf: str | None = Field(default=None, max_length=14)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    kinship: str | None = Field(default=None, max_length=80)
    student_ids: list[int] | None = None

    @field_validator("cpf")
    @classmethod
    def validate_document(cls, value: str | None) -> str | None:
        return validate_cpf(value)


class GuardianRead(GuardianBase):
    id: int
    student_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
