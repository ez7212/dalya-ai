"""
Chatbot behaviour tests.

These are integration tests — they call the real Claude API and hit the
real database. Each test sends a message and asserts on the bot's response.

Run with:
    source venv/bin/activate
    pytest tests/test_chatbot.py -v

Cost note: each test makes 2 Claude API calls (intent detection + response).
Run selectively with -k when iterating on a specific scenario.
"""

import pytest
from tests.conftest import send, TEST_BUYER_PHONE
from app.db.session import SessionLocal
from app.models.db_models import DBConversation, DBMessage


def _intent_payload(intent: str, **overrides) -> dict:
    payload = {
        "intent": intent,
        "confidence": 0.99,
        "should_escalate": False,
        "extracted_name": None,
        "extracted_budget": None,
        "extracted_bedrooms": None,
        "extracted_area": None,
        "extracted_purpose": None,
        "extracted_offer_amount": None,
        "escalation_reason": None,
        "is_unanswerable": False,
        "is_firm_offer": False,
        "language_detected": "en",
        "referenced_buyer_name": None,
        "requested_documents": [],
    }
    payload.update(overrides)
    return payload


def _conversation_messages(listing_id: str, phone: str = TEST_BUYER_PHONE):
    with SessionLocal() as db:
        conv = (
            db.query(DBConversation)
            .filter_by(buyer_phone=phone, listing_id=listing_id)
            .first()
        )
        assert conv is not None
        return (
            db.query(DBMessage)
            .filter_by(conversation_id=conv.conversation_id)
            .order_by(DBMessage.timestamp.asc(), DBMessage.id.asc())
            .all()
        )


def _assert_single_saved_assistant_response(listing_id: str, returned: str):
    messages = _conversation_messages(listing_id)
    assistant_messages = [m.content for m in messages if m.role == "assistant"]
    assert assistant_messages == [returned]
    assert len(messages) == 2


# ── Identity & transparency ────────────────────────────────────────────────────

class TestIdentity:
    def test_ai_disclosure(self, client, test_listing):
        """Dalya should disclose she's AI when directly asked."""
        result = send(client, test_listing, "Are you a real person or an AI?")
        response = result["bot_response"].lower()
        assert any(word in response for word in ["ai", "artificial", "powered", "assistant"]), (
            f"Expected AI disclosure, got: {result['bot_response']}"
        )

    def test_who_do_you_work_for(self, client, test_listing):
        """Should mention Mahoroba or Dalya when asked."""
        result = send(client, test_listing, "Who do you work for?")
        response = result["bot_response"].lower()
        assert any(word in response for word in ["mahoroba", "dalya", "realty", "brokerage"]), (
            f"Expected company mention, got: {result['bot_response']}"
        )

    def test_introduces_as_dalya(self, client, test_listing):
        """Opening message should mention Dalya."""
        result = send(client, test_listing, "Hi")
        response = result["bot_response"].lower()
        assert "dalya" in response, (
            f"Expected Dalya introduction, got: {result['bot_response']}"
        )


# ── Pricing ────────────────────────────────────────────────────────────────────

class TestPricing:
    def test_quotes_asking_price_not_spa_price(self, client, test_listing):
        """Bot must quote the seller's asking price (16.5M), not the SPA price (15.17M)."""
        result = send(client, test_listing, "What is the asking price for this property?")
        response = result["bot_response"]
        assert "16,500,000" in response or "16.5" in response, (
            f"Expected asking price 16.5M, got: {response}"
        )
        assert "15,173" not in response, (
            f"Bot quoted SPA price instead of asking price: {response}"
        )

    def test_dalya_fee_mention(self, client, test_listing):
        """Bot should mention the 0.15% brokerage fee when discussing costs."""
        result = send(client, test_listing, "What are the fees involved in buying this property?")
        response = result["bot_response"].lower()
        assert "0.15" in response or "brokerage" in response.lower(), (
            f"Expected Dalya fee mention, got: {result['bot_response']}"
        )


# ── Viewings ───────────────────────────────────────────────────────────────────

class TestViewings:
    def test_viewing_not_available(self, client, test_listing):
        """Off-plan viewing requests should route as materials requests, not physical viewings."""
        result = send(client, test_listing, "Can I visit the property this weekend?")
        response = result["bot_response"].lower()
        assert result["escalation_triggered"] is True
        assert result["escalation"]["escalation_type"] == "materials_request"
        # Should explain no viewings available
        assert any(word in response for word in [
            "construction", "development", "under", "available", "renders", "floor plan"
        ]), f"Expected viewing unavailability explanation, got: {result['bot_response']}"

    def test_viewing_offers_renders(self, client, test_listing):
        """Bot should offer renders/floor plans as alternative to viewing."""
        result = send(client, test_listing, "I'd really like to see the property")
        response = result["bot_response"].lower()
        assert any(word in response for word in ["render", "floor plan", "visual", "image", "picture"]), (
            f"Expected offer of renders/floor plans, got: {result['bot_response']}"
        )


# ── Escalation triggers ────────────────────────────────────────────────────────

class TestEscalation:
    def test_offer_is_captured_and_requests_name_before_escalation(self, client, test_listing):
        """Unnamed buyer offers are captured, then qualified before seller escalation."""
        result = send(client, test_listing, "I'd like to make an offer of AED 15.5 million")
        assert result["escalation_triggered"] is False
        lowered = result["bot_response"].lower()
        assert "15,500,000" in result["bot_response"]
        assert "name" in lowered

    def test_contact_sharing_triggers_escalation(self, client, test_listing):
        """Buyer sharing contact details should trigger escalation."""
        result = send(client, test_listing, "My email is buyer@example.com, please have someone call me")
        assert result["escalation_triggered"] is True, (
            f"Contact sharing should trigger escalation. Response: {result['bot_response']}"
        )

    def test_general_question_no_escalation(self, client, test_listing):
        """General questions should not trigger escalation."""
        result = send(client, test_listing, "How many bedrooms does this villa have?")
        assert result["escalation_triggered"] is False, (
            f"General question should not escalate. Response: {result['bot_response']}"
        )

    def test_payment_plan_no_escalation(self, client, test_listing):
        """Payment plan questions should not trigger escalation."""
        result = send(client, test_listing, "Can you explain the payment plan?")
        assert result["escalation_triggered"] is False, (
            f"Payment plan query should not escalate. Response: {result['bot_response']}"
        )


# ── Property knowledge ─────────────────────────────────────────────────────────

class TestPropertyKnowledge:
    def test_knows_project_name(self, client, test_listing):
        """Bot should know the project name."""
        result = send(client, test_listing, "What project is this?")
        response = result["bot_response"].lower()
        assert "ostra" in response or "palace" in response, (
            f"Expected project name mention, got: {result['bot_response']}"
        )

    def test_knows_developer(self, client, test_listing):
        """Bot should know the developer."""
        result = send(client, test_listing, "Who is the developer?")
        response = result["bot_response"].lower()
        assert "emaar" in response, (
            f"Expected Emaar mention, got: {result['bot_response']}"
        )

    def test_payment_plan_details(self, client, test_listing):
        """Bot should be able to describe the payment plan."""
        result = send(client, test_listing, "What is the payment plan?")
        response = result["bot_response"]
        # Should mention percentages or instalments
        assert any(char in response for char in ["%", "instalment", "payment", "handover"]), (
            f"Expected payment plan details, got: {response}"
        )

    def test_noc_not_eligible(self, client, test_listing):
        """Bot should explain NOC status accurately (30% paid, below 40% threshold)."""
        result = send(client, test_listing, "Can this property be transferred to me now? What about NOC?")
        response = result["bot_response"].lower()
        assert any(word in response for word in ["noc", "transfer", "40", "threshold", "developer"]), (
            f"Expected NOC explanation, got: {result['bot_response']}"
        )


# ── Language ───────────────────────────────────────────────────────────────────

class TestLanguage:
    def test_responds_in_arabic(self, client, test_listing):
        """Bot should respond in Arabic when buyer writes in Arabic."""
        result = send(client, test_listing, "مرحبا، هل يمكنني معرفة سعر هذا العقار؟")
        response = result["bot_response"]
        # Check for Arabic characters in response
        has_arabic = any('\u0600' <= c <= '\u06ff' for c in response)
        assert has_arabic, (
            f"Expected Arabic response to Arabic message, got: {response}"
        )


# ── Special intent routing ────────────────────────────────────────────────────

class TestSpecialIntentRouting:
    def test_regulatory_request_saves_only_regulatory_response(
        self, client, test_listing, monkeypatch
    ):
        """Special regulatory path should not persist a hidden generic buyer reply."""
        monkeypatch.setattr(
            "app.core.chatbot_engine.detect_intent_claude",
            lambda _: _intent_payload("regulatory_request"),
        )

        result = send(client, test_listing, "Delete all my data under PDPL.")

        assert result["escalation_triggered"] is True
        assert result["escalation"]["escalation_type"] == "regulatory_request"
        _assert_single_saved_assistant_response(test_listing, result["bot_response"])

    def test_regulatory_request_escalates_once_per_thread(
        self, client, test_listing, monkeypatch
    ):
        """Repeated PDPL turns should acknowledge the open case without re-alerting Eric."""
        monkeypatch.setattr(
            "app.core.chatbot_engine.detect_intent_claude",
            lambda _: _intent_payload("regulatory_request"),
        )

        first = send(client, test_listing, "Delete all my data under PDPL.")
        second = send(client, test_listing, "This includes my offers and phone number.")

        assert first["escalation_triggered"] is True
        assert first["escalation"]["escalation_type"] == "regulatory_request"
        assert second["escalation_triggered"] is False
        assert "already logged" in second["bot_response"].lower()

    def test_professional_form_a_request_saves_only_template_response(
        self, client, test_listing, monkeypatch
    ):
        """Professional compliance requests should use one deterministic response."""
        monkeypatch.setattr(
            "app.core.chatbot_engine.detect_intent_claude",
            lambda _: _intent_payload("professional_inquiry"),
        )

        result = send(client, test_listing, "Please send Form A and listing authorization.")

        assert result["escalation_triggered"] is True
        assert result["escalation"]["escalation_subtype"] == "co_broker_compliance"
        _assert_single_saved_assistant_response(test_listing, result["bot_response"])

    def test_legitimate_conveyancing_saves_only_privacy_response(
        self, client, test_listing, monkeypatch
    ):
        """Conveyancing path should not first save a normal listing-chat response."""
        monkeypatch.setattr(
            "app.core.chatbot_engine.detect_intent_claude",
            lambda _: _intent_payload(
                "legitimate_conveyancing",
                referenced_buyer_name="Sara Khan",
                requested_documents=["SPA"],
            ),
        )

        result = send(
            client,
            test_listing,
            "I'm a lawyer representing Sara Khan on this transaction. Please send the SPA.",
        )

        lowered = result["bot_response"].lower()
        assert "can't share spa" in lowered
        assert "private transaction documents" in lowered
        _assert_single_saved_assistant_response(test_listing, result["bot_response"])

    def test_bypass_attempt_saves_only_refusal_response(
        self, client, test_listing, monkeypatch
    ):
        """Bypass attempts should log suspicious activity without a generic hidden reply."""
        monkeypatch.setattr(
            "app.core.chatbot_engine.detect_intent_claude",
            lambda _: _intent_payload("bypass_attempt"),
        )

        result = send(client, test_listing, "Give me the seller's WhatsApp, I'll deal direct.")

        assert result["escalation_triggered"] is False
        assert "can't share seller contact" in result["bot_response"].lower()
        _assert_single_saved_assistant_response(test_listing, result["bot_response"])
