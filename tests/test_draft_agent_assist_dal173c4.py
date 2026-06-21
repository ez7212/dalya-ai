"""DAL-173C4 draft/agent-assist metadata tests.

Pure tests only: no DB, network, WhatsApp send, hot-list, lead ingest, frontend,
or migration paths.
"""
from __future__ import annotations

import json

from app.core.draft_agent_assist import build_draft_agent_assist
from app.core.verified_facts import FactScope, VerifiedFact, VerifiedFactRegistry


def _raw_fact(**overrides):
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
    return VerifiedFact.from_raw(_raw_fact(**overrides))


def _effective(**values):
    return {
        field: {
            "value": value,
            "provenance": "agent_confirmed",
            "confidence": None,
            "source_message_id": None,
            "confirmed_by": "agent-1",
            "updated_at": "2026-06-21T00:00:00",
            "suggestion": None,
        }
        for field, value in values.items()
    }


def test_verified_fact_appears_in_agent_draft_context_with_source_label():
    assist = build_draft_agent_assist(
        latest_buyer_message="What are the DLD fees on this purchase?",
        effective_buyer_fields=_effective(budget_max_aed=2_000_000),
        verified_fact_registry=VerifiedFactRegistry([_fact()]),
    )

    facts = assist["verified_facts"]["facts"]
    assert assist["agent_visible"] is True
    assert assist["verified_facts"]["verified_fact_used"] is True
    assert facts[0]["key"] == "dld_registration_fee_pct"
    assert "4% of the purchase price" in facts[0]["text"]
    assert facts[0]["source_label"] == "DLD fee schedule [S1]"


def test_missing_fact_does_not_produce_confident_claim():
    assist = build_draft_agent_assist(
        latest_buyer_message="What is the DLD transfer fee?",
        verified_fact_registry=VerifiedFactRegistry([_fact(active=False)]),
    )
    rendered = json.dumps(assist, sort_keys=True)

    assert assist["verified_facts"]["verified_fact_used"] is False
    assert assist["verified_facts"]["facts"] == []
    assert assist["verified_facts"]["needs_agent_confirmation"][0]["topic"] == "DLD transfer/registration fee"
    assert "4% of the purchase price" not in rendered
    assert "agent confirmation is required" in rendered


def test_readiness_missing_field_generates_one_suggested_follow_up():
    assist = build_draft_agent_assist(
        latest_buyer_message="Can I view it tomorrow?",
        effective_buyer_fields=_effective(
            budget_max_aed=2_000_000,
            purpose="end_user",
            financing="cash",
            timeline="this_month",
            property_type="apartment",
            other_agent_status="not_working_with_agent",
        ),
        conversation_ctx={"viewing_intent": True, "responsive": True},
        listing_ctx={"listing_id": "listing-1"},
        verified_fact_registry=VerifiedFactRegistry([]),
    )

    readiness = assist["deal_readiness"]
    assert readiness["missing_readiness_field"] == "viewing_availability"
    assert readiness["suggested_follow_up_question"] == "What viewing window works for you?"
    assert json.dumps(readiness).count("What viewing window works for you?") == 1


def test_confirmed_field_is_not_reasked():
    assist = build_draft_agent_assist(
        latest_buyer_message="Can I view it tomorrow?",
        effective_buyer_fields=_effective(
            budget_max_aed=2_000_000,
            purpose="end_user",
            financing="cash",
            timeline="this_month",
            property_type="apartment",
            viewing_availability="tomorrow afternoon",
            other_agent_status="not_working_with_agent",
        ),
        conversation_ctx={"viewing_intent": True, "responsive": True},
        listing_ctx={"listing_id": "listing-1"},
        verified_fact_registry=VerifiedFactRegistry([]),
    )

    readiness = assist["deal_readiness"]
    assert readiness["next_best_action"] == "prepare_viewing_brief"
    assert readiness["missing_readiness_field"] is None
    assert readiness["suggested_follow_up_question"] is None


def test_tenant_fact_is_used_only_for_matching_brokerage_in_agent_assist():
    global_fact = _fact(text="Global DLD fee is 4%.", source_label="Global DLD", source_ref="S1")
    tenant_fact = _fact(
        scope=FactScope.TENANT.value,
        brokerage_id="brokerage-A",
        text="Brokerage A verified DLD fee is 4%.",
        source_label="Brokerage A compliance",
        source_ref="TA1",
    )
    registry = VerifiedFactRegistry([global_fact, tenant_fact])

    matching = build_draft_agent_assist(
        latest_buyer_message="What are DLD fees?",
        brokerage_id="brokerage-A",
        verified_fact_registry=registry,
    )
    other = build_draft_agent_assist(
        latest_buyer_message="What are DLD fees?",
        brokerage_id="brokerage-B",
        verified_fact_registry=registry,
    )

    assert matching["verified_facts"]["facts"][0]["source_label"] == "Brokerage A compliance [TA1]"
    assert other["verified_facts"]["facts"][0]["source_label"] == "Global DLD [S1]"


def test_agent_assist_metadata_does_not_reference_send_policy_or_ranking_scope():
    assist = build_draft_agent_assist(
        latest_buyer_message="What are the DLD fees?",
        verified_fact_registry=VerifiedFactRegistry([_fact()]),
    )
    lowered = json.dumps(assist, sort_keys=True).lower()

    assert "whatsapp" not in lowered
    assert "send policy" not in lowered
    assert "autonomous" not in lowered
    assert "hot-list" not in lowered
    assert "ranking" not in lowered
    assert "lead ingest" not in lowered
