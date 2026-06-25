---
slug: dalya-listings-workspace-rebrand
status: approved
intent: clear
pending-action: execute only after explicit start-work or LazyCodex handoff
approach: Pass 1 makes /listings the canonical light/slate Dalya agent inventory workspace, with /listings/[id] route-backed detail tabs and legacy /dashboard/listings redirects. Pass 2 creation-flow cleanup is captured as follow-up unless the existing create flow blocks Pass 1 usability.
---

# Draft: dalya-listings-workspace-rebrand

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->
| C1 Design contract | `DESIGN.md` exists as a short implementation contract for new agent surfaces: light default, slate CTAs, no gold/dark luxury classes, Inter/tabular numerals, dense operational UI. | active | .omo/evidence/dalya-listings-workspace-rebrand/design-contract.md |
| C2 Inventory API | `/api/v1/listings/mine` supports only index-level operational fields needed for listing health, activity, offers, viewings, knowledge, logistics, assigned agent, and next action. | active | .omo/evidence/dalya-listings-workspace-rebrand/api-contract.json |
| C3 Listings index | `/listings` becomes an inventory command center with search, filters, sort, health/next-action columns, mobile cards, and links only to canonical `/listings/*` routes. | active | .omo/evidence/dalya-listings-workspace-rebrand/index-browser/ |
| C4 Listing workspace | `/listings/[id]` and subroutes share a `ListingWorkspaceShell` with breadcrumb, header, health badges, tabs, and next action in the new light/slate system. | active | .omo/evidence/dalya-listings-workspace-rebrand/workspace-browser/ |
| C5 Legacy redirects | Old `/dashboard/listings/*` routes redirect or wrap compatibly into canonical `/listings/*` without leaving users in old dark/gold UI. | active | .omo/evidence/dalya-listings-workspace-rebrand/redirects.json |
| C6 Creation flow cleanup | Split `FinishedListingFlow.tsx` and make creation substeps route-backed as Pass 2 follow-up, not a Pass 1 blocker unless current create flow prevents basic listing creation. | deferred | .omo/evidence/dalya-listings-workspace-rebrand/pass-2-creation-followup.md |

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->
| Execution scope | Pass 1 is required; Pass 2 is follow-up planning/ticketing only unless creation breaks `/listings` usability. | User explicitly said not to let Pass 2 block Pass 1. | yes |
| Canonical detail route | Use `/listings/[id]/documents` instead of `/spa`; show SPA-specific sections inside documents when applicable. | Ready listings may not have SPA context. | yes |
| API split | Extend `/api/v1/listings/mine` for index-level data only; add or reuse a separate detail payload for listing workspace data. | Prevents index API bloat and keeps table fast. | yes |
| Visual target | Match current `/agent` light/slate operational patterns rather than inventing a new listings-specific style. | The listings page is part of the agent daily workspace. | yes |
| Icon system | Continue existing Material Symbols for this pass; do not introduce a new icon library. | App shell already uses Material Symbols heavily; icon migration is out of scope. | yes |
| Tracking | Create/attach one Linear issue before implementation if available; if Linear is blocked, record one umbrella item in `BACKLOG.md` and continue. | Project requires delivery tracking, but first pass should not create ticket sprawl. | yes |

## Findings (cited - path:lines)
- `brand/BRAND.md`: brand attributes are Trustworthy, Calm, Sharp; gold is fully retired; light/default B2B agent surfaces should use slate blue `#3D5A80` and deeper slate `#324B6B`.
- `frontend/src/app/globals.css`: B2B tokens exist but legacy gold/dark tokens and classes (`btn-gold`, `surface-1`, `text-gold`, etc.) remain for older dashboard surfaces.
- `frontend/src/app/(app)/listings/page.tsx`: `/listings` currently delegates entirely to `AgentListingsIndex`.
- `frontend/src/components/listings/AgentListingsIndex.tsx`: current page has a header, four metrics, loading/error/empty states, and table only; it does not yet answer which listings need agent attention.
- `frontend/src/components/listings/AgentListingsTable.tsx`: current table links listing rows to `/dashboard/listings/${id}`, which punts users into legacy Mahoroba dashboard routes.
- `frontend/src/app/(app)/dashboard/listings/[id]/layout.tsx`: listing detail shell uses old `/dashboard/listings` paths and legacy `text-gold`, `text-sand`, and `border-gold` styling.
- `frontend/src/app/(app)/dashboard/listings/[id]/page.tsx`, `knowledge/page.tsx`, `offers/page.tsx`, `spa/page.tsx`, and `frontend/src/components/viewings/ListingLogisticsForm.tsx`: listing detail subpages still contain dark/gold legacy styling.
- `app/api/listing_inventory.py`: `/listings/mine` exists and returns list-level fields: id, title, property type, location, price, lead/escalation counts, image, document count, and created date.
- `frontend/src/lib/queries.ts`: `AgentListingSummary` and `AgentListingsResponse` mirror the current lean index payload and will need additive fields for operational health.
- `frontend/src/components/listings/FinishedListingFlow.tsx`: creation flow is a 1,652-line client component; splitting it belongs in Pass 2 unless it blocks Pass 1.
- Dirty worktree note: the listings files and API inventory file are already modified/untracked locally. Executors must not revert or overwrite unrelated user/LazyCodex changes.

## Decisions (with rationale)
- Use `/listings` and `/listings/[id]` as canonical agent inventory routes. `/dashboard/listings/*` becomes redirect/compatibility only.
- Use `/listings/[id]/documents` as the canonical documents route, not `/spa`. SPA data remains a section/state within documents for off-plan listings.
- Build a shared `ListingWorkspaceShell` so overview, knowledge, logistics, offers, and documents share header/tabs/status/next-action treatment and cannot drift back to old styling independently.
- Keep `/api/v1/listings/mine` lean and additive. Index rows get operational summary fields; detail tabs use dedicated detail endpoints or existing per-tab endpoints.
- Visual QA is required before completion: desktop, tablet, and mobile screenshots for `/listings` and at least one listing workspace route.
- Pass 2 creation cleanup is not required for Green unless current create flow breaks add-listing entry or canonical navigation.

## Scope IN
- Create `DESIGN.md` as a practical implementation contract for Dalya agent surfaces.
- Upgrade `/listings` inventory page with search, filters, sort, health, next action, and responsive table/cards.
- Add canonical `/listings/[id]` workspace shell and route-backed subpages for overview, knowledge, logistics, offers, and documents.
- Migrate the most important existing listing detail content into light/slate styling.
- Add redirects or compatibility wrappers from old `/dashboard/listings/*` to canonical routes.
- Extend backend and frontend listing summary types only where needed for index-level data.
- Add focused backend/frontend tests and browser QA evidence.

## Scope OUT (Must NOT have)
- No full rewrite of listing creation flow in Pass 1.
- No broad owner dashboard or legacy admin surface redesign.
- No new visual language beyond the Dalya B2B brand tokens.
- No gold/dark luxury classes in canonical `/listings` routes.
- No API mega-payload that loads all documents/offers/logistics into the index.
- No live customer data or production DB assumptions for verification.
- No route state replacing meaningful page navigation.

## Open questions
- None blocking. User approved the tightened direction. Default choices above are reversible if Eric changes direction before execution.

## Approval gate
status: approved
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->
Approved by Eric in-thread on 2026-06-24. Pending action: execute this plan only after an explicit start-work command.
