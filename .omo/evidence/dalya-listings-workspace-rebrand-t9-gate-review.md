# T9 Gate Review

recommendation: REJECT

## originalIntent

T9 was intended to add focused API and inventory UI tests for `/api/v1/listings/mine` and the listings inventory page without creating a broad new framework. Required coverage included empty state, normal row, missing facts/logistics next action, open offers and active viewings counts, brokerage scoping/no leak, lean payload/no nested mega-payload, search/filter/sort/action mapping, canonical links, and a legacy `/dashboard/listings` href failure guard.

## desiredOutcome

The user should be able to mark T9 complete only if the focused backend test, frontend verifier, typecheck, whitespace check, evidence JSON parse, direct overfit/slop review, and supporting review artifacts all show that T9 tests are meaningful and scoped to test/script/evidence files.

## userOutcomeReview

Most requested checks passed in direct execution. The backend pytest passed under no-secrets `.env.test` with escalated DNS/network access after sandbox DNS failed. The frontend verifier passed and imports runtime code compiled from `listingIndexActions.ts` plus an extracted source block from `AgentListingsIndex.tsx`; it does not keep a duplicate local implementation of the inventory helper. Typecheck, requested `git diff --check`, and JSON parse passed.

T9 still should not be marked complete. The backend tests assert `primary_next_action == "review_knowledge"` when both knowledge and logistics need attention, but they do not exercise the backend branch where knowledge is ready and missing ready-property logistics produces `primary_next_action == "set_logistics"`. That leaves the required missing-logistics next-action behavior uncovered. Separately, no T9 code-quality/slop review artifact exists, so the evidence set is missing the required independent report coverage for remove-ai-slops/programming criteria.

## checkedArtifactPaths

- `.omo/plans/dalya-listings-workspace-rebrand.md`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-9-tests.json`
- `tests/test_listing_inventory_api.py`
- `frontend/scripts/verify-listings-workspace.mjs`
- `frontend/src/components/listings/AgentListingsIndex.tsx`
- `frontend/src/components/listings/listingIndexActions.ts`
- `frontend/src/components/listings/AgentListingsTable.tsx`
- `frontend/src/components/app/nav-items.ts`
- `frontend/src/lib/queries.ts`
- `app/api/listing_inventory.py`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-3-code-quality-review.md`

## commandsAndResults

- `.venv-pilot/bin/dotenv -f .env.test run -- env PYTHONPATH=. .venv-pilot/bin/python -m pytest tests/test_listing_inventory_api.py -q`
  - sandbox result: blocked by DNS resolving the `.env.test` database host.
  - escalated rerun result: PASS, `5 passed, 47 warnings in 41.41s`; no env values printed.
- `cd frontend && node scripts/verify-listings-workspace.mjs`
  - PASS, JSON output reported 25 passed checks, 8 action cases, 29 scanned source files, unsupported action failure probe, and injected legacy href failure probe.
- `cd frontend && npx --no-install tsc --noEmit`
  - PASS, exit 0 with no output.
- `git diff --check tests/test_listing_inventory_api.py frontend/scripts .omo/evidence/dalya-listings-workspace-rebrand/task-9-tests.json`
  - PASS, exit 0 with no output.
- `node -e "JSON.parse(require('node:fs').readFileSync('.omo/evidence/dalya-listings-workspace-rebrand/task-9-tests.json','utf8')); console.log('json-ok')"`
  - PASS, `json-ok`.
- `git diff --no-index --check /dev/null tests/test_listing_inventory_api.py`
  - no whitespace diagnostics; exit 1 expected for no-index file difference.
- `git diff --no-index --check /dev/null frontend/scripts/verify-listings-workspace.mjs`
  - no whitespace diagnostics; exit 1 expected for no-index file difference.
- `git diff --no-index --check /dev/null .omo/evidence/dalya-listings-workspace-rebrand/task-9-tests.json`
  - no whitespace diagnostics; exit 1 expected for no-index file difference.

## directCoverageReview

- Backend empty state: covered by `test_my_listings_returns_empty_counts_for_empty_brokerage`.
- Backend normal row: covered by `test_my_listings_flags_missing_knowledge_and_logistics_for_attention`.
- Backend missing facts: covered with `missing_fact_count == 1`, `knowledge_status == "needs_attention"`, and `primary_next_action == "review_knowledge"`.
- Backend missing logistics next action: not fully covered. The test seeds absent logistics but also missing knowledge, so backend priority selects `review_knowledge`; the `set_logistics` branch is untested.
- Backend open offers/active viewings counts: covered with both counts asserted as `1`.
- Backend brokerage scoping/no leak: covered by same-brokerage assigned-agent scoping, multi-membership no-header `409 brokerage_context_required`, and explicit brokerage-B no-leak test.
- Backend lean payload/no nested mega-payload: covered by exact key-set assertion against `LEAN_LISTING_KEYS`.
- Frontend production helper/source of truth: acceptable. The verifier imports `nextActionForListing` and `SUPPORTED_INDEX_ACTIONS` from compiled production source, and extracts then exports the `AgentListingsIndex.tsx` inventory helper source instead of maintaining duplicate local helper functions.
- Frontend search/filter/sort/action mapping and canonical links: covered by the verifier output and direct source inspection.
- Legacy href guard: covered for scanned canonical listing roots and an injected failing probe; note the scan is not whole-frontend.
- Scope control: T9 evidence declares only `tests/test_listing_inventory_api.py`, `frontend/scripts/verify-listings-workspace.mjs`, and the T9 evidence JSON. Current worktree has many broader plan product files untracked/modified, so T9 product-scope isolation depends on the executor evidence and targeted path inspection.

## removeAiSlopsAndProgrammingPass

Loaded and applied `omo:remove-ai-slops` and `omo:programming` criteria directly.

- No deletion-only tests found.
- No tests that merely verify requested removal found.
- No snapshot-only or exact-rendering frontend checks found.
- Backend tests mostly assert observable API behavior through the route and seeded database rows, not private helper calls.
- The frontend verifier has some source-shape coupling because it extracts a helper block by string markers. This is acceptable for this focused verifier because it prevents duplicate helper logic and fails loudly if the helper structure moves.
- No unnecessary production extraction was added by T9; production helper extraction happens only inside the verifier temp module.
- Pure LOC: `tests/test_listing_inventory_api.py` 190, `frontend/scripts/verify-listings-workspace.mjs` 222, `frontend/src/components/listings/AgentListingsIndex.tsx` 217, `app/api/listing_inventory.py` 249.

## evidenceGaps

- Missing T9 code-quality/slop review report artifact. `find .omo/evidence ... task-9*review*` found no T9 review report, and `task-9-tests.json` does not explicitly provide the required remove-ai-slops/programming report coverage.
- Missing backend test for the backend `set_logistics` next-action branch when logistics are missing but knowledge is ready.
- Missing notepad path in the supplied input/evidence set.
- No separate manual QA matrix artifact was supplied for T9; the JSON has command/evidence checklists, but not a manual QA matrix path.

## blockers

1. Add a backend API test that proves a ready listing with acceptable knowledge but missing logistics returns `logistics_status == "needs_attention"` and `primary_next_action == "set_logistics"`.
2. Add the missing T9 code-quality/slop review artifact with explicit remove-ai-slops/programming coverage, including overfit/slop criteria for deletion-only tests, tautological tests, implementation-mirroring tests, unnecessary production extraction, and scope drift.

## final

T9 cannot be marked complete yet.
