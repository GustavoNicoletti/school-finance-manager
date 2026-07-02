from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogRead


router = APIRouter(prefix="/audit", tags=["Auditoria"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    entity: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    action: str | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.AUDIT_VIEW.value)),
) -> list[AuditLog]:
    query = db.query(AuditLog)
    if entity:
        query = query.filter(AuditLog.entity == entity)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
