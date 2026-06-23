#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
# --- How to run ---
# PYTHONPATH=. python3 scripts/verify_verified_facts_rule_keys.py \
#   --evidence .omo/evidence/task-5-rule-key-integrity.json

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeAlias

from app.core.verified_facts import load_verified_facts
from app.core.verified_facts_output_rules import (
    CLAIM_RULES,
    EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS,
    verify_claim_rule_fact_keys,
)

JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)

MAPPER_REPORTED_MISSING_KEYS = (
    "off_plan_mortgage_ltv_policy",
    "generic_noc_fee",
    "off_plan_payment_process_mechanics",
    "seller_original_purchase_price",
)


def _build_evidence() -> dict[str, JsonValue]:
    seeded_fact_keys = frozenset(fact.key for fact in load_verified_facts())
    failures = verify_claim_rule_fact_keys(CLAIM_RULES, seeded_fact_keys)
    rule_entries: list[JsonValue] = []

    for rule in CLAIM_RULES:
        fact_key = rule.fact_key
        seed_status = "defer_only_none"
        if fact_key is not None and fact_key in seeded_fact_keys:
            seed_status = "seed_present"
        if fact_key is not None and fact_key not in seeded_fact_keys:
            seed_status = "expected_missing"
        rule_entries.append(
            {
                "topic": rule.topic,
                "fact_key": fact_key,
                "seed_status": seed_status,
                "runtime_policy": "defer_only"
                if fact_key is None or fact_key in EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS
                else "seed_resolved",
            }
        )

    mapper_discrepancies = [
        key
        for key in MAPPER_REPORTED_MISSING_KEYS
        if key in seeded_fact_keys
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "rule_count": len(CLAIM_RULES),
        "non_null_fact_keys": sorted(
            {rule.fact_key for rule in CLAIM_RULES if rule.fact_key is not None}
        ),
        "seed_present_rule_keys": sorted(
            {
                rule.fact_key
                for rule in CLAIM_RULES
                if rule.fact_key is not None and rule.fact_key in seeded_fact_keys
            }
        ),
        "expected_missing_output_gate_fact_keys": EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS,
        "mapper_reported_missing_keys": list(MAPPER_REPORTED_MISSING_KEYS),
        "mapper_discrepancies_verified_by_loader": mapper_discrepancies,
        "fact_key_none_topics": sorted(
            rule.topic for rule in CLAIM_RULES if rule.fact_key is None
        ),
        "rules": rule_entries,
        "failures": [
            {
                "fact_key": failure.fact_key,
                "topic": failure.topic,
                "problem": failure.problem,
            }
            for failure in failures
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    evidence_path = Path(args.evidence)

    evidence = _build_evidence()
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return 0 if evidence["passed"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
