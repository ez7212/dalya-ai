"""
Transport-agnostic message envelopes and tags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EscalationTag(str, Enum):
    """
    Tags attached to an escalation envelope so the receiving managing agent
    knows what kind of event triggered the alert. Multiple tags can apply
    to a single envelope (e.g. near_threshold + at_or_above).
    """

    NEAR_THRESHOLD = "near_threshold"      # offer within 5% below threshold; buyer sees graceful pushback
    MARGINAL = "marginal"                  # legacy inner-band marker (kept for migration continuity)
    AT_OR_ABOVE = "at_or_above"            # offer at or above notification threshold
    REGULATORY = "regulatory"              # PDPL / GDPR / regulatory request
    CONVEYANCING_VERIFIED = "conveyancing_verified"
    LOW_CONFIDENCE = "low_confidence"      # bot cannot answer
    HUMAN_REQUEST = "human_request"        # buyer asked to speak with a human
    FORM_A = "form_a"
    BRN_REQUEST = "brn_request"
    SOFT_OFFER = "soft_offer"
    RETURNING_BUYER = "returning_buyer"
    GENERAL_LEAD_CAPTURE = "general_lead_capture"


@dataclass
class OutboundBuyerMessage:
    """An outbound message from the brokerage's Brokerage AI to the buyer."""

    brokerage_id: str
    brokerage_ai_number: str        # FROM number — the brokerage's buyer-facing WhatsApp
    buyer_phone: str                # TO number
    body: str
    conversation_id: Optional[str] = None
    listing_id: Optional[str] = None
    media_url: Optional[str] = None


@dataclass
class OutboundAgentMessage:
    """
    An outbound escalation envelope from the brokerage's Agents AI to a
    specific managing agent.

    The transport stamps `envelope_token` into the rendered body so that the
    agent's reply (quoted/threaded on WhatsApp) carries the token back to the
    inbound webhook, which looks it up in DBAgentMessageRoute and relays the
    body to the original buyer.
    """

    brokerage_id: str
    agents_ai_number: str           # FROM number — the brokerage's Agents AI WhatsApp
    agent_phone: str                # TO number — the managing agent's registered WhatsApp
    body: str
    conversation_id: str
    listing_id: str
    buyer_phone: str
    escalation_type: str
    tags: list[str] = field(default_factory=list)
    envelope_token: Optional[str] = None  # populated by the transport when send_to_agents_ai mints one
    agent_user_id: Optional[str] = None


@dataclass
class InboundEnvelope:
    """
    Normalized representation of an inbound webhook event, regardless of
    transport. The webhook delegates to `transport.parse_inbound(form_data)`
    which returns one of these.
    """

    transport: str                  # "twilio" | "dialog360" | "simulated"
    from_number: str                # buyer phone or managing-agent phone (without `whatsapp:` prefix)
    to_number: str                  # the brokerage's Brokerage AI OR Agents AI number
    body: str
    message_sid: str
    raw: dict[str, Any] = field(default_factory=dict)
    media_urls: list[str] = field(default_factory=list)
    media_content_types: list[str] = field(default_factory=list)  # parallel to media_urls
    envelope_token: Optional[str] = None  # parsed out of body if present, for agent reply routing


@dataclass
class SendResult:
    """The outcome of a transport `send_*` call."""

    ok: bool
    transport_message_id: Optional[str] = None
    error: Optional[str] = None
    envelope_token: Optional[str] = None
