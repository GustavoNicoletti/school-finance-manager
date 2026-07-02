from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    id: int
    user_id: int | None
    action: str
    entity: str
    entity_id: int | None
    previous_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
