"""
Chatbot Engine
The core AI conversation handler for Dalya listings.

Flow:
1. Receive buyer message
2. Load/create conversation state from DB
3. Detect intent (escalation trigger check)
4. Build context (system prompt + conversation history)
5. Call Claude for response
6. Persist message + updated state to DB
7. Fire escalation alert if triggered
8. Return response

Storage: PostgreSQL via SQLAlchemy
"""

import anthropic
import logging
import re
import time
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Optional, Tuple
from sqlalchemy.exc import DBAPIError

from app.core.response_validator import validate_and_rewrite_response
from app.core.refusal_variation import (
    GATING,
    OUT_OF_SCOPE,
    SELLER_PII,
    render_refusal,
)

DOCUMENT_DISCLOSURE = "document_disclosure"

# ── Post-generation sanitizer constants ───────────────────────────────────────
TEAM_REPLACEMENTS = [
    (re.compile(r"\bI'?ve passed (?:your )?(?:question|message|enquiry|inquiry)?\s*(?:to|along to)\s*(?:the\s+)?team\b", re.IGNORECASE), "I don't have that detail in the contract"),
    (re.compile(r"\b(?:our|the)\s+team\s+(?:will|can|follows?\s+up|gets?\s+back)\b", re.IGNORECASE), "I'll get back to you on that"),
    (re.compile(r"\bonce\s+the\s+team\s+follows?\s+up\b", re.IGNORECASE), "once we follow up"),
    (re.compile(r"\b(?:the|our)\s+team\b", re.IGNORECASE), "the seller's side"),
    (re.compile(r"\bI'?ll\s+pass\s+(?:this|that|your\s+\w+)\s+on\b", re.IGNORECASE), "I'll note that"),
    (re.compile(r"\b(?:back\s+office|backoffice)\b", re.IGNORECASE), "the seller"),
]

logger = logging.getLogger(__name__)

from app.schemas.spa import SPAParseResult
from app.schemas.conversation import (
    ConversationState,
    ConversationMessage,
    MessageRole,
    BuyerIntent,
    EscalationAlert,
    EscalationType,
    InboundMessage,
    BuyerProfile,
)
from app.core.payment_compute import compute_paid_to_date
from app.core.prompt_builder import build_system_prompt
from app.core.listing_enrichment import latest_listing_enrichment
from app.core.intent_classifier import detect_intent_claude
from app.core.voice_notes import (
    apply_voice_offer_intent,
    needs_voice_amount_confirmation,
    voice_amount_confirmation_response,
)
from app.core.multitenant_context import (
    BrokerageContext,
    context_for_listing,
    legacy_default_context,
)
from app.db.session import (
    SessionLocal,
    TransientDatabaseError,
    is_transient_db_error,
    reset_db_connections,
    safe_commit,
)
from app.db import crud


# ── Escalation triggers ────────────────────────────────────────────────────────
# Offers escalate only when the offer amount meets the negotiation threshold.
# Unanswerable questions escalate immediately.
# Contact sharing no longer triggers escalation.


class ChatbotEngine:
    def __init__(self):
        # Explicit timeout + bounded retries: with SDK defaults (600s timeout)
        # an Anthropic 529-overload retry storm could balloon a single turn to
        # 16 minutes (DAL-83). Cap it so a turn never hangs a live WhatsApp line.
        self.client = anthropic.Anthropic(timeout=45.0, max_retries=2)
        self.model = "claude-haiku-4-5-20251001"

    def handle_message_resilient(
        self,
        inbound: InboundMessage,
        seller_asking_price: Optional[float] = None,
        seller_notes: Optional[str] = None,
        attempts: int = 2,
    ) -> tuple[str, Optional[EscalationAlert], Optional[str]]:
        """
        Retry a full chatbot turn when the database connection drops mid-write.
        Duplicate message inserts are suppressed in crud.add_message.
        """
        for attempt in range(attempts):
            try:
                response_text, escalation, media_url = self.handle_message(
                    inbound,
                    seller_asking_price=seller_asking_price,
                    seller_notes=seller_notes,
                )
                # DAL-159 Path C: escalations triggered by a transcribed voice
                # note carry provenance so the Agents AI envelope can label it.
                if escalation is not None and (inbound.metadata or {}).get("voice_note"):
                    escalation.payload = {
                        **(escalation.payload or {}),
                        "voice_transcribed": True,
                    }
                return response_text, escalation, media_url
            except TransientDatabaseError as exc:
                retryable = True
                last_exc = exc
            except DBAPIError as exc:
                retryable = is_transient_db_error(exc)
                last_exc = exc

            if not retryable or attempt >= attempts - 1:
                raise last_exc

            reset_db_connections()
            logger.warning(
                "Retrying chatbot turn after transient DB error "
                "[sid:%s attempt:%s/%s]: %s",
                inbound.message_sid,
                attempt + 1,
                attempts,
                last_exc,
            )
            time.sleep(0.25 * (attempt + 1))

        raise RuntimeError("Unreachable chatbot retry state")

    # ── Listing registration ───────────────────────────────────────────────────

    def register_listing(
        self,
        listing_id: str,
        spa: SPAParseResult,
        community_data: Optional[dict] = None,
        seller_asking_price: Optional[float] = None,
        seller_notes: Optional[str] = None,
        negotiation_threshold_aed: Optional[float] = None,
    ) -> str:
        """
        Register a parsed listing so the chatbot can serve it.
        Persists to PostgreSQL. Returns the listing_id.
        """
        with SessionLocal() as db:
            crud.save_listing(
                db=db,
                listing_id=listing_id,
                spa=spa,
                community_data=community_data,
                seller_asking_price=seller_asking_price,
                seller_notes=seller_notes,
                negotiation_threshold_aed=negotiation_threshold_aed,
            )
        return listing_id

    # ── Main conversation handler ──────────────────────────────────────────────

    def handle_message(
        self,
        inbound: InboundMessage,
        seller_asking_price: Optional[float] = None,
        seller_notes: Optional[str] = None,
    ) -> tuple[str, Optional[EscalationAlert], Optional[str]]:
        """
        Main entry point. Process an inbound buyer message.

        Returns:
            tuple of (response_text, escalation_alert_or_None)
        """
        listing_id = inbound.listing_id

        with SessionLocal() as db:
            # Load listing
            db_listing = crud.get_listing(db, listing_id) if listing_id else None
            if not db_listing:
                # No listing context — portfolio-aware fallback to prevent hallucination
                return self._handle_no_listing_fallback(inbound, db)

            spa = SPAParseResult.model_validate(db_listing.spa_data)
            community = db_listing.community_data

            # Multi-tenant brokerage context — resolved from the listing's
            # brokerage_id + assigned_agent_id. Used everywhere we used to
            # hardcode Mahoroba/Eric or a fixed commission.
            ctx = context_for_listing(listing_id, db)

            # Use stored seller settings if not explicitly passed
            if seller_asking_price is None:
                seller_asking_price = db_listing.seller_asking_price
            if seller_notes is None:
                seller_notes = db_listing.seller_notes

            # ── Seller-mode detection ─────────────────────────────────────
            if self._is_seller_messaging(inbound, listing_id, db_listing):
                return self._handle_seller_message(inbound, listing_id, db_listing, spa, db)

            # Get or create conversation
            conv = crud.get_or_create_conversation(db, inbound.from_number, listing_id)
            if (
                (db_listing.brokerage_id and conv.brokerage_id != db_listing.brokerage_id)
                or (db_listing.assigned_agent_id and conv.assigned_agent_id != db_listing.assigned_agent_id)
            ):
                conv.brokerage_id = db_listing.brokerage_id
                conv.assigned_agent_id = db_listing.assigned_agent_id
                conv.updated_at = datetime.utcnow()
                safe_commit(db)

            seller_intent_probe = self._classify_seller_intent(inbound.body)
            seller_context_seen = (conv.escalation_reason or "").startswith("seller_action")
            if (
                (self._detect_claimed_seller_context(inbound.body) or seller_context_seen)
                and seller_intent_probe
                in {
                    "offer_acceptance", "counter_offer", "listing_status_change",
                    "advisory_question", "net_proceeds", "buyer_privacy_request",
                    "performance_metrics", "price_update", "threshold_update",
                    "listing_edit", "buyer_outreach_request", "general_seller_question",
                }
            ):
                return self._handle_seller_message(inbound, listing_id, db_listing, spa, db)

            # Detect intent using multilingual Claude Haiku classifier.
            # Falls back to rules-based detection on API failure.
            seller_qa = list(db_listing.seller_qa or [])
            intent_data = detect_intent_claude(inbound.body)
            intent_data = apply_voice_offer_intent(intent_data, inbound.metadata)
            intent = BuyerIntent(intent_data.get("intent", "unknown"))

            # Update conversation state with any extracted buyer info
            new_name = None
            new_budget = None
            if intent_data.get("extracted_name") and not conv.buyer_name:
                new_name = intent_data["extracted_name"]
            if intent_data.get("extracted_budget") and not conv.detected_budget:
                new_budget = intent_data["extracted_budget"]

            if new_name or new_budget:
                crud.update_conversation(
                    db, conv,
                    buyer_name=new_name,
                    detected_budget=new_budget,
                )

            # Persist buyer message
            persisted_message = crud.add_message(
                db,
                conversation_id=conv.conversation_id,
                role=MessageRole.user.value,
                content=inbound.body,
                intent=intent.value,
                metadata_json=inbound.metadata,
            )

            # DAL-164: qualification extraction on the message path — writes
            # ai_inferred rows only (the confirmed rows are untouchable here).
            from app.core.buyer_profiles import update_profile_from_message
            update_profile_from_message(
                db,
                conversation=conv,
                message_text=inbound.body,
                message_id=persisted_message.id if persisted_message else None,
                intent_data=intent_data,
            )

            # Update buyer profile
            self._update_buyer_profile(
                db=db,
                phone=inbound.from_number,
                spa=spa,
                db_listing=db_listing,
                listing_id=listing_id,
                buyer_message=inbound.body,
                intent_data=intent_data,
                buyer_name=conv.buyer_name,
                detected_budget=conv.detected_budget,
            )

            # ── Lead source detection ─────────────────────────────────────
            db_profile = crud.get_or_create_buyer_profile(db, inbound.from_number)
            if not db_profile.lead_source:
                if inbound.body.startswith("LISTING:"):
                    db_profile.lead_source = "portal"
                else:
                    db_profile.lead_source = "whatsapp_direct"
                safe_commit(db)
                db.refresh(db_profile)

            if needs_voice_amount_confirmation(intent_data, inbound.metadata):
                bot_response = voice_amount_confirmation_response(intent_data)
                bot_response, _ = self._finalize_response(bot_response, intent, conv, ctx=ctx)
                crud.add_message(
                    db,
                    conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value,
                    content=bot_response,
                    metadata_json={
                        "voice_offer_confirmation": {
                            "source_phrase": intent_data.get("voice_offer_source_phrase"),
                            "candidates": intent_data.get("voice_offer_candidates") or [],
                        }
                    },
                )
                crud.update_conversation(db, conv)
                return bot_response, None, None

            # Build buyer profile for prompt context
            buyer_profile = crud.db_profile_to_schema(db_profile)

            # Phase 10.1: Route special intents before any generic listing-chat
            # response is generated. These branches have their own privacy,
            # compliance, or peer-mode rules; letting the normal buyer prompt run
            # first can persist a response the buyer never receives.
            is_form_a_request = self._detect_co_broker_compliance(inbound.body)
            is_seller_contact_request = self._detect_seller_contact_request(inbound.body)
            is_document_disclosure_request = self._detect_document_disclosure_request(inbound.body)
            if not is_seller_contact_request and self._continues_seller_contact_probe(conv, inbound.body):
                is_seller_contact_request = True
            is_out_of_scope_refusal_request = self._detect_out_of_scope_refusal_request(inbound.body)
            from app.core.brokerage_access import (
                is_buyer_suppressed,
                is_opt_out_message,
                mark_buyer_opted_out,
                record_compliance_event,
            )
            brokerage_id = db_listing.brokerage_id or conv.brokerage_id
            opt_out_request = is_opt_out_message(inbound.body)
            already_suppressed = bool(
                brokerage_id and is_buyer_suppressed(db, brokerage_id, inbound.from_number)
            )

            if opt_out_request and brokerage_id:
                mark_buyer_opted_out(
                    db,
                    brokerage_id=brokerage_id,
                    buyer_phone=inbound.from_number,
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    reason="buyer requested no further contact",
                    source="buyer_message",
                )
                from app.core.escalation_threads import close_open_threads_for_opt_out
                close_open_threads_for_opt_out(
                    db,
                    brokerage_id=brokerage_id,
                    buyer_phone=inbound.from_number,
                )
                bot_response = self._compose_opt_out_acknowledgment()
                bot_response, _ = self._finalize_response(bot_response, BuyerIntent.not_interested, conv, ctx=ctx)
                crud.add_message(
                    db,
                    conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value,
                    content=bot_response,
                )
                crud.update_conversation(db, conv)
                return bot_response, None, None

            if already_suppressed and brokerage_id:
                record_compliance_event(
                    db,
                    brokerage_id=brokerage_id,
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    event_type="buyer_message_suppressed",
                    direction="inbound",
                    details={"message_preview": inbound.body[:200]},
                )
                crud.update_conversation(db, conv)
                return "", None, None

            if intent == BuyerIntent.regulatory_request:
                category = self._detect_regulatory_category(inbound.body)
                escalation = EscalationAlert(
                    escalation_type="regulatory_request",
                    priority="high",
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    trigger=intent,
                    trigger_message=inbound.body,
                    regulatory_category=category,
                    payload={
                        "category": category,
                        "request": inbound.body,
                        "requested_action": "Verify identity and respond under the applicable data-rights process.",
                    },
                )
                already_alerted = (
                    conv.escalation_triggered
                    and conv.escalation_reason == "regulatory_request"
                )
                bot_response = (
                    self._compose_regulatory_followup_acknowledgment(inbound.body)
                    if already_alerted
                    else self._compose_regulatory_acknowledgment(inbound.body)
                )
                bot_response, _ = self._finalize_response(bot_response, intent, conv, ctx=ctx)
                crud.add_message(
                    db,
                    conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value,
                    content=bot_response,
                )
                if already_alerted:
                    crud.update_conversation(db, conv)
                    return bot_response, None, None

                crud.update_conversation(
                    db, conv,
                    escalation_triggered=True,
                    escalation_reason="regulatory_request",
                    last_escalated_at=datetime.utcnow(),
                )
                record_compliance_event(
                    db,
                    brokerage_id=brokerage_id or db_listing.brokerage_id,
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    event_type="regulatory_request_received",
                    direction="inbound",
                    details={
                        "category": category,
                        "request": inbound.body,
                    },
                )
                return bot_response, escalation, None

            if is_seller_contact_request:
                ask_count, used_lines, already_refusal_escalated = self._next_refusal_state(conv, SELLER_PII)
                decision = render_refusal(
                    intent=SELLER_PII,
                    conv=conv,
                    managing_agent_name=ctx.managing_agent_name,
                    already_escalated=already_refusal_escalated or (conv.escalation_reason == f"bypass_attempt:{SELLER_PII}"),
                    ask_count_override=ask_count,
                    used_texts_override=used_lines,
                    language="ar" if self._is_arabic_text(inbound.body) else "en",
                )
                self._store_refusal_state(conv, SELLER_PII, decision)
                bot_response = decision.text
                bot_response, _ = self._finalize_response(bot_response, BuyerIntent.bypass_attempt, conv, ctx=ctx)
                crud.add_message(
                    db,
                    conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value,
                    content=bot_response,
                )
                crud.update_conversation(db, conv)
                crud.create_suspicious_activity(
                    db=db,
                    listing_id=listing_id,
                    conversation_id=conv.conversation_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    category="bypass_attempt",
                    trigger_message=inbound.body,
                    bot_response=bot_response,
                )
                escalation = None
                if decision.should_escalate:
                    escalation = EscalationAlert(
                        escalation_type="bypass_attempt",
                        priority="normal",
                        conversation_id=conv.conversation_id,
                        listing_id=listing_id,
                        buyer_phone=inbound.from_number,
                        buyer_name=conv.buyer_name,
                        trigger=BuyerIntent.bypass_attempt,
                        trigger_message=inbound.body,
                        escalation_subtype=SELLER_PII,
                        payload={
                            "refusal_class": SELLER_PII,
                            "ask_count": decision.ask_count,
                            "requested_action": "Review repeated seller-contact probe; seller PII was not disclosed.",
                        },
                    )
                    self._record_escalation_state(db, conv, escalation)
                return bot_response, escalation, None

            if is_document_disclosure_request:
                ask_count, used_lines, _ = self._next_refusal_state(conv, DOCUMENT_DISCLOSURE)
                bot_response = self._compose_privacy_refusal(
                    inbound.body,
                    conv=conv,
                    ctx=ctx,
                    ask_count=ask_count,
                    used_texts=used_lines,
                )
                self._store_refusal_state(
                    conv,
                    DOCUMENT_DISCLOSURE,
                    SimpleNamespace(
                        text=bot_response,
                        ask_count=ask_count,
                        should_escalate=False,
                    ),
                )
                bot_response, _ = self._finalize_response(bot_response, BuyerIntent.bypass_attempt, conv, ctx=ctx)
                crud.add_message(
                    db,
                    conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value,
                    content=bot_response,
                )
                crud.update_conversation(db, conv)
                return bot_response, None, None

            if is_out_of_scope_refusal_request:
                ask_count, used_lines, already_refusal_escalated = self._next_refusal_state(conv, OUT_OF_SCOPE)
                decision = render_refusal(
                    intent=OUT_OF_SCOPE,
                    conv=conv,
                    managing_agent_name=ctx.managing_agent_name,
                    already_escalated=already_refusal_escalated or (conv.escalation_reason == f"bypass_attempt:{OUT_OF_SCOPE}"),
                    ask_count_override=ask_count,
                    used_texts_override=used_lines,
                    language="ar" if self._is_arabic_text(inbound.body) else "en",
                )
                self._store_refusal_state(conv, OUT_OF_SCOPE, decision)
                bot_response = decision.text
                bot_response, _ = self._finalize_response(bot_response, BuyerIntent.bypass_attempt, conv, ctx=ctx)
                crud.add_message(
                    db,
                    conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value,
                    content=bot_response,
                )
                crud.update_conversation(db, conv)
                crud.create_suspicious_activity(
                    db=db,
                    listing_id=listing_id,
                    conversation_id=conv.conversation_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    category="bypass_attempt",
                    trigger_message=inbound.body,
                    bot_response=bot_response,
                )
                escalation = None
                if decision.should_escalate:
                    escalation = EscalationAlert(
                        escalation_type="bypass_attempt",
                        priority="normal",
                        conversation_id=conv.conversation_id,
                        listing_id=listing_id,
                        buyer_phone=inbound.from_number,
                        buyer_name=conv.buyer_name,
                        trigger=BuyerIntent.bypass_attempt,
                        trigger_message=inbound.body,
                        escalation_subtype=OUT_OF_SCOPE,
                        payload={
                            "refusal_class": OUT_OF_SCOPE,
                            "ask_count": decision.ask_count,
                            "requested_action": "Review repeated out-of-scope or instruction-override probe.",
                        },
                    )
                    self._record_escalation_state(db, conv, escalation)
                return bot_response, escalation, None

            if intent == BuyerIntent.legitimate_conveyancing:
                # Phase 8.7: NEVER confirm or deny whether the buyer has an offer on file.
                # Both verified and unverified branches use identical buyer-facing phrasing.
                referenced_buyer = intent_data.get("referenced_buyer_name")
                matched_offer = None
                if referenced_buyer:
                    matched_offer = crud.find_offer_by_buyer_name(db, listing_id, referenced_buyer)

                bot_response = (
                    "I can't share specifics about another buyer's offer status with you "
                    "directly. I've forwarded this to {managing_agent_name} and they'll reach out to discuss "
                    "the conveyancing next steps on this WhatsApp thread."
                )
                bot_response, _ = self._finalize_response(bot_response, intent, conv, ctx=ctx)
                crud.add_message(
                    db,
                    conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value,
                    content=bot_response,
                )
                crud.update_conversation(db, conv)

                escalation = EscalationAlert(
                    escalation_type=EscalationType.legitimate_conveyancing.value,
                    escalation_subtype="matched_offer" if matched_offer else "unverified_lawyer_mou",
                    priority="high" if matched_offer else "normal",
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    trigger=intent,
                    trigger_message=inbound.body,
                    payload={
                        "referenced_buyer": referenced_buyer,
                        "matched_offer": bool(matched_offer),
                        "doc_requested": "conveyancing next steps / offer status",
                        "requested_action": "Verify authority and continue via proper conveyancing channels.",
                    },
                )

                if not matched_offer:
                    crud.create_suspicious_activity(
                        db=db,
                        listing_id=listing_id,
                        conversation_id=conv.conversation_id,
                        buyer_phone=inbound.from_number,
                        buyer_name=conv.buyer_name,
                        category="unverified_lawyer",
                        trigger_message=inbound.body,
                    )

                if self._should_suppress_non_offer_escalation(conv, escalation, db=db):
                    if self._response_promises_forwarding(bot_response):
                        bot_response = self._remove_unbacked_forwarding_claim(bot_response, conv)
                    return bot_response, None, None
                self._record_escalation_state(db, conv, escalation)
                return bot_response, escalation, None

            if self._detect_new_listing_inquiry(inbound.body):
                bot_response = (
                    "I've forwarded this to {managing_agent_name}. They'll follow up on this WhatsApp thread "
                    "about listing your unit and the seller-side process."
                )
                escalation = EscalationAlert(
                    escalation_type="general_lead_capture",
                    priority="normal",
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    trigger=intent,
                    trigger_message=inbound.body,
                    escalation_subtype="new_listing_inquiry",
                    payload={
                        "requested_action": "Owner wants to discuss listing their property.",
                        "question_digest": inbound.body,
                    },
                )
                bot_response, _ = self._finalize_response(bot_response, intent, conv, ctx=ctx)
                crud.add_message(
                    db,
                    conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value,
                    content=bot_response,
                )
                crud.update_conversation(db, conv)
                self._record_escalation_state(db, conv, escalation)
                return bot_response, escalation, None

            if intent == BuyerIntent.professional_inquiry:
                if is_form_a_request:
                    if self._detect_brn_only_request(inbound.body):
                        bot_response = (
                            "I've forwarded your BRN verification request to {managing_agent_name}. They'll "
                            "follow up on this WhatsApp thread with the correct registration "
                            "details."
                        )
                        escalation = EscalationAlert(
                            escalation_type="brn_request",
                            priority="normal",
                            conversation_id=conv.conversation_id,
                            listing_id=listing_id,
                            buyer_phone=inbound.from_number,
                            buyer_name=conv.buyer_name,
                            trigger=intent,
                            trigger_message=inbound.body,
                            escalation_subtype="brn_request",
                            payload={
                                "doc_requested": "BRN / RERA card verification",
                                "requested_action": "Send the correct agent registration details.",
                            },
                        )
                    else:
                        bot_response = (
                            "I've forwarded your request to {managing_agent_name}. They'll reach out directly "
                            "to send the Form A and listing authorization through proper "
                            "channels."
                        )
                        escalation = EscalationAlert(
                            escalation_type="general_lead_capture",
                            priority="normal",
                            conversation_id=conv.conversation_id,
                            listing_id=listing_id,
                            buyer_phone=inbound.from_number,
                            buyer_name=conv.buyer_name,
                            trigger=intent,
                            trigger_message=inbound.body,
                            escalation_subtype="co_broker_compliance",
                            payload={
                                "doc_requested": "Form A / listing authorization",
                                "requested_action": "Send formal listing authorization through the proper channel.",
                            },
                        )
                    bot_response, _ = self._finalize_response(bot_response, intent, conv, ctx=ctx)
                    crud.add_message(
                        db,
                        conversation_id=conv.conversation_id,
                        role=MessageRole.assistant.value,
                        content=bot_response,
                    )
                    crud.update_conversation(db, conv)
                    if self._should_suppress_non_offer_escalation(conv, escalation, db=db):
                        return bot_response, None, None
                    self._record_escalation_state(db, conv, escalation)
                    return bot_response, escalation, None

                return self._handle_professional_inquiry(
                    inbound, listing_id, db_listing, spa, conv, db, intent_data, ctx
                )

            if intent == BuyerIntent.bypass_attempt and not is_form_a_request:
                if is_document_disclosure_request or self._detect_seller_contact_request(inbound.body):
                    ask_count, used_lines, already_refusal_escalated = self._next_refusal_state(conv, SELLER_PII)
                    decision = render_refusal(
                        intent=SELLER_PII,
                        conv=conv,
                        managing_agent_name=ctx.managing_agent_name,
                        already_escalated=already_refusal_escalated or (conv.escalation_reason == f"bypass_attempt:{SELLER_PII}"),
                        ask_count_override=ask_count,
                        used_texts_override=used_lines,
                        language="ar" if self._is_arabic_text(inbound.body) else "en",
                    )
                    self._store_refusal_state(conv, SELLER_PII, decision)
                    bot_response = decision.text
                    refusal_class = SELLER_PII
                else:
                    ask_count, used_lines, already_refusal_escalated = self._next_refusal_state(conv, OUT_OF_SCOPE)
                    decision = render_refusal(
                        intent=OUT_OF_SCOPE,
                        conv=conv,
                        managing_agent_name=ctx.managing_agent_name,
                        already_escalated=already_refusal_escalated or (conv.escalation_reason == f"bypass_attempt:{OUT_OF_SCOPE}"),
                        ask_count_override=ask_count,
                        used_texts_override=used_lines,
                        language="ar" if self._is_arabic_text(inbound.body) else "en",
                    )
                    self._store_refusal_state(conv, OUT_OF_SCOPE, decision)
                    bot_response = decision.text
                    refusal_class = OUT_OF_SCOPE
                bot_response, _ = self._finalize_response(bot_response, intent, conv, ctx=ctx)
                crud.add_message(
                    db,
                    conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value,
                    content=bot_response,
                )
                crud.update_conversation(db, conv)
                crud.create_suspicious_activity(
                    db=db,
                    listing_id=listing_id,
                    conversation_id=conv.conversation_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    category="bypass_attempt",
                    trigger_message=inbound.body,
                    bot_response=bot_response,
                )
                logger.info(
                    "bypass_attempt listing=%s buyer=%s buyer_name=%s message=%r bot_response=%r",
                    listing_id, inbound.from_number, conv.buyer_name,
                    inbound.body[:200], bot_response[:200],
                )
                escalation = None
                if decision.should_escalate:
                    escalation = EscalationAlert(
                        escalation_type="bypass_attempt",
                        priority="normal",
                        conversation_id=conv.conversation_id,
                        listing_id=listing_id,
                        buyer_phone=inbound.from_number,
                        buyer_name=conv.buyer_name,
                        trigger=BuyerIntent.bypass_attempt,
                        trigger_message=inbound.body,
                        escalation_subtype=refusal_class,
                        payload={
                            "refusal_class": refusal_class,
                            "ask_count": decision.ask_count,
                            "requested_action": "Review repeated refusal probe; prohibited information was not disclosed.",
                        },
                    )
                    self._record_escalation_state(db, conv, escalation)
                return bot_response, escalation, None

            deterministic_response = None
            if self._detect_closing_message(inbound.body, conv):
                deterministic_response = self._compose_closing_signoff(inbound.body, conv)
            elif self._detect_religious_ruling_query(inbound.body):
                deterministic_response = (
                    "I can't make religious compliance rulings. A qualified Islamic scholar or Islamic finance advisor "
                    "should review the transaction structure if that matters to your decision. I can stick to factual "
                    "listing details like price, status, payment schedule, and transfer process."
                )
            elif self._detect_legal_advice_query(inbound.body):
                deterministic_response = (
                    "That is a legal-risk question, so I can't advise on court exposure or remedies. "
                    "A Dubai real estate lawyer should review the SPA and payment obligations before "
                    "you rely on any legal position. I can explain the public payment schedule and "
                    "transaction process, but not legal consequences."
                )
            elif self._detect_developer_quality_query(inbound.body):
                deterministic_response = self._compose_developer_quality_response(spa, db_listing)
            elif (
                self._detect_parking_query(inbound.body)
                and self._is_villa_or_townhouse(spa)
                and not self._is_multi_feature_question(inbound.body)
            ):
                deterministic_response = self._compose_villa_parking_response(spa)
            elif (
                self._should_answer_handover_deterministically(inbound.body)
                and self._is_off_plan(db_listing, spa)
            ):
                deterministic_response = self._compose_handover_response(spa, inbound.body)
            elif (
                self._detect_occupancy_query(inbound.body)
                and not self._is_off_plan(db_listing, spa)
            ):
                deterministic_response = self._compose_ready_tenancy_response(
                    db_listing, inbound.body
                )
            elif (
                self._detect_occupancy_query(inbound.body)
                and self._is_off_plan(db_listing, spa)
                and not self._is_multi_feature_question(inbound.body)
            ):
                deterministic_response = self._compose_offplan_occupancy_response(conv)
            elif (location_response := self._compose_location_lookup(db, db_listing, spa, inbound.body)):
                deterministic_response = location_response
            elif self._detect_total_fees_query(inbound.body):
                dld_fee_fact = self._direct_verified_fact_for_prompt(
                    "dld_registration_fee_pct",
                    brokerage_id=ctx.brokerage_id or db_listing.brokerage_id or conv.brokerage_id,
                )
                deterministic_response = self._compose_total_fees_response(
                    spa=spa,
                    seller_asking_price=seller_asking_price,
                    ctx=ctx,
                    property_type=db_listing.property_type,
                    language=intent_data.get("language_detected") or ("ar" if self._is_arabic_text(inbound.body) else "en"),
                    dld_fee_fact=dld_fee_fact,
                )
            elif self._detect_remaining_payment_query(inbound.body):
                deterministic_response = self._compose_remaining_payment_response(
                    spa,
                    property_type=db_listing.property_type,
                    seller_asking_price=seller_asking_price,
                    ctx=ctx,
                )
            elif self._detect_offplan_mortgage_query(inbound.body, db_listing, spa):
                mortgage_fact = self._direct_verified_fact_for_prompt(
                    "off_plan_mortgage_ltv_policy",
                    brokerage_id=ctx.brokerage_id or db_listing.brokerage_id or conv.brokerage_id,
                )
                deterministic_response = self._compose_offplan_mortgage_response(
                    asking_price=seller_asking_price if self._message_asks_price(inbound.body) else None,
                    verified_fact=mortgage_fact,
                )
            elif self._detect_affordability_query(inbound.body):
                monthly_income = self._extract_monthly_income_aed(inbound.body)
                if monthly_income:
                    deterministic_response = self._compose_affordability_response(
                        asking_price=db_listing.seller_asking_price or spa.purchase_price_aed,
                        monthly_income_aed=monthly_income,
                    )

            if deterministic_response:
                bot_response, validator_telemetry = self._finalize_response(
                    deterministic_response, intent, conv, ctx=ctx
                )
                if any(validator_telemetry.values()):
                    logger.info(
                        "response_validator listing=%s intent=%s telemetry=%s",
                        listing_id, intent.value if intent else "?", validator_telemetry,
                    )
                crud.add_message(
                    db,
                    conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value,
                    content=bot_response,
                )
                crud.update_conversation(db, conv)
                return bot_response, None, None

            gap_topics = self._missing_listing_fact_topics(db_listing, spa, inbound.body)
            if gap_topics:
                # Carry every unmet item the buyer asked, not just the first (DAL-88).
                if len(gap_topics) == 1:
                    topic_str = gap_topics[0]
                else:
                    topic_str = ", ".join(gap_topics[:-1]) + f", and {gap_topics[-1]}"
                bot_response, escalation = self._handle_deterministic_info_gap(
                    db=db,
                    conv=conv,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    intent=intent,
                    message=inbound.body,
                    topic=topic_str,
                    ctx=ctx,
                )
                return bot_response, escalation, None

            # Get message count for name-capture timing
            message_count = len(conv.messages)  # already includes the one we just added

            # ── Phase 9.10: Returning-buyer detection ────────────────────────
            # The detection regex is selective (matches explicit historic
            # references like "messaged a few weeks ago", "did you hear back",
            # "follow up on my", "remember me"). When a buyer references prior
            # contact at any point, surface OfferRecord history and route to
            # Eric. Don't gate on conversation length — same phone + same
            # listing may have prior conversation messages even on a "fresh"
            # interaction (test orchestrator preserves history; production
            # users continue the same DB conversation).
            returning_context = None
            if self._detect_returning_buyer_claim(inbound.body):
                # Don't re-fire if the conversation has already surfaced this
                # signal (i.e., a prior assistant message contained the
                # returning-buyer template phrasing).
                already_surfaced = any(
                    m.role == "assistant"
                    and m.content
                    and (
                        "prior offer of AED" in m.content
                        or "I don't have a record of a prior conversation on this unit" in m.content
                    )
                    for m in conv.messages
                )
                if not already_surfaced:
                    prior_offers = crud.get_all_offers_for_buyer_listing(
                        db,
                        buyer_phone=inbound.from_number,
                        listing_id=listing_id,
                    )
                    returning_context = {
                        "claim_text": inbound.body,
                        "prior_offers": prior_offers,
                    }

            # ── Phase 8.1: Compute offer flags BEFORE Claude call ────────────
            # We branch the response generation: above-threshold and marginal offers
            # get a deterministic acknowledgment template instead of risking Claude
            # generating below-threshold pushback wording (Sara T9: "still a bit short").
            asking_price_pre = db_listing.seller_asking_price or spa.purchase_price_aed
            threshold_pre = self._offer_threshold_aed(db_listing)
            offer_amount_pre = intent_data.get("extracted_offer_amount")
            if isinstance(offer_amount_pre, (int, float)):
                offer_amount_pre = float(offer_amount_pre)
            else:
                offer_amount_pre = None

            is_hypothetical_offer_query = self._is_hypothetical_offer_query(inbound.body)
            is_firm_pre = (
                bool(intent_data.get("is_firm_offer", False))
                or self._is_explicit_offer_submission(inbound.body)
            ) and not is_hypothetical_offer_query
            is_offer_pre = offer_amount_pre is not None and is_firm_pre and returning_context is None
            above_threshold_pre = is_offer_pre and (
                threshold_pre is None or offer_amount_pre >= threshold_pre
            )

            # Phase 9.3: Detect downward revision within this conversation.
            # If the current offer is BELOW the most recent prior offer from
            # this same buyer in this same conversation, the response should
            # push back firmer ("moving the wrong direction").
            is_downward_revision_pre = False
            prior_offer_amount_in_conv = None
            if is_offer_pre:
                prior_offer = crud.get_active_offer(db, inbound.from_number, listing_id)
                if (
                    prior_offer is not None
                    and prior_offer.conversation_id == conv.conversation_id
                    and prior_offer.offer_amount_aed > offer_amount_pre
                ):
                    is_downward_revision_pre = True
                    prior_offer_amount_in_conv = prior_offer.offer_amount_aed

            # Near-threshold band (Phase 10): the 5% window below the
            # notification threshold escalates with a tag but the buyer-facing
            # template falls through to Claude's graceful pushback — identical
            # buyer experience to a far-below offer. Only at-or-above offers
            # get the deterministic ack template.
            NEAR_THRESHOLD_BUFFER_PCT_PRE = 5.0
            near_threshold_floor_pre = (
                threshold_pre * (1 - NEAR_THRESHOLD_BUFFER_PCT_PRE / 100.0)
                if threshold_pre is not None else None
            )
            is_near_threshold_pre = (
                is_offer_pre
                and not above_threshold_pre
                and threshold_pre is not None
                and near_threshold_floor_pre is not None
                and offer_amount_pre >= near_threshold_floor_pre
            )
            # Backwards-compat alias for any code path still reading is_marginal_pre
            is_marginal_pre = is_near_threshold_pre

            # Engagement gate (substantive count) — needed for template selection
            gate_passes_pre, _ = self._engagement_gate_pass(intent_data, conv)

            # Phase 8.6 + Phase 10: Form A / RERA / Trakheesi document request → templated response
            # with proactive forwarding (we reach out to them, not the other way).
            # IMPORTANT (Phase 10): near-threshold offers DROP OUT of the ack
            # template — they fall through to Claude so the buyer sees the same
            # graceful pushback they'd see for a far-below offer. Escalation
            # still fires for near-threshold offers (see should_escalate below).
            # R20: a buyer restating an offer that's already on record should be told
            # it's already placed — not "I'll forward it to the seller" as if new.
            prior_active_offer = (
                crud.get_active_offer(db, inbound.from_number, listing_id)
                if is_offer_pre else None
            )
            use_restated_offer_template = bool(
                is_offer_pre
                and above_threshold_pre
                and prior_active_offer is not None
                and offer_amount_pre is not None
                and abs((prior_active_offer.offer_amount_aed or 0) - offer_amount_pre) < 1000
            )
            use_offer_template = is_offer_pre and above_threshold_pre and not use_restated_offer_template
            use_above_threshold_pre_engagement_template = False
            use_hypothetical_above_asking_template = (
                offer_amount_pre is not None
                and not is_firm_pre
                and offer_amount_pre >= asking_price_pre
            )
            # Phase 9.10: Returning-buyer with detected claim → deterministic template.
            # Use template even if conv has prior escalations — those were for
            # different signals (offer, etc); the returning-buyer continuity
            # claim deserves its own deterministic acknowledgment. The
            # `already_surfaced` check above prevents double-firing within the
            # same conversation.
            use_returning_buyer_template = returning_context is not None
            # Phase 9.6: BRN-only requests get a distinct template from Form A
            use_brn_template = is_form_a_request and self._detect_brn_only_request(inbound.body)
            use_below_threshold_spam_template = (
                is_offer_pre
                and not above_threshold_pre
                and not is_marginal_pre
                and self._is_transactional_demand(inbound.body)
                and not self._is_substantive_message(inbound.body)
            )
            use_template_response = (
                use_offer_template
                or use_restated_offer_template
                or use_below_threshold_spam_template
                or use_hypothetical_above_asking_template
                or is_form_a_request
                or use_returning_buyer_template
            )

            if use_template_response:
                # Phase 8.1 / 8.6 / 9.10: Skip Claude. Use deterministic template.
                if use_restated_offer_template:
                    bot_response = (
                        f"That offer of AED {offer_amount_pre:,.0f} is already on record with "
                        "{managing_agent_name} from earlier — you don't need to resubmit it. "
                        "I'll follow up on where the seller stands and come back to you."
                    )
                    logger.info(
                        "phase910_restated_offer_template listing=%s buyer=%s offer=%s",
                        listing_id, inbound.from_number, offer_amount_pre,
                    )
                elif use_returning_buyer_template:
                    bot_response = self._returning_buyer_template(
                        returning_context,
                        conv,
                        ctx.managing_agent_name,
                    )
                    logger.info(
                        "phase910_returning_buyer_template listing=%s buyer=%s prior_offers=%d",
                        listing_id, inbound.from_number,
                        len(returning_context["prior_offers"]),
                    )
                elif use_offer_template:
                    bot_response = self._above_threshold_template(
                        offer_amount_pre, intent_data, conv, buyer_profile
                    )
                    logger.info(
                        "phase81_template_response listing=%s buyer=%s offer=%s above=%s marg=%s gate=%s",
                        listing_id, inbound.from_number, offer_amount_pre,
                        above_threshold_pre, is_marginal_pre, gate_passes_pre,
                    )
                elif use_above_threshold_pre_engagement_template:
                    bot_response = self._above_threshold_pre_engagement_template(
                        offer_amount_pre, intent_data
                    )
                    logger.info(
                        "above_threshold_pre_engagement_template listing=%s buyer=%s offer=%s",
                        listing_id, inbound.from_number, offer_amount_pre,
                    )
                elif use_below_threshold_spam_template:
                    bot_response = (
                        f"AED {offer_amount_pre:,.0f} is below where the seller is likely "
                        "to engage. If you want me to log a serious offer, send your "
                        "strongest number."
                    )
                    logger.info(
                        "below_threshold_spam_template listing=%s buyer=%s offer=%s threshold=%s",
                        listing_id, inbound.from_number, offer_amount_pre, threshold_pre,
                    )
                elif use_hypothetical_above_asking_template:
                    bot_response = (
                        f"AED {offer_amount_pre:,.0f} is above the asking price of "
                        f"AED {asking_price_pre:,.0f}. If you want to submit that "
                        "formally, confirm the offer amount and I'll record it for {managing_agent_name}."
                    )
                    logger.info(
                        "hypothetical_above_asking_template listing=%s buyer=%s amount=%s asking=%s",
                        listing_id, inbound.from_number, offer_amount_pre, asking_price_pre,
                    )
                elif use_brn_template:
                    bot_response = (
                        "I've forwarded your BRN verification request to {managing_agent_name}. They'll "
                        "follow up on this WhatsApp thread with the correct registration "
                        "details."
                    )
                    logger.info(
                        "phase96_brn_template listing=%s buyer=%s",
                        listing_id, inbound.from_number,
                    )
                else:  # is_form_a_request (non-BRN)
                    bot_response = (
                        "I've forwarded your request to {managing_agent_name}. They'll reach out directly "
                        "to send the Form A and listing authorization through proper "
                        "channels."
                    )
                    logger.info(
                        "phase86_form_a_template listing=%s buyer=%s",
                        listing_id, inbound.from_number,
                    )
                bot_response, validator_telemetry = self._finalize_response(bot_response, intent, conv, ctx=ctx)
            else:
                from app.core.buyer_preferences import should_surface_alternative_listings

                surface_alternatives = (
                    should_surface_alternative_listings(inbound.body)
                    or self._detect_portfolio_list_request(inbound.body)
                )
                # Find cross-listing recommendations (preference-based)
                matching_listings = (
                    self.find_matching_listings(
                        buyer_profile=buyer_profile,
                        current_listing_id=listing_id,
                        db=db,
                    )
                    if surface_alternatives
                    else []
                )

                # Only expose alternative inventory when the buyer asks or
                # signals mismatch; this avoids suggestion spam.
                all_other = (
                    self._rank_portfolio_brief(self._get_all_other_listings(listing_id, db))
                    if surface_alternatives else []
                )

                if self._detect_portfolio_list_request(inbound.body) and all_other:
                    limit = self._requested_listing_limit(inbound.body)
                    if limit is not None:
                        all_other = all_other[:limit]
                    bot_response = self._compose_portfolio_list_response(
                        all_other,
                        requested_limit=limit,
                    )
                    bot_response, validator_telemetry = self._finalize_response(bot_response, intent, conv, ctx=ctx)
                    media_urls = list(db_listing.media_urls or [])
                    logger.info(
                        "single_listing_portfolio_list listing=%s buyer=%s count=%d",
                        listing_id, inbound.from_number, len(all_other),
                    )
                    use_template_response = True
                    matching_listings = []
                    all_other = []
                    system_prompt = None
                    claude_messages = []
                else:

                    # Load media URLs for this listing
                    media_urls = list(db_listing.media_urls or [])

                # Resolve agent private notes for this community (visible
                # only when this listing's assigned_agent_id matches the note's
                # owner — enforced by the query).
                    agent_private_notes = []
                    if db_listing.community and db_listing.assigned_agent_id and db_listing.brokerage_id:
                        from app.models.db_models import DBAgentCommunityRemark
                        rows = (
                            db.query(DBAgentCommunityRemark)
                            .filter(
                                DBAgentCommunityRemark.brokerage_id == db_listing.brokerage_id,
                                DBAgentCommunityRemark.agent_user_id == db_listing.assigned_agent_id,
                                DBAgentCommunityRemark.community_key == db_listing.community,
                            )
                            .all()
                        )
                        agent_private_notes = [r.body for r in rows if r.body]

                    # Agent-verified per-field corrections to this project's community research.
                    agent_community_overrides = []
                    if db_listing.assigned_agent_id and db_listing.brokerage_id:
                        from app.core.agent_community_overrides import (
                            overrides_for_prompt,
                            project_key_from_name,
                            project_name_for_listing,
                        )
                        _project_key = project_key_from_name(project_name_for_listing(db_listing))
                        if _project_key:
                            agent_community_overrides = overrides_for_prompt(
                                db,
                                brokerage_id=db_listing.brokerage_id,
                                agent_user_id=db_listing.assigned_agent_id,
                                project_key=_project_key,
                            )

                    listing_amenities, listing_anchor_times = latest_listing_enrichment(db, listing_id)

                    from app.core.ready_property_knowledge import ready_property_knowledge_for_prompt

                    readiness_next_question = self._deal_readiness_next_question_for_prompt(
                        db,
                        brokerage_id=ctx.brokerage_id or db_listing.brokerage_id or conv.brokerage_id,
                        buyer_phone=inbound.from_number,
                        intent=intent,
                        fallback_budget_aed=conv.detected_budget,
                        listing_id=listing_id,
                    )
                    verified_facts_grounding = self._verified_facts_grounding_for_prompt(
                        inbound.body,
                        brokerage_id=ctx.brokerage_id or db_listing.brokerage_id or conv.brokerage_id,
                    )
                    dld_fee_fact = self._direct_verified_fact_for_prompt(
                        "dld_registration_fee_pct",
                        brokerage_id=ctx.brokerage_id or db_listing.brokerage_id or conv.brokerage_id,
                    )
                    dld_fee_pct = self._percentage_from_verified_fact(dld_fee_fact)
                    dld_fee_source = self._source_label_for_verified_fact(dld_fee_fact)

                    # Build system prompt
                    system_prompt = build_system_prompt(
                        spa=spa,
                        community_data=community,
                        seller_asking_price=seller_asking_price,
                        seller_notes=seller_notes,
                        buyer_profile=buyer_profile,
                        message_count=message_count,
                        seller_qa=seller_qa,
                        matching_listings=matching_listings,
                        all_other_listings=all_other,
                        media_urls=media_urls,
                        seller_phone=getattr(db_listing, 'seller_phone', None),
                        buyer_phone=inbound.from_number,
                        downward_revision_context=(
                            {
                                "current_offer": offer_amount_pre,
                                "prior_offer": prior_offer_amount_in_conv,
                            }
                            if is_downward_revision_pre else None
                        ),
                        # Multi-tenant context
                        brokerage_name=ctx.brokerage_name,
                        brokerage_short=ctx.brokerage_short,
                        brokerage_arabic=ctx.brokerage_arabic,
                        managing_agent_name=ctx.managing_agent_name,
                        managing_agent_title=ctx.managing_agent_title,
                        commission_rate=ctx.commission_rate,
                        market_benchmark_rate=ctx.market_benchmark_rate,
                        dashboard_url=ctx.dashboard_url,
                        property_type=db_listing.property_type or "off_plan",
                        agent_private_notes=agent_private_notes or None,
                        agent_community_overrides=agent_community_overrides or None,
                        unit_profile=db_listing.unit_profile or None,
                        reference_documents=list(db_listing.reference_documents or []) or None,
                        ready_property_knowledge=ready_property_knowledge_for_prompt(db, listing_id),
                        additional_fees=list(db_listing.additional_fees or []) or None,
                        listing_amenities=listing_amenities or None,
                        listing_anchor_times=listing_anchor_times or None,
                        readiness_next_question=readiness_next_question,
                        latest_buyer_message=inbound.body,
                        verified_facts_grounding=verified_facts_grounding,
                        dld_transfer_fee_pct=dld_fee_pct,
                        dld_transfer_fee_source=dld_fee_source,
                    )

                    # Build conversation history for Claude (last 20 messages).
                    # Phase 7.6.11: filter out prior regulatory-request turns so PDPL/GDPR
                    # state from earlier interactions does not bleed into the buyer-mode
                    # prompt and cause Claude to fabricate compliance status.
                    recent_messages = conv.messages[-20:]
                    claude_messages = []
                    skip_next_assistant = False
                    for msg in recent_messages[:-1]:  # exclude the message we just added
                        if skip_next_assistant and msg.role == "assistant":
                            skip_next_assistant = False
                            continue
                        if (
                            msg.role == "user"
                            and msg.intent == BuyerIntent.regulatory_request.value
                        ):
                            skip_next_assistant = True
                            continue
                        claude_messages.append({"role": msg.role, "content": msg.content})
                    claude_messages.append({"role": "user", "content": inbound.body})

                    # Call Claude with prompt caching — system prompt is identical across messages
                    # for the same listing, so cache_control saves ~90% of input token costs
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=512,
                        system=[{
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }],
                        messages=claude_messages,
                    )

                    bot_response = response.content[0].text.strip()
                    bot_response, validator_telemetry = self._finalize_response(bot_response, intent, conv, ctx=ctx)

            if any(validator_telemetry.values()):
                logger.info(
                    "response_validator listing=%s intent=%s telemetry=%s",
                    listing_id, intent.value if intent else "?", validator_telemetry,
                )

            if (
                self._is_hypothetical_offer_query(inbound.body)
                and self._response_promises_forwarding(bot_response)
            ):
                bot_response = self._remove_unbacked_forwarding_claim(bot_response, conv)
                logger.info(
                    "phase810_forwarding_promise_removed_hypothetical_offer listing=%s buyer=%s",
                    listing_id, inbound.from_number,
                )

            # media_urls may not have been loaded if we used template path; ensure defined
            if 'media_urls' not in locals():
                media_urls = list(db_listing.media_urls or [])

            # ── Auto-send media if bot offers renders/floor plans ─────────
            send_media_url = None
            if media_urls and "send you" in bot_response.lower():
                send_media_url = media_urls[0]

            # Persist bot response
            crud.add_message(
                db,
                conversation_id=conv.conversation_id,
                role=MessageRole.assistant.value,
                content=bot_response,
            )

            crud.update_conversation(db, conv)  # bumps updated_at

            # ── Escalation logic ───────────────────────────────────────────
            escalation = None
            asking_price = db_listing.seller_asking_price or spa.purchase_price_aed
            threshold = self._offer_threshold_aed(db_listing)
            offer_amount = intent_data.get("extracted_offer_amount")
            if isinstance(offer_amount, (int, float)):
                offer_amount = float(offer_amount)
            else:
                offer_amount = None

            # Unanswerable question: forward to Eric immediately
            is_unanswerable = intent_data.get("is_unanswerable", False)
            if (
                not is_unanswerable
                and self._detect_listing_fact_gap_request(inbound.body)
                and self._response_signals_info_gap(bot_response)
            ):
                is_unanswerable = True

            # ── Offer handling: store record + decide escalation ───────────
            # Phase 7.1: Detect offer regardless of intent label. is_firm_offer gates
            # hypotheticals ("if I offered X") from real escalation. This lets co-broker
            # offers with a concrete buyer amount escalate even when intent classifies
            # as professional_inquiry.
            is_firm_offer = (
                bool(intent_data.get("is_firm_offer", False))
                or self._is_explicit_offer_submission(inbound.body)
            ) and not is_hypothetical_offer_query
            is_offer = offer_amount is not None and is_firm_offer and returning_context is None
            above_threshold = is_offer and (threshold is None or offer_amount >= threshold)

            # Phase 7.2: Marginal offers within MARGINAL_BUFFER_PCT below threshold
            # escalate with is_marginal=True. The buyer-facing response stays on
            # the graceful below-threshold path; the agent alert flags the gap.
            MARGINAL_BUFFER_PCT = 5.0
            marginal_floor = (
                threshold * (1 - MARGINAL_BUFFER_PCT / 100.0)
                if threshold is not None else None
            )
            is_marginal = (
                is_offer
                and not above_threshold
                and threshold is not None
                and marginal_floor is not None
                and offer_amount >= marginal_floor
            )

            # Re-escalation guard: look up prior active offer from this buyer
            prev_db_offer = None
            prev_offer = None
            if is_offer:
                prev_db_offer = crud.get_active_offer(db, inbound.from_number, listing_id)
                if prev_db_offer:
                    prev_offer = prev_db_offer.offer_amount_aed

            time_elapsed = (
                conv.last_escalated_at is None
                or (datetime.utcnow() - conv.last_escalated_at) >= timedelta(hours=24)
            )
            no_prior = prev_offer is None
            higher_offer = (
                prev_offer is not None
                and offer_amount is not None
                and offer_amount > prev_offer
            )
            # R20: an exact restatement of an already-recorded offer is not a new
            # offer — don't re-escalate it.
            is_exact_restatement = (
                prev_offer is not None
                and offer_amount is not None
                and abs(prev_offer - offer_amount) < 1000
                and conv.escalation_triggered
            )

            # Decide escalation and reason string for logging
            gate_passes_offer, gate_suppression_reason = self._engagement_gate_pass(intent_data, conv)
            low_engagement_offer = bool(above_threshold and not gate_passes_offer)
            should_escalate = bool(above_threshold or is_marginal)
            if not is_offer:
                decision_reason = "not_an_offer"
                should_escalate_offer = False
            elif offer_amount is None:
                decision_reason = "no_amount"
                should_escalate_offer = False
            elif is_exact_restatement:
                decision_reason = "suppressed_exact_offer_restatement"
                should_escalate_offer = False
            elif not should_escalate:
                decision_reason = gate_suppression_reason or "below_threshold"
                should_escalate_offer = False
            elif low_engagement_offer:
                # R5: zero-context spam (transactional demand, no real engagement)
                # is stored for the data moat but must NOT escalate.
                if self._is_transactional_demand(inbound.body):
                    decision_reason = "suppressed_zero_context_spam_offer"
                    should_escalate_offer = False
                else:
                    decision_reason = "escalated_low_engagement_offer"
                    should_escalate_offer = True
            elif no_prior:
                decision_reason = "escalated_marginal_first_offer" if is_marginal else "escalated_first_offer"
                should_escalate_offer = True
            elif higher_offer:
                decision_reason = "escalated_marginal_higher_offer" if is_marginal else "escalated_higher_offer"
                should_escalate_offer = True
            elif time_elapsed:
                decision_reason = "escalated_marginal_after_24h" if is_marginal else "escalated_after_24h"
                should_escalate_offer = True
            else:
                decision_reason = "escalated_marginal_above_threshold_repeat" if is_marginal else "escalated_above_threshold_repeat"
                should_escalate_offer = True

            logger.info(
                "escalation_decision listing=%s buyer=%s intent=%s offer=%s threshold=%s "
                "above=%s marginal=%s prior_offer=%s decision=%s reason=%s",
                listing_id, inbound.from_number, intent.value, offer_amount, threshold,
                above_threshold, is_marginal, prev_offer, should_escalate_offer, decision_reason,
            )

            # Persist OfferRecord for every detected offer (audit trail)
            if is_offer:
                turn_number = len(conv.messages)
                # Phase 7.2: marginal flag rolls into above_threshold for OfferRecord
                # storage purposes (we want these visible in seller dashboard as
                # forwarded offers). The Eric-facing alert separately surfaces the
                # marginal caveat.
                new_offer_record = crud.create_offer_record(
                    db=db,
                    listing_id=listing_id,
                    conversation_id=conv.conversation_id,
                    buyer_phone=inbound.from_number,
                    offer_amount_aed=offer_amount,
                    asking_price_aed=asking_price,
                    above_threshold=above_threshold or is_marginal,
                    escalated=should_escalate_offer,
                    escalation_reason=decision_reason,
                    threshold_aed=threshold,
                    buyer_name=conv.buyer_name,
                    raw_message=inbound.body,
                    language_detected=intent_data.get("language_detected"),
                    turn_number=turn_number,
                )
                # Mark prior active offer as superseded by this new one
                if prev_db_offer:
                    crud.supersede_offer(db, prev_db_offer.offer_id, new_offer_record.offer_id)

            if should_escalate_offer:
                crud.update_conversation(
                    db, conv,
                    escalation_triggered=True,
                    escalation_reason=f"offer:{offer_amount}",
                    last_escalated_at=datetime.utcnow(),
                )
                db.refresh(conv)
                state = crud.db_conv_to_state(conv)
                summary = self._summarise_conversation(
                    state, spa,
                    asking_price_aed=asking_price,
                    offer_amount_aed=offer_amount,
                )

                # Multi-offer chain: prepend revision history when buyer has
                # submitted 2+ offers on this listing within 24 hours.
                prior_offers = crud.get_recent_offers_in_chain(
                    db, buyer_phone=inbound.from_number, listing_id=listing_id, hours=24
                )  # returns list ordered by created_at ascending; current new_offer_record IS included
                if len(prior_offers) >= 2:
                    chain_text = " → ".join(f"AED {o.offer_amount_aed:,.0f}" for o in prior_offers)
                    revision_prefix = f"[REVISED OFFER] Buyer revised offer upward: {chain_text}.\n\n"
                    summary = revision_prefix + summary
                    # TODO: future — Telegram edit-in-place rather than re-send

                # Phase 7.2: Marginal offers carry caveat fields so the agent alert
                # explicitly flags the under-threshold gap.
                marginal_gap_aed = (threshold - offer_amount) if (is_marginal and threshold) else None
                marginal_gap_pct = (
                    (threshold - offer_amount) / threshold * 100.0
                    if (is_marginal and threshold) else None
                )
                escalation = EscalationAlert(
                    escalation_type=EscalationType.offer.value,
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    trigger=intent,
                    trigger_message=inbound.body,
                    offer_amount_aed=offer_amount,
                    listing_price_aed=asking_price,
                    negotiation_threshold_aed=threshold,
                    is_marginal=is_marginal,
                    marginal_gap_aed=marginal_gap_aed,
                    marginal_gap_pct=marginal_gap_pct,
                        priority="normal" if (is_marginal or low_engagement_offer) else "high",
                        conversation_summary=summary,
                        payload={
                            "amount_aed": offer_amount,
                        "percent_of_asking": (
                            round(offer_amount / asking_price * 100, 1)
                            if asking_price else None
                        ),
                            "floor_aed": threshold,
                            "vs_floor_aed": (
                                offer_amount - threshold
                                if threshold is not None else None
                            ),
                            "buyer_ref": conv.buyer_name or inbound.from_number,
                            "engagement_gate_passed": gate_passes_offer,
                            "quality_flags": (
                                ["low_engagement", "no_specific_questions_asked"]
                                if low_engagement_offer else []
                            ),
                        },
                    )

            is_qualified_handoff = (
                (
                    intent in {BuyerIntent.speak_to_human, BuyerIntent.viewing_request}
                    or self._detect_viewing_request(inbound.body)
                )
                and self._is_qualified_human_request(inbound.body)
            )
            if is_unanswerable or is_qualified_handoff:
                alerted = list(conv.alerted_questions or [])

                # Skip if this exact question has already been sent to Eric
                trigger_text = inbound.body or "Buyer requested to speak with a human"
                if trigger_text not in alerted:
                    pending = list(conv.pending_forwarded_questions or [])
                    pending.append(trigger_text)
                    conv.pending_forwarded_questions = pending
                    safe_commit(db)

                    # Phase 7.8: Single pending question shouldn't carry a "1." prefix.
                    # Numbered formatting only applies when multiple are queued.
                    if len(pending) == 1:
                        trigger_msg_text = pending[0]
                    else:
                        trigger_msg_text = "\n".join(
                            f"{i+1}. {q}" for i, q in enumerate(pending)
                        )
                    is_viewing_request = (
                        intent == BuyerIntent.viewing_request
                        or self._detect_viewing_request(inbound.body)
                    )
                    is_ready_listing = (
                        (db_listing.property_type or "").lower() == "ready"
                        or (spa.property_status or "").lower() in {"ready", "completed", "complete", "handed over"}
                    )
                    if is_unanswerable:
                        escalation_type = "info_gap"
                        subtype = "listing_fact_gap"
                        payload = {
                            "question": trigger_msg_text,
                            "requested_action": "Confirm the missing listing fact and reply to the buyer.",
                        }
                    elif is_viewing_request and is_ready_listing:
                        escalation_type = "viewing_schedule"
                        subtype = "physical_viewing"
                        payload = {
                            "date_requested": self._extract_viewing_date_hint(inbound.body),
                            "requested_action": "Coordinate a physical viewing for the ready unit.",
                        }
                    elif is_viewing_request:
                        escalation_type = "materials_request"
                        subtype = "off_plan_materials"
                        payload = {
                            "materials": ["floor_plan", "renders", "brochure"],
                            "requested_action": "Send off-plan floor plans, renders, or brochure instead of scheduling a physical viewing.",
                        }
                    else:
                        escalation_type = "general_lead_capture"
                        subtype = "qualified_handoff"
                        payload = {"requested_action": "Follow up with the buyer on this request."}

                    escalation = EscalationAlert(
                        escalation_type=escalation_type,
                        conversation_id=conv.conversation_id,
                        listing_id=listing_id,
                        buyer_phone=inbound.from_number,
                        buyer_name=conv.buyer_name,
                        trigger=intent,
                        trigger_message=trigger_msg_text,
                        escalation_subtype=subtype,
                        payload=payload,
                    )

            # Phase 7.6.7c: existing-owner-pivots-to-seller signal. Fire a
            # general_lead_capture escalation so Eric can reach out for the
            # seller-acquisition conversation.
            if escalation is None and self._detect_new_listing_inquiry(inbound.body):
                escalation = EscalationAlert(
                    escalation_type="general_lead_capture",
                    priority="normal",
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    trigger=intent,
                    trigger_message=inbound.body,
                    escalation_subtype="new_listing_inquiry",
                    payload={
                        "requested_action": "Owner wants to discuss listing their property.",
                        "question_digest": inbound.body,
                    },
                )

            # Phase 8.6: Form A / RERA / co-broker compliance signals fire escalation
            # regardless of intent (classifier may route them to bypass_attempt or
            # general_enquiry; we still want Eric alerted for the documentation request).
            # Phase 9.6: BRN-only requests get a distinct escalation type from Form A.
            if escalation is None and is_form_a_request:
                if self._detect_brn_only_request(inbound.body):
                    escalation = EscalationAlert(
                        escalation_type="brn_request",
                        priority="normal",
                        conversation_id=conv.conversation_id,
                        listing_id=listing_id,
                        buyer_phone=inbound.from_number,
                        buyer_name=conv.buyer_name,
                        trigger=intent,
                        trigger_message=inbound.body,
                        escalation_subtype="brn_request",
                        payload={
                            "doc_requested": "BRN / RERA card verification",
                            "requested_action": "Send the correct agent registration details.",
                        },
                    )
                else:
                    escalation = EscalationAlert(
                        escalation_type="general_lead_capture",
                        priority="normal",
                        conversation_id=conv.conversation_id,
                        listing_id=listing_id,
                        buyer_phone=inbound.from_number,
                        buyer_name=conv.buyer_name,
                        trigger=intent,
                        trigger_message=inbound.body,
                        escalation_subtype="co_broker_compliance",
                        payload={
                            "doc_requested": "Form A / listing authorization",
                            "requested_action": "Send formal listing authorization through the proper channel.",
                        },
                    )

            # Phase 9.10: Returning-buyer follow-up — fire on T1/T2 if the buyer
            # references prior context and we have OfferRecord history (or they
            # claim they do; we forward either way so Eric can verify).
            if escalation is None and returning_context is not None:
                prior_offers_list = returning_context["prior_offers"]
                latest_prior = prior_offers_list[-1] if prior_offers_list else None
                escalation = EscalationAlert(
                    escalation_type="returning_buyer_followup",
                    priority="normal",
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    trigger=intent,
                    trigger_message=inbound.body,
                    offer_amount_aed=(latest_prior.offer_amount_aed if latest_prior else None),
                    listing_price_aed=asking_price_pre,
                    escalation_subtype=(
                        "returning_buyer_with_prior_offer" if latest_prior
                        else "returning_buyer_no_record"
                    ),
                    payload={
                        "claim_text": inbound.body,
                        "prior_offer_count": len(prior_offers_list),
                        "latest_prior_offer_aed": (
                            latest_prior.offer_amount_aed if latest_prior else None
                        ),
                    },
                )
                logger.info(
                    "phase910_returning_buyer listing=%s buyer=%s prior_offers=%d",
                    listing_id, inbound.from_number, len(prior_offers_list),
                )

            # Phase 8.5: Soft-offer detection — buyer floated an amount earlier
            # (often hypothetically) and is now stepping away. Capture as a warm lead
            # so Eric can follow up directly.
            if escalation is None:
                soft_offer_amount = self._detect_soft_offer_pause(conv, inbound.body)
                if soft_offer_amount is not None:
                    is_soft_above_asking = soft_offer_amount >= asking_price_pre
                    is_soft_above_threshold = (
                        threshold_pre is not None
                        and soft_offer_amount >= threshold_pre
                    )
                    escalation = EscalationAlert(
                        escalation_type="soft_offer",
                        priority="normal",
                        conversation_id=conv.conversation_id,
                        listing_id=listing_id,
                        buyer_phone=inbound.from_number,
                        buyer_name=conv.buyer_name,
                        trigger=intent,
                        trigger_message=inbound.body,
                        offer_amount_aed=soft_offer_amount,
                        listing_price_aed=asking_price_pre,
                        negotiation_threshold_aed=threshold_pre,
                        escalation_subtype=(
                            "soft_offer_above_asking" if is_soft_above_asking
                            else ("soft_offer_above_threshold" if is_soft_above_threshold
                                  else "soft_offer_below_threshold")
                        ),
                        payload={
                            "amount_aed": soft_offer_amount,
                            "percent_of_asking": (
                                round(soft_offer_amount / asking_price_pre * 100, 1)
                                if asking_price_pre else None
                            ),
                            "floor_aed": threshold_pre,
                            "vs_floor_aed": (
                                soft_offer_amount - threshold_pre
                                if threshold_pre is not None else None
                            ),
                            "buyer_ref": conv.buyer_name or inbound.from_number,
                        },
                    )
                    logger.info(
                        "phase85_soft_offer_detected listing=%s buyer=%s amount=%s above_asking=%s",
                        listing_id, inbound.from_number, soft_offer_amount, is_soft_above_asking,
                    )

            # Run 7: if the buyer-facing answer says floor plans/renders/brochure
            # can be sent, create an actionable info_gap alert so a human or
            # media route actually delivers the materials.
            if escalation is None and self._response_promises_materials(bot_response):
                escalation = EscalationAlert(
                    escalation_type="info_gap",
                    priority="normal",
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    trigger=intent,
                    trigger_message=inbound.body,
                    escalation_subtype="materials_request",
                    payload={
                        "materials": ["floor_plan", "renders", "brochure"],
                        "requested_action": "Send the promised floor plans, renders, brochure, or listing media to the buyer.",
                        "question_digest": inbound.body,
                    },
                )

            # Phase 8.10: If the bot promised to forward to Eric but no escalation fired,
            # ensure one fires. The bot's word should match the system's action.
            # Phase 9.5: But suppress when the engagement gate hasn't passed —
            # zero-context spammers (FastCash) shouldn't trigger Eric alerts even
            # if Claude said "I'll route" conditionally on a hypothetical.
            if escalation is None and self._response_promises_forwarding(bot_response):
                if self._is_non_actionable_deflection(inbound.body, bot_response):
                    bot_response = self._rewrite_non_actionable_deflection(bot_response, ctx)
                    logger.info(
                        "non_actionable_deflection_not_escalated listing=%s buyer=%s",
                        listing_id, inbound.from_number,
                    )
                    gate_ok = False
                elif self._is_hypothetical_offer_query(inbound.body):
                    bot_response = self._remove_unbacked_forwarding_claim(bot_response, conv)
                    logger.info(
                        "phase810_forwarding_promise_removed_hypothetical_offer listing=%s buyer=%s",
                        listing_id, inbound.from_number,
                    )
                    gate_ok = False
                else:
                    gate_ok, _ = self._engagement_gate_pass(intent_data, conv)
                if gate_ok:
                    escalation = EscalationAlert(
                        escalation_type="general_lead_capture",
                        priority="normal",
                        conversation_id=conv.conversation_id,
                        listing_id=listing_id,
                        buyer_phone=inbound.from_number,
                        buyer_name=conv.buyer_name,
                        trigger=intent,
                        trigger_message=inbound.body,
                        escalation_subtype="promise_kept",
                        payload={
                            "requested_action": "Follow up because the buyer-facing reply promised a handoff.",
                            "question_digest": inbound.body,
                        },
                    )
                else:
                    bot_response = self._remove_unbacked_forwarding_claim(bot_response, conv)
                    logger.info(
                        "phase95_promise_kept_suppressed_pre_engagement listing=%s buyer=%s",
                        listing_id, inbound.from_number,
                    )
                logger.info(
                    "phase810_forwarding_promise_kept listing=%s buyer=%s",
                    listing_id, inbound.from_number,
                )

            if escalation is not None and escalation.escalation_type != "offer":
                if self._should_suppress_non_offer_escalation(conv, escalation, db=db):
                    if self._response_promises_forwarding(bot_response):
                        bot_response = self._remove_unbacked_forwarding_claim(bot_response, conv)
                    logger.info(
                        "non_offer_escalation_suppressed listing=%s buyer=%s type=%s subtype=%s",
                        listing_id, inbound.from_number,
                        escalation.escalation_type, escalation.escalation_subtype,
                    )
                    escalation = None
                else:
                    self._record_escalation_state(db, conv, escalation)

        return bot_response, escalation, send_media_url

    # ── All other listings (for system prompt awareness) ─────────────────────

    @staticmethod
    def _offer_threshold_aed(db_listing) -> Optional[float]:
        """Canonical floor for offer routing.

        `notification_threshold_aed` is what the seller/report displays as the
        offer floor. `negotiation_threshold_aed` remains as a legacy alias for
        older rows, but must not override the displayed floor.
        """
        if not db_listing:
            return None
        threshold = getattr(db_listing, "notification_threshold_aed", None)
        if threshold is None:
            threshold = getattr(db_listing, "negotiation_threshold_aed", None)
        return float(threshold) if threshold is not None else None

    @staticmethod
    def _deal_readiness_next_question_for_prompt(
        db,
        *,
        brokerage_id: Optional[str],
        buyer_phone: Optional[str],
        intent: BuyerIntent,
        fallback_budget_aed: Optional[float],
        listing_id: Optional[str],
    ) -> Optional[str]:
        """Compute one optional qualification question without writing profile state."""
        if not brokerage_id or not buyer_phone:
            return None

        try:
            from app.core.buyer_profiles import effective_fields
            from app.core.deal_readiness import compute_readiness, fields_from_effective_fields
            from app.models.db_models import DBBrokerageBuyerProfile

            profile = (
                db.query(DBBrokerageBuyerProfile)
                .filter(
                    DBBrokerageBuyerProfile.brokerage_id == brokerage_id,
                    DBBrokerageBuyerProfile.buyer_phone == buyer_phone,
                )
                .first()
            )
            if profile is None:
                return None

            readiness_fields = fields_from_effective_fields(
                effective_fields(db, profile),
                fallback_budget_aed=fallback_budget_aed,
            )
            viewing_intent = intent is BuyerIntent.viewing_request
            offer_intent = intent in {
                BuyerIntent.offer_submission,
                BuyerIntent.price_negotiation,
            }
            if not readiness_fields and not viewing_intent and not offer_intent:
                return None

            readiness = compute_readiness(
                readiness_fields,
                conversation_ctx={
                    "viewing_intent": viewing_intent,
                    "offer_intent": offer_intent,
                },
                listing_ctx={"listing_id": listing_id} if listing_id else None,
            )
            return readiness.next_best_question
        except Exception:  # pragma: no cover - readiness planning must not break chat
            logger.warning("Deal readiness next-question planning failed", exc_info=True)
            return None

    @staticmethod
    def _direct_verified_fact_for_prompt(
        key: str,
        *,
        brokerage_id: Optional[str],
    ):
        """Return an active direct Verified Fact, or None to fail closed."""
        try:
            from app.core.verified_facts import default_verified_fact_registry, direct_fact_for_key

            return direct_fact_for_key(
                default_verified_fact_registry(),
                key,
                brokerage_id=brokerage_id,
            )
        except Exception:  # pragma: no cover - fact grounding must not break chat
            logger.warning("Verified Facts direct lookup failed", exc_info=True)
            return None

    @staticmethod
    def _verified_facts_grounding_for_prompt(
        message: Optional[str],
        *,
        brokerage_id: Optional[str],
    ):
        """Build Verified Facts grounding metadata for process/fee turns."""
        try:
            from app.core.verified_facts import (
                default_verified_fact_registry,
                verified_facts_grounding_for_message,
            )

            return verified_facts_grounding_for_message(
                message,
                registry=default_verified_fact_registry(),
                brokerage_id=brokerage_id,
            )
        except Exception:  # pragma: no cover - fail closed in prompt builder
            logger.warning("Verified Facts grounding failed", exc_info=True)
            return None

    @staticmethod
    def _percentage_from_verified_fact(fact) -> Optional[float]:
        if fact is None:
            return None
        try:
            from app.core.verified_facts import percentage_from_fact_text

            return percentage_from_fact_text(fact)
        except Exception:  # pragma: no cover - malformed fact should fail closed
            logger.warning("Verified Facts percentage extraction failed", exc_info=True)
            return None

    @staticmethod
    def _source_label_for_verified_fact(fact) -> Optional[str]:
        if fact is None:
            return None
        try:
            from app.core.verified_facts import fact_source_label

            return fact_source_label(fact)
        except Exception:  # pragma: no cover
            return getattr(fact, "source_label", None)

    @staticmethod
    def _escalation_state_reason(escalation: EscalationAlert) -> str:
        if escalation.escalation_type == "seller_action":
            return f"seller_action:{ChatbotEngine._seller_action_group(escalation.seller_intent)}"
        subtype = (
            escalation.escalation_subtype
            or escalation.seller_intent
            or escalation.regulatory_category
            or ""
        )
        return f"{escalation.escalation_type}:{subtype}"

    @staticmethod
    def _seller_action_group(seller_intent: Optional[str]) -> str:
        if seller_intent in {
            "price_update",
            "threshold_update",
            "listing_edit",
            "listing_status_change",
            "seller_pause",
            "buyer_outreach_request",
        }:
            return "listing_change"
        if seller_intent in {"offer_acceptance", "counter_offer", "net_proceeds"}:
            return "offer_negotiation"
        return "seller_advisory"

    def _should_suppress_non_offer_escalation(self, conv, escalation: Optional[EscalationAlert], db=None) -> bool:
        """Suppress repeated non-offer alerts once Eric already has the thread."""
        if not conv or escalation is None:
            return False
        if escalation.escalation_type in {"offer", "regulatory_request", "returning_buyer_followup"}:
            return False
        # Seller offer decisions (accept / reject+counter) are material and must
        # ALWAYS route to the agent — never consolidate them away (DAL-78).
        if getattr(escalation, "seller_intent", None) in {"offer_acceptance", "counter_offer"}:
            return False

        recent = (
            conv.last_escalated_at is not None
            and (datetime.utcnow() - conv.last_escalated_at) < timedelta(hours=24)
        )
        if not (conv.escalation_triggered and recent):
            return False

        existing = conv.escalation_reason or ""
        incoming = self._escalation_state_reason(escalation)

        if escalation.escalation_subtype == "new_listing_inquiry":
            return False
        if (
            escalation.escalation_subtype == "promise_kept"
            and existing.startswith("legitimate_conveyancing:")
        ):
            return True
        if escalation.escalation_subtype == "promise_kept":
            return False
        if (
            escalation.escalation_type == "seller_action"
            and incoming == "seller_action:seller_advisory"
            and existing in {"seller_action:listing_change", "seller_action:offer_negotiation"}
        ):
            return True
        if db is not None and escalation.escalation_type in {"info_gap", "unanswerable_question"}:
            # Threading owns consolidation for listing fact gaps. The legacy
            # conversation flag is too coarse: it only knows "info_gap", not
            # category, so it can hide a later fees gap after an earlier yield
            # gap. Let the thread layer append same-category questions or open
            # a separate category thread.
            return False
        if incoming != existing:
            return False
        if db is not None:
            try:
                from app.core.escalation_threads import has_open_thread_for_alert
                if has_open_thread_for_alert(db, conv, escalation):
                    return False
            except Exception:
                logger.exception("open escalation thread check failed; falling back to suppression")
        return True

    def _record_escalation_state(self, db, conv, escalation: EscalationAlert) -> None:
        if not conv or escalation is None:
            return
        crud.update_conversation(
            db, conv,
            escalation_triggered=True,
            escalation_reason=self._escalation_state_reason(escalation),
            last_escalated_at=datetime.utcnow(),
        )

    def _get_all_other_listings(self, current_listing_id: str, db) -> list:
        """Return summary of all other active listings so the bot can recommend them."""
        from app.models.db_models import DBListing

        current = db.get(DBListing, current_listing_id)
        filters = [DBListing.listing_id != current_listing_id]
        if current and current.brokerage_id:
            filters.append(DBListing.brokerage_id == current.brokerage_id)

        others = db.query(DBListing).filter(
            *filters
        ).all()

        result = []
        for listing in others:
            spa = listing.spa_data or {}
            price = listing.seller_asking_price or spa.get("purchase_price_aed")
            if not price:
                continue
            result.append({
                "project": spa.get("project", "Unknown"),
                "sub_community": spa.get("sub_community"),
                "unit_number": spa.get("unit_number", "?"),
                "property_type": spa.get("property_type", "Property"),
                "bedrooms": spa.get("bedrooms"),
                "bua_sqft": spa.get("bua_sqft"),
                "price_aed": price,
                "asking_price_aed": price,
                "asking_price": price,
            })
        return result

    # ── Cross-listing recommendations ────────────────────────────────────────

    def find_matching_listings(
        self,
        buyer_profile: BuyerProfile,
        current_listing_id: str,
        db,
    ) -> list:
        """
        Score other listings against buyer preferences and return top 2 matches.
        Returns list of dicts: {project, unit_number, price_aed}
        """
        from app.core.buyer_preferences import (
            get_or_create_preference_profile,
            match_buyer_profile_to_listings,
        )

        current = db.get(__import__("app.models.db_models", fromlist=["DBListing"]).DBListing, current_listing_id)
        if not current or not current.brokerage_id:
            return []

        profile = get_or_create_preference_profile(
            db,
            buyer_id=buyer_profile.phone,
            brokerage_id=current.brokerage_id,
        )
        matches = match_buyer_profile_to_listings(
            db,
            profile=profile,
            current_listing_id=current_listing_id,
            limit=2,
        )
        return [match.as_prompt_dict() for match in matches]

    # ── Conversation utilities ─────────────────────────────────────────────────

    # ── Post-generation sanitizer ──────────────────────────────────────────────

    @staticmethod
    def _replace_em_dashes(text: str) -> str:
        """Replace em-dashes with period or comma depending on what follows."""
        def repl(m):
            after = text[m.end(): m.end() + 3]
            if after.lstrip()[:1].isupper():
                return ". "
            return ", "
        return re.sub(r"\s*—\s*", repl, text)

    @staticmethod
    def _strip_reflexive_close(text: str, intent: str) -> str:
        """Remove a trailing closing question when the intent doesn't need one."""
        NO_FOLLOWUP_INTENTS = {
            "offer_submission", "viewing_request", "payment_plan_query",
            "speak_to_human", "contact_sharing", "price_negotiation",
        }
        if intent not in NO_FOLLOWUP_INTENTS:
            return text
        t = text.rstrip()
        if not t.endswith("?"):
            return text
        end = len(t) - 1
        m = list(re.finditer(r"[.!?\n]\s+", t[:end]))
        if not m:
            # Whole response is one question — bot is legitimately asking back. Keep it.
            return text
        cut_start = m[-1].end()
        core = t[:cut_start].rstrip()
        return core if core else text

    def _sanitize_response(self, raw: str, intent: str, listing_id: str = "") -> str:
        """
        DEPRECATED — replaced by validate_and_rewrite_response in response_validator.py.
        Kept for reference and potential future use. Not called from handle_message.

        Deterministic post-generation guard.
        1. Replace team-deflection phrases.
        2. Strip em-dashes with context-aware replacement.
        3. Strip reflexive closing questions for intents that don't need one.
        Logs when anything actually changed.
        """
        text = raw

        # 1. Team-deflection replacements
        for pattern, replacement in TEAM_REPLACEMENTS:
            text = pattern.sub(replacement, text)

        # 2. Em-dash replacement
        text = self._replace_em_dashes(text)

        # 3. Reflexive closing question removal
        text = self._strip_reflexive_close(text, intent)

        if text != raw:
            logger.info(
                "response_sanitized listing=%s intent=%s raw_len=%d sanitized_len=%d",
                listing_id, intent, len(raw), len(text),
            )

        return text

    def _summarise_conversation(
        self,
        state: ConversationState,
        spa: SPAParseResult,
        asking_price_aed: float,
        offer_amount_aed: Optional[float] = None,
    ) -> str:
        """Generate a brief summary of the conversation for Eric's escalation alert."""
        if len(state.messages) <= 2:
            return "New enquiry — conversation just started."

        history_text = "\n".join([
            f"{msg.role.value.upper()}: {msg.content}"
            for msg in state.messages[-10:]
        ])

        gap_aed = (asking_price_aed - offer_amount_aed) if offer_amount_aed else None
        gap_pct = (gap_aed / asking_price_aed * 100.0) if gap_aed else None

        ground_truth_lines = [
            f"- Asking price: AED {asking_price_aed:,.0f}",
        ]
        if offer_amount_aed:
            ground_truth_lines.append(f"- Buyer's offer: AED {offer_amount_aed:,.0f}")
            ground_truth_lines.append(f"- Gap from asking: AED {gap_aed:,.0f} ({gap_pct:.1f}% below)")
        ground_truth_lines.append(f"- Property: {spa.project} Unit {spa.unit_number}")
        ground_truth_block = "\n".join(ground_truth_lines)

        prompt = f"""You are summarising a property inquiry for the listing agent.

GROUND TRUTH (the only AED figures you may reference):
{ground_truth_block}

Conversation transcript:
{history_text}

Write 3 concise sentences covering ONLY:
1. Buyer's apparent seriousness — cite specific questions they asked.
2. Their stated constraints, motivations, or context.
3. Recommended next action for the agent.

CRITICAL RULES:
- DO NOT introduce any AED figures other than the ones in GROUND TRUTH above.
- DO NOT speculate on the seller's situation or motivations.
- DO NOT mention the SPA price, original purchase price, or any derived figure.
- If you don't have enough information for a field, write "not stated".

Summary:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": prompt,
                }],
            )
            summary = response.content[0].text.strip()

            # Build the allowed-figures set: every AED number the model is permitted to use
            allowed = {round(asking_price_aed)}
            if offer_amount_aed:
                allowed.add(round(offer_amount_aed))
                allowed.add(round(asking_price_aed - offer_amount_aed))  # gap

            # Find every AED figure in the summary
            figure_pattern = re.compile(r"AED\s*([\d,]+(?:\.\d+)?)\s*([MmKk]?)\b")
            rogue = []
            for match in figure_pattern.finditer(summary):
                raw = match.group(1).replace(",", "")
                suffix = match.group(2).lower()
                try:
                    value = float(raw)
                    if suffix == "m":
                        value *= 1_000_000
                    elif suffix == "k":
                        value *= 1_000
                    # Tolerance: within AED 1,000 of an allowed value
                    if not any(abs(value - a) < 1_000 for a in allowed):
                        rogue.append(match.group(0))
                except ValueError:
                    continue

            if rogue:
                # Fail closed: deterministic template instead of a fluent-but-wrong summary
                logger.warning(
                    "Summary contained rogue AED figures %s; falling back to template. allowed=%s, summary=%r",
                    rogue, allowed, summary,
                )
                parts = [f"Buyer enquired about {spa.project} Unit {spa.unit_number}."]
                if offer_amount_aed:
                    parts.append(f"Submitted offer of AED {offer_amount_aed:,.0f} against AED {asking_price_aed:,.0f} asking ({gap_pct:.1f}% below).")
                parts.append("Escalation triggered — review conversation for context.")
                return " ".join(parts)

            return summary
        except Exception:
            return f"Buyer enquired about {spa.unit_number}. Escalation triggered."

    def _suggest_agent_response(
        self,
        intent: BuyerIntent,
        buyer_name: Optional[str] = None,
    ) -> str:
        """Suggest what Eric should say when picking up the conversation."""
        name = buyer_name or "there"
        suggestions = {
            BuyerIntent.viewing_request: (
                f"Hi {name}, this is the listing agent. I understand you'd like to arrange "
                f"a viewing — I'd be happy to set that up. When works best for you?"
            ),
            BuyerIntent.offer_submission: (
                f"Hi {name}, the listing agent here. I saw your interest in making an offer "
                f"— let's discuss the details. What figure did you have in mind?"
            ),
            BuyerIntent.contact_sharing: (
                f"Hi {name}, the listing agent here. Thanks for reaching out — happy to help you "
                f"with this property. When's a good time for a quick call?"
            ),
            BuyerIntent.price_negotiation: (
                f"Hi {name}, the listing agent here. I understand you had some questions about "
                f"pricing — let me discuss that with you directly."
            ),
        }
        return suggestions.get(
            intent,
            f"Hi {name}, the listing agent here. The Property Advisor flagged your enquiry for "
            f"personal follow-up — happy to assist you directly."
        )

    # ── Conversation retrieval ─────────────────────────────────────────────────

    def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        with SessionLocal() as db:
            conv = crud.get_conversation(db, conversation_id)
            if not conv:
                return None
            return crud.db_conv_to_state(conv)

    def get_all_conversations(self, listing_id: str) -> list[ConversationState]:
        with SessionLocal() as db:
            convs = crud.get_conversations_for_listing(db, listing_id)
            return [crud.db_conv_to_state(c) for c in convs]

    def get_buyer_profile(self, phone: str) -> Optional[BuyerProfile]:
        with SessionLocal() as db:
            profile = db.get(
                __import__("app.models.db_models", fromlist=["DBBuyerProfile"]).DBBuyerProfile,
                phone,
            )
            if not profile:
                return None
            return crud.db_profile_to_schema(profile)

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

    # ── Private helpers ────────────────────────────────────────────────────────

    def _update_buyer_profile(
        self,
        db,
        phone: str,
        spa: SPAParseResult,
        db_listing,
        listing_id: str,
        buyer_message: str,
        intent_data: dict,
        buyer_name: Optional[str],
        detected_budget: Optional[float],
    ) -> None:
        from sqlalchemy import func, select
        from app.models.db_models import DBConversation, DBMessage

        profile = crud.get_or_create_buyer_profile(db, phone)

        extracted_bedrooms = intent_data.get("extracted_bedrooms")
        if isinstance(extracted_bedrooms, float):
            extracted_bedrooms = int(extracted_bedrooms)

        crud.update_buyer_profile(
            db,
            profile,
            name=buyer_name,
            budget_aed=detected_budget,
            bedroom=extracted_bedrooms if isinstance(extracted_bedrooms, int) else None,
            area=intent_data.get("extracted_area"),
            purpose=intent_data.get("extracted_purpose"),
        )

        crud.add_listing_inquiry(
            db,
            buyer_phone=phone,
            listing_id=listing_id,
            project=spa.project,
            unit_number=spa.unit_number,
            price_aed=spa.purchase_price_aed,
        )

        from app.core.buyer_preferences import update_buyer_preference_profile

        update_buyer_preference_profile(
            db,
            buyer_id=phone,
            brokerage_id=getattr(db_listing, "brokerage_id", None),
            buyer_message=buyer_message,
            listing=db_listing,
        )

        # ── Auto-stage advancement ────────────────────────────────────────
        # Manual-only stages are never auto-changed
        MANUAL_ONLY = {"negotiation", "closed_won", "closed_lost"}
        current = profile.lead_stage or "new"
        stage_rank = {"new": 0, "engaged": 1, "qualified": 2, "offer": 3,
                      "negotiation": 4, "closed_won": 5, "closed_lost": 5}

        if current not in MANUAL_ONLY:
            new_stage = current
            intent_val = intent_data.get("intent", "unknown")

            # new → engaged: 3+ buyer messages across all conversations
            if stage_rank.get(current, 0) < stage_rank["engaged"]:
                buyer_msg_count = db.execute(
                    select(func.count(DBMessage.id))
                    .join(DBConversation, DBConversation.conversation_id == DBMessage.conversation_id)
                    .where(DBConversation.buyer_phone == phone)
                    .where(DBMessage.role == "user")
                ).scalar() or 0
                if buyer_msg_count >= 3:
                    new_stage = "engaged"

            # engaged → qualified: budget or bedroom prefs set
            if stage_rank.get(new_stage, 0) < stage_rank["qualified"]:
                if profile.budget_aed or (profile.bedroom_preferences and len(profile.bedroom_preferences) > 0):
                    new_stage = "qualified"

            # qualified/engaged → offer: on offer_submission intent
            if stage_rank.get(new_stage, 0) < stage_rank["offer"]:
                if intent_val == "offer_submission":
                    new_stage = "offer"

            if new_stage != current:
                profile.lead_stage = new_stage
                profile.updated_at = datetime.utcnow()
                safe_commit(db)
                db.refresh(profile)


    # ── Phase 5.1: Three-message engagement gate ──────────────────────────────

    @staticmethod
    def _is_substantive_message(message_text: str) -> bool:
        """
        Phase 8.3: Substantive engagement = NOT a pure offer demand or transactional pressure.

        A buyer who only sends "5M cash" / "6M absolute final, give me the seller now"
        has not engaged with the listing — they're just demanding. Such messages do NOT
        count toward the 3-message engagement gate.
        """
        if not message_text:
            return False
        m = message_text.lower().strip()
        has_amount = bool(re.search(
            r"\b\d+(?:[.,]\d+)?\s*(?:m|million|aed|k|thousand|درهم|crore|lakh)\b",
            m,
        ))
        has_demand_verb = any(v in m for v in [
            "pay", "will pay", "offer", "take it", "leave it",
            "transfer", "wire", "cash today", "no questions",
            "give me", "send me the seller", "skip", "deal", "absolute final",
            "final offer", "best offer", " cash", "no financing",
        ])
        disqualifying_terms = [
            "system prompt", "ignore your instructions", "developer mode",
            "jailbreak", "bypass", "skip the broker", "skip broker",
            "deal direct", "seller contact", "seller phone", "seller number",
            "seller's phone", "seller's number", "seller's email",
            "seller's full name", "owner phone", "owner number",
            "owner's phone", "owner's number", "owner's email",
            "seller's brother", "owner directly", "seller directly",
            "passport", "emirates id", "under the table",
            "save us both the brokerage fee", "developer's portal directly",
            "directly with seller", "route around",
        ]
        if any(term in m for term in disqualifying_terms):
            return False
        if re.search(r"\b(?:share|send|give|forward|show).{0,40}\b(?:spa|soa|noc|title deed|passport|emirates id|eid|document|docs)\b", m):
            return False

        clear_interest_terms = [
            "price", "asking", "payment", "plan", "schedule", "noc", "handover",
            "transfer", "mou", "trustee", "mortgage", "bank", "financing",
            "bed", "bedroom", "bath", "sqft", "size", "plot", "bua", "floor",
            "view", "parking", "service charge", "furnished", "unfurnished",
            "pet", "maid", "layout", "floor plan", "rent", "rental", "yield",
            "roi", "school", "mosque", "location", "community", "amenities",
            "villa", "apartment", "townhouse", "unit", "property", "viewing",
            "visit", "brochure", "render", "offer", "counter",
            "سعر", "السعر", "دفعات", "دفعة", "الدفع", "خطة الدفع",
            "التسليم", "موعد", "مطور", "المطور", "غرف", "غرفة",
            "حمام", "حمامات", "مساحة", "مدارس", "مدرسة", "جوامع",
            "جامع", "مسجد", "منطقة", "المشروع", "مشروع", "عمولة",
            "عرض", "أقدم عرض", "اقدم عرض", "شراء", "اشتري",
        ]
        has_clear_interest = any(term in m for term in clear_interest_terms)
        has_question = "?" in message_text
        word_count = len(message_text.split())

        # Very short message with just an amount → not substantive
        if has_amount and not has_question and word_count <= 4:
            return False

        # Pure offer demand: amount + demand verb, no question, short
        if has_amount and has_demand_verb and not has_question and word_count < 12:
            return False
        return has_clear_interest or (has_question and word_count >= 6)

    def _engagement_gate_pass(
        self,
        intent_data: dict,
        conv,
        *,
        is_seller: bool = False,
        is_regulatory: bool = False,
        is_verified_lawyer: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """
        Returns (gate_passes, suppression_reason).

        Phase 8.3: Buyers must have 3+ prior SUBSTANTIVE buyer messages on this listing
        before any escalation fires. Pure offer demands ("6M cash now") don't count
        toward substantive engagement.

        Below the gate, escalations are suppressed (but offer records are still stored
        for the data moat).

        Exceptions: seller messages, regulatory requests, and verified-lawyer
        escalations bypass the gate entirely.
        """
        if is_seller or is_regulatory or is_verified_lawyer:
            return True, None

        # Phase 8.3: count SUBSTANTIVE buyer messages BEFORE the current one.
        prior_buyer_messages = [
            m for m in conv.messages if m.role == "user"
        ][:-1]  # exclude current message (already persisted by this point)

        substantive_count = sum(
            1 for m in prior_buyer_messages
            if self._is_substantive_message(m.content)
        )

        # Safety: if a prior escalation has already fired, always let through.
        if conv.escalation_triggered:
            return True, None

        if substantive_count < 3:
            return False, f"engagement_gate_below_threshold_{substantive_count}_substantive_of_3"
        return True, None

    # ── Phase 8.1: Above-threshold response templates ─────────────────────────

    # Phase 9.4: Expanded pool — varied phrasing across listings within 24h
    _ABOVE_THRESHOLD_TEMPLATES_EN = [
        "AED {offer:,.0f} noted. I'll get this to the seller and follow up with their response.",
        "AED {offer:,.0f} — got it. Passing this to the seller now and circling back once they've reviewed.",
        "AED {offer:,.0f} noted. Let me run this past the seller and I'll come back with where they land.",
        "Got it, AED {offer:,.0f}. I'll forward to the seller and follow up with their response.",
        "AED {offer:,.0f} noted. Sending this over to the seller now — I'll be back to you with their response shortly.",
        "AED {offer:,.0f} — that's heading to the seller. I'll let you know once they've come back to me.",
        "Got it. AED {offer:,.0f} is going to the seller now. I'll follow up as soon as they've responded.",
        "AED {offer:,.0f} acknowledged. I'm forwarding to the seller — expect a response from me soon.",
    ]

    _ABOVE_THRESHOLD_TEMPLATES_AR = [
        "تم استلام عرضك بقيمة {offer:,.0f} درهم. سأمرر هذا للبائع وأعود إليك بإجابتهم.",
        "تم تسجيل العرض بقيمة {offer:,.0f} درهم. سأرسله للبائع الآن وأتواصل معك بمجرد المراجعة.",
        "تم تأكيد العرض بقيمة {offer:,.0f} درهم. أنا أرسله للبائع، وسأعود إليك بمجرد سماع رده.",
    ]

    # Phase 9.4: Vary the contact-capture phrasing too
    _CONTACT_FOLLOWUP_EN_VARIANTS = [
        " What name should I put this under?",
        " Please send your name so I can attach it to the offer.",
        " What name should {managing_agent_name} see on the offer?",
        " Send your name and I'll keep the offer record clean.",
    ]
    _CONTACT_FOLLOWUP_AR_VARIANTS = [
        " ما الاسم الذي أضعه على العرض؟",
        " أرسل اسمك لو سمحت حتى أرفقه بالعرض.",
    ]

    # Backwards-compat single-template aliases (callers from earlier phases)
    _CONTACT_FOLLOWUP_EN = _CONTACT_FOLLOWUP_EN_VARIANTS[0]
    _CONTACT_FOLLOWUP_AR = _CONTACT_FOLLOWUP_AR_VARIANTS[0]

    _PRE_ENGAGEMENT_TEMPLATES_EN = [
        "AED {offer:,.0f} noted. Before I can route this to the seller, send your name and confirm whether you're buying directly or through an advisor.",
        "AED {offer:,.0f} noted. Send your name and timing, then I can treat this as a clean offer record.",
    ]

    _PRE_ENGAGEMENT_TEMPLATES_AR = [
        "تم استلام عرضك بقيمة {offer:,.0f} درهم. أرسل اسمك وتوقيت الشراء حتى أسجل العرض بشكل واضح.",
    ]

    @classmethod
    def _above_threshold_template(
        cls,
        offer_amount: float,
        intent_data: dict,
        conv,
        buyer_profile,
    ) -> str:
        """Phase 8.1 / 9.4: Deterministic acknowledgment for above-threshold + marginal offers.

        Phase 9.4 — listing-level rotation: avoid repeating a template that was
        used on this LISTING within the last 24h, not just within this conversation.
        Different buyers on the same listing should not all hear identical phrasing.
        """
        import random
        lang = (intent_data.get("language_detected") or "en").lower()
        is_arabic = lang.startswith("ar")
        templates = cls._ABOVE_THRESHOLD_TEMPLATES_AR if is_arabic else cls._ABOVE_THRESHOLD_TEMPLATES_EN
        followup_variants = (
            cls._CONTACT_FOLLOWUP_AR_VARIANTS if is_arabic
            else cls._CONTACT_FOLLOWUP_EN_VARIANTS
        )

        used_in_conv = {m.content for m in conv.messages if m.role == "assistant"}

        # Phase 9.4: Cross-conversation listing-level recent usage
        recently_used_on_listing = cls._recent_above_threshold_templates_for_listing(
            conv.listing_id, hours=24,
        )

        candidates = [
            t for t in templates
            if t.format(offer=offer_amount) not in used_in_conv
            and t not in recently_used_on_listing
        ]
        # Fall back if everything has been used recently
        if not candidates:
            candidates = [
                t for t in templates
                if t.format(offer=offer_amount) not in used_in_conv
            ]
        if not candidates:
            candidates = templates
        chosen_template = random.choice(candidates)
        body = chosen_template.format(offer=offer_amount)

        # Track template usage at listing level so other concurrent conversations
        # see this one as "recently used"
        cls._mark_above_threshold_template_used(conv.listing_id, chosen_template)

        # Capture contact if missing — pick a varied followup
        has_name = bool(buyer_profile and buyer_profile.name)
        if not has_name:
            body += random.choice(followup_variants)
        return body

    # Phase 9.4: In-process listing-level template-usage tracker.
    # Lightweight (no DB); keyed by (listing_id, template) -> last_used_ts.
    # Adequate for single-process deployments and the test orchestrator.
    _LISTING_TEMPLATE_USAGE: dict = {}

    @classmethod
    def _recent_above_threshold_templates_for_listing(
        cls, listing_id: str, hours: int = 24,
    ) -> set:
        """Phase 9.4: Templates used on this listing within the last N hours."""
        if not listing_id:
            return set()
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = set()
        for (lid, template), ts in list(cls._LISTING_TEMPLATE_USAGE.items()):
            if lid == listing_id and ts >= cutoff:
                result.add(template)
        return result

    @classmethod
    def _mark_above_threshold_template_used(cls, listing_id: str, template: str) -> None:
        """Phase 9.4: Record that this template fired on this listing now."""
        if not listing_id or not template:
            return
        cls._LISTING_TEMPLATE_USAGE[(listing_id, template)] = datetime.utcnow()

    @classmethod
    def _above_threshold_pre_engagement_template(
        cls,
        offer_amount: float,
        intent_data: dict,
    ) -> str:
        """Phase 8.1 + 8.3: Above-threshold offer but engagement gate hasn't passed yet.
        Don't promise to forward (we won't); push for substantive context first."""
        import random
        lang = (intent_data.get("language_detected") or "en").lower()
        is_arabic = lang.startswith("ar")
        templates = cls._PRE_ENGAGEMENT_TEMPLATES_AR if is_arabic else cls._PRE_ENGAGEMENT_TEMPLATES_EN
        return random.choice(templates).format(offer=offer_amount)

    # ── Phase 9.10: Returning-buyer template ──────────────────────────────────

    @classmethod
    def _returning_buyer_template(
        cls,
        returning_context: dict,
        conv,
        managing_agent_name: str = "{managing_agent_name}",
    ) -> str:
        """Phase 9.10: Buyer is returning to a previously-engaged listing. If
        we have OfferRecord history, acknowledge the prior offer specifically.
        If not, acknowledge the absence of record. Either way, escalate to Eric.
        """
        prior_offers = returning_context.get("prior_offers") or []
        latest = prior_offers[-1] if prior_offers else None
        if latest:
            return (
                "I'm Dalya. I can see a prior offer record on this unit. "
                f"I've flagged this for {managing_agent_name} so they can follow up with the current status "
                "on this WhatsApp thread."
            )
        # No prior offer in our records — buyer claims prior contact; escalate
        # so Eric can verify against a wider record.
        return (
            "I'm Dalya. I don't have a record of a prior conversation on this unit on my end. "
            "Let me forward this to {managing_agent_name} so they can check our records and follow up "
            "with you directly on this WhatsApp thread."
        )

    # ── Phase 8.5: Soft-offer detection ───────────────────────────────────────

    _SOFT_OFFER_PAUSE_PATTERNS = [
        r"discuss with",
        r"speak (?:to|with) (?:my|the)",
        r"come back",
        r"think about it",
        r"get back to you",
        r"will let you know",
        r"thank you for now",
        r"that's all for now",
        r"talk it over",
        r"will (?:revert|circle back)",
        r"in[ -]?sha[' -]?allah",
    ]

    @classmethod
    def _detect_soft_offer_pause(cls, conv, current_message: str) -> Optional[float]:
        """
        Phase 8.5: Detect a soft offer + pause pattern.

        A soft offer is when the buyer floated an amount in a recent turn (typically
        hypothetically — "if I offer X, how does that work?") and is now signaling
        they're stepping away.

        Returns the floated amount if both conditions met, else None.
        """
        if not current_message:
            return None
        # Current message must signal a pause/step-away
        is_pausing = any(
            re.search(p, current_message, re.IGNORECASE)
            for p in cls._SOFT_OFFER_PAUSE_PATTERNS
        )
        if not is_pausing:
            return None

        # Look back through last 5 buyer messages for a floated amount with hypothetical/conditional wording
        buyer_msgs = [m for m in conv.messages if m.role == "user"][-6:-1]  # last 5 prior to current
        for msg in reversed(buyer_msgs):
            text = msg.content or ""
            if cls._is_hypothetical_offer_query(text):
                continue
            # Hypothetical phrasing
            if not re.search(r"\b(if|hypothetic|what if|let'?s say|suppose|would|could)\b", text, re.IGNORECASE):
                continue
            # Find an AED amount in the message
            amount_match = re.search(
                r"(?:aed|AED)?\s*([\d.,]+)\s*(m|million|million dirhams|درهم|aed|AED)?",
                text, re.IGNORECASE,
            )
            if not amount_match:
                continue
            try:
                num_str = amount_match.group(1).replace(",", "")
                num = float(num_str)
                unit = (amount_match.group(2) or "").lower()
                if unit in ("m", "million", "million dirhams"):
                    num *= 1_000_000
                if num < 100_000:
                    # Probably a year or unit number, not an offer
                    continue
                return num
            except ValueError:
                continue
        return None

    # ── Phase 9.1 (multitenant rewrite): Managing-agent introduction on first mention ──

    _MANAGING_AGENT_INTRO_PHRASES = [
        "{managing_agent_name}, the {managing_agent_title} at {brokerage_short}",
        "{managing_agent_name}, the {brokerage_short} agent managing this listing",
        "{managing_agent_name}, the listing agent at {brokerage_short}",
    ]

    _MANAGING_AGENT_INTRO_MARKERS = (
        "lead broker",
        "managing director",
        "listing agent",
        "agent managing this listing",
        "handles all transactions",
        "handling all transactions",
        "handles transactions end-to-end",
    )

    @classmethod
    def _has_managing_agent_been_introduced(cls, conv, ctx) -> bool:
        """True if any prior assistant message in this conversation already
        introduced the managing agent by role. Derived from history rather
        than a DB flag so it can never drift out of sync with what was said."""
        if not conv or not getattr(conv, "messages", None):
            return False
        agent_name_lc = (ctx.managing_agent_name or "").lower()
        if not agent_name_lc:
            return True  # nothing to introduce
        for m in conv.messages:
            if m.role != "assistant":
                continue
            text = (m.content or "").lower()
            if agent_name_lc not in text:
                continue
            if any(marker in text for marker in cls._MANAGING_AGENT_INTRO_MARKERS):
                return True
            if (ctx.managing_agent_title or "").lower() in text:
                return True
        return False

    @classmethod
    def _inject_managing_agent_intro_on_first_mention(cls, response: str, conv, ctx) -> str:
        """If response mentions the managing agent AND they haven't been
        introduced yet in this conversation, replace the first standalone
        mention with the role-anchored introduction. Idempotent."""
        import random
        if not response or not ctx or not ctx.managing_agent_name:
            return response
        agent_name = ctx.managing_agent_name
        if agent_name.lower() not in response.lower():
            return response
        if cls._has_managing_agent_been_introduced(conv, ctx):
            return response
        response_lower = response.lower()
        if any(marker in response_lower for marker in cls._MANAGING_AGENT_INTRO_MARKERS):
            return response
        existing_intro = re.search(
            rf"\b{re.escape(agent_name)}\b.{0,90}"
            r"(?:listing agent|agent managing this listing|managing agent|at\s+"
            + re.escape(ctx.brokerage_short.lower())
            + r")",
            response_lower,
            re.IGNORECASE,
        )
        if existing_intro:
            return response
        intro_template = random.choice(cls._MANAGING_AGENT_INTRO_PHRASES)
        intro = intro_template.format(
            managing_agent_name=ctx.managing_agent_name,
            managing_agent_title=ctx.managing_agent_title,
            brokerage_short=ctx.brokerage_short,
        )
        pattern = re.compile(r'\b' + re.escape(agent_name) + r'\b')
        return pattern.sub(intro, response, count=1)

    # Backwards-compat aliases — legacy Eric-only paths still exist in some
    # tests; route them through the multitenant implementations.
    @classmethod
    def _has_eric_been_introduced(cls, conv):
        from app.core.multitenant_context import legacy_default_context
        return cls._has_managing_agent_been_introduced(conv, legacy_default_context())

    @classmethod
    def _inject_eric_intro_on_first_mention(cls, response, conv):
        from app.core.multitenant_context import legacy_default_context
        return cls._inject_managing_agent_intro_on_first_mention(
            response, conv, legacy_default_context()
        )

    @staticmethod
    def _is_transactional_demand(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        has_greeting = any(g in m for g in [
            "hi", "hello", "hey", "salam", "good morning", "good evening",
            "as-salam", "السلام",
        ])
        has_amount = bool(re.search(
            r"\b\d+(?:[.,]\d+)?\s*(?:m|million|aed|k|thousand)\b", m
        ))
        has_demand = any(v in m for v in [
            "pay", "offer", "buy", "take it", "leave it", "transfer",
            "wire", "deal", "cash today", "no questions", "final",
        ])
        return (not has_greeting) and has_amount and has_demand

    @staticmethod
    def _is_hypothetical_offer_query(message: str) -> bool:
        """True when an amount is used to ask about process, not to submit a bid."""
        if not message:
            return False
        m = message.lower()
        has_amount = bool(re.search(
            r"\b\d+(?:[.,]\d+)?\s*(?:m|million|aed|k|thousand)\b", m
        ))
        if not has_amount:
            return False
        if re.search(
            r"\bi\s+(?:want|would like|am ready|ready)\s+to\s+(?:make\s+an\s+)?offer\s+at\b",
            m,
            re.IGNORECASE,
        ):
            return False
        # R6: an explicit instruction to route/escalate the amount is a real offer,
        # not a hypothetical process question.
        if re.search(
            r"\b(?:escalate|route|forward|send|submit|pass|put|log|record)\b[^.\n]*\b(?:it|this|that|the offer|to (?:the )?(?:correct |right )?agent|to (?:the )?seller)\b",
            m,
            re.IGNORECASE,
        ):
            return False
        patterns = [
            r"\bif\s+i\s+(?:want|wanted|were|was|decide|decided)\s+to\s+(?:make\s+an\s+)?offer\b",
            r"\bif\s+i\s+(?:offer|offered)\b",
            r"\bhypothetic(?:al|ally)\b",
            r"\bwould\s+(?:you|the\s+seller)\s+(?:accept|consider|take)\b",
            r"\bhow\s+does\s+that\s+work\??\s*$",
        ]
        return any(re.search(pattern, m, re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _is_explicit_offer_submission(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        return bool(re.search(
            r"\b(?:i\s+)?(?:want|would like|am ready|ready)\s+to\s+(?:make\s+an\s+)?offer\s+at\s+(?:aed\s*)?[\d,]+",
            m,
            re.IGNORECASE,
        ))

    @staticmethod
    def _ensure_complete_sentence(text: str) -> str:
        """R3: guarantee the response ends as a complete sentence. Strips dangling
        trailing connectors/commas and appends a period when the text ends on a
        word/letter with no terminal punctuation. Arabic and Latin safe; never
        touches text that already ends in . ! ? … : or a closing quote/bracket."""
        if not text:
            return text
        t = text.rstrip()
        if not t:
            return text
        # Drop a dangling trailing connector word left by an upstream strip
        # (e.g. "... and", "... so", "... but,").
        t = re.sub(r"[\s,;:]+(?:and|or|but|so|because|with|to|for|that)\s*$", "", t, flags=re.IGNORECASE).rstrip()
        t = t.rstrip(",;: ")
        if not t:
            return text
        terminal = ".!?…:\"')]»”،؟।"
        if t[-1] in terminal:
            return t
        return t + "."

    # Post-escalation refusal "hold" lines are INTENTIONALLY allowed to repeat
    # (the customer is probing, not exploring) — the anti-verbatim guard must
    # leave them alone (REG-1).
    _INTENTIONAL_REPEAT_LINES = {
        "no. i won't share seller contact details.",
        "no. seller contact stays private.",
        "no. i won't help with that request.",
        "no. this stays limited to the property and proper transaction path.",
        "لا. لن أشارك بيانات تواصل البائع.",
        "لا. تواصل البائع يبقى خاصاً.",
        "لا. لن أساعد في هذا الطلب.",
        "لا. يبقى هذا محصوراً بالعقار ومسار المعاملة الصحيح.",
    }

    @staticmethod
    def _vary(pool: list, conv) -> str:
        """Pick from a variation pool by conversation position so consecutive
        deterministic turns don't read as byte-identical copy-paste (DAL-74)."""
        n = sum(
            1 for m in (getattr(conv, "messages", None) or [])
            if getattr(m, "role", None) == "assistant"
        )
        return pool[n % len(pool)]

    @classmethod
    def _avoid_verbatim_repeat(cls, response: str, conv) -> str:
        """Real variation, not a canned 'same answer as before' tic (DAL-74).
        Genuine duplicates are now prevented by varying the deterministic
        templates themselves; this is only a last-resort guard, and it never
        touches the intentional post-escalation refusal holds (REG-1)."""
        if not response or not conv:
            return response
        if response.strip().lower() in cls._INTENTIONAL_REPEAT_LINES:
            return response
        return response

    @staticmethod
    def _strip_terminal_question(text: str) -> str:
        t = text.rstrip()
        if not t.endswith("?"):
            return text
        matches = list(re.finditer(r"[.!?\n]\s+", t[:-1]))
        if not matches:
            return text
        return t[:matches[-1].end()].rstrip()

    @classmethod
    def _inject_first_turn_identity(cls, response: str, conv, ctx: Optional[BrokerageContext] = None) -> str:
        if not response or not conv or not getattr(conv, "messages", None):
            return response
        prior_assistant = [m for m in conv.messages if m.role == "assistant"]
        if prior_assistant:
            return response
        user_messages = [m.content for m in conv.messages if m.role == "user"]
        opening = user_messages[0] if user_messages else ""
        if cls._is_transactional_demand(opening):
            return response
        lower = response.lower()
        if ctx is None:
            ctx = legacy_default_context()
        if "dalya" in lower or ctx.brokerage_short.lower() in lower or ctx.brokerage_name.lower() in lower:
            return response
        return f"Dalya with {ctx.brokerage_name} here. {response}"

    @classmethod
    def _apply_question_budget(cls, response: str, conv) -> str:
        if not response or not response.rstrip().endswith("?") or not conv:
            return response
        lower = response.lower().rstrip()
        if re.search(r"(what name should|send your name|confirm the offer amount)", lower):
            return response

        prior_assistant = [
            m for m in getattr(conv, "messages", [])
            if m.role == "assistant" and m.content
        ]
        recent_questions = sum(1 for m in prior_assistant[-3:] if m.content.rstrip().endswith("?"))
        total_questions = sum(1 for m in prior_assistant if m.content.rstrip().endswith("?"))
        if recent_questions >= 1 or (prior_assistant and total_questions / len(prior_assistant) >= 0.34):
            return cls._strip_terminal_question(response)
        return response

    def _finalize_response(
        self,
        response: str,
        intent: Optional[BuyerIntent],
        conv=None,
        ctx: Optional[BrokerageContext] = None,
        latest_buyer_message: Optional[str] = None,
    ) -> tuple[str, dict]:
        """Single finalization step. Runs the universal validator, then
        substitutes brokerage context placeholders ({managing_agent_name},
        {brokerage_short}, etc.), injects the managing-agent role
        introduction on first mention, and applies the question budget.
        All response paths go through this before persisting."""
        if not response or not response.strip():
            response = "I don't have that detail in the listing record. I'll route this to the listing agent so they can confirm."
        if ctx is None:
            ctx = legacy_default_context()
        if latest_buyer_message is None:
            latest_buyer_message = self._latest_buyer_message_text(conv)
        # Phase 10: Substitute brokerage context placeholders embedded in
        # response templates (e.g. "I'll record this for {managing_agent_name}.").
        # Templates rendered as plain text — never use Python f-string syntax
        # on tainted buyer input.
        response = self._apply_brokerage_substitutions(response, ctx)
        response, telemetry = validate_and_rewrite_response(
            response,
            intent,
            latest_buyer_message=latest_buyer_message,
            brokerage_id=ctx.brokerage_id,
        )
        response = self._sanitize_public_response(response, ctx)
        response = self._inject_managing_agent_intro_on_first_mention(response, conv, ctx)
        response = self._sanitize_public_response(response, ctx)
        response = self._inject_first_turn_identity(response, conv, ctx)
        response = self._apply_question_budget(response, conv)
        response = self._ensure_complete_sentence(response)
        response = self._avoid_verbatim_repeat(response, conv)
        return response, telemetry

    @staticmethod
    def _latest_buyer_message_text(conv) -> Optional[str]:
        messages = list(getattr(conv, "messages", []) or [])
        for message in reversed(messages):
            role = getattr(message, "role", None)
            role_value = getattr(role, "value", role)
            if role_value == MessageRole.user.value:
                content = getattr(message, "content", None)
                return content if isinstance(content, str) else None
        return None

    @staticmethod
    def _apply_brokerage_substitutions(text: str, ctx: BrokerageContext) -> str:
        """Substitute {managing_agent_name}, {brokerage_short}, etc. in a response template."""
        if not text or "{" not in text:
            return text
        # Use string.Template-style substitution to be safe against stray braces in user content
        replacements = {
            "{managing_agent_name}": ctx.managing_agent_name,
            "{managing_agent_title}": ctx.managing_agent_title,
            "{brokerage_name}": ctx.brokerage_name,
            "{brokerage_short}": ctx.brokerage_short,
            "{brokerage_arabic}": ctx.brokerage_arabic,
            "{commission_pct_label}": ctx.commission_pct_label,
            "{market_pct_label}": ctx.market_pct_label,
            "{savings_pct_label}": ctx.savings_pct_label,
            "{dashboard_url}": ctx.dashboard_url,
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    @staticmethod
    def _sanitize_public_response(text: str, ctx: Optional[BrokerageContext] = None) -> str:
        """Remove internal fixture labels and collapse duplicated agent role phrases."""
        if not text:
            return text
        text = re.sub(r"\bUnit\s+Harness\b", "the unit", text, flags=re.IGNORECASE)
        text = re.sub(
            r"\bthe\s+Harness\s+(unit|villa|apartment|townhouse|property)\b",
            r"this \1",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bHarness\s+(unit|villa|apartment|townhouse|property)\b",
            r"this \1",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\bHarness\s+from\b", "the listing from", text, flags=re.IGNORECASE)
        text = re.sub(r"\bHarness\b", "the unit", text, flags=re.IGNORECASE)
        text = re.sub(
            r"\b(?:we|i)\s+(?:work|partner|source|can help source)[^.?!\n]*(?:co-?brokerage|other agencies|across the market)[^.?!\n]*(?:[.?!]|$)",
            "I can only discuss listings represented by this brokerage in this chat.",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\b(?:including|through)\s+co-?brokerage\s+(?:arrangements|deals|stock)[^.?!\n]*(?:[.?!]|$)",
            "I can only discuss listings represented by this brokerage in this chat.",
            text,
            flags=re.IGNORECASE,
        )
        offplan_copy_hint = bool(
            re.search(r"\bhandover\b|under construction|2027|2028|2029|2030|2031|تسليم", text, re.IGNORECASE)
        )
        if offplan_copy_hint:
            text = re.sub(
                r"\bin finished condition\.?\s*You'?d move in ready to go\.?",
                "delivered turnkey at handover.",
                text,
                flags=re.IGNORECASE,
            )
            text = re.sub(
                r"\bin finished condition\b",
                "delivered turnkey at handover",
                text,
                flags=re.IGNORECASE,
            )
            text = re.sub(
                r"في حالة تشطيب كامل",
                "سيتم تسليمها بتشطيب كامل عند موعد التسليم",
                text,
            )
            text = re.sub(
                r"بحالة تشطيب كامل",
                "وسيتم تسليمها بتشطيب كامل عند موعد التسليم",
                text,
            )
        text = re.sub(
            r"\bdelivered\s+delivered turnkey at handover\s+at handover\b",
            "delivered turnkey at handover",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bdelivered turnkey at handover\s+at handover\b",
            "delivered turnkey at handover",
            text,
            flags=re.IGNORECASE,
        )
        if ctx and ctx.managing_agent_name:
            name = re.escape(ctx.managing_agent_name)
            brokerage = re.escape(ctx.brokerage_short or ctx.brokerage_name or "")
            if brokerage:
                text = re.sub(
                    rf"\b({name}), the listing agent at ({brokerage}), "
                    rf"the agent managing this listing at \2\b",
                    r"\1, the agent managing this listing at \2",
                    text,
                    flags=re.IGNORECASE,
                )
                text = re.sub(
                    rf"\b({name}), the agent managing this listing at ({brokerage}) at \2\b",
                    r"\1, the agent managing this listing at \2",
                    text,
                    flags=re.IGNORECASE,
                )
                text = re.sub(
                    rf"\b({name}), the agent managing this listing at ({brokerage}), "
                    rf"the agent managing this listing at \2\b",
                    r"\1, the agent managing this listing at \2",
                    text,
                    flags=re.IGNORECASE,
                )
        # R2: identity is tenant-bound — the advisor represents the brokerage, not
        # the platform. Rewrite possessive "Dalya's (property) advisor" everywhere
        # (LLM output + deterministic templates). The bot name "Dalya" still stands
        # in non-possessive openers ("Dalya with <brokerage> here").
        brokerage_label = ""
        if ctx:
            brokerage_label = (ctx.brokerage_short or ctx.brokerage_name or "").strip()
        if brokerage_label:
            text = re.sub(
                r"\bDalya'?s\s+(?:property\s+)?advisor\b",
                f"{brokerage_label}'s property advisor",
                text,
                flags=re.IGNORECASE,
            )
            # R12: collapse "<brokerage> at <brokerage>" / "at <brokerage> at <brokerage>"
            # doubling that survives the role-intro injection.
            b = re.escape(brokerage_label)
            text = re.sub(rf"\bat\s+{b}\s+at\s+{b}\b", f"at {brokerage_label}", text, flags=re.IGNORECASE)
            text = re.sub(rf"\b{b}\s+at\s+{b}\b", brokerage_label, text, flags=re.IGNORECASE)
            # R12 (P9 T8): collapse a second "managing this listing/property" role
            # clause appended to the agent's first role phrase.
            text = re.sub(
                rf"(managing this (?:listing|property)(?:\s+at\s+{b})?),\s*the agent managing this (?:listing|property)(?:\s+at\s+{b})?",
                r"\1",
                text,
                flags=re.IGNORECASE,
            )
            text = re.sub(
                rf"(agent managing this (?:listing|property)),\s*the agent managing (?:our|this|the) listings at {b}\b",
                r"\1",
                text,
                flags=re.IGNORECASE,
            )
        # AR: drop the mistranslated "finished condition" descriptor on off-plan
        # Arabic copy (the English path is handled above).
        if offplan_copy_hint:
            text = re.sub(
                r"(?:،|\.)?\s*(?:في|بحالة)\s+حالة\s+تام(?:ة)?\s+الصرف",
                " سيتم تسليمها بتشطيب كامل عند موعد التسليم",
                text,
            )
            text = re.sub(
                r"\bتام(?:ة)?\s+الصرف\b",
                "بتشطيب كامل عند موعد التسليم",
                text,
            )
        text = re.sub(r",(?=[A-Za-z])", ", ", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    # ── Phase 8.10: Promise-language → escalation invariant ───────────────────

    _PROMISE_PATTERNS = [
        r"i'?ve (?:forwarded|flagged|escalated)",
        r"i'?ll (?:forward|flag|escalate|route)",
        r"i'?m (?:forwarding|flagging|routing|escalating)",
        r"forwarding (?:this )?to (?:[A-Z][a-z]+|the listing agent|the managing agent)",
        r"flagging (?:this )?to (?:[A-Z][a-z]+|the listing agent|the managing agent)",
        r"routing (?:this )?to (?:[A-Z][a-z]+|the listing agent|the managing agent)",
        r"i'?ve (?:routed|sent|forwarded|flagged) (?:this|that|your request|your inquiry|your message)?\s*to (?:[A-Z][a-z]+|the listing agent|the managing agent)",
        r"(?:[A-Z][a-z]+|the listing agent|the managing agent|the agent) will (?:reach out|be in touch|follow up|contact you|review|verify|action|arrange|flag|coordinate|discuss)",
        r"they'?ll (?:reach out|be in touch|follow up|contact you|review|verify|action|arrange|flag|coordinate|discuss)",
        r"they will (?:reach out|be in touch|follow up|contact you|review|verify|action|arrange|flag|coordinate|discuss)",
        r"passed (?:this|your inquiry|your request|your message) (?:to|along to) (?:[A-Z][a-z]+|the listing agent|the managing agent)",
        r"i can arrange that",
        r"i can route this",
        r"i can get (?:the listing agent|the managing agent|[A-Z][a-z]+) to",
    ]

    @classmethod
    def _response_promises_forwarding(cls, response: str) -> bool:
        """Phase 8.10: Returns True if bot output contains forwarding-promise language."""
        if not response:
            return False
        return any(re.search(p, response, re.IGNORECASE) for p in cls._PROMISE_PATTERNS)

    _MATERIALS_PROMISE_PATTERNS = [
        r"\bi\s+can\s+(?:send|share|forward).{0,100}\b(?:floor\s*plans?|renders?|developer\s+renders?|brochures?|images?|photos?|visuals?|media)\b",
        r"\bi\s+can\s+(?:send|share|forward).{0,100}\bofficial\s+developer\b",
        r"\b(?:floor\s*plans?|renders?|brochures?).{0,80}\b(?:right now|send|share|forward)\b",
    ]

    @classmethod
    def _response_promises_materials(cls, response: str) -> bool:
        if not response:
            return False
        return any(re.search(p, response, re.IGNORECASE) for p in cls._MATERIALS_PROMISE_PATTERNS)

    @classmethod
    def _remove_unbacked_forwarding_claim(cls, response: str, conv=None) -> str:
        """Remove handoff claims when the system did not create an escalation."""
        if not response:
            return response
        fallback = render_refusal(intent=GATING, conv=conv).text
        sentence_patterns = [
            r"\bBefore\s+I\s+can\s+(?:arrange that|route this)[^.?!\n]*(?:[.?!]|$)",
            r"\bI'?ve\s+(?:forwarded|flagged|routed|sent|escalated)[^.?!\n]*(?:[.?!]|$)",
            r"\bI\s+have\s+(?:forwarded|flagged|routed|sent|escalated)[^.?!\n]*(?:[.?!]|$)",
            r"\bI'?ll\s+(?:forward|flag|route|escalate)[^.?!\n]*(?:[.?!]|$)",
            r"\bI\s+will\s+(?:forward|flag|route|escalate)[^.?!\n]*(?:[.?!]|$)",
            r"\bI'?m\s+(?:forwarding|flagging|routing|escalating)[^.?!\n]*(?:[.?!]|$)",
            r"\bI\s+can\s+(?:arrange that|route this)[^.?!\n]*(?:[.?!]|$)",
            r"\bThey'?ll\s+(?:reach out|be in touch|follow up|contact you|review|verify|action|arrange|flag|coordinate|discuss)[^.?!\n]*(?:[.?!]|$)",
            r"\bThey\s+will\s+(?:reach out|be in touch|follow up|contact you|review|verify|action|arrange|flag|coordinate|discuss)[^.?!\n]*(?:[.?!]|$)",
            r"\b(?:[A-Z][a-z]+|the listing agent|the managing agent|the agent)\s+will\s+"
            r"(?:reach out|be in touch|follow up|contact you|review|verify|action|arrange|flag|coordinate|discuss)[^.?!\n]*(?:[.?!]|$)",
        ]
        cleaned = response
        for pattern in sentence_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"\bBefore\s+I\s+need\s+a\s+clearer\s+buying\s+intent\b",
            "I need a clearer buying intent",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+([,.?!])", r"\1", cleaned)
        cleaned = re.sub(r"(?<!\n)\n(?!\n)", "\n", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip(" \n,")
        cleaned = cls._ensure_complete_sentence(cleaned)
        return cleaned or fallback

    @classmethod
    def _remove_unbacked_seller_handoff_claim(cls, response: str) -> str:
        """Remove fresh handoff claims from seller replies when an alert was deduped."""
        if not response:
            return response
        fallback = "Your dashboard remains the source of truth, and the listing agent has the thread context."
        sentence_patterns = [
            r"\bI'?ve\s+(?:forwarded|flagged|routed|sent|escalated)[^.?!\n]*(?:[.?!]|$)",
            r"\bI'?ll\s+(?:forward|flag|route|escalate)[^.?!\n]*(?:[.?!]|$)",
            r"\bI'?m\s+(?:forwarding|flagging|routing|escalating)[^.?!\n]*(?:[.?!]|$)",
            r"\bThey'?ll\s+(?:reach out|be in touch|follow up|contact you|review|verify|action|arrange|flag|coordinate|discuss)[^.?!\n]*(?:[.?!]|$)",
            r"\bThey\s+will\s+(?:reach out|be in touch|follow up|contact you|review|verify|action|arrange|flag|coordinate|discuss)[^.?!\n]*(?:[.?!]|$)",
            r"\b(?:[A-Z][a-z]+|the listing agent|the managing agent|the agent)\s+will\s+"
            r"(?:reach out|be in touch|follow up|contact you|review|verify|action|arrange|flag|coordinate|discuss)[^.?!\n]*(?:[.?!]|$)",
        ]
        cleaned = response
        for pattern in sentence_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+([,.?!])", r"\1", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip(" \n,")
        cleaned = cls._ensure_complete_sentence(cleaned)
        # R14: never leave a bare stub like "Got it." once the handoff sentence is
        # removed — the seller deserves a complete, state-aware acknowledgment that
        # the action is captured on the thread the agent already has.
        if len(cleaned.split()) <= 4:
            stub = cleaned.rstrip(".!? ").strip()
            prefix = f"{stub}. " if stub else ""
            cleaned = (
                f"{prefix}That's captured on the thread the listing agent already has open, "
                "so you won't need to repeat it. Your dashboard stays the source of truth."
            )
        return cleaned or fallback

    @staticmethod
    def _is_non_actionable_deflection(message: str, response: str) -> bool:
        if not message or not response:
            return False
        m = message.lower()
        r = response.lower()
        question_only_topics = [
            "noc", "lowest", "minimum", "flexibility", "offer history",
            "any offers", "service charge", "seller's position",
        ]
        if not any(topic in m for topic in question_only_topics):
            return False
        return any(phrase in r for phrase in [
            "will verify before",
            "can verify before",
            "will review if you put",
            "put a number forward",
            "if you want to put a number",
        ])

    @staticmethod
    def _rewrite_non_actionable_deflection(response: str, ctx: Optional[BrokerageContext] = None) -> str:
        """Keep process wording factual without claiming a fresh alert was opened."""
        brokerage = "the listing brokerage"
        if ctx:
            brokerage = ctx.brokerage_short or ctx.brokerage_name or brokerage
        response = re.sub(
            r"\b(?:[A-Z][a-z]+|the listing agent|the managing agent|the agent)\s+will\s+verify\s+before\b",
            f"{brokerage} verifies before",
            response,
            flags=re.IGNORECASE,
        )
        response = re.sub(
            r"\b(?:[A-Z][a-z]+|the listing agent|the managing agent|the agent)\s+can\s+verify\s+before\b",
            f"{brokerage} verifies before",
            response,
            flags=re.IGNORECASE,
        )
        response = re.sub(
            r"\b(?:[A-Z][a-z]+|the listing agent|the managing agent|the agent)\s+will\s+review\s+if\s+you\s+put\b",
            "The seller reviews actual offers when you put",
            response,
            flags=re.IGNORECASE,
        )
        return response

    @staticmethod
    def _seller_question_digest(seller_conv, current_message: str) -> str:
        """Compact seller-thread questions/actions for the alert payload."""
        messages = [
            (m.content or "").strip()
            for m in (getattr(seller_conv, "messages", None) or [])
            if getattr(m, "role", None) == "user" and (m.content or "").strip()
        ]
        if current_message and current_message.strip() not in messages:
            messages.append(current_message.strip())
        # Preserve order, drop duplicates, keep the latest five material asks.
        deduped = list(dict.fromkeys(messages))[-5:]
        return " | ".join(deduped)

    @staticmethod
    def _is_qualified_human_request(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        bare_listing_openers = [
            "calling about the property listing",
            "calling about the the property listing",
            "interested in the property listing",
            "about the property listing",
        ]
        if any(phrase in m for phrase in bare_listing_openers):
            return False
        return any(phrase in m for phrase in [
            "speak to",
            "talk to",
            "connect me",
            "real person",
            "real agent",
            "listing agent",
            "human",
            "call me",
            "callback",
            "call back",
            "viewing",
            "visit",
            "arrange",
            "schedule",
            "can i come",
            "kani come",
            "come tomorrow",
            "come tomorow",
        ])

    @staticmethod
    def _detect_viewing_request(message: str) -> bool:
        if not message:
            return False
        m = re.sub(r"\s+", " ", message.lower())
        return any(phrase in m for phrase in [
            "viewing",
            "view the property",
            "visit the property",
            "visit the unit",
            "come tomorrow",
            "come tomorow",
            "can i come",
            "can we come",
            "kani come",
            "kan i come",
            "schedule a visit",
            "arrange a visit",
            "come this saturday",
            "come saturday",
        ])

    @staticmethod
    def _extract_viewing_date_hint(message: str) -> Optional[str]:
        if not message:
            return None
        m = re.sub(r"\s+", " ", message.strip())
        for pattern in [
            r"\b(?:today|tomorrow|this\s+saturday|saturday|sunday|monday|tuesday|wednesday|thursday|friday)\b",
            r"\b\d{1,2}(?:am|pm)\b",
            r"\b\d{1,2}[:.]\d{2}\s*(?:am|pm)?\b",
        ]:
            match = re.search(pattern, m, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    @staticmethod
    def _detect_listing_fact_gap_request(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        return any(term in m for term in [
            "maid", "maid's room", "maids room", "floor plan", "layout",
            "furnished", "furnishing", "parking", "floor", "view",
            "pets", "pet", "occupancy", "occupied", "vacant",
            "vacant possession", "lease", "tenant", "tenancy", "ejari",
            "service charge", "plot", "orientation", "security", "cctv",
            "access control", "guard", "concierge",
        ])

    @staticmethod
    def _response_signals_info_gap(response: str) -> bool:
        if not response:
            return False
        m = response.lower()
        return any(phrase in m for phrase in [
            "i don't have that detail",
            "i don't have the exact",
            "i don't have that in the listing",
            "let me confirm",
            "i'll confirm",
            "worth confirming",
            "the listing agent can confirm",
            "will verify",
            "i need to verify",
        ])

    @staticmethod
    def _listing_text_sources(db_listing) -> str:
        if not db_listing:
            return ""
        spa_data = getattr(db_listing, "spa_data", None) or {}
        imported = spa_data.get("imported_listing") or {}
        community = getattr(db_listing, "community_data", None) or {}
        unit_profile = getattr(db_listing, "unit_profile", None) or {}
        reference_documents = getattr(db_listing, "reference_documents", None) or []
        knowledge_summary = getattr(db_listing, "knowledge_summary", None)
        facts = getattr(db_listing, "facts", None) or []
        fact_text = " ".join(
            str(getattr(fact, "value_text", "") or "")
            for fact in facts
            if getattr(fact, "buyer_safe", True)
        )
        parts = [
            imported.get("description"),
            " ".join(str(item) for item in imported.get("amenities") or []),
            str(community),
            str(unit_profile),
            str(reference_documents),
            str(getattr(knowledge_summary, "buyer_safe_summary", "") or ""),
            fact_text,
        ]
        return " ".join(part for part in parts if part).lower()

    @classmethod
    def _missing_listing_fact_topic(cls, db_listing, spa: SPAParseResult, message: str) -> Optional[str]:
        """Back-compat single-topic accessor — the first unmet topic, if any."""
        topics = cls._missing_listing_fact_topics(db_listing, spa, message)
        return topics[0] if topics else None

    @classmethod
    def _missing_listing_fact_topics(cls, db_listing, spa: SPAParseResult, message: str) -> list[str]:
        """ALL unmet listing-fact topics in a (possibly multi-part) question, so
        the escalation carries every item the buyer asked, not just the first (DAL-88)."""
        if not message:
            return []
        m = message.lower()
        text = cls._listing_text_sources(db_listing)
        refs = [
            str((doc or {}).get("kind") or (doc or {}).get("label") or "").lower()
            for doc in (getattr(db_listing, "reference_documents", None) or [])
        ]
        unit_profile = getattr(db_listing, "unit_profile", None) or {}
        facts = [
            fact for fact in (getattr(db_listing, "facts", None) or [])
            if getattr(fact, "buyer_safe", True)
        ]

        def _relevant_facts(keys: set[str], groups: set[str]) -> list:
            return [
                fact for fact in facts
                if getattr(fact, "fact_key", None) in keys or getattr(fact, "fact_group", None) in groups
            ]

        def _has_reliable_fact(keys: set[str], groups: set[str]) -> bool:
            return any(
                not getattr(fact, "risk_flag", False)
                and float(getattr(fact, "confidence", 0.0) or 0.0) >= 0.6
                for fact in _relevant_facts(keys, groups)
            )

        def _needs_fact_verification(keys: set[str], groups: set[str]) -> bool:
            relevant = _relevant_facts(keys, groups)
            return bool(relevant) and not _has_reliable_fact(keys, groups)

        topics: list[str] = []

        if any(term in m for term in ["service charge", "maintenance fee", "owners association", "oa fee"]):
            fact_keys = {"service_charge"}
            fact_groups = {"charges"}
            if _needs_fact_verification(fact_keys, fact_groups):
                topics.append("service charge verification")
            elif not ("service charge" in text or any("service" in ref for ref in refs) or _has_reliable_fact(fact_keys, fact_groups)):
                topics.append("service charge")

        if any(term in m for term in ["rental yield", "gross yield", "net yield", "roi", "rent this", "rental income"]):
            if not any(term in text for term in ["rental yield", "gross yield", "net yield", "annual rent", "rent estimate"]):
                topics.append("rental yield")

        if any(term in m for term in ["appreciation", "capital growth", "price growth", "resale premium"]):
            if not any(term in text for term in ["appreciation", "capital growth", "resale premium"]):
                topics.append("capital appreciation")

        if any(term in m for term in ["comparable", "comparables", "comps", "recent sale", "recent transactions"]):
            if not any(term in text for term in ["comparable", "recent sale", "transaction"]):
                topics.append("comparables")

        if "parking" in m or "parking spot" in m or "parking bay" in m:
            # Villas / townhouses: parking is within the plot — not a gap (R7).
            if not cls._is_villa_or_townhouse(spa):
                fact_keys = {"parking_allocation"}
                fact_groups = {"parking"}
                exact_parking = bool(spa.parking and str(spa.parking).strip())
                exact_in_text = bool(re.search(r"\b\d+\s+(?:allocated\s+)?parking\s+(?:bay|bays|spot|spots|space|spaces)\b", text))
                if _needs_fact_verification(fact_keys, fact_groups):
                    topics.append("parking allocation verification")
                elif not (exact_parking or exact_in_text or _has_reliable_fact(fact_keys, fact_groups)):
                    topics.append("parking allocation")

        if re.search(r"\b(?:which\s+)?floor\b|\blevel\b|\bstorey\b|\bstory\b", m):
            fact_keys = {"floor_level"}
            fact_groups = {"layout"}
            if _needs_fact_verification(fact_keys, fact_groups):
                topics.append("floor level verification")
            elif not (unit_profile and any(k in unit_profile for k in ["floor", "level", "storey"])):
                if not re.search(r"\b\d+(?:st|nd|rd|th)?\s+floor\b", text):
                    topics.append("floor level")

        if re.search(r"\bviews?\b|\boutlook\b|\bfacing\b", m):
            fact_keys = {"view_orientation"}
            fact_groups = {"layout"}
            has_view = any(term in text for term in ["sea view", "marina view", "lagoon view", "park view", "golf view", "view of"])
            has_profile_view = bool(unit_profile and any(k in unit_profile for k in ["view", "orientation", "exposure"]))
            if _needs_fact_verification(fact_keys, fact_groups):
                topics.append("view and orientation verification")
            elif not (has_view or has_profile_view or _has_reliable_fact(fact_keys, fact_groups)):
                topics.append("view and orientation")

        # Word boundaries so "please" does not match "lease" (R6).
        if re.search(r"\b(?:occupancy|occupied|vacant|tenant|tenanted|lease|leased|ejari)\b", m):
            # Off-plan stock is unfurnished/untenanted — answered deterministically (R9).
            if not cls._is_off_plan(db_listing, spa):
                fact_keys = {"occupancy_status", "lease_expiry"}
                fact_groups = {"occupancy"}
                if _needs_fact_verification(fact_keys, fact_groups):
                    topics.append("occupancy status verification")
                elif not (any(term in text for term in ["vacant", "tenant", "tenanted", "occupied", "ejari", "lease"]) or _has_reliable_fact(fact_keys, fact_groups)):
                    topics.append("occupancy status")

        if any(term in m for term in ["security", "cctv", "access control", "guard", "concierge", "resident-only", "resident only"]):
            fact_keys = {"building_rules"}
            fact_groups = {"building"}
            if _needs_fact_verification(fact_keys, fact_groups):
                topics.append("security and access verification")
            elif not (any(term in text for term in ["security", "cctv", "access control", "guard", "concierge", "resident-only", "resident only"]) or _has_reliable_fact(fact_keys, fact_groups)):
                topics.append("security and access details")

        return topics

    @staticmethod
    def _is_villa_or_townhouse(spa: SPAParseResult) -> bool:
        ptype = (getattr(spa, "property_type", "") or "").lower()
        if any(t in ptype for t in ["villa", "townhouse", "town house", "mansion"]):
            return True
        # A real plot area is a strong villa/townhouse signal.
        try:
            return bool(spa.plot_sqft and float(spa.plot_sqft) > 0)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _is_off_plan(db_listing, spa: SPAParseResult) -> bool:
        listing_type = (getattr(db_listing, "property_type", "") or "").lower()
        status = (getattr(spa, "property_status", "") or "").lower()
        if listing_type in {"ready"} or status in {"ready", "completed", "complete", "handed over"}:
            return False
        return listing_type in {"off_plan", "off-plan", "offplan"} or status in {"under construction", "under_construction", "off-plan", "off plan"}

    def _handle_deterministic_info_gap(
        self,
        *,
        db,
        conv,
        listing_id: str,
        buyer_phone: str,
        buyer_name: Optional[str],
        intent: BuyerIntent,
        message: str,
        topic: str,
        ctx: Optional[BrokerageContext] = None,
    ) -> tuple[str, Optional[EscalationAlert]]:
        pending = list(conv.pending_forwarded_questions or [])
        if message not in pending:
            pending.append(message)
            conv.pending_forwarded_questions = pending
            safe_commit(db)
            db.refresh(conv)

        digest = "\n".join(f"{idx + 1}. {q}" for idx, q in enumerate(pending))
        escalation = EscalationAlert(
            escalation_type="info_gap",
            priority="normal",
            conversation_id=conv.conversation_id,
            listing_id=listing_id,
            buyer_phone=buyer_phone,
            buyer_name=buyer_name,
            trigger=intent,
            trigger_message=digest,
            escalation_subtype="listing_fact_gap",
            payload={
                "topic": topic,
                "question_digest": digest,
                "requested_action": "Confirm the missing listing fact and reply to the buyer.",
            },
        )

        suppressed = self._should_suppress_non_offer_escalation(conv, escalation, db=db)
        identity_prefix = ""
        if not any(getattr(m, "role", None) == "assistant" for m in (getattr(conv, "messages", None) or [])):
            brokerage_label = (ctx.brokerage_short or ctx.brokerage_name) if ctx else "the listing brokerage"
            identity_prefix = f"{brokerage_label}'s property advisor here. "
        # Pet policy: give a sensible default rather than a bare deflection (DAL-88).
        pet_default = ""
        if re.search(r"\bpets?\b|\bdog\b|\bcat\b", (message or "").lower()):
            pet_default = (
                " On pets: most Dubai communities allow them subject to the owners-association rules "
                "(some apartments cap size or number), so plan on confirming the building's specific policy."
            )
        if suppressed:
            closer = self._vary([
                "I'll get that confirmed for you before you rely on it.",
                "I'll have that checked and come back to you with the specifics.",
                "Let me get the exact detail confirmed so you're not relying on a guess.",
            ], conv)
            response = (
                f"{identity_prefix}I don't have the exact {topic} in the listing record. "
                f"{closer}" + pet_default
            )
            escalation = None
        else:
            handoff = self._vary([
                "I've flagged it for {managing_agent_name} to confirm before you rely on it.",
                "I'm asking {managing_agent_name} to confirm that against current listing and market data.",
                "{managing_agent_name} needs to verify that detail before you rely on it.",
            ], conv)
            response = (
                f"{identity_prefix}I don't have the exact {topic} in the listing record. "
                f"{handoff}" + pet_default
            )
            self._record_escalation_state(db, conv, escalation)

        bot_response, _ = self._finalize_response(response, intent, conv, ctx=ctx)
        crud.add_message(
            db,
            conversation_id=conv.conversation_id,
            role=MessageRole.assistant.value,
            content=bot_response,
        )
        crud.update_conversation(db, conv)
        return bot_response, escalation

    # ── Deterministic factual responses ─────────────────────────────────────

    @staticmethod
    def _detect_remaining_payment_query(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        return any(phrase in m for phrase in [
            "payment plan",
            "payment schedule",
            "payment is left",
            "payment left",
            "remaining payment",
            "remaining developer",
            "instalment",
            "installment",
            "to whom do i pay",
            "what is left to pay",
            "what's left to pay",
            "left to complete",
        ])

    @staticmethod
    def _message_asks_price(message: str) -> bool:
        m = (message or "").lower()
        return any(term in m for term in ["price", "pricing", "asking", "cost", "how much", "kya hai"])

    @staticmethod
    def _detect_developer_quality_query(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        # Don't misfire on built-up area / size questions ("built" in "built-up").
        if re.search(r"\bbuilt[\s-]?up\b", m) or "bua" in m or "square f" in m or "sq ft" in m or "sqft" in m:
            return False
        if not re.search(r"\b(?:developer|develper|devloper|builder)\b", m):
            return False
        if any(term in m for term in ["payment", "pay", "paid", "instalment", "installment", "balance", "schedule"]):
            return False
        return any(term in m for term in ["good", "ok", "reliable", "reputation", "track record", "quality", "who", "build"])

    @staticmethod
    def _format_handover_date(value: Optional[str]) -> Optional[str]:
        """ISO 'YYYY-MM-DD' → natural 'Month YYYY'; pass other formats through."""
        if not value:
            return None
        v = str(value).strip()
        m = re.match(r"^(\d{4})-(\d{2})(?:-\d{2})?$", v)
        if m:
            months = ["", "January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
            try:
                return f"{months[int(m.group(2))]} {m.group(1)}"
            except (IndexError, ValueError):
                return v
        return v

    @classmethod
    def _compose_developer_quality_response(cls, spa: SPAParseResult, db_listing=None) -> Optional[str]:
        developer = (spa.developer or "").strip()
        if not developer and db_listing is not None:
            imported = (getattr(db_listing, "spa_data", None) or {}).get("imported_listing") or {}
            developer = str(imported.get("developer") or "").strip()
        if not developer:
            # Don't dodge with a project-name non-answer — let the model name the
            # developer from brand/community context (DAL-65 / Dmitri T4).
            return None
        if "emaar" in developer.lower():
            parts = [
                f"{developer} is one of Dubai's established developers, with landmark projects including Downtown Dubai and Burj Khalifa."
            ]
        else:
            parts = [f"The developer is {developer}, an established Dubai developer."]
        status = (getattr(spa, "property_status", "") or "").lower()
        is_ready = status in {"ready", "completed", "complete", "handed over"}
        handover = cls._format_handover_date(getattr(spa, "estimated_completion_date", None))
        if is_ready:
            parts.append("It's a ready, completed unit.")
        elif handover:
            parts.append(f"Handover is {handover}.")
        parts.append("Still verify the SPA and title/NOC position before you commit.")
        return " ".join(parts)

    @staticmethod
    def _detect_parking_query(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        return "parking" in m

    @staticmethod
    def _is_multi_feature_question(message: str) -> bool:
        """True for 'what's included' / multi-item feature asks, so a single-fact
        deterministic answer doesn't short-circuit the other items (DAL-86)."""
        if not message:
            return False
        m = message.lower()
        if any(p in m for p in ["what's included", "what is included", "whats included",
                                 "kya kya", "what all", "what else is included", "everything included"]):
            return True
        feature_terms = [
            "maid", "maid's", "study", "view", "floor", "balcony", "storage",
            "garden", "pool", "furnish", "kitchen", "laundry", "ensuite", "en-suite",
            "pets", "pet", "service charge", "appliance",
        ]
        hits = sum(1 for t in feature_terms if t in m)
        # parking + at least one other distinct feature term = multi-part
        return ("parking" in m and hits >= 1) or hits >= 2

    @classmethod
    def _compose_villa_parking_response(cls, spa: SPAParseResult) -> str:
        kind = "townhouse" if "townhouse" in (getattr(spa, "property_type", "") or "").lower() else "villa"
        return (
            f"Parking is within the {kind} itself, on the private plot — typically a driveway plus "
            "covered/garage spaces, so there's no separate allocated-bay count like an apartment has. "
            "The exact garage capacity is confirmed on a viewing."
        )

    @staticmethod
    def _detect_occupancy_query(message: str) -> bool:
        if not message:
            return False
        return bool(re.search(
            r"\b(?:occupancy|occupied|vacant|tenant|tenanted|lease|leased|ejari|furnished|furnishing|rented|rent it out|vacant possession|eviction|non-renewal|notice)\b",
            message.lower(),
        ))

    @staticmethod
    def _detect_handover_query(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        return bool(re.search(r"\b(?:handover|completion date|completion timeline|ready date|move[- ]?in|take possession)\b", m)) or (
            "new school year" in m or "school year" in m
        )

    @classmethod
    def _should_answer_handover_deterministically(cls, message: str) -> bool:
        """Only let the handover shortcut own handover-first asks.

        Multi-topic investor questions often mention "handover" as context
        while asking for yield, service charges, or remaining payment details.
        Those need the specific deterministic branch or info-gap escalation,
        not a one-line handover-date stub.
        """
        if not cls._detect_handover_query(message):
            return False
        m = (message or "").lower()
        competing_terms = [
            "rental yield", "gross yield", "net yield", "yield", "roi",
            "capital appreciation", "appreciation", "capital growth", "price growth",
            "service charge", "service charges", "maintenance fee", "maintenance fees",
            "owners association", "oa fee",
            "payment plan", "payment schedule", "payment is left", "payment left",
            "remaining payment", "remaining developer", "left to complete",
            "what is left to pay", "what's left to pay",
            "instalment", "installment",
        ]
        if any(term in m for term in competing_terms):
            return False
        return not cls._is_multi_feature_question(message)

    @classmethod
    def _compose_handover_response(cls, spa: SPAParseResult, message: str | None = None) -> str:
        handover = cls._format_handover_date(getattr(spa, "estimated_completion_date", None))
        if handover:
            response = f"Handover is {handover}."
            if message and any(term in message.lower() for term in ["school year", "new school year"]):
                response += " So it won't be ready for this school year."
            return response
        return "Handover is as per the SPA."

    @classmethod
    def _compose_ready_tenancy_response(cls, db_listing, message: str) -> Optional[str]:
        unit_profile = getattr(db_listing, "unit_profile", None) or {}
        tenancy = unit_profile.get("tenancy") or {}
        status = str(
            tenancy.get("status")
            or unit_profile.get("occupancy_status")
            or ""
        ).strip().lower()
        if not status:
            return None

        lease_start = cls._format_profile_month(tenancy.get("lease_start"))
        lease_end = cls._format_profile_month(tenancy.get("lease_end"))
        lease_range = ""
        if lease_start and lease_end:
            lease_range = f" The lease runs {lease_start} to {lease_end}."
        elif lease_end:
            lease_range = f" The lease ends {lease_end}."

        m = (message or "").lower()
        if "rent" in m or "yield" in m:
            return (
                f"It's currently {status}.{lease_range} I don't have a current rent or yield figure to rely on, "
                "so that needs to be verified from the Ejari/lease record before you underwrite it."
            )

        notice_line = (
            "Vacant possession is not automatic at lease expiry. For qualifying vacant-possession grounds in Dubai, "
            "the owner normally needs 12 months' notice served through notary public or registered mail, so verify "
            "whether that notice has already been served."
        )
        discussion_line = (
            "The owner can also speak with the tenant around 3 months before lease end about renewal or move-out, "
            "but that does not replace the statutory notice route."
        )

        if any(term in m for term in ["vacant possession", "move in", "moving in", "notice", "eviction", "vacant"]):
            return f"It's currently {status}.{lease_range} {notice_line}\n\n{discussion_line}"

        if "when" in m or "lease end" in m or "lease ends" in m:
            return (
                f"It's currently {status}.{lease_range} Treat that as the lease expiry, not a guaranteed vacancy date. "
                "Vacant possession depends on the lease/Ejari position and whether valid 12-month notice has been served."
            )

        return (
            f"It's currently {status}.{lease_range} The lease transfers with the property, so vacant possession at transfer "
            "is not available unless it is legally/documentarily agreed."
        )

    @staticmethod
    def _format_profile_month(value) -> Optional[str]:
        if not value:
            return None
        raw = str(value).strip()
        match = re.match(r"^(\d{4})-(\d{2})(?:-\d{2})?$", raw)
        if not match:
            return raw
        months = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        try:
            return f"{months[int(match.group(2))]} {match.group(1)}"
        except (IndexError, ValueError):
            return raw

    @staticmethod
    def _compose_offplan_occupancy_response(conv=None) -> str:
        prior_text = "\n".join(
            (getattr(m, "content", "") or "").lower()
            for m in (getattr(conv, "messages", None) or [])
            if getattr(m, "role", None) == "assistant"
        )
        if "off-plan unit" in prior_text and ("unfurnished" in prior_text or "untenanted" in prior_text):
            return (
                "Right, as mentioned - this is off-plan, so it should be unfurnished and vacant at handover "
                "with no current tenant or lease."
            )
        return (
            "It's an off-plan unit, so it's unfurnished and untenanted — there's no existing lease or "
            "occupant. You take handover with vacant possession and decide whether to live in it, "
            "furnish it, or rent it out from there."
        )

    # ── Live location intelligence (commute + nearby POIs) ───────────────────

    _COMMUTE_INTENT_RE = re.compile(
        r"\b(how far|how long|how many (?:minutes|mins)|distance|commute|drive time|"
        r"minutes? away|kitna (?:door|time|der)|time lagega|kitne der|kitna lagega)\b",
        re.IGNORECASE,
    )
    _COMMUTE_STOPWORDS = {
        "the", "community", "here", "there", "work", "office", "my", "your", "normal",
        "traffic", "peak", "hours", "commute", "it", "this", "that", "dubai", "from",
        "place", "home", "area",
    }
    _SCHOOL_CURRICULA = {
        "ib": "IB", "british": "British", "uk": "British", "american": "American",
        "us": "American", "indian": "Indian", "cbse": "CBSE (Indian)", "icse": "ICSE (Indian)",
        "french": "French", "german": "German", "gcse": "British",
    }

    @classmethod
    def _detect_location_request(cls, message: str) -> Optional[dict]:
        """Detect a buyer ask that warrants a live location lookup. Returns a
        dict describing the lookup, or None to leave it to the normal path."""
        if not message:
            return None
        m = message.lower()

        # POI category asks (specific nearby place types)
        if re.search(r"\b(school|schools|curriculum|kindergarten)\b", m):
            curriculum = None
            for token, label in cls._SCHOOL_CURRICULA.items():
                if re.search(rf"\b{re.escape(token)}\b", m):
                    curriculum = label
                    break
            return {"kind": "poi", "category": "school", "curriculum": curriculum}
        if re.search(r"\b(nursery|nurseries|daycare|day care|pre-?school)\b", m):
            return {"kind": "poi", "category": "nursery", "curriculum": None}
        if re.search(r"\b(hospital|hospitals|clinic|clinics|medical (?:centre|center)|healthcare|emergency room|er nearby)\b", m):
            return {"kind": "poi", "category": "healthcare", "curriculum": None}
        if re.search(r"\b(metro|metro station|subway|tram station)\b", m):
            return {"kind": "poi", "category": "transit", "curriculum": None}
        if re.search(r"\b(supermarket|grocery|groceries|spinneys|carrefour|waitrose)\b", m):
            return {"kind": "poi", "category": "supermarket", "curriculum": None}
        if re.search(r"\b(mall|shopping (?:mall|centre|center))\b", m):
            return {"kind": "poi", "category": "retail", "curriculum": None}

        # Commute to a named destination
        if cls._COMMUTE_INTENT_RE.search(m):
            dest = cls._extract_commute_destination(message)
            if dest:
                return {"kind": "commute", "destination": dest}
        return None

    @classmethod
    def _extract_commute_destination(cls, message: str) -> Optional[str]:
        # Prefer well-known all-caps area abbreviations (JLT, JBR, DIFC, DXB).
        for abbr in re.findall(r"\b([A-Z]{3,4})\b", message):
            if abbr.upper() not in {"AED", "DLD", "NOC", "SPA", "MOU", "RERA", "BRN", "PDPL"}:
                return abbr
        # Otherwise the proper-noun phrase after a locational preposition.
        match = re.search(
            r"\b(?:to|from|in|into|near|reach|at|towards|toward)\s+"
            r"((?:the\s+)?[A-Z][\w'&-]*(?:\s+[A-Z][\w'&-]*){0,3})",
            message,
        )
        if not match:
            return None
        dest = re.sub(r"^the\s+", "", match.group(1).strip(), flags=re.IGNORECASE).strip()
        tokens = [t for t in dest.split() if t.lower() not in cls._COMMUTE_STOPWORDS]
        dest = " ".join(tokens).strip(" ,.")
        if not dest or len(dest) < 2:
            return None
        return dest

    @staticmethod
    def _community_label(spa: SPAParseResult) -> str:
        return (getattr(spa, "sub_community", None) or getattr(spa, "project", None) or "this community").strip()

    def _compose_location_lookup(self, db, db_listing, spa, message: str) -> Optional[str]:
        """Cache-first → live → deterministic answer. Returns None to fall
        through to the normal path (cache already covers it, or lookup failed)."""
        from app.core import location_lookup as loc
        req = self._detect_location_request(message)
        if not req:
            return None
        label = self._community_label(spa)
        try:
            if req["kind"] == "commute":
                fact = loc.lookup_commute(db, db_listing, req["destination"])
                if not fact or not fact.drive_time_min:
                    return None
                km = f", ~{fact.distance_km:.0f} km" if fact.distance_km else ""
                safe_commit(db)
                return (
                    f"{fact.anchor_name} is about {fact.drive_time_min:.0f} min by car from {label}"
                    f"{km}, in typical traffic. Exact time varies with the hour and your start point."
                )

            curriculum = req.get("curriculum")
            if req["category"] == "school":
                text_query = (
                    f"{curriculum} curriculum school near {label} Dubai"
                    if curriculum else f"international schools near {label} Dubai"
                )
            else:
                noun = {
                    "nursery": "nursery", "healthcare": "hospital",
                    "transit": "metro station", "supermarket": "supermarket",
                    "retail": "shopping mall",
                }[req["category"]]
                text_query = f"{noun} near {label} Dubai"

            facts = loc.lookup_pois(
                db, db_listing,
                category=req["category"],
                text_query=text_query,
                curriculum=curriculum,
            )
            if not facts:
                return None  # cache already covers it (LLM answers) or nothing found
            safe_commit(db)
            return self._format_poi_facts(facts, label=label, category=req["category"], curriculum=curriculum)
        except Exception as exc:  # never let a lookup break the turn
            logger.warning("location_lookup failed listing=%s: %s", getattr(db_listing, "listing_id", "?"), exc)
            try:
                db.rollback()
            except Exception:
                pass
            return None

    @staticmethod
    def _format_poi_facts(facts, *, label: str, category: str, curriculum: Optional[str]) -> str:
        heading = {
            "school": f"{curriculum} schools near {label}" if curriculum else f"Schools near {label}",
            "nursery": f"Nurseries near {label}",
            "healthcare": f"Hospitals and clinics near {label}",
            "transit": f"Nearest metro to {label}",
            "supermarket": f"Supermarkets near {label}",
            "retail": f"Malls near {label}",
        }.get(category, f"Nearby {category}")
        lines = []
        for f in facts[:4]:
            bits = [f.name]
            detail = []
            if f.drive_time_min:
                detail.append(f"{f.drive_time_min:.0f} min")
            if category == "school":
                if f.curriculum:
                    detail.append(f.curriculum if "(" in f.curriculum else f"{f.curriculum} curriculum")
                if f.khda_rating:
                    detail.append(f"KHDA {f.khda_rating}")
            if detail:
                bits.append("- " + ", ".join(detail))
            lines.append("- " + " ".join(bits))
        body = "\n".join(lines)
        tail = ""
        if category == "school" and curriculum:
            tail = f"\n\nWorth confirming the curriculum with each school directly before you rely on it."
        return f"{heading}:\n\n{body}{tail}"

    @staticmethod
    def _detect_offplan_mortgage_query(message: str, db_listing, spa: SPAParseResult) -> bool:
        if not message:
            return False
        m = message.lower()
        if "no financing" in m or "no finance" in m:
            return False
        if re.search(r"\boffer\b", m) and re.search(r"\b(?:aed\s*)?\d", m):
            return False
        if not any(term in m for term in ["mortgage", "loan", "ltv", "finance", "financing", "bank"]):
            return False
        status = (spa.property_status or "").lower()
        property_type = (getattr(db_listing, "property_type", "") or "").lower()
        is_ready = property_type == "ready" or status in {"ready", "completed", "complete", "handed over"}
        return not is_ready

    @staticmethod
    def _compose_offplan_mortgage_response(asking_price: Optional[float] = None, verified_fact=None) -> str:
        price_prefix = f"The asking price is AED {asking_price:,.0f}. " if asking_price else ""
        if verified_fact is not None:
            source = ChatbotEngine._source_label_for_verified_fact(verified_fact)
            source_note = f" Source: {source}." if source else ""
            return (
                price_prefix +
                f"{verified_fact.text}{source_note} "
                "A mortgage advisor or bank should still confirm the exact policy before you make an offer."
            )
        return (
            price_prefix +
            "Off-plan properties may become eligible for a mortgage once construction reaches roughly 50% completion, "
            "at which point a bank can typically finance the remaining balance of the price. Whether this is available, "
            "and on what terms, depends on the specific developer and bank, so you should consult a mortgage advisor or "
            "bank to confirm the exact policy before you rely on it or make an offer."
        )

    @staticmethod
    def _detect_affordability_query(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        return any(term in m for term in ["afford", "affordability", "can i buy", "can i qualify"]) and any(
            term in m for term in ["earn", "income", "salary", "per month", "monthly"]
        )

    @staticmethod
    def _extract_monthly_income_aed(message: str) -> Optional[float]:
        if not message:
            return None
        m = message.lower().replace(",", "")
        match = re.search(r"(?:earn|income|salary|make)\s*(?:is\s*)?(?:aed\s*)?(\d+(?:\.\d+)?)\s*(k|thousand|m|million)?", m)
        if not match:
            match = re.search(r"(?:aed\s*)?(\d+(?:\.\d+)?)\s*(k|thousand|m|million)?\s*(?:per month|monthly|/month)", m)
        if not match:
            return None
        amount = float(match.group(1))
        unit = (match.group(2) or "").lower()
        if unit in {"k", "thousand"}:
            amount *= 1_000
        elif unit in {"m", "million"}:
            amount *= 1_000_000
        return amount if amount >= 1_000 else None

    @staticmethod
    def _compose_affordability_response(asking_price: float, monthly_income_aed: float) -> str:
        loan_amount = asking_price * 0.80
        monthly_rate = 0.05 / 12
        months = 25 * 12
        payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        if payment > monthly_income_aed:
            return (
                f"Based on AED {monthly_income_aed:,.0f} monthly gross income, this appears out of range by a wide margin. "
                f"A rough 80% mortgage on AED {asking_price:,.0f} would be around AED {payment:,.0f} per month before service charges, insurance, and other costs, which is above the income figure you gave. "
                "A mortgage advisor or bank should confirm eligibility before you spend time on an offer."
            )
        return (
            f"Based on AED {monthly_income_aed:,.0f} monthly gross income, a rough 80% mortgage on AED {asking_price:,.0f} would be around AED {payment:,.0f} per month before service charges and other costs. "
            "That needs a proper bank pre-approval before you rely on it."
        )

    @staticmethod
    def _detect_legal_advice_query(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        legal_terms = ["sue", "court", "legal risk", "liability", "lawsuit", "legal exposure"]
        obligation_terms = ["developer", "instalment", "installment", "payment", "spa", "contract"]
        return any(term in m for term in legal_terms) and any(term in m for term in obligation_terms)

    _CLOSING_PHRASES = [
        "think about it", "need to think", "let me think", "discuss with my",
        "discuss with family", "discuss with the family", "speak to my", "talk to my",
        "speak with my", "talk it over", "get back to you", "will come back",
        "i'll be in touch", "ill be in touch", "will be in touch", "come back to you",
        "no questions for now", "that's all for now", "thats all for now",
    ]

    @classmethod
    def _detect_closing_message(cls, message: str, conv=None) -> bool:
        """A pure sign-off ('thanks, I'll discuss with family') — no new ask."""
        if not message:
            return False
        m = message.lower().strip()
        if "?" in m:
            return False
        if not any(p in m for p in cls._CLOSING_PHRASES):
            return False
        # Don't fire on the very first message (it's an opener, not a close).
        if conv is not None and not any(
            getattr(x, "role", None) == "assistant" for x in (getattr(conv, "messages", None) or [])
        ):
            return False
        # Avoid mistaking a substantive ask that merely contains a closing phrase.
        ask_terms = ["price", "offer", "parking", "school", "payment", "mortgage", "noc",
                     "view", "floor", "fee", "yield", "handover", "service charge", "seller"]
        if any(t in m for t in ask_terms):
            return False
        return True

    @staticmethod
    def _compose_closing_signoff(message: str, conv=None) -> str:
        import hashlib
        variants = [
            "Of course, take your time. I'm here whenever you're ready, just message me.",
            "No problem at all. Have that conversation and reach out whenever you'd like to pick it up.",
            "Sounds good. Take the time you need, and I'm one message away when you want to continue.",
        ]
        idx = int(hashlib.md5((message or "x").encode()).hexdigest(), 16) % len(variants)
        return variants[idx]

    @staticmethod
    def _detect_religious_ruling_query(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        return any(term in m for term in ["halal", "haram", "fatwa", "sharia", "shariah"])

    @staticmethod
    def _detect_total_fees_query(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        fee_terms = any(phrase in m for phrase in [
            "total fees",
            "total cost",
            "all fees",
            "fees involved",
            "costs involved",
            "including your brokerage",
            "including brokerage",
            "dld",
            "brokerage fee",
            "your fee",
            "mahoroba fee",
            "الرسوم",
            "التكاليف",
            "تكلفة",
            "رسوم",
            "دائرة الأراضي",
            "الدائرة",
            "العمولة",
            "كم ادفع",
            "كم أدفع",
            "المبلغ الإجمالي",
        ])
        buying_context = any(phrase in m for phrase in [
            "buy",
            "buying",
            "at asking",
            "purchase",
            "transaction",
            "involved",
            "including",
            "cost",
            "fee",
            "شراء",
            "اشتري",
            "أشتري",
            "ادفع",
            "أدفع",
            "الرسوم",
            "التكاليف",
            "المبلغ",
        ])
        return fee_terms and buying_context

    @staticmethod
    def _format_due_date_for_buyer(due_date: Optional[str]) -> str:
        if not due_date:
            return "on completion"
        try:
            parsed = datetime.strptime(due_date, "%Y-%m-%d")
            return f"due {parsed.strftime('%B %Y')}"
        except ValueError:
            return f"due {due_date}"

    @classmethod
    def _remaining_instalment_lines(cls, spa: SPAParseResult) -> list[str]:
        today = datetime.utcnow().date()
        lines = []
        for inst in spa.payment_schedule or []:
            include = True
            if inst.due_date:
                try:
                    include = datetime.strptime(inst.due_date, "%Y-%m-%d").date() > today
                except ValueError:
                    include = True
            if include:
                lines.append(
                    f"- {inst.milestone}: AED {inst.amount_aed:,.0f}, "
                    f"{cls._format_due_date_for_buyer(inst.due_date)}"
                )
        return lines

    @classmethod
    def _compose_remaining_payment_response(
        cls,
        spa: SPAParseResult,
        property_type: Optional[str] = None,
        seller_asking_price: Optional[float] = None,
        ctx: Optional["BrokerageContext"] = None,
    ) -> str:
        ctx = ctx or legacy_default_context()
        status = (spa.property_status or "").lower()
        ready_prefix = (
            f"At the asking price of AED {seller_asking_price:,.0f}, this"
            if seller_asking_price else "This"
        )
        offplan_prefix = (
            f"At the asking price of AED {seller_asking_price:,.0f}, remaining"
            if seller_asking_price else "Remaining"
        )
        if property_type == "ready" or status in {"ready", "completed", "complete"} or not spa.payment_schedule:
            return (
                f"{ready_prefix} is a ready property, so there is no remaining developer payment plan shown for the buyer to take over. "
                "At purchase, the buyer-side costs are the agreed property price, DLD transfer fee, "
                f"{ctx.brokerage_short} fee, and any documented transaction line items. "
                "The listing agent can verify tenancy, service charge, and closing mechanics before offer stage."
            )
        paid = compute_paid_to_date(spa)
        developer = spa.developer or "the developer"
        lines = cls._remaining_instalment_lines(spa)
        schedule = "\n".join(lines) if lines else "- No remaining developer instalments are shown in the SPA."
        return (
            f"{offplan_prefix} to the developer is AED {paid['remaining_aed']:,.0f}. "
            f"The remaining {developer} schedule must be confirmed against the listing documents and transaction mechanics "
            f"by {ctx.managing_agent_name} before you rely on it.\n\n"
            f"Remaining SPA instalments:\n{schedule}\n\n"
            f"{ctx.managing_agent_name} will confirm any offer-stage closing cash and transaction mechanics "
            "before you rely on them."
        )

    @classmethod
    def _compose_total_fees_response(
        cls,
        spa: SPAParseResult,
        seller_asking_price: Optional[float],
        ctx: Optional["BrokerageContext"] = None,
        property_type: Optional[str] = None,
        language: str = "en",
        dld_fee_fact=None,
    ) -> str:
        if ctx is None:
            ctx = legacy_default_context()
        asking = seller_asking_price or spa.purchase_price_aed
        dld_pct = cls._percentage_from_verified_fact(dld_fee_fact)
        dld_source = cls._source_label_for_verified_fact(dld_fee_fact)
        brokerage_fee = asking * ctx.commission_rate
        dld_fee = asking * dld_pct if dld_pct is not None else None
        lifecycle_total = asking + (dld_fee or 0) + brokerage_fee
        status = (spa.property_status or "").lower()
        is_arabic = (language or "").lower().startswith("ar")
        if dld_pct is None or dld_fee is None:
            if is_arabic:
                return (
                    f"على سعر الطلب {asking:,.0f} درهم، أستطيع تأكيد سعر العقار ورسوم "
                    f"{ctx.brokerage_arabic or ctx.brokerage_short} ({ctx.commission_pct_label})، "
                    "لكن يجب أن يؤكد الوكيل رسوم دائرة الأراضي أو أي رسوم حكومية حالية قبل أن نعطي إجمالي نهائي."
                )
            return (
                f"At the asking price of AED {asking:,.0f}, I can confirm the property price and "
                f"{ctx.brokerage_short} fee ({ctx.commission_pct_label}), but the listing agent needs "
                "to confirm the current DLD/government transfer fees before I quote a final total."
            )
        dld_pct_label = f"{dld_pct * 100:g}%"
        dld_source_note = f", source: {dld_source}" if dld_source else ""
        if property_type == "ready" or status in {"ready", "completed", "complete"} or not spa.payment_schedule:
            if is_arabic:
                return (
                    f"على سعر الطلب {asking:,.0f} درهم، التقسيم هو:\n\n"
                    f"1. السعر المدفوع للبائع: {asking:,.0f} درهم\n"
                    f"2. رسوم دائرة الأراضي {dld_pct_label}: {dld_fee:,.0f} درهم ({dld_source or 'Verified Facts'})\n"
                    f"3. رسوم {ctx.brokerage_arabic or ctx.brokerage_short} ({ctx.commission_pct_label}): {brokerage_fee:,.0f} درهم\n\n"
                    "هذا عقار جاهز، لذلك لا يوجد جدول مدفوعات متبقية للمطور يتسلمه المشتري. "
                    "ولا توجد دفعة منفصلة بعنوان حقوق البائع فوق سعر الطلب. "
                    f"الإجمالي هو "
                    f"{lifecycle_total:,.0f} درهم."
                )
            return (
                f"At the asking price of AED {asking:,.0f}, the ready-resale breakdown is:\n\n"
                f"1. Price paid to seller: AED {asking:,.0f}\n"
                f"2. DLD transfer fee ({dld_pct_label}{dld_source_note}): AED {dld_fee:,.0f}\n"
                f"3. {ctx.brokerage_short} fee ({ctx.commission_pct_label}): AED {brokerage_fee:,.0f}\n\n"
                "This is a ready property, so there is no remaining developer payment schedule for the buyer to take over. "
                f"There is no separate seller-equity amount on top of the asking price. Total: AED {lifecycle_total:,.0f}."
            )
        if is_arabic:
            return (
                f"على سعر الطلب {asking:,.0f} درهم، تكاليف المشتري في الصفقة هي:\n\n"
                f"- رسوم دائرة الأراضي {dld_pct_label}: {dld_fee:,.0f} درهم ({dld_source or 'Verified Facts'})\n"
                f"- رسوم {ctx.brokerage_arabic or ctx.brokerage_short} ({ctx.commission_pct_label}): {brokerage_fee:,.0f} درهم\n\n"
                "سعر الطلب هو إجمالي سعر العقار، وليس مبلغاً إضافياً فوق رصيد المطور. "
                "تفاصيل مبالغ الإغلاق وأي آلية دفع متبقية خاصة بالصفقة ويجب تأكيدها من الوكيل قبل الاعتماد عليها.\n\n"
                f"إجمالي قيمة الشراء مع رسوم دائرة الأراضي ورسوم {ctx.brokerage_arabic or ctx.brokerage_short} هو "
                f"{lifecycle_total:,.0f} درهم."
            )
        return (
            f"At the asking price of AED {asking:,.0f}, the buyer-side transaction costs are:\n\n"
            f"- DLD transfer fee ({dld_pct_label}{dld_source_note}): AED {dld_fee:,.0f}\n"
            f"- {ctx.brokerage_short} fee ({ctx.commission_pct_label}): AED {brokerage_fee:,.0f}\n\n"
            f"The asking price is the total property price, not an amount on top of the SPA balance. "
            "Offer-stage closing cash and any remaining payment mechanics are transaction-specific, "
            f"so {ctx.managing_agent_name} will confirm them before you rely on them.\n\n"
            f"Across the transaction value, asking price + DLD + {ctx.brokerage_short} fee is "
            f"AED {lifecycle_total:,.0f}."
        )

    # ── Phase 6.1: Active listings block builder ──────────────────────────────

    @staticmethod
    def _build_active_listings_block(listings_brief: list) -> str:
        """Build a structured attribute block for semantic portfolio matching."""
        blocks = []
        for l in listings_brief:
            attrs = [
                f"  Project: {l['project']}",
                f"  Developer: {l['developer']}",
                f"  Type: {l['property_type']}",
            ]
            if l.get("bedrooms"):
                attrs.append(f"  Bedrooms: {l['bedrooms']}")
            price = l.get("asking_price_aed") or l.get("asking_price")
            if price:
                attrs.append(f"  Asking: AED {price:,.0f}")
            if l.get("location_descriptor"):
                attrs.append(f"  Location: {l['location_descriptor']}")
            if l.get("tags"):
                attrs.append(f"  Tags: {', '.join(l['tags'])}")
            lid_short = (l.get("listing_id") or "")[:12]
            blocks.append(f"LISTING ({lid_short}...):\n" + "\n".join(attrs))
        return "\n\n".join(blocks) if blocks else "(No active listings at this time)"

    @staticmethod
    def _detect_portfolio_list_request(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        if any(phrase in m for phrase in [
            "send me everything",
            "everything you have",
            "whole list",
            "full list",
            "all listings",
            "top 3 listings",
            "top three listings",
            "listings with prices",
            "what do you have",
            "current portfolio",
        ]):
            return True
        # DAL-85: "what other units/listings does <brokerage> have", "alternatives", etc.
        if re.search(
            r"\b(?:what\s+)?other\s+(?:units?|listings?|properties|stock|inventory|options)\b", m
        ) or re.search(
            r"\b(?:any\s+)?(?:other|similar|alternative)\s+(?:units?|listings?|properties|options)\b", m
        ):
            return True
        if re.search(r"\bwhat\s+(?:else|other).{0,30}\b(?:have|represent|list|offer)\b", m):
            return True
        return False

    @staticmethod
    def _requested_listing_limit(message: str) -> Optional[int]:
        if not message:
            return None
        m = message.lower()
        word_numbers = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
        }
        match = re.search(r"\btop\s+(\d{1,2})\b", m)
        if match:
            return max(1, min(int(match.group(1)), 10))
        for word, value in word_numbers.items():
            if re.search(rf"\btop\s+{word}\b", m):
                return value
        return None

    @staticmethod
    def _compose_portfolio_list_response(listings_brief: list, requested_limit: Optional[int] = None) -> str:
        if not listings_brief:
            return "We don't have active listings available to share right now."

        lines = []
        for listing in listings_brief:
            project = listing.get("project") or "Property"
            bedrooms = listing.get("bedrooms")
            bedroom_text = f"{bedrooms}-bed " if bedrooms else ""
            property_type = (listing.get("property_type") or "property").lower()
            if property_type in {"apartment", "apartments"}:
                property_type = "apt"
            elif property_type in {"villa", "villas"}:
                property_type = "villa"
            elif property_type in {"townhouse", "townhouses", "town house", "town houses"}:
                property_type = "townhouse"
            price = (
                listing.get("asking_price_aed")
                or listing.get("asking_price")
                or listing.get("price_aed")
            )

            descriptor = f"{project}"
            if listing.get("sub_community") and listing.get("sub_community") != project:
                descriptor += f" ({listing['sub_community']})"
            descriptor += f" - {bedroom_text}{property_type}"
            if price:
                descriptor += f", AED {price:,.0f}"
            else:
                descriptor += ", price on request"
            lines.append(f"- {descriptor}")

        if requested_limit:
            # State the ranking key so "top N" isn't just an opaque first-N (DAL-90).
            heading = f"Here are {len(lines)} of our current listings, ordered by value (highest asking first):"
        else:
            heading = "Here are our current listings:"
        return heading + "\n\n" + "\n".join(lines)

    @staticmethod
    def _rank_portfolio_brief(listings_brief: list) -> list:
        """Stable public portfolio order for "top N" requests.

        Until a true recommendation score is productized, rank by data
        completeness first, then higher asking price, then project/unit name.
        This makes "top 3" deterministic and explainable instead of returning
        whatever order the database happens to provide.
        """
        def score(listing: dict) -> tuple:
            completeness = sum(
                1 for key in (
                    "project", "developer", "property_type", "bedrooms",
                    "asking_price_aed", "location_descriptor",
                )
                if listing.get(key)
            )
            price = float(listing.get("asking_price_aed") or listing.get("asking_price") or 0)
            return (-completeness, -price, str(listing.get("project") or ""), str(listing.get("unit_number") or ""))

        return sorted(listings_brief, key=score)

    # ── Phase 1.1 / 6.1: No-listing portfolio-aware fallback ─────────────────

    def _handle_no_listing_fallback(
        self,
        inbound: InboundMessage,
        db,
    ) -> tuple:
        """
        Portfolio-aware fallback when no listing_id is matched.
        Injects ONLY real active listings with structured attributes so the model
        can do semantic matching (not just name matching). Escalates as
        general_lead_capture when buyer reveals criteria.
        """
        from app.models.db_models import DBConversation as _DBConv

        from app.models.db_models import DBBrokerage as _DBBrokerage

        brokerage = (
            db.query(_DBBrokerage)
            .filter(_DBBrokerage.brokerage_ai_number == inbound.to_number)
            .first()
            if inbound.to_number else None
        )
        brokerage_id = brokerage.brokerage_id if brokerage else None
        listings_brief = self._rank_portfolio_brief(
            crud.get_all_listings_brief(db, brokerage_id=brokerage_id)
        )
        active_listings_block = self._build_active_listings_block(listings_brief)

        if self._detect_portfolio_list_request(inbound.body):
            if not brokerage_id:
                response_text = (
                    "I need a specific brokerage or listing reference before I can enumerate inventory. "
                    "Share the listing link or message from that brokerage's property thread and I can narrow it properly."
                )
                response_text, _ = self._finalize_response(response_text, None, None)
                return response_text, None, None
            limit = self._requested_listing_limit(inbound.body)
            if limit is not None:
                listings_brief = listings_brief[:limit]
            response_text = self._compose_portfolio_list_response(listings_brief, requested_limit=limit)
            response_text, _ = self._finalize_response(response_text, None, None)
            return response_text, None, None

        if not brokerage_id:
            response_text = (
                "I don't have a listing reference on this thread, so I can't safely enumerate brokerage inventory. "
                "Send the listing link, building, or community you're asking about and I'll match it against the right portfolio."
            )
            response_text, _ = self._finalize_response(response_text, None, None)
            return response_text, None, None

        fallback_system = f"""You are Dalya, the Property Advisor for {brokerage.name}.

A buyer has messaged without a specific listing reference. Your job is to match their natural-language description against the active portfolio and respond honestly.

ACTIVE PORTFOLIO (these are the ONLY properties the listing brokerage currently represents):

{active_listings_block}

HOW TO MATCH BUYER DESCRIPTIONS TO PORTFOLIO:

Buyers describe properties in many ways: by developer, by community, by property type, by branding, by area, or by combinations such as a branded villa or an off-plan apartment.

When a buyer describes a property:
1. Check whether their description matches the attributes (developer, type, community, tags) of any active listing.
2. If yes — confirm honestly which listing(s) match and offer details.
3. If partial match — acknowledge what we have and what's different.
4. If no match — say so honestly and ask what else they're considering.

EXAMPLES:

Buyer: "Do you have anything in a waterfront community?"
Correct: mention only matching listings from ACTIVE PORTFOLIO, with their real community and asking price from the block above.
Wrong: inventing an adjacent community or naming a listing outside ACTIVE PORTFOLIO.

Buyer: "Branded villa"
Correct: if a represented listing matches, identify that listing from ACTIVE PORTFOLIO and say what matches. If none matches, say none of the current represented listings fit that description.

Buyer: "Studio in JLT"
Correct: if no active listing matches, say so directly and briefly describe the closest represented alternatives from ACTIVE PORTFOLIO if useful.

CRITICAL RULES:
- NEVER invent listings, communities, or properties Dalya doesn't represent.
- NEVER deny a listing whose attributes match the buyer's description.
- When a description partially matches, say what matches and what doesn't.
- When nothing matches, be honest and ask follow-up questions to understand what they want.
- Capture buyer criteria (budget, area, type, timeline) and have the managing agent reach out if the portfolio doesn't fit.

BRAND VOICE:
- No emojis.
- No markdown bold (**text**) or headers.
- Default to 1-3 sentences.
- If you ask multiple intake questions, put each question on its own line with "- ".
- If you list properties, each property gets its own line and includes asking price.
- Example:
  "Here's everything we have right now:

  - Mirage The Oasis - 6-bed villa, AED 21,693,243
  - Palmiera - 4-bed villa, AED 11,100,000
  - The Pinnacle at Sobha Central - 2-bed apt, AED 3,173,000"
- Direct, professional, restrained."""

        # Check message count across all conversations for this buyer (general lead quality signal)
        from sqlalchemy import select as _select, func as _func
        from app.models.db_models import DBConversation as _DBConv2, DBMessage as _DBMsg
        buyer_msg_count = db.execute(
            _select(_func.count(_DBMsg.id))
            .join(_DBConv2, _DBConv2.conversation_id == _DBMsg.conversation_id)
            .where(_DBConv2.buyer_phone == inbound.from_number)
            .where(_DBMsg.role == "user")
        ).scalar() or 0

        # Detect if buyer has revealed criteria: explicit budget/area/timeline mentions
        intent_data = detect_intent_claude(inbound.body)
        has_budget = bool(intent_data.get("extracted_budget"))
        has_area = bool(intent_data.get("extracted_area"))
        has_bedrooms = bool(intent_data.get("extracted_bedrooms"))
        criteria_revealed = has_budget or has_area or has_bedrooms
        is_engaged = (buyer_msg_count >= 3) or criteria_revealed

        fallback_response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=[{
                "type": "text",
                "text": fallback_system,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": inbound.body}],
        )
        response_text = fallback_response.content[0].text.strip()
        response_text, _ = self._finalize_response(response_text, None, None)

        escalation = None
        if is_engaged:
            escalation = EscalationAlert(
                escalation_type="general_lead_capture",
                priority="normal",
                listing_id=None,
                buyer_phone=inbound.from_number,
                buyer_name=intent_data.get("extracted_name"),
                trigger=BuyerIntent.general_enquiry,
                trigger_message=inbound.body,
                payload={
                    "criteria": {
                        "budget": intent_data.get("extracted_budget"),
                        "area": intent_data.get("extracted_area"),
                        "bedrooms": intent_data.get("extracted_bedrooms"),
                    },
                    "requested_action": "Qualify no-listing inbound against this brokerage's portfolio.",
                },
            )

        return response_text, escalation, None

    # ── Phase 1.2: Seller-mode detection and routing ──────────────────────────

    def _is_seller_messaging(self, inbound: InboundMessage, listing_id: str, db_listing) -> bool:
        """Return True if the inbound message is from the registered seller phone."""
        if not db_listing or not db_listing.seller_phone:
            return False

        def _normalize(p: Optional[str]) -> str:
            return re.sub(r"\D", "", p or "")

        return _normalize(inbound.from_number) == _normalize(db_listing.seller_phone)

    @staticmethod
    def _detect_claimed_seller_context(message: str) -> bool:
        """True when an unverified sender is explicitly speaking as the seller/owner."""
        if not message:
            return False
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in [
            r"\b(?:i am|i'm|im)\s+(?:the\s+)?(?:owner|seller|vendor)\b",
            r"\bowner\s+of\s+(?:the\s+)?(?:unit|property|listing)\b",
            r"\bmy\s+(?:unit|property|listing)\b",
            r"\b(?:i|we)\s+(?:own|listed|am selling|are selling)\b",
            r"\bregistered\s+(?:owner|seller)\b",
        ])

    # ── Phase 7.6.5b / 7.6.7c: signal-based escalation detection ──────────────

    _CO_BROKER_COMPLIANCE_PATTERNS = [
        r"\bform\s*a\b",
        r"listing\s+authorization",
        r"trakheesi\s+(?:permit|number|certificate)",
        r"rera\s+(?:registration|documentation|certificate|verification|card\b)",
        r"brn\s+(?:of\s+(?:the\s+)?(?:agent|listing)|verification)",
        r"compliance\s+verification",
    ]

    _SELLER_CONTACT_REQUEST_PATTERNS = [
        r"(?:seller|owner|ownr|vendor)['’]?(?:s)?\s+(?:number|phone|whatsap|whatsapp|email|contact|mobile|full name|name)",
        r"seller['’]?s?\s+(?:brother|family|relative|friend).{0,40}(?:number|phone|whatsap|whatsapp|email|contact|mobile)",
        r"(?:speak|talk|deal|connect|reach|message|text|contact)\s+(?:to|with)?\s*(?:the\s+)?(?:seller|owner|ownr|vendor)\s+direct",
        r"(?:share|send|give|forward).{0,40}(?:seller|owner|ownr|vendor).{0,30}(?:number|phone|whatsap|whatsapp|email|contact|mobile)",
        r"(?:seller|owner|ownr|vendor).{0,40}(?:number|phone|whatsap|whatsapp|email|contact|mobile)",
        r"seller now",
        r"(?:رقم|هاتف|جوال|واتساب|ايميل|إيميل).{0,30}(?:البائع|المالك)",
        r"(?:البائع|المالك).{0,30}(?:رقم|هاتف|جوال|واتساب|ايميل|إيميل|مباشرة)",
        r"(?:اعطني|أعطني|ارسل|أرسل).{0,40}(?:رقم|هاتف|جوال|واتساب).{0,30}(?:البائع|المالك)",
    ]

    _OUT_OF_SCOPE_REFUSAL_PATTERNS = [
        r"ignore (?:your|all|previous) instructions",
        r"system prompt",
        r"developer mode",
        r"jailbreak",
        r"print your prompt",
        r"reveal your prompt",
        r"forget the rules",
        r"bypass the transaction",
        r"skip the brokerage",
        r"skip the broker",
        r"deal direct",
    ]

    _DOCUMENT_DISCLOSURE_REQUEST_PATTERNS = [
        r"(?:share|send|give|forward|show).{0,40}\b(?:spa|soa|noc|title deed|passport|emirates id|eid|mou|contract|document|docs)\b",
        r"\b(?:spa|soa|noc|title deed|passport|emirates id|eid|mou|contract|document|docs)\b.{0,40}(?:share|send|give|forward|show)",
        r"seller['’]?s?\s+(?:passport|emirates id|eid|documents?|docs?)",
    ]

    _BUYER_PRIVACY_REFUSAL_VARIANTS_EN = [
        "I can't share SPA, SOA, NOC, title-deed, or private transaction documents over WhatsApp. Those move through the brokerage and conveyancing channel once offer terms are accepted.",
        "Private sale documents don't go out in chat. After accepted terms, the listing agent and conveyancer handle the SPA/SOA/NOC document exchange through the formal transaction path.",
        "Those documents are not shared over WhatsApp before accepted terms. The formal transaction channel handles document review once an offer is agreed.",
        "I can discuss public unit facts here, but not private SPA/SOA/title documents. Those are exchanged through the brokerage and conveyancing process after acceptance.",
    ]
    _BUYER_PRIVACY_REFUSAL_VARIANTS_AR = [
        "لا يمكنني مشاركة بيانات البائع أو مستندات الصفقة الخاصة عبر واتساب. يتم تبادلها عبر شركة الوساطة والناقل القانوني بعد قبول العرض.",
        "بيانات البائع تبقى خاصة. عند قبول العرض، تنتقل المستندات والتنسيق عبر القنوات الرسمية للوساطة وإنهاء الصفقة.",
        "لا أستطيع توصيلك مباشرة بالبائع أو مشاركة مستندات خاصة هنا. هذه الأمور تتم عبر مسار الصفقة الرسمي بعد الاتفاق على الشروط.",
    ]
    _SELLER_SIDE_PRIVACY_VARIANTS_EN = [
        "I can't share buyer or inquirer contact details over WhatsApp. Serious-inquiry details stay in your authenticated dashboard, and {managing_agent_name} can walk you through them.",
        "Buyer details are not shared in chat. The dashboard keeps that data authenticated, and {managing_agent_name} can review serious inquiries with you directly.",
        "I keep buyer contact details out of WhatsApp for privacy. Use the dashboard for the full lead record, and {managing_agent_name} can talk through the active inquiries.",
    ]
    _SELLER_SIDE_PRIVACY_VARIANTS_AR = [
        "لا يمكنني مشاركة بيانات المشترين أو المستفسرين عبر واتساب. التفاصيل الكاملة تبقى في لوحة التحكم الموثقة، ويمكن للوكيل المسؤول مراجعتها معك.",
        "تفاصيل المشترين لا تُشارك في المحادثة حفاظاً على الخصوصية. لوحة التحكم هي المكان الصحيح للاطلاع عليها.",
    ]

    _NEW_LISTING_INQUIRY_PATTERNS = [
        r"\bif\s+i\s+(?:were\s+to\s+)?list\b(?:.*?)(?:mahoroba|with\s+you|here)",
        r"\bif\s+i\s+list\s+with\s+[A-Z][A-Za-z ]+\b",
        r"\bif\s+i\s+sell(?:.*?)(?:mahoroba|with\s+you|here)",
        r"(?:want|thinking|considering|plan)\s+(?:to|of|about)\s+(?:listing|selling)\s+(?:my|our)\s+(?:unit|villa|apartment|property|place)",
        r"(?:want|thinking|considering|plan)\s+(?:to|of|about)\s+(?:listing|selling)\s+mine\b",
        r"\bi\s+own\s+unit\s+\w+.{0,80}\b(?:list|listing|sell|selling)\b",
        r"how\s+(?:does|do)\s+(?:your|mahoroba['’]?s?)\s+(?:fee|commission|process)\s+(?:work\s+)?for\s+sellers?",
        r"how\s+(?:much|do)\s+(?:do\s+)?you\s+charge\s+(?:for\s+)?sellers?",
        r"list(?:ing)?\s+(?:my|our|the)\s+(?:unit|villa|apartment|property)\s+with",
    ]

    @classmethod
    def _detect_co_broker_compliance(cls, message: str) -> bool:
        """Phase 7.6.5b: Form A / RERA / listing authorization request detection."""
        return any(re.search(p, message, re.IGNORECASE) for p in cls._CO_BROKER_COMPLIANCE_PATTERNS)

    @classmethod
    def _detect_seller_contact_request(cls, message: str) -> bool:
        """True when the buyer/professional is trying to get direct seller contact."""
        if not message:
            return False
        return any(
            re.search(p, message, re.IGNORECASE)
            for p in cls._SELLER_CONTACT_REQUEST_PATTERNS
        )

    @classmethod
    def _continues_seller_contact_probe(cls, conv, message: str) -> bool:
        if not conv or not message:
            return False
        m = message.lower().strip()
        if not re.search(r"\b(?:number|digits|contact|whatsap|whatsapp|mobile|phone)\b", m):
            return False
        prior_probe = any(
            getattr(msg, "role", None) == "user"
            and cls._detect_seller_contact_request(getattr(msg, "content", "") or "")
            for msg in (getattr(conv, "messages", None) or [])[:-1]
        )
        return prior_probe and len(m.split()) <= 14

    @classmethod
    def _detect_out_of_scope_refusal_request(cls, message: str) -> bool:
        if not message:
            return False
        return any(
            re.search(p, message, re.IGNORECASE)
            for p in cls._OUT_OF_SCOPE_REFUSAL_PATTERNS
        )

    @classmethod
    def _detect_document_disclosure_request(cls, message: str) -> bool:
        if not message:
            return False
        return any(
            re.search(p, message, re.IGNORECASE)
            for p in cls._DOCUMENT_DISCLOSURE_REQUEST_PATTERNS
        )

    @staticmethod
    def _next_refusal_state(conv, refusal_class: str) -> tuple[int, set[str], bool]:
        summary = dict(getattr(conv, "ai_summary", None) or {})
        states = dict(summary.get("refusal_state") or {})
        state = dict(states.get(refusal_class) or {})
        try:
            count = int(state.get("count") or 0) + 1
        except (TypeError, ValueError):
            count = 1
        used_lines = {
            str(line).strip()
            for line in (state.get("used_lines") or [])
            if str(line).strip()
        }
        already_escalated = bool(state.get("escalated"))
        return count, used_lines, already_escalated

    @staticmethod
    def _store_refusal_state(conv, refusal_class: str, decision) -> None:
        summary = dict(getattr(conv, "ai_summary", None) or {})
        states = dict(summary.get("refusal_state") or {})
        state = dict(states.get(refusal_class) or {})
        prior_used = [
            str(line).strip()
            for line in (state.get("used_lines") or [])
            if str(line).strip()
        ]
        text = (getattr(decision, "text", "") or "").strip()
        used_lines = list(dict.fromkeys([*prior_used, text]))[-20:]
        states[refusal_class] = {
            "count": int(getattr(decision, "ask_count", 0) or 0),
            "used_lines": used_lines,
            "escalated": bool(state.get("escalated") or getattr(decision, "should_escalate", False)),
        }
        summary["refusal_state"] = states
        conv.ai_summary = summary

    @staticmethod
    def _is_arabic_text(text: str) -> bool:
        return bool(text and re.search(r"[\u0600-\u06FF]", text))

    @classmethod
    def _choose_thread_variant(cls, variants: list[str], conv=None) -> str:
        """Pick a non-repeated variant when conversation history is available."""
        if not variants:
            return ""
        used = {
            (m.content or "").strip()
            for m in (getattr(conv, "messages", None) or [])
            if getattr(m, "role", None) == "assistant"
        }
        for variant in variants:
            if variant.strip() not in used:
                return variant
        # Rotate deterministically once every variant has appeared.
        return variants[len(used) % len(variants)]

    @classmethod
    def _compose_privacy_refusal(
        cls,
        message: str,
        *,
        conv=None,
        ctx: Optional[BrokerageContext] = None,
        seller_side: bool = False,
        ask_count: Optional[int] = None,
        used_texts: Optional[set[str]] = None,
    ) -> str:
        is_arabic = cls._is_arabic_text(message)
        if seller_side:
            variants = (
                cls._SELLER_SIDE_PRIVACY_VARIANTS_AR
                if is_arabic else cls._SELLER_SIDE_PRIVACY_VARIANTS_EN
            )
        else:
            variants = (
                cls._BUYER_PRIVACY_REFUSAL_VARIANTS_AR
                if is_arabic else cls._BUYER_PRIVACY_REFUSAL_VARIANTS_EN
            )
        if used_texts:
            text = next((variant for variant in variants if variant.strip() not in used_texts), "")
            if not text:
                text = variants[((ask_count or 1) - 1) % len(variants)]
        elif ask_count:
            text = variants[(ask_count - 1) % len(variants)]
        else:
            text = cls._choose_thread_variant(variants, conv)
        if ctx:
            text = cls._apply_brokerage_substitutions(text, ctx)
        return text

    @classmethod
    def _compose_out_of_scope_refusal(cls, message: str) -> str:
        if cls._is_arabic_text(message):
            return (
                "أنا أتعامل فقط مع هذا العقار: السعر، المواصفات، الدفعات، إجراءات النقل، "
                "والخطوات الجدية للشراء. لا أستطيع المساعدة في مطالبات تتعلق بتعليمات داخلية أو تجاوز مسار الصفقة."
            )
        return (
            "I only handle this listing: price, specs, payment, transfer process, and genuine next steps. "
            "I can't help with internal-instruction requests or attempts to bypass the transaction process."
        )

    # Phase 9.6: BRN-specific patterns — distinct from Form A / listing authorization
    _BRN_REQUEST_PATTERNS = [
        r"\bbrn\b",
        r"broker\s+registration\s+number",
        r"agent['’]?s?\s+brn",
        r"rera\s+card",
        r"agent\s+registration\s+number",
    ]

    @classmethod
    def _detect_brn_only_request(cls, message: str) -> bool:
        """Phase 9.6: BRN/RERA-card requests are distinct from Form A documentation
        requests. A message that mentions BRN/RERA card without explicitly asking
        for Form A or listing authorization should route to a BRN-specific
        escalation with proactive forwarding language."""
        if not message:
            return False
        # Only treat as BRN-only if it does NOT also explicitly ask for Form A
        if re.search(r"\bform\s*a\b|listing\s+authorization", message, re.IGNORECASE):
            return False
        return any(re.search(p, message, re.IGNORECASE) for p in cls._BRN_REQUEST_PATTERNS)

    # Phase 9.10: Returning-buyer claim patterns
    _RETURNING_BUYER_PATTERNS = [
        r"\b(?:i\s+)?messaged?\s+(?:about\s+)?(?:this|that)\s+(?:property|unit|listing)",
        r"\b(?:we\s+)?(?:spoke|talked|chatted)\s+(?:to|with)\s+you",
        r"\bfew\s+(?:weeks?|days?|months?)\s+ago\b",
        r"\bdid\s+you\s+hear\s+back\b",
        r"\bfollow\s+up\s+on\s+my\b",
        r"\bmy\s+offer\s+(?:of|from)\b",
        r"\b(?:last|previous|prior)\s+(?:time|conversation|chat|message)\b",
        r"\bremember\s+me\b",
        r"\bcoming\s+back\s+(?:to|on|about)\b",
        r"\bcircling\s+back\b",
        r"\bwe['’]ve\s+(?:spoken|talked)\s+before\b",
    ]

    @classmethod
    def _detect_returning_buyer_claim(cls, message: str) -> bool:
        """Phase 9.10: True if the buyer's message references a prior conversation
        or offer on this listing. Triggers OfferRecord lookup + early escalation."""
        if not message:
            return False
        return any(
            re.search(p, message, re.IGNORECASE)
            for p in cls._RETURNING_BUYER_PATTERNS
        )

    @classmethod
    def _detect_new_listing_inquiry(cls, message: str) -> bool:
        """Phase 7.6.7c: existing owner asking about LISTING with Mahoroba."""
        return any(re.search(p, message, re.IGNORECASE) for p in cls._NEW_LISTING_INQUIRY_PATTERNS)

    def _classify_seller_intent(self, message: str) -> str:
        """Keyword-based seller intent classification."""
        msg = message.lower()

        # Material actions
        if self._detect_seller_request_for_buyer_details(message):
            return "buyer_privacy_request"
        if any(kw in msg for kw in ["what's my net", "what is my net", "net after", "net proceeds", "after all fees"]):
            return "net_proceeds"
        if any(kw in msg for kw in ["accept the", "let's go with", "i agree", "we agree", "accept offer"]):
            return "offer_acceptance"
        if any(kw in msg for kw in ["counter at", "tell them", "come back with", "counter offer", "counteroffer"]):
            return "counter_offer"
        if any(kw in msg for kw in [
            "take it off", "take off the market", "pause", "withdraw",
            "remove the listing", "delist", "pause listing",
        ]):
            return "listing_status_change"
        if any(kw in msg for kw in [
            "don't drop", "do not drop", "don't lower", "do not lower",
            "wait", "let me think", "think about it overnight",
            "hold off",
        ]):
            return "seller_pause"
        if any(kw in msg for kw in [
            "notify everyone", "notify buyers", "notify active",
            "message everyone", "message buyers", "send everyone",
            "buyers who inquired", "everyone who's inquired", "everyone who inquired",
            "active inquirers", "last 30 days about the price drop",
        ]):
            return "buyer_outreach_request"
        if any(kw in msg for kw in [
            "should i drop", "what should i", "recommend", "advice",
            "improve", "attract more", "what do you think", "your opinion",
        ]):
            return "advisory_question"
        # R13: questions ABOUT the effect of a change are advisory, not a change
        # request — they must not get the dashboard-redirect boilerplate.
        if "?" in msg or any(q in msg for q in ["what does", "what happens", "how does", "will it", "would it"]):
            if any(kw in msg for kw in [
                "mean for", "what does dropping", "what happens to", "impact on",
                "affect the offer", "affect our offer", "affect the existing",
                "do to the offer", "for the offers", "for our offers",
                "to the offers we", "mean for the offer",
            ]):
                return "advisory_question"

        # Routine actions (Phase 9.8: broader coverage of listing-change phrasings)
        if any(kw in msg for kw in [
            "change the price to", "drop the asking", "drop the price",
            "raise the price", "raise the asking",
            "update the price", "update my listing", "update the listing",
            "set asking", "new price", "price to", "asking price to",
            "lower the price", "lower the asking", "reduce the price",
            "make that change", "make the change", "proceed with the drop",
            "proceed with the price", "dropping the price", "price drop",
        ]):
            return "price_update"
        if any(kw in msg for kw in [
            "set threshold", "escalate above", "minimum offer",
            "threshold", "notify me above", "set a threshold",
            "willing to negotiate down to", "willing to negotiate to",
            "willing to accept down to", "minimum acceptable",
        ]):
            return "threshold_update"

        # Performance metrics
        if any(kw in msg for kw in [
            "how is", "any offers", "any inquiries", "performance",
            "metrics", "how many", "interest level", "views", "leads",
        ]):
            return "performance_metrics"

        return "general_seller_question"

    @staticmethod
    def _detect_seller_request_for_buyer_details(message: str) -> bool:
        if not message:
            return False
        m = message.lower()
        return any(phrase in m for phrase in [
            "buyer details",
            "buyer contact",
            "buyer phone",
            "buyer number",
            "inquirer details",
            "inquirer contact",
            "inquiries details",
            "who inquired",
            "who asked",
            "send me their",
            "share their number",
            "share the buyer",
        ])

    def _compute_activity_signal(self, listing_id: str, db) -> str:
        """
        Phase 7.7: Return ONE qualitative descriptor of listing activity. No numbers.

        WhatsApp is not the right surface for offer history, buyer engagement metrics,
        or any data that constitutes a competitive/commercial asset. The dashboard
        (dalya.ai/dashboard) is. This helper returns a coarse bucket the seller can
        get value from without leaking specifics.
        """
        from app.models.db_models import DBConversation as _DBConv, DBOfferRecord as _DBOffer

        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        inquiries = (
            db.query(_DBConv)
            .filter(_DBConv.listing_id == listing_id)
            .count()
        )
        offers = (
            db.query(_DBOffer)
            .filter(_DBOffer.listing_id == listing_id)
            .count()
        )
        recent_activity = (
            db.query(_DBConv)
            .filter(
                _DBConv.listing_id == listing_id,
                _DBConv.updated_at >= seven_days_ago,
            )
            .count()
        ) > 0

        has_offers = offers > 0

        if has_offers and recent_activity:
            return "Your listing has active buyer interest with offers in play."
        if has_offers:
            return "Your listing has offers on the table though traffic has eased in the last week."
        if recent_activity and inquiries >= 3:
            return "Your listing is getting active buyer interest."
        if recent_activity:
            return "Your listing is getting initial buyer interest."
        if inquiries == 0:
            return "Your listing is live and the dashboard remains the source of truth for activity."
        return "Your listing has had limited recent activity."

    def _handle_seller_message(
        self,
        inbound: InboundMessage,
        listing_id: str,
        db_listing,
        spa,
        db,
    ) -> tuple:
        """
        Route authenticated seller messages. Returns (response, escalation, media_url).
        Passes conversation history to Claude so repeated-metric responses vary naturally.
        """
        from app.models.db_models import DBConversation as _DBConv, DBOfferRecord as _DBOffer
        from sqlalchemy import func as _func

        seller_intent = self._classify_seller_intent(inbound.body)

        MATERIAL_INTENTS = {
            "offer_acceptance", "counter_offer", "listing_status_change",
            "advisory_question", "net_proceeds", "buyer_privacy_request",
        }
        ROUTINE_INTENTS = {"price_update", "threshold_update", "listing_edit"}

        project = spa.project or "your property"
        unit = spa.unit_number or ""

        # Resolve multi-tenant context for the seller-mode prompt's
        # {brokerage_short} / {managing_agent_name} / {commission_pct_label}
        # placeholders. Falls back to Mahoroba/Eric defaults if the listing
        # has no brokerage_id (legacy data).
        ctx_seller = context_for_listing(listing_id, db)

        # Phase 8.9: Persist seller messages so the privacy-explanation flag works
        # across turns. Previously seller-mode messages weren't being added to the DB,
        # so every turn looked like the first to the metric-redirect handler.
        seller_conv = crud.get_or_create_conversation(db, inbound.from_number, listing_id)
        crud.add_message(
            db,
            conversation_id=seller_conv.conversation_id,
            role=MessageRole.user.value,
            content=inbound.body,
        )

        seller_system = f"""You are Dalya speaking with the AUTHENTICATED SELLER of {project} {unit}.

BRAND VOICE (mandatory):
- Direct, professional, restrained — like a senior broker, not a chatbot.
- No exclamation marks unless the seller used them first.
- No "Hello! Thanks for reaching out!" openers.
- No emojis.
- No markdown bold (**text**), no markdown headers (# ##).
- No bullet lists. Use prose with line breaks if multiple data points.
- Use complete sentences. Brevity over performative helpfulness.

TONE EXAMPLES:

Bad: "Hello! Thank you for reaching out. I've noted that you'd like to **accept the AED 17,000,000 offer**. **{{managing_agent_name}} will be in touch with you shortly** to action the offer acceptance."
	Good: "Got it. {{managing_agent_name}} will action the AED 17M acceptance and be in touch shortly to walk through next steps. They will verify the offer terms and send you the full payout table."

Bad: "I'd be happy to help! However, I need a bit more context.

Which change would you like to make?
- **Listing price adjustment?**
- **Threshold change?**
- **Status update?**"
Good: "What change are you looking to make — price, threshold, or listing status? You can update any of those directly at dalya.ai/dashboard."

NEVER WRITE:
- "Hello!" or "Hi there!" with an exclamation mark
- "Thank you for reaching out"
- "I'd be happy to help"
- "Great question!"
- Markdown headers (## **anything**)
- Bullet lists with bold items
- "Here's what I can do for you:" followed by a list

SELLER-MODE RULES (HARD):
- For listing changes (price, threshold, status, photos, description), direct them to dalya.ai/dashboard. The dashboard is the source of truth — changes take effect immediately there. Do NOT action listing changes through chat.
- For material actions (offer acceptance, counter-offers, listing pauses), acknowledge and tell them {{managing_agent_name}} will reach out shortly to action it. {{managing_agent_name}} will be in direct contact for substantive negotiations.
- For advisory questions ("should I drop the price?", "how do I attract more buyers?"), acknowledge and tell them {{managing_agent_name}} will reach out personally. DO NOT improvise advice.

PERFORMANCE METRICS — DASHBOARD ROUTING (HARD RULE):
WhatsApp is NOT the right surface for specific listing data. The following must NEVER appear in seller chat regardless of who is asking:
- Specific numbers (inquiry counts, offer counts, days on market, conversion rates)
- Offer amounts, ranges, or trends, including "highest offer"
- Buyer names, contact details, or identifying descriptors of any inquirer
- Comparable market intelligence on the seller's own unit

For ANY of these, route the seller to dalya.ai/dashboard. Reasoning when first explained: WhatsApp is less secure than the authenticated dashboard; specific buyer and offer data shared via chat would be a privacy risk for buyers and a security risk for the seller.

WHAT YOU CAN SURFACE IN CHAT (in seller mode):
- ONE qualitative activity signal per response (e.g., "active buyer interest with offers in play", "early days yet", "limited recent activity"). Use the helper-provided phrase if given to you; do NOT generate signals freehand.
- Acknowledgement of offer-related INTENT from the seller (accept, reject, counter, set threshold)
	- Acknowledgement that {{managing_agent_name}} will verify a specific offer and send a full payout table. Do NOT calculate seller net proceeds in WhatsApp.
- Dashboard URL (dalya.ai/dashboard)
- Confirmation that {{managing_agent_name}} will reach out

EXAMPLES (seller mode):

Seller: "How is my listing doing?"
✓ "Your listing has active buyer interest with offers in play. The full breakdown — inquiry count, offer activity, buyer engagement — lives on your dashboard at dalya.ai/dashboard. We keep specifics off WhatsApp because buyer and offer data shared via chat would be a privacy risk for your buyers and a security risk for you. {{managing_agent_name}} will also reach out directly on key updates."
✗ "71 buyer conversations started, 21 offers recorded, highest offer AED 6,150,000."

Seller: "How many inquiries this week?"
✓ "Your listing is getting buyer interest. Head to dalya.ai/dashboard for the breakdown."
✗ "8 inquiries this week."

Seller: "What's the highest offer received?"
✓ "Specific offer figures live on dalya.ai/dashboard. Sharing offer amounts over WhatsApp would compromise buyer privacy, which is why we keep specifics on the dashboard."
✗ "The highest offer is AED 6,150,000."

Seller: "I want to accept the AED 17M offer"
	✓ "Got it. I'm flagging the AED 17M acceptance for {{managing_agent_name}} to action immediately. They will verify the offer terms and send you the full payout table. {{managing_agent_name}} will be in touch shortly to walk through next steps." [escalation]

Seller: "Should I drop the price?"
✓ "Pricing strategy is worth a direct conversation with {{managing_agent_name}}. They will reach out to walk through inquiry volume, offer activity, and timing. Listed price changes happen on the dashboard at dalya.ai/dashboard once you've made the call." [escalation]

	SELLER FEE STRUCTURE:
	- There is no cost to the seller to list with {{brokerage_short}}.
	- The buyer pays {{brokerage_short}}'s {{commission_pct_label}} transaction fee. This lower buyer fee is the value proposition because it improves the buyer's total cost versus the usual {{market_pct_label}} brokerage benchmark.
	- DLD transfer fees are paid by the new owner.
	- DO NOT say the seller pays {{brokerage_short}} {{commission_pct_label}}.
	- DO NOT calculate seller net proceeds in WhatsApp. Seller payout depends on accepted price, outstanding developer payments, NOC threshold payments, trustee mechanics, and any seller-specific obligations.
	- When seller asks "what's my net at AED X?", say {{managing_agent_name}} will verify and send the full payout table.

CONVERSATION HISTORY AWARENESS:
- You have access to the full conversation history below. If you have already answered a question in this conversation, acknowledge that and vary your phrasing rather than repeating verbatim.
- "As I mentioned" is better than repeating the same numbers again.

DASHBOARD URL: dalya.ai/dashboard"""

        # Phase 7.7: Performance metrics → dashboard redirect with qualitative signal.
        # Do NOT surface specific numbers (inquiry count, offer count, highest offer)
        # in chat. The dashboard is the source of truth for that data.
        if seller_intent == "performance_metrics":
            activity_signal = self._compute_activity_signal(listing_id, db)
            # Vary the buyer-facing phrasing so consecutive metric questions don't
            # read as the identical "initial buyer interest" line (DAL-74).
            if "active buyer" in activity_signal:
                activity_signal = self._vary([
                    "Your listing is getting active buyer interest.",
                    "There's solid, active buyer interest on your listing right now.",
                    "Buyer activity on your listing is healthy at the moment.",
                ], seller_conv)
            elif "initial buyer" in activity_signal:
                activity_signal = self._vary([
                    "Your listing is getting initial buyer interest.",
                    "There's early buyer interest coming in on your listing.",
                    "Your listing is drawing some initial interest from buyers.",
                ], seller_conv)

            # Phase 8.9: Detect whether the privacy reasoning has already been explained
            # in this conversation; avoid repeating it on every metric question. The
            # current message has been persisted so we look at PRIOR assistant messages.
            history_text = " ".join(
                m.content for m in seller_conv.messages
                if m.role == "assistant"
            ).lower()
            privacy_already_explained = (
                "dalya.ai/dashboard" in history_text
                or "privacy risk" in history_text
            )

            if privacy_already_explained:
                redirect = self._vary([
                    "Full breakdown is on dalya.ai/dashboard.",
                    "The inquiry and offer detail is all on dalya.ai/dashboard.",
                    "Head to dalya.ai/dashboard for the specific numbers.",
                ], seller_conv)
                perf_response = f"{activity_signal} {redirect}"
            else:
                perf_response = (
                    f"{activity_signal} The full breakdown — inquiry count, offer "
                    f"activity, buyer engagement — lives on your dashboard at "
                    f"dalya.ai/dashboard. We keep specifics off WhatsApp because "
                    f"buyer and offer data shared via chat would be a privacy risk "
                    f"for your buyers and a security risk for you. {{managing_agent_name}} will also "
                    f"reach out directly on key updates."
                )
            perf_response, _ = self._finalize_response(perf_response, None, seller_conv, ctx=ctx_seller)
            escalation = EscalationAlert(
                escalation_type="seller_action",
                priority="normal",
                conversation_id=seller_conv.conversation_id,
                listing_id=listing_id,
                buyer_phone=inbound.from_number,
                trigger=BuyerIntent.speak_to_human,
                trigger_message=inbound.body,
                seller_intent=seller_intent,
                payload={
                    "seller_intent": seller_intent,
                    "requested_action": "Review seller performance questions in one consolidated thread.",
                    "question_digest": self._seller_question_digest(seller_conv, inbound.body),
                },
            )
            crud.add_message(
                db,
                conversation_id=seller_conv.conversation_id,
                role=MessageRole.assistant.value,
                content=perf_response,
            )
            crud.update_conversation(db, seller_conv)
            if self._should_suppress_non_offer_escalation(seller_conv, escalation):
                if self._response_promises_forwarding(perf_response):
                    perf_response = self._remove_unbacked_seller_handoff_claim(perf_response)
                return perf_response, None, None
            self._record_escalation_state(db, seller_conv, escalation)
            return perf_response, escalation, None

        # Phase 9.8: Listing-change intents (price drop, threshold set, listing edit)
        # → deterministic dashboard redirect. The dashboard is the source of truth;
        # the bot must NOT confirm bot-actioned changes through Eric.
        if seller_intent in ROUTINE_INTENTS:
            if seller_intent == "threshold_update":
                # RES-6: a "set a floor / escalate offers at X to me" request is a
                # threshold set-up, not a generic price edit — confirm it as such.
                change_response = self._vary([
                    "Got it. Set that escalation threshold on dalya.ai/dashboard and I'll alert you on any offer at or above it. "
                    "You can also give {managing_agent_name} the figure and they'll set it with you.",
                    "Understood. The offer-alert threshold is set on dalya.ai/dashboard and takes effect immediately; "
                    "from then on I flag any offer that meets it. {managing_agent_name} can walk you through it if you'd like.",
                ], seller_conv)
            else:
                change_response = self._vary([
                    "Listing changes — including price and threshold updates — happen on "
                    "your dashboard at dalya.ai/dashboard, not through chat. The change "
                    "takes effect immediately once you save it there. "
                    "I've flagged this so {managing_agent_name} can review the pricing strategy with you first.",
                    "Price and threshold edits are made on dalya.ai/dashboard rather than over chat, "
                    "and they go live the moment you save. {managing_agent_name} can talk through the pricing call with you before you do.",
                    "You'll make that change directly on dalya.ai/dashboard — it applies immediately once saved. "
                    "I've looped {managing_agent_name} in so you can sense-check the strategy before committing.",
                ], seller_conv)
            change_response, _ = self._finalize_response(change_response, None, seller_conv, ctx=ctx_seller)
            crud.add_message(
                db,
                conversation_id=seller_conv.conversation_id,
                role=MessageRole.assistant.value,
                content=change_response,
            )
            crud.update_conversation(db, seller_conv)
            logger.info(
                "phase98_seller_change_routed_to_dashboard listing=%s intent=%s",
                listing_id, seller_intent,
            )
            escalation = EscalationAlert(
                escalation_type="seller_action",
                priority="normal",
                conversation_id=seller_conv.conversation_id,
                listing_id=listing_id,
                buyer_phone=inbound.from_number,
                trigger=BuyerIntent.speak_to_human,
                trigger_message=inbound.body,
                seller_intent=seller_intent,
                payload={
                    "seller_intent": seller_intent,
                    "requested_action": "Discuss the requested listing change; actual edits remain dashboard-only.",
                    "question_digest": self._seller_question_digest(seller_conv, inbound.body),
                },
            )
            if self._should_suppress_non_offer_escalation(seller_conv, escalation):
                if self._response_promises_forwarding(change_response):
                    change_response = self._remove_unbacked_seller_handoff_claim(change_response)
                return change_response, None, None
            self._record_escalation_state(db, seller_conv, escalation)
            return change_response, escalation, None

        if seller_intent == "buyer_outreach_request":
            outreach_response = (
                "Bulk buyer outreach is not actioned through WhatsApp. Keep the price update on "
                "dalya.ai/dashboard so the listing record is current and auditable. Buyer follow-up "
                "must stay controlled through the proper brokerage channel."
            )
            outreach_response, _ = self._finalize_response(outreach_response, None, seller_conv, ctx=ctx_seller)
            crud.add_message(
                db,
                conversation_id=seller_conv.conversation_id,
                role=MessageRole.assistant.value,
                content=outreach_response,
            )
            crud.update_conversation(db, seller_conv)
            escalation = EscalationAlert(
                escalation_type="seller_action",
                priority="normal",
                conversation_id=seller_conv.conversation_id,
                listing_id=listing_id,
                buyer_phone=inbound.from_number,
                trigger=BuyerIntent.speak_to_human,
                trigger_message=inbound.body,
                seller_intent=seller_intent,
                payload={
                    "seller_intent": seller_intent,
                    "requested_action": "Review compliant buyer outreach separately from the price change.",
                    "question_digest": self._seller_question_digest(seller_conv, inbound.body),
                },
            )
            if self._should_suppress_non_offer_escalation(seller_conv, escalation):
                return outreach_response, None, None
            self._record_escalation_state(db, seller_conv, escalation)
            return outreach_response, escalation, None

        if seller_intent in {"offer_acceptance", "counter_offer", "net_proceeds", "buyer_privacy_request"}:
            amount_text = ""
            parsed_amounts = []
            for amount_match in re.finditer(
                r"(\d+(?:[.,]\d+)?)\s*(m|million)?",
                inbound.body,
                re.IGNORECASE,
            ):
                raw_amount = amount_match.group(1).replace(",", "")
                unit = (amount_match.group(2) or "").lower()
                try:
                    value = float(raw_amount)
                    if unit in {"m", "million"}:
                        value *= 1_000_000
                    if value >= 100_000:
                        parsed_amounts.append(value)
                except ValueError:
                    continue
            if parsed_amounts:
                amount_text = f" at AED {parsed_amounts[-1]:,.0f}"

            if seller_intent == "offer_acceptance":
                seller_response = (
                    "Got it. I've flagged this for {managing_agent_name} to follow up directly. "
                    "They'll verify the offer terms and send you the full payout table before anything is finalized."
                )
            elif seller_intent == "counter_offer":
                seller_response = (
                    f"Got it. I've flagged the counter direction{amount_text} for {{managing_agent_name}} to review. "
                    "They'll verify the terms, present it through the proper channel, and send you the full payout table."
                )
            elif seller_intent == "net_proceeds":
                seller_response = (
                    "{managing_agent_name} will verify and send you the full payout table. I don't calculate seller net proceeds over WhatsApp because the final number depends on the accepted price, developer account position, NOC mechanics, trustee-office costs, and any seller-specific obligations."
                )
            else:
                seller_response = self._compose_privacy_refusal(
                    inbound.body,
                    conv=seller_conv,
                    ctx=ctx_seller,
                    seller_side=True,
                )

            seller_response, _ = self._finalize_response(seller_response, None, seller_conv, ctx=ctx_seller)
            escalation = EscalationAlert(
                escalation_type="seller_action",
                priority="high" if seller_intent != "net_proceeds" else "normal",
                conversation_id=seller_conv.conversation_id,
                listing_id=listing_id,
                buyer_phone=inbound.from_number,
                trigger=BuyerIntent.speak_to_human,
                trigger_message=inbound.body,
                seller_intent=seller_intent,
                payload={
                    "seller_intent": seller_intent,
                    "requested_action": "Action or review the seller request directly.",
                    "question_digest": self._seller_question_digest(seller_conv, inbound.body),
                    "amount_aed": parsed_amounts[-1] if parsed_amounts else None,
                },
            )
            crud.add_message(
                db,
                conversation_id=seller_conv.conversation_id,
                role=MessageRole.assistant.value,
                content=seller_response,
            )
            crud.update_conversation(db, seller_conv)
            if self._should_suppress_non_offer_escalation(seller_conv, escalation):
                if self._response_promises_forwarding(seller_response):
                    seller_response = self._remove_unbacked_seller_handoff_claim(seller_response)
                return seller_response, None, None
            self._record_escalation_state(db, seller_conv, escalation)
            return seller_response, escalation, None

        # For all other intents — generate via Claude with seller system prompt.
        # Load seller conversation history so the model can vary phrasing on repeated questions.
        seller_history = []
        if seller_conv.messages:
            # exclude the current message (already persisted) so it's added once at the end
            for m in seller_conv.messages[-11:-1]:
                seller_history.append({"role": m.role, "content": m.content})
        seller_history.append({"role": "user", "content": inbound.body})

        # Substitute brokerage-context placeholders in the seller-mode prompt
        # so a non-Mahoroba seller sees their own brokerage/agent identity.
        seller_system_rendered = self._apply_brokerage_substitutions(seller_system, ctx_seller)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            system=[{
                "type": "text",
                "text": seller_system_rendered,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=seller_history,
        )
        seller_response = response.content[0].text.strip()
        seller_response, _ = self._finalize_response(seller_response, None, seller_conv, ctx=ctx_seller)

        # Determine escalation
        escalation = None
        if seller_intent in MATERIAL_INTENTS:
            priority = "high"
            escalation = EscalationAlert(
                escalation_type="seller_action",
                priority=priority,
                conversation_id=seller_conv.conversation_id,
                listing_id=listing_id,
                buyer_phone=inbound.from_number,  # seller's phone in this field
                trigger=BuyerIntent.speak_to_human,
                trigger_message=inbound.body,
                seller_intent=seller_intent,
                payload={
                    "seller_intent": seller_intent,
                    "requested_action": "Review seller request directly.",
                    "question_digest": self._seller_question_digest(seller_conv, inbound.body),
                },
            )
        elif seller_intent == "general_seller_question":
            escalation = EscalationAlert(
                escalation_type="seller_action",
                priority="normal",
                conversation_id=seller_conv.conversation_id,
                listing_id=listing_id,
                buyer_phone=inbound.from_number,
                trigger=BuyerIntent.speak_to_human,
                trigger_message=inbound.body,
                seller_intent=seller_intent,
                payload={
                    "seller_intent": seller_intent,
                    "requested_action": "Review seller question directly.",
                    "question_digest": self._seller_question_digest(seller_conv, inbound.body),
                },
            )

        # Phase 8.9: Persist seller-mode bot response so conversation history
        # accumulates correctly (so privacy-explanation flag works across turns).
        crud.add_message(
            db,
            conversation_id=seller_conv.conversation_id,
            role=MessageRole.assistant.value,
            content=seller_response,
        )
        crud.update_conversation(db, seller_conv)

        if escalation is not None:
            if self._should_suppress_non_offer_escalation(seller_conv, escalation):
                if self._response_promises_forwarding(seller_response):
                    seller_response = self._remove_unbacked_seller_handoff_claim(seller_response)
                logger.info(
                    "seller_escalation_suppressed listing=%s seller_phone=%s intent=%s",
                    listing_id, inbound.from_number, seller_intent,
                )
                escalation = None
            else:
                self._record_escalation_state(db, seller_conv, escalation)

        logger.info(
            "seller_mode listing=%s seller_phone=%s intent=%s escalated=%s",
            listing_id, inbound.from_number, seller_intent, escalation is not None,
        )

        return seller_response, escalation, None

    # ── Professional intermediary handler ─────────────────────────────────────

    def _handle_professional_inquiry(
        self,
        inbound: InboundMessage,
        listing_id: str,
        db_listing,
        spa,
        conv,
        db,
        intent_data: dict,
        ctx: Optional[BrokerageContext] = None,
    ) -> tuple:
        """
        Professional intermediary handler. Answers public unit info, declines
        PII / docs, doesn't push for buyer offer.
        """
        project = spa.project or "the property"
        unit = spa.unit_number or ""
        asking = db_listing.seller_asking_price or spa.purchase_price_aed
        plot_line = (
            f"Plot: {spa.plot_sqft:,.0f} sqft, " if spa.plot_sqft else ""
        )
        status = (spa.property_status or "").lower()
        listing_property_type = (db_listing.property_type or "").lower()
        is_ready_listing = listing_property_type == "ready" or status in {"ready", "completed", "complete"}
        noc_line = (
            "ready resale; NOC/title-deed transfer timing should be verified through the listing agent"
            if is_ready_listing else (
                "listing record indicates NOC eligibility; listing agent must verify before reliance" if spa.noc_eligible
                else "not confirmed; listing agent must verify before reliance"
            )
        )

        # DAL-85: a professional asking what else the brokerage represents gets the
        # same-brokerage portfolio (cross-tenant isolation still holds — only this
        # listing's brokerage stock).
        if self._detect_portfolio_list_request(inbound.body):
            all_other = self._rank_portfolio_brief(self._get_all_other_listings(listing_id, db))
            if all_other:
                limit = self._requested_listing_limit(inbound.body)
                if limit is not None:
                    all_other = all_other[:limit]
                bot_response = self._compose_portfolio_list_response(all_other, requested_limit=limit)
                bot_response, _ = self._finalize_response(
                    bot_response, BuyerIntent.professional_inquiry, conv, ctx=ctx
                )
                crud.add_message(
                    db, conversation_id=conv.conversation_id,
                    role=MessageRole.assistant.value, content=bot_response,
                )
                return bot_response, None, None

        if re.search(r"referral|co-?broke|commission split|0\.15|fee", inbound.body, re.IGNORECASE):
            bot_response = (
                "The buyer pays {brokerage_short} {commission_pct_label} for our services on the transaction. "
                "Any advisory fee or commission you agree with your client is separate "
                "from us and sits between you and your client. {managing_agent_name} handles formal "
                "partnership terms directly if there is a broader arrangement to discuss."
            )
            bot_response, _ = self._finalize_response(
                bot_response, BuyerIntent.professional_inquiry, conv, ctx=ctx
            )
            crud.add_message(
                db,
                conversation_id=conv.conversation_id,
                role=MessageRole.assistant.value,
                content=bot_response,
            )
            return bot_response, None, None

        professional_prompt = f"""You are Dalya speaking with a PROFESSIONAL INTERMEDIARY (mortgage broker, financial advisor, conveyancer without verified offer, property manager).

This is NOT a buyer. Don't push for an offer. Don't fire commission pitches. Treat as peer-to-peer professional conversation.

UNIT FACTS (these are public — share freely):
- Project: {project}
- Unit: {unit}
- Developer: {spa.developer}
- Type: {spa.property_type}
- Status: {"READY resale (completed, handed over)" if is_ready_listing else "OFF-PLAN (under construction)"}
- Bedrooms: {spa.bedrooms}, Bathrooms: {spa.bathrooms}
- BUA: {f"{spa.bua_sqft:,.0f} sqft" if spa.bua_sqft else "available on request"}, {plot_line}Asking: AED {asking:,.0f}
- Handover: {spa.estimated_completion_date or "as per SPA"}
- NOC eligibility: {noc_line}

STATUS IS KNOWN — never ask the professional whether this is ready or off-plan. State it: this is a {"ready resale" if is_ready_listing else "off-plan"} listing, then proceed.

WHAT YOU CAN SHARE:
- All unit specs above
	- Payment schedule structure only if this is an off-plan listing
- Public market positioning
- Developer track record (from community KB if available)

	WHAT YOU CANNOT SHARE:
	- SPA, SOA, NOC, or any legal documents (those go through proper channels)
	- Seller name, contact details, or any PII
	- Other buyers' offer history or amounts
	- Specific valuations of comparable units (you don't have this data)
	- Bank-specific approvals or final LTV commitments (refer to the buyer's bank)
	- Generic 80% ready-resale LTV ceilings unless the professional explicitly asks for a generic maximum; residency, value band, use, and bank policy change it

		OFF-PLAN MORTGAGE FACTS:
		- If this is an off-plan listing, do not quote LTV percentages, paid-to-developer thresholds, developer bank-approval rules, or construction-completion thresholds unless an active direct Verified Fact for this buyer turn states them.
		- Without that fact, say off-plan finance is more constrained and must be confirmed by the buyer's bank or mortgage advisor for the specific deal.
		- Do not say "most UAE banks finance off-plan" broadly.
		- Final policy still sits with the buyer's lender.

	OFFERS THROUGH DALYA:
	- Firm offers can be submitted in this Dalya WhatsApp thread. Dalya records them and routes qualifying offers to the managing agent.
	- Do NOT say offers must be made outside Dalya or only directly through the listing agent.

	WHAT TO DO IF THEY ASK FOR REFERRAL FEE / CO-BROKE TERMS / INVESTMENT SUMMARY:
	- Answer the fee question directly: the buyer pays {ctx.brokerage_short if ctx else "the brokerage"} {ctx.commission_pct_label if ctx else "the configured commission"} on the transaction
	- Do not say we pay referral fees out of the brokerage commission.
	- Any additional advisory fee is between the intermediary and their client
	- {ctx.managing_agent_name if ctx else "the managing agent"} handles formal partnership arrangements directly if needed
	- Do not ask for phone/contact details; we already have the WhatsApp thread

WHAT TO DO IF THEY ASK FOR A TAX/LEGAL/CORPORATE STRUCTURE OPINION:
- Don't advise. Refer to a Dubai real estate lawyer.

TONE:
- Professional, peer-level
- No emojis, no markdown bold
- Default 1-3 sentences, then stop
- If giving a brief or inventory, use line items with every item on its own line
- Split two-topic answers with a blank line
- Examples:
	  "NOC and title-transfer timing depends on the developer, bank, documents, and transaction structure. The listing agent needs to confirm the current timing before anyone relies on it.

	  If bank finance is involved, the bank and listing agent will confirm the sequence before completion."

  "Here's the brief on the unit:

	  - 4-bed, 6-bath, 5,148 sqft, asking AED 16.99M
	  - Ready resale - completed, available for immediate transfer
	  - No developer payment plan
	  - NOC/title-transfer timing is confirmed by the listing agent once under contract"
- Don't ask "are you looking to invest or end-use?" (they're not the buyer)"""

        recent = (conv.messages[-10:] if conv and conv.messages else [])
        history = [{"role": m.role, "content": m.content} for m in recent]
        if not history or history[-1].get("content") != inbound.body:
            history.append({"role": "user", "content": inbound.body})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=[{
                "type": "text",
                "text": professional_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=history,
        )
        bot_response = response.content[0].text.strip()

        bot_response, _ = self._finalize_response(
            bot_response, BuyerIntent.professional_inquiry, conv, ctx=ctx
        )

        crud.add_message(
            db,
            conversation_id=conv.conversation_id,
            role=MessageRole.assistant.value,
            content=bot_response,
        )

        # Phase 7.6.5b: co-broker compliance triggers (Form A, listing auth, RERA verification)
        # fire a general_lead_capture escalation so Eric can handle the formal documentation.
        # Phase 9.6: BRN-only requests get a distinct escalation type from Form A.
        escalation = None
        if self._detect_co_broker_compliance(inbound.body):
            if self._detect_brn_only_request(inbound.body):
                escalation = EscalationAlert(
                    escalation_type="brn_request",
                    priority="normal",
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    trigger=BuyerIntent.professional_inquiry,
                    trigger_message=inbound.body,
                    escalation_subtype="brn_request",
                    payload={
                        "doc_requested": "BRN / RERA card verification",
                        "requested_action": "Send the correct agent registration details.",
                    },
                )
            else:
                escalation = EscalationAlert(
                    escalation_type="general_lead_capture",
                    priority="normal",
                    conversation_id=conv.conversation_id,
                    listing_id=listing_id,
                    buyer_phone=inbound.from_number,
                    buyer_name=conv.buyer_name,
                    trigger=BuyerIntent.professional_inquiry,
                    trigger_message=inbound.body,
                    escalation_subtype="co_broker_compliance",
                    payload={
                        "doc_requested": "Form A / listing authorization",
                        "requested_action": "Send formal listing authorization through the proper channel.",
                    },
                )

        return bot_response, escalation, None

    # ── Phase 1.3: Regulatory request handling ────────────────────────────────

    def _detect_regulatory_category(self, message: str) -> str:
        """Keyword-based regulatory category detector."""
        msg = message.lower()
        if "pdpl" in msg or "delete my data" in msg or "erasure" in msg or "right to be forgotten" in msg:
            return "pdpl_deletion"
        if "gdpr" in msg:
            return "gdpr"
        if "subject access" in msg or "data portability" in msg or "data access" in msg:
            return "data_access"
        return "general_data_protection"

    def _compose_regulatory_acknowledgment(self, message: str) -> str:
        return (
            "I'm Dalya, and I understand you're invoking your data protection rights. "
            "I'm escalating this to {brokerage_name}'s compliance team — "
            "they're the data controller and will respond within the 30-day PDPL window. "
            "They'll be in touch via your registered phone number to verify identity "
            "and process the request formally."
        )

    def _compose_regulatory_followup_acknowledgment(self, message: str) -> str:
        return (
            "Your data protection request is already logged with {brokerage_name}'s "
            "compliance team. They'll respond within the 30-day PDPL window and "
            "will use this WhatsApp thread or your registered phone number for "
            "identity verification and formal follow-up."
        )

    def _compose_opt_out_acknowledgment(self) -> str:
        return "Understood. We won't contact you again on this brokerage."


# ── Singleton instance ─────────────────────────────────────────────────────────
engine = ChatbotEngine()
