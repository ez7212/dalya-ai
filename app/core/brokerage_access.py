from __future__ import annotations

import logging
import os
import re
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Literal, Optional

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.auth import CurrentUser
from app.db.session import safe_commit, set_db_session_context
from app.models.db_models import (
    DBBrokerage,
    DBBrokerageMember,
    DBBuyerSuppression,
    DBComplianceEvent,
    DBConversation,
    DBConversationAccessGrant,
    DBLeadAssignment,
    DBListing,
)

_MANAGING_ROLES = {"owner", "team_lead", "admin"}
_REQUESTED_BROKERAGE_ID: ContextVar[str | None] = ContextVar("requested_brokerage_id", default=None)
BrokerageContextSource = Literal[
    "explicit_header",
    "single_membership_fallback",
    "service",
    "parent_object",
]


@dataclass(frozen=True)
class BrokerageContext:
    brokerage_id: str
    membership_id: str | None
    user_id: str
    role: str | None
    is_platform_admin: bool
    source: BrokerageContextSource
    warnings: tuple[str, ...] = ()


def get_requested_brokerage_id(
    x_brokerage_id: Optional[str] = Header(default=None, alias="X-Brokerage-Id"),
) -> Optional[str]:
    if x_brokerage_id is None:
        return None
    cleaned = x_brokerage_id.strip()
    return cleaned or None


async def capture_requested_brokerage_context(
    x_brokerage_id: Optional[str] = Header(default=None, alias="X-Brokerage-Id"),
) -> AsyncIterator[Optional[str]]:
    requested_brokerage_id = get_requested_brokerage_id(x_brokerage_id)
    token = _REQUESTED_BROKERAGE_ID.set(requested_brokerage_id)
    try:
        yield requested_brokerage_id
    finally:
        _REQUESTED_BROKERAGE_ID.reset(token)


def current_requested_brokerage_id() -> Optional[str]:
    return _REQUESTED_BROKERAGE_ID.get()


def _brokerage_context_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
        },
    )


def resolve_request_brokerage_context(
    db: Session,
    current_user: CurrentUser,
    explicit_brokerage_id: str | None,
    *,
    allow_single_membership_fallback: bool = True,
    require_explicit_for_multi: bool = True,
    allow_platform_admin: bool = False,
) -> BrokerageContext:
    """Resolve authenticated brokerage context without guessing for multi-tenant users."""
    user_id = current_user.id
    is_platform_admin = bool(os.getenv("ADMIN_USER_ID") and os.getenv("ADMIN_USER_ID") == user_id)
    set_db_session_context(
        db,
        user_id=user_id,
        is_platform_admin=False,
    )
    active_memberships = (
        db.query(DBBrokerageMember)
        .filter(
            DBBrokerageMember.user_id == user_id,
            DBBrokerageMember.status == "active",
        )
        .order_by(DBBrokerageMember.created_at.asc(), DBBrokerageMember.member_id.asc())
        .all()
    )

    if explicit_brokerage_id:
        member = next(
            (
                membership
                for membership in active_memberships
                if membership.brokerage_id == explicit_brokerage_id
            ),
            None,
        )
        if not member and allow_platform_admin and is_platform_admin:
            brokerage = db.get(DBBrokerage, explicit_brokerage_id)
            if brokerage and brokerage.status == "active":
                logger.info(
                    "brokerage_context_resolved",
                    extra={
                        "user_id": user_id,
                        "brokerage_id": explicit_brokerage_id,
                        "source": "explicit_header",
                        "is_platform_admin": True,
                    },
                )
                set_db_session_context(
                    db,
                    brokerage_id=explicit_brokerage_id,
                    is_platform_admin=True,
                )
                return BrokerageContext(
                    brokerage_id=explicit_brokerage_id,
                    membership_id=None,
                    user_id=user_id,
                    role="platform_admin",
                    is_platform_admin=True,
                    source="explicit_header",
                )
        if not member:
            logger.warning(
                "brokerage_context_forbidden",
                extra={
                    "user_id": user_id,
                    "brokerage_id": explicit_brokerage_id,
                    "code": "brokerage_context_forbidden",
                },
            )
            raise _brokerage_context_error(
                status.HTTP_403_FORBIDDEN,
                "brokerage_context_forbidden",
                "You do not have access to this brokerage.",
            )

        brokerage = db.get(DBBrokerage, member.brokerage_id)
        if not brokerage or brokerage.status != "active":
            logger.warning(
                "brokerage_context_forbidden",
                extra={
                    "user_id": user_id,
                    "brokerage_id": member.brokerage_id,
                    "code": "brokerage_context_forbidden",
                },
            )
            raise _brokerage_context_error(
                status.HTTP_403_FORBIDDEN,
                "brokerage_context_forbidden",
                "You do not have access to this brokerage.",
            )

        logger.info(
            "brokerage_context_resolved",
            extra={
                "user_id": user_id,
                "brokerage_id": member.brokerage_id,
                "source": "explicit_header",
            },
        )
        set_db_session_context(db, brokerage_id=member.brokerage_id)
        return BrokerageContext(
            brokerage_id=member.brokerage_id,
            membership_id=member.member_id,
            user_id=user_id,
            role=member.role,
            is_platform_admin=False,
            source="explicit_header",
        )

    if not active_memberships:
        logger.warning(
            "brokerage_context_no_active_membership",
            extra={"user_id": user_id, "code": "no_active_brokerage_membership"},
        )
        raise _brokerage_context_error(
            status.HTTP_403_FORBIDDEN,
            "no_active_brokerage_membership",
            "No active brokerage membership is available for this user.",
        )

    if len(active_memberships) == 1 and allow_single_membership_fallback:
        member = active_memberships[0]
        brokerage = db.get(DBBrokerage, member.brokerage_id)
        if not brokerage or brokerage.status != "active":
            logger.warning(
                "brokerage_context_forbidden",
                extra={
                    "user_id": user_id,
                    "brokerage_id": member.brokerage_id,
                    "code": "brokerage_context_forbidden",
                },
            )
            raise _brokerage_context_error(
                status.HTTP_403_FORBIDDEN,
                "brokerage_context_forbidden",
                "You do not have access to this brokerage.",
            )
        logger.info(
            "brokerage_context_resolved",
            extra={
                "user_id": user_id,
                "brokerage_id": member.brokerage_id,
                "source": "single_membership_fallback",
            },
        )
        set_db_session_context(db, brokerage_id=member.brokerage_id)
        return BrokerageContext(
            brokerage_id=member.brokerage_id,
            membership_id=member.member_id,
            user_id=user_id,
            role=member.role,
            is_platform_admin=False,
            source="single_membership_fallback",
            warnings=("single_membership_fallback",),
        )

    if len(active_memberships) > 1 and require_explicit_for_multi:
        logger.warning(
            "brokerage_context_required",
            extra={"user_id": user_id, "code": "brokerage_context_required"},
        )
        raise _brokerage_context_error(
            status.HTTP_409_CONFLICT,
            "brokerage_context_required",
            "Select a brokerage to continue.",
        )

    raise _brokerage_context_error(
        status.HTTP_403_FORBIDDEN,
        "brokerage_context_forbidden",
        "You do not have access to this brokerage.",
    )


_OPT_OUT_PATTERNS = (
    r"\bstop\b",
    r"\bunsubscribe\b",
    r"\bdo not contact\b",
    r"\bdon'?t contact\b",
    r"\bdo not message\b",
    r"\bdon'?t message\b",
    r"\bdo not call\b",
    r"\bdon'?t call\b",
    r"\bremove me\b",
    r"\bno more messages\b",
    r"\bno more texts\b",
    r"\bcease contact\b",
    r"\bopt\s*out\b",
    r"\bwithdraw consent\b",
)
_OPT_OUT_RE = re.compile("|".join(_OPT_OUT_PATTERNS), re.IGNORECASE)


def conversation_owner_user_id(db: Session, conversation: DBConversation) -> Optional[str]:
    """Resolve the primary owning agent for a conversation."""
    if not conversation:
        return None
    if conversation.assigned_agent_id:
        return conversation.assigned_agent_id

    lead_assignment = (
        db.query(DBLeadAssignment.assigned_agent_id)
        .filter(DBLeadAssignment.conversation_id == conversation.conversation_id)
        .first()
    )
    if lead_assignment and lead_assignment.assigned_agent_id:
        return lead_assignment.assigned_agent_id

    if conversation.listing_id:
        listing = db.get(DBListing, conversation.listing_id)
        if listing and listing.assigned_agent_id:
            return listing.assigned_agent_id
    return None


def is_managing_agent(role: Optional[str]) -> bool:
    return bool(role and role in _MANAGING_ROLES)


def can_view_conversation(
    db: Session,
    conversation: DBConversation,
    *,
    user_id: str,
    brokerage_id: str,
    role: Optional[str] = None,
) -> bool:
    if not conversation or conversation.brokerage_id != brokerage_id:
        return False
    if is_managing_agent(role):
        return True

    owner_id = conversation_owner_user_id(db, conversation)
    if owner_id and owner_id == user_id:
        return True

    grant = (
        db.query(DBConversationAccessGrant)
        .filter(
            DBConversationAccessGrant.brokerage_id == brokerage_id,
            DBConversationAccessGrant.conversation_id == conversation.conversation_id,
            DBConversationAccessGrant.agent_user_id == user_id,
            DBConversationAccessGrant.active.is_(True),
        )
        .first()
    )
    return grant is not None


def get_or_create_conversation_access_grant(
    db: Session,
    *,
    brokerage_id: str,
    conversation_id: str,
    agent_user_id: str,
    granted_by_user_id: Optional[str] = None,
    access_level: str = "viewer",
    reason: Optional[str] = None,
) -> DBConversationAccessGrant:
    grant = (
        db.query(DBConversationAccessGrant)
        .filter(
            DBConversationAccessGrant.brokerage_id == brokerage_id,
            DBConversationAccessGrant.conversation_id == conversation_id,
            DBConversationAccessGrant.agent_user_id == agent_user_id,
        )
        .first()
    )
    if not grant:
        grant = DBConversationAccessGrant(
            brokerage_id=brokerage_id,
            conversation_id=conversation_id,
            agent_user_id=agent_user_id,
            granted_by_user_id=granted_by_user_id,
            access_level=access_level,
            reason=reason,
            active=True,
        )
        db.add(grant)
    else:
        grant.granted_by_user_id = granted_by_user_id or grant.granted_by_user_id
        grant.access_level = access_level or grant.access_level
        grant.reason = reason if reason is not None else grant.reason
        grant.active = True
        grant.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(grant)
    return grant


def grant_conversation_access(
    db: Session,
    *,
    conversation: DBConversation,
    agent_user_id: str,
    granted_by_user_id: Optional[str] = None,
    access_level: str = "viewer",
    reason: Optional[str] = None,
) -> DBConversationAccessGrant:
    grant = get_or_create_conversation_access_grant(
        db,
        brokerage_id=conversation.brokerage_id,
        conversation_id=conversation.conversation_id,
        agent_user_id=agent_user_id,
        granted_by_user_id=granted_by_user_id,
        access_level=access_level,
        reason=reason,
    )
    record_compliance_event(
        db,
        brokerage_id=conversation.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=conversation.listing_id,
        buyer_phone=conversation.buyer_phone,
        actor_user_id=granted_by_user_id,
        event_type="conversation_access_granted",
        direction="system",
        details={
            "agent_user_id": agent_user_id,
            "access_level": access_level,
            "reason": reason,
        },
    )
    return grant


def get_or_create_lead_assignment(
    db: Session,
    conversation: DBConversation,
) -> DBLeadAssignment:
    assignment = (
        db.query(DBLeadAssignment)
        .filter(DBLeadAssignment.conversation_id == conversation.conversation_id)
        .first()
    )
    if not assignment:
        assignment = DBLeadAssignment(
            brokerage_id=conversation.brokerage_id,
            conversation_id=conversation.conversation_id,
            listing_id=conversation.listing_id,
            buyer_phone=conversation.buyer_phone,
            assigned_agent_id=conversation.assigned_agent_id,
            status="new",
            urgency_score=0,
        )
        db.add(assignment)
        safe_commit(db)
        db.refresh(assignment)
        return assignment

    changed = False
    if assignment.brokerage_id != conversation.brokerage_id and conversation.brokerage_id:
        assignment.brokerage_id = conversation.brokerage_id
        changed = True
    if assignment.listing_id != conversation.listing_id:
        assignment.listing_id = conversation.listing_id
        changed = True
    if assignment.buyer_phone != conversation.buyer_phone:
        assignment.buyer_phone = conversation.buyer_phone
        changed = True
    if assignment.assigned_agent_id != conversation.assigned_agent_id:
        assignment.assigned_agent_id = conversation.assigned_agent_id
        changed = True
    if changed:
        assignment.updated_at = datetime.utcnow()
        safe_commit(db)
        db.refresh(assignment)
    return assignment


def reassign_conversation(
    db: Session,
    *,
    conversation: DBConversation,
    new_agent_user_id: str,
    assigned_by_user_id: Optional[str] = None,
) -> DBConversation:
    conversation.assigned_agent_id = new_agent_user_id
    conversation.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(conversation)

    assignment = get_or_create_lead_assignment(db, conversation)
    assignment.assigned_agent_id = new_agent_user_id
    assignment.assigned_by = assigned_by_user_id
    assignment.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(assignment)

    record_compliance_event(
        db,
        brokerage_id=conversation.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=conversation.listing_id,
        buyer_phone=conversation.buyer_phone,
        actor_user_id=assigned_by_user_id,
        event_type="conversation_reassigned",
        direction="system",
        details={"new_agent_user_id": new_agent_user_id},
    )
    return conversation


def is_opt_out_message(body: str) -> bool:
    if not body:
        return False
    return bool(_OPT_OUT_RE.search(body))


def is_buyer_suppressed(db: Session, brokerage_id: str, buyer_phone: str) -> bool:
    suppression = (
        db.query(DBBuyerSuppression)
        .filter(
            DBBuyerSuppression.brokerage_id == brokerage_id,
            DBBuyerSuppression.buyer_phone == buyer_phone,
            DBBuyerSuppression.active.is_(True),
        )
        .first()
    )
    return suppression is not None


def mark_buyer_opted_out(
    db: Session,
    *,
    brokerage_id: str,
    buyer_phone: str,
    conversation_id: Optional[str] = None,
    listing_id: Optional[str] = None,
    suppressed_by_user_id: Optional[str] = None,
    reason: Optional[str] = None,
    source: str = "buyer_message",
) -> DBBuyerSuppression:
    suppression = (
        db.query(DBBuyerSuppression)
        .filter(
            DBBuyerSuppression.brokerage_id == brokerage_id,
            DBBuyerSuppression.buyer_phone == buyer_phone,
        )
        .first()
    )
    if not suppression:
        suppression = DBBuyerSuppression(
            brokerage_id=brokerage_id,
            buyer_phone=buyer_phone,
            conversation_id=conversation_id,
            listing_id=listing_id,
            suppressed_by_user_id=suppressed_by_user_id,
            source=source,
            reason=reason,
            active=True,
        )
        db.add(suppression)
    else:
        suppression.conversation_id = conversation_id or suppression.conversation_id
        suppression.listing_id = listing_id or suppression.listing_id
        suppression.suppressed_by_user_id = suppressed_by_user_id or suppression.suppressed_by_user_id
        suppression.source = source or suppression.source
        suppression.reason = reason if reason is not None else suppression.reason
        suppression.active = True
        suppression.lifted_at = None
        suppression.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(suppression)

    record_compliance_event(
        db,
        brokerage_id=brokerage_id,
        conversation_id=conversation_id,
        listing_id=listing_id,
        buyer_phone=buyer_phone,
        actor_user_id=suppressed_by_user_id,
        event_type="buyer_opt_out",
        direction="inbound",
        details={
            "source": source,
            "reason": reason,
        },
    )

    # DAL-162 catalog event #9 — compliance-relevant: the agent must know to
    # stop all channels. Immediate push, even in quiet hours.
    try:
        from app.core.agent_notifications import notify_agent
        from app.models.db_models import DBBrokerage, DBConversation

        conversation = db.get(DBConversation, conversation_id) if conversation_id else None
        if conversation is None:
            conversation = (
                db.query(DBConversation)
                .filter(
                    DBConversation.brokerage_id == brokerage_id,
                    DBConversation.buyer_phone == buyer_phone,
                )
                .order_by(DBConversation.updated_at.desc())
                .first()
            )
        agent_user_id = conversation.assigned_agent_id if conversation else None
        brokerage = db.get(DBBrokerage, brokerage_id)
        if brokerage and agent_user_id:
            buyer_label = (conversation.buyer_name if conversation else None) or buyer_phone
            notify_agent(
                db,
                brokerage=brokerage,
                agent_user_id=agent_user_id,
                event_type="buyer_opt_out",
                body=(
                    f"{buyer_label} opted out of messages. All channels are now "
                    "blocked for this buyer — do not contact them from personal numbers either."
                ),
                dedupe_key=f"buyer_opt_out:{suppression.suppression_id}:{suppression.updated_at.isoformat()}",
                conversation_id=conversation.conversation_id if conversation else None,
                listing_id=listing_id,
                deep_link_path=(
                    f"/agent/conversations/{conversation.conversation_id}" if conversation else "/agent"
                ),
            )
    except Exception:  # pragma: no cover — notification must never break opt-out
        logger.warning("buyer_opt_out notification failed", exc_info=True)
    return suppression


def record_compliance_event(
    db: Session,
    *,
    brokerage_id: str,
    event_type: str,
    direction: str = "system",
    conversation_id: Optional[str] = None,
    listing_id: Optional[str] = None,
    buyer_phone: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> DBComplianceEvent:
    event = DBComplianceEvent(
        brokerage_id=brokerage_id,
        conversation_id=conversation_id,
        listing_id=listing_id,
        buyer_phone=buyer_phone,
        actor_user_id=actor_user_id,
        event_type=event_type,
        direction=direction,
        details=details or {},
    )
    db.add(event)
    safe_commit(db)
    db.refresh(event)
    return event
