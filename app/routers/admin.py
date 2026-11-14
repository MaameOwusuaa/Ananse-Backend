"""Administrator-only user analytics."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import admin_user
from app.models import StoryCompletion, User, Visit, VisitPlan
from app.schemas import AdminUserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(admin_user),
) -> list[AdminUserOut]:
    users = db.query(User).filter(User.role != "admin").order_by(User.created_at.desc()).all()
    user_ids = [user.id for user in users]
    if not user_ids:
        return []

    visits = dict(
        db.query(Visit.user_id, func.count(Visit.id))
        .filter(Visit.user_id.in_(user_ids))
        .group_by(Visit.user_id)
        .all()
    )
    stories = dict(
        db.query(StoryCompletion.user_id, func.count(StoryCompletion.id))
        .filter(StoryCompletion.user_id.in_(user_ids))
        .group_by(StoryCompletion.user_id)
        .all()
    )
    plans = dict(
        db.query(VisitPlan.user_id, func.count(VisitPlan.id))
        .filter(VisitPlan.user_id.in_(user_ids))
        .group_by(VisitPlan.user_id)
        .all()
    )

    return [
        AdminUserOut(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            visit_count=visits.get(user.id, 0),
            story_count=stories.get(user.id, 0),
            plan_count=plans.get(user.id, 0),
        )
        for user in users
    ]
