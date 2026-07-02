from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import Role


class PermissionItemRead(BaseModel):
    key: str
    label: str
    description: str
    group: str


class RolePermissionRead(BaseModel):
    role: Role
    permissions: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RolePermissionUpdate(BaseModel):
    permissions: list[str]


class RolePermissionMatrixRead(BaseModel):
    profiles: list[RolePermissionRead]
    catalog: list[PermissionItemRead]
