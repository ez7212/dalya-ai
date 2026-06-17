"""
WhatsApp API Router
Handles inbound messages from Twilio WhatsApp webhook
and outbound responses back to buyers.

Twilio webhook flow:
1. Buyer sends WhatsApp message to your Dalya number
2. Twilio POSTs to this endpoint with message details
3. We process through chatbot engine
4. We respond via Twilio API
5. If escalation triggered, alert Eric via Telegram

Setup:
- Set your Twilio webhook URL to: https://your-domain.com/api/v1/whatsapp/webhook
- Method: POST
- In Twilio console: Messaging → Active Numbers → your number → Messaging Configuration
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import func
from starlette.concurrency import run_in_threadpool
from twilio.rest import Client as TwilioClient
from twilio.request_validator import RequestValidator

from app.core.auth import CurrentUser, get_current_user, require_admin
from app.core.chatbot_engine import engine
from app.core.pii_redaction import redact_pii
from app.core.runtime_config import debug_routes_enabled, is_production
from app.core.webhook_security import mark_inbound_provider_event, record_inbound_provider_event
from app.db.session import safe_commit
from app.schemas.conversation import InboundMessage, EscalationAlert

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Twilio config ──────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None


# ── Listing ID extraction ──────────────────────────────────────────────────────

def extract_listing_id(body: str) -> Optional[str]:
    """
    Extract listing ID from message body.
    Buyers arrive via pre-filled WhatsApp links like:
    wa.me/971XXXXXXXXX?text=LISTING:abc-123-def

    Falls back to None if no listing ID found — chatbot will ask buyer.
    """
    import re
    # Look for LISTING: prefix in pre-filled messages
    match = re.search(r"LISTING:([a-f0-9\-]{36})", body, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def generate_whatsapp_link(
    phone_number: str,
    listing_id: str,
    property_name: str,
) -> str:
    """
    Generate a pre-filled WhatsApp deep link for a specific listing.
    Use this in Property Finder and Bayut listings.

    Example output:
    https://wa.me/971501234567?text=LISTING:abc-123%20Hi%2C+I%27m+interested+in+Palace+Villas+Ostra
    """
    import urllib.parse
    clean_number = phone_number.replace("+", "").replace(" ", "")
    pre_fill = f"LISTING:{listing_id} Hi, I'm interested in {property_name}"
    encoded = urllib.parse.quote(pre_fill)
    return f"https://wa.me/{clean_number}?text={encoded}"


# ── Notification helpers ───────────────────────────────────────────────────────

async def notify_managing_agent(alert: EscalationAlert):
    """
    Route an escalation alert to the listing's managing agent via the
    brokerage's Agents AI WhatsApp number (the multi-tenant path), and
    optionally also fire the legacy Telegram alert for Mahoroba's existing
    operational flow (gated by brokerage.settings.legacy_telegram_alerts).

    The Agents AI envelope carries a token so the managing agent's reply
    relays back to the original buyer on the brokerage's Brokerage AI thread.
    """
    from app.core.brokerage_resolver import (
        get_managing_agent,
        resolve_brokerage_for_listing,
    )
    from app.core.escalation_threads import send_initial_or_update
    from app.db.session import SessionLocal as _SL
    from app.models.db_models import (
        DBListing,
    )
    from app.schemas.conversation import EscalationType

    # ── Multi-tenant agent-side relay (primary path) ────────────────────────
    with _SL() as db:
        listing = db.get(DBListing, alert.listing_id)
        brokerage = resolve_brokerage_for_listing(alert.listing_id, db) if listing else None
        managing_agent = get_managing_agent(listing, db) if listing else None

        if brokerage and managing_agent and brokerage.agents_ai_number:
            tags: list[str] = []
            etype = (
                str(alert.escalation_type.value)
                if hasattr(alert.escalation_type, "value")
                else str(alert.escalation_type)
            )
            if etype == "offer":
                if getattr(alert, "is_marginal", False):
                    tags.append("near_threshold")
                else:
                    tags.append("at_or_above")
            else:
                tags.append(etype)

            envelope_body = (
                f"[{etype.upper()}] {alert.buyer_name or 'Unknown buyer'} "
                f"({alert.buyer_phone})\n\n"
                f"Property: {alert.listing_id}\n"
            )
            if alert.offer_amount_aed is not None:
                envelope_body += f"Offer: AED {alert.offer_amount_aed:,.0f}\n"
            if alert.listing_price_aed is not None:
                envelope_body += f"Asking: AED {alert.listing_price_aed:,.0f}\n"
            if alert.negotiation_threshold_aed is not None:
                envelope_body += f"Notification threshold: AED {alert.negotiation_threshold_aed:,.0f}\n"
            if alert.escalation_subtype:
                envelope_body += f"Subtype: {alert.escalation_subtype}\n"
            if alert.seller_intent:
                envelope_body += f"Seller intent: {alert.seller_intent}\n"
            voice_transcribed = bool((alert.payload or {}).get("voice_transcribed"))
            if alert.payload:
                payload_lines = [
                    f"- {key}: {value}"
                    for key, value in alert.payload.items()
                    if value is not None and value != "" and value != []
                    and key != "voice_transcribed"
                ]
                if payload_lines:
                    envelope_body += "Payload:\n" + "\n".join(payload_lines) + "\n"
            if tags:
                envelope_body += f"Tags: {', '.join(tags)}\n"
            # DAL-159 Path C: label voice provenance so the agent knows the
            # quoted text came from a transcription.
            if voice_transcribed:
                envelope_body += f"\nBuyer message 🎙 (voice, transcribed):\n\"{alert.trigger_message}\""
            else:
                envelope_body += f"\nBuyer message:\n\"{alert.trigger_message}\""
            if alert.conversation_summary:
                envelope_body += f"\n\nSummary: {alert.conversation_summary}"

            threaded_result = send_initial_or_update(
                db,
                brokerage=brokerage,
                alert=alert,
                managing_agent=managing_agent,
                envelope_body=envelope_body,
                tags=tags,
                expires_at=datetime.utcnow() + timedelta(days=7),
            )

            # DAL-165: offer-classified escalations with an extracted amount
            # create a DRAFT_PENDING_CONFIRM offer anchored to the buyer's
            # message. No amount → escalation only, no draft, no hallucination.
            if etype == "offer" and alert.conversation_id:
                try:
                    from app.core.offers import create_draft_offer_from_alert
                    from app.models.db_models import DBConversation as _DBConversation

                    conv_row = db.get(_DBConversation, alert.conversation_id)
                    if conv_row:
                        create_draft_offer_from_alert(
                            db,
                            brokerage_id=brokerage.brokerage_id,
                            conversation=conv_row,
                            listing_id=alert.listing_id,
                            amount=alert.offer_amount_aed,
                            trigger_message=alert.trigger_message or "",
                            escalation_thread_id=(
                                threaded_result.thread.thread_id
                                if threaded_result.thread is not None
                                else None
                            ),
                        )
                except Exception:
                    logger.warning("Draft offer creation failed", exc_info=True)

            if threaded_result.action in {"debounced", "initial_sent", "update_debounced", "update_sent"}:
                return

        # If legacy_telegram_alerts is disabled on this brokerage, stop here.
        legacy_telegram = True
        if brokerage and isinstance(brokerage.settings, dict):
            legacy_telegram = bool(brokerage.settings.get("legacy_telegram_alerts", True))
        if not legacy_telegram:
            return

    # ── Legacy Telegram alert (Mahoroba operational continuity) ─────────────

    if alert.escalation_type == EscalationType.offer:
        threshold_line = (
            f"Negotiation threshold: AED {alert.negotiation_threshold_aed:,.0f}"
            if alert.negotiation_threshold_aed
            else "Negotiation threshold: not set"
        )
        message = f"""
💰 OFFER RECEIVED — {alert.buyer_name or 'Unknown buyer'} ({alert.buyer_phone})

Property: {alert.listing_id}
Listing price: AED {alert.listing_price_aed:,.0f}
{threshold_line}
Offer: AED {alert.offer_amount_aed:,.0f}

Their message:
"{alert.trigger_message}"

Summary: {alert.conversation_summary or 'N/A'}
""".strip()

    else:  # non-offer alert
        payload_text = ""
        if alert.payload:
            payload_lines = [
                f"- {key}: {value}"
                for key, value in alert.payload.items()
                if value is not None and value != "" and value != []
            ]
            if payload_lines:
                payload_text = "\n\nPayload:\n" + "\n".join(payload_lines)
        message = f"""
❓ QUESTIONS FORWARDED — {alert.buyer_name or 'Unknown buyer'} ({alert.buyer_phone})

Property: {alert.listing_id}
Type: {alert.escalation_type}
Subtype: {alert.escalation_subtype or 'N/A'}

Questions the AI couldn't answer:
{alert.trigger_message}
{payload_text}

Reply to THIS message on Telegram and Dalya will forward it to the buyer on WhatsApp.
""".strip()

    # Clear pending forwarded questions after sending the alert.
    # Move them into alerted_questions so they are never re-alerted.
    if str(alert.escalation_type) in {"unanswerable_question", "info_gap"}:
        from app.db.session import SessionLocal as _SL
        from app.models.db_models import DBConversation
        with _SL() as db:
            conv = db.get(DBConversation, alert.conversation_id)
            if conv:
                alerted = list(conv.alerted_questions or [])
                for q in (conv.pending_forwarded_questions or []):
                    if q not in alerted:
                        alerted.append(q)
                conv.alerted_questions = alerted
                conv.pending_forwarded_questions = []
                safe_commit(db)

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if telegram_token and telegram_chat_id:
        import httpx
        from app.db.session import SessionLocal
        from app.models.db_models import DBTelegramReplyRoute
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={"chat_id": telegram_chat_id, "text": message},
                    timeout=10,
                )
                data = resp.json()
                if data.get("ok"):
                    telegram_message_id = data["result"]["message_id"]
                    with SessionLocal() as db:
                        db.add(DBTelegramReplyRoute(
                            telegram_message_id=telegram_message_id,
                            buyer_phone=alert.buyer_phone,
                            conversation_id=alert.conversation_id,
                            listing_id=alert.listing_id,
                            buyer_name=alert.buyer_name,
                            alert_questions=(
                                alert.trigger_message
                                if str(alert.escalation_type) == "unanswerable_question"
                                else None
                            ),
                        ))
                        safe_commit(db)
        except Exception as e:
            logger.warning(f"[conv:{alert.conversation_id[:8]}] Failed to send Telegram alert: {e}")
    else:
        logger.info(
            "[conv:%s] Escalation alert (no Telegram configured):\n%s",
            alert.conversation_id[:8],
            redact_pii(message),
        )


def send_whatsapp_reply(
    to_number: str,
    body: str,
    media_url: Optional[str] = None,
    from_number: Optional[str] = None,
    brokerage_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    listing_id: Optional[str] = None,
):
    """
    Send a WhatsApp message to a buyer through the active MessagingTransport.

    `from_number` should be the brokerage's `brokerage_ai_number`. When omitted
    (legacy callers), falls back to the global TWILIO_WHATSAPP_NUMBER so the
    pre-multi-tenant Mahoroba flow keeps working.
    """
    from app.core.messaging import get_transport
    from app.core.messaging.types import OutboundBuyerMessage
    from app.core.brokerage_access import (
        is_buyer_suppressed,
        record_compliance_event,
    )
    from app.db.session import SessionLocal

    sender = from_number or TWILIO_WHATSAPP_NUMBER
    # Strip whatsapp: prefix — transports normalise on the way out.
    if sender.startswith("whatsapp:"):
        sender = sender[len("whatsapp:"):]
    if to_number.startswith("whatsapp:"):
        to_number = to_number[len("whatsapp:"):]

    if brokerage_id:
        with SessionLocal() as db:
            if is_buyer_suppressed(db, brokerage_id, to_number):
                record_compliance_event(
                    db,
                    brokerage_id=brokerage_id,
                    conversation_id=conversation_id,
                    listing_id=listing_id,
                    buyer_phone=to_number,
                    event_type="outbound_blocked_opt_out",
                    direction="outbound",
                    details={
                        "media_url": media_url,
                        "body_preview": body[:200],
                    },
                )
                logger.info(
                    "[suppressed] Skipping outbound buyer message for %s on brokerage %s",
                    redact_pii(to_number),
                    brokerage_id,
                )
                return

    result = get_transport().send_to_buyer(
        OutboundBuyerMessage(
            brokerage_id=brokerage_id or "",
            brokerage_ai_number=sender,
            buyer_phone=to_number,
            body=body,
            media_url=media_url,
            conversation_id=conversation_id,
            listing_id=listing_id,
        )
    )
    if brokerage_id and result.ok:
        with SessionLocal() as db:
            record_compliance_event(
                db,
                brokerage_id=brokerage_id,
                conversation_id=conversation_id,
                listing_id=listing_id,
                buyer_phone=to_number,
                event_type="outbound_buyer_message",
                direction="outbound",
                details={
                    "media_url": media_url,
                    "body_preview": body[:200],
                    "transport": type(get_transport()).__name__,
                    "transport_message_id": result.transport_message_id,
                },
            )


# ── Webhook endpoint ───────────────────────────────────────────────────────────

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...),
    NumMedia: str = Form(default="0"),
):
    """
    Twilio WhatsApp webhook endpoint.
    Called every time a buyer sends a message to your Dalya WhatsApp number.

    Twilio sends form-encoded POST data with these fields.
    Returns TwiML (empty response — we send replies via API, not TwiML).
    """
    empty_twiml = PlainTextResponse(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
    )

    # Validate request is actually from Twilio.
    # Uses PUBLIC_URL so the URL matches what Twilio signed — str(request.url)
    # would give the internal host (e.g. localhost) behind a proxy and fail.
    form_data = dict(await request.form())
    provider = "twilio"
    endpoint = "whatsapp/webhook"
    public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
    if is_production() and not TWILIO_AUTH_TOKEN:
        raise HTTPException(status_code=503, detail="Twilio signature verification is not configured")
    if is_production() and not public_url:
        raise HTTPException(status_code=503, detail="PUBLIC_URL is required for Twilio signature verification")
    if TWILIO_AUTH_TOKEN and public_url:
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        webhook_url = f"{public_url}/api/v1/whatsapp/webhook"
        signature = request.headers.get("X-Twilio-Signature", "")
        if not validator.validate(webhook_url, form_data, signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    from app.db.session import SessionLocal
    with SessionLocal() as db:
        is_new_event = record_inbound_provider_event(
            db,
            provider=provider,
            endpoint=endpoint,
            provider_event_id=MessageSid,
            payload=form_data,
        )
        if not is_new_event:
            logger.info("[WhatsApp] Duplicate Twilio MessageSid ignored: %s", MessageSid)
            return empty_twiml

    def _mark_provider_event(status: str) -> None:
        with SessionLocal() as db:
            mark_inbound_provider_event(
                db,
                provider=provider,
                endpoint=endpoint,
                provider_event_id=MessageSid,
                payload=form_data,
                status=status,
            )

    def _processed_response() -> PlainTextResponse:
        _mark_provider_event("processed")
        return empty_twiml

    # ── Agents AI reply path ────────────────────────────────────────────────
    # Messages sent to a brokerage's Agents AI number are managing-agent
    # replies to an escalation envelope. They bypass buyer debounce/chatbot
    # processing entirely and are relayed directly to the original buyer when
    # the envelope reference is valid.
    from app.core.brokerage_resolver import (
        resolve_brokerage_by_agents_ai_number,
        resolve_brokerage_by_inbound_number,
    )
    from app.core.messaging import get_transport
    with SessionLocal() as db:
        agents_brokerage = resolve_brokerage_by_agents_ai_number(To, db)
        if agents_brokerage:
            from app.core.agent_relay import (
                handle_agent_send_keyword,
                relay_agent_reply,
            )
            from app.core.conversation_takeover import handle_agents_ai_mode_keyword

            inbound = get_transport().parse_inbound(form_data)

            # TAKEOVER / RESUME are commands — consumed here, never relayed to
            # the buyer (DAL-158 live conversation takeover).
            keyword_result = handle_agents_ai_mode_keyword(
                db, brokerage=agents_brokerage, inbound=inbound
            )
            if keyword_result is not None:
                logger.info(
                    "[AgentsAI] mode keyword=%s status=%s conversation=%s",
                    keyword_result.keyword,
                    keyword_result.status,
                    keyword_result.conversation_id,
                )
                return _processed_response()

            # SEND releases a held voice transcript (DAL-159) — also a command,
            # never relayed to the buyer as literal text.
            send_result = handle_agent_send_keyword(
                db, brokerage=agents_brokerage, inbound=inbound
            )
            if send_result is not None:
                logger.info(
                    "[AgentsAI] SEND keyword status=%s relayed=%s conversation=%s",
                    send_result.status,
                    send_result.relayed,
                    send_result.conversation_id,
                )
                return _processed_response()

            # UNDO cancels held relay items (DAL-161) — consumed, never forwarded.
            from app.core.relay_media import (
                handle_agents_ai_undo_keyword,
                route_agents_ai_inbound,
            )

            undo_result = handle_agents_ai_undo_keyword(
                db, brokerage=agents_brokerage, inbound=inbound
            )
            if undo_result is not None:
                logger.info("[AgentsAI] UNDO status=%s", undo_result.status)
                return _processed_response()

            # Relay media + session routing (DAL-161): caption token → quote →
            # session → single media-request escalation → park/bounce. Returns
            # None when the message is a plain quoted reply for the standard
            # relay below.
            routing_result = route_agents_ai_inbound(
                db, brokerage=agents_brokerage, inbound=inbound
            )
            if routing_result is not None:
                logger.info(
                    "[AgentsAI] relay routing status=%s method=%s conversation=%s items=%d",
                    routing_result.status,
                    routing_result.routing_method,
                    routing_result.conversation_id,
                    len(routing_result.item_ids),
                )
                if routing_result.handled:
                    return _processed_response()
                # A quote-reply that answered a parking prompt also relays its
                # text body through the standard relay below.

            result = relay_agent_reply(db, brokerage=agents_brokerage, inbound=inbound)
            logger.info(
                "[AgentsAI] inbound reply status=%s relayed=%s route=%s",
                result.status,
                result.relayed,
                result.route_id,
            )
            return _processed_response()

        buyer_brokerage = resolve_brokerage_by_inbound_number(To, db)
        if buyer_brokerage:
            from app.core.post_viewing_capture import handle_buyer_post_viewing_reply
            from app.core.tenant_viewings import handle_tenant_viewing_reply

            inbound = get_transport().parse_inbound(form_data)
            handled, confirmation = handle_tenant_viewing_reply(
                db,
                brokerage=buyer_brokerage,
                tenant_phone=inbound.from_number,
                body=inbound.body,
                message_sid=inbound.message_sid,
            )
            if handled:
                logger.info(
                    "[TenantViewing] inbound reply status=%s confirmation=%s",
                    confirmation.status if confirmation else None,
                    confirmation.confirmation_id if confirmation else None,
                )
                return _processed_response()
            handled_feedback, feedback = handle_buyer_post_viewing_reply(
                db,
                brokerage=buyer_brokerage,
                buyer_phone=inbound.from_number,
                body=inbound.body,
                message_sid=inbound.message_sid,
            )
            if handled_feedback:
                logger.info(
                    "[PostViewing] inbound buyer feedback status=%s feedback=%s",
                    feedback.status if feedback else None,
                    feedback.feedback_id if feedback else None,
                )
                return _processed_response()

    # Strip whatsapp: prefix for our internal use
    buyer_phone = From.replace("whatsapp:", "")

    # Extract listing ID from message if pre-filled
    listing_id = extract_listing_id(Body)

    inbound = InboundMessage(
        from_number=buyer_phone,
        to_number=To,
        body=Body,
        message_sid=MessageSid,
        listing_id=listing_id,
    )

    # Save to debounce queue — worker will process after DEBOUNCE_SECONDS of silence
    from app.models.db_models import DBMessageQueue

    # ── Empty message guard ──────────────────────────────────────────────────
    num_media = int(NumMedia or "0")
    media_urls = [str(form_data.get(f"MediaUrl{i}") or "") for i in range(num_media)]
    media_urls = [url for url in media_urls if url]
    media_content_types = [
        str(form_data.get(f"MediaContentType{i}") or "") for i in range(num_media)
    ]
    has_audio_media = any(
        content_type.startswith("audio/") for content_type in media_content_types
    )
    has_video_media = any(
        content_type.startswith("video/") for content_type in media_content_types
    )
    # Audio is transcribed; video is enqueued so the worker can run the
    # media_unprocessable flow (forward-to-agent, never silent — DAL-159).
    if (not Body or not Body.strip()) and not has_audio_media and not has_video_media:
        send_whatsapp_reply(
            f"whatsapp:{buyer_phone}",
            "Hi! It looks like your message didn't come through. Could you try sending that again?"
        )
        return _processed_response()

    # ── Per-phone rate limiting (10 msgs / 60s) ──────────────────────────────
    with SessionLocal() as db:
        cutoff = datetime.utcnow() - timedelta(seconds=60)
        count = db.query(func.count(DBMessageQueue.id)).filter(
            DBMessageQueue.from_number == buyer_phone,
            DBMessageQueue.received_at >= cutoff,
        ).scalar()
        if count >= 10:
            logger.warning(
                "[RateLimit] Dropped message from %s — %s messages in last 60s",
                redact_pii(buyer_phone),
                count,
            )
            return _processed_response()

    with SessionLocal() as db:
        existing = (
            db.query(DBMessageQueue.id)
            .filter(DBMessageQueue.message_sid == MessageSid)
            .first()
        )
        if existing:
            logger.info("[WhatsApp] Duplicate Twilio MessageSid ignored: %s", MessageSid)
            return _processed_response()

        db.add(DBMessageQueue(
            from_number=buyer_phone,
            to_number=To,
            body=Body,
            message_sid=MessageSid,
            listing_id=listing_id,
            media_urls=media_urls,
            media_content_types=media_content_types,
            metadata_json={"has_audio_media": has_audio_media} if has_audio_media else {},
        ))
        safe_commit(db)

    # Return empty TwiML immediately — reply will be sent by debounce worker
    return _processed_response()


# ── Direct message endpoint (for testing without Twilio) ──────────────────────

@router.post("/whatsapp/send-test")
async def send_test_message(
    listing_id: str,
    buyer_phone: str,
    message: str,
):
    """
    Test endpoint — simulate a buyer message without going through Twilio.
    Use this to test the chatbot during development.

    Example:
    POST /api/v1/whatsapp/send-test?listing_id=abc&buyer_phone=+971501234567&message=What is the price?
    """
    if not debug_routes_enabled():
        raise HTTPException(status_code=404, detail="Not found")

    # Handle empty messages gracefully
    if not message or not message.strip():
        return {
            "buyer_message": message,
            "bot_response": "Hi! It looks like your message didn't come through. Could you try sending that again?",
            "escalation_triggered": False,
            "escalation": None,
            "media_url": None,
        }

    inbound = InboundMessage(
        from_number=buyer_phone,
        to_number=TWILIO_WHATSAPP_NUMBER,
        body=message,
        message_sid=f"TEST_{listing_id}",
        listing_id=listing_id,
    )

    response_text, escalation, media_url = await run_in_threadpool(
        engine.handle_message_resilient,
        inbound,
    )

    return {
        "buyer_message": message,
        "bot_response": response_text,
        "escalation_triggered": escalation is not None,
        "escalation": escalation.model_dump() if escalation else None,
        "media_url": media_url,
    }


@router.post("/whatsapp/send-test-voice")
async def send_test_voice_note(
    listing_id: str,
    buyer_phone: str,
    audio_path: Optional[str] = None,
    transcript_text: Optional[str] = None,
    content_type: str = "audio/ogg",
):
    """
    Test endpoint — simulate a buyer voice note without going through Twilio.
    If `transcript_text` is provided, it is used as an already-transcribed
    voice note so simulations can exercise routing without provider calls.
    """
    if not debug_routes_enabled():
        raise HTTPException(status_code=404, detail="Not found")

    if not audio_path and not transcript_text:
        raise HTTPException(status_code=400, detail="Provide audio_path or transcript_text")

    from app.core.transcription.models import (
        TranscriptionContext,
        TranscriptionResult,
    )
    from app.core.transcription.post_processor import ClaudeTranscriptPostProcessor
    from app.core.transcription.dictionary import load_transcription_dictionary
    from app.core.voice_notes import transcribe_audio_file, transcription_result_metadata
    from app.db.session import SessionLocal
    from app.models.db_models import DBListing

    asking_price = None
    with SessionLocal() as db:
        listing = db.get(DBListing, listing_id)
        if listing:
            spa = listing.spa_data or {}
            asking_price = listing.seller_asking_price or spa.get("purchase_price_aed")

    context = TranscriptionContext(
        listing_id=listing_id,
        asking_price_aed=asking_price,
    )
    if transcript_text:
        corrected, prices, low_segments, normalized_terms = ClaudeTranscriptPostProcessor().process(
            transcript_text,
            load_transcription_dictionary(),
            context,
        )
        result = TranscriptionResult(
            provider="provided",
            raw_transcript=transcript_text,
            corrected_transcript=corrected,
            prices=prices,
            low_confidence_segments=low_segments,
            normalized_terms=normalized_terms,
        )
    else:
        result = await run_in_threadpool(
            transcribe_audio_file,
            audio_path,
            content_type=content_type,
            audio_type="buyer_voice",
            context=context,
        )

    metadata = transcription_result_metadata(
        result,
        direction="buyer_to_property_advisor",
        audio_url=audio_path,
    )
    inbound = InboundMessage(
        from_number=buyer_phone,
        to_number=TWILIO_WHATSAPP_NUMBER,
        body=result.corrected_transcript,
        message_sid=f"TEST_VOICE_{listing_id}",
        listing_id=listing_id,
        metadata=metadata,
    )

    response_text, escalation, media_url = await run_in_threadpool(
        engine.handle_message_resilient,
        inbound,
    )

    return {
        "buyer_transcript": result.corrected_transcript,
        "transcription": result.model_dump(),
        "bot_response": response_text,
        "escalation_triggered": escalation is not None,
        "escalation": escalation.model_dump() if escalation else None,
        "media_url": media_url,
    }


# ── Listing management endpoints ───────────────────────────────────────────────

@router.post("/listings/{listing_id}/activate")
async def activate_listing_chatbot(
    listing_id: str,
    seller_asking_price: Optional[float] = None,
    seller_notes: Optional[str] = None,
    negotiation_threshold_aed: Optional[float] = None,
    seller_phone: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Activate the chatbot for a listing that's already been parsed.
    Call this after /parse-spa to make the listing live.
    """
    import asyncio
    from app.db.session import SessionLocal
    from app.db import crud
    from app.schemas.spa import SPAParseResult
    from app.core.community_data import get_community_data_for_listing
    from app.core.listing_stages import update_stage
    from app.models.db_models import DBCommunityResearch

    community_research_status = None

    with SessionLocal() as db:
        row = crud.get_listing(db, listing_id)
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Listing not found. Parse the SPA first via /api/v1/parse-spa"
            )

        spa = SPAParseResult.model_validate(row.spa_data)

        # Assign listing to the authenticated seller
        row.seller_id = user.id
        if seller_phone:
            row.seller_phone = seller_phone

        # Initialize processing stages if not already set
        if not row.processing_stages:
            from app.core.listing_stages import default_stages
            row.processing_stages = default_stages()

        safe_commit(db)

        # Auto-attach community data if a knowledge base exists for this project
        community_data = get_community_data_for_listing(spa.project, developer=spa.developer)

        if community_data:
            # Community data exists — mark research stage as complete
            if row.processing_stages:
                row.processing_stages = update_stage(
                    row.processing_stages, "community_research", "complete",
                    note="Community data loaded"
                )
                safe_commit(db)
            community_research_status = "complete"
        else:
            # No community data — check if research job exists or create one
            existing_research = db.query(DBCommunityResearch).filter(
                DBCommunityResearch.project_name.ilike(f"%{spa.project}%")
            ).first()

            if existing_research and existing_research.status == "approved":
                # Research exists and is approved but wasn't matched by alias —
                # this is a matching issue, not a research issue
                row.processing_stages = update_stage(
                    row.processing_stages, "community_research", "blocked",
                    note="Community data exists but alias matching failed — admin review needed"
                )
                safe_commit(db)
                community_research_status = existing_research.status
            elif existing_research and existing_research.status in ("pending", "researching", "needs_review"):
                # Research is already in progress
                status_map = {
                    "pending": ("in_progress", "Community research queued — starting shortly"),
                    "researching": ("in_progress", "Researching community data — typically 15-20 minutes"),
                    "needs_review": ("blocked", "Community research complete — typically reviewed within 24 hours"),
                }
                stage_status, stage_note = status_map[existing_research.status]
                row.processing_stages = update_stage(
                    row.processing_stages, "community_research", stage_status,
                    note=stage_note
                )
                safe_commit(db)
                community_research_status = existing_research.status
            else:
                # No research exists — create via get_or_create to avoid race conditions
                from sqlalchemy.exc import IntegrityError
                try:
                    new_research = DBCommunityResearch(
                        project_name=spa.project,
                        developer=spa.developer,
                        status="pending",
                    )
                    db.add(new_research)
                    db.flush()
                    should_launch = True
                except IntegrityError:
                    # Another request already created a record — use it
                    db.rollback()
                    new_research = db.query(DBCommunityResearch).filter_by(
                        project_name=spa.project, developer=spa.developer,
                    ).first()
                    should_launch = False

                row.processing_stages = update_stage(
                    row.processing_stages, "community_research", "in_progress",
                    note="Researching community data — typically 15-20 minutes"
                )
                safe_commit(db)
                community_research_status = "triggered"

                # Launch research in background only if we created the record
                if should_launch:
                    from app.core.community_researcher import CommunityResearcher

                    async def _run_research():
                        researcher = CommunityResearcher()
                        try:
                            await researcher.research_community(
                                project_name=spa.project,
                                developer=spa.developer,
                                sub_community=spa.sub_community,
                            )
                        except Exception as e:
                            logger.error(f"Community research failed for {spa.project}: {e}")

                    asyncio.create_task(_run_research())

    engine.register_listing(
        listing_id=listing_id,
        spa=spa,
        community_data=community_data,
        seller_asking_price=seller_asking_price,
        seller_notes=seller_notes,
        negotiation_threshold_aed=negotiation_threshold_aed,
    )

    # Generate the WhatsApp deep link for portals
    dalya_number = os.getenv("DALYA_PHONE_NUMBER", "+971500000000")
    wa_link = generate_whatsapp_link(dalya_number, listing_id, spa.project)

    return {
        "success": True,
        "listing_id": listing_id,
        "developer": spa.developer,
        "property": spa.project,
        "sub_community": spa.sub_community,
        "unit": spa.unit_number,
        "community_data_loaded": community_data is not None,
        "community_research_status": community_research_status,
        "whatsapp_link": wa_link,
        "message": "Chatbot is live. Use the whatsapp_link in your portal listings.",
    }


@router.get("/listings")
async def list_all_listings(admin: CurrentUser = Depends(require_admin)):
    """Return summary data for every listing — powers the multi-listing admin dashboard.

    Response shape matches the frontend AdminData contract: wrapped object
    with platform-level totals plus a list of listings using the frontend's
    field names (id/property_name/asking_price/etc).
    """
    import asyncio
    from app.db.session import SessionLocal
    from app.models.db_models import DBListing, DBConversation, DBBuyerProfile

    def _query():
        with SessionLocal() as db:
            listings = db.query(DBListing).all()
            stats_rows = (
                db.query(
                    DBConversation.listing_id,
                    func.count(DBConversation.conversation_id).label("conversations"),
                    func.count(DBConversation.conversation_id)
                    .filter(DBConversation.escalation_triggered.is_(True))
                    .label("escalated"),
                    func.max(DBConversation.updated_at).label("last_activity"),
                )
                .group_by(DBConversation.listing_id)
                .all()
            )
            stats_by_listing = {
                row.listing_id: {
                    "conversations": row.conversations or 0,
                    "escalated": row.escalated or 0,
                    "last_activity": row.last_activity,
                }
                for row in stats_rows
            }
            seller_ids = {listing.seller_id for listing in listings if listing.seller_id}
            seller_names = {}
            if seller_ids:
                profiles = (
                    db.query(DBBuyerProfile.phone, DBBuyerProfile.name)
                    .filter(DBBuyerProfile.phone.in_(seller_ids))
                    .all()
                )
                seller_names = {phone: name for phone, name in profiles if name}

            results = []
            total_conversations = 0
            total_escalated = 0
            unique_sellers = set()
            for listing in listings:
                spa = listing.spa_data or {}
                stats = stats_by_listing.get(listing.listing_id, {})
                convs = stats.get("conversations", 0)
                esc = stats.get("escalated", 0)
                total_conversations += convs
                total_escalated += esc

                if listing.seller_id:
                    unique_sellers.add(listing.seller_id)

                # Last activity: most recent conversation updated_at, or listing created_at
                last_activity = stats.get("last_activity") or listing.created_at

                # Look up the seller's email if we have a seller_id
                seller_email = seller_names.get(listing.seller_id, "") if listing.seller_id else ""

                # Derive a simple 'active' | 'draft' status from listing readiness.
                # A listing is considered active when it has both an asking price
                # AND has been parsed (spa_data present). Otherwise draft.
                derived_status = "active" if (
                    listing.seller_asking_price and listing.spa_data
                ) else "draft"

                results.append({
                    "id": listing.listing_id,
                    "property_name": spa.get("project", "Unknown"),
                    "unit_number": spa.get("unit_number", "—"),
                    "seller_email": seller_email,
                    "seller_id": listing.seller_id or "",
                    "asking_price": listing.seller_asking_price or 0,
                    "status": derived_status,
                    "conversations": convs,
                    "escalated": esc,
                    "last_activity": last_activity.isoformat() if last_activity else None,
                })

            return {
                "listings": results,
                "total_listings": len(results),
                "total_sellers": len(unique_sellers),
                "total_conversations": total_conversations,
                "total_escalated": total_escalated,
            }

    return await asyncio.get_event_loop().run_in_executor(None, _query)


@router.get("/listings/{listing_id}/portal-links")
async def get_portal_links(listing_id: str):
    """Return portal deep links for a listing — WhatsApp, Property Finder, Bayut."""
    import urllib.parse
    from app.db.session import SessionLocal
    from app.db import crud

    with SessionLocal() as db:
        row = crud.get_listing(db, listing_id)

    if not row:
        raise HTTPException(status_code=404, detail="Listing not found.")

    spa = row.spa_data or {}
    project_name = spa.get("project", "")

    dalya_number = os.getenv("DALYA_PHONE_NUMBER", "+971500000000")
    wa_link = generate_whatsapp_link(dalya_number, listing_id, project_name)

    return {
        "whatsapp": wa_link,
        "property_finder": f"https://www.propertyfinder.ae/en/search?q={urllib.parse.quote(project_name)}",
        "bayut": f"https://www.bayut.com/to-rent/property/dubai/?q={urllib.parse.quote(project_name)}",
    }


@router.get("/listings/{listing_id}/stats")
async def get_listing_stats(listing_id: str):
    """Get conversation stats for a listing — powers the seller dashboard."""
    return engine.get_listing_stats(listing_id)


@router.get("/listings/{listing_id}/conversations")
async def get_conversations(listing_id: str):
    """Get all conversations for a listing."""
    conversations = engine.get_all_conversations(listing_id)
    return {
        "listing_id": listing_id,
        "conversations": [c.model_dump() for c in conversations],
    }


@router.post("/listings/{listing_id}/media")
async def add_listing_media(listing_id: str, urls: list[str]):
    """
    Append render / floor-plan URLs to a listing's media_urls.
    Body: {"urls": ["https://..."]}
    """
    from app.db.session import SessionLocal
    from app.models.db_models import DBListing

    with SessionLocal() as db:
        listing = db.get(DBListing, listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found.")

        existing = list(listing.media_urls or [])
        for url in urls:
            if url not in existing:
                existing.append(url)
        listing.media_urls = existing
        safe_commit(db)

    return {"listing_id": listing_id, "media_urls": existing}
