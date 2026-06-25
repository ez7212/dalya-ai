recommendation: REJECT

# T5 Gate Review - /listings Inventory Command Center

## originalIntent
Upgrade `/listings` from a shallow placeholder/table into a dense operational inventory command center for agents. The index should make it obvious which listings need attention and should use only canonical `/listings/*` routes.

## desiredOutcome
Agents can scan inventory and see listing status, type/community, price, assigned agent, buyer conversations, knowledge and missing-fact state, logistics readiness, active viewings, open offers, last activity, and the correct primary next action. Search, status/work filters, sort, loading/error/empty/no-results states, and responsive rows/cards should work without legacy dashboard links or dark/gold styling.

## userOutcomeReview
The code and UI artifacts support the user-visible `/listings` command-center outcome. `frontend/src/app/(app)/listings/page.tsx` renders `AgentListingsIndex`. The index exposes summary metrics, search/status/work/sort controls, loading/error/empty/no-results states, and responsive listing cards/table code. The screenshots at 1280, 768, and 375 show a light slate operational inventory surface with the required fields and usable next actions.

Source inspection confirms canonical links: listing identity links use `/listings/${id}`, primary next actions come from `nextActionForListing`, and every supported action maps to `/listings/<id>` or a canonical subroute (`/knowledge`, `/logistics`, `/offers`, `/documents`). Scoped route/style scans over the T5-owned files returned no `/dashboard/listings` or banned legacy dark/gold token matches.

The stale limitation in `task-5-index.json` says visual browser screenshot QA could not be completed. Later evidence in `task-5-browser-qa/transcript.json` clearly supersedes it: the staged browser QA passed 81 checks, covered 1280/768/375, captured PNGs, verified canonical links/no overflow/no-results, and recorded cleanup of the 3197 QA server and temp workspace. The stale line is an evidence gap but not, by itself, misleading enough to reject because the superseding artifact is present and valid.

## blockers
- A Next dev server is still running from the reviewed workspace: `lsof -nP -iTCP:3000 -sTCP:LISTEN` reports PID 25996 on `127.0.0.1:3000`, and escalated `lsof -nP -p 25996` shows cwd `/Users/eric/dalya-ai/frontend`. The QA server on port 3197 was cleaned up, but the user explicitly asked to verify no dev server left running. T5 cannot be marked complete until PID 25996 is stopped or explicitly documented as user-owned/pre-existing and the no-leftover-server check is rerun.

## commandsAndResults
- `cd frontend && npx --no-install tsc --noEmit`: exit 0.
- `cd frontend && npm run lint`: exit 1, with errors in unrelated files (`ConversationDetail.tsx`, `EscalationInbox.tsx`, `SellerUpload.tsx`, `InspectionAudioInput.tsx`) and no T5-owned errors in the output.
- Scoped listings ESLint with quoted App Router path and T5 files: exit 0.
- Scoped legacy route/style scan over T5-owned files plus `queries.ts`: exit 1 with no output, meaning no matches.
- Broad legacy style scan over `frontend/src/app/(app)/listings` and `frontend/src/components/listings`: exit 0 only because out-of-scope creation-flow files (`FinishedListingFlow.tsx`, `NewListingFlow.tsx`) contain `surface-1` fallback strings. These are documented non-blocking matches outside T5 ownership.
- `git diff --check` for tracked T5 files/evidence: exit 0.
- `git diff --check --no-index -- /dev/null <new T5 file>` for untracked T5 files/evidence: exit 1 by Git design for new-file diffs, with no whitespace/conflict-marker output.
- `python3 -m json.tool` on `task-5-index.json`, `task-5-browser-qa/transcript.json`, and `source-state-receipt.json`: exit 0.
- Browser QA transcript summary: `passed=True`, `checks=81`, `failed=[]`, artifact widths `[1280, 768, 375]`, no viewport horizontal overflow.
- `test ! -e /private/tmp/dalya-final-surface-listings-qa`: exit 0.
- `lsof -nP -iTCP:3197 -sTCP:LISTEN`: exit 1 with no output, confirming the browser QA server is gone.
- `lsof -nP -iTCP:3000 -sTCP:LISTEN`: exit 0, showing a remaining `node` listener.
- `ps -p 25996 -o pid=,ppid=,start=,command=` with escalation: `25996 25995 7:29PM next-server (v16.2.1)`.

## slopAndQualityPass
Direct `remove-ai-slops` review found no deletion-only tests, tests that merely verify a requested removal, tautological tests, implementation-mirroring tests, unnecessary production extraction, over-defensive code, debug leftovers, or legacy route/style slop in the T5-owned index slice. There are no checked-in frontend tests for this slice, so there is no overfit-test slop; the remaining test gap is deferred to T9 by the plan and partly covered by deterministic browser/source QA.

Direct `programming` review found finite listing index field unions in `AgentListingSummary`, explicit action mapping with `assertNever`, no `any`/type-assertion/ts-ignore/non-null escape hatches in T5-owned files, and no T5-owned source file above the 250 pure-LOC defect threshold. Pure LOC: `AgentListingsIndex.tsx` 217, `AgentListingsControls.tsx` 150, `AgentListingsTable.tsx` 224. `AgentListingsIndex.tsx` remains in the warning band, but not over threshold.

The code-quality report explicitly includes `omo:programming`, the TypeScript reference, `omo:remove-ai-slops`, frontend/design/perfection context, and a slop/overfit audit. Its top-level `NEEDS-FIX` verdict is historical; the remediation note plus direct source checks confirm the listed action-contract/type blockers were resolved.

## checkedArtifactPaths
- `.omo/plans/dalya-listings-workspace-rebrand.md`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-5-code-quality-review.md`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/run-listings-qa.mjs`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/source-state-receipt.json`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/transcript.json`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/listings-1280.png`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/listings-768.png`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/listings-375.png`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/listings-375-no-results.png`
- `.omo/evidence/dalya-listings-workspace-rebrand-t5-gate-review.md`
- `DESIGN.md`
- `frontend/src/app/(app)/listings/page.tsx`
- `frontend/src/components/listings/AgentListingsIndex.tsx`
- `frontend/src/components/listings/AgentListingsControls.tsx`
- `frontend/src/components/listings/AgentListingsTable.tsx`
- `frontend/src/components/listings/listingIndexActions.ts`
- `frontend/src/components/listings/listingIndexLabels.ts`
- `frontend/src/lib/queries.ts`
- `app/api/listing_inventory.py`

## evidenceGaps
- `task-5-index.json` still contains a stale known limitation saying browser screenshot QA could not be completed. The later browser QA artifact supersedes it, but final reporting should cite `task-5-browser-qa/transcript.json` instead of the stale line.
- Browser QA covered 1280/768/375 cards; the dense table exists behind `2xl:block` and was source-verified but not screenshot-verified at a >=1536 viewport.
- Broad lint remains red due unrelated existing files outside T5 ownership.
- Broad legacy-token scan under `frontend/src/components/listings` still reports out-of-scope creation-flow `surface-1` fallback strings.
- No checked-in frontend unit/interaction test covers search/filter/sort/action mapping; T9 is the planned test task.
- A workspace Next dev server remains running on port 3000, which blocks the user's cleanup criterion.

## verdict
confidence: high for the T5 inventory-index implementation; high for the cleanup blocker.

canMarkT5Complete: false
