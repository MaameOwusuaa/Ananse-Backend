"""The Cultural Passport: visits, completed stories and badges."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import current_user
from app.models import Site, Story, StoryCompletion, User, Visit
from app.schemas import PassportOut, StoryProgressIn, StoryProgressOut, VisitIn, VisitOut
from app.services import badges as badge_service

router = APIRouter(prefix="/passport", tags=["passport"])


def _passport(db: Session, user: User) -> PassportOut:
    visits = (
        db.query(Visit)
        .filter(Visit.user_id == user.id)
        .order_by(Visit.recorded_at)
        .all()
    )
    completions = (
        db.query(StoryCompletion)
        .filter(StoryCompletion.user_id == user.id)
        .order_by(StoryCompletion.completed_at)
        .all()
    )

    return PassportOut(
        visits=[
            VisitOut(slug=visit.site.slug, source=visit.source, recorded_at=visit.recorded_at)
            for visit in visits
        ],
        stories=[
            StoryProgressOut(
                slug=completion.story.site.slug,
                score=completion.score,
                completed_at=completion.completed_at,
            )
            for completion in completions
        ],
        badges=badge_service.evaluate(db, user),
    )


@router.get("", response_model=PassportOut)
def read_passport(user: User = Depends(current_user), db: Session = Depends(get_db)) -> PassportOut:
    return _passport(db, user)


@router.post("/visits", response_model=PassportOut, status_code=status.HTTP_201_CREATED)
def record_visit(
    payload: VisitIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PassportOut:
    site = db.query(Site).filter(Site.slug == payload.slug).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No heritage site is published under that name",
        )

    existing = (
        db.query(Visit)
        .filter(Visit.user_id == user.id, Visit.site_id == site.id)
        .first()
    )
    if not existing:
        db.add(Visit(user_id=user.id, site_id=site.id, source=payload.source))
        db.commit()

    return _passport(db, user)


@router.post("/stories", response_model=PassportOut, status_code=status.HTTP_201_CREATED)
def record_story(
    payload: StoryProgressIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PassportOut:
    story = (
        db.query(Story)
        .join(Site, Story.site_id == Site.id)
        .filter(Site.slug == payload.slug)
        .first()
    )
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No story has been published for this site yet",
        )

    completion = (
        db.query(StoryCompletion)
        .filter(StoryCompletion.user_id == user.id, StoryCompletion.story_id == story.id)
        .first()
    )

    if completion:
        completion.score = max(completion.score, payload.score)
    else:
        db.add(StoryCompletion(user_id=user.id, story_id=story.id, score=payload.score))

    db.commit()
    return _passport(db, user)
