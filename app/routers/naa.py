from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import NaaIn, NaaOut
from app.services import naa as naa_service


router = APIRouter(
    prefix="/naa",
    tags=["naa"],
)


@router.post(
    "/ask",
    response_model=NaaOut,
)
def ask(
    payload: NaaIn,
    db: Session = Depends(get_db),
) -> NaaOut:

    site_context = naa_service.build_site_context(
        db,
        payload.site_slug,
    )

    result = naa_service.ask(
        payload.question,
        site_context,
    )

    return NaaOut(
        title=result.get(
            "title",
            "ANANSE Heritage Guide",
        ),
        introduction=result.get(
            "introduction",
            "",
        ),
        sections=result.get(
            "sections",
            [],
        ),
        visitor_notes=result.get(
            "visitor_notes",
            [],
        ),
        sources=result.get(
            "sources",
            [],
        ),
    )