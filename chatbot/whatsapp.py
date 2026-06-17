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

import os
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse
from twilio.rest import Client as TwilioClient
from twilio.request_validator import RequestValidator

from app.core.chatbot_engine import engine
from app.schemas.conversation import InboundMessage, EscalationAlert

router = APIRouter()

# ── Twilio config ──────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None


# ── Listing ID extraction ──────────────────────────────────────────────────────

def extract_listing_id(body: str) -> str | None:
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

async def notify_eric(alert: EscalationAlert):
    """
    Send escalation alert to Eric.
    Currently logs to console — wire to Telegram/SMS in phase 2.

    Phase 2: POST to Telegram Bot API
    POST https://api.telegram.org/bot{TOKEN}/sendMessage
    """
    message = f"""
🔔 DALYA LEAD ALERT

Property: {alert.listing_id}
Buyer: {alert.buyer_name or 'Unknown'} ({alert.buyer_phone})
Trigger: {alert.trigger.value.replace('_', ' ').title()}

Their message: "{alert.trigger_message}"

Summary: {alert.conversation_summary}

Suggested reply:
"{alert.suggested_response}"

Conversation ID: {alert.conversation_id}
""".strip()

    # TODO phase 2: send via Telegram Bot API
    # For now, print to console and log
    print("\n" + "="*50)
    print(message)
    print("="*50 + "\n")

    # Phase 2 implementation:
    # telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    # telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    # if telegram_token and telegram_chat_id:
    #     import httpx
    #     async with httpx.AsyncClient() as client:
    #         await client.post(
    #             f"https://api.telegram.org/bot{telegram_token}/sendMessage",
    #             json={"chat_id": telegram_chat_id, "text": message}
    #         )


def send_whatsapp_reply(to_number: str, body: str):
    """Send WhatsApp message via Twilio."""
    if not twilio_client:
        print(f"[MOCK SEND] To: {to_number}\n{body}\n")
        return

    # Ensure number has whatsapp: prefix
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"

    twilio_client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        to=to_number,
        body=body,
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
    # Validate request is actually from Twilio (security)
    # Uncomment in production:
    # validator = RequestValidator(TWILIO_AUTH_TOKEN)
    # url = str(request.url)
    # signature = request.headers.get("X-Twilio-Signature", "")
    # form_data = dict(await request.form())
    # if not validator.validate(url, form_data, signature):
    #     raise HTTPException(status_code=403, detail="Invalid Twilio signature")

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

    # Process through chatbot engine
    response_text, escalation = engine.handle_message(inbound)

    # Send reply back to buyer
    send_whatsapp_reply(From, response_text)

    # Fire escalation alert if triggered
    if escalation:
        await notify_eric(escalation)

    # Return empty TwiML — response already sent via API
    return PlainTextResponse(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
    )


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
    inbound = InboundMessage(
        from_number=buyer_phone,
        to_number=TWILIO_WHATSAPP_NUMBER,
        body=message,
        message_sid=f"TEST_{listing_id}",
        listing_id=listing_id,
    )

    response_text, escalation = engine.handle_message(inbound)

    return {
        "buyer_message": message,
        "bot_response": response_text,
        "escalation_triggered": escalation is not None,
        "escalation": escalation.model_dump() if escalation else None,
    }


# ── Listing management endpoints ───────────────────────────────────────────────

@router.post("/listings/{listing_id}/activate")
async def activate_listing_chatbot(
    listing_id: str,
    seller_asking_price: float | None = None,
    seller_notes: str | None = None,
):
    """
    Activate the chatbot for a listing that's already been parsed.
    Call this after /parse-spa to make the listing live.
    """
    from app.core.spa_parser import SPAParser
    # In phase 2 this loads from DB — for now check in-memory store
    from app.core.chatbot_engine import _listings
    if listing_id not in _listings:
        raise HTTPException(
            status_code=404,
            detail="Listing not found. Parse the SPA first via /api/v1/parse-spa"
        )

    spa = _listings[listing_id]
    engine.register_listing(
        listing_id=listing_id,
        spa=spa,
        seller_asking_price=seller_asking_price,
        seller_notes=seller_notes,
    )

    # Generate the WhatsApp deep link for portals
    dalya_number = os.getenv("DALYA_PHONE_NUMBER", "+971500000000")
    wa_link = generate_whatsapp_link(dalya_number, listing_id, spa.project)

    return {
        "success": True,
        "listing_id": listing_id,
        "property": spa.project,
        "unit": spa.unit_number,
        "whatsapp_link": wa_link,
        "message": "Chatbot is live. Use the whatsapp_link in your portal listings.",
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
