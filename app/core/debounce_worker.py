"""
Debounce Worker
Runs as a background asyncio task alongside FastAPI.

At a configurable interval, it checks for phone numbers whose last pending message
arrived more than DEBOUNCE_SECONDS ago. When the window closes, it:
  1. Collects all pending messages from that phone in the window
  2. Concatenates them into a single input
  3. Processes through the chatbot engine
  4. Sends the reply via Twilio
  5. Marks all collected messages as done

This means buyers can send 2-3 quick follow-up messages and the AI
responds once with full context — rather than interrupting mid-thought.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from app.db.session import SessionLocal, safe_commit
from app.models.db_models import DBMessageQueue
from app.schemas.conversation import InboundMessage

logger = logging.getLogger(__name__)

DEBOUNCE_SECONDS = int(os.getenv("DEBOUNCE_SECONDS", "5"))
DEBOUNCE_POLL_INTERVAL_SECONDS = float(os.getenv("DEBOUNCE_POLL_INTERVAL_SECONDS", "5"))


async def run_debounce_worker():
    """
    Main worker loop. Runs forever, checking the queue at the configured interval.
    Started in FastAPI lifespan — runs until server shuts down.
    """
    logger.info(
        "Debounce worker started "
        f"(window: {DEBOUNCE_SECONDS}s, poll: {DEBOUNCE_POLL_INTERVAL_SECONDS}s)"
    )

    while True:
        try:
            await _process_ready_batches()
            with SessionLocal() as db:
                from app.core.escalation_threads import process_due_escalation_threads
                process_due_escalation_threads(db)
            with SessionLocal() as db:
                # DAL-161: release due held relay items, expire stale parked media.
                from app.core.relay_media import process_relay_outbox
                process_relay_outbox(db)
        except Exception as e:
            logger.error(f"Debounce worker error: {e}", exc_info=True)

        await asyncio.sleep(DEBOUNCE_POLL_INTERVAL_SECONDS)


async def _process_ready_batches():
    """
    Find all phone numbers whose debounce window has closed and process them.
    """
    cutoff = datetime.utcnow() - timedelta(seconds=DEBOUNCE_SECONDS)
    batches = []

    with SessionLocal() as db:
        # Phones that still have pending messages newer than cutoff (still typing)
        from sqlalchemy import select
        still_typing = (
            select(DBMessageQueue.from_number)
            .where(
                DBMessageQueue.status == "pending",
                DBMessageQueue.received_at > cutoff,
            )
            .scalar_subquery()
        )

        # Phones with pending messages that have gone quiet (window closed)
        ready_phones = (
            db.query(DBMessageQueue.from_number)
            .filter(
                DBMessageQueue.status == "pending",
                DBMessageQueue.received_at <= cutoff,
                ~DBMessageQueue.from_number.in_(still_typing),
            )
            .distinct()
            .all()
        )

        for row in ready_phones:
            phone = row.from_number

            pending = (
                db.query(DBMessageQueue)
                .filter(
                    DBMessageQueue.from_number == phone,
                    DBMessageQueue.status == "pending",
                )
                .order_by(DBMessageQueue.received_at.asc())
                .all()
            )

            if not pending:
                continue

            # Mark as processing atomically before we release the DB session
            ids = [m.id for m in pending]
            db.query(DBMessageQueue).filter(
                DBMessageQueue.id.in_(ids)
            ).update({"status": "processing"}, synchronize_session=False)
            safe_commit(db)

            # Build the combined message
            bodies = [m.body for m in pending]
            combined_body = "\n".join(bodies) if len(bodies) > 1 else bodies[0]
            listing_id = next((m.listing_id for m in pending if m.listing_id), None)
            media_urls = []
            media_content_types = []
            metadata_items = []
            for message in pending:
                media_urls.extend(list(message.media_urls or []))
                media_content_types.extend(list(message.media_content_types or []))
                if message.metadata_json:
                    metadata_items.append(dict(message.metadata_json))

            batches.append({
                "phone": phone,
                "combined_body": combined_body,
                "listing_id": listing_id,
                "to_number": pending[0].to_number,
                "message_sid": pending[0].message_sid,
                "media_urls": media_urls,
                "media_content_types": media_content_types,
                "metadata_items": metadata_items,
                "ids": ids,
            })

    # Process all batches outside the DB session
    for batch in batches:
        await _handle_batch(**batch)


async def _handle_batch(
    phone: str,
    combined_body: str,
    listing_id: Optional[str],
    to_number: str,
    message_sid: str,
    media_urls: list,
    media_content_types: list,
    metadata_items: list,
    ids: list,
):
    """Process a debounced batch and send the reply."""
    from app.core.chatbot_engine import engine as chat_engine
    from app.api.whatsapp import send_whatsapp_reply, notify_managing_agent
    from app.core.brokerage_resolver import resolve_brokerage_by_inbound_number
    from app.core.brokerage_access import (
        is_buyer_suppressed,
        is_opt_out_message,
        record_compliance_event,
    )

    inbound_body = combined_body
    inbound_metadata = {}
    if media_urls or metadata_items:
        audio_present = any(
            (content_type or "").lower().startswith("audio/")
            for content_type in media_content_types
        ) or any(item.get("audio_path") for item in metadata_items)
        video_present = any(
            (content_type or "").lower().startswith("video/")
            for content_type in media_content_types
        )
        try:
            if video_present or (media_urls and not audio_present and not combined_body.strip()):
                # Video notes and unsupported attachments are forward-to-agent
                # only — never silently dropped (DAL-159 out-of-scope handling).
                raise UnprocessableMediaError("unsupported media type (video or unknown attachment)")
            if audio_present:
                inbound_body, inbound_metadata = await _prepare_voice_inbound(
                    combined_body=combined_body,
                    listing_id=listing_id,
                    media_urls=media_urls,
                    media_content_types=media_content_types,
                    metadata_items=metadata_items,
                )
        except Exception as exc:
            # DAL-159 failure mode: never silent. The buyer gets one polite
            # fallback in conversation language and the conversation escalates
            # with reason media_unprocessable. No AI answer is attempted.
            logger.warning("Voice/media processing failed for %s: %s", phone, exc)
            await _handle_unprocessable_media(
                phone=phone,
                to_number=to_number,
                listing_id=listing_id,
                combined_body=combined_body,
                error=str(exc),
            )
            _mark_messages(ids, "done")
            return

    inbound = InboundMessage(
        from_number=phone,
        to_number=to_number,
        body=inbound_body,
        message_sid=message_sid,
        listing_id=listing_id,
        metadata=inbound_metadata,
    )

    brokerage_for_route = resolve_brokerage_by_inbound_number(to_number)
    if brokerage_for_route:
        with SessionLocal() as db:
            suppressed = is_buyer_suppressed(
                db=db,
                brokerage_id=brokerage_for_route.brokerage_id,
                buyer_phone=phone,
            )
            if suppressed and not is_opt_out_message(inbound.body):
                record_compliance_event(
                    db,
                    brokerage_id=brokerage_for_route.brokerage_id,
                    event_type="buyer_message_suppressed",
                    direction="inbound",
                    buyer_phone=phone,
                    listing_id=listing_id,
                    details={"message_preview": inbound.body[:200]},
                )
                logger.info(
                    "Suppressed inbound batch from %s on brokerage %s without model call",
                    phone,
                    brokerage_for_route.brokerage_id,
                )
                _mark_messages(ids, "done")
                return

        # ── Live takeover gate (DAL-158) ─────────────────────────────────────
        # While a conversation is agent_controlled the concierge never answers:
        # the batch (including anything caught in the debounce window when the
        # takeover fired) is forwarded raw to the agent, never bundled into an
        # AI escalation summary. Opt-out messages still flow to the engine so
        # the opt-out machinery runs as today.
        if not is_opt_out_message(inbound.body):
            from app.core.conversation_takeover import (
                find_agent_controlled_conversation,
                forward_buyer_message_during_takeover,
            )

            with SessionLocal() as db:
                takeover_conv = find_agent_controlled_conversation(
                    db,
                    brokerage_id=brokerage_for_route.brokerage_id,
                    buyer_phone=phone,
                    listing_id=listing_id,
                )
                if takeover_conv:
                    from app.models.db_models import DBBrokerage

                    brokerage = db.get(DBBrokerage, brokerage_for_route.brokerage_id)
                    forward_buyer_message_during_takeover(
                        db,
                        brokerage=brokerage,
                        conversation=takeover_conv,
                        body=inbound.body,
                        message_sid=message_sid,
                    )
                    _mark_messages(ids, "done")
                    logger.info(
                        "Takeover raw-forwarded %d message(s) from %s on conversation %s",
                        len(ids),
                        phone,
                        takeover_conv.conversation_id,
                    )
                    return

    try:
        # Run the synchronous chatbot engine in a thread pool
        # so it doesn't block the asyncio event loop
        loop = asyncio.get_event_loop()
        response_text, escalation, media_url = await loop.run_in_executor(
            None, chat_engine.handle_message_resilient, inbound
        )

        # Follow-up suppression: don't send a second consecutive assistant
        # message if no buyer reply has come in since the last one.
        from app.db.session import SessionLocal as _SL
        from app.db import crud as _crud

        suppress = False
        with _SL() as _db:
            conv = (
                _db.query(_crud.DBConversation)
                .filter_by(buyer_phone=phone)
                .order_by(_crud.DBConversation.updated_at.desc())
                .first()
            )
            if conv and _crud.has_consecutive_assistant_tail(_db, conv.conversation_id):
                suppress = True

        if suppress:
            logger.warning(
                f"Suppressed follow-up reply to {phone}: last two messages are both from assistant"
            )
        elif response_text and response_text.strip():
            send_whatsapp_reply(
                f"whatsapp:{phone}",
                response_text,
                media_url=media_url,
                from_number=brokerage_for_route.brokerage_ai_number if brokerage_for_route else None,
                brokerage_id=brokerage_for_route.brokerage_id if brokerage_for_route else None,
                listing_id=listing_id,
            )
        else:
            logger.info("No outbound buyer reply generated for %s", phone)

        if escalation:
            await notify_managing_agent(escalation)

        _mark_messages(ids, "done")
        logger.info(f"Processed {len(ids)} message(s) from {phone} as one batch")

        # DAL-162 catalog event #3: hot-buyer reply push (score ≥ hot band).
        if brokerage_for_route:
            _notify_hot_buyer_reply(
                brokerage_id=brokerage_for_route.brokerage_id,
                phone=phone,
                listing_id=listing_id,
                message_sid=message_sid,
            )

    except Exception as e:
        logger.error(f"Failed to process batch for {phone}: {e}", exc_info=True)
        _mark_messages(ids, "failed")


def _mark_messages(ids: list, status: str):
    with SessionLocal() as db:
        db.query(DBMessageQueue).filter(
            DBMessageQueue.id.in_(ids)
        ).update(
            {"status": status, "processed_at": datetime.utcnow()},
            synchronize_session=False,
        )
        safe_commit(db)


class UnprocessableMediaError(RuntimeError):
    """Inbound media the voice pipeline cannot process (DAL-159)."""


# Reuses the existing "high" band cutoff from hot-list scoring (priority high
# at score ≥ 70) per GOAL_SPEC_0610 open question #5.
HOT_BUYER_REPLY_SCORE_THRESHOLD = int(os.getenv("HOT_BUYER_REPLY_SCORE_THRESHOLD", "70"))


def _notify_hot_buyer_reply(
    *,
    brokerage_id: str,
    phone: str,
    listing_id: Optional[str],
    message_sid: str,
) -> None:
    """DAL-162 event #3: "your hot buyer just replied" — only above threshold."""
    try:
        from app.core.agent_notifications import notify_agent
        from app.models.db_models import (
            DBBrokerage,
            DBConversation,
            DBLeadAssignment,
        )

        with SessionLocal() as db:
            query = db.query(DBConversation).filter(
                DBConversation.brokerage_id == brokerage_id,
                DBConversation.buyer_phone == phone,
            )
            if listing_id:
                query = query.filter(DBConversation.listing_id == listing_id)
            conversation = query.order_by(DBConversation.updated_at.desc()).first()
            if not conversation or not conversation.assigned_agent_id:
                return
            assignment = (
                db.query(DBLeadAssignment)
                .filter(DBLeadAssignment.conversation_id == conversation.conversation_id)
                .first()
            )
            score = assignment.urgency_score if assignment else None
            if not score or score < HOT_BUYER_REPLY_SCORE_THRESHOLD:
                return
            brokerage = db.get(DBBrokerage, brokerage_id)
            if not brokerage:
                return
            buyer_label = conversation.buyer_name or phone
            notify_agent(
                db,
                brokerage=brokerage,
                agent_user_id=conversation.assigned_agent_id,
                event_type="hot_buyer_reply",
                body=f"Your hot buyer {buyer_label} just replied (score {score}).",
                dedupe_key=f"hot_buyer_reply:{message_sid}",
                conversation_id=conversation.conversation_id,
                listing_id=conversation.listing_id,
                deep_link_path=f"/agent/conversations/{conversation.conversation_id}",
            )
    except Exception:  # pragma: no cover — never break the message pipeline
        logger.warning("hot_buyer_reply notification failed", exc_info=True)


_ARABIC_RANGE = ("؀", "ۿ")


def _contains_arabic(text: str) -> bool:
    return any(_ARABIC_RANGE[0] <= char <= _ARABIC_RANGE[1] for char in text or "")


MEDIA_FALLBACK_EN = (
    "I couldn't process your voice message — could you type it instead, "
    "or your agent will follow up shortly."
)
MEDIA_FALLBACK_AR = (
    "لم أتمكن من معالجة رسالتك الصوتية — هل يمكنك كتابتها بدلاً من ذلك؟ "
    "أو سيتواصل معك الوسيط قريباً."
)


async def _handle_unprocessable_media(
    *,
    phone: str,
    to_number: str,
    listing_id: Optional[str],
    combined_body: str,
    error: str,
):
    """
    DAL-159 failure mode: one polite fallback to the buyer in conversation
    language + a media_unprocessable escalation so the failure is never silent.
    """
    from app.api.whatsapp import notify_managing_agent, send_whatsapp_reply
    from app.core.brokerage_resolver import resolve_brokerage_by_inbound_number
    from app.core.brokerage_access import record_compliance_event
    from app.db import crud
    from app.models.db_models import DBMessage
    from app.schemas.conversation import EscalationAlert

    brokerage = resolve_brokerage_by_inbound_number(to_number)
    brokerage_id = brokerage.brokerage_id if brokerage else None

    conversation = None
    with SessionLocal() as db:
        if listing_id:
            conversation = crud.get_or_create_conversation(db, phone, listing_id)
        else:
            from app.models.db_models import DBConversation
            query = db.query(DBConversation).filter(DBConversation.buyer_phone == phone)
            if brokerage_id:
                query = query.filter(DBConversation.brokerage_id == brokerage_id)
            conversation = query.order_by(DBConversation.updated_at.desc()).first()

        conversation_id = conversation.conversation_id if conversation else None
        resolved_listing_id = conversation.listing_id if conversation else listing_id
        buyer_name = conversation.buyer_name if conversation else None

        # Language heuristic: Arabic if the buyer's surrounding text (or recent
        # messages) contain Arabic script, else English.
        arabic = _contains_arabic(combined_body)
        if not arabic and conversation_id:
            recent = (
                db.query(DBMessage)
                .filter(
                    DBMessage.conversation_id == conversation_id,
                    DBMessage.role == "user",
                )
                .order_by(DBMessage.timestamp.desc())
                .limit(5)
                .all()
            )
            arabic = any(_contains_arabic(message.content) for message in recent)

        if conversation_id:
            db.add(DBMessage(
                conversation_id=conversation_id,
                role="user",
                content=combined_body or "[Voice/video message — could not process]",
                intent="media_unprocessable",
                metadata_json={"media_unprocessable": {"error": error}},
            ))
            conversation.updated_at = datetime.utcnow()

        if brokerage_id:
            record_compliance_event(
                db,
                brokerage_id=brokerage_id,
                conversation_id=conversation_id,
                listing_id=resolved_listing_id,
                buyer_phone=phone,
                event_type="buyer_media_unprocessable",
                direction="inbound",
                details={"error": error, "had_text": bool(combined_body.strip())},
            )
        safe_commit(db)

    fallback = MEDIA_FALLBACK_AR if arabic else MEDIA_FALLBACK_EN
    send_whatsapp_reply(
        f"whatsapp:{phone}",
        fallback,
        from_number=brokerage.brokerage_ai_number if brokerage else None,
        brokerage_id=brokerage_id,
        conversation_id=conversation_id,
        listing_id=resolved_listing_id,
    )

    if conversation_id and resolved_listing_id:
        alert = EscalationAlert(
            escalation_type="media_unprocessable",
            conversation_id=conversation_id,
            listing_id=resolved_listing_id,
            buyer_phone=phone,
            buyer_name=buyer_name,
            trigger_message=(
                "Buyer sent a voice/video message Dalya couldn't process. "
                "They've been asked to type it — please follow up."
            ),
            priority="high",
            payload={"error": error, "buyer_text": combined_body[:200]},
        )
        await notify_managing_agent(alert)

        # DAL-162 catalog event #10 (ai_failure) — the escalation envelope above
        # is the push; record the framework row for audit + dedupe.
        try:
            from app.core.agent_notifications import notify_agent

            with SessionLocal() as db:
                from app.models.db_models import DBBrokerage as _DBBrokerage
                from app.models.db_models import DBConversation as _DBConversation

                conv = db.get(_DBConversation, conversation_id)
                brokerage_row = db.get(_DBBrokerage, brokerage_id) if brokerage_id else None
                if conv and conv.assigned_agent_id and brokerage_row:
                    notify_agent(
                        db,
                        brokerage=brokerage_row,
                        agent_user_id=conv.assigned_agent_id,
                        event_type="ai_failure",
                        body=f"Voice/video from {buyer_name or phone} couldn't be processed",
                        dedupe_key=f"ai_failure:media_unprocessable:{conversation_id}:{error[:40]}",
                        conversation_id=conversation_id,
                        listing_id=resolved_listing_id,
                        deep_link_path=f"/agent/conversations/{conversation_id}",
                        record_only=True,
                    )
        except Exception:  # pragma: no cover
            logger.warning("ai_failure notification record failed", exc_info=True)
    else:
        logger.warning(
            "media_unprocessable for %s had no resolvable conversation/listing — "
            "fallback sent, compliance event recorded, no escalation thread",
            phone,
        )


async def _prepare_voice_inbound(
    *,
    combined_body: str,
    listing_id: Optional[str],
    media_urls: list,
    media_content_types: list,
    metadata_items: list,
) -> tuple[str, dict]:
    from app.core.transcription.models import TranscriptionContext
    from app.core.voice_notes import (
        download_media_to_tempfile,
        transcribe_audio_file,
        transcription_result_metadata,
    )
    from app.db.session import SessionLocal as _SL
    from app.models.db_models import DBListing

    audio_path = None
    audio_url = None
    content_type = None
    for item in metadata_items:
        if item.get("audio_path"):
            audio_path = item["audio_path"]
            content_type = item.get("content_type")
            audio_url = item.get("audio_url")
            break

    if audio_path is None and media_urls:
        audio_url = str(media_urls[0])
        content_type = str(media_content_types[0]) if media_content_types else None
        import os
        auth = None
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        if sid and token:
            auth = (sid, token)
        audio_path = await download_media_to_tempfile(
            audio_url,
            content_type=content_type,
            auth=auth,
        )

    if audio_path is None:
        return combined_body, {}

    asking_price = None
    if listing_id:
        with _SL() as db:
            listing = db.get(DBListing, listing_id)
            if listing:
                spa = listing.spa_data or {}
                asking_price = listing.seller_asking_price or spa.get("purchase_price_aed")

    result = transcribe_audio_file(
        audio_path,
        content_type=content_type,
        audio_type="buyer_voice",
        context=TranscriptionContext(
            listing_id=listing_id,
            asking_price_aed=asking_price,
        ),
    )
    metadata = transcription_result_metadata(
        result,
        direction="buyer_to_property_advisor",
        audio_url=audio_url,
    )
    body = result.corrected_transcript.strip() or result.raw_transcript.strip() or combined_body
    if combined_body.strip():
        body = f"{combined_body.strip()}\n{body}"
    return body, metadata
