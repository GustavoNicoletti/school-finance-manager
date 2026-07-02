from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.student import StudentStatus


class StudentBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    birth_date: date | None = None
    class_name: str | None = Field(default=None, max_length=80)
    status: StudentStatus = StudentStatus.ACTIVE
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    medical_information: str | None = None


class StudentCreate(StudentBase):
    guardian_ids: list[int] = Field(default_factory=list)


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    birth_date: date | None = None
    class_name: str | None = Field(default=None, max_length=80)
    status: StudentStatus | None = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    medical_information: str | None = None
    guardian_ids: list[int] | None = None


class StudentRead(StudentBase):
    id: int
    guardian_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
