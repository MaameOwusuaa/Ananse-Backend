"""Create or reset an administrator from ADMIN_* environment settings.

Run with: python -m app.provision_admin
"""

from sqlalchemy import func

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import MAX_PASSWORD_BYTES, hash_password
from app.models import User


def provision_admin(*, create_tables: bool = True) -> None:
    email = settings.admin_email.strip().lower()
    password = settings.admin_password
    name = settings.admin_name.strip() or "Administrator"

    if not email or "@" not in email:
        raise SystemExit("Set ADMIN_EMAIL to a valid email address before provisioning.")
    if len(password) < 8 or len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise SystemExit("Set ADMIN_PASSWORD to 8 or more characters and no more than 72 UTF-8 bytes.")
    if len(name) > 120:
        raise SystemExit("ADMIN_NAME must be 120 characters or fewer.")

    if create_tables:
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(func.lower(User.email) == email).first()
        if user is None:
            user = User(full_name=name, email=email, password_hash="", role="admin")
            db.add(user)

        user.full_name = name
        user.email = email
        user.password_hash = hash_password(password)
        user.role = "admin"
        db.commit()
        print(f"Administrator account provisioned for {email}.")
    finally:
        db.close()


if __name__ == "__main__":
    provision_admin()
