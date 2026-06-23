# Task 2 DAL-199 Code Quality Review

Verdict: PASS

codeQualityStatus: WATCH
recommendation: APPROVE
reportPath: `.omo/evidence/task-2-dalya-post-closeout-hardening-code-review.md`
blockers: []

## Findings

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

1. `scripts/run_focused_backend_qa.py` is 227 pure LOC. This is under the 250 hard ceiling, but still in the programming-skill warning band; the next non-trivial runner edit should split responsibilities before the file grows further.

2. `_emit(...)` still carries eight parameters at `scripts/run_focused_backend_qa.py:179`. This is not blocking for the current guard fix, but it remains parameter-bloat from the programming perspective.

3. The `Status` enum match at `scripts/run_focused_backend_qa.py:207` does not include an explicit unreachable/default assertion. The enum is closed and current statuses are covered, so this is a low-risk strictness note rather than a release blocker.

## Prior Blocker Recheck

The previous blocker is fixed.

- PASS: canonical, `./`-prefixed, repo-absolute, directory-discovery, and package-style module selectors now normalize through `scripts/focused_backend_qa_policy.py:70` and block DB-backed selections before venv creation, dependency install, or pytest.
- PASS: directory selectors are rejected at `scripts/focused_backend_qa_policy.py:42` with `db_backed_directory_discovery_disallowed`.
- PASS: explicit DB-backed files are rejected at `scripts/focused_backend_qa_policy.py:50` with `db_backed_tests_disallowed`.
- PASS: the runner checks suite policy before real-run setup at `scripts/run_focused_backend_qa.py:261`, returning with `commands: []`.
- PASS: the regression test covers DB-backed canonical, dot-prefixed, absolute, directory, and module forms, plus allowed no-DB equivalents at `tests/test_focused_backend_qa_runner.py:31` and `tests/test_focused_backend_qa_runner.py:50`.

## Programming Perspective

Skill-perspective check: ran. I loaded `omo:programming` and `references/python/README.md` before judging the Python code and tests.

Result: no blocking programming violation under the requested criteria. The guard parses untrusted pytest selectors into normalized repo-relative paths before policy decisions, handles pytest node IDs and module selectors, fails closed on directory discovery and unclassified test selections, avoids broad exception swallowing, and keeps complexity bounded. The remaining programming notes are LOW only: main runner size warning band, `_emit` parameter count, and strict enum-match exhaustiveness.

## remove-ai-slops Perspective

Skill-perspective check: ran. I loaded `omo:remove-ai-slops` before judging test relevance, evidence quality, and maintainability.

Result: no blocking slop violation. The tests are not deletion-only, do not merely assert that code was removed, and are not tautological constants-only checks; they exercise policy outcomes across the exact bypass shapes that previously failed. The production helper is a small policy extraction with a real caller plus tests, not speculative abstraction. The evidence does not fake a runtime green: all local runtime QA artifacts inspected report `BLOCKED`, including the legacy-named `.omo/evidence/task-2-runtime-qa-green.json`.

## Evidence Checked

- `python3 -m unittest tests.test_focused_backend_qa_runner`: PASS, 2 tests.
- `python3 -m py_compile scripts/run_focused_backend_qa.py scripts/focused_backend_qa_policy.py tests/test_focused_backend_qa_runner.py`: PASS.
- `python3 scripts/run_focused_backend_qa.py --python python3.12 --evidence .omo/evidence/task-2-runtime-qa-review-dot-block.json -- ./tests/test_seller_lead_privacy.py -q`: exit 2, `BLOCKED`, `db_backed_tests_disallowed`, `commands: []`.
- `python3 scripts/run_focused_backend_qa.py --python python3.12 --evidence .omo/evidence/task-2-runtime-qa-review-directory-block.json -- tests -q`: exit 2, `BLOCKED`, `db_backed_directory_discovery_disallowed`, `commands: []`.
- `python3 scripts/run_focused_backend_qa.py --python python3.12 --evidence .omo/evidence/task-2-runtime-qa-review-module-block.json -- tests.test_seller_lead_privacy -q`: exit 2, `BLOCKED`, `db_backed_tests_disallowed`, `commands: []`.
- Direct classifier check for canonical, dot-prefixed, absolute, directory, and module selectors: all returned DB-backed or directory-discovery block reasons.
- Existing `.omo/evidence/dal-199-task2-canonical-blocked.json`, `dot-blocked.json`, `absolute-blocked.json`, `directory-blocked.json`, and `module-blocked.json`: all inspected as `status=BLOCKED`, `commands=0`.
- Existing `.omo/evidence/dal-199-task2-default-check-only.json`: `status=BLOCKED` because local Python is 3.14 / repo venv symlink is broken, with `suite_policy=allowed_no_db_tests_only` and `commands=0`.
- Existing `.omo/evidence/task-2-runtime-qa-green.json`: inspected as `status=BLOCKED`, not PASS, with `commands=0`.
- `git diff --check`: PASS.
- `rg -n "<<<<<<<|=======|>>>>>>>" scripts docs tests`: no matches.
- `test ! -d /private/tmp/dalya-focused-backend-qa-venv`: PASS.
- Pure LOC: `scripts/run_focused_backend_qa.py` 227, `scripts/focused_backend_qa_policy.py` 93, `tests/test_focused_backend_qa_runner.py` 47.

## Scope And Acceptance

- PASS: deterministic `BLOCKED` behavior is preserved when no compatible Python is available.
- PASS: no runtime green claim remains; the legacy `task-2-runtime-qa-green.json` filename contains a blocked artifact and the evidence text calls that out.
- PASS: DB-backed tests are blocked for canonical, dot-prefixed, absolute, directory, and module-style selectors.
- PASS: no dependency, lockfile, env-file, DB/product behavior, migration, DDL, RLS, grant, live write, CI workflow, or app behavior change appears in the scoped review.
- PASS: no temp venv remains at `/private/tmp/dalya-focused-backend-qa-venv`.

## Missing Input Notes

No notepad path or full precomputed diff was provided in the review input. I treated the listed scoped files and evidence paths as the Task 2 diff scope, inspected the untracked files directly with line numbers, and verified the tracked `BACKLOG.md` DAL-199 edit.
