import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Site
from app.schemas import NaaIn, NaaOut
from app.services import naa as naa_service

log = logging.getLogger("ananse.naa")

router = APIRouter(prefix="/naa", tags=["naa"])


@router.post("/ask", response_model=NaaOut)
def ask(payload: NaaIn, db: Session = Depends(get_db)) -> NaaOut:
    site_context = naa_service.build_site_context(db, payload.site_slug)

    try:
        result = naa_service.ask(payload.question, site_context)
    except Exception as exc:  # noqa: BLE001
        # Never return a 500 here: an unhandled 500 skips the CORS headers,
        # so the browser reports it as a CORS/network failure.
        log.warning("Naa AI provider failed, using database answer: %s", exc)
        query = db.query(Site)
        if payload.site_slug:
            query = query.filter(Site.slug == payload.site_slug)
        result = naa_service.answer_from_database(payload.question, query.all())

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
