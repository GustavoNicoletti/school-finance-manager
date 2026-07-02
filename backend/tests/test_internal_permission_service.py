import pytest

from app.core.permissions import ALL_PERMISSION_KEYS
from app.models.user import Role
from app.services.permission_service import (
    normalize_permissions,
    resolve_role_permissions,
    update_role_permissions,
)


def test_normalize_permissions_adds_required_dependencies() -> None:
    permissions = normalize_permissions(["students_manage", "users_manage"])

    assert "students_manage" in permissions
    assert "students_view" in permissions
    assert "guardians_view" in permissions
    assert "users_manage" in permissions
    assert "users_view" in permissions


def test_normalize_permissions_rejects_invalid_keys() -> None:
    with pytest.raises(ValueError) as exc_info:
        normalize_permissions(["students_view", "permissao_inexistente"])

    assert "Permissoes invalidas" in str(exc_info.value)


def test_resolve_role_permissions_returns_all_permissions_for_admin(db) -> None:
    permissions = resolve_role_permissions(db, Role.ADMINISTRADOR)

    assert permissions == sorted(ALL_PERMISSION_KEYS)


def test_update_role_permissions_persists_dependencies_for_profile(db) -> None:
    updated = update_role_permissions(db, Role.PROFESSOR, ["students_manage"])

    assert updated.role == Role.PROFESSOR
    assert updated.permissions == ["guardians_view", "students_manage", "students_view"]

    resolved = resolve_role_permissions(db, Role.PROFESSOR)
    assert resolved == updated.permissions
