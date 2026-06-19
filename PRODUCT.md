# Product

## Register

brand

> Dalya is dual-register. The `(marketing)` site is **brand** (design *is* the product — landing/marketing, demo-gen). The `(app)` agent & owner dashboard is **product** (design *serves* the workflow). `brand` is the default because this surface — the public marketing site — is what impeccable is set up around here. For dashboard / app / settings work, treat the register as **product** and read `reference/product.md`. Pick per surface.

## Users

**Individual agents (primary daily users).** Entry-level agents and team leads at small-to-medium Dubai brokerages. Mobile-first, WhatsApp-adjacent workflow; the dashboard is a daily-use surface for hours at a stretch. Trust trigger: the tool closes more deals and makes their day easier — it never replaces them.

**Brokerage owners (secondary — the buyer of the product).** Owners of small-to-medium Dubai brokerages who care about team performance, listing acquisition, and revenue per agent. Primarily desktop, sustained analytical work. Trust trigger: real telemetry on agents/listings, RERA + PDPL compliance, demonstrable revenue lift per agent. The marketing site speaks primarily to this buyer and to the agents who will use it daily.

**Buyers (consumed via the bot, not customers).** UAE-based qualified buyers who message via WhatsApp or portal-embedded chat. The bot answers on the agent's behalf. Multilingual (EN/AR/RU/HI). Their experience matters because it reflects on the agent and brokerage.

**Operational staff (tertiary).** Office managers / paperwork-only staff handling post-offer flow (NOC, MOU, trustees, Trakheesi).

## Product Purpose

Dalya is **B2B AI infrastructure for Dubai real-estate brokerages**. It gives individual agents tools to qualify buyers, run viewings, escalate serious offers, and keep follow-up tight; it gives owners visibility into team performance and pipeline. Positioning is **empowerment, not replacement** — Dalya does the work agents shouldn't (initial qualification, repetitive questions, midnight WhatsApp replies, viewing coordination) so agents can close. The owner-facing metric is **revenue per agent**, not headcount.

Dalya is **software, not RERA-licensed** — every listing on the platform is operated by a RERA-licensed brokerage; regulatory attribution is per-listing, never "Dalya is the licensee."

The current MVP is four blocks: **24/7 inquiry concierge · smart escalation to agents · morning hot list + follow-up · viewing logistics**. The marketing site's job is to communicate exactly those built capabilities and convert qualified brokerages into **booked demos** (pilot brokerages are already secured; the public site sells). Success = booked demos / agent stickiness; the site claims only what is actually built.

## Brand Personality

**Three words, in priority order: Trustworthy. Calm. Sharp.**

Voice: specific numbers, named sources, no exaggeration — default to under-claiming and over-delivering. Quiet by omission: no notification theatre, no growth-loop manipulation, no fake urgency. For capability, write present-tense and concrete ("answers the 2am inquiry, qualifies the buyer, flags the serious ones"). CTAs are operational verbs (Book a demo · Send · Accept · Escalate), not marketing fluff. The AI names itself **Dalya** / **Property Advisor** — never "chatbot," "bot," or "AI assistant."

## Anti-references

- **Property Finder / Bayut** — crowded portal UI, orange/red CTAs, broker-first clutter.
- **Generic SaaS landing** — pastel gradients, gradient-hero blobs, three-column icon-card grids, hero-metric template, laptop stock photos.
- **Tech-bro brutalism** and **crypto/Web3** — neon accents, glowing borders, aggressive motion.
- **The retired consumer-marketing Dalya** — dark-luxury navy `#0F1923` + gold `#C9A96E`, "luxury PropTech" residue, Dubai-themed exoticization. Fully retired; do not revive.

## Design Principles

1. **Empowerment, not replacement.** The interface must visibly augment the agent. The relationship, judgment, negotiation, and close always stay with the human.
2. **Trust through specifics.** Real numbers, named sources, compliance attributed to the listing's own RERA-licensed brokerage. No vague superlatives; no claiming Dalya is the licensee.
3. **Calm by omission.** Generous whitespace, restrained motion, accent colour only where status is genuinely meaningful. The product should be livable for four hours straight.
4. **Sharp at the moment of decision.** The brief reads in twenty seconds because that's how long an agent has before the call. Information arrives pre-organized, next action obvious.
5. **Claim only what's built.** Marketing reflects the actual shipped MVP — never advertise deferred or unbuilt capabilities.

## Accessibility & Inclusion

Target **WCAG 2.2 AA**: body text ≥4.5:1 (large text ≥3:1), visible keyboard focus, logical tab order, semantic landmarks, and a `prefers-reduced-motion` alternative for every animation.

**RTL is required** — author with logical CSS properties (`margin-inline`, `padding-inline-start`, Tailwind `ms-/me-/ps-/pe-`). **Multilingual:** EN/AR/RU/HI, using IBM Plex Sans Arabic for Arabic and Noto Sans Devanagari for Hindi. AED amounts use Inter tabular-nums with the slashed-zero stylistic set.
