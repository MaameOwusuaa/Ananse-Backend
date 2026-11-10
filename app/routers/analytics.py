"""Shared, privacy-minimal visitor analytics."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import admin_user
from app.models import AnalyticsEvent, User
from app.schemas import (
    AnalyticsDailyCount,
    AnalyticsEventIn,
    AnalyticsEventOut,
    AnalyticsSiteCount,
    AnalyticsSummaryOut,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post(
    "/events",
    response_model=AnalyticsEventOut,
    status_code=status.HTTP_201_CREATED,
)
def record_event(
    payload: AnalyticsEventIn,
    db: Session = Depends(get_db),
) -> AnalyticsEvent:
    event = AnalyticsEvent(
        event_type=payload.event_type,
        page=payload.page,
        site_slug=payload.site_slug,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/summary", response_model=AnalyticsSummaryOut)
def read_summary(
    db: Session = Depends(get_db),
    _: User = Depends(admin_user),
) -> AnalyticsSummaryOut:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=29)).replace(tzinfo=None)
    total_events = db.query(func.count(AnalyticsEvent.id)).scalar() or 0
    event_counts = (
        db.query(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
        .group_by(AnalyticsEvent.event_type)
        .all()
    )
    daily_counts = (
        db.query(func.date(AnalyticsEvent.created_at), func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.created_at >= cutoff)
        .group_by(func.date(AnalyticsEvent.created_at))
        .order_by(func.date(AnalyticsEvent.created_at))
        .all()
    )
    site_counts = (
        db.query(AnalyticsEvent.site_slug, func.count(AnalyticsEvent.id))
        .filter(
            AnalyticsEvent.event_type == "site_view",
            AnalyticsEvent.site_slug.is_not(None),
            AnalyticsEvent.created_at >= cutoff,
        )
        .group_by(AnalyticsEvent.site_slug)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(20)
        .all()
    )

    return AnalyticsSummaryOut(
        total_events=total_events,
        events_by_type={event_type: count for event_type, count in event_counts},
        daily_events=[
            AnalyticsDailyCount(day=day, count=count)
            for day, count in daily_counts
        ],
        top_sites=[
            AnalyticsSiteCount(site_slug=site_slug, count=count)
            for site_slug, count in site_counts
        ],
    )