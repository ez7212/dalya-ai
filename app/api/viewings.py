from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.brokerage_access import (
    can_view_conversation,
    capture_requested_brokerage_context,
    current_requested_brokerage_id,
    is_managing_agent,
    record_compliance_event,
    resolve_request_brokerage_context,
)
from app.core.google_calendar import (
    CalendarProviderError,
    calendar_provider,
    connected_google_connection,
    new_oauth_state,
)
from app.core.post_viewing_capture import (
    record_agent_post_viewing_feedback,
    request_due_post_viewing_feedback,
    request_post_viewing_feedback,
    serialize_post_viewing_feedback,
)
from app.core.tenant_viewings import send_tenant_viewing_notice
from app.core.viewing_lifecycle import (
    complete_due_viewings,
    mark_viewing_completed,
    send_viewing_notification,
)
from app.core.viewing_logistics import (
    build_logistics_prefill,
    confirm_viewing,
    create_viewing_proposal,
    generate_pre_viewing_brief,
    get_listing_logistics,
    logistics_summary,
    propose_viewing_slots,
    redact_logistics,
    store_notification_drafts,
    upsert_listing_logistics,
)
from app.db.session import get_db, safe_commit
from app.models.db_models import (
    DBAgentAvailabilityBlock,
    DBAgentCalendarConnection,
    DBBrokerageMember,
    DBConversation,
    DBListing,
    DBBrokerage,
    DBTenantViewingConfirmation,
    DBViewing,
)

router = APIRouter(dependencies=[Depends(capture_requested_brokerage_context)])


class AgentContext(BaseModel):
    brokerage_id: str
    user_id: str
    role: str


class LogisticsUpdate(BaseModel):
    access: Optional[dict] = None
    keys: Optional[dict] = None
    tenant: Optional[dict] = None
    owner_permissions: Optional[dict] = None
    confirmed: bool = True


class AvailabilityBlockCreate(BaseModel):
    block_type: str = "working_hours"
    weekday: Optional[int] = None
    date: Optional[str] = None
    start_time: str
    end_time: str
    timezone: str = "Asia/Dubai"
    recurring: bool = False
    label: Optional[str] = None
    active: bool = True
    metadata_json: dict = {}


class CalendarConnectionUpdate(BaseModel):
    provider: str = "google"
    status: str = "not_connected"
    selected_calendar_ids: list[str] = []
    sync_direction: str = "read_freebusy_write_viewings"
    token_ref: Optional[str] = None
    scopes: list[str] = []
    settings: dict = {}


class CalendarOAuthUrlRequest(BaseModel):
    provider: str = "google"
    redirect_uri: str


class CalendarOAuthCallback(BaseModel):
    provider: str = "google"
    code: str
    state: str
    redirect_uri: str
    token_ref: Optional[str] = None


class ViewingProposalCreate(BaseModel):
    count: int = 3
    origin_community: Optional[str] = None
    pair_lookup: dict = {}
    duration_minutes: int = 45


class ViewingConfirm(BaseModel):
    scheduled_for: datetime
    duration_minutes: int = 45


class ViewingCancel(BaseModel):
    reason: Optional[str] = None


class NotificationDraftCreate(BaseModel):
    draft_types: Optional[list[str]] = None


class TenantNoticeSend(BaseModel):
    body: Optional[str] = None


class ViewingNotificationSend(BaseModel):
    body: Optional[str] = None


class CompleteDueViewingsRequest(BaseModel):
    brokerage_only: bool = True


class PostViewingDueRequest(BaseModel):
    brokerage_only: bool = True


class AgentPostViewingFeedbackSubmit(BaseModel):
    raw_body: str
    score: Optional[int] = None
    temperature: Optional[str] = None
    financing_status: Optional[str] = None
    next_action: Optional[str] = None


class ConfirmationStatusUpdate(BaseModel):
    buyer: Optional[str] = None
    tenant: Optional[str] = None
    calendar: Optional[str] = None


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


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


def _listing_or_404(db: Session, listing_id: str, ctx: AgentContext) -> DBListing:
    listing = db.get(DBListing, listing_id)
    if not listing or listing.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


def _conversation_or_404(db: Session, conversation_id: str, ctx: AgentContext) -> DBConversation:
    conversation = db.get(DBConversation, conversation_id)
    if not conversation or not can_view_conversation(
        db,
        conversation,
        user_id=ctx.user_id,
        brokerage_id=ctx.brokerage_id,
        role=ctx.role,
    ):
        raise HTTPException(status_code=404, detail="Lead not found")
    return conversation


def _viewing_or_404(db: Session, viewing_id: str, ctx: AgentContext) -> DBViewing:
    viewing = db.get(DBViewing, viewing_id)
    if not viewing or viewing.brokerage_id != ctx.brokerage_id:
        raise HTTPException(status_code=404, detail="Viewing not found")
    conversation = db.get(DBConversation, viewing.conversation_id)
    if not conversation or not can_view_conversation(
        db,
        conversation,
        user_id=ctx.user_id,
        brokerage_id=ctx.brokerage_id,
        role=ctx.role,
    ):
        raise HTTPException(status_code=404, detail="Viewing not found")
    return viewing


def _brokerage_or_404(db: Session, brokerage_id: str) -> DBBrokerage:
    brokerage = db.get(DBBrokerage, brokerage_id)
    if not brokerage:
        raise HTTPException(status_code=404, detail="Brokerage not found")
    return brokerage


def _can_view_tenant_pii(ctx: AgentContext, listing: DBListing, logistics_agent_user_id: Optional[str]) -> bool:
    return (
        is_managing_agent(ctx.role)
        or listing.assigned_agent_id == ctx.user_id
        or logistics_agent_user_id == ctx.user_id
    )


def _serialize_availability(block: DBAgentAvailabilityBlock) -> dict:
    return {
        "block_id": block.block_id,
        "block_type": block.block_type,
        "weekday": block.weekday,
        "date": block.date,
        "start_time": block.start_time,
        "end_time": block.end_time,
        "timezone": block.timezone,
        "recurring": block.recurring,
        "label": block.label,
        "active": block.active,
        "metadata_json": block.metadata_json or {},
    }


def _serialize_calendar(connection: DBAgentCalendarConnection) -> dict:
    return {
        "connection_id": connection.connection_id,
        "provider": connection.provider,
        "status": connection.status,
        "selected_calendar_ids": connection.selected_calendar_ids or [],
        "sync_direction": connection.sync_direction,
        "token_ref": connection.token_ref,
        "scopes": connection.scopes or [],
        "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
        "settings": connection.settings or {},
    }


def _calendar_connection(db: Session, ctx: AgentContext, provider: str = "google") -> Optional[DBAgentCalendarConnection]:
    return (
        db.query(DBAgentCalendarConnection)
        .filter(
            DBAgentCalendarConnection.brokerage_id == ctx.brokerage_id,
            DBAgentCalendarConnection.agent_user_id == ctx.user_id,
            DBAgentCalendarConnection.provider == provider,
        )
        .first()
    )


def _calendar_busy_windows(
    db: Session,
    ctx: AgentContext,
    *,
    time_min: datetime,
    time_max: datetime,
) -> tuple[list[tuple[datetime, datetime]], dict]:
    connection = _calendar_connection(db, ctx, "google")
    if not connected_google_connection(connection):
        return [], {"status": "not_connected"}
    try:
        busy = calendar_provider().freebusy(connection, time_min=time_min, time_max=time_max)
    except CalendarProviderError as exc:
        return [], {"status": "error", "error": str(exc)}
    connection.last_sync_at = datetime.utcnow()
    connection.updated_at = datetime.utcnow()
    safe_commit(db)
    return [(item.starts_at, item.ends_at) for item in busy], {
        "status": "connected",
        "busy_count": len(busy),
        "calendar_ids": list({item.calendar_id for item in busy}),
    }


def _sync_viewing_calendar_event(
    db: Session,
    ctx: AgentContext,
    *,
    viewing: DBViewing,
    listing: DBListing,
    conversation: DBConversation,
    scheduled_for: datetime,
    duration_minutes: int,
) -> dict:
    connection = _calendar_connection(db, ctx, "google")
    if not connected_google_connection(connection):
        return {"status": "not_connected"}
    existing = ((viewing.metadata_json or {}).get("calendar_event") or {})
    try:
        event = calendar_provider().upsert_viewing_event(
            connection,
            viewing=viewing,
            listing=listing,
            conversation=conversation,
            scheduled_for=scheduled_for,
            duration_minutes=duration_minutes,
            existing_event_id=existing.get("event_id"),
        )
    except CalendarProviderError as exc:
        return {"status": "error", "error": str(exc)}
    connection.last_sync_at = datetime.utcnow()
    connection.updated_at = datetime.utcnow()
    safe_commit(db)
    return {"status": "synced", "event": event}


def _delete_viewing_calendar_event(
    db: Session,
    ctx: AgentContext,
    *,
    viewing: DBViewing,
) -> dict:
    connection = _calendar_connection(db, ctx, "google")
    existing = ((viewing.metadata_json or {}).get("calendar_event") or {})
    event_id = existing.get("event_id")
    if not event_id:
        return {"status": "not_required"}
    if not connected_google_connection(connection):
        return {"status": "not_connected", "event": existing}
    try:
        deleted = calendar_provider().delete_viewing_event(
            connection,
            event_id=event_id,
            calendar_id=existing.get("calendar_id"),
        )
    except CalendarProviderError as exc:
        return {"status": "error", "error": str(exc), "event": existing}
    connection.last_sync_at = datetime.utcnow()
    connection.updated_at = datetime.utcnow()
    safe_commit(db)
    return {"status": "deleted", "event": deleted}


def _serialize_viewing_row(db: Session, viewing: DBViewing) -> dict:
    listing = db.get(DBListing, viewing.listing_id)
    conversation = db.get(DBConversation, viewing.conversation_id)
    spa = (listing.spa_data or {}) if listing else {}
    metadata = viewing.metadata_json or {}
    return {
        "viewing_id": viewing.viewing_id,
        "conversation_id": viewing.conversation_id,
        "listing_id": viewing.listing_id,
        "buyer_phone": viewing.buyer_phone,
        "buyer_name": conversation.buyer_name if conversation else None,
        "agent_user_id": viewing.agent_user_id,
        "scheduled_for": _iso(viewing.scheduled_for),
        "status": viewing.status,
        "tenant_notice_required": viewing.tenant_notice_required,
        "listing": {
            "project": spa.get("project"),
            "unit_number": spa.get("unit_number"),
            "property_type": spa.get("property_type"),
        },
        "confirmation_status": metadata.get("confirmation_status") or {},
        "calendar_event": metadata.get("calendar_event") or None,
        "notification_drafts": list((metadata.get("notification_drafts") or {}).values()),
        "post_viewing": serialize_post_viewing_feedback(db, viewing),
        "proposed_slots": metadata.get("proposed_slots") or [],
        "logistics_summary": metadata.get("logistics_summary") or {},
        "created_at": _iso(viewing.created_at),
        "updated_at": _iso(viewing.updated_at),
    }


def _serialize_viewing_detail(db: Session, viewing: DBViewing, ctx: AgentContext) -> dict:
    listing = _listing_or_404(db, viewing.listing_id, ctx)
    conversation = _conversation_or_404(db, viewing.conversation_id, ctx)
    logistics = get_listing_logistics(db, listing.listing_id, ctx.brokerage_id)
    spa = listing.spa_data or {}
    metadata = viewing.metadata_json or {}
    can_view_tenant_pii = _can_view_tenant_pii(ctx, listing, logistics.agent_user_id if logistics else None)
    follow_up_cta_enabled = os.getenv("FEATURE_FOLLOWUP_DRAFT_CTA", "false").strip().lower() in {"1", "true", "yes", "on"}
    return {
        **_serialize_viewing_row(db, viewing),
        # DAL-166: flag off → CTA absent, no behavior change.
        "follow_up_draft_cta_enabled": follow_up_cta_enabled,
        "buyer": {
            "name": conversation.buyer_name,
            "phone": conversation.buyer_phone,
            "budget_aed": conversation.detected_budget,
            "summary": conversation.ai_summary or {},
        },
        "listing": {
            "listing_id": listing.listing_id,
            "project": spa.get("project"),
            "unit_number": spa.get("unit_number"),
            "developer": spa.get("developer"),
            "property_type": spa.get("property_type"),
            "bedrooms": spa.get("bedrooms"),
            "asking_price_aed": listing.seller_asking_price or spa.get("purchase_price_aed"),
        },
        "logistics": redact_logistics(logistics, can_view_tenant_pii=can_view_tenant_pii) if logistics else None,
        "logistics_summary": logistics_summary(logistics),
        "confirmation_status": metadata.get("confirmation_status") or {},
        "notification_drafts": list((metadata.get("notification_drafts") or {}).values()),
        "proposed_slots": metadata.get("proposed_slots") or [],
        "tenant_confirmation": _serialize_tenant_confirmation(
            db.query(DBTenantViewingConfirmation)
            .filter(DBTenantViewingConfirmation.viewing_id == viewing.viewing_id)
            .order_by(DBTenantViewingConfirmation.created_at.desc())
            .first()
        ),
    }


def _serialize_tenant_confirmation(row: Optional[DBTenantViewingConfirmation]) -> Optional[dict]:
    if not row:
        return None
    return {
        "confirmation_id": row.confirmation_id,
        "viewing_id": row.viewing_id,
        "listing_id": row.listing_id,
        "status": row.status,
        "tenant_contact_key": row.tenant_contact_key,
        "tenant_phone": row.tenant_phone,
        "notice_body": row.notice_body,
        "outbound_message_id": row.outbound_message_id,
        "last_inbound_body": row.last_inbound_body,
        "metadata_json": row.metadata_json or {},
        "sent_at": _iso(row.sent_at),
        "responded_at": _iso(row.responded_at),
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


@router.get("/agent/listings/{listing_id}/logistics/prefill")
async def listing_logistics_prefill(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    listing = _listing_or_404(db, listing_id, ctx)
    return build_logistics_prefill(db, listing)


@router.get("/agent/listings/{listing_id}/logistics")
async def get_logistics(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    listing = _listing_or_404(db, listing_id, ctx)
    logistics = get_listing_logistics(db, listing_id, ctx.brokerage_id)
    if not logistics:
        return {
            "listing_id": listing_id,
            "logistics": None,
            "prefill": build_logistics_prefill(db, listing),
        }
    return {
        "listing_id": listing_id,
        "logistics": redact_logistics(
            logistics,
            can_view_tenant_pii=_can_view_tenant_pii(ctx, listing, logistics.agent_user_id),
        ),
        "prefill": build_logistics_prefill(db, listing),
    }


@router.patch("/agent/listings/{listing_id}/logistics")
async def update_logistics(
    listing_id: str,
    body: LogisticsUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    listing = _listing_or_404(db, listing_id, ctx)
    try:
        logistics = upsert_listing_logistics(
            db,
            listing=listing,
            brokerage_id=ctx.brokerage_id,
            agent_user_id=ctx.user_id,
            access=body.access,
            keys=body.keys,
            tenant=body.tenant,
            owner_permissions=body.owner_permissions,
            confirmed=body.confirmed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "listing_id": listing_id,
        "logistics": redact_logistics(
            logistics,
            can_view_tenant_pii=_can_view_tenant_pii(ctx, listing, logistics.agent_user_id),
        ),
    }


@router.get("/agent/availability-blocks")
async def list_availability_blocks(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    blocks = (
        db.query(DBAgentAvailabilityBlock)
        .filter(
            DBAgentAvailabilityBlock.brokerage_id == ctx.brokerage_id,
            DBAgentAvailabilityBlock.agent_user_id == ctx.user_id,
        )
        .order_by(DBAgentAvailabilityBlock.weekday.asc().nullslast(), DBAgentAvailabilityBlock.start_time.asc())
        .all()
    )
    return {"blocks": [_serialize_availability(block) for block in blocks]}


@router.post("/agent/availability-blocks")
async def create_availability_block(
    body: AvailabilityBlockCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    if body.weekday is None and body.date is None:
        raise HTTPException(status_code=400, detail="weekday or date is required")
    block = DBAgentAvailabilityBlock(
        brokerage_id=ctx.brokerage_id,
        agent_user_id=ctx.user_id,
        block_type=body.block_type,
        weekday=body.weekday,
        date=body.date,
        start_time=body.start_time,
        end_time=body.end_time,
        timezone=body.timezone,
        recurring=body.recurring,
        label=body.label,
        active=body.active,
        metadata_json=body.metadata_json,
    )
    db.add(block)
    safe_commit(db)
    db.refresh(block)
    return _serialize_availability(block)


@router.get("/agent/calendar-connection")
async def get_calendar_connection(
    provider: str = "google",
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    connection = (
        db.query(DBAgentCalendarConnection)
        .filter(
            DBAgentCalendarConnection.brokerage_id == ctx.brokerage_id,
            DBAgentCalendarConnection.agent_user_id == ctx.user_id,
            DBAgentCalendarConnection.provider == provider,
        )
        .first()
    )
    if not connection:
        return {
            "provider": provider,
            "status": "not_connected",
            "selected_calendar_ids": [],
            "sync_direction": "read_freebusy_write_viewings",
            "scopes": ["calendar.freebusy", "calendar.events.owned"],
            "settings": {},
        }
    return _serialize_calendar(connection)


@router.patch("/agent/calendar-connection")
async def update_calendar_connection(
    body: CalendarConnectionUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    connection = (
        db.query(DBAgentCalendarConnection)
        .filter(
            DBAgentCalendarConnection.brokerage_id == ctx.brokerage_id,
            DBAgentCalendarConnection.agent_user_id == ctx.user_id,
            DBAgentCalendarConnection.provider == body.provider,
        )
        .first()
    )
    if not connection:
        connection = DBAgentCalendarConnection(
            brokerage_id=ctx.brokerage_id,
            agent_user_id=ctx.user_id,
            provider=body.provider,
        )
        db.add(connection)
    connection.status = body.status
    connection.selected_calendar_ids = body.selected_calendar_ids
    connection.sync_direction = body.sync_direction
    connection.token_ref = body.token_ref
    connection.scopes = body.scopes
    connection.settings = body.settings
    connection.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(connection)
    return _serialize_calendar(connection)


@router.post("/agent/calendar-connection/oauth-url")
async def create_calendar_oauth_url(
    body: CalendarOAuthUrlRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    state = new_oauth_state()
    connection = _calendar_connection(db, ctx, body.provider)
    if not connection:
        connection = DBAgentCalendarConnection(
            brokerage_id=ctx.brokerage_id,
            agent_user_id=ctx.user_id,
            provider=body.provider,
            status="not_connected",
            selected_calendar_ids=["primary"],
            scopes=["calendar.freebusy", "calendar.events.owned"],
        )
        db.add(connection)
    connection.settings = {
        **(connection.settings or {}),
        "oauth_state": state,
        "oauth_state_created_at": datetime.utcnow().isoformat(),
        "redirect_uri": body.redirect_uri,
    }
    connection.updated_at = datetime.utcnow()
    safe_commit(db)
    try:
        authorization_url = calendar_provider().authorization_url(
            state=state,
            redirect_uri=body.redirect_uri,
        )
    except CalendarProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "provider": body.provider,
        "state": state,
        "authorization_url": authorization_url,
    }


@router.post("/agent/calendar-connection/oauth-callback")
async def complete_calendar_oauth(
    body: CalendarOAuthCallback,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    connection = _calendar_connection(db, ctx, body.provider)
    if not connection:
        raise HTTPException(status_code=404, detail="Calendar connection not found")
    expected_state = (connection.settings or {}).get("oauth_state")
    if not expected_state or body.state != expected_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    try:
        token_payload = calendar_provider().exchange_code(
            code=body.code,
            redirect_uri=body.redirect_uri,
        )
    except CalendarProviderError as exc:
        connection.status = "error"
        connection.settings = {**(connection.settings or {}), "oauth_error": str(exc)}
        connection.updated_at = datetime.utcnow()
        safe_commit(db)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token_ref = body.token_ref or f"vault:google-calendar:{connection.connection_id}"
    connection.status = "connected"
    connection.token_ref = token_ref
    connection.selected_calendar_ids = connection.selected_calendar_ids or ["primary"]
    connection.scopes = connection.scopes or ["calendar.freebusy", "calendar.events.owned"]
    connection.settings = {
        **(connection.settings or {}),
        "oauth_state": None,
        "oauth_completed_at": datetime.utcnow().isoformat(),
        "token_ref_storage_required": body.token_ref is None,
        "token_payload_keys": sorted(token_payload.keys()),
        "expires_in": token_payload.get("expires_in"),
        "scope": token_payload.get("scope"),
    }
    connection.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(connection)
    return {
        **_serialize_calendar(connection),
        "token_storage_required": body.token_ref is None,
    }


@router.get("/agent/viewings")
async def list_agent_viewings(
    status: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    query = db.query(DBViewing).filter(DBViewing.brokerage_id == ctx.brokerage_id)
    if status:
        query = query.filter(DBViewing.status == status)
    else:
        query = query.filter(DBViewing.status.in_(["proposed", "confirmed", "completed"]))
    rows = (
        query
        .order_by(DBViewing.scheduled_for.asc().nullslast(), DBViewing.created_at.desc())
        .limit(50)
        .all()
    )
    visible = []
    for viewing in rows:
        conversation = db.get(DBConversation, viewing.conversation_id)
        if conversation and can_view_conversation(
            db,
            conversation,
            user_id=ctx.user_id,
            brokerage_id=ctx.brokerage_id,
            role=ctx.role,
        ):
            visible.append(_serialize_viewing_row(db, viewing))
    return {"viewings": visible}


@router.get("/agent/viewings/{viewing_id}")
async def get_agent_viewing(
    viewing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    return _serialize_viewing_detail(db, viewing, ctx)


@router.post("/agent/leads/{conversation_id}/viewings/propose")
async def propose_lead_viewing(
    conversation_id: str,
    body: ViewingProposalCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    conversation = _conversation_or_404(db, conversation_id, ctx)
    listing = _listing_or_404(db, conversation.listing_id, ctx)
    logistics = get_listing_logistics(db, listing.listing_id, ctx.brokerage_id)
    now = datetime.utcnow().replace(second=0, microsecond=0)
    busy_windows, calendar_lookup = _calendar_busy_windows(
        db,
        ctx,
        time_min=now,
        time_max=now + timedelta(days=21),
    )
    slots = propose_viewing_slots(
        db,
        brokerage_id=ctx.brokerage_id,
        agent_user_id=ctx.user_id,
        listing=listing,
        logistics=logistics,
        now=now,
        count=max(1, min(body.count, 5)),
        duration_minutes=body.duration_minutes,
        origin_community=body.origin_community,
        pair_lookup=body.pair_lookup,
        external_busy_windows=busy_windows,
    )
    viewing = create_viewing_proposal(
        db,
        conversation=conversation,
        listing=listing,
        agent_user_id=ctx.user_id,
        slots=slots,
    )
    record_compliance_event(
        db,
        brokerage_id=ctx.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=listing.listing_id,
        buyer_phone=conversation.buyer_phone,
        actor_user_id=ctx.user_id,
        event_type="viewing_slots_proposed",
        direction="system",
        details={"slot_count": len(slots), "viewing_id": viewing.viewing_id},
    )
    return {
        "viewing_id": viewing.viewing_id,
        "status": viewing.status,
        "slots": [slot.as_dict() for slot in slots],
        "calendar": calendar_lookup,
    }


@router.post("/agent/viewings/{viewing_id}/confirm")
async def confirm_agent_viewing(
    viewing_id: str,
    body: ViewingConfirm,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    listing = _listing_or_404(db, viewing.listing_id, ctx)
    conversation = _conversation_or_404(db, viewing.conversation_id, ctx)
    logistics = get_listing_logistics(db, listing.listing_id, ctx.brokerage_id)
    viewing = confirm_viewing(
        db,
        viewing=viewing,
        scheduled_for=body.scheduled_for,
        logistics=logistics,
        confirmed_by_user_id=ctx.user_id,
    )
    calendar_result = _sync_viewing_calendar_event(
        db,
        ctx,
        viewing=viewing,
        listing=listing,
        conversation=conversation,
        scheduled_for=body.scheduled_for,
        duration_minutes=body.duration_minutes,
    )
    metadata = dict(viewing.metadata_json or {})
    confirmation_status = dict(metadata.get("confirmation_status") or {})
    if calendar_result.get("status") == "synced":
        confirmation_status["calendar"] = "synced"
        metadata["calendar_event"] = calendar_result.get("event")
    elif calendar_result.get("status") == "not_connected":
        confirmation_status["calendar"] = "not_connected"
    else:
        confirmation_status["calendar"] = "error"
        metadata["calendar_error"] = calendar_result.get("error")
    metadata["confirmation_status"] = confirmation_status
    metadata["duration_minutes"] = body.duration_minutes
    viewing.metadata_json = metadata
    viewing.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(viewing)
    record_compliance_event(
        db,
        brokerage_id=ctx.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        actor_user_id=ctx.user_id,
        event_type="viewing_confirmed",
        direction="system",
        details={
            "viewing_id": viewing.viewing_id,
            "scheduled_for": body.scheduled_for.isoformat(),
            "calendar_status": confirmation_status.get("calendar"),
            "calendar_event_id": (metadata.get("calendar_event") or {}).get("event_id"),
        },
    )
    return {
        "viewing_id": viewing.viewing_id,
        "status": viewing.status,
        "scheduled_for": viewing.scheduled_for.isoformat() if viewing.scheduled_for else None,
        "tenant_notice_required": viewing.tenant_notice_required,
        "metadata": viewing.metadata_json or {},
    }


@router.post("/agent/viewings/{viewing_id}/cancel")
async def cancel_agent_viewing(
    viewing_id: str,
    body: ViewingCancel,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    calendar_result = _delete_viewing_calendar_event(db, ctx, viewing=viewing)
    metadata = dict(viewing.metadata_json or {})
    confirmation_status = dict(metadata.get("confirmation_status") or {})
    if calendar_result.get("status") == "deleted":
        confirmation_status["calendar"] = "deleted"
        metadata["calendar_event_deleted"] = calendar_result.get("event")
    elif calendar_result.get("status") == "not_required":
        confirmation_status["calendar"] = confirmation_status.get("calendar") or "not_required"
    elif calendar_result.get("status") == "not_connected":
        confirmation_status["calendar"] = "delete_pending"
    else:
        confirmation_status["calendar"] = "delete_error"
        metadata["calendar_delete_error"] = calendar_result.get("error")
    viewing.status = "cancelled"
    viewing.metadata_json = {
        **metadata,
        "confirmation_status": confirmation_status,
        "cancel_reason": body.reason,
        "cancelled_by_user_id": ctx.user_id,
        "cancelled_at": datetime.utcnow().isoformat(),
    }
    viewing.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(viewing)
    record_compliance_event(
        db,
        brokerage_id=ctx.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        actor_user_id=ctx.user_id,
        event_type="viewing_cancelled",
        direction="system",
        details={
            "viewing_id": viewing.viewing_id,
            "reason": body.reason,
            "calendar_status": confirmation_status.get("calendar"),
        },
    )
    return {
        "viewing_id": viewing.viewing_id,
        "status": viewing.status,
        "confirmation_status": confirmation_status,
        "metadata": viewing.metadata_json or {},
    }


@router.post("/agent/viewings/{viewing_id}/notification-drafts")
async def create_viewing_notification_drafts(
    viewing_id: str,
    body: NotificationDraftCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    listing = _listing_or_404(db, viewing.listing_id, ctx)
    conversation = _conversation_or_404(db, viewing.conversation_id, ctx)
    logistics = get_listing_logistics(db, listing.listing_id, ctx.brokerage_id)
    drafts = store_notification_drafts(
        db,
        viewing=viewing,
        conversation=conversation,
        listing=listing,
        logistics=logistics,
        draft_types=body.draft_types,
        actor_user_id=ctx.user_id,
    )
    return {
        "viewing_id": viewing.viewing_id,
        "drafts": drafts,
        "auto_sent": False,
    }


@router.post("/agent/viewings/{viewing_id}/tenant-notice/send")
async def send_viewing_tenant_notice(
    viewing_id: str,
    body: TenantNoticeSend,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    listing = _listing_or_404(db, viewing.listing_id, ctx)
    conversation = _conversation_or_404(db, viewing.conversation_id, ctx)
    logistics = get_listing_logistics(db, listing.listing_id, ctx.brokerage_id)
    brokerage = _brokerage_or_404(db, ctx.brokerage_id)
    try:
        confirmation = send_tenant_viewing_notice(
            db,
            brokerage=brokerage,
            viewing=viewing,
            conversation=conversation,
            listing=listing,
            logistics=logistics,
            actor_user_id=ctx.user_id,
            body_override=body.body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "viewing_id": viewing.viewing_id,
        "tenant_confirmation": _serialize_tenant_confirmation(confirmation),
        "confirmation_status": (viewing.metadata_json or {}).get("confirmation_status") or {},
        "notification_drafts": list(((viewing.metadata_json or {}).get("notification_drafts") or {}).values()),
    }


@router.post("/agent/viewings/{viewing_id}/notifications/{draft_type}/send")
async def send_viewing_notification_draft(
    viewing_id: str,
    draft_type: str,
    body: ViewingNotificationSend,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    listing = _listing_or_404(db, viewing.listing_id, ctx)
    conversation = _conversation_or_404(db, viewing.conversation_id, ctx)
    logistics = get_listing_logistics(db, listing.listing_id, ctx.brokerage_id)
    brokerage = _brokerage_or_404(db, ctx.brokerage_id)
    try:
        result = send_viewing_notification(
            db,
            brokerage=brokerage,
            viewing=viewing,
            conversation=conversation,
            listing=listing,
            logistics=logistics,
            draft_type=draft_type,
            actor_user_id=ctx.user_id,
            body_override=body.body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "viewing_id": viewing.viewing_id,
        **result,
        "notification_drafts": list(((viewing.metadata_json or {}).get("notification_drafts") or {}).values()),
    }


@router.post("/agent/viewings/{viewing_id}/complete")
async def complete_agent_viewing(
    viewing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    brokerage = _brokerage_or_404(db, ctx.brokerage_id)
    viewing = mark_viewing_completed(
        db,
        brokerage=brokerage,
        viewing=viewing,
        actor_user_id=ctx.user_id,
    )
    return _serialize_viewing_detail(db, viewing, ctx)


@router.post("/agent/viewings/{viewing_id}/feedback/request")
async def request_viewing_feedback(
    viewing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    listing = _listing_or_404(db, viewing.listing_id, ctx)
    conversation = _conversation_or_404(db, viewing.conversation_id, ctx)
    brokerage = _brokerage_or_404(db, ctx.brokerage_id)
    try:
        viewing = request_post_viewing_feedback(
            db,
            brokerage=brokerage,
            viewing=viewing,
            conversation=conversation,
            listing=listing,
            actor_user_id=ctx.user_id,
            force=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_viewing_detail(db, viewing, ctx)


@router.post("/agent/viewings/{viewing_id}/feedback/agent")
async def submit_agent_viewing_feedback(
    viewing_id: str,
    body: AgentPostViewingFeedbackSubmit,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    brokerage = _brokerage_or_404(db, ctx.brokerage_id)
    feedback = record_agent_post_viewing_feedback(
        db,
        brokerage=brokerage,
        viewing=viewing,
        actor_user_id=ctx.user_id,
        raw_body=body.raw_body,
        score=body.score,
        temperature=body.temperature,
        financing_status=body.financing_status,
        next_action=body.next_action,
    )
    return {
        "viewing_id": viewing.viewing_id,
        "feedback_id": feedback.feedback_id,
        "post_viewing": serialize_post_viewing_feedback(db, viewing),
    }


@router.post("/agent/viewings/{viewing_id}/feedback/draft-follow-up")
async def draft_follow_up_from_feedback(
    viewing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    DAL-166 (flagged optional): one CTA on received feedback → a review-only
    draft into the existing queue, grounded on the feedback, the buyer card's
    confirmed qualification, and up to 3 same-brokerage alternatives (simple
    filter match — never padded with weak matches). Reuses the entire draft
    approve/edit/send machinery; no new send paths.
    """
    import os as _os

    if (_os.getenv("FEATURE_FOLLOWUP_DRAFT_CTA", "false").strip().lower()
            not in {"1", "true", "yes", "on"}):
        raise HTTPException(status_code=404, detail="Feature not enabled")

    from app.core.post_viewing_followup import create_feedback_follow_up_draft

    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    try:
        draft = create_feedback_follow_up_draft(
            db,
            brokerage_id=ctx.brokerage_id,
            viewing=viewing,
            agent_user_id=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "draft_id": draft.draft_id,
        "draft_text": draft.draft_text,
        "status": draft.status,
        "alternatives": (draft.metadata_json or {}).get("alternative_listing_ids", []),
    }


@router.post("/agent/viewings/complete-due")
async def complete_due_agent_viewings(
    body: CompleteDueViewingsRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    rows = complete_due_viewings(
        db,
        brokerage_id=ctx.brokerage_id if body.brokerage_only else None,
    )
    visible = []
    for viewing in rows:
        conversation = db.get(DBConversation, viewing.conversation_id)
        if conversation and can_view_conversation(
            db,
            conversation,
            user_id=ctx.user_id,
            brokerage_id=ctx.brokerage_id,
            role=ctx.role,
        ):
            visible.append(_serialize_viewing_row(db, viewing))
    return {"completed_count": len(rows), "viewings": visible}


@router.post("/agent/viewings/post-viewing/request-due")
async def request_due_agent_post_viewing_feedback(
    body: PostViewingDueRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    rows = request_due_post_viewing_feedback(
        db,
        brokerage_id=ctx.brokerage_id if body.brokerage_only else None,
    )
    visible = []
    for viewing in rows:
        conversation = db.get(DBConversation, viewing.conversation_id)
        if conversation and can_view_conversation(
            db,
            conversation,
            user_id=ctx.user_id,
            brokerage_id=ctx.brokerage_id,
            role=ctx.role,
        ):
            visible.append(_serialize_viewing_row(db, viewing))
    return {"requested_count": len(rows), "viewings": visible}


@router.patch("/agent/viewings/{viewing_id}/confirmation-status")
async def update_viewing_confirmation_status(
    viewing_id: str,
    body: ConfirmationStatusUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    status = dict((viewing.metadata_json or {}).get("confirmation_status") or {})
    for key in ("buyer", "tenant", "calendar"):
        value = getattr(body, key)
        if value is not None:
            status[key] = value
    viewing.metadata_json = {
        **(viewing.metadata_json or {}),
        "confirmation_status": status,
    }
    viewing.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(viewing)
    record_compliance_event(
        db,
        brokerage_id=ctx.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        actor_user_id=ctx.user_id,
        event_type="viewing_confirmation_status_updated",
        direction="system",
        details={"viewing_id": viewing.viewing_id, "confirmation_status": status},
    )
    return {"viewing_id": viewing.viewing_id, "confirmation_status": status}


@router.get("/agent/viewings/{viewing_id}/brief")
async def viewing_brief(
    viewing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = _agent_context(user, db)
    viewing = _viewing_or_404(db, viewing_id, ctx)
    conversation = _conversation_or_404(db, viewing.conversation_id, ctx)
    listing = _listing_or_404(db, viewing.listing_id, ctx)
    logistics = get_listing_logistics(db, listing.listing_id, ctx.brokerage_id)
    return generate_pre_viewing_brief(
        db,
        viewing=viewing,
        conversation=conversation,
        listing=listing,
        logistics=logistics,
    )
