from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.brokerage_access import record_compliance_event
from app.core.messaging import get_transport
from app.core.messaging.types import OutboundAgentMessage
from app.db.session import safe_commit
from app.models.db_models import (
    DBAgentMessageRoute,
    DBBrokerage,
    DBConversation,
    DBEscalationThread,
    DBEscalationThreadQuestion,
)
from app.schemas.conversation import EscalationAlert


OPEN_THREAD_STATES = {"debouncing", "open", "updated"}
THREAD_WINDOW = timedelta(hours=24)
INITIAL_DEBOUNCE_SECONDS = 90
UPDATE_DEBOUNCE_SECONDS = 30
MAX_DEBOUNCE_SECONDS = 300
QUESTION_DISPLAY_CAP = 10
BYPASS_ESCALATION_TYPES = {
    "offer",
    "regulatory_request",
    "legitimate_conveyancing",
    # AI failure events are never debounced — silent failures forbidden (DAL-159).
    "media_unprocessable",
}
BYPASS_CATEGORIES = {"offer", "legal_general"}


def _keyword_category(text: str) -> Optional[str]:
    question = (text or "").lower()
    if "legal" in question or "lawyer" in question or "conveyanc" in question:
        return "legal_general"
    if re.search(r"\b(service charge|service charges|maintenance charge|maintenance charges|maintenance fee|maintenance fees|fee|fees|commission|dld|transfer)\b", question):
        return "fees_and_charges"
    if re.search(r"\b(payment plan|instalment|installment|post[- ]handover|remaining balance|remaining payment)\b", question):
        return "payment_plan"
    if re.search(r"\b(noc|title deed|title|ejari|spa|soa|form a|trakheesi|brn|document|documents)\b", question):
        return "regulatory_documents"
    if re.search(r"\b(rental yield|gross yield|net yield|roi|rental income|capital appreciation|capital growth|price growth|resale premium|market data|comparables|comps|recent sale|recent transaction)\b", question):
        return "market_analysis"
    if re.search(r"\b(tenant|tenanted|lease|vacant|evict|eviction|rent|rented)\b", question):
        return "tenancy_status"
    if re.search(r"\b(mortgage|finance|financing|ltv|bank|pre[- ]approval|loan)\b", question):
        return "financing"
    if re.search(r"\b(handover|completion|complete|snag|defect|defects liability)\b", question):
        return "developer_handover"
    if re.search(r"\b(school|metro|community|retail|mall|drive|airport|marina|downtown)\b", question):
        return "community_amenities"
    if re.search(r"\b(gym|pool|security|amenit|parking pass|concierge|lobby)\b", question):
        return "building_amenities"
    if re.search(r"\b(parking|storage|view|layout|sqft|bua|plot|bed|bath|window|ac|balcony|maid|floor level|orientation)\b", question):
        return "physical_property"
    return None


@dataclass
class ThreadedEscalationResult:
    action: str  # debounced | initial_sent | update_debounced | update_sent | skipped | timed_out | opt_out_closed
    thread: Optional[DBEscalationThread] = None
    route: Optional[DBAgentMessageRoute] = None
    token: Optional[str] = None


def escalation_category(alert: EscalationAlert) -> str:
    etype = str(alert.escalation_type or "")
    subtype = str(alert.escalation_subtype or "")
    topic = str((alert.payload or {}).get("topic") or "")

    if etype == "offer":
        return "offer"
    if etype in {"viewing_schedule", "viewing_request"}:
        return "viewing_logistics"
    if etype in {"regulatory_request", "brn_request", "legitimate_conveyancing"}:
        return "regulatory_documents"
    if etype == "seller_action":
        return "seller_action"
    if etype == "media_unprocessable":
        return "media_unprocessable"

    if etype in {"info_gap", "unanswerable_question"}:
        topic_category = _keyword_category(" ".join([topic, subtype]))
        if topic_category:
            return topic_category

    question = " ".join([
        str(alert.trigger_message or ""),
        str((alert.payload or {}).get("question") or ""),
        str((alert.payload or {}).get("question_digest") or ""),
        topic,
        subtype,
    ]).lower()
    keyword_category = _keyword_category(question)
    if keyword_category:
        return keyword_category
    if etype == "materials_request":
        return "regulatory_documents"
    if etype in {"info_gap", "unanswerable_question"}:
        return "physical_property"
    return "other"


def escalation_bypasses_debounce(alert: EscalationAlert, category: Optional[str] = None) -> bool:
    category = category or escalation_category(alert)
    return str(alert.escalation_type) in BYPASS_ESCALATION_TYPES or category in BYPASS_CATEGORIES


# DAL-161: keyword+intent rubric for buyer messages requesting media artifacts.
# The media_requested flag is set HERE at classification time and stored on the
# thread — relay routing reads state, it never re-interprets content.
_MEDIA_REQUEST_PATTERN = re.compile(
    r"\b(brochure|floor ?plans?|photos?|pictures?|pics|images?|videos?|video tour|"
    r"payment plan (pdf|document)|location pin|share (the )?location|"
    r"send (me )?(the )?(file|document|pdf|plan|map))\b",
    re.IGNORECASE,
)


def is_media_request(text: str) -> bool:
    return bool(_MEDIA_REQUEST_PATTERN.search(text or ""))


def alert_requests_media(alert: EscalationAlert) -> bool:
    if str(alert.escalation_type) == "materials_request":
        return True
    return any(is_media_request(question) for question in alert_questions(alert))


def mark_thread_media_requested(thread: DBEscalationThread, *, now: Optional[datetime] = None) -> None:
    metadata = dict(thread.metadata_json or {})
    metadata["media_requested"] = True
    metadata["media_requested_at"] = (now or datetime.utcnow()).isoformat()
    thread.metadata_json = metadata


def thread_media_requested(thread: DBEscalationThread) -> bool:
    return bool((thread.metadata_json or {}).get("media_requested"))


def alert_questions(alert: EscalationAlert) -> list[str]:
    text = (alert.trigger_message or "").strip()
    if not text:
        return ["Buyer requested agent follow-up."]

    numbered = []
    for line in text.splitlines():
        match = re.match(r"^\s*\d+\.\s+(.+?)\s*$", line)
        if match:
            numbered.append(match.group(1).strip())
    if numbered:
        return numbered

    parts = [part.strip(" \n\t;") for part in text.split("\n") if part.strip()]
    return parts or [text]


def find_open_thread(
    db: Session,
    *,
    brokerage_id: str,
    buyer_phone: str,
    listing_id: str,
    category: str,
    now: Optional[datetime] = None,
) -> Optional[DBEscalationThread]:
    now = now or datetime.utcnow()
    if category == "offer":
        return None
    cutoff = now - THREAD_WINDOW
    return (
        db.query(DBEscalationThread)
        .filter(
            DBEscalationThread.brokerage_id == brokerage_id,
            DBEscalationThread.buyer_phone == buyer_phone,
            DBEscalationThread.listing_id == listing_id,
            DBEscalationThread.category == category,
            DBEscalationThread.state.in_(OPEN_THREAD_STATES),
            DBEscalationThread.last_buyer_message_at >= cutoff,
        )
        .order_by(DBEscalationThread.updated_at.desc())
        .first()
    )


def has_open_thread_for_alert(db: Session, conv, alert: EscalationAlert) -> bool:
    if not db or not conv or not alert or not alert.buyer_phone or not alert.listing_id:
        return False
    brokerage_id = getattr(conv, "brokerage_id", None)
    if not brokerage_id:
        return False
    return find_open_thread(
        db,
        brokerage_id=brokerage_id,
        buyer_phone=alert.buyer_phone,
        listing_id=alert.listing_id,
        category=escalation_category(alert),
    ) is not None


def create_thread(
    db: Session,
    *,
    brokerage: DBBrokerage,
    alert: EscalationAlert,
    agent_user_id: Optional[str],
    agent_phone: Optional[str],
    category: str,
    state: str = "debouncing",
    metadata_json: Optional[dict] = None,
    now: Optional[datetime] = None,
) -> DBEscalationThread:
    now = now or datetime.utcnow()
    initial_debounce_until = now + timedelta(seconds=INITIAL_DEBOUNCE_SECONDS)
    max_debounce_until = now + timedelta(seconds=MAX_DEBOUNCE_SECONDS)
    thread = DBEscalationThread(
        brokerage_id=brokerage.brokerage_id,
        conversation_id=alert.conversation_id,
        listing_id=alert.listing_id,
        buyer_phone=alert.buyer_phone,
        agent_user_id=agent_user_id,
        agent_phone=agent_phone,
        category=category,
        state=state,
        escalation_type=str(alert.escalation_type),
        escalation_subtype=alert.escalation_subtype,
        opened_at=now,
        alerted_at=now if state in {"open", "updated"} else None,
        last_buyer_message_at=now,
        debounce_until=None if state in {"open", "updated"} else initial_debounce_until,
        max_debounce_until=max_debounce_until,
        metadata_json=metadata_json or {"source": "agents_ai_escalation"},
        updated_at=now,
    )
    db.add(thread)
    db.flush()
    for question in alert_questions(alert):
        append_question(
            db,
            thread=thread,
            question_text=question,
            category=category,
            escalation_subtype=alert.escalation_subtype,
            now=now,
        )
    thread.state = state
    return thread


def _mark_pending_questions_alerted(db: Session, *, thread: DBEscalationThread) -> None:
    if str(thread.escalation_type) not in {"unanswerable_question", "info_gap"}:
        return
    if not thread.conversation_id:
        return
    conv = db.get(DBConversation, thread.conversation_id)
    if not conv:
        return
    pending = list(conv.pending_forwarded_questions or [])
    if not pending:
        return
    alerted = list(conv.alerted_questions or [])
    for question in pending:
        if question not in alerted:
            alerted.append(question)
    conv.alerted_questions = alerted
    conv.pending_forwarded_questions = []


def _append_alert_to_existing_thread(
    db: Session,
    *,
    brokerage: DBBrokerage,
    existing: DBEscalationThread,
    alert: EscalationAlert,
    category: str,
    bypass: bool,
    now: datetime,
) -> ThreadedEscalationResult:
    new_questions = []
    for question in alert_questions(alert):
        appended = append_question(
            db,
            thread=existing,
            question_text=question,
            category=category,
            escalation_subtype=alert.escalation_subtype,
            record_event=True,
            now=now,
        )
        if appended and appended.added_at == now:
            new_questions.append(question)

    if not new_questions:
        safe_commit(db)
        return ThreadedEscalationResult(action="skipped", thread=existing, token=existing.envelope_token)

    metadata = dict(existing.metadata_json or {})
    metadata["pending_update_question"] = new_questions[-1]
    existing.metadata_json = metadata
    if existing.envelope_token:
        existing.state = "updated"
        existing.debounce_until = now if bypass else now + timedelta(seconds=UPDATE_DEBOUNCE_SECONDS)
        existing.updated_at = now
        if bypass:
            result = _send_update_for_thread(db, brokerage=brokerage, thread=existing, now=now)
            safe_commit(db)
            return result
        safe_commit(db)
        return ThreadedEscalationResult(action="update_debounced", thread=existing, token=existing.envelope_token)

    existing.debounce_until = min(
        now + timedelta(seconds=INITIAL_DEBOUNCE_SECONDS),
        existing.max_debounce_until or now + timedelta(seconds=MAX_DEBOUNCE_SECONDS),
    )
    existing.updated_at = now
    safe_commit(db)
    return ThreadedEscalationResult(action="debounced", thread=existing, token=existing.envelope_token)


def append_question(
    db: Session,
    *,
    thread: DBEscalationThread,
    question_text: str,
    category: str,
    escalation_subtype: Optional[str],
    brokerage_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    listing_id: Optional[str] = None,
    buyer_phone: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    record_event: bool = False,
    now: Optional[datetime] = None,
) -> Optional[DBEscalationThreadQuestion]:
    now = now or datetime.utcnow()
    normalized = question_text.strip()
    if not normalized:
        return None
    existing = (
        db.query(DBEscalationThreadQuestion)
        .filter(
            DBEscalationThreadQuestion.thread_id == thread.thread_id,
            DBEscalationThreadQuestion.question_text == normalized,
        )
        .first()
    )
    if existing:
        return existing

    sort_order = int(thread.question_count or 0) + 1
    question = DBEscalationThreadQuestion(
        thread_id=thread.thread_id,
        question_text=normalized,
        category=category,
        escalation_subtype=escalation_subtype,
        sort_order=sort_order,
        added_at=now,
    )
    db.add(question)
    thread.question_count = sort_order
    thread.last_buyer_message_at = now
    thread.updated_at = now
    if thread.state == "open":
        thread.state = "updated"
    if record_event:
        record_compliance_event(
            db,
            brokerage_id=brokerage_id or thread.brokerage_id,
            conversation_id=conversation_id or thread.conversation_id,
            listing_id=listing_id or thread.listing_id,
            buyer_phone=buyer_phone or thread.buyer_phone,
            actor_user_id=actor_user_id or thread.agent_user_id,
            event_type="escalation_thread_question_appended",
            direction="inbound",
            details={
                "thread_id": thread.thread_id,
                "category": category,
                "sort_order": sort_order,
                "question_count": thread.question_count,
            },
        )
    return question


def _relative_age(added_at: datetime, now: datetime) -> str:
    seconds = max(0, int((now - added_at).total_seconds()))
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    return f"{hours}h ago"


def format_update_message(
    db: Session,
    *,
    thread: DBEscalationThread,
    token: str,
    new_question: str,
    now: Optional[datetime] = None,
    cap: int = QUESTION_DISPLAY_CAP,
) -> str:
    now = now or datetime.utcnow()
    db.flush()
    questions = (
        db.query(DBEscalationThreadQuestion)
        .filter(DBEscalationThreadQuestion.thread_id == thread.thread_id)
        .order_by(DBEscalationThreadQuestion.sort_order.asc())
        .all()
    )
    visible = questions[:cap]
    lines = [
        f"[Update on Ref: {token}]",
        "",
        "Buyer also asked:",
        f"\"{new_question.strip()}\"",
        "",
        "Open questions on this escalation:",
    ]
    for question in visible:
        label = "original" if question.sort_order == 1 else "added"
        lines.append(
            f"{question.sort_order}. {question.question_text} "
            f"({label}, {_relative_age(question.added_at, now)})"
        )
    remaining = len(questions) - len(visible)
    if remaining > 0:
        lines.append(f"...and {remaining} more - see dashboard.")
    return "\n".join(lines)


def _format_initial_envelope(db: Session, *, thread: DBEscalationThread, envelope_body: str) -> str:
    db.flush()
    questions = (
        db.query(DBEscalationThreadQuestion)
        .filter(DBEscalationThreadQuestion.thread_id == thread.thread_id)
        .order_by(DBEscalationThreadQuestion.sort_order.asc())
        .all()
    )
    if len(questions) <= 1:
        return envelope_body
    lines = ["", "Open questions on this escalation:"]
    for question in questions[:QUESTION_DISPLAY_CAP]:
        lines.append(f"{question.sort_order}. {question.question_text}")
    remaining = len(questions) - QUESTION_DISPLAY_CAP
    if remaining > 0:
        lines.append(f"...and {remaining} more - see dashboard.")
    return f"{envelope_body.rstrip()}\n" + "\n".join(lines)


def _thread_metadata(
    *,
    envelope_body: str,
    tags: list[str],
    expires_at: datetime,
    requested_action: Optional[str] = None,
) -> dict:
    return {
        "source": "agents_ai_escalation",
        "envelope_body": envelope_body,
        "tags": list(tags),
        "expires_at": expires_at.isoformat(),
        "requested_action": requested_action,
    }


def _parse_expires_at(value: Optional[str], now: datetime) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return now + timedelta(days=7)


def _latest_question_text(db: Session, thread: DBEscalationThread) -> str:
    question = (
        db.query(DBEscalationThreadQuestion)
        .filter(DBEscalationThreadQuestion.thread_id == thread.thread_id)
        .order_by(DBEscalationThreadQuestion.sort_order.desc())
        .first()
    )
    return question.question_text if question else "Buyer added another question."


def _send_initial_alert_for_thread(
    db: Session,
    *,
    brokerage: DBBrokerage,
    thread: DBEscalationThread,
    now: Optional[datetime] = None,
) -> ThreadedEscalationResult:
    now = now or datetime.utcnow()
    metadata = dict(thread.metadata_json or {})
    envelope_body = metadata.get("envelope_body")
    if not envelope_body:
        return ThreadedEscalationResult(action="skipped", thread=thread)
    envelope_body = _format_initial_envelope(db, thread=thread, envelope_body=envelope_body)

    tags = list(metadata.get("tags") or [thread.escalation_type])
    result = get_transport().send_to_agents_ai(
        OutboundAgentMessage(
            brokerage_id=brokerage.brokerage_id,
            agents_ai_number=brokerage.agents_ai_number,
            agent_phone=thread.agent_phone,
            body=envelope_body,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
            buyer_phone=thread.buyer_phone,
            escalation_type=thread.escalation_type,
            tags=tags,
            agent_user_id=thread.agent_user_id,
        )
    )
    if not (result.ok and result.envelope_token):
        return ThreadedEscalationResult(action="skipped", thread=thread)

    thread.envelope_token = result.envelope_token
    thread.state = "open"
    thread.alerted_at = now
    thread.debounce_until = None
    thread.updated_at = now
    _mark_pending_questions_alerted(db, thread=thread)
    route = DBAgentMessageRoute(
        thread_id=thread.thread_id,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=thread.conversation_id,
        listing_id=thread.listing_id,
        buyer_phone=thread.buyer_phone,
        agent_user_id=thread.agent_user_id,
        agent_phone=thread.agent_phone,
        agents_ai_envelope_token=result.envelope_token,
        escalation_type=thread.escalation_type,
        tags=tags,
        expires_at=_parse_expires_at(metadata.get("expires_at"), now),
    )
    db.add(route)
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=thread.conversation_id,
        listing_id=thread.listing_id,
        buyer_phone=thread.buyer_phone,
        actor_user_id=thread.agent_user_id,
        event_type="escalation_sent",
        direction="outbound",
        details={
            "thread_id": thread.thread_id,
            "category": thread.category,
            "escalation_type": thread.escalation_type,
            "tags": tags,
            "envelope_token": result.envelope_token,
            "question_count": thread.question_count,
        },
    )
    return ThreadedEscalationResult(action="initial_sent", thread=thread, route=route, token=result.envelope_token)


def _send_update_for_thread(
    db: Session,
    *,
    brokerage: DBBrokerage,
    thread: DBEscalationThread,
    now: Optional[datetime] = None,
) -> ThreadedEscalationResult:
    now = now or datetime.utcnow()
    if not thread.envelope_token:
        return ThreadedEscalationResult(action="skipped", thread=thread)
    metadata = dict(thread.metadata_json or {})
    tags = list(metadata.get("tags") or [thread.escalation_type])
    pending_update_question = metadata.get("pending_update_question") or _latest_question_text(db, thread)
    body = format_update_message(
        db,
        thread=thread,
        token=thread.envelope_token,
        new_question=pending_update_question,
        now=now,
    )
    result = get_transport().send_to_agents_ai(
        OutboundAgentMessage(
            brokerage_id=brokerage.brokerage_id,
            agents_ai_number=brokerage.agents_ai_number,
            agent_phone=thread.agent_phone,
            body=body,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
            buyer_phone=thread.buyer_phone,
            escalation_type=thread.escalation_type,
            tags=tags,
            envelope_token=thread.envelope_token,
            agent_user_id=thread.agent_user_id,
        )
    )
    if not result.ok:
        return ThreadedEscalationResult(action="skipped", thread=thread, token=thread.envelope_token)
    metadata.pop("pending_update_question", None)
    thread.metadata_json = metadata
    thread.last_update_sent_at = now
    thread.debounce_until = None
    thread.updated_at = now
    _mark_pending_questions_alerted(db, thread=thread)
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=thread.conversation_id,
        listing_id=thread.listing_id,
        buyer_phone=thread.buyer_phone,
        actor_user_id=thread.agent_user_id,
        event_type="escalation_thread_updated",
        direction="outbound",
        details={
            "thread_id": thread.thread_id,
            "category": thread.category,
            "envelope_token": thread.envelope_token,
            "question_count": thread.question_count,
        },
    )
    return ThreadedEscalationResult(action="update_sent", thread=thread, token=thread.envelope_token)


def send_initial_or_update(
    db: Session,
    *,
    brokerage: DBBrokerage,
    alert: EscalationAlert,
    managing_agent,
    envelope_body: str,
    tags: list[str],
    expires_at: datetime,
    now: Optional[datetime] = None,
) -> ThreadedEscalationResult:
    now = now or datetime.utcnow()
    category = escalation_category(alert)
    bypass = escalation_bypasses_debounce(alert, category)
    existing = find_open_thread(
        db,
        brokerage_id=brokerage.brokerage_id,
        buyer_phone=alert.buyer_phone,
        listing_id=alert.listing_id,
        category=category,
        now=now,
    )

    if existing:
        if alert_requests_media(alert) and not thread_media_requested(existing):
            mark_thread_media_requested(existing, now=now)
        return _append_alert_to_existing_thread(
            db,
            brokerage=brokerage,
            existing=existing,
            alert=alert,
            category=category,
            bypass=bypass,
            now=now,
        )

    try:
        thread = create_thread(
            db,
            brokerage=brokerage,
            alert=alert,
            agent_user_id=managing_agent.user_id,
            agent_phone=managing_agent.whatsapp_phone,
            category=category,
            state="open" if bypass else "debouncing",
            metadata_json=_thread_metadata(
                envelope_body=envelope_body,
                tags=tags,
                expires_at=expires_at,
                requested_action=(alert.payload or {}).get("requested_action"),
            ),
            now=now,
        )
    except IntegrityError:
        db.rollback()
        existing = find_open_thread(
            db,
            brokerage_id=brokerage.brokerage_id,
            buyer_phone=alert.buyer_phone,
            listing_id=alert.listing_id,
            category=category,
            now=now,
        )
        if not existing:
            raise
        if alert_requests_media(alert) and not thread_media_requested(existing):
            mark_thread_media_requested(existing, now=now)
        return _append_alert_to_existing_thread(
            db,
            brokerage=brokerage,
            existing=existing,
            alert=alert,
            category=category,
            bypass=bypass,
            now=now,
        )

    # DAL-161: media_requested is set at classification time, stored on the
    # thread — never re-derived at relay routing time.
    if alert_requests_media(alert):
        mark_thread_media_requested(thread, now=now)
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=alert.conversation_id,
        listing_id=alert.listing_id,
        buyer_phone=alert.buyer_phone,
        actor_user_id=managing_agent.user_id,
        event_type="escalation_thread_created",
        direction="system",
        details={
            "thread_id": thread.thread_id,
            "category": thread.category,
            "state": thread.state,
            "bypasses_debounce": bypass,
            "question_count": thread.question_count,
        },
    )
    if bypass:
        result = _send_initial_alert_for_thread(db, brokerage=brokerage, thread=thread, now=now)
        safe_commit(db)
        return result

    safe_commit(db)
    return ThreadedEscalationResult(action="debounced", thread=thread)


def resolve_thread_for_route(db: Session, *, route: DBAgentMessageRoute, now: Optional[datetime] = None) -> int:
    now = now or datetime.utcnow()
    thread = db.get(DBEscalationThread, route.thread_id) if route.thread_id else None
    if not thread:
        return 0
    thread.state = "resolved"
    thread.closed_at = now
    thread.close_reason = "agent_reply"
    thread.updated_at = now
    questions = (
        db.query(DBEscalationThreadQuestion)
        .filter(
            DBEscalationThreadQuestion.thread_id == thread.thread_id,
            DBEscalationThreadQuestion.resolved_at.is_(None),
        )
        .all()
    )
    for question in questions:
        question.resolved_at = now
    count = int(thread.question_count or len(questions))
    record_compliance_event(
        db,
        brokerage_id=route.brokerage_id,
        conversation_id=route.conversation_id,
        listing_id=route.listing_id,
        buyer_phone=route.buyer_phone,
        actor_user_id=route.agent_user_id,
        event_type="escalation_thread_resolved",
        direction="system",
        details={
            "thread_id": thread.thread_id,
            "category": thread.category,
            "close_reason": "agent_reply",
            "question_count": count,
        },
    )
    return count


def process_due_escalation_threads(
    db: Session,
    *,
    now: Optional[datetime] = None,
    buyer_phone: Optional[str] = None,
    listing_id: Optional[str] = None,
) -> list[ThreadedEscalationResult]:
    now = now or datetime.utcnow()
    results: list[ThreadedEscalationResult] = []

    stale_cutoff = now - THREAD_WINDOW
    stale_query = db.query(DBEscalationThread).filter(
        DBEscalationThread.state.in_(OPEN_THREAD_STATES),
        DBEscalationThread.last_buyer_message_at < stale_cutoff,
    )
    if buyer_phone:
        stale_query = stale_query.filter(DBEscalationThread.buyer_phone == buyer_phone)
    if listing_id:
        stale_query = stale_query.filter(DBEscalationThread.listing_id == listing_id)
    stale_threads = stale_query.all()
    for thread in stale_threads:
        thread.state = "timed_out"
        thread.closed_at = now
        thread.close_reason = "timeout"
        thread.updated_at = now
        record_compliance_event(
            db,
            brokerage_id=thread.brokerage_id,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
            buyer_phone=thread.buyer_phone,
            actor_user_id=thread.agent_user_id,
            event_type="escalation_thread_timed_out",
            direction="system",
            details={
                "thread_id": thread.thread_id,
                "category": thread.category,
                "question_count": thread.question_count,
            },
        )
        results.append(ThreadedEscalationResult(action="timed_out", thread=thread, token=thread.envelope_token))

    due_query = db.query(DBEscalationThread).filter(
        DBEscalationThread.state.in_({"debouncing", "updated"}),
        or_(
            DBEscalationThread.debounce_until <= now,
            DBEscalationThread.max_debounce_until <= now,
        ),
    )
    if buyer_phone:
        due_query = due_query.filter(DBEscalationThread.buyer_phone == buyer_phone)
    if listing_id:
        due_query = due_query.filter(DBEscalationThread.listing_id == listing_id)
    due_threads = due_query.order_by(DBEscalationThread.updated_at.asc()).all()
    for thread in due_threads:
        if thread.state not in OPEN_THREAD_STATES:
            continue
        brokerage = db.get(DBBrokerage, thread.brokerage_id)
        if not brokerage:
            continue
        if thread.state == "debouncing":
            results.append(_send_initial_alert_for_thread(db, brokerage=brokerage, thread=thread, now=now))
        elif thread.state == "updated":
            results.append(_send_update_for_thread(db, brokerage=brokerage, thread=thread, now=now))
    safe_commit(db)
    return results


def close_open_threads_for_opt_out(
    db: Session,
    *,
    brokerage_id: str,
    buyer_phone: str,
    now: Optional[datetime] = None,
) -> int:
    now = now or datetime.utcnow()
    threads = (
        db.query(DBEscalationThread)
        .filter(
            DBEscalationThread.brokerage_id == brokerage_id,
            DBEscalationThread.buyer_phone == buyer_phone,
            DBEscalationThread.state.in_(OPEN_THREAD_STATES),
        )
        .all()
    )
    for thread in threads:
        thread.state = "opt_out_closed"
        thread.closed_at = now
        thread.close_reason = "opt_out"
        thread.updated_at = now
        record_compliance_event(
            db,
            brokerage_id=thread.brokerage_id,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
            buyer_phone=thread.buyer_phone,
            actor_user_id=thread.agent_user_id,
            event_type="escalation_thread_opt_out_closed",
            direction="system",
            details={
                "thread_id": thread.thread_id,
                "category": thread.category,
                "question_count": thread.question_count,
            },
        )
    return len(threads)
