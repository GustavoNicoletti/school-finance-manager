from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.permissions import ALL_PERMISSION_KEYS, DEFAULT_ROLE_PERMISSIONS, PERMISSION_CATALOG
from app.models.role_permission import RolePermissionProfile
from app.models.user import Role, User
from app.schemas.permission import PermissionItemRead, RolePermissionRead
from app.schemas.user import UserRead


PERMISSION_DEPENDENCIES: dict[str, set[str]] = {
    "students_manage": {"students_view", "guardians_view"},
    "guardians_manage": {"guardians_view", "students_view"},
    "receivables_manage": {"receivables_view"},
    "payables_manage": {"payables_view"},
    "users_manage": {"users_view", "guardians_view"},
    "users_delete": {"users_view"},
    "role_permissions_manage": {"users_view"},
}


def list_permission_catalog() -> list[PermissionItemRead]:
    return [
        PermissionItemRead(
            key=item["key"],
            label=item["label"],
            description=item["description"],
            group=group["group"],
        )
        for group in PERMISSION_CATALOG
        for item in group["items"]
    ]


def default_permissions_for_role(role: Role) -> list[str]:
    return sorted(DEFAULT_ROLE_PERMISSIONS.get(role, set()))


def sanitize_stored_permissions(permissions: list[str]) -> list[str]:
    return normalize_permissions([permission for permission in permissions if permission in ALL_PERMISSION_KEYS])


def normalize_permissions(permissions: list[str]) -> list[str]:
    expanded_permissions = set(permissions)
    changed = True
    while changed:
        changed = False
        for permission in list(expanded_permissions):
            dependencies = PERMISSION_DEPENDENCIES.get(permission, set())
            missing = dependencies - expanded_permissions
            if missing:
                expanded_permissions.update(missing)
                changed = True

    invalid_permissions = sorted(expanded_permissions - ALL_PERMISSION_KEYS)
    if invalid_permissions:
        raise ValueError(f"Permissoes invalidas: {', '.join(invalid_permissions)}.")
    return sorted(expanded_permissions)


def sync_role_permission_profiles(db: Session) -> list[RolePermissionProfile]:
    existing_profiles = {profile.role: profile for profile in db.query(RolePermissionProfile).all()}
    created = False

    for role in Role:
        if role not in existing_profiles:
            profile = RolePermissionProfile(role=role, permissions=default_permissions_for_role(role))
            db.add(profile)
            existing_profiles[role] = profile
            created = True

    if created:
        db.commit()
        for profile in existing_profiles.values():
            db.refresh(profile)

    return [existing_profiles[role] for role in Role]


def resolve_role_permissions(db: Session, role: Role) -> list[str]:
    if role == Role.ADMINISTRADOR:
        return sorted(ALL_PERMISSION_KEYS)

    profiles = sync_role_permission_profiles(db)
    profile_map = {profile.role: profile for profile in profiles}
    profile = profile_map.get(role)
    if not profile:
        return default_permissions_for_role(role)
    normalized_permissions = sanitize_stored_permissions(profile.permissions)
    if normalized_permissions != sorted(profile.permissions):
        profile.permissions = normalized_permissions
        db.commit()
        db.refresh(profile)
    return normalized_permissions


def resolve_permissions_by_roles(db: Session, roles: list[Role]) -> dict[Role, list[str]]:
    unique_roles = list(dict.fromkeys(roles))
    return {role: resolve_role_permissions(db, role) for role in unique_roles}


def role_permission_read(db: Session, role: Role) -> RolePermissionRead:
    profiles = sync_role_permission_profiles(db)
    profile_map = {profile.role: profile for profile in profiles}
    profile = profile_map[role]
    permissions = resolve_role_permissions(db, role)
    return RolePermissionRead(
        role=role,
        permissions=permissions,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def update_role_permissions(db: Session, role: Role, permissions: list[str]) -> RolePermissionRead:
    sync_role_permission_profiles(db)
    profile = db.query(RolePermissionProfile).filter(RolePermissionProfile.role == role).first()
    if not profile:
        profile = RolePermissionProfile(role=role, permissions=default_permissions_for_role(role))
        db.add(profile)
        db.flush()

    profile.permissions = sorted(ALL_PERMISSION_KEYS) if role == Role.ADMINISTRADOR else normalize_permissions(permissions)
    db.commit()
    db.refresh(profile)
    return role_permission_read(db, role)


def user_has_permissions(db: Session, user: User, *permissions: str) -> bool:
    granted_permissions = set(resolve_role_permissions(db, user.role))
    return all(permission in granted_permissions for permission in permissions)


def build_user_read(db: Session, user: User) -> UserRead:
    return UserRead(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        guardian_id=user.guardian_id,
        permissions=resolve_role_permissions(db, user.role),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def build_user_read_with_permissions(user: User, permissions: list[str]) -> UserRead:
    return UserRead(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        guardian_id=user.guardian_id,
        permissions=permissions,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
