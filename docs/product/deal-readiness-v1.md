# Deal Readiness v1

**Status:** Spec. No runtime code changed by this document. Safe parallel work while DAL-172 (explicit brokerage context) is in progress — this doc does not touch auth, tenant context, agent route helpers, or API client brokerage headers.

## Why this exists

Dalya extracts buyer signals in several places today (Haiku intent classifier, rule-based extraction in `app/core/buyer_profiles.py`, hot-list scoring in `app/core/hot_list.py`, conversation summaries in `app/core/summary_worker.py`), but there is **no single buyer-readiness model** they all share. Each surface re-derives "is this buyer serious?" its own way.

**Deal Readiness v1 defines one shared model** that can later feed:
- chatbot qualification (which question to ask next)
- the buyer card (qualification snapshot)
- the hot list (ranking + "why hot")
- draft-reply context (what the bot knows when drafting)
- the agent handoff summary
- the viewing brief
- agent escalation

This is deliberately aligned with what already exists so it can be adopted incrementally rather than rebuilt. Where the repo already has a field/enum, this spec reuses its name.

## Design principles

1. **One profile per `(brokerage_id, buyer_phone)`** — matches `DBBrokerageBuyerProfile`. Multi-tenant isolation is preserved; the same phone at two brokerages is two profiles. (This spec does not change isolation behavior — DAL-170/DAL-172 own that.)
2. **Every field carries provenance + confidence** — matches the existing `ai_inferred` / `agent_confirmed` split with `confidence` and `source_message_id`. The AI never overwrites an agent-confirmed value.
3. **Confirmed beats inferred; a conflicting inference becomes a suggestion chip** — matches `effective_fields()`.
4. **Readiness is derived, not stored as truth** — stages and next-best-action are computed from the field snapshot, so they can't drift from the underlying facts.
5. **Buyer messages are untrusted** — extraction writes only `ai_inferred` rows; promoting to confirmed is an agent action.

---

## Part A — DealReadinessProfile

A read model computed from the buyer profile field rows + conversation + listing context. Field names reuse `QUALIFICATION_FIELDS` where they already exist (marked ✅ existing); new fields are marked ➕ new.

Each field is described as: **meaning · example values · status model · source · safe to ask buyer directly? · agent should verify? · why it matters to a Dubai agent.**

### Core buyer fields

#### `budget_min` / `budget_max` (currency-aware) ✅ existing (`budget_min_aed`, `budget_max_aed`)
- **Meaning:** buyer's price range.
- **Examples:** min 3,000,000; max 4,500,000.
- **Status:** confirmed / inferred / missing.
- **Source:** buyer_message, imported_lead, agent_note, inferred.
- **Safe to ask buyer:** yes — first qualification question.
- **Agent verifies:** yes if inferred from a vague phrase ("around 4M-ish").
- **Why it matters:** budget gates everything; an unbudgeted buyer is not callable. Cash-at-4.5M ≠ mortgage-at-4.5M.

#### `currency` ➕ new
- **Meaning:** currency the budget is expressed in (default AED).
- **Examples:** AED, USD, GBP.
- **Status / source:** inferred from phrasing; usually AED.
- **Safe to ask:** rarely needed; infer.
- **Agent verifies:** only if a foreign-currency buyer implies FX/transfer complexity.
- **Why it matters:** overseas buyers quoting USD/GBP signal non-resident process (see edge cases in facts-to-verify §G).

#### `financing_type` ✅ existing (`financing`: `cash | mortgage_preapproved | mortgage_unknown | unknown`)
- **Meaning:** how the buyer pays.
- **Examples:** cash, mortgage_preapproved, mortgage_unknown, unknown.
- **Safe to ask:** yes — "cash or mortgage?" is natural.
- **Agent verifies:** yes — "cash" claimed in chat is not proof of funds.
- **Why it matters:** cash buyers close faster and are stronger at offer; mortgage-unknown buyers carry approval risk.

#### `mortgage_preapproval_status` ✅ existing (`preapproval_amount_aed`, `preapproval_bank`)
- **Meaning:** whether a mortgage buyer is pre-approved, for how much, with which bank.
- **Examples:** pre-approved 3.2M with Emirates NBD; "applied, awaiting"; none.
- **Safe to ask:** yes, lightly ("are you already pre-approved?").
- **Agent verifies:** yes — pre-approval letter is the real proof.
- **Why it matters:** a pre-approved mortgage buyer is close to a cash buyer in strength; "mortgage, not started" is a long road.
- **Note:** Dalya must not give mortgage advice or quote LTV (repo guardrail). Capturing status ≠ advising.

#### `purpose` ➕ new (`end_use | investment | both | unknown`)
- **Meaning:** is the buyer living in it or investing?
- **Examples:** end_use (family home), investment (yield/appreciation), both.
- **Safe to ask:** yes — "is this for you to live in, or investment?" is the highest-value second question.
- **Agent verifies:** low need.
- **Why it matters:** changes everything Dalya should surface — end-users care about schools/view/noise/handover; investors care about yield/payment-plan/exit. (Off-plan vs ready relevance, per `CLAUDE.md`.)

#### `property_type` ✅ existing
- **Meaning:** apartment / villa / townhouse / etc.
- **Safe to ask:** yes.
- **Why it matters:** filters stock; villa vs apartment changes the relevant questions (parking, service charge, community).

#### `bedrooms` ✅ existing
- **Meaning:** bedroom count or range.
- **Examples:** 2; [2,3]; "studio".
- **Safe to ask:** yes.
- **Why it matters:** core filter; mismatch with budget reveals an unrealistic buyer to coach.

#### `preferred_locations` ✅ existing (`target_areas`)
- **Meaning:** communities/areas of interest.
- **Examples:** ["Dubai Marina", "JBR"].
- **Safe to ask:** yes.
- **Why it matters:** Dubai buyers are location-anchored; a budget that doesn't fit the area is a coaching moment.

#### `timeline` ✅ existing
- **Meaning:** when they intend to transact.
- **Examples:** "this month", "within 2 weeks", "by Q3", "just browsing".
- **Safe to ask:** yes.
- **Why it matters:** separates a buyer worth calling today from a nurture lead.

#### `urgency` ➕ new (derived: `high | medium | low | unknown`)
- **Meaning:** derived pressure level, from timeline + intent signals (viewing/offer) + responsiveness.
- **Source:** inferred (not asked).
- **Why it matters:** drives hot-list ranking and "call now vs follow up".

#### `family_size` ➕ new
- **Meaning:** household size / has children.
- **Examples:** couple, family of 4, single.
- **Safe to ask:** only when natural (end-use buyer mentions kids).
- **Why it matters:** end-use fit (bedrooms, schools, community), and it humanizes the agent's call.

#### `decision_makers` ➕ new
- **Meaning:** who else must agree (spouse, partner, parents, company).
- **Examples:** "buying with wife", "needs partner sign-off", sole.
- **Safe to ask:** gently, near viewing/offer stage.
- **Agent verifies:** yes — a hidden second decision-maker kills deals late.
- **Why it matters:** an offer-ready buyer who hasn't looped in their co-decision-maker is a stall risk.

#### `in_dubai_now` ➕ new (`yes | no | unknown`)
- **Meaning:** is the buyer physically in Dubai / when do they arrive.
- **Safe to ask:** yes, near viewing.
- **Why it matters:** decides in-person vs video viewing and realistic timeline; overseas buyer → non-resident process flag.

#### `viewing_availability` ➕ new
- **Meaning:** when the buyer can view.
- **Examples:** "weekends", "this Thursday evening", specific slots.
- **Safe to ask:** yes, once viewing intent exists.
- **Why it matters:** the single field that turns viewing intent into a booked viewing.

#### `other_agent_status` ➕ new (`exclusive_with_us | working_with_others | unknown`)
- **Meaning:** is the buyer already working with another agent/brokerage.
- **Safe to ask:** carefully ("are you working with an agent already?").
- **Agent verifies:** yes.
- **Why it matters:** affects effort allocation and whether a Form B / buyer-agent relationship is realistic.

#### `contact_preference` ➕ new (`whatsapp | call | either`)
- **Meaning:** how the buyer wants to be reached.
- **Safe to ask:** yes.
- **Why it matters:** a buyer who said "WhatsApp only" shouldn't be cold-called at 9pm.

#### `nationality_or_residency_relevance` ➕ new
- **Meaning:** only captured when it materially affects process (non-resident, company buyer, needs POA).
- **Safe to ask:** only when relevant; never as a profiling question.
- **Agent verifies:** yes.
- **Why it matters:** flags non-resident/corporate process to the agent. **Capture only process-relevant facts; this is PDPL-covered personal data — do not collect ethnicity/nationality for any other purpose.**

#### `buyer_name` ✅ existing (on profile/conversation)
- **Safe to ask:** yes, naturally in the 2nd–3rd exchange (matches current bot behavior).
- **Why it matters:** personalizes handoff; "the buyer" vs "Sara" changes the agent's call.

#### `phone` ✅ existing (`buyer_phone`, profile key)
- **Why it matters:** identity + contact; already the profile key.

#### `preferred_language` ➕ new (if available; repo already detects `language_detected`)
- **Meaning:** buyer's language (EN/AR/RU/HI/Mandarin).
- **Source:** inferred from messages.
- **Why it matters:** agent should call in a language the buyer is comfortable in; routing to a matching agent.

### Field status model (reused from repo)
- **confirmed** — `agent_confirmed` row exists.
- **inferred** — only `ai_inferred` row exists (carries `confidence`, `source_message_id`).
- **missing** — no row.
- **suggestion** — confirmed row exists but a newer inference differs (surface as a chip; only an agent action promotes it). Matches `effective_fields()`.

### Source values (reused / extended)
`buyer_message` · `listing_context` · `agent_note` · `imported_lead` · `inferred`. (Today the message path tags `ai_inferred` with `source_message_id`; `imported_lead` maps to `DBLeadIngestRecord`.)

---

## Part B — Readiness stages

Stages are **derived** from the field snapshot + conversation intent. They are ordered but not strictly linear (a buyer can jump to `agent_takeover_required` from anywhere).

> ⚠️ "Required confirmed fields" should be read against Eric's actual qualification bar (verified-facts §1, currently `[Eric to fill]`). The thresholds below are a sensible v1 default, explicitly marked for Eric's review — they are product defaults, not Dubai regulatory claims.

### `new`
- **Required confirmed:** none.
- **Helpful optional:** anything captured at ingest (name, source listing).
- **Disqualifiers/blockers:** opted-out / spam-only.
- **Next best action:** `send_options` or `ask_budget` (or, for a fresh portal lead, the bounded first-touch — already handled by lead ingest).
- **Agent sees:** "New — not yet qualified," last message, source.

### `partially_qualified`
- **Required confirmed:** at least one core field beyond identity (budget OR purpose OR financing OR a concrete property interest).
- **Helpful optional:** the other core fields.
- **Blockers:** contradictory signals (budget far below area).
- **Next best action:** the highest-priority missing-field question (see Part C).
- **Agent sees:** partial snapshot + which fields are missing.

### `qualified`
- **Required confirmed:** budget (min or max) **and** financing_type **and** (purpose OR concrete property/location interest). [Eric to confirm bar]
- **Helpful optional:** timeline, bedrooms, locations.
- **Blockers:** none structural.
- **Next best action:** `send_options` / `draft_follow_up` / `agent_call_now` depending on urgency.
- **Agent sees:** "Qualified" badge, snapshot, suggested next move.

### `hot`
- **Required confirmed:** `qualified` **plus** a high-intent signal (viewing request, offer intent, or explicit urgency/timeline ≤ Eric's "urgent" window) **and** responsiveness.
- **Blockers:** an unresolved disqualifier downgrades it.
- **Next best action:** `agent_call_now` or `escalate_to_agent`.
- **Agent sees:** top of hot list with "why hot" + missing blocker (see [hot-list-scoring-v1](./hot-list-scoring-v1.md)).

### `viewing_ready`
- **Required confirmed:** property/listing of interest **and** `viewing_availability` (or enough to propose slots) **and** `in_dubai_now` (or video-viewing accepted).
- **Next best action:** `prepare_viewing_brief` / `ask_viewing_availability` if the slot is the only gap.
- **Agent sees:** proposed viewing context, what to confirm (access, slot).

### `offer_ready`
- **Required confirmed:** budget + financing + a specific listing + offer intent.
- **Helpful optional:** decision_makers confirmed, proof of funds / pre-approval.
- **Blockers:** undisclosed second decision-maker; financing unverified.
- **Next best action:** `prepare_offer_context` then `escalate_to_agent` — **Dalya never negotiates autonomously.**
- **Agent sees:** offer context pack, risk flags.

### `agent_takeover_required`
- **Trigger from any stage:** offer/negotiation, legal/process question not answerable from verified facts, low context confidence on a high-stakes turn, prompt-injection/abuse, regulatory (PDPL) request, or the buyer explicitly asking for a human.
- **Next best action:** `escalate_to_agent` / `agent_call_now` / `cannot_answer_needs_agent`.
- **Agent sees:** escalation reason + last message + draft (if any).

---

## Part C — Missing fields & Next Best Action

### The rule
**The bot asks at most one question per buyer-facing turn**, and it asks for the **highest-priority missing field only** (see [chatbot-qualification-rules-v1](./chatbot-qualification-rules-v1.md)). Never re-ask a field that is already confirmed or confidently inferred.

### Missing-field priority order
1. If **budget** missing → `ask_budget`.
2. If **purpose** missing → `ask_purpose` (end-use vs investment).
3. If **financing** missing → `ask_financing` (cash vs mortgage).
4. If **timeline** missing → `ask_timeline`.
5. If **location / property type** missing → `ask_location`.
6. If **viewing intent exists** → `ask_viewing_availability`.
7. If **offer intent exists** → `escalate_to_agent` / `prepare_offer_context` (draft, never auto-negotiate).
8. If a **legal/process question** appears → answer **only** from verified facts ([verified-facts](../domain/dubai-real-estate-verified-facts.md)); otherwise `draft_follow_up` / `cannot_answer_needs_agent`.

This order is a default for Eric's review. The intent of the ordering: qualify money and motivation before logistics, and let any explicit high-intent signal (viewing/offer) override the gather sequence.

### NextBestAction values
| Value | When | Bot vs agent |
|---|---|---|
| `ask_budget` | budget missing, no higher-priority intent | bot asks (one question) |
| `ask_purpose` | budget known, purpose missing | bot asks |
| `ask_financing` | purpose known, financing missing | bot asks |
| `ask_timeline` | financing known, timeline missing | bot asks |
| `ask_location` | location/type missing | bot asks |
| `ask_viewing_availability` | viewing intent, slot missing | bot asks |
| `send_options` | qualified + buyer asked for options | bot sends listing matches |
| `draft_follow_up` | stale / soft next step | **draft for agent** |
| `agent_call_now` | hot + high intent | agent action |
| `escalate_to_agent` | offer, ambiguity, low confidence | escalate (+ draft) |
| `prepare_viewing_brief` | viewing_ready | system assembles brief for agent |
| `prepare_offer_context` | offer_ready | system assembles offer pack for agent |
| `cannot_answer_needs_agent` | unverified legal/process/fee claim | safe decline + draft/escalate |

**Mapping to existing code:** the current `hot_list.py` `next_action` enum (`review_offer`, `book_viewing`, `clarify_financing`, `call_now`, `follow_up`) is a subset of the above. v1 implementation should **map**, not replace: `review_offer`→`prepare_offer_context`/`escalate_to_agent`; `book_viewing`→`ask_viewing_availability`/`prepare_viewing_brief`; `clarify_financing`→`ask_financing`; `call_now`→`agent_call_now`; `follow_up`→`draft_follow_up`.

---

## Dashboard implications

(Spec note only — **this task does not edit dashboard code**. UX implementation happens later with the UX Designer + Real Estate Guru reviewers.)

- The `/agent` first screen should eventually become a **Today queue** — the few buyers and actions that matter right now, not a generic list.
- Deal readiness should feed four dashboard surfaces:
  - **Needs Reply** — buyers awaiting a response / where a question is the next action.
  - **Hot Buyers** — `hot` / `offer_ready` / `viewing_ready`, ranked by the hot-list score, each row showing "why hot" + missing blocker.
  - **Drafts to Approve** — `DBDraftReply` rows in `draft`/`edited`, the draft-and-approve queue.
  - **Viewings / Follow-ups** — `viewing_ready` buyers and stale follow-ups.
- Each row should expose the same derived `next_best_action` + reason, so the bot, the card, and the dashboard never disagree.

---

## Current repo alignment

- **Likely current matching concepts:**
  - `app/core/buyer_profiles.py` — `QUALIFICATION_FIELDS`, provenance (`ai_inferred`/`agent_confirmed`), `confidence`, `source_message_id`, `effective_fields()` (confirmed-over-inferred + suggestion chip). This is ~70% of Part A already.
  - `app/core/hot_list.py` — `HotListScore` with `signal`, `urgency_score`, `next_action`, `next_action_reason`, `status` — a proto-readiness model.
  - `app/core/summary_worker.py` — `ai_summary` (`interest_level`, `sentiment`, `key_question`, `next_step_hint`) — proto-urgency signals.
  - `app/core/lead_ingest.py` — `imported_lead` source + first-touch flow.
  - `app/db/models` — `DBLeadAssignment` (`next_action`, `due_at`, `status`) is where derived readiness already lands.
- **Likely gaps vs this spec:**
  - No `purpose`, `urgency` (derived), `decision_makers`, `in_dubai_now`, `viewing_availability`, `other_agent_status`, `contact_preference`, `nationality_or_residency_relevance` fields yet.
  - Readiness "stages" don't exist as a named concept; `signal`/`status` are close but coarser.
  - `next_action` enum is narrower than `NextBestAction` and not driven by a missing-field priority order.
  - No single computed `DealReadinessProfile` read model that all surfaces consume.
- **Files likely affected later (do NOT change now):** `app/core/buyer_profiles.py` (add fields/enums), `app/core/hot_list.py` (consume readiness instead of ad-hoc branches), `app/core/summary_worker.py`, schemas in `app/schemas/conversation.py`, and a new `deal_readiness.py` read-model module. Dashboard/API wiring is out of scope and overlaps DAL-172 — defer.
- **Implementation ticket suggestion:** "Implement DealReadinessProfile read model" (see final output) — additive, no isolation/auth changes.
