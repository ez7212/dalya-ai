# Dalya — Component Direction

*Phase 2 deliverable. Read [`PHASE-1-LOCK.md`](./PHASE-1-LOCK.md), [`02-color-direction.md`](./02-color-direction.md), [`03-typography-direction.md`](./03-typography-direction.md), and [`05-surface-spacing.md`](./05-surface-spacing.md) first. This document specifies component behavior and content patterns on top of the surface and token system already locked.*

---

## How to read this document

This is not a Figma library or a code library. It is the point of view every component built for Dalya conforms to. For each component class: **purpose, anatomy, states, variants, when to use, when not to use, accessibility rules, Tailwind v4 implementation notes.**

A component that follows the surface tokens but violates the behavior rules here is not a Dalya component. Engineering and design both review against this.

The four open questions from `05-surface-spacing.md` §14 are answered inline at the relevant component (search this doc for "OQ-1" through "OQ-4").

---

## 0. Two pushbacks against the Phase 1 locks

### 0.1 Slate blue alone is undersupplied to carry the system.

Gold is fully retired. Slate blue `#3D5A80` (brand-500) is now the sole brand-driven UI color carrier — every primary button, every focus ring, every selected state, every primary badge, every wordmark surface. This is a lot of work for one color, and the color is a calm, desaturated mid-tone by deliberate brand choice. In the surface system the neutrals do 80% of the lifting; brand-500 fights for visibility against `neutral-50` (page background) at AA contrast (5.78:1 — passes, but not commanding).

**The risk:** the component library reads as "competent but bland." Slate-blue CTAs do not pull the eye the way gold CTAs did in the dark-luxury system. Brokerage owners scanning a dense dashboard for the next action will work harder than they did before. After 4 hours of use this becomes fatiguing in the opposite direction from what gold was — not too strong, but too quiet to navigate by.

**What I'd recommend** (Eric's call): introduce a **brand-600 variant at `#324B6B`** (deeper, more saturation) reserved specifically for *brand-critical primary CTAs only* (Upload SPA, Accept Offer, Send to Eric, Confirm). Not for every primary button. The cascade is:

- brand-500 (`#3D5A80`) — focus rings, links, selected states, secondary primary buttons, wordmark, brand-thread accent
- brand-600 (`#324B6B`) — first-priority CTAs only (3–5 across the entire product)
- brand-400 (`#5A7BA0`) — dark-mode focus ring (already in the system per `02-color-direction.md`)

This keeps slate blue as the brand color but gives the component library a deliberate visual anchor for the moments that matter. It is *not* gold by another name — it stays inside the slate family and inherits the calm posture. It is the *one* visual escalation the system allows.

If Eric rejects this, the alternative is to accept that brand-critical CTAs read at the same visual weight as a sidebar link, and lean harder on typography weight (Semibold-on-Medium) and spatial dominance (larger touch targets, more white-space around) to carry hierarchy. Workable but more design discipline per-screen.

### 0.2 The token system over-defines too early.

Eric explicitly demanded "component-first system with tokens and rules." I agree on tokens. I push back on freezing every component token before Phase 3 application examples expose them to real content.

**Tokens that are stable now and should be frozen this phase:**
- All color tokens (from `02`)
- All spacing scale tokens (from `05`)
- All surface tokens (from `05`)
- All border, radius, shadow, focus-ring tokens (from `05`)
- All typography scale tokens (from `03`)
- Z-index scale (from `05`)
- Button height, input height, row height density mappings (specified in this doc, §1 + §2 + §3)

**Tokens that should remain in component scope until Phase 3:**
- Per-component intra-padding for cards, modals, toasts (specified here as defaults; Phase 3 may reveal a need for variants)
- Conversation bubble dimensions (the chat surface is content-shape-dependent; defaults specified, free to evolve)
- Table column-priority order per route (cannot be specified abstractly)
- Empty-state illustrations (deferred entirely — see §9)
- Hover-transition timing (specified here; may need per-component override)

If the team treats every default in this document as a frozen token, the system calcifies. Treat color/spacing/surface as immutable; treat component dimensions as defaults with override rights when real content forces it.

---

## 1. Buttons

The most touched component in the product. Every other rule cascades off how this one behaves.

### 1.1 Variants — five and only five

| Variant | When to use | Color treatment |
|---|---|---|
| **Primary** | The one action this surface wants the user to take. Maximum one per surface (see §1.4). | `bg-brand-600 text-white` (per pushback 0.1). On dark: `bg-brand-500 text-white`. |
| **Secondary** | Equally important actions that aren't the *one* recommended path. Confirm/cancel pairs. Form submit alongside cancel. | `bg-surface-1 border-default text-text-1`. Hover: `bg-surface-2`. |
| **Tertiary (ghost)** | Inline actions inside cards/tables/lists. Most agent-surface actions. | `bg-transparent text-text-1`. Hover: `bg-surface-1`. |
| **Destructive** | Irreversible or hard-to-reverse actions. Delete listing, reject offer, sign out. Always paired with explicit confirmation. | `bg-error-600 text-white`. Always paired with the destructive confirmation pattern (§1.6). |
| **Icon-only** | Toolbar actions where the icon is unambiguous and a label would be redundant. Close, copy, expand. Always has `aria-label`. | `bg-transparent text-text-2`. Hover: `bg-surface-1 text-text-1`. |

There is no "outline" variant. There is no "link" variant. Links that look like links are link components (§1.7), not buttons.

### 1.2 Sizes — three, density-respecting

| Size | Height | Padding | Use |
|---|---|---|---|
| `md` (default) | `36px` comfortable / `32px` compact | `px-3 py-2` comfortable / `px-3 py-1.5` compact | All standard product UI |
| `sm` | `28px` (no density variant) | `px-2.5 py-1` | Inline actions in dense surfaces, table row buttons |
| `lg` | `44px` (no density variant) | `px-4 py-2.5` | Marketing, signed-out states, primary CTA in onboarding |

**OQ-1 answer: primary CTAs respect density.** A primary button on the brokerage dashboard (compact mode) is `32px`, not `36px`. Visual consistency with the surrounding row heights outweighs the marginal touch-target gain. The only exception: primary CTAs that are also *mobile* actions stay at `36px` regardless of density mode (touch target floor).

`lg` does not have a compact variant — it is a marketing/onboarding size and those surfaces ship in display density.

### 1.3 States

Every variant has six states. They must be visually distinct under both monochrome (color-blindness friendly) and color rendering.

1. **Rest** — base appearance per §1.1.
2. **Hover** — desktop only. Background lifts one tonal step (Primary brand-600 → brand-700; Secondary surface-1 → surface-2; etc.). Transition: `transition-colors duration-120 ease-out` (see `07-motion.md`).
3. **Active (pressed)** — momentary. Background drops one tonal step. No motion delay — transitions instantly so the press feels physical.
4. **Focus-visible** — keyboard focus only. Uses the system focus ring (`focus-ring` token from `05`). Must be present alongside any background/color change, not instead of.
5. **Disabled** — `opacity-50 cursor-not-allowed`. Disabled buttons never render with their semantic color (a disabled destructive button is not red — it's neutral).
6. **Loading** — replaces the label with an inline spinner. Button width is preserved so the page does not reflow. Disabled while loading; click ignored.

**Banned:** scale-on-hover, bounce-on-press, gradient backgrounds on rest, glow effects, any motion longer than 200ms on state change.

### 1.4 The "one primary per surface" rule

A primary button signals *the single most important action this surface is asking for.* If a surface has two equally-weighted actions, both are secondary. If a surface has none, no button is primary.

This rule is enforced because primary-button proliferation is how SaaS dashboards become visually shouty. Linear ships exactly one primary per surface. Notion sometimes ships two when the surface is genuinely bimodal (Save + Share). Eric's brokerage dashboard probably qualifies as bimodal (Approve Listing | Reject Listing) — in those cases, ship two *destructive-paired-with-primary*, not two primaries.

**Audit question for design review:** "If a brand-new user landed here, what would they expect to do first?" The answer is what gets `bg-brand-600`. Everything else is secondary, tertiary, or ghost.

### 1.5 Microcopy — verbs

Buttons are verbs. Verb-first, no "please," no "click here," no exclamation marks.

| Good | Bad |
|---|---|
| Upload SPA | Click to upload SPA |
| Accept offer | Yes, accept this offer |
| Send to Eric | Please send to Eric |
| Save changes | Save your changes! |
| Cancel | Go back |

Length: 1–3 words. If 4+ words are needed, the action is probably ambiguous and the surface needs a tooltip or helper text *outside* the button, not inside.

### 1.6 Destructive confirmation pattern

Every destructive action requires a confirmation step. The pattern:

1. User clicks destructive button.
2. A confirmation modal opens (not a popover, not an inline confirm — see §5.1).
3. Modal title states the action: *"Delete this listing?"* (not "Are you sure?").
4. Modal body states the consequence in specific terms: *"5 active buyer conversations on this listing will be archived. You cannot recover this listing once deleted."*
5. Confirmation button uses destructive variant and **repeats the action verb**, not "Confirm" or "Yes." Label is `Delete listing`, not `Confirm`.
6. Cancel button uses secondary variant. Default focus is on Cancel, not on the destructive button.
7. For irreversible high-stakes actions (delete account, revoke RERA permit), require typing the entity name to enable the destructive button.

### 1.7 Buttons vs links

| | Button | Link |
|---|---|---|
| Action | Mutates state (submit, save, delete, accept) | Navigates (go to listing, open offer, view conversation) |
| Color | Per §1.1 variants | `text-link` (`#3D5A80` brand-500 with underline-on-hover) |
| Cursor | `cursor-pointer` | `cursor-pointer` |
| Inline in prose | Never | Yes |

A "Delete" word that looks like blue text and underlines on hover is not a destructive button. It is a link that mutates state, which is the worst of both worlds. Use the destructive variant button.

### 1.8 Tailwind v4 implementation

```css
/* @theme — already in 05-surface-spacing.md @theme block */
--button-height-md: 36px;
--button-height-md-compact: 32px;
--button-height-sm: 28px;
--button-height-lg: 44px;
```

```tsx
// Primary button — md, comfortable density
<button className="
  h-[var(--button-height-md)] px-3 py-2 rounded-2
  bg-brand-600 text-white font-medium text-sm
  hover:bg-brand-700 active:bg-brand-700
  focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2
  disabled:opacity-50 disabled:cursor-not-allowed
  transition-colors duration-120 ease-out
">
  Upload SPA
</button>

// Compact density inherits via the surface's data-density attribute
// data-density="compact" on the parent route lowers --button-height-md
```

---

## 2. Form inputs

The agent and the brokerage owner spend non-trivial time in forms. SPA upload, asking-price edits, threshold settings, profile, listing notes. Every input is a daily-use surface.

### 2.1 Anatomy

```
┌─────────────────────────────────────────┐
│ Label (required *)                       │  ← text-sm, font-medium, text-text-2
│                                          │
│ ┌─────────────────────────────────────┐ │
│ │ Input field                          │ │  ← h-input-md, surface-1, border-hairline
│ └─────────────────────────────────────┘ │
│                                          │
│ Helper text or error message            │  ← text-xs, text-text-3 (helper) or text-error (error)
└─────────────────────────────────────────┘
```

**Label position:** above the input, always. No floating labels (they fail accessibility audits, break under translation, and break under autofill). No labels-inside-input (same reasons).

**Required marker:** `*` after the label text, in `text-brand-500`. Not "required" in parens. Not red.

**Helper text:** below the input, always. When error state, replaces helper text with error message in `text-error`.

### 2.2 Sizes and density

| Size | Height (comfortable) | Height (compact) | Padding |
|---|---|---|---|
| `md` (default) | `36px` | `32px` | `px-3 py-2` / `px-3 py-1.5` |
| `sm` | `28px` (no compact variant) | — | `px-2.5 py-1` |
| `lg` | `44px` | — | `px-4 py-3` |

Input height mirrors button height per density — a button next to an input in the same row must visually align without `align-items` hacks.

### 2.3 Variants

| Variant | When to use |
|---|---|
| **Text** | All free-form text shorter than ~80 characters |
| **Textarea** | Multi-line text (seller notes, conversation drafts). Default `rows=3`, autosize up to `rows=8` then scroll. |
| **Number (AED)** | Asking price, threshold, commission. Specific rules in §2.5. |
| **Number (count)** | Bedroom count, days on market, unit number. No prefix, no comma formatting until 4+ digits. |
| **Select** | 2–10 options. Native `<select>` on mobile; custom dropdown on desktop where searchability adds value. |
| **Multi-select** | Tags, area preferences, bedroom preferences. Pill-based with `×` to remove each. |
| **Search** | Free-form filtering of lists. Always with a search-icon prefix and a clear-icon suffix when populated. |
| **Date** | Use the native `<input type="date">` on mobile; custom date picker on desktop. Never custom on mobile — iOS/Android natives are better. |
| **File upload** | SPA upload. Drag-drop zone is the default surface; click-to-browse is a fallback. Specific rules in §2.6. |
| **Toggle / Switch** | Boolean settings (notification on/off). Never use a checkbox where a toggle is semantically right. |
| **Checkbox** | Multi-select boolean choices (assign to multiple agents). Never for single on/off. |
| **Radio** | Single choice from a small set (2–5). For 6+, use Select. |

### 2.4 States

Same six as buttons (§1.3): rest, hover, active, focus, disabled, loading. Plus two input-specific:

- **Error** — border swaps to `border-strong` in `border-error` color (per `02-color-direction.md`). Error message renders below. Focus ring on error inputs uses the error color, not brand.
- **Filled** — visual distinction is *optional*. Some products make filled inputs slightly more prominent; Dalya does not — the value text inside is the only distinction needed.

### 2.5 AED input rules — brand-critical

The AED input is the single most-used number in the product. The rules:

1. **Prefix "AED"** rendered inside the input on the left, in `text-text-3` (muted) so it doesn't compete with the user's value. The user does not type "AED"; they type the number.
2. **Comma formatting on type.** As the user types `1850000`, the visible value formats to `1,850,000` after each digit. The underlying value stays unformatted. Comma is the thousands separator in EN/RTL Arabic both — no locale override.
3. **Slashed-zero stylistic set enabled** on AED inputs specifically: `font-feature-settings: "tnum", "ss01"` per `03-typography-direction.md`. Reduces 0/O confusion for high-stakes financial entries.
4. **No currency symbol confusion.** Never render "AED" as a separate label *and* a prefix simultaneously. The prefix is the label for currency; the form-field label states *what AED amount* (Asking Price, Threshold, Commission).
5. **Validation:** must be a positive number. Maximum 11 digits (`99,999,999,999` covers Dubai real estate in lifetime values). Decimal allowed but not required — Dalya is whole-AED by default; fils-level precision is opt-in per form.
6. **Mobile keyboard:** `inputMode="decimal"` not `inputMode="numeric"` (allows the decimal separator).
7. **Paste handling:** if the user pastes `AED 1,850,000 (negotiable)` we strip everything except digits and decimal, then re-format. We do not reject the paste with an error.

```tsx
<div className="relative">
  <span className="absolute inset-y-0 left-3 flex items-center text-text-3 text-sm pointer-events-none">
    AED
  </span>
  <input
    type="text"
    inputMode="decimal"
    className="
      h-input-md w-full pl-14 pr-3 rounded-2
      bg-surface-1 border-hairline text-text-1 text-sm
      tabular-nums [font-feature-settings:'tnum','ss01']
      focus:border-default focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2
    "
    placeholder="1,850,000"
  />
</div>
```

### 2.6 File upload rules

SPA upload is the entry path for every seller-side workflow. The rules:

1. **Drag-drop zone is the default surface.** Center-aligned. Dashed border (`border-default`, dashed). Min height `200px`. Hover state: solid border `border-brand-500`, background tint `bg-brand-50`.
2. **Click-to-browse is the fallback.** Tappable on mobile (the whole zone is a click target). On desktop, also clickable.
3. **File-type validation:** accept `application/pdf, image/jpeg, image/png`. Reject everything else with an inline error: *"PDF, JPG, or PNG only."*
4. **File-size validation:** 25 MB cap. Reject larger with: *"File is over 25 MB. Compress the PDF or contact Eric."*
5. **Selected state:** when a file is chosen, the drop zone collapses into a single row showing filename, size, and a `×` to remove. Below the row, a primary button continues the action (`Continue`, `Parse SPA`).
6. **Loading state:** mirrors `SellerUpload.tsx` existing pattern — five-stage progress (`Uploading → Analyzing → Extracting → Processing → Finalizing`) with a determinate progress bar. Estimated 15–30 seconds. Show the filename throughout.
7. **No "browse" verb in placeholder copy.** Use *"Drop your SPA here, or click to choose a file."*

### 2.7 Auto-focus rules

- **First field in a single-purpose form** (search, login, SPA upload zone) — auto-focus on mount.
- **Modal with a primary input** (set threshold, edit note) — auto-focus on open.
- **Multi-field forms** (settings, listing details) — no auto-focus. The user picks where to start.
- **Re-mount of an already-edited form** (back navigation, route re-entry) — no auto-focus. The user's last position is preserved.

### 2.8 Banned input patterns

- Floating labels.
- Labels inside the input field.
- Required indicator as the word "(required)" — use the `*`.
- Error message that appears on every keystroke before submit. Validate on blur, not on input.
- Three-character minimum on the search input. Search every keystroke after one character.
- "Show password" toggle without a corresponding `aria-label`.

---

## 3. Tables & data lists

The brokerage owner's dashboard is mostly tables. The agent's pipeline view is a card list that is a table in disguise. Density matters here more than anywhere.

### 3.1 Surface treatment

Tables sit on `surface-1` (card-like). The table itself does not paint its own background; the surrounding card does. Borders inside the table use `border-hairline`. The first and last row do not have outer borders (the card edge handles it).

### 3.2 Row heights

| Density | Row height | Use |
|---|---|---|
| Comfortable | `48px` | Agent's working surface, default. Mobile default. |
| Compact | `36px` | Brokerage owner dashboard, dense data. Set via `data-density="compact"` on the route. |
| Display | `64px` | Marketing tables (rare). |

Row height includes padding. Cell content uses `text-sm` (14px) in comfortable, `text-xs` (12px) in compact. Numerical cells always use tabular-nums.

### 3.3 Header treatment

- Header row uses `text-xs uppercase tracking-widest text-text-3 font-medium`. Subtle, not shouty.
- Header row is `surface-2` (recessed) to read as distinct from data rows without a heavy color shift.
- Sortable column headers get a `↕` glyph (subtle, `text-text-3`). Active sort gets `↑` or `↓` in `text-text-1`.
- Sticky header on scroll. Use `position: sticky; top: 0` with z-index `z-sticky`.

### 3.4 Row states

| State | Treatment |
|---|---|
| Rest | `bg-transparent` (inherits surface-1 from container) |
| Hover | `bg-surface-2`. Cursor `pointer` if the row is clickable. Transition: `transition-colors duration-100 ease-out` (OQ-2 answer: 100ms hover for table rows; faster than buttons because table rows are scanned, not focused). |
| Active (pressed/clicked) | `bg-surface-2` lingers; `border-l-2 border-brand-500` appears on the left edge as a selection mark. |
| Selected | Same as active. Selection persists until the row is deselected. |
| Focus (keyboard) | Focus ring around the entire row (`focus-ring` token), no background change. |

### 3.5 Cell content rules

- **AED amounts** use tabular-nums + slashed-zero. Right-align all numeric columns. Always.
- **Names and free text** left-align. Never center-align prose.
- **Status pills** (see §8) center-align in their column. The column header for a status column is also center-aligned.
- **Action buttons** in a row use icon-only or ghost variant. Right-align in the cell. Never primary inside a table row — the primary is the row click itself.
- **Truncation:** single-line by default. Use `truncate` Tailwind utility. Tooltip on hover shows the full text only when truncation occurred (detect via `scrollWidth > clientWidth`).

### 3.6 Empty, loading, error states

| State | Treatment |
|---|---|
| Empty (no data) | Centered illustration-free message in `text-text-3`. Headline `text-sm font-medium`, body `text-xs`. Optional CTA. Example: *"No conversations yet. Listings go live in 30 minutes."* (See §9 for the empty-state pattern.) |
| Loading (first load) | Skeleton rows matching the row count of the previous load (or 8 rows if first). Skeleton uses `bg-surface-2 animate-pulse-skeleton`. (See `07-motion.md`.) |
| Loading (sort/filter) | Existing rows stay; a top loading-bar appears (height `2px`, `bg-brand-500`, indeterminate). |
| Error | Replaces the table content with a centered error block: icon, message, retry button. Specific: *"Couldn't load conversations. Retry."* |
| Partial error (some rows missing) | The rows we have render; a top warning banner explains: *"4 of 12 rows failed to load. Retry."* |

### 3.7 Mobile fallback — pick one and ship it

Tables don't work natively on mobile. Three patterns; pick per-table based on content:

- **Card collapse.** Each row becomes a card stacked vertically. The most common Dalya pattern (conversations list, listings list). Default for content-rich rows.
- **Column-priority hiding.** On `md` and below, hide columns ranked priority 3+. On `sm` and below, hide priority 2+. The brokerage dashboard pattern (analytics tables).
- **Horizontal scroll.** Last resort. Used only for tables that genuinely need all columns visible at once (transaction ledger, paperwork status grid).

Each table component declares its mobile strategy as a prop or config. No table renders the same on desktop and mobile by default.

### 3.8 Tailwind v4 implementation

```tsx
<div className="bg-surface-1 border-hairline rounded-2 overflow-hidden">
  <table className="w-full text-sm">
    <thead className="bg-surface-2">
      <tr>
        <th className="
          px-3 py-2 text-left text-xs uppercase tracking-widest
          text-text-3 font-medium border-b-hairline
        ">
          Property
        </th>
        {/* ...more headers */}
      </tr>
    </thead>
    <tbody>
      <tr className="
        h-row-comfortable
        hover:bg-surface-2 transition-colors duration-100
        border-b-hairline last:border-b-0
        data-[selected=true]:bg-surface-2
        data-[selected=true]:border-l-2 data-[selected=true]:border-brand-500
      ">
        <td className="px-3">Palace Villas Ostra · Unit 2805</td>
        {/* ...more cells */}
      </tr>
    </tbody>
  </table>
</div>
```

---

## 4. Cards & surfaces

A card is a unit of content with its own surface. The product is mostly cards.

### 4.1 Three card classes

| Class | Behavior | Use |
|---|---|---|
| **Informational** | No hover, no click. Displays a fact. | Stat cards on dashboard, NOC status card, SPA summary card. |
| **Interactive** | Whole card is clickable. Hover lifts via `surface-2` background. | Listing card, conversation card, persona card. |
| **Selected/Active** | Persistent state showing which item is currently focused. | Selected listing in a sidebar list, active conversation in chat list. |

### 4.2 Surface treatment

Cards sit on `surface-1` per `05-surface-spacing.md`. Container is `surface-0`. The visual lift is the tonal shift between surface-0 and surface-1, plus the hairline border. No shadow on rest state. (Shadows are reserved for overlays per `05` §5.)

### 4.3 Intra-card spacing

To prevent every team building cards differently, the intra-card padding rule:

```
┌──────────────────────────────────────────┐
│  ← px-card / py-card → (24px comfortable, 16px compact)
│                                           │
│  Card header                              │ ← text-base font-semibold
│  Subtle subhead                           │ ← text-xs text-text-3, mt-1
│                                           │ ← mb-card-section (20px comfortable, 16px compact)
│  ─────────────────────────────────       │ ← border-hairline divider (optional)
│                                           │
│  Card body content                        │
│                                           │
│  Footer actions or metadata               │ ← mt-card-section
│                                           │
└──────────────────────────────────────────┘
```

Tokens:
```css
--card-padding: 24px;           /* comfortable */
--card-padding-compact: 16px;   /* compact */
--card-padding-display: 32px;   /* marketing */
--card-section-gap: 20px;       /* comfortable */
--card-section-gap-compact: 16px;
```

Cards use `radius-3` (12px) by default. `radius-2` (8px) in compact density.

### 4.4 Card hover and selection behavior

| State | Treatment |
|---|---|
| Rest (interactive card) | `surface-1`, `border-hairline`, `cursor-pointer` |
| Hover | `bg-surface-2`, `border-default`. Subtle. Transition: `120ms` ease-out. No transform/scale. |
| Active (click pressed) | No additional visual — feedback comes from the navigation occurring |
| Selected (persistent) | `border-l-2 border-brand-500` on the left edge, `surface-2` background. Keeps the user oriented when they return. |
| Focus (keyboard) | Focus ring around the whole card |

**Banned card behaviors:**
- Lift-on-hover (translateY, increased shadow). Distracting in dense lists.
- Color-shift-on-hover that goes beyond surface tones (e.g. brand-tinted hover backgrounds). Cards are not buttons.
- Hover effects on `display`-density cards (marketing pages). Hover-state isn't load-bearing on signed-out surfaces.

### 4.5 Listing card content pattern

The listing card is one of the highest-touched components — agents scan a list of them dozens of times a day.

```
┌──────────────────────────────────────────┐
│ Project name · Unit number         [pill]│  ← title row, status pill right-aligned
│                                           │
│ AED 17,253,444                           │  ← asking price, font-mono tabular-nums, slashed-zero
│                                           │
│ 5BD · 8,500 sqft · The Oasis             │  ← spec row, text-text-3, dot separators
│                                           │
│ 12 leads · 3 escalated · Last activity 2h │  ← activity row, text-text-3
└──────────────────────────────────────────┘
```

- Pill in the top-right shows listing status (Live, Draft, Sold, Blocked). Hidden when status is `pending_review` per Eric's directive.
- Activity row uses relative time on hover-revealed absolute time (see voice/tone for time-formatting rules in `08`).
- Whole card is clickable; primary action is "open detail." No inline buttons.

### 4.6 Stat card pattern (dashboard)

```
┌──────────────────────────────────────────┐
│ TOTAL LISTINGS                            │ ← uppercase, tracking-widest, text-xs, text-text-3
│                                           │
│ 14                                        │ ← text-3xl, font-bold, font-mono, tabular-nums
│                                           │
│ +2 this week ↗                           │ ← optional delta, text-xs, color-coded
└──────────────────────────────────────────┘
```

- The number is the hero. Everything else is metadata.
- Color the delta only when it's directionally meaningful. Positive deltas use `text-success`, negative `text-error`. Neutral changes (e.g. no change) stay in `text-text-3`.
- Never gold. The previous design used gold for stat values; we use `text-text-1` neutrals.

---

## 5. Modals, overlays, popovers, tooltips, sheets

The default of every team is "modal for everything." We resist.

### 5.1 Modal — only when state must be confirmed before continuing

Use a modal when:
- The user must explicitly confirm or cancel before any other action becomes possible.
- The form is small (1–5 fields) and would feel out-of-place inline.
- The action is destructive (per §1.6).

Do **not** use a modal for:
- Showing additional information (use a popover or expand-in-place).
- Multi-step flows (use a dedicated page or a wizard).
- Anything the user might want to reference while doing something else.

Anatomy:
- Background overlay: `bg-black/30` (light mode), `bg-black/50` (dark mode).
- Modal surface: `surface-overlay` token from `05`, `radius-3` (12px), max-width `560px` (default; can override per modal).
- Header: title (text-lg, font-semibold) + `×` close button right-aligned. Close button is icon-only ghost.
- Body: padded `px-card py-card`.
- Footer: actions right-aligned, cancel left of confirm. Mobile: actions full-width stacked.

States:
- Mount: appears with the modal entry motion (see `07-motion.md`).
- Background scroll-locks while modal is open. `overflow: hidden` on body.
- Escape key dismisses (unless typing in an active field).
- Click-outside dismisses for informational modals; does NOT dismiss for confirmation modals (user must explicitly cancel).
- Focus trapped inside the modal while open. First focusable element gets focus on mount (or the dismissive button for destructive modals, per §1.6).

Mobile fallback: full-screen sheet (slides up from bottom, occupies viewport). Header gains a chevron-down dismiss in addition to `×`. Confirm/cancel pinned to the bottom of the sheet.

### 5.2 Sheet (side drawer) — for context that supplements but doesn't replace

Use a sheet when:
- The user is doing something on the page and wants to see related context without losing their place (e.g. opening a buyer profile from a conversation list).
- The context is too long for a popover but doesn't require a full page transition.

Slide-in from right on desktop (width `480px` default, `max-w-md`). Slide-up from bottom on mobile (full width, max-height `90vh`).

Same scroll-lock rules as modals. Click-outside dismisses by default.

### 5.3 Popover — for inline expansion

Use a popover when:
- The user clicks an element to reveal a small contextual control (date picker, filter dropdown, action menu).
- The content is small enough to fit in a ~320px wide box.

Popovers anchor to their trigger. Use `surface-overlay`, `shadow-overlay-sm`, `radius-2`. Click-outside dismisses. No scroll-lock.

### 5.4 Tooltip — rarely allowed

Tooltips are over-used and degrade accessibility (mobile users can't trigger them, keyboard users get fragile reveal-on-focus). Allowed in three cases only:

1. **Truncated text reveal.** A table cell shows `truncate`d content; hover reveals the full string. Click does nothing.
2. **Icon-only button label.** An icon button's `aria-label` content can also render as a tooltip on hover. The `aria-label` itself is the source of truth.
3. **Disabled-state explanation.** A disabled button explains *why* it's disabled. *"NOC pending — unavailable until SPA verified."*

Banned tooltip uses: explaining a label, replacing a help-text below a form field, showing a definition that a user might want to dwell on (use a popover or inline expansion).

Tooltip styling: `surface-overlay` (very subtle), `shadow-overlay-sm`, `radius-1` (4px), `text-xs`, max-width `240px`. Show delay `400ms` on hover. Dismiss on mouse-leave or anywhere-click.

### 5.5 Toast — transient feedback

Use a toast when:
- An asynchronous action has completed (offer sent, listing approved).
- A non-blocking failure occurred (offer save failed; retry in toast).
- A real-time event occurred while the user was elsewhere (new offer received).

Toast anatomy:
- Single line, max 2 lines, `text-sm`.
- Optional icon (success / warning / error / info).
- Optional action button (`Retry`, `View`, `Undo`).
- Auto-dismiss timing: 4 seconds (success), 6 seconds (info), 8 seconds (warning), never auto-dismiss (error). Hovering pauses the dismiss timer.
- Stack: max 3 visible at once; older ones fade out earliest.
- Position: bottom-right on desktop, top on mobile (where bottom is reserved for thumb actions).

Z-index: `z-toast` (above modals per `05` §9).

### 5.6 Banned overlay patterns

- Modal opening a modal opening a modal. Two-deep is the max; three-deep means the flow is broken and needs to be redesigned as a page.
- Multiple toasts of the same type queueing (collapse to "+3 more" indicator).
- Popovers that look like tooltips. Tooltips are decorative; popovers are interactive. Visual distinction is mandatory.

---

## 6. Conversation / chat surfaces

This is core product. The agent reads buyer-Dalya conversations and intervenes when escalated. Voice/tone for the bot itself is in `BOT_RULES.md`; voice/tone for the agent's intervention is in `08-voice-tone.md`.

### 6.1 Three senders, three patterns

Every message has one of three senders:

| Sender | Bubble alignment | Background | Text color | Notes |
|---|---|---|---|---|
| **Buyer** | Left | `surface-2` | `text-text-1` | Default. Most messages. |
| **Dalya** (the AI) | Left, distinct from buyer | `surface-1` with `border-l-2 border-brand-500` | `text-text-1` | Dalya is on the same side as the buyer because both are "incoming" from the agent's perspective. The left border distinguishes. |
| **Agent** (live intervention) | Right | `bg-brand-50` (light tint) | `text-text-1` | When the human agent steps in. Visually different enough to be unmistakable, restrained enough not to feel like a chat app. |

Sender labels appear above each bubble in `text-xs text-text-3`. Buyer's name (if known), "Dalya," or the agent's first name.

### 6.2 Message bubble anatomy

```
┌──────────────────────────────────────────┐
│ Buyer name · 14:23                       │ ← sender + timestamp, text-xs text-text-3
│ ┌──────────────────────────────────┐    │
│ │  Message body text. Wraps.       │    │ ← bubble, text-sm, surface as per §6.1
│ └──────────────────────────────────┘    │
└──────────────────────────────────────────┘
```

- Bubble has `radius-2` (8px), `border-hairline` matching the surface.
- Max width: `560px` desktop, `100%` mobile (with side padding).
- Padding: `px-3 py-2`.
- AED amounts inside message text use `tabular-nums slashed-zero` automatic via CSS (inherits from chat container).
- Long messages (>800 chars) collapse with "Show more" / "Show less" toggle.

### 6.3 Timestamp grouping rule

Showing a timestamp on every message creates visual noise. The rule:

- **First message of a session** (no prior messages or >30 min gap): show absolute time. *"Today at 14:23"* or *"Yesterday at 09:11"* or *"Apr 14 at 14:23"*.
- **Subsequent messages within 5 minutes**: no timestamp shown.
- **Subsequent messages after 5 minutes**: show relative offset. *"+12 min."*
- **Date boundary**: insert a centered date separator. *"— Tuesday, Apr 15 —"*

### 6.4 Inline data cards

When Dalya surfaces structured data inside a conversation (an offer, a Verified-SPA snippet, a listing reference, a NOC status), it renders as an **inline data card** *inside* the Dalya bubble.

```
┌─────────────────────────────────────────────┐
│ Dalya · 14:23                                │
│ ┌──────────────────────────────────────┐   │
│ │  Sure — here's the asking summary:    │   │
│ │                                        │   │
│ │  ┌──────────────────────────────┐    │   │ ← inline data card, surface-2 inside surface-1 bubble
│ │  │ ASKING PRICE                  │    │   │
│ │  │ AED 17,253,444                │    │   │
│ │  │ NOC eligible · 30% paid       │    │   │
│ │  └──────────────────────────────┘    │   │
│ │                                        │   │
│ │  Want me to send the floor plan too?  │   │
│ └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

Inline data cards use `surface-2`, `border-hairline`, `radius-2`. They are interactive when relevant — clicking opens the relevant detail page in the agent's working surface.

### 6.5 Escalation indicator

When a message triggers an escalation (per `BOT_RULES.md`), a thin `2px` bar appears on the left of the relevant Dalya bubble in the escalation color (per `02-color-direction.md`'s semantic palette). The escalation type renders as a small pill above the bubble: *"OFFER RECEIVED"*, *"BYPASS ATTEMPT"*, *"BRN REQUEST"*.

### 6.6 "View in working surface" entry point

The chat is a read surface. Action happens elsewhere. When Dalya surfaces an actionable item (an offer to accept, a buyer to call, a SPA to review), there's a *single* "View in working surface" link below the data card. This jumps the agent to the relevant detail page with the conversation still accessible in a side sheet.

### 6.7 Typing indicator — NO

We don't render a typing indicator for Dalya. Reasons:
- It lies about latency. Dalya doesn't "think slowly" the way a human does.
- It implies a longer response is coming, which is sometimes false.
- It creates an emotional dynamic (waiting on the bot) that the agent's working surface should not encourage.

When Dalya is generating a response, the only visible state is the message arriving. If latency exceeds 6 seconds, a single static text *"Dalya is preparing a response..."* appears in the agent's surface only, with a subtle pulse animation. Not in the buyer-facing surface.

### 6.8 Mobile chat behavior

On mobile, the chat takes the full viewport minus a fixed header (back + buyer name + status). The composer is pinned to the bottom. The list scrolls; the composer doesn't.

### 6.9 Banned chat patterns

- Sender avatars. The product is not WhatsApp. Names are sufficient.
- Read receipts. Privacy-coded, unnecessary for an agent's read surface.
- Reactions / emoji. The agent's intervention is verbal, not iconographic.
- Threading inside a conversation. Linear thread only.
- "Is Dalya typing..." animated dots. See §6.7.

---

## 7. Navigation patterns

Three nav contexts: agent working surface, brokerage owner dashboard, listing detail.

### 7.1 Agent working surface (mobile-first, also desktop)

Pattern: **"hot list" sidebar + detail view.** Linear's pattern.

Desktop layout:
```
┌──────────────────────────────────────────────────────────┐
│ [Dalya wordmark]            [search]      [user menu]    │ ← top bar, 56px, surface-1
├──────────────────────────────────────────────────────────┤
│         │                                                 │
│ Convos  │  Detail view (conversation, listing, profile)  │
│ ──────  │                                                 │
│ Active  │                                                 │
│  - Sara │                                                 │
│  - Tom  │                                                 │
│  - …    │                                                 │
│ Recent  │                                                 │
│ Archived│                                                 │
└─────────┴─────────────────────────────────────────────────┘
  240px wide          flex-1
```

- Sidebar: `240px` wide, `surface-1`, `border-r-hairline`.
- Sidebar items: 3 sections (Active, Recent, Archived). Each is a list of conversation cards in compact density (`36px` row height).
- Active conversation gets the selected state per §4.4 (left border + surface-2).
- Mobile: sidebar becomes a full-screen drawer triggered by a back-arrow on the detail view. Drawer slides from left.

### 7.2 Brokerage owner dashboard (desktop-first)

Pattern: **tabbed analytics + left rail.**

Desktop layout:
```
┌──────────────────────────────────────────────────────────┐
│ [Dalya wordmark]            [search]      [user menu]    │
├──────────┬───────────────────────────────────────────────┤
│          │ Overview | Listings | Agents | Reports        │ ← tab nav, 44px
│ Filters  │ ──────────────────────────────────            │
│ All time │                                                │
│ Q2 2026  │  Dashboard content (stat cards + tables)      │
│ Custom   │                                                │
│          │                                                │
│ Agents   │                                                │
│ All      │                                                │
│ Tom      │                                                │
│ Sara     │                                                │
└──────────┴───────────────────────────────────────────────┘
   220px            flex-1
```

- Tab nav: underline-on-active (Stripe pattern). Active tab has `border-b-2 border-brand-500 text-text-1`. Inactive: `text-text-3`.
- Left rail: filters (date range, agent, status). Persistent across tabs.
- Mobile: tabs become a horizontal scrollable bar; filters become a top-of-content collapsible drawer.

### 7.3 Listing detail (both audiences)

Pattern: **tabbed sub-pages on a single route.**

```
Back to My Listings
Palace Villas Ostra · Unit 2805
─────────────────────────────────
Overview | Offers | SPA Data | Activity
─────────────────────────────────
[Tab content]
```

- Tabs use the same underline pattern as §7.2 for consistency.
- On mobile, tabs become a horizontal scrollable bar.
- The "Back to" link is `text-xs text-text-3 hover:text-text-1` with a left chevron.

### 7.4 Wordmark in nav chrome

The Dalya wordmark renders as slate blue (per Phase 1 lock — gold fully retired). In nav chrome:

- Height: `28–32px` depending on context.
- Position: top-left, padded with `px-4 py-3`.
- Click-target: links to the user's home (agent → conversations list; owner → dashboard).
- Must not visually compete with primary CTAs. Solution: render at 80% opacity by default on dense surfaces; 100% on signed-out and marketing surfaces.

### 7.5 Mobile bottom nav — NO

The product is not consumer-grade. The brokerage workflow has too many distinct contexts (conversations, listings, activity, settings, dashboard) for a 4-icon bottom bar. Use the drawer + back navigation pattern instead.

---

## 8. Status indicators

CRM-grade products are heavy with status. We use four shape primitives and ban interchange.

### 8.1 The four shapes

| Shape | Use | Example |
|---|---|---|
| **Pill** (rounded full, with text) | Persistent status that the user reads to understand current state | Listing status: Live, Draft, Sold |
| **Badge** (small, with count) | Count of items needing attention | Sidebar nav: "3" next to Activity |
| **Dot** (8px circle) | Real-time presence or alert state | Pulse next to an active conversation |
| **Progress** (bar or ring) | Quantitative progress through a known total | NOC payment progress (30% paid) |

### 8.2 Pill variants

Pills use the semantic color palette from `02-color-direction.md`. Per Phase 1, the Verified-SPA badge and NOC-eligible pill (previously gold) use sage `bg-sage-100 text-sage-700` with a `✓` glyph.

| Pill | Color treatment | When |
|---|---|---|
| Live | `bg-success-50 text-success-700` | Listing is live |
| Draft | `bg-surface-2 text-text-3` | Listing is in draft |
| Sold | `bg-surface-2 text-text-3` (de-emphasized) | Listing has sold |
| Blocked | `bg-error-50 text-error-700` | Listing has a blocking issue |
| Verified SPA | `bg-sage-100 text-sage-700` with `✓` | SPA has been verified |
| NOC Eligible | `bg-sage-100 text-sage-700` | NOC threshold met |
| NOC Pending | `bg-copper-50 text-copper-700` | Approaching NOC threshold |
| New Offer | `bg-brand-50 text-brand-700` | Offer received in last 24h |
| Above Asking | `bg-success-100 text-success-800` | Offer is at or above asking |
| Below Asking | `bg-surface-2 text-text-3` | Offer is below asking (no alarm — typical) |
| Far Below | `bg-error-50 text-error-700` | Offer is 15%+ below asking |

Note: `pending_review` is hidden per Eric's directive (no pill rendered).

### 8.3 Offer status pill set

Per the bot's escalation model:

| Pill | Color |
|---|---|
| New | `bg-brand-50 text-brand-700` |
| Forwarded | `bg-surface-2 text-text-3` |
| Countered | `bg-copper-50 text-copper-700` |
| Accepted | `bg-success-50 text-success-700` |
| Declined | `bg-error-50 text-error-700` (de-emphasized) |
| Withdrawn | `bg-surface-2 text-text-3` (de-emphasized) |
| Superseded | `bg-surface-2 text-text-3` with strikethrough on the AED amount |

### 8.4 Dot indicators

Use sparingly. Dots draw the eye; if everything has a dot, nothing does.

- **Active conversation** (currently being responded to by the bot): `bg-brand-500` pulse.
- **Unread escalation**: `bg-error-500` no pulse.
- **Online presence** (future feature for owner viewing agents): `bg-sage-500` no pulse.

### 8.5 Progress

- **Bar** for known totals (NOC payment progress, SPA upload). Height `4px`, `radius-full`, color `bg-brand-500` filled segment, `bg-surface-2` track.
- **Ring** for compact contexts (sidebar metrics). 32px diameter, 2px stroke, same color treatment.
- **Indeterminate bar** for loading without known total. 2px height, sliding gradient.

### 8.6 Banned status patterns

- Two pills next to each other on the same row. Pick one.
- Pill with an emoji or icon that duplicates the color meaning (e.g. red pill + 🛑 emoji).
- Animated pills (other than the dot pulse).
- Pills inside table cells in compact density larger than `text-xs`.

---

## 9. Loading & skeleton states

The agent and owner are tolerant of latency in real-estate workflows (SPA parsing takes 15–30s). They are intolerant of blank screens.

### 9.1 Three patterns

| Pattern | When |
|---|---|
| **Skeleton** | First load of a page or component. Use when you know the shape of what's coming. |
| **Spinner (inline)** | Action loading state inside a button. Use when the action has a clear endpoint. |
| **Progress bar** | Multi-step or determinate operations (SPA parsing, file upload). |
| **Nothing** | When the operation completes in <200ms. Don't flash a loader. |

### 9.2 Skeleton anatomy

Skeleton uses `bg-surface-2` (not `bg-surface-1` — must visually contrast against the card it sits in) with the `animate-pulse-skeleton` motion (see `07-motion.md`).

Rules:
- Match the rough shape of the content. Text lines = `h-3 rounded-1` bars in varied widths (75%, 90%, 60%). Card title = `h-5 rounded-1` bar. AED amount = `h-7 rounded-1` bar.
- Match the row count from last load if known; default 4–6 rows for tables, 2–3 cards for card lists.
- Skeleton-to-content swap is instant (no fade). Layout shift is minimized by close shape-matching.

### 9.3 Empty state pattern

Empty states are not loading states. The rule:

- **Headline**: `text-sm font-medium text-text-1`. Single sentence stating what's not here. *"No conversations yet."*
- **Body**: `text-xs text-text-3`. Single sentence explaining why or what next. *"Listings go live in 30 minutes. Buyers will start messaging."*
- **CTA** (optional): Single primary or secondary button. Use only when there's a clear action the user can take. Often there isn't — empty is just empty.
- **No illustration.** Phase 2 ships without empty-state illustrations. Phase 3 may add them; we don't pre-design that surface.

**OQ-3 answer:** the empty-state dashed border uses `border-hairline` color (same as default borders), not a darker variant. Default to faint; the headline and body do the communicating, not the container.

### 9.4 Error state pattern

- Icon (`text-error-500`, `24px`).
- Headline: `text-sm font-medium`. *"Couldn't load this conversation."*
- Body: `text-xs text-text-3`. *"Check your connection, then retry."*
- Action: secondary button. *"Retry."*

Never blame the user. Never expose stack traces. Never use the word "Error" as the headline — describe what happened.

---

## Cross-references and handoffs

Tokens that this document defines (and that `05-surface-spacing.md` deferred):

- `--button-height-md`, `--button-height-md-compact`, `--button-height-sm`, `--button-height-lg`
- `--input-height-md`, `--input-height-md-compact`, `--input-height-sm`, `--input-height-lg`
- `--row-height-comfortable`, `--row-height-compact`, `--row-height-display`
- `--card-padding`, `--card-padding-compact`, `--card-padding-display`
- `--card-section-gap`, `--card-section-gap-compact`

**OQ-2 answer (motion for hover transitions):** specified inline:
- Button hover: `120ms ease-out`
- Card hover: `120ms ease-out`
- Table row hover: `100ms ease-out` (faster — table rows are scanned, buttons are decided)
- Selection state changes: instant (no transition)

These motion timings are confirmed in `07-motion.md`.

**OQ-4 answer (focus-ring offset in nested surface-2 regions):** the focus-ring offset color follows the *immediate* parent surface, not the page surface. Implementation: each surface utility class overrides `--focus-ring-offset-color` to match itself. Component code never needs to know — the cascade handles it.

---

## What is *not* in this document

Deferred to Phase 3 (application examples):
- Per-route layouts (login screen, signup, settings sub-pages, admin pages)
- Per-feature components (the offer-acceptance wizard, the SPA upload wizard, the listing creation flow)
- Iconography library choice
- Empty-state illustrations
- Marketing site components

Deferred to `07-motion.md`:
- Motion timing tokens, easing curves, the full ban list
- Reduced-motion fallbacks for each component class

Deferred to `08-voice-tone.md`:
- All microcopy phrasing rules, banned/required phrases
- Time and AED formatting conventions in prose
- Voice register across surfaces
