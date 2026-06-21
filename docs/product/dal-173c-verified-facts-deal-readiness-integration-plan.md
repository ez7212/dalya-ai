# DAL-173C Verified Facts + DealReadiness Integration Plan

**Status:** Design only. No runtime wiring, migrations, frontend changes, DB-backed
tests, chatbot behavior changes, WhatsApp send changes, lead-ingest changes, or
hot-list ranking changes in this branch.

**Linear:** DAL-186.

## Verdict

Split required.

DAL-173A and DAL-173B created the correct pure building blocks, but wiring them
directly into buyer-facing chat, first-touch sends, drafts, and hot-list ranking
would combine unrelated risk. Adoption should be staged from internal,
read-only visibility toward buyer-facing behavior only after source/fallback
guardrails and regression tests exist.

## Files Reviewed

- `app/core/verified_facts.py`
- `app/core/data/verified_facts_seed.json`
- `app/core/deal_readiness.py`
- `app/core/prompt_builder.py`
- `app/core/chatbot_engine.py`
- `app/core/response_validator.py`
- `app/core/buyer_profiles.py`
- `app/core/hot_list.py`
- `app/core/lead_ingest.py`
- `app/core/post_viewing_followup.py`
- `app/api/agent_dashboard.py`
- `app/api/agent.py`
- `tests/test_verified_facts_loader_dal173a.py`
- `tests/test_deal_readiness_dal173b.py`
- `docs/product/verified-facts-deal-readiness-spec.md`
- `docs/product/verified-facts-runtime-handoff.md`
- `docs/product/deal-readiness-v1.md`
- `docs/product/chatbot-qualification-rules-v1.md`
- `docs/product/hot-list-scoring-v1.md`
- `docs/product/agent-handoff-summary-v1.md`

## Current Building Blocks

### Verified Facts

`app/core/verified_facts.py` is pure and side-effect free. It validates required
fact fields, maps source status to runtime policy, separates global and
tenant-scoped facts, excludes inactive and `do_not_state` facts from active
retrieval, and exposes category/domain/scope query helpers.

That is enough for future consumers, but there is no current intent classifier
or planner that maps a buyer question to required fact keys. The chatbot still
contains deterministic Dubai process/fee branches and prompt guidance that can
state facts without consulting the registry.

### DealReadiness

`app/core/deal_readiness.py` is pure and deterministic. It turns a resolved
buyer field snapshot plus optional conversation/listing context into stage,
missing fields, next best action, score, priority band, and present fields.

The natural input source is `buyer_profiles.effective_fields()`, but current
profile extraction only captures a subset of readiness fields. Newer readiness
fields such as `purpose`, `viewing_availability`, `decision_makers`,
`in_dubai_now`, `other_agent_status`, `contact_preference`, and `family_size`
must be adopted incrementally without pretending missing data is known.

## Integration Points

| Area | Current behavior | Proposed integration | Risk | Recommended ticket |
| --- | --- | --- | --- | --- |
| Agent dashboard conversation/buyer payload | `/api/v1/agent/dashboard`, `/agent/buyers`, and buyer card expose existing summaries, qualification fields, hot-list score, tasks, drafts, and `needs_reply`. | Compute `DealReadinessProfile` from `effective_fields()` plus conversation/listing context and expose a read-only `deal_readiness` object. Do not change sort order, task creation, draft text, or frontend UI in the first pass. | Low: internal surface only, but tenant visibility and payload compatibility must be tested. | DAL-173C1 |
| Buyer profile qualification adapter | `buyer_profiles.py` stores provenance-tracked qualification fields and returns `effective_fields()`. It does not normalize them into readiness input. | Add a narrow adapter that flattens `effective_fields()` to readiness input and records which values were confirmed vs inferred for display. No new columns. | Low: read-only if the adapter does not write or expand extraction. | DAL-173C1 |
| Chatbot next-question planning | Chatbot prompt/rules and branches decide whether to ask qualification questions. `response_validator.py` also strips many reflexive closers. | Use `DealReadinessProfile.next_best_action` only as a planner input for one conversational next question per turn. Keep send policy, escalation policy, and tone unchanged until tests cover each changed turn. | Medium: buyer-facing wording can shift and validators can strip questions if not coordinated. | DAL-173C2 |
| Chatbot Dubai fee/process answers | `prompt_builder.py` and deterministic branches in `chatbot_engine.py` can answer DLD, fees, off-plan, ready-resale, NOC, mortgage, occupancy, and transfer/process questions from hardcoded logic or prompt context. | Route Dubai process/fee/off-plan/ready-resale claims through `VerifiedFactRegistry`. Direct answers require `RuntimePolicy.DIRECT` plus context match; missing, stale, transaction-specific, or draft-only facts must draft/escalate or safely decline. | High: buyer-facing regulatory/process claims and existing deterministic shortcuts can conflict. | DAL-173C3 |
| Response validation safety gate | Validator strips unsupported yield and developer puffery, but it does not know whether a Dubai process/fee claim came from a verified fact. | Add a final unverified-claim guard for exact Dubai process/fee/timeline claims. It should block or rewrite unsupported claims rather than repair them into new facts. | High: false positives can degrade valid answers; false negatives permit hallucinated claims. | DAL-173C3 |
| Draft generation | Hot-list stale follow-ups, first-touch nudges, manual draft templates, and post-viewing drafts are review-only, except lead first-touch is template-locked auto-send. | Use DealReadiness missing fields to choose draft intent/ask, and use Verified Facts only to add source-tagged agent-review snippets. Draft text remains review-only and must never bypass existing approval flow. | Medium: drafts can still be sent by agents, so fact source and wording must be visible. | DAL-173C4 |
| Agent answer assist / escalation inbox | Escalation threads expose questions, buyer/listing context, and relay token metadata. Agents currently compose replies without verified-fact suggestions. | Show fact-backed answer snippets and readiness context as agent-facing assist only. Each snippet must carry source label/ref and runtime policy. No auto-send. | Medium: agent trust depends on sources; tenant-scoped facts must not leak. | DAL-173C4 |
| Lead ingest qualification | Portal ingest parses lead source/name/phone/message, attaches listing/conversation, and sends a template-locked first touch. Nudge drafts are review-only. | Map parsed portal message fields into readiness read-only context later. Do not change first-touch templates, consent handling, suppression, dead-letter handling, or auto-send timing. | High: lead ingest includes the only auto-send exception. | DAL-173C5 |
| Hot-list scoring and ranking | `hot_list.score_conversation()` uses message recency, offers, viewing intent, financing signals, budget, stale state, and summary keywords to create assignments/tasks/drafts. | Later, map readiness score/stage into the hot-list explanation and eventually ranking after observation. First adoption should be shadow/read-only metadata before changing `urgency_score` or sort. | High: changes agent daily queue order and draft/task creation. | DAL-173C6 |
| Off-plan vs ready explanations | Current chatbot branches distinguish ready vs off-plan using listing/property status and SPA/payment schedule. | Verified Facts should provide only general source-backed process facts; listing-specific terms still come from the listing record or documents. Never generalize listing-specific facts across stock. | High: overgeneralization can create compliance and trust issues. | DAL-173C3 |

## Guardrails

- Source/citation enforcement: every Verified Fact used in runtime must carry
  `source_label` and either `source_ref` or `source_url`.
- Runtime policy enforcement: only `direct` facts can be stated autonomously, and
  only when the live listing/context matches.
- Fail closed: missing, stale, ambiguous, transaction-specific, draft-only, or
  listing-specific-mismatch facts must not become buyer-facing claims.
- Never invent Dubai process, DLD/RERA, NOC, mortgage, tax/VAT, legal, timeline,
  service-charge, or fee claims when no verified fact covers the answer.
- Preserve tenant/global separation: tenant facts require exact brokerage match;
  global facts must not carry brokerage-specific values.
- Listing-specific facts stay listing-specific. Do not apply the Emaar Oasis
  resale-premium note or any listing/document-derived claim to unrelated stock.
- Readiness questions should feel conversational, not like a form. Ask at most
  one missing field per buyer-facing turn.
- Do not ask for information already present or confirmed. Confirmed
  qualification beats inferred qualification.
- No autonomous send behavior changes in early adoption. First-touch templates,
  WhatsApp relay sends, escalation sends, and draft approval flows remain as-is.
- No hot-list ranking changes until readiness is observed in read-only mode and
  covered by ranking regression tests.
- Buyer-facing tone must not change incidentally. Any chatbot wording change
  needs focused snapshot/regression tests.
- Verified Facts may guide draft/assist output before direct buyer-facing output,
  but draft consumers must see source labels and policy.
- The response validator must block unsupported claims without manufacturing a
  replacement fact.
- No DB migrations for the first integration. Recompute readiness from existing
  profile/conversation/listing state.

## Recommended Split

### DAL-173C1 — DealReadiness Read-Only Dashboard/API Snapshot

Expose a computed `deal_readiness` object on backend dashboard/buyer payloads
using existing buyer profile fields and conversation/listing context.

- Allowed: backend API/dashboard serializers, a small readiness input adapter,
  focused tests.
- Forbidden: frontend changes, chatbot behavior, hot-list ranking, draft text,
  lead ingest, WhatsApp send, migrations.
- Tests: tenant visibility, payload compatibility, confirmed-over-inferred input,
  missing-field behavior, no ranking/sort changes.

### DAL-173C2 — DealReadiness Chatbot Next-Question Planning

Use `DealReadinessProfile.next_best_action` to pick one qualification question in
chatbot planning, without changing send policy or escalation policy.

- Start only after C1 proves the computed profile is stable.
- Add tests for one-question-per-turn, no re-ask of known fields, validator
  compatibility, and no autonomous sends.

### DAL-173C3 — Verified Facts Chatbot Grounding For Dubai Process/Fee Answers

Gate Dubai process, fee, off-plan/ready, NOC, mortgage, DLD/RERA, and timeline
answers through `VerifiedFactRegistry`.

- Start with narrow intent categories and direct facts only.
- Add tests for direct, draft-only, do-not-state, listing-specific mismatch, and
  missing-fact fail-closed behavior.
- Refactor deterministic branches only where a fact-backed replacement and tests
  exist.

### DAL-173C4 — Draft And Agent-Assist Integration

Use Verified Facts and DealReadiness in review-only drafts and agent-facing assist
snippets.

- Drafts can suggest the next readiness question or include source-backed context.
- Agents must see sources and policy labels for fact snippets.
- Existing approval/edit/send machinery remains the only send path.

### DAL-173C5 — Lead-Ingest Readiness Mapping

Map portal lead message content and listing context into readiness read-only
context after C1/C2 are stable.

- Do not change first-touch template text, timing, consent evidence, suppression,
  dedupe, dead-letter behavior, or notification policy.
- Any qualification extraction expansion must preserve provenance and
  confirmed-over-inferred rules.

### DAL-173C6 — Hot-List Scoring Integration

Use DealReadiness in hot-list scoring only after read-only observation.

- First add shadow metadata/explanations without changing `urgency_score`, task
  creation, due dates, draft creation, or sort.
- Ranking changes require a separate, explicitly reviewed PR with before/after
  fixtures.

## First Safe Implementation

The first implementation PR should be **DAL-173C1 — DealReadiness Read-Only
Dashboard/API Snapshot**.

Reason: it uses the already pure helper, touches only internal agent-facing
payloads, can be tested for tenant isolation and payload compatibility, and does
not change buyer-facing chatbot text, WhatsApp send behavior, lead ingest,
draft generation, hot-list ranking, or frontend rendering.

## Do Not Touch Yet

- Chatbot runtime behavior and prompt wording.
- WhatsApp send behavior, including first-touch and relay sends.
- Hot-list ranking, assignment score, task creation, due dates, and draft creation.
- Lead-ingest parsing, first-touch templates, suppression, dedupe, consent
  logging, and dead-letter handling.
- Frontend rendering or dashboard redesign.
- DB migrations or new persisted readiness fields.
- RLS/DAL-170E, DB roles, session context, or production DDL.
- DB-backed tests for this design branch.

## Next Prompt

```text
Implement DAL-173C1 DealReadiness read-only dashboard/API snapshot.

Start only after DAL-173C integration plan is merged and cleaned up.

Branch:
dal-173c1-deal-readiness-dashboard-readonly

Goal:
Expose DealReadinessProfile as a read-only computed backend payload for agent
workspace surfaces so agents can inspect readiness without changing chatbot,
draft, lead-ingest, WhatsApp send, hot-list ranking, or frontend behavior.

Scope:

* Backend API/dashboard serializers only.
* Add a narrow adapter from buyer_profiles.effective_fields() to
  app/core/deal_readiness.py input.
* Existing /api/v1/agent/dashboard conversation/buyer payloads and/or buyer card
  payloads only.
* No frontend changes.
* No schema changes or migrations.
* No chatbot runtime or prompt changes.
* No hot-list scoring/ranking/task/draft changes.
* No lead-ingest or WhatsApp send changes.
* No DB-backed tests unless explicitly verified safe.

Expected behavior:

* Compute a deal_readiness object from existing buyer/profile fields and optional
  conversation/listing context.
* Include stage, missing_fields, next_best_action, next_best_action_reason,
  score, priority_band, and present_fields.
* Preserve confirmed-over-inferred qualification semantics by using
  effective_fields().
* Preserve tenant isolation and conversation visibility.
* Preserve existing dashboard sorting, hot-list scores, tasks, drafts, and payload
  compatibility.

Allowed files:

* app/api/agent_dashboard.py
* app/api/agent.py only if buyer card/list payload needs the same read-only field
* app/core/buyer_profiles.py only for a small read-only adapter if needed
* focused tests for dashboard/API serialization
* BACKLOG.md narrow note

Forbidden:

* app/core/chatbot_engine.py
* app/core/prompt_builder.py
* app/core/response_validator.py
* app/core/hot_list.py ranking/scoring behavior
* app/core/lead_ingest.py
* WhatsApp send paths
* frontend
* migrations
* RLS/DAL-170E or DB role/session infra

Run:

* compileall on touched Python
* focused dashboard/API serialization tests
* DealReadiness tests
* Avoid external Neon DB unless explicitly verified as safe

Final output:

# DAL-173C1 DealReadiness Dashboard Snapshot

## Verdict

Complete / Blocked / Complete with Follow-ups

## Branch

Name:
Commit:

## Files Changed

List files.

## What Changed

Summarize read-only payload and adapter behavior.

## Tests

Compileall:
Dashboard/API:
DealReadiness:

## Out of Scope Confirmed

Confirm no chatbot runtime, prompt, WhatsApp send, hot-list ranking, lead ingest,
frontend, migrations, RLS/DAL-170E, or DB-backed unsafe tests.

Merge-gate:
Review read-only. Confirm deal_readiness is computed from existing scoped data,
tenant filtering is preserved, existing dashboard sorting/ranking/drafts are
unchanged, helper remains pure, and no forbidden runtime wiring slipped in.
Recommendation: Merge / Do not merge.
```
