# Dalya — Brand

*The canonical reference. Read this first. The detailed phase documents in this directory are the depth; this is the operating frame everyone in the company runs on.*

*Last updated: 2026-05-15 · Strategic pivot to B2B integrated · See [`STRATEGIC-PIVOT-2026-05-15.md`](./STRATEGIC-PIVOT-2026-05-15.md) for the underlying shift*

---

## 1. What Dalya is

**Dalya is B2B AI infrastructure for Dubai real estate brokerages.** The product gives individual agents tools to handle buyer conversations, run viewings, acquire listings, and close deals more efficiently. It gives brokerage owners visibility into team performance, pipeline health, and listing acquisition.

We took the work that used to happen on WhatsApp screenshots, broker phone calls, and spreadsheet pipelines, and rebuilt it as software. The chatbot answers buyer inquiries 24/7. The document parser turns a SPA, title deed, or Ejari into a live listing. The dashboard shows a brokerage owner where their business actually stands. The escalation graph keeps the right person in the loop only when it matters.

We started as a consumer-facing brokerage on Mahoroba Realty's RERA licence. **As of 2026-05-15, we are B2B agent infrastructure** — we sell to brokerage owners; agents are the daily users; buyers are consumed via the bot (not customers of Dalya). The shift is documented in full in [`STRATEGIC-PIVOT-2026-05-15.md`](./STRATEGIC-PIVOT-2026-05-15.md). Read that before relitigating positioning.

**Mahoroba Realty** remains alive but in maintenance mode. It is not the primary product. It is held in reserve as an eventual recruitment destination for agents once the Dalya platform is sticky enough to make that move possible.

> **Tagline (internal only — there is no product-facing tagline):** *Infrastructure for the work agents do every day.*

---

## 2. Who we serve

| Tier | Persona | Primary surface | What they need from Dalya |
|---|---|---|---|
| **Customer (the buyer of the product)** | Brokerage owners (Luqman is customer 1) | Desktop dashboard, 2–4 hours sustained daily | Visibility into agent performance, listing pipeline health, listing acquisition signal, RERA + PDPL compliance audit trail. Steered toward **revenue per agent** as the success metric — not headcount, not deal volume in isolation. |
| **Daily user** | Individual agents (entry-level, team leads, senior brokers) at customer brokerages | Mobile-first WhatsApp-adjacent workflow, plus desktop for pipeline depth | A working surface that holds buyer conversations, listing detail, pipeline status, viewing logistics, and offer flow. Calm enough to live in for four hours straight. The tool must *augment* the agent, never visibly replace them. |
| **Operational support (secondary)** | Office managers, support staff, paperwork-only workers at customer brokerages | Desktop, dense data | Post-offer flow: NOC, MOU, trustees registration, Trakheesi, Ejari handling for tenanted resale. |
| **Consumed via the bot, not customers** | Buyers (UAE-based, mostly expat, mobile-first, WhatsApp-preferred) | WhatsApp + portal-embedded chat | Honest, multilingual, fast answers about specific listings. Their experience reflects on the agent and the brokerage. |
| **Deferred** | Marketing specialists, portal-management staff | Different product entirely | Out of scope. Different workflow. |

**One brand, two product surfaces, three audiences.** The brokerage owner sees Dalya as a pane of glass over their business. The agent sees Dalya as the operating system they live in daily. The buyer sees Dalya as a property advisor on WhatsApp. The reconciliation across these three surfaces lives in voice (see §5 and [`08-voice-tone.md`](./08-voice-tone.md) §7).

**Empowerment, not replacement** — this is the load-bearing positioning frame. Dalya takes work the agent shouldn't be doing (repetitive questions, midnight WhatsApp replies, viewing coordination, follow-up nudges) so they can do the work they should be doing (closing deals, managing relationships, navigating negotiations). The agent dashboard shows "your agents are 30% more productive" not "Dalya handled 80% of your conversations." Same underlying reality, different framing, different conclusion the brokerage owner draws. Brokerages that buy the product expecting workforce reduction become unhappy customers when they realize they still need their agents. Set expectations correctly at the sale.

---

## 3. Brand attributes — in priority order

Every design and copy decision is judged against these three, in this order. When they conflict, the higher one wins.

### 1. Trustworthy
RERA-licensed. Regulator-aware. Factually grounded. The numbers are right. The compliance language is correct. The product never lies to make itself look more competent than it is. Trustworthy is mechanical, not aspirational — it is delivered through precision, not promise.

*What it looks like:* exact AED amounts, named regulators ("Trakheesi permit," "DLD transfer fee"), honest "I don't have that detail in the contract" responses, the Mahoroba Realty legal-entity name on every document.

### 2. Calm
The agent uses Dalya for four hours a day. Nothing in the surface gets in their way. No animation that doesn't serve a purpose. No color that doesn't earn its place. No exclamation marks. No "Oops!" copy. Calm is the absence of friction the user didn't sign up for.

*What it looks like:* one primary CTA per surface, neutral-scale doing 80% of the visual work, motion durations capped at 220ms, status pills colored only when status is actually meaningful.

### 3. Sharp
We respect the user's time and their intelligence. The dashboard renders dense data without padding it for decoration. The chatbot answers in one or two sentences. The buttons are verbs. The error messages diagnose and offer an action. Sharp is what separates *operational* infrastructure from *consumer-friendly* infrastructure.

*What it looks like:* tabular numerals everywhere, slashed zero in financial entries, body copy at 14px not 16px, no "Welcome to Dalya" onboarding, microcopy that omits "please."

**Adjectives explicitly off the table:** *luxurious, premium, opulent, bold, vibrant, futuristic, AI-forward.* If a design choice can be defended only with one of these words, the choice is wrong.

---

## 4. We are / We are not

The forcing function for every brand decision. Future hires read this and use it as a yes-or-no test.

| We are | We are not |
|---|---|
| B2B infrastructure for brokerages | A consumer brokerage competing on commission |
| The tool the agent already loves | The tool the agent fears will replace them |
| Sold to brokerage owners | Sold to buyers or sellers |
| Augmenting | Replacing |
| Infrastructure | A destination |
| Confident | Assertive |
| Dubai-grounded | Dubai-themed |
| Calm | Subdued |
| Sharp | Cold |
| Specific | Clever |
| Operational | Editorial |
| One pane of glass over a brokerage | A real-estate portal |
| Built for agents to use daily | Built for buyers to browse |
| RERA-licensed (via Mahoroba) | RERA-affiliated |
| Trustworthy by precision | Trustworthy by claim |
| A workflow + data moat | A proprietary-AI moat |
| Honest about being built on Claude | Pretending to be a foundation model |

Specifically: we are *not* a luxury PropTech brand, *not* a consumer-direct marketplace, and *not* a 0.15% commission story. Those were the previous consumer-direct strategy; they are retired. The current brand is harder to spot than the previous one — and that is the point. Brokerage owners buying agent infrastructure are not impressed by glossy. They are impressed by precision, regulatory awareness, and visible agent adoption.

---

## 5. Voice

One paragraph, three principles, one rule.

**The principles:** factual, brief, specific. Every product string passes all three or it ships rewritten.

**The rule:** the bot's buyer-facing voice (governed by [`BOT_RULES.md`](../BOT_RULES.md)) and the product's agent-facing voice ([`08-voice-tone.md`](./08-voice-tone.md)) share posture and diverge in register. The bot speaks in conversational sentences to a buyer making a decision. The product speaks in operational fragments to an agent doing their job. Both are calm. Both are precise. Both name Eric on first mention as "our Lead Broker at Dalya who handles all transactions." Neither apologizes by default. Neither uses "leverage," "delight," "Oops!", or the word "just."

**The reconciliation:** a buyer who screenshots a chat to a friend and an agent who shares their working surface to a client must both look like the same brand. The voice underneath is identical; only the surrounding chrome differs.

The complete required and banned phrase lists are in [`08-voice-tone.md`](./08-voice-tone.md) §4–§5. The Dubai-functional vocabulary (off-plan resale, Trakheesi permit, NOC threshold, trustees office, 0.15% commission, RERA-licensed, Mahoroba Realty) is operational language and required. Decorative Dubai-ness is banned.

---

## 6. Visual at a glance

### Wordmark
**dalya** — Inter 700, slate blue `#3D5A80`, letter-spacing `-0.015em`. Lower-case. Renders at 80% opacity in dense product chrome so it doesn't compete with primary CTAs. Renders at 100% on signed-out, marketing, login, and transactional-email surfaces. There is no logo mark separate from the wordmark.

### Color — the only colors that matter
- **Primary working color: slate blue `#3D5A80`** (brand-500). Wordmark, focus rings, links, selected states, secondary primary buttons. Brand-thread throughout.
- **Top-tier CTA: deeper slate `#324B6B`** (brand-600). Reserved for 3–5 brand-critical CTAs across the entire product: Upload SPA, Accept Offer, Send to Eric, Confirm destructive. Not for every primary button.
- **Workhorse: the neutral scale.** 11 steps from `#FFFFFF` to `#0A0A09`, warm-leaning (slight 1–2° warm bias at the top end). Carries 80% of the UI.
- **Semantics: sage / copper / brick red.** Success `#4A7C6F`, warning `#B7793A`, error `#B84838`. Bank-grade tones, never toast-notification bright.

**Gold (`#C9A96E`) is fully retired.** Not in product, not in marketing, not in the wordmark. The previous consumer brand's signature color is gone. Differentiation now lives in typography, density, voice, and surface restraint — not color memorability.

Full color system in [`02-color-direction.md`](./02-color-direction.md) and locked tokens in [`applications/_tokens.css`](./applications/_tokens.css).

### Typography
- **Inter Variable** — UI default. 14px body, tabular-nums for numerals, slashed-zero stylistic set enabled (`ss01`) on financial entries.
- **IBM Plex Mono** — code, RERA Trakheesi IDs, JSON snippets, terminal output. Never AED amounts (those use Inter tabular-nums).
- **IBM Plex Sans Arabic** — Arabic content. Locale-aware sizing (1.05× the Latin scale at matching weights).
- **Noto Sans Devanagari** — Hindi fallback.

Plus Jakarta Sans and JetBrains Mono are retired. Inter is the test of every other type decision.

Full type system in [`03-typography-direction.md`](./03-typography-direction.md).

### Surfaces
- **Three working levels + one overlay tier.** Stack via tonal lift + 1px hairline border. Shadows scoped to overlays only.
- **Soft-rounded corners.** `radius-2` (8px) is the workhorse. Cards `radius-3` (12px). Modals `radius-3`. Buttons `radius-2`. Avatars `radius-full`.
- **Hairline borders.** All 1px, in three color weights (hairline / default / strong). No double borders. No decorative colored borders.

Full surface system in [`05-surface-spacing.md`](./05-surface-spacing.md).

### Density
- **Comfortable** (default) — agent's primary working surface, all mobile.
- **Compact** (route-scoped) — brokerage dashboard, dense data.
- **Display** (signed-out, marketing) — more whitespace.

Mode switches via `data-density` on the route. Component heights drop, padding shrinks, radii tighten. Type sizes shift down one step in compact.

### Motion
Animation is the exception, not the rule. Four purposes only: state change, spatial continuity, progress feedback, attention to a destructive moment. Everything else is static. No number tickers. No AI-thinking shimmers. No parallax. No celebration animations.

Defaults: durations `120ms / 180ms / 220ms`. Easing `ease-out` `cubic-bezier(0.16, 1, 0.3, 1)`. `prefers-reduced-motion` honored on every animation.

Full motion principles in [`07-motion.md`](./07-motion.md).

### Light + dark
Light is the design baseline. Dark is parallel-designed (not derived), but disabled in Phase 3 build for review clarity. Production cascade: user toggle wins, then OS preference, light fallback.

---

## 7. The product

Two product surfaces. One platform. Shared data layer.

### Individual agent surface (daily user)
- Hot-list sidebar of conversations (Active / Recent / Archived)
- Conversation thread with three-sender bubbles (buyer / Dalya / agent intervention)
- Inline data cards when Dalya surfaces an offer or document reference inside the thread
- "View in working surface" jump from a conversation to the relevant listing
- Per-listing detail with overview, offers, SPA / title-deed / Ejari data, and activity tabs
- Mobile-first: drawer pattern, full-width thread, bottom-anchored composer
- Hot list / who-to-call-today on morning open (Pillar 4, in build)
- Pre-call buyer briefing surfaced before any voice call (Pillar 4, in build)
- Viewing logistics automation for ready stock (Pillar 2, in build)
- See [`applications/agent-desktop.html`](./applications/agent-desktop.html) and [`applications/agent-mobile.html`](./applications/agent-mobile.html)

### Brokerage owner dashboard (customer)
- Tabbed analytics (Overview / Listings / Agents / Reports) with a left filter rail
- Compact density throughout
- Stat cards at the top steered toward **revenue per agent**, dense listings + offers tables below, real-time activity feed in the right rail
- Agent performance analytics with empowerment-not-replacement framing
- Listing acquisition signal: owner pipeline + outreach engagement (Pillar 3, in build)
- Compliance + audit trail (RERA + PDPL)
- See [`applications/owner-dashboard.html`](./applications/owner-dashboard.html) and [`applications/listing-detail.html`](./applications/listing-detail.html)

### Buyer-facing surface (consumed via the bot, not a product surface customers buy)
- WhatsApp (and increasingly, embedded chat on Property Finder and Bayut listing pages)
- Dalya answers in English, Arabic, Russian, Hindi (Mandarin pending — Pillar 1)
- Governed by [`BOT_RULES.md`](../BOT_RULES.md) — the most prescriptive document in the system, because the bot is the front line that every buyer experiences
- Document grounding expands beyond SPA to include title deed, Ejari, service charges, NOC, valuation, snagging, mortgage (Pillar 1 + Document layer, in build)
- See [`applications/buyer-conversation.html`](./applications/buyer-conversation.html) for the agent's view of a conversation alongside the buyer's WhatsApp view

### Sign-in
- Three audience variants at `/signin/seller`, `/signin/agent`, `/signin/broker`
- Same Supabase auth backend, audience-specific sub-headline and post-login redirect
- "Seller" path is the residual surface for Mahoroba's own listings under maintenance-mode operation. Primary B2B paths are `/signin/agent` (agents at customer brokerages) and `/signin/broker` (the brokerage owner).
- See [`applications/login.html`](./applications/login.html)

---

## 8. The escalation graph — the brand made operational

The single most distinctive thing about Dalya is what gets escalated to a human and what doesn't. Voice and design follow from this:

| Trigger | Routes to | Why |
|---|---|---|
| Above-threshold offer | Eric, high priority, Telegram + dashboard | The seller has signaled they'd entertain offers above this number; we surface them immediately. |
| Marginal offer (within 2% below threshold) | Eric, normal priority | Worth a look, not worth a phone call. |
| Soft offer + buyer steps back | Eric, normal priority | Warm lead leaving without commitment — Eric follows up. |
| Returning buyer references prior context | Eric, normal priority, on T1/T2 | Continuity matters. Buyer expects you remember them. |
| Form A / Trakheesi / RERA documentation request | Eric, co-broker compliance | Regulator-adjacent, Eric handles offline. |
| BRN request | Eric, dedicated channel | Distinct from Form A — peer-broker professional courtesy. |
| Conveyancing lawyer with verified named buyer | Eric, high priority | Real transaction in motion. |
| PDPL / GDPR / data deletion | Eric + compliance, high priority | 30-day regulatory clock starts. |
| Bypass attempt | Logged to suspicious_activity, no alert | Manipulation, not a real handoff request. |
| Promise of forwarding (the bot said "I'll route this") | Eric, fallback alert | The bot's word must match the system's action. |

Full escalation logic in [`BOT_RULES.md`](../BOT_RULES.md) §8–§14 and `app/core/chatbot_engine.py`.

This list is part of the brand. The fact that Dalya knows the difference between a Form A request and a BRN request — and that those go to different places — is what makes us infrastructure rather than a chatbot.

---

## 9. What's locked, what's still moving

### Locked across Phase 1 / 2 / 3 (do not relitigate)
- The name "Dalya"
- The Arabic identity (Arabic wordmark + IBM Plex Sans Arabic for product copy)
- Gold fully retired
- Slate blue `#3D5A80` as sole primary, `#324B6B` for top-tier CTAs
- Inter + IBM Plex Mono + IBM Plex Sans Arabic typography stack
- "Property advisor" terminology for the bot when it speaks to a buyer; never "chatbot" or "AI assistant" in any surface. Note: *brand* positioning is "agent infrastructure," not "property advisor" — the bot's self-identification is distinct from the platform's positioning.
- Trustworthy / Calm / Sharp brand attributes in priority order
- Quiet-by-omission visual posture
- Dubai-functional voice posture
- 4px hybrid spacing scale
- The two-product-surface model (agent + brokerage owner) with buyers consumed via the bot
- B2B AI infrastructure for brokerages as the strategic positioning (per [`STRATEGIC-PIVOT-2026-05-15.md`](./STRATEGIC-PIVOT-2026-05-15.md))
- Empowerment-not-replacement as the load-bearing product frame

### Still in motion (Phase 3 lock surface or Phase 4)
- Dark-mode design audit (deferred until after Phase 3 light-mode build completes)
- Wordmark working-size variant for the Arabic chrome (Phase 3 deliverable that needs design)
- Iconography library choice (Phosphor or Lucide recommended; pending)
- Marketing site full build-out (homepage and how-it-works pages — pending, now needs to lead with B2B positioning not consumer-direct)
- Marketing specialist surface (deferred — different product entirely)
- Empty-state illustrations (Phase 3 ships without; Phase 4 may add)
- B2B platform infrastructure: multi-tenant scoping, per-brokerage prompt customization, aggregated anonymized data layer, cross-agent opt-out propagation (see [BACKLOG.md](../BACKLOG.md))
- Pricing model (deferred until stickiness proven with Luqman)

### Retired (do not bring back)
- The "Property intelligence. No pressure." tagline (buyer-facing reassurance, irrelevant to agents)
- The "Precise. Inviting. Modern." brand triplet (replaced by Trustworthy / Calm / Sharp)
- The 0.15% commission story as primary brand pitch (it remains accurate operational vocabulary for Mahoroba's residual transactions, but it is *not* the B2B platform's positioning — the platform sells SaaS to brokerages)
- The consumer-direct exit narrative ("transaction engine for Property Finder") — replaced by the B2B exit narrative ("agent infrastructure layer for Property Finder / Bayut / a CRM player")
- The seller-direct funnel ("List with Dalya") — listing acquisition now happens *through* brokerages (Pillar 3), not direct-to-Dalya
- The dark-luxury static landing page (`index.html`, 919 lines) and the original frontend developer brief (`dalya-frontend-developer-brief.md`) — obsolete as product spec, retained as historical reference only
- Plus Jakarta Sans (retired in favor of Inter)
- JetBrains Mono for AED figures (retired in favor of Inter tabular-nums)
- The previous dark-luxury surface palette (retired in favor of light-default + designed dark)
- Gold as a UI workhorse (retired entirely)
- "Evolution, not reset" as internal framing (replaced by "identity continuity, product replacement")

---

## 10. Where to look for more

### Brand documents (this directory)
| File | Use when |
|---|---|
| [BRAND.md](./BRAND.md) (this document) | Reading the brand for the first time, onboarding new hires, settling first-principles disputes. |
| [00-README.md](./00-README.md) | Quick index of all brand documents. |
| [PHASE-1-LOCK.md](./PHASE-1-LOCK.md) | Confirming what was decided about gold, color mode, user model, voice posture. |
| [PHASE-2-LOCK.md](./PHASE-2-LOCK.md) | Confirming the four operational decisions: brand-600 CTAs, 4px hybrid, prefers-color-scheme, Dubai-functional voice. |
| [01-foundations.md](./01-foundations.md) | Brand attribute definitions, voice posture, strategic risks. |
| [02-color-direction.md](./02-color-direction.md) | Hex values, contrast pairings, data-viz palette. |
| [03-typography-direction.md](./03-typography-direction.md) | Type scale, weight rules, numeral handling, Arabic pairing. |
| [04-cultural-strategy.md](./04-cultural-strategy.md) | Dubai context, RTL operational rules, multilingual stack. |
| [05-surface-spacing.md](./05-surface-spacing.md) | Spacing, surfaces, borders, radii, shadows, density, Tailwind v4 implementation. |
| [06-components.md](./06-components.md) | Button, input, table, card, modal, conversation, navigation patterns. |
| [07-motion.md](./07-motion.md) | What we animate, ban list, duration + easing tokens. |
| [08-voice-tone.md](./08-voice-tone.md) | Product microcopy, banned phrases, required phrases, voice review checklist. |

### Applications (proof of system under real content)
| File | What it tests |
|---|---|
| [applications/_tokens.css](./applications/_tokens.css) | The complete token system. Drop into the Next.js app's globals.css to translate the brand to production. |
| [applications/agent-desktop.html](./applications/agent-desktop.html) | Agent working surface, desktop. Hot list + conversation thread + composer. |
| [applications/agent-mobile.html](./applications/agent-mobile.html) | Agent working surface, mobile (375px). Drawer + bottom-sheet composer. |
| [applications/owner-dashboard.html](./applications/owner-dashboard.html) | Brokerage dashboard. Stat cards + dense tables + activity feed in compact density. |
| [applications/listing-detail.html](./applications/listing-detail.html) | Listing detail. Tabs + settings + SPA summary + NOC progress + payment schedule + processing stages. |
| [applications/buyer-conversation.html](./applications/buyer-conversation.html) | Agent view + WhatsApp view side-by-side. The voice-reconciliation test. |
| [applications/login.html](./applications/login.html) | Three audience-variant sign-in surfaces. |

### Product files (where brand becomes code)
| File | Use when |
|---|---|
| [`/CLAUDE.md`](../CLAUDE.md) | Project-level context Claude Code uses on every session. Pending update to align with this document. |
| [`/BOT_RULES.md`](../BOT_RULES.md) | The buyer-facing bot voice. Reading this is mandatory before touching prompts. |
| `app/core/prompt_builder.py` | Where the bot's persona, tone, and escalation language live. |
| `app/core/chatbot_engine.py` | The escalation graph. Where the brand becomes operational behavior. |
| `frontend/src/app/globals.css` | The production CSS that will receive `applications/_tokens.css` once Phase 3 ships. |

---

## 11. The single sentence

If a future hire reads only one line of this document, the line is:

> **Dalya is B2B AI infrastructure for Dubai real estate brokerages — agents use it to handle more buyers, run more viewings, and close more deals, and brokerage owners use it to see which of their agents are getting better at the job.**

Everything else in this document is the justification.
