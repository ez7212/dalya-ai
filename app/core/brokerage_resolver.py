"""
Brokerage and managing-agent resolution for the multi-tenant platform.

Inbound buyer messages arrive on a brokerage's Brokerage AI WhatsApp number.
This module resolves that number to the owning DBBrokerage so the rest of
the pipeline can scope listing queries, fee math, and prompt construction
correctly. It also resolves the managing agent for a listing — the routing
key used for escalations to the Agents AI number.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.db_models import (
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageMember,
    DBListing,
)

logger = logging.getLogger(__name__)


def _normalise_phone(number: Optional[str]) -> Optional[str]:
    """Strip whatsapp:/ prefix and trim whitespace. Returns None on falsy input."""
    if not number:
        return None
    cleaned = number.strip()
    if cleaned.lower().startswith("whatsapp:"):
        cleaned = cleaned[len("whatsapp:"):]
    return cleaned or None


def resolve_brokerage_by_inbound_number(
    to_number: str,
    db: Optional[Session] = None,
) -> Optional[DBBrokerage]:
    """
    Map an inbound `To` number on the webhook → DBBrokerage by matching against
    `brokerage_ai_number`. Returns None if no brokerage owns that number.
    """
    normalized = _normalise_phone(to_number)
    if not normalized:
        return None

    own_session = db is None
    session = db or SessionLocal()
    try:
        brokerage = (
            session.query(DBBrokerage)
            .filter(DBBrokerage.brokerage_ai_number == normalized)
            .first()
        )
        return brokerage
    finally:
        if own_session:
            session.close()


def resolve_brokerage_by_agents_ai_number(
    to_number: str,
    db: Optional[Session] = None,
) -> Optional[DBBrokerage]:
    """
    Map an inbound `To` number from the Agents AI webhook → DBBrokerage by
    matching against `agents_ai_number`. Used when a managing agent replies on
    their brokerage's Agents AI thread.
    """
    normalized = _normalise_phone(to_number)
    if not normalized:
        return None

    own_session = db is None
    session = db or SessionLocal()
    try:
        return (
            session.query(DBBrokerage)
            .filter(DBBrokerage.agents_ai_number == normalized)
            .first()
        )
    finally:
        if own_session:
            session.close()


def resolve_brokerage_for_listing(
    listing_id: str,
    db: Optional[Session] = None,
) -> Optional[DBBrokerage]:
    """Look up the brokerage that owns a given listing."""
    own_session = db is None
    session = db or SessionLocal()
    try:
        listing = session.get(DBListing, listing_id)
        if not listing or not listing.brokerage_id:
            return None
        return session.get(DBBrokerage, listing.brokerage_id)
    finally:
        if own_session:
            session.close()


def get_managing_agent(
    listing: DBListing,
    db: Optional[Session] = None,
) -> Optional[DBAgentProfile]:
    """
    Resolve the managing-agent DBAgentProfile for a listing.

    The listing carries `assigned_agent_id` (the agent's user_id). We look up
    the profile under the same brokerage. This is the routing key for
    escalations — the profile's whatsapp_phone is the address the Agents AI
    relay surfaces inside its envelope.
    """
    if not listing or not listing.assigned_agent_id:
        return None

    own_session = db is None
    session = db or SessionLocal()
    try:
        return (
            session.query(DBAgentProfile)
            .filter(
                DBAgentProfile.brokerage_id == listing.brokerage_id,
                DBAgentProfile.user_id == listing.assigned_agent_id,
            )
            .first()
        )
    finally:
        if own_session:
            session.close()


def list_approved_brokerages(db: Optional[Session] = None) -> list[DBBrokerage]:
    """
    Return brokerages an agent is allowed to register under
    (i.e. agent_signup_enabled, active, with a real_estate_number set).
    """
    own_session = db is None
    session = db or SessionLocal()
    try:
        return (
            session.query(DBBrokerage)
            .filter(
                DBBrokerage.status == "active",
                DBBrokerage.agent_signup_enabled.is_(True),
                DBBrokerage.real_estate_number.isnot(None),
            )
            .order_by(DBBrokerage.name.asc())
            .all()
        )
    finally:
        if own_session:
            session.close()


def get_managing_agent_title(brokerage: Optional[DBBrokerage]) -> str:
    """
    Pull the managing-agent role title from the brokerage's prompt_config /
    default_fee_framing, falling back to a generic label.
    """
    if not brokerage:
        return "the managing agent"
    prompt_cfg = brokerage.prompt_config or {}
    if isinstance(prompt_cfg, dict) and prompt_cfg.get("managing_agent_title"):
        return prompt_cfg["managing_agent_title"]
    fee_framing = brokerage.default_fee_framing or {}
    if isinstance(fee_framing, dict) and fee_framing.get("managing_agent_title"):
        return fee_framing["managing_agent_title"]
    return "the managing agent"
