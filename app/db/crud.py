"""
CRUD operations — all database reads and writes go through here.
Replaces the in-memory dicts from the original chatbot_engine.py.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import func, select, Integer, cast
from sqlalchemy.orm import Session

from app.db.session import safe_commit
from app.models.db_models import (
    DBListing,
    DBConversation,
    DBMessage,
    DBBuyerProfile,
    DBListingInquiry,
    DBOfferRecord,
    DBLeadAssignment,
    DBSuspiciousActivity,
)
from app.core.brokerage_access import get_or_create_lead_assignment
from app.schemas.conversation import (
    ConversationState,
    ConversationMessage,
    MessageRole,
    BuyerIntent,
    BuyerProfile,
    ListingInquiry,
)
from app.schemas.spa import SPAParseResult


# ── Listings ───────────────────────────────────────────────────────────────────

def save_listing(
    db: Session,
    listing_id: str,
    spa: SPAParseResult,
    community_data: Optional[dict] = None,
    seller_asking_price: Optional[float] = None,
    seller_notes: Optional[str] = None,
    negotiation_threshold_aed: Optional[float] = None,
    commission_rate: float = 0.0015,
    property_type: Optional[str] = None,
) -> DBListing:
    resolved_property_type = property_type
    if not resolved_property_type:
        status = (spa.property_status or "").strip().lower()
        resolved_property_type = "ready" if status in {"ready", "completed", "complete", "handed over"} else "off_plan"

    existing = db.get(DBListing, listing_id)
    if existing:
        existing.spa_data = spa.model_dump()
        existing.community_data = community_data
        existing.seller_asking_price = seller_asking_price
        existing.seller_notes = seller_notes
        existing.negotiation_threshold_aed = negotiation_threshold_aed
        if existing.commission_rate is None:
            existing.commission_rate = commission_rate
        if not existing.property_type:
            existing.property_type = resolved_property_type
        safe_commit(db)
        return existing

    listing = DBListing(
        listing_id=listing_id,
        spa_data=spa.model_dump(),
        community_data=community_data,
        seller_asking_price=seller_asking_price,
        seller_notes=seller_notes,
        negotiation_threshold_aed=negotiation_threshold_aed,
        commission_rate=commission_rate,
        property_type=resolved_property_type,
        additional_fees=[],
        seller_qa=[],
        media_urls=[],
        unit_profile={},
        unit_profile_history=[],
        processing_stages={},
        reference_documents=[],
    )
    db.add(listing)
    safe_commit(db)
    db.refresh(listing)
    return listing


def get_listing(db: Session, listing_id: str) -> Optional[DBListing]:
    return db.get(DBListing, listing_id)


def get_listings_for_seller(db: Session, seller_id: str) -> list[DBListing]:
    return db.query(DBListing).filter(DBListing.seller_id == seller_id).all()


def _infer_location_descriptor(spa: dict) -> str:
    """Infer a human-readable location descriptor from SPA project/community fields."""
    proj = (spa.get("project") or "").lower()
    if "oasis" in proj or "ostra" in proj:
        return "The Oasis, Dubailand"
    if "seahaven" in proj:
        return "Dubai Harbour"
    return spa.get("sub_community") or ""


def _infer_listing_tags(spa: dict, community_data) -> list:
    """Infer semantic tags from SPA fields for fuzzy portfolio matching."""
    tags = []
    proj = (spa.get("project") or "").lower()
    dev = (spa.get("developer") or "").lower()
    ptype = (spa.get("property_type") or "").lower()
    if "emaar" in dev:
        tags.append("emaar")
    if "sobha" in dev:
        tags.append("sobha")
    if "villa" in ptype:
        tags.append("villa")
    if "apartment" in ptype:
        tags.append("apartment")
    if "townhouse" in ptype:
        tags.append("townhouse")
    if "palace" in proj:
        tags += ["palace branded", "branded", "luxury"]
    if "ostra" in proj:
        tags += ["the oasis", "dubailand", "off-plan", "5-bedroom"]
    if "seahaven" in proj:
        tags += ["dubai harbour", "marina-adjacent", "waterfront", "off-plan"]
    bedrooms = spa.get("bedrooms")
    if bedrooms:
        tags.append(f"{bedrooms}-bedroom")
    return tags


def get_all_listings_brief(db: Session, brokerage_id: Optional[str] = None) -> list[dict]:
    """
    Return rich attribute dicts for active listings — used by no-listing fallback.
    Includes location_descriptor and semantic tags for portfolio matching.
    """
    query = db.query(DBListing)
    if brokerage_id:
        query = query.filter(DBListing.brokerage_id == brokerage_id)
    rows = query.all()
    result = []
    for row in rows:
        spa = row.spa_data or {}
        price = row.seller_asking_price or spa.get("purchase_price_aed")
        if not price:
            continue
        result.append({
            "listing_id": row.listing_id,
            "project": spa.get("project") or "",
            "sub_community": spa.get("sub_community") or "",
            "developer": spa.get("developer") or "",
            "property_type": spa.get("property_type") or "",
            "bedrooms": spa.get("bedrooms"),
            "asking_price_aed": price,
            # Keep legacy key so existing listing_lines loop in engine still works
            "asking_price": price,
            "unit_number": spa.get("unit_number") or "",
            "location_descriptor": _infer_location_descriptor(spa),
            "tags": _infer_listing_tags(spa, row.community_data),
        })
    return result


def get_listing_stats_fast(db: Session, listing_id: str) -> dict:
    """
    Aggregate stats in a single SQL round-trip. Avoids loading conversations
    or messages into Python. Only used by the seller dashboard/listing endpoints.
    """
    # Single query: conversation summary with per-conversation message counts,
    # ordered by most recent, limited to 20 for the active_buyers list.
    rows = db.execute(
        select(
            DBConversation.conversation_id,
            DBConversation.buyer_phone,
            DBConversation.buyer_name,
            DBConversation.escalation_triggered,
            DBConversation.updated_at,
            func.count(DBMessage.id).label("msg_count"),
        )
        .outerjoin(DBMessage, DBMessage.conversation_id == DBConversation.conversation_id)
        .where(DBConversation.listing_id == listing_id)
        .group_by(
            DBConversation.conversation_id,
            DBConversation.buyer_phone,
            DBConversation.buyer_name,
            DBConversation.escalation_triggered,
            DBConversation.updated_at,
        )
        .order_by(DBConversation.updated_at.desc())
    ).all()

    total_conversations = len(rows)
    escalated = sum(1 for r in rows if r.escalation_triggered)
    total_messages = sum(r.msg_count for r in rows)

    active_buyers = [
        {
            "phone": r.buyer_phone,
            "name": r.buyer_name,
            "messages": r.msg_count,
            "escalated": r.escalation_triggered,
            "last_active": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows[:20]
    ]

    return {
        "listing_id": listing_id,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "escalated_leads": escalated,
        "active_buyers": active_buyers,
    }


def get_spa(db: Session, listing_id: str) -> Optional[SPAParseResult]:
    row = db.get(DBListing, listing_id)
    if not row:
        return None
    return SPAParseResult.model_validate(row.spa_data)


# ── Conversations ──────────────────────────────────────────────────────────────

def get_or_create_conversation(
    db: Session,
    buyer_phone: str,
    listing_id: str,
) -> DBConversation:
    """
    One conversation per buyer per listing.
    Keyed by phone + listing_id combination.
    """
    existing = (
        db.query(DBConversation)
        .filter_by(buyer_phone=buyer_phone, listing_id=listing_id)
        .first()
    )
    if existing:
        listing = db.get(DBListing, listing_id)
        if listing:
            changed = False
            if listing.brokerage_id and existing.brokerage_id != listing.brokerage_id:
                existing.brokerage_id = listing.brokerage_id
                changed = True
            if listing.assigned_agent_id and existing.assigned_agent_id != listing.assigned_agent_id:
                existing.assigned_agent_id = listing.assigned_agent_id
                changed = True
            if changed:
                existing.updated_at = datetime.utcnow()
                safe_commit(db)
                db.refresh(existing)
            get_or_create_lead_assignment(db, existing)
        return existing

    import uuid
    listing = db.get(DBListing, listing_id)
    conv = DBConversation(
        conversation_id=str(uuid.uuid4()),
        listing_id=listing_id,
        buyer_phone=buyer_phone,
        brokerage_id=listing.brokerage_id if listing and listing.brokerage_id else None,
        assigned_agent_id=listing.assigned_agent_id if listing and listing.assigned_agent_id else None,
    )
    db.add(conv)
    safe_commit(db)
    db.refresh(conv)
    get_or_create_lead_assignment(db, conv)
    return conv


def add_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    intent: Optional[str] = None,
    metadata_json: Optional[dict] = None,
    dedupe_window_seconds: Optional[int] = 120,
) -> DBMessage:
    if dedupe_window_seconds and content:
        cutoff = datetime.utcnow() - timedelta(seconds=dedupe_window_seconds)
        existing = (
            db.query(DBMessage)
            .filter(
                DBMessage.conversation_id == conversation_id,
                DBMessage.role == role,
                DBMessage.content == content,
                DBMessage.intent == intent,
                DBMessage.timestamp >= cutoff,
            )
            .order_by(DBMessage.timestamp.desc())
            .first()
        )
        if existing:
            return existing

    msg = DBMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        intent=intent,
        metadata_json=metadata_json or {},
    )
    # Mirror voice-note transcription fields onto the message record (DAL-159).
    voice_note = (metadata_json or {}).get("voice_note") or {}
    if voice_note:
        msg.transcription_text = voice_note.get("transcription_text") or voice_note.get("corrected_transcript")
        msg.transcription_language = voice_note.get("transcription_language")
        confidence = voice_note.get("transcription_confidence")
        msg.transcription_confidence = float(confidence) if isinstance(confidence, (int, float)) else None
        msg.transcription_provider = voice_note.get("transcription_provider") or voice_note.get("provider")
    db.add(msg)
    safe_commit(db)
    db.refresh(msg)
    return msg


def update_conversation(
    db: Session,
    conv: DBConversation,
    buyer_name: Optional[str] = None,
    detected_budget: Optional[float] = None,
    escalation_triggered: Optional[bool] = None,
    escalation_reason: Optional[str] = None,
    last_escalated_at: Optional[datetime] = None,
    assigned_agent_id: Optional[str] = None,
) -> DBConversation:
    if buyer_name is not None:
        conv.buyer_name = buyer_name
    if detected_budget is not None:
        conv.detected_budget = detected_budget
    if escalation_triggered is not None:
        conv.escalation_triggered = escalation_triggered
    if escalation_reason is not None:
        conv.escalation_reason = escalation_reason
    if last_escalated_at is not None:
        conv.last_escalated_at = last_escalated_at
    if assigned_agent_id is not None:
        conv.assigned_agent_id = assigned_agent_id
    conv.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(conv)
    if assigned_agent_id is not None:
        get_or_create_lead_assignment(db, conv)
    return conv


def get_conversation(db: Session, conversation_id: str) -> Optional[DBConversation]:
    return db.get(DBConversation, conversation_id)


def get_conversations_for_listing(
    db: Session, listing_id: str
) -> list[DBConversation]:
    return (
        db.query(DBConversation)
        .filter_by(listing_id=listing_id)
        .order_by(DBConversation.updated_at.desc())
        .all()
    )


def db_conv_to_state(conv: DBConversation) -> ConversationState:
    """Convert a DBConversation (with messages loaded) to ConversationState."""
    messages = [
        ConversationMessage(
            role=MessageRole(msg.role),
            content=msg.content,
            timestamp=msg.timestamp,
            intent=BuyerIntent(msg.intent) if msg.intent else None,
            metadata=msg.metadata_json or {},
        )
        for msg in conv.messages
    ]
    return ConversationState(
        conversation_id=conv.conversation_id,
        listing_id=conv.listing_id,
        buyer_phone=conv.buyer_phone,
        buyer_name=conv.buyer_name,
        detected_budget=conv.detected_budget,
        escalation_triggered=conv.escalation_triggered,
        escalation_reason=conv.escalation_reason,
        messages=messages,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def get_last_message_role(db: Session, conversation_id: str) -> Optional[str]:
    """Return the role of the most recent message in a conversation, or None."""
    last = (
        db.query(DBMessage.role)
        .filter_by(conversation_id=conversation_id)
        .order_by(DBMessage.timestamp.desc())
        .first()
    )
    return last.role if last else None


def has_consecutive_assistant_tail(db: Session, conversation_id: str) -> bool:
    """True if the last two messages are both from 'assistant' (no user reply between)."""
    last_two = (
        db.query(DBMessage.role)
        .filter_by(conversation_id=conversation_id)
        .order_by(DBMessage.timestamp.desc())
        .limit(2)
        .all()
    )
    return len(last_two) == 2 and all(r.role == "assistant" for r in last_two)


# ── Buyer profiles ─────────────────────────────────────────────────────────────

def get_or_create_buyer_profile(db: Session, phone: str) -> DBBuyerProfile:
    profile = db.get(DBBuyerProfile, phone)
    if not profile:
        profile = DBBuyerProfile(
            phone=phone,
            bedroom_preferences=[],
            area_preferences=[],
        )
        db.add(profile)
        safe_commit(db)
        db.refresh(profile)
    return profile


def update_buyer_profile(
    db: Session,
    profile: DBBuyerProfile,
    name: Optional[str] = None,
    budget_aed: Optional[float] = None,
    bedroom: Optional[int] = None,
    area: Optional[str] = None,
    purpose: Optional[str] = None,
) -> DBBuyerProfile:
    if name and not profile.name:
        profile.name = name
    if budget_aed and not profile.budget_aed:
        profile.budget_aed = budget_aed
    if bedroom and bedroom not in (profile.bedroom_preferences or []):
        profile.bedroom_preferences = list(profile.bedroom_preferences or []) + [bedroom]
    if area and area not in (profile.area_preferences or []):
        profile.area_preferences = list(profile.area_preferences or []) + [area]
    if purpose and not profile.purpose:
        profile.purpose = purpose
    profile.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(profile)
    return profile


def add_listing_inquiry(
    db: Session,
    buyer_phone: str,
    listing_id: str,
    project: str,
    unit_number: str,
    price_aed: float,
) -> None:
    """Add a listing to a buyer's inquiry history if not already there."""
    existing = (
        db.query(DBListingInquiry)
        .filter_by(buyer_phone=buyer_phone, listing_id=listing_id)
        .first()
    )
    if not existing:
        inquiry = DBListingInquiry(
            buyer_phone=buyer_phone,
            listing_id=listing_id,
            project=project,
            unit_number=unit_number,
            price_aed=price_aed,
        )
        db.add(inquiry)
        safe_commit(db)


def db_profile_to_schema(profile: DBBuyerProfile) -> BuyerProfile:
    """Convert DBBuyerProfile to Pydantic BuyerProfile schema."""
    inquiries = [
        ListingInquiry(
            listing_id=i.listing_id,
            project=i.project,
            unit_number=i.unit_number,
            price_aed=i.price_aed,
            first_contact=i.first_contact,
        )
        for i in (profile.inquiries or [])
    ]
    return BuyerProfile(
        phone=profile.phone,
        name=profile.name,
        budget_aed=profile.budget_aed,
        bedroom_preferences=profile.bedroom_preferences or [],
        area_preferences=profile.area_preferences or [],
        purpose=profile.purpose,
        listings_inquired=inquiries,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# ── Offer records ──────────────────────────────────────────────────────────────

def get_active_offer(
    db: Session,
    buyer_phone: str,
    listing_id: str,
) -> Optional[DBOfferRecord]:
    """
    Return the most recent non-superseded offer from this buyer on this listing.
    An offer is "active" when superseded_by is NULL.
    """
    return (
        db.query(DBOfferRecord)
        .filter(
            DBOfferRecord.buyer_phone == buyer_phone,
            DBOfferRecord.listing_id == listing_id,
            DBOfferRecord.superseded_by.is_(None),
        )
        .order_by(DBOfferRecord.created_at.desc())
        .first()
    )


def create_offer_record(
    db: Session,
    listing_id: str,
    conversation_id: str,
    buyer_phone: str,
    offer_amount_aed: float,
    asking_price_aed: float,
    above_threshold: bool,
    escalated: bool,
    escalation_reason: Optional[str] = None,
    threshold_aed: Optional[float] = None,
    buyer_name: Optional[str] = None,
    raw_message: Optional[str] = None,
    language_detected: Optional[str] = None,
    turn_number: Optional[int] = None,
) -> DBOfferRecord:
    """
    Insert a new OfferRecord. Does NOT mark any prior offer as superseded —
    callers must do that separately after receiving the new offer_id.
    """
    gap_pct = (
        (asking_price_aed - offer_amount_aed) / asking_price_aed * 100.0
        if asking_price_aed
        else 0.0
    )
    record = DBOfferRecord(
        offer_id=str(uuid.uuid4()),
        listing_id=listing_id,
        conversation_id=conversation_id,
        buyer_phone=buyer_phone,
        buyer_name=buyer_name,
        offer_amount_aed=offer_amount_aed,
        asking_price_aed=asking_price_aed,
        gap_pct=gap_pct,
        above_threshold=above_threshold,
        threshold_aed=threshold_aed,
        escalated=escalated,
        escalation_reason=escalation_reason,
        raw_message=raw_message,
        language_detected=language_detected,
        turn_number=turn_number,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    safe_commit(db)
    db.refresh(record)
    return record


def supersede_offer(
    db: Session,
    old_offer_id: str,
    new_offer_id: str,
) -> None:
    """Mark an existing offer as superseded by a newer one."""
    old = db.get(DBOfferRecord, old_offer_id)
    if old:
        old.superseded_by = new_offer_id
        safe_commit(db)


def get_recent_offers_in_chain(
    db: Session, buyer_phone: str, listing_id: str, hours: int = 24,
) -> list["DBOfferRecord"]:
    """All offers from this buyer on this listing in the last N hours, oldest first."""
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    return (
        db.query(DBOfferRecord)
        .filter(
            DBOfferRecord.buyer_phone == buyer_phone,
            DBOfferRecord.listing_id == listing_id,
            DBOfferRecord.created_at >= cutoff,
        )
        .order_by(DBOfferRecord.created_at.asc())
        .all()
    )


def get_all_offers_for_buyer_listing(
    db: Session, buyer_phone: str, listing_id: str,
) -> list["DBOfferRecord"]:
    """
    Phase 9.10: All offers from this buyer on this listing, oldest first,
    with NO time window. Used to surface a returning buyer's prior offer
    history when they re-engage outside the 24h chain window.
    """
    return (
        db.query(DBOfferRecord)
        .filter(
            DBOfferRecord.buyer_phone == buyer_phone,
            DBOfferRecord.listing_id == listing_id,
        )
        .order_by(DBOfferRecord.created_at.asc())
        .all()
    )


def find_offer_by_buyer_name(
    db: Session,
    listing_id: str,
    buyer_name: str,
    fuzzy_threshold: int = 80,
) -> Optional["DBOfferRecord"]:
    """
    Search active OfferRecords on a listing by buyer name. Fuzzy-matches with
    rapidfuzz at given threshold (0-100). Returns best match or None.

    Used to verify lawyer claims like "I represent the buyer Sara who
    submitted an offer."
    """
    from rapidfuzz import fuzz
    candidates = (
        db.query(DBOfferRecord)
        .filter(
            DBOfferRecord.listing_id == listing_id,
            DBOfferRecord.superseded_by.is_(None),
        )
        .all()
    )
    if not candidates:
        return None
    if not buyer_name:
        return None

    best = None
    best_score = 0
    for offer in candidates:
        if not offer.buyer_name:
            continue
        score = fuzz.WRatio(buyer_name.lower(), offer.buyer_name.lower())
        if score > best_score and score >= fuzzy_threshold:
            best_score = score
            best = offer
    return best


def create_suspicious_activity(
    db: Session,
    listing_id: str,
    conversation_id: str,
    buyer_phone: str,
    category: str,
    trigger_message: str,
    bot_response: str | None = None,
    buyer_name: str | None = None,
) -> "DBSuspiciousActivity":
    activity = DBSuspiciousActivity(
        listing_id=listing_id,
        conversation_id=conversation_id,
        buyer_phone=buyer_phone,
        buyer_name=buyer_name,
        category=category,
        trigger_message=trigger_message[:500] if trigger_message else "",
        bot_response=bot_response[:1000] if bot_response else None,
    )
    db.add(activity)
    safe_commit(db)
    db.refresh(activity)
    return activity
