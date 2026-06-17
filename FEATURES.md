# Dalya — Features

*Last updated: 2026-06-09 (`GOAL_SPEC_0609` MVP completion roadmap applied)*

This document is split into two parts:

1. **[Dalya B2B Platform](#dalya-b2b-platform-current-focus)** — what we're building now. Six feature pillars for the B2B agent infrastructure product. Pillar 1 (buyer engagement) is mostly built — those features carried over from the consumer-direct work and are still valid. Pillars 2–6 are mostly net-new.
2. **[Mahoroba consumer-direct platform (legacy)](#mahoroba-consumer-direct-platform-legacy)** — what was built for the original 0.15% consumer-marketplace strategy. Retained for two reasons: most of the underlying engine (escalation logic, prompt rules, intent classification, voice validator) is platform infrastructure that survives the pivot; and the seller/buyer dashboards still serve Mahoroba's maintenance-mode operation. Mark anything in this section as *legacy* before reusing it in a B2B context.

---

# Dalya B2B Platform (current focus)

The product gives **individual agents** tools to handle buyer conversations, run viewings, follow up, and close deals more efficiently. Brokerage owner visibility and listing acquisition remain strategic future pillars, but they are no longer part of the launch MVP.

The customer is the brokerage. The user is the agent. The buyer is consumed via the bot, not as a customer of Dalya.

## Platform foundations (backend complete for MVP)

The four MVP blocks now have the backend foundation they need:

- ✅ Universal brokerage scoping on rows and read paths, with brokerage-wide listing access and private-by-default buyer conversations
- ✅ Auth and route enforcement tied to brokerage membership plus conversation-level grants/reassignment
- ✅ Compliance and audit logging for opt-outs, outbound sends, blocked sends, escalations, regulatory requests, conversation shares/reassignments, and brokerage-config changes
- ✅ Safe anonymized aggregation across brokerages through an explicit aggregate output contract with minimum sample sizes and identifier rejection
- ✅ Brokerage-specific configuration for prompt variables, managing-agent naming, fee framing, language defaults, dashboard URL, and handoff contacts

## MVP completion roadmap

Canonical roadmap: [`MVP_ROADMAP_0609.md`](./MVP_ROADMAP_0609.md).

| Priority | Linear | Feature | Status |
|---|---|---|---|
| 1 | DAL-149 | Dashboard reply composer | Built: API, `/agent/escalations`, `/agent/conversations/[id]`, timeline/compliance/thread resolution, consumed-route guard |
| 2 | DAL-150 | Draft approval queue | Built: `/agent/drafts`, edit/send/reject/snooze/view conversation, no auto-send |
| 3 | DAL-151 | Scheduled hot-list refresh | Built: persisted refresh runs, scheduled script, manual refresh API/UI, run status |
| 4 | DAL-152 | Ready property intelligence layer | Built: document ingestion, extracted facts, verification controls, buyer-safe summaries, prompt grounding |
| 5 | DAL-153 | Google Calendar integration | Built: OAuth URL/callback, token-ref settings, free/busy, viewing event create/update/delete, `/agent/calendar` |
| 6 | DAL-154 | Tenant WhatsApp confirmation flow | Built: tenant notice send, webhook reply handling, viewing state updates, agent notification |
| 7 | DAL-155 | Viewing logistics completion | Built: approved buyer/reminder/running-late/reschedule sends, completion API/job, compliance trail, post-viewing task/draft trigger |
| 8 | DAL-156 | Post-viewing capture | Built: due feedback requests, buyer reply capture, agent form, structured `viewing_feedback`, hot-list/task updates |
| 9 | DAL-157 | Agent performance dashboard | Built: current-agent today/7d/30d metrics on `/agent`, no owner rollups |
| 10 | DAL-143 | WhatsApp/BSP production verification | Report complete: Twilio path verified; 360dialog BSP blocked by explicit stub pending WABA approval/implementation |

Explicitly deferred from MVP: Mandarin production support, owner outreach/campaigns/listing acquisition automation, AI buyer matching launch surface, brokerage owner dashboard/owner rollups, and advanced Google Maps route optimization.

## Pillar 1 — Buyer engagement / Inquiry Concierge (mostly built)

Most of this pillar's logic exists in `app/core/chatbot_engine.py`, `app/core/prompt_builder.py`, `app/core/intent_classifier.py`, and `app/core/response_validator.py`. It was originally built for Mahoroba's listings; the engine is brokerage-agnostic and ports cleanly to Luqman's listings once multi-tenant scoping is in place.

- ✅ 24/7 multilingual inquiry concierge (EN/AR/RU/HI; Mandarin deferred) grounded in actual document data
- ✅ Above-threshold offer escalation with deterministic acknowledgment template (Phase 8.1)
- ✅ Three-message engagement gate to suppress spam/probe escalations (Phase 5.1 + 8.3)
- ✅ Conveyancing privacy unification: lawyers asking about a buyer's offer never get confirmation of existence (Phase 8.7)
- ✅ Form A / RERA / Trakheesi co-broker compliance escalation (Phase 8.6)
- ✅ BRN-only requests routed to a distinct escalation type (Phase 9.6)
- ✅ Soft-offer detection — buyer floated an amount then paused, captured as warm lead (Phase 8.5)
- ✅ Returning-buyer detection — surfaces prior offers on T1/T2 (Phase 9.10)
- ✅ Promise → escalation invariant — if the bot says "I've forwarded to Eric," an escalation actually fires (Phase 8.10)
- ✅ Managing-agent introduction on first mention (Phase 9.1 generalized) — uses each brokerage's configured handoff contact/title instead of a hardcoded Eric equivalent
- ✅ SPA price arithmetic protection — never disclose seller's purchase price (Phase 8.2)
- ✅ DLD trustees-office closing mechanics in prompt (Phase 8.4)
- ✅ Universal response validator: em-dash replacement, deferral-phrase rewrite, reflexive-closer stripping, markdown-bold stripping, emoji stripping (Phase 7.5)
- ✅ Multilingual intent classifier with `is_firm_offer` discrimination, currency normalization, hypothetical filtering (Phase 7.1)
- ✅ **Net new for B2B:** multi-tenant scoping — each brokerage's conversations, listings, offers, prompts, opt-outs, and handoff config live in their own namespace; cross-brokerage data accumulation uses aggregated anonymized signal only
- ✅ **Net new for B2B:** voice-note transcription foundation with action/price extraction, confidence metadata, and low-confidence amount confirmation
- ✅ **Net new for B2B:** buyer preference and same-brokerage matching scaffolding exists
- ✅ **Priority 4:** ready-property document intelligence — upload title deed/Oqood/Ejari/service charge/NOC/valuation/mortgage/floor plan/snagging/DEWA/rules/disclosure documents, extract structured facts, let agents verify, and ground ready-property buyer answers in the knowledge layer
- 🔲 **Deferred:** AI buyer matching launch surface

## Smart Escalation to Agents

- ✅ Escalation alerts route through each brokerage's Agents AI number to the listing's managing agent
- ✅ Agent reply relay: agent replies with the `[Ref: TOKEN]` envelope in the Agents AI thread and Dalya relays the cleaned reply to the buyer through the brokerage's buyer-facing number
- ✅ Reply validation: token, brokerage, agent phone, route expiry, buyer opt-out, listing, and conversation destination are checked before relay
- ✅ Timeline + audit persistence: relayed replies become `agent_relay` conversation messages, lead actions, and compliance events; blocked attempts are also logged
- ✅ Webapp escalation inbox: `/agent/escalations` lists brokerage-scoped threads with filters, ordered questions, urgency/category/state badges, route metadata, and manual resolve
- ✅ **Priority 1:** Dashboard reply composition controls for agents who prefer dashboard-based handoff instead of WhatsApp replies

## Pillar 2 — Viewing and inspection workflow (new build, ready-stock focus)

Ready buyers view; off-plan buyers usually don't. Viewing logistics is the largest workflow improvement for ready-stock agents.

- ✅ Phase 1A backend/provider-ready foundation: per-listing logistics records, building-level prefill, contributor confidence, tenant PII redaction, tenant consent/audit, agent availability blocks, calendar provider settings, deterministic slot proposals, viewing confirmation, and pre-viewing brief API
- ✅ Dynamic buffer fallback: slot proposals use prep floor, community-pair travel fallback, and rush-hour multiplier while live Google Maps credentials/billing are pending
- ✅ PDPL-safe tenant handling: tenant lawful basis, opt-in state, retention date, and audit trail exist before tenant notification automation is added
- ✅ Webapp logistics surfaces: `/dashboard/listings/[id]/logistics` for Access / Keys / Tenant / Owner tabs, `/agent/viewings` for viewing calendar/list, and `/agent/viewings/[id]` for viewing detail, draft notifications, logistics summary, and brief display
- ✅ Draft-and-approve viewing notifications: buyer T-24h confirmation, T-1h reminder, tenant notice, running-late, and reschedule drafts are generated and stored without auto-sending
- ✅ Ready-property knowledge surface: `/dashboard/listings/[id]/knowledge` lets agents process ready-property document text, review extracted facts, mark facts verified/buyer-safe/internal/risk-flagged, and see missing/risk signals
- ✅ **Priority 5:** Live Google Calendar integration: OAuth, free/busy read, selected calendars, Dalya viewing write-back/update/cancel
- 🔲 Basic Google Maps travel buffer: Distance Matrix `duration_in_traffic`; advanced route optimization deferred
- ✅ **Priority 6:** Tenant WhatsApp confirmation flow: approved tenant notice send, confirm/reschedule/decline/free-text reply handling, tenant confirmation/reschedule state, agent notification
- ✅ **Priority 7:** Viewing logistics completion: buyer confirmation, reminders, tenant lifecycle, calendar invite write-back, viewing status lifecycle, completion trigger
- ✅ **Priority 8:** Post-viewing capture: buyer feedback and agent buyer-rating prompt 4 hours after viewing, structured storage, hot-list update
- 🔲 Live unit intelligence capture: agent walks a unit and dictates notes; system structures them into a queryable per-unit profile (AC notes, paintwork, view direction, neighbor signals, etc.) that augments document-extracted data
- 🔲 Multilingual real-time viewing translation: agent and buyer in different languages during a physical viewing, system translates inline

## Pillar 3 — Listing acquisition and seller engagement (deferred)

The hardest problem in Dubai brokerage. It remains strategically important, but `GOAL_SPEC_0609` defers owner outreach, owner CSV upload, campaign builder, listing-acquisition automation, and AI property one-pager generation until after the launch MVP.

- 🔲 Deferred: owner identification and prioritization
- 🔲 Deferred: hyper-personalized owner outreach drafts
- 🔲 Deferred: just-listed/just-sold neighbor outreach
- 🔲 Deferred: owner-specific market intelligence reports
- 🔲 Deferred: newsletter generation per community/developer
- 🔲 Deferred: listing renewal intelligence
- 🔲 Deferred: pricing conversation support
- 🔲 Deferred: owner sentiment and engagement tracking
- 🔲 Deferred: off-market listing aggregation
- 🔲 Deferred: seller-facing landing page generator

**Regulatory constraint (mandatory from day one of this pillar):** consent management, opt-out enforcement, rate limits, and WhatsApp Business template compliance. UAE PDPL + federal anti-spam law apply. Cross-agent opt-out propagation within a brokerage is required. *"The only listing acquisition tool built to UAE PDPL standards"* is positioned as a differentiator, not a constraint.

## Pillar 4 — Daily agent workflow

- ✅ Hot list / who-to-call-today: deterministic backend ranking by offer state, viewing intent, financing/budget signal, engagement depth, recency, and stale-buyer state
- ✅ Automated follow-up nudges: stale buyers get one deduped open task plus one review-only WhatsApp draft
- ✅ Dashboard integration: `/api/v1/agent/dashboard` refreshes and returns real `lead_assignments`, `lead_tasks`, `draft_replies`, escalation threads, and a live conversation inbox while preserving conversation-level visibility
- ✅ Persistent full-flow demo workspace: `scripts/chatbot_full_test.py --persist-agent-workspace` seeds all canonical harness listings under Eric at Mahoroba, preserves conversations/offers/escalations/hot-list rows for `/agent` review, and writes a workspace snapshot artifact
- ✅ **Priority 2:** Draft approval queue at `/agent/drafts`
- ✅ **Priority 3:** Scheduled morning hot-list refresh with stored run status and manual refresh
- ✅ **Priority 9:** Personal agent performance dashboard for today/7d/30d, no owner rollups
- 🔲 One-tap conversation takeover: agent enters live bot conversation with full prior context preserved
- 🔲 Draft-and-send mode: AI drafts replies for agent approval when the agent is actively engaged in a conversation

## Pillar 5 — Negotiation and closing support

- ✅ OfferRecord persistence and revision chains across conversations (Phase 5+)
- ✅ Multi-offer alert consolidation: same buyer + same listing within 24h shows full revision chain in the alert (Phase 5.1)
- 🔲 Comparable lookup on demand: real-time comparables surfaced when an offer comes in
- 🔲 Negotiation support with full context: offer + comparables + seller flexibility signals + suggested counters
- 🔲 Reuse Phase 8.4 trustees-office closing-mechanics framing for ready-property closings (similar mechanics, fewer NOC dependencies)

## Pillar 6 — Seller-side workflow

- 🔲 Automated weekly seller updates: Friday one-page reports, agent reviews and sends with one tap

## MVP feature set

1. 24/7 Inquiry Concierge
2. Smart Escalation to Agents
3. Morning Hot List + Follow-Up Engine
4. Viewing Logistics Automation + Pre-Viewing Report

The launch acceptance criteria are the 15-point definition of done in [`MVP_ROADMAP_0609.md`](./MVP_ROADMAP_0609.md). Resist building broad. The ten completion priorities are the MVP.

## Two-product surface model

| Surface | User | Primary device | Daily session length |
|---|---|---|---|
| Brokerage owner dashboard | Owner (Luqman) | Desktop | 2–4 hours sustained |
| Individual agent surface | Agents | Mobile-first, WhatsApp-adjacent | Quick interactions throughout the day |

Shared data layer. One platform. For MVP, build only the individual agent surface plus personal agent metrics; owner dashboard and owner rollups are deferred.

## Document layer expansion (B2B-required)

Off-plan resale was the original scope. B2B requires expanding to ready-property resale and tenanted resale. New document types the system must learn to parse and ground prompts in:

- ✅ SPA (off-plan) — current parser
- ✅ MVP document knowledge layer supports title deed (ready property — replaces SPA at handover)
- ✅ Oqood (pre-handover title record where applicable)
- ✅ Ejari (tenancy contract for rented units; ~30–40% of Dubai ready resale)
- ✅ Service charge statements
- ✅ NOC from developer for resale
- ✅ Valuation reports
- ✅ Mortgage liability letters
- ✅ Floor plans
- ✅ Snagging reports
- ✅ DEWA / utility info
- ✅ Building/community rules
- ✅ Seller disclosure notes

---

# Mahoroba consumer-direct platform (legacy)

The features below were built for the original consumer-direct brokerage strategy (sellers list directly with Dalya at 0.15% commission; buyers find listings on Property Finder/Bayut and chat with Dalya). That strategy is retired. Mahoroba Realty continues in maintenance mode using these surfaces; the underlying engine (escalation logic, prompt rules, intent classification, voice validator) is platform infrastructure that survives the pivot and is referenced in the B2B section above with cross-links.

When reading the section below, mentally tag everything as *legacy product surface* unless explicitly marked as platform-engine-shared.

## Core Platform

### Infrastructure
- **Twilio WhatsApp setup** — Sandbox connected, webhook live
- **PostgreSQL persistence** — Supabase + Neon via SQLAlchemy; tables: `listings`, `conversations`, `messages`, `buyer_profiles`, `listing_inquiries`, `message_queue`, `telegram_reply_routes`, `offer_records`, `suspicious_activity`
- **Conversation history persistence** — Survives server restarts
- **Rate limiting** — 10 msgs / 60 seconds per phone number
- **Twilio signature validation** — Live on webhook with PUBLIC_URL handling
- **Structured logging** — Python logging with conversation_id; structured `escalation_decision`, `engagement_gate_suppressed`, `bypass_attempt`, `response_validator`, `response_sanitized` events
- **Health check endpoint** — `GET /health` returns API key, DB, Twilio, Telegram, listing count
- **Neon DB connection stability** — `pool_recycle=300`, TCP keepalives to prevent sleep disconnects
- **API cost optimization** — Multilingual Haiku-based intent classifier (~$0.0008/turn) + system prompt caching (~85% input cost reduction); rule-based intent fallback when classifier API fails

### Auth & Users
- **Seller portal** — Full web UI: login (Google OAuth + email/password), dashboard, edit listing details, auth-protected SPA upload
- **Supabase Auth** — ES256 JWT verification via JWKS endpoint
- **Admin-only CRM access** — `ADMIN_USER_ID` env check in proxy.ts, protected `/admin/*` routes

---

## Chatbot Intelligence

### Core Behavior
- **Buyer name capture** — Asks naturally within first 2-3 exchanges; classifier extracts `extracted_buyer_name` per turn
- **Buyer profiles** — Tracks budget, bedroom/area preferences, purpose, inquired properties across conversations
- **Viewing request handling** — Off-plan viewings declined gracefully, renders offered instead
- **Message debounce queue** — 5s rolling window; multi-message bursts processed as one input
- **Asking price override** — Seller asking price used over SPA price
- **AI identity** — Presents as Dalya; discloses AI nature only when directly asked, no sales pitch after
- **Cross-language identity disclosure** — First response in any language must include Dalya + Mahoroba; canonical Arabic phrasing "أنا دليا، مساعدة العقارات من شركة مهروبة العقارية"
- **Multi-language** — Fluent Arabic, Russian, and Hindi responses for MVP; Mandarin remains deferred. The classifier ignores foreign-language greetings ("Salam", "Bonjour", "Ni hao") when detecting conversation language so an English message that opens with "Salam, what's the price?" gets an English response (Phase 7.6.2)
- **Conversation style** — Direct, no affirmation openers, no repeated stats, max 3-4 sentences, no markdown formatting (rule + post-generation validator)
- **Off-topic handling** — Brief honest answer, no sales pivot
- **Brand voice rules** — No emojis, no markdown bold (`**`), no markdown headers, no bullet lists with bold items; enforced in prompt + post-generation validator strips em-dashes, deferral phrases, reflexive closing questions, markdown bold, and emojis. Validator runs as the SINGLE entry point on every response path (buyer / seller / regulatory / no-listing / professional / conveyancing) — Phase 7.5
- **Date-driven `paid_to_date`** — Computed at runtime from payment_schedule + per-instalment `actually_paid` override + as-of date; no stale snapshots in prompt
- **First-turn identity carve-out for transactional demands** — Identity-disclosure rule relaxed when buyer's opening message is a price+demand-verb without greeting (spam-offer pattern); bot may anchor against the offer first

### Escalation Logic
- **Multilingual offer/intent classifier** — Haiku-based JSON-structured classifier covering EN/AR/Hinglish/broken-English/Russian; currency normalization (USD/GBP/EUR/INR/AED, lakh/crore, Arabic-Indic numerals); `is_firm_offer` discrimination (declarative offer vs hypothetical / counter-asking question)
- **Smart threshold gating** — Offers escalate when `>=` `negotiation_threshold_aed` regardless of intent label (Phase 7.1: works from `professional_inquiry` / co-broker context, not just `offer_submission`); gated by `is_firm_offer` flag to filter hypotheticals
- **Marginal offer buffer** — Offers within 2% below threshold escalate as `is_marginal=true` with `marginal_gap_aed` and `marginal_gap_pct` so Eric sees the under-threshold caveat. Buyer-facing response identical to non-marginal escalations (no leak of threshold or buffer logic) — Phase 7.2
- **Escalation re-trigger guard** — Re-escalates if new offer is higher than previous or 24h+ passed
- **Three-message engagement gate** — Buyers must send 3+ buyer messages before any escalation fires; below the gate, OfferRecord is still stored (data moat) but no Telegram alert. Exemptions: seller messages, regulatory requests, verified-lawyer escalations
- **Multi-offer alert consolidation** — Same buyer + same listing within 24h: each subsequent above-threshold offer prefixes its conversation summary with `[REVISED OFFER] AED X → Y → Z` so the seller sees full chain in the alert
- **Below-threshold offer storage** — Every detected offer creates a `DBOfferRecord` regardless of threshold; supersede chains via `superseded_by` foreign key
- **Follow-up suppression** — Suppresses outbound if last two messages are both from assistant
- **Grouped forwarded questions** — Unanswerable questions accumulate, one grouped Telegram alert, list clears
- **Speak-to-human detection** — Explicit escalation trigger for "can I talk to a real person?"
- **Below-threshold offer handling** — Bot pushes back firmly with varied phrasing without disclosing the asking-price gap or promising to "pass it along" (Phase 7.3 prompt rules); engine separately decides escalation, decoupled from bot wording
- **Foreign currency offers** — Auto-converts USD/EUR/INR (lakhs/crore) to AED, asks for confirmation
- **`bypass_attempt` intent** — Manipulation patterns (request seller's direct contact, demand documents to bypass broker, claim peer-broker status to extract seller info) silently logged to `DBSuspiciousActivity` table — no Telegram alert, eliminates noise from social engineering
- **`regulatory_request` intent** — PDPL/GDPR/right-to-erasure/subject-access patterns route to high-priority escalation with `regulatory_category` (`pdpl_deletion`, `gdpr`, `data_access`, `general_data_protection`); response template acknowledges within 30-day window, never makes false data-storage claims
- **`legitimate_conveyancing` intent** — Lawyer self-id + named buyer with matching active OfferRecord → high-priority escalation with offer_id reference. Buyer-name lookup uses rapidfuzz (threshold 80) to handle variations. Bot does NOT disclose offer amount to lawyer (they should know from their client). Unverified lawyer claims log to suspicious_activity, polite refusal
- **`professional_inquiry` intent** — Mortgage brokers, financial advisors, conveyancers without verified buyers, family offices, valuers route to peer-to-peer handler with public unit facts; declines PII / docs / corporate-structure advice; no commission pitch, no buyer-mode qualifying questions
- **Grounded conversation summary** — Escalation alert summary built with explicit `asking_price_aed` + `offer_amount_aed` ground-truth params; post-generation regex validator scans for any AED figure not in the allowed set; on rogue figure, falls back to deterministic template (no fluent-but-wrong text reaches the seller)
- **KB-only premium citation rule** — Bot may only cite numerical figures (resale premiums, capital appreciation %, yield projections) explicitly present in the loaded community KB or seller-supplied data; attribution required ("per Emaar's market data")

### Telegram Bridge
- **Telegram escalation alerts** — Fires on qualifying offers + unanswerable questions + seller actions (high-priority) + regulatory requests + legitimate_conveyancing
- **Telegram reply bridge** — Eric replies on Telegram → forwards to buyer on WhatsApp → confirmation
- **Seller Q&A memory** — Eric's Telegram replies saved as Q&A on the listing; future buyers get the answer directly
- **Priority field on EscalationAlert** — `low | normal | high` so Telegram client / future routing can prioritize visibility (regulatory + seller-action + legitimate_conveyancing fire `high`)

### Negotiation
- **Negotiation threshold** — Per-listing minimum offer threshold to alert seller
- **Asking price validation** — Minimum offer to alert must be less than asking price
- **0.15% flat fee lock** — Fee is hardcoded 0.15% in seller-mode prompt, no per-listing override, no representation-based variance, no co-broke pool. Bot quotes "AED savings vs 2% market" deterministically. Net-proceeds calc: `net = asking - (asking × 0.0015)`

### Cross-listing
- **Cross-listing recommendations** — All active listings always included in system prompt; bot recommends on explicit asks ("other properties?") or implicit signals ("too expensive", "too small")
- **Semantic portfolio matching (no-listing fallback)** — When `inbound.listing_id` is empty, the bot pulls active listings from the DB at request time with structured attributes (developer, type, bedrooms, location_descriptor, tags) and matches buyer descriptions semantically. "Villa in some Emaar community" → surfaces Palace Villas Ostra. "Anything in Dubai Marina" → honest "no Marina listing, but Seahaven is the next waterfront community over." `general_lead_capture` escalation fires when buyer reveals criteria

### Seller-Mode Authentication
- **Phone-match seller auth** — `inbound.from_number` normalized + matched against `listing.seller_phone`; verified senders enter seller-mode
- **Seller intent classifier** — Keyword-based router across `offer_acceptance`, `counter_offer`, `listing_status_change`, `advisory_question`, `price_update`, `threshold_update`, `listing_edit`, `performance_metrics`, `general_seller_question`
- **Material seller actions escalate** — Offer acceptance, counter-offers, listing status changes, advisory questions ("should I drop the price?") fire `seller_action` high-priority escalation; bot acknowledges and tells the seller Eric will be in touch shortly
- **Routine seller actions → dashboard** — Price updates, threshold updates, listing edits routed to `dalya.ai/dashboard` (no autonomous DB writes from chat)
- **Performance metrics with PII protection** — Aggregate-only response: inquiry count, offer count, highest offer received. Buyer names, phone numbers, contact details NEVER disclosed even to authenticated seller
- **Seller-mode brand voice** — Same no-markdown / no-bullets / no-affirmation-opener rules as buyer-mode; conversation history passed to Claude so repeated-metric responses vary phrasing instead of emitting verbatim duplicates

### Response Validator (Post-Generation)
- **Em-dash replacement** — Strips em-dashes (`—`) and replaces with periods (next word capitalized) or commas (lowercase) based on context
- **Deferral phrase replacement** — Catches deflective deferral patterns (`let me check with the team`, `I've passed it to the team`, `the team will follow up`) and replaces with rotating pool of honest alternatives. Referential mentions (`our compliance team`, `Eric and the team`, `our broker`) correctly pass through
- **Intent-aware closing-question stripping** — Strips reflexive closing questions ("Anything else I can help with?") when intent is in the no-follow-up set (offer_submission, viewing_request, payment_plan_query, speak_to_human, contact_sharing, price_negotiation). Preserves the question for general_enquiry / contact_sharing where information is needed
- **Telemetry** — Each invocation logs `em_dashes_replaced`, `deferral_phrases_replaced`, `closing_questions_stripped` counts for quality metrics

---

## Listings

### SPA Parser
- **SPA upload** — PDF, JPEG, PNG supported
- **Text extraction first** — PyMuPDF text extraction (no API call), falls back to image for scanned docs
- **Image page cap** — Max 8 pages for image-based extraction
- **Bedrooms/bathrooms auto-lookup** — If not in SPA, Haiku-based web lookup based on project + BUA sqft
- **Parse confidence scoring** — 0-1 score flagged if below 0.7
- **Duplicate detection** — Same SPA uploaded twice returns existing listing (stable deterministic ID)
- **PII excluded** — Never extracts passport, Emirates ID, phone, email from SPAs
- **Parse progress bar** — Staged frontend progress with 5 stages + ease-out animation
- **`validate_spa_parse` warnings** — Post-parse validation flags suspiciously round BUA / plot (likely parser rounding or hand-crafted fixture), out-of-plausible-range purchase prices, payment_schedule percentages not summing to 100%, missing bedrooms on Villa/Apartment/Townhouse property types. Logged at WARNING level
- **Per-instalment `actually_paid` schema** — `PaymentInstalment` schema accepts `actually_paid: Optional[bool]` (true=confirmed paid, false=not paid, None=infer from due_date) and `paid_date: Optional[date]`; backwards-compatible with existing parsed data

### Listing Management
- **Seller self-serve upload** — 4-step flow: upload → verify → details → submitted
- **Listing portal link generator** — `/api/v1/listings/{id}/portal-links` for Property Finder / Bayut deep links
- **Developer renders/floor plans** — Media URLs stored per listing; bot sends actual images via WhatsApp Media API
- **Listing settings edit** — Asking price, threshold, seller notes editable from listing detail page
- **Listing status pipeline** — Processing stages tracked: SPA Verified → Listing Review → Trakheesi → Portal Listings → AI Advisor Live
- **Community data auto-attach** — Known projects get curated community data (schools, amenities, ROI, etc.)

---

## Seller Dashboard

### Navigation
- **Sidebar navigation** — Persistent sidebar with My Listings, Upload SPA, Activity, Settings
- **Separated marketing vs app** — Marketing site and seller app have different layouts; login page standalone
- **Mobile hamburger menu** — Responsive sidebar collapse

### My Listings
- **Listing cards** — Status pills (Live, Pending Review, Sold, Draft), asking price, lead count, escalated count, last activity
- **Stats bar** — Total listings, conversations, escalated leads

### Upload SPA
- **URL-based wizard state** — Back/forward navigation preserves draft via sessionStorage + URL params
- **4-step flow** — Upload → Verify parsed data → Listing details → Submitted confirmation
- **Contact method selector** — WhatsApp or Email with validation
- **Phone number auto-populate** — From user_metadata; saved back to profile on submit

### Listing Detail
- **Overview tab** — Stats, SPA summary, processing status pipeline, editable listing settings
- **Offers tab** — Anonymized offers with amount, vs asking %, status
- **SPA Data tab** — Full parsed SPA with all extracted fields
- **Nested layout with tabs** — Overview / Offers / SPA Data

### Activity Feed
- **Cross-listing activity** — Real events (inquiry, offer, escalation, milestone)
- **Filter chips** — All / Conversations / Offers / Status Changes
- **Click through to listing** — Each event links to the listing detail

### Settings
- **Account** — Editable display name + phone (persists to Supabase user_metadata)
- **Notifications** — UI toggles (not yet wired to backend)
- **Danger zone** — Sign out of all sessions, delete account

---

## Admin CRM

### Buyer Tracking
- **Lead stages** — new → engaged → qualified → offer → negotiation → closed_won/lost
- **Auto-stage advancement** — Rule-based transitions: 3+ messages = engaged; budget/prefs detected = qualified; offer submitted = offer
- **Lead source tracking** — Portal links vs direct WhatsApp
- **Manual stages** — negotiation / closed_won / closed_lost set from admin UI

### CRM Views (admin-only)
- **Buyer list** — Searchable, filterable, sortable; stage pills; budget, bedrooms, listings count
- **Buyer detail** — Full profile, editable stage/tags, timestamped notes, conversation list, inquiries history
- **Transcript viewer** — WhatsApp-style chat view with intent badges, escalation highlights

### AI Summarization
- **Structured summaries** — Haiku-generated JSON: topics, interest_level, sentiment, key_question, buyer_context, next_step_hint
- **Inactivity-triggered** — Summary worker runs every 5 min; summarizes conversations inactive 30+ min
- **Incremental summarization** — Uses previous summary + new messages only
- **Batched by listing** — Multiple conversations per API call with prompt caching
- **Tiered strategy** — Skips low-signal runs (< 2 new messages)

### Offer History (Data Moat)
- **`DBOfferRecord` table** — Every detected offer stored with `listing_id`, `conversation_id`, `buyer_phone`, `buyer_name`, `offer_amount_aed`, `asking_price_aed`, `gap_pct`, `above_threshold`, `escalated`, `escalation_reason`, `superseded_by`, `raw_message`, `language_detected`, `turn_number`, `created_at`
- **Supersede chains** — When same buyer + same listing submits a new offer, prior is marked `superseded_by=<new_offer_id>`. Active offer = `superseded_by IS NULL`
- **Below-threshold preservation** — Suppressed (engagement-gated or below-threshold) offers still stored — captures market-clearing-price intelligence and tire-kicker patterns

### Suspicious Activity Log
- **`DBSuspiciousActivity` table** — Logs `bypass_attempt` and `unverified_lawyer` interactions silently. Categories: `bypass_attempt` (manipulation/PII fishing), `unverified_lawyer` (legal claim without matching offer). Includes `trigger_message`, `bot_response`, `created_at`, `reviewed_at`, `reviewed_by` for admin review

---

## Phase 7 — Production Hardening (2026-05-08)

### Validator scope expansion (Phase 7.5)
- `validate_and_rewrite_response` is the SINGLE post-generation cleaner for ALL response paths: buyer, seller, regulatory, no-listing fallback, professional inquiry, legitimate conveyancing (verified + unverified), and seller-mode performance metrics
- Markdown bold (`**...**`) and emoji stripping added to existing rules (em-dash, deferral phrase, reflexive closing question)
- Closing-question patterns expanded for Phase 7.4: "does that make sense?", "what's your thinking?", "are you looking to invest or end-use?", "shall I walk you through?", and similar reflexive closes are stripped when intent is not in `QUESTION_JUSTIFIED_INTENTS` (offer_submission / contact_sharing / viewing_request / payment_plan_query)

### Closing-question prompt rules (Phase 7.4)
- New `CLOSING QUESTIONS — STRICT RULES` section in `prompt_builder.py` with explicit ONLY/NEVER conditions and examples (factual answer + reflexive close → strip; decline + pivot question → strip; intent that needs info → keep)

### Above-threshold + marginal escalation (Phase 7.1, 7.2)
- Offer detection runs across all intents; engine gates on `is_firm_offer` to filter hypotheticals from professional/co-broker contexts
- `EscalationAlert` carries `is_marginal: bool`, `marginal_gap_aed: float`, `marginal_gap_pct: float` so Eric's alert shows under-threshold buffer details
- Decision-reason logging covers `escalated_marginal_first_offer`, `escalated_marginal_higher_offer`, `escalated_marginal_after_24h`

### Seller-mode dashboard routing (Phase 7.7)
- `_compute_activity_signal(listing_id)` returns ONE qualitative descriptor (e.g., "active buyer interest with offers in play", "early days yet", "limited recent activity"). No specific numbers, ever.
- Seller-mode `performance_metrics` branch redirects to `dalya.ai/dashboard` with the activity signal + privacy reasoning (first time only); subsequent metric questions get signal + URL only
- Seller system prompt encodes the hard rule: never surface inquiry counts, offer counts, "highest offer", days-on-market, or buyer descriptors in chat — direct to dashboard

### Lawyer classifier hardening (Phase 7.6.4)
- Classifier prompt extended with explicit negative examples: "verify with my lawyer", "my lawyer needs the SPA", "send me the SPA so my advisor can review" → classify by buyer's actual intent (typically `bypass_attempt`), NOT `legitimate_conveyancing`
- Verified-conveyancing branch in `chatbot_engine` now rephrases via proactive forwarding: "Confirmed on the offer reference. I've forwarded this to Eric and he'll reach out directly..." (no longer claims "I have an active offer on file" if no DB match — asks for offer details instead)

### Off-plan resale framing (Phase 7.6.6, 7.6.8)
- Prompt explains TWO payment streams: seller equity (paid to seller at trustees-office close) vs developer balance (assumed by buyer via SPA novation). No more conflation of "50% paid" with "remaining buyer commitment"
- Closing mechanics: title transfer happens at trustees office BEFORE physical handover, not at handover

### Fee structure separation (Phase 7.6.1d, 7.6.7d)
- Prompt strictly separates Mahoroba's 0.15% brokerage fee from DLD's 4% transfer fee: "These are SEPARATE charges. The 0.15% is OUR fee. The 4% is the GOVERNMENT registration fee."
- 0.15% flat documented as applying regardless of representation (buyer-only / seller-only / both); structural buyer-savings advantage of 1.85% vs market 2% rate

### Forwarding language pattern (Phase 7.6.8b)
- Bot phrases all escalation-bound responses as PROACTIVE forwarding ("I've forwarded your inquiry, Eric will reach out") — never as buyer-action prompts ("speak with Eric directly", "you'll want to email Eric")

### Privacy framing for offer-history probes (Phase 7.6.7b)
- Buyer probing about other buyers' offers, seller's "flexibility", "highest offer received" → frame decline as discretion ("I don't share offer history for privacy reasons") — never as a knowledge gap ("I don't have visibility")

### Payment-method routing (Phase 7.6.6c)
- Cash / bank transfer / manager's cheque / escrow / mortgage questions → "Payment specifics get worked out after the offer stage. Submit an offer first, Eric will follow up to discuss the structure."

### Co-broker compliance escalation (Phase 7.6.5b)
- `_detect_co_broker_compliance` regex check fires `general_lead_capture` escalation with `seller_intent="co_broker_compliance"` for Form A / RERA / listing authorization / Trakheesi / BRN verification requests in `_handle_professional_inquiry`

### New-listing-inquiry escalation (Phase 7.6.7c)
- `_detect_new_listing_inquiry` regex check fires `general_lead_capture` escalation with `seller_intent="new_listing_inquiry"` when buyer-mode messages signal seller-acquisition intent ("if I list with Mahoroba", "thinking of selling my unit", "how does your fee work for sellers")

### PDPL state isolation (Phase 7.6.11)
- Conversation-history filter strips prior `regulatory_request` user turns + the immediately following bot response from the buyer-mode prompt context, so PDPL state can't bleed into ordinary chat
- New prompt rule: NEVER mention PDPL / data deletion / compliance hold unless the engine has explicitly invoked the regulatory handler for the current message

### Trigger-message deduplication (Phase 7.8)
- Single pending unanswerable question no longer carries a stray "1." prefix; numbered formatting only applies when 2+ are queued

---

## Phase 8 — Pilot Hardening (2026-05-08)

### Above-threshold response language branch (Phase 8.1)
- Engine refactored: above-threshold and marginal offers SKIP the Claude call entirely and use deterministic acknowledgment templates (`_above_threshold_template`, `_above_threshold_pre_engagement_template`)
- Templates exist in EN + AR with random selection per turn; contact-capture appendix when buyer name not yet known
- Pre-engagement variant when offer is above-threshold but the substantive engagement gate hasn't passed
- Eliminates the Phase 7 regression where Sara T9 (above-threshold 17M) got a "still a bit short" pushback that contradicted the firing escalation

### SPA price arithmetic protection (Phase 8.2, PRIVACY)
- New prompt rule: NEVER simultaneously disclose any TWO of {paid_amount_aed, paid_percentage, remaining_amount_aed, seller_equity_aed} — together they back-calculate the seller's original purchase price
- "What's left to pay?" now answers with REMAINING ONLY (no "paid to date" alongside)
- Adversarial "what did the seller actually pay?" → declines + recommends independent market analyst
- Examples in prompt cover Sara T4 (was leaking 4.55M paid + 10.62M remaining → 15.17M ≈ SPA) and Persona 9 T10 (adversarial)

### Substantive-engagement gate (Phase 8.3)
- `_engagement_gate_pass` now counts SUBSTANTIVE buyer messages, not raw count
- `_is_substantive_message` filters: pure offer demands ("5M cash today"), short messages with amounts (≤ 4 words), demand-verb + amount under 12 words
- FastCash with 3 pure-demand turns now gets `engagement_gate_below_threshold_0_substantive_of_3` — no auto-escalation
- Test orchestrator clears test-phone state (conversations / messages / offer records / suspicious activity / buyer profiles / inquiries) before each run, eliminating cross-run hallucination ("you offered 6M earlier" from prior runs)

### DLD/trustees-office closing mechanics (Phase 8.4)
- Reinforced prompt section with explicit examples ("Can we close in 30 days?" → "Yes, that's realistic. Once NOC is issued by [developer], the trustees office registers the title transfer well before physical handover.")
- Hard rule documented: title transfer happens at trustees office, NOT at handover
- David Chen 30-day-close case unblocks correctly

### Soft-offer escalation (Phase 8.5, NEW)
- New `escalation_type="soft_offer"` in EscalationAlert literal
- `_detect_soft_offer_pause(conv, current_message)` looks back 5 buyer messages for hypothetical phrasing + amount; if current message has pause-signal language ("discuss with", "come back", "inshallah", etc.), fires the escalation
- Captures warm leads: Mohammed T9 (floats 17.5M hypothetically) + T10 ("inshallah I'll discuss with my wife") → soft_offer with `seller_intent="soft_offer_above_asking"`

### Form A / co-broker compliance escalation (Phase 8.6)
- `_detect_co_broker_compliance` regex now runs in `handle_message` regardless of intent classification (was only in `_handle_professional_inquiry` which got bypassed for Sarah Patel T6 due to bypass_attempt routing)
- Templated response with proactive forwarding: "I've forwarded your request to Eric. He'll reach out directly to send the Form A and listing authorization through proper channels."
- Fires `general_lead_capture` with `seller_intent="co_broker_compliance"`

### Conveyancing offer-existence privacy (Phase 8.7)
- Verified + unverified branches in `legitimate_conveyancing` now use IDENTICAL phrasing — no implicit confirmation/denial of another buyer's offer status
- "I can't share specifics about another buyer's offer status with you directly. I've forwarded this to Eric and he'll reach out to discuss the conveyancing next steps."
- Escalation alerts still differ (verified = high-priority `legitimate_conveyancing`; unverified = no Telegram alert + suspicious_activity log)

### Direct intermediary fee answers (Phase 8.8)
- New prompt section `INTERMEDIARY FEE QUESTIONS` answers substantively rather than deferring entirely to Eric
- "Buyer pays 0.15% to Mahoroba on the transaction. Any additional fee you negotiate with your client is separate from us. For partnership terms, Eric handles those directly."

### Seller-mode message persistence + privacy-explanation tracking (Phase 8.9)
- `_handle_seller_message` now `get_or_create_conversation` + persists both seller messages AND bot responses
- Privacy-explanation flag (`dalya.ai/dashboard` + `privacy risk` in prior bot messages) now correctly detected on T2+ → short-form variant: `"Your listing has active buyer interest with offers in play. Full breakdown is on dalya.ai/dashboard."`
- T1 still gets the full privacy reasoning

### Promise-language → escalation invariant (Phase 8.10)
- Post-response check: if `_response_promises_forwarding(bot_response)` matches and no escalation already fired, fires a default `general_lead_capture` with `escalation_subtype="promise_kept"` (Phase 9.10 migrated from `seller_intent`)
- Bot's words now match system actions; "I've forwarded to Eric" no longer fires without an actual alert

---

## Phase 9 — Pilot Polish (2026-05-08)

### Eric Lead Broker introduction on first mention (Phase 9.1)
- New helpers `_has_eric_been_introduced(conv)` and `_inject_eric_intro_on_first_mention(response, conv)` in `chatbot_engine.py`
- First mention of Eric in a conversation gets the Lead Broker intro: "Eric, our Lead Broker at Dalya who handles all transactions"
- Subsequent mentions use just "Eric"
- Derived from message history (no DB schema change) — three rotated phrasings; idempotent
- Universal `_finalize_response()` wrapper applies the rule across buyer mode, seller mode, professional mode, conveyancing mode, no-listing fallback, regulatory acknowledgments
- Prompt builder now also instructs Claude to write the introduction itself on first mention; the post-processor is the failsafe

### Total cost breakdown three-bucket framing (Phase 9.2)
- New prompt section `TOTAL COST BREAKDOWN — CORRECT FRAMING` separates "due at closing" (DLD 4% + Mahoroba 0.15% + seller equity settled at closing) from "over remaining SPA schedule" (developer balance assumed by buyer)
- Banned old framings: "Total fees on top of asking", "Total out of pocket: AED X" — these implied asking price was due upfront
- Seller equity remains a structural component (no quoted figure) — preserves Phase 8.2 SPA arithmetic protection

### Downward offer revision detection (Phase 9.3)
- Engine detects when current offer < most recent prior offer in same conversation (`is_downward_revision_pre`)
- New `downward_revision_context` kwarg threaded through `build_system_prompt`
- New prompt section `DOWNWARD OFFER REVISION — CURRENT TURN` instructs Claude to use distinct push-back language ("moving the wrong direction", "step back from your last offer") rather than fresh below-threshold pushback
- Forbids language suggesting progress when buyer revised down

### Above-threshold template variety + listing-level rotation (Phase 9.4)
- `_ABOVE_THRESHOLD_TEMPLATES_EN` expanded from 4 → 8 variants
- `_CONTACT_FOLLOWUP_EN_VARIANTS` (4 variants) and `_CONTACT_FOLLOWUP_AR_VARIANTS` (2 variants) replace single hard-coded follow-up
- New listing-level usage tracker `_LISTING_TEMPLATE_USAGE` (in-process dict, 24h decay) prevents the same template firing for different buyers on the same listing within 24h
- Falls back gracefully when all templates have been used recently

### FastCash engagement gate audit (Phase 9.5)
- Verified Phase 8.3 substantive-engagement gate is wired correctly: `_engagement_gate_pass()` runs BEFORE escalation logic in both pre-Claude template branch and the late-escalation block
- No code changes needed; gate continues to suppress escalations when buyer has < 3 substantive prior messages

### BRN request distinct from Form A (Phase 9.6)
- New `_detect_brn_only_request()` distinguishes BRN-only / RERA-card requests from Form A / listing-authorization requests
- Trigger patterns: `\bbrn\b`, `broker registration number`, `agent's BRN`, `RERA card`, `agent registration number` — without explicit Form A reference
- New escalation type `brn_request` (added to `EscalationAlert.escalation_type` Literal)
- Distinct deterministic template: "I've forwarded your BRN verification request to Eric. He'll reach out directly with the registration details for your CRM."
- Routes through both buyer-mode and professional-inquiry paths

### Conveyancing privacy strengthening (Phase 9.7)
- New prompt section `NAMED-BUYER OFFER STATUS — HARD INVARIANT`: forbids confirming or denying whether a SPECIFIC NAMED individual has submitted an offer, regardless of classifier routing
- Closes the gap when classifier reclassifies T2+ away from `legitimate_conveyancing` to `general_enquiry`
- Banned phrasings: "I don't have an offer from [Name] on file", "[Name] hasn't submitted an offer here", positive confirmations like "Yes, I have [Name]'s offer"
- Existing engine-level branch (Phase 8.7) continues to use the unified template for verified-classifier paths

### Seller listing-change → dashboard routing (Phase 9.8)
- New deterministic handler in `_handle_seller_message`: when `seller_intent in ROUTINE_INTENTS` (price_update, threshold_update, listing_edit) → bot returns dashboard-redirect template, NO escalation, NO Eric routing
- Seller intent classifier broadened: now catches "drop the price", "raise the price", "willing to negotiate down to", "reduce the price", "willing to accept down to" etc.
- Bot no longer says "Got it. You're setting a threshold at X..." (which implied actioning the change)
- Bot says: "Listing changes happen on your dashboard at dalya.ai/dashboard, not through chat. The change takes effect immediately once you save it there."

### OfferRecord realtime + returning-buyer detection (Phase 9.10)
- OfferRecord persistence on every detected offer (regardless of escalation) was already in place from Phase 5+ — verified intact
- New CRUD helper `crud.get_all_offers_for_buyer_listing(phone, listing_id)` — returns all offers, no time window, used for returning-buyer lookup
- New engine helper `_detect_returning_buyer_claim()` detects phrases like "messaged about this property", "few weeks ago", "did you hear back", "follow up on my", "circling back", "remember me"
- Returning-buyer logic fires on T1/T2 (not T5): if early turn AND returning-buyer claim detected, query OfferRecord; fire `returning_buyer_followup` escalation immediately
- New deterministic template `_returning_buyer_template` acknowledges prior offer (with relative date: "yesterday", "5 days ago", "about 3 weeks ago") if found in OfferRecord, OR notes "no record found, forwarded to Eric for verification" if not
- New escalation type `returning_buyer_followup` (added to `EscalationAlert.escalation_type` Literal)
- New schema field `escalation_subtype` separates buyer-mode subtypes from `seller_intent` (which now stays seller-mode-only)
- Migrated buyer-mode subtypes off `seller_intent`: `new_listing_inquiry`, `co_broker_compliance`, `soft_offer_above_*`, `promise_kept`, `brn_request`, `returning_buyer_*`
- Pre-existing latent bug `alert.escalation_type.value` (would crash on string-typed Literal) replaced with `str(alert.escalation_type)` in `notify_eric()` to handle all new escalation types safely

### Documentation
- New consolidated `BOT_RULES.md` reference doc — flattens prompt rules, engine logic, response sanitization, intent classification, schema constraints into one human-readable index for non-engineers + future-you. 29 sections covering identity, formatting, situation handlers, escalation rules, privacy invariants, fee structure, anti-hallucination guardrails, multilingual rules, and a source file map.

---

## Community Research System

### Automated Research Pipeline
- **Community Researcher agent** — Opus + Tavily web search two-pass pipeline: research pass extracts structured data, audit pass cross-checks for contradictions/staleness
- **Canonical KB schema** — JSON Schema (draft 2020-12) defining required structure for all community knowledge base files
- **Schema validator** — `scripts/validate_kb.py` CLI validates all KB files; `app/core/schema_validator.py` for programmatic use
- **Staging workflow** — Research output lands in `knowledge_base/needs_review/`, admin approves before going live
- **Admin research API** — `POST /admin/research` trigger, `GET /admin/research` list jobs, `POST /admin/research/{id}/approve` promote to live, `DELETE /admin/research/{id}` reject

### Auto-trigger on SPA Upload
- **Missing community detection** — When a listing activates without matching community data, research job auto-triggers
- **Listing status integration** — New "Community Research" stage in processing pipeline between SPA Verified and Listing Review
- **Seller notification** — Listing status shows "Researching community data" with descriptive notes per stage (queued, researching, awaiting review)

### 30-Day Re-audit
- **Staleness detection** — Daily worker checks approved KB files; flags any with `last_audited_at` > 30 days
- **Haiku-powered diff** — Lightweight re-audit using Haiku 4.5 + fresh web search to detect stale prices, construction updates, sold-out status changes
- **Flag-only** — Never auto-updates live data; sets status to "stale" with `audit_flags` for admin review
- **Rate-limited** — Max 3 communities per daily run to control API costs

---

## Developer Experience
- **Seed script** — `python scripts/seed.py` parses test SPA, activates, runs mock conversation
- **`.env.example`** — All required env vars documented
- **Automated tests** — Integration tests covering identity, pricing, viewings, escalation, property knowledge, language
- **24-persona chatbot test suite** — `scripts/chatbot_full_test.py` runs 24 personas in two passes (independent + dependent), with seller_phone seeding/teardown, intent-aware quality metrics (em-dashes, deferral phrases, closing-question rate, markdown bold, emoji), per-persona rubric checks. Successful full runs publish the full JSON set plus `index.html` to `reports/chatbot_test_multitenant/`; incomplete runs stay in a temporary work directory and are not published to `reports/`. Reproducer: `PYTHONPATH=$(pwd) python scripts/chatbot_full_test.py`
- **Quality metrics framework** — Fleet-level + per-persona quality metrics with comparator-based pass/fail (`<=`, `==`, `>=`); per-persona `metric_targets` overrides for negotiation-heavy personas
