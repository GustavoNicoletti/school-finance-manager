from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def model_snapshot(instance: Any) -> dict[str, Any]:
    mapper = inspect(instance).mapper
    return {
        column.key: jsonable_encoder(getattr(instance, column.key))
        for column in mapper.column_attrs
    }


def register_audit(
    db: Session,
    *,
    user: User | None,
    action: str,
    entity: str,
    entity_id: int | None,
    previous_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            previous_value=previous_value,
            new_value=new_value,
        )
    )
    db.commit()
