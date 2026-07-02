from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import Permission
from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.security import get_password_hash
from app.models.guardian import Guardian
from app.models.user import Role, User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.audit_service import model_snapshot, register_audit
from app.services.permission_service import build_user_read, build_user_read_with_permissions, resolve_permissions_by_roles


router = APIRouter(prefix="/users", tags=["Usuarios"])


def _ensure_guardian_exists(db: Session, guardian_id: int) -> None:
    if not db.get(Guardian, guardian_id):
        raise HTTPException(status_code=400, detail="Responsavel informado nao foi encontrado.")


def _resolve_guardian_id(
    db: Session,
    *,
    role: Role,
    guardian_id: int | None,
    guardian_id_provided: bool,
    current_guardian_id: int | None = None,
) -> int | None:
    if role == Role.RESPONSAVEL:
        final_guardian_id = guardian_id if guardian_id_provided else current_guardian_id
        if final_guardian_id is None:
            raise HTTPException(status_code=400, detail="Usuario com perfil responsavel deve ser vinculado a um responsavel.")
        _ensure_guardian_exists(db, final_guardian_id)
        return final_guardian_id

    if guardian_id_provided and guardian_id is not None:
        raise HTTPException(status_code=400, detail="Somente usuarios com perfil responsavel podem ser vinculados a um responsavel.")

    return None


@router.get("", response_model=list[UserRead])
def list_users(
    search: str | None = None,
    role: Role | None = None,
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.USERS_VIEW.value)),
) -> list[UserRead]:
    query = db.query(User)
    if search:
        query = query.filter(User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    users = query.order_by(User.full_name).offset(skip).limit(limit).all()
    permissions_by_role = resolve_permissions_by_roles(db, [user.role for user in users])
    return [build_user_read_with_permissions(user, permissions_by_role[user.role]) for user in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.USERS_MANAGE.value)),
) -> UserRead:
    guardian_id = _resolve_guardian_id(
        db,
        role=payload.role,
        guardian_id=payload.guardian_id,
        guardian_id_provided=True,
    )
    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        guardian_id=guardian_id,
        role=payload.role,
        is_active=payload.is_active,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ja existe um usuario com este e-mail.") from exc

    register_audit(db, user=current_user, action="create", entity="User", entity_id=user.id, new_value=model_snapshot(user))
    return build_user_read(db, user)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.USERS_VIEW.value)),
) -> UserRead:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    return build_user_read(db, user)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.USERS_MANAGE.value)),
) -> UserRead:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")

    previous = model_snapshot(user)
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        data["email"] = data["email"].lower()
    data["guardian_id"] = _resolve_guardian_id(
        db,
        role=data.get("role", user.role),
        guardian_id=data.get("guardian_id"),
        guardian_id_provided="guardian_id" in data,
        current_guardian_id=user.guardian_id,
    )
    password = data.pop("password", None)
    if password:
        user.hashed_password = get_password_hash(password)
    for field, value in data.items():
        setattr(user, field, value)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ja existe um usuario com este e-mail.") from exc

    register_audit(
        db,
        user=current_user,
        action="update",
        entity="User",
        entity_id=user.id,
        previous_value=previous,
        new_value=model_snapshot(user),
    )
    return build_user_read(db, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.USERS_DELETE.value)),
) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Voce nao pode excluir o proprio usuario.")

    previous = model_snapshot(user)
    db.delete(user)
    db.commit()
    register_audit(db, user=current_user, action="delete", entity="User", entity_id=user_id, previous_value=previous)
