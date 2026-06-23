# Task 4 / DAL-201 Security/Privacy Review

Date: 2026-06-23
Reviewer: Security Researcher
Mode: Review only; product code not modified.
Verdict: WATCH

## Scope Reviewed

- `app/api/seller.py`
- `app/core/seller_summary_privacy.py`
- `tests/test_seller_conversation_summary_privacy.py`
- `scripts/verify_seller_conversation_summary_privacy.py`
- `.omo/evidence/task-4-dalya-post-closeout-hardening.md`
- `.omo/evidence/task-4-seller-summary-privacy-pure.json`
- `.omo/evidence/task-4-seller-summary-api.json`
- `.omo/evidence/task-4-runtime-qa-investigation.md`
- `.omo/evidence/task-4-seller-summary-api.qa.json`
- `.omo/evidence/task-4-dalya-post-closeout-hardening-gate-review.md`

## Verdict

Launch readiness for DAL-201 Task 4 privacy fix: Yellow / WATCH
Score: 8/10

One-sentence verdict: The latest recursive fix satisfies the seller-summary privacy contract in the pure sanitizer and is statically wired into the seller `/conversations` response without mutating stored or agent-facing data, but endpoint-level TestClient/API proof remains blocked locally and must stay a WATCH caveat rather than a false green.

## Findings

### Critical / High

No Critical or High privacy/security blocker was found in this scoped review.

### Medium - Endpoint-level API proof is still blocked locally

- Attack scenario: A future route, serializer, dependency override, or response-shape change bypasses the sanitizer even though pure sanitizer behavior is correct; without runnable API proof in this environment, the executed seller response path is not independently proven here.
- Evidence:
  - The seller route authorizes listing ownership before returning conversations at `app/api/seller.py:221-225`.
  - The seller route builds a local `summary_text` by passing `conv.ai_summary` through `sanitize_seller_ai_summary()` with `buyer_name`, `buyer_phone`, and `conversation_id` at `app/api/seller.py:245-255`.
  - The seller response appends anonymized `buyer_label`, counts, sanitized `summary`, offer flag, timestamps, and language at `app/api/seller.py:267-285`; it does not return `buyer_name`, `buyer_phone`, raw messages, or conversation ID on this path.
  - Local pytest remains blocked before collection by missing `fastapi`; reviewer rerun: `PYTHONPATH=. python3 -m pytest --noconftest tests/test_seller_conversation_summary_privacy.py -q` exited 2 with `ModuleNotFoundError: No module named 'fastapi'`.
  - Local verifier remains blocked by missing `dotenv`; reviewer rerun printed `{"evidence": ".omo/evidence/task-4-seller-summary-api.reviewer.json", "status": "BLOCKED"}`, and the scratch evidence file was removed to honor the requested write scope.
  - Prior evidence records the same API/TestClient blocker honestly at `.omo/evidence/task-4-seller-summary-api.json:1-14`, `.omo/evidence/task-4-seller-summary-api.qa.json:1-12`, and `.omo/evidence/task-4-runtime-qa-investigation.md:7-13`.
- Recommended fix: Run the focused pytest and verifier in the supported backend runtime, or provide a no-external-DB TestClient harness that proves the seller endpoint without reading live env or touching external databases.
- Verification step: Attach PASS evidence showing seller response redaction, cross-seller 403 leak-free behavior, stored `ai_summary` preservation, and authorized agent identity preservation.

### Low - Short first-name-only mentions are outside the covered redaction guarantee

- Attack scenario: If a stored buyer name is a short token such as `Jo Li` and a nested seller summary says only `Jo wants a viewing`, the token-length guard can leave that first name visible.
- Evidence: `MIN_NAME_TOKEN_LENGTH` is `3` at `app/core/seller_summary_privacy.py:20`; `_buyer_name_parts()` filters shorter tokens at `app/core/seller_summary_privacy.py:123-138`. Current tests cover `Sara` first-name-only redaction at `tests/test_seller_conversation_summary_privacy.py:272-280`.
- Recommended fix: Track a follow-up to redact short first-name tokens when they are known buyer-name parts and not in a small safe-token allowlist.
- Verification step: Add pure sanitizer cases for two-letter and three-letter buyer names, including a non-name/common-word over-redaction guard.

## Privacy Contract Checks

- PASS - Recursive nested values: `_sanitize_json_value()` recursively handles strings, lists, and dicts at `app/core/seller_summary_privacy.py:88-99`; `_sanitize_list()` recurses through list members at `app/core/seller_summary_privacy.py:106-110`.
- PASS - Nested dict keys: `_sanitize_dict()` redacts dict keys and values at `app/core/seller_summary_privacy.py:102-103`.
- PASS - Top-level unknown raw keys: `sanitize_seller_ai_summary()` returns only keys in `SELLER_SUMMARY_KEYS` at `app/core/seller_summary_privacy.py:36-45` and `app/core/seller_summary_privacy.py:61-66`; the regression includes `raw_prompt` and expects it to be dropped at `tests/test_seller_conversation_summary_privacy.py:313-335`.
- PASS - Covered PII classes: `_redact_text()` applies WhatsApp, email, exact conversation ID, `conv_*` token, buyer phone, UAE phone, UAE local mobile, international phone, full buyer name, and first-name-token redaction at `app/core/seller_summary_privacy.py:73-85`.
- PASS - `+44` and `+1` examples: tests assert `+44 7700 900123` and `+1 415 555 2671` become `[redacted phone]` at `tests/test_seller_conversation_summary_privacy.py:283-295`; pure evidence records those examples at `.omo/evidence/task-4-seller-summary-privacy-pure.json:5-8`.
- PASS - Safe context preservation: the focused recursive regression expects nested `buyer_context`, `summary`, `topics`, nested dict keys, and nested list content to retain `wants a viewing tomorrow` while replacing PII placeholders at `tests/test_seller_conversation_summary_privacy.py:298-335`.
- PASS - Stored and agent-facing data not mutated: the seller route uses local `summary_text` and does not assign back to `conv.ai_summary`, `conv.buyer_name`, or `conv.buyer_phone` at `app/api/seller.py:245-285`; tests assert stored `ai_summary`, `buyer_name`, and `buyer_phone` remain unchanged at `tests/test_seller_conversation_summary_privacy.py:264-269`, and agent dashboard identity remains visible to authorized agents at `tests/test_seller_conversation_summary_privacy.py:338-351`.
- PASS - Evidence honesty: `.omo/evidence/task-4-dalya-post-closeout-hardening.md:168-206` records pytest/API verifier blockers rather than claiming endpoint green; `.omo/evidence/task-4-runtime-qa-investigation.md:7-13` explicitly distinguishes pure sanitizer PASS from API/TestClient BLOCKED.

## Reviewer Verification Commands

- `python3 -m py_compile app/core/seller_summary_privacy.py tests/test_seller_conversation_summary_privacy.py scripts/verify_seller_conversation_summary_privacy.py`
  - Result: PASS, exit 0.
- Pure sanitizer command covering nested `buyer_context`, `summary`, nested `topics`, nested list values, PII-bearing dict keys, full name, first-name-only `Sara`, email, WhatsApp, UAE/local phone, `+44 7700 900123`, exact conversation ID, unknown `raw_prompt`, and safe context.
  - Result: PASS, exit 0.
- `PYTHONPATH=. python3 -m pytest --noconftest tests/test_seller_conversation_summary_privacy.py -q`
  - Result: BLOCKED before collection, `ModuleNotFoundError: No module named 'fastapi'`.
- `PYTHONPATH=. python3 scripts/verify_seller_conversation_summary_privacy.py --evidence .omo/evidence/task-4-seller-summary-api.reviewer.json`
  - Result: BLOCKED, stdout status `BLOCKED`; scratch evidence file removed after inspection to keep only the allowed refreshed artifact.

## Residual Risk Assessment

No remaining high/critical privacy risk was found that should block Task 4. The prior final-gate failure mode, nested dict/list seller summary content being dropped instead of recursively redacted, is closed in current code and pure evidence.

Residual WATCH items:

- API/TestClient endpoint proof remains blocked in this local environment, so endpoint confidence rests on static route review plus focused tests/evidence inspection until a supported runtime executes the suite.
- Short first-name-only buyer mentions below three characters are not covered by the current privacy guarantee.
- The sanitizer is purpose-built for the Task 4 PII classes; additional identity types such as passport/Emirates ID strings should be considered in a broader seller-summary privacy hardening task if those fields can enter AI summaries.

## Linear-Ready Follow-Ups

Title: DAL-201 - Produce runnable seller summary privacy API proof
Priority: Medium

Description:
Run the seller conversation summary privacy pytest and verifier in a supported backend runtime, or add a no-external-DB TestClient harness, so DAL-201 has endpoint-level proof in addition to pure sanitizer proof.

Acceptance Criteria:
- `tests/test_seller_conversation_summary_privacy.py` passes in the supported runtime.
- `scripts/verify_seller_conversation_summary_privacy.py --evidence .omo/evidence/task-4-seller-summary-api.json` records `status: "PASS"`.
- PASS evidence covers seller redaction, forbidden seller response, stored summary preservation, and authorized agent identity preservation.

Title: DAL-201 - Harden short first-name seller-summary redaction
Priority: Low

Description:
Add a focused sanitizer follow-up for short buyer-name tokens so first-name-only seller summaries do not leak two-letter names while avoiding broad over-redaction of common words.

Acceptance Criteria:
- Pure sanitizer tests cover two-letter first names, three-letter first names, and a common-word false-positive guard.
- Seller-visible placeholders still preserve safe context.
