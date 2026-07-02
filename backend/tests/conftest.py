import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.guardian import Guardian
from app.models.user import Role, User
from app.services.login_rate_limit_service import reset_login_rate_limit_state


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL or "_test" not in TEST_DATABASE_URL:
    pytest.skip("Set TEST_DATABASE_URL with a dedicated PostgreSQL test database containing '_test'.", allow_module_level=True)


engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database():
    reset_login_rate_limit_state()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    reset_login_rate_limit_state()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def db() -> Session:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_user(db: Session, *, email: str, role: Role, guardian: Guardian | None = None, active: bool = True) -> User:
    user = User(
        full_name=email.split("@")[0].replace(".", " ").title(),
        email=email,
        hashed_password=get_password_hash("ChangeMe@123456"),
        role=role,
        is_active=active,
        guardian=guardian,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": "ChangeMe@123456"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def refresh_like_token_for(user_id: int) -> str:
    settings = get_settings()
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "refresh",
            "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def expired_access_token_for(user_id: int) -> str:
    return create_access_token(str(user_id), expires_delta=timedelta(minutes=-1))

