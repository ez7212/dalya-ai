"""
Agent dashboard API.

This endpoint returns a denormalized contract for the current agent workspace
from brokerage-scoped rows.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased, joinedload

from app.core.auth import CurrentUser, get_current_user
from app.core.brokerage_access import (
    can_view_conversation,
    capture_requested_brokerage_context,
    current_requested_brokerage_id,
    is_buyer_suppressed,
    record_compliance_event,
    resolve_request_brokerage_context,
)
from app.core.buyer_profiles import effective_fields
from app.core.deal_readiness import compute_readiness, fields_from_effective_fields, serialize_readiness
from app.core.hot_list import (
    latest_hotlist_refresh_run,
    refresh_hotlist_with_run,
    refresh_morning_hot_list,
)
from app.db.session import get_db, safe_commit
from app.models.db_models import (
    DBAIDraft,
    DBAgentMessageRoute,
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageBuyerProfile,
    DBBrokerageMember,
    DBBuyerSuppression,
    DBCampaign,
    DBCampaignRecipient,
    DBCampaignUpload,
    DBConversation,
    DBDraftReply,
    DBLeadAction,
    DBLeadAssignment,
    DBLeadTask,
    DBMarketingEvent,
    DBMarketingPage,
    DBMessage,
    DBEscalationThread,
    DBEscalationThreadQuestion,
    DBListing,
    DBOfferRecord,
    DBOwnerLead,
    DBOutreachDraft,
    DBViewing,
)

router = APIRouter(dependencies=[Depends(capture_requested_brokerage_context)])

TERMINAL_ESCALATION_STATES = {"resolved", "timed_out", "opt_out_closed"}


class AgentDashboardContext(BaseModel):
    brokerage_id: str
    brokerage_name: Optional[str] = None
    user_id: str
    role: str
    display_name: Optional[str] = None


class SnoozeTaskRequest(BaseModel):
    snoozed_until: Optional[datetime] = None
    minutes: Optional[int] = None
    reason: Optional[str] = None


class ResolveEscalationRequest(BaseModel):
    reason: str = "manual"
    note: Optional[str] = None


class EscalationReplyRequest(BaseModel):
    body: str
    send_to_buyer: bool = True


class DraftUpdateRequest(BaseModel):
    body: str


class DraftSendRequest(BaseModel):
    body: Optional[str] = None


class DraftRejectRequest(BaseModel):
    reason: Optional[str] = None


class DraftSnoozeRequest(BaseModel):
    snoozed_until: Optional[datetime] = None
    minutes: Optional[int] = None
    reason: Optional[str] = None


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _agent_context(user: CurrentUser, db: Session) -> AgentDashboardContext:
    context = resolve_request_brokerage_context(
        db,
        user,
        current_requested_brokerage_id(),
    )
    brokerage = db.get(DBBrokerage, context.brokerage_id)
    profile = (
        db.query(DBAgentProfile)
        .filter(
            DBAgentProfile.brokerage_id == context.brokerage_id,
            DBAgentProfile.user_id == user.id,
        )
        .first()
    )
    member = db.get(DBBrokerageMember, context.membership_id) if context.membership_id else None
    return AgentDashboardContext(
        brokerage_id=context.brokerage_id,
        brokerage_name=brokerage.name if brokerage else None,
        user_id=context.user_id,
        role=context.role or "agent",
        display_name=profile.display_name if profile else (member.display_name if member else user.email),
    )


def _conversation_is_visible(db: Session, ctx: AgentDashboardContext, conversation_id: Optional[str]) -> bool:
    if not conversation_id:
        return True
    conv = db.get(DBConversation, conversation_id)
    if not conv:
        return True
    return can_view_conversation(
        db,
        conv,
        user_id=ctx.user_id,
        brokerage_id=ctx.brokerage_id,
        role=ctx.role,
    )


def _get_visible_reply_draft_or_404(
    db: Session,
    *,
    draft_id: str,
    ctx: AgentDashboardContext,
) -> DBDraftReply:
    draft = db.get(DBDraftReply, draft_id)
    if (
        not draft
        or draft.brokerage_id != ctx.brokerage_id
        or not _conversation_is_visible(db, ctx, draft.conversation_id)
    ):
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


def _draft_category_key(draft: DBDraftReply) -> str:
    metadata = draft.metadata_json or {}
    intent = draft.intent or "general_nurture"
    if metadata.get("created_from") == "morning_hot_list" or intent == "follow_up":
        return "stale_buyer"
    if intent in {"viewing_slots", "viewing_follow_up"}:
        return "viewing_follow_up"
    if intent in {"offer_ack", "offer_follow_up"}:
        return "offer_follow_up"
    if intent in {"budget_clarification", "financing_follow_up"}:
        return "financing_follow_up"
    if intent == "urgent":
        return "urgent"
    if intent == "today":
        return "today"
    return "general_nurture"


def _metadata_datetime(metadata: dict, key: str) -> Optional[datetime]:
    value = metadata.get(key)
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _serialize_reply_draft(db: Session, draft: DBDraftReply) -> dict:
    conversation = db.get(DBConversation, draft.conversation_id)
    if not conversation or not conversation.brokerage_id:
        conversation = None
    listing = db.get(DBListing, draft.listing_id) if draft.listing_id else None
    if not listing or not listing.brokerage_id:
        listing = None
    spa = (listing.spa_data or {}) if listing else {}
    metadata = draft.metadata_json or {}
    return {
        "draft_id": draft.draft_id,
        "conversation_id": draft.conversation_id,
        "listing_id": draft.listing_id,
        "buyer_phone": draft.buyer_phone,
        "buyer_name": conversation.buyer_name if conversation else None,
        "listing_name": spa.get("project") or spa.get("building_or_project") or "Listing",
        "unit_number": spa.get("unit_number"),
        "intent": draft.intent,
        "category": _draft_category_key(draft),
        "body": draft.draft_text,
        "source": draft.source,
        "status": draft.status,
        "snoozed_until": metadata.get("snoozed_until"),
        "created_at": _iso(draft.created_at),
        "updated_at": _iso(draft.updated_at),
        "sent_at": _iso(draft.sent_at),
        "metadata": metadata,
    }


def _hotlist_refresh_payload(db: Session, ctx: AgentDashboardContext) -> dict:
    run = latest_hotlist_refresh_run(db, brokerage_id=ctx.brokerage_id)
    if not run:
        return {
            "status": "not_run",
            "last_refresh_at": None,
            "completed_at": None,
            "trigger": None,
            "assignment_count": 0,
            "task_count": 0,
            "draft_count": 0,
            "error": None,
        }
    return {
        "run_id": run.run_id,
        "status": run.status,
        "last_refresh_at": _iso(run.started_at),
        "completed_at": _iso(run.completed_at),
        "trigger": run.trigger,
        "brokerage_timezone": run.brokerage_timezone,
        "refresh_date": run.refresh_date,
        "assignment_count": run.assignment_count,
        "task_count": run.task_count,
        "draft_count": run.draft_count,
        "error": run.error,
    }


def _latest_messages_by_conversation(db: Session, conversation_ids: list[str]) -> dict[str, DBMessage]:
    if not conversation_ids:
        return {}

    ranked_messages = (
        db.query(
            DBMessage,
            func.row_number()
            .over(
                partition_by=DBMessage.conversation_id,
                order_by=DBMessage.timestamp.desc(),
            )
            .label("message_rank"),
        )
        .filter(DBMessage.conversation_id.in_(conversation_ids))
        .subquery()
    )
    latest_message = aliased(DBMessage, ranked_messages)
    latest_rows = (
        db.query(latest_message)
        .filter(ranked_messages.c.message_rank == 1)
        .all()
    )
    return {message.conversation_id: message for message in latest_rows}


def _label_signal(signal: Optional[str]) -> str:
    labels = {
        "firm_offer": "Firm offer",
        "ready_to_view": "Ready to view",
        "budget_matched": "Budget matched",
        "needs_financing": "Needs financing",
        "cold": "Follow-up",
    }
    return labels.get(signal or "", signal or "Follow-up")


def _label_next_action(next_action: Optional[str]) -> str:
    labels = {
        "call_now": "Call now",
        "send_whatsapp": "Draft WhatsApp",
        "book_viewing": "Book viewing",
        "follow_up": "Follow up",
        "review_offer": "Review offer",
        "clarify_financing": "Clarify financing",
    }
    return labels.get(next_action or "", next_action or "Follow up")


def _listing_payload(assignment: DBLeadAssignment) -> dict:
    listing = assignment.conversation.listing if assignment.conversation else None
    spa = (listing.spa_data or {}) if listing else {}
    return {
        "listing_id": assignment.listing_id,
        "project": spa.get("project", "Unknown listing"),
        "unit_number": spa.get("unit_number"),
        "unit_label": spa.get("unit_type") or spa.get("bedrooms"),
        "asking_price_aed": listing.seller_asking_price if listing else None,
        "developer": spa.get("developer"),
        "noc_status": spa.get("noc_status") or spa.get("noc"),
    }


def _summary_text(summary: dict) -> str:
    if not isinstance(summary, dict):
        return ""
    values: list[str] = []
    for key in ("summary", "one_line", "key_question", "next_step_hint", "interest_level"):
        value = summary.get(key)
        if value:
            values.append(str(value))
    topics = summary.get("topics")
    if isinstance(topics, list):
        values.extend(str(topic) for topic in topics if topic)
    return " ".join(values).lower()


def _readiness_payload(
    db: Session,
    *,
    profile: Optional[DBBrokerageBuyerProfile],
    conversation: DBConversation,
    listing: Optional[DBListing] = None,
    latest_message: Optional[DBMessage] = None,
    summary: Optional[dict] = None,
    offer_count: int = 0,
    open_thread_count: int = 0,
) -> dict:
    qualification = effective_fields(db, profile) if profile else {}
    fields = fields_from_effective_fields(
        qualification,
        fallback_budget_aed=conversation.detected_budget,
    )
    text = " ".join(
        value
        for value in (
            latest_message.content if latest_message else "",
            _summary_text(summary or {}),
        )
        if value
    ).lower()
    conversation_ctx = {
        "viewing_intent": bool(
            (latest_message and latest_message.intent == "viewing_request")
            or any(term in text for term in ("viewing", "view the", "see it", "tour"))
        ),
        "offer_intent": bool(
            offer_count
            or (
                conversation.escalation_reason
                and conversation.escalation_reason.startswith("offer:")
            )
        ),
        "responsive": bool(latest_message and latest_message.role == "user"),
        "urgent": any(term in text for term in ("urgent", "asap", "serious", "high intent")),
        "agent_takeover": int(open_thread_count or 0) > 0,
    }
    listing_ctx = (
        {
            "listing_id": listing.listing_id,
            "property_type": listing.property_type,
        }
        if listing
        else (
            {"listing_id": conversation.listing_id}
            if conversation.listing_id
            else None
        )
    )
    return serialize_readiness(
        compute_readiness(
            fields,
            conversation_ctx=conversation_ctx,
            listing_ctx=listing_ctx,
        )
    )


def _buyer_payload(assignment: DBLeadAssignment) -> dict:
    conv = assignment.conversation
    return {
        "name": conv.buyer_name if conv else None,
        "phone": assignment.buyer_phone,
        "budget_aed": conv.detected_budget if conv else None,
        "stage": assignment.status,
    }


def _hot_leads(db: Session, ctx: AgentDashboardContext) -> list[dict]:
    assignments = (
        db.query(DBLeadAssignment)
        .options(joinedload(DBLeadAssignment.conversation).joinedload(DBConversation.listing))
        .filter(
            DBLeadAssignment.brokerage_id == ctx.brokerage_id,
            DBLeadAssignment.status.notin_(["won", "lost", "archived"]),
        )
        .order_by(DBLeadAssignment.urgency_score.desc(), DBLeadAssignment.updated_at.desc())
        .limit(25)
        .all()
    )

    latest_messages = _latest_messages_by_conversation(
        db,
        [assignment.conversation_id for assignment in assignments],
    )
    leads = []
    for assignment in assignments:
        if assignment.conversation_id and not _conversation_is_visible(db, ctx, assignment.conversation_id):
            continue
        latest = latest_messages.get(assignment.conversation_id)
        metadata = assignment.metadata_json or {}
        hot_list_metadata = metadata.get("hot_list") if isinstance(metadata, dict) else {}
        leads.append({
            "id": assignment.assignment_id,
            "conversation_id": assignment.conversation_id,
            "buyer": _buyer_payload(assignment),
            "listing": _listing_payload(assignment),
            "signal": _label_signal(assignment.signal),
            "signal_key": assignment.signal,
            "next_action": _label_next_action(assignment.next_action),
            "next_action_key": assignment.next_action,
            "reason": assignment.next_action_reason,
            "urgency_score": assignment.urgency_score,
            "last_message": latest.content if latest else None,
            "last_message_at": _iso(latest.timestamp if latest else None),
            "last_buyer_message_at": _iso(assignment.last_buyer_message_at),
            "due_at": _iso(assignment.due_at),
            "status": assignment.status,
            "readiness_shadow": (hot_list_metadata or {}).get("readiness_shadow"),
        })
    return leads


def _conversation_inbox(db: Session, ctx: AgentDashboardContext) -> list[dict]:
    rows = (
        db.query(DBConversation)
        .options(joinedload(DBConversation.listing))
        .filter(DBConversation.brokerage_id == ctx.brokerage_id)
        .order_by(DBConversation.updated_at.desc().nullslast(), DBConversation.created_at.desc())
        .limit(100)
        .all()
    )
    rows = [
        row for row in rows
        if can_view_conversation(
            db,
            row,
            user_id=ctx.user_id,
            brokerage_id=ctx.brokerage_id,
            role=ctx.role,
        )
    ]
    conversation_ids = [row.conversation_id for row in rows]
    buyer_profiles = {
        profile.buyer_phone: profile
        for profile in (
            db.query(DBBrokerageBuyerProfile)
            .filter(
                DBBrokerageBuyerProfile.brokerage_id == ctx.brokerage_id,
                DBBrokerageBuyerProfile.buyer_phone.in_([row.buyer_phone for row in rows if row.buyer_phone]),
            )
            .all()
        )
    } if rows else {}
    latest_messages = _latest_messages_by_conversation(db, conversation_ids)
    message_counts = dict(
        db.query(DBMessage.conversation_id, func.count(DBMessage.id))
        .filter(DBMessage.conversation_id.in_(conversation_ids))
        .group_by(DBMessage.conversation_id)
        .all()
    ) if conversation_ids else {}
    offer_counts = dict(
        db.query(DBOfferRecord.conversation_id, func.count(DBOfferRecord.offer_id))
        .filter(DBOfferRecord.conversation_id.in_(conversation_ids))
        .group_by(DBOfferRecord.conversation_id)
        .all()
    ) if conversation_ids else {}
    open_thread_counts = dict(
        db.query(DBEscalationThread.conversation_id, func.count(DBEscalationThread.thread_id))
        .filter(
            DBEscalationThread.conversation_id.in_(conversation_ids),
            DBEscalationThread.state.in_(["debouncing", "open", "updated"]),
        )
        .group_by(DBEscalationThread.conversation_id)
        .all()
    ) if conversation_ids else {}
    terminal_thread_completed_at = dict(
        db.query(
            DBEscalationThread.conversation_id,
            func.max(func.coalesce(
                DBEscalationThread.closed_at,
                DBEscalationThread.updated_at,
                DBEscalationThread.last_buyer_message_at,
            )),
        )
        .filter(
            DBEscalationThread.conversation_id.in_(conversation_ids),
            DBEscalationThread.state.in_(TERMINAL_ESCALATION_STATES),
        )
        .group_by(DBEscalationThread.conversation_id)
        .all()
    ) if conversation_ids else {}

    # needs_reply signal (DAL-170E5): derived from the latest inbound (buyer)
    # vs latest outbound (agent/bot) message timestamps, with no schema change.
    # A thread needs a reply when the buyer's last message is newer than any
    # agent/bot response, has not been covered by a terminal escalation state,
    # and the buyer has not opted out.
    last_buyer_message_at = dict(
        db.query(DBMessage.conversation_id, func.max(DBMessage.timestamp))
        .filter(
            DBMessage.conversation_id.in_(conversation_ids),
            DBMessage.role == "user",
        )
        .group_by(DBMessage.conversation_id)
        .all()
    ) if conversation_ids else {}
    last_agent_response_at = dict(
        db.query(DBMessage.conversation_id, func.max(DBMessage.timestamp))
        .filter(
            DBMessage.conversation_id.in_(conversation_ids),
            DBMessage.role.in_(["assistant", "agent", "owner", "platform_admin"]),
        )
        .group_by(DBMessage.conversation_id)
        .all()
    ) if conversation_ids else {}
    pending_draft_convs = {
        row[0]
        for row in (
            db.query(DBDraftReply.conversation_id)
            .filter(
                DBDraftReply.conversation_id.in_(conversation_ids),
                DBDraftReply.status.in_(["draft", "edited"]),
            )
            .distinct()
            .all()
        )
    } if conversation_ids else set()
    pending_draft_convs |= {
        row[0]
        for row in (
            db.query(DBAIDraft.conversation_id)
            .filter(
                DBAIDraft.conversation_id.in_(conversation_ids),
                DBAIDraft.status == "draft",
            )
            .distinct()
            .all()
        )
    } if conversation_ids else set()
    suppressed_phones = {
        row[0]
        for row in (
            db.query(DBBuyerSuppression.buyer_phone)
            .filter(
                DBBuyerSuppression.brokerage_id == ctx.brokerage_id,
                DBBuyerSuppression.active.is_(True),
            )
            .all()
        )
    }

    items = []
    for conv in rows:
        listing = conv.listing
        spa = (listing.spa_data or {}) if listing else {}
        latest = latest_messages.get(conv.conversation_id)
        summary = conv.ai_summary or {}
        buyer_at = last_buyer_message_at.get(conv.conversation_id)
        agent_at = last_agent_response_at.get(conv.conversation_id)
        has_pending_draft = conv.conversation_id in pending_draft_convs
        is_suppressed = bool(conv.buyer_phone) and conv.buyer_phone in suppressed_phones
        terminal_at = terminal_thread_completed_at.get(conv.conversation_id)
        terminal_covers_latest_buyer = bool(
            buyer_at is not None
            and terminal_at is not None
            and terminal_at >= buyer_at
        )
        needs_reply = bool(
            buyer_at is not None
            and (agent_at is None or buyer_at > agent_at)
            and not terminal_covers_latest_buyer
            and not is_suppressed
        )
        if not needs_reply:
            needs_reply_reason = None
        elif has_pending_draft:
            needs_reply_reason = "draft_ready"
        elif int(open_thread_counts.get(conv.conversation_id, 0)) > 0:
            needs_reply_reason = "escalation_open"
        else:
            needs_reply_reason = "buyer_awaiting"
        items.append({
            "conversation_id": conv.conversation_id,
            "buyer": {
                "name": conv.buyer_name,
                "phone": conv.buyer_phone,
                "budget_aed": conv.detected_budget,
            },
            "listing": {
                "listing_id": conv.listing_id,
                "project": spa.get("project") or (listing.community if listing else None) or "Listing",
                "unit_number": spa.get("unit_number"),
                "unit_label": spa.get("unit_type") or spa.get("bedrooms"),
                "asking_price_aed": listing.seller_asking_price if listing else None,
            },
            "summary": summary.get("summary") or summary.get("one_line") or summary.get("key_question"),
            "next_step_hint": summary.get("next_step_hint"),
            "interest_level": summary.get("interest_level"),
            "last_message": latest.content if latest else None,
            "last_message_role": latest.role if latest else None,
            "last_message_at": _iso(latest.timestamp if latest else None),
            "message_count": int(message_counts.get(conv.conversation_id, 0)),
            "offer_count": int(offer_counts.get(conv.conversation_id, 0)),
            "open_escalation_count": int(open_thread_counts.get(conv.conversation_id, 0)),
            "deal_readiness": _readiness_payload(
                db,
                profile=buyer_profiles.get(conv.buyer_phone),
                conversation=conv,
                listing=listing,
                latest_message=latest,
                summary=summary,
                offer_count=int(offer_counts.get(conv.conversation_id, 0)),
                open_thread_count=int(open_thread_counts.get(conv.conversation_id, 0)),
            ),
            "needs_reply": needs_reply,
            "needs_reply_reason": needs_reply_reason,
            "has_pending_draft": has_pending_draft,
            "last_buyer_message_at": _iso(buyer_at),
            "last_agent_response_at": _iso(agent_at),
            "created_at": _iso(conv.created_at),
            "updated_at": _iso(conv.updated_at),
        })
    # Rank needs_reply threads first; preserve the existing recency order within
    # each group (Python's sort is stable).
    items.sort(key=lambda item: 0 if item["needs_reply"] else 1)
    return items


def _tasks(db: Session, ctx: AgentDashboardContext) -> list[dict]:
    now = datetime.utcnow()
    rows = (
        db.query(DBLeadTask)
        .filter(
            DBLeadTask.brokerage_id == ctx.brokerage_id,
            DBLeadTask.status.in_(["open", "in_progress"]),
            or_(DBLeadTask.snoozed_until.is_(None), DBLeadTask.snoozed_until <= now),
        )
        .order_by(DBLeadTask.due_at.asc().nullslast(), DBLeadTask.created_at.desc())
        .limit(30)
        .all()
    )
    rows = [task for task in rows if _conversation_is_visible(db, ctx, task.conversation_id)]
    return [
        {
            "task_id": task.task_id,
            "task_key": task.task_key,
            "type": task.task_type,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "source": task.source,
            "conversation_id": task.conversation_id,
            "listing_id": task.listing_id,
            "buyer_phone": task.buyer_phone,
            "assigned_agent_id": task.assigned_agent_id,
            "due_at": _iso(task.due_at),
            "snoozed_until": _iso(task.snoozed_until),
            "created_at": _iso(task.created_at),
            "metadata": task.metadata_json or {},
        }
        for task in rows
    ]


def _viewings(db: Session, ctx: AgentDashboardContext) -> list[dict]:
    rows = (
        db.query(DBViewing)
        .filter(
            DBViewing.brokerage_id == ctx.brokerage_id,
            DBViewing.status.in_(["proposed", "confirmed"]),
        )
        .order_by(DBViewing.scheduled_for.asc().nullslast(), DBViewing.created_at.desc())
        .limit(15)
        .all()
    )
    rows = [viewing for viewing in rows if _conversation_is_visible(db, ctx, viewing.conversation_id)]
    return [
        {
            "viewing_id": viewing.viewing_id,
            "conversation_id": viewing.conversation_id,
            "listing_id": viewing.listing_id,
            "buyer_phone": viewing.buyer_phone,
            "agent_user_id": viewing.agent_user_id,
            "scheduled_for": _iso(viewing.scheduled_for),
            "status": viewing.status,
            "tenant_notice_required": viewing.tenant_notice_required,
            "access_notes": viewing.access_notes,
        }
        for viewing in rows
    ]


def _urgency_for_thread(thread: DBEscalationThread) -> str:
    if thread.category == "offer":
        return "critical"
    if thread.state in {"updated", "timed_out"}:
        return "high"
    if thread.category in {"legal_general", "regulatory_documents", "seller_action"}:
        return "high"
    if int(thread.question_count or 0) >= 3:
        return "high"
    return "normal"


def _latest_route_for_thread(db: Session, thread_id: str) -> Optional[DBAgentMessageRoute]:
    return (
        db.query(DBAgentMessageRoute)
        .filter(DBAgentMessageRoute.thread_id == thread_id)
        .order_by(DBAgentMessageRoute.created_at.desc())
        .first()
    )


def _questions_for_threads(db: Session, thread_ids: list[str]) -> dict[str, list[dict]]:
    if not thread_ids:
        return {}
    rows = (
        db.query(DBEscalationThreadQuestion)
        .filter(DBEscalationThreadQuestion.thread_id.in_(thread_ids))
        .order_by(DBEscalationThreadQuestion.thread_id.asc(), DBEscalationThreadQuestion.sort_order.asc())
        .all()
    )
    grouped: dict[str, list[dict]] = {}
    for question in rows:
        grouped.setdefault(question.thread_id, []).append({
            "question_id": question.question_id,
            "question_text": question.question_text,
            "category": question.category,
            "escalation_subtype": question.escalation_subtype,
            "sort_order": question.sort_order,
            "added_at": _iso(question.added_at),
            "resolved_at": _iso(question.resolved_at),
        })
    return grouped


def _listing_for_thread(db: Session, thread: DBEscalationThread) -> dict:
    listing = db.get(DBListing, thread.listing_id)
    if not listing or not listing.brokerage_id:
        listing = None
    spa = (listing.spa_data or {}) if listing else {}
    return {
        "listing_id": thread.listing_id,
        "project": spa.get("project") or spa.get("building_or_project") or "Listing",
        "unit_number": spa.get("unit_number"),
        "unit_label": spa.get("unit_type") or spa.get("bedrooms"),
        "asking_price_aed": listing.seller_asking_price if listing else None,
        "developer": spa.get("developer"),
    }


def _buyer_for_thread(db: Session, thread: DBEscalationThread) -> dict:
    conversation = db.get(DBConversation, thread.conversation_id)
    if not conversation or not conversation.brokerage_id:
        conversation = None
    return {
        "name": conversation.buyer_name if conversation else None,
        "phone": thread.buyer_phone,
        "budget_aed": conversation.detected_budget if conversation else None,
        "summary": conversation.ai_summary if conversation else None,
    }


def _serialize_escalation_thread(
    db: Session,
    thread: DBEscalationThread,
    *,
    questions: list[dict],
) -> dict:
    route = _latest_route_for_thread(db, thread.thread_id)
    latest_question = questions[-1]["question_text"] if questions else None
    from app.core.conversation_takeover import conversation_ai_mode

    conversation = db.get(DBConversation, thread.conversation_id)
    return {
        "thread_id": thread.thread_id,
        "conversation_id": thread.conversation_id,
        "ai_mode": conversation_ai_mode(conversation),
        "listing_id": thread.listing_id,
        "buyer_phone": thread.buyer_phone,
        "agent_user_id": thread.agent_user_id,
        "agent_phone": thread.agent_phone,
        "category": thread.category,
        "state": thread.state,
        "urgency": _urgency_for_thread(thread),
        "escalation_type": thread.escalation_type,
        "escalation_subtype": thread.escalation_subtype,
        "envelope_token": thread.envelope_token,
        "latest_route_id": route.route_id if route else None,
        "latest_route_expires_at": _iso(route.expires_at if route else None),
        "latest_route_consumed_at": _iso(route.consumed_at if route else None),
        "question_count": thread.question_count or len(questions),
        "questions": questions,
        "latest_question": latest_question,
        "buyer": _buyer_for_thread(db, thread),
        "listing": _listing_for_thread(db, thread),
        "opened_at": _iso(thread.opened_at),
        "alerted_at": _iso(thread.alerted_at),
        "last_buyer_message_at": _iso(thread.last_buyer_message_at),
        "last_update_sent_at": _iso(thread.last_update_sent_at),
        "debounce_until": _iso(thread.debounce_until),
        "closed_at": _iso(thread.closed_at),
        "close_reason": thread.close_reason,
    }


def _escalation_threads(
    db: Session,
    ctx: AgentDashboardContext,
    *,
    states: Optional[set[str]] = None,
    category: Optional[str] = None,
    agent_user_id: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    query = (
        db.query(DBEscalationThread)
        .filter(DBEscalationThread.brokerage_id == ctx.brokerage_id)
    )
    if states:
        query = query.filter(DBEscalationThread.state.in_(states))
    if category:
        query = query.filter(DBEscalationThread.category == category)
    if agent_user_id:
        query = query.filter(DBEscalationThread.agent_user_id == agent_user_id)

    rows = (
        query
        .order_by(DBEscalationThread.updated_at.desc(), DBEscalationThread.opened_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    visible = [
        thread for thread in rows
        if _conversation_is_visible(db, ctx, thread.conversation_id)
    ]
    grouped_questions = _questions_for_threads(db, [thread.thread_id for thread in visible])
    return [
        _serialize_escalation_thread(
            db,
            thread,
            questions=grouped_questions.get(thread.thread_id, []),
        )
        for thread in visible
    ]


def _escalation_counts(threads: list[dict]) -> dict:
    counts = {
        "total": len(threads),
        "open": 0,
        "updated": 0,
        "debouncing": 0,
        "timed_out": 0,
        "resolved": 0,
        "critical": 0,
        "high": 0,
        "normal": 0,
        "categories": {},
    }
    for thread in threads:
        state = thread.get("state") or "open"
        urgency = thread.get("urgency") or "normal"
        category = thread.get("category") or "other"
        if state in counts:
            counts[state] += 1
        if urgency in counts:
            counts[urgency] += 1
        counts["categories"][category] = counts["categories"].get(category, 0) + 1
    return counts


def _drafts(db: Session, ctx: AgentDashboardContext) -> dict:
    reply_rows = (
        db.query(DBDraftReply)
        .filter(DBDraftReply.brokerage_id == ctx.brokerage_id, DBDraftReply.status == "draft")
        .order_by(DBDraftReply.created_at.desc())
        .limit(10)
        .all()
    )
    ai_rows = (
        db.query(DBAIDraft)
        .filter(DBAIDraft.brokerage_id == ctx.brokerage_id, DBAIDraft.status == "draft")
        .order_by(DBAIDraft.created_at.desc())
        .limit(10)
        .all()
    )
    reply_rows = [row for row in reply_rows if _conversation_is_visible(db, ctx, row.conversation_id)]
    ai_rows = [row for row in ai_rows if _conversation_is_visible(db, ctx, row.conversation_id)]
    outreach_rows = (
        db.query(DBOutreachDraft)
        .filter(DBOutreachDraft.brokerage_id == ctx.brokerage_id, DBOutreachDraft.status == "draft")
        .order_by(DBOutreachDraft.created_at.desc())
        .limit(10)
        .all()
    )
    return {
        "reply_drafts": [
            {
                "draft_id": row.draft_id,
                "conversation_id": row.conversation_id,
                "intent": row.intent,
                "body": row.draft_text,
                "created_at": _iso(row.created_at),
            }
            for row in reply_rows
        ],
        "ai_drafts": [
            {
                "draft_id": row.draft_id,
                "draft_type": row.draft_type,
                "title": row.title,
                "body": row.body,
                "confidence_score": row.confidence_score,
                "created_at": _iso(row.created_at),
            }
            for row in ai_rows
        ],
        "outreach_drafts": [
            {
                "outreach_draft_id": row.outreach_draft_id,
                "campaign_id": row.campaign_id,
                "owner_lead_id": row.owner_lead_id,
                "channel": row.channel,
                "subject": row.subject,
                "body": row.body,
                "created_at": _iso(row.created_at),
            }
            for row in outreach_rows
        ],
    }


def _campaigns(db: Session, ctx: AgentDashboardContext) -> list[dict]:
    rows = (
        db.query(DBCampaign)
        .filter(DBCampaign.brokerage_id == ctx.brokerage_id)
        .order_by(DBCampaign.updated_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "campaign_id": campaign.campaign_id,
            "name": campaign.name,
            "campaign_type": campaign.campaign_type,
            "channel": campaign.channel,
            "status": campaign.status,
            "audience": campaign.audience or {},
            "offer": campaign.offer or {},
            "metrics": campaign.metrics or {},
            "starts_at": _iso(campaign.starts_at),
            "ends_at": _iso(campaign.ends_at),
        }
        for campaign in rows
    ]


def _campaign_uploads(db: Session, ctx: AgentDashboardContext) -> list[dict]:
    rows = (
        db.query(DBCampaignUpload)
        .filter(DBCampaignUpload.brokerage_id == ctx.brokerage_id)
        .order_by(DBCampaignUpload.created_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "upload_id": row.upload_id,
            "campaign_id": row.campaign_id,
            "file_name": row.file_name,
            "file_type": row.file_type,
            "row_count": row.row_count,
            "status": row.status,
            "parsed_summary": row.parsed_summary or {},
            "error": row.error,
            "created_at": _iso(row.created_at),
            "processed_at": _iso(row.processed_at),
        }
        for row in rows
    ]


def _campaign_recipients(db: Session, ctx: AgentDashboardContext) -> list[dict]:
    rows = (
        db.query(DBCampaignRecipient)
        .filter(DBCampaignRecipient.brokerage_id == ctx.brokerage_id)
        .order_by(DBCampaignRecipient.updated_at.desc())
        .limit(25)
        .all()
    )
    return [
        {
            "recipient_id": row.recipient_id,
            "campaign_id": row.campaign_id,
            "owner_lead_id": row.owner_lead_id,
            "recipient_key": row.recipient_key,
            "name": row.name,
            "phone": row.phone,
            "email": row.email,
            "channel": row.channel,
            "status": row.status,
            "last_message_at": _iso(row.last_message_at),
            "last_response_at": _iso(row.last_response_at),
        }
        for row in rows
    ]


def _owner_leads(db: Session, ctx: AgentDashboardContext) -> list[dict]:
    rows = (
        db.query(DBOwnerLead)
        .filter(DBOwnerLead.brokerage_id == ctx.brokerage_id)
        .order_by(DBOwnerLead.updated_at.desc())
        .limit(15)
        .all()
    )
    return [
        {
            "owner_lead_id": row.owner_lead_id,
            "campaign_id": row.campaign_id,
            "owner_name": row.owner_name,
            "owner_phone": row.owner_phone,
            "project": row.project,
            "unit_number": row.unit_number,
            "estimated_value_aed": row.estimated_value_aed,
            "intent": row.intent,
            "stage": row.stage,
            "priority": row.priority,
            "next_follow_up_at": _iso(row.next_follow_up_at),
        }
        for row in rows
    ]


def _marketing(db: Session, ctx: AgentDashboardContext) -> dict:
    pages = (
        db.query(DBMarketingPage)
        .filter(DBMarketingPage.brokerage_id == ctx.brokerage_id)
        .order_by(DBMarketingPage.updated_at.desc())
        .limit(10)
        .all()
    )
    return {
        "pages": [
            {
                "page_id": page.page_id,
                "campaign_id": page.campaign_id,
                "slug": page.slug,
                "title": page.title,
                "status": page.status,
                "url": page.url,
                "metrics": page.metrics or {},
                "published_at": _iso(page.published_at),
            }
            for page in pages
        ],
        "events_7d": (
            db.query(func.count(DBMarketingEvent.event_id))
            .filter(
                DBMarketingEvent.brokerage_id == ctx.brokerage_id,
                DBMarketingEvent.occurred_at >= datetime.utcnow() - timedelta(days=7),
            )
            .scalar()
            or 0
        ),
    }


def _metrics(db: Session, ctx: AgentDashboardContext, payload: dict) -> dict:
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    return {
        "conversations": len(payload.get("conversations", [])),
        "needs_reply": len([c for c in payload.get("conversations", []) if c.get("needs_reply")]),
        "hot_leads": len(payload["hot_leads"]),
        "open_tasks": (
            db.query(func.count(DBLeadTask.task_id))
            .filter(DBLeadTask.brokerage_id == ctx.brokerage_id, DBLeadTask.status.in_(["open", "in_progress"]))
            .scalar()
            or 0
        ),
        "viewings_today": (
            db.query(func.count(DBViewing.viewing_id))
            .filter(
                DBViewing.brokerage_id == ctx.brokerage_id,
                DBViewing.scheduled_for >= today_start,
                DBViewing.scheduled_for < today_start + timedelta(days=1),
                DBViewing.status.in_(["proposed", "confirmed", "completed"]),
            )
            .scalar()
            or 0
        ),
        "stale_leads": (
            db.query(func.count(DBLeadAssignment.assignment_id))
            .filter(
                DBLeadAssignment.brokerage_id == ctx.brokerage_id,
                DBLeadAssignment.status.in_(["new", "active", "viewing", "offer"]),
                DBLeadAssignment.last_buyer_message_at < now - timedelta(days=1),
            )
            .scalar()
            or 0
        ),
        "draft_replies": len(payload["drafts"]["reply_drafts"]) + len(payload["drafts"]["ai_drafts"]),
        "outreach_drafts": len(payload["drafts"]["outreach_drafts"]),
        "active_campaigns": len([c for c in payload["campaigns"] if c["status"] == "active"]),
        "new_owner_leads": len([lead for lead in payload["owner_leads"] if lead["stage"] == "new"]),
        "marketing_events_7d": payload["marketing"]["events_7d"],
        "open_escalations": len([
            thread for thread in payload.get("escalation_threads", [])
            if thread.get("state") in {"debouncing", "open", "updated"}
        ]),
    }


def _performance_metrics(db: Session, ctx: AgentDashboardContext) -> dict:
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    windows = [
        ("today", "Today", today_start),
        ("7d", "7 days", now - timedelta(days=7)),
        ("30d", "30 days", now - timedelta(days=30)),
    ]
    rows = [
        _performance_window(db, ctx, key=key, label=label, start=start, end=now)
        for key, label, start in windows
    ]
    return {
        "scope": "current_agent",
        "agent_user_id": ctx.user_id,
        "generated_at": _iso(now),
        "windows": rows,
        "primary": rows[0],
    }


def _performance_window(
    db: Session,
    ctx: AgentDashboardContext,
    *,
    key: str,
    label: str,
    start: datetime,
    end: datetime,
) -> dict:
    assigned_conversation_filter = (
        DBConversation.brokerage_id == ctx.brokerage_id,
        DBConversation.assigned_agent_id == ctx.user_id,
    )
    active_statuses = {"new", "active", "viewing", "offer"}
    completed_viewing_statuses = {"completed", "feedback_requested", "feedback_completed"}
    return {
        "key": key,
        "label": label,
        "start_at": _iso(start),
        "end_at": _iso(end),
        "metrics": {
            "new_buyer_conversations": (
                db.query(func.count(DBConversation.conversation_id))
                .filter(*assigned_conversation_filter, DBConversation.created_at >= start, DBConversation.created_at <= end)
                .scalar()
                or 0
            ),
            "escalations_handled": (
                db.query(func.count(DBEscalationThread.thread_id))
                .filter(
                    DBEscalationThread.brokerage_id == ctx.brokerage_id,
                    DBEscalationThread.agent_user_id == ctx.user_id,
                    DBEscalationThread.state == "resolved",
                    DBEscalationThread.closed_at >= start,
                    DBEscalationThread.closed_at <= end,
                )
                .scalar()
                or 0
            ),
            "avg_response_minutes": _average_response_minutes(db, ctx, start=start, end=end),
            "follow_ups_sent": (
                db.query(func.count(DBDraftReply.draft_id))
                .filter(
                    DBDraftReply.brokerage_id == ctx.brokerage_id,
                    DBDraftReply.agent_user_id == ctx.user_id,
                    DBDraftReply.intent == "follow_up",
                    DBDraftReply.status == "sent",
                    DBDraftReply.sent_at >= start,
                    DBDraftReply.sent_at <= end,
                )
                .scalar()
                or 0
            ),
            "viewings_proposed": (
                db.query(func.count(DBViewing.viewing_id))
                .filter(
                    DBViewing.brokerage_id == ctx.brokerage_id,
                    DBViewing.agent_user_id == ctx.user_id,
                    DBViewing.created_at >= start,
                    DBViewing.created_at <= end,
                )
                .scalar()
                or 0
            ),
            "viewings_confirmed": (
                db.query(func.count(DBViewing.viewing_id))
                .filter(
                    DBViewing.brokerage_id == ctx.brokerage_id,
                    DBViewing.agent_user_id == ctx.user_id,
                    DBViewing.scheduled_for.isnot(None),
                    DBViewing.status.in_(["confirmed", *completed_viewing_statuses]),
                    DBViewing.updated_at >= start,
                    DBViewing.updated_at <= end,
                )
                .scalar()
                or 0
            ),
            "viewings_completed": (
                db.query(func.count(DBViewing.viewing_id))
                .filter(
                    DBViewing.brokerage_id == ctx.brokerage_id,
                    DBViewing.agent_user_id == ctx.user_id,
                    DBViewing.status.in_(completed_viewing_statuses),
                    DBViewing.updated_at >= start,
                    DBViewing.updated_at <= end,
                )
                .scalar()
                or 0
            ),
            "offers_detected": (
                db.query(func.count(DBOfferRecord.offer_id))
                .join(DBConversation, DBConversation.conversation_id == DBOfferRecord.conversation_id)
                .filter(
                    DBOfferRecord.brokerage_id == ctx.brokerage_id,
                    DBConversation.assigned_agent_id == ctx.user_id,
                    DBOfferRecord.created_at >= start,
                    DBOfferRecord.created_at <= end,
                )
                .scalar()
                or 0
            ),
            "hot_leads_active": (
                db.query(func.count(DBLeadAssignment.assignment_id))
                .filter(
                    DBLeadAssignment.brokerage_id == ctx.brokerage_id,
                    DBLeadAssignment.assigned_agent_id == ctx.user_id,
                    DBLeadAssignment.status.in_(active_statuses),
                    DBLeadAssignment.updated_at >= start,
                    DBLeadAssignment.updated_at <= end,
                )
                .scalar()
                or 0
            ),
            "tasks_overdue": (
                db.query(func.count(DBLeadTask.task_id))
                .filter(
                    DBLeadTask.brokerage_id == ctx.brokerage_id,
                    DBLeadTask.assigned_agent_id == ctx.user_id,
                    DBLeadTask.status.in_(["open", "in_progress"]),
                    DBLeadTask.due_at >= start,
                    DBLeadTask.due_at < end,
                )
                .scalar()
                or 0
            ),
        },
    }


def _average_response_minutes(db: Session, ctx: AgentDashboardContext, *, start: datetime, end: datetime) -> Optional[float]:
    actions = (
        db.query(DBLeadAction)
        .filter(
            DBLeadAction.brokerage_id == ctx.brokerage_id,
            DBLeadAction.agent_user_id == ctx.user_id,
            DBLeadAction.action_type.in_(["agent_dashboard_reply_sent", "draft_reply_sent"]),
            DBLeadAction.created_at >= start,
            DBLeadAction.created_at <= end,
        )
        .order_by(DBLeadAction.created_at.asc())
        .limit(200)
        .all()
    )
    deltas: list[float] = []
    for action in actions:
        last_buyer_message = (
            db.query(DBMessage)
            .filter(
                DBMessage.conversation_id == action.conversation_id,
                DBMessage.role == "user",
                DBMessage.timestamp <= action.created_at,
            )
            .order_by(DBMessage.timestamp.desc())
            .first()
        )
        if not last_buyer_message:
            continue
        delta = action.created_at - last_buyer_message.timestamp
        if delta.total_seconds() >= 0:
            deltas.append(delta.total_seconds() / 60)
    if not deltas:
        return None
    return round(sum(deltas) / len(deltas), 1)


@router.get("/agent/dashboard")
async def agent_dashboard(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    refresh_morning_hot_list(
        db,
        brokerage_id=ctx.brokerage_id,
        user_id=ctx.user_id,
        role=ctx.role,
        limit=50,
    )
    payload = {
        "sample_data": False,
        "generated_at": _iso(datetime.utcnow()),
        "agent": {
            "user_id": ctx.user_id,
            "display_name": ctx.display_name,
            "role": ctx.role,
        },
        "brokerage": {
            "brokerage_id": ctx.brokerage_id,
            "name": ctx.brokerage_name,
        },
        "empty_state": None,
        "conversations": _conversation_inbox(db, ctx),
        "hot_leads": _hot_leads(db, ctx),
        "tasks": _tasks(db, ctx),
        "viewings": _viewings(db, ctx),
        "escalation_threads": _escalation_threads(
            db,
            ctx,
            states={"debouncing", "open", "updated", "timed_out"},
            limit=25,
        ),
        "drafts": _drafts(db, ctx),
        "hot_list_refresh": _hotlist_refresh_payload(db, ctx),
        "campaigns": _campaigns(db, ctx),
        "campaign_uploads": _campaign_uploads(db, ctx),
        "campaign_recipients": _campaign_recipients(db, ctx),
        "owner_leads": _owner_leads(db, ctx),
        "marketing": _marketing(db, ctx),
    }
    payload["metrics"] = _metrics(db, ctx, payload)
    payload["performance"] = _performance_metrics(db, ctx)

    has_real_collections = any([
        payload["hot_leads"],
        payload["conversations"],
        payload["tasks"],
        payload["viewings"],
        payload["escalation_threads"],
        payload["campaigns"],
        payload["campaign_uploads"],
        payload["campaign_recipients"],
        payload["owner_leads"],
        payload["drafts"]["reply_drafts"],
        payload["drafts"]["ai_drafts"],
        payload["drafts"]["outreach_drafts"],
    ])
    has_metric_activity = any(
        value > 0
        for value in payload["metrics"].values()
        if isinstance(value, int | float)
    )
    if not has_real_collections and not has_metric_activity:
        payload["empty_state"] = {
            "reason": "no_workspace_activity",
            "message": (
                "No live buyer conversations, tasks, viewings, drafts, escalations, "
                "or campaigns have landed in this workspace yet."
            ),
        }
    return payload


@router.post("/agent/hot-list/refresh")
async def refresh_agent_hot_list(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    run = refresh_hotlist_with_run(
        db,
        brokerage_id=ctx.brokerage_id,
        requested_by_user_id=ctx.user_id,
        role=ctx.role,
        trigger="manual",
        limit=100,
    )
    return _hotlist_refresh_payload(db, ctx) | {
        "run_id": run.run_id,
        "status": run.status,
    }


@router.get("/agent/drafts")
async def agent_draft_queue(
    include_snoozed: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    now = datetime.utcnow()
    rows = (
        db.query(DBDraftReply)
        .filter(
            DBDraftReply.brokerage_id == ctx.brokerage_id,
            DBDraftReply.status.in_(["draft", "edited", "snoozed"]),
        )
        .order_by(DBDraftReply.updated_at.desc(), DBDraftReply.created_at.desc())
        .limit(limit)
        .all()
    )
    visible: list[DBDraftReply] = []
    for draft in rows:
        if not _conversation_is_visible(db, ctx, draft.conversation_id):
            continue
        snoozed_until = _metadata_datetime(draft.metadata_json or {}, "snoozed_until")
        if draft.status == "snoozed" and snoozed_until and snoozed_until > now and not include_snoozed:
            continue
        visible.append(draft)

    serialized = [_serialize_reply_draft(db, draft) for draft in visible]
    categories: dict[str, int] = {}
    for draft in serialized:
        key = draft["category"]
        categories[key] = categories.get(key, 0) + 1
    return {
        "generated_at": _iso(now),
        "drafts": serialized,
        "counts": {
            "total": len(serialized),
            "categories": categories,
        },
    }


@router.patch("/agent/drafts/{draft_id}")
async def update_reply_draft(
    draft_id: str,
    body: DraftUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    draft = _get_visible_reply_draft_or_404(db, draft_id=draft_id, ctx=ctx)
    if draft.status not in {"draft", "edited", "snoozed"}:
        raise HTTPException(status_code=409, detail=f"Draft is {draft.status}")
    text = (body.body or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Draft body is required")

    metadata = dict(draft.metadata_json or {})
    metadata["last_edited_at"] = datetime.utcnow().isoformat()
    metadata["last_edited_by"] = ctx.user_id
    draft.draft_text = text
    draft.status = "edited"
    draft.metadata_json = metadata
    draft.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(draft)
    return _serialize_reply_draft(db, draft)


@router.post("/agent/drafts/{draft_id}/send")
async def send_reply_draft(
    draft_id: str,
    body: DraftSendRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    draft = _get_visible_reply_draft_or_404(db, draft_id=draft_id, ctx=ctx)
    if draft.status not in {"draft", "edited", "snoozed"}:
        raise HTTPException(status_code=409, detail=f"Draft is {draft.status}")
    text = (body.body if body.body is not None else draft.draft_text).strip()
    if not text:
        raise HTTPException(status_code=400, detail="Draft body is required")

    conversation = db.get(DBConversation, draft.conversation_id)
    if not conversation or not conversation.brokerage_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    brokerage = db.get(DBBrokerage, ctx.brokerage_id)
    if not brokerage or not brokerage.brokerage_ai_number:
        raise HTTPException(status_code=400, detail="Brokerage AI number is not configured")
    buyer_phone = draft.buyer_phone or conversation.buyer_phone
    if is_buyer_suppressed(db, ctx.brokerage_id, buyer_phone):
        record_compliance_event(
            db,
            brokerage_id=ctx.brokerage_id,
            conversation_id=draft.conversation_id,
            listing_id=draft.listing_id,
            buyer_phone=buyer_phone,
            actor_user_id=ctx.user_id,
            event_type="draft_reply_blocked_opt_out",
            direction="outbound",
            details={"draft_id": draft.draft_id, "body_preview": text[:200]},
        )
        raise HTTPException(status_code=409, detail="Buyer has opted out")

    from app.core.messaging import get_transport
    from app.core.messaging.types import OutboundBuyerMessage

    send_result = get_transport().send_to_buyer(
        OutboundBuyerMessage(
            brokerage_id=ctx.brokerage_id,
            brokerage_ai_number=brokerage.brokerage_ai_number,
            buyer_phone=buyer_phone,
            body=text,
            conversation_id=draft.conversation_id,
            listing_id=draft.listing_id,
        )
    )
    if not send_result.ok:
        raise HTTPException(status_code=502, detail=send_result.error or "Draft send failed")

    now = datetime.utcnow()
    draft.draft_text = text
    draft.status = "sent"
    draft.sent_at = now
    metadata = dict(draft.metadata_json or {})
    metadata["sent_at"] = now.isoformat()
    metadata["sent_by"] = ctx.user_id
    metadata["transport_message_id"] = send_result.transport_message_id
    draft.metadata_json = metadata
    draft.updated_at = now

    db.add(DBMessage(
        conversation_id=draft.conversation_id,
        role="assistant",
        content=text,
        intent="agent_draft_reply",
        metadata_json={
            "source": "draft_approval_queue",
            "draft_id": draft.draft_id,
            "agent_user_id": ctx.user_id,
            "transport_message_id": send_result.transport_message_id,
        },
    ))
    conversation.updated_at = now

    assignment = (
        db.query(DBLeadAssignment)
        .filter(DBLeadAssignment.conversation_id == draft.conversation_id)
        .first()
    )
    if assignment:
        assignment.last_agent_action_at = now
        assignment.updated_at = now

    db.add(DBLeadAction(
        brokerage_id=ctx.brokerage_id,
        conversation_id=draft.conversation_id,
        listing_id=draft.listing_id,
        buyer_phone=buyer_phone,
        agent_user_id=ctx.user_id,
        action_type="draft_reply_sent",
        outcome=draft.intent,
        note=text[:500],
        payload={
            "draft_id": draft.draft_id,
            "transport_message_id": send_result.transport_message_id,
        },
    ))
    record_compliance_event(
        db,
        brokerage_id=ctx.brokerage_id,
        conversation_id=draft.conversation_id,
        listing_id=draft.listing_id,
        buyer_phone=buyer_phone,
        actor_user_id=ctx.user_id,
        event_type="draft_reply_sent",
        direction="outbound",
        details={
            "draft_id": draft.draft_id,
            "intent": draft.intent,
            "body_preview": text[:200],
            "transport_message_id": send_result.transport_message_id,
        },
    )
    safe_commit(db)
    db.refresh(draft)
    return {**_serialize_reply_draft(db, draft), "sent": True}


@router.post("/agent/drafts/{draft_id}/reject")
async def reject_reply_draft(
    draft_id: str,
    body: DraftRejectRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    draft = _get_visible_reply_draft_or_404(db, draft_id=draft_id, ctx=ctx)
    if draft.status not in {"draft", "edited", "snoozed"}:
        raise HTTPException(status_code=409, detail=f"Draft is {draft.status}")
    now = datetime.utcnow()
    metadata = dict(draft.metadata_json or {})
    metadata["rejected_at"] = now.isoformat()
    metadata["rejected_by"] = ctx.user_id
    metadata["reject_reason"] = body.reason
    draft.status = "discarded"
    draft.metadata_json = metadata
    draft.updated_at = now
    db.add(DBLeadAction(
        brokerage_id=ctx.brokerage_id,
        conversation_id=draft.conversation_id,
        listing_id=draft.listing_id,
        buyer_phone=draft.buyer_phone,
        agent_user_id=ctx.user_id,
        action_type="draft_reply_rejected",
        outcome=draft.intent,
        note=body.reason,
        payload={"draft_id": draft.draft_id},
    ))
    safe_commit(db)
    db.refresh(draft)
    return _serialize_reply_draft(db, draft)


@router.post("/agent/drafts/{draft_id}/snooze")
async def snooze_reply_draft(
    draft_id: str,
    body: DraftSnoozeRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    draft = _get_visible_reply_draft_or_404(db, draft_id=draft_id, ctx=ctx)
    if draft.status not in {"draft", "edited", "snoozed"}:
        raise HTTPException(status_code=409, detail=f"Draft is {draft.status}")
    now = datetime.utcnow()
    snoozed_until = body.snoozed_until
    if not snoozed_until:
        snoozed_until = now + timedelta(minutes=body.minutes or 120)
    if snoozed_until <= now:
        raise HTTPException(status_code=400, detail="snoozed_until must be in the future")

    metadata = dict(draft.metadata_json or {})
    metadata["snoozed_until"] = snoozed_until.isoformat()
    metadata["snoozed_by"] = ctx.user_id
    metadata["snooze_reason"] = body.reason
    draft.status = "snoozed"
    draft.metadata_json = metadata
    draft.updated_at = now
    db.add(DBLeadAction(
        brokerage_id=ctx.brokerage_id,
        conversation_id=draft.conversation_id,
        listing_id=draft.listing_id,
        buyer_phone=draft.buyer_phone,
        agent_user_id=ctx.user_id,
        action_type="draft_reply_snoozed",
        outcome=draft.intent,
        note=body.reason,
        payload={
            "draft_id": draft.draft_id,
            "snoozed_until": snoozed_until.isoformat(),
        },
    ))
    safe_commit(db)
    db.refresh(draft)
    return _serialize_reply_draft(db, draft)


@router.get("/agent/escalations")
async def agent_escalation_inbox(
    state: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    agent_user_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    states = None
    if state:
        if state == "active":
            states = {"debouncing", "open", "updated"}
        elif state == "closed":
            states = {"resolved", "timed_out", "opt_out_closed"}
        else:
            states = {part.strip() for part in state.split(",") if part.strip()}
    threads = _escalation_threads(
        db,
        ctx,
        states=states,
        category=category,
        agent_user_id=agent_user_id,
        limit=limit,
    )
    return {
        "generated_at": _iso(datetime.utcnow()),
        "threads": threads,
        "counts": _escalation_counts(threads),
        "filters": {
            "state": state,
            "category": category,
            "agent_user_id": agent_user_id,
            "limit": limit,
        },
    }


@router.post("/agent/escalations/{thread_id}/resolve")
async def resolve_escalation_thread(
    thread_id: str,
    body: ResolveEscalationRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    thread = db.get(DBEscalationThread, thread_id)
    if not thread or thread.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Escalation thread not found")
    conversation = db.get(DBConversation, thread.conversation_id)
    if not conversation or not can_view_conversation(
        db,
        conversation,
        user_id=ctx.user_id,
        brokerage_id=ctx.brokerage_id,
        role=ctx.role,
    ):
        raise HTTPException(status_code=404, detail="Escalation thread not found")
    if thread.state in {"resolved", "timed_out", "opt_out_closed"}:
        return {
            "thread_id": thread.thread_id,
            "state": thread.state,
            "closed_at": _iso(thread.closed_at),
            "close_reason": thread.close_reason,
        }

    now = datetime.utcnow()
    thread.state = "resolved"
    thread.closed_at = now
    thread.close_reason = body.reason or "manual"
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
    record_compliance_event(
        db,
        brokerage_id=thread.brokerage_id,
        conversation_id=thread.conversation_id,
        listing_id=thread.listing_id,
        buyer_phone=thread.buyer_phone,
        actor_user_id=ctx.user_id,
        event_type="escalation_thread_resolved",
        direction="system",
        details={
            "thread_id": thread.thread_id,
            "category": thread.category,
            "close_reason": thread.close_reason,
            "resolution_source": "agent_dashboard",
            "question_count": thread.question_count or len(questions),
            "note": body.note,
        },
    )
    safe_commit(db)
    return {
        "thread_id": thread.thread_id,
        "state": thread.state,
        "closed_at": _iso(thread.closed_at),
        "close_reason": thread.close_reason,
        "resolved_question_count": len(questions),
    }


@router.post("/agent/escalations/{thread_id}/reply")
async def reply_to_escalation_thread(
    thread_id: str,
    body: EscalationReplyRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    if body.send_to_buyer is not True:
        raise HTTPException(status_code=400, detail="Dashboard replies must set send_to_buyer=true")
    reply_body = (body.body or "").strip()
    if not reply_body:
        raise HTTPException(status_code=400, detail="Reply body is required")

    thread = db.get(DBEscalationThread, thread_id)
    if not thread or thread.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Escalation thread not found")
    conversation = db.get(DBConversation, thread.conversation_id)
    if not conversation or not can_view_conversation(
        db,
        conversation,
        user_id=ctx.user_id,
        brokerage_id=ctx.brokerage_id,
        role=ctx.role,
    ):
        raise HTTPException(status_code=404, detail="Escalation thread not found")
    if thread.state in {"resolved", "timed_out", "opt_out_closed"}:
        raise HTTPException(status_code=409, detail=f"Escalation thread is {thread.state}")

    brokerage = db.get(DBBrokerage, ctx.brokerage_id)
    if not brokerage:
        raise HTTPException(status_code=404, detail="Brokerage not found")

    from app.core.agent_relay import send_dashboard_escalation_reply

    result = send_dashboard_escalation_reply(
        db,
        brokerage=brokerage,
        thread=thread,
        actor_user_id=ctx.user_id,
        body=reply_body,
    )
    if not result.relayed:
        status_code = 400 if result.status in {"empty_reply", "missing_brokerage_ai_number"} else 502
        raise HTTPException(status_code=status_code, detail=result.reason or result.status)
    db.refresh(thread)
    return {
        "thread_id": thread.thread_id,
        "state": thread.state,
        "closed_at": _iso(thread.closed_at),
        "close_reason": thread.close_reason,
        "conversation_id": thread.conversation_id,
        "buyer_phone": thread.buyer_phone,
        "route_id": result.route_id,
        "transport_message_id": result.transport_message_id,
        "sent": True,
    }


@router.post("/agent/tasks/{task_id}/done")
async def mark_task_done(
    task_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    task = db.get(DBLeadTask, task_id)
    if not task or task.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Task not found")

    now = datetime.utcnow()
    task.status = "done"
    task.completed_at = now
    task.completed_by = user.id
    task.snoozed_until = None
    task.snooze_reason = None
    task.updated_at = now
    if task.conversation_id:
        db.add(DBLeadAction(
            brokerage_id=ctx.brokerage_id,
            conversation_id=task.conversation_id,
            listing_id=task.listing_id,
            buyer_phone=task.buyer_phone,
            agent_user_id=user.id,
            action_type="task_done",
            outcome=task.task_type,
            note=task.title,
            payload={"task_id": task.task_id},
        ))
    safe_commit(db)
    return {"task_id": task.task_id, "status": task.status, "completed_at": _iso(task.completed_at)}


@router.post("/agent/tasks/{task_id}/snooze")
async def snooze_task(
    task_id: str,
    body: SnoozeTaskRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    task = db.get(DBLeadTask, task_id)
    if not task or task.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == "done":
        raise HTTPException(status_code=409, detail="Completed tasks cannot be snoozed")

    minutes = body.minutes if body.minutes is not None else 24 * 60
    if minutes <= 0:
        raise HTTPException(status_code=400, detail="minutes must be positive")

    now = datetime.utcnow()
    task.snoozed_until = body.snoozed_until or now + timedelta(minutes=minutes)
    task.snooze_reason = body.reason
    task.updated_at = now
    if task.conversation_id:
        db.add(DBLeadAction(
            brokerage_id=ctx.brokerage_id,
            conversation_id=task.conversation_id,
            listing_id=task.listing_id,
            buyer_phone=task.buyer_phone,
            agent_user_id=user.id,
            action_type="task_snoozed",
            outcome=task.task_type,
            note=body.reason,
            payload={"task_id": task.task_id, "snoozed_until": _iso(task.snoozed_until)},
        ))
    safe_commit(db)
    return {"task_id": task.task_id, "status": task.status, "snoozed_until": _iso(task.snoozed_until)}
