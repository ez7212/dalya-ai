from __future__ import annotations

import re

from app.core.verified_facts import load_verified_facts
from app.core.verified_facts_output_rules import (
    CLAIM_RULES,
    EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS,
    OutputClaimRule,
    verify_claim_rule_fact_keys,
)


def _seeded_fact_keys() -> frozenset[str]:
    return frozenset(fact.key for fact in load_verified_facts())


def test_claim_rules_fact_keys_resolve_to_seed_or_expected_missing_defer_only() -> None:
    # Given: the default Verified Facts seed and the output-gate claim rules.
    seeded_fact_keys = _seeded_fact_keys()

    # When: rule fact-key integrity is checked.
    failures = verify_claim_rule_fact_keys(CLAIM_RULES, seeded_fact_keys)

    # Then: every non-null key is seeded or explicitly expected-missing, and
    # fact_key=None rules remain explicit defer-only rules with no seed lookup.
    assert failures == ()
    for metadata in EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS.values():
        assert metadata["reason"].strip()
        assert metadata["runtime_policy"] == "defer_only"
    assert {
        rule.topic for rule in CLAIM_RULES if rule.fact_key is None
    } == {
        "generic_fee_amount",
        "legal_tax_advice",
        "tenancy_legal_process",
    }


def test_integrity_helper_rejects_bogus_fact_key() -> None:
    # Given: a rule with a non-null fact key that is neither seeded nor expected.
    bogus_rule = OutputClaimRule(
        topic="bogus_typo",
        fact_key="missing_typo",
        patterns=(re.compile(r"missing typo"),),
        deferral="Defer this unsupported claim.",
    )

    # When: the integrity helper checks that rule against the real seed keys.
    failures = verify_claim_rule_fact_keys((bogus_rule,), _seeded_fact_keys())

    # Then: the bogus key is rejected instead of silently becoming defer-only.
    assert len(failures) == 1
    assert failures[0].fact_key == "missing_typo"
    assert failures[0].topic == "bogus_typo"
    assert failures[0].problem == "missing_seed_fact_key"


def test_integrity_helper_rejects_invalid_expected_missing_metadata() -> None:
    # Given: an expected-missing annotation with an invalid runtime policy.
    rule = OutputClaimRule(
        topic="bad_policy",
        fact_key="policy_gap",
        patterns=(re.compile(r"policy gap"),),
        deferral="Defer this unsupported claim.",
    )

    # When: the integrity helper checks the custom policy metadata.
    failures = verify_claim_rule_fact_keys(
        (rule,),
        _seeded_fact_keys(),
        expected_missing={
            "policy_gap": {
                "reason": "This test fixture should fail metadata validation.",
                "runtime_policy": "direct",
            },
        },
    )

    # Then: invalid expected-missing metadata is reported as a failure.
    assert len(failures) == 1
    assert failures[0].fact_key == "policy_gap"
    assert failures[0].problem == "expected_missing_runtime_policy"
