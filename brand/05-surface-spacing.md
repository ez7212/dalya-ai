# 05 — Surface & Spacing System (Phase 2)

*Owner: UX Architect*
*Scope: the foundation the component direction (`06-components.md`) hangs off of. Spacing scale, surface elevation, borders, radii, shadows, focus rings, density rules, layout primitives, z-index, RTL, dark-mode strategy, Tailwind v4 implementation, mobile fallbacks.*
*Coordinates with: `02-color-direction.md` (color tokens are upstream of every section below), `03-typography-direction.md` (font scale interacts with density), `06-components.md` (component behavior — out of scope here; surface tokens specified here).*
*Status: Draft 1 — prescriptive. Two specific pushbacks against Phase 1 locks in §0.*

---

## 0. Two pushbacks against the Phase 1 locks

The brief mandates focused pushback on two specific decisions. Both are real. Eric should read these before §1.

### 0.1 The 8px grid is wrong for this product. Recommend 4px-base with 4/8 hybrid rules.

Eric specified an 8px grid in the brief. I tested it against the actual surfaces this system needs to support and it fails on three of them. The honest recommendation is a 4px base with a 4/8 hybrid discipline — most spacing decisions land on 8px multiples, but the four hard cases below need 4px increments. Here is the working.

**Where 8px-strict fails:**

1. **Form input internal padding.** A 14px-body input with 8px vertical padding makes a 30px-tall input (8 + 14 + 8 = 30). 30 is not on the 8px grid. Force to 32px (8 + 16 + 8) and the input has 16px vertical breathing room around 14px text — too generous, the input feels balloony next to a 36px button. Force to 24px (8 + 8 + 8) and the text touches the chrome edge. The correct value is **28px tall (4 + 14 + 10) or 32px tall**, and 28 needs the 4px grid to express. Attio, Linear, Notion all land here — their inputs are 28–32px tall with sub-8px-precision internal padding.

2. **Dense table row height.** A "Compact" density table row needs to be roughly 28–32px tall to show 14 rows on a 1080-row dashboard above the fold. 8px-strict forces 32px or 24px. 32 is too generous (the brokerage owner wants more rows visible); 24 is too cramped (touch targets fail on tablet). The right answer is 28px or 30px — both off the 8px grid.

3. **Icon-to-text gap inside a chip or pill.** A 12px icon plus 13px text plus internal padding inside a status pill (NOC eligible badge, verified-SPA chip) needs 6px gap between icon and text. 8px reads as "the icon and text are separate things." 4px reads as "they're crushed." The right answer is 6px, which is off both 4px and 8px grids — but 4px grid lets you express it as `gap: 6px` without the system protesting that you broke discipline.

4. **Avatar-to-name gap in a chat list.** Same problem. The 32px avatar with the 14px sender name needs ~10px gap. 8px reads cramped, 16px reads loose. 10px is right and off the 8px grid.

**Where 8px-strict is right:**

- Page-level rhythm: section gaps, card-to-card spacing, sidebar widths, header height. All multiples of 8 (or 16 / 24 / 32).
- Card internal section spacing. The gap between the listing-card image and the listing-card body is 16px or 24px — never 12, never 20.
- Layout grid gutters: 16px or 24px.
- Modal padding, drawer padding, page margin: 16, 24, 32.

**The recommendation:**

A **4px base grid with strong 8px-multiple bias**. The scale jumps in 4s at the low end and in 8s at the high end. Specifically:

- `0, 2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64, 96`

The `2`, `6`, `10`, `20`, `40` steps exist for the four hard cases above and **only** for those cases. The rule shifts from *"never break 8px"* to **"prefer 8px multiples; the 4px-only steps are reserved for component-internal precision and must be justified in code review."** This is enforceable because it's a smaller list of exceptions, not a free-for-all.

If Eric overrides this and insists on 8px-strict, the fallback is to ship inputs at 32px tall, dense table rows at 32px tall, and accept that compact-density tables show ~25% fewer rows than competitors. That's a real cost paid for grid purity. Eric should pick consciously, not by default.

**Where I land:** 4px base with 4/8 hybrid rules. Spec below assumes this. If Eric insists 8px-strict, drop `space-0.5` (2), `space-1.5` (6), `space-2.5` (10), `space-5` (20), `space-10` (40) and the spec still works — the components just feel slightly looser. Not catastrophic. But I'd rather have the precision and discipline the exceptions.

### 0.2 Light-default is right for the agent, wrong for the brokerage owner's dashboard. Recommend a per-surface default, not a per-product default.

Phase 1 locked "light-default with parallel dark mode." That's correct for the agent's working chrome — they work in bright environments (car between viewings, coffee shop, brokerage office), they switch between WhatsApp and Dalya constantly, light mode matches the surrounding OS chrome they're alongside.

But the **brokerage owner sitting in their office at 7am before agents arrive, looking at a dashboard of pipeline analytics for the next 2–4 hours** is doing the work that Bloomberg, Linear, and trading terminals all default-dark for. The reasons trading terminals lean dark are not aesthetic — they are operational. Dense data plus sustained gaze plus low ambient light (owner offices have softer lighting than the agent's pickup-truck-and-coffee-shop reality) means dark mode reduces eye fatigue measurably. The brokerage owner is the persona most likely to actually live in the product for sustained sessions and the persona for whom dark-default is most defensible.

**Three options:**

- **A. Phase 1 lock as written.** Light-default everywhere. Owner gets a toggle to dark.
- **B. Per-surface default.** Agent chrome defaults light. Brokerage-owner dashboard defaults dark. Both surfaces remember user override.
- **C. System-preference default.** Both surfaces default to `prefers-color-scheme`. User override is sticky. Dalya makes no assumption about which mode anyone wants.

**My recommendation: C, with a soft surface-aware nudge.** The owner's dashboard route (`/dashboard/owner` or whatever it ends up being) defaults dark *only if the user has never set a preference*. Once they touch the toggle, their preference is sticky across surfaces and across sessions.

Why I prefer C over B: per-surface forced defaults break user expectation. An owner who has explicitly chosen light mode and then navigates to their dashboard does not want the page to silently swap to dark. Brand-product consistency matters more than per-surface optimization.

Why I prefer C over A: A defers entirely to a strong-default assumption ("light is right for everyone") that contradicts the operational reality of one of the two primary personas. Phase 1's lock was made before the brokerage-owner workflow was specified in §0.4 of `01-foundations.md`. Now it's specified, and the assumption is weaker than the lock implies.

**Concrete proposal:** the spec below assumes Option C — system-preference default, user-override sticky, no per-surface forced default. The dark-mode strategy is designed (not derived) but the *which mode the user lands in* is user-or-OS-controlled. Eric can override this back to Phase 1-strict; the cost is the brokerage-owner persona reaching for a toggle every time they open the product, which is a small but real workflow friction.

**Where I land:** Option C. If Eric reverts to Option A, the only change to the spec below is the `@theme` default — flip the cascade so light tokens are the unconditional default and dark tokens activate only via `data-theme="dark"`.

The remainder of this document proceeds on **4px-base hybrid + system-preference default**. Both can be reverted to Phase 1-strict without re-architecture.

---

## 1. Spacing scale

**Base unit:** 4px. Bias toward 8px multiples. Reserved 4px-only steps for component-internal precision (see §0.1).

| Token | px | rem | Role (the rule is this column, not the value) |
|---|---|---|---|
| `space-0` | 0 | 0 | Reset, zero spacing in containers. |
| `space-0.5` | 2 | 0.125 | **4px-only reserve.** Hairline separations inside chips; tabular-figure column alignment fine-tune. |
| `space-1` | 4 | 0.25 | Icon-to-text gap in dense surfaces (table cells, breadcrumbs, badges). |
| `space-1.5` | 6 | 0.375 | **4px-only reserve.** Icon-to-text gap in pills/chips where 4 cramps and 8 separates. |
| `space-2` | 8 | 0.5 | Icon-to-text gap in body surfaces. Internal padding of compact chips. Vertical gap inside a single form field group. |
| `space-2.5` | 10 | 0.625 | **4px-only reserve.** Avatar-to-name gap in conversation list. Sub-8 internal padding for short-text inputs. |
| `space-3` | 12 | 0.75 | Button vertical padding (default size). Form input horizontal padding. Default card internal corner gap. |
| `space-4` | 16 | 1 | **Workhorse.** Card body padding (default density). Form field stack gap. Section internal gap. List item padding. |
| `space-5` | 20 | 1.25 | **4px-only reserve.** Card body padding (display density — between 16 and 24, justified). |
| `space-6` | 24 | 1.5 | Card internal section gap (multi-section card). Page margin (mobile). Modal body padding. |
| `space-8` | 32 | 2 | Card-to-card gap in a list. Page section gap (medium). Header height tier. Form section gap. |
| `space-10` | 40 | 2.5 | **4px-only reserve.** Header height (default desktop). |
| `space-12` | 48 | 3 | Page section gap (large). Page margin (desktop default). Empty-state vertical spacing. |
| `space-16` | 64 | 4 | Marketing section gap. Page-top spacing for signed-out hero surfaces. |
| `space-24` | 96 | 6 | Marketing-only. Hero internal vertical padding. Rarely in product chrome. |

### Operational rules

1. **Never ad-hoc.** If the spacing you want is not on this scale, the answer is "pick the nearest scale step," not "add a one-off pixel value." Lint rule: any `padding`, `margin`, or `gap` in a `*.tsx` file outside `marketing/` that isn't a token reference fails CI.

2. **4px-only steps are flagged.** The five reserved 4px-only steps (`space-0.5`, `space-1.5`, `space-2.5`, `space-5`, `space-10`) require a code-review comment explaining why an 8px-multiple wasn't right. This is the discipline that keeps the hybrid honest.

3. **Density override scaling.** The Comfortable / Compact / Display densities (§7) modify a subset of these tokens via CSS variable cascade, not via separate token sets. Components opt into density-awareness; static surfaces (marketing pages) ignore it.

4. **No negative spacing.** No `-space-4` style negative-margin tokens. Negative margin is a hack and we don't have a use case for it in this product. If a designer reaches for it, the layout is wrong.

5. **Bidi-safe by default.** All spacing tokens that apply to `margin-inline-*`, `padding-inline-*`, `gap` are RTL-safe automatically. The Tailwind v4 utilities `ms-*`, `me-*`, `ps-*`, `pe-*` map to these tokens via logical properties (see §10).

### What each step is *for* — the canonical list

Designers reach for the wrong scale step when they don't know what each step is canonically for. The table above gives a role for each; this is the enforcement list.

- **Icon-to-text gap inside a dense surface (table cell, breadcrumb, tag):** `space-1` (4px).
- **Icon-to-text gap inside a body surface (button, card title row):** `space-2` (8px).
- **Button vertical padding (default size):** `space-3` (12px). Total button height with 14px text = 12 + 14 + 12 = 38px. We override to **36px** via component spec (see §7 density rules + handoff to `06-components.md`).
- **Form input vertical padding (default):** `space-2.5` (10px). Total input height with 14px text = 10 + 14 + 10 = 34px. Rounded to **32px** via line-height containment.
- **Card body padding (default):** `space-4` (16px). All four sides.
- **Card body padding (display density, marketing):** `space-6` (24px) or `space-8` (32px).
- **Card internal section gap (when a card has a header + body + footer):** `space-6` (24px) between sections, `space-4` (16px) within a section.
- **List item vertical padding (default):** `space-3` (12px). Compact density: `space-2` (8px). Display density: `space-4` (16px).
- **Page section gap (between top-level sections of a page):** `space-12` (48px) on desktop, `space-8` (32px) on mobile.
- **Modal body padding:** `space-6` (24px). Modal header padding: `space-4` + `space-6` (16 vertical, 24 horizontal).
- **Form field stack gap (vertical gap between form fields):** `space-4` (16px).
- **Form section gap (between groups of related fields):** `space-8` (32px).
- **Page margin (mobile):** `space-4` (16px). Page margin (tablet): `space-6` (24px). Page margin (desktop): `space-8` (32px) or `space-12` (48px) depending on layout context.

> *Handoff to `06-components.md`:* component-specific spacing (button heights, input heights, exact tab indicator offsets, exact card hover-state offsets) is your specification. The scale and the canonical roles are upstream from you. Where a component wants a value not on the scale, raise it as an exception — don't quietly add a `space-3.5` token.

---

## 2. Surface elevation

**The decision:** 3 elevation levels (recommended) plus one ephemeral overlay level. Surfaces stack via **tonal lift + hairline border**, *not* via shadow as the primary stacking mechanism.

This is the most consequential decision in this document. The reasoning:

- **Light-default UIs in 2026 are split between two stacking philosophies.** Linear, Notion, Attio, Vercel lean on borders + tonal lift (slightly different background colors at each level). Stripe, Figma, modern Atlassian lean on shadow. The Phase 1 lock for "calm" and the reference cluster (Linear, Attio, Notion as primary) point us strongly toward borders + tonal lift.
- **Shadow-as-elevation reads as "marketing" or "luxury" in light mode.** It works on Stripe because Stripe is half-marketing-site. It works on Figma because Figma's elevation system is *load-bearing* — you need to see floating panels at a glance. For Dalya's working surfaces (tables, dashboards, conversation lists), shadows would add noise without informational benefit.
- **The previous Dalya system used ambient ink-tinted shadows.** That was correct for the dark consumer surface, where shadow could be tinted with the brand ink to feel intentional. In light mode, "ink-tinted shadow on near-white surface" reads as either invisible (too subtle) or muddy (too visible). Tonal lift is the cleaner solution.
- **Shadows do appear** — for transient overlays only (modals, popovers, toasts). They are functional, not decorative. They communicate "I am floating over the page; click outside me to dismiss." This is the only role shadows play in the system.

### The four levels

| Token | Role | Light bg | Light border | Dark bg | Dark border | Shadow (light) | Shadow (dark) |
|---|---|---|---|---|---|---|---|
| `surface-0` | Page background. The "paper." | `neutral-50` `#FAFAF7` | none | `dark-bg` `#0E1116` | none | none | none |
| `surface-1` | Primary working surface. Cards, panels, inline editors, table containers. | `neutral-0` `#FFFFFF` | `neutral-200` `#E8E8E3`, 1px | `dark-surface-1` `#161A21` | `dark-border` `#2E3540`, 1px | none | none |
| `surface-2` | Nested surface inside a card. Sub-panel, inline form, expanded row. | `neutral-50` `#FAFAF7` | `neutral-200` `#E8E8E3`, 1px | `dark-surface-2` `#1F242C` | `dark-border` `#2E3540`, 1px | none | none |
| `surface-overlay` | Transient floating surface. Modal, popover, dropdown menu, toast. | `neutral-0` `#FFFFFF` | `neutral-300` `#D4D4CD`, 1px | `dark-surface-2` `#1F242C` | `dark-border-strong` `#3E4654`, 1px | `shadow-overlay-light` (see §5) | `shadow-overlay-dark` (see §5) |

### Notes on this table

- **`surface-0` is the page background.** It is the *darker* of the two "white" tokens. The card surface (`surface-1` = pure white) sits *on top* of `surface-0` and the card is the *lighter* element. This is counter to the dark-mode intuition (where the page is darkest and surfaces step up) and is correct for light mode: white cards on paper-warm-tinted page reads as "documents on a desk," which is the metaphor working tools should evoke.
- **`surface-2` is `neutral-50` — same as the page.** A nested panel inside a card looks "recessed" because it returns to the page color while the card remains pure white. This is the Attio pattern. Two consequences: (a) a `surface-2` element placed directly on the page is *visually identical to the page background*, which is correct — `surface-2` is only meaningful inside a `surface-1` container; (b) the recessed effect requires the card to have a visible border, which is why borders are non-negotiable in this system.
- **No `surface-3`.** I considered a fourth level for deeply-nested elements (sub-tab inside a sub-panel inside a card). The audit: this pattern is rare in CRM UI and when it appears it usually indicates information hierarchy that should be flattened. If `06-components.md` needs `surface-3` for a specific component, raise it; otherwise it stays out.
- **Why no shadow on `surface-1` or `surface-2`:** consistency. The presence of a shadow on a card would code "this card is special / floating / interactive in a different way than other cards." All cards on a working surface are visually-flat, separated by border + tonal contrast. The exception is the modal/popover layer, which earns its shadow because it's actually floating.

### Surface composition rules

1. **`surface-0` is the unconditional page background.** No content surface ever uses `surface-0` directly as its own background; if a content surface needs to *visually disappear* into the page (e.g., a borderless section), it inherits the page background via `bg-inherit` or by omitting a background entirely.
2. **`surface-1` always has a border in light mode.** Cards without borders read as floating, which is the role of `surface-overlay`. Borderless cards are banned in light mode.
3. **In dark mode, `surface-1` borders are optional** and replaced by tonal contrast against `dark-bg`. The difference between `#0E1116` (page) and `#161A21` (surface) is sufficient to delineate without a border. If the card edge is ambiguous on a specific surface, add the border conditionally; never as a default-on rule.
4. **Nested `surface-2` inside `surface-1` does not need a border between them.** The tonal step (white card → paper-warm sub-panel) is the boundary. Adding a border would be the banned "double border" pattern (§3).
5. **`surface-overlay` always has shadow + border** in both modes. The shadow does the float work; the border keeps the edge crisp against bright backgrounds where the shadow alone is insufficient.

---

## 3. Borders

Three border tokens. Light + dark mappings. Semantic load rules.

### Tokens

| Token | Width | Light color | Dark color | Role |
|---|---|---|---|---|
| `border-hairline` | 1px | `neutral-200` `#E8E8E3` | `dark-border` `#2E3540` | **Default everywhere.** Card edges, table row separators, divider lines, form input borders at rest. |
| `border-default` | 1px | `neutral-300` `#D4D4CD` | `dark-border-strong` `#3E4654` | Emphasized edges — selected card, hovered row, button outline-variant, separator between major page sections. |
| `border-strong` | 1px | `neutral-500` `#7A7A73` | `dark-text-muted` `#6E737B` | Form input focus (paired with focus ring), warning callout edges, error-state input border (paired with `error-strong`). |

### Notes

- **All three are 1px.** No 2px borders in the system. 2px reads as "decorative" or "warning panel" and breaks the calm-by-default rule. Where emphasis is needed, the system uses color or background contrast, not stroke width. (Exception: focus rings — see §6 — which use a 2px ring for accessibility, not a 2px border.)
- **Color, not width, carries border emphasis.** This is critical and is the most-violated rule in B2B SaaS systems. If a designer wants a "stronger" border on a hovered row, they reach for the `border-default` token, not `border-2`.
- **`border-hairline` is the only one used on rest-state working surfaces.** `border-default` and `border-strong` only appear on hover, focus, selected, error states.

### When borders carry semantic load

- **Form field at rest:** `border-hairline`. **On focus:** `border-strong` plus a 2px focus ring (see §6) — the input *itself* gains a stronger edge, *and* the ring sits outside it. The two together form the focus indication. **On error:** `border-strong` colored with `error-strong` plus the focus ring colored with `error-strong`.
- **Table row separator:** `border-hairline` between rows. Hovered row: row background shifts to `neutral-100`, border stays `border-hairline`. Selected row: row background shifts to `brand-50`, border *upgrades* to `border-default` on the *left edge only* (a 3px-wide left edge would be the wrong instinct — keep it 1px, but stronger color). RTL: left edge becomes right edge automatically via logical properties.
- **Card edge:** `border-hairline`. Selected card: `border-default` paired with a subtle `brand-50` background tint. Hovered card: optional `border-default` if the card is clickable; no change if the card is informational.
- **Section divider on a settings page:** `border-hairline`, full-width horizontal rule. Never decorative — only between distinct semantic sections.

### Decorative borders — when they're allowed

Almost never. The system uses borders for *structure*, not *decoration*. The two exceptions:

1. **Empty-state container.** A dashed `border-hairline` rectangle around a "no listings yet" or "drag SPA here to upload" zone. Dashed style codes "this is a placeholder for content that doesn't exist yet." Solid would code "this is a real container." This is the only place dashed borders appear.
2. **Code block / pre block.** `border-hairline` around a code sample (rare in this product — admin tooling, dev settings).

### Banned border patterns

- **Nested borders.** A border on a card *and* a border on the immediate child element. The two borders sitting next to each other create a visual "track" that reads as a print-design artifact, not a digital surface. The child either inherits the card's edge (no border) or sits *inside* a `surface-2` recessed region (border on neither, tonal step instead).
- **Double borders.** Two borders on the same element (e.g., `border` on the input + an outer ring that reads as a second border). The focus ring is *not* a border — it's an outline-style ring offset 2px outside the element. The eye reads them as separate things.
- **Border + heavy shadow.** A card that has both a hairline border *and* a drop shadow. Pick one. In this system, working surfaces pick border; overlay surfaces pick shadow + border (the border keeps the edge crisp; the shadow does the elevation work).
- **Coloured borders for decoration.** A card with a `brand-500` border to signal "this is the Dalya brand card." Banned. Color carries semantic load (selected, error, focus). Coloured borders without semantic meaning create false visual hierarchy.
- **Wide / 2px+ borders.** Banned globally. See above.
- **Dotted borders.** Banned. Dashed is the empty-state convention; dotted reads as Web 1.0.

---

## 4. Border radii

The system is **softly-rounded** — not razor-sharp like Linear, not playful-rounded like Notion. The argument:

- **Razor-sharp (0–2px radii, Linear-style)** reads as ultra-modern, slightly cold, slightly engineering-aesthetic. It works on Linear because Linear's audience is engineers who are happy in that register. Dalya's audience is real estate agents — the register should feel competent but not engineering-tribal.
- **Playful-rounded (12px+ on cards, Notion-style)** reads as friendly, slightly informal, slightly consumer. Wrong register for regulator-aware property infrastructure.
- **Softly-rounded (4–8px on most things, with 12px on cards and 16px on modals)** is the Attio / Stripe-dashboard register. Competent, modern, not aggressive in either direction.

### Tokens

| Token | px | Role |
|---|---|---|
| `radius-0` | 0 | **Square corners.** Used for: page-level layout containers (sidebars, header), full-width banners, data table cells (cells stay sharp; only the table container has radius). |
| `radius-1` | 4 | Small. Inputs, badges, chips, small icon buttons (icon-only square buttons), table container outer corner. |
| `radius-2` | 8 | **Default.** Cards (working surfaces), buttons, dropdown items, list items in a settings list. The most common radius in the system. |
| `radius-3` | 12 | Large. Modals, drawers, sheets, popovers. The "floating" radius. |
| `radius-4` | 16 | Display only. Marketing-page cards, signed-out hero containers. Rare in product chrome. |
| `radius-full` | 9999 | Pills, avatars, circular icon buttons, status dots. |

### Why this scale specifically

- **`radius-0` exists** because a sharp-cornered data table cell *inside* a `radius-1` table container is the correct pattern. The container softens the table's outer edge; the cells stay precise because data wants precision. If everything were rounded, the table would read as a card-of-cards instead of a structured data surface.
- **`radius-1` (4px) is for tactical small elements.** A 36px-tall button with `radius-1` reads stocky. A 24px-tall input chip with `radius-1` reads structured. The right element for the radius.
- **`radius-2` (8px) is the workhorse.** Roughly 8px is the smallest radius that reads as "rounded on purpose" rather than "the renderer is anti-aliasing the corner." It's the universal default for cards and buttons in 2024–2026 B2B SaaS — Attio, Linear's button, Stripe's dashboard cards all land here or within 2px of it.
- **`radius-3` (12px) for modals and floating surfaces** because the larger surface area needs more visible radius to feel intentionally rounded. A 12px radius on a 600px-wide modal reads at the same visual *weight* as 8px on a 320px-wide card.
- **`radius-full` for pills** because pills (status badges, language switcher chips) read as "tag-like" with full-radius, and read as "small button" with `radius-1`. The difference is communicative.

### Banned radius patterns

- **Asymmetric radii** on the same element (e.g., `border-radius: 12px 4px 4px 4px` on a card to imply directionality). Banned — reads as theme-y. The only exception is a tab-like element where the top corners are rounded and the bottom is square because the tab is "attached" to a panel underneath; even there, prefer a tab indicator approach over the asymmetric-radius approach.
- **Mixed radii in a single composition.** A card with `radius-2` containing a button with `radius-3` reads chaotic. The button radius should equal or be smaller than the container radius.
- **`radius-full` on rectangles wider than 2x their height.** A long full-radius element reads as a stadium-shaped pill; that's only correct for actual pills (status chips, language switcher options). A "rounded button" should use `radius-2`, not `radius-full`.

---

## 5. Shadows

Shadow is scoped to the overlay surface tier only (§2). Three shadow tokens. Light and dark are designed separately, not derived.

### Tokens

```css
/* Light-mode shadows — neutral-ink-tinted, very subtle */
--shadow-overlay-sm:
  0 1px 2px 0 rgba(38, 38, 36, 0.04),
  0 1px 3px 0 rgba(38, 38, 36, 0.06);

--shadow-overlay-md:
  0 4px 6px -1px rgba(38, 38, 36, 0.06),
  0 2px 4px -1px rgba(38, 38, 36, 0.04),
  0 0 0 1px rgba(38, 38, 36, 0.04);

--shadow-overlay-lg:
  0 10px 15px -3px rgba(38, 38, 36, 0.08),
  0 4px 6px -2px rgba(38, 38, 36, 0.04),
  0 0 0 1px rgba(38, 38, 36, 0.04);

/* Dark-mode shadows — much subtler, the heavy lifting is tonal contrast */
--shadow-overlay-sm-dark:
  0 1px 2px 0 rgba(0, 0, 0, 0.30);

--shadow-overlay-md-dark:
  0 4px 8px 0 rgba(0, 0, 0, 0.40),
  0 0 0 1px rgba(255, 255, 255, 0.04);

--shadow-overlay-lg-dark:
  0 12px 24px 0 rgba(0, 0, 0, 0.50),
  0 0 0 1px rgba(255, 255, 255, 0.04);
```

### Roles

| Token | Use |
|---|---|
| `shadow-overlay-sm` | Dropdown menus, small popovers (≤320px wide), language-switcher dropdown, table-row action menu. |
| `shadow-overlay-md` | Standard modals, side drawers, popover cards (e.g., AED-figure tooltip with detail). |
| `shadow-overlay-lg` | Dialogs that demand maximal attention — destructive-action confirmations, full-screen-takeover modals on mobile. Used sparingly. |

### Why neutral-ink-tinted (not gold, not brand)

The previous Dalya system used gold-tinted ambient shadows. That was correct for dark-mode + gold-accent brand. In light mode, gold-tinted shadows on `surface-1` (white) read as a faint sickly yellow at the edges — not premium, dirty. The light-mode shadow base is **`rgba(38, 38, 36, …)`** — that's `neutral-800` in `rgba` form. Same neutral that body text uses. Reads as natural shadow of an object on paper rather than tinted-anything.

Brand-tinted shadow (using `brand-500` rgba) was considered. Rejected — same problem: anything but neutral reads as themed, and themed shadow is decorative-not-functional. Shadow's job is to communicate float, not brand identity.

### Why dark-mode shadows are different

In dark mode, "shadow" is mostly an illusion — a darker region of the screen against a slightly less-dark surface. The 30–50% opacity rgba(0,0,0,...) creates a *darker-than-page* halo around the overlay. Plus a subtle `0 0 0 1px rgba(255, 255, 255, 0.04)` ring above it — that white-tinted 1px ring is what actually delineates the overlay's edge against the dark background.

This is the standard dark-mode overlay pattern: heavy darker shadow + subtle lighter ring for edge definition. Linear, Notion, Attio all do this. Without the white-tinted ring, dark-mode modals look like vague darker regions of the page with no clear edge.

### Mobile fallback (linked to §13)

Light-mode shadows can wash out on mobile under direct sunlight or on cheap LCD panels (a real risk for the agent in a parking lot). For the mobile breakpoint (≤768px) all overlay surfaces *additionally* get a `border-default` (`neutral-300`, 1px) to keep the edge visible when the shadow is invisible. The desktop hairline ring (`rgba(38, 38, 36, 0.04)` in the box-shadow stack) is insufficient on mobile.

### Banned shadow patterns

- **Coloured shadows.** Gold, brand-blue, or any non-neutral shadow. Banned.
- **Inner shadows.** Inset shadows on inputs or cards. Banned — they read as skeuomorphic. Modern depth comes from outer shadow + edge, not from "inset to look pressed."
- **Layered shadows for "depth."** Two stacked shadows on the same card to simulate stronger elevation. The system has three pre-built shadow tokens (sm/md/lg) — use them, don't stack.
- **Shadow on working surfaces.** No shadow on `surface-1` or `surface-2`. Already covered in §2 but worth restating.

---

## 6. Focus rings

Critical accessibility surface. The default Tailwind ring (`ring-2 ring-blue-500`) is wrong because (a) the default blue isn't our brand color, (b) the default ring sits *flush* against the element, which is hard to see on focused inputs that already have borders, (c) it doesn't account for high-contrast mode.

### Token

```css
--focus-ring-color: var(--color-brand-500);     /* #3D5A80 */
--focus-ring-offset: 2px;                        /* gap between element edge and ring */
--focus-ring-width: 2px;                         /* ring thickness */
--focus-ring-offset-color: var(--color-surface-0); /* the page background — fills the offset gap */

/* The composed ring */
--focus-ring:
  0 0 0 var(--focus-ring-offset) var(--focus-ring-offset-color),
  0 0 0 calc(var(--focus-ring-offset) + var(--focus-ring-width)) var(--focus-ring-color);
```

### Behaviour

- **2px offset, 2px ring.** Total ring footprint extends 4px outside the element. That's enough to be unmistakable without looking inflated.
- **Offset-color matches the surface background.** This is the critical detail. The 2px gap *appears as a separating space* between the element and the ring because it matches whatever surface the element sits on. If the focused element is on `surface-1` (white card), the offset is white. If on `surface-0` (paper page), offset is paper. The cascade handles this automatically via CSS variable — `--focus-ring-offset-color` is overridden at each surface level.
- **Brand-500 color.** Slate blue. Same as primary brand. Color-blind safe against most error/warning palettes. Verified AA against `surface-0` (`neutral-50`) at 6.62:1.
- **The ring is always visible on `:focus-visible`, never on `:focus`.** Keyboard-driven focus shows the ring; click-driven focus does not. This is the standard 2025 pattern — mouse users don't need a focus ring on the button they just clicked, but keyboard users always do.

### High-contrast mode

In Windows / macOS High Contrast Mode (forced-colors media query), the brand-blue ring may be overridden by the OS to its own focus color (often a high-contrast yellow or system blue). The override is correct — we should defer to the user's OS-level accessibility preference.

```css
@media (forced-colors: active) {
  :focus-visible {
    outline: 2px solid CanvasText;
    outline-offset: 2px;
    box-shadow: none;
  }
}
```

`CanvasText` is the system-defined high-contrast foreground color. This rule swaps from our shadow-based ring to an `outline:` which forced-colors mode handles correctly.

### Error-state focus

For an input in error state, the focus ring color shifts:

```css
.field--error:focus-visible {
  --focus-ring-color: var(--color-error-strong);  /* #A8332A */
}
```

The 2px offset remains, the width remains. Only the color changes. This is a documented pattern for `06-components.md` to implement at the form-component level.

### Dark-mode focus ring

The brand-500 ring at 6.85:1 contrast on `surface-1` (white) is fine. In dark mode, `surface-1` is `#161A21` and `brand-500` at `#3D5A80` only hits ~4.2:1 — borderline for the focus indicator's 3:1 minimum.

**Fix:** in dark mode the focus ring color shifts to `brand-400` (`#5F7DA2`), which hits ~5.9:1 against `dark-surface-1`. The cascade handles this:

```css
:root {
  --focus-ring-color: var(--color-brand-500);
}
[data-theme="dark"] :root, html[data-theme="dark"] {
  --focus-ring-color: var(--color-brand-400);
}
```

### Banned focus patterns

- **No focus ring at all.** Banned globally. Even on `:focus-visible` it must be present for keyboard users.
- **Default browser outline (`outline: -webkit-focus-ring-color`).** Banned — inconsistent across browsers, accessibility uncertain.
- **A focus ring that's the same color as the element it surrounds.** A focused brand-blue button with a brand-blue ring is invisible. The ring contrasts against the page surface, not the element.

---

## 7. Density rules

Three density modes. The brief specified the rough shape; here are the concrete deltas.

### Modes

| Mode | Where it's the default | Body text | Component scaling |
|---|---|---|---|
| `density-comfortable` | Agent workspace, mobile defaults everywhere, advisor chat surface | 14px / `text-base` | Default values from §1. |
| `density-compact` | Brokerage owner dashboard tables, analytic pivot tables, agent performance grids | 13px / `text-sm` | Sub-8px tightening on rows, padding, gaps. |
| `density-display` | Marketing pages, signed-out states, onboarding hero, first-run empty states | 16px / `text-md` | Loosening to `space-5`+ on internal gaps, taller heroes. |

### Comfortable (default)

- Body: 14px / `text-base`. 1.6 line-height.
- Buttons: 36px tall. Vertical padding `space-3` (12px), text 14px.
- Form inputs: 36px tall. Vertical padding 10px (line-height absorbs 1px each side, target 36 total).
- List item: 12px vertical padding, 16px horizontal. Roughly 44px tall row.
- Table row: 44px tall (12px vertical padding around 14px text + 2px row border).
- Card body padding: 16px (`space-4`).
- Section gap inside a page: 32–48px (`space-8` / `space-12`).
- This is the agent's default working surface.

### Compact (opt-in by surface)

- Body: 13px / `text-sm`. 1.55 line-height.
- Buttons: 32px tall. (Used only as toolbar buttons within compact surfaces; primary CTAs stay at comfortable density.)
- Form inputs: 32px tall. Vertical padding 8px.
- List item: 8px vertical padding, 12px horizontal. ~36px tall row.
- Table row: **30px tall**. (10px vertical padding around 13px text + 1px border. This is the row that lets the brokerage owner see 14 rows above the fold instead of 10.)
- Card body padding: 12px (`space-3`).
- Section gap inside a page: 24–32px (`space-6` / `space-8`).
- Density-compact is **route-scoped**, not user-toggleable. The brokerage owner's analytics dashboard ships at compact. The advisor chat is never compact.

### Display (signed-out / marketing / first-run)

- Body: 16px / `text-md`. 1.55 line-height.
- Buttons: 44px tall. (More tappable, more "this is the primary action of the page.")
- Form inputs: 44px tall.
- Card body padding: 24–32px (`space-6` / `space-8`).
- Section gap inside a page: 64–96px (`space-16` / `space-24`).
- Used on: marketing site, login page, first-run onboarding empty states, the "drag SPA here" upload surface.

### Implementation rule

Density is a CSS variable cascade on a route or surface scope, not a class on every component. The Comfortable values are the *default*; Compact and Display override the relevant vars:

```css
[data-density="compact"] {
  --row-height: 30px;
  --button-height: 32px;
  --input-height: 32px;
  --card-padding: var(--space-3);  /* 12px */
  --body-size: var(--text-sm);
  --body-line-height: 1.55;
}

[data-density="display"] {
  --row-height: 56px;
  --button-height: 44px;
  --input-height: 44px;
  --card-padding: var(--space-6);  /* 24px */
  --body-size: var(--text-md);
  --body-line-height: 1.55;
}
```

Components read from CSS variables (`height: var(--row-height)`), and the surrounding `[data-density="..."]` element controls the value. The `06-components.md` spec will define which components honor the density override and which are density-invariant (e.g., the navigation chrome stays comfortable regardless of the page's density).

> *Handoff to `06-components.md`:* the density-aware components are: table rows, list items, buttons (sometimes), inputs (sometimes), card padding. Density-invariant: navigation chrome, modal padding, focus ring, page margins. Where this boundary is unclear, the rule is "if it's part of a page-level data surface, it honors density; if it's chrome, it doesn't."

### Banned density patterns

- **Mixing densities on the same surface.** A page with some compact tables and some comfortable tables is chaotic. Pick one per page.
- **A user-toggle density switcher in the main chrome.** Out of scope for Phase 2. Density is route-determined. If a Phase 3 feature wants per-user density preference, design that separately.
- **Density on text-heavy surfaces.** The advisor chat is `density-comfortable` permanently. Compact at 13px ruins the reading flow.

---

## 8. Layout primitives

### Maximum content widths

Eric uses `max-w-5xl` and `max-w-6xl` interchangeably in the existing codebase. Standardize:

| Token | px | Use |
|---|---|---|
| `width-prose` | 720 | Long-form reading text (advisor chat message column, settings descriptions, error-page bodies). Optimal reading line length. |
| `width-content` | 1080 | **Default content width.** Most marketing pages, settings pages, dashboard pages. Center-aligned via `mx-auto`. |
| `width-wide` | 1280 | Dashboard surfaces with side-by-side panels (chat + detail), data tables that benefit from horizontal room. |
| `width-full` | 100% | Full-bleed surfaces — admin tables, owner analytics dashboards that span the viewport. |

### Page-level grid

12-column on desktop, single-column on mobile, with breakpoints (§ below).

| Breakpoint | Columns | Gutter | Margin |
|---|---|---|---|
| `mobile` (≤640) | 1 | n/a | 16px |
| `sm` (640+) | 4 | 16px | 24px |
| `md` (768+) | 8 | 16px | 24px |
| `lg` (1024+) | 12 | 24px | 32px |
| `xl` (1280+) | 12 | 24px | 32px |
| `2xl` (1536+) | 12 | 24px | 48px |

### Sidebar widths

The agent workspace and the brokerage owner dashboard both have a left rail.

| Token | px | Use |
|---|---|---|
| `sidebar-narrow` | 64 | Icon-only collapsed nav. Hover-expands to wide. |
| `sidebar-default` | 240 | Default expanded nav. Icon + label. |
| `sidebar-wide` | 280 | Conversation list (advisor chat surface). Holds buyer name + last message preview + timestamp. |

Mobile collapses all of these into a sheet that slides in over the content. Sheet width: 80% of viewport, max 320px.

### Header height

| Token | px | Use |
|---|---|---|
| `header-default` | 56 | Standard product chrome header. Logo + nav + user menu. |
| `header-compact` | 48 | Embedded surfaces — modal headers, drawer headers. |
| `header-display` | 72 | Marketing pages. Slightly more breathing room. |

Mobile: header collapses to 56px on all surfaces.

### Mobile hamburger zone

44px × 44px tap target. Top-left on LTR, top-right on RTL (logical positioning). The hamburger icon is 20px centered in the tap target.

### Breakpoints

Tailwind v4's defaults are `sm 640 / md 768 / lg 1024 / xl 1280 / 2xl 1536`. The brief asks me to pick mine. **My picks: match v4 defaults except shift `xl` to 1200.**

Reasoning: the brokerage owner's dashboard layout transitions from single-rail to dual-rail at ~1200px, not 1280. The 1280 breakpoint was set by Tailwind to match common laptop displays, but the dual-rail dashboard needs the layout switch slightly earlier or the dashboard at 1280–1350 feels squeezed.

| Token | px | Notes |
|---|---|---|
| `sm` | 640 | Phone landscape, narrow tablet portrait. |
| `md` | 768 | Tablet portrait, narrow tablet landscape. |
| `lg` | 1024 | Tablet landscape, small laptop. |
| `xl` | 1200 | **Custom.** Triggers dual-rail dashboard layout. |
| `2xl` | 1536 | Wide desktop. Triggers maximum content widths. |

If `lg → xl` shift to 1200 conflicts with anything in `06-components.md`, that should be raised — but the breakpoint is foundational so it lives here.

### Banned layout patterns

- **Pixel-precise widths in component code.** Components reference `width-content` / `width-wide` tokens, not `1080px` directly.
- **Negative margin to extend content beyond the container.** Banned. If a section needs full-bleed, it lives outside the container, not negative-margined out of it.
- **Centered text columns wider than 720px.** Banned by typography rules; restated here as a layout rule.

---

## 9. Z-index scale

Seven steps. Token-named. The whole point is to prevent the "z-index: 9999" arms race that happens unbounded.

```css
--z-base: 0;          /* Default in-flow content. Never explicitly used; the absence of z-index. */
--z-nav: 10;          /* Sticky page headers, the sidebar, persistent navigation chrome. */
--z-sticky: 20;       /* Sticky table headers, sticky form footers, anything that follows scroll. */
--z-dropdown: 30;     /* Dropdown menus, autocomplete suggestions, language switcher. */
--z-popover: 40;      /* Tooltips, popover cards, inline-edit panels. */
--z-modal: 50;        /* Modals, dialogs, side drawers. */
--z-toast: 60;        /* Toast notifications. Above modals — toasts can fire over an open modal. */
```

### Rules

1. **No z-index value outside this scale in any product surface.** Lint rule: `z-index: \d+` in `.tsx` / `.css` files must reference a token (`var(--z-modal)` or Tailwind's `z-modal` utility).
2. **Toasts above modals is deliberate.** A toast saying "Connection lost — retrying" while a user is mid-modal must be visible. The toast tier is permanently the top.
3. **Backdrop is implicit at modal-1.** The semi-transparent backdrop behind a modal sits at `z-modal - 1` automatically via the modal component spec.

---

## 10. RTL support

Cultural Strategy mandated RTL-from-day-one. The system implements this via logical CSS properties throughout. **No physical-side properties in any component code outside marketing.**

### The rule (binding)

- **Margins:** `margin-inline-start`, `margin-inline-end`, `margin-block-start`, `margin-block-end`. Never `margin-left` / `margin-right` / `margin-top` / `margin-bottom`.
- **Paddings:** same as above with `padding-*`.
- **Positioning:** `inset-inline-start`, `inset-inline-end`, `inset-block-start`, `inset-block-end`. Never `left` / `right`.
- **Text alignment:** `text-align: start` / `text-align: end`. Never `left` / `right`.
- **Borders:** `border-inline-start`, `border-inline-end`. Never `border-left` / `border-right`.

### Tailwind v4 mapping

Tailwind v4 ships logical-property utilities:

| Physical (BANNED) | Logical (USE) |
|---|---|
| `ml-4` | `ms-4` (`margin-inline-start: 1rem`) |
| `mr-4` | `me-4` (`margin-inline-end: 1rem`) |
| `pl-4` | `ps-4` (`padding-inline-start: 1rem`) |
| `pr-4` | `pe-4` (`padding-inline-end: 1rem`) |
| `text-left` | `text-start` |
| `text-right` | `text-end` |
| `border-l` | `border-s` |
| `border-r` | `border-e` |
| `left-0` | `start-0` |
| `right-0` | `end-0` |
| `rounded-l-lg` | `rounded-s-lg` |
| `rounded-r-lg` | `rounded-e-lg` |

### Which spacing tokens are bidi-safe automatically

All of `space-*` tokens are direction-agnostic — they're scalar values (e.g., `8px`). The bidi safety depends on **which CSS property the token is applied to**.

| CSS Application | Bidi-safe? |
|---|---|
| `gap` | Yes, always — gap doesn't have a direction. |
| `padding-inline`, `padding-block` | Yes. |
| `margin-inline`, `margin-block` | Yes. |
| `padding-left` / `padding-right` (banned but for reference) | No — physical side. |

### Which spacing tokens need explicit RTL variants

None at the token level. The token is direction-neutral. The *utility class name* encodes direction (`ms-4` vs `me-4`), and Tailwind's RTL handling swaps them at the document level via the `dir="rtl"` attribute.

### Icon mirroring

Icons that have directionality (chevrons, arrows, "next" / "previous" indicators) need mirrored variants in RTL. The pattern:

```css
[dir="rtl"] .icon--directional {
  transform: scaleX(-1);
}
```

Or — preferred — use icons from a library that ships logical variants (e.g., `ChevronStart` and `ChevronEnd` rather than `ChevronLeft` and `ChevronRight`). The `06-components.md` spec will name the icon library and the convention.

### What doesn't mirror in RTL

- **AED numerals.** Tabular numerals stay LTR even in RTL Arabic text. Browser handles this automatically with `dir="auto"` or `unicode-bidi`.
- **Currency prefix position.** Per Cultural Strategy §3.3, AED stays as `AED 2,450,000` even in RTL contexts when in English locale; in Arabic locale becomes `٢٬٤٥٠٬٠٠٠ درهم`. This is a locale decision, not an RTL decision.
- **Logos and brand marks.** The Dalya wordmark does not mirror. It is the brand identity in both directions.
- **Code blocks.** Mono-font code samples stay LTR.

### Banned RTL patterns

- **Hardcoded physical-side properties in product code.** Caught by lint.
- **`!important` overrides to "fix" RTL.** If a layout breaks in RTL, the underlying property is using physical sides. Fix the property, don't override.

---

## 11. Dark-mode strategy

Per §0.2, the recommended default is system-preference with sticky user override. Both modes are designed in parallel — not derived.

### How tokens switch

The system uses a **dual-fallback approach**:

```css
@theme {
  /* All tokens defined as light-mode by default */
  --color-surface-1: #FFFFFF;
  --color-text-primary: #3D3D38;
  /* ... */
}

/* OS-preference dark mode (no user override) */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-surface-1: #161A21;
    --color-text-primary: #E8E8E3;
    /* ... */
  }
}

/* Explicit user override */
:root[data-theme="dark"] {
  --color-surface-1: #161A21;
  --color-text-primary: #E8E8E3;
  /* ... */
}
```

The cascade:

1. Default = light.
2. OS dark + no user override = dark.
3. User toggle to dark (regardless of OS) = dark.
4. User toggle to light (regardless of OS) = light.

If Eric reverts to Phase 1-strict (light unconditional default), drop the `@media (prefers-color-scheme: dark)` block. The user toggle still works.

### Which tokens have direct dark mappings, which are re-derived

**Direct mapping (token has a `-dark` counterpart already defined in `02-color-direction.md`):**

- All surface tokens.
- All text tokens.
- All semantic tokens (success / warning / error / info).
- All border tokens.

**Re-derived (uses the same token name; the value swaps):**

- All spacing tokens — they don't change between modes.
- All radius tokens — don't change.
- All breakpoint tokens — don't change.
- All z-index tokens — don't change.

**Mode-aware (changes based on cascade):**

- Focus ring color (brand-500 light → brand-400 dark).
- Shadow tokens (entirely different stacks).
- Brand color usage on text — `brand-500` on light, `brand-300` on dark for body-text-color brand usage.

### Tailwind v4 `dark:` variant syntax

In Tailwind v4, the dark variant is configured via `@variant`:

```css
@variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));
```

Then in components:

```html
<div class="bg-surface-1 dark:bg-dark-surface-1 text-text-primary dark:text-dark-text-primary">
```

This is verbose. The cleaner approach (which I recommend) is to **reference the semantic token directly** and let the CSS variable cascade handle the swap:

```html
<div class="bg-[color:var(--color-surface-1)] text-[color:var(--color-text-primary)]">
```

With `--color-surface-1` defined to swap in dark mode automatically. No `dark:` variant needed in component code. This is the pattern Linear, Attio, and the Tailwind v4 reference apps use.

For the cleanest possible component code, the design system should ship **semantic Tailwind aliases**:

```css
@theme {
  /* Semantic surface aliases */
  --color-bg-page: var(--color-surface-0);
  --color-bg-card: var(--color-surface-1);
  --color-bg-recessed: var(--color-surface-2);
  --color-bg-overlay: var(--color-surface-overlay);
  --color-text-default: var(--color-text-primary);
  --color-text-subtle: var(--color-text-secondary);
  --color-text-muted: var(--color-text-tertiary);
  --color-border-default: var(--color-border-hairline);
}
```

Then in dark mode:

```css
:root[data-theme="dark"] {
  --color-bg-page: var(--color-dark-bg);
  --color-bg-card: var(--color-dark-surface-1);
  /* ... */
}
```

Components write `bg-bg-card` and the alias resolves correctly in both modes. **No `dark:` prefixes anywhere in component code.** This is the pattern engineering should ship against.

> *Handoff to `06-components.md`:* the semantic-alias pattern above is the recommended way for component CSS to reference colors. If a component genuinely needs mode-specific styling that the alias can't express (rare — usually shadow tokens), use the explicit `dark:` variant. Otherwise, the variant should not appear in component code.

---

## 12. Tailwind v4 implementation block

Paste-ready `@theme` block. Append below the existing color and typography blocks from `02-color-direction.md` and `03-typography-direction.md`. Together they form the complete `globals.css`.

```css
@import "tailwindcss";

/* Color and typography blocks live in their respective files. This block is the surface + spacing layer. */

@theme {
  /* === Spacing scale (4px base with 8px-bias) === */
  --spacing-0: 0;
  --spacing-0\.5: 0.125rem;   /* 2px */
  --spacing-1: 0.25rem;        /* 4px */
  --spacing-1\.5: 0.375rem;    /* 6px */
  --spacing-2: 0.5rem;         /* 8px */
  --spacing-2\.5: 0.625rem;    /* 10px */
  --spacing-3: 0.75rem;        /* 12px */
  --spacing-4: 1rem;           /* 16px */
  --spacing-5: 1.25rem;        /* 20px */
  --spacing-6: 1.5rem;         /* 24px */
  --spacing-8: 2rem;           /* 32px */
  --spacing-10: 2.5rem;        /* 40px */
  --spacing-12: 3rem;          /* 48px */
  --spacing-16: 4rem;          /* 64px */
  --spacing-24: 6rem;          /* 96px */

  /* === Surface tokens (semantic aliases — resolve to color tokens) === */
  --color-surface-0: var(--color-neutral-50);       /* page background */
  --color-surface-1: var(--color-neutral-0);        /* primary working surface */
  --color-surface-2: var(--color-neutral-50);       /* nested recessed surface */
  --color-surface-overlay: var(--color-neutral-0);  /* floating surface */

  /* === Semantic text aliases === */
  --color-text-primary: var(--color-neutral-700);
  --color-text-secondary: var(--color-neutral-500);
  --color-text-tertiary: var(--color-neutral-400);
  --color-text-strong: var(--color-neutral-900);

  /* === Border tokens === */
  --color-border-hairline: var(--color-neutral-200);
  --color-border-default: var(--color-neutral-300);
  --color-border-strong: var(--color-neutral-500);
  --border-width-default: 1px;

  /* === Border radii === */
  --radius-0: 0;
  --radius-1: 0.25rem;        /* 4px */
  --radius-2: 0.5rem;         /* 8px */
  --radius-3: 0.75rem;        /* 12px */
  --radius-4: 1rem;           /* 16px */
  --radius-full: 9999px;

  /* === Shadows (light mode, neutral-ink-tinted) === */
  --shadow-overlay-sm:
    0 1px 2px 0 rgba(38, 38, 36, 0.04),
    0 1px 3px 0 rgba(38, 38, 36, 0.06);
  --shadow-overlay-md:
    0 4px 6px -1px rgba(38, 38, 36, 0.06),
    0 2px 4px -1px rgba(38, 38, 36, 0.04),
    0 0 0 1px rgba(38, 38, 36, 0.04);
  --shadow-overlay-lg:
    0 10px 15px -3px rgba(38, 38, 36, 0.08),
    0 4px 6px -2px rgba(38, 38, 36, 0.04),
    0 0 0 1px rgba(38, 38, 36, 0.04);

  /* === Focus ring === */
  --focus-ring-color: var(--color-brand-500);
  --focus-ring-offset: 2px;
  --focus-ring-width: 2px;
  --focus-ring-offset-color: var(--color-surface-0);

  /* === Layout primitives === */
  --width-prose: 45rem;        /* 720px */
  --width-content: 67.5rem;    /* 1080px */
  --width-wide: 80rem;         /* 1280px */
  --sidebar-narrow: 4rem;      /* 64px */
  --sidebar-default: 15rem;    /* 240px */
  --sidebar-wide: 17.5rem;     /* 280px */
  --header-default: 3.5rem;    /* 56px */
  --header-compact: 3rem;      /* 48px */
  --header-display: 4.5rem;    /* 72px */

  /* === Breakpoints (override v4 default xl=1280 to 1200) === */
  --breakpoint-sm: 40rem;      /* 640px */
  --breakpoint-md: 48rem;      /* 768px */
  --breakpoint-lg: 64rem;      /* 1024px */
  --breakpoint-xl: 75rem;      /* 1200px — custom, was 1280 in v4 default */
  --breakpoint-2xl: 96rem;     /* 1536px */

  /* === Z-index scale === */
  --z-base: 0;
  --z-nav: 10;
  --z-sticky: 20;
  --z-dropdown: 30;
  --z-popover: 40;
  --z-modal: 50;
  --z-toast: 60;

  /* === Density runtime tokens (default = comfortable) === */
  --row-height: 2.75rem;       /* 44px */
  --button-height: 2.25rem;    /* 36px */
  --input-height: 2.25rem;     /* 36px */
  --card-padding: var(--spacing-4);
}

/* === Dark-mode token swaps === */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-surface-0: var(--color-dark-bg);
    --color-surface-1: var(--color-dark-surface-1);
    --color-surface-2: var(--color-dark-surface-2);
    --color-surface-overlay: var(--color-dark-surface-2);
    --color-text-primary: var(--color-dark-text-primary);
    --color-text-secondary: var(--color-dark-text-secondary);
    --color-text-tertiary: var(--color-dark-text-muted);
    --color-text-strong: var(--color-dark-text-ink);
    --color-border-hairline: var(--color-dark-border);
    --color-border-default: var(--color-dark-border-strong);
    --color-border-strong: var(--color-dark-text-muted);
    --focus-ring-color: var(--color-brand-400);
    --focus-ring-offset-color: var(--color-surface-0);

    --shadow-overlay-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.30);
    --shadow-overlay-md:
      0 4px 8px 0 rgba(0, 0, 0, 0.40),
      0 0 0 1px rgba(255, 255, 255, 0.04);
    --shadow-overlay-lg:
      0 12px 24px 0 rgba(0, 0, 0, 0.50),
      0 0 0 1px rgba(255, 255, 255, 0.04);
  }
}

:root[data-theme="dark"] {
  --color-surface-0: var(--color-dark-bg);
  --color-surface-1: var(--color-dark-surface-1);
  --color-surface-2: var(--color-dark-surface-2);
  --color-surface-overlay: var(--color-dark-surface-2);
  --color-text-primary: var(--color-dark-text-primary);
  --color-text-secondary: var(--color-dark-text-secondary);
  --color-text-tertiary: var(--color-dark-text-muted);
  --color-text-strong: var(--color-dark-text-ink);
  --color-border-hairline: var(--color-dark-border);
  --color-border-default: var(--color-dark-border-strong);
  --color-border-strong: var(--color-dark-text-muted);
  --focus-ring-color: var(--color-brand-400);
  --focus-ring-offset-color: var(--color-surface-0);

  --shadow-overlay-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.30);
  --shadow-overlay-md:
    0 4px 8px 0 rgba(0, 0, 0, 0.40),
    0 0 0 1px rgba(255, 255, 255, 0.04);
  --shadow-overlay-lg:
    0 12px 24px 0 rgba(0, 0, 0, 0.50),
    0 0 0 1px rgba(255, 255, 255, 0.04);
}

/* === Tailwind dark variant configuration === */
@variant dark (&:where([data-theme="dark"], [data-theme="dark"] *), &:where(:root:not([data-theme="light"]) *) where (prefers-color-scheme: dark));

/* === Density route-scoped overrides === */
[data-density="compact"] {
  --row-height: 1.875rem;      /* 30px */
  --button-height: 2rem;       /* 32px */
  --input-height: 2rem;        /* 32px */
  --card-padding: var(--spacing-3);
}

[data-density="display"] {
  --row-height: 3.5rem;        /* 56px */
  --button-height: 2.75rem;    /* 44px */
  --input-height: 2.75rem;     /* 44px */
  --card-padding: var(--spacing-6);
}

/* === Universal focus ring === */
:focus-visible {
  outline: none;
  box-shadow:
    0 0 0 var(--focus-ring-offset) var(--focus-ring-offset-color),
    0 0 0 calc(var(--focus-ring-offset) + var(--focus-ring-width)) var(--focus-ring-color);
}

@media (forced-colors: active) {
  :focus-visible {
    outline: 2px solid CanvasText;
    outline-offset: 2px;
    box-shadow: none;
  }
}
```

### Tailwind v4 caveats already flagged in `02-color-direction.md`

Three repeated here for completeness:

1. **No `theme.extend`.** `@theme` *replaces* the default Tailwind palette unless explicitly preserved. Combined with the color block from `02-color-direction.md`, any `text-red-500` or `bg-blue-100` in current code will silently break. Audit before pasting.
2. **The `@variant dark` syntax above is v4-specific.** The `:where()` pattern is required to keep specificity flat — otherwise `dark:` overrides chain badly through component cascades.
3. **`--spacing-0\.5` escaping.** Tailwind v4 accepts dotted spacing tokens but requires the dot to be escaped in the CSS variable name (or quoted in JS). The token resolves to `spacing-0.5` in utility class names (`p-0.5`, `m-0.5`). Verify the build tool doesn't strip the escape.

---

## 13. Mobile vs desktop — elevation pattern fallbacks

The brief flagged this: drop shadows on light backgrounds fade out under sunlight; subtle borders disappear on small screens. Specify the fallback per elevation level.

### `surface-0` (page)

- **Desktop:** `neutral-50` (`#FAFAF7`). Paper-warm.
- **Mobile:** same. No change. The page is the page.

### `surface-1` (card / primary working surface)

- **Desktop light mode:** `neutral-0` (white) + `border-hairline` (1px `neutral-200`). Border is the primary edge signal.
- **Desktop dark mode:** `dark-surface-1` + optional `dark-border` (tonal contrast does most of the work).
- **Mobile light mode (sunlight risk):** `neutral-0` + `border-default` (1px `neutral-300`, slightly darker). The `neutral-200` border can wash out at ~6500K daylight + low contrast viewing. Bumping to `neutral-300` keeps the edge visible. **This is a route-scoped override at the mobile breakpoint, not a separate token.**
- **Mobile dark mode:** `dark-surface-1` + `dark-border` (always on, even though desktop dark mode can omit it). On mobile dark, the tonal step alone is sometimes insufficient because the small screen makes the contrast harder to read at glance speed.

Implementation:

```css
@media (max-width: 768px) {
  :root {
    --color-border-hairline: var(--color-neutral-300);
  }
  :root[data-theme="dark"] {
    --color-border-hairline: var(--color-dark-border-strong);
  }
}
```

### `surface-2` (nested recessed)

- **Desktop:** `neutral-50` inside a `surface-1` card. No border between them — tonal step is the boundary.
- **Mobile light mode:** same. Tonal step is sufficient on mobile because the recessed surface is contained within an already-bordered card; the inner boundary doesn't need its own edge.
- **Mobile dark mode:** same.

### `surface-overlay` (floating)

- **Desktop light mode:** `neutral-0` + `shadow-overlay-md` + 1px hairline ring in the shadow stack.
- **Desktop dark mode:** `dark-surface-2` + dark shadow + white-tinted 1px ring.
- **Mobile light mode (critical):** `neutral-0` + `shadow-overlay-md` + **explicit `border-default` 1px `neutral-300`**. The shadow alone is unreliable under direct sunlight. The border is the fallback signal.
- **Mobile dark mode:** same as desktop dark — shadow + white-tinted ring is reliable on dark because there's no sunlight-wash risk (dark screens are darker than the environment regardless).

Implementation:

```css
.overlay {
  background: var(--color-surface-overlay);
  box-shadow: var(--shadow-overlay-md);
}

@media (max-width: 768px) {
  .overlay {
    border: 1px solid var(--color-border-default);
  }
}
```

### Focus rings

- **Desktop:** 2px ring at brand-500 (light) or brand-400 (dark). Sufficient contrast.
- **Mobile light mode:** same. The brand-500 ring at 6.85:1 contrast holds even under sunlight wash — color tinting is more sunlight-resistant than near-neutral shadows.
- **Mobile dark mode:** same as desktop dark.

### Banned mobile patterns

- **Shadow-only elevation on mobile.** Any overlay or popover on mobile must have an explicit border in addition to its shadow. Lint: any `box-shadow: var(--shadow-overlay-*)` without a paired border at the mobile breakpoint is flagged.
- **Subtle `neutral-200` borders on mobile.** Where borders carry semantic load on mobile, they must use `neutral-300` or stronger. The hairline border via cascade override above handles this for `surface-1`; for ad-hoc cases, designers should use `border-default` explicitly.

---

## 14. Out of scope (boundary with `06-components.md`)

This document specifies the underlying token system. The following are explicitly the UI Designer's lane in `06-components.md`:

- **Button component spec.** Sizes, states (rest / hover / active / disabled / loading), variants (primary / secondary / ghost / destructive). The button reads from `--button-height`, `--space-3`, `--radius-2`, `--focus-ring`. The component's *behavior* (hover transition timing, focus animation, loading-state spinner) is the UI Designer's call.
- **Form component spec.** Input, textarea, select, checkbox, radio, toggle. Read from `--input-height`, surface tokens, border tokens, focus ring. Component behavior (validation states, helper-text positioning, label association) is the UI Designer's call.
- **Card component spec.** Default card variants (informational vs interactive vs selected), card hover states, card internal layout patterns. Read from `surface-1`, `border-hairline`, `radius-2`, `card-padding`. Hover/selected behavior is the UI Designer's call.
- **Table component spec.** Row variants, sorting affordances, expandable rows, sticky headers. Reads from `row-height`, density tokens, surface tokens. Behavior is the UI Designer's call.
- **Modal / drawer / popover component spec.** Read from `surface-overlay`, `shadow-overlay-*`, `radius-3`. Animation, dismiss patterns, keyboard handling — UI Designer.
- **Toast component spec.** Read from `z-toast`, semantic colors. Timing, position, queueing — UI Designer.
- **Iconography library choice.** Cultural Strategy specified directional icons should have logical variants. The library itself is the UI Designer's call.
- **Motion system.** Transition durations, easing curves, animation principles. Entire scope of motion principles is the UI Designer's lane.

### Open questions to raise with the UI Designer before they finalize `06-components.md`

1. **Does the button respect density?** I've specified `--button-height: 36px` in comfortable and `32px` in compact, but the agent's primary action button (`Upload your SPA`-style) might want to stay at 36px even on a compact dashboard. Confirm.
2. **Does the table row hover-state need a defined transition duration?** I haven't specified motion tokens; that's your lane. Raise the question if the surface system would benefit from a baseline transition token.
3. **Does the empty-state container's dashed border use the same `border-hairline` color or a slightly darker variant?** Mid-ground decision. Default to `border-hairline`; override if the dashed pattern reads too faint.
4. **Should the focus ring offset color follow `surface-2` when the focused element is inside a recessed sub-panel?** The CSS-variable cascade handles this if `--focus-ring-offset-color` is locally overridden inside `surface-2` regions. Confirm whether you want this in the surface-recipe layer or in the component layer.

---

## 15. Summary of surface/spacing calls

For the synthesis pass.

1. **Spacing: 4px-base with 8px-multiple bias.** Scale: `0, 2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64, 96`. Five reserved 4px-only steps require code-review justification.
2. **Surfaces: 3 working + 1 overlay.** Stack via tonal lift + hairline border (Linear/Notion/Attio pattern). Shadow scoped to overlays only.
3. **Borders: 3 tokens, all 1px.** `border-hairline` is the default; emphasis comes from color, not width.
4. **Radii: softly-rounded.** `0, 4, 8, 12, 16, full`. `8px` is the workhorse. Attio/Stripe-dashboard register.
5. **Shadows: overlay-only.** Light mode = neutral-ink-tinted. Dark mode = darker rgba(0,0,0) + white-tinted 1px ring.
6. **Focus ring: 2px brand-500, 2px offset matching surface.** Light/dark color swap. Forced-colors mode defers to OS.
7. **Density: 3 modes via CSS variable cascade.** Comfortable (default), compact (route-scoped, brokerage owner dashboard), display (marketing).
8. **Layout: standardized content widths.** 720 / 1080 / 1280. Breakpoint `xl` shifted from v4 default 1280 → 1200 for dual-rail dashboard.
9. **Z-index: 7-step scale.** Lint-enforced.
10. **RTL: logical properties throughout.** Tailwind v4 `ms-/me-/ps-/pe-` utilities. Icon library should ship logical variants.
11. **Dark mode: system-preference default + sticky user override.** Designed in parallel via dual-cascade (media query + data-attribute).
12. **Tailwind v4 implementation: single `@theme` block.** Semantic aliases over raw color tokens in component code; minimizes `dark:` variant usage.
13. **Mobile fallbacks: borders strengthen on `surface-1` and `surface-overlay`.** Shadow-only elevation banned on mobile.

### Two pushbacks against Phase 1 raised

- **8px-strict grid → 4px-base hybrid.** Four specific surfaces fail 8px purity (form input padding, dense table rows, icon-in-pill gap, avatar-name gap). Hybrid with reserved 4px-only steps is more honest.
- **Light-default everywhere → system-preference default with sticky override.** The brokerage owner persona is the strongest case for dark-default, and Phase 1 lock predates the owner persona being fully specified.

Both pushbacks are revertible without re-architecture if Eric prefers Phase 1-strict.

---

*End of surface and spacing system.*
