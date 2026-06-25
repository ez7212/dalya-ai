# 02 — Pilot Seed Dataset (the exact spec)

All rows are **pilot/demo data**. Every row carries a marker so reset is surgical:
- id prefix `pilot_` where the model has a string PK, OR
- a `metadata`/notes tag `dalya_pilot=mahoroba-2026-06`.

Brokerage id is the canonical **`mahoroba-realty`**. Phone numbers are fake UAE test numbers in the
`+97150000xxxx` range (matching existing seed convention). Reset refuses to run without
`DALYA_PILOT_CONFIRM=mahoroba-realty`.

> Values marked **[INPUT]** should be confirmed by Eric (`07-MANUAL-INPUTS.md`); the bracketed value is
> the safe default the agents use if no answer is given.

---

## 1. Brokerage (1)

| Field | Value |
|-------|-------|
| brokerage_id | `mahoroba-realty` |
| name | Mahoroba Realty |
| slug | `mahoroba-realty` |
| real_estate_number (DLD) | `1858` **[INPUT — confirm or use placeholder]** |
| brokerage_ai_number | `+971500000001` |
| agents_ai_number | `+971500000099` |
| status | active · agent signup enabled |
| default_fee_framing | market_benchmark 0.02, commission_rate 0.0085, managing_agent_title "agent managing this listing" |

## 2. Agents (Eric + 3 supporting)

| user_id | name | email | phone | role | specialty |
|---------|------|-------|-------|------|-----------|
| `pilot_eric` (→ **real Supabase uuid [INPUT §6]**) | Eric Zhu | `eric+dalya-pilot@example.com` **[INPUT — or `ericzhu0702@gmail.com`]** | `+971500000010` | brokerage admin + primary agent | all-round, owner |
| `pilot_sara` | Sara Khan | `sara+dalya-pilot@example.com` | `+971500000011` | senior agent | Dubai Hills / ready villas |
| `pilot_omar` | Omar Haddad | `omar+dalya-pilot@example.com` | `+971500000012` | off-plan specialist | Emaar / waterfront |
| `pilot_lina` | Lina Petrova | `lina+dalya-pilot@example.com` | `+971500000013` | leasing / viewing coordinator | tenant coordination, viewing logistics |

Each agent needs: `DBBrokerageMember` (status active), `DBAgentProfile` (verification_status `approved`,
onboarding_status `active`, RERA `BRN-PILOT-<NAME>`), `DBAgentChatbotConfig` (active). Only **Eric**
must map to a real Supabase auth user (he is the one who logs in); the other three can be data-only.

## 3. Listings (5)

> Off-plan listings should set `community`/`project` to a name present in `knowledge_base/` so
> community research + verified facts render (Emaar Oasis, Sobha SeaHaven, Address Harbour Point...).

### L1 — Dubai Hills ready villa (GOLDEN PATH) — agent: Eric
- property_type `ready`, type villa, 4BR, Dubai Hills Estate, ~5,200 sqft
- asking_price `AED 6,750,000` · notification_threshold `AED 6,400,000` (~5% below)
- occupancy `tenant-occupied`, tenant notice required, access via Lina; viewing logistics: weekday
  evenings + weekend mornings, 24h tenant notice
- service charge ~AED 16/sqft, title-deed/Ejari-style facts present and **verified+buyer_safe**
- seller notes (agent-only): "motivated, relocating Q4; will entertain 6.45M for fast close"
- media: 3 placeholder image URLs (`https://placehold.co/...`)

### L2 — Dubai Hills ready listing, INCOMPLETE facts (SAFE-FAILURE) — agent: Sara
- property_type `ready`, type townhouse, 3BR, Dubai Hills Estate
- asking_price `AED 4,900,000` · threshold set but **seller motivation unknown**
- **Intentionally missing/uncertain:** service charge (absent), title-deed/NOC details (absent),
  viewing access (unknown), seller motivation (unknown). Facts NOT verified.
- Purpose: force "agent confirmation needed" language + escalation on fact gaps.

### L3 — Emaar off-plan (VERIFIED FACTS) — agent: Omar
- property_type `off_plan`, developer Emaar, community **Emaar The Oasis** (maps to `emaar_oasis.json`)
- unit type 5BR villa · resale price `AED 12,500,000` · original price stored agent-only
- payment_schedule (SPA-like): 10% DLD + 80% during construction / 20% on handover (illustrative)
- amount_paid 40% · remaining 60% · handover **per knowledge base / SPA** (do NOT invent a date)
- brochure/floor-plan/render placeholder URLs
- Purpose: exercise Verified Facts output gate (DLD, NOC, LTV, remaining payment), off-plan
  **no-physical-viewing** behavior (lean to brochure/renders/agent follow-up).

### L4 — Investment-focused off-plan (ANALYTICAL INVESTOR) — agent: Omar
- property_type `off_plan`, developer Sobha, community **Sobha SeaHaven** (maps to `sobha_seahaven.json`)
- 2BR apartment · price `AED 3,400,000` · handover per KB/SPA · standard payment plan
- known-safe facts only; **no unsupported ROI/rental-yield promises** — any projection stored as
  agent-only note, never buyer-facing.
- Purpose: ROI-style questions handled safely; verified vs unsupported separation.

### L5 — Luxury / high-ticket (PREMIUM QUALIFICATION) — agent: Eric (or Sara)
- property_type `ready`, type signature villa, Dubai Hills / Emirates Hills-tier, 6BR
- asking_price `AED 28,000,000` · threshold `AED 26,500,000`
- seller notes (agent-only): "discreet sale, no portal listing, qualified buyers only"
- viewing constraints: by appointment, proof-of-funds before access
- Purpose: serious-buyer qualification, negotiation threshold, premium handoff.

## 4. Buyers (8) — simulated personas

| key | name | phone | budget | listing | profile / intent |
|-----|------|-------|--------|---------|------------------|
| `hot_ready` | Adam Miller | `+971551000001` | AED 6.5M | L1 | 4BR Dubai Hills, in Dubai, cash/pre-approved, this week, decision-maker present, wants viewing → should go **viewing-ready/hot** |
| `offplan_analytical` | Priya Shah | `+971551000002` | AED 3–4M | L4 (and L3) | off-plan investor; asks payment schedule, DLD fees, NOC, mortgage/LTV, service charge, handover risk → **Verified Facts gate + escalate unverified/legal** |
| `low_context` | (unknown→infer) | `+971551000003` | unknown | L1 | "price?", "last price?", "send pics" → **one useful qualifying question, low/partial readiness, no over-qualify** |
| `offer_buyer` | Hassan Ali | `+971551000004` | ~AED 6.1M | L1 | firm **below-threshold** offer, then revises up → **offer records, firm-offer detect, escalate, offer history** |
| `human_takeover` | Mei Chen | `+971551000005` | mixed | L5 | "can I speak to an agent?", mixed-language/vague → **escalation + agent takeover, pause/resume AI** |
| `media_voice` | (voice/img) | `+971551000006` | — | L1 | sends voice note / asks for images → **private-media posture or graceful fallback** (document if not simulable) |
| `opt_out` | (stop) | `+971551000007` | — | L1 | sends "stop" → **suppression + dashboard state** (`DBBuyerSuppression`) |
| `weak_listing` | Tom Becker | `+971551000008` | AED 4.8M | L2 | asks service charge / NOC / viewing on the **incomplete** listing → **safe failure + agent-confirmation language** |

Each maps to `DBBrokerageBuyerProfile` + `DBBuyerProfileField` rows. Pre-seed only the minimum profile
fields; let the chatbot simulation populate the rest so provenance (`ai_inferred` vs `agent_confirmed`)
is exercised live.

## 5. Conversations / messages (target 12–20 threads)

Seed 1 conversation per buyer (8), plus extra threads so Today Queue has volume:
- 2 stale/follow-up threads on L1/L3 (needs-reply, > 24h old)
- 1 post-viewing thread on L1 (drives post-viewing follow-up draft)
- 1–2 portal-lead-originated threads on L3/L4 (from §10 lead ingest)
Each conversation: `DBConversation` (listing_id, buyer_phone, ai_mode) + seeded `DBMessage` history
(role user/assistant). Most message volume comes from the **live simulation** in Phase 3, not pre-seed.

## 6. Offers (2–3)

- **O1 (firm, below threshold):** Hassan/L1, AED 6,100,000 buyer_offer, status `submitted`, escalated
  (gap below 6.4M threshold) → later seller counter AED 6,550,000 → buyer revises to AED 6,350,000.
- **O2 (AI-proposed draft to discard):** L3/Priya, `draft_pending_confirm` → **discard** (tests discard).
- **O3 (premium):** L5/Mei, AED 26,000,000 buyer_offer near threshold → counter path.
Use `DBOffer`/`DBOfferRecord`; exercise `confirm`, `discard`, `transition` (countered/accepted).

## 7. Viewings (2–3 flows)

- **V1 (ready, full flow):** L1/Adam — set logistics → availability blocks → propose slots from
  conversation → confirm → draft+send **tenant notice** (Lina) → buyer/tenant/calendar confirmation
  states → complete → request buyer feedback → record agent feedback.
- **V2 (off-plan, no-physical-viewing):** L3/Priya — system must **not** push physical viewing
  logistics; lean to brochure/floor-plan/renders/agent follow-up.
- **V3 (premium, gated):** L5/Mei — by-appointment, proof-of-funds before access.
Use `DBViewing` / `DBListingLogistics` / `DBTenantViewingConfirmation` / `DBViewingFeedback`.

## 8. Escalations (3–5 threads)

| key | source | type | expected |
|-----|--------|------|----------|
| E1 | Hassan firm offer (O1) | `offer` | critical, routes to Eric, bundles offer questions, no dup spam |
| E2 | Priya legal/fee uncertainty (L3/L4) | `regulatory`/`unanswerable_question` | escalate, agent-confirmation language to buyer |
| E3 | Mei speak-to-human (L5) | human handoff | escalation + AI pause |
| E4 | Tom unverified fact on L2 | `unanswerable_question` | "agent needs to confirm" + escalate |
| E5 (opt) | Adam viewing request (L1) | `viewing_request` | actionable viewing in queue |
Use `DBEscalationThread`/`DBEscalationThreadQuestion`; verify bundling (multiple questions → one
thread) and the `[Ref: TOKEN]` agent-reply relay via `DBAgentMessageRoute`/`DBAgentRelaySession`.

## 9. Drafts (3–5)

- D1 follow-up after low_context buyer asked price (L1)
- D2 post-viewing follow-up (L1, after V1 complete)
- D3 agent-confirmation-needed answer (L2, off the unverified-fact escalation)
- D4 offer response (L1, Hassan)
- D5 (opt) off-plan brochure follow-up (L3)
Use `DBDraftReply`/`DBAIDraft`. Each draft must carry: verified-fact metadata, missing-facts list,
DealReadiness snapshot, and a suggested follow-up question (draft-assist payload). Test
edit/send/reject/snooze; sent drafts must write message + action + compliance event where implemented.

## 10. Portal lead ingest (1–2)

- Property Finder payload → L3 (Emaar Oasis), buyer maps to a new profile, brokerage resolves to
  `mahoroba-realty`, **template-locked first touch only** (not free-form AI), assignment + nudge +
  compliance trail. Parser `property_finder:v1`.
- Bayut payload → L4 (Sobha), test **deduplication** against an existing buyer profile. Parser
  `bayut:v1`. Endpoint `POST /api/v1/leads/ingest/email` with `LEAD_INGEST_SECRET` header. Fixtures:
  reuse `tests/harness/snapshots/` shapes; if none fit, author minimal pilot fixtures under
  `tests/pilot/fixtures/`.

---

## Auth wiring for Eric (the one human-dependent piece)

The seed creates Eric's `DBBrokerageMember` + `DBAgentProfile` keyed on a **Supabase user uuid**. That
uuid must belong to a real Supabase auth user Eric can sign in as. Three acceptable paths, in order of
preference (Agent A picks whichever the environment allows, documents the choice):

1. **Real Supabase test user (preferred):** Eric provides/creates a Supabase user
   (`eric+dalya-pilot@example.com`) in the project's Supabase, gives the agents its **uuid** and a way
   to obtain a JWT (sign in via `/login` on the frontend, or a short-lived token). Seed uses that uuid.
   Set `ADMIN_USER_ID` to it so admin/CRM routes also work.
2. **Mint a JWT from `SUPABASE_JWT_SECRET`** (if HS-compatible test signing is available) for
   API-level phases (C/D) — UI phases still need a real session.
3. **Document blocker:** if no Supabase access, run Phases 3/4/5 at API level with a service/test
   context and record "UI-as-Eric login blocked: needs Supabase test user" — the demo (Phase 6/7)
   then can't run from the browser and that becomes a top blocker.
