"""
SQLAlchemy ORM models — the database schema for Dalya.

Design decisions:
- SPA data stored as JSON column: avoids a 15-table relational mapping for
  payment schedules, purchasers etc. We always read/write the full SPA object.
- Conversations and messages are relational: we query them individually.
- Buyer profiles are relational: updated incrementally per message.
- All primary keys are strings (UUID or phone number) matching existing logic.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Index, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.db.session import Base


class DBListing(Base):
    __tablename__ = "listings"

    listing_id = Column(String, primary_key=True)
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=True, index=True)
    seller_id = Column(String, nullable=True, index=True)
    assigned_agent_id = Column(String, nullable=True, index=True)
    seller_phone = Column(String, nullable=True)      # seller's WhatsApp number for verification
    spa_data = Column(JSON, nullable=False)           # full SPAParseResult as dict
    community_data = Column(JSON, nullable=True)
    seller_asking_price = Column(Float, nullable=True)
    seller_notes = Column(Text, nullable=True)
    negotiation_threshold_aed = Column(Float, nullable=True)  # legacy alias of notification_threshold_aed (kept for back-compat)
    notification_threshold_aed = Column(Float, nullable=True) # min offer the Property Advisor escalates on
    seller_qa = Column(JSON, default=list)                    # Q&A pairs from managing agent replies
    media_urls = Column(JSON, default=list)                   # render/floor-plan URLs for this listing
    unit_profile = Column(JSON, default=dict)                 # structured agent-authored inspection notes
    unit_profile_history = Column(JSON, default=list)         # append-only dictation/edit audit trail
    processing_stages = Column(JSON, default=dict)            # stage_key → {status, at, note}

    # Multi-tenant fee model — replaces legacy hardcoded Mahoroba rates.
    # Future feature (deferred): per-fee public/private toggle so agents can hide fee math from buyers.
    commission_rate = Column(Float, nullable=False)           # decimal (e.g. 0.02 = 2%); required per listing
    additional_fees = Column(JSON, default=list)              # [{label, amount_aed, paid_by, public}]

    # Off-plan vs ready property — drives prompt-builder question-anchor selection.
    property_type = Column(String, nullable=True)             # "off_plan" | "ready"

    # Finished-property listings scraped from PF/Bayut: keep the source URL for audit.
    source_url = Column(Text, nullable=True)

    # Low-structured-value documents the Property Advisor can draw context from
    # (title deed, Ejari, service charge, DEWA, NOC, valuation, snagging, mortgage).
    reference_documents = Column(JSON, default=list)          # [{kind, url, label}]

    # Community key joins to DBCommunityResearch and DBAgentCommunityRemark.
    community = Column(String, nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    brokerage = relationship("DBBrokerage", back_populates="listings")
    conversations = relationship("DBConversation", back_populates="listing")
    amenities = relationship("DBListingAmenity", back_populates="listing")
    anchor_times = relationship("DBListingAnchorTime", back_populates="listing")
    enrichment_runs = relationship("DBEnrichmentRun", back_populates="listing")
    documents = relationship("DBListingDocument", back_populates="listing")
    facts = relationship("DBListingFact", back_populates="listing")
    knowledge_summary = relationship("DBListingKnowledgeSummary", back_populates="listing", uselist=False)


class DBListingDocument(Base):
    __tablename__ = "listing_documents"

    document_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    document_type = Column(String, nullable=False, index=True)
    label = Column(String, nullable=True)
    source_url = Column(Text, nullable=True)
    content_text = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="processed", index=True)
    extracted_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    listing = relationship("DBListing", back_populates="documents")
    facts = relationship("DBListingFact", back_populates="document")


class DBListingFact(Base):
    __tablename__ = "listing_facts"
    __table_args__ = (
        UniqueConstraint("listing_id", "document_id", "fact_key", name="uq_listing_fact_document_key"),
    )

    fact_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("listing_documents.document_id"), nullable=True, index=True)
    fact_key = Column(String, nullable=False, index=True)
    fact_group = Column(String, nullable=False, index=True)
    value_text = Column(Text, nullable=False)
    value_json = Column(JSON, default=dict)
    confidence = Column(Float, nullable=False, default=0.7)
    source = Column(String, nullable=False, default="document_extraction")
    verified = Column(Boolean, nullable=False, default=False, index=True)
    buyer_safe = Column(Boolean, nullable=False, default=True, index=True)
    risk_flag = Column(Boolean, nullable=False, default=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    listing = relationship("DBListing", back_populates="facts")
    document = relationship("DBListingDocument", back_populates="facts")


class DBListingKnowledgeSummary(Base):
    __tablename__ = "listing_knowledge_summaries"
    __table_args__ = (
        UniqueConstraint("brokerage_id", "listing_id", name="uq_listing_knowledge_summary_scope"),
    )

    summary_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    buyer_safe_summary = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    missing_information = Column(JSON, default=list)
    risk_flags = Column(JSON, default=list)
    status = Column(String, nullable=False, default="ready", index=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    listing = relationship("DBListing", back_populates="knowledge_summary")


class DBListingAmenity(Base):
    __tablename__ = "listing_amenities"
    __table_args__ = (
        UniqueConstraint(
            "listing_id",
            "profile_version",
            "category",
            "name",
            "source",
            "status",
            name="uq_listing_amenity_profile_fact",
        ),
    )

    amenity_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    category = Column(String, nullable=False, index=True)  # school | retail | transit | healthcare | worship | park | planned
    name = Column(String, nullable=False)
    google_place_id = Column(String, nullable=True, index=True)
    source = Column(String, nullable=False)  # google_places | developer_brochure | khda | harness_fixture
    status = Column(String, nullable=False, default="existing")  # existing | planned | none_found
    primary_type = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    straight_line_m = Column(Float, nullable=True)
    drive_time_min = Column(Float, nullable=True)
    walk_time_min = Column(Float, nullable=True)
    khda_rating = Column(String, nullable=True)
    khda_rating_year = Column(Integer, nullable=True)
    curriculum = Column(String, nullable=True)
    match_confidence = Column(Float, nullable=True)
    profile_version = Column(Integer, nullable=False, default=1, index=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    listing = relationship("DBListing", back_populates="amenities")


class DBListingAnchorTime(Base):
    __tablename__ = "listing_anchor_times"
    __table_args__ = (
        UniqueConstraint(
            "listing_id",
            "profile_version",
            "anchor_key",
            name="uq_listing_anchor_time_profile_key",
        ),
    )

    anchor_time_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    anchor_key = Column(String, nullable=False, index=True)
    anchor_name = Column(String, nullable=False)
    drive_time_min = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    source = Column(String, nullable=False, default="google_routes")
    profile_version = Column(Integer, nullable=False, default=1, index=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    listing = relationship("DBListing", back_populates="anchor_times")


class DBEnrichmentRun(Base):
    __tablename__ = "enrichment_runs"

    run_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    profile_version = Column(Integer, nullable=False, default=1, index=True)
    provider = Column(String, nullable=False, default="harness_fixture")
    mode = Column(String, nullable=False, default="batch")
    sku_usage = Column(JSON, default=dict)
    status = Column(String, nullable=False, default="complete", index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)

    listing = relationship("DBListing", back_populates="enrichment_runs")


class DBKHDASchool(Base):
    __tablename__ = "khda_schools"
    __table_args__ = (
        UniqueConstraint("normalized_name", "area", name="uq_khda_school_normalized_area"),
    )

    school_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    normalized_name = Column(String, nullable=False, index=True)
    area = Column(String, nullable=True, index=True)
    rating = Column(String, nullable=True)
    rating_year = Column(Integer, nullable=True)
    curriculum = Column(String, nullable=True)
    phase = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    source_url = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBBrokerage(Base):
    __tablename__ = "brokerages"

    brokerage_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    real_estate_number = Column(String, nullable=True, unique=True, index=True)
    agent_signup_code = Column(String, nullable=True, unique=True, index=True)
    agent_signup_enabled = Column(Boolean, nullable=False, default=False)
    primary_contact_name = Column(String, nullable=True)
    primary_contact_email = Column(String, nullable=True)
    primary_contact_phone = Column(String, nullable=True)
    rera_license_number = Column(String, nullable=True)
    escalation_contact_name = Column(String, nullable=True)
    escalation_contact_title = Column(String, nullable=True)
    escalation_contact_phone = Column(String, nullable=True)
    # Two-WhatsApp-number topology — Brokerage AI (buyer-facing) and Agents AI (agent-facing).
    # These may hold simulated/placeholder values until 360dialog WABA approval lands.
    brokerage_ai_number = Column(String, nullable=True, index=True)
    agents_ai_number = Column(String, nullable=True, index=True)
    # Optional per-brokerage cost-savings narrative used by prompt_builder when no listing override.
    # Shape: {"market_benchmark": 0.02, "narrative": "save vs 2% market", "managing_agent_title": "Lead Broker"}
    default_fee_framing = Column(JSON, nullable=True)
    prompt_config = Column(JSON, default=dict)
    settings = Column(JSON, default=dict)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    listings = relationship("DBListing", back_populates="brokerage")
    members = relationship("DBBrokerageMember", back_populates="brokerage")
    agent_profiles = relationship("DBAgentProfile", back_populates="brokerage")


class DBBrokerageMember(Base):
    __tablename__ = "brokerage_members"
    __table_args__ = (
        UniqueConstraint("brokerage_id", "user_id", name="uq_brokerage_member_user"),
    )

    member_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True, index=True)
    display_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    role = Column(String, nullable=False, default="agent")  # owner | team_lead | agent | admin
    status = Column(String, nullable=False, default="active")
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    brokerage = relationship("DBBrokerage", back_populates="members")


class DBAgentProfile(Base):
    __tablename__ = "agent_profiles"
    __table_args__ = (
        UniqueConstraint("brokerage_id", "user_id", name="uq_agent_profile_brokerage_user"),
    )

    profile_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True, index=True)
    full_name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    whatsapp_phone = Column(String, nullable=False, index=True)
    rera_broker_card_number = Column(String, nullable=False, index=True)
    rera_card_expiry = Column(DateTime, nullable=True)
    broker_card_file_url = Column(Text, nullable=True)
    languages = Column(JSON, default=list)
    service_areas = Column(JSON, default=list)
    verification_status = Column(String, nullable=False, default="submitted")
    verification_provider = Column(String, nullable=False, default="manual")
    verification_notes = Column(Text, nullable=True)
    chatbot_display_name = Column(String, nullable=True)
    chatbot_handoff_phone = Column(String, nullable=True)
    onboarding_status = Column(String, nullable=False, default="submitted")
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    brokerage = relationship("DBBrokerage", back_populates="agent_profiles")
    chatbot_config = relationship("DBAgentChatbotConfig", back_populates="agent_profile", uselist=False)
    verification_events = relationship("DBAgentVerification", back_populates="agent_profile")


class DBAgentVerification(Base):
    __tablename__ = "agent_verifications"

    verification_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_profile_id = Column(String, ForeignKey("agent_profiles.profile_id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, default="manual")  # manual | dubai_rest | trakheesi
    status = Column(String, nullable=False, default="submitted")
    rera_broker_card_number = Column(String, nullable=False)
    raw_response = Column(JSON, default=dict)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    agent_profile = relationship("DBAgentProfile", back_populates="verification_events")


class DBAgentChatbotConfig(Base):
    __tablename__ = "agent_chatbot_configs"
    __table_args__ = (
        UniqueConstraint("agent_profile_id", name="uq_agent_chatbot_config_profile"),
    )

    config_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_profile_id = Column(String, ForeignKey("agent_profiles.profile_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=False, index=True)
    handoff_display_name = Column(String, nullable=False)
    escalation_whatsapp_phone = Column(String, nullable=False)
    fallback_user_id = Column(String, nullable=True)
    active = Column(Boolean, nullable=False, default=False)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    agent_profile = relationship("DBAgentProfile", back_populates="chatbot_config")


class DBConversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(String, primary_key=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False)
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=True, index=True)
    assigned_agent_id = Column(String, nullable=True, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    buyer_name = Column(String, nullable=True)
    detected_budget = Column(Float, nullable=True)
    escalation_triggered = Column(Boolean, default=False)
    escalation_reason = Column(String, nullable=True)
    last_escalated_at = Column(DateTime, nullable=True)
    pending_forwarded_questions = Column(JSON, default=list)  # unanswerable questions awaiting grouped alert
    alerted_questions = Column(JSON, default=list)            # questions already sent to Eric — never re-alerted
    ai_summary = Column(JSON, nullable=True)                  # structured summary: {topics, interest_level, sentiment, key_question, next_step_hint}
    last_summarized_at = Column(DateTime, nullable=True)      # when the summary was last regenerated
    # Live takeover (DAL-158): while agent_controlled the concierge never answers;
    # inbound buyer messages are forwarded raw to the agent via Agents AI.
    ai_mode = Column(String, nullable=False, default="active")  # active | agent_controlled
    ai_mode_changed_at = Column(DateTime, nullable=True)
    ai_mode_changed_by = Column(String, nullable=True)          # agent user_id
    ai_mode_change_source = Column(String, nullable=True)       # dashboard | whatsapp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("DBListing", back_populates="conversations")
    brokerage = relationship("DBBrokerage")
    messages = relationship(
        "DBMessage",
        back_populates="conversation",
        order_by="DBMessage.timestamp",
    )
    lead_assignment = relationship("DBLeadAssignment", back_populates="conversation", uselist=False)
    tasks = relationship("DBLeadTask", back_populates="conversation")
    actions = relationship("DBLeadAction", back_populates="conversation")
    viewings = relationship("DBViewing", back_populates="conversation")
    draft_replies = relationship("DBDraftReply", back_populates="conversation")


class DBConversationAccessGrant(Base):
    __tablename__ = "conversation_access_grants"
    __table_args__ = (
        UniqueConstraint(
            "brokerage_id",
            "conversation_id",
            "agent_user_id",
            name="uq_conversation_access_grant_scope",
        ),
    )

    grant_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=False, index=True)
    granted_by_user_id = Column(String, nullable=True, index=True)
    access_level = Column(String, nullable=False, default="viewer")  # viewer | collaborator
    reason = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        String, ForeignKey("conversations.conversation_id"), nullable=False, index=True
    )
    role = Column(String, nullable=False)       # "user" | "assistant"
    content = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    metadata_json = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)
    # Voice-note transcription storage (DAL-159). Populated when the message
    # originated as audio; mirrors metadata_json["voice_note"].
    transcription_text = Column(Text, nullable=True)
    transcription_language = Column(String, nullable=True)
    transcription_confidence = Column(Float, nullable=True)
    transcription_provider = Column(String, nullable=True)

    conversation = relationship("DBConversation", back_populates="messages")


class DBBuyerSuppression(Base):
    __tablename__ = "buyer_suppressions"
    __table_args__ = (
        UniqueConstraint("brokerage_id", "buyer_phone", name="uq_buyer_suppression_scope"),
    )

    suppression_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=True, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    suppressed_by_user_id = Column(String, nullable=True, index=True)
    source = Column(String, nullable=False, default="buyer_opt_out")
    reason = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    lifted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBComplianceEvent(Base):
    __tablename__ = "compliance_events"

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=True, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=True, index=True)
    actor_user_id = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    direction = Column(String, nullable=False, default="system")  # inbound | outbound | system
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBPlatformAggregate(Base):
    __tablename__ = "platform_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "signal_type",
            "scope_key",
            "period_key",
            name="uq_platform_aggregate_signal_scope_period",
        ),
    )

    aggregate_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_type = Column(String, nullable=False, index=True)
    scope_key = Column(String, nullable=False, index=True)
    period_key = Column(String, nullable=False, index=True)
    sample_count = Column(Integer, nullable=False, default=0)
    brokerage_count = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, default=dict)
    source = Column(String, nullable=False, default="system")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBBuyerProfile(Base):
    __tablename__ = "buyer_profiles"

    phone = Column(String, primary_key=True)
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=True, index=True)
    name = Column(String, nullable=True)
    budget_aed = Column(Float, nullable=True)
    bedroom_preferences = Column(JSON, default=list)   # e.g. [4, 5]
    area_preferences = Column(JSON, default=list)      # e.g. ["Dubai Hills"]
    purpose = Column(String, nullable=True)            # "investment" | "end_user"
    lead_stage = Column(String, default="new")
    lead_source = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    admin_notes = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    inquiries = relationship("DBListingInquiry", back_populates="buyer")


class DBBuyerPreferenceProfile(Base):
    __tablename__ = "buyer_preference_profiles"
    __table_args__ = (
        UniqueConstraint("brokerage_id", "buyer_id", name="uq_buyer_preference_profile_scope"),
    )

    profile_id = Column(String, primary_key=True)
    buyer_id = Column(String, nullable=False, index=True)  # phone-number-based for v1
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    stated_preferences = Column(JSON, default=dict)
    inferred_preferences = Column(JSON, default=dict)
    inquiry_history = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    last_alternative_surface_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBBuyerListingMatch(Base):
    __tablename__ = "buyer_listing_matches"
    __table_args__ = (
        UniqueConstraint("listing_id", "buyer_profile_id", name="uq_buyer_listing_match"),
    )

    match_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    buyer_profile_id = Column(String, ForeignKey("buyer_preference_profiles.profile_id"), nullable=False, index=True)
    buyer_id = Column(String, nullable=False, index=True)
    match_score = Column(Float, nullable=False, default=0)
    aligned_preferences = Column(JSON, default=list)
    traced_inquiry_listing_ids = Column(JSON, default=list)
    outreach_draft = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="draft")  # draft | copied | dismissed | sent_external
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBListingInquiry(Base):
    __tablename__ = "listing_inquiries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=True, index=True)
    buyer_phone = Column(
        String, ForeignKey("buyer_profiles.phone"), nullable=False, index=True
    )
    listing_id = Column(String, nullable=False)
    project = Column(String, nullable=False)
    unit_number = Column(String, nullable=False)
    price_aed = Column(Float, nullable=False)
    first_contact = Column(DateTime, default=datetime.utcnow)

    buyer = relationship("DBBuyerProfile", back_populates="inquiries")


class DBAgentCommunityRemark(Base):
    """
    Agent-scoped private remark on a community.

    Private to the owning agent — never leaks across agents or brokerages.
    The Property Advisor injects these remarks ONLY when serving a listing
    whose assigned_agent_id matches this remark's agent_user_id AND whose
    community matches this remark's community_key.
    """
    __tablename__ = "agent_community_remarks"

    remark_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=False, index=True)
    community_key = Column(String, nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBAgentMessageRoute(Base):
    """
    Transport-agnostic reply-routing record.

    When the engine escalates to the brokerage's Agents AI, we mint a unique
    envelope token, send it with the alert to the managing agent's phone, and
    store a route here. When the agent replies (referencing the token), we
    look up this record and relay the body back to the original buyer via
    the brokerage's Brokerage AI number.
    """
    __tablename__ = "agent_message_routes"

    route_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id = Column(String, ForeignKey("escalation_threads.thread_id"), nullable=True, index=True)
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    agent_phone = Column(String, nullable=True)
    agents_ai_envelope_token = Column(String, nullable=False, unique=True, index=True)
    escalation_type = Column(String, nullable=False)
    tags = Column(JSON, default=list)
    expires_at = Column(DateTime, nullable=True)
    consumed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBMediaAsset(Base):
    """
    Outbound/inbound media stored by the platform (DAL-160). Storage refs are
    brokerage-scoped paths; the actual bytes live under MEDIA_STORAGE_DIR (or
    an external URL for listing assets re-sent without re-upload).
    """
    __tablename__ = "media_assets"

    media_asset_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=True, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)
    storage_ref = Column(Text, nullable=False)   # brokerage-scoped relative path or external URL
    sha256 = Column(String, nullable=True, index=True)
    original_filename = Column(String, nullable=True)
    source = Column(String, nullable=False, default="composer_upload")  # composer_upload | listing_asset | relay_inbound
    signing_nonce = Column(String, nullable=False, default=lambda: str(uuid.uuid4()))
    revoked_at = Column(DateTime, nullable=True, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    retention_until = Column(DateTime, nullable=True, index=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBBrokerageBuyerProfile(Base):
    """
    Brokerage-scoped buyer profile (DAL-164). Keyed by (brokerage_id,
    normalized phone) — one profile spans the buyer's conversations within a
    brokerage, but the same phone at two brokerages is two independent
    profiles. That is the tenant boundary; the cross-brokerage intelligence
    graph is a Phase 2 strategic question, not an MVP data model.
    """
    __tablename__ = "brokerage_buyer_profiles"
    __table_args__ = (
        UniqueConstraint("brokerage_id", "buyer_phone", name="uq_brokerage_buyer_profile"),
    )

    profile_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    language = Column(String, nullable=True)
    source = Column(String, nullable=True)  # portal | whatsapp_direct
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fields = relationship("DBBuyerProfileField", back_populates="profile")


class DBBuyerProfileField(Base):
    """
    Field-level qualification rows (DAL-164): one row per (profile, field,
    provenance). The AI write path only ever touches provenance='ai_inferred'
    rows — the (profile_id, field, provenance) uniqueness plus the scoped
    write path is the structural no-overwrite guard: an agent_confirmed value
    is physically a different row that AI inference cannot reach. A
    conflicting inference surfaces as a suggestion chip, agent-actioned only.
    """
    __tablename__ = "buyer_profile_fields"
    __table_args__ = (
        UniqueConstraint("profile_id", "field", "provenance", name="uq_buyer_profile_field_provenance"),
    )

    field_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("brokerage_buyer_profiles.profile_id"), nullable=False, index=True)
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    field = Column(String, nullable=False, index=True)
    # budget_min_aed | budget_max_aed | financing | purpose | family_size |
    # decision_makers | in_dubai_now | viewing_availability |
    # other_agent_status | urgency | contact_preference | timeline |
    # target_areas | property_type | bedrooms | must_haves | deal_breakers
    value = Column(JSON, nullable=True)
    provenance = Column(String, nullable=False)  # ai_inferred | agent_confirmed
    confidence = Column(Float, nullable=True)
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    confirmed_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = relationship("DBBrokerageBuyerProfile", back_populates="fields")


class DBOffer(Base):
    """
    First-class offer record (DAL-165). A thread is the sequence of
    offer/counter rows on one conversation+listing (thread_key). An offer
    never enters SUBMITTED without agent confirmation — AI proposes
    (DRAFT_PENDING_CONFIRM), the agent disposes.
    """
    __tablename__ = "offers"

    offer_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    buyer_profile_id = Column(String, ForeignKey("brokerage_buyer_profiles.profile_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    thread_key = Column(String, nullable=False, index=True)  # conversation_id:listing_id
    amount = Column(Float, nullable=True)
    direction = Column(String, nullable=False, default="buyer_offer")  # buyer_offer | seller_counter
    status = Column(String, nullable=False, default="draft_pending_confirm", index=True)
    # draft_pending_confirm | submitted | countered | accepted | rejected |
    # withdrawn | expired | discarded
    conditions = Column(Text, nullable=True)
    financing_contingent = Column(Boolean, nullable=False, default=False)
    subject_to_viewing = Column(Boolean, nullable=False, default=False)
    source = Column(String, nullable=False, default="agent_logged")  # ai_detected | agent_logged
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    thread_id = Column(String, ForeignKey("escalation_threads.thread_id"), nullable=True, index=True)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(String, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBLeadIngestRecord(Base):
    """
    A portal lead ingested by email (or, later, CRM webhook) — DAL-163.
    The raw payload is retained as the PDPL consent-basis evidence for the
    business-initiated first-touch template.
    """
    __tablename__ = "lead_ingests"

    ingest_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    source = Column(String, nullable=False, default="unknown")  # property_finder | bayut | unknown
    parser_version = Column(String, nullable=True)
    status = Column(String, nullable=False, default="ingested", index=True)
    # ingested | attached | duplicate | dead_letter
    buyer_name = Column(String, nullable=True)
    buyer_phone = Column(String, nullable=True, index=True)
    buyer_message = Column(Text, nullable=True)
    portal_listing_ref = Column(String, nullable=True)
    portal_listing_url = Column(Text, nullable=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    listing_resolution = Column(String, nullable=True)
    # matched_url | matched_permit | fuzzy_pending | unresolved
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=True, index=True)
    first_touch_sent = Column(Boolean, nullable=False, default=False)
    first_touch_template = Column(String, nullable=True)
    nudge_draft_id = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    raw_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBInboundProviderEvent(Base):
    """
    Provider webhook replay ledger. This is intentionally separate from business
    tables so idempotency is enforced before buyer/agent routing branches.
    """
    __tablename__ = "inbound_provider_events"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "endpoint",
            "provider_event_id",
            name="uq_inbound_provider_event_id",
        ),
        UniqueConstraint(
            "provider",
            "endpoint",
            "payload_fingerprint",
            name="uq_inbound_provider_payload_fingerprint",
        ),
    )

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String, nullable=False, index=True)
    endpoint = Column(String, nullable=False, index=True)
    provider_event_id = Column(String, nullable=True, index=True)
    payload_fingerprint = Column(String, nullable=False, index=True)
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=True, index=True)
    status = Column(String, nullable=False, default="processing")
    replay_count = Column(Integer, nullable=False, default=0)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    replayed_at = Column(DateTime, nullable=True)


class DBAgentNotification(Base):
    """
    Unified agent notification record (DAL-162). Every time-sensitive event
    pushes to the agent's WhatsApp via Agents AI with a deep link; digest-class
    events queue for the morning hot-list digest. Suppressions are recorded,
    never silently dropped.
    """
    __tablename__ = "agent_notifications"

    notification_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    urgency = Column(String, nullable=False, default="immediate")  # immediate | digest
    status = Column(String, nullable=False, default="sent", index=True)
    # sent | queued_digest | digested | suppressed_pref | collapsed_rate | failed
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=True, index=True)
    viewing_id = Column(String, ForeignKey("viewings.viewing_id"), nullable=True, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    dedupe_key = Column(String, nullable=True, unique=True, index=True)
    body = Column(Text, nullable=True)
    deep_link = Column(Text, nullable=True)
    whatsapp_message_sid = Column(String, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBAgentRelaySession(Base):
    """
    A ref session on the WhatsApp agent relay (DAL-161). Opened/refreshed by a
    quote-reply (tier 2); unquoted, untagged messages within 10 minutes route
    to the session conversation (tier 3, held). One active session per agent
    number — interleaved work uses caption tokens instead.
    """
    __tablename__ = "agent_relay_sessions"

    session_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    agent_phone = Column(String, nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active", index=True)  # active | closed
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)
    closed_reason = Column(String, nullable=True)  # superseded | expired | undo
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBRelayOutboxItem(Base):
    """
    A relay item awaiting delivery (DAL-161). Implicit-tier routing (session /
    escalation match) is held ~30s with an UNDO window; unrouted media is
    parked pending a routing prompt answer and expires after 30 minutes.
    """
    __tablename__ = "relay_outbox"

    item_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    agent_phone = Column(String, nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=True, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=True)
    media_asset_id = Column(String, ForeignKey("media_assets.media_asset_id"), nullable=True, index=True)
    body = Column(Text, nullable=True)            # caption for media, text for tier-3 text holds
    status = Column(String, nullable=False, default="held", index=True)  # held | sent | cancelled | parked | expired
    routing_method = Column(String, nullable=True)  # caption_token | quote_reply | session | escalation_match | parking_prompt
    release_at = Column(DateTime, nullable=True, index=True)
    parked_batch_id = Column(String, nullable=True, index=True)
    sent_at = Column(DateTime, nullable=True)
    cancelled_reason = Column(String, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBAgentVoiceReplyHold(Base):
    """
    A transcribed agent voice reply held below the confidence threshold
    (DAL-159, option B1). The agent receives the transcript and must reply
    SEND on the same [Ref: TOKEN] thread to release it to the buyer — the
    only flow where confidence gates sending.
    """
    __tablename__ = "agent_voice_reply_holds"

    hold_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    route_id = Column(String, ForeignKey("agent_message_routes.route_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    agent_phone = Column(String, nullable=True)
    envelope_token = Column(String, nullable=False, index=True)
    transcript = Column(Text, nullable=False)
    transcription_language = Column(String, nullable=True)
    transcription_confidence = Column(Float, nullable=True)
    transcription_provider = Column(String, nullable=True)
    status = Column(String, nullable=False, default="held")  # held | sent | cancelled | expired
    released_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBEscalationThread(Base):
    """
    Product-level escalation thread.

    This is separate from DBAgentMessageRoute: a thread is the open work item
    for the agent, while routes are transport tokens used to relay WhatsApp
    replies. A thread can collect multiple buyer questions under one token.
    """
    __tablename__ = "escalation_threads"
    __table_args__ = (
        Index(
            "ix_escalation_threads_open_match",
            "brokerage_id",
            "buyer_phone",
            "listing_id",
            "category",
            "state",
        ),
    )

    thread_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    agent_phone = Column(String, nullable=True)
    category = Column(String, nullable=False, index=True)
    state = Column(String, nullable=False, default="debouncing", index=True)  # debouncing | open | updated | resolved | timed_out | opt_out_closed
    escalation_type = Column(String, nullable=False)
    escalation_subtype = Column(String, nullable=True)
    envelope_token = Column(String, nullable=True, index=True)
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    alerted_at = Column(DateTime, nullable=True)
    last_buyer_message_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_update_sent_at = Column(DateTime, nullable=True)
    debounce_until = Column(DateTime, nullable=True)
    max_debounce_until = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    close_reason = Column(String, nullable=True)
    question_count = Column(Integer, nullable=False, default=0)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBEscalationThreadQuestion(Base):
    """Ordered buyer questions attached to a product-level escalation thread."""
    __tablename__ = "escalation_thread_questions"
    __table_args__ = (
        UniqueConstraint("thread_id", "sort_order", name="uq_escalation_question_order"),
    )

    question_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id = Column(String, ForeignKey("escalation_threads.thread_id"), nullable=False, index=True)
    buyer_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    question_text = Column(Text, nullable=False)
    category = Column(String, nullable=False, index=True)
    escalation_subtype = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)


class DBTelegramReplyRoute(Base):
    """
    Maps a Telegram message_id (sent by the bot) to a buyer's WhatsApp number.
    When Eric replies to an alert on Telegram, we look up this table to know
    which buyer to forward his reply to on WhatsApp.
    """
    __tablename__ = "telegram_reply_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_message_id = Column(Integer, unique=True, nullable=False, index=True)
    buyer_phone = Column(String, nullable=False)
    conversation_id = Column(String, nullable=False)
    listing_id = Column(String, nullable=False)
    buyer_name = Column(String, nullable=True)
    alert_questions = Column(Text, nullable=True)          # questions that triggered this alert — stored so Eric's reply becomes Q&A on the listing
    # Unused (kept for schema compatibility)
    pending_reply_text = Column(Text, nullable=True)
    confirm_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DBMessageQueue(Base):
    """
    Debounce queue for inbound WhatsApp messages.

    Messages sit here as 'pending' until DEBOUNCE_SECONDS have passed
    since the last message from that phone number. The background worker
    then collects all pending messages from the window, concatenates them,
    and processes them as a single input — so the AI always gets full context.

    Statuses: pending → processing → done | failed
    """
    __tablename__ = "message_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_number = Column(String, nullable=False, index=True)
    to_number = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    message_sid = Column(String, nullable=False)
    listing_id = Column(String, nullable=True)
    media_urls = Column(JSON, default=list)
    media_content_types = Column(JSON, default=list)
    metadata_json = Column(JSON, default=dict)
    status = Column(String, nullable=False, default="pending", index=True)
    received_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=True)


class DBCommunityResearch(Base):
    """
    Tracks community knowledge base research jobs.

    Lifecycle:
    - pending     → research job queued (SPA uploaded for unknown community)
    - researching → Opus + web search running
    - needs_review → draft file generated, awaiting admin approval
    - approved    → live in knowledge_base/, attached to listings
    - stale       → 30+ days since last audit, needs refresh
    """
    __tablename__ = "community_research"
    __table_args__ = (
        UniqueConstraint("project_name", "developer", name="uq_community_research_project_dev"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String, nullable=False, index=True)      # e.g. "The Oasis"
    developer = Column(String, nullable=False)                       # e.g. "Emaar Properties"
    status = Column(String, nullable=False, default="pending")       # pending/researching/needs_review/approved/stale
    file_path = Column(String, nullable=True)                        # relative path: "emaar_oasis.json" or "needs_review/emaar_oasis.json"
    source_urls = Column(JSON, default=list)                         # URLs used during research
    audit_flags = Column(JSON, default=list)                         # issues found in last audit
    research_confidence = Column(Float, nullable=True)               # 0-1 confidence score
    created_at = Column(DateTime, default=datetime.utcnow)
    last_researched_at = Column(DateTime, nullable=True)
    last_audited_at = Column(DateTime, nullable=True)


class DBSuspiciousActivity(Base):
    __tablename__ = "suspicious_activity"

    activity_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=True, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    buyer_name = Column(String, nullable=True)
    category = Column(String, nullable=False)  # "bypass_attempt", future: "scammer", "broker_probe", etc.
    trigger_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBOfferRecord(Base):
    """
    Immutable audit log of every buyer offer detected by the intent classifier.
    Stored regardless of whether the offer triggered escalation — gives a full
    paper trail for negotiation history and multilingual debugging.
    """
    __tablename__ = "offer_records"

    offer_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=True, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    buyer_name = Column(String, nullable=True)
    offer_amount_aed = Column(Float, nullable=False)
    asking_price_aed = Column(Float, nullable=False)
    gap_pct = Column(Float, nullable=False)           # (asking - offer) / asking * 100
    above_threshold = Column(Boolean, nullable=False, default=False)
    threshold_aed = Column(Float, nullable=True)      # snapshot of threshold at time of offer
    escalated = Column(Boolean, nullable=False, default=False)
    escalation_reason = Column(String, nullable=True) # e.g. "above_threshold", "first_offer", "higher_than_prior"
    superseded_by = Column(String, ForeignKey("offer_records.offer_id"), nullable=True)
    raw_message = Column(Text, nullable=True)         # original buyer text — useful for multilingual debugging
    language_detected = Column(String, nullable=True)
    turn_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBLeadAssignment(Base):
    """
    Current ownership and agent-facing state for a buyer conversation.
    This is the agent dashboard's primary work queue row.
    """
    __tablename__ = "lead_assignments"
    __table_args__ = (
        UniqueConstraint("conversation_id", name="uq_lead_assignment_conversation"),
    )

    assignment_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    assigned_agent_id = Column(String, nullable=True, index=True)
    assigned_by = Column(String, nullable=True)
    status = Column(String, nullable=False, default="new")  # new | active | viewing | offer | won | lost | archived
    signal = Column(String, nullable=True)                  # firm_offer | ready_to_view | budget_matched | needs_financing | cold
    urgency_score = Column(Integer, nullable=False, default=0)
    next_action = Column(String, nullable=True)             # call_now | send_whatsapp | book_viewing | follow_up | review_offer
    next_action_reason = Column(Text, nullable=True)
    due_at = Column(DateTime, nullable=True, index=True)
    last_agent_action_at = Column(DateTime, nullable=True)
    last_buyer_message_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("DBConversation", back_populates="lead_assignment")


class DBHotlistRefreshRun(Base):
    __tablename__ = "hotlist_refresh_runs"

    run_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    requested_by_user_id = Column(String, nullable=True, index=True)
    trigger = Column(String, nullable=False, default="manual")  # manual | scheduled | dashboard_load
    status = Column(String, nullable=False, default="running", index=True)  # running | complete | failed
    brokerage_timezone = Column(String, nullable=False, default="Asia/Dubai")
    refresh_date = Column(String, nullable=True, index=True)
    assignment_count = Column(Integer, nullable=False, default=0)
    task_count = Column(Integer, nullable=False, default=0)
    draft_count = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class DBLeadTask(Base):
    __tablename__ = "lead_tasks"

    task_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_key = Column(String, nullable=True, unique=True, index=True)
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=True, index=True)
    assigned_agent_id = Column(String, nullable=True, index=True)
    task_type = Column(String, nullable=False)              # call | whatsapp | viewing | offer | paperwork | owner_follow_up
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="open") # open | in_progress | done | skipped | cancelled
    priority = Column(String, nullable=False, default="normal")
    source = Column(String, nullable=True)                  # agent_dashboard | campaign | manual | system
    due_at = Column(DateTime, nullable=True, index=True)
    snoozed_until = Column(DateTime, nullable=True, index=True)
    snooze_reason = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(String, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("DBConversation", back_populates="tasks")


class DBLeadAction(Base):
    __tablename__ = "lead_actions"

    action_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=True, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    action_type = Column(String, nullable=False)            # call_started | call_completed | whatsapp_sent | viewing_booked | offer_reviewed
    outcome = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("DBConversation", back_populates="actions")


class DBViewing(Base):
    __tablename__ = "viewings"

    viewing_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    buyer_phone = Column(String, nullable=False, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    scheduled_for = Column(DateTime, nullable=True, index=True)
    status = Column(String, nullable=False, default="proposed") # proposed | confirmed | completed | cancelled | no_show
    tenant_notice_required = Column(Boolean, nullable=False, default=False)
    tenant_notice_sent_at = Column(DateTime, nullable=True)
    access_notes = Column(Text, nullable=True)
    post_viewing_notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("DBConversation", back_populates="viewings")


class DBTenantViewingConfirmation(Base):
    __tablename__ = "tenant_viewing_confirmations"
    __table_args__ = (
        UniqueConstraint("brokerage_id", "viewing_id", "tenant_contact_key", name="uq_tenant_viewing_confirmation_contact"),
    )

    confirmation_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    viewing_id = Column(String, ForeignKey("viewings.viewing_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    tenant_contact_key = Column(String, nullable=False, index=True)
    tenant_phone = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="pending", index=True)  # pending | notice_sent | confirmed | reschedule_requested | declined
    notice_body = Column(Text, nullable=True)
    outbound_message_id = Column(String, nullable=True)
    last_inbound_body = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    sent_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBViewingFeedback(Base):
    __tablename__ = "viewing_feedback"
    __table_args__ = (
        UniqueConstraint("viewing_id", "participant_type", name="uq_viewing_feedback_participant"),
    )

    feedback_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    viewing_id = Column(String, ForeignKey("viewings.viewing_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=True, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    participant_type = Column(String, nullable=False, index=True)  # buyer | agent
    status = Column(String, nullable=False, default="requested", index=True)  # requested | received
    score = Column(Integer, nullable=True)
    sentiment = Column(String, nullable=True)
    temperature = Column(String, nullable=True)
    financing_status = Column(String, nullable=True)
    next_action = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    raw_body = Column(Text, nullable=True)
    structured_json = Column(JSON, default=dict)
    source = Column(String, nullable=False, default="post_viewing_capture")
    requested_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBBuildingProfile(Base):
    """
    Building/community logistics facts learned from agent-confirmed listings.

    The key is provisional in Phase 1A. A later integration can map it to DLD,
    Property Finder, or another canonical source without changing callers.
    """
    __tablename__ = "building_profiles"
    __table_args__ = (
        UniqueConstraint("building_key", name="uq_building_profile_key"),
    )

    building_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    building_key = Column(String, nullable=False, index=True)
    community_key = Column(String, nullable=True, index=True)
    display_name = Column(String, nullable=False)
    canonical_source = Column(String, nullable=False, default="provisional_slug")
    access_defaults = Column(JSON, default=dict)
    security_defaults = Column(JSON, default=dict)
    notice_defaults = Column(JSON, default=dict)
    contributor_count = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=False, default=0.0)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBListingLogistics(Base):
    __tablename__ = "listing_logistics"
    __table_args__ = (
        UniqueConstraint("brokerage_id", "listing_id", name="uq_listing_logistics_scope"),
    )

    logistics_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    building_id = Column(String, ForeignKey("building_profiles.building_id"), nullable=True, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    access = Column(JSON, default=dict)
    keys = Column(JSON, default=dict)
    tenant = Column(JSON, default=dict)
    owner_permissions = Column(JSON, default=dict)
    source = Column(String, nullable=False, default="agent_confirmed")
    confirmed_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBTenantConsent(Base):
    __tablename__ = "tenant_consents"
    __table_args__ = (
        UniqueConstraint("brokerage_id", "listing_id", "tenant_contact_key", name="uq_tenant_consent_contact"),
    )

    consent_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=False, index=True)
    tenant_contact_key = Column(String, nullable=False, index=True)
    lawful_basis = Column(String, nullable=False, default="listing_viewing_coordination")
    opt_in_status = Column(String, nullable=False, default="pending")  # pending | opted_in | declined | not_required
    opt_in_requested_at = Column(DateTime, nullable=True)
    opt_in_confirmed_at = Column(DateTime, nullable=True)
    retention_until = Column(DateTime, nullable=True, index=True)
    visible_to_agent_user_id = Column(String, nullable=True, index=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBAgentAvailabilityBlock(Base):
    __tablename__ = "agent_availability_blocks"

    block_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=False, index=True)
    block_type = Column(String, nullable=False, default="working_hours")  # working_hours | time_off | busy_override
    weekday = Column(Integer, nullable=True, index=True)  # Monday=0
    date = Column(String, nullable=True, index=True)      # YYYY-MM-DD override
    start_time = Column(String, nullable=False)           # HH:MM
    end_time = Column(String, nullable=False)             # HH:MM
    timezone = Column(String, nullable=False, default="Asia/Dubai")
    recurring = Column(Boolean, nullable=False, default=False)
    label = Column(String, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBAgentCalendarConnection(Base):
    __tablename__ = "agent_calendar_connections"
    __table_args__ = (
        UniqueConstraint("brokerage_id", "agent_user_id", "provider", name="uq_agent_calendar_provider"),
    )

    connection_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, default="google")
    status = Column(String, nullable=False, default="not_connected")  # not_connected | connected | error
    selected_calendar_ids = Column(JSON, default=list)
    sync_direction = Column(String, nullable=False, default="read_freebusy_write_viewings")
    token_ref = Column(String, nullable=True)
    scopes = Column(JSON, default=list)
    last_sync_at = Column(DateTime, nullable=True)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBDraftReply(Base):
    __tablename__ = "draft_replies"

    draft_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=True, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    intent = Column(String, nullable=False)                 # follow_up | viewing_slots | budget_clarification | offer_ack
    draft_text = Column(Text, nullable=False)
    source = Column(String, nullable=False, default="template")
    status = Column(String, nullable=False, default="draft") # draft | edited | sent | discarded
    sent_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("DBConversation", back_populates="draft_replies")


class DBAIDraft(Base):
    __tablename__ = "ai_drafts"

    draft_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=True, index=True)
    listing_id = Column(String, ForeignKey("listings.listing_id"), nullable=True, index=True)
    buyer_phone = Column(String, nullable=True, index=True)
    draft_type = Column(String, nullable=False)             # whatsapp_reply | seller_update | offer_counter | campaign_message
    title = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="draft") # draft | approved | sent | discarded
    source = Column(String, nullable=False, default="agent_dashboard")
    confidence_score = Column(Float, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBCampaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    owner_agent_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False)
    campaign_type = Column(String, nullable=False, default="owner_acquisition")
    channel = Column(String, nullable=False, default="whatsapp") # whatsapp | email | landing_page | mixed
    status = Column(String, nullable=False, default="draft")      # draft | active | paused | completed | archived
    audience = Column(JSON, default=dict)
    offer = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    uploads = relationship("DBCampaignUpload", back_populates="campaign")
    recipients = relationship("DBCampaignRecipient", back_populates="campaign")
    outreach_drafts = relationship("DBOutreachDraft", back_populates="campaign")
    owner_leads = relationship("DBOwnerLead", back_populates="campaign")
    marketing_pages = relationship("DBMarketingPage", back_populates="campaign")


class DBCampaignUpload(Base):
    __tablename__ = "campaign_uploads"

    upload_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False, index=True)
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    uploaded_by = Column(String, nullable=True, index=True)
    file_name = Column(String, nullable=False)
    file_url = Column(Text, nullable=True)
    file_type = Column(String, nullable=True)
    row_count = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="uploaded") # uploaded | processing | processed | failed
    parsed_summary = Column(JSON, default=dict)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    campaign = relationship("DBCampaign", back_populates="uploads")


class DBOwnerLead(Base):
    __tablename__ = "owner_leads"

    owner_lead_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=True, index=True)
    assigned_agent_id = Column(String, nullable=True, index=True)
    owner_name = Column(String, nullable=True)
    owner_phone = Column(String, nullable=True, index=True)
    owner_email = Column(String, nullable=True, index=True)
    project = Column(String, nullable=True, index=True)
    unit_number = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    estimated_value_aed = Column(Float, nullable=True)
    intent = Column(String, nullable=True)                  # sell | rent | valuation | unknown
    lead_source = Column(String, nullable=True)
    stage = Column(String, nullable=False, default="new")   # new | contacted | qualified | spa_requested | listed | lost
    priority = Column(String, nullable=False, default="normal")
    last_contacted_at = Column(DateTime, nullable=True)
    next_follow_up_at = Column(DateTime, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("DBCampaign", back_populates="owner_leads")


class DBCampaignRecipient(Base):
    __tablename__ = "campaign_recipients"
    __table_args__ = (
        UniqueConstraint("campaign_id", "recipient_key", name="uq_campaign_recipient_key"),
    )

    recipient_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False, index=True)
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    owner_lead_id = Column(String, ForeignKey("owner_leads.owner_lead_id"), nullable=True, index=True)
    recipient_key = Column(String, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    channel = Column(String, nullable=False, default="whatsapp")
    status = Column(String, nullable=False, default="queued") # queued | drafted | sent | replied | bounced | opted_out
    last_message_at = Column(DateTime, nullable=True)
    last_response_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("DBCampaign", back_populates="recipients")


class DBOutreachDraft(Base):
    __tablename__ = "outreach_drafts"

    outreach_draft_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=True, index=True)
    recipient_id = Column(String, ForeignKey("campaign_recipients.recipient_id"), nullable=True, index=True)
    owner_lead_id = Column(String, ForeignKey("owner_leads.owner_lead_id"), nullable=True, index=True)
    agent_user_id = Column(String, nullable=True, index=True)
    channel = Column(String, nullable=False, default="whatsapp")
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="draft") # draft | approved | sent | discarded
    source = Column(String, nullable=False, default="ai")
    sent_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("DBCampaign", back_populates="outreach_drafts")


class DBMarketingPage(Base):
    __tablename__ = "marketing_pages"

    page_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=True, index=True)
    slug = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    page_type = Column(String, nullable=False, default="campaign_landing")
    status = Column(String, nullable=False, default="draft") # draft | published | archived
    url = Column(Text, nullable=True)
    content = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("DBCampaign", back_populates="marketing_pages")
    events = relationship("DBMarketingEvent", back_populates="page")


class DBMarketingEvent(Base):
    __tablename__ = "marketing_events"

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brokerage_id = Column(String, ForeignKey("brokerages.brokerage_id"), nullable=False, index=True)
    page_id = Column(String, ForeignKey("marketing_pages.page_id"), nullable=True, index=True)
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=True, index=True)
    owner_lead_id = Column(String, ForeignKey("owner_leads.owner_lead_id"), nullable=True, index=True)
    event_type = Column(String, nullable=False)             # page_view | cta_click | form_submit | whatsapp_click
    visitor_id = Column(String, nullable=True, index=True)
    source = Column(String, nullable=True)
    payload = Column(JSON, default=dict)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    page = relationship("DBMarketingPage", back_populates="events")
