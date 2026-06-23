# Task 5 / DAL-202 Verified Facts rule-key map

Scope mapped from:
- `app/core/verified_facts_output_rules.py::CLAIM_RULES`
- `app/core/verified_facts.py`
- `app/core/data/verified_facts_seed.json`
- `tests/test_verified_facts_output_gate.py`
- `tests/test_verified_facts_seed_closing_costs.py`
- `.omo/plans/dalya-post-closeout-hardening.md`

## 1) Current non-null `fact_key` values in `CLAIM_RULES`

Unique non-null keys, in rule order:
- `dld_registration_fee_pct`
- `off_plan_mortgage_ltv_policy`
- `specific_noc_transfer_timing`  
  Appears in two rules: `noc_timeline` and `trustee_closing_timeline`
- `generic_noc_fee`
- `off_plan_payment_process_mechanics`
- `seller_original_purchase_price`

Rules with `fact_key=None`:
- `generic_fee_amount`
- `legal_tax_advice`
- `tenancy_legal_process`

## 2) Seed-data coverage

Seed keys present in `app/core/data/verified_facts_seed.json` that match rule keys:
- `dld_registration_fee_pct`
- `specific_noc_transfer_timing`

Rule keys with no matching seed fact:
- `off_plan_mortgage_ltv_policy`
- `generic_noc_fee`
- `off_plan_payment_process_mechanics`
- `seller_original_purchase_price`

Non-rule seed keys that exist but are not output-rule keys:
- `dld_title_deed_certificate_fee`
- `dld_map_fee_policy`
- `dld_knowledge_innovation_fees`
- `dld_trustee_service_partner_fee`
- `dld_mortgaged_sale_service_fee`
- `dld_mortgage_fee_varies_by_bank`
- `broker_commission_form_contract_caveat`
- `dld_sale_registration_documents`
- `off_plan_requires_developer_noc`
- `trakheesi_permit_exists`
- `off_plan_pre_handover_rental_legality`
- `emaar_oasis_resale_premium`
- `legacy_dld_fee_note` (inactive)

## 3) `fact_key=None` rules to treat as explicit defer-only

These are already explicit defer-only in the current output gate because they have no backing fact key:
- `generic_fee_amount` -> fee claims involving generic brokerage/agent/service/admin/processing fees
- `legal_tax_advice` -> legal/tax assertions; defers to qualified advisor
- `tenancy_legal_process` -> tenancy/eviction/vacant-possession/legal-process assertions; defers to qualified advisor

## 4) Typo candidate vs intentional missing/defer-only candidate

Obvious typo candidate: none surfaced from the current sources.

Intentionally missing / defer-only candidates:
- `off_plan_mortgage_ltv_policy` looks intentionally absent from seed data because the rule targets unsupported mortgage/LTV claims and the existing tests already treat the related topic as non-direct.
- `generic_noc_fee` looks intentionally absent from seed data and is the strongest candidate for an explicit expected-missing annotation if the executor adds one, because the output gate blocks generic NOC fee assertions and the seed tests already assert it should not become a direct fact.
- `off_plan_payment_process_mechanics` looks intentionally absent because it targets back-calculated payment mechanics that the gate should defer.
- `seller_original_purchase_price` looks intentionally absent because the seed itself marks that fact as `do not state` and the gate should never surface it directly.
- `specific_noc_transfer_timing` is present in seed data, but the seed classifies it as `transaction_specific: true`, so it is draft-for-agent-only rather than direct-safe; that matches the gate’s defer behavior for timing claims.

## 5) Existing verification commands and likely blockers

Commands already implied by the plan/tests:
- `PYTHONPATH=. python3 -m pytest --noconftest tests/test_verified_facts_output_gate.py tests/test_verified_facts_seed_closing_costs.py -q`
- `python3 -m py_compile app/core/verified_facts_output_rules.py tests/test_verified_facts_rule_key_integrity.py`
- optional helper suggested by the plan: `PYTHONPATH=. python3 scripts/verify_verified_facts_rule_keys.py --evidence .omo/evidence/task-5-rule-key-integrity.json`

Likely blockers to expect before implementation:
- `tests/test_verified_facts_rule_key_integrity.py` does not exist yet in the current tree.
- `app/core/verified_facts_output_rules.py` does not currently define `EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS` or any similar explicit expected-missing registry.
- `app/core/verified_facts.py` only exposes runtime-policy derivation and direct-fact lookup helpers; there is no rule-key integrity helper there yet.
- The existing output-gate tests validate current behavior but do not enforce full rule-key/seed integrity for all non-null `fact_key` values.
