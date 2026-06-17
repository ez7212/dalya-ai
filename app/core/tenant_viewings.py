from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.brokerage_access import record_compliance_event
from app.core.brokerage_resolver import get_managing_agent
from app.core.messaging import get_transport
from app.core.messaging.types import OutboundAgentMessage, OutboundBuyerMessage
from app.core.viewing_logistics import store_notification_drafts
from app.db.session import safe_commit
from app.models.db_models import (
    DBBrokerage,
    DBConversation,
    DBLeadAction,
    DBListing,
    DBListingLogistics,
    DBTenantViewingConfirmation,
    DBViewing,
)

logger = logging.getLogger(__name__)


CONFIRM_TERMS = {
    "yes", "y", "ok", "okay", "confirmed", "confirm", "works", "approved", "fine",
    "تمام", "نعم", "اوكي", "موافق",
}
DECLINE_PATTERNS = [
    r"\bdecline\b", r"\bdeclined\b", r"\brefuse\b", r"\bnot\s+allow", r"\bcancel\b",
]
RESCHEDULE_PATTERNS = [
    r"\breschedule\b", r"\bdifferent\s+time\b", r"\banother\s+time\b", r"\bnot\s+available\b",
    r"\bcan't\b", r"\bcannot\b", r"\bdoesn'?t\s+work\b", r"\bnot\s+work\b",
    r"غير مناسب", r"وقت آخر", r"مو مناسب",
]


def normalize_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = str(value).strip()
    if cleaned.lower().startswith("whatsapp:"):
        cleaned = cleaned[len("whatsapp:"):]
    cleaned = re.sub(r"[^\d+]", "", cleaned)
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    return cleaned or None


def tenant_contact_from_logistics(logistics: Optional[DBListingLogistics]) -> tuple[Optional[str], Optional[str]]:
    tenant = (logistics.tenant or {}) if logistics else {}
    raw = tenant.get("whatsapp_number") or tenant.get("phone")
    phone = normalize_phone(raw)
    if phone:
        return phone, phone.lower()
    email = tenant.get("email")
    return None, str(email).strip().lower() if email else None


def _tenant_notice_draft(
    db: Session,
    *,
    viewing: DBViewing,
    conversation: DBConversation,
    listing: DBListing,
    logistics: Optional[DBListingLogistics],
    actor_user_id: str,
) -> dict[str, Any]:
    drafts_by_type = (viewing.metadata_json or {}).get("notification_drafts") or {}
    draft = drafts_by_type.get("tenant_notice")
    if not draft:
        drafts = store_notification_drafts(
            db,
            viewing=viewing,
            conversation=conversation,
            listing=listing,
            logistics=logistics,
            draft_types=["tenant_notice"],
            actor_user_id=actor_user_id,
        )
        draft = drafts[0] if drafts else None
    if not draft:
        raise ValueError("Tenant notice draft could not be generated")
    return draft


def send_tenant_viewing_notice(
    db: Session,
    *,
    brokerage: DBBrokerage,
    viewing: DBViewing,
    conversation: DBConversation,
    listing: DBListing,
    logistics: Optional[DBListingLogistics],
    actor_user_id: str,
    body_override: Optional[str] = None,
) -> DBTenantViewingConfirmation:
    tenant_phone, tenant_contact_key = tenant_contact_from_logistics(logistics)
    if not tenant_phone or not tenant_contact_key:
        raise ValueError("Tenant WhatsApp phone number is required before sending notice")
    if not brokerage.brokerage_ai_number:
        raise ValueError("Brokerage AI WhatsApp number is not configured")

    draft = _tenant_notice_draft(
        db,
        viewing=viewing,
        conversation=conversation,
        listing=listing,
        logistics=logistics,
        actor_user_id=actor_user_id,
    )
    body = body_override or draft.get("body") or ""
    confirmation = (
        db.query(DBTenantViewingConfirmation)
        .filter(
            DBTenantViewingConfirmation.brokerage_id == brokerage.brokerage_id,
            DBTenantViewingConfirmation.viewing_id == viewing.viewing_id,
            DBTenantViewingConfirmation.tenant_contact_key == tenant_contact_key,
        )
        .first()
    )
    if not confirmation:
        confirmation = DBTenantViewingConfirmation(
            brokerage_id=brokerage.brokerage_id,
            viewing_id=viewing.viewing_id,
            listing_id=viewing.listing_id,
            tenant_contact_key=tenant_contact_key,
            tenant_phone=tenant_phone,
        )
        db.add(confirmation)

    result = get_transport().send_to_buyer(
        OutboundBuyerMessage(
            brokerage_id=brokerage.brokerage_id,
            brokerage_ai_number=brokerage.brokerage_ai_number,
            buyer_phone=tenant_phone,
            body=body,
            conversation_id=viewing.conversation_id,
            listing_id=viewing.listing_id,
        )
    )
    if not result.ok:
        raise ValueError(result.error or "Tenant notice send failed")

    now = datetime.utcnow()
    confirmation.status = "notice_sent"
    confirmation.notice_body = body
    confirmation.outbound_message_id = result.transport_message_id
    confirmation.sent_at = now
    confirmation.updated_at = now
    confirmation.metadata_json = {
        **(confirmation.metadata_json or {}),
        "draft_id": draft.get("draft_id"),
        "recipient_type": "tenant",
    }

    drafts = dict((viewing.metadata_json or {}).get("notification_drafts") or {})
    if "tenant_notice" in drafts:
        drafts["tenant_notice"] = {
            **drafts["tenant_notice"],
            "status": "sent",
            "sent_at": now.isoformat(),
            "transport_message_id": result.transport_message_id,
        }
    status = dict((viewing.metadata_json or {}).get("confirmation_status") or {})
    status["tenant"] = "notice_sent"
    viewing.tenant_notice_sent_at = now
    viewing.metadata_json = {
        **(viewing.metadata_json or {}),
        "notification_drafts": drafts,
        "confirmation_status": status,
        "tenant_confirmation_id": confirmation.confirmation_id,
    }
    viewing.updated_at = now
    db.add(DBLeadAction(
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        agent_user_id=actor_user_id,
        action_type="tenant_notice_sent",
        outcome="sent",
        payload={
            "viewing_id": viewing.viewing_id,
            "tenant_contact_key": tenant_contact_key,
            "transport_message_id": result.transport_message_id,
        },
    ))
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        actor_user_id=actor_user_id,
        event_type="tenant_viewing_notice_sent",
        direction="outbound",
        details={
            "viewing_id": viewing.viewing_id,
            "tenant_contact_key": tenant_contact_key,
            "transport_message_id": result.transport_message_id,
        },
    )
    safe_commit(db)
    db.refresh(confirmation)
    db.refresh(viewing)
    return confirmation


def classify_tenant_reply(body: str) -> tuple[str, str]:
    text = (body or "").strip()
    lower = text.lower()
    if any(re.search(pattern, lower) for pattern in DECLINE_PATTERNS):
        return "declined", "Tenant declined or cancelled access."
    if any(re.search(pattern, lower) for pattern in RESCHEDULE_PATTERNS):
        return "reschedule_requested", "Tenant requested a different time or said the proposed time does not work."
    tokens = {token.strip(".,!?").lower() for token in lower.split()}
    if "👍" in text or tokens.intersection(CONFIRM_TERMS):
        return "confirmed", "Tenant confirmed the viewing time."
    return "needs_agent_review", "Tenant replied with free text that needs agent review."


def handle_tenant_viewing_reply(
    db: Session,
    *,
    brokerage: DBBrokerage,
    tenant_phone: str,
    body: str,
    message_sid: str,
) -> tuple[bool, Optional[DBTenantViewingConfirmation]]:
    phone = normalize_phone(tenant_phone)
    if not phone:
        return False, None
    confirmation = (
        db.query(DBTenantViewingConfirmation)
        .filter(
            DBTenantViewingConfirmation.brokerage_id == brokerage.brokerage_id,
            DBTenantViewingConfirmation.tenant_phone == phone,
            DBTenantViewingConfirmation.status.in_(["pending", "notice_sent", "needs_agent_review"]),
        )
        .order_by(DBTenantViewingConfirmation.sent_at.desc().nullslast(), DBTenantViewingConfirmation.created_at.desc())
        .first()
    )
    if not confirmation:
        return False, None

    viewing = db.get(DBViewing, confirmation.viewing_id)
    listing = db.get(DBListing, confirmation.listing_id)
    conversation = db.get(DBConversation, viewing.conversation_id) if viewing else None
    if not viewing or not listing or not conversation:
        return False, None

    status, summary = classify_tenant_reply(body)
    now = datetime.utcnow()
    confirmation.status = status
    confirmation.last_inbound_body = body
    confirmation.responded_at = now
    confirmation.updated_at = now
    confirmation.metadata_json = {
        **(confirmation.metadata_json or {}),
        "last_message_sid": message_sid,
        "summary": summary,
    }

    viewing_status = dict((viewing.metadata_json or {}).get("confirmation_status") or {})
    viewing_status["tenant"] = status
    viewing.metadata_json = {
        **(viewing.metadata_json or {}),
        "confirmation_status": viewing_status,
        "tenant_reply": {
            "status": status,
            "summary": summary,
            "body": body,
            "received_at": now.isoformat(),
            "message_sid": message_sid,
        },
    }
    viewing.updated_at = now
    db.add(DBLeadAction(
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        agent_user_id=viewing.agent_user_id,
        action_type="tenant_reply_received",
        outcome=status,
        note=summary,
        payload={
            "viewing_id": viewing.viewing_id,
            "tenant_contact_key": confirmation.tenant_contact_key,
            "message_sid": message_sid,
        },
    ))
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        event_type="tenant_viewing_reply_received",
        direction="inbound",
        details={
            "viewing_id": viewing.viewing_id,
            "tenant_contact_key": confirmation.tenant_contact_key,
            "status": status,
            "summary": summary,
        },
    )
    _notify_agent_of_tenant_reply(
        db,
        brokerage=brokerage,
        viewing=viewing,
        listing=listing,
        conversation=conversation,
        status=status,
        summary=summary,
        body=body,
    )
    safe_commit(db)
    db.refresh(confirmation)
    return True, confirmation


def _notify_agent_of_tenant_reply(
    db: Session,
    *,
    brokerage: DBBrokerage,
    viewing: DBViewing,
    listing: DBListing,
    conversation: DBConversation,
    status: str,
    summary: str,
    body: str,
) -> None:
    if not brokerage.agents_ai_number:
        return
    managing_agent = get_managing_agent(listing, db)
    agent_phone = getattr(managing_agent, "whatsapp_phone", None)
    agent_user_id = getattr(managing_agent, "user_id", None) or viewing.agent_user_id
    if not agent_phone:
        return
    spa = listing.spa_data or {}
    project = spa.get("project") or listing.listing_id
    scheduled = viewing.scheduled_for.isoformat() if viewing.scheduled_for else "unscheduled"
    body_text = (
        f"[TENANT VIEWING {status.upper()}]\n"
        f"Property: {project} Unit {spa.get('unit_number') or ''}\n"
        f"Viewing: {scheduled}\n"
        f"Buyer: {conversation.buyer_name or conversation.buyer_phone}\n\n"
        f"{summary}\n\n"
        f"Tenant reply:\n\"{body}\""
    )
    get_transport().send_to_agents_ai(
        OutboundAgentMessage(
            brokerage_id=brokerage.brokerage_id,
            agents_ai_number=brokerage.agents_ai_number,
            agent_phone=agent_phone,
            body=body_text,
            conversation_id=viewing.conversation_id,
            listing_id=viewing.listing_id,
            buyer_phone=viewing.buyer_phone,
            escalation_type="tenant_viewing_reply",
            tags=["tenant", status],
            agent_user_id=agent_user_id,
        )
    )
    # DAL-162 catalog event #5 — push already sent above; record for audit/dedupe.
    if agent_user_id:
        from app.core.agent_notifications import notify_agent

        try:
            notify_agent(
                db,
                brokerage=brokerage,
                agent_user_id=agent_user_id,
                event_type="tenant_confirmation",
                body=f"Tenant {status} — {project} viewing",
                dedupe_key=f"tenant_confirmation:{viewing.viewing_id}:{status}:{body[:40]}",
                conversation_id=viewing.conversation_id,
                viewing_id=viewing.viewing_id,
                listing_id=viewing.listing_id,
                deep_link_path=f"/agent/viewings/{viewing.viewing_id}",
                record_only=True,
            )
        except Exception:  # pragma: no cover — audit row must never break the reply flow
            logger.warning("tenant_confirmation notification record failed", exc_info=True)
