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


def _parse(content: str) -> dict:
    content = (content or "").strip()
    if content.startswith("```"):
        content = content.strip("`")
        content = content[content.find("{"):]
    if not content:
        raise RuntimeError("The model returned an empty response.")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("The model returned invalid JSON.") from exc


def _thinking_config(types):
    """Keep Naa fast: 2.x models take thinking_budget (0 = off); newer
    models (3.x) take thinking_level instead and reject thinking_budget."""
    if settings.gemini_model.startswith("gemini-2"):
        return types.ThinkingConfig(thinking_budget=0)
    return types.ThinkingConfig(thinking_level="low")


def _ask_gemini(question: str, system_instruction: str) -> dict:
    """Hosted model (free tier available) - works on Render."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_json_schema=OLLAMA_RESPONSE_SCHEMA,
            temperature=0.2,
            # Thinking tokens count against this limit, so leave room.
            max_output_tokens=4096,
            thinking_config=_thinking_config(types),
        ),
    )
    return _parse(response.text)


def _ask_ollama(question: str, system_instruction: str) -> dict:
    """Self-hosted Ollama - only works where an Ollama server is reachable."""
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": question},
        ],
        "stream": False,
        "format": OLLAMA_RESPONSE_SCHEMA,
        "options": {"temperature": 0.2, "num_predict": 500},
    }
    try:
        response = httpx.post(
            f"{settings.ollama_url.rstrip('/')}/api/chat",
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Could not connect to Ollama: {exc}") from exc

    return _parse(response.json().get("message", {}).get("content", ""))


def answer_from_database(question: str, sites: list[Site]) -> dict:
    """No-AI fallback: answer straight from the reviewed database content,
    so Naa always replies even if the AI provider is down or not configured."""
    words = {w.strip("?.,!").lower() for w in question.split() if len(w) > 3}
    matches = [
        s for s in sites
        if any(w in f"{s.name} {s.region} {s.category}".lower() for w in words)
    ] or sites[:3]

    if not matches:
        return {
            "title": "ANANSE Heritage Guide",
            "introduction": "That information is not currently available in ANANSE.",
            "sections": [], "visitor_notes": [], "sources": [],
        }

    sections = []
    for s in matches[:3]:
        content = s.summary or "No summary is available yet."
        if s.journey_minutes:
            content += f" Typical journey time: {s.journey_minutes} minutes."
        sections.append({"heading": f"{s.name} ({s.region})", "content": content})

    return {
        "title": matches[0].name if len(matches) == 1 else "ANANSE Heritage Guide",
        "introduction": "Here is what ANANSE's reviewed heritage records say.",
        "sections": sections,
        "visitor_notes": [],
        "sources": [],
    }


def ask(question: str, site_context: str) -> dict:
    """Send the database context and visitor question to the configured model.

    Provider order: Gemini (if GEMINI_API_KEY is set), then Ollama
    (if OLLAMA_URL is set). Raises RuntimeError if none is available.
    """
    system_instruction = build_system_instruction(site_context)
    errors = []

    if settings.gemini_api_key:
        try:
            return _ask_gemini(question, system_instruction)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Gemini: {exc}")

    if settings.ollama_url:
        try:
            return _ask_ollama(question, system_instruction)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Ollama: {exc}")

    raise RuntimeError("; ".join(errors) or "No AI provider is configured.")


def provider_status() -> dict:
    """Try a tiny request to each configured provider and report the result
    (no keys or secrets are returned). Used by GET /api/naa/status."""
    status = {
        "gemini_key_set": bool(settings.gemini_api_key),
        "gemini_model": settings.gemini_model,
        "ollama_url_set": bool(settings.ollama_url),
    }
    if settings.gemini_api_key:
        try:
            result = _ask_gemini(
                "Say hello to a visitor in one short sentence.",
                build_system_instruction("No heritage site data is needed for this test."),
            )
            status["gemini"] = "ok: " + str(result.get("introduction", ""))[:120]
        except Exception as exc:  # noqa: BLE001
            status["gemini"] = f"error: {type(exc).__name__}: {str(exc)[:300]}"
    return status
