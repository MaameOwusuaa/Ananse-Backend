"""Badge rules.

A badge is earned by doing something, not by asking for it, so the rules are
evaluated on the server every time the passport changes.
"""

from sqlalchemy.orm import Session

from app.models import Badge, BadgeAward, Site, StoryCompletion, User, Visit

NORTHERN_REGIONS = {"Northern", "Savannah", "Upper East", "Upper West", "North East"}


def _progress(db: Session, user: User, badge: Badge) -> int:
    rule, _, value = badge.rule.partition(":")

    if rule == "visits":
        return db.query(Visit).filter(Visit.user_id == user.id).count()

    if rule == "stories":
        return db.query(StoryCompletion).filter(StoryCompletion.user_id == user.id).count()

    if rule == "category":
        return (
            db.query(Visit)
            .join(Site, Visit.site_id == Site.id)
            .filter(Visit.user_id == user.id, Site.category == value)
            .count()
        )

    if rule == "region" and value == "north":
        return (
            db.query(Visit)
            .join(Site, Visit.site_id == Site.id)
            .filter(Visit.user_id == user.id, Site.region.in_(NORTHERN_REGIONS))
            .count()
        )

    return 0


def evaluate(db: Session, user: User) -> list[str]:
    """Award any badge the user now qualifies for and return every slug held."""
    held = {
        award.badge.slug
        for award in db.query(BadgeAward).filter(BadgeAward.user_id == user.id).all()
    }

    for badge in db.query(Badge).all():
        if badge.slug in held:
            continue
        if _progress(db, user, badge) >= badge.threshold:
            db.add(BadgeAward(user_id=user.id, badge_id=badge.id))
            held.add(badge.slug)

    db.commit()
    return sorted(held)
