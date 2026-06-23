# Task 3 - Final surface verifier safety repair

Status: GREEN
Linear: DAL-200
Requested branch: `codex/final-surface-qa-pass`

## Scope
- Refactored verifier responsibilities under `frontend/scripts/` while preserving CLI behavior and Task 3 evidence schema.
- Thin orchestrator: `frontend/scripts/verify-next-mvp-final-surface.mjs`.
- New helper modules: `frontend/scripts/final-surface-constants.mjs`, `frontend/scripts/final-surface-cli.mjs`, `frontend/scripts/final-surface-safe-env.mjs`, `frontend/scripts/final-surface-transcript.mjs`, `frontend/scripts/final-surface-server.mjs`, `frontend/scripts/final-surface-browser-fixtures.mjs`, `frontend/scripts/final-surface-browser-qa.mjs`.
- Regenerated Task 3 evidence under `.omo/evidence/task-3-final-surface`.
- Added focused RED artifacts under `.omo/evidence/task-3-final-surface-red-env-local`, `.omo/evidence/task-3-final-surface-red-env-production-local`, and `.omo/evidence/task-3-final-surface-red-safe-temp`.
- Preserved unrelated dirty worktree changes and did not modify product UI, package files, lock files, or env files.
- Did not mark any plan checkbox.

## Implementation
- Safe-temp cleanup is validated before any `rmSync`: the path must be under an expected temp root, use the expected `dalya-final-surface-*` or `dalya-next-mvp-final-surface-*` name prefix, avoid repo/source overlap, and either be absent/empty or carry `.dalya-final-surface-verifier-temp`.
- Direct fixture mode blocks on any root-level `.env*` entry in the chosen frontend root before server startup. The guard records file names only and does not read env contents.
- Transcripts now record env names, categories, value policy, and safety mode only. Raw env values and env-derived paths are tokenized or redacted before transcript/BLOCKED writes.
- Transcript writes fail closed if tracked env values remain in the serialized JSON.
- `today-queue-escalation-focus.png` is now a focused viewport screenshot, so it no longer duplicates `agent.png`; transcript capture metadata records `captureKind`.
- `first-run-error-state.png` remains a real first-run workspace with a synthetic/internal refresh failure, so it is visually distinct from the generic dashboard fetch failure.

## Refactor follow-up - 2026-06-23

Gate blocker resolved: `frontend/scripts/verify-next-mvp-final-surface.mjs` no longer mixes safe-temp validation, env scanning, staging, server lifecycle, browser QA, transcript redaction, screenshot capture metadata, and cleanup in one 963-line harness.

### Module split
- `final-surface-constants.mjs`: repo/frontend roots, safe env names/categories, safe-temp marker/prefixes, fake operational text denylist.
- `final-surface-cli.mjs`: flag parsing, JSON route response helper, assertion helper.
- `final-surface-safe-env.mjs`: `.env*` name scanning, safe-temp validation/removal, safe frontend staging, sanitized Next env, transcript extra path values.
- `final-surface-transcript.mjs`: transcript/BLOCKED writes, env/path redaction, fail-closed leak check.
- `final-surface-server.mjs`: temporary Supabase auth stub, Next dev server start/wait/stop, auth seeding.
- `final-surface-browser-fixtures.mjs`: mocked dashboard/escalation payloads and shared Playwright API mocks.
- `final-surface-browser-qa.mjs`: six browser capture flows and screenshot capture metadata.
- `verify-next-mvp-final-surface.mjs`: CLI orchestration, blocked-path branching, transcript assembly, cleanup sequencing, exit codes.

### LOC after refactor
- `frontend/scripts/verify-next-mvp-final-surface.mjs`: 262 lines / 243 pure LOC.
- `frontend/scripts/final-surface-browser-fixtures.mjs`: 100 lines / 95 pure LOC.
- `frontend/scripts/final-surface-browser-qa.mjs`: 183 lines / 172 pure LOC.
- `frontend/scripts/final-surface-cli.mjs`: 19 lines / 17 pure LOC.
- `frontend/scripts/final-surface-constants.mjs`: 45 lines / 39 pure LOC.
- `frontend/scripts/final-surface-safe-env.mjs`: 218 lines / 199 pure LOC.
- `frontend/scripts/final-surface-server.mjs`: 149 lines / 138 pure LOC.
- `frontend/scripts/final-surface-transcript.mjs`: 130 lines / 121 pure LOC.

### Refactor verification
- Scenario: RED direct `.env.local` guard using `/private/tmp/dalya-final-surface-red-local-refactor/frontend/.env.local`.
- Invocation: `cd frontend && node scripts/verify-next-mvp-final-surface.mjs --fixture-frontend-root /private/tmp/dalya-final-surface-red-local-refactor/frontend --base-url http://127.0.0.1:3999 --output-dir ../.omo/evidence/task-3-final-surface-red-env-local`.
- Binary observable: exit `2`; stdout reported `passed: false`, `blocked: true`, reason `fixture root has Next-loadable .env* files and no --safe-temp-workdir was supplied`.
- Artifact: `.omo/evidence/task-3-final-surface-red-env-local/transcript.json`.

- Scenario: RED direct `.env.production.local` guard using `/private/tmp/dalya-final-surface-red-production-refactor/frontend/.env.production.local`.
- Invocation: `cd frontend && node scripts/verify-next-mvp-final-surface.mjs --fixture-frontend-root /private/tmp/dalya-final-surface-red-production-refactor/frontend --base-url http://127.0.0.1:3999 --output-dir ../.omo/evidence/task-3-final-surface-red-env-production-local`.
- Binary observable: exit `2`; stdout reported `passed: false`, `blocked: true`, reason `fixture root has Next-loadable .env* files and no --safe-temp-workdir was supplied`.
- Artifact: `.omo/evidence/task-3-final-surface-red-env-production-local/transcript.json`.

- Scenario: RED dangerous safe-temp cleanup guard using caller-owned `/private/tmp/dalya-final-surface-danger-parent-refactor`.
- Invocation: `cd frontend && node scripts/verify-next-mvp-final-surface.mjs --safe-temp-workdir /private/tmp/dalya-final-surface-danger-parent-refactor --base-url http://127.0.0.1:3999 --output-dir ../.omo/evidence/task-3-final-surface-red-safe-temp`.
- Binary observable: exit `2`; stdout reported `passed: false`, `blocked: true`, reason `unsafe --safe-temp-workdir refused before cleanup or staging`.
- Artifact: `.omo/evidence/task-3-final-surface-red-safe-temp/transcript.json`.
- Deletion observable: `test -f /private/tmp/dalya-final-surface-danger-parent-refactor/marker.txt` exited `0` after the verifier blocked.

- Scenario: GREEN safe-temp final Next MVP browser surface QA.
- Invocation: `cd frontend && node scripts/verify-next-mvp-final-surface.mjs --safe-temp-workdir /private/tmp/dalya-final-surface-frontend-refactor --base-url http://127.0.0.1:3000 --output-dir ../.omo/evidence/task-3-final-surface`.
- Binary observable: first sandbox run exited `2` with `listen EPERM: operation not permitted 127.0.0.1`; rerun with approved loopback binding exited `0` and stdout reported `passed: true`, `captures: 6`, transcript `.omo/evidence/task-3-final-surface/transcript.json`.
- Transcript facts: `envSafetyMode=safe-temp-workdir`, `safeTempEnvFiles=[]`, `domAssertions=21`, cleanup `server exited after SIGTERM`, `supabaseStub=closed`, `safeTempWorkdir=removed <ENV:SAFE_TEMP_WORKDIR>`, and `passed=true`.
- Screenshot artifacts: `.omo/evidence/task-3-final-surface/agent.png`, `.omo/evidence/task-3-final-surface/today-queue-escalation-focus.png`, `.omo/evidence/task-3-final-surface/dashboard-fetch-failure.png`, `.omo/evidence/task-3-final-surface/escalation-reply-affordance.png`, `.omo/evidence/task-3-final-surface/first-run-empty-state.png`, `.omo/evidence/task-3-final-surface/first-run-error-state.png`.

- Scenario: transcript leakage scan across current RED/GREEN Task 3 transcripts and BLOCKED artifacts.
- Invocation: `rg -ni "secret|do-not-read|do_not_read|do_not_leak|DALYA_TASK3_ENV|access.token|refresh.token|password|database_url" .omo/evidence/task-3-final-surface .omo/evidence/task-3-final-surface-red-env-local .omo/evidence/task-3-final-surface-red-env-production-local .omo/evidence/task-3-final-surface-red-safe-temp`.
- Binary observable: exit `1`, no matches.

- Scenario: screenshot distinction from current GREEN PNG files.
- Invocation: repo-local Node + `frontend/node_modules/sharp` rewrote `.omo/evidence/task-3-final-surface/screenshot-distinction.json` and `.omo/evidence/task-3-final-surface/first-run-vs-dashboard-pixel-diff.json`.
- Binary observable: exit `0`; `duplicateHashGroups=[]`; `first-run-error-state` versus `dashboard-fetch-failure` has `pixelIdentical=false`, `diffPixels=371398`, `totalPixels=1054720`, `diffRatio=0.3521294751213592`.

- Scenario: syntax checks for orchestrator and new helper modules.
- Invocation: `cd frontend && node --check scripts/verify-next-mvp-final-surface.mjs && for file in scripts/final-surface-*.mjs; do node --check "$file" || exit 1; done`.
- Binary observable: exit `0`, no output.

- Scenario: TypeScript project validation.
- Invocation: `cd frontend && npx --no-install tsc --noEmit`.
- Binary observable: exit `0`, no output.

- Scenario: diff whitespace validation.
- Invocation: `git diff --check`.
- Binary observable: exit `0`, no output.

- Scenario: anchored conflict scan over `frontend/scripts` and Task 3 evidence.
- Invocation: `rg -n "^(<<<<<<<|=======|>>>>>>>)" frontend/scripts .omo/evidence/task-3-dalya-post-closeout-hardening.md .omo/evidence/task-3-final-surface .omo/evidence/task-3-final-surface-red-env-local .omo/evidence/task-3-final-surface-red-env-production-local .omo/evidence/task-3-final-surface-red-safe-temp`.
- Binary observable: exit `1`, no matches.

- Scenario: cleanup after refactor verification.
- Invocation: `test ! -e /private/tmp/dalya-final-surface-frontend-refactor && test ! -e /private/tmp/dalya-final-surface-red-local-refactor && test ! -e /private/tmp/dalya-final-surface-red-production-refactor && test ! -e /private/tmp/dalya-final-surface-danger-parent-refactor`.
- Binary observable: exit `0`, no output.
- Invocation: `lsof -iTCP:3000 -sTCP:LISTEN -nP; lsof -iTCP:3999 -sTCP:LISTEN -nP`.
- Binary observable: exit `1`, no output from either port query.

## Verification

### RED direct `.env.local` guard
- Scenario: unsafe fixture with `/private/tmp/dalya-final-surface-red-local/frontend/.env.local` containing a marker string.
- Invocation: `cd frontend && node scripts/verify-next-mvp-final-surface.mjs --fixture-frontend-root /private/tmp/dalya-final-surface-red-local/frontend --base-url http://127.0.0.1:3999 --output-dir ../.omo/evidence/task-3-final-surface-red-env-local`
- Binary observable: exit `2`; stdout reported `passed: false`, `blocked: true`, reason `fixture root has Next-loadable .env* files and no --safe-temp-workdir was supplied`.
- Artifact: `.omo/evidence/task-3-final-surface-red-env-local/transcript.json`.

### RED direct `.env.production.local` guard
- Scenario: unsafe fixture with `/private/tmp/dalya-final-surface-red-production/frontend/.env.production.local` containing a marker string.
- Invocation: `cd frontend && node scripts/verify-next-mvp-final-surface.mjs --fixture-frontend-root /private/tmp/dalya-final-surface-red-production/frontend --base-url http://127.0.0.1:3999 --output-dir ../.omo/evidence/task-3-final-surface-red-env-production-local`
- Binary observable: exit `2`; stdout reported `passed: false`, `blocked: true`, reason `fixture root has Next-loadable .env* files and no --safe-temp-workdir was supplied`.
- Artifact: `.omo/evidence/task-3-final-surface-red-env-production-local/transcript.json`.

### RED dangerous safe-temp cleanup guard
- Scenario: caller-owned existing directory `/private/tmp/dalya-final-surface-danger-parent` with `marker.txt` was passed as `--safe-temp-workdir`.
- Invocation: `cd frontend && node scripts/verify-next-mvp-final-surface.mjs --safe-temp-workdir /private/tmp/dalya-final-surface-danger-parent --base-url http://127.0.0.1:3999 --output-dir ../.omo/evidence/task-3-final-surface-red-safe-temp`
- Binary observable: exit `2`; stdout reported `passed: false`, `blocked: true`, reason `unsafe --safe-temp-workdir refused before cleanup or staging`.
- Artifact: `.omo/evidence/task-3-final-surface-red-safe-temp/transcript.json`.
- Deletion observable: `test -f /private/tmp/dalya-final-surface-danger-parent/marker.txt` exited `0` after the verifier blocked.

### Env transcript no-content check
- Scenario: all RED/GREEN Task 3 transcripts and BLOCKED artifacts were scanned for broad secret/token markers without writing fixture env contents into the evidence note.
- Invocation: `rg -ni "secret|do-not-read|do_not_read|access.token|refresh.token|password|database_url" .omo/evidence/task-3-final-surface .omo/evidence/task-3-final-surface-red-env-local .omo/evidence/task-3-final-surface-red-env-production-local .omo/evidence/task-3-final-surface-red-safe-temp`
- Binary observable: exit `1`, no matches.
- Artifact checked: `.omo/evidence/task-3-final-surface/transcript.json` records `envSummary.valuePolicy=names-and-categories-only; no environment values recorded` and tokenized `serverCwd=<ENV:SAFE_TEMP_WORKDIR>`.

### GREEN safe-temp browser verifier
- Scenario: safe-temp final Next MVP browser surface QA.
- Invocation: `cd frontend && node scripts/verify-next-mvp-final-surface.mjs --safe-temp-workdir /private/tmp/dalya-final-surface-frontend --base-url http://127.0.0.1:3000 --output-dir ../.omo/evidence/task-3-final-surface`
- Binary observable: exit `0`; stdout reported `passed: true`, `captures: 6`, transcript `.omo/evidence/task-3-final-surface/transcript.json`.
- Note: local bind permission was required for the temporary Supabase stub and Next dev server on `127.0.0.1`.
- Transcript facts: `envSafetyMode=safe-temp-workdir`, `safeTempEnvFiles=[]`, `domAssertions=21`, cleanup `server exited after SIGTERM`, `supabaseStub=closed`, `safeTempWorkdir=removed <ENV:SAFE_TEMP_WORKDIR>`, and `passed=true`.
- Stale artifact check: `test ! -e .omo/evidence/task-3-final-surface/BLOCKED.md` exited `0`.
- Required screenshots:
  - `.omo/evidence/task-3-final-surface/agent.png`
  - `.omo/evidence/task-3-final-surface/today-queue-escalation-focus.png`
  - `.omo/evidence/task-3-final-surface/dashboard-fetch-failure.png`
  - `.omo/evidence/task-3-final-surface/escalation-reply-affordance.png`
  - `.omo/evidence/task-3-final-surface/first-run-empty-state.png`
  - `.omo/evidence/task-3-final-surface/first-run-error-state.png`

### Screenshot independence and visual distinction
- Scenario: prove screenshots do not overclaim duplicate surface coverage.
- Invocation: Node + repo-local `sharp` hashed all six screenshots and wrote `.omo/evidence/task-3-final-surface/screenshot-distinction.json`.
- Binary observable: exit `0`; `duplicateHashGroups=[]`.
- Hash observables:
  - `agent.png=935556e53768d101f45e2f635bbbb2cc0cf8bc73274dfb226681ef986c19b7bd`
  - `today-queue-escalation-focus.png=3ee2ab68bfa4cc4c1a259316a304b067513af2bec0c67c9e270a4c3a8e706a26`
  - `dashboard-fetch-failure.png=4eb92327ebc5323a8d15f089d16d843834eace469ac2f9b05063e94ea1cab031`
  - `escalation-reply-affordance.png=409f4138b9fee9fb6726c58f0049b731e6e80f1d2c3c3cda756d89196306a020`
  - `first-run-empty-state.png=463e3551d77631619b628e35f7ad5e89eee46acc082470ecefde477a484f7787`
  - `first-run-error-state.png=c1ddbafee40fa12505c11c6c88a219acf49575bd36c9c8ccc73dad4abd45dd68`
- Pixel artifact: `.omo/evidence/task-3-final-surface/first-run-vs-dashboard-pixel-diff.json`.
- Pixel observable: `first-run-error-state` versus `dashboard-fetch-failure` has `pixelIdentical=false`, `diffPixels=371398`, `totalPixels=1054720`, `diffRatio=0.3521294751213592`.
- Agent/today duplicate fix observable: `agent` and `today-queue-escalation-focus` have different hashes and different dimensions because Today Queue is captured as a focused viewport screenshot.

### Static / type / hygiene gates
- `cd frontend && node --check scripts/verify-next-mvp-final-surface.mjs`: PASS.
- `cd frontend && npx --no-install tsc --noEmit`: PASS.
- `git diff --check`: PASS.
- Anchored conflict scan: `rg -n "^(<<<<<<<|=======|>>>>>>>)" frontend/scripts/verify-next-mvp-final-surface.mjs .omo/evidence/task-3-dalya-post-closeout-hardening.md .omo/evidence/task-3-final-surface .omo/evidence/task-3-final-surface-red-env-local .omo/evidence/task-3-final-surface-red-env-production-local .omo/evidence/task-3-final-surface-red-safe-temp` exited `1`, no matches.

## Cleanup
- `test ! -e /private/tmp/dalya-final-surface-frontend`: PASS after GREEN run.
- `test ! -e /private/tmp/dalya-final-surface-red-local`: PASS after fixture cleanup.
- `test ! -e /private/tmp/dalya-final-surface-red-production`: PASS after fixture cleanup.
- `test ! -e /private/tmp/dalya-final-surface-danger-parent`: PASS after fixture cleanup.
- `lsof -iTCP:3000 -sTCP:LISTEN -nP`: no output.
- `lsof -iTCP:3999 -sTCP:LISTEN -nP`: no output.

## DoneClaim
- changed_files: `frontend/scripts/verify-next-mvp-final-surface.mjs`, `.omo/evidence/task-3-dalya-post-closeout-hardening.md`, `.omo/evidence/task-3-final-surface/*`, `.omo/evidence/task-3-final-surface-red-env-local/*`, `.omo/evidence/task-3-final-surface-red-env-production-local/*`, `.omo/evidence/task-3-final-surface-red-safe-temp/*`, `BACKLOG.md`.
- tests: RED `.env.local` guard PASS; RED `.env.production.local` guard PASS; RED dangerous safe-temp guard PASS; GREEN safe-temp browser verifier PASS; screenshot hash/pixel distinction PASS; env transcript no-content scans PASS; `node --check` PASS; `npx --no-install tsc --noEmit` PASS; `git diff --check` PASS; anchored conflict scan PASS; cleanup checks PASS.
- risks: Direct fixture mode now blocks root-level `.env*` entries conservatively by name only; safe-temp mode remains the supported path when local env files are present.
