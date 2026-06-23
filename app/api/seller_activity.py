from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TypedDict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.seller_conversations import INTENT_LABELS, is_offer_reason, offer_amount
from app.db import crud
from app.models.db_models import DBConversation, DBListing, DBMessage


class ActivityConversation(Protocol):
    conversation_id: str
    listing_id: str
    escalation_triggered: bool
    escalation_reason: str | None
    last_escalated_at: datetime | None
    created_at: datetime | None
    updated_at: datetime


class SellerActivityEvent(TypedDict):
    type: str
    listing_name: str
    listing_id: str
    description: str
    timestamp: str | None


class SellerActivityPayload(TypedDict):
    events: list[SellerActivityEvent]


@dataclass(frozen=True, slots=True)
class ActivityInputs:
    conversations: list[ActivityConversation]
    listing_map: dict[str, str]
    message_counts: dict[str, int]
    first_intents: dict[str, list[str]]


@dataclass(frozen=True, slots=True)
class ActivityConversationContext:
    conversation: ActivityConversation
    listing_name: str
    msg_count: int
    first_intents: list[str]


def build_seller_activity_payload(db: Session, seller_id: str) -> SellerActivityPayload:
    listings = crud.get_listings_for_seller(db, seller_id)
    if not listings:
        return {"events": []}

    listing_map = _listing_names(listings)
    conversations = _seller_activity_conversations(db, list(listing_map.keys()))
    conversation_ids = [conversation.conversation_id for conversation in conversations]
    if not conversation_ids:
        return {"events": []}

    inputs = ActivityInputs(
        conversations=conversations,
        listing_map=listing_map,
        message_counts=_buyer_message_counts(db, conversation_ids),
        first_intents=_first_intents_by_conversation(db, conversation_ids),
    )
    events = _seller_activity_events(inputs)
    events.sort(key=lambda event: event["timestamp"] or "", reverse=True)
    return {"events": events}


def _listing_names(listings: list[DBListing]) -> dict[str, str]:
    listing_map: dict[str, str] = {}
    for listing in listings:
        spa = listing.spa_data or {}
        project = spa.get("project", "Unknown")
        unit = spa.get("unit_number", "")
        listing_map[listing.listing_id] = f"{project} — Unit {unit}" if unit else project
    return listing_map


def _seller_activity_conversations(
    db: Session,
    listing_ids: list[str],
) -> list[ActivityConversation]:
    return (
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


def _buyer_message_counts(db: Session, conversation_ids: list[str]) -> dict[str, int]:
    return dict(
        db.query(DBMessage.conversation_id, func.count(DBMessage.id))
        .filter(DBMessage.conversation_id.in_(conversation_ids), DBMessage.role == "user")
        .group_by(DBMessage.conversation_id)
        .all()
    )


def _first_intents_by_conversation(
    db: Session,
    conversation_ids: list[str],
) -> dict[str, list[str]]:
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
    first_intents: dict[str, list[str]] = {}
    for conversation_id, intent in intent_rows:
        intents = first_intents.setdefault(conversation_id, [])
        if len(intents) < 3:
            intents.append(intent)
    return first_intents


def _seller_activity_events(inputs: ActivityInputs) -> list[SellerActivityEvent]:
    events: list[SellerActivityEvent] = []
    for conversation in inputs.conversations:
        context = ActivityConversationContext(
            conversation=conversation,
            listing_name=inputs.listing_map.get(conversation.listing_id, "Unknown"),
            msg_count=inputs.message_counts.get(conversation.conversation_id, 0),
            first_intents=inputs.first_intents.get(conversation.conversation_id, []),
        )
        _append_status_event(events, context)
        _append_inquiry_event(events, context)
        _append_milestone_event(events, context)
    return events


def _append_status_event(
    events: list[SellerActivityEvent],
    context: ActivityConversationContext,
) -> None:
    is_offer = (
        context.conversation.escalation_triggered
        and is_offer_reason(context.conversation.escalation_reason)
    )
    if is_offer:
        amount = offer_amount(context.conversation.escalation_reason)
        if amount is not None:
            events.append({
                "type": "offer",
                "listing_name": context.listing_name,
                "listing_id": context.conversation.listing_id,
                "description": f"New offer received: AED {amount:,.0f}",
                "timestamp": context.conversation.last_escalated_at.isoformat()
                if context.conversation.last_escalated_at
                else context.conversation.updated_at.isoformat(),
            })
    elif context.conversation.escalation_triggered and context.conversation.escalation_reason:
        events.append({
            "type": "escalation",
            "listing_name": context.listing_name,
            "listing_id": context.conversation.listing_id,
            "description": "Question forwarded to seller for review",
            "timestamp": context.conversation.last_escalated_at.isoformat()
            if context.conversation.last_escalated_at
            else context.conversation.updated_at.isoformat(),
        })


def _append_inquiry_event(
    events: list[SellerActivityEvent],
    context: ActivityConversationContext,
) -> None:
    topics: list[str] = []
    for intent in context.first_intents:
        label = INTENT_LABELS.get(intent)
        if label and label not in topics:
            topics.append(label)
    topic_str = " and ".join(topics[:2]) if topics else "the property"
    events.append({
        "type": "inquiry",
        "listing_name": context.listing_name,
        "listing_id": context.conversation.listing_id,
        "description": f"New inquiry — buyer asked about {topic_str}",
        "timestamp": (
            context.conversation.created_at.isoformat()
            if context.conversation.created_at
            else None
        ),
    })


def _append_milestone_event(
    events: list[SellerActivityEvent],
    context: ActivityConversationContext,
) -> None:
    for threshold in [15, 10, 5]:
        if context.msg_count >= threshold:
            events.append({
                "type": "milestone",
                "listing_name": context.listing_name,
                "listing_id": context.conversation.listing_id,
                "description": f"A buyer reached {threshold} messages — high engagement",
                "timestamp": (
                    context.conversation.updated_at.isoformat()
                    if context.conversation.updated_at
                    else None
                ),
            })
            break
