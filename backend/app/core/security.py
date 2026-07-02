from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    issued_at = datetime.now(UTC)
    expire = issued_at + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de autenticacao invalido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        subject = payload.get("sub")
        if subject is None or payload.get("type") != "access":
            raise credentials_exception
        return str(subject)
    except JWTError as exc:
        raise credentials_exception from exc


def get_request_access_token(request: Request, bearer_token: str | None) -> str | None:
    if bearer_token:
        return bearer_token
    return request.cookies.get(settings.access_token_cookie_name)


def set_access_token_cookie(response: Response, token: str) -> None:
    max_age = settings.access_token_expire_minutes * 60
    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=token,
        max_age=max_age,
        expires=max_age,
        path="/",
        domain=settings.access_token_cookie_domain,
        secure=settings.resolved_access_token_cookie_secure,
        httponly=True,
        samesite=settings.access_token_cookie_samesite,
    )


def clear_access_token_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.access_token_cookie_name,
        path="/",
        domain=settings.access_token_cookie_domain,
        secure=settings.resolved_access_token_cookie_secure,
        httponly=True,
        samesite=settings.access_token_cookie_samesite,
    )
