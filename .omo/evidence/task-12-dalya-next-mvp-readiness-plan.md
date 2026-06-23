# Task 12 Evidence - First-run activation and stronger empty/error states

Date: 2026-06-23
Branch: `codex/agent-first-run-activation`
Tracking: `.omo/evidence/task-12-tracking-dalya-next-mvp-readiness-plan.json`

## Scope

- Improved authenticated `/agent` empty workspace UI without adding live sample buyer, offer, queue, phone, amount, task, or escalation rows.
- Added safe first-run guidance for synthetic/internal pilot rehearsal and visible `Refresh hot list` for explicit API empty states, without linking to fake operational demo rows.
- Preserved a neutral clear-day state for live zero-queue dashboards that do not include API `empty_state`.
- Added connection error manual fallback guidance: retry the dashboard API or use WhatsApp directly until the workspace reconnects.
- Updated the focused backend empty-state test harness import stubs only; the authenticated dashboard API empty-state contract was not changed.

## Acceptance criteria evidence

1. Empty authenticated workspace contains no fake buyer records but gives a clear safe next step.
   - Scenario: mocked authenticated `/agent` API returns `sample_data: false`, empty arrays, zero metrics, and `empty_state.reason = no_workspace_activity`.
   - Invocation: `cd frontend && node scripts/verify-task-next-first-run-state.mjs`.
   - Binary observable: 15 checks passed; verifier asserts `Start with an internal pilot rehearsal`, `synthetic/internal records only`, `Refresh hot list`, no `Preview safe demo states` or `/component-showcase` leak, and zero `fakeOperationalTexts` leaks.
   - Captured artifact: `.omo/evidence/task-12-first-run-state/functional-transcript.json`.

2. Normal live zero-queue dashboard stays neutral without first-run/internal-pilot copy.
   - Scenario: mocked authenticated `/agent` API returns `sample_data: false`, empty arrays, zero metrics, and no `empty_state`.
   - Invocation: `cd frontend && node scripts/verify-task-next-first-run-state.mjs`.
   - Binary observable: verifier asserts `Your day is clear`, neutral no-queue explanation, no `Start with an internal pilot rehearsal`, no `synthetic/internal records only`, no `Confirm pilot scope`, no `data class`, no `Preview safe demo states`, and zero `fakeOperationalTexts` leaks.
   - Captured artifact: `.omo/evidence/task-12-first-run-state/functional-transcript.json`.

3. RED proof captured the prior weak first-run/error state.
   - Scenario: same mocked authenticated empty/error workspace before UI changes.
   - Invocation: `cd frontend && node scripts/verify-task-next-first-run-state.mjs --red`.
   - Binary observable: 3 RED checks passed by proving the old empty workspace lacked internal-pilot activation/demo action and the old error state lacked a named manual fallback.
   - Captured artifact: `.omo/evidence/task-12-first-run-state/functional-red-transcript.json`.

4. Connection error state gives retry/manual fallback.
   - Scenario: authenticated `/agent` dashboard API mocked as HTTP 503.
   - Invocation: `cd frontend && node scripts/verify-task-next-first-run-state.mjs`.
   - Binary observable: verifier asserts `Retry`, `Manual fallback`, `Use WhatsApp directly`, and zero fake operational row leaks.
   - Captured artifact: `.omo/evidence/task-12-first-run-state/functional-transcript.json`.

5. Visual QA confirms mobile/desktop layout without text overlap.
   - Scenario: authenticated empty workspace rendered at 1280x900 and 390x900.
   - Invocation: `cd frontend && node scripts/verify-task-next-first-run-visual.mjs --desktop ../.omo/evidence/task-12-first-run-desktop.png --mobile ../.omo/evidence/task-12-first-run-mobile.png`.
   - Binary observable: 6 visual verifier checks passed; each viewport asserted zero fake operational row leaks, no horizontal overflow, and no fake-operational demo preview link.
   - Captured artifacts: `.omo/evidence/task-12-first-run-desktop.png`, `.omo/evidence/task-12-first-run-mobile.png`, `.omo/evidence/task-12-first-run-state/visual-transcript.json`.

6. Authenticated dashboard empty-state API contract remains stable.
   - Scenario: no-DB focused backend test stubs all dashboard sources as empty.
   - Invocation: `python3 tests/test_agent_dashboard_empty_state.py`.
   - Binary observable: exited 0; asserts `sample_data is False`, zero metrics, all operational arrays empty, and no forbidden sample markers in the payload text.
   - Captured artifact: command transcript in Codex run output; source assertion lives in `tests/test_agent_dashboard_empty_state.py`.

## Static QA

- `cd frontend && npx --no-install tsc --noEmit`: passed.
- `git diff --check`: passed.
- Conflict-marker scan over changed Task 12 paths: passed with no actual marker lines.

## Blocked QA

- `cd frontend && npm run build`: blocked by env-file guard because `frontend/.env.local` exists. The build command was not run.

## Safety confirmations

- No sample buyer, offer, task, queue, phone, amount, or escalation rows were reintroduced in authenticated live paths.
- No owner dashboard expansion or broad CRM surface was added.
- No authenticated dashboard API empty-state contract change was made.
- No production/staging env file contents were read.
- No external DB-backed test, production/staging DDL, migration, RLS/role/grant change, live write, dependency/lockfile edit, or Task 13 work occurred.
