"""
Seller API Router — authenticated endpoints for listing owners.

All endpoints require a valid Supabase JWT. Sellers can only access
their own listings (verified via listing.seller_id == user.id).

CRITICAL: Never expose buyer phone numbers, names, or PII in any response.
Use anonymized labels like "Buyer 1", "Buyer 2" ordered by first contact.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.chatbot_engine import engine
from app.db import crud
from app.db.session import get_db, safe_commit
from app.models.db_models import DBConversation, DBMessage, DBListing

router = APIRouter()


# ── Intent-to-readable mapping for conversation summaries ─────────────────────

_INTENT_LABELS = {
    "general_enquiry": "general questions",
    "price_negotiation": "price negotiation",
    "viewing_request": "viewing",
    "payment_plan_query": "payment schedule",
    "offer_submission": "submitted an offer",
    "contact_sharing": "shared contact details",
    "comparison_shopping": "comparison shopping",
    "speak_to_human": "requested to speak with someone",
    "empty_message": None,
    "not_interested": "expressed disinterest",
    "unknown": None,
}


def _summarize_intents(messages: list[DBMessage], escalation_triggered: bool) -> str:
    """Build a readable summary from stored message intents. No Claude call."""
    seen = []
    for msg in messages:
        if msg.role != "user" or not msg.intent:
            continue
        label = _INTENT_LABELS.get(msg.intent)
        if label and label not in seen:
            seen.append(label)

    if not seen:
        return "General inquiry."

    # Capitalise first topic, join rest
    parts = list(seen)
    summary = "Asked about " + ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1] + "."
    if len(parts) == 1:
        summary = "Asked about " + parts[0] + "."

    if escalation_triggered:
        # Check if offer was already mentioned
        if "submitted an offer" not in seen:
            summary = summary.rstrip(".") + ". Escalated to seller."
    return summary


def _detect_language(messages: list[DBMessage]) -> str:
    """Simple language detection from buyer messages — checks for Arabic script."""
    for msg in messages:
        if msg.role == "user" and msg.content:
            # Check for Arabic Unicode range
            arabic_chars = sum(1 for c in msg.content if "\u0600" <= c <= "\u06FF")
            if arabic_chars > len(msg.content) * 0.3:
                return "Arabic"
    return "English"


class ListingUpdate(BaseModel):
    seller_asking_price: Optional[float] = None
    negotiation_threshold_aed: Optional[float] = None
    seller_notes: Optional[str] = None


@router.get("/seller/listings")
async def get_my_listings(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all listings owned by the authenticated seller."""
    from app.core.listing_stages import STAGE_ORDER

    listings = crud.get_listings_for_seller(db, user.id)
    results = []
    total_conversations = 0
    total_escalated = 0
    for listing in listings:
        spa = listing.spa_data or {}
        stats = crud.get_listing_stats_fast(db, listing.listing_id)
        convs = stats.get("total_conversations", 0)
        esc = stats.get("escalated_leads", 0)
        total_conversations += convs
        total_escalated += esc

        # Compute derived status from processing stages
        stages = listing.processing_stages or {}
        ai_live_status = (stages.get("ai_advisor_live") or {}).get("status", "pending")
        if ai_live_status == "complete":
            derived_status = "active"
        else:
            # Find first stage that's in_progress or blocked
            derived_status = "pending_review"
            for stage_key in STAGE_ORDER:
                stage = stages.get(stage_key) or {}
                if stage.get("status") == "blocked":
                    derived_status = "blocked"
                    break

        results.append({
            "id": listing.listing_id,
            "property_name": spa.get("project", "Unknown"),
            "unit_number": spa.get("unit_number", "—"),
            "asking_price": listing.seller_asking_price,
            "status": derived_status,
            "lead_count": convs,
            "escalated_count": esc,
            "last_activity": None,
        })
    return {
        "listings": results,
        "total_conversations": total_conversations,
        "total_escalated": total_escalated,
    }


@router.patch("/seller/listings/{listing_id}")
async def update_my_listing(
    listing_id: str,
    body: ListingUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update seller-configurable fields on a listing the user owns."""
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    if body.seller_asking_price is not None:
        listing.seller_asking_price = body.seller_asking_price
    if body.negotiation_threshold_aed is not None:
        listing.negotiation_threshold_aed = body.negotiation_threshold_aed
    if body.seller_notes is not None:
        listing.seller_notes = body.seller_notes
    safe_commit(db)

    return {"success": True, "listing_id": listing_id}


@router.get("/seller/listings/{listing_id}/leads")
async def get_my_listing_leads(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return full listing details + conversation stats for a listing the user owns."""
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    spa = listing.spa_data or {}
    stats = crud.get_listing_stats_fast(db, listing_id)

    from app.core.listing_stages import serialize_stages

    return {
        "id": listing.listing_id,
        "property_name": spa.get("project", "Unknown"),
        "developer": spa.get("developer", "Unknown"),
        "unit_number": spa.get("unit_number", "—"),
        "sub_community": spa.get("sub_community"),
        "property_type": spa.get("property_type"),
        "property_status": spa.get("property_status"),
        "bedrooms": spa.get("bedrooms"),
        "bathrooms": spa.get("bathrooms"),
        "bua_sqft": spa.get("bua_sqft"),
        "plot_sqft": spa.get("plot_sqft"),
        "total_price": spa.get("purchase_price_aed"),
        "asking_price": listing.seller_asking_price,
        "negotiation_threshold": listing.negotiation_threshold_aed,
        "seller_notes": listing.seller_notes,
        "unit_profile": listing.unit_profile or {},
        "unit_profile_history": listing.unit_profile_history or [],
        "noc_eligible": spa.get("noc_eligible"),
        "total_paid_percent": spa.get("total_paid_percent"),
        "handover_date": spa.get("estimated_completion_date"),
        "payment_schedule": spa.get("payment_schedule", []),
        "status": "active",
        "lead_count": stats.get("total_conversations", 0),
        "escalated_count": stats.get("escalated_leads", 0),
        "leads": stats.get("active_buyers", []),
        "processing_stages": serialize_stages(listing.processing_stages),
    }


# ── Conversation summaries (anonymized) ──────────────────────────────────────

@router.get("/seller/listings/{listing_id}/conversations")
async def get_listing_conversations(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return anonymized conversation summaries for a listing. No buyer PII."""
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    # Load conversations ordered by creation date for stable buyer numbering
    conversations = (
        db.query(DBConversation)
        .filter(DBConversation.listing_id == listing_id)
        .order_by(DBConversation.created_at.asc())
        .all()
    )

    results = []
    for idx, conv in enumerate(conversations, start=1):
        messages = (
            db.query(DBMessage)
            .filter(DBMessage.conversation_id == conv.conversation_id)
            .order_by(DBMessage.timestamp.asc())
            .all()
        )
        buyer_msgs = [m for m in messages if m.role == "user"]

        # Prefer AI-generated structured summary if available
        ai_summary = conv.ai_summary
        if ai_summary and isinstance(ai_summary, dict):
            summary_text = ai_summary
        else:
            summary_text = {
                "topics": [],
                "interest_level": None,
                "sentiment": None,
                "key_question": None,
                "next_step_hint": None,
                "buyer_context": None,
                "_fallback": _summarize_intents(messages, conv.escalation_triggered),
            }

        results.append({
            "buyer_label": f"Buyer {idx}",
            "message_count": len(messages),
            "buyer_messages": len(buyer_msgs),
            "summary": summary_text,
            "offer_made": bool(
                conv.escalation_triggered
                and conv.escalation_reason
                and conv.escalation_reason.startswith("offer:")
            ),
            "last_active": conv.updated_at.isoformat() if conv.updated_at else None,
            "language": _detect_language(messages),
            "started_at": conv.created_at.isoformat() if conv.created_at else None,
        })

    return {
        "listing_id": listing_id,
        "conversations": results,
    }


# ── Offers endpoint (anonymized) ─────────────────────────────────────────────

@router.get("/seller/listings/{listing_id}/offers")
async def get_listing_offers(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all offers received on a listing. No buyer PII."""
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    # All conversations ordered by creation for stable buyer numbering
    all_convs = (
        db.query(DBConversation)
        .filter(DBConversation.listing_id == listing_id)
        .order_by(DBConversation.created_at.asc())
        .all()
    )

    # Build buyer label map and extract offers
    offers = []
    asking = listing.seller_asking_price
    for idx, conv in enumerate(all_convs, start=1):
        if not (conv.escalation_triggered and conv.escalation_reason
                and conv.escalation_reason.startswith("offer:")):
            continue
        try:
            amount = float(conv.escalation_reason.split(":", 1)[1])
        except (ValueError, IndexError):
            continue

        vs_asking = None
        if asking and asking > 0:
            pct = ((amount - asking) / asking) * 100
            vs_asking = f"{pct:+.1f}%"

        offers.append({
            "buyer_label": f"Buyer {idx}",
            "amount_aed": amount,
            "vs_asking": vs_asking,
            "status": "pending",
            "received_at": conv.last_escalated_at.isoformat() if conv.last_escalated_at else None,
        })

    return {
        "listing_id": listing_id,
        "asking_price": asking,
        "threshold": listing.negotiation_threshold_aed,
        "offers": offers,
    }


# ── Activity feed (anonymized, cross-listing) ────────────────────────────────

@router.get("/seller/activity")
async def get_seller_activity(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reverse-chronological activity feed across all seller listings. No buyer PII."""
    listings = crud.get_listings_for_seller(db, user.id)
    if not listings:
        return {"events": []}

    listing_map = {}
    for lst in listings:
        spa = lst.spa_data or {}
        project = spa.get("project", "Unknown")
        unit = spa.get("unit_number", "")
        name = f"{project} — Unit {unit}" if unit else project
        listing_map[lst.listing_id] = name

    listing_ids = list(listing_map.keys())

    # Load all conversations for this seller's listings, most recent first
    conversations = (
        db.query(
            DBConversation.conversation_id,
            DBConversation.listing_id,
            DBConversation.escalation_triggered,
            DBConversation.escalation_reason,
            DBConversation.last_escalated_at,
            DBConversation.created_at,
            DBConversation.updated_at,
        )
        .filter(DBConversation.listing_id.in_(listing_ids))
        .order_by(DBConversation.updated_at.desc())
        .all()
    )
    conversation_ids = [conv.conversation_id for conv in conversations]
    if not conversation_ids:
        return {"events": []}

    message_counts = dict(
        db.query(DBMessage.conversation_id, func.count(DBMessage.id))
        .filter(
            DBMessage.conversation_id.in_(conversation_ids),
            DBMessage.role == "user",
        )
        .group_by(DBMessage.conversation_id)
        .all()
    )

    intent_rows = (
        db.query(DBMessage.conversation_id, DBMessage.intent)
        .filter(
            DBMessage.conversation_id.in_(conversation_ids),
            DBMessage.role == "user",
            DBMessage.intent.isnot(None),
        )
        .order_by(DBMessage.conversation_id.asc(), DBMessage.timestamp.asc())
        .all()
    )
    first_intents_by_conversation: dict[str, list[str]] = {}
    for conversation_id, intent_val in intent_rows:
        intents = first_intents_by_conversation.setdefault(conversation_id, [])
        if len(intents) < 3:
            intents.append(intent_val)

    events = []
    for conv in conversations:
        listing_name = listing_map.get(conv.listing_id, "Unknown")

        # Count messages for milestone detection
        msg_count = message_counts.get(conv.conversation_id, 0)

        # Event: offer received
        if (conv.escalation_triggered and conv.escalation_reason
                and conv.escalation_reason.startswith("offer:")):
            try:
                amount = float(conv.escalation_reason.split(":", 1)[1])
                events.append({
                    "type": "offer",
                    "listing_name": listing_name,
                    "listing_id": conv.listing_id,
                    "description": f"New offer received: AED {amount:,.0f}",
                    "timestamp": conv.last_escalated_at.isoformat() if conv.last_escalated_at else conv.updated_at.isoformat(),
                })
            except (ValueError, IndexError):
                pass

        # Event: escalation (non-offer — forwarded question)
        elif conv.escalation_triggered and conv.escalation_reason:
            events.append({
                "type": "escalation",
                "listing_name": listing_name,
                "listing_id": conv.listing_id,
                "description": "Question forwarded to seller for review",
                "timestamp": conv.last_escalated_at.isoformat() if conv.last_escalated_at else conv.updated_at.isoformat(),
            })

        # Event: new inquiry (first message)
        # Build a description from the first few intents
        topics = []
        for intent_val in first_intents_by_conversation.get(conv.conversation_id, []):
            label = _INTENT_LABELS.get(intent_val)
            if label and label not in topics:
                topics.append(label)
        topic_str = " and ".join(topics[:2]) if topics else "the property"

        events.append({
            "type": "inquiry",
            "listing_name": listing_name,
            "listing_id": conv.listing_id,
            "description": f"New inquiry — buyer asked about {topic_str}",
            "timestamp": conv.created_at.isoformat() if conv.created_at else None,
        })

        # Event: milestones (5, 10, 15 messages) — emit only the highest reached
        for threshold in [15, 10, 5]:
            if msg_count >= threshold:
                events.append({
                    "type": "milestone",
                    "listing_name": listing_name,
                    "listing_id": conv.listing_id,
                    "description": f"A buyer reached {threshold} messages — high engagement",
                    "timestamp": conv.updated_at.isoformat() if conv.updated_at else None,
                })
                break

    # Sort all events reverse-chronologically
    events.sort(key=lambda e: e["timestamp"] or "", reverse=True)

    return {"events": events}
