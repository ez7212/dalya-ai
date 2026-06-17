"""
Chatbot Engine
The core AI conversation handler for Dalya listings.

Flow:
1. Receive buyer message
2. Load/create conversation state
3. Detect intent (escalation trigger check)
4. Build context (system prompt + conversation history)
5. Call Claude for response
6. Update conversation state
7. Fire escalation alert if triggered
8. Return response

Storage: In-memory for MVP (dict keyed by conversation_id)
Phase 2: Replace with PostgreSQL via SQLAlchemy
"""

import anthropic
import json
import re
import uuid
from datetime import datetime
from typing import Optional

from app.schemas.spa import SPAParseResult
from app.schemas.conversation import (
    ConversationState,
    ConversationMessage,
    MessageRole,
    BuyerIntent,
    EscalationAlert,
    InboundMessage,
)
from app.core.prompt_builder import build_system_prompt, build_intent_detection_prompt


# ── In-memory stores (replace with DB in phase 2) ─────────────────────────────
# conversation_id → ConversationState
_conversations: dict[str, ConversationState] = {}

# listing_id → SPAParseResult
_listings: dict[str, SPAParseResult] = {}

# listing_id → community data dict
_community_data: dict[str, dict] = {}

# buyer_phone → conversation_id (for routing inbound messages)
_phone_to_conversation: dict[str, str] = {}


# ── Escalation triggers ────────────────────────────────────────────────────────
ESCALATION_INTENTS = {
    BuyerIntent.offer_submission,
    BuyerIntent.viewing_request,
    BuyerIntent.contact_sharing,
}


class ChatbotEngine:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = "claude-sonnet-4-20250514"

    # ── Listing registration ───────────────────────────────────────────────────

    def register_listing(
        self,
        listing_id: str,
        spa: SPAParseResult,
        community_data: Optional[dict] = None,
        seller_asking_price: Optional[float] = None,
        seller_notes: Optional[str] = None,
    ) -> str:
        """
        Register a parsed listing so the chatbot can serve it.
        Returns the listing_id.
        """
        _listings[listing_id] = spa
        if community_data:
            _community_data[listing_id] = community_data
        return listing_id

    def get_or_create_conversation(
        self,
        buyer_phone: str,
        listing_id: str,
    ) -> ConversationState:
        """
        Get existing conversation for this buyer+listing, or create a new one.
        A buyer can have different conversations for different listings.
        """
        # Key is phone + listing — one conversation per buyer per listing
        key = f"{buyer_phone}:{listing_id}"

        if key in _phone_to_conversation:
            conv_id = _phone_to_conversation[key]
            if conv_id in _conversations:
                return _conversations[conv_id]

        # Create new conversation
        conv_id = str(uuid.uuid4())
        state = ConversationState(
            conversation_id=conv_id,
            listing_id=listing_id,
            buyer_phone=buyer_phone,
        )
        _conversations[conv_id] = state
        _phone_to_conversation[key] = conv_id
        return state

    # ── Intent detection ───────────────────────────────────────────────────────

    def detect_intent(self, message: str) -> dict:
        """
        Classify buyer message intent using Claude.
        Returns structured intent data.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": build_intent_detection_prompt(message),
                }],
            )
            raw = response.content[0].text.strip()
            json_text = re.sub(r"^```(?:json)?\n?", "", raw)
            json_text = re.sub(r"\n?```$", "", json_text)
            return json.loads(json_text)
        except Exception:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "should_escalate": False,
                "extracted_name": None,
                "extracted_budget": None,
                "escalation_reason": None,
            }

    # ── Main conversation handler ──────────────────────────────────────────────

    def handle_message(
        self,
        inbound: InboundMessage,
        seller_asking_price: Optional[float] = None,
        seller_notes: Optional[str] = None,
    ) -> tuple[str, Optional[EscalationAlert]]:
        """
        Main entry point. Process an inbound buyer message.

        Returns:
            tuple of (response_text, escalation_alert_or_None)
        """
        listing_id = inbound.listing_id

        # Load listing
        spa = _listings.get(listing_id)
        if not spa:
            return (
                "Hi! I'm the Dalya AI assistant. Could you let me know which "
                "property you're enquiring about so I can help you properly?",
                None,
            )

        community = _community_data.get(listing_id)

        # Get or create conversation
        state = self.get_or_create_conversation(inbound.from_number, listing_id)

        # Detect intent
        intent_data = self.detect_intent(inbound.body)
        intent = BuyerIntent(intent_data.get("intent", "unknown"))

        # Update buyer info if extracted
        if intent_data.get("extracted_name") and not state.buyer_name:
            state.buyer_name = intent_data["extracted_name"]
        if intent_data.get("extracted_budget") and not state.detected_budget:
            state.detected_budget = intent_data["extracted_budget"]

        # Add buyer message to history
        state.messages.append(ConversationMessage(
            role=MessageRole.user,
            content=inbound.body,
            intent=intent,
        ))

        # Build system prompt
        system_prompt = build_system_prompt(
            spa=spa,
            community_data=community,
            seller_asking_price=seller_asking_price,
            seller_notes=seller_notes,
        )

        # Build conversation history for Claude
        # Keep last 20 messages to manage context window
        history = state.messages[-20:]
        claude_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in history[:-1]  # exclude the message we just added
        ]
        claude_messages.append({
            "role": "user",
            "content": inbound.body,
        })

        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=claude_messages,
        )

        bot_response = response.content[0].text.strip()

        # Add bot response to history
        state.messages.append(ConversationMessage(
            role=MessageRole.assistant,
            content=bot_response,
        ))

        state.updated_at = datetime.utcnow()

        # Check escalation
        escalation = None
        should_escalate = (
            intent_data.get("should_escalate", False)
            or intent in ESCALATION_INTENTS
        )

        if should_escalate and not state.escalation_triggered:
            state.escalation_triggered = True
            state.escalation_reason = intent_data.get("escalation_reason", intent.value)

            # Generate conversation summary for Eric
            summary = self._summarise_conversation(state, spa)

            escalation = EscalationAlert(
                conversation_id=state.conversation_id,
                listing_id=listing_id,
                buyer_phone=inbound.from_number,
                buyer_name=state.buyer_name,
                trigger=intent,
                trigger_message=inbound.body,
                conversation_summary=summary,
                suggested_response=self._suggest_agent_response(intent, state),
            )

        return bot_response, escalation

    # ── Conversation utilities ─────────────────────────────────────────────────

    def _summarise_conversation(
        self,
        state: ConversationState,
        spa: SPAParseResult,
    ) -> str:
        """Generate a brief summary of the conversation for Eric's escalation alert."""
        if len(state.messages) <= 2:
            return "New enquiry — conversation just started."

        history_text = "\n".join([
            f"{msg.role.value.upper()}: {msg.content}"
            for msg in state.messages[-10:]
        ])

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": f"""Summarise this WhatsApp conversation between a buyer and an AI agent for a Dubai property listing ({spa.project}, {spa.unit_number}, asking AED {spa.purchase_price_aed:,.0f}).

Write 2-3 sentences covering: buyer's level of interest, key questions asked, and why escalation was triggered.

Conversation:
{history_text}

Summary:""",
                }],
            )
            return response.content[0].text.strip()
        except Exception:
            return f"Buyer enquired about {spa.unit_number}. Escalation triggered."

    def _suggest_agent_response(
        self,
        intent: BuyerIntent,
        state: ConversationState,
    ) -> str:
        """Suggest what Eric should say when picking up the conversation."""
        name = state.buyer_name or "the buyer"
        suggestions = {
            BuyerIntent.viewing_request: (
                f"Hi {name}, this is Eric from Dalya. I understand you'd like to arrange "
                f"a viewing — I'd be happy to set that up. When works best for you?"
            ),
            BuyerIntent.offer_submission: (
                f"Hi {name}, Eric from Dalya here. I saw your interest in making an offer "
                f"— let's discuss the details. What figure did you have in mind?"
            ),
            BuyerIntent.contact_sharing: (
                f"Hi {name}, Eric from Dalya. Thanks for reaching out — happy to help you "
                f"with this property. When's a good time for a quick call?"
            ),
            BuyerIntent.price_negotiation: (
                f"Hi {name}, Eric from Dalya. I understand you had some questions about "
                f"pricing — let me discuss that with you directly."
            ),
        }
        return suggestions.get(
            intent,
            f"Hi {name}, Eric from Dalya here. The AI flagged your enquiry for "
            f"personal follow-up — happy to assist you directly."
        )

    # ── Conversation retrieval ─────────────────────────────────────────────────

    def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        return _conversations.get(conversation_id)

    def get_all_conversations(self, listing_id: str) -> list[ConversationState]:
        return [
            c for c in _conversations.values()
            if c.listing_id == listing_id
        ]

    def get_listing_stats(self, listing_id: str) -> dict:
        """Quick stats for seller dashboard."""
        conversations = self.get_all_conversations(listing_id)
        escalated = [c for c in conversations if c.escalation_triggered]
        total_messages = sum(len(c.messages) for c in conversations)

        return {
            "listing_id": listing_id,
            "total_conversations": len(conversations),
            "total_messages": total_messages,
            "escalated_leads": len(escalated),
            "active_buyers": [
                {
                    "phone": c.buyer_phone,
                    "name": c.buyer_name,
                    "messages": len(c.messages),
                    "escalated": c.escalation_triggered,
                    "last_active": c.updated_at.isoformat(),
                }
                for c in sorted(conversations, key=lambda x: x.updated_at, reverse=True)
            ],
        }


# ── Singleton instance ─────────────────────────────────────────────────────────
engine = ChatbotEngine()
