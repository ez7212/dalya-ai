# Plan — Agent Community Research Review + Per-Agent Overrides

## Goal / user story
As an agent, I want to **review the community research** for a project I have listings in, and **correct facts for my own buyers** (e.g. "Golf Grove has 166 units"), where my corrections:
- apply to **all my current and future listings in that community**,
- are **private to me** — never change the shared research and never reach another agent or brokerage,
- **take precedence** over the shared community KB in the buyer-facing advisor's answers.

## Scope decision (confirmed with Eric)
- Override scope = **(brokerage_id + agent_user_id + community_key)**. One correction covers every listing that agent has in that community, now and later (the bot matches by `community_key` at answer time, so future listings are automatically covered).
- Not per-listing. Not shared/global. Not cross-agent.

## Current state (verified in codebase)
- `DBCommunityResearch` (`app/models/db_models.py:1043`) is **platform-wide** (project_name+developer unique); approved KB JSON lives in `knowledge_base/` and is loaded via the alias index in `app/core/community_data.py`. Approved data is copied onto `DBListing.community_data` for matching listings.
- Admin-only review/approve at `app/api/research.py` (`/admin/research*`, `/admin/knowledge-base*`) + `frontend/.../admin/knowledge-base/`. **Agents have no view today.**
- `DBAgentCommunityRemark` (`db_models.py:588`) already exists at exactly the target scope `(brokerage_id, agent_user_id, community_key)` and is injected into the bot prompt as "AGENT PRIVATE NOTES" (`app/core/prompt_builder.py:770`, `chatbot_engine.py:1205`) — but it is **free-form text**, not structured field corrections.
- Bot source precedence today (highest→lowest): unit_profile → `DBListingFact` (buyer_safe) → agent remarks → community KB → seller Q&A → docs. The model weighs by trust label; there is no hard field replacement.

## UX model (confirmed with Eric)
Show **all the community research, field by field, in a structured layout**. Each field renders the researched value (read-only) with an **inline "Override" toggle**; when enabled, the agent types custom text that replaces that field **for their buyers only**. No separate "add a correction" list — the override lives next to the fact it corrects. This means overrides are keyed to a **specific research field**, not a free-form label.

## Design

### 0. Community field catalog (the structuring layer)
The KB JSON is deeply nested, so we need a curated **field catalog** mapping the buyer-relevant fields to stable keys + labels + a read accessor into the KB:
- A server-side list, e.g. `COMMUNITY_FIELDS = [{ key: "total_units", label: "Total units", path: "master_development.overview.total_residential_units", group: "Overview" }, { key: "completion_date", label: "Completion date", path: "...", group: "Overview" }, { key: "price_range_3br", label: "3BR price range (AED)", path: "...", group: "Pricing" }, ...]`.
- Grouped by section (Overview, Pricing, Payment plan, Amenities, Location, Schools, Investment) for the UI.
- `GET /listings/{id}/community` resolves each field's researched value from the listing's approved KB via these paths, returning a flat, ordered list of `{ key, label, group, researched_value, override }`.
- Stable keys decouple overrides from KB JSON shape changes; if the KB lacks a field, it renders "Not in research" and is still overridable.

### 1. Data model — per-field agent overrides
Add `DBAgentCommunityOverride` (sibling to `DBAgentCommunityRemark`, same scope):
- `override_id` (pk)
- `brokerage_id`, `agent_user_id`, `community_key` — scope key (index on all three)
- `field_key` (text, stable key from the field catalog, e.g. "total_units")
- `value_text` (text — the agent's custom value, e.g. "166 units")
- `note` (optional text — why / source)
- `buyer_safe` (bool, default true) — whether the advisor may state it to buyers
- `created_at`, `updated_at`
- Unique on (brokerage_id, agent_user_id, community_key, field_key) → one override per field per agent per community; toggling off = delete row (or `enabled` flag).

Rationale for a new table: per-field corrections with their own buyer_safe flag, cleanly joined onto the catalog for the structured view, reusing the proven `(brokerage, agent, community)` scope + bot matching of the remark layer. Free-form `DBAgentCommunityRemark` stays as-is for general notes.

### 2. Backend endpoints (agent-facing, brokerage-scoped)
All require an active brokerage member; all scoped to the caller's `user.id` + resolved brokerage. Reuse `_get_scoped_listing` / brokerage-context helpers.

- `GET /api/v1/listings/{id}/community` → resolve the listing's project/community to its approved community research (read-only digest: project name, unit/price/amenity/location highlights, confidence, source count, audit_flags), **plus** the caller's existing overrides for that community_key. If no approved research exists, return status (`needs_review` / `none`) so the UI can say so honestly.
- `GET /api/v1/agent/communities/{community_key}/overrides` → list caller's overrides for that community.
- `POST /api/v1/agent/communities/{community_key}/overrides` → create `{field_label, value_text, note?, buyer_safe?}`.
- `PATCH /api/v1/agent/communities/{community_key}/overrides/{override_id}` → edit.
- `DELETE /api/v1/agent/communities/{community_key}/overrides/{override_id}`.

`community_key` derives from the listing exactly as `DBAgentCommunityRemark` matching does (listing.community). Reject writes where the caller has no listing in that community (prevents arbitrary community edits) — optional guard, decide in review.

### 3. Bot wiring (precedence)
- Load the assigned agent's `DBAgentCommunityOverride` rows for the listing's `community_key` (same match condition already used for remarks: `assigned_agent_id == agent_user_id AND listing.community == community_key AND brokerage matches`).
- Inject as a distinct **"AGENT-VERIFIED CORRECTIONS (highest trust for this agent)"** block in `prompt_builder`, positioned **above the community KB section** and instructed to override conflicting community-KB values. Only `buyer_safe=true` rows are stated to buyers; others are internal-only context.
- Keep free-form `DBAgentCommunityRemark` behavior unchanged.

### 4. Frontend (agent surface) — structured field list with inline overrides
- Add a **"Community Data"** tab in the listing workspace (`/listings/[id]/community`, consistent with the route-backed workspace tabs).
- Header: project name, confidence badge, source count, and empty states ("not researched yet" / "in review"). Agents cannot approve (admin-only).
- Body: the **field catalog rendered group by group** (Overview, Pricing, Payment plan, Amenities, Location, Schools, Investment). Each row:
  - Field label + **researched value** (read-only).
  - An **"Override" toggle**. Off = the advisor uses the researched value. On = reveal a text input (prefilled with the researched value as a starting point) for the agent's custom value, plus an optional note and a `buyer_safe` toggle.
  - A subtle "overridden" indicator + a reset/clear to remove the override.
- Persistent banner/footnote: **"Overrides apply to all your {Community} listings — now and future — and are private to you. Other agents are not affected."**
- Save per-field (PATCH on toggle/edit, DELETE on clear) so it feels live, like the facts panel.
- Reuse `ListingKnowledgeWorkspace` / `ListingKnowledgeFactsPanel` styling (light/slate, FormSection patterns, sage/copper badges).

### 5. Access control / safety
- Overrides are strictly scoped to caller's `user.id` + brokerage; never readable/writable cross-agent or cross-brokerage (mirror `DBAgentCommunityRemark` access).
- Agents can **never** edit `DBCommunityResearch` or approved KB files (those stay admin-only).
- `buyer_safe=false` corrections inform the agent/advisor internally but are not stated to buyers (consistent with verified-facts gating).
- PII / unsafe-claim gating: corrections flow through the same buyer-safe posture as facts.

## Out of scope (first pass)
- No per-listing-level override (only per-community, per Eric).
- No agent ability to approve/trigger platform research.
- No field-path mapping into the nested KB JSON (corrections are labeled key/value injected as high-trust context, not structural JSON patches).
- No admin moderation of agent overrides.

## Verification
- Backend pytest: override CRUD is brokerage+agent scoped; cross-agent/cross-brokerage read/write denied; override surfaces only for listings whose assigned agent + community match.
- Bot test: with an override "Total units = 166" for agent A's Golf Grove, a buyer asking unit count on agent A's Golf Grove listing gets 166; the same question on agent B's Golf Grove listing (no override) gets the shared KB value; shared `community_research` row unchanged.
- Frontend: tsc/lint/build; agent can view research digest, add/edit/delete a correction, see the "applies to all your {community} listings / private" messaging; empty/needs-review states render.

## Resolved decisions (Eric)
1. **Dedicated "Community Data" tab** at `/listings/[id]/community` (route-backed workspace tab).
2. **Guard ON** — overrides are only allowed for communities where the agent currently holds a listing (reject writes otherwise).
3. **`buyer_safe` defaults to ON** — the advisor may state an override to buyers unless the agent turns it off.
