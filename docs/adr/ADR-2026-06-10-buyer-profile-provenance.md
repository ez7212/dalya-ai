# ADR — Buyer profile field-level provenance and the no-overwrite guard (DAL-164)

**Date:** 2026-06-10
**Status:** Accepted
**Linear:** DAL-164

## Context

Buyer context lived in conversation summaries. Agents need a structured
qualification snapshot (budget, financing, timeline, areas, beds, must-haves,
deal-breakers) at a glance — and they need to trust it. Trust requires two
properties: every value says where it came from, and an agent's correction is
final until the agent changes it. An AI inference silently overwriting a
value an agent confirmed on a phone call is exactly the kind of betrayal that
kills adoption.

## Decision

### Profiles are brokerage-scoped

`brokerage_buyer_profiles` is keyed `(brokerage_id, normalized phone)`. One
profile spans the buyer's conversations within a brokerage; the same phone at
two brokerages is two independent profiles. That is the tenant boundary — the
cross-brokerage intelligence graph is a Phase 2 strategic question, not an
MVP data model.

### Qualification is field-level rows, not columns

`buyer_profile_fields` holds one row per `(profile_id, field, provenance)`
with `value`, `confidence`, `source_message_id`, `confirmed_by`, timestamps —
audit-friendly and enforceable per field.

### The no-overwrite guard is structural, not a prompt instruction

Provenance is part of the row key (`UNIQUE (profile_id, field, provenance)`),
and the AI write path (`record_inferred_field`) filters
`provenance = 'ai_inferred'` in its upsert — an `agent_confirmed` value is
physically a different row that the inference path cannot reach. There is no
code path from model output to a confirmed row; only `confirm_field` (an
agent action, compliance-logged) writes those.

A conflicting inference therefore *coexists* with the confirmed value, and the
card surfaces it as a suggestion chip ("buyer mentioned 1.8M — update
confirmed budget of 2M?") that only an agent action promotes.

### Reads prefer confirmed-over-inferred

`effective_fields` resolves each field to the confirmed row when one exists,
else the inferred row, and attaches the differing inference as `suggestion`.
Hot-list scoring and the post-viewing follow-up grounding read through this
same resolution.

### Extraction runs on the message-processing path

The Haiku-tier intent classifier already extracts budget; a deterministic
rules layer adds financing/timeline/bedrooms signals. Both write
`ai_inferred` rows with the source message anchored. A backfill
(`scripts/migrate_buyer_profiles_offers.py --backfill`) seeds profiles from
existing conversations.

## Alternatives considered

- **Columns on the profile with a `confirmed_fields` JSON list:** the guard
  becomes application discipline over shared columns — exactly the
  prompt-instruction-grade enforcement the spec forbids.
- **DB trigger rejecting AI updates to confirmed values:** strongest at the
  engine level but couples migrations to trigger DDL across environments;
  the provenance-keyed row split achieves unreachability with plain
  constraints. Revisit if a second write path to confirmed rows ever appears.

## Consequences

- The card can always answer "why does it say this?" — every value carries
  provenance, confidence, and a source-message link.
- PDPL display rules: phone is masked on list surfaces, full on the card
  (agent-scope), opt-out status disables send CTAs.
- DAL-165 offers and viewing/feedback histories render from their source
  tables — read views, no duplicated state.
