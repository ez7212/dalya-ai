"""
Service layer for agent-scoped community-research overrides.

Resolves a listing's project, loads its (shared) community research KB, and
merges the owning agent's private per-field corrections. Overrides are scoped
to (brokerage_id, agent_user_id, project_key) where project_key is the slug of
the research project (e.g. "golf_grove") — so a correction applies to all of
the agent's listings in that project, now and future, and never leaks.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.community_field_catalog import FIELD_BY_KEY, resolve_fields
from app.models.db_models import DBAgentCommunityOverride, DBCommunityResearch, DBListing

_KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent.parent / "knowledge_base"


def project_name_for_listing(listing: DBListing) -> Optional[str]:
    """The project/development name (legacy field: spa_data.project), e.g. 'Golf Grove'."""
    spa = listing.spa_data if isinstance(listing.spa_data, dict) else {}
    name = spa.get("project")
    if isinstance(name, str) and name.strip() and name.strip().lower() != "listing":
        return name.strip()
    return None


def project_key_from_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return cleaned or None


def find_research(db: Session, project_name: str) -> Optional[DBCommunityResearch]:
    """Match the shared research row the same way the buyer-facing bot does."""
    return (
        db.query(DBCommunityResearch)
        .filter(DBCommunityResearch.project_name.ilike(project_name))
        .first()
    )


def _load_kb(file_path: Optional[str]) -> Optional[dict[str, Any]]:
    if not file_path:
        return None
    target = (_KNOWLEDGE_BASE_DIR / file_path).resolve()
    # Stay inside the knowledge base dir.
    if _KNOWLEDGE_BASE_DIR.resolve() not in target.parents or not target.is_file():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def agent_overrides(
    db: Session, *, brokerage_id: str, agent_user_id: str, project_key: str
) -> list[DBAgentCommunityOverride]:
    return (
        db.query(DBAgentCommunityOverride)
        .filter(
            DBAgentCommunityOverride.brokerage_id == brokerage_id,
            DBAgentCommunityOverride.agent_user_id == agent_user_id,
            DBAgentCommunityOverride.project_key == project_key,
        )
        .all()
    )


def agent_holds_listing_in_project(
    db: Session, *, brokerage_id: str, agent_user_id: str, project_key: str
) -> bool:
    """Guard: the agent must currently have a listing in this project to edit it."""
    rows = (
        db.query(DBListing)
        .filter(
            DBListing.brokerage_id == brokerage_id,
            (DBListing.assigned_agent_id == agent_user_id) | (DBListing.seller_id == agent_user_id),
        )
        .all()
    )
    for listing in rows:
        if project_key_from_name(project_name_for_listing(listing)) == project_key:
            return True
    return False


def _serialize_override(o: DBAgentCommunityOverride) -> dict[str, Any]:
    return {
        "override_id": o.override_id,
        "field_key": o.field_key,
        "value_text": o.value_text,
        "note": o.note,
        "buyer_safe": o.buyer_safe,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }


def build_community_view(
    db: Session, *, listing: DBListing, brokerage_id: str, agent_user_id: str
) -> dict[str, Any]:
    """Structured, field-by-field research view with the agent's overrides merged in."""
    project_name = project_name_for_listing(listing)
    project_key = project_key_from_name(project_name)

    if not project_name or not project_key:
        return {
            "project_name": None,
            "project_key": None,
            "research_status": "none",
            "research_confidence": None,
            "source_count": 0,
            "fields": [],
        }

    research = find_research(db, project_name)
    kb = _load_kb(research.file_path) if research else None
    overrides_by_field = {
        o.field_key: o
        for o in agent_overrides(db, brokerage_id=brokerage_id, agent_user_id=agent_user_id, project_key=project_key)
    }

    fields: list[dict[str, Any]] = []
    for field in resolve_fields(kb or {}):
        o = overrides_by_field.get(field["key"])
        fields.append({**field, "override": _serialize_override(o) if o else None})

    if research is None:
        status = "none"
    elif research.status == "approved":
        status = "approved"
    else:
        status = "in_review"

    return {
        "project_name": project_name,
        "project_key": project_key,
        "research_status": status,
        "research_confidence": getattr(research, "research_confidence", None) if research else None,
        "source_count": len(research.source_urls or []) if research else 0,
        "fields": fields,
    }


def overrides_for_prompt(
    db: Session, *, brokerage_id: str, agent_user_id: str, project_key: str
) -> list[dict[str, Any]]:
    """Buyer-safe overrides as {label, value, note} for injection into the advisor prompt."""
    out: list[dict[str, Any]] = []
    for o in agent_overrides(db, brokerage_id=brokerage_id, agent_user_id=agent_user_id, project_key=project_key):
        if not o.buyer_safe:
            continue
        label = FIELD_BY_KEY.get(o.field_key, {}).get("label", o.field_key)
        out.append({"label": label, "value": o.value_text, "note": o.note})
    return out
