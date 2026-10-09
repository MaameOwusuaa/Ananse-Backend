"""ANANSE API — application entry point.

Run it from the backend folder:

    uvicorn app.main:app --reload

Interactive documentation is then at http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.core.config import settings
from app.core.database import Base, engine
from app.routers import auth, badges, naa, passport, sites, stories


print("ANANSE: application import started", flush=True)


print("ANANSE: creating FastAPI application", flush=True)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Heritage sites, interactive stories, the Naa guide and the "
        "Cultural Passport for the ANANSE platform."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


for router in (
    auth.router,
    sites.router,
    stories.router,
    naa.router,
    passport.router,
    badges.router,
):
    app.include_router(
        router,
        prefix=settings.api_prefix,
    )


@app.on_event("startup")
def create_tables() -> None:
    """Database tables will be managed separately."""
    print("ANANSE: startup event reached", flush=True)

@app.get("/api/health", tags=["health"])
def health() -> dict:
    """Quick check, safe to share: no passwords are returned."""
    from sqlalchemy import text

    from app.core.database import DATABASE_URL

    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {type(exc).__name__}: {str(exc)[:200]}"

    return {
        "status": "ok",
        "service": settings.app_name,
        "build": "2026-10-09-dbfix",
        "database_host": settings.database_host,
        "database_driver": DATABASE_URL.drivername,
        "database_name": DATABASE_URL.database,
        "database_url_options": sorted(DATABASE_URL.query.keys()),
        "database": db_status,
    }
