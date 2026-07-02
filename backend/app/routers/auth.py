from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import clear_access_token_cookie, create_access_token, set_access_token_cookie, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserRead
from app.services.login_rate_limit_service import (
    build_login_rate_limit_key,
    ensure_login_allowed,
    register_failed_login,
    register_successful_login,
)
from app.services.permission_service import build_user_read


router = APIRouter(prefix="/auth", tags=["Autenticacao"])
settings = get_settings()


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> Token:
    rate_limit_key = build_login_rate_limit_key(request, payload.email)
    ensure_login_allowed(rate_limit_key)

    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        register_failed_login(rate_limit_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha invalidos.")
    if not user.is_active:
        register_failed_login(rate_limit_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha invalidos.")

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    register_successful_login(rate_limit_key)
    set_access_token_cookie(response, access_token)
    return Token(access_token=access_token, user=build_user_read(db, user))


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserRead:
    return build_user_read(db, current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    clear_access_token_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
