# DAL-201 Task 4 Post-Recursive-Fix Code Review

Verdict: WATCH
codeQualityStatus: WATCH
recommendation: APPROVE
reportPath: /Users/eric/dalya-ai/.omo/evidence/task-4-dalya-post-closeout-hardening-code-review.md
blockers: []

## Scope Reviewed

- `app/api/seller.py`
- `app/core/seller_summary_privacy.py`
- `tests/test_seller_conversation_summary_privacy.py`
- `scripts/verify_seller_conversation_summary_privacy.py`
- `BACKLOG.md`
- `PROJECT_BRIEF.md`
- Evidence listed in the review request

The worktree contains unrelated dirty/untracked files. This review stayed bounded to DAL-201 and refreshed only this report artifact. No notepad path was provided.

## Skill-Perspective Check

Ran before judging test relevance and maintainability:

- Loaded `omo:remove-ai-slops` from `/Users/eric/.codex/plugins/cache/sisyphuslabs/omo/4.13.0/skills/remove-ai-slops/SKILL.md`.
- Loaded `omo:programming` from `/Users/eric/.codex/plugins/cache/sisyphuslabs/omo/4.13.0/skills/programming/SKILL.md`.
- Loaded Python reference `/Users/eric/.codex/plugins/cache/sisyphuslabs/omo/4.13.0/skills/programming/references/python/README.md`.

Remove-ai-slops perspective: the latest test/verifier additions are not deletion-only, tautological, or merely checking that content was removed. They now assert nested safe content survives with redaction placeholders.

Programming perspective: production code is scoped and typed. The focused test and verifier files exceed the 250 pure-LOC smell threshold (`321` and `320` pure LOC), so I leave that as LOW/WATCH harness debt, not an approval blocker for this privacy fix.

## CRITICAL

None.

## HIGH

None.

## MEDIUM

1. API/TestClient proof remains blocked locally, so route execution is not green evidence in this environment.

   Static wiring is correct: the seller route sanitizes `conv.ai_summary` into a local `summary_text` response copy at `app/api/seller.py:245` and returns it at `app/api/seller.py:267`. Runtime evidence is still blocked, not passing: `.omo/evidence/task-4-seller-summary-api.json:12` and `.omo/evidence/task-4-seller-summary-api.qa.json:10` report `BLOCKED` with `missing_module:dotenv` at line 5 in both files. `.omo/evidence/task-4-runtime-qa-investigation.md:9` also records API/TestClient QA as blocked.

## LOW

1. The focused test and verifier are oversized harness files.

   `tests/test_seller_conversation_summary_privacy.py` is 321 pure LOC and `scripts/verify_seller_conversation_summary_privacy.py` is 320 pure LOC. This does not create a false PASS, but future additions should split fixture setup/cleanup from pure sanitizer assertions.

2. `.omo/evidence/task-4-seller-summary-api.qa.json` is older-schema blocked evidence.

   It truthfully reports `BLOCKED`, but unlike `.omo/evidence/task-4-seller-summary-api.json:8`, it does not include the newer `pure_recursive_preservation` field. This is evidence hygiene only; it does not overstate API success.

## Checks Passed

- Recursive nested summary preservation is now implemented. Top-level filtering only keeps the seller summary contract keys, including `summary` and `_fallback`, at `app/core/seller_summary_privacy.py:36` and `app/core/seller_summary_privacy.py:61`. Allowed values then recurse through strings, lists, and dicts at `app/core/seller_summary_privacy.py:88`, with nested dict keys and values sanitized at `app/core/seller_summary_privacy.py:102` and list shape preserved at `app/core/seller_summary_privacy.py:106`.
- Unknown top-level raw keys remain blocked by the allowlist comprehension at `app/core/seller_summary_privacy.py:61`.
- Prior PII protections remain: email/WhatsApp/UAE/local/international phone/conversation-token regexes are defined at `app/core/seller_summary_privacy.py:9`; redaction is applied at `app/core/seller_summary_privacy.py:73`; buyer full-name and 3+ char name-token redaction is applied at `app/core/seller_summary_privacy.py:82` and tokenized at `app/core/seller_summary_privacy.py:123`.
- API route sanitizes only the seller response copy. There is no write back to `conv.ai_summary`, `conv.buyer_name`, or `conv.buyer_phone` in `app/api/seller.py:245`. Agent dashboard identity remains sourced from raw conversation fields at `app/api/agent_dashboard.py:790`.
- Tests/verifier now fail the prior deletion behavior. The focused unit test asserts exact recursive output for nested `buyer_context`, `summary`, and `topics` at `tests/test_seller_conversation_summary_privacy.py:298`; the verifier has an exact pure recursive preservation check at `scripts/verify_seller_conversation_summary_privacy.py:243`.
- Evidence is truthful: pure sanitizer evidence reports PASS with `recursive_contract_values_preserved` at `.omo/evidence/task-4-seller-summary-privacy-pure.json:8` and `status` PASS at line 46; API/TestClient evidence reports BLOCKED rather than green at `.omo/evidence/task-4-seller-summary-api.json:12` and `.omo/evidence/task-4-seller-summary-api.qa.json:10`.
- Documentation matches the inspected behavior and caveats: `BACKLOG.md:164` and `PROJECT_BRIEF.md:71` both describe recursive seller-visible redaction, unknown top-level key dropping, stored/agent identity preservation, and blocked API/TestClient evidence.

## Reviewer Verification

- Read required `remove-ai-slops`, `programming`, and Python programming references.
- Inspected source with line numbers and current evidence artifacts.
- Ran an independent no-write pure sanitizer probe with `python3 -B`; it passed recursive preservation for nested dict/list values, nested dict keys, `_fallback` list values, unknown top-level key dropping, first-name/full-name redaction, email, WhatsApp, UAE/local phones, `+44`, `+1`, and conversation IDs.
- Ran no-write syntax compilation via `compile(...)` over the DAL-201 Python files: PASS.
- Ran scoped `git diff --check -- app/api/seller.py BACKLOG.md PROJECT_BRIEF.md`: PASS.
- Ran conflict-marker scan across DAL-201 files and requested evidence: no matches.
- Did not rerun pytest/TestClient because the requested review is write-limited and the existing local runtime evidence shows the DB/TestClient path is blocked by missing supported dependencies/runtime.

## Test And Evidence Assessment

The latest fix satisfies the previously rejected recursive nested-summary requirement by code inspection, focused unit assertions, verifier assertions, pure PASS evidence, and my independent pure probe. The API route wiring is also correct by inspection, but endpoint execution remains a WATCH item because local TestClient evidence is blocked. No CRITICAL or HIGH findings remain.

Smallest concrete fixes if this were to be tightened further: run the focused pytest/verifier in a supported Python 3.12/3.13 dependency environment, and split the oversized test/verifier harness before adding more cases.
