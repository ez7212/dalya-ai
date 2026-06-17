# Phase 2 — Lock

*Locked: 2026-05-14 by Eric. All four decisions below accepted. Phase 3 (application examples) is unblocked.*

## Status: locked

| Decision | Locked outcome |
|---|---|
| Brand-600 for top-tier CTAs | ✅ Locked. `#324B6B` introduced as `brand-600`, reserved for 3–5 top-priority CTAs across the entire product (Upload SPA, Accept Offer, Send to Eric, Confirm Destructive). brand-500 carries everything else (links, focus rings, selected states, secondary primaries, wordmark, brand thread). |
| 8px grid → 4px hybrid | ✅ Locked. 4px base scale with 5 reserved 4px-only steps (form input padding, compact table rows, icon-in-pill, avatar-name, small ornament). Code review must justify use of the 4px-only steps. Default authoring guidance remains 8px-multiple. |
| Light default → `prefers-color-scheme` + sticky toggle | ✅ Locked. Most users get light. Users with OS dark preference get dark. Persistent per-user toggle overrides both. This amends Phase 1's "light-default everywhere" lock; the broader user model (especially brokerage owners doing sustained data work) justifies the amendment. |
| Dubai-functional voice | ✅ Locked. Quiet-by-omission applies to *decoration* (no ornament, no exoticization). Voice keeps Dubai-market vocabulary as functional language: off-plan resale, Trakheesi permit, NOC threshold, trustees office, 0.15% commission, RERA-licensed, Mahoroba Realty. Per `08-voice-tone.md` §5. |

---

This document also surfaces the open follow-ups Phase 3 inherits, and the items still needing your confirmation before Phase 3 starts.

---

## Documents shipped in Phase 2

| File | Owner | Pages (lines) | Status |
|---|---|---|---|
| [`05-surface-spacing.md`](./05-surface-spacing.md) | UX Architect | ~28 pp (1076 lines) | ✅ Complete |
| [`06-components.md`](./06-components.md) | UI Designer (me, after agent timeouts) | ~24 pp (915 lines) | ✅ Complete |
| [`07-motion.md`](./07-motion.md) | UI Designer (me, after agent timeouts) | ~8 pp (310 lines) | ✅ Complete |
| [`08-voice-tone.md`](./08-voice-tone.md) | Brand Guardian (me, after agent timeouts) | ~13 pp (508 lines) | ✅ Complete |

Combined Phase 2 output: ~2,800 lines of operational direction.

---

## Decisions — all locked (2026-05-14)

### Decision 1 — Brand-600 for top-tier CTAs ✅

Locked: `#324B6B` introduced as `brand-600`. Reserved for top-priority CTAs only — Upload SPA, Accept Offer, Send to Eric, Confirm Destructive. 3–5 surfaces across the entire product.

`brand-500` (`#3D5A80`) keeps everything else: secondary primary buttons, links, focus rings, selected states, wordmark, brand thread accents.

### Decision 2 — 4px hybrid spacing grid ✅

Locked. The 4px base scale with 8px-multiple authoring convention is the working system. Five reserved 4px-only steps require code-review justification (form input padding, compact table rows, icon-in-pill gap, avatar-name gap, small ornament gaps).

Phase 1's "8px grid" instruction is amended.

### Decision 3 — `prefers-color-scheme` + sticky toggle ✅ (deferred re-enable)

Locked in principle. Production cascade order:
1. User's persistent in-app toggle (highest priority — sticky per Supabase user_metadata).
2. `prefers-color-scheme` (OS preference) if no in-app override exists.
3. Light fallback if neither resolves.

**Phase 3 build amendment (2026-05-14):** Eric is building Phase 3 application examples in light mode only. The `prefers-color-scheme` auto-switch is commented out in `applications/_tokens.css` so mockups render predictably regardless of the reviewer's OS theme. The `[data-theme="dark"]` block remains in the file but does not fire unless explicitly set.

Re-enable + audit dark mode against finished mockups after Phase 3 lock. The dark-mode token values stay parked in the same file.

### Decision 4 — Dubai-functional voice ✅

Locked. Visual quiet-by-omission stands (no decorative ornament). Voice keeps Dubai-market vocabulary as functional language. See `08-voice-tone.md` §5 for the locked required-phrase list.

---

## Open follow-ups Phase 3 needs to address

Documented in the relevant Phase 2 files; surfaced here for visibility:

1. **Empty-state illustrations** — Phase 2 ships without them. Phase 3 may add them. Decision deferred.
2. **Iconography library** — Cultural Intelligence specified directional icons should have logical variants for RTL. Library choice still open. Recommend phosphor-icons or lucide for the consistency + RTL story.
3. **Wordmark working-size variants** — Cultural Intelligence flagged that the existing wordmark at marketing size may not survive 14px in a sidebar. Phase 3 needs a sidebar-sized Arabic + Latin wordmark variant.
4. **Per-route layouts** (login, signup, settings, admin sub-pages) — deferred to Phase 3.
5. **Wizard flows** (SPA upload, offer acceptance, listing creation) — deferred to Phase 3.
6. **Marketing site components** — deferred to Phase 3.

---

## Linting infrastructure to ship alongside Phase 3

Recommended in `08-voice-tone.md` §9. Three pieces:

1. A grep-based linter against the banned phrase list in `08-voice-tone.md` §4. PR-blocking on match.
2. A PR template checklist baked into the repo's `.github/PULL_REQUEST_TEMPLATE.md` that prompts the voice review checklist (§8 of `08`) for any UI-string change.
3. A localization brief that defines the equivalent of §4/§5 for Arabic, Russian, Hindi as those surfaces ship.

These are not Phase 2 deliverables but enforce the work Phase 2 produced.

---

## Tokens locked in Phase 2

For engineering reference, the complete frozen token set from Phase 2:

From `05-surface-spacing.md`:
- All spacing scale tokens (`--space-0` through `--space-96`)
- All surface tokens (`surface-0`/`1`/`2`/`overlay` + dark mode equivalents)
- All border tokens (`border-hairline`/`default`/`strong`)
- All radius tokens (`radius-0/4/8/12/16/full`)
- All shadow tokens (overlay-only)
- Focus ring tokens
- Z-index scale (7 steps)
- Density mode tokens

From `06-components.md`:
- Button height tokens (`--button-height-md`/`md-compact`/`sm`/`lg`)
- Input height tokens (`--input-height-md`/etc.)
- Row height tokens (`--row-height-comfortable`/`compact`/`display`)
- Card padding tokens (`--card-padding`/`compact`/`display`)
- Card section gap tokens

From `07-motion.md`:
- Duration tokens (`--duration-instant`/`fast`/`base`/`medium`/`slow`)
- Easing tokens (`--ease-out`/`in`/`out-quart`/`in-quart`/`out-back`)
- Three keyframes (`pulse-skeleton`/`pulse-dot`/`progress-indeterminate`)

Tokens explicitly kept *free* until Phase 3 (per pushback 0.2 in `06`):
- Per-component intra-padding for individual modal types, toast types
- Conversation bubble dimensions (content-shape-dependent)
- Table column-priority order per route (can only be specified per-table in Phase 3)
- Empty-state illustration handling

---

## Phase 3 prerequisites

Before Phase 3 (application examples) launches:

1. Lock or defer the four decisions above.
2. Confirm wordmark size-variant question (see open follow-up #3).
3. Confirm whether marketing specialists are in or out of scope (Phase 1 deferred them — confirm).

Once locked, Phase 3 produces:
- Agent working surface — desktop + mobile
- Brokerage owner dashboard — desktop
- Listing detail view — desktop + mobile
- Buyer conversation view — desktop (inside agent surface) + the bot's view that the buyer sees on WhatsApp
- Login + signup + auth screens
- Marketing site (homepage, how-it-works, about, signed-out states)

Phase 3 is the test of every system Phase 1 and 2 produced. Expect Phase 2 token adjustments after the first 5–8 routes meet real content.
