# Task 12 PR #66 Follow-Up Evidence

Date: 2026-06-23
Branch: `codex/agent-first-run-activation`
Starting head: `2803c3593c105fb11773a7297f7c0b03467f7239`

## Fixed Blockers

1. First-run/internal-pilot activation copy is gated to explicit dashboard API `empty_state`.
   - Scenario: mocked authenticated `/agent` API returns `sample_data: false`, empty operational arrays, zero metrics, and `empty_state.reason = no_workspace_activity`.
   - Invocation: `cd frontend && node scripts/verify-task-next-first-run-state.mjs`.
   - Binary observable: 15 checks passed; empty workspace includes `Start with an internal pilot rehearsal`, `synthetic/internal records only`, `Refresh hot list`, no fake operational row leaks, and no `Preview safe demo states` or `/component-showcase` leak.
   - Captured artifact: `.omo/evidence/task-12-first-run-state/functional-transcript.json`.

2. Normal live zero-queue dashboard without API `empty_state` remains neutral.
   - Scenario: mocked authenticated `/agent` API returns `sample_data: false`, empty operational arrays, zero metrics, and no `empty_state`.
   - Invocation: `cd frontend && node scripts/verify-task-next-first-run-state.mjs`.
   - Binary observable: 15 checks passed; live zero-queue body includes `Your day is clear` and neutral no-queue copy, while excluding `Start with an internal pilot rehearsal`, `synthetic/internal records only`, `Confirm pilot scope`, `data class`, `Preview safe demo states`, and fake operational row markers.
   - Captured artifact: `.omo/evidence/task-12-first-run-state/functional-transcript.json`.

3. Connection error still has retry/manual fallback.
   - Scenario: mocked authenticated `/agent` dashboard API returns HTTP 503.
   - Invocation: `cd frontend && node scripts/verify-task-next-first-run-state.mjs`.
   - Binary observable: 15 checks passed; error body includes `Retry`, `Manual fallback`, `Use WhatsApp directly`, and zero fake operational row leaks.
   - Captured artifact: `.omo/evidence/task-12-first-run-state/functional-transcript.json`.

4. Visual empty-state QA remains clean after removing the demo CTA.
   - Scenario: mocked authenticated first-run empty workspace rendered at 1280x900 and 390x900.
   - Invocation: `cd frontend && node scripts/verify-task-next-first-run-visual.mjs --desktop ../.omo/evidence/task-12-first-run-desktop.png --mobile ../.omo/evidence/task-12-first-run-mobile.png`.
   - Binary observable: 6 checks passed; both viewports have zero fake operational row leaks, no horizontal overflow, and no fake-operational demo preview link.
   - Captured artifacts: `.omo/evidence/task-12-first-run-desktop.png`, `.omo/evidence/task-12-first-run-mobile.png`, `.omo/evidence/task-12-first-run-state/visual-transcript.json`.

5. Static and backend safety checks passed.
   - Scenario: frontend typecheck.
   - Invocation: `cd frontend && npx --no-install tsc --noEmit`.
   - Binary observable: exited 0.
   - Captured artifact: Codex command transcript.
   - Scenario: backend empty-state contract regression.
   - Invocation: `python3 tests/test_agent_dashboard_empty_state.py`.
   - Binary observable: exited 0.
   - Captured artifact: Codex command transcript.
   - Scenario: whitespace and conflict-marker safety.
   - Invocation: `git diff --check`; `rg -n "<<<<<<<|=======|>>>>>>>" <changed Task 12 paths>`.
   - Binary observable: `git diff --check` exited 0; conflict-marker scan exited 1 with no matches.
   - Captured artifact: Codex command transcript.

## Safety

- No fake authenticated live buyer, offer, task, queue, phone, amount, or escalation rows were added.
- No owner dashboard expansion, API contract change, Task 13 work, dependency/lockfile edit, migration, RLS/role/grant change, live write, external DB test, or production/staging env-file read occurred.
- `cd frontend && npm run build` was not run because `frontend/.env.local` exists and the env-file guard marks that path blocked.
- PR body was updated to remove the stale internal demo-state preview claim.
