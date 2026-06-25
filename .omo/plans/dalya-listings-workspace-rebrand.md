# dalya-listings-workspace-rebrand - Work Plan

## TL;DR (For humans)
**What you'll get:** A real Dalya agent inventory workspace: listings that show what needs attention, listing workspaces that stay inside the new product, and legacy listing routes that no longer drop agents into the old dark/gold Mahoroba dashboard.

**Why this approach:** The first pass fixes the canonical workspace and navigation before touching the giant creation flow. That gets the daily agent surface coherent without turning a brand/workspace migration into a broad form refactor.

**What it will NOT do:** It will not fully split the listing creation flow in this pass unless creation is blocking basic workspace usability. It will not redesign owner/admin surfaces or introduce a new visual language outside the locked Dalya brand.

**Effort:** Large
**Risk:** Medium - the risk is route/API coupling across old listing detail tabs and the existing dirty worktree, not the visual direction.
**Decisions to sanity-check:** Canonical documents route is `/listings/[id]/documents`, not `/spa`; `/dashboard/listings/*` becomes compatibility/redirect only; Pass 2 is follow-up unless creation blocks Pass 1.

Your next move: say `$start-work` or otherwise hand this plan to LazyCodex for execution. Full execution detail follows below.

---

> TL;DR (machine): Large medium-risk Pass 1 migration: design contract, lean inventory API additions, operational `/listings`, canonical `/listings/[id]` shell/subroutes, legacy redirects, tests, browser QA, and a non-blocking Pass 2 creation-flow follow-up.

## Scope
### Must have
- `DESIGN.md` at repo root as a practical implementation contract for new Dalya agent surfaces.
- `/listings` upgraded from a shallow table into an operational inventory command center.
- Additive `/api/v1/listings/mine` fields for index-level health and activity only.
- Canonical `/listings/[id]` workspace shell with route-backed tabs:
  - `/listings/[id]`
  - `/listings/[id]/knowledge`
  - `/listings/[id]/logistics`
  - `/listings/[id]/offers`
  - `/listings/[id]/documents`
- Shared listing workspace header: breadcrumb, listing title/status, assigned agent, price/community/type, health badges, tabs, and primary next action.
- `/listings` rows/cards answer “which listings need my attention?” with title, community, type, bedrooms, asking price, live/draft/incomplete state, listing health, conversations/leads, open offers, active viewings, knowledge status, logistics status, assigned agent, last activity, and next action.
- Filters for ready/off-plan, live/draft, missing facts, logistics needed, has offers, and active buyer conversations.
- Search by title, community, unit, and listing id.
- Sort by last activity, created date, leads/conversations, escalations/offers, and asking price.
- Row/card actions: Open, Review knowledge, Set logistics, View offers, Add listing.
- Legacy `/dashboard/listings/*` routes redirect or compatibility-wrap to canonical `/listings/*`.
- No gold/dark legacy classes in canonical `/listings` routes.
- Focused backend/frontend tests, typecheck/lint/build, and browser QA at mobile/tablet/desktop widths.
- Pass 2 creation-flow cleanup captured as follow-up ticket/plan, not required for Pass 1 Green unless creation is broken.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Do not fully rewrite or split `FinishedListingFlow.tsx` in Pass 1 unless it blocks add-listing usability.
- Do not leave canonical listing detail routes under `/dashboard/listings/*`.
- Do not let `/listings` links open old dark/gold listing pages.
- Do not use gold/dark luxury classes (`text-gold`, `btn-gold`, `surface-1`, `text-sand`, `border-gold`, `bg-deep`, `ghost-border`, `shadow-gold`) in canonical `/listings` routes.
- Do not add a bulky index payload that embeds all documents, offers, logistics, or full knowledge records.
- Do not redesign unrelated owner/admin/campaign/seller-archive surfaces.
- Do not introduce a new design system beyond the locked Dalya B2B brand.
- Do not weaken route-backed navigation with in-component step state for primary listing workspace screens.
- Do not revert current uncommitted user/LazyCodex changes; work with them.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: tests-after for API/UI behavior, plus browser visual QA. No broad new framework.
- Backend tests: focused pytest around `/api/v1/listings/mine` computed fields, brokerage scoping, and empty state.
- Frontend static checks: `cd frontend && npx --no-install tsc --noEmit`, `cd frontend && npm run lint`, `cd frontend && npm run build`.
- Browser QA: real local app screenshots/transcripts for `/listings`, `/listings/[id]`, `/listings/[id]/knowledge`, `/listings/[id]/logistics`, `/listings/[id]/offers`, `/listings/[id]/documents`, plus old-route redirects. Test desktop 1280px, tablet 768px, and mobile 375px.
- Visual/brand scan: `rg -n "text-gold|btn-gold|surface-1|text-sand|border-gold|bg-deep|ghost-border|shadow-gold|#C9A96E|gold" frontend/src/app/'(app)'/listings frontend/src/components/listings` must return no matches except documented compatibility comments if any.
- Navigation scan: `rg -n "/dashboard/listings" frontend/src/app/'(app)'/listings frontend/src/components/listings` must return no canonical links.
- Evidence root: `.omo/evidence/dalya-listings-workspace-rebrand/`.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.
- Wave 0: tracking, dirty-worktree audit, and design contract.
- Wave 1: API contract and canonical route shell can proceed in parallel after design contract.
- Wave 2: inventory page and workspace subpage migrations proceed against the shell/API contract.
- Wave 3: redirects, Pass 2 follow-up package, and verification hardening.
- Wave 4: final browser QA, brand scan, and report/update.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| T1 tracking + dirty-worktree audit | none | T2-T12 | none |
| T2 design contract | T1 | T3-T12 | none |
| T3 listing API contract | T2 | T5, T9, T12 | T4, T6 |
| T4 canonical route skeleton + redirects map | T2 | T6, T7, T8, T10, T12 | T3 |
| T5 inventory page UX | T3, T4 | T9, T12 | T6, T7, T8 |
| T6 workspace shell | T4 | T7, T8, T10, T12 | T5 |
| T7 overview + documents migration | T6 | T10, T12 | T8 |
| T8 knowledge/logistics/offers migration | T6 | T10, T12 | T7 |
| T9 frontend/API tests for inventory | T3, T5 | T12 | T10, T11 |
| T10 redirect compatibility tests | T4, T7, T8 | T12 | T9, T11 |
| T11 Pass 2 creation follow-up package | T1 | T12 | T9, T10 |
| T12 final QA and report | T5, T7, T8, T9, T10, T11 | final verification | none |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [x] 1. Record implementation tracking and dirty-worktree boundaries.
  What to do / Must NOT do: Create or attach one Linear issue for the Pass 1 listings workspace migration if Linear is available; otherwise record one umbrella item in `BACKLOG.md` and continue. Capture `git status --short` before edits and identify current user/LazyCodex changes in listings-related files. Do not revert or overwrite unrelated changes.
  Parallelization: Wave 0 | Blocked by: none | Blocks: T2-T12
  References (executor has NO interview context - be exhaustive): `AGENTS.md` delivery tracking; `BACKLOG.md`; current dirty files seen during planning: `frontend/src/app/(app)/listings/page.tsx`, `frontend/src/components/listings/AgentListingsIndex.tsx`, `frontend/src/components/listings/AgentListingsTable.tsx`, `frontend/src/components/listings/FinishedListingFlow.tsx`, `frontend/src/lib/queries.ts`, `app/api/listing_inventory.py`, `frontend/src/components/app/nav-items.ts`, `app/main.py`.
  Acceptance criteria (agent-executable): Evidence file records Linear issue id or BACKLOG fallback, plus dirty-worktree scope. `rg -n "listings workspace|inventory workspace|Linear|DAL-" BACKLOG.md .omo/evidence/dalya-listings-workspace-rebrand/task-1-tracking.md` finds the tracking note.
  QA scenarios (name the exact tool + invocation): happy `git status --short > .omo/evidence/dalya-listings-workspace-rebrand/task-1-git-status.txt && rg -n "listings workspace|inventory workspace|DAL-" BACKLOG.md .omo/evidence/dalya-listings-workspace-rebrand/task-1-tracking.md`; failure `test -s .omo/evidence/dalya-listings-workspace-rebrand/task-1-git-status.txt`. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-1-tracking.md`
  Commit: Y | docs(listings): track workspace migration

- [x] 2. Create the practical Dalya agent `DESIGN.md` contract.
  What to do / Must NOT do: Add `DESIGN.md` at repo root as a short implementation contract, not a brand manifesto. Include: light default surfaces, slate primary CTAs, no gold/dark luxury classes in new agent surfaces, 8px operational radius, Inter/tabular numerals for AED values, dense calm operations UI, sage/copper/brick/slate status palette, responsive table/card rules, route-backed workflow rule, and visual QA requirements. Do not duplicate the entire brand book.
  Parallelization: Wave 0 | Blocked by: T1 | Blocks: T3-T12
  References (executor has NO interview context - be exhaustive): `brand/BRAND.md`; `brand/applications/_tokens.css`; `frontend/src/app/globals.css`; `frontend/src/components/agent-dashboard/TodayQueue.tsx`; `frontend/src/components/app/AppSidebar.tsx`; `frontend/src/app/(app)/layout.tsx`.
  Acceptance criteria (agent-executable): `DESIGN.md` exists and contains the explicit banned legacy class list and listings workspace contract. `rg -n "No gold|text-gold|btn-gold|surface-1|8px|tabular|route-backed|Listings workspace" DESIGN.md` returns matches.
  QA scenarios (name the exact tool + invocation): happy `test -f DESIGN.md && rg -n "Listings workspace|No gold|Slate|Inter|tabular|route-backed" DESIGN.md`; failure `! rg -n "luxury|premium|opulent|gold as primary" DESIGN.md`. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-2-design-contract.md`
  Commit: Y | docs(design): add Dalya agent surface contract

- [x] 3. Extend the lean listings inventory API contract.
  What to do / Must NOT do: Add only index-level fields to `/api/v1/listings/mine`: `last_activity_at`, `assigned_agent_name`, `knowledge_status`, `missing_fact_count`, `active_viewing_count`, `open_offer_count`, `buyer_conversation_count`, `logistics_status`, and `primary_next_action`. Compute from existing listing stats, conversations, offers, viewings, documents/facts/knowledge, and logistics models where available. Use conservative statuses when data is absent. Do not include full documents, full offers, full logistics payloads, or full knowledge facts in the index response.
  Parallelization: Wave 1 | Blocked by: T2 | Blocks: T5, T9, T12
  References (executor has NO interview context - be exhaustive): `app/api/listing_inventory.py`; `app/api/listings.py`; `app/api/agent.py`; `app/api/viewings.py`; `app/models/db_models.py`; `frontend/src/lib/queries.ts`; existing tests around brokerage context/listings if present.
  Acceptance criteria (agent-executable): Backend response for seeded/listing test data includes the new fields; non-managing agents remain scoped to own/assigned listings; empty database returns empty list with zero counts. Add focused pytest coverage.
  QA scenarios (name the exact tool + invocation): happy `PYTHONPATH=. python3 -m pytest tests/test_listing_inventory_api.py -q`; failure test creates a listing with missing buyer-safe facts/logistics and asserts `knowledge_status`/`logistics_status`/`primary_next_action` indicate attention needed. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-3-api.json`
  Commit: Y | feat(listings): add inventory health summary

- [x] 4. Add canonical `/listings/[id]` routes and redirect map.
  What to do / Must NOT do: Create canonical route files for `/listings/[id]`, `/listings/[id]/knowledge`, `/listings/[id]/logistics`, `/listings/[id]/offers`, and `/listings/[id]/documents`. Add redirects or compatibility wrappers from `/dashboard/listings/[id]`, `/dashboard/listings/[id]/knowledge`, `/dashboard/listings/[id]/logistics`, `/dashboard/listings/[id]/offers`, and `/dashboard/listings/[id]/spa` to canonical routes. `/dashboard/listings/[id]/spa` should redirect to `/listings/[id]/documents`. Do not remove old files destructively unless the redirect replacement is clear and reviewed.
  Parallelization: Wave 1 | Blocked by: T2 | Blocks: T6, T7, T8, T10, T12
  References (executor has NO interview context - be exhaustive): `frontend/src/app/(app)/listings/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/layout.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/knowledge/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/logistics/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/offers/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/spa/page.tsx`; Next.js App Router redirect patterns in existing repo.
  Acceptance criteria (agent-executable): Canonical route files exist; old route requests redirect to canonical equivalents; no canonical route imports a legacy dashboard layout.
  QA scenarios (name the exact tool + invocation): happy `find frontend/src/app/'(app)'/listings -maxdepth 3 -type f | sort > .omo/evidence/dalya-listings-workspace-rebrand/task-4-routes.txt && rg -n "redirect\\(|permanentRedirect\\(|/listings/\\$\\{id\\}|/listings/\\[id\\]" frontend/src/app/'(app)'/dashboard/listings frontend/src/app/'(app)'/listings`; failure `! rg -n "/dashboard/listings" frontend/src/app/'(app)'/listings frontend/src/components/listings`. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-4-routes.txt`
  Commit: Y | feat(listings): add canonical listing workspace routes

- [x] 5. Upgrade `/listings` into the operational inventory command center.
  What to do / Must NOT do: Replace the shallow index/table with a searchable, filterable, sortable inventory surface. Preserve loading/error/empty states. Desktop should use a dense table with fixed-format columns; mobile should use stable cards. Include fields and filters listed in Scope. All links/actions must target `/listings/*`. Do not use fallback/sample rows as live data. Do not add marketing copy.
  Parallelization: Wave 2 | Blocked by: T3, T4 | Blocks: T9, T12
  References (executor has NO interview context - be exhaustive): `frontend/src/components/listings/AgentListingsIndex.tsx`; `frontend/src/components/listings/AgentListingsTable.tsx`; `frontend/src/lib/queries.ts`; `frontend/src/components/agent-dashboard/TodayQueue.tsx`; `frontend/src/components/agent-dashboard/DayIsClear.tsx`; `DESIGN.md`.
  Acceptance criteria (agent-executable): Search filters rows by title/community/unit/id; filters and sorts affect visible data; row actions point to canonical routes; empty/error/loading states remain composed and on-brand; mobile has no horizontal overflow.
  QA scenarios (name the exact tool + invocation): happy `cd frontend && npx --no-install tsc --noEmit && npm run lint`; failure browser QA injects one missing-facts listing and asserts its next action links to `/listings/<id>/knowledge`, not `/dashboard/listings/<id>/knowledge`. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json`
  Commit: Y | feat(listings): build inventory command center

- [x] 6. Build `ListingWorkspaceShell`.
  What to do / Must NOT do: Add a shared shell component for listing workspace routes. It must render breadcrumb `Listings / listing title`, title/status header, assigned agent, price/community/type metadata, health badges, primary next action, and route-backed tabs. Keep the shell light/slate and density-aligned with `/agent`. Do not let each tab own its own unrelated header or tab styling.
  Parallelization: Wave 2 | Blocked by: T4 | Blocks: T7, T8, T10, T12
  References (executor has NO interview context - be exhaustive): `frontend/src/app/(app)/dashboard/listings/[id]/layout.tsx`; `frontend/src/components/app/AppSidebar.tsx`; `frontend/src/components/agent-dashboard/TodayQueue.tsx`; `frontend/src/lib/queries.ts`; `DESIGN.md`.
  Acceptance criteria (agent-executable): Every canonical listing subroute renders the same shell/header/tabs; active tab is visible; primary next action links to the correct canonical subroute; shell has loading/error states.
  QA scenarios (name the exact tool + invocation): happy `cd frontend && npx --no-install tsc --noEmit`; failure browser QA opens `/listings/<id>/knowledge` directly and verifies shell still appears with active Knowledge tab. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-6-shell.json`
  Commit: Y | feat(listings): add listing workspace shell

- [x] 7. Migrate overview and documents routes into the new workspace.
  What to do / Must NOT do: Move/adapt the important overview content from old `/dashboard/listings/[id]` into `/listings/[id]`: key stats, listing settings/agent notes if still appropriate, buyer matches/inspection notes if they are agent-relevant, processing/health state. Create `/listings/[id]/documents` as the canonical document workspace for SPA, title deed, floor plans, brochures, ready-property docs, and attachments. Off-plan SPA fields can appear as a section in documents. Do not keep `/spa` as canonical.
  Parallelization: Wave 2 | Blocked by: T6 | Blocks: T10, T12
  References (executor has NO interview context - be exhaustive): `frontend/src/app/(app)/dashboard/listings/[id]/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/spa/page.tsx`; `frontend/src/components/shared-ui/UnitProfileView.tsx`; `frontend/src/components/shared-ui/InterestedBuyersPanel.tsx`; `frontend/src/lib/queries.ts`; `DESIGN.md`.
  Acceptance criteria (agent-executable): `/listings/[id]` and `/listings/[id]/documents` render useful content in the new style; AED values use Inter tabular numerals, not JetBrains/legacy mono; no gold/dark classes remain in those canonical files.
  QA scenarios (name the exact tool + invocation): happy `rg -n "text-gold|btn-gold|surface-1|text-sand|border-gold|bg-deep|ghost-border|shadow-gold" frontend/src/app/'(app)'/listings frontend/src/components/listings` returns no matches; failure browser QA opens a ready listing and an off-plan listing and verifies documents route labels do not imply every listing has SPA. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-7-overview-documents.json`
  Commit: Y | feat(listings): migrate overview and documents workspace

- [x] 8. Migrate knowledge, logistics, and offers routes into the new workspace.
  What to do / Must NOT do: Adapt existing knowledge, logistics, and offers content into `/listings/[id]/knowledge`, `/listings/[id]/logistics`, and `/listings/[id]/offers` under `ListingWorkspaceShell`. Convert legacy dark/gold classes to DESIGN.md tokens. Keep actions operational: review facts, upload/add document text where supported, set logistics, view active/past offers. Do not redesign unrelated viewing pages beyond shared logistics component styling needed here.
  Parallelization: Wave 2 | Blocked by: T6 | Blocks: T10, T12
  References (executor has NO interview context - be exhaustive): `frontend/src/app/(app)/dashboard/listings/[id]/knowledge/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/logistics/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/offers/page.tsx`; `frontend/src/components/viewings/ListingLogisticsForm.tsx`; `frontend/src/components/ui/Badge.tsx`; `frontend/src/lib/queries.ts`; `DESIGN.md`.
  Acceptance criteria (agent-executable): The three canonical subroutes render in light/slate style; forms have visible focus/error/loading states; offer statuses use sage/copper/brick/slate; no gold/dark classes remain in canonical listing files or listing logistics component.
  QA scenarios (name the exact tool + invocation): happy `rg -n "text-gold|btn-gold|surface-1|text-sand|border-gold|bg-deep|ghost-border|shadow-gold|#C9A96E" frontend/src/app/'(app)'/listings frontend/src/components/listings frontend/src/components/viewings/ListingLogisticsForm.tsx` returns no matches; failure browser QA opens logistics with missing data and verifies the empty/prefill state is readable and not dark-themed. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-8-subroutes.json`
  Commit: Y | feat(listings): migrate listing knowledge logistics offers

- [x] 9. Add focused API and inventory UI tests.
  What to do / Must NOT do: Add/extend tests for `/api/v1/listings/mine` and the inventory page behavior. Prefer existing pytest and frontend verification scripts. Do not create a broad new test framework. Cover empty state, normal row, missing facts/logistics next action, open offers/active viewings counts, brokerage scoping, and canonical link targets.
  Parallelization: Wave 3 | Blocked by: T3, T5 | Blocks: T12
  References (executor has NO interview context - be exhaustive): `tests/test_brokerage_context_dal172.py`; `tests/test_tenant_isolation_dal170.py`; `tests/test_viewing_logistics.py`; `tests/test_buyer_card_offers.py`; `app/api/listing_inventory.py`; `frontend/scripts/*` existing verification style; `frontend/src/components/listings/*`.
  Acceptance criteria (agent-executable): Focused backend tests pass; frontend script or component-level browser script verifies search/filter/sort and canonical links; failures are meaningful, not snapshot-only.
  QA scenarios (name the exact tool + invocation): happy `PYTHONPATH=. python3 -m pytest tests/test_listing_inventory_api.py -q && cd frontend && node scripts/verify-listings-workspace.mjs`; failure frontend script injects rows with old `/dashboard/listings` href and exits non-zero. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-9-tests.json`
  Commit: Y | test(listings): cover inventory workspace behavior

- [x] 10. Verify legacy redirects and compatibility wrappers.
  What to do / Must NOT do: Ensure old `/dashboard/listings/*` URLs redirect or compatibility-wrap to canonical `/listings/*`. Users must not bounce between new and legacy UI. Preserve browser back behavior. Do not leave duplicate detail implementations active unless old one is only a thin redirect/wrapper.
  Parallelization: Wave 3 | Blocked by: T4, T7, T8 | Blocks: T12
  References (executor has NO interview context - be exhaustive): `frontend/src/app/(app)/dashboard/listings/[id]/layout.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/knowledge/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/logistics/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/offers/page.tsx`; `frontend/src/app/(app)/dashboard/listings/[id]/spa/page.tsx`; Next.js redirect docs/patterns already in repo.
  Acceptance criteria (agent-executable): Direct visits to old routes land on canonical equivalents; `/dashboard/listings/[id]/spa` lands on `/listings/[id]/documents`; no old route renders a dark/gold listing page.
  QA scenarios (name the exact tool + invocation): happy browser script opens each old route and records final URL; failure script flags any final URL still starting `/dashboard/listings`. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-10-redirects.json`
  Commit: Y | chore(listings): redirect legacy listing routes

- [x] 11. Package Pass 2 creation-flow cleanup as follow-up.
  What to do / Must NOT do: Audit `FinishedListingFlow.tsx` and write a follow-up task/ticket plan for splitting it into route-backed creation steps. Include recommended routes `/listings/new`, `/listings/new/portal`, `/listings/new/manual`, `/listings/new/manual/ready`, `/listings/new/manual/off-plan`, and component extraction boundaries. If Pass 1 revealed creation is broken, escalate the smallest blocking fix only; otherwise do not refactor creation code in this pass.
  Parallelization: Wave 3 | Blocked by: T1 | Blocks: T12
  References (executor has NO interview context - be exhaustive): `frontend/src/components/listings/FinishedListingFlow.tsx`; `frontend/src/components/listings/NewListingFlow.tsx`; `frontend/src/app/(app)/listings/new/**`; `frontend/src/app/(app)/dashboard/listings/new/page.tsx`; App Navigation Architecture instructions in `AGENTS.md`.
  Acceptance criteria (agent-executable): Follow-up artifact exists with route plan, extraction modules, risks, and acceptance criteria; any Linear/BACKLOG follow-up references Pass 2 explicitly; Pass 1 final report says whether creation was changed or deferred.
  QA scenarios (name the exact tool + invocation): happy `test -f .omo/evidence/dalya-listings-workspace-rebrand/pass-2-creation-followup.md && rg -n "FinishedListingFlow|/listings/new/manual/ready|route-backed|Pass 2" .omo/evidence/dalya-listings-workspace-rebrand/pass-2-creation-followup.md`; failure `rg -n "Pass 2" BACKLOG.md .omo/evidence/dalya-listings-workspace-rebrand/pass-2-creation-followup.md`. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/pass-2-creation-followup.md`
  Commit: Y | docs(listings): scope creation flow follow-up

- [ ] 12. Run final checks, browser QA, and delivery update.
  What to do / Must NOT do: Run static checks, backend tests, build, brand scans, navigation scans, and browser QA. Capture screenshots/transcripts at 375, 768, and 1280 widths for `/listings` and key workspace subroutes. Update `BACKLOG.md` delivered status and Command Center activity. Do not claim Green if any canonical route still opens old dashboard UI or contains gold/dark classes.
  Parallelization: Wave 4 | Blocked by: T5, T7, T8, T9, T10, T11 | Blocks: final verification
  References (executor has NO interview context - be exhaustive): `DESIGN.md`; `frontend/src/app/(app)/listings/**`; `frontend/src/components/listings/**`; `frontend/src/components/viewings/ListingLogisticsForm.tsx`; `app/api/listing_inventory.py`; `BACKLOG.md`; Command Center logging instructions in `AGENTS.md`.
  Acceptance criteria (agent-executable): `tsc`, lint, build, focused pytest, brand scan, nav scan, and browser QA all pass or document pre-existing blockers with exact reason. Evidence directory includes screenshots/transcripts and final summary.
  QA scenarios (name the exact tool + invocation): happy `cd frontend && npx --no-install tsc --noEmit && npm run lint && npm run build`; happy `PYTHONPATH=. python3 -m pytest tests/test_listing_inventory_api.py -q`; happy `rg -n "text-gold|btn-gold|surface-1|text-sand|border-gold|bg-deep|ghost-border|shadow-gold|#C9A96E" frontend/src/app/'(app)'/listings frontend/src/components/listings frontend/src/components/viewings/ListingLogisticsForm.tsx` returns no matches; failure browser QA proves `/listings` never follows a link to `/dashboard/listings`. Evidence `.omo/evidence/dalya-listings-workspace-rebrand/task-12-final.json`
  Commit: Y | feat(listings): migrate agent inventory workspace

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit: verify every Must Have has evidence, Pass 2 did not block Pass 1, delivery tracking exists, and no criteria require Eric to manually inspect state.
- [ ] F2. Code quality review: audit changed API/frontend code for scoped payloads, route-backed navigation, type safety, no broad refactors, no destructive overwrite of dirty worktree changes, and no suppressed errors.
- [ ] F3. Real browser QA: drive `/listings`, `/listings/[id]`, `/knowledge`, `/logistics`, `/offers`, `/documents`, plus old-route redirects at 375/768/1280; compare screenshots to `DESIGN.md`.
- [ ] F4. Scope fidelity: verify the work did not drift into owner/admin/campaign redesign, full creation-flow refactor, production data, or legacy marketplace surfaces.

## Commit strategy
- Do not commit unless Eric explicitly authorizes commits or the execution mode does.
- Prefer atomic commits by wave:
  - `docs(design): add Dalya agent surface contract`
  - `feat(listings): add inventory health summary`
  - `feat(listings): add canonical listing workspace routes`
  - `feat(listings): build inventory command center`
  - `feat(listings): migrate listing workspace tabs`
  - `test(listings): cover inventory workspace behavior`
  - `chore(listings): redirect legacy listing routes`
  - `docs(listings): scope creation flow follow-up`
- Final commit footer if committed from this plan: `Plan: .omo/plans/dalya-listings-workspace-rebrand.md`

## Success criteria
- `/listings` feels like a real inventory command center, not a shallow table.
- Opening any listing stays inside `/listings/[id]` and canonical subroutes.
- Overview, knowledge, logistics, offers, and documents use the new light/slate Dalya design.
- Old `/dashboard/listings/*` routes redirect or are clearly compatibility-only.
- `/api/v1/listings/mine` supports listing health, activity, offers, viewings, missing facts, logistics, assigned agent, and next action without becoming a detail mega-payload.
- No gold/dark legacy classes remain in canonical listings routes or listing logistics component used by them.
- Search, filters, sort, row actions, loading, empty, and error states work on desktop and mobile.
- The create flow is not worsened; full route-backed creation cleanup is documented as Pass 2 unless it was required to unblock Pass 1.
- Typecheck, lint, build, focused API tests, brand scans, navigation scans, and browser QA pass or name exact pre-existing blockers.
