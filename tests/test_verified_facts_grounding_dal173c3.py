"""DAL-173C3 — Verified Facts grounding for Dubai process/fee answers.

Pure tests for answer-planning metadata and deterministic fee response guards.
No DB, network, WhatsApp send, hot-list, draft, lead-ingest, or frontend paths.
"""
from __future__ import annotations

from app.core.chatbot_engine import ChatbotEngine
from app.core.prompt_builder import build_verified_facts_grounding_section
from app.core.verified_facts import (
    FactScope,
    RuntimePolicy,
    VerifiedFact,
    VerifiedFactRegistry,
    direct_fact_for_key,
    verified_facts_grounding_for_message,
)
from app.schemas.spa import SPAParseResult


def _raw(**overrides):
    base = {
        "key": "dld_registration_fee_pct",
        "category": "fees",
        "domain": "dubai_real_estate",
        "scope": "global",
        "text": "The standard Dubai Land Department (DLD) property registration fee is 4% of the purchase price, paid by the buyer.",
        "source_label": "DLD fee schedule",
        "source_ref": "S1",
        "status": "confirmed",
        "transaction_specific": False,
        "active": True,
    }
    base.update(overrides)
    return base


def _fact(**overrides):
    return VerifiedFact.from_raw(_raw(**overrides))


def _ready_spa():
    return SPAParseResult(
        project="Test Tower",
        unit_number="1201",
        developer="Test Developer",
        property_type="Apartment",
        purchase_price_aed=2_000_000,
        property_status="ready",
        payment_schedule=[],
    )


def test_known_dubai_fee_question_includes_active_verified_fact_context():
    registry = VerifiedFactRegistry([_fact()])
    grounding = verified_facts_grounding_for_message(
        "What are the DLD fees if I buy?",
        registry=registry,
    )
    section = build_verified_facts_grounding_section(grounding)

    assert grounding is not None
    assert grounding.direct_facts[0].key == "dld_registration_fee_pct"
    assert "4% of the purchase price" in section
    assert "DLD fee schedule [S1]" in section
    assert "Do not invent fee percentages" in section


def test_inactive_or_missing_fact_fails_closed():
    registry = VerifiedFactRegistry([_fact(active=False)])
    grounding = verified_facts_grounding_for_message(
        "What is the DLD transfer fee?",
        registry=registry,
    )
    section = build_verified_facts_grounding_section(grounding)

    assert grounding is not None
    assert grounding.direct_facts == ()
    assert "DLD transfer/registration fee" in grounding.missing_topics
    assert "None for this buyer turn" in section
    assert "listing agent needs to confirm" in section


def test_property_listing_fact_without_process_claim_is_unchanged():
    registry = VerifiedFactRegistry([_fact()])

    assert verified_facts_grounding_for_message(
        "How many bedrooms and how large is the unit?",
        registry=registry,
    ) is None
    assert build_verified_facts_grounding_section(None) == ""


def test_unverified_legal_process_claim_is_blocked_for_agent_confirmation():
    registry = VerifiedFactRegistry([
        _fact(
            key="off_plan_pre_handover_rental_legality",
            category="off_plan",
            text="Whether an off-plan unit can be legally rented before handover is pending Eric/legal confirmation; do not state as law.",
            source_label="Internal pending legal",
            source_ref=None,
            status="Eric decision required",
        )
    ])
    grounding = verified_facts_grounding_for_message(
        "Is it legal to rent before handover?",
        registry=registry,
    )
    section = build_verified_facts_grounding_section(grounding)

    assert grounding is not None
    assert grounding.direct_facts == ()
    assert grounding.blocked_facts[0].runtime_policy is RuntimePolicy.DRAFT_FOR_AGENT_ONLY
    assert "policy=draft_for_agent_only" in section
    assert "agent needs to confirm" in section


def test_tenant_fact_is_used_only_for_matching_brokerage():
    global_fact = _fact(text="Global DLD fee is 4%.", source_label="Global DLD", source_ref="S1")
    tenant_fact = _fact(
        scope=FactScope.TENANT.value,
        brokerage_id="brokerage-A",
        text="Brokerage A verified DLD fee is 4%.",
        source_label="Brokerage A compliance note",
        source_ref="TA1",
    )
    registry = VerifiedFactRegistry([global_fact, tenant_fact])

    assert direct_fact_for_key(
        registry,
        "dld_registration_fee_pct",
        brokerage_id="brokerage-A",
    ).source_label == "Brokerage A compliance note"
    assert direct_fact_for_key(
        registry,
        "dld_registration_fee_pct",
        brokerage_id="brokerage-B",
    ).source_label == "Global DLD"


def test_total_fees_response_uses_active_verified_dld_fact_source():
    response = ChatbotEngine._compose_total_fees_response(
        spa=_ready_spa(),
        seller_asking_price=2_000_000,
        dld_fee_fact=_fact(),
    )

    assert "DLD transfer fee (4%, source: DLD fee schedule [S1])" in response
    assert "AED 80,000" in response


def test_total_fees_response_fails_closed_without_active_dld_fact():
    response = ChatbotEngine._compose_total_fees_response(
        spa=_ready_spa(),
        seller_asking_price=2_000_000,
        dld_fee_fact=None,
    )

    assert "4%" not in response
    assert "DLD/government transfer fees" in response
    assert "confirm" in response.lower()


def test_grounding_metadata_does_not_reference_send_ranking_or_drafts():
    section = build_verified_facts_grounding_section(
        verified_facts_grounding_for_message(
            "What are the DLD fees?",
            registry=VerifiedFactRegistry([_fact()]),
        )
    )
    lowered = section.lower()

    assert "whatsapp" not in lowered
    assert "send policy" not in lowered
    assert "hot-list" not in lowered
    assert "ranking" not in lowered
    assert "draft generation" not in lowered
