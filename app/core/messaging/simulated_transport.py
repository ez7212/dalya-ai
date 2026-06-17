"""
In-memory MessagingTransport used by the simulation script and tests.

Captures every outbound message in `outbox` for assertion. Lets the caller
inject inbound messages (buyer or agent-reply) for end-to-end simulation
without touching live WhatsApp.
"""

from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

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


@dataclass
class SimulatedSend:
    direction: str               # "to_buyer" | "to_agents_ai"
    from_number: str
    to_number: str
    body: str
    conversation_id: Optional[str] = None
    listing_id: Optional[str] = None
    media_url: Optional[str] = None
    envelope_token: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    escalation_type: Optional[str] = None


class SimulatedTransport(MessagingTransport):
    name = "simulated"

    def __init__(self):
        self.outbox: list[SimulatedSend] = []
        self.inbox: deque[InboundEnvelope] = deque()
        self._lock = threading.Lock()
        # Token → last-known agent address bookkeeping for assertion convenience.
        self.token_to_agent_phone: dict[str, str] = {}

    # ── Sends ────────────────────────────────────────────────────────────────

    def send_to_buyer(self, msg: OutboundBuyerMessage) -> SendResult:
        with self._lock:
            self.outbox.append(
                SimulatedSend(
                    direction="to_buyer",
                    from_number=msg.brokerage_ai_number,
                    to_number=msg.buyer_phone,
                    body=msg.body,
                    conversation_id=msg.conversation_id,
                    listing_id=msg.listing_id,
                    media_url=msg.media_url,
                )
            )
        return SendResult(ok=True, transport_message_id=f"sim-{uuid.uuid4().hex[:8]}")

    def send_to_agents_ai(self, msg: OutboundAgentMessage) -> SendResult:
        token = msg.envelope_token or mint_envelope_token()
        stamped = stamp_envelope_token(msg.body, token)
        with self._lock:
            self.outbox.append(
                SimulatedSend(
                    direction="to_agents_ai",
                    from_number=msg.agents_ai_number,
                    to_number=msg.agent_phone,
                    body=stamped,
                    conversation_id=msg.conversation_id,
                    listing_id=msg.listing_id,
                    envelope_token=token,
                    tags=list(msg.tags),
                    escalation_type=msg.escalation_type,
                )
            )
            self.token_to_agent_phone[token] = msg.agent_phone
        return SendResult(
            ok=True,
            transport_message_id=f"sim-agent-{uuid.uuid4().hex[:8]}",
            envelope_token=token,
        )

    # ── Inbound injection ────────────────────────────────────────────────────

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
            from_number=form_data.get("From") or "",
            to_number=form_data.get("To") or "",
            body=body,
            message_sid=form_data.get("MessageSid") or f"sim-msg-{uuid.uuid4().hex[:8]}",
            raw=dict(form_data),
            media_urls=[url for url, _ in media],
            media_content_types=[content_type for _, content_type in media],
            envelope_token=parse_envelope_token(body),
        )

    def inject_buyer_message(
        self,
        from_buyer: str,
        to_brokerage_ai_number: str,
        body: str,
        message_sid: Optional[str] = None,
    ) -> InboundEnvelope:
        return self.parse_inbound(
            {
                "From": from_buyer,
                "To": to_brokerage_ai_number,
                "Body": body,
                "MessageSid": message_sid or f"sim-buyer-{uuid.uuid4().hex[:8]}",
            }
        )

    def inject_buyer_voice_note(
        self,
        from_buyer: str,
        to_brokerage_ai_number: str,
        audio_path: str,
        body: str = "",
        content_type: str = "audio/ogg",
        message_sid: Optional[str] = None,
    ) -> InboundEnvelope:
        return self.parse_inbound(
            {
                "From": from_buyer,
                "To": to_brokerage_ai_number,
                "Body": body,
                "MessageSid": message_sid or f"sim-buyer-voice-{uuid.uuid4().hex[:8]}",
                "NumMedia": "1",
                "MediaUrl0": audio_path,
                "MediaContentType0": content_type,
                "AudioPath": audio_path,
            }
        )

    def inject_agent_voice_reply(
        self,
        envelope_token: str,
        audio_url: str,
        agents_ai_number: str,
        agent_phone: Optional[str] = None,
        transcript_hint: str = "",
    ) -> InboundEnvelope:
        agent_phone = agent_phone or self.token_to_agent_phone.get(envelope_token) or "+971500000000"
        return self.parse_inbound(
            {
                "From": agent_phone,
                "To": agents_ai_number,
                "Body": stamp_envelope_token(transcript_hint, envelope_token),
                "MessageSid": f"sim-agent-voice-{uuid.uuid4().hex[:8]}",
                "NumMedia": "1",
                "MediaUrl0": audio_url,
                "MediaContentType0": "audio/ogg",
            }
        )

    def inject_agent_reply(
        self,
        envelope_token: str,
        body_without_token: str,
        agents_ai_number: str,
        agent_phone: Optional[str] = None,
    ) -> InboundEnvelope:
        """
        Simulate the managing agent replying on the Agents AI thread.
        The body is sent with the envelope token preserved (mimicking the
        agent's quoted reply or replying to the threaded message), so the
        webhook can look up DBAgentMessageRoute and relay correctly.
        """
        agent_phone = agent_phone or self.token_to_agent_phone.get(envelope_token) or "+971500000000"
        body_with_token = stamp_envelope_token(body_without_token, envelope_token)
        return self.parse_inbound(
            {
                "From": agent_phone,
                "To": agents_ai_number,
                "Body": body_with_token,
                "MessageSid": f"sim-agent-reply-{uuid.uuid4().hex[:8]}",
            }
        )

    # ── Assertion helpers ────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self.outbox.clear()
            self.inbox.clear()
            self.token_to_agent_phone.clear()

    def messages_to_buyer(self, buyer_phone: Optional[str] = None) -> list[SimulatedSend]:
        return [
            m for m in self.outbox
            if m.direction == "to_buyer" and (buyer_phone is None or m.to_number == buyer_phone)
        ]

    def messages_to_agents_ai(self) -> list[SimulatedSend]:
        return [m for m in self.outbox if m.direction == "to_agents_ai"]
