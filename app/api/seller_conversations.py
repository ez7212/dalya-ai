from __future__ import annotations

from typing import Final, TypedDict

from sqlalchemy.orm import Session

from app.core.seller_summary_privacy import (
    JsonValue,
    SellerSummaryRedactionContext,
    sanitize_seller_ai_summary,
)
from app.models.db_models import DBConversation, DBListing, DBMessage

INTENT_LABELS: Final[dict[str, str | None]] = {
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


class SellerConversation(TypedDict):
    buyer_label: str
    message_count: int
    buyer_messages: int
    summary: JsonValue
    offer_made: bool
    last_active: str | None
    language: str
    started_at: str | None


class ListingConversationsPayload(TypedDict):
    listing_id: str
    conversations: list[SellerConversation]


class SellerOffer(TypedDict):
    buyer_label: str
    amount_aed: float
    vs_asking: str | None
    status: str
    received_at: str | None


class ListingOffersPayload(TypedDict):
    listing_id: str
    asking_price: float | None
    threshold: float | None
    offers: list[SellerOffer]


def build_listing_conversations_payload(
    db: Session,
    listing_id: str,
) -> ListingConversationsPayload:
    conversations = (
        db.query(DBConversation)
        .filter(DBConversation.listing_id == listing_id)
        .order_by(DBConversation.created_at.asc())
        .all()
    )

    results: list[SellerConversation] = []
    for idx, conversation in enumerate(conversations, start=1):
        messages = _conversation_messages(db, conversation.conversation_id)
        buyer_messages = [message for message in messages if message.role == "user"]
        results.append({
            "buyer_label": f"Buyer {idx}",
            "message_count": len(messages),
            "buyer_messages": len(buyer_messages),
            "summary": _seller_summary(conversation, messages),
            "offer_made": bool(
                conversation.escalation_triggered
                and is_offer_reason(conversation.escalation_reason)
            ),
            "last_active": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "language": _detect_language(messages),
            "started_at": conversation.created_at.isoformat() if conversation.created_at else None,
        })

    return {"listing_id": listing_id, "conversations": results}


def build_listing_offers_payload(
    db: Session,
    listing_id: str,
    listing: DBListing,
) -> ListingOffersPayload:
    conversations = (
        db.query(DBConversation)
        .filter(DBConversation.listing_id == listing_id)
        .order_by(DBConversation.created_at.asc())
        .all()
    )

    offers: list[SellerOffer] = []
    asking = listing.seller_asking_price
    for idx, conversation in enumerate(conversations, start=1):
        if not conversation.escalation_triggered:
            continue
        amount = offer_amount(conversation.escalation_reason)
        if amount is None:
            continue
        offers.append({
            "buyer_label": f"Buyer {idx}",
            "amount_aed": amount,
            "vs_asking": _vs_asking(amount, asking),
            "status": "pending",
            "received_at": (
                conversation.last_escalated_at.isoformat()
                if conversation.last_escalated_at
                else None
            ),
        })

    return {
        "listing_id": listing_id,
        "asking_price": asking,
        "threshold": listing.negotiation_threshold_aed,
        "offers": offers,
    }


def _conversation_messages(db: Session, conversation_id: str) -> list[DBMessage]:
    return (
        db.query(DBMessage)
        .filter(DBMessage.conversation_id == conversation_id)
        .order_by(DBMessage.timestamp.asc())
        .all()
    )


def _seller_summary(conversation: DBConversation, messages: list[DBMessage]) -> JsonValue:
    ai_summary = conversation.ai_summary
    if ai_summary and isinstance(ai_summary, dict):
        return sanitize_seller_ai_summary(
            ai_summary,
            SellerSummaryRedactionContext(
                buyer_name=conversation.buyer_name,
                buyer_phone=conversation.buyer_phone,
                conversation_id=conversation.conversation_id,
            ),
        )
    return {
        "topics": [],
        "interest_level": None,
        "sentiment": None,
        "key_question": None,
        "next_step_hint": None,
        "buyer_context": None,
        "_fallback": _summarize_intents(messages, conversation.escalation_triggered),
    }


def _summarize_intents(messages: list[DBMessage], escalation_triggered: bool) -> str:
    seen: list[str] = []
    for message in messages:
        if message.role != "user" or not message.intent:
            continue
        label = INTENT_LABELS.get(message.intent)
        if label and label not in seen:
            seen.append(label)

    if not seen:
        return "General inquiry."

    parts = list(seen)
    summary = (
        "Asked about "
        + ", ".join(parts[:-1])
        + (" and " if len(parts) > 1 else "")
        + parts[-1]
        + "."
    )
    if len(parts) == 1:
        summary = "Asked about " + parts[0] + "."
    if escalation_triggered and "submitted an offer" not in seen:
        summary = summary.rstrip(".") + ". Escalated to seller."
    return summary


def _detect_language(messages: list[DBMessage]) -> str:
    for message in messages:
        if message.role == "user" and message.content:
            arabic_chars = sum(1 for char in message.content if "\u0600" <= char <= "\u06FF")
            if arabic_chars > len(message.content) * 0.3:
                return "Arabic"
    return "English"


def is_offer_reason(escalation_reason: str | None) -> bool:
    return bool(escalation_reason and escalation_reason.startswith("offer:"))


def offer_amount(escalation_reason: str | None) -> float | None:
    if not is_offer_reason(escalation_reason):
        return None
    try:
        return float(escalation_reason.split(":", 1)[1])
    except (ValueError, IndexError):
        return None


def _vs_asking(amount: float, asking: float | None) -> str | None:
    if asking and asking > 0:
        return f"{((amount - asking) / asking) * 100:+.1f}%"
    return None
