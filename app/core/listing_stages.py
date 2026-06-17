"""
Listing processing stages — tracks where a listing is in the onboarding pipeline.

Stage lifecycle:
- pending     → not started
- in_progress → actively being worked on
- complete    → done
- blocked     → waiting on seller action (include reason in note)

Stages (in order):
1. spa_verified        — SPA was parsed successfully (auto)
2. community_research  — System researches community data for the project (auto)
3. listing_review      — Admin review of listing details (manual)
4. trakheesi_permit    — RERA advertising permit application (manual, external)
5. portal_listings     — Live on Property Finder / Bayut (manual)
6. ai_advisor_live     — Dalya answers buyer inquiries (auto once prior stages complete)
"""

from datetime import datetime
from typing import Optional


STAGE_ORDER = [
    "spa_verified",
    "community_research",
    "listing_review",
    "trakheesi_permit",
    "portal_listings",
    "ai_advisor_live",
]

STAGE_LABELS = {
    "spa_verified": "SPA Verified",
    "community_research": "Community Research",
    "listing_review": "Listing Review",
    "trakheesi_permit": "Trakheesi Permit",
    "portal_listings": "Portal Listings",
    "ai_advisor_live": "AI Advisor Live",
}

STAGE_DESCRIPTIONS = {
    "spa_verified": "Your SPA has been parsed and verified",
    "community_research": "Researching community data, amenities, and investment insights",
    "listing_review": "Our team is reviewing your listing details",
    "trakheesi_permit": "RERA advertising permit application",
    "portal_listings": "Property Finder, Bayut, and Dalya",
    "ai_advisor_live": "Dalya answers buyer inquiries 24/7",
}

VALID_STATUSES = {"pending", "in_progress", "complete", "blocked"}


def default_stages() -> dict:
    """Return the initial stages dict for a new listing."""
    now = datetime.utcnow().isoformat()
    stages = {}
    for key in STAGE_ORDER:
        stages[key] = {"status": "pending", "at": None, "note": None}
    # SPA is verified the moment the listing is created (parse already happened)
    stages["spa_verified"] = {"status": "complete", "at": now, "note": None}
    return stages


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
    # Ensure all stages exist (backfill legacy listings)
    for k in STAGE_ORDER:
        if k not in new_stages:
            new_stages[k] = {"status": "pending", "at": None, "note": None}

    new_stages[stage_key] = {
        "status": status,
        "at": datetime.utcnow().isoformat(),
        "note": note,
    }
    return new_stages


def serialize_stages(stages: Optional[dict]) -> list[dict]:
    """Return stages as an ordered list with labels/descriptions for frontend display."""
    stages = stages or {}
    result = []
    for key in STAGE_ORDER:
        stage = stages.get(key) or {"status": "pending", "at": None, "note": None}
        result.append({
            "key": key,
            "label": STAGE_LABELS[key],
            "description": STAGE_DESCRIPTIONS[key],
            "status": stage.get("status", "pending"),
            "at": stage.get("at"),
            "note": stage.get("note"),
        })
    return result
