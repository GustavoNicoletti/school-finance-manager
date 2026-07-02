from app.models.user import Role

from .conftest import auth_headers, create_user


def test_auth_me_includes_permissions_for_logged_user(client, db):
    create_user(db, email="teacher@example.com", role=Role.PROFESSOR)

    response = client.get("/api/auth/me", headers=auth_headers(client, "teacher@example.com"))

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "professor"
    assert "students_view" in body["permissions"]
    assert "guardians_view" in body["permissions"]
    assert "receivables_view" not in body["permissions"]


def test_role_permission_update_changes_access_boundaries(client, db):
    create_user(db, email="admin@example.com", role=Role.ADMINISTRADOR)
    create_user(db, email="teacher@example.com", role=Role.PROFESSOR)

    update_response = client.put(
        "/api/role-permissions/professor",
        json={"permissions": ["dashboard_view"]},
        headers=auth_headers(client, "admin@example.com"),
    )

    assert update_response.status_code == 200
    assert update_response.json()["permissions"] == ["dashboard_view"]

    professor_headers = auth_headers(client, "teacher@example.com")
    assert client.get("/api/dashboard", headers=professor_headers).status_code == 200
    assert client.get("/api/students", headers=professor_headers).status_code == 403
    assert client.get("/api/guardians", headers=professor_headers).status_code == 403


def test_director_cannot_delete_users_without_specific_permission(client, db):
    create_user(db, email="director@example.com", role=Role.DIRETOR)
    target = create_user(db, email="secretary@example.com", role=Role.SECRETARIA)

    response = client.delete(f"/api/users/{target.id}", headers=auth_headers(client, "director@example.com"))

    assert response.status_code == 403

