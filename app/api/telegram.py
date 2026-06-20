"""
Telegram Webhook Router

When Eric replies to a Dalya alert on Telegram:
1. Message is sent immediately to the buyer on WhatsApp
2. Dalya confirms back: "✅ Sent to [name] ([phone]): '[preview]'"
   so Eric can verify it went to the right person

Any message that is NOT a reply to an alert is ignored with a reminder.
"""

import os
import logging
from fastapi import APIRouter, Request
from app.db.session import safe_commit, service_session, set_service_db_session_context

router = APIRouter()
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()

    message = update.get("message")
    if not message:
        return {"ok": True}

    # Only process messages from Eric's chat
    chat_id = str(message.get("chat", {}).get("id", ""))
    if chat_id != TELEGRAM_CHAT_ID:
        return {"ok": True}

    text = message.get("text", "").strip()
    reply_to = message.get("reply_to_message")

    if not text:
        return {"ok": True}

    # Must be a reply to one of our alert messages
    if not reply_to:
        await _send_message(
            "👋 To reply to a buyer, reply directly to one of the Dalya alert messages above.\n"
            "Do not send a new message here — it won't be routed to anyone."
        )
        return {"ok": True}

    original_message_id = reply_to.get("message_id")

    from app.models.db_models import DBTelegramReplyRoute

    with service_session() as db:
        route = (
            db.query(DBTelegramReplyRoute)
            .filter_by(telegram_message_id=original_message_id)
            .first()
        )

    if not route:
        await _send_message(
            "⚠️ Couldn't find the original alert for this message.\n"
            "Only reply directly to Dalya alert messages to reach buyers."
        )
        return {"ok": True}

    # Send to buyer
    from app.api.whatsapp import send_whatsapp_reply
    try:
        send_whatsapp_reply(f"whatsapp:{route.buyer_phone}", text)

        buyer_display = f"{route.buyer_name} ({route.buyer_phone})" if route.buyer_name else route.buyer_phone
        preview = text if len(text) <= 120 else text[:120] + "..."
        await _send_message(f"✅ Sent to {buyer_display}:\n\"{preview}\"")

        logger.info(f"Reply forwarded to {route.buyer_phone}: {text[:50]}")

        # If this was a questions alert, save Eric's answer as Q&A on the listing
        # so Dalya can answer the same question for future buyers
        if route.alert_questions and route.listing_id:
            _save_qa_to_listing(route.listing_id, route.alert_questions, text)

    except Exception as e:
        await _send_message(f"❌ Failed to send to buyer: {e}")
        logger.error(f"Failed to forward reply to {route.buyer_phone}: {e}")

    return {"ok": True}


async def _send_message(text: str) -> int:
    """Send a message to Eric and return the Telegram message_id."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
                timeout=5,
            )
            return resp.json().get("result", {}).get("message_id", 0)
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return 0


def _save_qa_to_listing(listing_id: str, questions: str, answer: str) -> None:
    """
    Append a Q&A pair to the listing's seller_qa store.
    Called after Eric replies to a questions alert on Telegram.
    Future buyers asking the same question will get this answer from Dalya directly.
    """
    from app.models.db_models import DBListing
    try:
        with service_session() as db:
            listing = db.get(DBListing, listing_id)
            if listing and listing.brokerage_id:
                set_service_db_session_context(db, brokerage_id=listing.brokerage_id)
            if listing:
                qa = list(listing.seller_qa or [])
                qa.append({"question": questions, "answer": answer})
                listing.seller_qa = qa
                safe_commit(db)
                logger.info(f"Saved Q&A to listing {listing_id}: {questions[:60]}")
    except Exception as e:
        logger.error(f"Failed to save Q&A to listing {listing_id}: {e}")


async def register_telegram_webhook(public_url: str):
    """Register the Telegram webhook. Called at server startup."""
    import httpx
    webhook_url = f"{public_url.rstrip('/')}/api/v1/telegram/webhook"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
                json={"url": webhook_url},
                timeout=10,
            )
            data = resp.json()
            if data.get("ok"):
                logger.info(f"Telegram webhook registered: {webhook_url}")
            else:
                logger.warning(f"Telegram webhook registration failed: {data}")
    except Exception as e:
        logger.warning(f"Could not register Telegram webhook: {e}")
