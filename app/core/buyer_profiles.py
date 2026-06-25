"""
Brokerage-scoped buyer profiles with field-level provenance (DAL-164).

Buyer context used to live in conversation summaries; agents need the
qualification snapshot at a glance and the ability to correct AI inferences.

The no-overwrite rule is structural, not a prompt instruction: qualification
values are field-level rows keyed (profile_id, field, provenance). The AI
write path (`record_inferred_field`) only ever upserts provenance='ai_inferred'
rows — an agent_confirmed value is physically a different row it cannot touch.
A conflicting inference therefore coexists as a suggestion chip, which only an
agent action (`confirm_field`) can promote.

See docs/adr/ADR-2026-06-10-buyer-profile-provenance.md.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.brokerage_access import record_compliance_event
from app.db.session import safe_commit
from app.models.db_models import (
    DBBrokerageBuyerProfile,
    DBBuyerProfileField,
    DBListingInquiry,
    DBConversation,
    DBMessage,
)
from app.schemas.conversation import BuyerProfile, ListingInquiry

logger = logging.getLogger(__name__)

QUALIFICATION_FIELDS = {
    "budget_min_aed",
    "budget_max_aed",
    "financing",            # cash | mortgage_preapproved | mortgage_unknown | unknown
    "preapproval_amount_aed",
    "preapproval_bank",
    "purpose",              # investment | end_user | both
    "family_size",
    "decision_makers",
    "in_dubai_now",
    "viewing_availability",
    "other_agent_status",
    "urgency",
    "contact_preference",
    "timeline",
    "target_areas",
    "property_type",
    "bedrooms",
    "must_haves",
    "deal_breakers",
}

PROVENANCE_AI = "ai_inferred"
PROVENANCE_CONFIRMED = "agent_confirmed"


def get_or_create_profile(
    db: Session,
    *,
    brokerage_id: str,
    buyer_phone: str,
    name: Optional[str] = None,
    source: Optional[str] = None,
) -> DBBrokerageBuyerProfile:
    profile = (
        db.query(DBBrokerageBuyerProfile)
        .filter(
            DBBrokerageBuyerProfile.brokerage_id == brokerage_id,
            DBBrokerageBuyerProfile.buyer_phone == buyer_phone,
        )
        .first()
    )
    if profile:
        if name and not profile.name:
            profile.name = name
        return profile
    profile = DBBrokerageBuyerProfile(
        brokerage_id=brokerage_id,
        buyer_phone=buyer_phone,
        name=name,
        source=source,
    )
    db.add(profile)
    db.flush()
    return profile


def record_inferred_field(
    db: Session,
    *,
    profile: DBBrokerageBuyerProfile,
    field: str,
    value: Any,
    confidence: Optional[float] = None,
    source_message_id: Optional[int] = None,
    now: Optional[datetime] = None,
) -> Optional[DBBuyerProfileField]:
    """
    AI write path. Upserts ONLY the ai_inferred row for this field — the
    agent_confirmed row is unreachable from here by construction. When a
    confirmed value exists and differs, the inferred row becomes the
    suggestion chip the card surfaces.
    """
    if field not in QUALIFICATION_FIELDS:
        raise ValueError(f"Unknown qualification field: {field}")
    if value is None:
        return None
    now = now or datetime.utcnow()

    row = (
        db.query(DBBuyerProfileField)
        .filter(
            DBBuyerProfileField.profile_id == profile.profile_id,
            DBBuyerProfileField.field == field,
            DBBuyerProfileField.provenance == PROVENANCE_AI,  # structural guard
        )
        .first()
    )
    if row:
        row.value = value
        row.confidence = confidence
        row.source_message_id = source_message_id
        row.updated_at = now
    else:
        row = DBBuyerProfileField(
            profile_id=profile.profile_id,
            brokerage_id=profile.brokerage_id,
            field=field,
            value=value,
            provenance=PROVENANCE_AI,
            confidence=confidence,
            source_message_id=source_message_id,
        )
        db.add(row)
    profile.updated_at = now
    return row


def confirm_field(
    db: Session,
    *,
    profile: DBBrokerageBuyerProfile,
    field: str,
    value: Any,
    confirmed_by: str,
    now: Optional[datetime] = None,
) -> DBBuyerProfileField:
    """Agent edit/confirm — promotes (or sets) the agent_confirmed row."""
    if field not in QUALIFICATION_FIELDS:
        raise ValueError(f"Unknown qualification field: {field}")
    now = now or datetime.utcnow()
    row = (
        db.query(DBBuyerProfileField)
        .filter(
            DBBuyerProfileField.profile_id == profile.profile_id,
            DBBuyerProfileField.field == field,
            DBBuyerProfileField.provenance == PROVENANCE_CONFIRMED,
        )
        .first()
    )
    if row:
        row.value = value
        row.confirmed_by = confirmed_by
        row.updated_at = now
    else:
        row = DBBuyerProfileField(
            profile_id=profile.profile_id,
            brokerage_id=profile.brokerage_id,
            field=field,
            value=value,
            provenance=PROVENANCE_CONFIRMED,
            confirmed_by=confirmed_by,
        )
        db.add(row)
    profile.updated_at = now
    record_compliance_event(
        db,
        brokerage_id=profile.brokerage_id,
        buyer_phone=profile.buyer_phone,
        actor_user_id=confirmed_by,
        event_type="buyer_profile_field_confirmed",
        direction="system",
        details={"profile_id": profile.profile_id, "field": field},
    )
    safe_commit(db)
    return row


def effective_fields_from_rows(rows) -> dict:
    """Compute the effective qualification snapshot from pre-fetched field rows.

    Pure (no DB access) so callers listing many buyers can batch the
    `DBBuyerProfileField` fetch once and avoid an N+1 per profile.
    """
    by_field: dict[str, dict] = {}
    for row in rows:
        entry = by_field.setdefault(row.field, {})
        entry[row.provenance] = row
    snapshot: dict[str, dict] = {}
    for field, entry in by_field.items():
        confirmed = entry.get(PROVENANCE_CONFIRMED)
        inferred = entry.get(PROVENANCE_AI)
        chosen = confirmed or inferred
        item = {
            "value": chosen.value,
            "provenance": chosen.provenance,
            "confidence": chosen.confidence,
            "source_message_id": chosen.source_message_id,
            "confirmed_by": chosen.confirmed_by,
            "updated_at": chosen.updated_at.isoformat() if chosen.updated_at else None,
            "suggestion": None,
        }
        if confirmed is not None and inferred is not None and inferred.value != confirmed.value:
            item["suggestion"] = {
                "value": inferred.value,
                "confidence": inferred.confidence,
                "source_message_id": inferred.source_message_id,
                "updated_at": inferred.updated_at.isoformat() if inferred.updated_at else None,
            }
        snapshot[field] = item
    return snapshot


def effective_fields(db: Session, profile: DBBrokerageBuyerProfile) -> dict:
    """
    Effective qualification snapshot: confirmed-over-inferred per field, with
    suggestion chips where a differing inference exists alongside a confirmed
    value.
    """
    rows = (
        db.query(DBBuyerProfileField)
        .filter(DBBuyerProfileField.profile_id == profile.profile_id)
        .all()
    )
    return effective_fields_from_rows(rows)


def profile_to_schema(
    db: Session,
    profile: DBBrokerageBuyerProfile,
) -> BuyerProfile:
    """Convert a tenant-scoped buyer profile without reading legacy/global profile state."""
    fields = effective_fields(db, profile)
    budget_field = fields.get("budget_max_aed") or fields.get("budget_min_aed") or {}
    bedroom_field = fields.get("bedrooms") or {}
    area_field = fields.get("target_areas") or {}
    bedroom_value = bedroom_field.get("value")
    area_value = area_field.get("value")
    bedroom_preferences = (
        list(bedroom_value)
        if isinstance(bedroom_value, list)
        else ([int(bedroom_value)] if isinstance(bedroom_value, int) else [])
    )
    area_preferences = (
        list(area_value)
        if isinstance(area_value, list)
        else ([str(area_value)] if area_value else [])
    )
    inquiries = (
        db.query(DBListingInquiry)
        .filter(
            DBListingInquiry.brokerage_id == profile.brokerage_id,
            DBListingInquiry.buyer_phone == profile.buyer_phone,
        )
        .order_by(DBListingInquiry.first_contact.asc())
        .all()
    )
    return BuyerProfile(
        phone=profile.buyer_phone,
        name=profile.name,
        budget_aed=budget_field.get("value"),
        bedroom_preferences=bedroom_preferences,
        area_preferences=area_preferences,
        purpose=None,
        listings_inquired=[
            ListingInquiry(
                listing_id=item.listing_id,
                project=item.project,
                unit_number=item.unit_number,
                price_aed=item.price_aed,
                first_contact=item.first_contact,
            )
            for item in inquiries
        ],
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# ── Rules-layer extraction on the message-processing path ──────────────────────

_FINANCING_CASH = re.compile(r"\b(cash buyers?|paying cash|all cash|cash purchase|no mortgage)\b", re.IGNORECASE)
_FINANCING_PREAPPROVED = re.compile(r"\b(pre[- ]?approv\w*)\b", re.IGNORECASE)
_FINANCING_MORTGAGE = re.compile(r"\b(mortgage|home loan|financing|bank loan)\b", re.IGNORECASE)
_TIMELINE = re.compile(
    r"\b(asap|immediately|this (?:week|month)|next (?:week|month)|within (?:a|\d+) (?:week|month)s?|"
    r"in \d+ (?:week|month)s?|by (?:end of )?(?:q[1-4]|january|february|march|april|may|june|july|"
    r"august|september|october|november|december))\b",
    re.IGNORECASE,
)
_BEDROOMS = re.compile(r"\b(\d+)\s*(?:br|bed(?:room)?s?)\b", re.IGNORECASE)


def extract_qualification_signals(text: str, intent_data: Optional[dict] = None) -> dict:
    """
    Deterministic extraction layered on the Haiku classifier's output (which
    already extracts budget). Returns field → (value, confidence).
    """
    signals: dict[str, tuple[Any, float]] = {}
    intent_data = intent_data or {}
    budget = intent_data.get("extracted_budget")
    if isinstance(budget, (int, float)) and budget > 0:
        signals["budget_max_aed"] = (float(budget), 0.8)
    if _FINANCING_CASH.search(text or ""):
        signals["financing"] = ("cash", 0.85)
    elif _FINANCING_PREAPPROVED.search(text or ""):
        signals["financing"] = ("mortgage_preapproved", 0.85)
    elif _FINANCING_MORTGAGE.search(text or ""):
        signals["financing"] = ("mortgage_unknown", 0.7)
    timeline = _TIMELINE.search(text or "")
    if timeline:
        signals["timeline"] = (timeline.group(1).lower(), 0.7)
    bedrooms = _BEDROOMS.search(text or "")
    if bedrooms:
        signals["bedrooms"] = (int(bedrooms.group(1)), 0.75)
    return signals


def update_profile_from_message(
    db: Session,
    *,
    conversation: DBConversation,
    message_text: str,
    message_id: Optional[int] = None,
    intent_data: Optional[dict] = None,
) -> Optional[DBBrokerageBuyerProfile]:
    """Message-path hook: write ai_inferred rows for any extracted signals."""
    if not conversation.brokerage_id:
        return None
    try:
        profile = get_or_create_profile(
            db,
            brokerage_id=conversation.brokerage_id,
            buyer_phone=conversation.buyer_phone,
            name=conversation.buyer_name,
        )
        signals = extract_qualification_signals(message_text, intent_data)
        for field, (value, confidence) in signals.items():
            record_inferred_field(
                db,
                profile=profile,
                field=field,
                value=value,
                confidence=confidence,
                source_message_id=message_id,
            )
        safe_commit(db)
        return profile
    except Exception:  # pragma: no cover — profiling must never break the pipeline
        logger.warning("Buyer profile update failed", exc_info=True)
        db.rollback()
        return None


def backfill_profiles_from_conversations(db: Session) -> int:
    """Migration-time backfill over existing conversations."""
    created = 0
    conversations = (
        db.query(DBConversation)
        .filter(DBConversation.brokerage_id.isnot(None))
        .all()
    )
    for conversation in conversations:
        profile = get_or_create_profile(
            db,
            brokerage_id=conversation.brokerage_id,
            buyer_phone=conversation.buyer_phone,
            name=conversation.buyer_name,
        )
        if conversation.detected_budget:
            record_inferred_field(
                db,
                profile=profile,
                field="budget_max_aed",
                value=float(conversation.detected_budget),
                confidence=0.7,
            )
        created += 1
    safe_commit(db)
    return created
