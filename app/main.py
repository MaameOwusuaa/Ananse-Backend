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

for router in (auth.router, sites.router, stories.router, naa.router, passport.router, badges.router):
    app.include_router(router, prefix=settings.api_prefix)


@app.on_event("startup")
def create_tables() -> None:
    """Create any missing tables. Use Alembic once the schema starts moving."""
    Base.metadata.create_all(bind=engine)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
