"""Load the reviewed heritage content into the database.

    python -m app.seed

The content comes from app/content/heritage.json, which is exported from the
frontend bundle by tools/export_content.mjs so the two never drift apart.
"""

import json
from pathlib import Path

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import Badge, Site, Story, User

CONTENT = Path(__file__).resolve().parent / "content" / "heritage.json"

DEMO_USER = {
    "full_name": "Ama Mensah",
    "email": "ama@example.com",
    "password": "ananse123",
    "role": "visitor",
}


def load() -> dict:
    with CONTENT.open(encoding="utf-8") as handle:
        return json.load(handle)


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    content = load()
    db = SessionLocal()

    try:
        for entry in content["sites"]:
            site = db.query(Site).filter(Site.slug == entry["slug"]).first() or Site(slug=entry["slug"])
            site.name = entry["name"]
            site.region = entry["region"]
            site.category = entry["category"]
            site.latitude = entry["latitude"]
            site.longitude = entry["longitude"]
            site.summary = entry["summary"]
            site.history = entry["history"]
            site.facts = entry["facts"]
            site.accessibility = entry["accessibility"]
            site.reviewer = entry.get("reviewer", "")
            site.journey_minutes = entry.get("journeyMinutes", 60)
            site.badge_slug = entry.get("badge", "")
            db.add(site)

        db.commit()

        for slug, entry in content["stories"].items():
            site = db.query(Site).filter(Site.slug == slug).first()
            if not site:
                continue
            story = db.query(Story).filter(Story.site_id == site.id).first() or Story(site_id=site.id)
            story.title = entry["title"]
            story.minutes = entry["minutes"]
            story.chapters = entry["chapters"]
            db.add(story)

        for entry in content["badges"]:
            badge = db.query(Badge).filter(Badge.slug == entry["slug"]).first() or Badge(slug=entry["slug"])
            badge.name = entry["name"]
            badge.requirement = entry["requirement"]
            badge.threshold = entry["threshold"]
            badge.rule = entry["rule"]
            db.add(badge)

        if not db.query(User).filter(User.email == DEMO_USER["email"]).first():
            db.add(
                User(
                    full_name=DEMO_USER["full_name"],
                    email=DEMO_USER["email"],
                    password_hash=hash_password(DEMO_USER["password"]),
                    role=DEMO_USER["role"],
                )
            )

        db.commit()

        print(
            f"Seeded {db.query(Site).count()} sites, "
            f"{db.query(Story).count()} stories and "
            f"{db.query(Badge).count()} badges."
        )
        print(f"Demo sign in: {DEMO_USER['email']} / {DEMO_USER['password']}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
