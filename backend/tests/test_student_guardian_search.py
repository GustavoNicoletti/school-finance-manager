from app.models.guardian import Guardian
from app.models.student import Student, StudentStatus
from app.models.user import Role
from .conftest import auth_headers, create_user


def test_students_search_matches_guardian_name(client, db):
    create_user(db, email="secretary@example.com", role=Role.SECRETARIA)
    guardian = Guardian(full_name="Marina Lopes", email="marina@familia.com")
    student = Student(full_name="Thiago Almeida", status=StudentStatus.ACTIVE)
    student.guardians = [guardian]
    db.add_all([guardian, student])
    db.commit()

    response = client.get("/api/students", params={"search": "Marina"}, headers=auth_headers(client, "secretary@example.com"))

    assert response.status_code == 200
    assert [item["full_name"] for item in response.json()] == ["Thiago Almeida"]


def test_guardians_search_matches_student_name(client, db):
    create_user(db, email="secretary@example.com", role=Role.SECRETARIA)
    guardian = Guardian(full_name="Paulo Mendes", email="paulo@familia.com")
    student = Student(full_name="Clara Mendes", status=StudentStatus.ACTIVE)
    guardian.students = [student]
    db.add_all([guardian, student])
    db.commit()

    response = client.get("/api/guardians", params={"search": "Clara"}, headers=auth_headers(client, "secretary@example.com"))

    assert response.status_code == 200
    assert [item["full_name"] for item in response.json()] == ["Paulo Mendes"]


