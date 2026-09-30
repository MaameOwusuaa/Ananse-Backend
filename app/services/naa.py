from __future__ import annotations

import json

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Site


OLLAMA_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "introduction": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["heading", "content"],
            },
        },
        "visitor_notes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["title", "url"],
            },
        },
    },
    "required": [
        "title",
        "introduction",
        "sections",
        "visitor_notes",
        "sources",
    ],
}


def build_site_context(
    db: Session,
    site_slug: str | None = None,
) -> str:
    """
    Retrieve only the relevant heritage site information from MySQL.

    MySQL remains the source of truth.
    Ollama only receives the retrieved information and turns it
    into a visitor-friendly response.
    """

    query = db.query(Site)

    if site_slug:
        query = query.filter(Site.slug == site_slug)

    sites = query.all()

    if not sites:
        return "No matching heritage site was found in the ANANSE database."

    context_parts = []

    for site in sites:
        history = site.history or {}
        facts = site.facts or {}
        accessibility = site.accessibility or {}

        context_parts.append(
            f"""
HERITAGE SITE

Name: {site.name}
Region: {site.region}
Category: {site.category}

Summary:
{site.summary}

Historical information:
{json.dumps(history, ensure_ascii=False)}

Key facts:
{json.dumps(facts, ensure_ascii=False)}

Accessibility:
{json.dumps(accessibility, ensure_ascii=False)}

Reviewer:
{site.reviewer}

Typical journey time:
{site.journey_minutes} minutes
"""
        )

    return "\n".join(context_parts)


def build_system_instruction(site_context: str) -> str:
    """
    Short system instruction to reduce unnecessary model processing.
    """

    return f"""
You are Naa, the cultural heritage guide for ANANSE.

Answer the visitor using ONLY the information supplied below.

DATABASE INFORMATION:
{site_context}

RULES:
1. MySQL database information is the source of truth.
2. Do not invent historical facts, dates, locations, prices, opening hours,
   facilities, or other information that is not provided.
3. If the database does not contain enough information to answer something,
   say that the information is not currently available in ANANSE.
4. Be clear, friendly, concise, and useful to a visitor.
5. Return ONLY valid JSON matching the requested response structure.
6. Do not use Markdown.
7. Do not create external sources unless they are provided in the database.
8. Keep the response reasonably short.

The JSON must contain:
- title
- introduction
- sections
- visitor_notes
- sources
"""


def ask(
    question: str,
    site_context: str,
) -> dict:
    """
    Send the database context and visitor question to Ollama.
    """

    system_instruction = build_system_instruction(site_context)

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {
                "role": "system",
                "content": system_instruction,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        "stream": False,
        "format": OLLAMA_RESPONSE_SCHEMA,
        "options": {
            "temperature": 0.2,
            "num_predict": 500,
        },
    }

    try:
        response = httpx.post(
            f"{settings.ollama_url}/api/chat",
            json=payload,
            timeout=120.0,
        )

        response.raise_for_status()

    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"Could not connect to Ollama: {exc}"
        ) from exc

    data = response.json()

    message = data.get("message", {})
    content = message.get("content", "")

    if not content:
        raise RuntimeError("Ollama returned an empty response.")

    try:
        return json.loads(content)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Ollama returned invalid JSON."
        ) from exc