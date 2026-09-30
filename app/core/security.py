"""Password hashing and access tokens.

bcrypt is used directly rather than through a wrapper: it is one function
each way, and it keeps the dependency list short.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

#: bcrypt only reads the first 72 bytes of a password; longer input is an error.
MAX_PASSWORD_BYTES = 72


def _encode(raw: str) -> bytes:
    return raw.encode("utf-8")[:MAX_PASSWORD_BYTES]


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(_encode(raw), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_encode(raw), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": subject, "exp": expires}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def read_access_token(token: str) -> str | None:
    """Return the subject of a valid token, or None if it cannot be trusted."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
    return payload.get("sub")
