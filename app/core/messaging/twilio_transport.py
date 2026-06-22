"""
Twilio implementation of MessagingTransport.

Wraps `twilio.rest.Client.messages.create` so that all wire calls flow through
the abstract interface. The legacy Mahoroba flow continues to work because
this transport stays the default until 360dialog WABA approval lands.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from twilio.rest import Client as TwilioClient
from twilio.request_validator import RequestValidator

from app.core.pii_redaction import redact_pii, redacted_preview
from app.core.runtime_config import is_live_environment

from app.core.messaging.transport import (
    MessagingTransport,
    mint_envelope_token,
    parse_envelope_token,
    stamp_envelope_token,
)
from app.core.messaging.types import (
    InboundEnvelope,
    OutboundAgentMessage,
    OutboundBuyerMessage,
    SendResult,
)

logger = logging.getLogger(__name__)


def _whatsapp(number: str) -> str:
    if not number:
        return number
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


def _strip_whatsapp(number: str) -> str:
    if not number:
        return number
    return number[len("whatsapp:"):] if number.startswith("whatsapp:") else number


class TwilioTransport(MessagingTransport):
    name = "twilio"

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
    ):
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN", "")
        if is_live_environment() and (not self.account_sid or not self.auth_token):
            raise RuntimeError("Twilio transport requires TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in live-class environments")
        self._client: Optional[TwilioClient] = (
            TwilioClient(self.account_sid, self.auth_token) if self.account_sid else None
        )

    def _send(self, from_number: str, to_number: str, body: str, media_url: Optional[str] = None) -> SendResult:
        if not self._client:
            logger.info(
                "[MOCK SEND] from=%s to=%s body=%s",
                redact_pii(from_number),
                redact_pii(to_number),
                redacted_preview(body),
            )
            return SendResult(ok=True, transport_message_id=None)
        kwargs = dict(from_=_whatsapp(from_number), to=_whatsapp(to_number), body=body)
        if media_url:
            kwargs["media_url"] = [media_url]
        try:
            message = self._client.messages.create(**kwargs)
            return SendResult(ok=True, transport_message_id=message.sid)
        except Exception as exc:
            logger.error("Twilio send failed: %s", exc)
            return SendResult(ok=False, error=str(exc))

    def send_to_buyer(self, msg: OutboundBuyerMessage) -> SendResult:
        return self._send(
            from_number=msg.brokerage_ai_number,
            to_number=msg.buyer_phone,
            body=msg.body,
            media_url=msg.media_url,
        )

    def send_to_agents_ai(self, msg: OutboundAgentMessage) -> SendResult:
        token = msg.envelope_token or mint_envelope_token()
        stamped_body = stamp_envelope_token(msg.body, token)
        result = self._send(
            from_number=msg.agents_ai_number,
            to_number=msg.agent_phone,
            body=stamped_body,
        )
        result.envelope_token = token
        return result

    def parse_inbound(self, form_data: dict) -> InboundEnvelope:
        body = form_data.get("Body") or ""
        num_media = int(form_data.get("NumMedia") or "0")
        media = [
            (
                form_data.get(f"MediaUrl{i}") or "",
                form_data.get(f"MediaContentType{i}") or "",
            )
            for i in range(num_media)
        ]
        media = [(url, content_type) for url, content_type in media if url]
        return InboundEnvelope(
            transport=self.name,
            from_number=_strip_whatsapp(form_data.get("From") or ""),
            to_number=_strip_whatsapp(form_data.get("To") or ""),
            body=body,
            message_sid=form_data.get("MessageSid") or "",
            raw=dict(form_data),
            media_urls=[url for url, _ in media],
            media_content_types=[content_type for _, content_type in media],
            envelope_token=parse_envelope_token(body),
        )

    def verify_signature(self, request) -> bool:
        if not self.auth_token:
            return not is_live_environment()
        validator = RequestValidator(self.auth_token)
        public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
        webhook_url = f"{public_url}/api/v1/whatsapp/webhook"
        signature = request.headers.get("X-Twilio-Signature", "")
        if not public_url:
            return not is_live_environment()
        try:
            form_data = request._form_data_cache  # type: ignore[attr-defined]
        except AttributeError:
            return not is_live_environment()
        return validator.validate(webhook_url, form_data, signature)
