from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.models.guardian import Guardian
from app.models.student import Student, StudentStatus
from app.models.user import User
from app.schemas.student import StudentCreate, StudentRead, StudentUpdate
from app.services.audit_service import model_snapshot, register_audit


router = APIRouter(prefix="/students", tags=["Alunos"])


def _get_guardians(db: Session, guardian_ids: list[int]) -> list[Guardian]:
    if not guardian_ids:
        return []
    guardians = db.query(Guardian).filter(Guardian.id.in_(guardian_ids)).all()
    if len(guardians) != len(set(guardian_ids)):
        raise HTTPException(status_code=400, detail="Um ou mais responsaveis nao foram encontrados.")
    return guardians


@router.get("", response_model=list[StudentRead])
def list_students(
    search: str | None = None,
    status_filter: StudentStatus | None = Query(default=None, alias="status"),
    class_name: str | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.STUDENTS_VIEW.value)),
) -> list[Student]:
    query = db.query(Student).options(selectinload(Student.guardians))
    if search:
        query = (
            query.outerjoin(Student.guardians)
            .filter(
                or_(
                    Student.full_name.ilike(f"%{search}%"),
                    Student.class_name.ilike(f"%{search}%"),
                    Guardian.full_name.ilike(f"%{search}%"),
                    Guardian.cpf.ilike(f"%{search}%"),
                    Guardian.phone.ilike(f"%{search}%"),
                )
            )
            .distinct()
        )
    if status_filter:
        query = query.filter(Student.status == status_filter)
    if class_name:
        query = query.filter(Student.class_name.ilike(f"%{class_name}%"))
    return query.order_by(Student.full_name).offset(skip).limit(limit).all()


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.STUDENTS_MANAGE.value)),
) -> Student:
    data = payload.model_dump(exclude={"guardian_ids"})
    student = Student(**data)
    student.guardians = _get_guardians(db, payload.guardian_ids)
    db.add(student)
    db.commit()
    db.refresh(student)
    register_audit(db, user=current_user, action="create", entity="Student", entity_id=student.id, new_value=model_snapshot(student))
    return student


@router.get("/{student_id}", response_model=StudentRead)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.STUDENTS_VIEW.value)),
) -> Student:
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Aluno nao encontrado.")
    return student


@router.put("/{student_id}", response_model=StudentRead)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.STUDENTS_MANAGE.value)),
) -> Student:
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Aluno nao encontrado.")

    previous = model_snapshot(student)
    data = payload.model_dump(exclude_unset=True, exclude={"guardian_ids"})
    for field, value in data.items():
        setattr(student, field, value)
    if payload.guardian_ids is not None:
        student.guardians = _get_guardians(db, payload.guardian_ids)

    db.commit()
    db.refresh(student)
    register_audit(
        db,
        user=current_user,
        action="update",
        entity="Student",
        entity_id=student.id,
        previous_value=previous,
        new_value=model_snapshot(student),
    )
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.STUDENTS_MANAGE.value)),
) -> None:
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Aluno nao encontrado.")
    previous = model_snapshot(student)
    db.delete(student)
    db.commit()
    register_audit(db, user=current_user, action="delete", entity="Student", entity_id=student_id, previous_value=previous)
