# Pass 2 Creation-Flow Follow-Up

## Objective

Package the Pass 2 follow-up for splitting listing creation into route-backed, agent-workspace creation steps without changing product source code in Pass 1. The goal is to make `/listings/new` creation easier to reason about, easier to QA, and consistent with the App Navigation Architecture rule that meaningful workflow decisions use browser-visible routes.

This artifact was written against the current dirty tree on 2026-06-24 after reading the current plan, draft, `DESIGN.md`, creation route files, `FinishedListingFlow.tsx`, `NewListingFlow.tsx`, and relevant `BACKLOG.md` entries. `BACKLOG.md` already references `DAL-203` and explicitly includes the Pass 2 creation-flow follow-up, so no backlog edit was needed.

## Non-Goals

- Do not refactor `FinishedListingFlow.tsx` in Pass 1 unless the creation flow blocks the listings workspace rebrand.
- Do not change product source code as part of this packaging task.
- Do not redesign owner/admin creation surfaces.
- Do not introduce new visual language outside the locked Dalya light/slate agent surface contract.
- Do not replace off-plan SPA upload behavior; preserve it while clarifying route ownership.

## Current State Verified

- `/listings/new` renders `NewListingFlow`.
- `/dashboard/listings/new` also renders `NewListingFlow` as a legacy-compatible entry.
- `/listings/new/portal` renders `FinishedListingFlow`.
- `/listings/new/manual` renders `ManualListingChoice`.
- `/listings/new/manual/off-plan` renders `SellerUpload`.
- `/listings/new/manual/finished` renders `FinishedListingFlow startManual`.
- `/listings/new/manual/ready` does not exist today.
- `FinishedListingFlow.tsx` is a 1,652-line client component that currently owns listing type and entry method state, portal scraping, ready/off-plan field state, image upload handling, supporting documents, DLD fee calculation, listing submit, supporting-document attachment, and success CTA routing.

## Route-Backed Creation Plan

### `/listings/new`

Purpose: choose the import path.

Behavior:
- Show two choices: portal import and manual upload.
- Link to `/listings/new/portal` and `/listings/new/manual`.
- Keep this as a small server page plus a small client-free chooser when possible.
- Legacy `/dashboard/listings/new` should redirect or compatibility-render to this canonical route after Pass 1 redirect policy is settled.

### `/listings/new/portal`

Purpose: paste Property Finder / Bayut URL, fetch a draft, and route to the correct review form.

Behavior:
- Own only portal URL entry, scrape status, and scrape error recovery.
- On successful scrape, normalize the draft into a shared creation draft shape.
- If the scraped listing is ready resale, continue to the ready review form state under `/listings/new/manual/ready` or a later explicit route such as `/listings/new/portal/ready`.
- If the scraped listing is off-plan, continue to the off-plan review path or hand off to the existing SPA-backed path only when a document upload is required.
- If scrape fails, offer a route-backed manual fallback instead of opening an in-component blank form.

### `/listings/new/manual`

Purpose: choose manual listing type.

Behavior:
- Link to `/listings/new/manual/ready` and `/listings/new/manual/off-plan`.
- Replace the current "Finished property" copy/link with "Ready property" terminology.
- Keep only choice UI here; no form state.

### `/listings/new/manual/ready`

Purpose: create ready-property resale inventory manually.

Behavior:
- Add this route as the canonical ready-property manual creation form.
- Move the current `FinishedListingFlow startManual` ready-property behavior here.
- Redirect or replace `/listings/new/manual/finished` so old links do not strand users. Recommended path: create `/ready`, then make `/finished` a temporary redirect to `/ready`.
- Keep the success CTA pointed at `/listings/[id]`.
- Preserve ready-property supporting document workflows: title deed, Ejari, service charge statement, NOC, valuation report, snagging report, mortgage documents, floor plans, building rules, and seller disclosure notes.

### `/listings/new/manual/off-plan`

Purpose: create off-plan inventory from SPA upload.

Behavior:
- Preserve the existing `SellerUpload` route as the off-plan manual entry point.
- Ensure off-plan creation copy remains SPA/payment-plan/NOC/handover specific.
- Do not force off-plan through ready-property document or fee controls unless the backend contract requires a shared submit model later.

## Component Extraction Boundaries

Split `FinishedListingFlow.tsx` by ownership, not by visual section alone:

- `creation/types.ts`: `ListingPropertyType`, `EntryMethod`, `Draft`, `AdditionalFee`, `ImageItem`, `SupportingDocumentItem`, select option types, and shared constants.
- `creation/new-listing-choice.tsx`: current `NewListingFlow`, `ManualListingChoice`, and `FlowCard`, with ready-property route terminology.
- `creation/portal-import-form.tsx`: portal URL input, `draft-from-url` call, scrape status/error, and draft normalization.
- `creation/ready-listing-form.tsx`: ready-property form shell, submit orchestration, success state, DLD fee, pricing, permit, brokerage/agent fields, and CTA to `/listings/[id]`.
- `creation/ready-listing-state.ts`: pure state initialization and mapping between draft/form state and `POST /api/v1/listings` payload.
- `creation/media-uploader.tsx`: image file handling, object URL lifecycle, preview grid, and removal actions.
- `creation/supporting-documents.tsx`: document upload/manual document controls, document type selection, document text extraction status, and attachment calls to `/api/v1/listings/{id}/documents`.
- `creation/fields.tsx`: reusable `Field`, `TextArea`, `SelectField`, segmented control, numeric/currency fields, month field, field labels, and tooltip behavior.
- `creation/formatters.ts`: `calculatePricePerSqft`, `calculatePercentageFee`, furnishing/developer normalization, month options, file size, formatted number parsing, document label/type helpers, and file-to-data-url utilities where not tied to React lifecycle.

Avoid extracting a generic mega "listing creation engine." The useful boundary is ready-property creation plus shared low-level form/media/document helpers. Off-plan can stay on `SellerUpload` until a separate Pass 2 slice decides whether it should share the same submit form.

## Risks

- Route state migration can accidentally drop scraped draft data if handoff between `/portal` and `/manual/ready` is not explicitly designed.
- `/finished` terminology exists in current routes and copy; replacing it with `/ready` needs a redirect or compatibility page to avoid breaking saved links.
- `FinishedListingFlow.tsx` currently contains object URL cleanup for image previews; moving media handling without preserving cleanup can leak object URLs during repeated uploads.
- Supporting documents are attached after listing creation; failures produce partial success. The extracted submit flow must preserve the current "listing created, document attach warning" behavior.
- Portal scrape ownership guardrails should be checked before publish work expands, because `BACKLOG.md` has a production guardrail item for scraped listings owned by other agents/brokerages.
- The current component allows off-plan selection inside the portal flow while manual off-plan uses `SellerUpload`; Pass 2 must decide whether portal off-plan review is supported or routed to SPA upload.

## Dependencies

- Pass 1 canonical listings route decision: `/listings/*` remains the active agent workspace, with `/dashboard/listings/*` compatibility only.
- Existing backend endpoints: `POST /api/v1/listings/draft-from-url`, `POST /api/v1/listings`, and `POST /api/v1/listings/{id}/documents`.
- Existing `SellerUpload` behavior for off-plan SPA upload.
- `DESIGN.md` route-backed workflow and light/slate design contract.
- `DAL-203` backlog tracking for the listings workspace migration and Pass 2 follow-up.

## Migration Order

1. Add `/listings/new/manual/ready` as a route that preserves current ready-property manual creation behavior.
2. Add a compatibility redirect or wrapper from `/listings/new/manual/finished` to `/listings/new/manual/ready`.
3. Update `ManualListingChoice` copy and links from finished-property terminology to ready-property terminology.
4. Extract shared field and formatting helpers from `FinishedListingFlow.tsx` with no behavior change.
5. Extract media upload handling and supporting-document handling with focused tests around object URL cleanup, document label/type mapping, and attach failure messaging.
6. Extract ready-property form state and submit mapping, preserving `POST /api/v1/listings` payload shape and DLD 4% buyer fee behavior.
7. Reduce `/listings/new/portal` to scrape and route handoff, then wire the scraped ready draft into the ready-property route.
8. Re-run route, build, lint, and browser QA across portal, manual ready, manual off-plan, and legacy finished redirect.

## Acceptance Criteria

- `/listings/new`, `/listings/new/portal`, `/listings/new/manual`, `/listings/new/manual/ready`, and `/listings/new/manual/off-plan` are all meaningful route-backed screens.
- `/listings/new/manual/finished` no longer owns the canonical ready-property form; it redirects or compatibility-renders to `/ready`.
- Browser Back returns from ready/off-plan choice to `/listings/new/manual`, and from manual/portal choice to `/listings/new`.
- Creating a ready listing manually still submits the same backend payload fields, adds the DLD 4% buyer fee, attaches supporting documents, and routes success to `/listings/[id]`.
- Portal scrape failure still gives a clear manual fallback without hiding the form in opaque component state.
- Off-plan manual creation still uses SPA upload and remains specific to payment plan, NOC, handover, and developer facts.
- No banned legacy classes or `#C9A96E` appear in new canonical creation routes.
- Tests or harnesses cover route existence, finished-to-ready compatibility, ready manual submit mapping, document attachment partial failure messaging, and portal scrape fallback.

## QA Plan

Commands:
- `npm --prefix frontend run build`
- `npm --prefix frontend run lint -- "src/components/listings/**/*" "src/app/(app)/listings/new/**/*"`
- Route scan: `find frontend/src/app/'(app)'/listings/new -maxdepth 4 -type f | sort`
- Brand scan: `rg -n "text-gold|btn-gold|surface-1|text-sand|border-gold|bg-deep|ghost-border|shadow-gold|#C9A96E" frontend/src/app/'(app)'/listings/new frontend/src/components/listings`

Browser scenarios:
- Desktop and mobile `/listings/new`: choices link to portal/manual.
- Desktop and mobile `/listings/new/manual`: choices link to ready/off-plan; Back works from each route.
- `/listings/new/manual/ready`: fill minimum valid ready-property form, add an image, add a manual supporting document, publish, and verify success CTA points to `/listings/[id]`.
- `/listings/new/manual/off-plan`: load SPA upload surface and verify copy remains off-plan specific.
- `/listings/new/portal`: successful scrape prefill path and scrape-failure manual fallback.
- `/listings/new/manual/finished`: verify redirect or compatibility behavior to `/ready`.

Artifacts:
- Save screenshots under `.omo/evidence/dalya-listings-workspace-rebrand/pass-2-creation-browser/`.
- Save command output JSON or text evidence under `.omo/evidence/dalya-listings-workspace-rebrand/pass-2-creation-verification.*`.

## Pass 1 Note

Pass 1 workspace rebrand does not refactor the creation flow unless a blocker is found. Based on this packaging audit, creation cleanup should remain Pass 2 follow-up work; no source-code blocker was found during this documentation task.
