# T2 Design Contract Evidence

## Scope

- Plan task: T2, create the practical Dalya agent `DESIGN.md` contract.
- Changed files: `DESIGN.md`, `.omo/evidence/dalya-listings-workspace-rebrand/task-2-design-contract.md`.
- Product source files changed: none.
- Plan checkbox changed: no.

## Baseline Gap

Baseline command:

```bash
omo sparkshell --shell 'test -f DESIGN.md && rg -n "Listings workspace|No gold|Slate|Inter|tabular|route-backed|text-gold|btn-gold|surface-1" DESIGN.md || true' --budget 20000
```

Result: exit 0. The existing file contained broad brand/design-system content and matched some generic terms such as `Inter`, `tabular`, and slate references, plus legacy class names. It did not provide a concise listings-specific implementation contract with the required route-backed listings workspace rules, visual QA checklist, and explicit practical guardrails for new agent/listings surfaces.

Pre-edit dirty status for the allowed files:

```text
git status --short -- DESIGN.md .omo/evidence/dalya-listings-workspace-rebrand/task-2-design-contract.md
```

Result: no output; both scoped files were clean or absent before this task.

## References Read

Read through `omo sparkshell` before editing:

- `brand/BRAND.md`
- `brand/applications/_tokens.css`
- `frontend/src/app/globals.css`
- `frontend/src/components/agent-dashboard/TodayQueue.tsx`
- `frontend/src/components/app/AppSidebar.tsx`
- `frontend/src/app/(app)/layout.tsx`

Observed implementation anchors:

- Brand docs and tokens set light default surfaces, slate brand colors, sage/copper/brick status colors, 8px workhorse radius, and Inter tabular numerals for AED values.
- `globals.css` still exposes legacy global utilities including `btn-gold`, `surface-1`, `ghost-border`, and `shadow-gold`, so the contract needs to ban their use in new agent surfaces while source migration proceeds separately.
- Agent chrome components use `bg-white`, `bg-neutral-50`, `border-neutral-200`, `rounded-md`, `brand-*`, and status semantic colors, matching the desired light/slate operations UI.

## DESIGN.md Changes

Replaced the existing broad design-system note with a short implementation contract:

- `Non-Negotiables`: light surfaces, Slate CTAs, banned legacy class/token list, 8px operational radius, Inter/tabular AED values, dense calm operations UI, and sage/copper/brick/slate status palette.
- `Tables And Cards`: desktop table and mobile card rules, stable dimensions, and no nested cards.
- `Route-Backed Workflows`: route-backed workflow requirement and limits on page-level component step state.
- `Listings Workspace`: canonical `/listings` route contract, required inventory fields, shared header/tabs, no canonical `/dashboard/listings/*` actions, and documents route expectations.
- `Visual QA Requirements`: desktop/tablet/mobile widths, artifact capture, banned legacy scan, overflow/focus/status/link checks.

## Verification Results

Command 1:

```bash
omo sparkshell --shell 'test -f DESIGN.md && rg -n "Listings workspace|No gold|Slate|Inter|tabular|route-backed" DESIGN.md' --budget 20000
```

Result: exit 0. Matches:

- line 13: `Slate` CTA/action color rule.
- line 14: `No gold/dark legacy classes` plus banned list.
- line 16: `Inter` and `tabular-nums` rule for AED values.
- line 29: `route-backed` workflow rule.
- line 35: `Listings workspace` canonical route contract.
- line 37: `route-backed` tabs in the shared workspace header.

Command 2:

```bash
omo sparkshell --shell '! rg -n "luxury|premium|opulent|gold as primary" DESIGN.md' --budget 20000
```

Result: exit 0 with no matches.

Command 3:

```bash
omo sparkshell --shell 'rg -n "text-gold|btn-gold|surface-1|text-sand|border-gold|bg-deep|ghost-border|shadow-gold|#C9A96E" DESIGN.md' --budget 20000
```

Result: exit 0. Matches:

- line 14: full banned legacy class/token list.
- line 45: visual QA scan requirement for `#C9A96E`.

Stale-state check: re-read `DESIGN.md` after editing and confirmed the required terms and sections exist in the saved file.

Post-edit dirty status for the allowed files before final diff check:

```text
 M DESIGN.md
?? .omo/evidence/dalya-listings-workspace-rebrand/task-2-design-contract.md
```

## Canonical Listings Protection

The contract prevents legacy branding on canonical listings routes by requiring all new listings actions and links to target `/listings/*`, banning the legacy class/token list in new agent surfaces, and making a brand scan for those banned classes plus `#C9A96E` part of visual QA before a route can be claimed migrated.

## Adversarial QA

- `dirty_worktree`: applicable. Pre-edit status was clean/absent for scoped files; post-edit status shows only the two allowed files.
- `stale_state`: applicable. Re-read `DESIGN.md` after edit and verified the required terms in saved content.
- `misleading_success_output`: applicable. Recorded grep match summaries with line numbers instead of pass/fail only.
- `generated_or_cached_artifacts`: not applicable except this evidence file; no generated runtime artifacts.
- `malformed_input`: not applicable; no parser input.
- `prompt_injection`: not applicable; only local trusted project reference files were read.
- `cancel/resume`: not applicable; short documentation task.
- `long_external_commands`: not applicable; commands were short local grep/read checks.
- `flaky_tests`: not applicable; deterministic grep/diff checks only.
- `repeated_interruptions`: not applicable; no interruption occurred.

## Cleanup Receipt

No servers, processes, ports, temp directories, or generated runtime artifacts were created. Cleanup receipt: none needed.
