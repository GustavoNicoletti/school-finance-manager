from app.core.config import get_settings
from app.models.guardian import Guardian
from app.models.user import Role
from .conftest import auth_headers, create_user, expired_access_token_for, refresh_like_token_for


def test_login_success_and_invalid_password(client, db):
    create_user(db, email="admin@example.com", role=Role.ADMINISTRADOR)

    success = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "ChangeMe@123456"})
    assert success.status_code == 200
    assert success.json()["user"]["role"] == Role.ADMINISTRADOR.value
    assert "hashed_password" not in success.json()["user"]

    failure = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "senha-errada"})
    assert failure.status_code == 401


def test_login_rejects_password_above_bcrypt_limit(client, db):
    create_user(db, email="admin@example.com", role=Role.ADMINISTRADOR)

    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "x" * 73})

    assert response.status_code == 422


def test_login_sets_cookie_and_auth_me_accepts_cookie(client, db):
    create_user(db, email="admin@example.com", role=Role.ADMINISTRADOR)

    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "ChangeMe@123456"})

    assert response.status_code == 200
    assert "set-cookie" in response.headers
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]

    me_response = client.get("/api/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "admin@example.com"


def test_logout_clears_cookie_session(client, db):
    create_user(db, email="admin@example.com", role=Role.ADMINISTRADOR)
    login_response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "ChangeMe@123456"})

    assert login_response.status_code == 200
    assert client.get("/api/auth/me").status_code == 200

    logout_response = client.post("/api/auth/logout")

    assert logout_response.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_login_rate_limit_blocks_repeated_failures(client, db):
    settings = get_settings()
    create_user(db, email="admin@example.com", role=Role.ADMINISTRADOR)
    headers = {"X-Forwarded-For": "203.0.113.55"}

    for _ in range(settings.login_rate_limit_max_attempts):
        response = client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "senha-errada"},
            headers=headers,
        )
        assert response.status_code == 401

    blocked_response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMe@123456"},
        headers=headers,
    )

    assert blocked_response.status_code == 429
    assert blocked_response.headers["retry-after"].isdigit()


def test_invalid_and_expired_tokens_are_rejected(client, db):
    user = create_user(db, email="admin@example.com", role=Role.ADMINISTRADOR)
    expired_token = expired_access_token_for(user.id)
    refresh_like_token = refresh_like_token_for(user.id)

    invalid_response = client.get("/api/auth/me", headers={"Authorization": "Bearer token-invalido"})
    expired_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    wrong_type_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {refresh_like_token}"})

    assert invalid_response.status_code == 401
    assert expired_response.status_code == 401
    assert wrong_type_response.status_code == 401


def test_professor_cannot_access_finance(client, db):
    create_user(db, email="teacher@example.com", role=Role.PROFESSOR)

    response = client.get("/api/finance/payables", headers=auth_headers(client, "teacher@example.com"))

    assert response.status_code == 403


def test_role_boundaries_for_finance_secretaria_and_responsavel(client, db):
    guardian = Guardian(full_name="Responsavel Teste", email="guardian.family@example.com")
    db.add(guardian)
    db.commit()
    create_user(db, email="finance@example.com", role=Role.FINANCEIRO)
    create_user(db, email="secretary@example.com", role=Role.SECRETARIA)
    create_user(db, email="guardian@example.com", role=Role.RESPONSAVEL, guardian=guardian)

    finance_headers = auth_headers(client, "finance@example.com")
    secretaria_headers = auth_headers(client, "secretary@example.com")
    responsavel_headers = auth_headers(client, "guardian@example.com")

    assert client.get("/api/dashboard", headers=finance_headers).status_code == 200
    assert client.get("/api/finance/payables", headers=secretaria_headers).status_code == 403
    assert client.get("/api/dashboard", headers=secretaria_headers).status_code == 403
    assert client.get("/api/students", headers=secretaria_headers).status_code == 200
    assert client.get("/api/students", headers=responsavel_headers).status_code == 403
    assert client.get("/api/finance/receivables", headers=responsavel_headers).status_code == 403

