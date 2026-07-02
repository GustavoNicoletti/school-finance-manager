from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Role(str, Enum):
    ADMINISTRADOR = "administrador"
    DIRETOR = "diretor"
    FINANCEIRO = "financeiro"
    SECRETARIA = "secretaria"
    PROFESSOR = "professor"
    RESPONSAVEL = "responsavel"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    guardian_id: Mapped[int | None] = mapped_column(ForeignKey("guardians.id", ondelete="SET NULL"), nullable=True, index=True)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, values_callable=lambda enum: [item.value for item in enum], name="user_role"),
        nullable=False,
        default=Role.SECRETARIA,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    guardian = relationship("Guardian", back_populates="users")
