"""
WhatsApp agent relay media routing (DAL-161) — the 5-PDF problem.

Routing precedence, explicit to implicit:

  1. Caption token   — `#TOKEN` in the caption/body routes immediately to that
                       conversation. Typos fall through; never fuzzy-matched.
  2. Quote-reply     — routes immediately and opens/refreshes a ref session
                       (handled by agent_relay for text/voice; here for media).
  3. Active session  — unquoted, untagged messages within 10 minutes of session
                       activity route to the session conversation, HELD 30s
                       with a recipient-naming ack. UNDO cancels held items.
  4. Single open media_requested escalation — exactly one qualifying thread
                       (open/updated, alerted < 48h) captures unrouted media,
                       held 30s with a basis-stating ack.

No tier matches → media is PARKED (60s burst batches, one routing prompt per
batch, 30-minute expiry with a discard notice); non-media messages bounce
asking for a quote or #REF caption. Never guess beyond tier 4's exactly-one
rule.

Caption hygiene: forwarded media (`Forwarded` webhook param) has its caption
stripped by default — a forwarded caption can carry another buyer's name or
internal pricing (PDPL exposure). Directly-sent media keeps its caption minus
any routed #TOKEN.

Every send records its routing method on the timeline/compliance event:
caption_token | quote_reply | session | escalation_match | parking_prompt.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.brokerage_access import record_compliance_event
from app.core.escalation_threads import OPEN_THREAD_STATES, thread_media_requested
from app.core.messaging import get_transport
from app.core.messaging.types import InboundEnvelope, OutboundAgentMessage
from app.db.session import safe_commit
from app.models.db_models import (
    DBAgentMessageRoute,
    DBAgentRelaySession,
    DBBrokerage,
    DBConversation,
    DBEscalationThread,
    DBMediaAsset,
    DBMessage,
    DBRelayOutboxItem,
)

logger = logging.getLogger(__name__)

SESSION_ACTIVITY_WINDOW = timedelta(minutes=10)
IMPLICIT_HOLD_SECONDS = int(os.getenv("RELAY_IMPLICIT_HOLD_SECONDS", "30"))
PARKED_EXPIRY = timedelta(minutes=30)
PARKED_BURST_WINDOW = timedelta(seconds=60)
MEDIA_REQUEST_FRESHNESS = timedelta(hours=48)

CAPTION_TOKEN_PATTERN = re.compile(r"#(?:REF[:\-\s]?)?([A-Za-z0-9]{6,16})\b", re.IGNORECASE)


@dataclass
class RelayRoutingResult:
    status: str
    handled: bool = True
    routing_method: Optional[str] = None
    conversation_id: Optional[str] = None
    item_ids: list[str] = field(default_factory=list)
    relay_text_after: bool = False  # quote-reply batch answers also relay their text
    details: dict = field(default_factory=dict)


def _normalize_phone(number: Optional[str]) -> str:
    if not number:
        return ""
    cleaned = number.strip()
    if cleaned.lower().startswith("whatsapp:"):
        cleaned = cleaned[len("whatsapp:"):]
    return cleaned


def _notify_agent(
    brokerage: DBBrokerage,
    *,
    agent_phone: str,
    body: str,
    conversation_id: str = "",
    listing_id: str = "",
    buyer_phone: str = "",
    envelope_token: Optional[str] = None,
) -> None:
    if not (brokerage.agents_ai_number and agent_phone):
        return
    get_transport().send_to_agents_ai(
        OutboundAgentMessage(
            brokerage_id=brokerage.brokerage_id,
            agents_ai_number=brokerage.agents_ai_number,
            agent_phone=agent_phone,
            body=body,
            conversation_id=conversation_id,
            listing_id=listing_id,
            buyer_phone=buyer_phone,
            escalation_type="relay_routing_notice",
            envelope_token=envelope_token,
        )
    )


def _conversation_label(db: Session, conversation: DBConversation) -> str:
    from app.models.db_models import DBListing

    buyer = conversation.buyer_name or conversation.buyer_phone
    listing = db.get(DBListing, conversation.listing_id) if conversation.listing_id else None
    spa = (listing.spa_data or {}) if listing else {}
    project = spa.get("project") or "listing"
    unit = spa.get("unit_number")
    listing_label = f"{project} {unit}".strip() if unit else project
    return f"{buyer} ({listing_label})"


def _dashboard_link(brokerage: DBBrokerage, conversation_id: Optional[str]) -> str:
    base = ""
    if isinstance(brokerage.settings, dict):
        base = str(brokerage.settings.get("dashboard_url") or "")
    base = (base or os.getenv("DASHBOARD_BASE_URL", "")).rstrip("/")
    path = f"/agent/conversations/{conversation_id}" if conversation_id else "/agent"
    return f"{base}{path}" if base else path


# ── Sessions (tier 2 opens, tier 3 consumes) ───────────────────────────────────


def active_session(
    db: Session,
    *,
    brokerage_id: str,
    agent_phone: str,
    now: Optional[datetime] = None,
) -> Optional[DBAgentRelaySession]:
    now = now or datetime.utcnow()
    session = (
        db.query(DBAgentRelaySession)
        .filter(
            DBAgentRelaySession.brokerage_id == brokerage_id,
            DBAgentRelaySession.agent_phone == agent_phone,
            DBAgentRelaySession.status == "active",
        )
        .order_by(DBAgentRelaySession.last_activity_at.desc())
        .first()
    )
    if not session:
        return None
    if session.last_activity_at < now - SESSION_ACTIVITY_WINDOW:
        session.status = "closed"
        session.closed_reason = "expired"
        return None
    return session


def open_or_refresh_session(
    db: Session,
    *,
    brokerage_id: str,
    agent_user_id: Optional[str],
    agent_phone: str,
    conversation_id: str,
    listing_id: Optional[str],
    buyer_phone: str,
    now: Optional[datetime] = None,
) -> DBAgentRelaySession:
    """
    Quote-reply semantics (tier 2): opens/refreshes the ref session; a quote to
    a DIFFERENT ref closes the old session. Closing a session must not
    re-route its in-flight items — held items keep their conversation.
    """
    now = now or datetime.utcnow()
    sessions = (
        db.query(DBAgentRelaySession)
        .filter(
            DBAgentRelaySession.brokerage_id == brokerage_id,
            DBAgentRelaySession.agent_phone == agent_phone,
            DBAgentRelaySession.status == "active",
        )
        .all()
    )
    current = None
    for session in sessions:
        if session.conversation_id == conversation_id:
            current = session
        else:
            session.status = "closed"
            session.closed_reason = "superseded"
    if current:
        current.last_activity_at = now
        current.expires_at = now + SESSION_ACTIVITY_WINDOW
        return current

    session = DBAgentRelaySession(
        brokerage_id=brokerage_id,
        agent_user_id=agent_user_id,
        agent_phone=agent_phone,
        conversation_id=conversation_id,
        listing_id=listing_id,
        buyer_phone=buyer_phone,
        status="active",
        opened_at=now,
        last_activity_at=now,
        expires_at=now + SESSION_ACTIVITY_WINDOW,
    )
    db.add(session)
    return session


# ── Inbound media persistence ──────────────────────────────────────────────────


def _is_audio(content_type: str, url: str) -> bool:
    if (content_type or "").lower().startswith("audio/"):
        return True
    return bool(re.search(r"\.(ogg|opus|mp3|m4a|wav|aac|flac)$", (url or "").lower()))


def _inbound_media_items(inbound: InboundEnvelope) -> list[tuple[str, str]]:
    """Non-audio media (url, content_type) — audio is the voice-reply flow."""
    items = []
    for index, url in enumerate(inbound.media_urls):
        content_type = (
            inbound.media_content_types[index]
            if index < len(inbound.media_content_types)
            else ""
        )
        if not _is_audio(content_type, url):
            items.append((url, content_type or "application/octet-stream"))
    return items


def _is_forwarded(inbound: InboundEnvelope) -> bool:
    raw = inbound.raw or {}
    forwarded = raw.get("Forwarded") or raw.get("forwarded")
    if isinstance(forwarded, str):
        return forwarded.strip().lower() == "true"
    if isinstance(forwarded, bool):
        return forwarded
    context = raw.get("context")
    if isinstance(context, dict):
        return bool(context.get("forwarded"))
    return False


def _store_inbound_media(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound: InboundEnvelope,
    agent_user_id: Optional[str],
) -> list[DBMediaAsset]:
    from app.core.media_assets import store_media_asset
    from app.core.voice_notes import download_media_to_tempfile_sync, twilio_media_auth

    assets: list[DBMediaAsset] = []
    for url, content_type in _inbound_media_items(inbound):
        try:
            path = download_media_to_tempfile_sync(
                url,
                content_type=content_type,
                auth=twilio_media_auth() if url.startswith("http") else None,
            )
            content = path.read_bytes()
        except Exception as exc:
            logger.warning("Relay media download failed for %s: %s", url, exc)
            continue
        assets.append(store_media_asset(
            db,
            brokerage_id=brokerage.brokerage_id,
            agent_user_id=agent_user_id,
            conversation_id=None,
            listing_id=None,
            content=content,
            mime_type=content_type,
            original_filename=url.rsplit("/", 1)[-1][:120] or None,
            source="relay_inbound",
        ))
    return assets


def _clean_caption(inbound: InboundEnvelope, *, strip_all: bool) -> str:
    """Caption hygiene (DAL-161): forwards are stripped; #TOKEN always removed."""
    if strip_all:
        return ""
    body = inbound.body or ""
    body = re.sub(r"\s*\[Ref:\s*[A-Za-z0-9]{6,16}\]\s*", " ", body, flags=re.IGNORECASE)
    body = CAPTION_TOKEN_PATTERN.sub(" ", body)
    return re.sub(r"\s+", " ", body).strip()


# ── Item creation + delivery ───────────────────────────────────────────────────


def _create_item(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound: InboundEnvelope,
    asset: Optional[DBMediaAsset],
    body: str,
    status: str,
    routing_method: Optional[str],
    conversation: Optional[DBConversation],
    agent_user_id: Optional[str],
    release_at: Optional[datetime] = None,
    parked_batch_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> DBRelayOutboxItem:
    item = DBRelayOutboxItem(
        brokerage_id=brokerage.brokerage_id,
        agent_user_id=agent_user_id,
        agent_phone=_normalize_phone(inbound.from_number),
        conversation_id=conversation.conversation_id if conversation else None,
        listing_id=conversation.listing_id if conversation else None,
        buyer_phone=conversation.buyer_phone if conversation else None,
        media_asset_id=asset.media_asset_id if asset else None,
        body=body,
        status=status,
        routing_method=routing_method,
        release_at=release_at,
        parked_batch_id=parked_batch_id,
        metadata_json={
            **(metadata or {}),
            "message_sid": inbound.message_sid,
            "forwarded": _is_forwarded(inbound),
        },
    )
    db.add(item)
    if asset and conversation:
        asset.conversation_id = conversation.conversation_id
        asset.listing_id = conversation.listing_id
    return item


def _deliver_item(
    db: Session,
    *,
    brokerage: DBBrokerage,
    item: DBRelayOutboxItem,
    now: Optional[datetime] = None,
) -> bool:
    """
    Send a routed relay item. The 24h-window check runs per item (interleaved
    buyers can have different window states); a closed window bounces back to
    the agent with the reason and a dashboard deep link.
    """
    from app.core.media_assets import (
        MediaValidationError,
        SessionWindowClosedError,
        send_conversation_media,
    )

    now = now or datetime.utcnow()
    conversation = db.get(DBConversation, item.conversation_id) if item.conversation_id else None
    if not conversation:
        item.status = "cancelled"
        item.cancelled_reason = "conversation_missing"
        return False

    try:
        if item.media_asset_id:
            asset = db.get(DBMediaAsset, item.media_asset_id)
            send_conversation_media(
                db,
                brokerage=brokerage,
                conversation=conversation,
                agent_user_id=item.agent_user_id,
                assets=[asset],
                caption=item.body or "",
                source="whatsapp_relay",
                routing_method=item.routing_method,
                now=now,
            )
        else:
            # Tier-3 text hold: plain relay of the agent's words.
            from app.core.messaging.types import OutboundBuyerMessage

            send_result = get_transport().send_to_buyer(
                OutboundBuyerMessage(
                    brokerage_id=brokerage.brokerage_id,
                    brokerage_ai_number=brokerage.brokerage_ai_number,
                    buyer_phone=conversation.buyer_phone,
                    body=item.body or "",
                    conversation_id=conversation.conversation_id,
                    listing_id=conversation.listing_id,
                )
            )
            if not send_result.ok:
                raise MediaValidationError(send_result.error or "transport send failed")
            db.add(DBMessage(
                conversation_id=conversation.conversation_id,
                role="assistant",
                content=item.body or "",
                intent="agent_relay",
                metadata_json={
                    "source": "whatsapp_relay_session",
                    "agent_user_id": item.agent_user_id,
                    "routing_method": item.routing_method,
                },
            ))
            conversation.updated_at = now
            record_compliance_event(
                db,
                brokerage_id=brokerage.brokerage_id,
                conversation_id=conversation.conversation_id,
                listing_id=conversation.listing_id,
                buyer_phone=conversation.buyer_phone,
                actor_user_id=item.agent_user_id,
                event_type="agent_reply_relayed",
                direction="outbound",
                details={
                    "routing_method": item.routing_method,
                    "body_preview": (item.body or "")[:200],
                    "source": "whatsapp_relay_session",
                },
            )
    except SessionWindowClosedError:
        item.status = "cancelled"
        item.cancelled_reason = "session_window_closed"
        _notify_agent(
            brokerage,
            agent_phone=item.agent_phone,
            body=(
                f"Couldn't deliver to {_conversation_label(db, conversation)} — their 24-hour "
                "session window is closed. Reopen it from the dashboard: "
                f"{_dashboard_link(brokerage, conversation.conversation_id)}"
            ),
        )
        return False
    except MediaValidationError as exc:
        item.status = "cancelled"
        item.cancelled_reason = str(exc)[:200]
        _notify_agent(
            brokerage,
            agent_phone=item.agent_phone,
            body=f"Couldn't deliver to {_conversation_label(db, conversation)}: {exc}",
        )
        return False

    item.status = "sent"
    item.sent_at = now
    return True


# ── UNDO keyword ───────────────────────────────────────────────────────────────


def handle_agents_ai_undo_keyword(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound: InboundEnvelope,
    now: Optional[datetime] = None,
) -> Optional[RelayRoutingResult]:
    """UNDO cancels all held, unsent items for this agent. Consumed, never forwarded."""
    from app.core.agent_relay import strip_envelope_token

    now = now or datetime.utcnow()
    text = strip_envelope_token(inbound.body or "", inbound.envelope_token).strip().strip(".!").lower()
    if text != "undo":
        return None

    agent_phone = _normalize_phone(inbound.from_number)
    held = (
        db.query(DBRelayOutboxItem)
        .filter(
            DBRelayOutboxItem.brokerage_id == brokerage.brokerage_id,
            DBRelayOutboxItem.agent_phone == agent_phone,
            DBRelayOutboxItem.status == "held",
        )
        .all()
    )
    labels = []
    for item in held:
        item.status = "cancelled"
        item.cancelled_reason = "undo"
        conversation = db.get(DBConversation, item.conversation_id) if item.conversation_id else None
        if conversation:
            label = _conversation_label(db, conversation)
            if label not in labels:
                labels.append(label)
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        event_type="relay_items_undone",
        direction="inbound",
        details={"agent_phone": agent_phone, "cancelled_count": len(held)},
    )
    safe_commit(db)
    if held:
        recipients = "; ".join(labels) if labels else "the pending recipient"
        _notify_agent(
            brokerage,
            agent_phone=agent_phone,
            body=f"Cancelled — {len(held)} held item(s) for {recipients} will not be sent.",
        )
    else:
        _notify_agent(
            brokerage,
            agent_phone=agent_phone,
            body="Nothing is waiting to send — there were no held items to cancel.",
        )
    return RelayRoutingResult(status="undone", details={"cancelled_count": len(held)})


# ── Parked batches ─────────────────────────────────────────────────────────────


def _open_parked_batch(
    db: Session,
    *,
    brokerage_id: str,
    agent_phone: str,
    now: datetime,
) -> Optional[str]:
    latest = (
        db.query(DBRelayOutboxItem)
        .filter(
            DBRelayOutboxItem.brokerage_id == brokerage_id,
            DBRelayOutboxItem.agent_phone == agent_phone,
            DBRelayOutboxItem.status == "parked",
        )
        .order_by(DBRelayOutboxItem.created_at.desc())
        .first()
    )
    if latest and latest.created_at >= now - PARKED_BURST_WINDOW:
        return latest.parked_batch_id
    return None


def _parked_items(db: Session, *, brokerage_id: str, agent_phone: str) -> list[DBRelayOutboxItem]:
    return (
        db.query(DBRelayOutboxItem)
        .filter(
            DBRelayOutboxItem.brokerage_id == brokerage_id,
            DBRelayOutboxItem.agent_phone == agent_phone,
            DBRelayOutboxItem.status == "parked",
        )
        .order_by(DBRelayOutboxItem.created_at.asc())
        .all()
    )


def _eligible_media_request_threads(
    db: Session,
    *,
    brokerage_id: str,
    agent_phone: str,
    now: datetime,
) -> list[DBEscalationThread]:
    """
    Tier-4 eligibility, read as stored state: open/updated threads flagged
    media_requested at classification time, alerted within the last 48 hours.
    """
    threads = (
        db.query(DBEscalationThread)
        .filter(
            DBEscalationThread.brokerage_id == brokerage_id,
            DBEscalationThread.agent_phone == agent_phone,
            DBEscalationThread.state.in_(OPEN_THREAD_STATES - {"debouncing"}),
            DBEscalationThread.alerted_at.isnot(None),
            DBEscalationThread.alerted_at >= now - MEDIA_REQUEST_FRESHNESS,
        )
        .order_by(DBEscalationThread.alerted_at.desc())
        .all()
    )
    return [thread for thread in threads if thread_media_requested(thread)]


def handle_parked_batch_answer(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound: InboundEnvelope,
    now: Optional[datetime] = None,
) -> Optional[RelayRoutingResult]:
    """
    A numeric reply, quote-reply, or #REF routes the whole parked batch, which
    then sends immediately — routing became explicit.
    """
    from app.core.agent_relay import strip_envelope_token

    now = now or datetime.utcnow()
    agent_phone = _normalize_phone(inbound.from_number)
    parked = _parked_items(db, brokerage_id=brokerage.brokerage_id, agent_phone=agent_phone)
    if not parked:
        return None
    if _inbound_media_items(inbound):
        return None  # new media is routed on its own, not as a batch answer

    text = strip_envelope_token(inbound.body or "", inbound.envelope_token).strip()
    conversation: Optional[DBConversation] = None
    relay_text_after = False

    caption_token = None
    caption_match = CAPTION_TOKEN_PATTERN.search(text)
    if caption_match:
        caption_token = caption_match.group(1).upper()

    if text.isdigit():
        options = (parked[0].metadata_json or {}).get("routing_options") or []
        index = int(text) - 1
        if 0 <= index < len(options):
            conversation = db.get(DBConversation, options[index]["conversation_id"])
        else:
            _notify_agent(
                brokerage,
                agent_phone=agent_phone,
                body=f"That option isn't on the list — reply 1-{len(options)}, quote a ref, or reply #REF.",
            )
            return RelayRoutingResult(status="parked_answer_invalid")
    elif caption_token:
        route = _route_for_token(db, brokerage_id=brokerage.brokerage_id, token=caption_token, agent_phone=agent_phone)
        if route:
            conversation = db.get(DBConversation, route.conversation_id)
        else:
            _notify_agent(
                brokerage,
                agent_phone=agent_phone,
                body="I couldn't match that #REF. Check the token and try again — I never guess the buyer.",
            )
            return RelayRoutingResult(status="parked_answer_unknown_ref")
    elif inbound.envelope_token:
        route = _route_for_token(db, brokerage_id=brokerage.brokerage_id, token=inbound.envelope_token, agent_phone=agent_phone)
        if route:
            conversation = db.get(DBConversation, route.conversation_id)
            relay_text_after = bool(text)  # the quoted text also relays as a normal reply
    if not conversation:
        return None

    released = []
    for item in parked:
        item.conversation_id = conversation.conversation_id
        item.listing_id = conversation.listing_id
        item.buyer_phone = conversation.buyer_phone
        item.routing_method = "parking_prompt"
        asset = db.get(DBMediaAsset, item.media_asset_id) if item.media_asset_id else None
        if asset:
            asset.conversation_id = conversation.conversation_id
            asset.listing_id = conversation.listing_id
        item.status = "held"
        item.release_at = now  # explicit routing → sends immediately
        if _deliver_item(db, brokerage=brokerage, item=item, now=now):
            released.append(item.item_id)
    safe_commit(db)
    if released:
        _notify_agent(
            brokerage,
            agent_phone=agent_phone,
            body=f"Sent {len(released)} file(s) to {_conversation_label(db, conversation)}.",
        )
    return RelayRoutingResult(
        status="parked_batch_routed",
        routing_method="parking_prompt",
        conversation_id=conversation.conversation_id,
        item_ids=released,
        relay_text_after=relay_text_after,
    )


# ── Main router ────────────────────────────────────────────────────────────────


def _route_for_token(
    db: Session,
    *,
    brokerage_id: str,
    token: str,
    agent_phone: Optional[str] = None,
) -> Optional[DBAgentMessageRoute]:
    """
    Token lookup is brokerage-scoped (token-forgery isolation) and, when an
    agent phone is supplied, agent-scoped — another agent's ref never routes.
    """
    route = (
        db.query(DBAgentMessageRoute)
        .filter(
            DBAgentMessageRoute.brokerage_id == brokerage_id,
            DBAgentMessageRoute.agents_ai_envelope_token == token.upper(),
        )
        .first()
    )
    if route and agent_phone:
        route_phone = _normalize_phone(route.agent_phone)
        if route_phone and route_phone != _normalize_phone(agent_phone):
            return None
    return route


def route_agents_ai_inbound(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound: InboundEnvelope,
    now: Optional[datetime] = None,
) -> Optional[RelayRoutingResult]:
    """
    Route a non-keyword Agents AI inbound through the explicit-to-implicit
    tiers. Returns None when the message should fall through to the standard
    quote-reply relay (agent_relay.relay_agent_reply).
    """
    now = now or datetime.utcnow()
    agent_phone = _normalize_phone(inbound.from_number)

    # Outstanding parking prompt answers take precedence over fresh routing.
    answer = handle_parked_batch_answer(db, brokerage=brokerage, inbound=inbound, now=now)
    if answer is not None:
        if answer.relay_text_after:
            answer.handled = False  # webhook continues into relay_agent_reply
        return answer

    media_items = _inbound_media_items(inbound)
    has_audio = any(
        _is_audio(
            inbound.media_content_types[index] if index < len(inbound.media_content_types) else "",
            url,
        )
        for index, url in enumerate(inbound.media_urls)
    )

    if has_audio and not media_items:
        # Voice replies require a quote (tier 2) — never auto-route audio.
        if inbound.envelope_token:
            return None  # → relay_agent_reply voice path (DAL-159)
        _notify_agent(
            brokerage,
            agent_phone=agent_phone,
            body="To send a voice reply, quote-reply the buyer's [Ref: …] message with your voice note.",
        )
        return RelayRoutingResult(status="voice_requires_quote")

    if not media_items:
        return _route_text_inbound(db, brokerage=brokerage, inbound=inbound, now=now)

    return _route_media_inbound(
        db,
        brokerage=brokerage,
        inbound=inbound,
        media_items=media_items,
        now=now,
    )


def _route_text_inbound(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound: InboundEnvelope,
    now: datetime,
) -> Optional[RelayRoutingResult]:
    from app.core.agent_relay import strip_envelope_token

    agent_phone = _normalize_phone(inbound.from_number)

    if inbound.envelope_token:
        return None  # tier 2 — the standard relay handles quoted text

    text = (inbound.body or "").strip()
    caption_match = CAPTION_TOKEN_PATTERN.search(text)
    if caption_match:
        route = _route_for_token(db, brokerage_id=brokerage.brokerage_id, token=caption_match.group(1), agent_phone=agent_phone)
        if route:
            conversation = db.get(DBConversation, route.conversation_id)
            if conversation:
                body = _clean_caption(inbound, strip_all=False)
                item = _create_item(
                    db,
                    brokerage=brokerage,
                    inbound=inbound,
                    asset=None,
                    body=body,
                    status="held",
                    routing_method="caption_token",
                    conversation=conversation,
                    agent_user_id=route.agent_user_id,
                    release_at=now,
                )
                db.flush()
                delivered = _deliver_item(db, brokerage=brokerage, item=item, now=now)
                safe_commit(db)
                return RelayRoutingResult(
                    status="sent" if delivered else "bounced",
                    routing_method="caption_token",
                    conversation_id=conversation.conversation_id,
                    item_ids=[item.item_id],
                )
        # Token typo: fall through — never fuzzy-matched.

    session = active_session(db, brokerage_id=brokerage.brokerage_id, agent_phone=agent_phone, now=now)
    if session:
        conversation = db.get(DBConversation, session.conversation_id)
        if conversation:
            body = strip_envelope_token(inbound.body or "", None).strip()
            item = _create_item(
                db,
                brokerage=brokerage,
                inbound=inbound,
                asset=None,
                body=body,
                status="held",
                routing_method="session",
                conversation=conversation,
                agent_user_id=session.agent_user_id,
                release_at=now + timedelta(seconds=IMPLICIT_HOLD_SECONDS),
            )
            session.last_activity_at = now
            session.expires_at = now + SESSION_ACTIVITY_WINDOW
            db.flush()
            safe_commit(db)
            _notify_agent(
                brokerage,
                agent_phone=agent_phone,
                body=(
                    f"→ {_conversation_label(db, conversation)} — sending in "
                    f"{IMPLICIT_HOLD_SECONDS}s. Reply UNDO to cancel."
                ),
            )
            return RelayRoutingResult(
                status="held",
                routing_method="session",
                conversation_id=conversation.conversation_id,
                item_ids=[item.item_id],
            )

    # No tier matched: text bounces (cheap to re-send; media parks instead).
    _notify_agent(
        brokerage,
        agent_phone=agent_phone,
        body=(
            "I couldn't tell which buyer this is for. Quote-reply their "
            "[Ref: …] message, or include their #REF token."
        ),
    )
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        event_type="relay_text_bounced",
        direction="inbound",
        details={"agent_phone": agent_phone, "body_preview": (inbound.body or "")[:200]},
    )
    safe_commit(db)
    return RelayRoutingResult(status="bounced_no_route")


def _route_media_inbound(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound: InboundEnvelope,
    media_items: list[tuple[str, str]],
    now: datetime,
) -> RelayRoutingResult:
    agent_phone = _normalize_phone(inbound.from_number)
    forwarded = _is_forwarded(inbound)
    caption = _clean_caption(inbound, strip_all=forwarded)

    # Resolve agent identity for asset bookkeeping where a route gives it.
    agent_user_id: Optional[str] = None

    conversation: Optional[DBConversation] = None
    routing_method: Optional[str] = None
    held = False
    basis = ""

    # Tier 1 — caption token (unavailable on forwards: captions can't be edited).
    caption_match = CAPTION_TOKEN_PATTERN.search(inbound.body or "")
    if caption_match:
        route = _route_for_token(db, brokerage_id=brokerage.brokerage_id, token=caption_match.group(1), agent_phone=agent_phone)
        if route:
            conversation = db.get(DBConversation, route.conversation_id)
            routing_method = "caption_token"
            agent_user_id = route.agent_user_id
        # Typo/no-match → fall through to tier 2/3 — never fuzzy-matched.

    # Tier 2 — quote-reply: routes and opens/refreshes the ref session.
    if conversation is None and inbound.envelope_token:
        route = _route_for_token(db, brokerage_id=brokerage.brokerage_id, token=inbound.envelope_token, agent_phone=agent_phone)
        if route:
            conversation = db.get(DBConversation, route.conversation_id)
            routing_method = "quote_reply"
            agent_user_id = route.agent_user_id
            if conversation:
                open_or_refresh_session(
                    db,
                    brokerage_id=brokerage.brokerage_id,
                    agent_user_id=route.agent_user_id,
                    agent_phone=agent_phone,
                    conversation_id=conversation.conversation_id,
                    listing_id=conversation.listing_id,
                    buyer_phone=conversation.buyer_phone,
                    now=now,
                )

    # Tier 3 — active session (held). Session takes precedence over tier 4.
    if conversation is None:
        session = active_session(db, brokerage_id=brokerage.brokerage_id, agent_phone=agent_phone, now=now)
        if session:
            conversation = db.get(DBConversation, session.conversation_id)
            routing_method = "session"
            agent_user_id = session.agent_user_id
            held = True
            session.last_activity_at = now
            session.expires_at = now + SESSION_ACTIVITY_WINDOW

    # Tier 4 — exactly one open media_requested escalation (held, basis-stated).
    if conversation is None:
        eligible = _eligible_media_request_threads(
            db, brokerage_id=brokerage.brokerage_id, agent_phone=agent_phone, now=now
        )
        if len(eligible) == 1:
            thread = eligible[0]
            conversation = db.get(DBConversation, thread.conversation_id)
            routing_method = "escalation_match"
            agent_user_id = thread.agent_user_id
            held = True
            basis = " — matched your open escalation asking for media"

    assets = _store_inbound_media(db, brokerage=brokerage, inbound=inbound, agent_user_id=agent_user_id)
    if not assets:
        _notify_agent(
            brokerage,
            agent_phone=agent_phone,
            body="I couldn't read that file — please try sending it again.",
        )
        return RelayRoutingResult(status="media_unreadable")

    if conversation is None:
        return _park_media(
            db,
            brokerage=brokerage,
            inbound=inbound,
            assets=assets,
            caption=caption,
            now=now,
        )

    item_ids = []
    explicit = routing_method in {"caption_token", "quote_reply"}
    release_at = now if explicit else now + timedelta(seconds=IMPLICIT_HOLD_SECONDS)
    for index, asset in enumerate(assets):
        item = _create_item(
            db,
            brokerage=brokerage,
            inbound=inbound,
            asset=asset,
            body=caption if index == 0 else "",
            status="held",
            routing_method=routing_method,
            conversation=conversation,
            agent_user_id=agent_user_id,
            release_at=release_at,
        )
        db.flush()
        item_ids.append(item.item_id)
        if explicit:
            _deliver_item(db, brokerage=brokerage, item=item, now=now)
    safe_commit(db)

    if not explicit:
        _notify_agent(
            brokerage,
            agent_phone=agent_phone,
            body=(
                f"→ {_conversation_label(db, conversation)}{basis} — sending in "
                f"{IMPLICIT_HOLD_SECONDS}s. Reply UNDO to cancel."
            ),
        )
    return RelayRoutingResult(
        status="sent" if explicit else "held",
        routing_method=routing_method,
        conversation_id=conversation.conversation_id,
        item_ids=item_ids,
    )


def _park_media(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound: InboundEnvelope,
    assets: list[DBMediaAsset],
    caption: str,
    now: datetime,
) -> RelayRoutingResult:
    """
    No tier matched: park, don't reject. Multiple unrouted media within a 60s
    burst group into one batch with one routing prompt. Agents forward first
    and think about routing second — the system accommodates that order.
    """
    agent_phone = _normalize_phone(inbound.from_number)
    existing_batch = _open_parked_batch(
        db, brokerage_id=brokerage.brokerage_id, agent_phone=agent_phone, now=now
    )
    batch_id = existing_batch or uuid.uuid4().hex
    is_new_batch = existing_batch is None

    eligible = _eligible_media_request_threads(
        db, brokerage_id=brokerage.brokerage_id, agent_phone=agent_phone, now=now
    )
    routing_options = []
    for thread in eligible:
        conversation = db.get(DBConversation, thread.conversation_id)
        if conversation:
            routing_options.append({
                "conversation_id": conversation.conversation_id,
                "label": _conversation_label(db, conversation),
                "thread_id": thread.thread_id,
            })

    item_ids = []
    for index, asset in enumerate(assets):
        item = _create_item(
            db,
            brokerage=brokerage,
            inbound=inbound,
            asset=asset,
            body=caption if index == 0 else "",
            status="parked",
            routing_method=None,
            conversation=None,
            agent_user_id=None,
            parked_batch_id=batch_id,
            metadata={"routing_options": routing_options},
        )
        db.flush()
        item_ids.append(item.item_id)
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        event_type="relay_media_parked",
        direction="inbound",
        details={
            "agent_phone": agent_phone,
            "batch_id": batch_id,
            "file_count": len(assets),
            "option_count": len(routing_options),
        },
    )
    safe_commit(db)

    if is_new_batch:
        count = len(assets)
        files = f"{count} file{'s' if count != 1 else ''}"
        if len(routing_options) >= 2:
            numbered = ", ".join(
                f"{index + 1} = {option['label']}" for index, option in enumerate(routing_options)
            )
            prompt = (
                f"Got {files} — who are these for? {numbered}, or quote a ref / reply #REF."
            )
        else:
            prompt = f"Got {files} — where should these go? Quote a buyer's ref, or reply with the #REF token."
        _notify_agent(brokerage, agent_phone=agent_phone, body=prompt)
    return RelayRoutingResult(status="parked", item_ids=item_ids, details={"batch_id": batch_id})


# ── Outbox worker ──────────────────────────────────────────────────────────────


def process_relay_outbox(db: Session, *, now: Optional[datetime] = None) -> dict:
    """
    Release due held items and expire stale parked items. Runs on the debounce
    worker's poll interval; tests call it directly with a pinned `now`.
    """
    now = now or datetime.utcnow()
    released = 0
    expired = 0

    due = (
        db.query(DBRelayOutboxItem)
        .filter(
            DBRelayOutboxItem.status == "held",
            DBRelayOutboxItem.release_at.isnot(None),
            DBRelayOutboxItem.release_at <= now,
        )
        .order_by(DBRelayOutboxItem.created_at.asc())
        .all()
    )
    for item in due:
        brokerage = db.get(DBBrokerage, item.brokerage_id)
        if not brokerage:
            continue
        if _deliver_item(db, brokerage=brokerage, item=item, now=now):
            released += 1

    stale_cutoff = now - PARKED_EXPIRY
    stale = (
        db.query(DBRelayOutboxItem)
        .filter(
            DBRelayOutboxItem.status == "parked",
            DBRelayOutboxItem.created_at < stale_cutoff,
        )
        .all()
    )
    notified_batches = set()
    for item in stale:
        item.status = "expired"
        item.cancelled_reason = "parked_expired"
        expired += 1
        # Media asset retained per retention policy — never sent.
        batch_key = (item.brokerage_id, item.agent_phone, item.parked_batch_id)
        if batch_key not in notified_batches:
            notified_batches.add(batch_key)
            brokerage = db.get(DBBrokerage, item.brokerage_id)
            if brokerage:
                _notify_agent(
                    brokerage,
                    agent_phone=item.agent_phone,
                    body=(
                        "The files you forwarded 30 minutes ago were never routed to a "
                        "buyer, so I've discarded them. Forward them again and quote a "
                        "ref or reply #REF to send."
                    ),
                )
    safe_commit(db)
    return {"released": released, "expired": expired}
