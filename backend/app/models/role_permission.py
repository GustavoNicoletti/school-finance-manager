from datetime import datetime

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import Role


class RolePermissionProfile(Base):
    __tablename__ = "role_permission_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, values_callable=lambda enum: [item.value for item in enum], name="user_role"),
        nullable=False,
        unique=True,
        index=True,
    )
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
