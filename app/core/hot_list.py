from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.brokerage_access import can_view_conversation, get_or_create_lead_assignment
from app.core.buyer_profiles import effective_fields
from app.core.deal_readiness import compute_readiness, fields_from_effective_fields, serialize_readiness
from app.db.session import safe_commit
from app.models.db_models import (
    DBBrokerage,
    DBBrokerageBuyerProfile,
    DBConversation,
    DBDraftReply,
    DBHotlistRefreshRun,
    DBLeadAssignment,
    DBLeadTask,
    DBMessage,
)


ACTIVE_ASSIGNMENT_STATUSES = {"new", "active", "viewing", "offer"}
STALE_AFTER = timedelta(hours=24)


@dataclass(frozen=True)
class HotListScore:
    signal: str
    urgency_score: int
    next_action: str
    next_action_reason: str
    status: str
    task_type: str
    task_title: str
    task_description: str
    task_priority: str
    due_at: datetime
    last_buyer_message_at: Optional[datetime]
    latest_message_at: Optional[datetime]
    buyer_message_count: int
    stale: bool


def _latest_message(db: Session, conversation_id: str) -> Optional[DBMessage]:
    return (
        db.query(DBMessage)
        .filter(DBMessage.conversation_id == conversation_id)
        .order_by(DBMessage.timestamp.desc())
        .first()
    )


def _latest_buyer_message(db: Session, conversation_id: str) -> Optional[DBMessage]:
    return (
        db.query(DBMessage)
        .filter(DBMessage.conversation_id == conversation_id, DBMessage.role == "user")
        .order_by(DBMessage.timestamp.desc())
        .first()
    )


def _buyer_message_count(db: Session, conversation_id: str) -> int:
    return (
        db.query(DBMessage)
        .filter(DBMessage.conversation_id == conversation_id, DBMessage.role == "user")
        .count()
    )


def _summary_text(conversation: DBConversation) -> str:
    summary = conversation.ai_summary or {}
    if not isinstance(summary, dict):
        return ""
    values: list[str] = []
    for key in ("interest_level", "sentiment", "key_question", "next_step_hint"):
        value = summary.get(key)
        if value:
            values.append(str(value))
    topics = summary.get("topics")
    if isinstance(topics, list):
        values.extend(str(topic) for topic in topics if topic)
    return " ".join(values).lower()


def _listing_name(conversation: DBConversation) -> str:
    listing = conversation.listing
    spa = (listing.spa_data or {}) if listing else {}
    return spa.get("project") or "the property"


def _buyer_name(conversation: DBConversation) -> str:
    return conversation.buyer_name or "the buyer"


def _contains_financing_signal(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in ("mortgage", "finance", "financing", "loan", "bank approval", "ltv"))


def _is_offer(conversation: DBConversation) -> bool:
    return bool(conversation.escalation_reason and conversation.escalation_reason.startswith("offer:"))


def _is_viewing_intent(latest: Optional[DBMessage], summary_text: str) -> bool:
    if latest and latest.intent == "viewing_request":
        return True
    return any(token in summary_text for token in ("viewing", "view the", "see it", "tour"))


def score_conversation(
    db: Session,
    conversation: DBConversation,
    *,
    now: Optional[datetime] = None,
) -> HotListScore:
    now = now or datetime.utcnow()
    latest = _latest_message(db, conversation.conversation_id)
    latest_buyer = _latest_buyer_message(db, conversation.conversation_id)
    buyer_count = _buyer_message_count(db, conversation.conversation_id)
    latest_content = latest.content if latest else ""
    summary = _summary_text(conversation)
    last_buyer_at = latest_buyer.timestamp if latest_buyer else None
    latest_at = latest.timestamp if latest else None
    stale = bool(last_buyer_at and last_buyer_at <= now - STALE_AFTER)

    score = 10
    signal = "cold"
    status = "active" if buyer_count else "new"
    next_action = "follow_up"
    task_type = "whatsapp"
    due_at = now + timedelta(hours=2)
    reason = "Buyer activity needs a light follow-up before the thread goes cold."

    # DAL-165: the structured offer record is preferred over message-derived
    # offer signals — one branch, so a first-class offer never double-counts
    # with the legacy escalation-reason signal.
    from app.core.offers import open_offer_for_conversation

    structured_offer = open_offer_for_conversation(db, conversation.conversation_id)
    if structured_offer is not None or _is_offer(conversation):
        signal = "firm_offer"
        status = "offer"
        next_action = "review_offer"
        task_type = "offer"
        score += 55
        due_at = now
        reason = (
            f"Open {structured_offer.status} offer of AED {structured_offer.amount:,.0f} on this thread."
            if structured_offer is not None and structured_offer.amount
            else "Buyer submitted a specific offer and needs agent review."
        )
    elif _is_viewing_intent(latest, summary):
        signal = "ready_to_view"
        status = "viewing"
        next_action = "book_viewing"
        task_type = "viewing"
        score += 42
        due_at = now + timedelta(minutes=30)
        reason = "Buyer asked about viewing or availability. Confirm slots and access details."
    elif _contains_financing_signal(latest_content) or _contains_financing_signal(summary):
        signal = "needs_financing"
        next_action = "clarify_financing"
        task_type = "call"
        score += 32
        due_at = now + timedelta(hours=1)
        reason = "Buyer raised financing. Confirm cash or mortgage readiness before next steps."
    elif conversation.detected_budget:
        signal = "budget_matched"
        next_action = "call_now"
        task_type = "call"
        score += 28
        due_at = now + timedelta(hours=1)
        reason = "Buyer has a detected budget. Qualify timeline, funding, and fit."

    if latest and latest.role == "user":
        score += 12
    if latest_at:
        age = now - latest_at
        if age <= timedelta(hours=4):
            score += 14
        elif age <= timedelta(hours=24):
            score += 8
    score += min(15, buyer_count * 3)
    if "high" in summary or "serious" in summary or "motivated" in summary:
        score += 10
    if stale:
        score += 8
        if next_action not in {"review_offer", "book_viewing"}:
            next_action = "follow_up"
            task_type = "whatsapp"
            due_at = now + timedelta(hours=1)
            reason = "Buyer has gone quiet after meaningful engagement. Send a short check-in."

    score = max(0, min(score, 100))
    priority = "critical" if score >= 90 else "high" if score >= 70 else "normal"
    title_action = {
        "review_offer": "Review offer",
        "book_viewing": "Book viewing",
        "clarify_financing": "Clarify financing",
        "call_now": "Call buyer",
        "follow_up": "Follow up",
    }.get(next_action, "Follow up")
    task_title = f"{title_action}: {_buyer_name(conversation)}"
    task_description = f"{reason} Listing: {_listing_name(conversation)}."

    return HotListScore(
        signal=signal,
        urgency_score=score,
        next_action=next_action,
        next_action_reason=reason,
        status=status,
        task_type=task_type,
        task_title=task_title,
        task_description=task_description,
        task_priority=priority,
        due_at=due_at,
        last_buyer_message_at=last_buyer_at,
        latest_message_at=latest_at,
        buyer_message_count=buyer_count,
        stale=stale,
    )


def _readiness_conversation_context(score: HotListScore, conversation: DBConversation) -> dict:
    latest_text = ""
    latest_message = None
    try:
        latest_message = conversation.messages[-1] if conversation.messages else None
        latest_text = (latest_message.content if latest_message else "").lower()
    except Exception:
        latest_text = ""
    return {
        "viewing_intent": bool(
            score.next_action == "book_viewing"
            or score.signal == "ready_to_view"
            or (latest_message and latest_message.intent == "viewing_request")
        ),
        "offer_intent": bool(
            score.next_action == "review_offer"
            or score.signal == "firm_offer"
            or _is_offer(conversation)
        ),
        "responsive": bool(latest_message and latest_message.role == "user"),
        "urgent": bool((score.urgency_score or 0) >= 70 or any(term in latest_text for term in ("urgent", "asap", "serious"))),
    }


def build_hot_list_readiness_shadow(
    *,
    effective_buyer_fields: dict,
    conversation: DBConversation,
    score: HotListScore,
) -> dict:
    """Read-only DealReadiness metadata for hot-list inspection.

    This is deliberately not an input to hot-list scoring, thresholds, task
    creation, notifications, drafts, or sends.
    """
    listing = conversation.listing
    fields = fields_from_effective_fields(
        effective_buyer_fields or {},
        fallback_budget_aed=conversation.detected_budget,
    )
    readiness = compute_readiness(
        fields,
        conversation_ctx=_readiness_conversation_context(score, conversation),
        listing_ctx=(
            {
                "listing_id": listing.listing_id,
                "property_type": listing.property_type,
            }
            if listing
            else {"listing_id": conversation.listing_id}
        ),
    )
    return {
        "mode": "shadow_read_only",
        "used_for_ranking": False,
        "used_for_thresholds": False,
        "used_for_tasks": False,
        "deal_readiness": serialize_readiness(readiness),
    }


def _hot_list_readiness_shadow(
    db: Session,
    *,
    conversation: DBConversation,
    score: HotListScore,
) -> dict:
    profile = (
        db.query(DBBrokerageBuyerProfile)
        .filter(
            DBBrokerageBuyerProfile.brokerage_id == conversation.brokerage_id,
            DBBrokerageBuyerProfile.buyer_phone == conversation.buyer_phone,
        )
        .first()
    )
    fields = effective_fields(db, profile) if profile else {}
    return build_hot_list_readiness_shadow(
        effective_buyer_fields=fields,
        conversation=conversation,
        score=score,
    )


def _hot_task_key(brokerage_id: str, conversation_id: str, next_action: str) -> str:
    return f"morning_hot_list:{brokerage_id}:{conversation_id}:{next_action}"


def upsert_assignment_from_score(
    db: Session,
    conversation: DBConversation,
    score: HotListScore,
) -> DBLeadAssignment:
    assignment = get_or_create_lead_assignment(db, conversation)
    assignment.signal = score.signal
    assignment.urgency_score = score.urgency_score
    assignment.next_action = score.next_action
    assignment.next_action_reason = score.next_action_reason
    assignment.due_at = score.due_at
    assignment.last_buyer_message_at = score.last_buyer_message_at
    assignment.assigned_agent_id = conversation.assigned_agent_id
    if assignment.status in {"new", "active", "viewing", "offer"}:
        assignment.status = score.status
    metadata = dict(assignment.metadata_json or {})
    metadata.update({
        "hot_list": {
            "latest_message_at": score.latest_message_at.isoformat() if score.latest_message_at else None,
            "buyer_message_count": score.buyer_message_count,
            "stale": score.stale,
            "readiness_shadow": _hot_list_readiness_shadow(
                db,
                conversation=conversation,
                score=score,
            ),
        }
    })
    assignment.metadata_json = metadata
    assignment.updated_at = datetime.utcnow()
    db.add(assignment)
    return assignment


def upsert_task_from_score(
    db: Session,
    conversation: DBConversation,
    assignment: DBLeadAssignment,
    score: HotListScore,
) -> DBLeadTask:
    key = _hot_task_key(conversation.brokerage_id, conversation.conversation_id, score.next_action)
    task = db.query(DBLeadTask).filter(DBLeadTask.task_key == key).first()
    now = datetime.utcnow()
    if not task:
        task = DBLeadTask(
            task_key=key,
            brokerage_id=conversation.brokerage_id,
            conversation_id=conversation.conversation_id,
            listing_id=conversation.listing_id,
            buyer_phone=conversation.buyer_phone,
            assigned_agent_id=assignment.assigned_agent_id,
            task_type=score.task_type,
            title=score.task_title,
            description=score.task_description,
            status="open",
            priority=score.task_priority,
            source="morning_hot_list",
            due_at=score.due_at,
            metadata_json={"signal": score.signal, "next_action": score.next_action},
        )
        db.add(task)
    elif task.status in {"open", "in_progress"}:
        task.assigned_agent_id = assignment.assigned_agent_id
        task.task_type = score.task_type
        task.title = score.task_title
        task.description = score.task_description
        task.priority = score.task_priority
        task.due_at = score.due_at
        task.metadata_json = {"signal": score.signal, "next_action": score.next_action}
        task.updated_at = now

    (
        db.query(DBLeadTask)
        .filter(
            DBLeadTask.brokerage_id == conversation.brokerage_id,
            DBLeadTask.conversation_id == conversation.conversation_id,
            DBLeadTask.source == "morning_hot_list",
            DBLeadTask.status.in_(["open", "in_progress"]),
            DBLeadTask.task_key != key,
        )
        .update({"status": "cancelled", "updated_at": now}, synchronize_session=False)
    )
    return task


def _active_follow_up_draft(
    db: Session,
    *,
    brokerage_id: str,
    conversation_id: str,
) -> Optional[DBDraftReply]:
    return (
        db.query(DBDraftReply)
        .filter(
            DBDraftReply.brokerage_id == brokerage_id,
            DBDraftReply.conversation_id == conversation_id,
            DBDraftReply.intent == "follow_up",
            DBDraftReply.status.in_(["draft", "edited"]),
        )
        .order_by(DBDraftReply.created_at.desc())
        .first()
    )


def draft_follow_up_text(conversation: DBConversation) -> str:
    buyer = conversation.buyer_name or "there"
    listing = _listing_name(conversation)
    if conversation.detected_budget:
        return (
            f"Hi {buyer}, just checking if you're still considering {listing}. "
            "I can send updated availability or suggest a better fit around your budget."
        )
    return (
        f"Hi {buyer}, just checking if {listing} is still of interest. "
        "I can send the latest availability or help compare it with another option."
    )


def ensure_follow_up_draft(
    db: Session,
    conversation: DBConversation,
    *,
    agent_user_id: Optional[str],
    score: HotListScore,
) -> Optional[DBDraftReply]:
    # Live takeover (DAL-158): draft generation is suppressed while the
    # conversation is agent-controlled.
    from app.core.conversation_takeover import is_agent_controlled

    if is_agent_controlled(conversation):
        return None
    if not score.stale or score.next_action not in {"follow_up", "call_now", "clarify_financing"}:
        return None
    existing = _active_follow_up_draft(
        db,
        brokerage_id=conversation.brokerage_id,
        conversation_id=conversation.conversation_id,
    )
    if existing:
        return existing
    draft = DBDraftReply(
        brokerage_id=conversation.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=conversation.listing_id,
        buyer_phone=conversation.buyer_phone,
        agent_user_id=agent_user_id or conversation.assigned_agent_id,
        intent="follow_up",
        draft_text=draft_follow_up_text(conversation),
        source="morning_hot_list",
        status="draft",
        metadata_json={
            "created_from": "morning_hot_list",
            "signal": score.signal,
            "urgency_score": score.urgency_score,
        },
    )
    db.add(draft)
    return draft


def refresh_morning_hot_list(
    db: Session,
    *,
    brokerage_id: str,
    user_id: Optional[str] = None,
    role: str = "agent",
    limit: int = 50,
    now: Optional[datetime] = None,
    create_follow_up_drafts: bool = True,
) -> list[DBLeadAssignment]:
    now = now or datetime.utcnow()
    conversations = (
        db.query(DBConversation)
        .filter(DBConversation.brokerage_id == brokerage_id)
        .order_by(DBConversation.updated_at.desc())
        .limit(limit)
        .all()
    )
    assignments: list[DBLeadAssignment] = []
    for conversation in conversations:
        if user_id and not can_view_conversation(
            db,
            conversation,
            user_id=user_id,
            brokerage_id=brokerage_id,
            role=role,
        ):
            continue
        score = score_conversation(db, conversation, now=now)
        assignment = upsert_assignment_from_score(db, conversation, score)
        if assignment.status in ACTIVE_ASSIGNMENT_STATUSES:
            upsert_task_from_score(db, conversation, assignment, score)
            if create_follow_up_drafts:
                ensure_follow_up_draft(
                    db,
                    conversation,
                    agent_user_id=user_id,
                    score=score,
                )
        assignments.append(assignment)
    safe_commit(db)
    for assignment in assignments:
        db.refresh(assignment)
    assignments.sort(key=lambda row: (row.urgency_score or 0, row.updated_at), reverse=True)
    return assignments


def _brokerage_timezone(brokerage: Optional[DBBrokerage]) -> str:
    settings = brokerage.settings if brokerage and isinstance(brokerage.settings, dict) else {}
    return str(settings.get("timezone") or settings.get("brokerage_timezone") or "Asia/Dubai")


def latest_hotlist_refresh_run(
    db: Session,
    *,
    brokerage_id: str,
) -> Optional[DBHotlistRefreshRun]:
    return (
        db.query(DBHotlistRefreshRun)
        .filter(DBHotlistRefreshRun.brokerage_id == brokerage_id)
        .order_by(DBHotlistRefreshRun.started_at.desc())
        .first()
    )


def refresh_hotlist_with_run(
    db: Session,
    *,
    brokerage_id: str,
    requested_by_user_id: Optional[str] = None,
    role: str = "owner",
    trigger: str = "manual",
    now: Optional[datetime] = None,
    limit: int = 100,
) -> DBHotlistRefreshRun:
    now = now or datetime.utcnow()
    brokerage = db.get(DBBrokerage, brokerage_id)
    timezone = _brokerage_timezone(brokerage)
    run = DBHotlistRefreshRun(
        brokerage_id=brokerage_id,
        requested_by_user_id=requested_by_user_id,
        trigger=trigger,
        status="running",
        brokerage_timezone=timezone,
        refresh_date=now.date().isoformat(),
        started_at=now,
        metadata_json={"requested_limit": limit},
    )
    db.add(run)
    safe_commit(db)
    db.refresh(run)

    try:
        assignments = refresh_morning_hot_list(
            db,
            brokerage_id=brokerage_id,
            user_id=requested_by_user_id if trigger == "manual" else None,
            role=role,
            limit=limit,
            now=now,
        )
        task_count = (
            db.query(DBLeadTask)
            .filter(
                DBLeadTask.brokerage_id == brokerage_id,
                DBLeadTask.source == "morning_hot_list",
                DBLeadTask.status.in_(["open", "in_progress"]),
            )
            .count()
        )
        draft_count = (
            db.query(DBDraftReply)
            .filter(
                DBDraftReply.brokerage_id == brokerage_id,
                DBDraftReply.source == "morning_hot_list",
                DBDraftReply.status.in_(["draft", "edited", "snoozed"]),
            )
            .count()
        )
        run.status = "complete"
        run.assignment_count = len(assignments)
        run.task_count = task_count
        run.draft_count = draft_count
        run.completed_at = datetime.utcnow()
        run.metadata_json = {
            **(run.metadata_json or {}),
            "assignment_ids": [assignment.assignment_id for assignment in assignments],
        }
        safe_commit(db)
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.completed_at = datetime.utcnow()
        safe_commit(db)
        raise
    db.refresh(run)
    return run


def run_scheduled_hotlist_refresh(
    db: Session,
    *,
    now: Optional[datetime] = None,
    limit: int = 100,
) -> list[DBHotlistRefreshRun]:
    now = now or datetime.utcnow()
    brokerages = (
        db.query(DBBrokerage)
        .filter(DBBrokerage.status == "active")
        .order_by(DBBrokerage.created_at.asc())
        .all()
    )
    runs: list[DBHotlistRefreshRun] = []
    for brokerage in brokerages:
        runs.append(
            refresh_hotlist_with_run(
                db,
                brokerage_id=brokerage.brokerage_id,
                trigger="scheduled",
                role="owner",
                now=now,
                limit=limit,
            )
        )
        # DAL-162 event #13: the morning digest anchors on the scheduled
        # refresh; queued digest items, pending drafts, and stale takeovers
        # ride along, one message per agent.
        try:
            from app.core.agent_notifications import send_morning_digest

            agent_ids = {
                row.assigned_agent_id
                for row in db.query(DBLeadAssignment.assigned_agent_id)
                .filter(
                    DBLeadAssignment.brokerage_id == brokerage.brokerage_id,
                    DBLeadAssignment.assigned_agent_id.isnot(None),
                )
                .distinct()
                .all()
            }
            for agent_user_id in agent_ids:
                send_morning_digest(
                    db,
                    brokerage=brokerage,
                    agent_user_id=agent_user_id,
                    now=now,
                )
        except Exception:  # pragma: no cover — digest must never fail the refresh
            logger.warning(
                "Morning digest failed for brokerage %s", brokerage.brokerage_id, exc_info=True
            )
    # DAL-163: review-only nudge drafts for first-touch leads silent for 48h.
    try:
        from app.core.lead_ingest import create_first_touch_nudge_drafts

        create_first_touch_nudge_drafts(db, now=now)
    except Exception:  # pragma: no cover
        logger.warning("First-touch nudge draft job failed", exc_info=True)
    return runs
