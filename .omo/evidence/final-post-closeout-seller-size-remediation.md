# Final Post-Closeout Seller Size Remediation

Date: 2026-06-23

## Change

- Extracted seller conversation summary, offer, and activity response construction out of `app/api/seller.py`.
- Added `app/api/seller_conversations.py` for stable buyer numbering, message counts, offer flag detection, language detection, timestamps, fallback summaries, and seller-summary redaction.
- Added `app/api/seller_activity.py` for the existing seller activity feed serialization.
- Kept `app/api/seller.py` route ownership checks in place before delegation.
- Stored `ai_summary` and agent-facing identity remain untouched; the sanitizer is only applied while building the seller conversation response.
- Preserved malformed `offer:` behavior: seller conversation `offer_made` is based on the `offer:` reason flag, while offers/activity still skip malformed amount parsing.

## Evidence

Scenario: changed Python files compile.

Invocation:

```bash
python3 -m py_compile app/api/seller.py app/api/seller_conversations.py app/api/seller_activity.py app/core/seller_summary_privacy.py tests/test_seller_conversation_summary_privacy.py scripts/verify_seller_conversation_summary_privacy.py scripts/seller_summary_privacy_contract.py scripts/seller_summary_privacy_isolation.py scripts/seller_summary_privacy_app_probe.py
```

Binary observable: exit 0, no stderr.

Captured artifact path: `.omo/evidence/final-post-closeout-seller-size-remediation.md`

Scenario: pure seller summary sanitizer contract still passes.

Invocation:

```bash
PYTHONPATH=. python3 -c 'from scripts.seller_summary_privacy_contract import pure_first_name_redaction_passes, pure_phone_redaction_passes, pure_recursive_redaction_passes; print({"pure_first_name_redaction": pure_first_name_redaction_passes(), "pure_phone_redaction": pure_phone_redaction_passes(), "pure_recursive_preservation": pure_recursive_redaction_passes()})'
```

Binary observable:

```text
{'pure_first_name_redaction': True, 'pure_phone_redaction': True, 'pure_recursive_preservation': True}
```

Captured artifact path: `.omo/evidence/final-post-closeout-seller-size-remediation.md`

Scenario: app-level seller privacy verifier attempted.

Invocation:

```bash
PYTHONPATH=. python3 scripts/verify_seller_conversation_summary_privacy.py --evidence .omo/evidence/final-post-closeout-seller-size-remediation-privacy.json
```

Binary observable: exit 1 with verifier status `BLOCKED`.

Captured artifact path: `.omo/evidence/final-post-closeout-seller-size-remediation-privacy.json`

Blocker:

```json
{
  "forbidden_runtime_blocker": "missing_module:sqlalchemy",
  "status": "BLOCKED",
  "pure_first_name_redaction": true,
  "pure_phone_redaction": true,
  "pure_recursive_preservation": true
}
```

Scenario: focused pytest attempted.

Invocation:

```bash
PYTHONPATH=. python3 -m pytest tests/test_seller_conversation_summary_privacy.py -q
```

Binary observable: exit 4, blocked during `tests/conftest.py` import.

Captured artifact path: `.omo/evidence/final-post-closeout-seller-size-remediation.md`

Blocker:

```text
ModuleNotFoundError: No module named 'fastapi'
```

Scenario: whitespace diff check.

Invocation:

```bash
git diff --check -- app/api/seller.py app/api/seller_conversations.py app/api/seller_activity.py app/core/seller_summary_privacy.py tests/test_seller_conversation_summary_privacy.py scripts/verify_seller_conversation_summary_privacy.py scripts/seller_summary_privacy_contract.py scripts/seller_summary_privacy_isolation.py scripts/seller_summary_privacy_app_probe.py .omo/evidence/final-post-closeout-seller-size-remediation-privacy.json
```

Binary observable: exit 0, no output.

Captured artifact path: `.omo/evidence/final-post-closeout-seller-size-remediation.md`

Scenario: conflict marker scan on owned files.

Invocation:

```bash
rg -n "^(<<<<<<<|=======|>>>>>>>)" app/api/seller.py app/api/seller_conversations.py app/api/seller_activity.py app/core/seller_summary_privacy.py tests/test_seller_conversation_summary_privacy.py scripts/verify_seller_conversation_summary_privacy.py scripts/seller_summary_privacy_contract.py scripts/seller_summary_privacy_isolation.py scripts/seller_summary_privacy_app_probe.py .omo/evidence/final-post-closeout-seller-size-remediation-privacy.json
```

Binary observable: exit 1, no matches.

Captured artifact path: `.omo/evidence/final-post-closeout-seller-size-remediation.md`

Scenario: pure LOC for changed production/test/script Python files.

Invocation:

```bash
for file in app/api/seller.py app/api/seller_conversations.py app/api/seller_activity.py app/core/seller_summary_privacy.py tests/test_seller_conversation_summary_privacy.py scripts/verify_seller_conversation_summary_privacy.py scripts/seller_summary_privacy_contract.py scripts/seller_summary_privacy_isolation.py scripts/seller_summary_privacy_app_probe.py; do count=$(awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(#|\/\/|--)/' "$file" | wc -l | tr -d ' '); printf '%s %s\n' "$file" "$count"; done
```

Binary observable:

```text
app/api/seller.py 167
app/api/seller_conversations.py 177
app/api/seller_activity.py 190
app/core/seller_summary_privacy.py 122
tests/test_seller_conversation_summary_privacy.py 88
scripts/verify_seller_conversation_summary_privacy.py 99
scripts/seller_summary_privacy_contract.py 133
scripts/seller_summary_privacy_isolation.py 56
scripts/seller_summary_privacy_app_probe.py 201
```

Captured artifact path: `.omo/evidence/final-post-closeout-seller-size-remediation.md`

## Residual Risk

- Runtime route verification and focused pytest were not executable in this local environment because `sqlalchemy` and `fastapi` are missing.
- Static compile, pure sanitizer probes, conflict scan, diff check, and size measurements completed successfully.
