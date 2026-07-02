from datetime import date, datetime
from enum import Enum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StudentStatus(str, Enum):
    ACTIVE = "ativo"
    INACTIVE = "inativo"
    TRANSFERRED = "transferido"


student_guardians = Table(
    "student_guardians",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
    Column("guardian_id", Integer, ForeignKey("guardians.id", ondelete="CASCADE"), primary_key=True),
)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[StudentStatus] = mapped_column(
        SAEnum(StudentStatus, values_callable=lambda enum: [item.value for item in enum], name="student_status"),
        nullable=False,
        default=StudentStatus.ACTIVE,
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    medical_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    guardians = relationship("Guardian", secondary=student_guardians, back_populates="students")
    receivables = relationship("Receivable", back_populates="student", cascade="all, delete-orphan")

    @property
    def guardian_ids(self) -> list[int]:
        return [guardian.id for guardian in self.guardians]
