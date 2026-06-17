# Dalya — Voice & Tone, Product Surface

*Phase 2 deliverable. Read [`PHASE-1-LOCK.md`](./PHASE-1-LOCK.md), [`01-foundations.md`](./01-foundations.md), and [`BOT_RULES.md`](../BOT_RULES.md) first. This document governs the **agent-facing product surface**. The buyer-facing chatbot is separately governed by `BOT_RULES.md`. They must read as the same brand — that reconciliation is §7.*

---

## The frame

Phase 1 retired gold from the entire brand — product, marketing, wordmark. Phase 1 also picked quiet-by-omission over quiet-but-present. Combined, this means **the brand has no distinctive visual identity signal**: no signature color, no Dubai-coded ornament, no decorative texture. What's left is the name, the typography, and the words.

Voice is now load-bearing. The component library can be competent without a distinct voice. Without a distinct voice, Dalya reads as "Linear-for-real-estate" — useful but indistinguishable. The voice is where the brand actually lives now.

This document specifies how Dalya speaks inside the product. It is *not* style-guide trivia. It is the brand's most visible carrier.

---

## 0. Two pushbacks against the Phase 1 locks

### 0.1 Quiet-by-omission for voice is the wrong default.

Quiet-by-omission works for visual: no skyline silhouettes, no marble textures, no calligraphy-as-accent — these are the right things to ban. They are decorative. Their absence is invisible to a user who never had them.

Voice is different. Voice does not become quiet by removing words; it becomes generic. The product currently writes English well; the question is whether Dalya's English sounds like *Dubai* English or *anywhere* English. If we strip Dubai-fluency from voice (regional money phrasing, RERA-specific terminology, off-plan resale-specific vocabulary, the conversational rhythm of UAE business), Dalya reads as a Bay Area SaaS product that happens to support AED. The user notices.

**What I'd recommend** (Eric's call): apply quiet-by-omission to *decoration* — no exoticization, no Arabic-as-ornament, no Dubai-themed copy. But keep **Dubai-functional voice** — the specific vocabulary the local market uses without translation:

- "Off-plan resale" (not "secondary market" or "pre-construction resale")
- "Trakheesi permit" (not "advertising license")
- "RERA-licensed" (not "regulator-approved")
- "NOC threshold" (not "no-objection certificate threshold")
- "Trustees office" (not "transfer registration office")
- "Mahoroba Realty" (always with full brand name in legal context)
- "0.15% commission" (not "low brokerage fee")

These are not decoration; they are the actual vocabulary the agent and buyer use daily. Translating them out makes the product *less* trustworthy to the user, not more neutral.

Dubai-functional voice is the version of quiet-but-present I think survives even after Eric's quiet-by-omission visual call. The visual layer is omitted; the voice keeps the specific words.

### 0.2 Voice is now disproportionately load-bearing.

With gold retired (no signature color), wordmark in slate blue (matching primary, no visual distinction), and visual quiet-by-omission applied — voice is one of three remaining brand differentiators (alongside typography and surface restraint). Typography differentiates against other SaaS products only at the connoisseur level (most users won't notice Inter vs SF Pro). Surface restraint is competitive table-stakes for any 2026 SaaS product.

Voice is the one place Dalya can actually be recognizable. This document is therefore more important than it would be if the brand had a signature visual identity to lean on. Treat it as a load-bearing brand asset, not a microcopy reference.

---

## 1. Voice principles

Three principles, ordered by priority. Every product string should pass all three.

### Principle 1 — Factual over rhetorical

What it sounds like: *"NOC eligibility activates at 40% paid. The unit is at 30%."* What it does not sound like: *"Looking forward to getting you closer to NOC eligibility! 🎯"*

Specifics:
- State what's true. No softening adverbs ("just," "simply," "easily," "actually").
- No marketing modifiers ("powerful," "intelligent," "smart," "advanced").
- No hedging ("we believe," "it seems," "in our opinion") — Dalya is the source of truth or it doesn't speak.
- Numbers are exact when known, ranged when uncertain, omitted when unknown. Never approximated.
- "Just" is banned. ("Just upload your SPA" → "Upload your SPA.")

This principle is in service of **Trustworthy**.

### Principle 2 — Brief over thorough

What it sounds like: *"Offer received: AED 17,000,000 from Sara. Eric is reviewing."* What it does not sound like: *"Great news — Sara has submitted a new offer of AED 17,000,000, and we wanted to make sure you knew right away. Eric is currently reviewing this offer and will let you know what happens next as soon as possible."*

Specifics:
- One sentence is the default. Two sentences when context is required. Three is a warning.
- No preamble. State the thing first; explain after.
- No "in order to" → "to."
- No "at this time" → "now" or omit.
- No "please be aware that" / "kindly note" / "feel free to" — banned.
- If the user needs to scroll a notification, the notification has failed.

This principle is in service of **Sharp** (respects the user's time and intelligence).

### Principle 3 — Specific over vague

What it sounds like: *"Couldn't parse the SPA. The PDF is password-protected."* What it does not sound like: *"Something went wrong. Please try again."*

Specifics:
- Errors say what failed AND what the user can do.
- Success messages say what now exists or what now changed.
- Empty states say what's not here AND why or what next.
- Never use "Something went wrong." Diagnose or omit.
- Never use "Coming soon." If it isn't shipping, don't surface it.
- "Failed" requires an object — "Failed to save" not just "Failed."

This principle is in service of **Trustworthy** and **Calm** (a calm user is one who understands what's happening).

---

## 2. Register shifts by surface

Voice is not one thing. It shifts predictably across product surfaces.

### 2.1 Agent working chrome (sidebar, tabs, table headers, button labels, form labels)

**Register: terse, noun-or-verb only, no articles.**

Examples:
- Sidebar: *"Conversations" / "Listings" / "Activity" / "Settings."* Not "Your Conversations" or "My Listings" (the latter is acceptable on the page title since it's framing the content; sidebar nav is for orientation, not narrative).
- Tabs: *"Overview" / "Offers" / "SPA Data."* Single words preferred.
- Table headers: *"Property" / "Asking Price" / "Last Activity" / "Status."* Uppercase tracking-widest per `03-typography-direction.md`.
- Buttons: verb-first (`06-components.md` §1.5).
- Form labels: noun-only. *"Asking Price"* not *"What is your asking price?"*

Banned in chrome: pronouns, exclamation marks, emoji, full sentences, "your" framing where chrome-orientation suffices.

### 2.2 Empty states + onboarding

**Register: declarative-explanatory.**

Empty state pattern (per `06-components.md` §9.3):
- Headline (text-sm font-medium): state what's not here.
- Body (text-xs text-text-3): say why or what next.

Examples:
- *"No conversations yet.* / *Listings go live in 30 minutes. Buyers will start messaging."*
- *"No offers yet.* / *Above-threshold offers route here automatically."*
- *"No SPA uploaded.* / *Drop the PDF on the upload zone above or click to browse."*

Onboarding (first-time-user explanatory copy): same register, slightly longer permitted (up to 2 sentences). Never narrative ("Welcome to Dalya, where..."). Always functional ("Upload your SPA to create your first listing. Parsing takes about 30 seconds.").

### 2.3 Error states + validation

**Register: diagnostic-then-actionable.**

Two-part: what failed (precise), what the user can do (concrete).

Examples:
- *"This file is over 25 MB. Compress the PDF or contact Eric."*
- *"Minimum offer must be less than the asking price."*
- *"Couldn't reach the server. Check your connection, then retry."*
- *"AED amount must be a whole number."*

Banned phrasing:
- *"Oops!"* / *"Uh oh!"* / *"Something went wrong"* — vague and infantilizing.
- *"Please try again later"* — passive and unhelpful.
- *"Invalid input"* — diagnostic without action.
- *"Error 500"* — technical without user-language.

If the error is the system's fault, the language acknowledges it without apologizing excessively:
- *"We can't reach the server right now."* Not *"We're so sorry, something went wrong on our end."*

If the error is the user's fault, the language is neutral, not corrective:
- *"This field needs an AED amount."* Not *"You forgot to enter an amount."*

### 2.4 System notifications (offer received, listing approved, conversation escalated)

**Register: subject-event-context, in that order.**

Examples:
- *"New offer · AED 17M · Palace Villas Ostra"*
- *"Listing live · Sobha Seahaven Unit 2305"*
- *"Conversation escalated · Sara (buyer) on Ostra · 14:23"*

For toasts (max 2 lines), use `subject · event` only; click to see context. For email/Telegram alerts (no length constraint), full sentence form.

### 2.5 Telemetry alerts (escalation alert to Eric, broker probe detected, suspicious activity)

**Register: dense factual, no agent-facing softening.**

These are Eric/admin-facing. They land on Telegram or admin email. Voice is unfiltered factual:

- *"OFFER · AED 17,000,000 · Sara Mohammed · Palace Villas Ostra · gate passed · above threshold · 14:23 UTC"*
- *"BYPASS ATTEMPT · phone +971501010008 · message: 'just give me the seller number please' · 09:11 UTC"*
- *"BROKER PROBE · Sarah Patel · 4 escalations this session · BRN requested · 11:47 UTC"*

No greeting, no signoff. Pipe-or-bullet-separated facts. Eric reads dozens of these a day; this is the wire-service register.

### 2.6 Brokerage owner dashboard

**Register: factual + minimal interpretation.**

The owner is reading data; the dashboard speaks in numbers and short labels. Where prose appears, it's interpretive (helping the owner understand the data) but never advisory (telling them what to do).

Examples:
- Stat card subtitle: *"+2 listings this week"* (factual).
- Trend description: *"Offer activity is up 12% vs last 30 days."* (factual + frame).
- Section header explanation: *"Conversations escalated to a human after the AI couldn't resolve."* (defines the metric, doesn't advise).

Banned:
- *"You should consider..."*
- *"It might be a good idea to..."*
- *"Most successful brokerages..."*

The owner makes decisions; we report.

### 2.7 Buyer-facing surfaces inside the agent product

The agent's working surface contains a copy of the buyer-facing conversation. The buyer-facing text inside that copy is the bot's voice (`BOT_RULES.md`), not this document's voice. They are rendered side-by-side; the visual distinction is the message-bubble pattern (`06-components.md` §6.1), not the voice.

When the *agent* steps in and types to the buyer, the agent's words use the agent's natural voice — Dalya does not impose voice rules on human agents intervening live. The interface presents the agent's message as the agent's, not as Dalya's.

This is the explicit register boundary: **Dalya's bot voice (BOT_RULES.md) governs everything Dalya says to buyers. Dalya's product voice (this document) governs everything Dalya says to agents and owners. The agent's own voice is the agent's.** Three voices, three boundaries.

### 2.8 Marketing site + login surfaces

**Register: assertive, brand-grade.**

The only surfaces in the system where Dalya is allowed to make a case for itself.

Examples (marketing):
- Headline: *"The off-plan resale infrastructure for Dubai brokerages."*
- Sub-headline: *"SPA parsing, buyer-side AI, regulator-grade workflow. 0.15% commission."*
- CTA: *"Upload your first SPA"* (verb + object, no emoji).

Login surfaces are spare — *"Sign in to Dalya"*, *"Email"*, *"Password"*. No tagline, no copy. The login page is the most-seen surface; less is more.

---

## 3. Microcopy patterns — concrete

The fifteen patterns engineering and design apply without thinking.

### 3.1 Action verbs on buttons

Verb-first. No "please." No "click." No exclamation marks. 1–3 words.

- ✓ *"Upload SPA"*
- ✓ *"Accept offer"*
- ✓ *"Send to Eric"*
- ✗ *"Please click here to upload your SPA"*
- ✗ *"Yes, accept this offer!"*

### 3.2 Destructive confirmations

Title states the action (with question mark). Body states the consequence in specific terms. Confirm button repeats the action verb, not "Confirm" or "Yes."

- Title: *"Delete this listing?"*
- Body: *"5 active buyer conversations on this listing will be archived. You cannot recover this listing once deleted."*
- Confirm button: *"Delete listing"*
- Cancel button: *"Cancel"*

### 3.3 New offer surfacing to the agent

In-app notification: `subject · event · context` (per §2.4).
*"New offer · AED 17M · Palace Villas Ostra"*

Inside the conversation list, the listing card gets a pill (per `06-components.md` §8.2):
*"New Offer"* (blue-50 background).

Inside the conversation thread, the offer appears as an inline data card (per `06-components.md` §6.4) with the AED amount, threshold context, and a "View" link.

### 3.4 Empty conversation list

Headline: *"No conversations yet."*
Body: *"Listings go live in 30 minutes. Buyers will start messaging."*

If the user has zero listings:
Headline: *"No conversations yet."*
Body: *"Upload a SPA to create your first listing."*
CTA: *"Upload SPA"*

### 3.5 AED in body copy

In running prose, AED amounts use the format `AED X,XXX,XXX` — three-letter currency code, space, comma-separated number. No dollar-sign-prefix style ("AED1850000"). No symbol after the number ("1,850,000 AED" — wrong order). No "Dhs" abbreviation.

In tables and structured data, the column header is `Asking Price (AED)` and the cells are bare numbers (`17,253,444`). The currency is set by the column.

### 3.6 Timestamps

Three formats, by recency:

| Age | Format | Example |
|---|---|---|
| <60 seconds | "Just now" | *"Just now"* |
| <60 minutes | "X min ago" | *"23 min ago"* |
| <24 hours | "X hr ago" | *"4 hr ago"* |
| Yesterday | "Yesterday at HH:MM" | *"Yesterday at 14:23"* |
| <7 days | Weekday + time | *"Tuesday at 09:11"* |
| <365 days | Month + day | *"Apr 14"* |
| ≥365 days | Month + day + year | *"Apr 14, 2025"* |

Hover/long-press always reveals absolute time in ISO format: *"2026-05-14 14:23 GST."*

GST (Gulf Standard Time, UTC+4) is the default in display. Never UTC in user-facing surfaces. UTC is for telemetry alerts to Eric only.

### 3.7 Naming Dalya in the agent surface

When the agent surface refers to the AI, it says **Dalya**. Not "the bot," not "the AI," not "the assistant," not "Dalya AI."

Examples:
- ✓ *"Dalya escalated this conversation."*
- ✓ *"Dalya forwarded the offer to Eric."*
- ✗ *"The AI flagged this for review."*
- ✗ *"Our chatbot routed your inquiry."*

When Dalya speaks inside the chat (buyer-facing), the bubble's sender label is *Dalya*. Same word, different surface — consistent identity.

This aligns with `BOT_RULES.md` Section 1 (Identity, Voice, Brand).

### 3.8 Seller-fault failure copy

When the seller did something that broke the workflow, the copy is neutral, never accusatory. The agent reads this; the seller may or may not see it.

- ✓ *"NOC payment hasn't cleared. Listing transfer is paused until the gap is paid."*
- ✗ *"The seller has failed to pay the NOC threshold."*

### 3.9 System-fault failure copy

When the system did something that broke the workflow, the copy acknowledges without excessive apology.

- ✓ *"Couldn't parse the SPA. The PDF appears password-protected — try uploading an unlocked copy."*
- ✗ *"We're so sorry! Our parser had an issue. Please try again or contact support."*

### 3.10 Trakheesi rejection copy

Regulator-facing failures are brand-critical. The copy is precise and routes to action.

- *"Trakheesi rejected — listing not yet permitted to advertise. Eric is on it; we'll send a follow-up within 24 hours."*

No detail about the rejection reason in the user-facing string (legal sensitivity); Eric gets the detail via Telegram.

### 3.11 Number formatting in prose

- Counts: bare numbers up to 999 (*"3 leads," "27 conversations"*). Thousand-separators above (*"1,247 buyers"*).
- Percentages: integer (*"30% paid"*), one decimal only when the decimal matters (*"0.15% commission"*).
- Time durations: most-significant unit first (*"30 days," "2 weeks," "6 months"*). Never "1 day(s)" — always handle singular/plural.

### 3.12 "We" vs "Dalya" vs "the system"

- Use **Dalya** when the AI is the actor (per §3.7).
- Use **Eric** when the named human is the actor.
- Use **Mahoroba Realty** when the legal entity is the actor (signing documents, accepting offers, regulatory compliance).
- Use **we** sparingly, only on signed-out marketing surfaces where "we" = the company.
- Banned: "the system," "the platform," "the tool," "the dashboard." These are circumlocutions.

### 3.13 Numeric uncertainty

When showing a calculated estimate, prefix or suffix to mark it estimated:
- *"~AED 25,880 estimated commission"*
- *"Roughly 4–6 weeks to close (NOC dependent)"*
- *"AED 690,138 DLD fee · final amount confirmed at trustees"*

Never present a calculated estimate as if it were measured. The user is making a financial decision.

### 3.14 Buyer name display

When the buyer's name is known (extracted from conversation), display it as `First Last` in full on the first reference within a surface, then `First` after. *"Sara Mohammed offered AED 17M. Sara is asking about NOC."*

When the buyer's name is unknown, display the phone number: *"+971 50 101 0001 sent an inquiry."* Not "Anonymous buyer," not "User," not "Unknown."

### 3.15 Offer descriptors

- **At asking**: *"At asking (AED 17,253,444)."*
- **Above asking**: *"AED X above asking."*
- **Below asking**: *"AED Y below asking."*
- **Above threshold but below asking**: *"AED Y below asking (above your alert threshold)."*
- **Below threshold**: NOT escalated, so this string doesn't appear in real-time. Surfaces only in offer history.

Never *"low-ball"*, *"strong"*, *"weak"*, *"premium"*. The numbers describe themselves.

---

## 4. What we never say — the ban list

Each entry: phrase, one-line reason for ban.

| Banned | Reason |
|---|---|
| "AI-powered" | Brags about a means, not an outcome. The agent doesn't care what powers it. |
| "Intelligent" / "Smart" | Same. Empty praise. |
| "Leverage" | Consultant-ese. Use "use." |
| "Synergy" / "Synergistic" | Banned in any form for any reason. |
| "Delight" / "Delightful" | Anti-trust signal in a regulator-grade tool. |
| "Magic" / "Magical" | Same. Trustworthiness is mechanical, not magical. |
| "Best-in-class" | Comparative without comparable. |
| "Cutting-edge" / "State-of-the-art" / "Next-generation" | Marketing-page filler. |
| "Luxury" / "Luxurious" / "Premium" | Phase 1 banned adjectives — these were the words Dalya is *leaving*. |
| "Opulent" / "Sophisticated" / "Bespoke" | Same family. |
| "Vibrant" / "Bold" / "Striking" | Loud descriptors don't match the brand attributes. |
| "Effortless" / "Easy" / "Simple" | The user decides what's easy. Don't assert. |
| "Just" (as in "just click here") | Diminishes the action. |
| "Simply" | Same. |
| "Powerful" | Empty. What does it do? |
| "Robust" | What does this even mean. |
| "Cutting-edge AI" | See above + see "AI-powered". |
| "Game-changing" / "Game changer" | Cliché. |
| "Revolutionize" / "Disrupt" | Cliché. |
| "Dubai's #1" / "Leading" / "Premier" | Self-superlative without basis. |
| "Welcome to Dalya" | Onboarding cliché. State what the user can do, not where they are. |
| "Oops!" / "Uh oh!" / "Something went wrong" | Infantilizing. Specifies nothing. |
| "Please" (in microcopy) | Begging. Buttons command; they don't request. |
| "Kindly" | British formality leaks across — banned in any form. |
| "Feel free to" | Permission-granting where none is needed. |
| "Don't hesitate to" | Same. |
| "Reach out" (instead of "contact" or specific verb) | LinkedIn-ese. |
| "Touch base" | LinkedIn-ese. |
| "Circle back" | LinkedIn-ese. |
| "Loop in" | LinkedIn-ese. |
| "Take this offline" | LinkedIn-ese. |
| "At this time" | Use "now" or omit. |
| "Going forward" | Use "from now on" or omit. |
| "Stay tuned" | Suggests there's nothing actionable. |
| "Coming soon" | If it isn't shipping, don't surface it. |

The banned list is enforceable via a linter — every PR can grep against it. Recommend implementing.

---

## 5. What we always say — the required list

Phrases that must appear where applicable.

| Required | Where | Reason |
|---|---|---|
| "RERA-licensed" | Marketing footer, signed-out trust strip, any regulatory-context surface | Legitimacy signal. Required by Mahoroba's market positioning. |
| "Mahoroba Realty" | Legal footer, terms-of-service, signed contracts | Mahoroba is the licensed entity. Dalya is the product brand. They must coexist. |
| "0.15% commission" | Any surface referencing commission. As a number, not a phrase. | "Low commission" is banned; the actual figure is the signal. |
| "Off-plan resale" | Product copy where transaction type matters | Local-market term. "Secondary market" / "pre-construction resale" are wrong-register. |
| "Trakheesi permit" | Permit-status surfaces | Local-market term. "Advertising license" is wrong-register. |
| "Trustees office" | Closing-mechanics copy | Local-market term. Per `BOT_RULES.md` §6. |
| "NOC" / "No-Objection Certificate" | NOC-status surfaces. First reference: full form + abbreviation. Subsequent: abbreviation. | Local-market term. |
| "Dalya" | Anywhere referring to the AI | Per §3.7. |
| "Eric" | When referring to the named human routing/handling | Per `BOT_RULES.md` Phase 9.1. First mention in any new conversation in chat surface includes "Eric, our Lead Broker at Dalya who handles all transactions." See `BOT_RULES.md` for the exact pattern. |

---

## 6. Voice across languages

Product chrome defaults to English (per Cultural Intelligence brief, §4 of `04-cultural-strategy.md`). When the chrome renders in another language, the register shifts as follows:

### 6.1 Arabic chrome

Translation, not transcreation. The same factual-brief-specific register applies. The Arabic typography pair handles the visual; the voice principles are identical.

Specifics:
- Buttons remain verb-first in Arabic where grammar permits (often `أَرسِل العَرض` for "Send offer" — imperative form).
- Honorifics are avoided. The product is functional infrastructure, not formal communication.
- The "Eric, our Lead Broker" introduction (per `BOT_RULES.md`) renders as direct equivalent: *"إيريك، مدير الوساطة لدى دليا الذي يتولى جميع المعاملات"* — no decorative phrasing.
- AED renders as *"درهم"* in body prose, *"AED"* in tables (matches the column header convention).

### 6.2 Russian and Hindi

Limited surface presence in chrome — primarily appears in the buyer-facing bot, not the agent product. When it does appear:
- Same factual-brief-specific register.
- No softening phrases that work in English but read sycophantic in Russian/Hindi.
- "Eric" stays in Latin script (it's a name, not a translation target).

### 6.3 Mixed-language users

The agent surface stays in the user's chosen chrome language. The conversation thread renders in the language of the buyer's actual messages (which may differ from the agent's chrome). This is per `BOT_RULES.md` Section 24.

---

## 7. The reconciliation problem — bot voice vs product voice as the same brand

The bot speaks one way (`BOT_RULES.md`). The product speaks another way (this document). They must read as the same brand, because:
- A buyer can screenshot a conversation and share it with a friend; the friend sees the bot's voice.
- An agent might share their working surface to a buyer (via screen-share, during onboarding); the buyer sees the product voice.
- A brokerage owner reviewing telemetry sees both.

The reconciliation rule: **both voices share the three principles (factual, brief, specific). They differ in register, not in posture.**

| | Bot voice (buyer-facing) | Product voice (agent-facing) |
|---|---|---|
| Audience | Buyer with a property decision | Agent or owner doing their job |
| Register | Conversational professional | Operational professional |
| Length | Multi-sentence as needed | Often single-phrase |
| Pronouns | "I" (Dalya) addressing "you" (buyer) | Mostly absent; chrome speaks in noun-only register |
| Emoji | Banned | Banned |
| Markdown | Banned (WhatsApp) | Banned where rendered (chat); allowed in admin tooling |
| Apology | Honest acknowledgment when wrong | Honest acknowledgment when wrong |
| Sign-off | None (per `BOT_RULES.md`) | None |

The reconciliation across surfaces is the *shared posture* — calm, regulator-aware, factually grounded, never apologetic-by-default, never hyperbolic. The register difference is appropriate (talking to a buyer is different from talking to an agent) and reads as the same person calibrating their tone, not two different brands.

---

## 8. Voice review checklist

Before any new product string ships:

1. Does it pass the three principles (factual / brief / specific)?
2. Is it in the right register for its surface (per §2)?
3. Does it use any banned phrase from §4? If yes, rewrite.
4. Does it require any phrase from §5? If yes, ensure presence.
5. If it references AED, time, or buyer names, does it use the conventions in §3.5 / §3.6 / §3.14?
6. If it names the AI, does it use "Dalya" (§3.7)?
7. If it's an error message, does it say what failed and what the user can do (§2.3)?
8. If it's an empty state, does it say what's not here and what next (§2.2)?
9. If it crosses surfaces (e.g. a notification that becomes an email), does each surface get its own version, or one-version-shared?
10. Read it aloud. Does it sound like a Dubai broker who is good at their job? Or does it sound like a SaaS marketing page?

If the answer to 10 is "marketing page," it ships only on the marketing site, not in the product.

---

## 9. Operationalizing this document

Three concrete pieces of infrastructure to build alongside Phase 3:

1. **A linter** that grep-scans all product strings against the §4 ban list. PR-blocking on match. Trivially cheap.
2. **A reviewer checklist** baked into PR templates: every PR that adds or changes a user-facing string must check §8.
3. **A localization brief** for any new language: the principles in §1 are global; the conventions in §3 are mostly global; the §4/§5 lists need localized equivalents.

These aren't deliverables of this document. They are the artifacts that keep this document operational past launch.

---

## Where this document ends

This is the agent-facing product voice. The buyer-facing chatbot voice lives in `BOT_RULES.md`. The brand strategic frame lives in `01-foundations.md`. Visual surfaces live in `05-surface-spacing.md` and `06-components.md`. Motion lives in `07-motion.md`.

Phase 3 (application examples) tests this voice against real screens. Expect adjustments after the first 5–8 routes are built and the voice meets real content.
