"""
Offer log (DAL-165).

Escalation flags offer-related messages; this tracks the offer itself. A
thread is the sequence of offer/counter rows on one conversation+listing:

    DRAFT_PENDING_CONFIRM ─▶ SUBMITTED ─▶ COUNTERED ─▶ (SUBMITTED…)
    SUBMITTED/COUNTERED ─▶ ACCEPTED | REJECTED | WITHDRAWN | EXPIRED

AI proposes, the agent disposes: an AI-detected offer enters
DRAFT_PENDING_CONFIRM and never reaches SUBMITTED without agent confirmation.
The banned-output rule is structural — a draft offer is only created when the
classifier extracted an amount from the buyer's actual message, and the row
anchors that source message; a vague "would they take less?" escalates with
no draft and no hallucinated amount.

Offer history is the audit trail a brokerage owner asks about — and a quiet
seed for the Negotiation Co-Pilot data layer later.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.brokerage_access import record_compliance_event
from app.db.session import safe_commit
from app.models.db_models import (
    DBConversation,
    DBLeadAction,
    DBMessage,
    DBOffer,
)

logger = logging.getLogger(__name__)

OPEN_OFFER_STATUSES = {"submitted", "countered"}
TERMINAL_STATUSES = {"accepted", "rejected", "withdrawn", "expired", "discarded"}

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft_pending_confirm": {"submitted", "discarded"},
    "submitted": {"countered", "accepted", "rejected", "withdrawn", "expired"},
    "countered": {"submitted", "accepted", "rejected", "withdrawn", "expired"},
}

_FINANCING_CONTINGENT = re.compile(r"\b(mortgage|financing|finance approval|bank approval|loan)\b", re.IGNORECASE)
_SUBJECT_TO_VIEWING = re.compile(r"\b(after (?:a |the )?viewing|subject to (?:a )?viewing|once i see|need to see it first)\b", re.IGNORECASE)


def thread_key_for(conversation_id: str, listing_id: str) -> str:
    return f"{conversation_id}:{listing_id}"


def detect_conditions(text: str) -> dict:
    return {
        "financing_contingent": bool(_FINANCING_CONTINGENT.search(text or "")),
        "subject_to_viewing": bool(_SUBJECT_TO_VIEWING.search(text or "")),
    }


def create_draft_offer_from_alert(
    db: Session,
    *,
    brokerage_id: str,
    conversation: DBConversation,
    listing_id: str,
    amount: Optional[float],
    trigger_message: str,
    escalation_thread_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Optional[DBOffer]:
    """
    AI-detected path: called when escalation classification fires offer-related.
    No extracted amount → no draft offer (escalation only) — the amount must
    have a source-message anchor.
    """
    now = now or datetime.utcnow()
    if not amount or amount <= 0:
        return None

    # Anchor: the buyer message that carried the offer.
    source_message = (
        db.query(DBMessage)
        .filter(
            DBMessage.conversation_id == conversation.conversation_id,
            DBMessage.role == "user",
        )
        .order_by(DBMessage.timestamp.desc())
        .first()
    )

    # One open draft per thread — a repeated alert refreshes, not duplicates.
    existing = (
        db.query(DBOffer)
        .filter(
            DBOffer.thread_key == thread_key_for(conversation.conversation_id, listing_id),
            DBOffer.status == "draft_pending_confirm",
        )
        .first()
    )
    conditions = detect_conditions(trigger_message)
    if existing:
        existing.amount = amount
        existing.conditions = trigger_message[:500]
        existing.financing_contingent = conditions["financing_contingent"]
        existing.subject_to_viewing = conditions["subject_to_viewing"]
        existing.source_message_id = source_message.id if source_message else None
        existing.updated_at = now
        safe_commit(db)
        return existing

    from app.core.buyer_profiles import get_or_create_profile

    profile = None
    if conversation.brokerage_id:
        profile = get_or_create_profile(
            db,
            brokerage_id=conversation.brokerage_id,
            buyer_phone=conversation.buyer_phone,
            name=conversation.buyer_name,
        )

    offer = DBOffer(
        brokerage_id=brokerage_id,
        agent_user_id=conversation.assigned_agent_id,
        conversation_id=conversation.conversation_id,
        listing_id=listing_id,
        buyer_profile_id=profile.profile_id if profile else None,
        buyer_phone=conversation.buyer_phone,
        thread_key=thread_key_for(conversation.conversation_id, listing_id),
        amount=amount,
        direction="buyer_offer",
        status="draft_pending_confirm",
        conditions=trigger_message[:500],
        financing_contingent=conditions["financing_contingent"],
        subject_to_viewing=conditions["subject_to_viewing"],
        source="ai_detected",
        source_message_id=source_message.id if source_message else None,
        thread_id=escalation_thread_id,
    )
    db.add(offer)
    _record_offer_event(
        db,
        offer=offer,
        event_type="offer_draft_created",
        actor_user_id=None,
        details={"amount": amount, "source": "ai_detected"},
    )
    safe_commit(db)
    db.refresh(offer)
    return offer


def log_agent_offer(
    db: Session,
    *,
    brokerage_id: str,
    conversation: DBConversation,
    listing_id: str,
    agent_user_id: str,
    amount: float,
    direction: str = "buyer_offer",
    conditions: Optional[str] = None,
    financing_contingent: bool = False,
    subject_to_viewing: bool = False,
    now: Optional[datetime] = None,
) -> DBOffer:
    """Manual "log offer" — agent-logged offers enter SUBMITTED directly."""
    now = now or datetime.utcnow()
    from app.core.buyer_profiles import get_or_create_profile

    profile = None
    if conversation.brokerage_id:
        profile = get_or_create_profile(
            db,
            brokerage_id=conversation.brokerage_id,
            buyer_phone=conversation.buyer_phone,
            name=conversation.buyer_name,
        )
    offer = DBOffer(
        brokerage_id=brokerage_id,
        agent_user_id=agent_user_id,
        conversation_id=conversation.conversation_id,
        listing_id=listing_id,
        buyer_profile_id=profile.profile_id if profile else None,
        buyer_phone=conversation.buyer_phone,
        thread_key=thread_key_for(conversation.conversation_id, listing_id),
        amount=amount,
        direction=direction,
        status="submitted",
        conditions=conditions,
        financing_contingent=financing_contingent,
        subject_to_viewing=subject_to_viewing,
        source="agent_logged",
        confirmed_at=now,
        confirmed_by=agent_user_id,
    )
    db.add(offer)
    _record_offer_event(
        db,
        offer=offer,
        event_type="offer_logged",
        actor_user_id=agent_user_id,
        details={"amount": amount, "direction": direction},
    )
    safe_commit(db)
    db.refresh(offer)
    return offer


def confirm_draft_offer(
    db: Session,
    *,
    offer: DBOffer,
    agent_user_id: str,
    amount: Optional[float] = None,
    now: Optional[datetime] = None,
) -> DBOffer:
    """Agent confirm (optionally editing the amount) → SUBMITTED."""
    now = now or datetime.utcnow()
    if offer.status != "draft_pending_confirm":
        raise ValueError(f"Offer is {offer.status}, not pending confirmation")
    if amount is not None:
        offer.amount = amount
    offer.status = "submitted"
    offer.confirmed_at = now
    offer.confirmed_by = agent_user_id
    offer.updated_at = now
    _record_offer_event(
        db,
        offer=offer,
        event_type="offer_confirmed",
        actor_user_id=agent_user_id,
        details={"amount": offer.amount},
    )
    safe_commit(db)
    return offer


def discard_draft_offer(
    db: Session,
    *,
    offer: DBOffer,
    agent_user_id: str,
    reason: Optional[str] = None,
    now: Optional[datetime] = None,
) -> DBOffer:
    now = now or datetime.utcnow()
    if offer.status != "draft_pending_confirm":
        raise ValueError(f"Offer is {offer.status}, not pending confirmation")
    offer.status = "discarded"
    offer.closed_at = now
    offer.updated_at = now
    _record_offer_event(
        db,
        offer=offer,
        event_type="offer_discarded",
        actor_user_id=agent_user_id,
        details={"reason": reason},
    )
    safe_commit(db)
    return offer


def transition_offer(
    db: Session,
    *,
    offer: DBOffer,
    new_status: str,
    agent_user_id: str,
    counter_amount: Optional[float] = None,
    note: Optional[str] = None,
    now: Optional[datetime] = None,
) -> DBOffer:
    """
    Advance the offer thread. A counter closes the current row as `countered`
    and opens a new SUBMITTED row in the opposite direction — the thread is
    the ordered sequence of rows on the thread_key.
    """
    now = now or datetime.utcnow()
    allowed = _ALLOWED_TRANSITIONS.get(offer.status, set())
    if new_status not in allowed:
        raise ValueError(f"Cannot move offer from {offer.status} to {new_status}")

    offer.status = new_status
    offer.updated_at = now
    if new_status in TERMINAL_STATUSES:
        offer.closed_at = now
    _record_offer_event(
        db,
        offer=offer,
        event_type=f"offer_{new_status}",
        actor_user_id=agent_user_id,
        details={"note": note, "amount": offer.amount},
    )

    counter = None
    if new_status == "countered":
        counter_direction = "seller_counter" if offer.direction == "buyer_offer" else "buyer_offer"
        counter = DBOffer(
            brokerage_id=offer.brokerage_id,
            agent_user_id=agent_user_id,
            conversation_id=offer.conversation_id,
            listing_id=offer.listing_id,
            buyer_profile_id=offer.buyer_profile_id,
            buyer_phone=offer.buyer_phone,
            thread_key=offer.thread_key,
            amount=counter_amount,
            direction=counter_direction,
            status="submitted",
            conditions=note,
            source="agent_logged",
            confirmed_at=now,
            confirmed_by=agent_user_id,
        )
        db.add(counter)
        _record_offer_event(
            db,
            offer=counter,
            event_type="offer_counter_logged",
            actor_user_id=agent_user_id,
            details={"amount": counter_amount, "direction": counter_direction},
        )
    safe_commit(db)
    if counter is not None:
        db.refresh(counter)
        return counter
    return offer


def open_offer_for_conversation(db: Session, conversation_id: str) -> Optional[DBOffer]:
    """Structured open offer (SUBMITTED/COUNTERED), preferred over message signals."""
    return (
        db.query(DBOffer)
        .filter(
            DBOffer.conversation_id == conversation_id,
            DBOffer.status.in_(OPEN_OFFER_STATUSES),
        )
        .order_by(DBOffer.updated_at.desc())
        .first()
    )


def offers_for_thread(db: Session, thread_key: str) -> list[DBOffer]:
    return (
        db.query(DBOffer)
        .filter(DBOffer.thread_key == thread_key)
        .order_by(DBOffer.created_at.asc())
        .all()
    )


def serialize_offer(offer: DBOffer) -> dict:
    return {
        "offer_id": offer.offer_id,
        "conversation_id": offer.conversation_id,
        "listing_id": offer.listing_id,
        "buyer_profile_id": offer.buyer_profile_id,
        "buyer_phone": offer.buyer_phone,
        "thread_key": offer.thread_key,
        "amount": offer.amount,
        "direction": offer.direction,
        "status": offer.status,
        "conditions": offer.conditions,
        "financing_contingent": offer.financing_contingent,
        "subject_to_viewing": offer.subject_to_viewing,
        "source": offer.source,
        "source_message_id": offer.source_message_id,
        "confirmed_at": offer.confirmed_at.isoformat() if offer.confirmed_at else None,
        "confirmed_by": offer.confirmed_by,
        "closed_at": offer.closed_at.isoformat() if offer.closed_at else None,
        "created_at": offer.created_at.isoformat() if offer.created_at else None,
        "updated_at": offer.updated_at.isoformat() if offer.updated_at else None,
    }


def _record_offer_event(
    db: Session,
    *,
    offer: DBOffer,
    event_type: str,
    actor_user_id: Optional[str],
    details: dict,
) -> None:
    db.add(DBLeadAction(
        brokerage_id=offer.brokerage_id,
        conversation_id=offer.conversation_id,
        listing_id=offer.listing_id,
        buyer_phone=offer.buyer_phone,
        agent_user_id=actor_user_id or offer.agent_user_id,
        action_type=event_type,
        outcome=offer.status,
        note=(details.get("note") or "")[:500] or None,
        payload={"offer_id": offer.offer_id, **{k: v for k, v in details.items() if v is not None}},
    ))
    record_compliance_event(
        db,
        brokerage_id=offer.brokerage_id,
        conversation_id=offer.conversation_id,
        listing_id=offer.listing_id,
        buyer_phone=offer.buyer_phone,
        actor_user_id=actor_user_id,
        event_type=event_type,
        direction="system",
        details={"offer_id": offer.offer_id, "status": offer.status, **details},
    )
