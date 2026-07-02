from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import Role, User


settings = get_settings()


def seed_admin(db: Session) -> None:
    existing_user = db.query(User).filter(User.email == settings.first_superuser_email.lower()).first()
    if existing_user:
        print("Usuário administrador inicial já existe.")
        return

    admin = User(
        full_name=settings.first_superuser_name,
        email=settings.first_superuser_email.lower(),
        hashed_password=get_password_hash(settings.first_superuser_password),
        role=Role.ADMINISTRADOR,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print(f"Usuário administrador criado: {admin.email}")


def main() -> None:
    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
