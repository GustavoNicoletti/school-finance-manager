from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.models.guardian import Guardian
from app.models.student import Student
from app.models.user import User
from app.schemas.guardian import GuardianCreate, GuardianRead, GuardianUpdate
from app.services.audit_service import model_snapshot, register_audit


router = APIRouter(prefix="/guardians", tags=["Responsaveis"])


def _get_students(db: Session, student_ids: list[int]) -> list[Student]:
    if not student_ids:
        return []
    students = db.query(Student).filter(Student.id.in_(student_ids)).all()
    if len(students) != len(set(student_ids)):
        raise HTTPException(status_code=400, detail="Um ou mais alunos nao foram encontrados.")
    return students


@router.get("", response_model=list[GuardianRead])
def list_guardians(
    search: str | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.GUARDIANS_VIEW.value)),
) -> list[Guardian]:
    query = db.query(Guardian).options(selectinload(Guardian.students))
    if search:
        query = (
            query.outerjoin(Guardian.students)
            .filter(
                or_(
                    Guardian.full_name.ilike(f"%{search}%"),
                    Guardian.cpf.ilike(f"%{search}%"),
                    Guardian.email.ilike(f"%{search}%"),
                    Guardian.phone.ilike(f"%{search}%"),
                    Student.full_name.ilike(f"%{search}%"),
                    Student.class_name.ilike(f"%{search}%"),
                )
            )
            .distinct()
        )
    return query.order_by(Guardian.full_name).offset(skip).limit(limit).all()


@router.post("", response_model=GuardianRead, status_code=status.HTTP_201_CREATED)
def create_guardian(
    payload: GuardianCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.GUARDIANS_MANAGE.value)),
) -> Guardian:
    data = payload.model_dump(exclude={"student_ids"})
    guardian = Guardian(**data)
    guardian.students = _get_students(db, payload.student_ids)
    db.add(guardian)
    try:
        db.commit()
        db.refresh(guardian)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ja existe um responsavel com este CPF.") from exc

    register_audit(db, user=current_user, action="create", entity="Guardian", entity_id=guardian.id, new_value=model_snapshot(guardian))
    return guardian


@router.get("/{guardian_id}", response_model=GuardianRead)
def get_guardian(
    guardian_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.GUARDIANS_VIEW.value)),
) -> Guardian:
    guardian = db.get(Guardian, guardian_id)
    if not guardian:
        raise HTTPException(status_code=404, detail="Responsavel nao encontrado.")
    return guardian


@router.put("/{guardian_id}", response_model=GuardianRead)
def update_guardian(
    guardian_id: int,
    payload: GuardianUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.GUARDIANS_MANAGE.value)),
) -> Guardian:
    guardian = db.get(Guardian, guardian_id)
    if not guardian:
        raise HTTPException(status_code=404, detail="Responsavel nao encontrado.")

    previous = model_snapshot(guardian)
    data = payload.model_dump(exclude_unset=True, exclude={"student_ids"})
    for field, value in data.items():
        setattr(guardian, field, value)
    if payload.student_ids is not None:
        guardian.students = _get_students(db, payload.student_ids)

    try:
        db.commit()
        db.refresh(guardian)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ja existe um responsavel com este CPF.") from exc

    register_audit(
        db,
        user=current_user,
        action="update",
        entity="Guardian",
        entity_id=guardian.id,
        previous_value=previous,
        new_value=model_snapshot(guardian),
    )
    return guardian


@router.delete("/{guardian_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guardian(
    guardian_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.GUARDIANS_MANAGE.value)),
) -> None:
    guardian = db.get(Guardian, guardian_id)
    if not guardian:
        raise HTTPException(status_code=404, detail="Responsavel nao encontrado.")
    previous = model_snapshot(guardian)
    db.delete(guardian)
    db.commit()
    register_audit(db, user=current_user, action="delete", entity="Guardian", entity_id=guardian_id, previous_value=previous)
