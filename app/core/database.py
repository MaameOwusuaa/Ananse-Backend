"""Database engine and session handling."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Options that Aiven puts in its copied URI but mysql-connector rejects
# ("Unsupported argument 'ssl-mode'"). SSL is still used: mysql-connector
# negotiates it by default when the server (Aiven) requires it.
_UNSUPPORTED = {"ssl-mode", "ssl_mode", "sslmode"}


def _clean_url(raw: str):
    url = make_url(raw.strip().strip('"').strip("'"))
    query = {k: v for k, v in url.query.items() if k.lower() not in _UNSUPPORTED}
    return url.set(query=query)


DATABASE_URL = _clean_url(settings.database_url)

connect_args = {"check_same_thread": False} if DATABASE_URL.drivername.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for every ORM model."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
