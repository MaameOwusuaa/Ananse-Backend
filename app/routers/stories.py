"""Interactive heritage stories."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import admin_user
from app.models import Site, Story
from app.schemas import StoryCreate, StoryOut, StoryUpdate

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("/{slug}", response_model=StoryOut)
def get_story(slug: str, db: Session = Depends(get_db)) -> StoryOut:
    """The story published for a heritage site, addressed by the site slug."""
    story = (
        db.query(Story)
        .join(Site, Story.site_id == Site.id)
        .filter(Site.slug == slug)
        .first()
    )
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No story has been published for this site yet",
        )

    return StoryOut(
        title=story.title,
        site=story.site.slug,
        minutes=story.minutes,
        chapters=story.chapters,
    )


@router.post("", response_model=StoryOut, status_code=status.HTTP_201_CREATED)
def create_story(payload: StoryCreate, db: Session = Depends(get_db), _: object = Depends(admin_user)) -> StoryOut:
    site = db.query(Site).filter(Site.id == payload.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Heritage site not found")
    story = Story(**payload.model_dump())
    db.add(story)
    db.commit()
    db.refresh(story)
    return StoryOut(title=story.title, site=site.slug, minutes=story.minutes, chapters=story.chapters)


@router.put("/id/{story_id}", response_model=StoryOut)
def update_story(story_id: int, payload: StoryUpdate, db: Session = Depends(get_db), _: object = Depends(admin_user)) -> StoryOut:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(story, key, value)
    site = db.query(Site).filter(Site.id == story.site_id).first()
    db.commit()
    db.refresh(story)
    return StoryOut(title=story.title, site=site.slug, minutes=story.minutes, chapters=story.chapters)


@router.delete("/id/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(story_id: int, db: Session = Depends(get_db), _: object = Depends(admin_user)) -> None:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    db.delete(story)
    db.commit()
