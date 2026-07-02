from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import get_dashboard_summary


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardSummary)
def dashboard_summary(
    reference_date: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.DASHBOARD_VIEW.value)),
) -> DashboardSummary:
    return get_dashboard_summary(db, reference_date=reference_date)
