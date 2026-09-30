"""Badge definitions."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Badge
from app.schemas import BadgeOut

router = APIRouter(prefix="/badges", tags=["badges"])


@router.get("", response_model=list[BadgeOut])
def list_badges(db: Session = Depends(get_db)) -> list[Badge]:
    return db.query(Badge).order_by(Badge.threshold).all()
