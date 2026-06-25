# Dalya T8 Code Quality Review

## Skill-Perspective Check

- `omo:remove-ai-slops`: loaded and applied as a read-only overfit/slop pass. No deletion-only or tautological tests were added in this slice. Violations found: mocked browser QA payload does not match the real API shape, creating false confidence; logistics form remains in the 200-250 pure LOC warning band.
- `omo:programming`: loaded with the TypeScript reference. `tsc --noEmit` and scoped ESLint pass; no scoped `any`, `as any`, `as unknown`, `@ts-ignore`, or non-null assertions found. Violation found: hand-written TypeScript API types drift from the real backend serializer for knowledge summary signals.
- `omo:frontend`: loaded for UI/design review, with `DESIGN.md` consulted. Scoped legacy-token and stale-dashboard-link scans are clean, but browser visual QA artifacts are absent for the changed UI routes.

## CRITICAL

None.

## HIGH

1. **Knowledge summary crashes against the real API shape.**
   - `frontend/src/components/listings/ListingKnowledgeTypes.ts:24` types `missing_information` and `risk_flags` as `readonly string[]`.
   - `frontend/src/components/listings/ListingKnowledgeSummaryPanel.tsx:23` and `frontend/src/components/listings/ListingKnowledgeSummaryPanel.tsx:24` pass those arrays directly to `SignalList`.
   - `frontend/src/components/listings/ListingKnowledgeSummaryPanel.tsx:29` and `frontend/src/components/listings/ListingKnowledgeSummaryPanel.tsx:36` render each item as a React child.
   - The backend builds those fields as arrays of objects in `app/core/ready_property_knowledge.py:313` and `app/core/ready_property_knowledge.py:324`, and serializes them unchanged in `app/api/listings.py:237` and `app/api/listings.py:238`.
   - Impact: real knowledge summaries with missing facts or risk flags will render objects as React children, producing a runtime error instead of the canonical `/listings/[id]/knowledge` workspace. This blocks T8 acceptance for adapted useful content.

## MEDIUM

1. **Browser QA evidence is insufficient and its fixture masks the HIGH bug.**
   - `.omo/evidence/dalya-listings-workspace-rebrand/task-8-browser-qa/run-t8-browser-qa.mjs:112` and `.omo/evidence/dalya-listings-workspace-rebrand/task-8-browser-qa/run-t8-browser-qa.mjs:113` stub `missing_information` and `risk_flags` as strings, unlike the backend object arrays.
   - The `task-8-browser-qa` directory currently has no screenshots, transcript JSON, or `manualQa.json`; it only contains the harness, cleanup receipt, and a redirect curl artifact.
   - Impact: focus, overflow, loading/error/empty state claims remain mostly static-code assertions, not rendered-route evidence.

2. **Logistics form can overwrite unsaved edits on query refetch.**
   - `frontend/src/components/viewings/ListingLogisticsForm.tsx:37` through `frontend/src/components/viewings/ListingLogisticsForm.tsx:43` copy server data into local form state on every `data` object change.
   - `useListingLogistics` uses React Query defaults, so a focus/reconnect/refetch while an agent is editing can reset `access`, `keys`, `tenant`, and `owner` fields without a dirty-state guard.
   - Impact: possible user data loss in the logistics workflow. This appears pre-existing in the touched form, but T8 still depends on this form for `/listings/[id]/logistics`.

## LOW

1. **`ListingLogisticsForm.tsx` is close to the file-size threshold and carries dynamic form-state slop.**
   - Measured pure LOC: `frontend/src/components/viewings/ListingLogisticsForm.tsx` = 243.
   - The file remains under the 250 pure LOC hard ceiling, but it combines route data hydration, save mutation, four subforms, field widgets, and normalization helpers. Next functional edit should split it by responsibility before adding more logic.

## Checks Run

- `npx --no-install tsc --noEmit` from `frontend`: PASS.
- `npx eslint <scoped T8 files> --max-warnings=0` from `frontend`: PASS.
- `npm run lint -- --max-warnings=0` from `frontend`: FAIL on pre-existing out-of-scope files (`ConversationDetail.tsx`, `EscalationInbox.tsx`, `SellerUpload.tsx`, `InspectionAudioInput.tsx`, plus warnings). No scoped T8 failures.
- Legacy token scan on scoped T8 files: PASS, empty output.
- `/dashboard/listings` scan on scoped T8 files: PASS, empty output.
- `git diff --check` on scoped T8 files and evidence JSON: PASS, empty output.
- Pure LOC check: route pages 10 each; `ListingKnowledgeWorkspace.tsx` 218; facts panel 72; source panels 79; summary panel 44; types 56; logistics workspace 26; offers workspace 145; logistics form 243.
- LSP diagnostics: unavailable; TypeScript LSP is not installed and was previously declined.

## Residual Risk

- The scoped pages and components are mostly untracked in the current worktree, so diff-based review cannot distinguish all T8 work from earlier untracked listing-workspace work.
- Full authenticated browser QA was not available from the provided artifacts.

## Verdict

- `codeQualityStatus`: BLOCK
- `recommendation`: REQUEST_CHANGES
- `blockers`: Fix the knowledge summary API/UI contract mismatch before approval.
