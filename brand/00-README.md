# Dalya — Brand

*Last updated: 2026-05-15 — Strategic pivot to B2B integrated. Phases 1, 2, 3 visual + operational systems still hold. Positioning sections of BRAND.md updated.*

## ⮕ Start here: [BRAND.md](./BRAND.md)

The canonical brand document. Read this first. The phase documents below are the depth that supports it.

## ⮕ Then read: [STRATEGIC-PIVOT-2026-05-15.md](./STRATEGIC-PIVOT-2026-05-15.md)

The permanent record of the shift from consumer-direct brokerage to B2B AI infrastructure for brokerages. Read this before relitigating any positioning that contradicts it. Mahoroba Realty remains alive in maintenance mode but is no longer the primary product; it's held as an eventual recruitment destination once the platform is sticky.

This directory holds the strategic frame, visual direction, operational system, and application examples for Dalya.

- **Phase 1** (locked): foundations + color/type direction
- **Phase 2** (locked): surface system, components, motion, voice
- **Phase 3** (locked): application examples — six mockups + complete token system
- **Pivot** (2026-05-15): consumer-direct → B2B AI infrastructure for brokerages

The Phase 1–3 visual and operational decisions all survive the pivot. The strategic positioning, audience model, and product pillars are what changed. See `BRAND.md` §1, §2, §4, §7, §11 for the rewritten sections.

## Pre-pivot brand artifacts (historical reference)

The consumer-direct brand artifacts produced in March 2026 have been moved to [`../archive/pre-pivot-brand/`](../archive/pre-pivot-brand/) for read-only reference. Three documents are there: the original 38K brand identity system, the 30K positioning + marketing strategy, and the 32K consumer-direct website copy. They are not source-of-truth anymore but capture the design thinking that preceded this brand system.

## Phase 1 documents

| # | File | Owner | Scope |
|---|---|---|---|
| 01 | [foundations.md](./01-foundations.md) | Brand Guardian | Strategic positioning, brand attributes, what stays / changes, voice posture |
| 02 | [color-direction.md](./02-color-direction.md) | UI Designer | Neutral scale, primary, semantic, viz, dark mode, Tailwind tokens |
| 03 | [typography-direction.md](./03-typography-direction.md) | UI Designer | Typeface selection (Inter + IBM Plex Mono + Plex Sans Arabic), scale, weights, numerals |
| 04 | [cultural-strategy.md](./04-cultural-strategy.md) | Cultural Intelligence Strategist | Dubai context, multilingual operations, RTL strategy |
| — | [PHASE-1-LOCK.md](./PHASE-1-LOCK.md) | — | Eric's locked decisions: gold fully retired, quiet-by-omission, slate blue primary, Inter UI, user model clustering |

## Phase 2 documents

| # | File | Owner | Scope |
|---|---|---|---|
| 05 | [surface-spacing.md](./05-surface-spacing.md) | UX Architect | Surfaces, spacing (4px hybrid), borders, radii, shadows, density modes, layout primitives, RTL, Tailwind v4 |
| 06 | [components.md](./06-components.md) | UI Designer | Buttons, inputs, tables, cards, modals, conversation surfaces, navigation, status indicators |
| 07 | [motion.md](./07-motion.md) | UI Designer | What we animate (allow list), what we never animate (ban list), tokens, reduced-motion |
| 08 | [voice-tone.md](./08-voice-tone.md) | Brand Guardian | Agent-facing product voice. Coordinates with `BOT_RULES.md` (buyer-facing bot voice) |
| — | [PHASE-2-LOCK.md](./PHASE-2-LOCK.md) | — | Locked decisions: brand-600 CTAs, 4px hybrid, color-mode toggle, Dubai-functional voice |

## Phase 3 — Applications

Six standalone HTML mockups built against the locked token system. Open any of them in a browser via `file://` — they validate that the system actually holds under real content.

| File | What it tests |
|---|---|
| [applications/_tokens.css](./applications/_tokens.css) | Complete token set. Translates straight to production Next.js `globals.css`. |
| [applications/agent-desktop.html](./applications/agent-desktop.html) | Agent working surface — desktop. Hot list, conversation thread, three-sender bubbles, inline data card, escalation pill. |
| [applications/agent-mobile.html](./applications/agent-mobile.html) | Agent working surface — mobile (375 × 812). Drawer + bottom-sheet composer + mobile-only fallback rules. |
| [applications/owner-dashboard.html](./applications/owner-dashboard.html) | Brokerage owner dashboard. Compact density, stat cards, dense tables, right-rail activity feed. |
| [applications/listing-detail.html](./applications/listing-detail.html) | Listing detail. Tabs, settings, SPA summary, NOC progress bar, payment schedule, processing stages. |
| [applications/buyer-conversation.html](./applications/buyer-conversation.html) | Agent's view of a buyer-Dalya conversation, side-by-side with the buyer's WhatsApp view of the same thread. The voice-reconciliation test. |
| [applications/login.html](./applications/login.html) | Three audience-variant sign-in surfaces: `/signin/seller`, `/signin/agent`, `/signin/broker`. |

---

## Cross-agent verdict (Eric's review surface)

Three agents worked in parallel against the same brief. Their independent conclusions overlap more than they diverge. The points of divergence are the decisions Eric needs to make before Phase 2 starts.

### Where the three agents agree

1. **"Evolution, not reset" is the wrong framing.** Both Brand Guardian and Cultural Intelligence independently flagged this. Honest framing: **identity continuity, product replacement.** The wordmark, name, Arabic identity, and tone DNA carry through. The visual system, IA, tagline, brand triplet, and surface vocabulary are being rebuilt. Telling the design team "evolution" anchors them too close to the consumer-marketing brand they're supposed to escape from.

2. **The user model is too thin to design against.** Both Brand Guardian and Cultural Intelligence independently called this out. "A Dubai real estate agent" is a 12-word job description. The Dubai brokerage workforce is at least three meaningfully different personas (expat-hustler, Emirati senior, brokerage owner) with conflicting needs. Brand decisions made for the most-visible persona will quietly fail the persona who renews the subscription. **Phase 2 is blocked on a 3-4 persona model.**

3. **The "calm, dense, daily-use" reference brand cluster is Attio, with Notion for white-space and Linear for palette discipline.** Both Brand Guardian and UI Designer reduced Eric's seven references to a coherent thesis. Stripe is mostly noise for product UI (marketing-only). Pipedrive and Dropbox are outliers that don't fit.

4. **Plus Jakarta Sans is wrong for working UI.** Single-agent call (UI Designer), but well-defended: PJS fails Windows ClearType hinting at 14px, tabular figures are uneven, and the editorial energy carries the wrong signal. Recommended: **Inter Variable.**

5. **The current Arabic wordmark probably doesn't survive at 14px.** Single-agent call (Cultural Intelligence). A working-size variant is in Phase 1 scope, not a drop-in from marketing. Contradicts Eric's stated "wordmark carries through unchanged" if read literally.

### Where the three agents disagree — Eric's call

#### **DECISION A: How aggressively does gold get demoted?**

| Position | Argument |
|---|---|
| **Brand Guardian — Option A: retire from product** | Gold (#C9A96E) coded "luxury PropTech" to consumers. It codes the brand Dalya is *leaving* to agents. Keep it in the wordmark + 1–2 brand moments (login, marketing). Banned from product chrome entirely. |
| **Brand Guardian — Option B: one product role** | Gold survives in *exactly one* product role — AED figure typography on asking price. Politically easier; harder to enforce; risks creep within 2 quarters. |
| **UI Designer — four enumerated roles + functional variant** | `#C9A96E` fails WCAG on white (2.19:1). Create `#9C7A3C` as the functional gold (5.21:1 on white). Allowed in 4 roles only: brand-critical CTAs, Verified-SPA badge, Mahoroba commission-savings AED, wordmark + RERA licence strip. Banned elsewhere. |
| **Cultural Intelligence — status-hybrid** | Default chrome is functional/quiet. Client-facing surfaces an agent screenshots to a buyer get a controlled aspirational treatment — gold lives where the client sees it. |

These are not the same answer. The four enumerated roles include CTAs broadly; Option A says no product roles. **Eric, you need to pick the ceiling.** My read: the Cultural framing reconciles Brand Guardian Option B with UI Designer's roles if you bound it to *client-facing-screenshot moments* (Verified-SPA badge, AED-on-asking, commission savings) rather than brand-critical CTAs. CTAs as gold reintroduces the dark-luxury energy.

#### **DECISION B: "Quiet-by-omission" or "quiet-but-present"?**

Cultural Intelligence forced this out: Eric wrote *"Dubai-aware without being visually loud."* That phrase is two different strategies.

- **Quiet-by-omission** — Dubai-ness is in the *absence* of generic-SaaS markers. No Dubai imagery, no Arabic ornament, but also no operational localization beyond compliance. Brand reads as "global SaaS, available in Dubai."
- **Quiet-but-present** — Dubai-ness is in the *operational defaults*. AED-prefix formatting, Sat-Sun weekend logic, Ramadan-aware proactive nudge suppression, Arabic co-equal in the wordmark stack, language switcher in native scripts. Decoration banned, presence asserted.

Cultural recommends quiet-but-present. Brand Guardian's "infrastructure not destination" is compatible with either. **You need to pick.** Once picked, it shapes everything from the empty state copy to the data-viz palette to the date formatting.

#### **DECISION C: Drop JetBrains Mono from AED figures?**

UI Designer recommends yes. Mono on white reads as either "code editor" or "Bayut clone." AED figures move to Inter with tabular numerals + slashed-zero stylistic set. Mono restricted to RERA IDs, JSON snippets, and actual code.

This breaks the current visual identity of AED amounts (which are mono-set in the dark-luxury system). It's the right call but it is a visible change. **You need to acknowledge it.**

#### **DECISION D: Replace primary working color with slate blue `#3D5A80`?**

UI Designer's call. Rejected sage (semantic-role conflict — sage is success/NOC-eligible in the existing system), rejected violet/indigo (Linear-derivative tech-bro association). Settled on a desaturated slate blue 213°/35%/37%.

This is the closest thing to a new brand color you're getting. Calm, regulator-aware, not generic. **Eric, this is your call** — if you want to push toward something else (a green that isn't sage, a tertiary warm tone), now is the moment to say so.

---

## Strategic risks the agents independently flagged

Pulled from each document's risk section. These should be present in any Phase 2 design review.

1. **Gold creep.** Whichever decision Eric picks for Decision A, gold will try to expand back into 5+ roles within two quarters unless the rule is enforced through component-level lint or design review. (Brand Guardian + UI Designer)
2. **Dual-audience drift.** The brokerage-owner dashboard and the agent working surface have different cognitive loads. A single design system that serves both can quietly tilt toward whichever one the designer is sitting in. (Brand Guardian)
3. **Cultural failure modes** (Cultural Intelligence):
   - Coming off as expat-Western to Emirati owners — sterile, foreign, not for them.
   - Coming off as too gulf-coded to expat agents — exotic-feeling, not their tool.
   - Ramadan / Eid surface-behavior misalignment.
   - Gendered language defaults that exclude female agents.
4. **Buyer-facing surface reconciliation.** Dalya remains a buyer-facing brand on listing pages and WhatsApp output. The B2B agent UI cannot diverge so far that the same buyer sees two unrelated brands. (Brand Guardian)
5. **Arabic working-size assets** — the marketing-grade Arabic wordmark is not the same as a sidebar-grade Arabic logotype. Skipping this leaves Phase 2 with an unanswered chrome asset. (Cultural Intelligence)

---

## Phase 1 → Phase 2 transition

Phase 2 does not start until Eric responds to the four decisions above. Two are blocking (A: gold ceiling; user model expansion is implicit in everything Phase 2 does):

| Status | Item |
|---|---|
| Blocking | Decision A — gold's ceiling in product chrome |
| Blocking | User model expansion (3–4 personas, not 1) |
| Required | Decision B — quiet-by-omission vs quiet-but-present |
| Required | Decision C — JetBrains Mono dropped from AED figures (acknowledge) |
| Required | Decision D — slate blue `#3D5A80` as primary (confirm or redirect) |
| Non-blocking flag | "Evolution, not reset" → "identity continuity, product replacement" (internal framing only) |
| Non-blocking flag | "Property intelligence. No pressure." tagline retires (buyer-facing reassurance, irrelevant to agents) |
| Non-blocking flag | "Precise. Inviting. Modern." brand triplet retires (replaced by Trustworthy / Calm / Sharp) |

Once locked, Phase 2 commences: surface/spacing system, component direction (buttons, forms, tables, cards, modals, chat surfaces, nav patterns), motion principles, and full voice/microcopy guidelines.

Phase 3 (application examples) follows Phase 2 lock.
