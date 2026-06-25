# T5 Code Quality And Slop Audit

Verdict: NEEDS-FIX
codeQualityStatus: BLOCK
recommendation: REQUEST_CHANGES

Remediation note, 2026-06-24: T5 remediation addressed the listed code blockers in owned files by narrowing the listing index finite fields in `frontend/src/lib/queries.ts`, moving `primary_next_action` routing into `frontend/src/components/listings/listingIndexActions.ts` with an exported supported-action list and explicit switch cases, splitting label helpers into `listingIndexLabels.ts`, and keeping the wide table behind the `2xl` breakpoint. Evidence is recorded in `task-5-index.json`. The original review verdict above is preserved as the historical audit result; authenticated visual QA still must be rerun.

Scope reviewed:
- `frontend/src/app/(app)/listings/page.tsx`
- `frontend/src/components/listings/AgentListingsIndex.tsx`
- `frontend/src/components/listings/AgentListingsControls.tsx`
- `frontend/src/components/listings/AgentListingsTable.tsx`
- `frontend/src/lib/queries.ts` around `AgentListingSummary`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json`

Skill-perspective check:
- Ran: loaded `omo:programming` plus `references/typescript/README.md`.
- Ran: loaded `omo:remove-ai-slops`.
- Also loaded for UI audit context: `omo:frontend`, `references/design/README.md`, `references/perfection/README.md`, and root `DESIGN.md`.
- Programming perspective result: violates strict TypeScript/test discipline because finite backend values are widened to `string` and T5 has no behavior tests covering action/status mapping.
- Remove-ai-slops perspective result: no obvious legacy style slop, no `any`/assertion escape hatches in scoped listing components, but the implementation still has false-confidence risk from missing tests and two files in the 200-250 pure LOC warning band.

## Findings

### CRITICAL

None.

### HIGH

1. Missing behavioral regression coverage for the inventory action contract.

   Backend inventory emits finite `primary_next_action` values, including `follow_up_buyers` at `app/api/listing_inventory.py:210-221`. The table maps these values in `frontend/src/components/listings/AgentListingsTable.tsx:221-237`, and the index counts any non-`open_listing` value as attention in `frontend/src/components/listings/AgentListingsIndex.tsx:144-150`.

   The known gate blocker is fixed in the current file state: `frontend/src/components/listings/AgentListingsTable.tsx:234-235` now maps `follow_up_buyers` to `Follow up buyers` on `/listings/<id>`. However, this exact issue passed the static gates before review because there is no test that checks every backend action value has an explicit UI mapping. My search found no T5-specific tests for `AgentListingsIndex`, `AgentListingsControls`, `ListingsTable`, `useAgentListings`, `primary_next_action`, or `follow_up_buyers`.

   Required before approval: add a focused regression test or contract test that fails when a backend `primary_next_action` value is not explicitly represented by the UI route/label mapping.

2. The listing summary contract is too weak for the values the UI branches on.

   `frontend/src/lib/queries.ts:96-102` types `knowledge_status`, `logistics_status`, and `primary_next_action` as plain `string`; `frontend/src/lib/queries.ts:87` types `status` as `'live' | 'draft' | string`. That prevents exhaustive handling and allowed the prior `follow_up_buyers` omission to compile. A concrete current inconsistency remains: `frontend/src/components/listings/AgentListingsTable.tsx:146` labels every non-`live` status as `Draft`, while `frontend/src/components/listings/AgentListingsIndex.tsx:111-114` only includes exact `draft` values in the Draft filter. If the API returns any other allowed string, the row can be displayed as Draft but not match the Draft filter.

   Required before approval: narrow these API-facing fields to explicit unions or parse them into explicit UI-safe variants, then use exhaustive handling for branch logic that drives labels, filters, and routes.

### MEDIUM

1. Component/file size is close to the programming threshold.

   Pure LOC results:
   - `AgentListingsIndex.tsx`: 217
   - `AgentListingsControls.tsx`: 150
   - `AgentListingsTable.tsx`: 248
   - Combined scoped components: 615

   `AgentListingsIndex.tsx` and `AgentListingsTable.tsx` are in the 200-250 warning band. `AgentListingsTable.tsx` is especially risky at 248 pure LOC and owns desktop table rendering, mobile cards, field formatters, badges, status display, and next-action routing. Any non-trivial follow-up can push it over the 250 LOC defect threshold unless lines are removed or responsibilities are split.

2. Operational UI completeness is only statically verified.

   Static read confirms the route renders the index (`page.tsx:1-5`), includes summary metrics and loading/error/empty/no-results states (`AgentListingsIndex.tsx:45-76`, `193-240`), includes search/filter/sort controls (`AgentListingsControls.tsx:44-92`), and exposes table/mobile rows with agent, buyer, readiness, pipeline, activity, and next action fields (`AgentListingsTable.tsx:7-88`). The task evidence still states authenticated visual browser QA was not completed and `/listings` was only checked as an unauthenticated redirect in `.omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json:148-151`. This does not prove responsive layout, text fit, focus/hover behavior, or authenticated data rendering.

### LOW

1. Evidence artifact is transparent about limitations, but acceptance claims rely on non-visual checks.

   `.omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json` now records the `follow_up_buyers` remediation and the lack of authenticated visual QA. This is not misleading in the current version, but it is not enough evidence to claim the UI has been exercised as an agent would use it.

2. Helper abstraction review found no deletion-only tests, tautological tests, legacy gold/dark tokens, or obvious one-off production abstractions in the scoped listing components.

## Code-Quality Checklist

- Strict `any`/assertion escape hatches: PASS for scoped component scan; no `any`, ` as `, `@ts-ignore`, `@ts-expect-error`, non-null assertion scan hits, or legacy route/style hits.
- Type discipline: NEEDS-FIX for widened finite strings in `AgentListingSummary`.
- Exhaustive action/status handling: NEEDS-FIX; current `follow_up_buyers` branch exists, but the compiler cannot enforce coverage of future/current backend variants.
- File size: WATCH; `AgentListingsTable.tsx` is 248 pure LOC and `AgentListingsIndex.tsx` is 217 pure LOC.
- Helper/function complexity: WATCH; table component combines desktop rendering, mobile rendering, formatting, badges, and action mapping.
- One-off abstractions: PASS; local helpers are small or reused enough to be reasonable.
- Canonical links: PASS for scoped scan; no `/dashboard/listings` matches, and current links target `/listings/*`.
- Operational UI states: PASS by static source inspection for loading/error/empty/no-results, but WATCH because authenticated visual QA is missing.
- Tests: NEEDS-FIX; no T5 behavior test coverage found.

## Slop / Overfit / Misleading Evidence Audit

- Deletion-only tests: none found.
- Tests that merely verify removal: none found.
- Tautological implementation-mirroring tests: none found because no relevant tests were found.
- Tests that only mirror constants: none found.
- Needless production extraction/parsing/normalization: none identified in scoped listing components.
- Over-defensive code: no obvious redundant null checks in scoped components beyond nullable API display handling.
- Misleading success output: current evidence does not claim lint passed repo-wide; it records unrelated lint blockers and separately records scoped lint. It also records missing visual QA. The remaining risk is false confidence from static-only verification.

## Exact Command Results

Command:

```bash
awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(\/\/|#|--)/' frontend/src/components/listings/AgentListingsIndex.tsx frontend/src/components/listings/AgentListingsControls.tsx frontend/src/components/listings/AgentListingsTable.tsx | wc -l
```

Exit code: 0

```text
     615
```

Per-file equivalents:

```bash
awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(\/\/|#|--)/' frontend/src/components/listings/AgentListingsIndex.tsx | wc -l
```

```text
     217
```

```bash
awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(\/\/|#|--)/' frontend/src/components/listings/AgentListingsControls.tsx | wc -l
```

```text
     150
```

```bash
awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(\/\/|#|--)/' frontend/src/components/listings/AgentListingsTable.tsx | wc -l
```

```text
     248
```

Command:

```bash
rg -n "any| as |@ts-ignore|@ts-expect-error|!\.|/dashboard/listings|text-gold|btn-gold|surface-1|text-sand|border-gold|bg-deep|ghost-border|shadow-gold|#C9A96E" frontend/src/components/listings/AgentListingsIndex.tsx frontend/src/components/listings/AgentListingsControls.tsx frontend/src/components/listings/AgentListingsTable.tsx frontend/src/app/'(app)'/listings/page.tsx || true
```

Exit code: 0

```text
<no output>
```

Command:

```bash
cd frontend && npx --no-install eslint src/components/listings/AgentListingsIndex.tsx src/components/listings/AgentListingsControls.tsx src/components/listings/AgentListingsTable.tsx
```

Executed with working directory `/Users/eric/dalya-ai/frontend` as:

```bash
npx --no-install eslint src/components/listings/AgentListingsIndex.tsx src/components/listings/AgentListingsControls.tsx src/components/listings/AgentListingsTable.tsx
```

Exit code: 0

```text
<no output>
```

Additional verification:

```bash
npx --no-install tsc --noEmit
```

Working directory: `/Users/eric/dalya-ai/frontend`

Exit code: 0

```text
<no output>
```

```bash
rg -n "follow_up_buyers" frontend/src/components/listings/AgentListingsTable.tsx app/api/listing_inventory.py .omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json
```

Exit code: 0

```text
.omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json:59:      "scenario": "T5 gate blocker remediation - follow_up_buyers next action mapping",
.omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json:60:      "invocation": "rg -n \"follow_up_buyers|/dashboard/listings\" frontend/src/components/listings/AgentListingsTable.tsx",
.omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json:62:      "observable": "Matched only AgentListingsTable.tsx:234 follow_up_buyers; no /dashboard/listings match. The action now routes to /listings/<id> with label Follow up buyers.",
.omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json:137:      "result": "Primary action maps to /knowledge, /logistics, /offers, /documents, or /listings/<id>. The gate-blocking follow_up_buyers action now maps to /listings/<id> with label Follow up buyers because there is no canonical buyers subroute. Scoped /dashboard/listings scan returned no matches."
.omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json:155:    "gate_blocker_remediation": "Independent gate found backend primary_next_action follow_up_buyers counted as attention by AgentListingsIndex but falling through to Open listing in AgentListingsTable. Fixed AgentListingsTable.nextAction to return label Follow up buyers, icon forum, and canonical /listings/<id> route; no /dashboard/listings route was introduced.",
app/api/listing_inventory.py:219:        primary_next_action = "follow_up_buyers"
frontend/src/components/listings/AgentListingsTable.tsx:234:  if (listing.primary_next_action === 'follow_up_buyers') {
```

```bash
rg -n "AgentListingsIndex|ListingsTable|AgentListingsControls|useAgentListings|primary_next_action|follow_up_buyers" frontend/src --glob '*.{test,spec}.{ts,tsx}' --glob '*__tests__*'
```

Exit code: 1

```text
<no output>
```

```bash
jq empty .omo/evidence/dalya-listings-workspace-rebrand/task-5-index.json
```

Exit code: 0

```text
<no output>
```

## Blockers

- Add behavioral coverage for `primary_next_action` UI mapping so every backend-emitted action, including `follow_up_buyers`, has a tested route/label outcome.
- Tighten `AgentListingSummary` finite fields, especially `primary_next_action` and `status`, so route, label, attention, and filter logic can be handled exhaustively instead of falling through plain `string`.
