"""
Abstract MessagingTransport.

All routing/relay code reaches the wire through `get_transport()`. Concrete
implementations (Twilio, 360dialog, simulated) live alongside this file.
"""

from __future__ import annotations

import re
import secrets
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from app.core.runtime_config import is_live_environment

from app.core.messaging.types import (
    InboundEnvelope,
    OutboundAgentMessage,
    OutboundBuyerMessage,
    SendResult,
)


# Pattern used to embed and parse the envelope reference tag inside a WhatsApp
# message body. Kept short and unambiguous so managing agents can quote-reply
# without losing context.
ENVELOPE_TAG_PATTERN = re.compile(r"\[Ref:\s*([A-Za-z0-9]{6,16})\]")


def mint_envelope_token() -> str:
    """Generate a fresh envelope token used to tag agent-facing alerts."""
    return secrets.token_urlsafe(8).replace("_", "").replace("-", "")[:10].upper()


def stamp_envelope_token(body: str, token: str) -> str:
    """Append the envelope reference tag to a message body so an agent's quoted reply carries it back."""
    suffix = f"\n\n[Ref: {token}]"
    if body.endswith(suffix.strip()):
        return body
    return f"{body.rstrip()}\n\n[Ref: {token}]"


def parse_envelope_token(body: str) -> Optional[str]:
    """Extract the envelope token from an inbound body, if present."""
    if not body:
        return None
    match = ENVELOPE_TAG_PATTERN.search(body)
    return match.group(1) if match else None


# Per-transport media size limits (DAL-160). Encoded in the transport layer,
# not the UI — Twilio WhatsApp caps media at 16 MB; images are capped lower
# because several BSPs (incl. the 360dialog production path) enforce 5 MB.
DEFAULT_MEDIA_LIMIT_BYTES = 16 * 1024 * 1024
IMAGE_MEDIA_LIMIT_BYTES = 5 * 1024 * 1024


class MessagingTransport(ABC):
    """
    Wire-protocol-agnostic interface used by escalation routing and relay
    logic. Implementations: Twilio (live), 360dialog (stub), simulated (tests).
    """

    name: str = "abstract"

    def media_limit_bytes(self, mime_type: str) -> int:
        """Max outbound media size for this transport by MIME type (DAL-160)."""
        if (mime_type or "").lower().startswith("image/"):
            return IMAGE_MEDIA_LIMIT_BYTES
        return DEFAULT_MEDIA_LIMIT_BYTES

    @abstractmethod
    def send_to_buyer(self, msg: OutboundBuyerMessage) -> SendResult:
        """Send a message from the brokerage's Brokerage AI to a buyer."""

    @abstractmethod
    def send_to_agents_ai(self, msg: OutboundAgentMessage) -> SendResult:
        """
        Send an escalation alert to the brokerage's Agents AI number,
        addressed to a specific managing agent. The transport stamps an
        envelope token into the body (and into the SendResult) so the caller
        can persist a DBAgentMessageRoute keyed on it.
        """

    @abstractmethod
    def parse_inbound(self, form_data: dict) -> InboundEnvelope:
        """Translate a raw webhook payload into a normalized InboundEnvelope."""

    def verify_signature(self, request) -> bool:  # pragma: no cover — default permissive
        """Default permissive outside live-class environments; live transports must override."""
        return not is_live_environment()


def now() -> datetime:
    """Helper, kept here so concrete transports can stub it in tests."""
    return datetime.utcnow()
