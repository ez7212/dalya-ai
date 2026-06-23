# Task 2 Runtime QA Environment Repair Evidence

Date: 2026-06-23
Task: `2. Runtime QA environment repair`
Ticket: `DAL-199`
Requested branch: `codex/runtime-qa-env-repair`

## Scope Delivered

- Added `scripts/run_focused_backend_qa.py`, a focused no-DB backend QA runner.
- Added `docs/runbooks/focused-backend-qa.md` with canonical commands.
- Updated the runner/runbook/backlog evidence after code review so the no-DB path refuses DB/app-state tests before venv creation, dependency install, or pytest.
- Command Center activities: original `dalya-2026-06-23-repair-focused-runtime-qa-path-e9ee4627`; correction `dalya-2026-06-23-correct-focused-backend-qa-db-guardrail-6e421a2a`.
- No app behavior, product code, dependency pins, lockfiles, `.github/workflows`, production/staging env files, DB tests, migrations, RLS, role/grant, DDL, live writes, or CI fallback were changed or run.

## Branch / Worktree

- Scenario: requested branch creation.
- Invocation: `git switch -c codex/runtime-qa-env-repair`
- Observable: BLOCKED with `fatal: cannot lock ref 'refs/heads/codex/runtime-qa-env-repair': unable to create directory for .git/refs/heads/codex/runtime-qa-env-repair`.
- Follow-up inspection: `ls -la .git/refs/heads .git/refs/heads/codex` showed `.git/refs/heads/codex` does not exist. Work continued from detached `HEAD` with scoped safe changes only.
- Dirty worktree: `git status --short --branch` showed detached `HEAD`, pre-existing modified `BACKLOG.md`, `PROJECT_BRIEF.md`, `reports/dalya-next-mvp-readiness-closeout-2026-06-23.md`, `scripts/verify_next_mvp_scope_guard.py`, and extensive pre-existing untracked `.omo` evidence. These were not cleaned or reverted.

## Runner Behavior

- Default temp venv path: `/private/tmp/dalya-focused-backend-qa-venv`.
- Dependency source: existing `requirements.txt` only.
- Python policy: Python 3.12/3.13 only; Python 3.14 is refused for the pinned dependency stack.
- Pytest policy: pass-through args after `--`; `--noconftest` is injected when absent.
- Suite policy: fail closed to the no-DB allowlist only: `tests/test_legacy_telegram_removed.py`, `tests/test_cors_live_env.py`, and `tests/test_verified_facts_seed_closing_costs.py`.
- DB/app-state exclusions: `tests/test_seller_lead_privacy.py`, `tests/test_verified_facts_output_gate.py`, and `tests/test_needs_reply_priority.py` are refused with `db_backed_tests_disallowed` until a safe DB harness exists.
- Evidence policy: JSON contains selected interpreter, version, commands, status, reason, temp venv path, cleanup result, and durations. It does not record env-file or secret contents.
- Bounded commands: interpreter probe timeout 10s, venv creation timeout 120s, requirements install timeout 900s, pytest timeout 300s.

## Required QA Scenarios

### Failure/check proof

- Scenario: current local repo venv/Python mismatch before using the repair path.
- Invocation: `python3 scripts/run_focused_backend_qa.py --check-only --evidence .omo/evidence/task-2-runtime-qa-check-red.json`
- Observable: exit code `2`; stdout `{"reason": "python_3.14_refused_for_pinned_deps_expected_3.12_or_3.13;repo_venv_python_broken_symlink:python3.13", "status": "BLOCKED"}`.
- Artifact: `.omo/evidence/task-2-runtime-qa-check-red.json`
- JSON observable: `suite_policy: allowed_no_db_tests_only`, `commands: []`, and default `pytest_args` limited to the allowed no-DB suite.

### Original mixed-suite run now refused

- Scenario: requested Python 3.12 focused backend command from the original plan, including DB/app-state tests.
- Invocation: `python3 scripts/run_focused_backend_qa.py --python python3.12 --evidence .omo/evidence/task-2-runtime-qa-green.json -- tests/test_legacy_telegram_removed.py tests/test_cors_live_env.py tests/test_seller_lead_privacy.py tests/test_verified_facts_output_gate.py tests/test_verified_facts_seed_closing_costs.py tests/test_needs_reply_priority.py -q`
- Observable: exit code `2`; stdout starts with `{"reason": "db_backed_tests_disallowed:tests/test_seller_lead_privacy.py(...),tests/test_verified_facts_output_gate.py(...),tests/test_needs_reply_priority.py(...)", "status": "BLOCKED"}`.
- Artifact: `.omo/evidence/task-2-runtime-qa-green.json`
- Result: BLOCKED, not green. Focused pytest did not run because the requested suite is disallowed for this no-DB runner.
- JSON observable: `commands: []`, `cleanup_reason: real_run_not_started`, and `suite_policy` equals the same `db_backed_tests_disallowed` reason.

### DB-backed suite guardrail proof

- Scenario: explicit malformed/disallowed suite proof using the original mixed DB/no-DB command.
- Invocation: `python3 scripts/run_focused_backend_qa.py --python python3.12 --evidence .omo/evidence/task-2-runtime-qa-db-suite-blocked.json -- tests/test_legacy_telegram_removed.py tests/test_cors_live_env.py tests/test_seller_lead_privacy.py tests/test_verified_facts_output_gate.py tests/test_verified_facts_seed_closing_costs.py tests/test_needs_reply_priority.py -q`
- Observable: exit code `2`; stdout starts with `{"reason": "db_backed_tests_disallowed:tests/test_seller_lead_privacy.py(...),tests/test_verified_facts_output_gate.py(...),tests/test_needs_reply_priority.py(...)", "status": "BLOCKED"}`.
- Artifact: `.omo/evidence/task-2-runtime-qa-db-suite-blocked.json`
- Result: BLOCKED before venv creation, dependency install, or pytest; JSON `commands` is empty.

### Fallback blocked evidence

- Scenario: deterministic current-state blocked evidence.
- Invocation: `python3 scripts/run_focused_backend_qa.py --check-only --evidence .omo/evidence/task-2-runtime-qa-blocked.json`
- Observable: exit code `2`; stdout `{"reason": "python_3.14_refused_for_pinned_deps_expected_3.12_or_3.13;repo_venv_python_broken_symlink:python3.13", "status": "BLOCKED"}`.
- Artifact: `.omo/evidence/task-2-runtime-qa-blocked.json`

### Malformed input

- Scenario: bad `--python` value.
- Invocation: `python3 scripts/run_focused_backend_qa.py --check-only --python definitely-not-python --evidence .omo/evidence/task-2-runtime-qa-bad-python.json`
- Observable: exit code `2`; stdout `{"reason": "interpreter_not_found:definitely-not-python;repo_venv_python_broken_symlink:python3.13", "status": "BLOCKED"}`.
- Artifact: `.omo/evidence/task-2-runtime-qa-bad-python.json`

## Static / Cleanup Gates

- Scenario: Python syntax gate.
- Invocation: `python3 -m py_compile scripts/run_focused_backend_qa.py`
- Observable: exit code `0`.
- Artifact: bytecode compile only.

- Scenario: Python file size gate.
- Invocation: `awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(\/\/|#|--)/' scripts/run_focused_backend_qa.py | wc -l`
- Observable: `235`, under the 250 pure-LOC ceiling.
- Artifact: terminal output only.

- Scenario: whitespace gate.
- Invocation: `git diff --check`
- Observable: exit code `0`.
- Artifact: terminal output only.

- Scenario: conflict-marker scan.
- Invocation: `rg -n "<<<<<<<|=======|>>>>>>>" scripts docs`
- Observable: exit code `1`, no matches.
- Artifact: terminal output only.

- Scenario: temp venv cleanup receipt.
- Invocation: `test ! -d /private/tmp/dalya-focused-backend-qa-venv`
- Observable: exit code `0`; temp venv absent after the blocked real-run attempt.
- Artifact: `.omo/evidence/task-2-runtime-qa-green.json` records `commands: []`, `cleanup_occurred: false`, `cleanup_reason: real_run_not_started`.

## Adversarial Classes

- `dirty_worktree`: inspected with `git status --short --branch`; unrelated pre-existing work and `.omo` noise preserved.
- `stale_state`: check-only artifacts were regenerated after implementation and reflect current Python 3.14 / broken repo venv state.
- `misleading_success_output`: JSON status was inspected; all runtime QA artifacts are `BLOCKED`, `.omo/evidence/task-2-runtime-qa-green.json` is a blocked artifact despite its legacy filename, and no runtime QA green claim is made.
- `hung/long_commands`: runner records durations and bounds version, venv, install, and pytest subprocesses with timeouts.
- `generated/cached_artifacts`: required JSON artifacts were regenerated; `/private/tmp/dalya-focused-backend-qa-venv` is absent.
- `malformed_input`: bad `--python` produces a clear BLOCKED artifact with exact missing-interpreter reason.
- `db_backed_suite`: the original mixed suite is now refused with `db_backed_tests_disallowed` and empty `commands`, proving no venv creation/install/pytest occurred.
- `prompt_injection`, `cancel_resume`, `flaky_tests`, and `repeated_interruptions`: not applicable to this local runner task; no untrusted external content or test execution occurred.

## Result

Task 2 remains a deterministic BLOCKED runtime-QA path locally: the runner and canonical no-DB commands exist, DB-backed test selections are intentionally excluded/refused, and this machine cannot claim focused backend QA green until Python 3.12 or 3.13 is installed and the allowed no-DB pytest suite actually runs.
