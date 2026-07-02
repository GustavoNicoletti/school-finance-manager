from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token, get_request_access_token, oauth2_scheme
from app.services.permission_service import user_has_permissions
from app.models.user import Role, User


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    resolved_token = get_request_access_token(request, token)
    if not resolved_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario nao autenticado.")

    user_id = decode_access_token(resolved_token)
    try:
        user_id_int = int(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autenticacao invalido.") from exc

    user = db.query(User).filter(User.id == user_id_int).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario nao autenticado.")
    return user


def require_roles(*roles: Role) -> Callable[[User], User]:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Voce nao possui permissao para executar esta acao.",
            )
        return current_user

    return dependency


def require_permissions(*permissions: str) -> Callable[[User], User]:
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not user_has_permissions(db, current_user, *permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Voce nao possui permissao para executar esta acao.",
            )
        return current_user

    return dependency
