"""
Post-viewing follow-up draft CTA (DAL-166 — flagged optional).

The smallest possible loop-closer: when buyer feedback lands, the agent can
generate one review-only draft grounded on the feedback content, the buyer
card's confirmed qualification, and — only if real matches exist — up to 3
alternative listings from the SAME brokerage's inventory. A zero-match case
produces a plain follow-up; the draft is never padded with weak matches.

Reuses the existing draft approve/edit/send machinery. No new send paths.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.session import safe_commit
from app.models.db_models import (
    DBConversation,
    DBDraftReply,
    DBListing,
    DBViewing,
    DBViewingFeedback,
)

logger = logging.getLogger(__name__)

MAX_ALTERNATIVES = 3


def _confirmed_qualification(db: Session, *, brokerage_id: str, buyer_phone: str) -> dict:
    """Confirmed-only fields — alternatives must match what the agent verified."""
    from app.core.buyer_profiles import effective_fields, get_or_create_profile

    profile = get_or_create_profile(db, brokerage_id=brokerage_id, buyer_phone=buyer_phone)
    fields = effective_fields(db, profile)
    return {
        field: entry["value"]
        for field, entry in fields.items()
        if entry["provenance"] == "agent_confirmed" and entry["value"] is not None
    }


def find_alternative_listings(
    db: Session,
    *,
    brokerage_id: str,
    exclude_listing_id: str,
    confirmed: dict,
) -> list[DBListing]:
    """
    Simple filter match against confirmed fields only — not the deferred AI
    matching system. No confirmed criteria → no alternatives (never padded).
    """
    budget_max = confirmed.get("budget_max_aed")
    bedrooms = confirmed.get("bedrooms")
    property_type = confirmed.get("property_type")
    if budget_max is None and bedrooms is None and property_type is None:
        return []

    candidates = (
        db.query(DBListing)
        .filter(
            DBListing.brokerage_id == brokerage_id,   # same brokerage only
            DBListing.listing_id != exclude_listing_id,
            DBListing.seller_asking_price.isnot(None),
        )
        .all()
    )
    matches: list[DBListing] = []
    for listing in candidates:
        spa = listing.spa_data or {}
        if budget_max is not None and listing.seller_asking_price > float(budget_max) * 1.05:
            continue
        if bedrooms is not None:
            listing_beds = spa.get("bedrooms")
            try:
                if listing_beds is None or int(listing_beds) != int(bedrooms):
                    continue
            except (TypeError, ValueError):
                continue
        if property_type is not None:
            spa_type = str(spa.get("property_type") or listing.property_type or "").lower()
            if spa_type and str(property_type).lower() not in spa_type:
                continue
        matches.append(listing)
    matches.sort(key=lambda listing: listing.seller_asking_price or 0)
    return matches[:MAX_ALTERNATIVES]


def create_feedback_follow_up_draft(
    db: Session,
    *,
    brokerage_id: str,
    viewing: DBViewing,
    agent_user_id: str,
) -> DBDraftReply:
    feedback = (
        db.query(DBViewingFeedback)
        .filter(
            DBViewingFeedback.viewing_id == viewing.viewing_id,
            DBViewingFeedback.participant_type == "buyer",
            DBViewingFeedback.status == "received",
        )
        .first()
    )
    if not feedback:
        raise ValueError("No buyer feedback received for this viewing yet")

    conversation = db.get(DBConversation, viewing.conversation_id)
    if not conversation:
        raise ValueError("Viewing has no conversation")
    listing = db.get(DBListing, viewing.listing_id)
    spa = (listing.spa_data or {}) if listing else {}
    project = spa.get("project") or "the property"
    buyer = (conversation.buyer_name or "there").split(" ")[0]

    confirmed = _confirmed_qualification(
        db, brokerage_id=brokerage_id, buyer_phone=conversation.buyer_phone
    )
    alternatives = find_alternative_listings(
        db,
        brokerage_id=brokerage_id,
        exclude_listing_id=viewing.listing_id,
        confirmed=confirmed,
    )

    lines = [f"Hi {buyer}, thanks for taking the time to view {project}."]
    if feedback.summary:
        lines.append(f"You mentioned: {feedback.summary.strip()}")
    if alternatives:
        lines.append("Based on what you're looking for, a few other options from our portfolio:")
        for alternative in alternatives:
            alt_spa = alternative.spa_data or {}
            alt_label = alt_spa.get("project") or alternative.listing_id
            price = alternative.seller_asking_price
            lines.append(
                f"• {alt_label}"
                + (f" — AED {price:,.0f}" if price else "")
            )
        lines.append("Happy to arrange viewings for any of these.")
    else:
        lines.append("Would you like to discuss next steps, or shall I keep an eye out for similar options?")
    draft_text = "\n".join(lines)

    draft = DBDraftReply(
        brokerage_id=brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=conversation.buyer_phone,
        agent_user_id=agent_user_id,
        intent="follow_up",
        draft_text=draft_text,
        source="post_viewing_followup_cta",
        status="draft",  # review-only: the normal approval flow, never auto-sent
        metadata_json={
            "viewing_id": viewing.viewing_id,
            "feedback_id": feedback.feedback_id,
            "grounding": {
                "feedback_summary": feedback.summary,
                "confirmed_fields": confirmed,
            },
            "alternative_listing_ids": [listing.listing_id for listing in alternatives],
        },
    )
    db.add(draft)
    safe_commit(db)
    db.refresh(draft)
    return draft
