# 03 — Typography Direction (Phase 1)

**Scope:** Type system for Dalya as agent infrastructure. Designed for legibility under 4-hour load on dense data UIs. Latin + Arabic pairing technical specs. Cyrillic/Devanagari coverage. Tailwind v4 tokens.

**Attribute priority (carries over):** Trustworthy > Calm > Sharp.
**Operating constraint:** the system must hold up at 14–16px on Windows ClearType, macOS, ChromeOS, and Linux — not just on a designer's Retina display.

---

## Pushback (read first)

### 1. Plus Jakarta Sans is wrong for this evolution. Recommend Inter as primary.

Plus Jakarta Sans (PJS) was a reasonable pick for the consumer-facing marketplace brand — it has a slight editorial flair, the geometric counters read as modern-but-warm, and it ranges nicely across display sizes. It is *not* the right choice for an agent's working UI for four specific reasons:

1. **Hinting at 14–16px is mediocre on Windows.** PJS is hinted, but not aggressively. On a Windows machine running ClearType — which is what a meaningful chunk of Dubai brokerage agents are on — PJS at 14px goes soft. Letters smear, the `e` and `a` round counters collapse slightly, and after 4 hours the agent's eyes are working harder than they need to.
2. **Numerals are inconsistent.** PJS's tabular figures are present but the spacing is slightly uneven, particularly across `0/6/8`. For an AED-figures-everywhere product this matters. Inter's tabular figures are class-leading and rendered identically across all platforms.
3. **Editorial vs operational mismatch.** PJS has a slight display-face energy — terminals are softly cut, the `g` is double-storey with personality. That's right for "modern PropTech consumer brand." It's the wrong personality for "I have been managing leads in this UI since 9am."
4. **The "everyone uses Inter" objection is weak.** Yes, Inter is overused in B2B SaaS. The reasons it's overused are good reasons: it was designed for screen, it hints well at small sizes, its tabular figures are correct, its Cyrillic and extended Latin are first-class, and it's variable-font ready. Generic doesn't mean wrong.

**My pick: Inter.** Specifically Inter variable (`Inter Variable`), so all weights load from a single file.

**Considered alternatives:**

| Face | Verdict | Why not |
|---|---|---|
| **Plus Jakarta Sans** | Reject (current) | Hinting issues at 14px, editorial energy, see above. |
| **Inter** | **Selected** | Best small-size rendering on Windows. Tabular figures correct. Full extended Latin + Cyrillic. Variable font. Free. |
| **SF Pro** | Reject | Apple-licensed for system UI only — using it as a web font in product is a licence ambiguity. Not worth the risk. |
| **Söhne** | Strong consider, reject on cost | Klim's Söhne is genuinely better than Inter for marketing surfaces. Costs $$ per seat for variable web. For an early-stage product, not justifiable. Revisit when funded. |
| **Manrope** | Reject | Geometric, designer-friendly, but small-size rendering is weaker than Inter and tabular figures are slightly off. |
| **Geist** | Reject | Vercel's. Designed as a marketing face, not a working face. Inferior tabular figures to Inter. Heavy Vercel-cultural association. |
| **Aktiv Grotesk** | Reject on cost | Excellent neogrotesk, pairs well with Arabic IBM Plex. Commercial licence. Not justified for Phase 1. |
| **IBM Plex Sans** | Strong consider, reject on tone | Plex is great. Pairs with IBM Plex Arabic perfectly. Free. The reason I'm not picking it: it has IBM-corporate visual association that fights the "Dalya, Dubai-aware, considered" tone. If Eric wants to revisit, this is the most defensible alternative to Inter. |

**If Eric overrules me and wants to keep PJS:** the only way it survives is if it's used at 15px+ minimum body and 16px+ for dense tabular data, and Inter is loaded as a secondary face for tables and small-size UI labels. That's a worse system than just picking Inter for everything.

### 2. JetBrains Mono for AED figures is wrong on light-default UI. Strip it.

This is the spicier pushback. JetBrains Mono in the current dark palette works because mono on a deep ink background reads as "data, computed, precise." Mono on white reads as "code editor" or worse, "Bayut-clone bold price tag." A property listing showing `AED 2,450,000` in JetBrains Mono on a white card looks like a search result from 2008.

**Recommendation:** drop JetBrains Mono from AED figures entirely. Use Inter's tabular-figures feature instead. Inter's tabular numerals are wide enough to align cleanly in columns, have a slight square shoulder that reads as "data," and don't carry the cultural "code editor" baggage of a mono face on white.

**Reserve mono for:**
- Actual code blocks (rare in this product — maybe API docs, dev settings, an audit log).
- Property reference IDs, RERA permit numbers, Trakheesi IDs — the alphanumeric identifiers where character-by-character distinction matters.
- That's it.

**Mono face for those reserved roles:** keep JetBrains Mono. It's free, well-hinted, and tonally consistent. Or — slightly preferred — **IBM Plex Mono**, which pairs more naturally with Inter than JetBrains does.

### 3. Reference brand reality check

Eric asked me to coordinate honestly with the reference cluster. My read for typography specifically:

- **Linear** — uses Inter. Their type system is genuinely a weak point of the brand; small-size rendering on Linear's web app suffers from the same Inter-at-small-sizes complaints that get aired in design Discords. But Linear has chosen Inter because *the alternatives are worse for screen*. This is the same logic I'm applying to Dalya. Inter is the least-bad screen face. Steal: their commitment to tabular figures.
- **Notion** — uses a custom Inter-derived face. Masterful at light-mode density. Steal: their conservative weight stack (Regular and Medium do almost everything; Semibold is rare).
- **Stripe** — uses a custom face (Sohne-derived). Beautiful, expensive, not relevant to your stack decision.
- **Attio** — uses Inter. Best in-class for dense CRM UI. **This is the brand I'm designing toward.**

**The brand I'm actually designing toward, for type:** Attio. Direct quote of intent. The other references are scenery.

---

## 1. Typeface Stack

### Primary (Latin)

**Inter Variable** (open source, SIL Open Font Licence).

- File weight: ~330KB for full variable font (Latin + Latin Ext + Cyrillic + Vietnamese). Acceptable.
- Subset if needed: Latin only is ~110KB. For Phase 1 ship the full Latin Ext + Cyrillic subset (~210KB) since Russian is in the product roadmap.
- Self-host. Do not load from Google Fonts CDN — privacy regs in EU/UAE plus a 2022 German court ruling make Google Fonts CDN loading legally fraught for a UAE-incorporated product.

### Arabic pairing

**IBM Plex Sans Arabic** (open source, SIL OFL).

- Pairs technically well with Inter: both are neutral neogrotesks with similar x-height ratios, neither carries excessive editorial flair.
- IBM Plex Arabic supports the full set of contextual Arabic forms — initial, medial, final, isolated — with correctly designed connecting strokes. This matters for Dubai property terminology (تملك حر, off-plan, NOC) which Cultural Intelligence will detail.
- Weight matching: Inter Regular pairs with Plex Arabic Regular, Inter Medium with Plex Arabic Medium. Inter Bold (700) pairs with Plex Arabic SemiBold (600), not Bold (700) — Plex Arabic Bold is too heavy and visually overwhelms Inter Bold. Document this.
- File weight: Plex Arabic at four weights is ~340KB. Load only when locale is Arabic; lazy-load via `font-display: swap` and locale detection.

**Pushback note for Cultural Intelligence agent:** I'm picking the type pairing on technical grounds (shaping, weight match, file size). The cultural reasoning — whether Plex Arabic feels appropriately "Dubai-aware" vs "IBM-corporate" — is Cultural Intelligence's call. If they argue for a different Arabic face (e.g., 29LT Bukra, GE SS Two, Boutros) I'll defer on cultural fit and re-pair the Latin face accordingly. Coordinate before Phase 2.

### Mono (restricted role)

**IBM Plex Mono** (open source, SIL OFL). Roles defined in Pushback #2 above.

- Pairs with Inter and IBM Plex Sans Arabic without visual collision.
- Replaces JetBrains Mono from the current system.
- Load only on routes that surface code/identifier roles — lazy-load.

### Cyrillic + Devanagari coverage (chatbot supports EN/AR/RU/HI)

| Script | Face | Status |
|---|---|---|
| Latin (EN) | Inter | First-class |
| Arabic (AR) | IBM Plex Sans Arabic | First-class |
| Cyrillic (RU) | Inter | First-class — Inter's Cyrillic is excellent |
| Devanagari (HI) | **Noto Sans Devanagari** | Pair as fallback |

Inter does not include Devanagari. The chatbot's Hindi rendering needs a paired face. **Noto Sans Devanagari** is the right pick — Google-funded, open source, hinted, designed to pair with neutral Latin grotesks. Weight match: Noto Sans Devanagari Regular with Inter Regular, etc. The pairing is documented at scale (Noto's whole project is "harmonize with Latin grotesks") so the match is reliable.

### Font stack (CSS)

```css
--font-sans: 'Inter Variable', 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-sans-ar: 'IBM Plex Sans Arabic', 'Inter Variable', system-ui, sans-serif;
--font-sans-hi: 'Noto Sans Devanagari', 'Inter Variable', system-ui, sans-serif;
--font-mono: 'IBM Plex Mono', 'JetBrains Mono', ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, monospace;
```

Apply via `:lang(ar) { font-family: var(--font-sans-ar); }` and `:lang(hi) { font-family: var(--font-sans-hi); }`. Direction switching (`dir="rtl"`) is independent of font-family switching — both must be set on the locale-aware root.

---

## 2. Type Scale

11 steps. Designed operationally, not editorially. Each step's role is enumerated. Sizes in `rem` assuming `1rem = 16px`.

| Token | rem / px | Line-height | Letter-spacing | Weight default | Role |
|---|---|---|---|---|---|
| `text-2xs` | 0.6875rem / 11px | 1.45 (16px) | +0.02em | 500 | Micro-labels, table column captions, eyebrow tags. Avoid for body. |
| `text-xs` | 0.75rem / 12px | 1.5 (18px) | +0.01em | 500 | Metadata, timestamps, "edited 3m ago" text. Min for accessible UI. |
| `text-sm` | 0.8125rem / 13px | 1.55 (20px) | 0 | 400 | Dense table body, secondary descriptors. |
| `text-base` | 0.875rem / 14px | 1.6 (22.4px) | 0 | 400 | **Default body for working UI.** Inter at 14px is the Attio/Linear baseline. |
| `text-md` | 1rem / 16px | 1.55 (24.8px) | -0.005em | 400 | Long-form reading (advisor chat messages, listing descriptions). |
| `text-lg` | 1.125rem / 18px | 1.5 (27px) | -0.01em | 500 | Card titles, section subheadings. |
| `text-xl` | 1.25rem / 20px | 1.4 (28px) | -0.015em | 600 | H3, modal titles, key data labels. |
| `text-2xl` | 1.5rem / 24px | 1.35 (32.4px) | -0.02em | 600 | H2, page section headers. |
| `text-3xl` | 1.875rem / 30px | 1.25 (37.5px) | -0.025em | 600 | H1 in product, dashboard headlines. |
| `text-4xl` | 2.25rem / 36px | 1.2 (43.2px) | -0.03em | 600 | Marketing H1, hero figures (AED display amounts). |
| `text-5xl` | 3rem / 48px | 1.1 (52.8px) | -0.035em | 700 | Marketing display only. Rarely in product. |

### Calibration notes

- **Body at 14px not 16px** is deliberate. Agent CRM UIs need density. 16px is reading-page comfortable; 14px is working-UI comfortable when the line-height is generous (1.6) and the typeface hints well at that size. Inter does. This is why Attio and Linear ship at 14px body.
- **Letter-spacing tightens as size grows.** Inter ships slightly loose at default. At display sizes (24px+) it benefits from -0.02em to -0.035em tightening to avoid feeling watery. At small sizes (12px and below) it benefits from +0.01–0.02em loosening to keep counters open.
- **Line-height ratios are tighter at the top, looser at the body.** This is correct for hierarchy — display text breathes through size, body text breathes through leading.
- **No 17px, no 19px, no in-between sizes.** Discipline. If a designer wants 17px because "14 is too small and 18 feels heavy," the answer is "no, pick one." This is the lesson Notion's type scale teaches.

---

## 3. Weight Usage Rules — three, enforceable

The most common type system failure in B2B SaaS is over-using Semibold. Every label, button, heading, and column header ends up at 600, the page feels shouty, and visual hierarchy collapses because everything is emphasized. Notion's discipline here is the model.

### Rule 1 — Default to 400 Regular for body and 500 Medium for everything else that isn't a heading.

400 is body, advisor chat messages, listing descriptions, paragraph text, anything reading-length.

500 is UI element labels, table column headers, button text, navigation items, badges, chips, key data labels. **Medium does most of the lifting that lazy designers reach for Semibold for.**

### Rule 2 — Semibold (600) is reserved for headings (text-xl and up) and emphasized values.

Card titles, section headers, page H1, modal titles. Plus: the actual AED amount when it's the data hero of a card (e.g., the listing price on a listing card — 600 weight, tabular figures, gold-500 color).

Buttons are **not** 600. They are 500. Tabs are **not** 600. They are 500. This is the most important rule in the system.

### Rule 3 — Bold (700) is reserved for marketing display, never product UI.

Hero headlines on marketing pages. Display figures. Never used inside the product. If a designer reaches for 700 in a product surface, the answer is "use 600 and increase the size by one step."

That's three rules. They're enforceable in design review and lintable in code (`font-weight: 700` outside of `marketing/` should fail a check).

---

## 4. Numerals

Tabular figures required throughout the product. AED amounts, percentages, square footage, transaction counts, lead counts, days-on-market, IDs, dates — all tabular.

### Inter font-feature settings

```css
:root {
  font-feature-settings:
    "cv11" 1,    /* single-storey alternate a, optional — see below */
    "ss01" 1,    /* slashed zero, single-storey g, etc */
    "tnum" 1,    /* tabular numerals */
    "kern" 1,    /* kerning on */
    "calt" 1;    /* contextual alternates */
  font-variant-numeric: tabular-nums;
}
```

`font-variant-numeric: tabular-nums` is the canonical CSS way; the `font-feature-settings: "tnum"` is the lower-level form. Set both for browser-coverage belt-and-braces.

### Slashed zero (`ss01`)

Inter's `ss01` stylistic set enables a slashed zero plus a single-storey `g`. **Recommend ON.** A slashed zero is a real-estate-product requirement: agents read AED figures, RERA permit numbers, and IDs constantly. Zeroes confused with O's cost time and create errors. The single-storey `g` is a stylistic bonus.

### When proportional figures are acceptable

- Display marketing headlines (e.g., a hero saying "5,000+ verified SPAs"). Aesthetic, not data-critical.
- Body prose where a number is mentioned in passing ("listed for three months").
- **Never in tables, never in data cards, never in dashboards, never in transaction amounts.**

Implement as `font-variant-numeric: proportional-nums` on a `.prose` or `.marketing-heading` class scope.

### AED currency formatting

Set AED prefix in text-xs uppercase tracking +0.05em followed by the figure at 1-2 steps larger in tabular-nums. The visual hierarchy is: currency label (small, restrained) → figure (large, data-weighted, gold-500 if hero AED).

```html
<span class="aed-figure">
  <span class="aed-currency">AED</span>
  <span class="aed-amount">2,450,000</span>
</span>
```

```css
.aed-figure { display: inline-flex; align-items: baseline; gap: 0.25rem; }
.aed-currency {
  font-size: var(--text-xs);
  font-weight: 500;
  letter-spacing: 0.05em;
  color: var(--color-neutral-500);
  text-transform: uppercase;
}
.aed-amount {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--color-gold-600); /* hero AED only; default elsewhere is neutral-900 */
}
```

---

## 5. Mono Usage

Already covered in Pushback #2. Concise summary:

- Drop JetBrains Mono from AED figures. Use Inter tabular-nums.
- Adopt **IBM Plex Mono** as the mono face.
- Mono is allowed for: code blocks, RERA/Trakheesi/property IDs, JSON/audit-log displays, dev settings.
- Mono is banned for: prices, percentages, dates, counts, names, addresses, anything that isn't computed/identifier data.

Size: mono runs slightly larger than sans at the same visual size. When pairing mono and sans in a single line (e.g., "Property ID: RES-2024-00821 — Listed 3d ago"), set mono to `0.95em` to compensate.

---

## 6. Arabic Typography Pairing (technical)

(Cultural reasoning is owned by the Cultural Intelligence agent. This section is the technical pairing spec.)

### Face: IBM Plex Sans Arabic

- Weights to load: 400, 500, 600 (skip 700 — Plex Arabic 700 is too heavy for Inter Bold pairing).
- File weight (3 weights, subset): ~210KB. Acceptable when conditionally loaded for `:lang(ar)`.

### Weight pairing matrix

| Inter (Latin) | IBM Plex Sans Arabic |
|---|---|
| 400 Regular | 400 Regular |
| 500 Medium | 500 Medium |
| 600 SemiBold | 600 SemiBold |
| 700 Bold | **Use 600 SemiBold** — Plex Arabic 700 is visually too heavy |

### Size adjustment

Arabic typically sits visually larger than Latin at the same point size because of the longer descenders and the height of dotted glyphs. Apply `font-size: 1.05em` to `:lang(ar)` elements at body sizes, and `1em` (no adjustment) at display sizes (24px+) where the difference compresses.

```css
:lang(ar) {
  font-family: var(--font-sans-ar);
  font-size: 1.05em;     /* compensate for Arabic visual size */
  line-height: 1.7;       /* Arabic benefits from looser leading */
}

:lang(ar) .text-2xl,
:lang(ar) .text-3xl,
:lang(ar) .text-4xl {
  font-size: 1em;         /* reset at display sizes */
  line-height: 1.35;
}
```

### RTL rendering rules

- Use logical CSS properties throughout (`margin-inline-start`, `padding-inline-end`, `border-inline-start`). This is already noted in the existing CLAUDE.md as a Phase 3 requirement — apply *now* to avoid rewrites. The Tailwind v4 `ms-*`, `me-*`, `ps-*`, `pe-*` utilities map to these directly.
- Tabular numerals stay LTR even in RTL text. This is browser default and correct — AED figures read left-to-right inside otherwise right-to-left Arabic content.
- Currency symbol position: AED prefix stays LTR-positioned (`AED 2,450,000`) even in RTL contexts. This is the Dubai market convention.

### Mixed-script lines

Common case: "AED 2,450,000 — تملك حر, ready handover 2026."

Browsers handle bidi reasonably with proper `dir="auto"` on the containing element. Don't manually wrap segments unless mixed-script lines break visually. Test in Safari (worst bidi rendering of the four major engines) before declaring done.

---

## 7. Cyrillic + Devanagari + Mixed-script

### Cyrillic (RU)

Inter ships excellent Cyrillic. No additional face needed. Same weight rules apply. Slashed-zero stylistic set works identically.

```css
:lang(ru) {
  font-family: var(--font-sans);
  /* No size adjustment needed — Inter Cyrillic matches Latin metrics. */
}
```

### Devanagari (HI)

Pair with Noto Sans Devanagari (see section 1). Weight matching:

| Inter (Latin) | Noto Sans Devanagari |
|---|---|
| 400 Regular | 400 Regular |
| 500 Medium | 500 Medium |
| 600 SemiBold | 600 SemiBold |
| 700 Bold | 700 Bold |

Size adjustment: Devanagari runs slightly smaller than Latin at the same point size (the script's "height" is from the headstroke up, leaving more whitespace above descenders). Apply `font-size: 1.05em` at body sizes to compensate, similar to Arabic.

```css
:lang(hi) {
  font-family: var(--font-sans-hi);
  font-size: 1.05em;
  line-height: 1.65;
}
```

### Mixed-script lines (the advisor chat reality)

Buyer messages may be EN-only, AR-only, or mixed ("AED 2.4M ka kya breakdown hai?"). Set `dir="auto"` on the message container; the browser determines direction per paragraph. Set font-family to a stack that includes Devanagari fallback by default in chat UI so a Hindi character doesn't render as a tofu box.

```css
.advisor-message {
  font-family: var(--font-sans), 'Noto Sans Devanagari', 'IBM Plex Sans Arabic', sans-serif;
  dir: auto;
}
```

---

## 8. Tailwind v4 Token Mapping

Paste-ready for `globals.css`. Append below the color tokens.

```css
@theme {
  /* === Font families === */
  --font-sans: 'Inter Variable', 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-sans-ar: 'IBM Plex Sans Arabic', 'Inter Variable', system-ui, sans-serif;
  --font-sans-hi: 'Noto Sans Devanagari', 'Inter Variable', system-ui, sans-serif;
  --font-mono: 'IBM Plex Mono', 'JetBrains Mono', ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, monospace;

  /* === Font sizes (paired line-height + letter-spacing where v4 supports) === */
  --text-2xs: 0.6875rem;
  --text-2xs--line-height: 1.45;
  --text-2xs--letter-spacing: 0.02em;
  --text-2xs--font-weight: 500;

  --text-xs: 0.75rem;
  --text-xs--line-height: 1.5;
  --text-xs--letter-spacing: 0.01em;
  --text-xs--font-weight: 500;

  --text-sm: 0.8125rem;
  --text-sm--line-height: 1.55;

  --text-base: 0.875rem;
  --text-base--line-height: 1.6;

  --text-md: 1rem;
  --text-md--line-height: 1.55;
  --text-md--letter-spacing: -0.005em;

  --text-lg: 1.125rem;
  --text-lg--line-height: 1.5;
  --text-lg--letter-spacing: -0.01em;
  --text-lg--font-weight: 500;

  --text-xl: 1.25rem;
  --text-xl--line-height: 1.4;
  --text-xl--letter-spacing: -0.015em;
  --text-xl--font-weight: 600;

  --text-2xl: 1.5rem;
  --text-2xl--line-height: 1.35;
  --text-2xl--letter-spacing: -0.02em;
  --text-2xl--font-weight: 600;

  --text-3xl: 1.875rem;
  --text-3xl--line-height: 1.25;
  --text-3xl--letter-spacing: -0.025em;
  --text-3xl--font-weight: 600;

  --text-4xl: 2.25rem;
  --text-4xl--line-height: 1.2;
  --text-4xl--letter-spacing: -0.03em;
  --text-4xl--font-weight: 600;

  --text-5xl: 3rem;
  --text-5xl--line-height: 1.1;
  --text-5xl--letter-spacing: -0.035em;
  --text-5xl--font-weight: 700;

  /* === Font weights === */
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
}

/* === Base + feature settings === */
:root {
  font-family: var(--font-sans);
  font-feature-settings: "ss01" 1, "tnum" 1, "kern" 1, "calt" 1;
  font-variant-numeric: tabular-nums;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* === Proportional figures escape hatch === */
.prose,
.marketing-headline {
  font-variant-numeric: proportional-nums;
}

/* === Mono override for data ID roles === */
.mono,
code,
kbd,
samp,
pre {
  font-family: var(--font-mono);
  font-feature-settings: "tnum" 1, "ss01" 1;
}

/* === Locale-aware font + size === */
:lang(ar) {
  font-family: var(--font-sans-ar);
  font-size: 1.05em;
  line-height: 1.7;
}
:lang(ar) [class*="text-2xl"],
:lang(ar) [class*="text-3xl"],
:lang(ar) [class*="text-4xl"],
:lang(ar) [class*="text-5xl"] {
  font-size: 1em;
  line-height: 1.35;
}

:lang(hi) {
  font-family: var(--font-sans-hi);
  font-size: 1.05em;
  line-height: 1.65;
}
```

### Tailwind v4 token caveat (Pushback #4)

Tailwind v4 supports paired sub-properties on text tokens (e.g., `--text-base--line-height`). This is a v4-only feature; if any tooling assumes v3 token shape (`font-size` only, with `lineHeight` separate), it will silently drop the line-height pairings. The Next.js app at `/Users/eric/dalya-ai/frontend/` is on Tailwind v4 already per the existing `globals.css` — so this is safe to paste directly. Worth confirming with the eng team before they wire in any third-party Tailwind plugin that hasn't shipped v4 compatibility.

---

## Out of scope (Phase 2)

- **Component-level type application.** When does a button use `text-base` vs `text-sm`? When does a table row vs. table header use which size + weight? That's component-system work.
- **Animation/transition specifications** for typography (e.g., subtle weight transitions on hover, focus-ring animation). Out of scope.
- **Print stylesheet typography** (for any PDF exports — listing reports, agent performance reports). Out of scope, but flagged.
- **WhatsApp Business message rendering.** Dalya's outbound WhatsApp messages don't honor custom fonts — they use WhatsApp's default. Worth noting that the type system applies to web/app surfaces, and WhatsApp tone is owned by the copy system.
- **Editorial moments.** If the marketing site wants a display face for a hero (something more distinctive than Inter Bold), Phase 2 can introduce a single display face for marketing-only headlines. Don't pre-empt that decision here.

---

## Summary of decisions

1. **Inter Variable** as primary Latin face, replacing Plus Jakarta Sans.
2. **IBM Plex Sans Arabic** as Arabic pair (subject to Cultural Intelligence confirmation).
3. **Noto Sans Devanagari** as Devanagari pair for Hindi chat.
4. **IBM Plex Mono** replacing JetBrains Mono, restricted to code/IDs only.
5. **AED figures use Inter tabular-nums, not mono.**
6. **Body default: 14px / 1.6 leading / weight 400.** Operational, not editorial.
7. **Three weight rules: 400 body, 500 UI elements, 600 headings + emphasized data, 700 marketing-only.**
8. **Slashed-zero stylistic set ON** by default.
9. **Locale-aware font-family + size scaling** for AR (1.05em body) and HI (1.05em body).
