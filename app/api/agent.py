"""
Agent API Router — brokerage-scoped endpoints for the agent workflow surface.

The agent dashboard is allowed to show buyer identity and phone numbers, but
only inside the authenticated user's brokerage scope.
"""

import os
import base64
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.brokerage_access import (
    can_view_conversation,
    capture_requested_brokerage_context,
    current_requested_brokerage_id,
    grant_conversation_access,
    is_managing_agent,
    record_compliance_event,
    reassign_conversation,
    resolve_request_brokerage_context,
)
from app.core.brokerage_config import (
    apply_brokerage_config_update,
    runtime_config_for_brokerage,
    serialize_runtime_config,
)
from app.core.buyer_profiles import effective_fields, effective_fields_from_rows
from app.core.conversation_takeover import (
    AI_MODES,
    conversation_ai_mode,
    set_ai_mode,
)
from app.core.deal_readiness import compute_readiness, fields_from_effective_fields, serialize_readiness
from app.core.draft_agent_assist import build_draft_agent_assist
from app.core.hot_list import refresh_morning_hot_list
from app.db.session import get_db, safe_commit
from app.models.db_models import (
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageMember,
    DBConversation,
    DBDraftReply,
    DBLeadAction,
    DBLeadAssignment,
    DBListing,
    DBMessage,
    DBBrokerageBuyerProfile,
)

router = APIRouter(dependencies=[Depends(capture_requested_brokerage_context)])


class AgentContext(BaseModel):
    brokerage_id: str
    user_id: str
    role: str


class LeadActionCreate(BaseModel):
    action_type: str
    outcome: Optional[str] = None
    note: Optional[str] = None
    payload: dict = {}


class DraftReplyCreate(BaseModel):
    intent: str


class ConversationShareCreate(BaseModel):
    agent_user_id: str
    access_level: str = "viewer"
    reason: Optional[str] = None


class ConversationReassignCreate(BaseModel):
    agent_user_id: str


class AiModeUpdate(BaseModel):
    mode: str  # active | agent_controlled


class ListingMediaSendCreate(BaseModel):
    urls: list[str]
    caption: Optional[str] = None


class NotificationPreferencesUpdate(BaseModel):
    events: Optional[dict[str, bool]] = None
    quiet_hours: Optional[dict[str, str]] = None  # {"start": "22:00", "end": "07:00"}


class BuyerFieldUpdate(BaseModel):
    field: str
    value: object


class OfferCreate(BaseModel):
    conversation_id: str
    amount: float
    direction: str = "buyer_offer"
    conditions: Optional[str] = None
    financing_contingent: bool = False
    subject_to_viewing: bool = False


class OfferConfirm(BaseModel):
    amount: Optional[float] = None


class OfferTransition(BaseModel):
    status: str  # countered | accepted | rejected | withdrawn | expired
    counter_amount: Optional[float] = None
    note: Optional[str] = None


class BrokerageConfigUpdate(BaseModel):
    prompt_config: Optional[dict] = None
    default_fee_framing: Optional[dict] = None
    settings: Optional[dict] = None
    escalation_contact_name: Optional[str] = None
    escalation_contact_title: Optional[str] = None
    escalation_contact_phone: Optional[str] = None


class MatchStatusUpdate(BaseModel):
    status: str


class AgentVoiceNoteCreate(BaseModel):
    audio_url: str
    audio_path: Optional[str] = None
    transcript_text: Optional[str] = None
    content_type: Optional[str] = "audio/ogg"


class InspectionNotesCreate(BaseModel):
    transcript_text: Optional[str] = None
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    audio_path: Optional[str] = None
    content_type: Optional[str] = "audio/webm"
    mode: str = "append"


def _agent_context(user: CurrentUser, db: Session) -> AgentContext:
    context = resolve_request_brokerage_context(
        db,
        user,
        current_requested_brokerage_id(),
    )
    return AgentContext(
        brokerage_id=context.brokerage_id,
        user_id=context.user_id,
        role=context.role or "agent",
    )


def _get_visible_conversation_or_404(
    db: Session,
    *,
    conversation_id: str,
    ctx: AgentContext,
) -> DBConversation:
    conv = db.get(DBConversation, conversation_id)
    if not conv or not can_view_conversation(
        db,
        conv,
        user_id=ctx.user_id,
        brokerage_id=ctx.brokerage_id,
        role=ctx.role,
    ):
        raise HTTPException(status_code=404, detail="Lead not found")
    return conv


def _require_same_brokerage_member(db: Session, *, brokerage_id: str, user_id: str) -> None:
    member = (
        db.query(DBBrokerageMember.member_id)
        .filter(
            DBBrokerageMember.brokerage_id == brokerage_id,
            DBBrokerageMember.user_id == user_id,
            DBBrokerageMember.status == "active",
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Target agent is not an active brokerage member")


def _latest_message(db: Session, conversation_id: str) -> Optional[DBMessage]:
    return (
        db.query(DBMessage)
        .filter(DBMessage.conversation_id == conversation_id)
        .order_by(DBMessage.timestamp.desc())
        .first()
    )


def _agent_profile_for_context(db: Session, ctx: AgentContext) -> Optional[DBAgentProfile]:
    return (
        db.query(DBAgentProfile)
        .filter(
            DBAgentProfile.brokerage_id == ctx.brokerage_id,
            DBAgentProfile.user_id == ctx.user_id,
        )
        .first()
    )


@router.get("/agent/brokerage/config")
async def get_brokerage_config(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    brokerage = db.get(DBBrokerage, ctx.brokerage_id)
    if not brokerage:
        raise HTTPException(status_code=404, detail="Brokerage not found")
    agent = _agent_profile_for_context(db, ctx)
    return serialize_runtime_config(runtime_config_for_brokerage(brokerage, agent=agent))


@router.patch("/agent/brokerage/config")
async def update_brokerage_config(
    body: BrokerageConfigUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    if not is_managing_agent(ctx.role):
        raise HTTPException(status_code=403, detail="Managing-agent access required")
    brokerage = db.get(DBBrokerage, ctx.brokerage_id)
    if not brokerage:
        raise HTTPException(status_code=404, detail="Brokerage not found")

    updated = apply_brokerage_config_update(
        db,
        brokerage,
        prompt_config=body.prompt_config,
        default_fee_framing=body.default_fee_framing,
        settings=body.settings,
        escalation_contact_name=body.escalation_contact_name,
        escalation_contact_title=body.escalation_contact_title,
        escalation_contact_phone=body.escalation_contact_phone,
    )
    record_compliance_event(
        db,
        brokerage_id=ctx.brokerage_id,
        actor_user_id=user.id,
        event_type="brokerage_config_updated",
        direction="system",
        details={
            "prompt_config_keys": sorted((body.prompt_config or {}).keys()),
            "fee_framing_keys": sorted((body.default_fee_framing or {}).keys()),
            "settings_keys": sorted((body.settings or {}).keys()),
            "escalation_contact_updated": any([
                body.escalation_contact_name is not None,
                body.escalation_contact_title is not None,
                body.escalation_contact_phone is not None,
            ]),
        },
    )
    agent = _agent_profile_for_context(db, ctx)
    return serialize_runtime_config(runtime_config_for_brokerage(updated, agent=agent))


@router.get("/agent/notification-preferences")
async def get_notification_preferences(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-agent notification preferences (DAL-162): per-event on/off + quiet hours."""
    from app.core.agent_notifications import EVENT_CATALOG, notification_preferences

    ctx = _agent_context(user, db)
    profile = _agent_profile_for_context(db, ctx)
    prefs = notification_preferences(profile)
    return {
        "events": {
            event_type: prefs["events"].get(event_type, True)
            for event_type in EVENT_CATALOG
        },
        "quiet_hours": prefs["quiet_hours"],
        "catalog": {
            event_type: {"urgency": spec.urgency, "sends_in_quiet_hours": spec.sends_in_quiet_hours}
            for event_type, spec in EVENT_CATALOG.items()
        },
    }


@router.patch("/agent/notification-preferences")
async def update_notification_preferences(
    body: NotificationPreferencesUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.agent_notifications import EVENT_CATALOG

    ctx = _agent_context(user, db)
    profile = _agent_profile_for_context(db, ctx)
    if not profile:
        raise HTTPException(status_code=404, detail="Agent profile not found")

    settings = dict(profile.settings or {})
    prefs = dict(settings.get("notifications") or {})
    if body.events is not None:
        unknown = sorted(set(body.events) - set(EVENT_CATALOG))
        if unknown:
            raise HTTPException(status_code=422, detail=f"Unknown event types: {unknown}")
        events = dict(prefs.get("events") or {})
        events.update(body.events)
        prefs["events"] = events
    if body.quiet_hours is not None:
        quiet = dict(prefs.get("quiet_hours") or {})
        for key in ("start", "end"):
            if key in body.quiet_hours:
                value = str(body.quiet_hours[key])
                try:
                    hour, minute = value.split(":")
                    assert 0 <= int(hour) < 24 and 0 <= int(minute) < 60
                except Exception:
                    raise HTTPException(status_code=422, detail=f"Invalid quiet_hours.{key}: {value!r}")
                quiet[key] = value
        prefs["quiet_hours"] = quiet
    settings["notifications"] = prefs
    profile.settings = settings
    profile.updated_at = datetime.utcnow()
    safe_commit(db)

    from app.core.agent_notifications import notification_preferences

    updated = notification_preferences(profile)
    return {"events": updated["events"], "quiet_hours": updated["quiet_hours"]}


_HOT_LIST_CACHE_TTL = timedelta(minutes=5)


@router.get("/agent/hot-list")
async def hot_list(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Today queue.

    A GET no longer recomputes the whole hot list on every load. If a refresh
    ran for this brokerage within the TTL we serve the cached assignments
    (fast); otherwise we recompute brokerage-wide once, record the run, and then
    read. The explicit `POST /agent/hot-list/refresh` still forces a recompute.
    """
    from sqlalchemy import func

    from app.core.hot_list import ACTIVE_ASSIGNMENT_STATUSES
    from app.models.db_models import DBConversationAccessGrant

    ctx = _agent_context(user, db)
    now = datetime.utcnow()

    # Throttle off the freshest assignment for this brokerage — no extra record to
    # write (and nothing for test teardowns to leak). A recompute upserts
    # assignments, bumping their updated_at, so the next load inside the TTL reads
    # cached. The explicit POST /agent/hot-list/refresh still forces a recompute.
    last_refresh = (
        db.query(func.max(DBLeadAssignment.updated_at))
        .filter(DBLeadAssignment.brokerage_id == ctx.brokerage_id)
        .scalar()
    )
    is_fresh = bool(last_refresh and last_refresh >= now - _HOT_LIST_CACHE_TTL)
    if not is_fresh:
        # Recompute brokerage-wide (user_id=None) so one refresh serves every agent.
        refresh_morning_hot_list(
            db, brokerage_id=ctx.brokerage_id, user_id=None, role="owner", limit=50, now=now
        )

    # ── Read active assignments (cached) and build leads with batched lookups. ──
    assignments = (
        db.query(DBLeadAssignment)
        .filter(
            DBLeadAssignment.brokerage_id == ctx.brokerage_id,
            DBLeadAssignment.status.in_(tuple(ACTIVE_ASSIGNMENT_STATUSES)),
        )
        .all()
    )
    conv_ids = [a.conversation_id for a in assignments]
    convs_by_id: dict = {}
    if conv_ids:
        for c in db.query(DBConversation).filter(DBConversation.conversation_id.in_(conv_ids)).all():
            convs_by_id[c.conversation_id] = c

    managing = is_managing_agent(ctx.role)
    grant_ids: set = set()
    if not managing and conv_ids:
        grant_ids = {
            g.conversation_id
            for g in db.query(DBConversationAccessGrant.conversation_id).filter(
                DBConversationAccessGrant.brokerage_id == ctx.brokerage_id,
                DBConversationAccessGrant.agent_user_id == ctx.user_id,
                DBConversationAccessGrant.active.is_(True),
            ).all()
        }
    listing_owner: dict = {}
    _lids = list({c.listing_id for c in convs_by_id.values() if c.listing_id})
    if _lids:
        for lst in db.query(DBListing.listing_id, DBListing.assigned_agent_id).filter(
            DBListing.listing_id.in_(_lids)
        ).all():
            listing_owner[lst.listing_id] = lst.assigned_agent_id

    def _visible(conv):
        if not conv or conv.brokerage_id != ctx.brokerage_id:
            return False
        if managing:
            return True
        owner = conv.assigned_agent_id or (listing_owner.get(conv.listing_id) if conv.listing_id else None)
        if owner and owner == ctx.user_id:
            return True
        return conv.conversation_id in grant_ids

    visible = [a for a in assignments if _visible(convs_by_id.get(a.conversation_id))]

    vis_conv_ids = [a.conversation_id for a in visible]
    latest_by_conv: dict = {}
    if vis_conv_ids:
        for msg in (
            db.query(DBMessage)
            .filter(DBMessage.conversation_id.in_(vis_conv_ids))
            .order_by(DBMessage.timestamp.desc())
            .all()
        ):
            latest_by_conv.setdefault(msg.conversation_id, msg)
    listings_by_id: dict = {}
    _alids = list({convs_by_id[cid].listing_id for cid in vis_conv_ids
                   if convs_by_id.get(cid) and convs_by_id[cid].listing_id})
    if _alids:
        for lst in db.query(DBListing).filter(DBListing.listing_id.in_(_alids)).all():
            listings_by_id[lst.listing_id] = lst

    leads = []
    for assignment in visible:
        conv = convs_by_id.get(assignment.conversation_id)
        if not conv:
            continue
        latest = latest_by_conv.get(conv.conversation_id)
        listing = listings_by_id.get(conv.listing_id)
        spa = (listing.spa_data or {}) if listing else {}
        metadata = assignment.metadata_json or {}
        hot_list_metadata = metadata.get("hot_list") if isinstance(metadata, dict) else {}

        leads.append({
            "conversation_id": conv.conversation_id,
            "buyer_name": conv.buyer_name,
            "buyer_phone": conv.buyer_phone,
            "listing_id": conv.listing_id,
            "listing_name": spa.get("project", "Unknown listing"),
            "unit_number": spa.get("unit_number", "—"),
            "asking_price_aed": listing.seller_asking_price if listing else None,
            "last_message_at": latest.timestamp.isoformat() if latest else None,
            "last_message_preview": latest.content[:180] if latest else None,
            "signal": assignment.signal,
            "urgency_score": assignment.urgency_score,
            "next_action": assignment.next_action,
            "reason": assignment.next_action_reason,
            "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
            "ai_mode": conversation_ai_mode(conv),
            "readiness_shadow": (hot_list_metadata or {}).get("readiness_shadow"),
        })

    leads.sort(key=lambda item: item["urgency_score"] or 0, reverse=True)
    return {"leads": leads[:25]}


@router.get("/agent/leads/{conversation_id}")
async def lead_detail(
    conversation_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.media_assets import session_window_state

    ctx = _agent_context(user, db)
    conv = _get_visible_conversation_or_404(db, conversation_id=conversation_id, ctx=ctx)

    listing = conv.listing
    spa = (listing.spa_data or {}) if listing else {}
    messages = (
        db.query(DBMessage)
        .filter(DBMessage.conversation_id == conversation_id)
        .order_by(DBMessage.timestamp.asc())
        .all()
    )
    assignment = (
        db.query(DBLeadAssignment)
        .filter(DBLeadAssignment.conversation_id == conversation_id)
        .first()
    )

    return {
        "conversation_id": conv.conversation_id,
        "ai_mode": conversation_ai_mode(conv),
        "ai_mode_changed_at": conv.ai_mode_changed_at.isoformat() if conv.ai_mode_changed_at else None,
        "ai_mode_change_source": conv.ai_mode_change_source,
        "media_window": session_window_state(db, conv.conversation_id),
        "buyer": {
            "name": conv.buyer_name,
            "phone": conv.buyer_phone,
            "budget_aed": conv.detected_budget,
        },
        "listing": {
            "listing_id": conv.listing_id,
            "project": spa.get("project", "Unknown listing"),
            "unit_number": spa.get("unit_number", "—"),
            "price_aed": listing.seller_asking_price if listing else None,
            "bedrooms": spa.get("bedrooms"),
            "property_status": spa.get("property_status"),
        },
        "brief": {
            "summary": conv.ai_summary,
            "suggested_next_action": assignment.next_action if assignment else None,
            "reason": assignment.next_action_reason if assignment else None,
        },
        "timeline": [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "intent": message.intent,
                "metadata": message.metadata_json or {},
                "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            }
            for message in messages
        ],
    }


@router.post("/agent/leads/{conversation_id}/voice-note")
async def send_agent_voice_note(
    conversation_id: str,
    body: AgentVoiceNoteCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    conv = _get_visible_conversation_or_404(db, conversation_id=conversation_id, ctx=ctx)

    brokerage = db.get(DBBrokerage, ctx.brokerage_id)
    if not brokerage or not brokerage.brokerage_ai_number:
        raise HTTPException(status_code=400, detail="Brokerage AI number is not configured")

    transcript = (body.transcript_text or "").strip()
    metadata = {
        "voice_note": {
            "direction": "agent_to_buyer",
            "audio_url": body.audio_url,
            "raw_transcript": transcript,
            "corrected_transcript": transcript,
            "transcript_source": "provided" if transcript else "pending",
        }
    }

    if body.audio_path and not transcript:
        from app.core.transcription.models import TranscriptionContext
        from app.core.voice_notes import transcribe_audio_file, transcription_result_metadata

        listing = conv.listing
        asking_price = None
        if listing:
            spa = listing.spa_data or {}
            asking_price = listing.seller_asking_price or spa.get("purchase_price_aed")
        result = transcribe_audio_file(
            body.audio_path,
            content_type=body.content_type,
            audio_type="agent_reply_voice",
            context=TranscriptionContext(
                listing_id=conv.listing_id,
                asking_price_aed=asking_price,
            ),
        )
        transcript = result.corrected_transcript or result.raw_transcript
        metadata = transcription_result_metadata(
            result,
            direction="agent_to_buyer",
            audio_url=body.audio_url,
        )

    from app.core.messaging import get_transport
    from app.core.messaging.types import OutboundBuyerMessage

    # DAL-159 option B1: deliver the transcript as text. Never forward agent
    # audio from the brokerage's AI number — brand-confusing for the buyer and
    # loses searchable text on the timeline.
    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="Voice note could not be transcribed — nothing was sent. Please type the reply instead.",
        )

    send_result = get_transport().send_to_buyer(
        OutboundBuyerMessage(
            brokerage_id=ctx.brokerage_id,
            brokerage_ai_number=brokerage.brokerage_ai_number,
            buyer_phone=conv.buyer_phone,
            body=transcript,
            conversation_id=conv.conversation_id,
            listing_id=conv.listing_id,
        )
    )
    if not send_result.ok:
        raise HTTPException(status_code=502, detail=send_result.error or "Voice note send failed")

    message = DBMessage(
        conversation_id=conversation_id,
        role="assistant",
        content=transcript or "[Agent voice note]",
        intent="agent_voice_note",
        metadata_json=metadata,
    )
    db.add(message)
    conv.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(message)

    return {
        "message_id": str(message.id),
        "sent": True,
        "transport_message_id": send_result.transport_message_id,
        "transcript": transcript,
        "metadata": metadata,
    }


# ── Buyer card & list (DAL-164) ───────────────────────────────────────────────


def _mask_phone(phone: Optional[str]) -> str:
    """PDPL display rule for list surfaces: keep prefix + last 3 digits."""
    if not phone or len(phone) < 8:
        return phone or ""
    return f"{phone[:6]}•••{phone[-3:]}"


def _visible_profile_or_404(db: Session, *, profile_id: str, ctx: AgentContext):
    from app.models.db_models import DBBrokerageBuyerProfile

    profile = db.get(DBBrokerageBuyerProfile, profile_id)
    if not profile or profile.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Buyer not found")
    # Assignment-level scoping: the agent must be able to view at least one of
    # the buyer's conversations (owners/team leads see brokerage-wide).
    conversations = (
        db.query(DBConversation)
        .filter(
            DBConversation.brokerage_id == ctx.brokerage_id,
            DBConversation.buyer_phone == profile.buyer_phone,
        )
        .all()
    )
    visible = [
        conv for conv in conversations
        if can_view_conversation(db, conv, user_id=ctx.user_id, brokerage_id=ctx.brokerage_id, role=ctx.role)
    ]
    if not visible:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return profile, visible


_READINESS_MISSING = object()


def _buyer_readiness_payload(
    db: Session,
    *,
    profile,
    top_conversation: DBConversation,
    assignment: Optional[DBLeadAssignment] = None,
    open_offers: int = 0,
    has_next_viewing: bool = False,
    effective=_READINESS_MISSING,
    latest_message=_READINESS_MISSING,
    listing=_READINESS_MISSING,
) -> dict:
    # `effective`, `latest_message`, `listing` may be pre-fetched by a batched
    # caller (list_buyers) to avoid an N+1; default sentinels keep single-buyer
    # callers (buyer_card) querying lazily.
    qualification = effective_fields(db, profile) if effective is _READINESS_MISSING else effective
    fields = fields_from_effective_fields(
        qualification,
        fallback_budget_aed=top_conversation.detected_budget,
    )
    if latest_message is _READINESS_MISSING:
        latest = (
            db.query(DBMessage)
            .filter(DBMessage.conversation_id == top_conversation.conversation_id)
            .order_by(DBMessage.timestamp.desc())
            .first()
        )
    else:
        latest = latest_message
    summary = top_conversation.ai_summary or {}
    summary_text = ""
    if isinstance(summary, dict):
        summary_text = " ".join(
            str(value)
            for key in ("summary", "one_line", "key_question", "next_step_hint", "interest_level")
            if (value := summary.get(key))
        ).lower()
    latest_text = (latest.content if latest else "").lower()
    text = f"{latest_text} {summary_text}"
    next_action = assignment.next_action if assignment else None
    conversation_ctx = {
        "viewing_intent": bool(
            has_next_viewing
            or next_action == "book_viewing"
            or (latest and latest.intent == "viewing_request")
            or any(term in text for term in ("viewing", "view the", "see it", "tour"))
        ),
        "offer_intent": bool(
            open_offers
            or next_action == "review_offer"
            or (
                top_conversation.escalation_reason
                and top_conversation.escalation_reason.startswith("offer:")
            )
        ),
        "responsive": bool(latest and latest.role == "user"),
        "urgent": bool((assignment and (assignment.urgency_score or 0) >= 70) or "urgent" in text),
    }
    listing_obj = top_conversation.listing if listing is _READINESS_MISSING else listing
    listing_ctx = (
        {
            "listing_id": listing_obj.listing_id,
            "property_type": listing_obj.property_type,
        }
        if listing_obj
        else (
            {"listing_id": top_conversation.listing_id}
            if top_conversation.listing_id
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


@router.get("/agent/buyers")
async def list_buyers(
    filter: Optional[str] = None,
    sort: str = "score",
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Buyer list (DAL-164): assignment-scoped — agents see their own buyers."""
    from app.core.offers import OPEN_OFFER_STATUSES
    from app.models.db_models import (
        DBBrokerageBuyerProfile,
        DBBuyerSuppression,
        DBOffer,
        DBViewing,
    )

    ctx = _agent_context(user, db)
    profiles = (
        db.query(DBBrokerageBuyerProfile)
        .filter(DBBrokerageBuyerProfile.brokerage_id == ctx.brokerage_id)
        .all()
    )
    now = datetime.utcnow()
    rows = []

    # ── Batch every per-buyer lookup into brokerage-wide queries (no N+1). ──
    from collections import defaultdict
    from sqlalchemy import func
    from app.models.db_models import DBBuyerProfileField, DBConversationAccessGrant

    phones = [p.buyer_phone for p in profiles]
    profile_ids = [p.profile_id for p in profiles]

    convs = (
        db.query(DBConversation)
        .filter(
            DBConversation.brokerage_id == ctx.brokerage_id,
            DBConversation.buyer_phone.in_(phones) if phones else False,
        )
        .order_by(DBConversation.updated_at.desc())
        .all()
    ) if phones else []
    convs_by_phone: dict = defaultdict(list)
    for c in convs:
        convs_by_phone[c.buyer_phone].append(c)

    all_conv_ids = [c.conversation_id for c in convs]
    assignments_by_conv: dict = {}
    if all_conv_ids:
        for a in db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id.in_(all_conv_ids)).all():
            assignments_by_conv.setdefault(a.conversation_id, a)

    # Listing-owner fallback map (preserves conversation_owner_user_id's last resort).
    conv_listing_owner: dict = {}
    _all_listing_ids = list({c.listing_id for c in convs if c.listing_id})
    if _all_listing_ids:
        for lst in db.query(DBListing.listing_id, DBListing.assigned_agent_id).filter(
            DBListing.listing_id.in_(_all_listing_ids)
        ).all():
            conv_listing_owner[lst.listing_id] = lst.assigned_agent_id

    # Visibility: managing agents see all; others by owner==self or an active grant.
    managing = is_managing_agent(ctx.role)
    grant_ids: set = set()
    if not managing and all_conv_ids:
        grant_ids = {
            g.conversation_id
            for g in db.query(DBConversationAccessGrant.conversation_id).filter(
                DBConversationAccessGrant.brokerage_id == ctx.brokerage_id,
                DBConversationAccessGrant.agent_user_id == ctx.user_id,
                DBConversationAccessGrant.active.is_(True),
            ).all()
        }

    def _owner(conv):
        if conv.assigned_agent_id:
            return conv.assigned_agent_id
        a = assignments_by_conv.get(conv.conversation_id)
        if a and a.assigned_agent_id:
            return a.assigned_agent_id
        if conv.listing_id:
            return conv_listing_owner.get(conv.listing_id)
        return None

    def _visible(conv):
        if conv.brokerage_id != ctx.brokerage_id:
            return False
        if managing:
            return True
        owner = _owner(conv)
        if owner and owner == ctx.user_id:
            return True
        return conv.conversation_id in grant_ids

    offers_by_phone = dict(
        db.query(DBOffer.buyer_phone, func.count())
        .filter(
            DBOffer.brokerage_id == ctx.brokerage_id,
            DBOffer.buyer_phone.in_(phones),
            DBOffer.status.in_(OPEN_OFFER_STATUSES),
        )
        .group_by(DBOffer.buyer_phone)
        .all()
    ) if phones else {}

    next_viewing_by_phone: dict = {}
    if phones:
        for v in (
            db.query(DBViewing)
            .filter(
                DBViewing.brokerage_id == ctx.brokerage_id,
                DBViewing.buyer_phone.in_(phones),
                DBViewing.scheduled_for.isnot(None),
                DBViewing.scheduled_for >= now,
                DBViewing.status.in_(["proposed", "confirmed"]),
            )
            .order_by(DBViewing.scheduled_for.asc())
            .all()
        ):
            next_viewing_by_phone.setdefault(v.buyer_phone, v)

    suppressed: set = set()
    if phones:
        suppressed = {
            r.buyer_phone
            for r in db.query(DBBuyerSuppression.buyer_phone).filter(
                DBBuyerSuppression.brokerage_id == ctx.brokerage_id,
                DBBuyerSuppression.buyer_phone.in_(phones),
                DBBuyerSuppression.active.is_(True),
            ).all()
        }

    fields_by_profile: dict = defaultdict(list)
    if profile_ids:
        for fr in db.query(DBBuyerProfileField).filter(DBBuyerProfileField.profile_id.in_(profile_ids)).all():
            fields_by_profile[fr.profile_id].append(fr)

    # Resolve each profile's top (most-recent visible) conversation.
    top_by_profile: dict = {}
    visible_count_by_profile: dict = {}
    for profile in profiles:
        visibles = [c for c in convs_by_phone.get(profile.buyer_phone, []) if _visible(c)]
        visible_count_by_profile[profile.profile_id] = len(visibles)
        if visibles:
            top_by_profile[profile.profile_id] = visibles[0]

    top_conv_ids = [c.conversation_id for c in top_by_profile.values()]
    latest_msg_by_conv: dict = {}
    if top_conv_ids:
        for m in (
            db.query(DBMessage)
            .filter(DBMessage.conversation_id.in_(top_conv_ids))
            .order_by(DBMessage.timestamp.desc())
            .all()
        ):
            latest_msg_by_conv.setdefault(m.conversation_id, m)

    listing_ids = [c.listing_id for c in top_by_profile.values() if c.listing_id]
    listings_by_id: dict = {}
    if listing_ids:
        for lst in db.query(DBListing).filter(DBListing.listing_id.in_(listing_ids)).all():
            listings_by_id[lst.listing_id] = lst

    for profile in profiles:
        top = top_by_profile.get(profile.profile_id)
        if top is None:
            continue
        assignment = assignments_by_conv.get(top.conversation_id)
        open_offers = int(offers_by_phone.get(profile.buyer_phone, 0))
        next_viewing = next_viewing_by_phone.get(profile.buyer_phone)
        opted_out = profile.buyer_phone in suppressed
        fields = effective_fields_from_rows(fields_by_profile.get(profile.profile_id, []))
        listing = listings_by_id.get(top.listing_id)
        deal_readiness = _buyer_readiness_payload(
            db,
            profile=profile,
            top_conversation=top,
            assignment=assignment,
            open_offers=open_offers,
            has_next_viewing=bool(next_viewing),
            effective=fields,
            latest_message=latest_msg_by_conv.get(top.conversation_id),
            listing=listing,
        )
        spa = (listing.spa_data or {}) if listing else {}
        last_activity = top.updated_at
        stale = bool(last_activity and last_activity <= now - timedelta(hours=48))
        row = {
            "profile_id": profile.profile_id,
            "name": profile.name or top.buyer_name,
            "phone_masked": _mask_phone(profile.buyer_phone),
            "top_conversation_id": top.conversation_id,
            "top_listing": spa.get("project"),
            "qualification": {
                "budget_max_aed": (fields.get("budget_max_aed") or {}).get("value"),
                "financing": (fields.get("financing") or {}).get("value"),
                "timeline": (fields.get("timeline") or {}).get("value"),
            },
            "deal_readiness": deal_readiness,
            "score": assignment.urgency_score if assignment else None,
            "last_activity_at": last_activity.isoformat() if last_activity else None,
            "open_offers": open_offers,
            "next_viewing_at": next_viewing.scheduled_for.isoformat() if next_viewing else None,
            "opted_out": opted_out,
            "stale": stale,
            "conversation_count": visible_count_by_profile.get(profile.profile_id, 0),
        }
        if filter == "has_open_offer" and not open_offers:
            continue
        if filter == "viewing_scheduled" and not next_viewing:
            continue
        if filter == "stale" and not stale:
            continue
        rows.append(row)

    if sort == "last_activity":
        rows.sort(key=lambda item: item["last_activity_at"] or "", reverse=True)
    elif sort == "name":
        rows.sort(key=lambda item: (item["name"] or "").lower())
    else:
        rows.sort(key=lambda item: item["score"] or 0, reverse=True)
    return {"buyers": rows, "filters": {"filter": filter, "sort": sort}}


@router.get("/agent/buyers/{profile_id}")
async def buyer_card(
    profile_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The buyer card (DAL-164): identity, provenance-tracked qualification,
    and synced histories read from their source tables."""
    from app.core.offers import serialize_offer
    from app.models.db_models import (
        DBBuyerSuppression,
        DBEscalationThread,
        DBOffer,
        DBViewing,
        DBViewingFeedback,
    )

    ctx = _agent_context(user, db)
    profile, visible = _visible_profile_or_404(db, profile_id=profile_id, ctx=ctx)

    opted_out = (
        db.query(DBBuyerSuppression)
        .filter(
            DBBuyerSuppression.brokerage_id == ctx.brokerage_id,
            DBBuyerSuppression.buyer_phone == profile.buyer_phone,
            DBBuyerSuppression.active.is_(True),
        )
        .count()
        > 0
    )
    viewings = (
        db.query(DBViewing)
        .filter(
            DBViewing.brokerage_id == ctx.brokerage_id,
            DBViewing.buyer_phone == profile.buyer_phone,
        )
        .order_by(DBViewing.scheduled_for.desc().nullslast())
        .all()
    )
    feedback_by_viewing = {}
    if viewings:
        for feedback in (
            db.query(DBViewingFeedback)
            .filter(
                DBViewingFeedback.viewing_id.in_([viewing.viewing_id for viewing in viewings]),
                DBViewingFeedback.participant_type == "buyer",
            )
            .all()
        ):
            feedback_by_viewing[feedback.viewing_id] = feedback
    offers = (
        db.query(DBOffer)
        .filter(
            DBOffer.brokerage_id == ctx.brokerage_id,
            DBOffer.buyer_phone == profile.buyer_phone,
        )
        .order_by(DBOffer.created_at.asc())
        .all()
    )
    escalation_count = (
        db.query(DBEscalationThread)
        .filter(
            DBEscalationThread.brokerage_id == ctx.brokerage_id,
            DBEscalationThread.buyer_phone == profile.buyer_phone,
        )
        .count()
    )

    top_conversation = visible[0]
    assignment = (
        db.query(DBLeadAssignment)
        .filter(DBLeadAssignment.conversation_id == top_conversation.conversation_id)
        .first()
    )
    next_viewing = next(
        (
            viewing
            for viewing in viewings
            if viewing.scheduled_for and viewing.scheduled_for >= datetime.utcnow()
            and viewing.status in {"proposed", "confirmed"}
        ),
        None,
    )

    return {
        "profile_id": profile.profile_id,
        "identity": {
            "name": profile.name,
            "phone": profile.buyer_phone,  # full on the card; masked in lists
            "language": profile.language,
            "source": profile.source,
            "opted_out": opted_out,
        },
        "qualification": effective_fields(db, profile),
        "deal_readiness": _buyer_readiness_payload(
            db,
            profile=profile,
            top_conversation=top_conversation,
            assignment=assignment,
            open_offers=sum(1 for offer in offers if offer.status in {"draft_pending_confirm", "submitted", "countered"}),
            has_next_viewing=bool(next_viewing),
        ),
        "conversations": [
            {
                "conversation_id": conv.conversation_id,
                "listing_id": conv.listing_id,
                "listing": ((conv.listing.spa_data or {}).get("project") if conv.listing else None),
                "ai_summary": conv.ai_summary,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            }
            for conv in visible
        ],
        "viewings": [
            {
                "viewing_id": viewing.viewing_id,
                "listing_id": viewing.listing_id,
                "scheduled_for": viewing.scheduled_for.isoformat() if viewing.scheduled_for else None,
                "status": viewing.status,
                "feedback": (
                    {
                        "score": feedback_by_viewing[viewing.viewing_id].score,
                        "summary": feedback_by_viewing[viewing.viewing_id].summary,
                        "sentiment": feedback_by_viewing[viewing.viewing_id].sentiment,
                    }
                    if viewing.viewing_id in feedback_by_viewing
                    else None
                ),
            }
            for viewing in viewings
        ],
        "offers": [serialize_offer(offer) for offer in offers],
        "escalation_count": escalation_count,
    }


@router.patch("/agent/buyers/{profile_id}/fields")
async def confirm_buyer_field(
    profile_id: str,
    body: BuyerFieldUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Agent edit → agent_confirmed. AI inference can never overwrite this."""
    from app.core.buyer_profiles import QUALIFICATION_FIELDS, confirm_field, effective_fields

    ctx = _agent_context(user, db)
    profile, _ = _visible_profile_or_404(db, profile_id=profile_id, ctx=ctx)
    if body.field not in QUALIFICATION_FIELDS:
        raise HTTPException(status_code=422, detail=f"Unknown field {body.field!r}")
    confirm_field(
        db,
        profile=profile,
        field=body.field,
        value=body.value,
        confirmed_by=ctx.user_id,
    )
    return {"profile_id": profile.profile_id, "qualification": effective_fields(db, profile)}


# ── Offer log (DAL-165) ───────────────────────────────────────────────────────


@router.post("/agent/offers")
async def create_offer(
    body: OfferCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.offers import log_agent_offer, serialize_offer

    ctx = _agent_context(user, db)
    conv = _get_visible_conversation_or_404(db, conversation_id=body.conversation_id, ctx=ctx)
    if body.direction not in {"buyer_offer", "seller_counter"}:
        raise HTTPException(status_code=422, detail="direction must be buyer_offer or seller_counter")
    offer = log_agent_offer(
        db,
        brokerage_id=ctx.brokerage_id,
        conversation=conv,
        listing_id=conv.listing_id,
        agent_user_id=ctx.user_id,
        amount=body.amount,
        direction=body.direction,
        conditions=body.conditions,
        financing_contingent=body.financing_contingent,
        subject_to_viewing=body.subject_to_viewing,
    )
    return serialize_offer(offer)


@router.get("/agent/offers")
async def list_offers(
    conversation_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.offers import serialize_offer
    from app.models.db_models import DBOffer

    ctx = _agent_context(user, db)
    query = db.query(DBOffer).filter(DBOffer.brokerage_id == ctx.brokerage_id)
    if conversation_id:
        conv = _get_visible_conversation_or_404(db, conversation_id=conversation_id, ctx=ctx)
        query = query.filter(DBOffer.conversation_id == conv.conversation_id)
    offers = query.order_by(DBOffer.created_at.asc()).all()
    visible = []
    for offer in offers:
        conv = db.get(DBConversation, offer.conversation_id)
        if conv and can_view_conversation(db, conv, user_id=ctx.user_id, brokerage_id=ctx.brokerage_id, role=ctx.role):
            visible.append(serialize_offer(offer))
    return {"offers": visible}


def _visible_offer_or_404(db: Session, *, offer_id: str, ctx: AgentContext):
    from app.models.db_models import DBOffer

    offer = db.get(DBOffer, offer_id)
    if not offer or offer.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Offer not found")
    conv = db.get(DBConversation, offer.conversation_id)
    if not conv or not can_view_conversation(db, conv, user_id=ctx.user_id, brokerage_id=ctx.brokerage_id, role=ctx.role):
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer


@router.post("/agent/offers/{offer_id}/confirm")
async def confirm_offer(
    offer_id: str,
    body: OfferConfirm,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI proposes, the agent disposes — DRAFT_PENDING_CONFIRM → SUBMITTED."""
    from app.core.offers import confirm_draft_offer, serialize_offer

    ctx = _agent_context(user, db)
    offer = _visible_offer_or_404(db, offer_id=offer_id, ctx=ctx)
    try:
        confirm_draft_offer(db, offer=offer, agent_user_id=ctx.user_id, amount=body.amount)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return serialize_offer(offer)


@router.post("/agent/offers/{offer_id}/discard")
async def discard_offer(
    offer_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.offers import discard_draft_offer, serialize_offer

    ctx = _agent_context(user, db)
    offer = _visible_offer_or_404(db, offer_id=offer_id, ctx=ctx)
    try:
        discard_draft_offer(db, offer=offer, agent_user_id=ctx.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return serialize_offer(offer)


@router.post("/agent/offers/{offer_id}/transition")
async def transition_offer_endpoint(
    offer_id: str,
    body: OfferTransition,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.offers import serialize_offer, transition_offer

    ctx = _agent_context(user, db)
    offer = _visible_offer_or_404(db, offer_id=offer_id, ctx=ctx)
    try:
        result = transition_offer(
            db,
            offer=offer,
            new_status=body.status,
            agent_user_id=ctx.user_id,
            counter_amount=body.counter_amount,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return serialize_offer(result)


@router.post("/agent/leads/{conversation_id}/media")
async def send_conversation_media_endpoint(
    conversation_id: str,
    files: list[UploadFile] = File(...),
    caption: str = Form(default=""),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dashboard composer media (DAL-160): upload PDF/JPEG/PNG attachments and
    send them into the buyer conversation. Validation (type, per-transport
    size limit, attachment cap, 24h session window) happens before anything
    is sent — nothing is partially delivered on a validation failure.
    """
    from app.core.media_assets import (
        MAX_ATTACHMENTS_PER_SEND,
        MediaValidationError,
        SessionWindowClosedError,
        send_conversation_media,
        session_window_state,
        store_media_asset,
        validate_media_upload,
    )

    ctx = _agent_context(user, db)
    conv = _get_visible_conversation_or_404(db, conversation_id=conversation_id, ctx=ctx)
    brokerage = db.get(DBBrokerage, ctx.brokerage_id)
    if not brokerage or not brokerage.brokerage_ai_number:
        raise HTTPException(status_code=400, detail="Brokerage AI number is not configured")

    if len(files) > MAX_ATTACHMENTS_PER_SEND:
        raise HTTPException(
            status_code=422,
            detail=f"Too many attachments ({len(files)}). Limit is {MAX_ATTACHMENTS_PER_SEND} per send.",
        )

    # Validate everything up front so an oversize file means nothing sends.
    payloads: list[tuple[bytes, str, Optional[str]]] = []
    for upload in files:
        content = await upload.read()
        mime_type = upload.content_type or "application/octet-stream"
        try:
            validate_media_upload(mime_type=mime_type, size_bytes=len(content))
        except MediaValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        payloads.append((content, mime_type, upload.filename))

    window = session_window_state(db, conv.conversation_id)
    if not window["open"]:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "session_window_closed",
                "message": (
                    "The buyer's 24-hour session window is closed. Use the "
                    "template-first reopen flow before sending media."
                ),
                "last_inbound_at": window["last_inbound_at"],
            },
        )

    assets = [
        store_media_asset(
            db,
            brokerage_id=ctx.brokerage_id,
            agent_user_id=ctx.user_id,
            conversation_id=conv.conversation_id,
            listing_id=conv.listing_id,
            content=content,
            mime_type=mime_type,
            original_filename=filename,
            source="composer_upload",
        )
        for content, mime_type, filename in payloads
    ]

    try:
        outcome = send_conversation_media(
            db,
            brokerage=brokerage,
            conversation=conv,
            agent_user_id=ctx.user_id,
            assets=assets,
            caption=caption,
            source="dashboard_composer",
        )
    except SessionWindowClosedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "session_window_closed",
                "last_inbound_at": exc.last_inbound_at.isoformat() if exc.last_inbound_at else None,
            },
        )
    except MediaValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "message_id": outcome.message_id,
        "sent": True,
        "attachments": outcome.sent_assets,
        "caption": outcome.caption,
    }


@router.post("/agent/leads/{conversation_id}/media/from-listing")
async def send_listing_media_endpoint(
    conversation_id: str,
    body: ListingMediaSendCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Attach-from-listing (DAL-160): re-send the listing's already-in-system
    brochure/photos without re-uploading per buyer — the 80% case.
    """
    from app.core.media_assets import (
        MediaValidationError,
        SessionWindowClosedError,
        listing_assets_for_attachment,
        register_external_media_asset,
        send_conversation_media,
    )

    ctx = _agent_context(user, db)
    conv = _get_visible_conversation_or_404(db, conversation_id=conversation_id, ctx=ctx)
    brokerage = db.get(DBBrokerage, ctx.brokerage_id)
    if not brokerage or not brokerage.brokerage_ai_number:
        raise HTTPException(status_code=400, detail="Brokerage AI number is not configured")

    listing = db.get(DBListing, conv.listing_id)
    if not listing or listing.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Listing not found")

    allowed_urls = {item["url"] for item in listing_assets_for_attachment(db, listing)}
    requested = [url for url in body.urls if url]
    if not requested:
        raise HTTPException(status_code=422, detail="No listing assets selected.")
    invalid = [url for url in requested if url not in allowed_urls]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail="Selected assets do not belong to this listing.",
        )

    assets = [
        register_external_media_asset(
            db,
            brokerage_id=ctx.brokerage_id,
            agent_user_id=ctx.user_id,
            conversation_id=conv.conversation_id,
            listing_id=conv.listing_id,
            url=url,
            source="listing_asset",
        )
        for url in requested
    ]
    try:
        outcome = send_conversation_media(
            db,
            brokerage=brokerage,
            conversation=conv,
            agent_user_id=ctx.user_id,
            assets=assets,
            caption=body.caption or "",
            source="listing_asset",
        )
    except SessionWindowClosedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "session_window_closed",
                "last_inbound_at": exc.last_inbound_at.isoformat() if exc.last_inbound_at else None,
            },
        )
    except MediaValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "message_id": outcome.message_id,
        "sent": True,
        "attachments": outcome.sent_assets,
        "caption": outcome.caption,
    }


@router.get("/agent/listings/{listing_id}/assets")
async def get_listing_attachable_assets(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Listing media available to attach-from-listing (brokerage-scoped)."""
    from app.core.media_assets import listing_assets_for_attachment

    ctx = _agent_context(user, db)
    listing = db.get(DBListing, listing_id)
    if not listing or listing.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"listing_id": listing_id, "assets": listing_assets_for_attachment(db, listing)}


@router.post("/agent/leads/{conversation_id}/ai-mode")
async def set_conversation_ai_mode(
    conversation_id: str,
    body: AiModeUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Live takeover toggle (DAL-158). Pausing (active → agent_controlled) is
    confirmation-free; the dangerous direction is resuming, which the UI
    confirms before calling this endpoint.
    """
    ctx = _agent_context(user, db)
    conv = _get_visible_conversation_or_404(db, conversation_id=conversation_id, ctx=ctx)
    if body.mode not in AI_MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of {sorted(AI_MODES)}")

    result = set_ai_mode(
        db,
        conv,
        mode=body.mode,
        actor_user_id=ctx.user_id,
        source="dashboard",
    )
    return {
        "conversation_id": conv.conversation_id,
        "ai_mode": conversation_ai_mode(conv),
        "ai_mode_changed_at": conv.ai_mode_changed_at.isoformat() if conv.ai_mode_changed_at else None,
        "ai_mode_change_source": conv.ai_mode_change_source,
        "changed": result["changed"],
        "snoozed_draft_ids": result["snoozed_draft_ids"],
    }


@router.post("/agent/leads/{conversation_id}/actions")
async def create_action(
    conversation_id: str,
    body: LeadActionCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    conv = _get_visible_conversation_or_404(db, conversation_id=conversation_id, ctx=ctx)

    action = DBLeadAction(
        brokerage_id=ctx.brokerage_id,
        conversation_id=conversation_id,
        listing_id=conv.listing_id,
        buyer_phone=conv.buyer_phone,
        agent_user_id=user.id,
        action_type=body.action_type,
        outcome=body.outcome,
        note=body.note,
        payload=body.payload,
    )
    db.add(action)
    safe_commit(db)
    db.refresh(action)
    return {"action_id": action.action_id, "created_at": action.created_at.isoformat()}


@router.post("/agent/leads/{conversation_id}/draft-reply")
async def create_draft_reply(
    conversation_id: str,
    body: DraftReplyCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    conv = _get_visible_conversation_or_404(db, conversation_id=conversation_id, ctx=ctx)

    buyer_name = conv.buyer_name or "there"
    templates = {
        "follow_up": f"Hi {buyer_name}, just checking if you would still like to move forward on this property.",
        "viewing_slots": f"Hi {buyer_name}, I can help arrange a viewing. What time window works best for you today or tomorrow?",
        "budget_clarification": f"Hi {buyer_name}, before I recommend next steps, can you confirm your target budget and whether you are cash or mortgage-backed?",
        "offer_ack": f"Hi {buyer_name}, noted. I am reviewing the offer context now and will come back with the right next step.",
    }
    draft_text = templates.get(body.intent, templates["follow_up"])
    latest_buyer_message = (
        db.query(DBMessage)
        .filter(
            DBMessage.conversation_id == conversation_id,
            DBMessage.role == "user",
        )
        .order_by(DBMessage.timestamp.desc())
        .first()
    )
    profile = (
        db.query(DBBrokerageBuyerProfile)
        .filter(
            DBBrokerageBuyerProfile.brokerage_id == ctx.brokerage_id,
            DBBrokerageBuyerProfile.buyer_phone == conv.buyer_phone,
        )
        .first()
    )
    qualification = effective_fields(db, profile) if profile else {}
    latest_text = (latest_buyer_message.content if latest_buyer_message else "").lower()
    agent_assist = build_draft_agent_assist(
        latest_buyer_message=latest_buyer_message.content if latest_buyer_message else None,
        effective_buyer_fields=qualification,
        fallback_budget_aed=conv.detected_budget,
        conversation_ctx={
            "viewing_intent": bool(
                body.intent == "viewing_slots"
                or (latest_buyer_message and latest_buyer_message.intent == "viewing_request")
                or any(term in latest_text for term in ("viewing", "view the", "see it", "tour"))
            ),
            "offer_intent": bool(
                body.intent == "offer_ack"
                or (
                    conv.escalation_reason
                    and conv.escalation_reason.startswith("offer:")
                )
            ),
            "responsive": bool(latest_buyer_message),
            "urgent": any(term in latest_text for term in ("urgent", "asap", "serious")),
            "legal_question": any(term in latest_text for term in ("legal", "law", "lawyer")),
        },
        listing_ctx={"listing_id": conv.listing_id},
        brokerage_id=ctx.brokerage_id,
    )

    draft = DBDraftReply(
        brokerage_id=ctx.brokerage_id,
        conversation_id=conversation_id,
        listing_id=conv.listing_id,
        buyer_phone=conv.buyer_phone,
        agent_user_id=user.id,
        intent=body.intent,
        draft_text=draft_text,
        source="template",
        status="draft",
        metadata_json={
            "created_from": "agent_api",
            "created_at": datetime.utcnow().isoformat(),
            "agent_assist": agent_assist,
        },
    )
    db.add(draft)
    safe_commit(db)
    db.refresh(draft)
    return {
        "draft_id": draft.draft_id,
        "draft": draft.draft_text,
        "source": draft.source,
        "metadata": draft.metadata_json,
        "requires_review": True,
    }


@router.post("/agent/leads/{conversation_id}/shares")
async def share_conversation(
    conversation_id: str,
    body: ConversationShareCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    if not is_managing_agent(ctx.role):
        raise HTTPException(status_code=403, detail="Managing-agent access required")

    conv = _get_visible_conversation_or_404(db, conversation_id=conversation_id, ctx=ctx)
    _require_same_brokerage_member(db, brokerage_id=ctx.brokerage_id, user_id=body.agent_user_id)
    grant = grant_conversation_access(
        db,
        conversation=conv,
        agent_user_id=body.agent_user_id,
        granted_by_user_id=user.id,
        access_level=body.access_level,
        reason=body.reason,
    )
    return {
        "grant_id": grant.grant_id,
        "conversation_id": grant.conversation_id,
        "agent_user_id": grant.agent_user_id,
        "access_level": grant.access_level,
        "reason": grant.reason,
        "active": grant.active,
    }


@router.post("/agent/leads/{conversation_id}/reassign")
async def reassign_conversation_route(
    conversation_id: str,
    body: ConversationReassignCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    if not is_managing_agent(ctx.role):
        raise HTTPException(status_code=403, detail="Managing-agent access required")

    conv = _get_visible_conversation_or_404(db, conversation_id=conversation_id, ctx=ctx)
    _require_same_brokerage_member(db, brokerage_id=ctx.brokerage_id, user_id=body.agent_user_id)
    updated = reassign_conversation(
        db,
        conversation=conv,
        new_agent_user_id=body.agent_user_id,
        assigned_by_user_id=user.id,
    )
    return {
        "conversation_id": updated.conversation_id,
        "assigned_agent_id": updated.assigned_agent_id,
        "updated_at": updated.updated_at.isoformat() if updated.updated_at else None,
    }


@router.get("/agent/listings/{listing_id}/buyer-matches")
async def listing_buyer_matches(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    listing = db.get(DBListing, listing_id)
    if not listing or listing.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Listing not found")

    from app.core.remarketing import (
        generate_buyer_matches_for_listing,
        list_buyer_matches_for_listing,
        serialize_buyer_match,
    )

    matches = list_buyer_matches_for_listing(
        db,
        listing_id=listing_id,
        brokerage_id=ctx.brokerage_id,
        limit=5,
    )
    if not matches:
        matches = generate_buyer_matches_for_listing(db, listing=listing, limit=5)

    return {
        "listing_id": listing_id,
        "matches": [serialize_buyer_match(match) for match in matches],
    }


@router.patch("/agent/listings/{listing_id}/buyer-matches/{match_id}")
async def update_listing_buyer_match(
    listing_id: str,
    match_id: str,
    body: MatchStatusUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.status not in {"draft", "copied", "dismissed", "sent_external"}:
        raise HTTPException(status_code=400, detail="Unsupported match status")

    ctx = _agent_context(user, db)
    from app.models.db_models import DBBuyerListingMatch

    match = db.get(DBBuyerListingMatch, match_id)
    if (
        not match
        or match.listing_id != listing_id
        or match.brokerage_id != ctx.brokerage_id
    ):
        raise HTTPException(status_code=404, detail="Buyer match not found")

    match.status = body.status
    match.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(match)
    return {"match_id": match.match_id, "status": match.status}


@router.get("/agent/listings/{listing_id}/unit-profile")
async def get_listing_unit_profile(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    listing = db.get(DBListing, listing_id)
    if not listing or listing.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {
        "listing_id": listing_id,
        "unit_profile": listing.unit_profile or {},
        "history": listing.unit_profile_history or [],
    }


@router.post("/agent/listings/{listing_id}/inspection-notes")
async def add_listing_inspection_notes(
    listing_id: str,
    body: InspectionNotesCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    listing = db.get(DBListing, listing_id)
    if not listing or listing.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Listing not found")
    if body.mode not in {"append", "replace"}:
        raise HTTPException(status_code=400, detail="mode must be append or replace")
    if not any([body.transcript_text, body.audio_base64, body.audio_path]):
        raise HTTPException(status_code=400, detail="Provide transcript_text, audio_base64, or audio_path")

    transcript = (body.transcript_text or "").strip()
    transcription_metadata: dict = {}
    temp_path: Optional[Path] = None
    try:
        if not transcript:
            from app.core.transcription.models import TranscriptionContext
            from app.core.voice_notes import transcribe_audio_file, transcription_result_metadata

            audio_path = body.audio_path
            if body.audio_base64:
                suffix = _audio_suffix(body.content_type)
                fd, temp_name = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                temp_path = Path(temp_name)
                temp_path.write_bytes(base64.b64decode(body.audio_base64))
                audio_path = str(temp_path)
            if not audio_path:
                raise HTTPException(status_code=400, detail="No audio data provided")

            spa = listing.spa_data or {}
            result = transcribe_audio_file(
                audio_path,
                content_type=body.content_type,
                audio_type="agent_property_dictation",
                context=TranscriptionContext(
                    listing_id=listing_id,
                    asking_price_aed=listing.seller_asking_price or spa.get("purchase_price_aed"),
                ),
            )
            transcript = result.corrected_transcript or result.raw_transcript
            transcription_metadata = transcription_result_metadata(
                result,
                direction="agent_listing_dictation",
                audio_url=body.audio_url,
            )

        from app.core.unit_profile import (
            UnitProfileStructurer,
            append_unit_profile_history,
        )

        existing_profile = {} if body.mode == "replace" else dict(listing.unit_profile or {})
        structured = UnitProfileStructurer().structure(
            transcript,
            existing_profile=existing_profile,
        )
        listing.unit_profile = structured.model_dump()
        listing.unit_profile_history = append_unit_profile_history(
            listing.unit_profile_history or [],
            transcript=transcript,
            structured_profile=structured,
            source="voice_dictation" if not body.transcript_text else "transcript_text",
            agent_user_id=user.id,
            audio_url=body.audio_url,
            transcription_metadata=transcription_metadata.get("voice_note") or transcription_metadata,
        )
        safe_commit(db)
        db.refresh(listing)
        return {
            "listing_id": listing_id,
            "transcript": transcript,
            "unit_profile": listing.unit_profile or {},
            "history_count": len(listing.unit_profile_history or []),
        }
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def _audio_suffix(content_type: Optional[str]) -> str:
    content_type = (content_type or "").split(";")[0].lower()
    return {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/opus": ".opus",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/wav": ".wav",
    }.get(content_type, ".webm")
