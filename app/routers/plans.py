"""Visit planning for signed-in visitors and administrators."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.deps import admin_user, current_user
from app.models import Site, User, VisitPlan
from app.schemas import VisitPlanCreate, VisitPlanOut

router = APIRouter(prefix="/plans", tags=["plans"])


def _out(plan: VisitPlan) -> VisitPlanOut:
    return VisitPlanOut(
        id=plan.id,
        site_slug=plan.site.slug,
        site_name=plan.site.name,
        user_name=plan.user.full_name,
        user_email=plan.user.email,
        visit_date=plan.visit_date,
        visit_time=plan.visit_time.strftime("%H:%M"),
        visitors=plan.visitors,
        saved_at=plan.saved_at,
    )


def _query_plans(db: Session):
    return db.query(VisitPlan).options(
        joinedload(VisitPlan.user), joinedload(VisitPlan.site)
    )


@router.post("", response_model=VisitPlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: VisitPlanCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> VisitPlanOut:
    if payload.visit_date < date.today():
        raise HTTPException(status_code=422, detail="Visit date cannot be in the past")

    site = db.query(Site).filter(Site.slug == payload.site_slug).first()
    if not site:
        raise HTTPException(status_code=404, detail="Heritage site not found")

    from datetime import time

    hour, minute = (int(value) for value in payload.visit_time.split(":"))
    plan = VisitPlan(
        user_id=user.id,
        site_id=site.id,
        visit_date=payload.visit_date,
        visit_time=time(hour, minute),
        visitors=payload.visitors,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    plan.user = user
    plan.site = site
    return _out(plan)


@router.get("/mine", response_model=list[VisitPlanOut])
def list_my_plans(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[VisitPlanOut]:
    plans = _query_plans(db).filter(VisitPlan.user_id == user.id).order_by(
        VisitPlan.saved_at.desc()
    ).all()
    return [_out(plan) for plan in plans]


@router.get("/admin", response_model=list[VisitPlanOut])
def list_all_plans(
    db: Session = Depends(get_db),
    _: User = Depends(admin_user),
) -> list[VisitPlanOut]:
    plans = _query_plans(db).order_by(
        VisitPlan.visit_date.desc(), VisitPlan.saved_at.desc()
    ).all()
    return [_out(plan) for plan in plans]
