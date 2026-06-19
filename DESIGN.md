---
name: Dalya
description: B2B AI infrastructure for Dubai brokerages — a calm, trustworthy operating layer for agents.
colors:
  brand-slate: "#3D5A80"
  brand-slate-cta: "#324B6B"
  brand-slate-pressed: "#283C56"
  brand-slate-wash: "#EEF2F7"
  brand-slate-soft: "#D6E0EC"
  sage: "#4A7C6F"
  sage-tint: "#D0E1DD"
  sage-ink: "#2F5048"
  copper: "#B7793A"
  copper-tint: "#F4DFC8"
  copper-ink: "#7A4F25"
  brick: "#B84838"
  brick-tint: "#EFCFC8"
  brick-ink: "#7A2A1F"
  surface-page: "#FAFAF9"
  surface-card: "#F4F4F2"
  surface-recessed: "#E8E8E5"
  surface-white: "#FFFFFF"
  ink-primary: "#3D3D39"
  ink-secondary: "#5C5C57"
  ink-muted: "#7B7B76"
  border-hairline: "#E8E8E5"
  border-default: "#D6D6D2"
typography:
  display:
    fontFamily: "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "clamp(40px, 6vw, 60px)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "clamp(28px, 4vw, 40px)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  body-large:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "-0.005em"
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.12em"
  mono:
    fontFamily: "IBM Plex Mono, SF Mono, Consolas, monospace"
    fontSize: "13px"
    fontWeight: 400
    fontFeature: "tnum, ss01"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  "2xl": "48px"
  "3xl": "96px"
components:
  button-primary:
    backgroundColor: "{colors.brand-slate-cta}"
    textColor: "{colors.surface-white}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
    height: "36px"
  button-primary-hover:
    backgroundColor: "{colors.brand-slate-pressed}"
    textColor: "{colors.surface-white}"
  button-secondary:
    backgroundColor: "{colors.brand-slate}"
    textColor: "{colors.surface-white}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.ink-primary}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  card:
    backgroundColor: "{colors.surface-page}"
    rounded: "{rounded.lg}"
    padding: "24px"
  input:
    backgroundColor: "{colors.surface-page}"
    textColor: "{colors.ink-primary}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  chip:
    backgroundColor: "{colors.brand-slate-wash}"
    textColor: "{colors.brand-slate-pressed}"
    rounded: "{rounded.sm}"
    padding: "2px 6px"
---

# Design System: Dalya

## 1. Overview

**Creative North Star: "The Calm Operating Layer"**

Dalya is the quiet operating layer around a Dubai agent's day. The visual system behaves like the product: it does the work, surfaces exactly what matters, and then recedes. Nothing shouts. A near-white warm-neutral page, a single slate-blue voice, and a generous amount of restraint carry the whole surface — the closest references are **Attio** (product chrome), **Notion** (white-space discipline), and **Linear** (color discipline). The system is built light-default with a designed-parallel dark mode (currently held off in build); identity lives in the light surface.

This system explicitly rejects the crowded-portal look of **Property Finder / Bayut** (orange/red CTAs, broker-first clutter), the **generic SaaS landing** kit (pastel gradients, gradient-hero blobs, three-up icon-card grids, the hero-metric template), **tech-bro brutalism** and **crypto/Web3** neon, and — most of all — the **retired consumer Dalya** (dark-luxury navy `#0F1923` + gold `#C9A96E`). Gold is fully retired. Warmth is carried by the neutral tint and the copy, never by a saturated body background.

Density is dual: marketing surfaces breathe (96px section rhythm, 60px display type); the agent/owner dashboard is dense and operational (compact rows, 8px workhorse radius, tabular numerals). Same tokens, two densities.

**Key Characteristics:**
- One brand voice: slate blue, used sparingly and always meaningfully.
- Warm-neutral light surfaces in three tonal layers; depth by tone, not by heavy shadow.
- Inter for everything UI; IBM Plex Mono reserved for AED figures and RERA IDs only.
- Semantic color (sage / copper / brick) appears only when a status is genuinely meaningful.
- Calm by omission — restraint is the aesthetic, not a constraint.

## 2. Colors

A warm-neutral light field carrying a single slate-blue brand voice, with sage / copper / brick reserved strictly for status.

### Primary
- **Slate Blue** (`#3D5A80`): the sole brand-driven color. Wordmark, links, focus rings, selected state, secondary-primary buttons, and the accent that draws the eye to the one thing that matters on a screen.
- **Slate Blue CTA** (`#324B6B`): the deeper slate reserved for the 3–5 brand-critical CTAs ("Book a demo", "Accept offer"). Also the pressed state of the primary slate.
- **Slate Pressed / Wash** (`#283C56` pressed; `#EEF2F7` wash, `#D6E0EC` soft): hover/pressed depth and the faint tint behind selected rows, chips, and the "Dalya draft" message bubble.

### Secondary (status — never decorative)
- **Sage** (`#4A7C6F`, tint `#D0E1DD`, ink `#2F5048`): verified, confirmed, live, NOC-eligible. Success.
- **Copper** (`#B7793A`, tint `#F4DFC8`, ink `#7A4F25`): pending, countered, escalation-needs-you. Warning.
- **Brick** (`#B84838`, tint `#EFCFC8`, ink `#7A2A1F`): destructive, blocked, error. Bank-grade, never alarmist.

### Neutral
- **Page** (`#FAFAF9`): the warm-neutral body background. Off-white, tinted at near-zero chroma — never cream/sand.
- **Card** (`#F4F4F2`) / **Recessed** (`#E8E8E5`): the two surfaces above the page; depth is carried by these tonal steps.
- **Ink Primary** (`#3D3D39`): body and headings. **Ink Secondary** (`#5C5C57`): helper/secondary. **Ink Muted** (`#7B7B76`): metadata, placeholders — still ≥4.5:1 on page.
- **Hairline** (`#E8E8E5`) / **Default border** (`#D6D6D2`): all borders are 1px.

### Named Rules
**The One Voice Rule.** Slate blue is the only brand color. It appears on a small fraction of any screen — CTAs, the active nav item, focus, a single accent numeral. Its rarity is what makes it read as "important."

**The Status-Only Rule.** Sage, copper, and brick are forbidden as decoration. If a sage pill appears, something is genuinely confirmed; if copper appears, something genuinely needs the agent. Color carries meaning or it doesn't appear.

**The Retired-Gold Rule.** `#C9A96E` gold and `#0F1923` navy are prohibited. They are the old consumer brand; reviving them is a regression.

## 3. Typography

**Display / Body Font:** Inter (with `system-ui, -apple-system, Segoe UI, Roboto` fallback)
**Mono Font:** IBM Plex Mono (with `SF Mono, Consolas` fallback)
**Arabic:** IBM Plex Sans Arabic · **Hindi:** Noto Sans Devanagari

**Character:** One family, many weights — restraint over contrast-pairing. Inter does all UI and editorial work; weight and size create hierarchy, not a second typeface. Tight tracking on large display sizes gives headlines a deliberate, engineered feel without crowding.

### Hierarchy
- **Display** (700, `clamp(40px, 6vw, 60px)`, 1.05, -0.025em): marketing hero headlines only. `text-wrap: balance`.
- **Headline** (700, `clamp(28px, 4vw, 40px)`, 1.1, -0.02em): section headings.
- **Title** (600, 17–20px, 1.35, -0.01em): card and modal titles.
- **Body Large** (400, 18px, 1.5): marketing lede paragraphs. Cap 65–75ch.
- **Body** (400, 15px, 1.5): default reading / operational text.
- **Label** (600, 11px, 0.12em, UPPERCASE): the brand eyebrow / kicker and small-caps metadata.
- **Mono** (IBM Plex Mono, tabular + slashed-zero): AED amounts, percentages, RERA IDs, code.

### Named Rules
**The Mono-for-Money Rule.** IBM Plex Mono is reserved for AED figures, percentages, RERA/permit IDs, and code. It never sets prose. AED amounts always use tabular-nums + slashed-zero (`"tnum", "ss01"`).

**The Eyebrow-Is-a-Device-Not-Scaffolding Rule.** The uppercase label is a permitted brand kicker, but it is not mandatory above every section. Vary the cadence — a numbered list, a lead sentence, or nothing is often better. An eyebrow on every section is AI grammar, not voice.

## 4. Elevation

Flat by default. Depth is carried primarily by the three tonal surface steps (page → card → recessed), not by shadow. Shadows are **overlay-only**: they appear on things that genuinely float above the page — floating hero cards, popovers, modals, the embedded product mockups — and are ink-tinted (`rgba(35,35,32,…)`), never pure black.

### Shadow Vocabulary
- **Overlay SM** (`0 1px 2px 0 rgba(35,35,32,.06), 0 1px 1px 0 rgba(35,35,32,.04)`): resting cards that need a whisper of lift (e.g. the contact form).
- **Overlay MD** (`0 4px 8px -2px rgba(35,35,32,.08), 0 2px 4px -2px rgba(35,35,32,.06)`): product mockup cards, surface previews.
- **Overlay LG** (`0 12px 24px -6px rgba(35,35,32,.10), 0 4px 8px -2px rgba(35,35,32,.06)`): floating hero cards, popovers.

### Named Rules
**The Flat-By-Default Rule.** Surfaces are flat at rest and separated by tone. A shadow means "this element is above the page." If everything has a shadow, nothing reads as elevated — so most things don't.

## 5. Components

### Buttons
- **Shape:** softly rounded, 8px (`rounded.md`) — the workhorse radius across the system.
- **Primary (top-tier CTA):** deep slate `#324B6B` background, white text, ~10px/20px padding. Reserved for the 3–5 brand-critical actions ("Book a demo"). Hover deepens to `#283C56`.
- **Secondary primary:** slate `#3D5A80` background, white text — the everyday primary.
- **Outline / ghost:** transparent background, ink-primary text, 1px default border; hover fills to card surface. Used for the secondary CTA next to a primary ("See the workflow").
- **Focus:** 2px slate ring with a 2px surface-matched offset (`--focus-ring`), on `:focus-visible` only.
- CTAs are operational verbs (Book a demo · Send · Accept · Escalate), never marketing fluff.

### Chips / Pills
- **Style:** small (4px radius), semantic tint background with matching ink — slate wash for neutral/selected, sage tint for confirmed, copper tint for pending, brick tint for blocked.
- **State:** an uppercase 9–11px label inside; carries status, not decoration.

### Cards / Containers
- **Corner:** 12px (`rounded.lg`) for standard cards, 16px for marketing-grade containers.
- **Background:** page or card surface; **separated from the page by tone and a 1px hairline**, not by a heavy shadow.
- **Shadow:** none at rest unless it genuinely floats (see Elevation).
- **Internal padding:** 24px comfortable / 16px compact / 32px display.
- **Never nest cards inside cards.** Use tone + hairline + spacing for internal hierarchy.

### Inputs / Fields
- **Style:** page-surface background, 1px hairline border, 8px radius, 10px/12px padding.
- **Focus:** border shifts to slate `#3D5A80` plus a soft `rgba(61,90,128,.12)` ring.
- **Required / error:** required marked at the label; error state uses brick ink + tint, never a bare red border.

### Navigation (marketing)
- **Style:** sticky top bar, page-surface at 85% with an 8px backdrop blur, 1px hairline bottom border. Wordmark (slate, 700) at left; text links at 13px; one deep-slate "Book a demo" CTA at right.
- **States:** active link gets ink-primary color + card-surface background; rest are ink-secondary.

### Signature: Floating product cards
The marketing hero and sections use small, slightly-rotated overlay cards (WhatsApp thread, offer escalation, hot-list summary) on `Overlay LG`. They are the system's one moment of motion-ready personality — concrete proof, never decoration. Mockup action rows (Accept / Send) are marked `aria-hidden` with a "Preview" cue since they're illustrative, not interactive.

## 6. Do's and Don'ts

### Do:
- **Do** keep slate blue rare — CTAs, focus, active nav, one accent. Its scarcity is the point (The One Voice Rule).
- **Do** carry depth with the three tonal surface steps + 1px hairlines; reserve shadow for things that truly float.
- **Do** use sage / copper / brick **only** when a status is genuinely meaningful.
- **Do** set AED figures, percentages, and RERA IDs in IBM Plex Mono with tabular + slashed-zero numerals.
- **Do** keep body text ≥4.5:1 on its surface; placeholder/muted ink still meets 4.5:1.
- **Do** author RTL-ready with logical properties (`margin-inline`, `ms-/me-/ps-/pe-`) and support EN/AR/RU/HI.
- **Do** give every animation a `prefers-reduced-motion` alternative; ease-out with exponential curves (`cubic-bezier(0.16,1,0.3,1)`), never bounce.

### Don't:
- **Don't** revive the retired consumer brand: no `#0F1923` navy, no `#C9A96E` gold, no "luxury PropTech" residue.
- **Don't** build the **Property Finder / Bayut** crowded portal — orange/red CTAs, broker-first clutter.
- **Don't** ship **generic-SaaS** tells: pastel gradients, gradient-hero blobs, the hero-metric template, or identical icon-card grids repeated endlessly.
- **Don't** use **gradient text** (`background-clip: text`), **side-stripe borders** (`border-left` >1px as a colored accent), or **glassmorphism** as decoration. The nav's subtle backdrop-blur is the one sanctioned, purposeful use.
- **Don't** put a tracked uppercase eyebrow above every section, or numbered `01 / 02 / 03` markers as default scaffolding — vary the cadence (The Eyebrow-Is-a-Device Rule).
- **Don't** nest cards inside cards, or add a shadow to a resting surface.
- **Don't** introduce neon, glow, or aggressive motion — calm by omission is the brand.
