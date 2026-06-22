from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest

from app.core.chatbot_engine import ChatbotEngine
from app.core.messaging import set_transport_override
from app.core.messaging.transport import MessagingTransport
from app.core.messaging.types import InboundEnvelope, OutboundAgentMessage, OutboundBuyerMessage, SendResult
from app.core.response_validator import validate_and_rewrite_response
from app.core.verified_facts import VerifiedFact, VerifiedFactRegistry
from app.core.verified_facts_output_gate import apply_verified_facts_output_gate
from app.schemas.conversation import BuyerIntent
from app.schemas.spa import PaymentInstalment, SPAParseResult


@dataclass
class CapturingTransport(MessagingTransport):
    sent_to_buyer: OutboundBuyerMessage | None = None

    def send_to_buyer(self, msg: OutboundBuyerMessage) -> SendResult:
        self.sent_to_buyer = msg
        return SendResult(ok=True, transport_message_id="test-msg")

    def send_to_agents_ai(self, msg: OutboundAgentMessage) -> SendResult:
        return SendResult(ok=True, transport_message_id="agent-msg")

    def parse_inbound(self, form_data: dict) -> InboundEnvelope:
        return InboundEnvelope(
            transport="test",
            from_number="+971500000001",
            to_number="+971500000002",
            body=str(form_data.get("Body", "")),
            message_sid="inbound-msg",
            raw=form_data,
        )


@pytest.mark.parametrize(
    ("generated", "blocked_terms"),
    [
        (
            "Banks usually allow 50% LTV on this off-plan resale.",
            ("50% LTV",),
        ),
        (
            "The developer NOC should take 3-5 days once we apply.",
            ("3-5 days",),
        ),
        (
            "The trustee transfer normally closes in 30-45 days.",
            ("30-45 days",),
        ),
        (
            "The generic developer NOC fee is AED 5,000.",
            ("AED 5,000",),
        ),
        (
            "The agency fee is 2% and the trustee fee is AED 4,000.",
            ("2%", "AED 4,000"),
        ),
        (
            "There is no tax exposure here, so you do not need legal advice.",
            ("no tax exposure", "do not need legal advice"),
        ),
        (
            "Vacant possession is guaranteed after 12 months because the tenant notice is automatic.",
            ("12 months", "guaranteed", "automatic"),
        ),
        (
            "The seller has paid AED 12,000,000 to date, so you only take over the AED 3,000,000 developer balance.",
            ("AED 12,000,000", "AED 3,000,000", "take over"),
        ),
        (
            "The seller originally paid AED 12,000,000, so the premium is about 25%.",
            ("AED 12,000,000", "25%"),
        ),
    ],
)
def test_output_gate_rewrites_unsupported_generated_claims_after_generation(
    generated: str,
    blocked_terms: tuple[str, ...],
) -> None:
    # Given: an already-generated buyer-facing answer with an unsupported
    # Verified Facts-sensitive claim.

    # When: the central post-generation validator runs.
    response, telemetry = validate_and_rewrite_response(
        generated,
        BuyerIntent.general_enquiry,
        latest_buyer_message="Can you give me exact finance, NOC, tax, and payment details?",
    )

    # Then: the unsafe claim is replaced after generation and telemetry records it.
    lowered = response.lower()
    assert "listing agent needs to confirm" in lowered or "qualified advisor" in lowered
    for term in blocked_terms:
        assert term.lower() not in lowered
    assert telemetry["verified_facts_output_rewrites"] == 1


def test_output_gate_preserves_active_confirmed_direct_general_fact() -> None:
    # Given: a generated answer that states the active direct DLD registration fact.
    generated = "The standard Dubai Land Department (DLD) property registration fee is 4% of the purchase price, paid by the buyer."

    # When: the output gate validates the response.
    response, telemetry = validate_and_rewrite_response(
        generated,
        BuyerIntent.general_enquiry,
        latest_buyer_message="What is the DLD fee?",
    )

    # Then: the confirmed fact passes unchanged.
    assert response == generated
    assert telemetry["verified_facts_output_rewrites"] == 0


def test_output_gate_preserves_tenant_scoped_active_direct_fact_for_current_brokerage() -> None:
    # Given: a tenant-scoped confirmed direct fact for the current brokerage.
    registry = VerifiedFactRegistry([
        VerifiedFact.from_raw(
            {
                "key": "specific_noc_transfer_timing",
                "category": "noc_transfer",
                "domain": "dubai_real_estate",
                "scope": "tenant",
                "brokerage_id": "brokerage-A",
                "text": "For brokerage A verified listing context, the developer NOC takes 7 days.",
                "source_label": "Brokerage A compliance note",
                "source_ref": "NOC1",
                "status": "confirmed",
                "transaction_specific": False,
                "active": True,
            }
        )
    ])
    generated = "The developer NOC takes 7 days."

    # When: the output gate runs with the matching brokerage context.
    result = apply_verified_facts_output_gate(
        generated,
        latest_buyer_message="How long does the NOC take?",
        brokerage_id="brokerage-A",
        registry=registry,
    )

    # Then: the verified tenant-scoped claim passes unchanged.
    assert result.response == generated
    assert result.rewrite_count == 0


def test_output_gate_blocks_tenant_scoped_direct_fact_for_other_brokerage() -> None:
    # Given: a tenant-scoped direct fact that belongs to another brokerage.
    registry = VerifiedFactRegistry([
        VerifiedFact.from_raw(
            {
                "key": "specific_noc_transfer_timing",
                "category": "noc_transfer",
                "domain": "dubai_real_estate",
                "scope": "tenant",
                "brokerage_id": "brokerage-A",
                "text": "For brokerage A verified listing context, the developer NOC takes 7 days.",
                "source_label": "Brokerage A compliance note",
                "source_ref": "NOC1",
                "status": "confirmed",
                "transaction_specific": False,
                "active": True,
            }
        )
    ])

    # When: the output gate runs for a different brokerage.
    result = apply_verified_facts_output_gate(
        "The developer NOC takes 7 days.",
        latest_buyer_message="How long does the NOC take?",
        brokerage_id="brokerage-B",
        registry=registry,
    )

    # Then: the unsupported tenant-specific claim is deferred.
    assert "7 days" not in result.response
    assert "listing agent needs to confirm" in result.response.lower()
    assert result.rewrite_count == 1


def test_output_gate_preserves_deterministic_remaining_payment_wording() -> None:
    # Given: deterministic remaining-payment copy grounded in the SPA schedule.
    spa = SPAParseResult(
        project="The Oasis",
        unit_number="V-12",
        developer="Emaar",
        property_type="Villa",
        purchase_price_aed=15_000_000,
        property_status="Under Construction",
        estimated_completion_date="2028-12-31",
        payment_schedule=[
            PaymentInstalment(
                instalment_number=1,
                milestone="Remaining on handover",
                percentage=20,
                amount_aed=3_000_000,
                amount_incl_vat_aed=3_000_000,
                due_date="2028-12-31",
            )
        ],
    )
    generated = ChatbotEngine._compose_remaining_payment_response(
        spa,
        property_type="off_plan",
        seller_asking_price=16_500_000,
    )

    # When: the central validator runs on the deterministic response.
    response, telemetry = validate_and_rewrite_response(
        generated,
        BuyerIntent.payment_plan_query,
        latest_buyer_message="How much remains to the developer?",
    )

    # Then: the known remaining-payment wording is not mistaken for a back-calculation.
    assert response == generated
    assert "AED 3,000,000" in response
    assert telemetry["verified_facts_output_rewrites"] == 0


def test_engine_finalizer_runs_verified_facts_output_gate_on_model_final_text() -> None:
    # Given: model-finalized text with an unsafe numeric LTV claim.
    engine = ChatbotEngine()

    # When: the central engine finalizer prepares the response for return/persist.
    response, telemetry = engine._finalize_response(
        "For this off-plan resale, the bank can finance 50% LTV.",
        BuyerIntent.general_enquiry,
        latest_buyer_message="What LTV can I get?",
    )

    # Then: the unsafe claim does not reach the direct API/chatbot return path.
    assert "50% LTV" not in response
    assert "listing agent needs to confirm" in response.lower()
    assert telemetry["verified_facts_output_rewrites"] == 1


def test_whatsapp_send_path_records_verified_facts_output_gate_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given: a direct WhatsApp outbound body that bypasses chatbot generation.
    from app.api.whatsapp import send_whatsapp_reply

    transport = CapturingTransport()
    set_transport_override(transport)
    monkeypatch.setattr("app.api.whatsapp.service_session", None)
    caplog.set_level(logging.INFO, logger="app.api.whatsapp")

    try:
        # When: the buyer-facing WhatsApp send seam sends the body.
        send_whatsapp_reply(
            "whatsapp:+971500000001",
            "The developer NOC should take 3-5 days once we apply.",
            from_number="whatsapp:+971500000002",
        )
    finally:
        set_transport_override(None)

    # Then: the transport receives the rewritten safe body.
    assert transport.sent_to_buyer is not None
    assert "3-5 days" not in transport.sent_to_buyer.body
    assert "listing agent needs to confirm" in transport.sent_to_buyer.body.lower()
    rewrite_logs = [
        record
        for record in caplog.records
        if record.getMessage()
        == "[VerifiedFacts] Rewrote standalone outbound WhatsApp body before transport"
    ]
    assert len(rewrite_logs) == 1
    assert rewrite_logs[0].verified_facts_output_rewrites == 1
    assert rewrite_logs[0].verified_facts_output_topics == ("noc_transfer",)
