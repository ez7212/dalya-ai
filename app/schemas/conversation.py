from pydantic import BaseModel, Field
from typing import Literal, Optional
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
    speak_to_human = "speak_to_human"
    bypass_attempt = "bypass_attempt"
    empty_message = "empty_message"
    not_interested = "not_interested"
    regulatory_request = "regulatory_request"
    legitimate_conveyancing = "legitimate_conveyancing"
    professional_inquiry = "professional_inquiry"
    unknown = "unknown"


class ConversationMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    intent: Optional[BuyerIntent] = None
    metadata: dict = Field(default_factory=dict)


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


class ListingInquiry(BaseModel):
    """A single property this buyer has enquired about."""
    listing_id: str
    project: str
    unit_number: str
    price_aed: float
    bedrooms: Optional[int] = None
    first_contact: datetime = Field(default_factory=datetime.utcnow)


class BuyerProfile(BaseModel):
    """
    Aggregated profile built across all conversations for a single buyer.
    Keyed by phone number. Used for personalisation and cross-listing recommendations.
    """
    phone: str
    name: Optional[str] = None
    budget_aed: Optional[float] = None
    bedroom_preferences: list[int] = []         # e.g. [4, 5]
    area_preferences: list[str] = []            # e.g. ["Dubailand", "Dubai Hills"]
    purpose: Optional[str] = None               # "investment" | "end_user"
    listings_inquired: list[ListingInquiry] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InboundMessage(BaseModel):
    """Incoming WhatsApp message from buyer."""
    from_number: str        # buyer's WhatsApp number
    to_number: str          # your Dalya WhatsApp number
    body: str               # message text
    message_sid: str        # Twilio message ID
    listing_id: Optional[str] = None  # extracted from pre-fill or context
    metadata: dict = Field(default_factory=dict)


class OutboundMessage(BaseModel):
    """Response to send back to buyer."""
    to_number: str
    body: str
    listing_id: str
    conversation_id: str


class EscalationType(str, Enum):
    offer = "offer"                         # buyer submitted an offer >= negotiation threshold
    unanswerable_question = "unanswerable_question"  # AI couldn't answer, forwarded to Eric
    info_gap = "info_gap"                   # listing fact/spec gap that needs agent confirmation
    materials_request = "materials_request" # off-plan renders/floor-plan/brochure request
    viewing_schedule = "viewing_schedule"   # ready-unit physical viewing request
    seller_action = "seller_action"         # seller messaging about offer/listing changes
    general_lead_capture = "general_lead_capture"  # buyer with no listing context reveals criteria
    legitimate_conveyancing = "legitimate_conveyancing"  # genuine legal/conveyancing process
    regulatory_request = "regulatory_request"  # PDPL / GDPR / data protection request


class EscalationAlert(BaseModel):
    """Fired to Eric when buyer hits a trigger."""
    escalation_type: Literal[
        "offer", "soft_offer", "viewing_request", "contact_sharing", "speak_to_human",
        "bypass_attempt", "regulatory_request",
        "seller_action", "general_lead_capture", "legitimate_conveyancing",
        "unanswerable_question", "info_gap", "materials_request", "viewing_schedule",
        "returning_buyer_followup",  # Phase 9.10
        "brn_request",                # Phase 9.6
        "media_unprocessable",        # DAL-159: voice/video the pipeline couldn't process
    ]
    conversation_id: Optional[str] = None
    listing_id: Optional[str] = None
    buyer_phone: Optional[str] = None
    buyer_name: Optional[str] = None
    trigger: Optional[BuyerIntent] = None
    trigger_message: Optional[str] = None

    # Offer-specific fields
    offer_amount_aed: Optional[float] = None
    listing_price_aed: Optional[float] = None
    negotiation_threshold_aed: Optional[float] = None

    # Phase 7.2: Marginal offer flag (within 5% below threshold — forwarded with caveat)
    is_marginal: bool = False
    marginal_gap_aed: Optional[float] = None
    marginal_gap_pct: Optional[float] = None

    # Summary (populated for offers; skipped for quick unanswerable forwards)
    conversation_summary: Optional[str] = None

    # Priority
    priority: Literal["low", "normal", "high"] = "normal"

    # Seller-action: classified seller intent (seller-mode only)
    seller_intent: Optional[str] = None

    # Phase 9.10: Buyer-mode subtype (e.g. soft_offer_above_asking,
    # co_broker_compliance, returning_buyer_followup, promise_kept).
    # Kept separate from seller_intent so buyer-mode escalations no longer
    # carry seller-mode field artifacts.
    escalation_subtype: Optional[str] = None

    # Regulatory request category
    regulatory_category: Optional[str] = None

    # Type-specific actionable context for the agent.
    payload: dict = Field(default_factory=dict)
