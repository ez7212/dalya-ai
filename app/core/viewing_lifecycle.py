from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.brokerage_access import record_compliance_event
from app.core.messaging import get_transport
from app.core.messaging.types import OutboundBuyerMessage
from app.core.tenant_viewings import tenant_contact_from_logistics
from app.core.viewing_logistics import store_notification_drafts
from app.db.session import safe_commit
from app.models.db_models import (
    DBBrokerage,
    DBConversation,
    DBDraftReply,
    DBLeadAction,
    DBLeadTask,
    DBListing,
    DBListingLogistics,
    DBViewing,
)


BUYER_DRAFT_TYPES = {"buyer_confirmation_t24", "buyer_reminder_t1"}
TENANT_DRAFT_TYPES = {"tenant_notice"}
MULTI_RECIPIENT_DRAFT_TYPES = {"running_late", "reschedule"}
SENDABLE_DRAFT_TYPES = BUYER_DRAFT_TYPES | TENANT_DRAFT_TYPES | MULTI_RECIPIENT_DRAFT_TYPES


def _draft_for_type(
    db: Session,
    *,
    viewing: DBViewing,
    conversation: DBConversation,
    listing: DBListing,
    logistics: Optional[DBListingLogistics],
    draft_type: str,
    actor_user_id: str,
) -> dict[str, Any]:
    drafts = (viewing.metadata_json or {}).get("notification_drafts") or {}
    draft = drafts.get(draft_type)
    if not draft:
        created = store_notification_drafts(
            db,
            viewing=viewing,
            conversation=conversation,
            listing=listing,
            logistics=logistics,
            draft_types=[draft_type],
            actor_user_id=actor_user_id,
        )
        draft = created[0] if created else None
    if not draft:
        raise ValueError(f"Notification draft {draft_type} could not be generated")
    return draft


def _send_to_phone(
    *,
    brokerage: DBBrokerage,
    phone: str,
    body: str,
    viewing: DBViewing,
) -> str | None:
    if not brokerage.brokerage_ai_number:
        raise ValueError("Brokerage AI WhatsApp number is not configured")
    result = get_transport().send_to_buyer(
        OutboundBuyerMessage(
            brokerage_id=brokerage.brokerage_id,
            brokerage_ai_number=brokerage.brokerage_ai_number,
            buyer_phone=phone,
            body=body,
            conversation_id=viewing.conversation_id,
            listing_id=viewing.listing_id,
        )
    )
    if not result.ok:
        raise ValueError(result.error or "Notification send failed")
    return result.transport_message_id


def send_viewing_notification(
    db: Session,
    *,
    brokerage: DBBrokerage,
    viewing: DBViewing,
    conversation: DBConversation,
    listing: DBListing,
    logistics: Optional[DBListingLogistics],
    draft_type: str,
    actor_user_id: str,
    body_override: Optional[str] = None,
) -> dict[str, Any]:
    if draft_type not in SENDABLE_DRAFT_TYPES:
        raise ValueError(f"Unsupported viewing notification type: {draft_type}")
    draft = _draft_for_type(
        db,
        viewing=viewing,
        conversation=conversation,
        listing=listing,
        logistics=logistics,
        draft_type=draft_type,
        actor_user_id=actor_user_id,
    )
    body = body_override or draft.get("body") or ""
    recipients: list[tuple[str, str]] = []
    if draft_type in BUYER_DRAFT_TYPES:
        recipients.append(("buyer", conversation.buyer_phone))
    elif draft_type in TENANT_DRAFT_TYPES:
        tenant_phone, _tenant_key = tenant_contact_from_logistics(logistics)
        if not tenant_phone:
            raise ValueError("Tenant WhatsApp phone number is required")
        recipients.append(("tenant", tenant_phone))
    else:
        recipients.append(("buyer", conversation.buyer_phone))
        tenant_phone, _tenant_key = tenant_contact_from_logistics(logistics)
        if tenant_phone:
            recipients.append(("tenant", tenant_phone))

    sent = []
    for recipient_type, phone in recipients:
        transport_message_id = _send_to_phone(
            brokerage=brokerage,
            phone=phone,
            body=body,
            viewing=viewing,
        )
        sent.append({
            "recipient_type": recipient_type,
            "phone": phone,
            "transport_message_id": transport_message_id,
        })

    now = datetime.utcnow()
    metadata = dict(viewing.metadata_json or {})
    drafts = dict(metadata.get("notification_drafts") or {})
    drafts[draft_type] = {
        **draft,
        "status": "sent",
        "sent_at": now.isoformat(),
        "sent": sent,
    }
    status = dict(metadata.get("confirmation_status") or {})
    if draft_type == "buyer_confirmation_t24":
        status["buyer"] = "notice_sent"
    elif draft_type == "buyer_reminder_t1":
        status["buyer_reminder"] = "sent"
    elif draft_type == "tenant_notice":
        status["tenant"] = "notice_sent"
    elif draft_type == "running_late":
        status["running_late"] = "sent"
    elif draft_type == "reschedule":
        status["reschedule"] = "sent"
    viewing.metadata_json = {
        **metadata,
        "notification_drafts": drafts,
        "confirmation_status": status,
    }
    viewing.updated_at = now
    db.add(DBLeadAction(
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        agent_user_id=actor_user_id,
        action_type="viewing_notification_sent",
        outcome=draft_type,
        payload={"viewing_id": viewing.viewing_id, "draft_type": draft_type, "sent": sent},
    ))
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        actor_user_id=actor_user_id,
        event_type="viewing_notification_sent",
        direction="outbound",
        details={"viewing_id": viewing.viewing_id, "draft_type": draft_type, "sent": sent},
    )
    safe_commit(db)
    db.refresh(viewing)
    return {"draft_type": draft_type, "sent": sent, "confirmation_status": status}


def mark_viewing_completed(
    db: Session,
    *,
    brokerage: DBBrokerage,
    viewing: DBViewing,
    actor_user_id: Optional[str],
    now: Optional[datetime] = None,
) -> DBViewing:
    now = now or datetime.utcnow()
    viewing.status = "completed"
    metadata = dict(viewing.metadata_json or {})
    metadata["completed_at"] = now.isoformat()
    viewing.metadata_json = metadata
    viewing.updated_at = now
    db.add(DBLeadAction(
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        agent_user_id=actor_user_id or viewing.agent_user_id,
        action_type="viewing_completed",
        outcome="completed",
        payload={"viewing_id": viewing.viewing_id},
    ))
    _ensure_post_viewing_trigger(db, brokerage=brokerage, viewing=viewing, now=now)
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        actor_user_id=actor_user_id,
        event_type="viewing_completed",
        direction="system",
        details={"viewing_id": viewing.viewing_id},
    )
    safe_commit(db)
    db.refresh(viewing)
    return viewing


def complete_due_viewings(db: Session, *, brokerage_id: Optional[str] = None, now: Optional[datetime] = None) -> list[DBViewing]:
    now = now or datetime.utcnow()
    query = db.query(DBViewing).filter(
        DBViewing.status == "confirmed",
        DBViewing.scheduled_for.isnot(None),
        DBViewing.scheduled_for <= now - timedelta(minutes=45),
    )
    if brokerage_id:
        query = query.filter(DBViewing.brokerage_id == brokerage_id)
    rows = query.all()
    completed: list[DBViewing] = []
    for viewing in rows:
        brokerage = db.get(DBBrokerage, viewing.brokerage_id)
        if not brokerage:
            continue
        completed.append(mark_viewing_completed(
            db,
            brokerage=brokerage,
            viewing=viewing,
            actor_user_id=None,
            now=now,
        ))
    return completed


def _ensure_post_viewing_trigger(
    db: Session,
    *,
    brokerage: DBBrokerage,
    viewing: DBViewing,
    now: datetime,
) -> None:
    task_key = f"post-viewing-feedback:{viewing.viewing_id}"
    existing = db.query(DBLeadTask).filter(DBLeadTask.task_key == task_key).first()
    if not existing:
        db.add(DBLeadTask(
            task_key=task_key,
            brokerage_id=brokerage.brokerage_id,
            conversation_id=viewing.conversation_id,
            listing_id=viewing.listing_id,
            buyer_phone=viewing.buyer_phone,
            assigned_agent_id=viewing.agent_user_id,
            task_type="post_viewing",
            title="Capture post-viewing feedback",
            description="Ask the buyer and agent for feedback from the completed viewing.",
            status="open",
            priority="normal",
            source="viewing_lifecycle",
            due_at=now,
            metadata_json={"viewing_id": viewing.viewing_id, "trigger": "viewing_completed"},
        ))

    draft = (
        db.query(DBDraftReply)
        .filter(
            DBDraftReply.conversation_id == viewing.conversation_id,
            DBDraftReply.intent == "post_viewing_feedback",
            DBDraftReply.status.in_(["draft", "edited"]),
        )
        .first()
    )
    if not draft:
        db.add(DBDraftReply(
            brokerage_id=brokerage.brokerage_id,
            conversation_id=viewing.conversation_id,
            listing_id=viewing.listing_id,
            buyer_phone=viewing.buyer_phone,
            agent_user_id=viewing.agent_user_id,
            intent="post_viewing_feedback",
            draft_text="Hi, how did the viewing go? What stood out, and is there anything you want clarified before deciding next steps?",
            source="viewing_lifecycle",
            status="draft",
            metadata_json={"viewing_id": viewing.viewing_id, "trigger": "viewing_completed"},
        ))
