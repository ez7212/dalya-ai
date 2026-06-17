"""
Live conversation takeover (DAL-158).

The escalation model covers "AI knows it should hand off". Takeover covers
"AI doesn't know it's wrong": a per-conversation kill switch that pauses the
concierge entirely.

    AI_ACTIVE  ──(takeover)──▶  AGENT_CONTROLLED
    AI_ACTIVE  ◀──(resume)───  AGENT_CONTROLLED

While AGENT_CONTROLLED:
  - Inbound buyer messages are never answered by the concierge. They are
    forwarded raw to the agent via Agents AI (with [Ref: TOKEN]) and appear in
    the dashboard inbox as unanswered.
  - Intent classification still runs (rules layer, for analytics/compliance
    tagging) but produces no buyer-facing output.
  - Draft generation is suppressed: hot-list refresh skips draft creation and
    pending drafts are auto-snoozed with reason "takeover".
  - Agent replies (dashboard or WhatsApp relay) flow exactly as today.

Triggers: a dashboard toggle, or the agent quote-replying any [Ref: TOKEN]
message on Agents AI with the single keyword TAKEOVER / RESUME. Keywords are
consumed as commands and never forwarded to the buyer.

Tenant confirmation conversations are exempt — those replies are intercepted
before the buyer pipeline and never reach this module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.agent_relay import strip_envelope_token
from app.core.brokerage_access import record_compliance_event
from app.core.messaging import get_transport
from app.core.messaging.types import OutboundAgentMessage
from app.db.session import safe_commit
from app.models.db_models import (
    DBAgentMessageRoute,
    DBAgentProfile,
    DBBrokerage,
    DBConversation,
    DBDraftReply,
    DBLeadAction,
    DBListing,
    DBMessage,
)

logger = logging.getLogger(__name__)

AI_MODE_ACTIVE = "active"
AI_MODE_AGENT_CONTROLLED = "agent_controlled"
AI_MODES = {AI_MODE_ACTIVE, AI_MODE_AGENT_CONTROLLED}

# Quote-reply keywords on Agents AI. Case-insensitive, trimmed, single word.
MODE_KEYWORDS = {
    "takeover": AI_MODE_AGENT_CONTROLLED,
    "resume": AI_MODE_ACTIVE,
}

TAKEOVER_FORWARD_ROUTE_TYPE = "takeover_forward"
TAKEOVER_DRAFT_SNOOZE_DAYS = 7


@dataclass
class ModeKeywordResult:
    """Outcome of an Agents AI mode-keyword command (TAKEOVER / RESUME)."""

    status: str  # mode_set | mode_unchanged | missing_ref | unknown_ref | wrong_agent
    keyword: str
    mode: Optional[str] = None
    conversation_id: Optional[str] = None
    details: dict = field(default_factory=dict)


def conversation_ai_mode(conversation: Optional[DBConversation]) -> str:
    """ai_mode with a safe default for rows created before the migration."""
    mode = getattr(conversation, "ai_mode", None) if conversation else None
    return mode if mode in AI_MODES else AI_MODE_ACTIVE


def is_agent_controlled(conversation: Optional[DBConversation]) -> bool:
    return conversation_ai_mode(conversation) == AI_MODE_AGENT_CONTROLLED


def parse_mode_keyword(body: str, token: Optional[str] = None) -> Optional[str]:
    """
    Return "takeover" / "resume" when the body is exactly that keyword
    (case-insensitive, trimmed, envelope token stripped), else None.
    """
    text = strip_envelope_token(body or "", token).strip().strip(".!").lower()
    return text if text in MODE_KEYWORDS else None


def set_ai_mode(
    db: Session,
    conversation: DBConversation,
    *,
    mode: str,
    actor_user_id: Optional[str],
    source: str,
    now: Optional[datetime] = None,
) -> dict:
    """
    Transition a conversation's AI mode. Writes a timeline event (lead action)
    and a compliance event for every transition. On takeover, auto-snoozes
    pending drafts with reason "takeover".
    """
    if mode not in AI_MODES:
        raise ValueError(f"Invalid ai_mode: {mode!r}")
    now = now or datetime.utcnow()
    previous = conversation_ai_mode(conversation)
    if previous == mode:
        return {
            "changed": False,
            "ai_mode": previous,
            "snoozed_draft_ids": [],
        }

    conversation.ai_mode = mode
    conversation.ai_mode_changed_at = now
    conversation.ai_mode_changed_by = actor_user_id
    conversation.ai_mode_change_source = source
    conversation.updated_at = now

    snoozed_draft_ids: list[str] = []
    if mode == AI_MODE_AGENT_CONTROLLED:
        snoozed_draft_ids = _snooze_pending_drafts(
            db,
            conversation=conversation,
            actor_user_id=actor_user_id,
            now=now,
        )

    action_type = (
        "conversation_takeover_started"
        if mode == AI_MODE_AGENT_CONTROLLED
        else "conversation_takeover_resumed"
    )
    db.add(DBLeadAction(
        brokerage_id=conversation.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=conversation.listing_id,
        buyer_phone=conversation.buyer_phone,
        agent_user_id=actor_user_id,
        action_type=action_type,
        outcome=mode,
        note=f"AI mode {previous} → {mode} via {source}",
        payload={
            "previous_mode": previous,
            "mode": mode,
            "source": source,
            "snoozed_draft_ids": snoozed_draft_ids,
        },
    ))
    record_compliance_event(
        db,
        brokerage_id=conversation.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=conversation.listing_id,
        buyer_phone=conversation.buyer_phone,
        actor_user_id=actor_user_id,
        event_type="conversation_ai_mode_changed",
        direction="system",
        details={
            "previous_mode": previous,
            "mode": mode,
            "source": source,
            "snoozed_draft_count": len(snoozed_draft_ids),
            "snoozed_draft_ids": snoozed_draft_ids,
        },
    )
    safe_commit(db)
    return {
        "changed": True,
        "ai_mode": mode,
        "snoozed_draft_ids": snoozed_draft_ids,
    }


def _snooze_pending_drafts(
    db: Session,
    *,
    conversation: DBConversation,
    actor_user_id: Optional[str],
    now: datetime,
) -> list[str]:
    drafts = (
        db.query(DBDraftReply)
        .filter(
            DBDraftReply.brokerage_id == conversation.brokerage_id,
            DBDraftReply.conversation_id == conversation.conversation_id,
            DBDraftReply.status.in_(["draft", "edited"]),
        )
        .all()
    )
    snoozed_until = now + timedelta(days=TAKEOVER_DRAFT_SNOOZE_DAYS)
    snoozed_ids = []
    for draft in drafts:
        metadata = dict(draft.metadata_json or {})
        metadata["snoozed_until"] = snoozed_until.isoformat()
        metadata["snoozed_by"] = actor_user_id
        metadata["snooze_reason"] = "takeover"
        draft.metadata_json = metadata
        draft.status = "snoozed"
        draft.updated_at = now
        snoozed_ids.append(draft.draft_id)
    return snoozed_ids


# ── Agents AI keyword commands (TAKEOVER / RESUME) ─────────────────────────────


def handle_agents_ai_mode_keyword(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound,
    now: Optional[datetime] = None,
) -> Optional[ModeKeywordResult]:
    """
    If the inbound Agents AI message is a mode keyword, consume it as a command:
    toggle the conversation's AI mode and confirm to the agent. Returns None
    when the message is not a keyword (caller proceeds with the normal relay).
    Keyword messages are never forwarded to the buyer.
    """
    now = now or datetime.utcnow()
    keyword = parse_mode_keyword(inbound.body, inbound.envelope_token)
    if not keyword:
        return None

    target_mode = MODE_KEYWORDS[keyword]
    token = inbound.envelope_token

    def _prompt_agent(text: str) -> None:
        if not brokerage.agents_ai_number:
            return
        get_transport().send_to_agents_ai(
            OutboundAgentMessage(
                brokerage_id=brokerage.brokerage_id,
                agents_ai_number=brokerage.agents_ai_number,
                agent_phone=_normalize(inbound.from_number),
                body=text,
                conversation_id="",
                listing_id="",
                buyer_phone="",
                escalation_type="mode_keyword_prompt",
                envelope_token=token,
            )
        )

    if not token:
        # Never guess the conversation.
        _prompt_agent(
            f"To use {keyword.upper()}, quote-reply the [Ref: …] message for the "
            "conversation you mean — I never guess which buyer you're referring to."
        )
        record_compliance_event(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="conversation_ai_mode_keyword_missing_ref",
            direction="inbound",
            details={"keyword": keyword, "from_number": _normalize(inbound.from_number)},
        )
        safe_commit(db)
        return ModeKeywordResult(status="missing_ref", keyword=keyword)

    route = (
        db.query(DBAgentMessageRoute)
        .filter(
            DBAgentMessageRoute.brokerage_id == brokerage.brokerage_id,
            DBAgentMessageRoute.agents_ai_envelope_token == token,
        )
        .first()
    )
    if not route:
        _prompt_agent(
            f"I couldn't match that ref to a conversation. Quote-reply a "
            f"[Ref: …] message and send {keyword.upper()} again."
        )
        record_compliance_event(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="conversation_ai_mode_keyword_unknown_ref",
            direction="inbound",
            details={
                "keyword": keyword,
                "envelope_token": token,
                "from_number": _normalize(inbound.from_number),
            },
        )
        safe_commit(db)
        return ModeKeywordResult(status="unknown_ref", keyword=keyword)

    route_agent_phone = _normalize(route.agent_phone)
    if route_agent_phone and _normalize(inbound.from_number) != route_agent_phone:
        record_compliance_event(
            db,
            brokerage_id=brokerage.brokerage_id,
            conversation_id=route.conversation_id,
            listing_id=route.listing_id,
            buyer_phone=route.buyer_phone,
            event_type="conversation_ai_mode_keyword_wrong_agent",
            direction="inbound",
            details={
                "keyword": keyword,
                "envelope_token": token,
                "from_number": _normalize(inbound.from_number),
                "expected_agent_phone": route_agent_phone,
            },
        )
        safe_commit(db)
        return ModeKeywordResult(status="wrong_agent", keyword=keyword)

    conversation = db.get(DBConversation, route.conversation_id)
    if not conversation:
        return ModeKeywordResult(status="unknown_ref", keyword=keyword)

    result = set_ai_mode(
        db,
        conversation,
        mode=target_mode,
        actor_user_id=route.agent_user_id,
        source="whatsapp",
        now=now,
    )

    buyer_label = conversation.buyer_name or conversation.buyer_phone
    listing_label = _listing_label(db, conversation.listing_id)
    if target_mode == AI_MODE_AGENT_CONTROLLED:
        confirmation = (
            f"AI paused for {buyer_label} ({listing_label}). All messages will be "
            "forwarded to you. Reply RESUME to this thread to re-enable."
        )
    else:
        confirmation = (
            f"AI resumed for {buyer_label} ({listing_label}). Dalya will answer "
            "their next message as normal."
        )
    if brokerage.agents_ai_number and route.agent_phone:
        get_transport().send_to_agents_ai(
            OutboundAgentMessage(
                brokerage_id=brokerage.brokerage_id,
                agents_ai_number=brokerage.agents_ai_number,
                agent_phone=route.agent_phone,
                body=confirmation,
                conversation_id=conversation.conversation_id,
                listing_id=conversation.listing_id,
                buyer_phone=conversation.buyer_phone,
                escalation_type="mode_keyword_confirmation",
                envelope_token=token,
                agent_user_id=route.agent_user_id,
            )
        )

    return ModeKeywordResult(
        status="mode_set" if result["changed"] else "mode_unchanged",
        keyword=keyword,
        mode=target_mode,
        conversation_id=conversation.conversation_id,
        details={"snoozed_draft_ids": result["snoozed_draft_ids"]},
    )


# ── Raw forwards while agent-controlled ────────────────────────────────────────


def find_agent_controlled_conversation(
    db: Session,
    *,
    brokerage_id: str,
    buyer_phone: str,
    listing_id: Optional[str] = None,
) -> Optional[DBConversation]:
    """
    Resolve the conversation an inbound buyer message would land on and return
    it only when it is agent-controlled. Mirrors the engine's routing key:
    listing when known, else the buyer's most recent conversation in scope.
    """
    query = db.query(DBConversation).filter(
        DBConversation.brokerage_id == brokerage_id,
        DBConversation.buyer_phone == buyer_phone,
    )
    if listing_id:
        query = query.filter(DBConversation.listing_id == listing_id)
    conversation = query.order_by(DBConversation.updated_at.desc()).first()
    if conversation and is_agent_controlled(conversation):
        return conversation
    return None


def forward_buyer_message_during_takeover(
    db: Session,
    *,
    brokerage: DBBrokerage,
    conversation: DBConversation,
    body: str,
    message_sid: Optional[str] = None,
    now: Optional[datetime] = None,
) -> bool:
    """
    Persist the inbound buyer message (so the inbox shows it unanswered) and
    forward it raw to the agent via Agents AI with a fresh [Ref: TOKEN] route.
    Runs the rules intent classifier for analytics tagging only — there is no
    buyer-facing output on this path. Returns True when the forward was sent.
    """
    now = now or datetime.utcnow()

    # Analytics/compliance tagging only — deterministic rules layer, no model call.
    intent_tag = None
    try:
        from app.core.intent_rules import detect_intent_rules
        intent_tag = (detect_intent_rules(body) or {}).get("intent")
    except Exception:  # pragma: no cover — tagging must never block the forward
        logger.warning("Takeover intent tagging failed", exc_info=True)

    db.add(DBMessage(
        conversation_id=conversation.conversation_id,
        role="user",
        content=body,
        intent=intent_tag,
        metadata_json={
            "source": "takeover_raw_forward",
            "ai_mode": AI_MODE_AGENT_CONTROLLED,
            "message_sid": message_sid,
        },
    ))
    conversation.updated_at = now

    agent_profile = _agent_profile_for_conversation(db, conversation)
    forwarded = False
    if brokerage.agents_ai_number and agent_profile and agent_profile.whatsapp_phone:
        buyer_label = conversation.buyer_name or conversation.buyer_phone
        listing_label = _listing_label(db, conversation.listing_id)
        envelope_body = (
            f"[AI PAUSED] {buyer_label} ({conversation.buyer_phone}) — {listing_label}\n\n"
            f"\"{body}\"\n\n"
            "Quote-reply this message to answer. Reply RESUME to re-enable Dalya."
        )
        send_result = get_transport().send_to_agents_ai(
            OutboundAgentMessage(
                brokerage_id=brokerage.brokerage_id,
                agents_ai_number=brokerage.agents_ai_number,
                agent_phone=agent_profile.whatsapp_phone,
                body=envelope_body,
                conversation_id=conversation.conversation_id,
                listing_id=conversation.listing_id,
                buyer_phone=conversation.buyer_phone,
                escalation_type=TAKEOVER_FORWARD_ROUTE_TYPE,
                tags=[TAKEOVER_FORWARD_ROUTE_TYPE],
                agent_user_id=agent_profile.user_id,
            )
        )
        if send_result.ok and send_result.envelope_token:
            db.add(DBAgentMessageRoute(
                brokerage_id=brokerage.brokerage_id,
                conversation_id=conversation.conversation_id,
                listing_id=conversation.listing_id,
                buyer_phone=conversation.buyer_phone,
                agent_user_id=agent_profile.user_id,
                agent_phone=agent_profile.whatsapp_phone,
                agents_ai_envelope_token=send_result.envelope_token,
                escalation_type=TAKEOVER_FORWARD_ROUTE_TYPE,
                tags=[TAKEOVER_FORWARD_ROUTE_TYPE],
                expires_at=now + timedelta(days=7),
            ))
            forwarded = True

    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=conversation.listing_id,
        buyer_phone=conversation.buyer_phone,
        actor_user_id=agent_profile.user_id if agent_profile else None,
        event_type="takeover_buyer_message_forwarded",
        direction="inbound",
        details={
            "forwarded": forwarded,
            "intent_tag": intent_tag,
            "message_preview": (body or "")[:200],
            "agent_phone": agent_profile.whatsapp_phone if agent_profile else None,
        },
    )
    if not forwarded:
        # Never silent: the message is persisted as unanswered in the inbox and
        # the gap is recorded on the compliance trail.
        logger.warning(
            "Takeover forward not delivered for conversation %s (agents_ai_number=%s, agent=%s)",
            conversation.conversation_id,
            brokerage.agents_ai_number,
            agent_profile.user_id if agent_profile else None,
        )
    safe_commit(db)
    return forwarded


def _agent_profile_for_conversation(
    db: Session,
    conversation: DBConversation,
) -> Optional[DBAgentProfile]:
    agent_user_id = conversation.assigned_agent_id
    if not agent_user_id:
        listing = db.get(DBListing, conversation.listing_id)
        agent_user_id = listing.assigned_agent_id if listing else None
    if not agent_user_id:
        return None
    return (
        db.query(DBAgentProfile)
        .filter(
            DBAgentProfile.brokerage_id == conversation.brokerage_id,
            DBAgentProfile.user_id == agent_user_id,
        )
        .first()
    )


def _listing_label(db: Session, listing_id: Optional[str]) -> str:
    if not listing_id:
        return "Unknown listing"
    listing = db.get(DBListing, listing_id)
    spa = (listing.spa_data or {}) if listing else {}
    project = spa.get("project") or "Unknown listing"
    unit = spa.get("unit_number")
    return f"{project} {unit}".strip() if unit else project


def _normalize(number: Optional[str]) -> str:
    if not number:
        return ""
    cleaned = number.strip()
    if cleaned.lower().startswith("whatsapp:"):
        cleaned = cleaned[len("whatsapp:"):]
    return cleaned
