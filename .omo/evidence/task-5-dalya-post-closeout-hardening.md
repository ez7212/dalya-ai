# Task 5 / DAL-202 Verified Facts Rule-Key Integrity

## Scope

- Task source: `.omo/plans/dalya-post-closeout-hardening.md`, Task 5.
- Linear: DAL-202.
- Changed implementation/test files: `app/core/verified_facts_output_rules.py`, `tests/test_verified_facts_rule_key_integrity.py`, `scripts/verify_verified_facts_rule_keys.py`.
- Tracking/evidence updates: `BACKLOG.md`, `PROJECT_BRIEF.md`, `.omo/evidence/task-5-rule-key-integrity.json`, this file.

## Implementation

- Added `EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS` with non-empty `reason` and `runtime_policy="defer_only"` for:
  - `off_plan_mortgage_ltv_policy`
  - `generic_noc_fee`
  - `off_plan_payment_process_mechanics`
- Added `verify_claim_rule_fact_keys(...)`, a pure helper that:
  - accepts explicit rules and seed keys;
  - treats `fact_key=None` rules as explicit defer-only and skips seed lookup;
  - rejects non-null keys not present in seed keys or expected-missing metadata;
  - rejects expected-missing metadata with an empty reason or non-`defer_only` runtime policy.
- Added `tests/test_verified_facts_rule_key_integrity.py`, including `test_integrity_helper_rejects_bogus_fact_key`.
- Added `scripts/verify_verified_facts_rule_keys.py` to write structured JSON evidence.
- Incorporated mapper input from `.omo/evidence/task-5-rule-key-map.md`; direct loader verification found `seller_original_purchase_price` is seed-present, so it remains seed-resolved rather than expected-missing.

## Validation

### RED

Scenario: integrity suite before helper/expected-missing registry existed.

Invocation:

```bash
PYTHONPATH=. python3 -m pytest --noconftest tests/test_verified_facts_rule_key_integrity.py -q
```

Observable: failed during collection with `ImportError: cannot import name 'EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS' from 'app.core.verified_facts_output_rules'`.

Artifact: terminal output captured in this evidence file.

### GREEN

Scenario: current rule set integrity and bogus-key rejection.

Invocation:

```bash
PYTHONPATH=. python3 -m pytest --noconftest tests/test_verified_facts_rule_key_integrity.py -q
```

Observable: `3 passed in 0.01s`.

Artifact: terminal output captured in this evidence file.

### Regression

Scenario: required broader Verified Facts output-gate regression.

Invocation:

```bash
PYTHONPATH=. python3 -m pytest --noconftest tests/test_verified_facts_output_gate.py tests/test_verified_facts_seed_closing_costs.py tests/test_verified_facts_rule_key_integrity.py -q
```

Observable: BLOCKED before tests ran because the active Python 3.14 environment lacks `anthropic`, imported by `app/core/chatbot_engine.py` during `tests/test_verified_facts_output_gate.py` collection:

```text
ModuleNotFoundError: No module named 'anthropic'
```

Artifact: terminal output captured in this evidence file. No dependency install or lockfile edit was attempted.

### Static

Invocation:

```bash
python3 -m py_compile app/core/verified_facts_output_rules.py tests/test_verified_facts_rule_key_integrity.py scripts/verify_verified_facts_rule_keys.py
```

Observable: exit 0.

Artifact: terminal output captured in this evidence file.

### Helper Evidence

Invocation:

```bash
PYTHONPATH=. python3 scripts/verify_verified_facts_rule_keys.py --evidence .omo/evidence/task-5-rule-key-integrity.json
```

Observable: exit 0 and JSON `"passed": true`.

Artifact: `.omo/evidence/task-5-rule-key-integrity.json`.

Binary observables in the JSON artifact:

- `non_null_fact_keys`: `dld_registration_fee_pct`, `generic_noc_fee`, `off_plan_mortgage_ltv_policy`, `off_plan_payment_process_mechanics`, `seller_original_purchase_price`, `specific_noc_transfer_timing`.
- `seed_present_rule_keys`: `dld_registration_fee_pct`, `seller_original_purchase_price`, `specific_noc_transfer_timing`.
- `expected_missing_output_gate_fact_keys`: `off_plan_mortgage_ltv_policy`, `generic_noc_fee`, `off_plan_payment_process_mechanics`, each with `runtime_policy="defer_only"`.
- `fact_key_none_topics`: `generic_fee_amount`, `legal_tax_advice`, `tenancy_legal_process`.
- `mapper_discrepancies_verified_by_loader`: `seller_original_purchase_price`.
- `failures`: empty list.

### Diff/Conflict

Invocation:

```bash
git diff --check
```

Observable: exit 0.

Invocation:

```bash
rg -n "<<<<<<<|=======|>>>>>>>" app/core tests scripts
```

Observable: exit 1 with no matches, which is the expected clean conflict-marker result for `rg`.

Artifact: terminal output captured in this evidence file.

### File Size

Invocation:

```bash
awk '!/^[[:space:]]*$/ && !/^[[:space:]]*#/ { count++ } END { print count+0 }' app/core/verified_facts_output_rules.py
awk '!/^[[:space:]]*$/ && !/^[[:space:]]*#/ { count++ } END { print count+0 }' tests/test_verified_facts_rule_key_integrity.py
awk '!/^[[:space:]]*$/ && !/^[[:space:]]*#/ { count++ } END { print count+0 }' scripts/verify_verified_facts_rule_keys.py
```

Observable:

- `app/core/verified_facts_output_rules.py`: 241 pure LOC, warning band but under the 250 pure-LOC ceiling.
- `tests/test_verified_facts_rule_key_integrity.py`: 57 pure LOC.
- `scripts/verify_verified_facts_rule_keys.py`: 88 pure LOC.

## Scope Confirmations

- No Task 10b work.
- No dependency or lockfile edits.
- No production/staging env-file reads.
- No DB tests, external DB access, live writes, migrations, production/staging DDL, RLS enablement, or role/grant mutation.
- No direct-safe fact expansion.
- No buyer-facing output behavior change.
- No typo correction was made because direct seed verification found no typo candidate.

## Command Center

Invocation:

```bash
COMMAND_CENTER_WORKING_DIR="$PWD" npm --prefix /Users/eric/command-center run activity-log -- --project dalya --title "Verify Verified Facts rule keys" --work-type coding --labels testing,verified-facts --purpose "Prevent output-gate fact_key drift from silently bypassing Verified Facts seed coverage" --process "Added expected-missing defer-only metadata, a pure rule-key integrity helper, regression tests including bogus-key rejection, and JSON evidence generation" --outcome "Current output rules pass integrity; missing runtime dependencies still block the broader output-gate pytest regression"
```

Observable: `activity-log ok project=dalya id=dalya-2026-06-23-verify-verified-facts-rule-keys-9bb390e2`.

## Residual Risk

- The broader output-gate regression remains locally BLOCKED until the runtime has installed project dependencies or an approved Python 3.12/3.13 focused QA path. The pure integrity suite, helper script, static compile, diff check, and conflict scan passed.
