from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class BuyerIntent(str, Enum):
    """Detected intent from buyer message — drives escalation logic."""
    general_enquiry = "general_enquiry"
    price_negotiation = "price_negotiation"
    viewing_request = "viewing_request"
    payment_plan_query = "payment_plan_query"
    offer_submission = "offer_submission"
    contact_sharing = "contact_sharing"
    comparison_shopping = "comparison_shopping"
    not_interested = "not_interested"
    unknown = "unknown"


class ConversationMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    intent: Optional[BuyerIntent] = None


class ConversationState(BaseModel):
    """
    Full state of a buyer conversation.
    Persisted between messages — lives in memory for now,
    database in phase 2.
    """
    conversation_id: str
    listing_id: str
    buyer_phone: str
    messages: list[ConversationMessage] = []
    buyer_name: Optional[str] = None
    detected_budget: Optional[float] = None
    escalation_triggered: bool = False
    escalation_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InboundMessage(BaseModel):
    """Incoming WhatsApp message from buyer."""
    from_number: str        # buyer's WhatsApp number
    to_number: str          # your Dalya WhatsApp number
    body: str               # message text
    message_sid: str        # Twilio message ID
    listing_id: Optional[str] = None  # extracted from pre-fill or context


class OutboundMessage(BaseModel):
    """Response to send back to buyer."""
    to_number: str
    body: str
    listing_id: str
    conversation_id: str


class EscalationAlert(BaseModel):
    """Fired to Eric when buyer hits a trigger."""
    conversation_id: str
    listing_id: str
    buyer_phone: str
    buyer_name: Optional[str]
    trigger: BuyerIntent
    trigger_message: str    # the message that triggered escalation
    conversation_summary: str  # AI-generated summary for Eric
    suggested_response: str    # what Eric might say
