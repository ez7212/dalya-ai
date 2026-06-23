# Task 1 Dalya Post-Closeout Hardening Evidence

Date: 2026-06-23
Task: Verification closeout PR
Linear ticket: DAL-198
Requested branch: `codex/verification-closeout-cleanup`

## Scope Completed

- Tightened `scripts/verify_next_mvp_scope_guard.py` with fixture flags and strict `scripts/audit_*.py` / `scripts/migrate_*.py` helper-script detection.
- Added `.omo/evidence/task-1-helper-script-allowlist.json` for known separator-only historical helper-script edits.
- Added `tests/test_next_mvp_scope_guard_helper_scripts.py` to prove unapproved audit/migrate helper edits fail with JSON evidence.
- Updated `reports/dalya-next-mvp-readiness-closeout-2026-06-23.md`, `BACKLOG.md`, and `PROJECT_BRIEF.md` for PR #67 merge commit `ddae7bb231e4e5c2d3f3353010d6113bd54d0aab`, F1/F2/F4 PASS, F3 BLOCKED, PR #59/#62 guard-history classification, and Task 10b blocked posture.
- Prepared Task 1 for orchestrator completion in `.omo/plans/dalya-post-closeout-hardening.md` and removed the historical self-matching conflict-marker regex from `.omo/plans/dalya-next-mvp-readiness-plan.md`; the checkbox remains controlled by the start-work gate and is marked only after independent review confirms the work.

## Branch / Dirty Worktree

- Invocation: `git status --short --branch`
- Initial observable: `## HEAD (no branch)` plus pre-existing modified `.omo/evidence/task-12-tracking-dalya-next-mvp-readiness-plan.json` and many pre-existing untracked `.omo` evidence paths.
- Invocation: `git switch -c codex/verification-closeout-cleanup`
- Result: BLOCKED, exit code `128`.
- Exact output: `fatal: cannot lock ref 'refs/heads/codex/verification-closeout-cleanup': unable to create directory for .git/refs/heads/codex/verification-closeout-cleanup`
- Resolution: continued with scoped file changes only; did not revert or delete unrelated dirty `.omo` worktree noise.

## RED Proof

- Invocation: `python3 -m pytest --noconftest tests/test_next_mvp_scope_guard_helper_scripts.py -q`
- First local result before test creation: BLOCKED by local runner, exit code `1`, `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3: No module named pytest`.
- Setup invocation: `python3 -m pip install --user pytest==8.3.0`
- Result: PASS, installed `pytest==8.3.0`, `pluggy==1.6.0`, and `iniconfig==2.3.0` into the active Python 3.14 user site so the exact required pytest command could run. No repo dependency or lockfile changed.
- RED invocation after adding the test and before verifier changes: `python3 -m pytest --noconftest tests/test_next_mvp_scope_guard_helper_scripts.py -q`
- RED result: FAIL, exit code `1`.
- Binary observable: test failed with `FileNotFoundError: [Errno 2] No such file or directory: '/private/tmp/dalya-scope-guard-fixtures/out.json'` because the existing verifier did not support `--changed-paths-fixture`, `--diff-fixture`, or `--helper-script-allowlist` and therefore produced no JSON fixture output.

## Verification Commands

- Invocation: `python3 -m pytest --noconftest tests/test_next_mvp_scope_guard_helper_scripts.py -q`
- Result: PASS, exit code `0`.
- Observable: `1 passed in 0.04s`.
- Scenario: fixture writes `/private/tmp/dalya-scope-guard-fixtures/changed-paths.txt` and `/private/tmp/dalya-scope-guard-fixtures/diff.patch` containing `scripts/migrate_fake.py` and `scripts/audit_fake.py`, invokes the scope guard with fixture flags and `.omo/evidence/task-1-helper-script-allowlist.json`, and asserts nonzero JSON names both unapproved helper scripts.

- Invocation: `python3 scripts/verify_next_mvp_scope_guard.py --base 3482a7fb863c542836fa2aabef707ad8fd503b71 --output .omo/evidence/task-1-scope-guard-green.json --helper-script-allowlist .omo/evidence/task-1-helper-script-allowlist.json`
- Result: PASS, exit code `0`.
- Artifact: `.omo/evidence/task-1-scope-guard-green.json`
- Binary observable: JSON has `"passed": true`; helper-script result evidence lists only the four allowlisted historical separator-only helper edits.

- Invocation: `python3 scripts/verify_next_mvp_plan_completion.py --plan .omo/plans/dalya-next-mvp-readiness-plan.md --evidence-dir .omo/evidence --output .omo/evidence/task-1-plan-compliance.json`
- Result: PASS, exit code `0`.
- Artifact: `.omo/evidence/task-1-plan-compliance.json`
- Binary observable: JSON has `"passed": true` and verifies Tasks 1-12 plus 9A/9B and Task 13 closeout assets.

- Invocation: `rg -n "production ready|live data ready|external brokerage pilot ready|Task 10b.*complete|Telegram.*enabled|360dialog.*ready|BSP.*ready" reports/dalya-next-mvp-readiness-closeout-2026-06-23.md PROJECT_BRIEF.md BACKLOG.md docs/runbooks/dalya-friendly-pilot-readiness-runbook.md`
- Result: PASS as no-match, exit code `1`.
- Observable: no unsupported current-state claims found.

- Invocation: `python3 -m py_compile scripts/verify_next_mvp_scope_guard.py tests/test_next_mvp_scope_guard_helper_scripts.py`
- Result: PASS, exit code `0`.

- Invocation: `git diff --check`
- Result: PASS, exit code `0`.

- Invocation: `rg -n "<<<<<<<|=======|>>>>>>>" .omo/plans/dalya-next-mvp-readiness-plan.md reports BACKLOG.md PROJECT_BRIEF.md docs/runbooks scripts tests`
- Result: PASS as no-match, exit code `1`.
- Note: the historical plan previously self-matched because it contained the literal conflict-marker regex in Task 13 QA instructions; DAL-198 replaced that literal with descriptive wording.

## Manual QA Artifact

- Scenario: data-shaped scope guard manual QA.
- Invocation: `python3 scripts/verify_next_mvp_scope_guard.py --base 3482a7fb863c542836fa2aabef707ad8fd503b71 --output .omo/evidence/task-1-scope-guard-green.json --helper-script-allowlist .omo/evidence/task-1-helper-script-allowlist.json`
- Artifact: `.omo/evidence/task-1-scope-guard-green.json`
- Binary observable: `"passed": true`; `"approved audit/migrate helper-script edits only"` evidence contains `scripts/audit_tenant_constraints_dal170d.py`, `scripts/audit_tenant_isolation.py`, `scripts/migrate_tenant_constraints_dal170d.py`, and `scripts/migrate_tenant_root_normalization.py`, proving known helper edits pass only through explicit rationale allowlisting.

## Adversarial Probes

- dirty_worktree: probed with `git status --short --branch`; repo remained detached with pre-existing `.omo` noise. Scoped changes only; no unrelated cleanup or revert.
- stale_state: reran the direct scope guard and plan completion verifier after code/doc edits; outputs were regenerated at `.omo/evidence/task-1-scope-guard-green.json` and `.omo/evidence/task-1-plan-compliance.json`.
- misleading_success_output: inspected JSON outputs, not just exit codes; scope guard and plan compliance both contain `"passed": true` with expected result details.
- malformed input: ran `printf '{bad json' > /private/tmp/dalya-scope-guard-fixtures/bad-allowlist.json` then `python3 scripts/verify_next_mvp_scope_guard.py --base 3482a7fb863c542836fa2aabef707ad8fd503b71 --output /private/tmp/dalya-scope-guard-fixtures/bad-allowlist-out.json --changed-paths-fixture /private/tmp/dalya-scope-guard-fixtures/changed-paths.txt --diff-fixture /private/tmp/dalya-scope-guard-fixtures/diff.patch --helper-script-allowlist /private/tmp/dalya-scope-guard-fixtures/bad-allowlist.json`; result exit code `1`, JSON `"passed": false`, and `"helper-script allowlist is well formed"` evidence named invalid JSON.
- cancel/resume: not applicable; no resumable workflow or mid-operation persisted transaction was introduced.
- generated/cached artifacts: applicable through JSON outputs; stale-state rerun covered this, and artifacts were regenerated after edits.
- hung commands: no long-running command observed; each gate returned promptly.
- flaky tests: focused pytest was run twice after `pytest` was available, with stable `1 passed`.
- prompt injection: not applicable; no untrusted external prose is executed or sent to an LLM.
- repeated interruptions: not applicable; no interrupted command or partial resume occurred.

## Cleanup

- Invocation: `rm -rf /private/tmp/dalya-scope-guard-fixtures && test ! -e /private/tmp/dalya-scope-guard-fixtures`
- Result: PASS, exit code `0`.
- Observable: temporary fixture directory removed.
- Environment note: `pytest==8.3.0` remains installed in the active Python user site to preserve the exact `python3 -m pytest ...` gate availability; repo dependencies and lockfiles were not modified.
- Command Center invocation: `COMMAND_CENTER_WORKING_DIR="$PWD" npm --prefix /Users/eric/command-center run activity-log -- --project dalya --title "Clean up readiness verification closeout" --work-type coding --labels verification,hardening --purpose "Make the next-MVP closeout state auditable and prevent unapproved audit or migrate helper-script drift." --process "Added strict helper-script fixture support and rationale allowlisting to the scope guard, documented PR #67 and PR #59/#62 guard histories, updated closeout docs, and recorded Task 1 evidence." --outcome "DAL-198 evidence now shows F1/F2/F4 PASS, F3 BLOCKED, direct scope guard JSON PASS, and unapproved helper scripts failing through pytest fixtures."`
- Command Center result: PASS, `activity-log ok project=dalya id=dalya-2026-06-23-clean-up-readiness-verification-closeout-c7d15434`.

## Code Quality Notes

- `scripts/verify_next_mvp_scope_guard.py` pure LOC: 146.
- `tests/test_next_mvp_scope_guard_helper_scripts.py` pure LOC: 71.
- Single responsibility: verifier owns closeout scope checks; test owns helper-script fixture behavior.
- Boundary purity: allowlist JSON is parsed at CLI boundary and malformed input fails closed.
- Variant discrimination: no tagged variants introduced.
- Escape hatches: no `Any`, `cast`, or type-ignore introduced.
- Defensive layer: no broad exception handling introduced; JSON parse catches only `json.JSONDecodeError`.
- Tests: reverting the verifier fixture/allowlist behavior makes the new pytest fail.

## Risks

- Branch creation was blocked by `.git` ref write restrictions, so no PR branch was created locally.
- Runtime pytest availability required installing `pytest==8.3.0` into the user site because the repo `venv/bin/python` symlink points to missing `python3.13` and system Python initially had no pytest.
- PR #62 is classified as a process error in the report because a later artifact still marked actual merge/cleanup blocked by read-only role even though the PR was merged.
- Post-implementation gate and code-quality reviews were spawned by the start-work orchestrator; their review artifacts are recorded separately under `.omo/evidence/`.
