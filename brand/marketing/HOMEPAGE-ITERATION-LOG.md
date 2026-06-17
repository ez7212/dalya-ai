# Homepage iteration log

*Build pass 1: 2026-05-15. Three iterations. v3 is current.*

## v1 — first draft

Built directly from the content strategy in [`00-CONTENT-STRATEGY.md`](./00-CONTENT-STRATEGY.md). Hero, frame paragraph, two surfaces, six pillars, empowerment frame, how-we-ship, trust strip, closing CTA, footer.

### What was wrong with v1 (critique)

1. **Hero too crowded.** H1 + sub + 2 CTAs + trust meta = 5 competing elements. Linear/Attio/Mercury heroes ship 3.
2. **"Built for Dubai brokerages" tagline appendage on the H1 weak.** Two thoughts in one headline.
3. **"Talk to us about a design partnership" too long for a button.** Voice §3.1 says 1–3 words.
4. **Italics-on-brand-color in the frame paragraph shouty.** Three emphasis instances in one paragraph.
5. **Hero trust meta overlapped with the trust strip below.** Two locations, redundant.
6. **Empowerment headlines read SaaS-marketing-flavored** ("up", "longer", "compounds"). Should be thesis-shaped sentences.
7. **Pillar SVG icons decorative.** Generic shapes that don't earn their place.
8. **Closing CTA repeated content already on the page.** Too verbose.

## v2 — tightening pass

Changes:
- H1 reduced to single sentence: "Your agents close more deals."
- Hero CTA reduced to one ("Talk to us") + dropped the "See how it works" secondary
- Hero trust meta strip removed (trust strip below handles it)
- Frame paragraph emphasis simplified (kept the `em` tag but styled as text-1, not brand-color)
- Empowerment headlines rewritten as theses
- Closing CTA trimmed

### What was wrong with v2 (critique)

1. **Em-dashes throughout.** Forgot — the brand validator strips em-dashes (Phase 7.5). Hero sub had two, frame paragraph had two. Replace with periods/commas.
2. **Pillar icons remained decorative.** Should be either dropped or replaced with a documentation-grade pattern.
3. **"Two surfaces. One platform." CRM-cliché.** Generic phrase that any SaaS could ship.
4. **Trust strip "Twilio WhatsApp Business" too implementation-specific** for a marketing surface.

## v3 — current

Changes:
- Em-dashes purged throughout (replace-all on " — " → "," then sentence-by-sentence cleanup)
- Pillar icons replaced with monospace `01 / Buyers`, `02 / Viewings` etc. — documentation-grade, matches "data is the hero"
- Two-surface eyebrow changed from "Two surfaces, one platform" to "The platform"
- Trust strip trimmed from 4 items to 3 (dropped Twilio)
- Pillar body copy rewritten with more specific verbs and shorter sentences

### What v3 still has wrong (Phase 2 iteration backlog)

1. **Inline `style="..."` on H2s throughout.** Repeats four times. Extract to a `.section-h2` class.
2. **Pillar grid border-bottom on the last row.** Cosmetic edge case. Add `:nth-last-child(-n+2) { border-bottom: 0 }` rule.
3. **No competitive framing.** Brokerage owners thinking "kvCORE already does this" don't get a response. Single section or paragraph answering "why Dubai brokerages specifically." But this might violate the brand's "don't make claims" posture. Worth an explicit decision.
4. **Dead nav links.** `/brokerages`, `/agents`, `/how-it-works`, `/about`, `/contact`, `/terms`, `/privacy` all stub. Either build the pages or remove the nav items.
5. **Footer copyright.** Says "© 2026 Dalya" — Dalya isn't a legal entity. Mahoroba is. Should be "© 2026 Mahoroba Realty · operating Dalya" or similar.
6. **No social proof or evidence.** Premature now — Luqman hasn't gone live. Once they have, add a quiet "in design partnership with [...]" line above the trust strip.
7. **Iframe surface previews untested across browsers.** Safari's iframe-scale handling differs from Chrome's. Verify on both before any external sharing.
8. **The 56px H1 might be heavy on mobile.** Should scale down at the `sm` breakpoint. Currently single-size.

## Rejected ideas

- **H1 "AI-powered infrastructure for Dubai brokerages."** Rejected — has "AI-powered" which is banned per voice §4 ("brags about a means, not an outcome").
- **H1 "Dubai's first AI-native brokerage platform."** Rejected — has "first" superlative and "AI-native" hype, both banned.
- **A pricing tier section.** Rejected — pricing is deferred until stickiness is proven per the strategic pivot. We pitch design partnerships, not subscriptions.
- **Customer logos at the top.** Rejected — we have one customer (Luqman) and they aren't live yet. Adding placeholders would be dishonest.
- **A hero photo of a Dubai skyline or agents on tablets.** Rejected — quiet-by-omission visual posture per Phase 1.

## What I'd build next

In order of probable impact on conversion:

1. **`/contact` page** — both CTAs go nowhere. This is the blocker for the homepage to produce any leads.
2. **`/brokerages` page** — the depth pitch for the buyer of the product. Currently the homepage is doing both top-of-funnel and depth.
3. **`/how-it-works` page** — for owners who've decided they want to know more before talking. Walks through the six pillars with the actual mockup screenshots.
4. **`/agents` page** — empowerment-not-replacement pitch from the agent's POV. Critical because a worried agent at a customer brokerage could torpedo the deal.
5. **`/about` page** — credibility. Mahoroba's RERA, Eric's background, the design-partnership thesis explained.
6. Marketing site polish: extract shared classes, mobile breakpoint, footer correction.

I'd hold off on `/pricing` until after Luqman renews. Until then, the answer is "talk to us."
