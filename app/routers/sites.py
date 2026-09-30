"""Heritage sites."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import admin_user
from app.models import Site
from app.schemas import SiteCreate, SiteOut, SiteUpdate

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=list[SiteOut], response_model_by_alias=True)
def list_sites(
    search: str | None = Query(default=None, max_length=120),
    region: str | None = Query(default=None, max_length=60),
    category: str | None = Query(default=None, max_length=60),
    db: Session = Depends(get_db),
) -> list[Site]:
    """Every published site, narrowed by search text, region or category."""
    query = db.query(Site)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(Site.name.ilike(pattern), Site.summary.ilike(pattern), Site.region.ilike(pattern))
        )
    if region:
        query = query.filter(Site.region == region)
    if category:
        query = query.filter(Site.category == category)

    return query.order_by(Site.name).all()


@router.get("/{slug}", response_model=SiteOut, response_model_by_alias=True)
def get_site(slug: str, db: Session = Depends(get_db)) -> Site:
    site = db.query(Site).filter(Site.slug == slug).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No heritage site is published under that name",
        )
    return site


@router.post("", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
def create_site(payload: SiteCreate, db: Session = Depends(get_db), _: object = Depends(admin_user)) -> Site:
    if db.query(Site).filter(Site.slug == payload.slug).first():
        raise HTTPException(status_code=409, detail="A site with that slug already exists")
    site = Site(**payload.model_dump())
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.put("/id/{site_id}", response_model=SiteOut)
def update_site(site_id: int, payload: SiteUpdate, db: Session = Depends(get_db), _: object = Depends(admin_user)) -> Site:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Heritage site not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(site, key, value)
    db.commit()
    db.refresh(site)
    return site


@router.delete("/id/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(site_id: int, db: Session = Depends(get_db), _: object = Depends(admin_user)) -> None:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Heritage site not found")
    db.delete(site)
    db.commit()
