"""
360dialog WhatsApp Business API transport — STUB.

This transport is intentionally unimplemented. Live 360dialog wiring is
deferred until WABA approval lands. The transport is included so the rest
of the system can be wired to the interface today; the env-driven factory
returns this stub when MESSAGING_TRANSPORT=dialog360, and any attempt to
send through it raises NotImplementedError with a clear message.

Required env vars when implemented:
- D360_API_KEY
- D360_PARTNER_ID (optional, for hub-managed numbers)
- D360_BASE_URL (default https://waba.360dialog.io)
- D360_WEBHOOK_SECRET (HMAC for inbound signature verification)
"""

from __future__ import annotations

from app.core.messaging.transport import MessagingTransport
from app.core.messaging.types import (
    InboundEnvelope,
    OutboundAgentMessage,
    OutboundBuyerMessage,
    SendResult,
)


_NOT_READY = (
    "360dialog transport pending WABA approval. "
    "Swap MESSAGING_TRANSPORT to 'twilio' (live) or 'simulated' (tests) for now."
)


class Dialog360Transport(MessagingTransport):
    name = "dialog360"

    def send_to_buyer(self, msg: OutboundBuyerMessage) -> SendResult:  # pragma: no cover
        raise NotImplementedError(_NOT_READY)

    def send_to_agents_ai(self, msg: OutboundAgentMessage) -> SendResult:  # pragma: no cover
        raise NotImplementedError(_NOT_READY)

    def parse_inbound(self, form_data: dict) -> InboundEnvelope:  # pragma: no cover
        raise NotImplementedError(_NOT_READY)
