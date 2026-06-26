"""
Listing processing stages — the agent-facing "Processing health" tracker.

We deliberately track only the two stages an agent actually cares about:

1. community_research  — System researches the project's community data.
                         Reflects the live DBCommunityResearch job:
                         pending/researching → in_progress, approved → complete.
2. ai_advisor_live     — Dalya answers buyer inquiries. Live by default (the bot
                         is always on the moment a listing exists).

Stage status lifecycle: pending → in_progress → complete (or blocked, with a note).

The earlier SPA-verified / listing-review / Trakheesi-permit / portal-listings
stages were removed from the tracker — they were internal/ops concerns, not agent
signal.
"""

from datetime import datetime
from typing import Optional


STAGE_ORDER = [
    "community_research",
    "ai_advisor_live",
]

STAGE_LABELS = {
    "community_research": "Community Research",
    "ai_advisor_live": "AI Advisor",
}

STAGE_DESCRIPTIONS = {
    "community_research": "Researching community data, amenities, and investment insights",
    "ai_advisor_live": "Dalya answers buyer inquiries 24/7",
}

VALID_STATUSES = {"pending", "in_progress", "complete", "blocked"}


def default_stages() -> dict:
    """Return the initial stages dict for a new listing. The AI Advisor is Live
    immediately (the bot is always on); community research starts pending until a
    research job reports progress."""
    now = datetime.utcnow().isoformat()
    return {
        "community_research": {"status": "pending", "at": None, "note": None},
        "ai_advisor_live": {"status": "complete", "at": now, "note": None},
    }


def update_stage(
    stages: dict,
    stage_key: str,
    status: str,
    note: Optional[str] = None,
) -> dict:
    """Update a single stage. Returns a new dict (safe for SQLAlchemy JSON mutation tracking)."""
    if stage_key not in STAGE_ORDER:
        raise ValueError(f"Unknown stage: {stage_key}")
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    new_stages = dict(stages or {})
    for k in STAGE_ORDER:
        if k not in new_stages:
            new_stages[k] = {"status": "pending", "at": None, "note": None}

    new_stages[stage_key] = {
        "status": status,
        "at": datetime.utcnow().isoformat(),
        "note": note,
    }
    return new_stages


def community_stage_from_research_status(research_status: Optional[str]) -> Optional[tuple[str, str]]:
    """Map a DBCommunityResearch row status to a (stage_status, note) for the
    community_research tracker. Returns None when there's nothing to override."""
    if not research_status:
        return None
    status = research_status.lower()
    if status in ("approved", "complete", "completed"):
        return ("complete", "Community data is ready.")
    if status in ("pending", "queued", "triggered", "researching", "in_progress"):
        return ("in_progress", "Researching community data — check back soon.")
    if status in ("needs_review", "in_review"):
        return ("in_progress", "Community research is being reviewed.")
    if status in ("failed", "error", "blocked"):
        return ("blocked", "Community research needs admin review.")
    return None


def serialize_stages(
    stages: Optional[dict],
    *,
    community_research_status: Optional[str] = None,
) -> list[dict]:
    """Return stages as an ordered list with labels/descriptions for the frontend.

    The AI Advisor reads as Live (complete) by default. The community_research
    stage is reconciled with the live research job status when one is supplied, so
    the tracker shows in_progress while the job runs and complete when it's done.
    """
    stages = stages or {}
    community_override = community_stage_from_research_status(community_research_status)
    result = []
    for key in STAGE_ORDER:
        stage = stages.get(key) or {"status": "pending", "at": None, "note": None}
        status = stage.get("status", "pending")
        note = stage.get("note")

        if key == "ai_advisor_live" and status in (None, "pending"):
            # The advisor is Live the moment a listing exists.
            status = "complete"
        if key == "community_research" and community_override:
            status, note = community_override

        result.append({
            "key": key,
            "label": STAGE_LABELS[key],
            "description": STAGE_DESCRIPTIONS[key],
            "status": status,
            "at": stage.get("at"),
            "note": note,
        })
    return result
