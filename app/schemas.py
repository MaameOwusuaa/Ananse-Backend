"""Pydantic schemas — the shapes the API accepts and returns.

Field names are camelCase on the way out so the frontend can use one set of
property names everywhere.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SiteCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    region: str = Field(min_length=2, max_length=60)
    category: str = Field(min_length=2, max_length=60)
    latitude: float
    longitude: float
    summary: str = Field(min_length=10)
    history: list[str] = Field(default_factory=list)
    facts: dict[str, str] = Field(default_factory=dict)
    accessibility: list[str] = Field(default_factory=list)
    reviewer: str = ""
    journey_minutes: int = Field(default=60, ge=1)
    badge_slug: str = ""


class SiteUpdate(BaseModel):
    name: str | None = None
    region: str | None = None
    category: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    summary: str | None = None
    history: list[str] | None = None
    facts: dict[str, str] | None = None
    accessibility: list[str] | None = None
    reviewer: str | None = None
    journey_minutes: int | None = Field(default=None, ge=1)
    badge_slug: str | None = None


class SiteOut(BaseModel):
    id: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    slug: str
    name: str
    region: str
    category: str
    latitude: float
    longitude: float
    summary: str
    history: list[str] = Field(default_factory=list)
    facts: dict[str, str] = Field(default_factory=dict)
    accessibility: list[str] = Field(default_factory=list)
    reviewer: str = ""
    journey_minutes: int = Field(default=60, serialization_alias="journeyMinutes")
    badge_slug: str = Field(default="", serialization_alias="badge")


class StoryCreate(BaseModel):
    site_id: int
    title: str = Field(min_length=2, max_length=160)
    minutes: int = Field(default=5, ge=1)
    chapters: list[dict] = Field(default_factory=list)


class StoryUpdate(BaseModel):
    site_id: int | None = None
    title: str | None = None
    minutes: int | None = Field(default=None, ge=1)
    chapters: list[dict] | None = None


class StoryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    site: str
    minutes: int
    chapters: list[dict]


class BadgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    requirement: str
    threshold: int
    rule: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1200
    user: UserOut


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginIn(BaseModel):
    id_token: str = Field(min_length=1, max_length=8192)


class VisitIn(BaseModel):
    slug: str
    source: str = "app"


class VisitOut(BaseModel):
    slug: str
    source: str
    recorded_at: datetime


class AnalyticsEventIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_type: Literal[
        "page_view",
        "site_view",
        "story_view",
        "story_complete",
        "search",
    ] = Field(alias="eventType")
    page: str = Field(
        min_length=1,
        max_length=240,
        pattern=r"^/[A-Za-z0-9/_-]*$",
    )
    site_slug: str | None = Field(
        default=None,
        alias="siteSlug",
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )


class AnalyticsEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    event_type: str = Field(serialization_alias="eventType")
    created_at: datetime = Field(serialization_alias="createdAt")


class AnalyticsDailyCount(BaseModel):
    day: date
    count: int


class AnalyticsSiteCount(BaseModel):
    site_slug: str = Field(serialization_alias="siteSlug")
    count: int


class AnalyticsSummaryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_events: int = Field(serialization_alias="totalEvents")
    events_by_type: dict[str, int] = Field(serialization_alias="eventsByType")
    daily_events: list[AnalyticsDailyCount] = Field(serialization_alias="dailyEvents")
    top_sites: list[AnalyticsSiteCount] = Field(serialization_alias="topSites")


class VisitPlanCreate(BaseModel):
    site_slug: str = Field(min_length=2, max_length=80)
    visit_date: date
    visit_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    visitors: Literal["1", "2", "3", "4", "5", "6+"]


class VisitPlanOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    site_slug: str = Field(serialization_alias="siteSlug")
    site_name: str = Field(serialization_alias="siteName")
    user_name: str = Field(serialization_alias="userName")
    user_email: EmailStr = Field(serialization_alias="userEmail")
    visit_date: date = Field(serialization_alias="visitDate")
    visit_time: str = Field(serialization_alias="visitTime")
    visitors: str
    saved_at: datetime = Field(serialization_alias="savedAt")


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    full_name: str = Field(serialization_alias="fullName")
    email: EmailStr
    role: str
    created_at: datetime = Field(serialization_alias="createdAt")
    visit_count: int = Field(serialization_alias="visitCount")
    story_count: int = Field(serialization_alias="storyCount")
    plan_count: int = Field(serialization_alias="planCount")


class StoryProgressIn(BaseModel):
    slug: str
    score: int = 0

    @field_validator("score")
    @classmethod
    def score_is_sane(cls, value: int) -> int:
        return max(0, min(value, 50))


class StoryProgressOut(BaseModel):
    slug: str
    score: int
    completed_at: datetime


class PassportOut(BaseModel):
    visits: list[VisitOut]
    stories: list[StoryProgressOut]
    badges: list[str]


class NaaIn(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=500,
    )
    site_slug: str | None = None


class NaaSection(BaseModel):
    heading: str
    content: str


class NaaSource(BaseModel):
    title: str
    url: str


class NaaOut(BaseModel):
    title: str
    introduction: str
    sections: list[NaaSection] = Field(
        default_factory=list
    )
    visitor_notes: list[str] = Field(
        default_factory=list
    )
    sources: list[NaaSource] = Field(
        default_factory=list
    )