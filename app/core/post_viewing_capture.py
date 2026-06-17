from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.brokerage_access import record_compliance_event
from app.core.brokerage_resolver import get_managing_agent
from app.core.messaging import get_transport
from app.core.messaging.types import OutboundAgentMessage, OutboundBuyerMessage
from app.core.tenant_viewings import normalize_phone
from app.db.session import safe_commit
from app.models.db_models import (
    DBBrokerage,
    DBConversation,
    DBDraftReply,
    DBLeadAction,
    DBLeadAssignment,
    DBLeadTask,
    DBListing,
    DBViewing,
    DBViewingFeedback,
)


FEEDBACK_DELAY = timedelta(hours=4)
DEFAULT_VIEWING_DURATION_MINUTES = 45


def viewing_end_at(viewing: DBViewing) -> Optional[datetime]:
    if not viewing.scheduled_for:
        return None
    metadata = viewing.metadata_json or {}
    duration = metadata.get("duration_minutes")
    if duration is None:
        calendar_event = metadata.get("calendar_event") or {}
        duration = calendar_event.get("duration_minutes")
    try:
        duration_minutes = int(duration or DEFAULT_VIEWING_DURATION_MINUTES)
    except (TypeError, ValueError):
        duration_minutes = DEFAULT_VIEWING_DURATION_MINUTES
    return viewing.scheduled_for + timedelta(minutes=max(15, duration_minutes))


def post_viewing_due_at(viewing: DBViewing) -> Optional[datetime]:
    ended = viewing_end_at(viewing)
    return ended + FEEDBACK_DELAY if ended else None


def serialize_post_viewing_feedback(db: Session, viewing: DBViewing) -> dict[str, Any]:
    rows = (
        db.query(DBViewingFeedback)
        .filter(DBViewingFeedback.viewing_id == viewing.viewing_id)
        .all()
    )
    by_participant = {row.participant_type: _serialize_feedback(row) for row in rows}
    metadata = dict((viewing.metadata_json or {}).get("post_viewing") or {})
    return {
        "status": metadata.get("status") or "not_requested",
        "due_at": metadata.get("due_at") or _iso(post_viewing_due_at(viewing)),
        "requested_at": metadata.get("requested_at"),
        "buyer": by_participant.get("buyer"),
        "agent": by_participant.get("agent"),
        "metadata": metadata,
    }


def request_due_post_viewing_feedback(
    db: Session,
    *,
    brokerage_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> list[DBViewing]:
    now = now or datetime.utcnow()
    query = db.query(DBViewing).filter(DBViewing.status == "completed")
    if brokerage_id:
        query = query.filter(DBViewing.brokerage_id == brokerage_id)
    requested: list[DBViewing] = []
    for viewing in query.all():
        due_at = post_viewing_due_at(viewing)
        metadata = dict((viewing.metadata_json or {}).get("post_viewing") or {})
        if not due_at or due_at > now or metadata.get("requested_at"):
            continue
        brokerage = db.get(DBBrokerage, viewing.brokerage_id)
        conversation = db.get(DBConversation, viewing.conversation_id)
        listing = db.get(DBListing, viewing.listing_id)
        if not brokerage or not conversation or not listing:
            continue
        requested.append(request_post_viewing_feedback(
            db,
            brokerage=brokerage,
            viewing=viewing,
            conversation=conversation,
            listing=listing,
            actor_user_id=None,
            now=now,
            force=True,
        ))
    return requested


def request_post_viewing_feedback(
    db: Session,
    *,
    brokerage: DBBrokerage,
    viewing: DBViewing,
    conversation: DBConversation,
    listing: DBListing,
    actor_user_id: Optional[str],
    now: Optional[datetime] = None,
    force: bool = False,
) -> DBViewing:
    now = now or datetime.utcnow()
    due_at = post_viewing_due_at(viewing)
    if not force and due_at and due_at > now:
        raise ValueError("Post-viewing feedback is not due yet")
    if not brokerage.brokerage_ai_number:
        raise ValueError("Brokerage AI WhatsApp number is not configured")

    metadata = dict(viewing.metadata_json or {})
    post_viewing = dict(metadata.get("post_viewing") or {})
    if post_viewing.get("requested_at") and not force:
        raise ValueError("Post-viewing feedback has already been requested")

    buyer_body = _buyer_feedback_prompt(conversation, listing)
    buyer_result = get_transport().send_to_buyer(
        OutboundBuyerMessage(
            brokerage_id=brokerage.brokerage_id,
            brokerage_ai_number=brokerage.brokerage_ai_number,
            buyer_phone=viewing.buyer_phone,
            body=buyer_body,
            conversation_id=viewing.conversation_id,
            listing_id=viewing.listing_id,
        )
    )
    if not buyer_result.ok:
        raise ValueError(buyer_result.error or "Buyer feedback request failed")

    buyer_row = _upsert_feedback_request(
        db,
        brokerage=brokerage,
        viewing=viewing,
        participant_type="buyer",
        requested_at=now,
        metadata={
            "prompt_body": buyer_body,
            "transport_message_id": buyer_result.transport_message_id,
        },
    )

    agent_status = "not_configured"
    agent_transport_id = None
    agent_prompt = _agent_feedback_prompt(conversation, listing, viewing)
    managing_agent = get_managing_agent(listing, db)
    agent_phone = getattr(managing_agent, "whatsapp_phone", None)
    agent_user_id = getattr(managing_agent, "user_id", None) or viewing.agent_user_id
    if brokerage.agents_ai_number and agent_phone:
        agent_result = get_transport().send_to_agents_ai(
            OutboundAgentMessage(
                brokerage_id=brokerage.brokerage_id,
                agents_ai_number=brokerage.agents_ai_number,
                agent_phone=agent_phone,
                body=agent_prompt,
                conversation_id=viewing.conversation_id,
                listing_id=viewing.listing_id,
                buyer_phone=viewing.buyer_phone,
                escalation_type="post_viewing_feedback",
                tags=["post_viewing", "feedback"],
                agent_user_id=agent_user_id,
            )
        )
        if agent_result.ok:
            agent_status = "sent"
            agent_transport_id = agent_result.transport_message_id
    _upsert_feedback_request(
        db,
        brokerage=brokerage,
        viewing=viewing,
        participant_type="agent",
        requested_at=now,
        metadata={
            "prompt_body": agent_prompt,
            "transport_message_id": agent_transport_id,
            "agent_request_status": agent_status,
        },
    )

    post_viewing.update({
        "status": "requested",
        "due_at": _iso(due_at),
        "requested_at": now.isoformat(),
        "buyer_request_status": "sent",
        "agent_request_status": agent_status,
        "buyer_feedback_id": buyer_row.feedback_id,
    })
    viewing.status = "feedback_requested"
    viewing.metadata_json = {**metadata, "post_viewing": post_viewing}
    viewing.updated_at = now
    _mark_post_viewing_task(db, viewing=viewing, status="in_progress", now=now)
    _mark_post_viewing_draft_sent(db, viewing=viewing, now=now)
    db.add(DBLeadAction(
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        agent_user_id=actor_user_id or viewing.agent_user_id,
        action_type="post_viewing_feedback_requested",
        outcome="requested",
        payload={"viewing_id": viewing.viewing_id, "buyer_feedback_id": buyer_row.feedback_id},
    ))
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        actor_user_id=actor_user_id,
        event_type="post_viewing_feedback_requested",
        direction="outbound",
        details={"viewing_id": viewing.viewing_id, "agent_request_status": agent_status},
    )
    safe_commit(db)
    db.refresh(viewing)
    return viewing


def handle_buyer_post_viewing_reply(
    db: Session,
    *,
    brokerage: DBBrokerage,
    buyer_phone: str,
    body: str,
    message_sid: Optional[str] = None,
    now: Optional[datetime] = None,
) -> tuple[bool, Optional[DBViewingFeedback]]:
    now = now or datetime.utcnow()
    normalized_phone = normalize_phone(buyer_phone)
    raw_phone = str(buyer_phone or "").strip()
    if raw_phone.lower().startswith("whatsapp:"):
        raw_phone = raw_phone[len("whatsapp:"):]
    phone_candidates = {phone for phone in (raw_phone, normalized_phone) if phone}
    if not phone_candidates:
        return False, None
    feedback = (
        db.query(DBViewingFeedback)
        .filter(
            DBViewingFeedback.brokerage_id == brokerage.brokerage_id,
            DBViewingFeedback.participant_type == "buyer",
            DBViewingFeedback.buyer_phone.in_(phone_candidates),
            DBViewingFeedback.status == "requested",
            DBViewingFeedback.requested_at >= now - timedelta(days=14),
        )
        .order_by(DBViewingFeedback.requested_at.desc().nullslast(), DBViewingFeedback.created_at.desc())
        .first()
    )
    if not feedback:
        return False, None
    viewing = db.get(DBViewing, feedback.viewing_id)
    if not viewing:
        return False, None
    parsed = parse_buyer_feedback(body)
    _apply_feedback(
        feedback,
        parsed=parsed,
        raw_body=body,
        source="whatsapp_buyer_reply",
        message_sid=message_sid,
        now=now,
    )
    _after_feedback_received(
        db,
        brokerage=brokerage,
        viewing=viewing,
        feedback=feedback,
        actor_user_id=None,
        now=now,
    )
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=feedback.conversation_id,
        listing_id=feedback.listing_id,
        buyer_phone=feedback.buyer_phone,
        actor_user_id=None,
        event_type="post_viewing_buyer_feedback_received",
        direction="inbound",
        details={"viewing_id": feedback.viewing_id, "feedback_id": feedback.feedback_id},
    )
    safe_commit(db)
    db.refresh(feedback)
    return True, feedback


def record_agent_post_viewing_feedback(
    db: Session,
    *,
    brokerage: DBBrokerage,
    viewing: DBViewing,
    actor_user_id: str,
    raw_body: str,
    score: Optional[int] = None,
    temperature: Optional[str] = None,
    financing_status: Optional[str] = None,
    next_action: Optional[str] = None,
    now: Optional[datetime] = None,
) -> DBViewingFeedback:
    now = now or datetime.utcnow()
    parsed = parse_agent_feedback(
        raw_body,
        score=score,
        temperature=temperature,
        financing_status=financing_status,
        next_action=next_action,
    )
    feedback = _upsert_feedback_request(
        db,
        brokerage=brokerage,
        viewing=viewing,
        participant_type="agent",
        requested_at=now,
        metadata={"submitted_by_user_id": actor_user_id},
    )
    _apply_feedback(
        feedback,
        parsed=parsed,
        raw_body=raw_body,
        source="dashboard_agent_form",
        message_sid=None,
        now=now,
    )
    _after_feedback_received(
        db,
        brokerage=brokerage,
        viewing=viewing,
        feedback=feedback,
        actor_user_id=actor_user_id,
        now=now,
    )
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        actor_user_id=actor_user_id,
        event_type="post_viewing_agent_feedback_received",
        direction="system",
        details={"viewing_id": viewing.viewing_id, "feedback_id": feedback.feedback_id},
    )
    safe_commit(db)
    db.refresh(feedback)
    return feedback


def parse_buyer_feedback(body: str) -> dict[str, Any]:
    lower = body.lower()
    score = _extract_score(body)
    likes: list[str] = []
    concerns: list[str] = []
    if any(token in lower for token in ("liked", "loved", "good", "great", "view", "layout", "location")):
        likes.append(body.strip())
    if any(token in lower for token in ("concern", "issue", "expensive", "price", "small", "noise", "parking")):
        concerns.append(body.strip())
    next_action = "call_buyer"
    if any(token in lower for token in ("offer", "bid", "negotiate")):
        next_action = "discuss_offer"
    elif any(token in lower for token in ("similar", "alternative", "other option", "another")):
        next_action = "send_alternatives"
    elif any(token in lower for token in ("not interested", "pass", "no thanks")):
        next_action = "nurture"
    return {
        "score": score,
        "sentiment": _sentiment_from_score_and_text(score, lower),
        "next_action": next_action,
        "summary": body.strip(),
        "structured": {
            "likes": likes,
            "concerns": concerns,
            "offer_interest": next_action == "discuss_offer",
            "similar_options_interest": next_action == "send_alternatives",
        },
    }


def parse_agent_feedback(
    body: str,
    *,
    score: Optional[int],
    temperature: Optional[str],
    financing_status: Optional[str],
    next_action: Optional[str],
) -> dict[str, Any]:
    lower = body.lower()
    parsed_score = score if score is not None else _extract_score(body)
    parsed_temperature = temperature or _temperature_from_text(lower, parsed_score)
    parsed_financing = financing_status or _financing_from_text(lower)
    parsed_next = next_action or _agent_next_action_from_text(lower)
    return {
        "score": parsed_score,
        "sentiment": _sentiment_from_score_and_text(parsed_score, lower),
        "temperature": parsed_temperature,
        "financing_status": parsed_financing,
        "next_action": parsed_next,
        "summary": body.strip(),
        "structured": {
            "temperature": parsed_temperature,
            "financing_status": parsed_financing,
            "next_action": parsed_next,
        },
    }


def _upsert_feedback_request(
    db: Session,
    *,
    brokerage: DBBrokerage,
    viewing: DBViewing,
    participant_type: str,
    requested_at: datetime,
    metadata: dict[str, Any],
) -> DBViewingFeedback:
    row = (
        db.query(DBViewingFeedback)
        .filter(
            DBViewingFeedback.viewing_id == viewing.viewing_id,
            DBViewingFeedback.participant_type == participant_type,
        )
        .first()
    )
    if not row:
        row = DBViewingFeedback(
            brokerage_id=brokerage.brokerage_id,
            viewing_id=viewing.viewing_id,
            conversation_id=viewing.conversation_id,
            listing_id=viewing.listing_id,
            buyer_phone=viewing.buyer_phone,
            agent_user_id=viewing.agent_user_id,
            participant_type=participant_type,
            status="requested",
            requested_at=requested_at,
            metadata_json=metadata,
        )
        db.add(row)
    else:
        existing = dict(row.metadata_json or {})
        row.status = row.status or "requested"
        row.requested_at = row.requested_at or requested_at
        row.metadata_json = {**existing, **metadata}
        row.updated_at = requested_at
    return row


def _apply_feedback(
    feedback: DBViewingFeedback,
    *,
    parsed: dict[str, Any],
    raw_body: str,
    source: str,
    message_sid: Optional[str],
    now: datetime,
) -> None:
    metadata = dict(feedback.metadata_json or {})
    if message_sid:
        metadata["message_sid"] = message_sid
    feedback.status = "received"
    feedback.score = parsed.get("score")
    feedback.sentiment = parsed.get("sentiment")
    feedback.temperature = parsed.get("temperature")
    feedback.financing_status = parsed.get("financing_status")
    feedback.next_action = parsed.get("next_action")
    feedback.summary = parsed.get("summary")
    feedback.raw_body = raw_body
    feedback.structured_json = parsed.get("structured") or {}
    feedback.source = source
    feedback.responded_at = now
    feedback.metadata_json = metadata
    feedback.updated_at = now


def _after_feedback_received(
    db: Session,
    *,
    brokerage: DBBrokerage,
    viewing: DBViewing,
    feedback: DBViewingFeedback,
    actor_user_id: Optional[str],
    now: datetime,
) -> None:
    metadata = dict(viewing.metadata_json or {})
    post_viewing = dict(metadata.get("post_viewing") or {})
    post_viewing[f"{feedback.participant_type}_status"] = "received"
    post_viewing[f"{feedback.participant_type}_feedback_id"] = feedback.feedback_id
    post_viewing[f"{feedback.participant_type}_responded_at"] = now.isoformat()
    if _both_feedback_received(db, viewing.viewing_id, pending_feedback=feedback):
        post_viewing["status"] = "completed"
        viewing.status = "feedback_completed"
        _mark_post_viewing_task(db, viewing=viewing, status="done", now=now, completed_by=actor_user_id)
    else:
        post_viewing["status"] = "partially_received"
    viewing.post_viewing_notes = _combined_notes(db, viewing.viewing_id, pending_feedback=feedback)
    viewing.metadata_json = {**metadata, "post_viewing": post_viewing}
    viewing.updated_at = now
    _feed_hot_list_state(db, viewing=viewing, feedback=feedback, now=now)
    db.add(DBLeadAction(
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        agent_user_id=actor_user_id or viewing.agent_user_id,
        action_type=f"post_viewing_{feedback.participant_type}_feedback_received",
        outcome=feedback.next_action,
        note=feedback.summary,
        payload={"viewing_id": viewing.viewing_id, "feedback_id": feedback.feedback_id},
    ))


def _both_feedback_received(db: Session, viewing_id: str, *, pending_feedback: DBViewingFeedback) -> bool:
    rows = (
        db.query(DBViewingFeedback)
        .filter(DBViewingFeedback.viewing_id == viewing_id)
        .all()
    )
    statuses = {row.participant_type: row.status for row in rows}
    statuses[pending_feedback.participant_type] = pending_feedback.status
    return statuses.get("buyer") == "received" and statuses.get("agent") == "received"


def _combined_notes(db: Session, viewing_id: str, *, pending_feedback: DBViewingFeedback) -> str:
    rows = (
        db.query(DBViewingFeedback)
        .filter(DBViewingFeedback.viewing_id == viewing_id)
        .all()
    )
    by_participant = {row.participant_type: row for row in rows}
    by_participant[pending_feedback.participant_type] = pending_feedback
    parts = []
    for label in ("buyer", "agent"):
        row = by_participant.get(label)
        if row and row.summary:
            parts.append(f"{label.title()}: {row.summary}")
    return "\n".join(parts)


def _feed_hot_list_state(db: Session, *, viewing: DBViewing, feedback: DBViewingFeedback, now: datetime) -> None:
    assignment = (
        db.query(DBLeadAssignment)
        .filter(DBLeadAssignment.conversation_id == viewing.conversation_id)
        .first()
    )
    if assignment:
        metadata = dict(assignment.metadata_json or {})
        metadata["post_viewing_feedback"] = {
            "viewing_id": viewing.viewing_id,
            "participant_type": feedback.participant_type,
            "score": feedback.score,
            "sentiment": feedback.sentiment,
            "next_action": feedback.next_action,
            "received_at": now.isoformat(),
        }
        assignment.metadata_json = metadata
        assignment.signal = "post_viewing_hot" if feedback.next_action in {"discuss_offer", "call_buyer"} else "post_viewing_follow_up"
        assignment.next_action = feedback.next_action or "post_viewing_follow_up"
        assignment.next_action_reason = "Post-viewing feedback received; agent should act on the captured next step."
        assignment.urgency_score = max(assignment.urgency_score or 0, 82 if feedback.next_action == "discuss_offer" else 68)
        assignment.status = "offer" if feedback.next_action == "discuss_offer" else "active"
        assignment.due_at = now
        assignment.updated_at = now

    task_key = f"post-viewing-next-action:{viewing.viewing_id}"
    task = db.query(DBLeadTask).filter(DBLeadTask.task_key == task_key).first()
    title = "Discuss offer" if feedback.next_action == "discuss_offer" else "Follow up after viewing"
    if not task:
        db.add(DBLeadTask(
            task_key=task_key,
            brokerage_id=viewing.brokerage_id,
            conversation_id=viewing.conversation_id,
            listing_id=viewing.listing_id,
            buyer_phone=viewing.buyer_phone,
            assigned_agent_id=viewing.agent_user_id,
            task_type="offer" if feedback.next_action == "discuss_offer" else "whatsapp",
            title=title,
            description=feedback.summary or "Post-viewing feedback needs agent follow-up.",
            status="open",
            priority="high" if feedback.next_action == "discuss_offer" else "normal",
            source="post_viewing_capture",
            due_at=now,
            metadata_json={"viewing_id": viewing.viewing_id, "feedback_id": feedback.feedback_id, "next_action": feedback.next_action},
        ))


def _mark_post_viewing_task(
    db: Session,
    *,
    viewing: DBViewing,
    status: str,
    now: datetime,
    completed_by: Optional[str] = None,
) -> None:
    task = (
        db.query(DBLeadTask)
        .filter(DBLeadTask.task_key == f"post-viewing-feedback:{viewing.viewing_id}")
        .first()
    )
    if not task:
        return
    task.status = status
    task.updated_at = now
    if status == "done":
        task.completed_at = now
        task.completed_by = completed_by or viewing.agent_user_id


def _mark_post_viewing_draft_sent(db: Session, *, viewing: DBViewing, now: datetime) -> None:
    draft = (
        db.query(DBDraftReply)
        .filter(
            DBDraftReply.conversation_id == viewing.conversation_id,
            DBDraftReply.intent == "post_viewing_feedback",
            DBDraftReply.status.in_(["draft", "edited"]),
        )
        .order_by(DBDraftReply.created_at.desc())
        .first()
    )
    if draft:
        draft.status = "sent"
        draft.sent_at = now
        draft.updated_at = now


def _extract_score(body: str) -> Optional[int]:
    match = re.search(r"\b([1-9]|10)\s*(?:/|out of)\s*10\b", body, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"\b([1-5])\s*(?:/|out of)\s*5\b", body, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 2
    match = re.search(r"\bscore\s*[:=-]?\s*([1-9]|10)\b", body, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _sentiment_from_score_and_text(score: Optional[int], lower: str) -> str:
    if score is not None:
        if score >= 8:
            return "positive"
        if score <= 4:
            return "negative"
    if any(token in lower for token in ("loved", "great", "interested", "offer", "good")):
        return "positive"
    if any(token in lower for token in ("not interested", "bad", "too expensive", "small", "pass")):
        return "negative"
    return "neutral"


def _temperature_from_text(lower: str, score: Optional[int]) -> str:
    if any(token in lower for token in ("hot", "offer", "very interested", "ready")) or (score is not None and score >= 8):
        return "hot"
    if any(token in lower for token in ("cold", "not interested", "pass")) or (score is not None and score <= 4):
        return "cold"
    return "warm"


def _financing_from_text(lower: str) -> str:
    if any(token in lower for token in ("cash", "cash buyer")):
        return "cash"
    if any(token in lower for token in ("mortgage", "finance", "financing", "bank")):
        return "mortgage"
    return "unknown"


def _agent_next_action_from_text(lower: str) -> str:
    if any(token in lower for token in ("offer", "negotiate", "bid")):
        return "discuss_offer"
    if any(token in lower for token in ("similar", "alternative", "other option")):
        return "send_alternatives"
    if any(token in lower for token in ("call", "phone")):
        return "call_buyer"
    return "follow_up"


def _buyer_feedback_prompt(conversation: DBConversation, listing: DBListing) -> str:
    buyer = conversation.buyer_name or "there"
    project = (listing.spa_data or {}).get("project") or "the property"
    return (
        f"Hi {buyer}, thanks for viewing {project}. How did it feel on a 1-10 scale? "
        "Reply with what you liked, any concerns, and whether you want to discuss an offer or see similar options."
    )


def _agent_feedback_prompt(conversation: DBConversation, listing: DBListing, viewing: DBViewing) -> str:
    project = (listing.spa_data or {}).get("project") or listing.listing_id
    scheduled = viewing.scheduled_for.isoformat() if viewing.scheduled_for else "unscheduled"
    return (
        "[POST-VIEWING FEEDBACK]\n"
        f"Property: {project}\n"
        f"Viewing: {scheduled}\n"
        f"Buyer: {conversation.buyer_name or conversation.buyer_phone}\n\n"
        "Please capture buyer rating, temperature, financing status, and next action in the viewing detail page."
    )


def _serialize_feedback(row: DBViewingFeedback) -> dict[str, Any]:
    return {
        "feedback_id": row.feedback_id,
        "participant_type": row.participant_type,
        "status": row.status,
        "score": row.score,
        "sentiment": row.sentiment,
        "temperature": row.temperature,
        "financing_status": row.financing_status,
        "next_action": row.next_action,
        "summary": row.summary,
        "structured": row.structured_json or {},
        "source": row.source,
        "requested_at": _iso(row.requested_at),
        "responded_at": _iso(row.responded_at),
        "metadata": row.metadata_json or {},
    }


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None
