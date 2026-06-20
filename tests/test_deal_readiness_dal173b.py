"""DAL-173B — DealReadinessProfile core tests.

Pure unit tests (no DB, no network, no side effects). Validate stage derivation,
missing-field surfacing, investor vs end-user handling, deterministic next-best
action, and purity (no input mutation, repeatable output).
"""
from __future__ import annotations

import copy

from app.core.deal_readiness import (
    NextBestAction,
    PriorityBand,
    ReadinessStage,
    compute_readiness,
)


def _complete_fields():
    return {
        "budget_min_aed": 3_000_000,
        "budget_max_aed": 4_500_000,
        "financing": "cash",
        "purpose": "end_user",
        "timeline": "this month",
        "target_areas": ["Dubai Hills"],
        "property_type": "villa",
        "bedrooms": 4,
        "viewing_availability": "Thursday evening",
        "decision_makers": "buying with wife",
        "in_dubai_now": "yes",
        "contact_preference": "whatsapp",
        "family_size": "family of 4",
    }


def test_complete_profile_high_readiness():
    profile = compute_readiness(
        _complete_fields(),
        conversation_ctx={"responsive": True, "urgent": True},
    )
    assert profile.score >= 70
    assert profile.priority_band is PriorityBand.HIGH
    assert profile.stage in {ReadinessStage.QUALIFIED, ReadinessStage.HOT}
    assert profile.missing_fields == []


def test_hot_when_qualified_and_high_intent_and_responsive():
    profile = compute_readiness(
        _complete_fields(),
        conversation_ctx={"responsive": True, "viewing_intent": False, "urgent": True},
    )
    assert profile.stage is ReadinessStage.HOT
    assert profile.next_best_action is NextBestAction.AGENT_CALL_NOW


def test_missing_financing_viewing_decision_surfaced():
    fields = {
        "budget_max_aed": 2_000_000,
        "purpose": "investment",
        "target_areas": ["Marina"],
        # no financing, no viewing_availability, no decision_makers
    }
    profile = compute_readiness(
        fields,
        conversation_ctx={"viewing_intent": True, "offer_intent": True},
    )
    assert "financing" in profile.missing_fields
    assert "viewing_availability" in profile.missing_fields
    assert "decision_makers" in profile.missing_fields


def test_new_buyer_asks_budget_first():
    profile = compute_readiness({})
    assert profile.stage is ReadinessStage.NEW
    assert profile.next_best_action is NextBestAction.ASK_BUDGET
    assert profile.priority_band is PriorityBand.LOW


def test_next_best_action_priority_is_deterministic():
    # budget present, purpose missing -> ask_purpose (not financing/timeline)
    fields = {"budget_max_aed": 2_000_000}
    a = compute_readiness(fields)
    b = compute_readiness(fields)
    assert a == b  # deterministic
    assert a.next_best_action is NextBestAction.ASK_PURPOSE


def test_investor_vs_end_user_handled():
    investor = compute_readiness({**_base_qualified(), "purpose": "investment"})
    end_user = compute_readiness({**_base_qualified(), "purpose": "end_user"})
    # end-user surfaces family_size as helpful-missing; investor does not
    assert "family_size" in end_user.missing_fields
    assert "family_size" not in investor.missing_fields
    # both reach at least qualified
    assert investor.stage in {ReadinessStage.QUALIFIED, ReadinessStage.HOT}
    assert end_user.stage in {ReadinessStage.QUALIFIED, ReadinessStage.HOT}


def test_offer_intent_prepares_offer_context_when_ready():
    fields = {**_base_qualified(), "decision_makers": "sole", "viewing_availability": "anytime"}
    profile = compute_readiness(
        fields,
        conversation_ctx={"offer_intent": True},
        listing_ctx={"listing_id": "listing-1"},
    )
    assert profile.stage is ReadinessStage.OFFER_READY
    assert profile.next_best_action is NextBestAction.PREPARE_OFFER_CONTEXT


def test_legal_question_routes_to_agent():
    profile = compute_readiness(_complete_fields(), conversation_ctx={"legal_question": True})
    assert profile.stage is ReadinessStage.AGENT_TAKEOVER_REQUIRED
    assert profile.next_best_action is NextBestAction.CANNOT_ANSWER_NEEDS_AGENT


def test_pure_no_input_mutation():
    fields = _complete_fields()
    ctx = {"responsive": True}
    listing = {"listing_id": "x"}
    fields_snapshot = copy.deepcopy(fields)
    ctx_snapshot = copy.deepcopy(ctx)
    listing_snapshot = copy.deepcopy(listing)
    compute_readiness(fields, conversation_ctx=ctx, listing_ctx=listing)
    assert fields == fields_snapshot
    assert ctx == ctx_snapshot
    assert listing == listing_snapshot


def _base_qualified():
    return {
        "budget_max_aed": 3_000_000,
        "financing": "mortgage_preapproved",
        "target_areas": ["JVC"],
        "property_type": "apartment",
    }
