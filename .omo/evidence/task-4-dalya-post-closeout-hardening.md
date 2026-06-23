# Task 4 / DAL-201 - Seller Summary Privacy Final Gate Fix

Date: 2026-06-23

## Scope

- Final gate rejection fixed: seller-visible summary sanitization no longer drops nested dict/list content under allowed summary fields.
- Owned implementation files changed:
  - `app/core/seller_summary_privacy.py`
  - `tests/test_seller_conversation_summary_privacy.py`
  - `scripts/verify_seller_conversation_summary_privacy.py`
- Owned docs/evidence refreshed:
  - `BACKLOG.md`
  - `PROJECT_BRIEF.md`
  - `.omo/evidence/task-4-dalya-post-closeout-hardening.md`
  - `.omo/evidence/task-4-seller-summary-privacy-pure.json`
  - `.omo/evidence/task-4-seller-summary-api.json`
- Existing unrelated worktree changes were not reverted.

## Change

- Added `summary` to the top-level seller-visible summary contract allowlist.
- Changed allowed seller summary values to sanitize recursively through string, list, and dict values.
- Redacts nested dict keys as well as values, while preserving unknown top-level key dropping so prompt/model-injected raw keys are still excluded from seller-visible responses.
- Preserved existing redactions for full buyer names, first-name-only buyer mentions, emails, WhatsApp handles, UAE local/compact/international phones, non-UAE plus-country phones such as `+44` and `+1`, direct conversation IDs, and long `conv_*` tokens.
- Added a focused unit regression requiring nested `buyer_context`, `summary`, and `topics` dict/list shapes to retain safe context and expose placeholders.
- Extended the verifier JSON with `pure_recursive_preservation`.

## Evidence

### Red Reproduction

Scenario: pre-fix pure sanitizer deleted nested allowed values instead of recursively redacting them.

Invocation:

```bash
python3 - <<'PY'
from app.core.seller_summary_privacy import SellerSummaryRedactionContext, sanitize_seller_ai_summary
ctx = SellerSummaryRedactionContext('Sara Privacy', '+971501112222', 'conv_01HPIISECRET1234567890')
summary = {
    'buyer_context': {'one_line': 'Sara Privacy wants a viewing tomorrow +971501112222'},
    'summary': {'one_line': 'Sara Privacy wants a viewing tomorrow +971501112222'},
    'topics': [{'raw': 'Sara Privacy wants a viewing tomorrow +971501112222'}],
}
print(sanitize_seller_ai_summary(summary, ctx))
PY
```

Observable before the fix: exit 0 with deleted nested content.

Captured output:

```text
{'buyer_context': None, 'topics': []}
```

Artifact path: `.omo/evidence/task-4-dalya-post-closeout-hardening.md`.

### Pure Recursive Probe

Scenario: direct pure sanitizer probe preserves nested safe context, redacts PII in nested dict keys and values, allows `summary`, and drops unknown top-level raw keys.

Invocation:

```bash
python3 - <<'PY'
from app.core.seller_summary_privacy import SellerSummaryRedactionContext, sanitize_seller_ai_summary
ctx = SellerSummaryRedactionContext('Sara Privacy', '+971501112222', 'conv_01HPIISECRET1234567890')
summary = {
    'buyer_context': {'one_line': 'Sara Privacy wants a viewing tomorrow +971501112222'},
    'summary': {'one_line': 'Sara Privacy wants a viewing tomorrow +971501112222'},
    'topics': [
        {'raw': 'Sara Privacy wants a viewing tomorrow +971501112222'},
        {'Sara Privacy +971501112222': 'wants a viewing tomorrow'},
    ],
    'raw_prompt': 'Sara Privacy +971501112222',
}
expected = {
    'buyer_context': {'one_line': '[redacted buyer] wants a viewing tomorrow [redacted phone]'},
    'summary': {'one_line': '[redacted buyer] wants a viewing tomorrow [redacted phone]'},
    'topics': [
        {'raw': '[redacted buyer] wants a viewing tomorrow [redacted phone]'},
        {'[redacted buyer] [redacted phone]': 'wants a viewing tomorrow'},
    ],
}
actual = sanitize_seller_ai_summary(summary, ctx)
assert actual == expected, actual
print(actual)
PY
```

Observable: PASS, exit 0.

Captured output:

```text
{'buyer_context': {'one_line': '[redacted buyer] wants a viewing tomorrow [redacted phone]'}, 'summary': {'one_line': '[redacted buyer] wants a viewing tomorrow [redacted phone]'}, 'topics': [{'raw': '[redacted buyer] wants a viewing tomorrow [redacted phone]'}, {'[redacted buyer] [redacted phone]': 'wants a viewing tomorrow'}]}
```

Artifact path: `.omo/evidence/task-4-dalya-post-closeout-hardening.md`.

### Pure Sanitizer Evidence JSON

Scenario: pure seller summary sanitizer recursively redacts allowed nested seller-summary values and nested dict keys while dropping unknown top-level keys.

Invocation:

```bash
python3 - <<'PY'
# Writes .omo/evidence/task-4-seller-summary-privacy-pure.json after asserting:
# - allowed keys include summary
# - buyer_context, summary, and topics nested values are preserved recursively
# - safe context "wants a viewing tomorrow" remains present
# - buyer name tokens, emails, WhatsApp handles, UAE phones, +44/+1 phones, conversation IDs, and prompt_ keys are absent
PY
```

Observable: PASS, exit 0.

Captured output:

```json
{"artifact": ".omo/evidence/task-4-seller-summary-privacy-pure.json", "status": "PASS"}
```

Captured artifact fields:

```json
{
  "recursive_contract_values_preserved": true,
  "nested_dict_keys_redacted": true,
  "safe_context_preserved": true,
  "status": "PASS",
  "summary_key_allowed": true,
  "unknown_keys_dropped": true
}
```

Artifact path: `.omo/evidence/task-4-seller-summary-privacy-pure.json`.

### Python Compile

Scenario: syntax compile for changed sanitizer, focused test, and verifier files.

Invocation:

```bash
python3 -m py_compile app/core/seller_summary_privacy.py tests/test_seller_conversation_summary_privacy.py scripts/verify_seller_conversation_summary_privacy.py
```

Observable: PASS, exit 0.

Captured output: empty.

Artifact path: `.omo/evidence/task-4-dalya-post-closeout-hardening.md`.

### Focused Pytest

Scenario: focused seller conversation summary privacy pytest.

Invocation:

```bash
python3 -m pytest tests/test_seller_conversation_summary_privacy.py -q
```

Observable: BLOCKED before collection, exit 4.

Captured blocker:

```text
ImportError while loading conftest '/Users/eric/dalya-ai/tests/conftest.py'.
tests/conftest.py:11: in <module>
    from fastapi.testclient import TestClient
E   ModuleNotFoundError: No module named 'fastapi'
```

Artifact path: `.omo/evidence/task-4-dalya-post-closeout-hardening.md`.

### TestClient Verifier

Scenario: DB/TestClient seller summary privacy verifier.

Invocation:

```bash
PYTHONPATH=. python3 scripts/verify_seller_conversation_summary_privacy.py --evidence .omo/evidence/task-4-seller-summary-api.json
```

Observable: BLOCKED before TestClient execution, exit 1.

Captured output:

```json
{"evidence": ".omo/evidence/task-4-seller-summary-api.json", "status": "BLOCKED"}
```

Captured blocker from JSON evidence:

```json
{
  "forbidden_runtime_blocker": "missing_module:dotenv",
  "pure_first_name_redaction": true,
  "pure_recursive_preservation": true,
  "status": "BLOCKED"
}
```

Artifact path: `.omo/evidence/task-4-seller-summary-api.json`.

### Import-Path Verifier Attempt

Scenario: verifier invoked without repo import path.

Invocation:

```bash
python3 scripts/verify_seller_conversation_summary_privacy.py --evidence .omo/evidence/task-4-seller-summary-api.json
```

Observable: BLOCKED before evidence write, exit 1.

Captured blocker:

```text
ModuleNotFoundError: No module named 'app'
```

Artifact path: `.omo/evidence/task-4-dalya-post-closeout-hardening.md`.

### Diff Hygiene

Scenario: repository whitespace diff check.

Invocation:

```bash
git diff --check
```

Observable: PASS, exit 0.

Captured output: empty.

Artifact path: `.omo/evidence/task-4-dalya-post-closeout-hardening.md`.

### Conflict Scan

Scenario: conflict marker scan on owned files and evidence.

Invocation:

```bash
rg -n '^(<<<<<<<|=======|>>>>>>>)' app/core/seller_summary_privacy.py tests/test_seller_conversation_summary_privacy.py scripts/verify_seller_conversation_summary_privacy.py BACKLOG.md PROJECT_BRIEF.md .omo/evidence/task-4-dalya-post-closeout-hardening.md .omo/evidence/task-4-seller-summary-privacy-pure.json
```

Observable: PASS/no matches, exit 1.

Captured output: empty.

Artifact path: `.omo/evidence/task-4-dalya-post-closeout-hardening.md`.

### Size Check

Scenario: pure LOC check for changed Python files.

Invocations and captured outputs:

```text
awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(#|--)/' app/core/seller_summary_privacy.py | wc -l
     122

awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(#|--)/' tests/test_seller_conversation_summary_privacy.py | wc -l
     321

awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(#|--)/' scripts/verify_seller_conversation_summary_privacy.py | wc -l
     320
```

Observable: sanitizer is below the threshold. The focused test and verifier files are above the 250 pure-LOC project smell threshold; they were already oversized in this shared worktree before this final gate fix, and no broad split was performed because the assignment explicitly constrained scope to the sanitizer rejection.

Artifact path: `.omo/evidence/task-4-dalya-post-closeout-hardening.md`.

## Review Notes

- Single responsibility: `seller_summary_privacy.py` owns seller-visible summary redaction only.
- Boundary purity: the existing `JsonValue` recursive alias remains the sanitizer boundary type.
- Variant discrimination: recursive value handling uses `match`.
- Escape hatches: no new `Any`, casts, or type ignores.
- Defensive layer: no redundant post-write validation code added.
- Tests: the new focused regression would fail if nested dict/list handling reverted to deletion.
- Parameter bloat: no new function exceeds three parameters.

## Residual Risk

- Focused pytest and TestClient API behavior are not locally green because the current Python environment lacks required app dependencies (`fastapi`, `dotenv`).
- `app/core/seller_summary_privacy.py`, `tests/test_seller_conversation_summary_privacy.py`, `scripts/verify_seller_conversation_summary_privacy.py`, and the refreshed Task 4 evidence files are untracked in the current shared worktree. This evidence records command behavior against the current filesystem content.

## F4 Remediation Addendum

Artifact: `.omo/evidence/final-post-closeout-f4-remediation.md`.

Current file-size truth after F4 remediation:

```text
tests/test_seller_conversation_summary_privacy.py       88
scripts/verify_seller_conversation_summary_privacy.py       99
scripts/seller_summary_privacy_contract.py      133
scripts/seller_summary_privacy_isolation.py       56
scripts/seller_summary_privacy_app_probe.py      201
```

The DB-backed pytest/verifier now install a local SQLite isolation harness before app import. The local run remains BLOCKED by missing `sqlalchemy`, but `.omo/evidence/task-4-seller-summary-api.json` records `failed_before_app_db_import: true`, `dotenv_reads_blocked: true`, and `forbidden_runtime_blocker: missing_module:sqlalchemy`.
