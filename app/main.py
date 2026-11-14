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
from app.provision_admin import provision_admin
from app.routers import admin, analytics, auth, badges, naa, passport, plans, sites, stories
from app.models import VisitPlan


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
    allow_origins=settings.origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


for router in (
    analytics.router,
    admin.router,
    auth.router,
    plans.router,
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
    """Ensure app-managed tables exist; existing tables remain externally managed."""
    print("ANANSE: startup event reached", flush=True)
    models.AnalyticsEvent.__table__.create(bind=engine, checkfirst=True)
    VisitPlan.__table__.create(bind=engine, checkfirst=True)
    # Provision only when both deployment secrets are configured. This lets a
    # hosted deployment create or update its admin in the same database used
    # by sign-in, without requiring a separate shell command.
    has_admin_email = bool(settings.admin_email.strip())
    has_admin_password = bool(settings.admin_password)
    if has_admin_email != has_admin_password:
        raise RuntimeError(
            "Configure both ADMIN_EMAIL and ADMIN_PASSWORD to provision the administrator."
        )
    if has_admin_email:
        provision_admin(create_tables=False)
    else:
        print(
            "ANANSE: admin provisioning skipped; configure ADMIN_EMAIL and ADMIN_PASSWORD.",
            flush=True,
        )

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
        "google_sign_in_configured": bool(settings.google_client_id),
        "build": "2026-10-09-dbfix",
        "database_host": settings.database_host,
        "database_driver": DATABASE_URL.drivername,
        "database_name": DATABASE_URL.database,
        "database_url_options": sorted(DATABASE_URL.query.keys()),
        "database": db_status,
    }
