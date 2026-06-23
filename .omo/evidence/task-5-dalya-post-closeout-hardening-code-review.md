# Task 5 / DAL-202 Code Review

Verdict: WATCH
codeQualityStatus: WATCH
recommendation: APPROVE
reportPath: `.omo/evidence/task-5-dalya-post-closeout-hardening-code-review.md`
blockers: none

## Skill-Perspective Check

- `remove-ai-slops` skill was loaded and applied as a review lens for overfit/slop, tautological tests, needless production complexity, and oversized modules.
- `programming` skill was loaded, including the Python reference, and applied for typed Python, no `Any`/`cast`/`type-ignore`, parse-boundary discipline, and the 250 pure-LOC ceiling.
- Result: no blocking violations of either perspective. The tests are mostly behavior-oriented and the helper is typed. Watch items are listed under LOW.

## Reviewed Scope

- `app/core/verified_facts_output_rules.py`
- `tests/test_verified_facts_rule_key_integrity.py`
- `scripts/verify_verified_facts_rule_keys.py`
- `BACKLOG.md`
- `PROJECT_BRIEF.md`
- `.omo/evidence/task-5-dalya-post-closeout-hardening.md`
- `.omo/evidence/task-5-rule-key-integrity.json`
- `.omo/evidence/task-5-rule-key-map.md`

## Findings

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

1. `.omo/evidence/task-5-rule-key-map.md:33` still lists `seller_original_purchase_price` as having no matching seed fact, while the live seed has it at `app/core/data/verified_facts_seed.json:187` as a `do not state` privacy fact. The final task evidence correctly calls this a mapper discrepancy at `.omo/evidence/task-5-dalya-post-closeout-hardening.md:23`, so this is not blocking, but the map artifact itself is stale and could confuse a future audit. Small fix: update the map to mark that key as seed-present/do-not-state, or mark the map as superseded by the loader-verified JSON.

2. `tests/test_verified_facts_rule_key_integrity.py:59` directly negative-tests bad `runtime_policy`, and `tests/test_verified_facts_rule_key_integrity.py:28` checks the current expected-missing reasons are non-empty. It does not directly negative-test the helper branch at `app/core/verified_facts_output_rules.py:70` for a whitespace-only custom reason. I manually confirmed the helper rejects that case, so this is not a correctness blocker. Small fix: add a fixture with `reason="   "` and assert `expected_missing_empty_reason`.

3. `app/core/verified_facts_output_rules.py` is now 241 pure LOC. That is under the >250 defect threshold requested for this review, but it is in the programming skill warning band. Small fix for the next edit: split rule-key integrity metadata/helper or the claim-rule table into a focused module before adding more production lines.

## Validation Assessment

- Focused integrity tests: PASS.
  Command run: `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. python3 -m pytest --noconftest -p no:cacheprovider tests/test_verified_facts_rule_key_integrity.py -q`
  Result: `3 passed in 0.01s`.

- Required broader Verified Facts regression: BLOCKED honestly.
  Command run: `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. python3 -m pytest --noconftest -p no:cacheprovider tests/test_verified_facts_output_gate.py tests/test_verified_facts_seed_closing_costs.py tests/test_verified_facts_rule_key_integrity.py -q`
  Result: collection fails before tests run with `ModuleNotFoundError: No module named 'anthropic'` from `app/core/chatbot_engine.py`.

- Diff hygiene: PASS.
  Command run: `git diff --check`
  Result: exit 0.

- Conflict marker scan: PASS for code/test/script paths.
  Command run: `rg -n '<<<<<<<|=======|>>>>>>>' app/core tests scripts`
  Result: exit 1, no matches.

- File-size check: PASS with warning.
  Pure LOC measured by `awk`:
  `app/core/verified_facts_output_rules.py` 241, `tests/test_verified_facts_rule_key_integrity.py` 57, `scripts/verify_verified_facts_rule_keys.py` 88.

## Acceptance Review

- Bogus non-null fact keys are rejected by `verify_claim_rule_fact_keys`, covered by `tests/test_verified_facts_rule_key_integrity.py:40`.
- Bad expected-missing metadata is rejected by helper logic at `app/core/verified_facts_output_rules.py:69`; runtime-policy rejection is covered by `tests/test_verified_facts_rule_key_integrity.py:59`, and whitespace reason rejection was manually probed.
- Current `CLAIM_RULES` pass only when non-null keys are loader-present or expected-missing/defer-only. Live probe returned no failures for current rules.
- `fact_key=None` rules are skipped by seed lookup at `app/core/verified_facts_output_rules.py:87` and asserted as the three explicit defer-only topics at `tests/test_verified_facts_rule_key_integrity.py:31`.
- No buyer-facing output behavior changed: `app/core/verified_facts_output_gate.py` and the seed file are unchanged; the diff in `app/core/verified_facts_output_rules.py` adds metadata, types, and a pure helper before the existing rule table.
- No broad direct-safe fact expansion occurred. `seller_original_purchase_price` is seed-present but `do_not_state`; `specific_noc_transfer_timing` is seed-present but `draft_for_agent_only`; the three actual missing rule keys are expected-missing/defer-only.
- The JSON verifier evidence is truthful for current code: `.omo/evidence/task-5-rule-key-integrity.json:3` says passed, `.omo/evidence/task-5-rule-key-integrity.json:18` records the three expected-missing keys, and `.omo/evidence/task-5-rule-key-integrity.json:38` records the mapper discrepancy for `seller_original_purchase_price`.

## Final Judgment

APPROVE with WATCH notes. There are no CRITICAL/HIGH findings and no blockers. The remaining issues are evidence cleanup and narrow test-hardening improvements, not correctness failures for DAL-202.
