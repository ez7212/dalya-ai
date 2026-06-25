# T1 Tracking - Listings Workspace Rebrand

Plan: `.omo/plans/dalya-listings-workspace-rebrand.md`
Task: T1, record implementation tracking and dirty-worktree boundaries.
Date: 2026-06-24

## Baseline / Failing-First Proof

Command:

```bash
omo sparkshell --shell 'rg -n "listings workspace migration|agent inventory workspace|dalya-listings-workspace-rebrand" BACKLOG.md .omo/evidence/dalya-listings-workspace-rebrand 2>/dev/null || true' --budget 20000
```

Result: exit 0 with empty output. No prior T1 tracking note matched the required migration/evidence terms before edits.

## Tracking Record

Linear was available through the Linear MCP connector.

- Issue: `DAL-203`
- Title: `Pass 1 listings workspace migration`
- URL: `https://linear.app/dalya/issue/DAL-203/pass-1-listings-workspace-migration`
- State: `Todo`
- Priority: `Medium`
- Label: `Feature`
- Link attachment note: Linear rejected the local `file://` plan link as an unsupported URL, but the issue description names the local plan path.

`BACKLOG.md` was updated with an open `DAL-203: Pass 1 listings workspace migration` item under the current Dalya B2B backlog. This is not the Linear fallback; it reflects the delivered tracking status required by project instructions.

## Dirty Worktree Boundary

Initial status command:

```bash
omo sparkshell --shell 'git status --short' --budget 20000
```

Captured pre-edit output:

```text
 M BACKLOG.md
 M app/main.py
 M frontend/src/app/(app)/listings/new/portal/page.tsx
 M frontend/src/app/(app)/listings/page.tsx
 M frontend/src/components/app/nav-items.ts
 M frontend/src/components/listings/FinishedListingFlow.tsx
 M frontend/src/lib/queries.ts
 M tests/test_brokerage_context_dal172.py
?? .omo/boulder.json
?? .omo/drafts/
?? .omo/pilots/
?? .omo/plans/dalya-internal-omo-pilot.md
?? .omo/plans/dalya-listings-workspace-rebrand.md
?? .omo/start-work/
?? .venv-pilot/
?? app/api/listing_inventory.py
?? claude-pilot/
?? codex-pilot/
?? frontend/src/components/listings/AgentListingsIndex.tsx
?? frontend/src/components/listings/AgentListingsTable.tsx
```

Listings-related existing user/LazyCodex changes identified before T1 edits:

- `frontend/src/app/(app)/listings/new/portal/page.tsx`
- `frontend/src/app/(app)/listings/page.tsx`
- `frontend/src/components/listings/FinishedListingFlow.tsx`
- `frontend/src/lib/queries.ts`
- `app/api/listing_inventory.py`
- `frontend/src/components/listings/AgentListingsIndex.tsx`
- `frontend/src/components/listings/AgentListingsTable.tsx`
- Possibly listing-adjacent: `app/main.py`, `frontend/src/components/app/nav-items.ts`, `tests/test_brokerage_context_dal172.py`

Other existing dirty/untracked state observed and not touched:

- `.omo/boulder.json`
- `.omo/drafts/`
- `.omo/pilots/`
- `.omo/plans/dalya-internal-omo-pilot.md`
- `.omo/plans/dalya-listings-workspace-rebrand.md`
- `.omo/start-work/`
- `.venv-pilot/`
- `claude-pilot/`
- `codex-pilot/`

Boundary decision: T1 only edits `BACKLOG.md` and `.omo/evidence/dalya-listings-workspace-rebrand/task-1-tracking.md`, plus creates `.omo/evidence/dalya-listings-workspace-rebrand/task-1-git-status.txt` during verification. Existing dirty listings work is preserved; unrelated changes must not be reverted.

## Manual QA Channel

Data-shaped QA: inspect this evidence file and the git-status artifact.

Binary observable:

- `.omo/evidence/dalya-listings-workspace-rebrand/task-1-tracking.md` exists and contains `DAL-203`, `listings workspace`, `inventory workspace`, `Linear`, and `dalya-listings-workspace-rebrand`.
- `.omo/evidence/dalya-listings-workspace-rebrand/task-1-git-status.txt` exists and is non-empty after the verification command.
- Required grep returns concrete matches from `BACKLOG.md` and this evidence file.

Artifact paths:

- `.omo/evidence/dalya-listings-workspace-rebrand/task-1-tracking.md`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-1-git-status.txt`

## Adversarial QA

- `dirty_worktree`: applicable. Pre-edit status lists existing modified/untracked files above. Do not revert unrelated changes.
- `stale_state`: applicable. Re-read `git status --short` after edits via the required verification command into `task-1-git-status.txt`.
- `misleading_success_output`: applicable. Required grep output must include match lines, not only an exit code.
- `long external commands`: not applicable. Linear returned in 4.3773s and no long-running external command was used.
- `malformed input`: not applicable. No parser input.
- `prompt injection`: not applicable. No untrusted external text consumed.
- `cancel/resume`: not applicable. Short state task.
- `flaky tests`: not applicable. No timing-sensitive tests.
- `repeated interruptions`: not applicable. No interruption occurred.

## Cleanup Receipt

none needed. No servers, processes, ports, containers, or temporary QA resources were started. Evidence directory path: `.omo/evidence/dalya-listings-workspace-rebrand/`.

## Post-Edit Evidence Summary

Required verification command 1:

```bash
omo sparkshell --shell 'git status --short > .omo/evidence/dalya-listings-workspace-rebrand/task-1-git-status.txt && test -s .omo/evidence/dalya-listings-workspace-rebrand/task-1-git-status.txt' --budget 20000
```

Result: exit 0 with empty stdout. Binary observable passed: `task-1-git-status.txt` exists and is non-empty.

Required verification command 2:

```bash
omo sparkshell --shell 'rg -n "listings workspace|inventory workspace|Linear|DAL-|dalya-listings-workspace-rebrand" BACKLOG.md .omo/evidence/dalya-listings-workspace-rebrand/task-1-tracking.md' --budget 20000
```

Result: exit 0 with concrete matches, including:

- `task-1-tracking.md:19:Linear was available through the Linear MCP connector.`
- `task-1-tracking.md:21:- Issue: \`DAL-203\``
- `task-1-tracking.md:22:- Title: \`Pass 1 listings workspace migration\``
- `BACKLOG.md:28:- [ ] **DAL-203: Pass 1 listings workspace migration.** ...`

Required verification command 3:

```bash
omo sparkshell --shell 'git diff --check BACKLOG.md .omo/evidence/dalya-listings-workspace-rebrand/task-1-tracking.md' --budget 20000
```

Result: exit 0 with empty stdout. No whitespace errors were reported for the edited files.

Artifact inspection:

```bash
omo sparkshell --shell 'wc -c .omo/evidence/dalya-listings-workspace-rebrand/task-1-tracking.md .omo/evidence/dalya-listings-workspace-rebrand/task-1-git-status.txt' --budget 20000
omo sparkshell --shell 'sed -n "1,120p" .omo/evidence/dalya-listings-workspace-rebrand/task-1-git-status.txt' --budget 20000
omo sparkshell --shell 'git status --short' --budget 20000
```

Result at inspection time:

- `task-1-tracking.md`: 5024 bytes before this final summary append; content summary: baseline proof, Linear `DAL-203`, backlog tracking update, dirty-worktree boundary, manual QA channel, adversarial QA, cleanup receipt, and verification summaries.
- `task-1-git-status.txt`: 720 bytes; content summary: current short status with `BACKLOG.md` modified, pre-existing modified listings/product/test files, and `.omo/evidence/dalya-listings-workspace-rebrand/` now untracked.
- Re-read `git status --short` matched `task-1-git-status.txt` at inspection time, proving stale-state recheck. The only intentional T1 scope additions were `BACKLOG.md` content and the `.omo/evidence/dalya-listings-workspace-rebrand/` evidence artifacts.
