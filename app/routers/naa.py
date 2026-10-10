import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Site
from app.schemas import NaaIn, NaaOut
from app.services import naa as naa_service

log = logging.getLogger("ananse.naa")

router = APIRouter(prefix="/naa", tags=["naa"])

DB_UNAVAILABLE = NaaOut(
    title="ANANSE Heritage Guide",
    introduction=(
        "Sorry, Naa can't reach ANANSE's heritage records right now. "
        "Please try again in a few minutes."
    ),
)


def _load_sites(db: Session, site_slug: str | None) -> list[Site]:
    query = db.query(Site)
    if site_slug:
        query = query.filter(Site.slug == site_slug)
    return query.all()


@router.post("/ask", response_model=NaaOut)
def ask(payload: NaaIn, db: Session = Depends(get_db)) -> NaaOut:
    # Every path below returns a normal 200 reply. An unhandled 500 skips the
    # CORS headers, so the browser would only show "connection error".

    # 1. Database: the source of truth. If it is down (e.g. the Aiven free
    #    service has been powered off), say so instead of crashing.
    try:
        site_context = naa_service.build_site_context(db, payload.site_slug)
    except Exception as exc:  # noqa: BLE001
        log.error("Naa could not read the database: %s", exc)
        return DB_UNAVAILABLE

    # 2. AI provider, falling back to the reviewed database text.
    try:
        result = naa_service.ask(payload.question, site_context)
    except Exception as exc:  # noqa: BLE001
        log.warning("Naa AI provider failed, using database answer: %s", exc)
        try:
            result = naa_service.answer_from_database(
                payload.question, _load_sites(db, payload.site_slug)
            )
        except Exception as db_exc:  # noqa: BLE001
            log.error("Naa database fallback failed: %s", db_exc)
            return DB_UNAVAILABLE

    try:
        return NaaOut(
            title=result.get("title") or "ANANSE Heritage Guide",
            introduction=result.get("introduction", ""),
            sections=result.get("sections", []),
            visitor_notes=result.get("visitor_notes", []),
            sources=result.get("sources", []),
        )
    except Exception:  # model returned the wrong shape
        return NaaOut(title="ANANSE Heritage Guide",
                      introduction=str(result.get("introduction", "")))


@router.get("/status")
def status() -> dict:
    """Is Naa's AI provider working? Safe to share: no keys are returned."""
    return naa_service.provider_status()
