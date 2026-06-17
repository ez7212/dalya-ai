# Phase 1 — Lock Decisions

*Locked: 2026-05-14, by Eric. These are the constraints Phase 2 designs against.*

## Locked

### 1. Gold (#C9A96E) is fully retired — product AND marketing AND wordmark
**Rationale (Eric):** Most agents are expats; gold is too strong a color for daily viewing. *"I dont really want gold anywhere."*

This is the most aggressive of all options floated. Brand Guardian recommended Option A (gold survives in wordmark + 1–2 brand moments). UI Designer proposed a two-gold system. Cultural Intelligence proposed status-hybrid. Eric overrode all three.

Implications now in force:
- No gold CTAs.
- No gold on AED figures, Verified-SPA badges, RERA strip, commission-savings callouts.
- **Wordmark color**: slate blue `#3D5A80` (matches the new primary). Locked.
- The previous brand identity's signature color is fully replaced. Phase 2 component work treats `#C9A96E` as a banned token. Any reference to "gold" in `CLAUDE.md`, `BOT_RULES.md`, or existing CSS is legacy documentation pending cleanup.
- Slate blue `#3D5A80` is now the sole brand-driven UI color carrier across product, marketing, login, transactional email, wordmark.

**Trade-off Eric is making (worth naming):** the brand loses its most distinctive identity signal. Slate blue is competent and calm but it is also a common SaaS color (variants of it appear in Linear, Stripe, Notion, Attio). Differentiation now has to come from typography, density, voice, and surface restraint — not color memorability. This makes typography choices (Inter + IBM Plex Mono) and voice/tone (Phase 2 deliverable) load-bearing in a way they wouldn't be if gold was still doing some lifting.

### 2. Quiet-by-omission, not quiet-but-present
**Rationale (Eric):** confirmed selection.

This overrides Cultural Intelligence's recommendation. The brand strategy now is **"global infrastructure that operates in Dubai,"** not **"Dubai-grown infrastructure."**

Implications now in force:
- No Sat-Sun weekend logic as a brand statement (still a date-handling fact).
- No Ramadan-aware proactive UX. Compliance only, not cultural surfacing.
- No Arabic-script ornamentation, no calligraphy-as-accent.
- AED prefix is a currency formatting rule, not a brand surface.
- Arabic is supported because the regulator requires it and clients use it, not because the brand identifies with it.
- **Trade-off Eric is making (worth naming):** Dalya forfeits some moat against a global SaaS competitor entering Dubai. Quiet-but-present would have built switching cost through cultural fluency the competitor can't easily replicate. Quiet-by-omission is more scalable beyond UAE later, less defensible inside it. Acceptable given the agent persona is mostly expat.

### 3. JetBrains Mono drops from AED figures
**Rationale (Eric):** confirmed.

AED figures move to Inter with tabular-nums + slashed-zero. Mono restricted to: RERA Trakheesi IDs, JSON snippets in admin tooling, actual code.

**Mono typeface change:** UI Designer recommended IBM Plex Mono replace JetBrains Mono. Locked unless objected.

### 4. Slate blue #3D5A80 as primary working color
**Rationale (Eric):** use it for now, revisit halfway through UI build.

Locked as primary for Phase 2 component work. Eric flagged this for revisit; the natural revisit moment is after the first 5–8 production component sets are built and the color has been observed under load. Phase 2 will produce visual artifacts you can judge against.

**Worth knowing:** primary color is foundational and changing it later means re-skinning every interactive surface. If you have any instinct now that slate blue is the wrong call, surface it before Phase 2 starts. Mid-build changes are expensive.

## Non-blocking flags (auto-applied)

- "Evolution, not reset" → internal framing changes to **"identity continuity, product replacement."**
- Tagline "Property intelligence. No pressure." retires. It was a buyer-facing reassurance and is irrelevant to the agent surface. A new product-side tagline is not required for Phase 2; the product is the tagline.
- Brand triplet "Precise. Inviting. Modern." retires. Replaced by **Trustworthy / Calm / Sharp** (priority order) from Eric's brief.

## User model — Eric's expansion + proposed clustering

Eric's list, verbatim: *entry-level agents, team leads, brokerage owners, support staff, office managers, marketing specialists, workers who only handle paperwork once the offer is accepted.*

That's 7 roles. Designing against 7 personas is unworkable; the system tilts toward whichever one the designer is sitting in. Proposed clustering:

| Tier | Role | Behavior | Primary surface |
|---|---|---|---|
| **Primary (transacting)** | Entry-level agents | High-volume buyer conversations, listing-side or buyer-side | Mobile + WhatsApp-adjacent |
| **Primary (transacting)** | Team leads | Same as entry-level plus pipeline oversight for 3–8 agents under them | Mobile + desktop |
| **Primary (oversight)** | Brokerage owners | Aggregate visibility, performance, commission economics | Desktop dashboard |
| **Secondary (operational)** | Office managers | Listing intake, status, paperwork routing | Desktop |
| **Secondary (operational)** | Support staff + paperwork-only workers | Post-offer transaction shepherding (NOC, MOU, trustees, Trakheesi) | Desktop |
| **Tertiary** | Marketing specialists | Listing photography, portal listings, lead-gen workflow | Desktop (likely a different surface) |

Proposed Phase 2 design priorities:
- **Design first against the Primary tier (3 personas).** This is the workflow surface.
- **Design the operational secondary tier next.** Distinct enough to need its own pattern set but shares the chrome and the data primitives.
- **Defer marketing specialists to Phase 3 or a separate surface.** Their workflow is portal-management adjacent and probably doesn't share the working chrome at all. Treat as out-of-scope for the agent product unless Eric explicitly wants it in.

**Eric — confirm or override this clustering before Phase 2 launches.**

## All decisions resolved — Phase 2 active

1. **Wordmark**: slate blue `#3D5A80`. Locked.
2. **User model clustering**: confirmed. Primary tier (entry agents / team leads / brokerage owners) is the design target. Secondary operational tier follows. Marketing specialists deferred to a separate surface.

Phase 2 commences against these constraints:
- Surface and spacing system (UX Architect)
- Component direction (UI Designer)
- Motion principles (UI Designer)
- Voice and tone guidelines (Brand Guardian)

---

## Phase 2 amendments to Phase 1 locks (2026-05-14)

Phase 2 work surfaced two constraints from Phase 1 that needed adjustment. Both amendments accepted by Eric on review:

- **8px-strict spacing grid → 4px-base hybrid.** Five reserved 4px-only steps are permitted (form input padding, compact table rows, icon-in-pill gap, avatar-name gap, small ornament gaps). Default authoring guidance remains 8px-multiple. See `05-surface-spacing.md` §0.1 and `PHASE-2-LOCK.md` Decision 2.
- **Light-default everywhere → `prefers-color-scheme` + sticky user toggle.** Light remains the *fallback* default if neither in-app toggle nor OS preference resolves, but the system honors the user's choice. The brokerage owner persona's dashboard usage is the strongest case for dark. See `05-surface-spacing.md` §0.2 and `PHASE-2-LOCK.md` Decision 3.

Phase 2 also introduced one new token to honor a Phase 2 risk (gold-retired-system reads as bland):
- **`brand-600` (`#324B6B`)** gains a second role as top-tier-CTA rest state, in addition to its original "pressed state of brand-500" use. Reserved for 3–5 brand-critical CTAs across the product. See `02-color-direction.md` brand scale and `06-components.md` §1.1.
