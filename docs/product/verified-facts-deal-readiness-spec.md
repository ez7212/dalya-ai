# Verified Facts + DealReadiness — Shared Layer Design Spec

**Status:** Design/spec only. **No runtime code, prompts, migrations, API, or
frontend change in this PR.** This document defines the shared *Verified Facts*
and *DealReadiness* layer and splits it into two implementation tickets
(**DAL-173A** loader, **DAL-173B** readiness core) that can be built without
touching chatbot behaviour.

This spec **consolidates and does not replace** the existing design docs. Those
remain the authoritative product detail; this one adds the concrete shared data
model / module interfaces and the implementation split:

- Product detail for readiness: [`deal-readiness-v1.md`](./deal-readiness-v1.md)
- Loader/runtime handoff for facts: [`verified-facts-runtime-handoff.md`](./verified-facts-runtime-handoff.md)
- Fact content + status legend: [`../domain/dubai-real-estate-verified-facts.md`](../domain/dubai-real-estate-verified-facts.md)
- Supporting: [`chatbot-qualification-rules-v1.md`](./chatbot-qualification-rules-v1.md),
  [`hot-list-scoring-v1.md`](./hot-list-scoring-v1.md),
  [`agent-handoff-summary-v1.md`](./agent-handoff-summary-v1.md)

## Why one shared layer

Two independent capabilities are needed before the chatbot/runtime can be made
smarter, and both must be buildable as **pure, side-effect-free data layers**
first:

1. **Verified Facts** — a structured, source-tagged, freshness-aware registry of
   Dubai real-estate facts the chatbot is *allowed* to state. Today the facts
   live as markdown (`dubai-real-estate-verified-facts.md`); there is no
   programmatic loader/registry.
2. **DealReadiness** — a single derived buyer-readiness read model
   (`stage`, `missing fields`, `next best action`, `score`) that every surface
   can share. Today each surface re-derives "is this buyer serious?" its own way
   (`buyer_profiles.py`, `hot_list.py`, `summary_worker.py`).

Building these as standalone, tested modules (DAL-173A, DAL-173B) lets the
chatbot/dashboard adopt them later in a separate, reviewed step — **no behaviour
change until then.**

---

## Part 1 — Verified Facts

### 1.1 Goal
A loader + in-memory registry that reads verified facts from a config-backed
source (initially the domain markdown and/or a small structured fixture), exposes
them as validated `VerifiedFact` records, and lets a consumer query by
category/domain/status. **Global (Dalya-wide) facts are kept separate from
brokerage-specific knowledge.**

### 1.2 `VerifiedFact` representation (target for DAL-173A)
A minimal, immutable record. Field names are the contract for the loader and its
tests:

| Field | Type | Meaning |
| --- | --- | --- |
| `key` | str | Stable identifier, e.g. `dld_registration_fee_pct`. |
| `category` | str | Section/topic, e.g. `fees`, `noc_transfer`, `off_plan`, `ready_resale`, `forms`, `mortgage`, `process`. |
| `domain` | str | Jurisdiction/domain scope, default `dubai_real_estate`. |
| `scope` | enum | `global` (Dalya-wide) vs `tenant` (brokerage-specific). Default `global`. |
| `text` | str | The fact statement / value. |
| `source_label` | str | Human source name (e.g. "DLD service catalogue"). |
| `source_ref` | str \| null | Citation id resolvable to the source register, e.g. `S1`. |
| `source_url` | str \| null | URL when available. |
| `effective_date` / `version` | str \| null | Freshness / "last verified" date or version tag. |
| `status` | enum | Markdown status label (see legend). |
| `runtime_policy` | enum | Derived consumption policy: `direct` · `draft_for_agent_only` · `do_not_state` · `listing_specific_only`. |
| `active` | bool | Inactive facts are excluded from active retrieval. |

### 1.3 Status → runtime policy (authoritative mapping)
Reuse the mapping already specified in
[`verified-facts-runtime-handoff.md`](./verified-facts-runtime-handoff.md) §2:

| Markdown status | `runtime_policy` |
| --- | --- |
| `confirmed` (general) | `direct` |
| `confirmed` (transaction-/listing-specific) | `draft_for_agent_only` |
| `draft-for-agent only` | `draft_for_agent_only` |
| `Eric decision required` | `draft_for_agent_only` |
| `repo-asserted (unverified)` | `draft_for_agent_only` |
| `listing-specific only` | `listing_specific_only` |
| `do not state` | `do_not_state` |

**Hard rule the loader encodes:** `direct` is granted **only** to a `confirmed`
row that is *not* transaction/listing-specific. Source-confirmed ≠ direct-safe.

### 1.4 Validation rules (loader must enforce)
- Reject a fact missing `key`, `category`, `text`, `source_label`, or `status`.
- Reject an unrecognized `status` (do **not** guess); a missing/ambiguous status
  is treated as `draft_for_agent_only`, never `direct`.
- `scope=global` facts must not carry a `brokerage_id`; `scope=tenant` facts must.
- Active retrieval excludes `active=False` and `do_not_state` from any
  buyer-facing query path.

### 1.5 Loader interface (target shape, DAL-173A)
A pure module `app/core/verified_facts.py` (no DB writes, no network at import):
- `load_verified_facts(source=...) -> list[VerifiedFact]` — parse + validate.
- `VerifiedFactRegistry` with: `get(key)`, `by_category(category)`,
  `by_domain(domain)`, `active()` (active + retrievable), and a `scope` filter
  (`global` vs `tenant`).
- Source is config-backed (path to the markdown/fixture), so tests can load a
  small fixture without the full domain file.

### 1.6 Freshness / update model
- Each fact exposes `effective_date`/`version`; the registry can report the
  oldest fact per category so staleness is visible.
- Updating facts = editing the source file/fixture + re-running the loader; no
  schema, no migration. (A DB-backed store is explicitly out of scope for 173A.)

### 1.7 How the chatbot will consume (LATER — not in 173A)
Per [`verified-facts-runtime-handoff.md`](./verified-facts-runtime-handoff.md)
§3: `direct` only when the live listing/context matches; otherwise
`draft_for_agent_only`; `do_not_state` refuses safely; `listing_specific_only`
only from that listing's verified data. **173A wires nothing into answer
generation.**

---

## Part 2 — DealReadinessProfile

### 2.1 Goal
A pure helper that converts available buyer/profile data into a derived readiness
read model: **stage, missing fields, next best action, score/priority band** —
deterministic and side-effect-free.

### 2.2 Inputs (reuse existing data — no new buyer fields required for the core)
Built from the existing buyer-profile field rows
(`app/core/buyer_profiles.py` `effective_fields()` over `DBBuyerProfileField`,
provenance `ai_inferred`/`agent_confirmed`) plus conversation/listing context.
Existing `QUALIFICATION_FIELDS` already cover `budget_min_aed`, `budget_max_aed`,
`financing`, `preapproval_*`, `timeline`, `target_areas`, `property_type`,
`bedrooms`, `must_haves`, `deal_breakers`. Fields the readiness model considers
(`purpose`, `family_size`, `decision_makers`, `in_dubai_now`,
`viewing_availability`, `other_agent_status`, `urgency`, `contact_preference`,
preferred area/type) are read **if present**; absent ones surface as *missing*.
The full field semantics are in [`deal-readiness-v1.md`](./deal-readiness-v1.md)
Part A — **DAL-173B does not add buyer-profile columns**; new fields are adopted
later when the extraction layer is extended.

### 2.3 `DealReadinessProfile` output (target for DAL-173B)
| Field | Type | Meaning |
| --- | --- | --- |
| `stage` | enum | `new` · `partially_qualified` · `qualified` · `hot` · `viewing_ready` · `offer_ready` · `agent_takeover_required` (from [`deal-readiness-v1.md`](./deal-readiness-v1.md) Part B). |
| `missing_fields` | list[str] | Required/helpful fields not yet known. |
| `next_best_action` | enum | One `NextBestAction` value (Part C of deal-readiness-v1). |
| `next_best_action_reason` | str | Short why, for agent display. |
| `score` | int | 0–100 readiness/priority score. |
| `priority_band` | enum | `low` · `medium` · `high` (derived from score). |
| `present_fields` | dict | Snapshot of the fields used, with provenance. |

### 2.4 Determinism & purity (DAL-173B contract)
- Pure function: same input → same output; **no DB writes, no outbound
  messages, no hot-list mutation.**
- `next_best_action` follows the missing-field priority order in
  [`deal-readiness-v1.md`](./deal-readiness-v1.md) Part C (qualify money &
  motivation before logistics; explicit viewing/offer intent overrides).
- Investor vs end-user (`purpose`) changes which fields matter and the next
  question, but the function stays deterministic.
- Readiness is **derived, never stored as truth** — callers recompute from the
  field snapshot.

### 2.5 Helper interface (target shape)
A pure module `app/core/deal_readiness.py`:
- `compute_readiness(fields: dict, *, conversation_ctx=None, listing_ctx=None) -> DealReadinessProfile`.
- Thresholds (the `qualified`/`hot` bars) are constants flagged "Eric to confirm"
  per deal-readiness-v1 — defaults are product defaults, not regulatory claims.

---

## Part 3 — Integration plan (LATER — explicitly out of this and 173A/173B)

This spec and the two implementation tickets are **read-only data layers**. None
of the following happen in 173A/173B; each is a separate, reviewed step:

- **Chatbot integration (later).** Gate exact regulatory/fee/process claims
  through the Verified Facts registry in `prompt_builder.py` /
  `response_validator.py` / `chatbot_engine.py`. Per the handoff doc, **do not
  touch chatbot-runtime files in parallel with DAL-172A.** No prompt changes now.
- **Agent dashboard integration (later).** Feed `DealReadinessProfile` into the
  Today Queue surfaces (Needs Reply / Hot Buyers / Drafts / Viewings) so the bot,
  buyer card, and dashboard share one `next_best_action`. (The dashboard already
  consumes a server `needs_reply` signal — DAL-170E5.)
- **Lead-ingest / drafts / hot-list compatibility.** DealReadiness must *map to*,
  not replace, the existing `hot_list.py` `next_action` enum and
  `DBLeadAssignment` derived fields (mapping table in deal-readiness-v1 Part C).
  173B is additive and changes no ranking; hot-list/lead-ingest behaviour is
  unchanged until a later adoption ticket.

**Compatibility guarantee:** building 173A and 173B changes no existing surface.
They are new modules + tests only.

---

## Part 4 — Implementation split (actionable tickets)

### DAL-173A — Verified Facts loader
- **Build:** `app/core/verified_facts.py` (`VerifiedFact`, `load_verified_facts`,
  `VerifiedFactRegistry`); a small seed fixture of Dubai facts if safe.
- **Enforce:** §1.4 validation; §1.3 status→policy mapping; global vs tenant
  separation.
- **Tests:** valid facts load; missing source/status/category rejected; inactive
  excluded from active retrieval; category/domain filtering; `direct` only for
  general `confirmed`; tenant/global distinction preserved.
- **Do NOT:** wire into chatbot answer generation; change prompts; add DB
  migrations; touch dashboard/frontend; implement DealReadiness beyond any types
  needed for imports.

### DAL-173B — DealReadinessProfile core
- **Build:** `app/core/deal_readiness.py` (`DealReadinessProfile`,
  `compute_readiness`) reading existing buyer-profile fields.
- **Produce:** `stage`, `missing_fields`, `next_best_action` (+reason), `score`,
  `priority_band` — deterministic, pure.
- **Tests:** complete profile → high readiness; missing
  decision-maker/viewing/financing → surfaced in `missing_fields`; investor vs
  end-user handled; next-best-question deterministic; no DB writes / no side
  effects.
- **Do NOT:** change chatbot/prompt behaviour, hot-list ranking, lead-ingest,
  WhatsApp send, dashboard UI; add migrations unless absolutely required and
  justified; modify the Verified Facts loader beyond imports/types.

---

## Out of scope (this PR)
No chatbot runtime changes, prompt changes, DB migrations, API changes, frontend
changes, RLS/DAL-170E changes, WhatsApp behaviour changes, or lead-ingest
changes. Spec only.
