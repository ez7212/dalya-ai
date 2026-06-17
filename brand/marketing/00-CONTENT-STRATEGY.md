# Marketing site — content strategy

*Last updated: 2026-05-15*

## Sitemap

| Page | URL | Audience | Primary CTA |
|---|---|---|---|
| Home | `/` | Brokerage owners (primary), agents (secondary) | Talk to us about a design partnership |
| For brokerages | `/brokerages` | Brokerage owners | Book a 30-min call |
| For agents | `/agents` | Agents — pitch from their POV | (No CTA — empowerment-not-replacement; we sell to their owner, not them) |
| How it works | `/how-it-works` | Anyone | Talk to us |
| About | `/about` | Anyone investigating credibility | Talk to us |
| Pricing | `/pricing` | Owners about to convert | Talk to us (pricing is deferred — see strategic pivot) |
| Contact / Book a call | `/contact` | Everyone | (Form submission) |

## Voice posture (per `08-voice-tone.md §2.8`)

The marketing site is the **only surface in the system where Dalya is allowed to make a case for itself.** Register is more assertive than product chrome, but still factual, brief, specific. No hype. No "powered by AI." No "revolutionize." No "delight."

The marketing voice has three jobs in priority order:
1. **Earn the meeting.** The brokerage owner closes the tab if it reads as another generic SaaS landing page. Specificity to Dubai real estate is the wedge.
2. **Set expectations correctly.** Empowerment not replacement. If they buy expecting workforce reduction we will lose them in month 3.
3. **Signal regulatory awareness.** RERA. PDPL. Mahoroba's licence. Quiet trust signals throughout.

## What's on the homepage

1. **Top nav** — minimal: Dalya wordmark, links to For brokerages, For agents, How it works, About. Single CTA "Talk to us" on the right.
2. **Hero** — H1 + one-sentence sub + single CTA. No image, no animation, no social proof bar.
3. **The frame** — one short paragraph stating what we are and aren't. Sets expectation.
4. **Two surfaces (live mockup embeds)** — agent-desktop.html and owner-dashboard.html in iframes. Captions explain who uses each. This is the product evidence.
5. **What Dalya handles** — the six pillars condensed into one scannable list with one-line descriptions each.
6. **The empowerment frame** — three short statements about the outcome shape (revenue per agent up, top agents stay longer, listing acquisition compounds).
7. **How we ship** — design partnerships, not enterprise sales. Builds trust by explaining the unusual way we operate.
8. **Built on Mahoroba's RERA licence** — quiet trust strip.
9. **Single secondary CTA** — at the bottom, repeated.
10. **Footer** — copyright, terms, privacy, RERA notice. No "press kit," no "careers" (we don't have either yet).

## Image strategy — no stock photography

Quiet-by-omission applied to imagery: no Dubai skyline shots, no agents-on-tablets staged photos, no glass-tower buildings, no marble. The only visuals are:
- **Product surface screenshots** rendered live via `<iframe src="../applications/...">`.
- **Inline SVG icons** for the feature pillar list (lucide or phosphor style — geometric, single-stroke, slate-blue).
- **Typography as art**: the wordmark and the H1 are the visual hierarchy.

If at any point we feel we need a hero image, the brand has failed somewhere else.

## What's NOT on the marketing site

These belong to the retired consumer-direct strategy and have no place on the B2B site:
- "0.15% commission disruption" hero
- "List with Dalya" seller-facing CTA
- "Buyer savings calculator"
- "Live on Property Finder in 30 minutes"
- The dual-audience (Sell / Buy) page split — the Buy surface is the bot on WhatsApp, not a marketing page

## Iteration log

The homepage was iterated three times in the first build pass. The iteration log is in [`HOMEPAGE-ITERATION-LOG.md`](./HOMEPAGE-ITERATION-LOG.md) — read it before significantly editing the homepage so you understand what was tried and rejected.
