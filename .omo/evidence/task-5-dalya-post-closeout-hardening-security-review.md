# Task 5 / DAL-202 Security Review

## Reviewer

Name: Security Researcher
Scope reviewed: Task 5 Verified Facts rule-key integrity from `.omo/plans/dalya-post-closeout-hardening.md`.
Files inspected: `app/core/verified_facts_output_rules.py`, `tests/test_verified_facts_rule_key_integrity.py`, `scripts/verify_verified_facts_rule_keys.py`, `.omo/evidence/task-5-dalya-post-closeout-hardening.md`, `.omo/evidence/task-5-rule-key-integrity.json`, `.omo/evidence/task-5-rule-key-map.md`, `BACKLOG.md`, `PROJECT_BRIEF.md`.
Supporting files inspected: `app/core/verified_facts.py`, `app/core/verified_facts_output_gate.py`, `app/core/data/verified_facts_seed.json`, `tests/test_verified_facts_seed_closing_costs.py`, `tests/test_verified_facts_output_gate.py`.
Files not found but expected: none.

## Verdict

Verdict: WATCH
Launch readiness: Yellow
Score: 8/10
One-sentence verdict: The Task 5 implementation preserves the output gate's privacy/security posture and does not broaden direct-safe facts, but the broader output-gate regression remains locally blocked by missing runtime dependencies.

## Top Findings

### Critical / High / Medium

No Critical, High, or Medium security/privacy findings found in this Task 5 scope.

### Low / Watch

1. **Broader output-gate regression is still locally blocked**
   - Severity: Low / Watch.
   - Attack scenario: A future change could regress the runtime output gate while the narrow rule-key integrity suite stays green, because the full output-gate regression cannot currently collect under the active local Python environment.
   - Evidence: The task evidence records the required broader regression as blocked by `ModuleNotFoundError: No module named 'anthropic'` in `.omo/evidence/task-5-dalya-post-closeout-hardening.md:65-71`. I independently reran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -p no:cacheprovider --noconftest tests/test_verified_facts_output_gate.py tests/test_verified_facts_seed_closing_costs.py tests/test_verified_facts_rule_key_integrity.py -q`; it failed during `tests/test_verified_facts_output_gate.py` collection for the same missing `anthropic` import.
   - Recommended fix: Run the broader regression under the approved focused Python 3.12/3.13 dependency path once available, without dependency/lockfile edits or env-file reads.
   - Files/areas likely affected: local QA/runtime environment, not Task 5 product code.
   - Verification step: `PYTHONPATH=. python3 -m pytest --noconftest tests/test_verified_facts_output_gate.py tests/test_verified_facts_seed_closing_costs.py tests/test_verified_facts_rule_key_integrity.py -q` passes in the approved local runtime.

## Security Assertions Reviewed

- Direct-safe facts were not expanded by this change. The new integrity helper only checks whether a non-null `CLAIM_RULES` key is seed-present or explicitly expected-missing; it does not alter `direct_fact_for_key` or output rewriting behavior. Evidence: `verify_claim_rule_fact_keys(...)` returns failures only for metadata/rule-key integrity in `app/core/verified_facts_output_rules.py:61-102`, while direct-safe runtime policy remains derived only in `app/core/verified_facts.py:66-80` and returned only when `fact.is_directly_answerable` is true in `app/core/verified_facts.py:274-296`.
- Missing output-gate keys are explicitly defer-only, not silently accepted. Evidence: `EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS` lists `off_plan_mortgage_ltv_policy`, `generic_noc_fee`, and `off_plan_payment_process_mechanics` with non-empty rationales and `runtime_policy: "defer_only"` in `app/core/verified_facts_output_rules.py:45-58`; invalid metadata is rejected in `app/core/verified_facts_output_rules.py:69-85` and tested in `tests/test_verified_facts_rule_key_integrity.py:59-83`.
- Arbitrary missing rule keys are rejected by default. Evidence: the helper rejects non-null keys absent from seed and expected-missing metadata in `app/core/verified_facts_output_rules.py:87-100`, and `test_integrity_helper_rejects_bogus_fact_key` proves `missing_typo` fails in `tests/test_verified_facts_rule_key_integrity.py:40-56`.
- `fact_key=None` rules remain explicit defer-only. Evidence: the helper skips seed lookup for `None` keys in `app/core/verified_facts_output_rules.py:87-89`, and the integrity test asserts the only null-key topics are `generic_fee_amount`, `legal_tax_advice`, and `tenancy_legal_process` in `tests/test_verified_facts_rule_key_integrity.py:31-37`.
- Seller original purchase price remains protected. Evidence: the seed marks `seller_original_purchase_price` as category `privacy` and status `do not state` in `app/core/data/verified_facts_seed.json:187-198`; the output gate always returns the blocking rule for do-not-state facts before direct-support checks in `app/core/verified_facts_output_gate.py:87-95` and implements that check in `app/core/verified_facts_output_gate.py:143-159`.
- Evidence does not falsely claim a full green. Evidence: the narrow integrity test is green in `.omo/evidence/task-5-dalya-post-closeout-hardening.md:41-53`, helper JSON reports `"passed": true` only for the rule-key verifier in `.omo/evidence/task-5-rule-key-integrity.json:1-4`, and the broader output-gate regression is explicitly recorded as BLOCKED in `.omo/evidence/task-5-dalya-post-closeout-hardening.md:55-71`.
- Scope stayed outside Task 10b and live infrastructure. Evidence: Task 5 scope confirmations state no Task 10b, dependency/lockfile edits, production/staging env reads, DB tests/access, live writes, migrations, DDL, RLS, or role/grant mutation in `.omo/evidence/task-5-dalya-post-closeout-hardening.md:142-150`. Reviewed changed Task 5 files do not introduce migrations, env reads, service-role access, DB/live writes, or dependency edits.

## Verification Performed

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -p no:cacheprovider --noconftest tests/test_verified_facts_rule_key_integrity.py -q` -> `3 passed in 0.01s`.
- Broader regression rerun -> blocked during collection by missing `anthropic`, matching existing evidence.
- `git diff --check` -> exit 0.
- Anchored conflict-marker scan over relevant Task 5 files -> no matches.

## Residual Risk Assessment

Residual risk is low and operational. The integrity guard is narrow and suitable for preventing rule-key drift, but it is not a substitute for the blocked runtime output-gate regression. The JSON helper evidence labels seed-present keys as `seed_resolved`; reviewers must continue checking the seed runtime policy for sensitive keys like `seller_original_purchase_price`, which is seed-present specifically as `do not state`, not buyer-direct.
