from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.brokerage_access import (
    is_buyer_suppressed,
    record_compliance_event,
)
from app.core.messaging import get_transport
from app.core.messaging.types import (
    InboundEnvelope,
    OutboundAgentMessage,
    OutboundBuyerMessage,
)
from app.db.session import safe_commit
from app.models.db_models import (
    DBAgentMessageRoute,
    DBAgentVoiceReplyHold,
    DBBrokerage,
    DBConversation,
    DBEscalationThread,
    DBLeadAction,
    DBLeadAssignment,
    DBMessage,
)

logger = logging.getLogger(__name__)

# Below this transcript confidence an agent voice reply is held for a SEND
# confirm instead of auto-sending (DAL-159 option B1). Needs empirical tuning
# against Speechmatics confidence on Gulf-accented English/Arabic.
AGENT_VOICE_SEND_CONFIDENCE_THRESHOLD = float(
    os.getenv("AGENT_VOICE_SEND_CONFIDENCE_THRESHOLD", "0.75")
)


@dataclass
class AgentRelayResult:
    status: str
    relayed: bool = False
    route_id: Optional[str] = None
    conversation_id: Optional[str] = None
    listing_id: Optional[str] = None
    buyer_phone: Optional[str] = None
    transport_message_id: Optional[str] = None
    reason: Optional[str] = None
    details: dict = field(default_factory=dict)


def _normalize_phone(number: Optional[str]) -> str:
    if not number:
        return ""
    cleaned = number.strip()
    if cleaned.lower().startswith("whatsapp:"):
        cleaned = cleaned[len("whatsapp:"):]
    return cleaned


def strip_envelope_token(body: str, token: Optional[str]) -> str:
    if not body:
        return ""
    text = body
    if token:
        text = re.sub(rf"\s*\[Ref:\s*{re.escape(token)}\]\s*", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def _blocked(
    db: Session,
    *,
    brokerage_id: str,
    event_type: str,
    inbound: InboundEnvelope,
    reason: str,
    route: Optional[DBAgentMessageRoute] = None,
    details: Optional[dict] = None,
) -> AgentRelayResult:
    payload = {
        "reason": reason,
        "from_number": _normalize_phone(inbound.from_number),
        "to_number": _normalize_phone(inbound.to_number),
        "envelope_token": inbound.envelope_token,
        **(details or {}),
    }
    record_compliance_event(
        db,
        brokerage_id=brokerage_id,
        conversation_id=route.conversation_id if route else None,
        listing_id=route.listing_id if route else None,
        buyer_phone=route.buyer_phone if route else None,
        actor_user_id=route.agent_user_id if route else None,
        event_type=event_type,
        direction="inbound",
        details=payload,
    )
    safe_commit(db)
    return AgentRelayResult(
        status=event_type,
        relayed=False,
        route_id=route.route_id if route else None,
        conversation_id=route.conversation_id if route else None,
        listing_id=route.listing_id if route else None,
        buyer_phone=route.buyer_phone if route else None,
        reason=reason,
        details=payload,
    )


def relay_agent_reply(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound: InboundEnvelope,
    now: Optional[datetime] = None,
) -> AgentRelayResult:
    now = now or datetime.utcnow()
    token = inbound.envelope_token
    if not token:
        return _blocked(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="agent_reply_blocked_missing_token",
            inbound=inbound,
            reason="missing_envelope_token",
        )

    route = (
        db.query(DBAgentMessageRoute)
        .filter(
            DBAgentMessageRoute.brokerage_id == brokerage.brokerage_id,
            DBAgentMessageRoute.agents_ai_envelope_token == token,
        )
        .first()
    )
    if not route:
        return _blocked(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="agent_reply_blocked_unknown_token",
            inbound=inbound,
            reason="unknown_envelope_token",
        )

    from_number = _normalize_phone(inbound.from_number)
    route_agent_phone = _normalize_phone(route.agent_phone)
    if route_agent_phone and from_number != route_agent_phone:
        return _blocked(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="agent_reply_blocked_wrong_agent",
            inbound=inbound,
            reason="wrong_agent_phone",
            route=route,
            details={"expected_agent_phone": route_agent_phone},
        )

    if route.expires_at and route.expires_at < now:
        return _blocked(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="agent_reply_blocked_expired",
            inbound=inbound,
            reason="route_expired",
            route=route,
            details={"expires_at": route.expires_at.isoformat()},
        )

    if route.consumed_at:
        return _blocked(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="agent_reply_blocked_consumed",
            inbound=inbound,
            reason="route_consumed",
            route=route,
            details={"consumed_at": route.consumed_at.isoformat()},
        )

    if is_buyer_suppressed(db, brokerage.brokerage_id, route.buyer_phone):
        return _blocked(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="agent_reply_blocked_opt_out",
            inbound=inbound,
            reason="buyer_suppressed",
            route=route,
        )

    # ── Agent voice reply (DAL-159, option B1) ───────────────────────────────
    # The agent spoke the words: transcribe and deliver as text, gating on
    # transcription confidence. Never forward agent audio to the buyer from
    # the brokerage's AI number.
    audio = _first_audio_media(inbound)
    if audio:
        return _handle_agent_voice_reply(
            db,
            brokerage=brokerage,
            route=route,
            inbound=inbound,
            audio_url=audio[0],
            content_type=audio[1],
            now=now,
        )

    body = strip_envelope_token(inbound.body, token)
    media_url = inbound.media_urls[0] if inbound.media_urls else None
    if not body and not media_url:
        return _blocked(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="agent_reply_blocked_empty",
            inbound=inbound,
            reason="empty_reply",
            route=route,
        )

    # A typed reply supersedes any voice transcript still waiting for SEND.
    _cancel_pending_holds(db, route=route, reason="superseded_by_reply", now=now)

    result = _deliver_agent_reply(
        db,
        brokerage=brokerage,
        route=route,
        body=body,
        media_url=media_url,
        source="agents_ai_reply",
        now=now,
    )
    if result.status == "agent_reply_send_failed":
        return _blocked(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="agent_reply_send_failed",
            inbound=inbound,
            reason=result.reason or "transport_send_failed",
            route=route,
        )
    return result


def _deliver_agent_reply(
    db: Session,
    *,
    brokerage: DBBrokerage,
    route: DBAgentMessageRoute,
    body: str,
    media_url: Optional[str] = None,
    source: str = "agents_ai_reply",
    extra_message_metadata: Optional[dict] = None,
    now: Optional[datetime] = None,
) -> AgentRelayResult:
    """
    Send an agent-authored reply to the buyer and do all relay bookkeeping:
    timeline message, lead action, route consumption, thread resolution, and
    compliance event. Shared by the text relay, the voice B1 path, and the
    SEND-confirm release.
    """
    now = now or datetime.utcnow()
    token = route.agents_ai_envelope_token

    send_result = get_transport().send_to_buyer(
        OutboundBuyerMessage(
            brokerage_id=brokerage.brokerage_id,
            brokerage_ai_number=brokerage.brokerage_ai_number,
            buyer_phone=route.buyer_phone,
            body=body,
            conversation_id=route.conversation_id,
            listing_id=route.listing_id,
            media_url=media_url,
        )
    )
    if not send_result.ok:
        return AgentRelayResult(
            status="agent_reply_send_failed",
            relayed=False,
            route_id=route.route_id,
            conversation_id=route.conversation_id,
            listing_id=route.listing_id,
            buyer_phone=route.buyer_phone,
            reason=send_result.error or "transport_send_failed",
        )

    message_metadata = {
        "source": source,
        "agent_user_id": route.agent_user_id,
        "agent_phone": route.agent_phone,
        "route_id": route.route_id,
        "thread_id": route.thread_id,
        "envelope_token": token,
        "media_url": media_url,
        "transport_message_id": send_result.transport_message_id,
        **(extra_message_metadata or {}),
    }
    message = DBMessage(
        conversation_id=route.conversation_id,
        role="assistant",
        content=body or "[Agent media reply]",
        intent="agent_relay",
        metadata_json=message_metadata,
    )
    voice_note = message_metadata.get("voice_note") or {}
    if voice_note:
        message.transcription_text = voice_note.get("transcription_text")
        message.transcription_language = voice_note.get("transcription_language")
        confidence = voice_note.get("transcription_confidence")
        message.transcription_confidence = (
            float(confidence) if isinstance(confidence, (int, float)) else None
        )
        message.transcription_provider = voice_note.get("transcription_provider")
    db.add(message)

    conversation = db.get(DBConversation, route.conversation_id)
    if conversation:
        conversation.updated_at = now

    assignment = (
        db.query(DBLeadAssignment)
        .filter(DBLeadAssignment.conversation_id == route.conversation_id)
        .first()
    )
    if assignment:
        assignment.last_agent_action_at = now
        assignment.updated_at = now

    db.add(DBLeadAction(
        brokerage_id=brokerage.brokerage_id,
        conversation_id=route.conversation_id,
        listing_id=route.listing_id,
        buyer_phone=route.buyer_phone,
        agent_user_id=route.agent_user_id,
        action_type="agent_reply_relayed",
        outcome=route.escalation_type,
        note=body[:500] if body else "[Agent media reply]",
        payload={
            "route_id": route.route_id,
            "thread_id": route.thread_id,
            "envelope_token": token,
            "media_url": media_url,
            "source": source,
            "transport_message_id": send_result.transport_message_id,
        },
    ))

    route.consumed_at = now

    # Delete-on-handle: if this route carried a pushed reply draft and the agent
    # has now replied from their phone, the draft is handled — discard it so it
    # disappears from the web app's draft queue.
    if getattr(route, "draft_id", None):
        from app.models.db_models import DBDraftReply

        pushed_draft = db.get(DBDraftReply, route.draft_id)
        if pushed_draft and pushed_draft.status in {"draft", "edited", "snoozed"}:
            draft_metadata = dict(pushed_draft.metadata_json or {})
            draft_metadata["handled_via"] = "agent_whatsapp_reply"
            draft_metadata["handled_at"] = now.isoformat()
            pushed_draft.metadata_json = draft_metadata
            pushed_draft.status = "discarded"
            pushed_draft.updated_at = now

    thread_question_count = 0
    if route.thread_id:
        from app.core.escalation_threads import resolve_thread_for_route
        thread_question_count = resolve_thread_for_route(db, route=route, now=now)

    # DAL-161: a quote-reply opens/refreshes the agent's ref session so
    # unquoted follow-ups within 10 minutes route to the same buyer.
    if route.agent_phone:
        from app.core.relay_media import open_or_refresh_session
        open_or_refresh_session(
            db,
            brokerage_id=brokerage.brokerage_id,
            agent_user_id=route.agent_user_id,
            agent_phone=route.agent_phone,
            conversation_id=route.conversation_id,
            listing_id=route.listing_id,
            buyer_phone=route.buyer_phone,
            now=now,
        )

    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=route.conversation_id,
        listing_id=route.listing_id,
        buyer_phone=route.buyer_phone,
        actor_user_id=route.agent_user_id,
        event_type="agent_reply_relayed",
        direction="outbound",
        details={
            "route_id": route.route_id,
            "thread_id": route.thread_id,
            "envelope_token": token,
            "agent_phone": route.agent_phone,
            "media_url": media_url,
            "source": source,
            "routing_method": "quote_reply",
            "body_preview": body[:200],
            "transport_message_id": send_result.transport_message_id,
            "question_count": thread_question_count or None,
        },
    )
    safe_commit(db)
    return AgentRelayResult(
        status="relayed",
        relayed=True,
        route_id=route.route_id,
        conversation_id=route.conversation_id,
        listing_id=route.listing_id,
        buyer_phone=route.buyer_phone,
        transport_message_id=send_result.transport_message_id,
    )


def _first_audio_media(inbound: InboundEnvelope) -> Optional[tuple[str, str]]:
    for index, url in enumerate(inbound.media_urls):
        content_type = (
            inbound.media_content_types[index]
            if index < len(inbound.media_content_types)
            else ""
        )
        if content_type.lower().startswith("audio/"):
            return url, content_type
        # Local fixture paths from the simulated transport may omit the
        # content type — fall back to the file suffix.
        if not content_type and re.search(r"\.(ogg|opus|mp3|m4a|wav|webm|aac|flac)$", url.lower()):
            return url, content_type
    return None


def _notify_agent_on_thread(
    *,
    brokerage: DBBrokerage,
    route: DBAgentMessageRoute,
    body: str,
) -> None:
    if not (brokerage.agents_ai_number and route.agent_phone):
        return
    get_transport().send_to_agents_ai(
        OutboundAgentMessage(
            brokerage_id=brokerage.brokerage_id,
            agents_ai_number=brokerage.agents_ai_number,
            agent_phone=route.agent_phone,
            body=body,
            conversation_id=route.conversation_id,
            listing_id=route.listing_id,
            buyer_phone=route.buyer_phone,
            escalation_type="agent_voice_reply_notice",
            envelope_token=route.agents_ai_envelope_token,
            agent_user_id=route.agent_user_id,
        )
    )


def _cancel_pending_holds(
    db: Session,
    *,
    route: DBAgentMessageRoute,
    reason: str,
    now: datetime,
) -> int:
    holds = (
        db.query(DBAgentVoiceReplyHold)
        .filter(
            DBAgentVoiceReplyHold.route_id == route.route_id,
            DBAgentVoiceReplyHold.status == "held",
        )
        .all()
    )
    for hold in holds:
        hold.status = "cancelled"
        hold.released_at = now
        metadata = dict(hold.metadata_json or {})
        metadata["cancel_reason"] = reason
        hold.metadata_json = metadata
    return len(holds)


def _handle_agent_voice_reply(
    db: Session,
    *,
    brokerage: DBBrokerage,
    route: DBAgentMessageRoute,
    inbound: InboundEnvelope,
    audio_url: str,
    content_type: str,
    now: datetime,
) -> AgentRelayResult:
    from app.core.voice_notes import (
        download_media_to_tempfile_sync,
        transcribe_audio_file,
        transcription_result_metadata,
        twilio_media_auth,
    )
    from app.core.transcription.models import TranscriptionContext

    token = route.agents_ai_envelope_token
    try:
        audio_path = download_media_to_tempfile_sync(
            audio_url,
            content_type=content_type or None,
            auth=twilio_media_auth() if audio_url.startswith("http") else None,
        )
        result = transcribe_audio_file(
            audio_path,
            content_type=content_type or None,
            audio_type="agent_reply_voice",
            context=TranscriptionContext(listing_id=route.listing_id),
        )
        transcript = (result.corrected_transcript or result.raw_transcript).strip()
        if not transcript:
            raise ValueError("empty transcript")
    except Exception as exc:
        logger.warning("Agent voice reply transcription failed: %s", exc)
        _notify_agent_on_thread(
            brokerage=brokerage,
            route=route,
            body=(
                "I couldn't process that voice note — could you type your reply "
                "instead? Nothing was sent to the buyer."
            ),
        )
        record_compliance_event(
            db,
            brokerage_id=brokerage.brokerage_id,
            conversation_id=route.conversation_id,
            listing_id=route.listing_id,
            buyer_phone=route.buyer_phone,
            actor_user_id=route.agent_user_id,
            event_type="agent_voice_reply_unprocessable",
            direction="inbound",
            details={
                "route_id": route.route_id,
                "envelope_token": token,
                "audio_url": audio_url,
                "error": str(exc),
            },
        )
        safe_commit(db)
        return AgentRelayResult(
            status="agent_voice_reply_unprocessable",
            relayed=False,
            route_id=route.route_id,
            conversation_id=route.conversation_id,
            listing_id=route.listing_id,
            buyer_phone=route.buyer_phone,
            reason="transcription_failed",
        )

    confidence = result.effective_confidence()
    voice_metadata = transcription_result_metadata(
        result,
        direction="agent_to_buyer",
        audio_url=audio_url,
    )

    if confidence >= AGENT_VOICE_SEND_CONFIDENCE_THRESHOLD:
        delivery = _deliver_agent_reply(
            db,
            brokerage=brokerage,
            route=route,
            body=transcript,
            media_url=None,
            source="agents_ai_voice_reply",
            extra_message_metadata=voice_metadata,
            now=now,
        )
        if delivery.relayed:
            _cancel_pending_holds(db, route=route, reason="superseded_by_voice_send", now=now)
            _notify_agent_on_thread(
                brokerage=brokerage,
                route=route,
                body=f'Sent as text: "{transcript}"',
            )
            safe_commit(db)
        return delivery

    # Low confidence: hold for SEND confirm — the only flow where confidence
    # gates sending (DAL-159).
    hold = DBAgentVoiceReplyHold(
        brokerage_id=brokerage.brokerage_id,
        route_id=route.route_id,
        conversation_id=route.conversation_id,
        listing_id=route.listing_id,
        buyer_phone=route.buyer_phone,
        agent_user_id=route.agent_user_id,
        agent_phone=route.agent_phone,
        envelope_token=token,
        transcript=transcript,
        transcription_language=result.language,
        transcription_confidence=confidence,
        transcription_provider=result.provider,
        status="held",
        metadata_json={"audio_url": audio_url},
    )
    db.add(hold)
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=route.conversation_id,
        listing_id=route.listing_id,
        buyer_phone=route.buyer_phone,
        actor_user_id=route.agent_user_id,
        event_type="agent_voice_reply_held",
        direction="inbound",
        details={
            "route_id": route.route_id,
            "envelope_token": token,
            "transcription_confidence": confidence,
            "threshold": AGENT_VOICE_SEND_CONFIDENCE_THRESHOLD,
            "transcript_preview": transcript[:200],
        },
    )
    safe_commit(db)
    _notify_agent_on_thread(
        brokerage=brokerage,
        route=route,
        body=(
            "I transcribed your voice note but I'm not confident I heard it "
            f'right:\n\n"{transcript}"\n\n'
            "Reply SEND to deliver it as text, or type your reply instead. "
            "Nothing has been sent to the buyer yet."
        ),
    )
    return AgentRelayResult(
        status="agent_voice_reply_held",
        relayed=False,
        route_id=route.route_id,
        conversation_id=route.conversation_id,
        listing_id=route.listing_id,
        buyer_phone=route.buyer_phone,
        details={"hold_id": hold.hold_id, "confidence": confidence},
    )


def handle_agent_send_keyword(
    db: Session,
    *,
    brokerage: DBBrokerage,
    inbound: InboundEnvelope,
    now: Optional[datetime] = None,
) -> Optional[AgentRelayResult]:
    """
    SEND confirms a held voice transcript on the quoted [Ref: TOKEN] thread
    (DAL-159). Returns None when the message isn't the SEND keyword — the
    caller proceeds with the normal relay. SEND is consumed as a command and
    never forwarded to the buyer.
    """
    now = now or datetime.utcnow()
    text = strip_envelope_token(inbound.body or "", inbound.envelope_token).strip().strip(".!").lower()
    if text != "send":
        return None

    token = inbound.envelope_token
    from_number = _normalize_phone(inbound.from_number)

    def _result(status: str, hold: Optional[DBAgentVoiceReplyHold] = None) -> AgentRelayResult:
        return AgentRelayResult(
            status=status,
            relayed=False,
            conversation_id=hold.conversation_id if hold else None,
            buyer_phone=hold.buyer_phone if hold else None,
        )

    def _prompt(body: str) -> None:
        if not brokerage.agents_ai_number:
            return
        get_transport().send_to_agents_ai(
            OutboundAgentMessage(
                brokerage_id=brokerage.brokerage_id,
                agents_ai_number=brokerage.agents_ai_number,
                agent_phone=from_number,
                body=body,
                conversation_id="",
                listing_id="",
                buyer_phone="",
                escalation_type="agent_voice_send_prompt",
                envelope_token=token,
            )
        )

    if not token:
        _prompt("To release a held voice note, quote-reply the [Ref: …] thread and send SEND again.")
        return _result("agent_voice_send_missing_ref")

    hold = (
        db.query(DBAgentVoiceReplyHold)
        .filter(
            DBAgentVoiceReplyHold.brokerage_id == brokerage.brokerage_id,
            DBAgentVoiceReplyHold.envelope_token == token,
            DBAgentVoiceReplyHold.status == "held",
        )
        .order_by(DBAgentVoiceReplyHold.created_at.desc())
        .first()
    )
    if not hold:
        _prompt("There's no voice note waiting for SEND on that thread.")
        return _result("agent_voice_send_no_hold")

    hold_agent_phone = _normalize_phone(hold.agent_phone)
    if hold_agent_phone and from_number != hold_agent_phone:
        record_compliance_event(
            db,
            brokerage_id=brokerage.brokerage_id,
            conversation_id=hold.conversation_id,
            listing_id=hold.listing_id,
            buyer_phone=hold.buyer_phone,
            event_type="agent_voice_send_blocked_wrong_agent",
            direction="inbound",
            details={
                "hold_id": hold.hold_id,
                "from_number": from_number,
                "expected_agent_phone": hold_agent_phone,
            },
        )
        safe_commit(db)
        return _result("agent_voice_send_blocked_wrong_agent", hold)

    route = db.get(DBAgentMessageRoute, hold.route_id)
    if not route:
        _prompt("That thread is no longer active — please type your reply instead.")
        return _result("agent_voice_send_route_missing", hold)

    delivery = _deliver_agent_reply(
        db,
        brokerage=brokerage,
        route=route,
        body=hold.transcript,
        media_url=None,
        source="agents_ai_voice_reply_confirmed",
        extra_message_metadata={
            "voice_note": {
                "direction": "agent_to_buyer",
                "transcription_text": hold.transcript,
                "transcription_language": hold.transcription_language,
                "transcription_confidence": hold.transcription_confidence,
                "transcription_provider": hold.transcription_provider,
                "confirmed_via": "send_keyword",
            }
        },
        now=now,
    )
    if delivery.relayed:
        hold.status = "sent"
        hold.released_at = now
        safe_commit(db)
        _notify_agent_on_thread(
            brokerage=brokerage,
            route=route,
            body=f'Sent as text: "{hold.transcript}"',
        )
    return delivery


def send_dashboard_escalation_reply(
    db: Session,
    *,
    brokerage: DBBrokerage,
    thread: DBEscalationThread,
    actor_user_id: str,
    body: str,
    now: Optional[datetime] = None,
) -> AgentRelayResult:
    """Send an agent-authored dashboard reply to the buyer and close the thread."""
    now = now or datetime.utcnow()
    cleaned_body = (body or "").strip()
    if not cleaned_body:
        return AgentRelayResult(
            status="empty_reply",
            relayed=False,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
            buyer_phone=thread.buyer_phone,
            reason="empty_reply",
        )

    if not brokerage.brokerage_ai_number:
        return AgentRelayResult(
            status="missing_brokerage_ai_number",
            relayed=False,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
            buyer_phone=thread.buyer_phone,
            reason="missing_brokerage_ai_number",
        )

    route = (
        db.query(DBAgentMessageRoute)
        .filter(
            DBAgentMessageRoute.thread_id == thread.thread_id,
            DBAgentMessageRoute.brokerage_id == brokerage.brokerage_id,
        )
        .order_by(DBAgentMessageRoute.created_at.desc())
        .first()
    )

    if is_buyer_suppressed(db, brokerage.brokerage_id, thread.buyer_phone):
        record_compliance_event(
            db,
            brokerage_id=brokerage.brokerage_id,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
            buyer_phone=thread.buyer_phone,
            actor_user_id=actor_user_id,
            event_type="agent_dashboard_reply_blocked_opt_out",
            direction="outbound",
            details={
                "thread_id": thread.thread_id,
                "route_id": route.route_id if route else None,
            },
        )
        safe_commit(db)
        return AgentRelayResult(
            status="agent_dashboard_reply_blocked_opt_out",
            relayed=False,
            route_id=route.route_id if route else None,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
            buyer_phone=thread.buyer_phone,
            reason="buyer_suppressed",
        )

    send_result = get_transport().send_to_buyer(
        OutboundBuyerMessage(
            brokerage_id=brokerage.brokerage_id,
            brokerage_ai_number=brokerage.brokerage_ai_number,
            buyer_phone=thread.buyer_phone,
            body=cleaned_body,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
        )
    )
    if not send_result.ok:
        record_compliance_event(
            db,
            brokerage_id=brokerage.brokerage_id,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
            buyer_phone=thread.buyer_phone,
            actor_user_id=actor_user_id,
            event_type="agent_dashboard_reply_send_failed",
            direction="outbound",
            details={
                "thread_id": thread.thread_id,
                "route_id": route.route_id if route else None,
                "error": send_result.error,
            },
        )
        safe_commit(db)
        return AgentRelayResult(
            status="agent_dashboard_reply_send_failed",
            relayed=False,
            route_id=route.route_id if route else None,
            conversation_id=thread.conversation_id,
            listing_id=thread.listing_id,
            buyer_phone=thread.buyer_phone,
            reason=send_result.error or "transport_send_failed",
        )

    db.add(DBMessage(
        conversation_id=thread.conversation_id,
        role="assistant",
        content=cleaned_body,
        intent="agent_relay",
        metadata_json={
            "source": "agent_dashboard_reply",
            "agent_user_id": actor_user_id,
            "route_id": route.route_id if route else None,
            "thread_id": thread.thread_id,
            "envelope_token": route.agents_ai_envelope_token if route else thread.envelope_token,
            "transport_message_id": send_result.transport_message_id,
        },
    ))

    conversation = db.get(DBConversation, thread.conversation_id)
    if conversation:
        conversation.updated_at = now

    assignment = (
        db.query(DBLeadAssignment)
        .filter(DBLeadAssignment.conversation_id == thread.conversation_id)
        .first()
    )
    if assignment:
        assignment.last_agent_action_at = now
        assignment.updated_at = now

    db.add(DBLeadAction(
        brokerage_id=brokerage.brokerage_id,
        conversation_id=thread.conversation_id,
        listing_id=thread.listing_id,
        buyer_phone=thread.buyer_phone,
        agent_user_id=actor_user_id,
        action_type="agent_dashboard_reply_sent",
        outcome=thread.escalation_type,
        note=cleaned_body[:500],
        payload={
            "route_id": route.route_id if route else None,
            "thread_id": thread.thread_id,
            "envelope_token": route.agents_ai_envelope_token if route else thread.envelope_token,
            "transport_message_id": send_result.transport_message_id,
        },
    ))

    if route:
        route.consumed_at = now
    thread_question_count = 0
    if route:
        from app.core.escalation_threads import resolve_thread_for_route
        thread_question_count = resolve_thread_for_route(db, route=route, now=now)
    else:
        thread.state = "resolved"
        thread.closed_at = now
        thread.close_reason = "agent_dashboard_reply"
        thread.updated_at = now
        from app.models.db_models import DBEscalationThreadQuestion
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
        thread_question_count = int(thread.question_count or len(questions))

    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=thread.conversation_id,
        listing_id=thread.listing_id,
        buyer_phone=thread.buyer_phone,
        actor_user_id=actor_user_id,
        event_type="agent_dashboard_reply_sent",
        direction="outbound",
        details={
            "thread_id": thread.thread_id,
            "route_id": route.route_id if route else None,
            "envelope_token": route.agents_ai_envelope_token if route else thread.envelope_token,
            "body_preview": cleaned_body[:200],
            "transport_message_id": send_result.transport_message_id,
            "question_count": thread_question_count or None,
        },
    )
    safe_commit(db)
    return AgentRelayResult(
        status="relayed",
        relayed=True,
        route_id=route.route_id if route else None,
        conversation_id=thread.conversation_id,
        listing_id=thread.listing_id,
        buyer_phone=thread.buyer_phone,
        transport_message_id=send_result.transport_message_id,
    )
