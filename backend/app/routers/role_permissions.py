from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.models.user import Role, User
from app.schemas.permission import RolePermissionMatrixRead, RolePermissionRead, RolePermissionUpdate
from app.services.audit_service import register_audit
from app.services.permission_service import (
    list_permission_catalog,
    role_permission_read,
    sync_role_permission_profiles,
    update_role_permissions,
)


router = APIRouter(prefix="/role-permissions", tags=["Permissoes"])


@router.get("", response_model=RolePermissionMatrixRead)
def list_role_permissions(
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.ROLE_PERMISSIONS_MANAGE.value)),
) -> RolePermissionMatrixRead:
    sync_role_permission_profiles(db)
    return RolePermissionMatrixRead(
        profiles=[role_permission_read(db, role) for role in Role],
        catalog=list_permission_catalog(),
    )


@router.get("/{role}", response_model=RolePermissionRead)
def get_role_permissions(
    role: Role,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.ROLE_PERMISSIONS_MANAGE.value)),
) -> RolePermissionRead:
    return role_permission_read(db, role)


@router.put("/{role}", response_model=RolePermissionRead)
def save_role_permissions(
    role: Role,
    payload: RolePermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.ROLE_PERMISSIONS_MANAGE.value)),
) -> RolePermissionRead:
    previous = role_permission_read(db, role)
    updated = update_role_permissions(db, role, payload.permissions)
    register_audit(
        db,
        user=current_user,
        action="update_permissions",
        entity="RolePermissionProfile",
        entity_id=None,
        previous_value=previous.model_dump(mode="json"),
        new_value=updated.model_dump(mode="json"),
    )
    return updated
