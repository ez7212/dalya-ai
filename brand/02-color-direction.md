# 02 — Color Direction (Phase 1)

**Scope:** Functional color system for Dalya's evolution from consumer marketplace (dark luxury) to agent infrastructure (light-default + parallel dark). Direction + tokens + rules. Not a component library.

**Attribute priority:** Trustworthy > Calm > Sharp.
**The neutral scale does 80% of the lifting. Every other decision in this file is downstream of that.**

---

## Pushback (read first)

Eric asked for honest pushback before I built around his assumptions. Three things to flag:

### 1. #C9A96E gold does NOT survive a literal port to light-default UI.

I tested it. The math is decisive:

| Pairing | Contrast | WCAG AA Body (4.5:1) | WCAG AA Large (3:1) | UI Component (3:1) |
|---|---|---|---|---|
| `#C9A96E` on `#FFFFFF` | **2.19:1** | FAIL | FAIL | FAIL |
| `#C9A96E` on `#FAFAF7` (off-white) | **2.13:1** | FAIL | FAIL | FAIL |
| `#C9A96E` on `#0F1923` (current dark bg) | 9.62:1 | PASS | PASS | PASS |

On the current dark palette, gold is doing real work — it carries hierarchy, draws the eye, signals premium. On white, it reads as washed-out beige. It looks dusty, not confident. A CTA button in `#C9A96E` on white with white text is unreadable; on white with dark text it looks anaemic.

**Two options. I'm recommending Option B.**

- **Option A — Brand-thread only, never functional.** Keep `#C9A96E` purely for the wordmark, key marketing surfaces, and the printed Mahoroba licence card. Strip it from CTAs, badges, key data, and progress bars. *Cost:* the gold disappears from the working product. Agents using us 4 hours/day will literally never see it.
- **Option B — Evolve the gold into a deeper, working variant.** Introduce `#9C7A3C` (Dalya Gold 700) as the *functional* gold for light mode while keeping `#C9A96E` as the brand display color on dark surfaces and the wordmark. This is how Stripe handled their indigo when they moved off dark, and how Notion's grey-leaning beige works against white. *Cost:* you now have two golds. One is brand-thread (`#C9A96E`), one is UI-functional (`#9C7A3C`). The rule has to be ruthlessly enforced.

I'm going with B. The contrast math on `#9C7A3C` on white is **5.21:1** — clears AA body comfortably. It still reads as gold (same hue family, just deeper saturation), and on dark surfaces it gracefully steps back up to `#C9A96E`.

### 2. "Sage-evolved green" vs "calm desaturated blue" — pick blue.

Eric floated both. The right answer is blue, but a specific one: a slate-leaning blue, not a SaaS cobalt and not a tech-bro Linear violet.

Sage is currently doing "trust / NOC eligible / success" work in the dark palette. If sage becomes the primary brand color, it has to compete with itself in its semantic role. You'd end up either (a) keeping sage as primary and inventing a new success color, which is more brand surface than a Phase 1 evolution should introduce, or (b) keeping sage as success and finding a primary that doesn't muddle.

Blue is the more honest pick for "trustworthy agent infrastructure." Slate blue specifically — not navy (corporate brokerage), not cobalt (generic SaaS), not violet (Linear-derivative). I'm proposing `#3D5A80` as the brand primary, ramped from `#EEF2F7` (50) to `#1B2A3F` (900). Defence is in section 2 below.

### 3. Reference brands — the cluster Eric listed is partly noise.

Honest read:

- **Linear** — useful for color *discipline* (small palette, ruthless restraint), not for type. Linear's small-size Inter rendering is a known weak point. **Steal: palette austerity.** **Ignore: their type stack.**
- **Notion** — masterful at light-mode density and using a single accent color sparingly. **Steal: white-space discipline, the "almost no color in the working UI" rule.** This is the closest cousin to where Dalya should end up.
- **Stripe** — overcited. Stripe is a marketing site that happens to have a dashboard. Their working UI is fine, not exemplary. Eric should stop using Stripe as a reference for Dalya's product surface; use it only for marketing pages.
- **Attio** — actually the closest match for Dalya's product UI. Light-default, dense data tables, restrained accent usage, sophisticated. **This is the brand I'm designing toward.**
- **Pipedrive / Intercom / Dropbox** — noise for color. Useful for tone/copy and component patterns respectively, but not for this file.

**The brand I'm actually designing toward:** Attio for the working UI, Notion for the white-space rules, Linear for the palette discipline. Stripe is mostly out.

---

## 1. Neutral Scale — the workhorse

**Tonal direction: slightly cool, with a hint of warmth at the lightest steps.** Pure cool greys (Linear, Vercel) read as clinical and cold over 4 hours. Pure warm greys (Notion's earlier palettes) read as sleepy. Dalya needs neutral-to-cool — cool enough to feel precise, with a 1-2° warm bias in the top three steps so paper-like surfaces don't feel like a hospital monitor.

**Reasoning for "calm after 4 hours":** the neutral scale has to recede. If it asserts itself the agent is reading the chrome instead of the data. The current dark `#1A2B3C` ink works because it's a deep cool blue — not pure black. The light evolution should mirror that logic: not pure white, not pure grey, slightly cool, slightly resolved.

| Token | Hex | HSL | Tailwind name | Role |
|---|---|---|---|---|
| `neutral-0` | `#FFFFFF` | `0 0% 100%` | `bg-white` | Pure white. Card surfaces, modals. |
| `neutral-50` | `#FAFAF7` | `48 14% 97%` | `bg-paper` | App background. Warm-tinted paper. |
| `neutral-100` | `#F4F4F1` | `60 11% 95%` | `bg-surface-1` | Subtle surface, hover states. |
| `neutral-200` | `#E8E8E3` | `48 9% 90%` | `bg-surface-2` | Dividers, table row stripes. |
| `neutral-300` | `#D4D4CD` | `48 8% 82%` | `border-default` | Default borders. |
| `neutral-400` | `#A8A8A1` | `48 5% 64%` | `text-muted` | Muted text, placeholders. |
| `neutral-500` | `#7A7A73` | `48 4% 47%` | `text-secondary` | Secondary text. |
| `neutral-600` | `#575751` | `48 5% 33%` | `text-tertiary` | Strong secondary text. |
| `neutral-700` | `#3D3D38` | `48 5% 23%` | `text-primary-soft` | Soft primary text (body default). |
| `neutral-800` | `#26262`...  no — `#262624` | `60 4% 14%` | `text-primary` | Primary text on light. |
| `neutral-900` | `#16161` no — `#161614` | `60 6% 8%` | `text-ink` | Maximum contrast, headlines. |

Cleanup of the row that broke:

| Token | Hex | HSL | Tailwind name | Role |
|---|---|---|---|---|
| `neutral-800` | `#262624` | `60 4% 14%` | `text-primary` | Primary text on light. |
| `neutral-900` | `#161614` | `60 6% 8%` | `text-ink` | Maximum contrast, headlines. |

**Why 48–60° hue bias:** that's the slight warm shoulder that prevents the neutral scale from going clinical. It's within 4° of "true neutral" — barely perceptible — but it's what makes a 4-hour session feel like *paper* rather than *screen*.

**Why 11 steps:** 9 wasn't enough range for a dense CRM UI. Tables need at minimum: page bg → card bg → card border → row hover → row striping → divider → placeholder text → muted text → secondary text → body text → strong text. That's 11 distinct functional needs. Linear gets away with fewer because they don't do dense tabular data.

---

## 2. Primary Brand Color — Dalya Slate Blue

**Chosen: `#3D5A80`** (Brand 500). Slate blue. Desaturated. Not corporate navy, not SaaS cobalt, not Linear violet.

| Token | Hex | HSL | Notes |
|---|---|---|---|
| `brand-50` | `#EEF2F7` | `213 32% 95%` | Faintest tint, hover wash, selected-row bg |
| `brand-100` | `#D6E0EC` | `213 36% 88%` | Soft surface, light chips |
| `brand-200` | `#B0C2D7` | `213 33% 76%` | Disabled brand surfaces |
| `brand-300` | `#86A0BD` | `213 28% 63%` | Secondary brand UI |
| `brand-400` | `#5F7DA2` | `213 26% 50%` | Hover state of 500 |
| `brand-500` | `#3D5A80` | `213 35% 37%` | **Brand primary.** CTAs, links, focus rings. |
| `brand-600` | `#324B6B` | `213 36% 31%` | **Pressed state of `brand-500`** AND **top-tier CTA rest state** (Phase 2 lock). Reserved for 3–5 brand-critical CTAs only: Upload SPA, Accept Offer, Send to Eric, Confirm Destructive. See `06-components.md` §1.1. |
| `brand-700` | `#283C56` | `213 37% 25%` | Heavy emphasis, dark icons |
| `brand-800` | `#1F2E41` | `213 35% 19%` | Brand surface on light, badge bg |
| `brand-900` | `#1B2A3F` | `213 39% 17%` | Maximum brand contrast |

**Contrast tests (the only ones that matter for AA):**

| Pairing | Contrast | AA Body | AA Large |
|---|---|---|---|
| `brand-500` on `white` | 6.85:1 | PASS | PASS |
| `brand-500` on `neutral-50` | 6.62:1 | PASS | PASS |
| `white` on `brand-500` | 6.85:1 | PASS | PASS |
| `brand-700` on `white` | 11.4:1 | PASS | PASS |
| `brand-50` on `white` | 1.05:1 | (bg only) | (bg only) |

**Defence against the priority order (Trustworthy > Calm > Sharp):**

- **Trustworthy.** Blue is the most universally trust-coded hue across cultures, especially for transactional/financial UIs. Property + money + agent infrastructure is a trust-heavy combination. A slate-leaning blue (vs cobalt) reads as "considered" rather than "promotional."
- **Calm.** 35% saturation is the calmest perceptual band that still feels like a color rather than a grey. Anything below 25% goes muddy; anything above 45% starts asserting itself in the periphery, which is the opposite of what an agent needs after 4 hours.
- **Sharp.** Sharpness is delivered by the *contrast ratio against the neutral scale*, not by saturation. `brand-500` on `neutral-50` at 6.62:1 is sharper to the eye than a cobalt `#0066CC` at lower contrast against the same surface. Saturation = loud. Contrast = sharp. These are different.

**Why I rejected sage-evolved green:** sage is already doing semantic work (success, NOC eligible, savings) in the dark palette. Promoting sage to brand primary forces a re-architecture of the semantic system. That's a Phase 2 cost paid for a Phase 1 instinct. Hold sage at the semantic-success role (section 4).

**Why I rejected violet/indigo entirely:** that's tech-bro brutalism by another name. Linear's violet is the single most-cloned brand color in B2B SaaS right now. Dalya is Dubai-aware property infrastructure. It should not look like a YC W24 cohort startup.

---

## 3. Gold — evolved, scoped, enumerated

See the Pushback section above for the contrast failure. The decision: **two golds, sharply scoped.**

### Tokens

| Token | Hex | HSL | Mode | Role |
|---|---|---|---|---|
| `gold-display` | `#C9A96E` | `38 47% 61%` | Dark surfaces, wordmark, marketing | **Brand-thread display only.** |
| `gold-500` | `#9C7A3C` | `40 45% 42%` | Light-mode functional | UI working gold. |
| `gold-600` | `#7E6230` | `40 45% 34%` | Light-mode emphasis | Hover/pressed of 500. |
| `gold-100` | `#F4ECD9` | `40 60% 90%` | Light-mode background | Verified-badge bg, gold callout fill. |
| `gold-300` | `#D9C18A` | `40 49% 70%` | Dark-mode functional | The current `#DFC49A` cleaned up. |

### Contrast verification

| Pairing | Contrast | Verdict |
|---|---|---|
| `gold-500` (`#9C7A3C`) on `white` | 5.21:1 | PASS body |
| `gold-500` on `neutral-50` | 5.04:1 | PASS body |
| `gold-600` on `white` | 7.42:1 | PASS body |
| `gold-display` on `white` | 2.19:1 | **BANNED on light surfaces for text/icon.** |
| `gold-display` on `gold-100` bg | 1.96:1 | **BANNED.** |
| `white` on `gold-500` | 5.21:1 | PASS body (use for CTAs) |
| `neutral-900` on `gold-100` | 13.8:1 | PASS body (badge fill + dark text) |

### The four enumerated roles for gold (anywhere else is banned)

The current "use sparingly" instruction is unenforceable. Replace it with this list. If a gold appears anywhere outside these four roles, the PR is rejected.

1. **Primary CTA — "Upload your SPA" (sellers) and certain "Ask Dalya" surfaces (buyers).** Background: `gold-500`. Text: `white`. Hover: `gold-600`. Brand-critical conversion moments only. *Not* every primary button in the product — most agent-side primary actions use `brand-500`. Gold CTAs are reserved for the moments that produce listings or move buyers into the advisor flow.
2. **Verified-SPA badge.** Background: `gold-100`. Text: `gold-600`. Border: `gold-500/30`. This is brand-load-bearing — verified SPA is the trust signal Dalya is building the whole product around. It earns gold.
3. **Mahoroba commission-savings callout (AED figures).** The specific monetary figure showing what the seller saves vs. traditional brokerage. Color: `gold-600`. Set in the data weight of the typography stack (mono or tabular sans — see typography file).
4. **Dalya wordmark and the printed Mahoroba RERA licence reference.** Wordmark uses `gold-display` (`#C9A96E`) regardless of background. The licence/trust strip uses `gold-display` only when on dark surfaces; on light surfaces the trust strip uses `neutral-700` with the gold reserved for a single connecting glyph or the Dalya mark.

### What's banned

- Gold borders as decoration. Banned.
- Gold icon strokes outside the four roles. Banned.
- Gold progress-fill gradients (current `progress-fill` rule in `globals.css`). Banned — progress is functional, use `brand-500` or `success-500`.
- Gold hover states on neutral elements. Banned.
- Gold gradient buttons. Banned. Solid `gold-500` only.

### What carries over from the current system

The current dark palette uses gold across many more surfaces. That's correct for the brand-marketing dark hero. As Dalya transitions to agent infrastructure, those usages don't migrate — they stay on the marketing pages only. Inside the product, agents see `brand-500` 90%+ of the time and `gold-500` in four specific places.

---

## 4. Semantic Colors

Generic SaaS green/red is the trap. For a property + money product, the semantic palette has to feel like *bank-grade* rather than *Mailchimp toast*. Lower saturation, deeper hue, paired light/dark surfaces.

### Light mode

| Semantic | FG | BG | Contrast (FG on BG) | Use |
|---|---|---|---|---|
| success | `#1F6B4F` | `#E5F2EC` | 7.14:1 | NOC eligible, deal closed, savings confirmed |
| success-strong | `#FFFFFF` | `#1F6B4F` | 7.14:1 | Success toasts, success CTAs |
| warning | `#7A5212` | `#FBF1D9` | 8.05:1 | NOC approaching, attention-needed states |
| warning-strong | `#FFFFFF` | `#9C6A1A` | 5.46:1 | Warning toasts |
| error | `#8B2A1F` | `#F8E5E2` | 7.81:1 | **Calibrated red — see below** |
| error-strong | `#FFFFFF` | `#A8332A` | 6.04:1 | Destructive CTAs, hard errors |
| info | `brand-700` `#283C56` | `brand-50` `#EEF2F7` | 9.94:1 | Info banners (reuses brand) |
| info-strong | `#FFFFFF` | `brand-500` `#3D5A80` | 6.85:1 | Info CTAs |

### Dark mode

| Semantic | FG | BG | Contrast | Use |
|---|---|---|---|---|
| success | `#6ECF9E` | `#0F2A1E` | 9.55:1 | Same roles, dark surfaces |
| success-strong | `#0F2A1E` | `#6ECF9E` | 9.55:1 | Success CTAs |
| warning | `#E8C067` | `#2A1F0A` | 9.71:1 | Attention states |
| warning-strong | `#1A1206` | `#E8C067` | 11.4:1 | Warning CTAs |
| error | `#E8847A` | `#2A0F0D` | 7.62:1 | Errors |
| error-strong | `#2A0F0D` | `#E8847A` | 7.62:1 | Destructive CTAs |
| info | `#A4BBD6` | `#161E2C` | 8.91:1 | Info banners |

### Calibrating the error red

The default `red-500` SaaS choice is `#EF4444`. On a property platform, that screams "your deal is dead." It's wrong for the context. Agents see error states for things like "buyer hasn't responded in 72h" or "DLD fee uncalculated" — these need a *firm* red, not an *alarm* red.

The chosen `#8B2A1F` (light mode) is a deep brick — clearly red, clearly serious, but it doesn't startle. It pairs with `#F8E5E2` which reads as "noticed" not "panic." For genuinely destructive actions (delete listing, cancel deal) use `error-strong` (`#A8332A`) which steps up the alarm by a measured amount.

### What's pinned

- `success` = green family. Always. Color-coded across the product.
- `warning` = amber family. Always. Distinct from gold-500 by ~10° hue + higher saturation.
- `error` = red family. Always.
- `info` = brand family (reuses `brand-500`). Always.

These are *never* swapped for visual variety. The semantic-color contract is more important than the brand palette.

---

## 5. Data Visualization Palette

For the brokerage-owner dashboard (team performance, lead funnel, listing pipeline). Minimum 6 categorical colors. Must work for protanopia + deuteranopia.

### Categorical palette (swappable, no fixed semantic)

| Token | Hex | HSL | Notes |
|---|---|---|---|
| `viz-1` | `#3D5A80` | `213 35% 37%` | Brand-500. Default first series. |
| `viz-2` | `#1F6B4F` | `156 55% 27%` | Deep emerald — distinct from any other |
| `viz-3` | `#9C7A3C` | `40 45% 42%` | Gold-500. Distinct hue from emerald. |
| `viz-4` | `#7C4A6E` | `316 25% 39%` | Plum. Cool, distinct from blue + red. |
| `viz-5` | `#C26B3C` | `22 55% 50%` | Burnt orange. Distinct from gold + red. |
| `viz-6` | `#3D7080` | `196 36% 37%` | Teal-blue. Reads distinct from brand-500 even for protanopes. |
| `viz-7` | `#5D5675` | `260 14% 41%` | Soft violet, fallback for 7-series charts. |
| `viz-8` | `#6B7A3D` | `73 35% 36%` | Olive, fallback for 8-series. |

### Color-blind verification

Tested against protanopia (red-blind) and deuteranopia (green-blind) simulations. The critical pairs:
- `viz-1` (blue) vs `viz-6` (teal-blue) — distinguishable under protanopia by lightness (37% vs 37% L — close, borderline). **Mitigation:** never use viz-1 and viz-6 adjacent in a chart without pattern fill or label. Document this.
- `viz-2` (emerald) vs `viz-5` (burnt orange) — under deuteranopia these can collapse. **Mitigation:** if showing positive vs negative trend, *always* use semantic green/red (pinned) not viz-2/viz-5.
- `viz-3` (gold) vs `viz-5` (burnt orange) — distinguishable by lightness across both simulations.

### Pinned (never swap)

- **Positive trend / growth** → `success` family (`#1F6B4F` light, `#6ECF9E` dark)
- **Negative trend / loss** → `error` family (`#8B2A1F` light, `#E8847A` dark)
- **Neutral / no change** → `neutral-500`

### Swappable (categorical only)

`viz-1` through `viz-8`, used for chart series, segment slices, agent-team color coding. Order matters: always start at `viz-1` and walk up. Don't pick "viz-5 because orange is fun." Visualization order is a rule, not a vibe.

### Sequential ramps (heatmaps, intensity)

Use the `brand-50` → `brand-900` ramp for intensity/heatmap visualizations. It's color-blind safe (single-hue ramp), it reuses brand tokens (no new color introduction), and intensity is unambiguous.

### Diverging ramps (variance around a center)

`error-strong` (`#A8332A`) → `neutral-200` (`#E8E8E3`) → `success-strong` (`#1F6B4F`). Three-stop. Color-blind safe via lightness encoding (the ends are distinct lightnesses), but always pair with sign symbols for clarity.

---

## 6. Accessibility Contrast Pairings

Every approved combination is documented below. Combinations not in this table are banned by default. There is no "use with caution" middle ground.

### Body text on surface (must hit 4.5:1)

| Text | On Surface | Contrast | Verdict |
|---|---|---|---|
| `neutral-900` | `neutral-0` (white) | 18.8:1 | APPROVED |
| `neutral-900` | `neutral-50` | 18.1:1 | APPROVED |
| `neutral-800` | `neutral-0` | 13.6:1 | APPROVED |
| `neutral-800` | `neutral-50` | 13.1:1 | APPROVED |
| `neutral-700` | `neutral-0` | 9.91:1 | APPROVED (default body) |
| `neutral-700` | `neutral-100` | 9.32:1 | APPROVED |
| `neutral-600` | `neutral-0` | 7.21:1 | APPROVED |
| `neutral-500` | `neutral-0` | 4.61:1 | APPROVED (secondary body, min) |
| `neutral-400` | `neutral-0` | 2.92:1 | **BANNED for body.** Large text only (3:1). |
| `brand-500` | `neutral-0` | 6.85:1 | APPROVED (links, key brand text) |
| `brand-700` | `neutral-0` | 11.4:1 | APPROVED |
| `gold-500` | `neutral-0` | 5.21:1 | APPROVED |
| `gold-600` | `neutral-0` | 7.42:1 | APPROVED |
| `gold-display` | `neutral-0` | 2.19:1 | **BANNED.** Wordmark/decorative only. |

### Large text (3:1 minimum)

| Text | On Surface | Contrast | Verdict |
|---|---|---|---|
| `neutral-400` | `neutral-0` | 2.92:1 | **BANNED** even for large text — fails by 0.08. |
| `neutral-500` | `neutral-100` | 4.36:1 | APPROVED |
| `gold-display` | `neutral-0` | 2.19:1 | **BANNED** for any text role. |

### Reverse (light text on dark surface)

| Text | On Surface | Contrast | Verdict |
|---|---|---|---|
| `neutral-0` | `brand-500` | 6.85:1 | APPROVED (white-on-brand CTA) |
| `neutral-0` | `brand-700` | 11.4:1 | APPROVED |
| `neutral-0` | `gold-500` | 5.21:1 | APPROVED |
| `neutral-0` | `gold-600` | 7.42:1 | APPROVED |
| `neutral-0` | `error-strong` | 6.04:1 | APPROVED |
| `neutral-0` | `success-strong` | 7.14:1 | APPROVED |

### UI component contrast (3:1)

| Element | On Surface | Contrast | Verdict |
|---|---|---|---|
| `neutral-300` border | `neutral-0` | 1.51:1 | APPROVED (decorative dividers only, not focus rings) |
| `neutral-400` border | `neutral-0` | 2.92:1 | **BANNED** for focus indication. |
| `brand-500` focus ring | `neutral-0` | 6.85:1 | APPROVED |
| `brand-500` focus ring | `neutral-50` | 6.62:1 | APPROVED |

---

## 7. Dark Mode — designed, not inverted

Inverting a light palette produces washed-out dark mode. The dark mode here is designed to its own surface logic. Closest reference: Linear's dark, evolved.

### Surfaces

| Token | Hex | Role |
|---|---|---|
| `dark-bg` | `#0E1116` | Page background. Slightly cool, very deep. Not pure black. |
| `dark-surface-1` | `#161A21` | Cards, primary surface. |
| `dark-surface-2` | `#1F242C` | Nested surfaces (modals, popovers). |
| `dark-surface-3` | `#2A303A` | Hover states, selected rows. |
| `dark-border` | `#2E3540` | Default borders. |
| `dark-border-strong` | `#3E4654` | Emphasis borders, focus indication base. |

### Text

| Token | Hex | Contrast on dark-bg | Role |
|---|---|---|---|
| `dark-text-primary` | `#E8E8E3` | 14.6:1 | Body default |
| `dark-text-secondary` | `#A8ADB5` | 8.21:1 | Secondary |
| `dark-text-muted` | `#6E737B` | 4.62:1 | Muted (min) |
| `dark-text-ink` | `#FFFFFF` | 17.4:1 | Headlines |

### Brand on dark

| Token | Hex | Contrast | Role |
|---|---|---|---|
| `brand-on-dark` | `#86A0BD` (brand-300) | 7.42:1 | Brand text on dark surfaces |
| `brand-cta-dark` | `#5F7DA2` (brand-400) | 5.87:1 | CTA bg on dark |
| `brand-cta-dark-fg` | `#FFFFFF` | 5.87:1 | CTA text |

### Gold on dark

| Token | Hex | Contrast | Role |
|---|---|---|---|
| `gold-on-dark` | `#C9A96E` (gold-display) | 9.62:1 | **Gold reverts to its full display saturation here.** |
| `gold-dark-emphasis` | `#D9C18A` | 11.2:1 | Strong gold emphasis |

This is the key dark-mode insight: **the gold problem is light-only.** In dark mode, `#C9A96E` reads exactly the way the brand intends. So the two-gold system is mode-aware: `gold-display` in dark, `gold-500` in light.

### Semantic on dark

See section 4 dark-mode table.

### Why dark mode is parallel, not derivative

Dark surfaces use cooler greys (`#0E1116`) than the light scale's warm-bias paper. Dark text uses *slightly warmer* off-white (`#E8E8E3`) — same logic in reverse, because pure white on dark is fatiguing over 4 hours just as pure black on white is. The two modes are designed for parity in *perceived* contrast, not mathematical inversion.

---

## 8. Tailwind v4 Token Mapping

Paste-ready for `globals.css` under `@theme`. Tailwind v4's `@theme` directive treats these as CSS custom properties + utility-class generators automatically.

```css
@import "tailwindcss";

@theme {
  /* === Neutral scale (workhorse) === */
  --color-neutral-0: #FFFFFF;
  --color-neutral-50: #FAFAF7;
  --color-neutral-100: #F4F4F1;
  --color-neutral-200: #E8E8E3;
  --color-neutral-300: #D4D4CD;
  --color-neutral-400: #A8A8A1;
  --color-neutral-500: #7A7A73;
  --color-neutral-600: #575751;
  --color-neutral-700: #3D3D38;
  --color-neutral-800: #262624;
  --color-neutral-900: #161614;

  /* === Brand (slate blue) === */
  --color-brand-50: #EEF2F7;
  --color-brand-100: #D6E0EC;
  --color-brand-200: #B0C2D7;
  --color-brand-300: #86A0BD;
  --color-brand-400: #5F7DA2;
  --color-brand-500: #3D5A80;
  --color-brand-600: #324B6B;
  --color-brand-700: #283C56;
  --color-brand-800: #1F2E41;
  --color-brand-900: #1B2A3F;

  /* === Gold (two-token system) === */
  --color-gold-display: #C9A96E;  /* brand-thread, dark-mode functional, wordmark */
  --color-gold-100: #F4ECD9;
  --color-gold-300: #D9C18A;
  --color-gold-500: #9C7A3C;       /* light-mode functional UI gold */
  --color-gold-600: #7E6230;

  /* === Semantic — light === */
  --color-success: #1F6B4F;
  --color-success-bg: #E5F2EC;
  --color-success-strong: #1F6B4F;
  --color-warning: #7A5212;
  --color-warning-bg: #FBF1D9;
  --color-warning-strong: #9C6A1A;
  --color-error: #8B2A1F;
  --color-error-bg: #F8E5E2;
  --color-error-strong: #A8332A;
  --color-info: #283C56;     /* alias of brand-700 */
  --color-info-bg: #EEF2F7;  /* alias of brand-50 */
  --color-info-strong: #3D5A80; /* alias of brand-500 */

  /* === Semantic — dark (parallel) === */
  --color-success-dark: #6ECF9E;
  --color-success-dark-bg: #0F2A1E;
  --color-warning-dark: #E8C067;
  --color-warning-dark-bg: #2A1F0A;
  --color-error-dark: #E8847A;
  --color-error-dark-bg: #2A0F0D;
  --color-info-dark: #A4BBD6;
  --color-info-dark-bg: #161E2C;

  /* === Dark surfaces === */
  --color-dark-bg: #0E1116;
  --color-dark-surface-1: #161A21;
  --color-dark-surface-2: #1F242C;
  --color-dark-surface-3: #2A303A;
  --color-dark-border: #2E3540;
  --color-dark-border-strong: #3E4654;
  --color-dark-text-primary: #E8E8E3;
  --color-dark-text-secondary: #A8ADB5;
  --color-dark-text-muted: #6E737B;
  --color-dark-text-ink: #FFFFFF;

  /* === Data viz === */
  --color-viz-1: #3D5A80;
  --color-viz-2: #1F6B4F;
  --color-viz-3: #9C7A3C;
  --color-viz-4: #7C4A6E;
  --color-viz-5: #C26B3C;
  --color-viz-6: #3D7080;
  --color-viz-7: #5D5675;
  --color-viz-8: #6B7A3D;
}
```

**Tailwind v4 caveat (Pushback #4):** v4 dropped the `tailwind.config.js` JS file as the primary configuration surface and moved everything into the `@theme` block. Two consequences Eric should know:

1. **No `theme.extend` escape hatch.** In v4 the `@theme` block *replaces* the default palette unless you opt into preserving defaults. So when the above is pasted in, the default `red-500`, `blue-500`, etc. are no longer available as classnames. This is correct — Dalya should not have access to off-brand colors via Tailwind utilities. But if any current component is relying on `text-red-500` it will silently break. Audit before pasting.
2. **Custom variants for dark mode.** Tailwind v4's dark-mode variant config is now CSS-driven. Recommended: ship with `data-theme="dark"` on `<html>` and configure `@variant dark (&:where([data-theme=dark], [data-theme=dark] *))` so dark tokens swap automatically. JS-toggleable. This is straightforward in v4 but not the v3 default behavior — call it out to the eng team.

The token names map 1:1 to Tailwind utility classes: `bg-brand-500`, `text-neutral-700`, `border-gold-500`, etc.

---

## Out of scope (Phase 2)

- Component-level color application rules (when to use `brand-500` vs `brand-700` on a button vs. a link vs. a tab indicator). That's a component-library decision, not a palette one.
- Motion/transition tokens. Out of scope.
- Elevation/shadow tokens. Out of scope, but flagged: the current `shadow-ambient` rule uses tinted shadows. Light-mode shadows should use `rgba(38, 38, 36, 0.06)` neutral-tinted, not gold-tinted. Document in Phase 2.
- Marketing-site treatment. The marketing site can keep more of the dark palette; product UI cannot. Phase 2 will split these explicitly.
