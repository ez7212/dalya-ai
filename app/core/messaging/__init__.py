"""
Messaging-transport interface for Dalya.

All buyer-facing and agent-facing message sends route through a
MessagingTransport implementation. The interface insulates business logic
(escalation routing, agent reply relay, deterministic templates) from the
underlying wire protocol so that swapping Twilio for 360dialog later is a
provider-swap, not a logic change.

See `transport.py` for the abstract base class.
See `factory.py` for env-driven selection.
"""

from app.core.messaging.factory import get_transport, set_transport_override
from app.core.messaging.transport import MessagingTransport, SendResult
from app.core.messaging.types import (
    EscalationTag,
    InboundEnvelope,
    OutboundAgentMessage,
    OutboundBuyerMessage,
)

__all__ = [
    "EscalationTag",
    "InboundEnvelope",
    "MessagingTransport",
    "OutboundAgentMessage",
    "OutboundBuyerMessage",
    "SendResult",
    "get_transport",
    "set_transport_override",
]
