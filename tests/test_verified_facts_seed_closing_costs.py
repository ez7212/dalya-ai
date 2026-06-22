from __future__ import annotations

from app.core.verified_facts import (
    FactScope,
    FactStatus,
    RuntimePolicy,
    load_verified_facts,
)

EXPECTED_CONFIRMED_CLOSING_COST_FACTS = {
    "dld_title_deed_certificate_fee": "S1",
    "dld_map_fee_policy": "S1",
    "dld_knowledge_innovation_fees": "S1",
    "dld_trustee_service_partner_fee": "S1;S4",
    "dld_mortgaged_sale_service_fee": "S2",
    "dld_mortgage_fee_varies_by_bank": "S2",
    "broker_commission_form_contract_caveat": "S4",
}


NON_DIRECT_FEE_TOPICS = (
    "generic_noc_fee",
    "vat_on_brokerage_invoice",
    "managing_brokerage_fee",
)


def test_seed_has_confirmed_direct_closing_cost_facts():
    # Given: the default Verified Facts seed fixture.
    facts = load_verified_facts()
    facts_by_key = {fact.key: fact for fact in facts}

    # When: Task 7 closing-cost keys are inspected.
    keys = set(facts_by_key)

    # Then: each expected local-source fact is active, direct-safe, and cited.
    assert EXPECTED_CONFIRMED_CLOSING_COST_FACTS.keys() <= keys
    for key, source_ref in EXPECTED_CONFIRMED_CLOSING_COST_FACTS.items():
        fact = facts_by_key[key]
        assert fact.status is FactStatus.CONFIRMED
        assert fact.runtime_policy is RuntimePolicy.DIRECT
        assert fact.is_directly_answerable is True
        assert fact.active is True
        assert fact.transaction_specific is False
        assert fact.scope is FactScope.GLOBAL
        assert fact.effective_date == "2026-06-19"
        assert fact.source_ref == source_ref


def test_seed_has_no_duplicate_keys_and_direct_facts_are_general_confirmed():
    # Given: the default Verified Facts seed fixture.
    facts = load_verified_facts()

    # When: seed keys and buyer-direct facts are collected.
    keys = [fact.key for fact in facts]
    direct_facts = [fact for fact in facts if fact.is_directly_answerable]

    # Then: loader-visible keys are unique and direct facts stay policy-safe.
    assert len(keys) == len(set(keys))
    assert direct_facts
    for fact in direct_facts:
        assert fact.status is FactStatus.CONFIRMED
        assert fact.active is True
        assert fact.transaction_specific is False


def test_seed_does_not_upgrade_draft_or_eric_decision_fee_topics():
    # Given: the default Verified Facts seed fixture after the Task 7 additions.
    facts = load_verified_facts()
    facts_by_key = {fact.key: fact for fact in facts}
    direct_keys = {fact.key for fact in facts if fact.is_directly_answerable}

    # When: non-direct closing-cost topics are checked.
    existing_transfer_timing = facts_by_key["specific_noc_transfer_timing"]

    # Then: NOC fee, brokerage-invoice VAT, and generic brokerage fees remain absent
    # from direct seed facts, and timing remains transaction-specific.
    assert not (set(NON_DIRECT_FEE_TOPICS) & direct_keys)
    assert all(topic not in facts_by_key for topic in NON_DIRECT_FEE_TOPICS)
    assert existing_transfer_timing.status is FactStatus.CONFIRMED
    assert existing_transfer_timing.runtime_policy is RuntimePolicy.DRAFT_FOR_AGENT_ONLY
    assert existing_transfer_timing.transaction_specific is True
