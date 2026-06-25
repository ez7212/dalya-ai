# T12 Gate Review - dalya-listings-workspace-rebrand

## recommendation

REJECT

## confidence

High. The required JSON artifacts parse and most final-command evidence is internally consistent, but direct source and screenshot review found unresolved user-visible product defects and an incomplete final-wave code-quality artifact.

## originalIntent

T12 should prove that the Pass 1 listings workspace migration is actually deliverable: final checks, browser QA, delivery docs, cleanup evidence, and honest limitations for `.omo/plans/dalya-listings-workspace-rebrand.md`, without editing product code or marking the plan checkbox.

## desiredOutcome

Eric should be able to mark T12 complete only if `/listings` is a trustworthy operational inventory workspace for ready and off-plan listings, canonical workspace routes stay under `/listings/[id]`, old dashboard routes do not bounce to legacy UI, verification artifacts are evidence-backed, and delivery updates are concise and accurate.

## userOutcomeReview

The final artifact set is stronger than the previous rejected T12 state. `task-12-final.json`, `manualQa.json`, and `browser-transcript.json` parse; `final-report.md` exists; final command outputs evidence `tsc`, focused verifier scripts, pytest via `.env.test` with a no-secrets DNS retry, build retry, lint limitation, brand/nav scans, browser QA, Command Center logging, and cleanup. Browser QA now derives PASS rows from route markers, DOM/link/overflow checks, screenshot file existence, redirect final paths, and cleanup state rather than unconditional PASS literals. It covers `/listings`, overview, documents, knowledge, logistics, and offers at 1280/768/375, plus five `/dashboard/listings/*` redirect paths.

From the user's perspective, the shipped result is still not approval-ready. The direct product-code pass found off-plan listings are mishandled by the new inventory contract/UI, and sampled final screenshots show the workspace primary CTA leaking a raw enum token (`review_knowledge`). These are exactly the kind of user-visible issues final browser QA should catch before T12 claims Green.

## blockers

1. **Off-plan logistics status is emitted by the API but unsupported by the frontend, causing false attention state.**

   Evidence: `app/api/listing_inventory.py:115-117` returns `"not_required"` for off-plan listings. `frontend/src/lib/queries.ts:76-77` types `AgentListingLogisticsStatus` as only `'ready' | 'needs_attention'`. `frontend/src/components/listings/listingIndexLabels.ts:23-31` has no label branch for `not_required`, and `frontend/src/components/listings/AgentListingsIndex.tsx:144-150` treats every logistics status other than `ready` as needing attention. Result: an off-plan listing with ready knowledge can be marked as attention-needed and can render an incomplete `Logistics` badge label. This violates the plan's off-plan/ready-property scope and the inventory goal of showing which listings actually need work.

   Evidence gap: `tests/test_listing_inventory_api.py:180-229` covers ready listings only. The final browser fixture is also ready-only (`run-final-browser-qa.mjs:50`), while `task-3-api.json` claims off-plan listings are `not_required`. No final QA artifact proves the off-plan path renders correctly.

2. **Workspace primary CTA displays raw enum copy.**

   Evidence: `frontend/src/components/listings/ListingWorkspaceShell.tsx:235-244` sets `label = summary?.primary_next_action`, so `review_knowledge` is rendered directly. The sampled final screenshots `final-qa/overview-1280.png` and `final-qa/logistics-375.png` visibly show the top CTA as `review_knowledge`. The index action helper already has the correct human label mapping at `frontend/src/components/listings/listingIndexActions.ts:22-39`, but the workspace shell does not reuse it.

   Impact: this fails the user-visible outcome for quiet operational software and the product CTA standard. It also proves the final browser QA did not assert important visible copy despite reporting a PASS.

3. **Final-wave code-quality coverage is incomplete for the actual product diff.**

   Evidence: final verification wave F2 requires a code quality review that audits changed API/frontend code for scoped payloads, route-backed navigation, type safety, no broad refactors, no dirty-worktree overwrite, and no suppressed errors (`.omo/plans/dalya-listings-workspace-rebrand.md:188-192`). The current T12 code-quality artifact scopes itself to the final QA harness/evidence and says the production/test dirty diff is "evidence only" (`final-qa/t12-code-quality-review.md:5-11`). It does include useful overfit/slop coverage for the browser harness, but it did not catch the off-plan API/frontend contract mismatch or raw CTA label.

   Impact: the final PASS report overclaims code-quality closure. Prior per-task reviews reduce risk, but they do not replace the final F2 audit over the integrated product state.

## nonBlockingNotes

- `task-12-final.json`, `manualQa.json`, and `browser-transcript.json` parse. `final-report.md` exists.
- Final command evidence is present for `tsc`, `verify-listings-workspace`, `verify-listing-legacy-redirects`, focused pytest, build, lint, browser QA, scans, and Command Center logging.
- `npm run lint` remains blocked by unrelated existing non-listings errors; the limitation is explicit and not overclaimed as clean.
- The broad legacy-token scan only matches `--color-surface-1` CSS variable references in deferred creation-flow files; precise canonical workspace scan is empty.
- Cleanup evidence is acceptable: the QA server was stopped, `lsof -iTCP:52310 -sTCP:LISTEN -n -P` returned no listener, `/private/tmp/dalya-final-surface-listings-final-qa` is absent, and the pre-existing port 3000 listener was intentionally left untouched with curl/lsof rationale.
- `BACKLOG.md` and `PROJECT_BRIEF.md` updates are concise enough for DAL-203 and correctly mention Pass 2 as follow-up.
- Size watch: `app/api/listing_inventory.py` is 249 pure LOC, `ListingOverviewWorkspace.tsx` 248, and `ListingLogisticsForm.tsx` 246. They are below the hard ceiling but in the warning band.

## commandsResults

- `jq empty task-12-final.json manualQa.json browser-transcript.json`: PASS.
- `test -f final-report.md`: PASS.
- `git status --short`: dirty tree with DAL-203 product/evidence changes; plan checkbox remains unchecked.
- `git diff --check -- <tracked T12/product paths>`: PASS, no output.
- `rg -n "[[:blank:]]$" <final report/json/review artifacts>`: PASS, no trailing whitespace matches.
- `rg final-report anchors`: PASS; found Verification Commands, Browser QA, Known Limitations, and Evidence Index.
- `jq '{surface: (.surfaceEvidence | length), adversarial: (.adversarialCases | length)}' manualQa.json`: PASS, 23 surface rows and 5 adversarial rows.
- `jq '.results | length' browser-transcript.json`: PASS, 23 route/redirect results.
- `rg unconditional PASS scan run-final-browser-qa.mjs`: PASS; no unconditional PASS literals found, verdicts are computed expressions.
- `lsof -iTCP:52310 -sTCP:LISTEN -n -P`: PASS by no listener output.
- `test ! -e /private/tmp/dalya-final-surface-listings-final-qa`: PASS.
- Visual inspection via `view_image`: `index-375.png`, `overview-1280.png`, and `logistics-375.png` are light/slate and non-legacy, but overview/logistics show raw CTA text `review_knowledge`.

## checkedArtifactPaths

- `.omo/plans/dalya-listings-workspace-rebrand.md`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-12-final.json`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-report.md`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/manualQa.json`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/browser-transcript.json`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/t12-code-quality-review.md`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/t12-dirty-worktree-receipt.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/cleanup-receipt.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/tsc.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/verify-listings-workspace.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/verify-listing-legacy-redirects.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/pytest-listing-inventory.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/pytest-listing-inventory-escalated.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/npm-build.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/npm-build-escalated.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/npm-lint.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/run-final-browser-qa.mjs`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/overview-1280.png`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/logistics-375.png`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/lsof-port-3000-after.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/curl-localhost-3000-listings.txt`
- `.omo/evidence/dalya-listings-workspace-rebrand/final-qa/curl-127001-3000-listings.txt`
- `app/api/listing_inventory.py`
- `tests/test_listing_inventory_api.py`
- `frontend/src/lib/queries.ts`
- `frontend/src/components/listings/AgentListingsIndex.tsx`
- `frontend/src/components/listings/AgentListingsTable.tsx`
- `frontend/src/components/listings/listingIndexLabels.ts`
- `frontend/src/components/listings/listingIndexActions.ts`
- `frontend/src/components/listings/ListingWorkspaceShell.tsx`
- `BACKLOG.md`
- `PROJECT_BRIEF.md`

## exactEvidenceGaps

- No backend/frontend/browser test covers an off-plan listing with `logistics_status: "not_required"`.
- No final browser assertion checks human-readable primary CTA labels; screenshots show a raw enum leak while the QA report says PASS.
- The T12 code-quality/slop report covers final evidence harness integrity, but not the integrated changed API/frontend product state required by final-wave F2.

## canMarkT12Complete

false
