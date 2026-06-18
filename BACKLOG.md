# Dalya — Backlog

*Last updated: 2026-06-17 (`DAL-169` P0 production security hardening shipped)*

This document is split into two parts, mirroring [FEATURES.md](./FEATURES.md):

1. **[Dalya B2B Platform backlog](#dalya-b2b-platform-backlog-current-focus)** — what we're building now. Priority order is now the launch-critical MVP completion sequence in [`MVP_ROADMAP_0609.md`](./MVP_ROADMAP_0609.md).
2. **[Mahoroba consumer-direct backlog (legacy)](#mahoroba-consumer-direct-backlog-legacy)** — what was queued for the original consumer-direct strategy. Some items are still applicable (engine-layer improvements, regulatory tooling, multilingual extensions); some are not (seller self-onboarding for direct listing, asking-price formatting decisions for buyer-facing listing cards, etc.). Each item is annotated for B2B applicability where the call is non-obvious.

---

# Dalya B2B Platform backlog (current focus)

## MVP feature set for Luqman's design partnership

The product frame remains four blocks, but the launch roadmap is now more concrete:

1. **24/7 Inquiry Concierge.** EN/AR/RU/HI inquiry handling, buyer qualification, voice-note transcription, document-grounded property info, and agent-authored inspection notes. Mandarin is deferred until after MVP.
2. **Smart Escalation to Agents.** Brokerage AI escalates serious or unanswerable buyer questions to Agents AI, and agents can answer through WhatsApp token relay or the dashboard.
3. **Morning Hot List + Follow-Up Engine.** Automatic morning queue refresh, ranked conversations, deduped tasks, and review-only draft follow-ups.
4. **Viewing Logistics Automation + Pre-Viewing Report.** Ready-property logistics, slot proposal, buyer/tenant confirmation, Google Calendar, reminders, pre-viewing brief, and post-viewing feedback.

Canonical launch roadmap: [`MVP_ROADMAP_0609.md`](./MVP_ROADMAP_0609.md).

### Agent operating instructions and reviewer infrastructure

1. [x] **DAL-167: Verify and route Dalya reviewer agents.** Added `dalya-reviewers/file-routing.md` so Chatbot Master, Real Estate Guru, UX Designer, and Security Researcher have concrete backend/frontend/test/report scopes to inspect; wired it into reviewer commands, root instructions, installed `.codex/agents`, installed `.claude/agents`, and adapter templates. Confirmation: all four reviewer definitions are present and readable, and installed definitions now point to the shared routing map.
2. [x] **DAL-168: Align AGENTS.md with B2B brokerage platform direction.** Replaced the stale pre-pivot Mahoroba/off-plan marketplace context in root `AGENTS.md` with the current B2B AI infrastructure direction: brokerages as customers, agents as daily users, buyers as bot-consumed leads, `/agent` as the active workspace, and consumer-direct surfaces as legacy/maintenance unless explicitly requested. Removed the duplicate stale Dalya/Mahoroba first-turn identity block.
3. [x] **DAL-169: P0 production security hardening.** Added production-safe route gates for debug/admin/test surfaces (`/admin-dashboard`, SPA parse retrieval, WhatsApp send-test routes) and reduced production `/health` detail; made missing environment markers fail safe as production; made Twilio and lead-ingest verification fail closed in production; blocked production simulated/360dialog transports and unconfigured Twilio sends; added inbound provider replay ledger for Twilio `MessageSid` and lead-ingest provider IDs/payload fingerprints with failed/stale-processing retry support; added cross-tenant authorization regression coverage and same-brokerage target validation for share/reassign; added PII redaction for logs touched by these flows. Verification: `venv/bin/python -m compileall app scripts/migrate_inbound_provider_events.py tests/test_security_p0_hardening.py`; `PYTHONPATH=/Users/eric/dalya-ai venv/bin/python -m dotenv -f .env.test run -- venv/bin/python scripts/migrate_inbound_provider_events.py`; `venv/bin/python -m dotenv -f .env.test run -- venv/bin/python -m pytest tests/test_security_p0_hardening.py -q` (14 passed); broader regression `tests/test_lead_ingest.py tests/test_voice_note_flows.py tests/test_smart_escalation_relay.py tests/test_conversation_takeover.py tests/test_security_p0_hardening.py` (52 passed). Security Researcher final review: merge ready with follow-up tickets, no P0 blockers.

### Final MVP completion order

1. [x] **DAL-149: Dashboard reply composer.** Added dashboard reply path for escalation threads while keeping `[Ref: TOKEN]` WhatsApp relay intact. Verification: `tests/test_escalation_inbox_api.py` + `tests/test_smart_escalation_relay.py`; frontend `npm run build`.
2. [x] **DAL-150: Draft approval queue.** Added `/agent/drafts` so agents can edit/send/reject/snooze AI follow-up drafts and open the underlying conversation. Verification: `tests/test_draft_queue_api.py`; frontend `npm run build`.
3. [x] **DAL-151: Scheduled hot-list refresh.** Added persisted refresh runs, scheduled-run script, stored refresh status, and manual refresh UI/API. Verification: `tests/test_morning_hot_list.py`; frontend `npm run build`.
4. [x] **DAL-152: Ready property intelligence layer.** Added ready-property document upload/parsing, extracted facts, buyer-safe knowledge summary, verification UI, and prompt grounding. Verification: `tests/test_ready_property_knowledge.py`; frontend `npm run build`; migration `scripts/migrate_ready_property_knowledge.py`.
5. [x] **DAL-153: Google Calendar integration.** Added Google Calendar provider abstraction, OAuth URL/callback endpoints, token-ref connection settings, free/busy filtering, viewing event create/update/delete, `/agent/calendar`, and fake-provider regression coverage. Verification: `tests/test_viewing_logistics.py`; frontend `npm run build`.
6. [x] **DAL-154: Tenant WhatsApp confirmation flow.** Added tenant confirmation records, approved tenant notice sending, webhook reply handling for confirm/reschedule/decline/free-text, agent notification, viewing state updates, and viewing-detail controls. Verification: `tests/test_viewing_logistics.py`; frontend `npm run build`; migration `scripts/migrate_tenant_viewing_confirmations.py`.
7. [x] **DAL-155: Viewing logistics completion.** Added approved buyer/reminder/running-late/reschedule sends, viewing completion API/job, compliance/actions, and post-viewing task/draft trigger. Verification: `tests/test_viewing_logistics.py`; frontend `npm run build`.
8. [x] **DAL-156: Post-viewing capture.** Added `viewing_feedback`, due feedback request API/job, buyer WhatsApp reply capture, agent feedback form, structured parsing, hot-list/task updates, and viewing-detail feedback summaries. Verification: `tests/test_viewing_logistics.py`; frontend `npm run build`; migration `scripts/migrate_viewing_feedback.py`.
9. [x] **DAL-157: Agent performance dashboard.** Added `/agent` current-agent performance block for today/7d/30d: buyer conversations, escalations handled, response time, follow-ups, viewing funnel, offers, hot leads, and overdue tasks. Verification: `tests/test_morning_hot_list.py`; frontend `npm run build`.
10. [x] **DAL-143: WhatsApp/BSP production verification.** Produced `reports/whatsapp_production_readiness_20260610.md`; Twilio Brokerage AI / Agents AI flows, dashboard reply, tenant viewing flow, opt-out, and duplicate-webhook protection are verified. 360dialog BSP remains blocked because the transport is intentionally stubbed pending WABA approval/implementation.

Resist building broad. These ten items are the MVP; owner outreach/campaigns, AI buyer matching, Mandarin production support, and owner dashboards are deferred.

### MVP gap-closure sequence (`GOAL_SPEC_0610`)

Eight workstreams closing the gaps from the June 10 MVP review, ordered by agent-visible impact. Ticketed in Linear on 2026-06-10 under the **MVP Gap Closure** label; full behavior specs, data models, edge cases, and per-ticket verification checklists live in [`GOAL_SPEC_0610.md`](./GOAL_SPEC_0610.md) and on each Linear issue. Logistics building-level inheritance is explicitly out of scope. Per the one-change-set-per-run discipline, each ticket is an independent change-set with its own verification checklist.

**P1 — day-one failures an agent sees on real traffic:**

1. [x] **DAL-158: Live conversation takeover (pause/resume AI).** Shipped 2026-06-10: `ai_mode` on conversations with dashboard toggle (`/agent/conversations/[id]` + escalation inbox rows) and WhatsApp `TAKEOVER`/`RESUME` quote-reply keywords; raw forwards to Agents AI while paused (debounce-window messages included); draft auto-snooze with reason `takeover` + hot-list draft suppression; compliance events per transition; cross-tenant token isolation. Verification: `tests/test_conversation_takeover.py` (12 passed) + relay/threading/hot-list/inbox/draft/cross-tenant regression (36 passed); `frontend npm run build`; migration `scripts/migrate_conversation_ai_mode.py`. *(Linear: Done)*
2. [x] **DAL-159: Voice note handling in buyer + agent flows.** Shipped 2026-06-10 (option B1): language auto-detect + confidence on the transcription service; `transcription_*` fields on the message record; agent voice quote-replies deliver as text with confidence-gated `SEND` holds (`agent_voice_reply_holds`); 🎙 provenance on escalation envelopes; `media_unprocessable` fallback + escalation for failures/video — never silent; RTL `dir="auto"` on timelines. **Deliberate harness re-baseline: 30/30 personas, 0 issues; new thread baseline 27.1% append / 28.6% bundle / 42.9% bypass** (`reports/chatbot_test_2026-06-10_dal159_rebaseline/`). Verification: `tests/test_voice_note_flows.py` (11 passed) + 49 regression tests; migration `scripts/migrate_voice_note_handling.py`. *(Linear: Done)*
3. [x] **DAL-160: Outbound media via dashboard composer.** Shipped 2026-06-10: `media_assets` storage layer (brokerage-scoped refs, sha256) + `/media` static mount; per-transport size limits in the transport layer (16 MB / 5 MB images); 24h session-window block with 409 + reopen surfacing; multipart media endpoint (≤10 files, all-up-front validation), attach-from-listing without re-upload, listing assets endpoint; composer UI on conversation detail + escalation reply attachments; timeline file chips; compliance event per media send. Verification: `tests/test_media_composer.py` (6 passed); `frontend npm run build`; migration `scripts/migrate_media_assets.py`. *(Linear: Done)*
4. [x] **DAL-161: Outbound media via WhatsApp agent relay.** Shipped 2026-06-10: `app/core/relay_media.py` four-tier routing (caption `#TOKEN` → quote-reply ref session → 10-min session held 30s with UNDO → exactly-one `media_requested` escalation), parked-media burst batches with numbered-option prompts + 30-min expiry, forwarded-caption stripping (PDPL), per-item 24h window bounces with deep links, `media_requested` set at classification time, routing method on every compliance event, agent-scoped token lookups. ADR `docs/adr/ADR-2026-06-10-relay-ref-sessions.md`. Verification: `tests/test_relay_media.py` (21 passed); migration `scripts/migrate_relay_media.py`. *(Linear: Done)*

**P2 — fill the funnel, keep the agent informed without polling:**

5. [x] **DAL-162: Agent notification framework.** Shipped 2026-06-10: `app/core/agent_notifications.py` 13-event catalog, `agent_notifications` table with dedupe keys, deep links, per-agent quiet hours (22:00–07:00 GST, brokerage-timezone aware) + per-event on/off (`/api/v1/agent/notification-preferences` + settings UI), 20/hr rate guard with single overflow collapse, morning digest (drafts pending + takeover >48h ride along with the scheduled hot-list refresh), suppressed events recorded never dropped. Wired: escalations, lead first-touch, hot-buyer reply (≥70 band), tenant confirmations, opt-outs, AI failures. Verification: `tests/test_agent_notifications.py` (7 passed); migration `scripts/migrate_agent_notifications.py`. *(Linear: Done)*
6. [x] **DAL-163: Portal lead ingestion + AI first-touch.** Shipped 2026-06-10: `app/core/lead_ingest.py` with `LeadIngestAdapter` + versioned PF/Bayut email parsers, secret-guarded `POST /api/v1/leads/ingest/email`, slug-scoped tenant boundary, dead-letter queue with notification, listing resolution (source_url → permit → fuzzy-flagged → unresolved-still-routed), template-locked auto first-touch with consent-basis compliance evidence, 48h review-only nudge drafts, STOP propagation. ADR `docs/adr/ADR-2026-06-10-first-touch-template-exception.md` (utility + marketing template variants drafted — **WABA submission remains the external dependency**). Open question #1 (Luqman's CRM) still gates a second adapter. Verification: `tests/test_lead_ingest.py` (10 passed); migration `scripts/migrate_lead_ingest.py`. *(Linear: Done)*

**P3 — structured-data layer that compounds (164+165 land together):**

7. [x] **DAL-164: Buyer card & buyer list view.** Shipped 2026-06-10: `brokerage_buyer_profiles` keyed (`brokerage_id`, phone) — tenant boundary; field-level `buyer_profile_fields` with `ai_inferred`/`agent_confirmed` provenance where the AI write path physically cannot reach confirmed rows (provenance-keyed uniqueness — the structural no-overwrite guard); suggestion chips on conflicts; extraction on the message path (classifier budget + rules for financing/timeline/beds) + backfill; `/agent/buyers` list (masked phones, chips, filters/sorts) + `/agent/buyers/[id]` card (full identity, provenance-tagged qualification, offer/viewing/feedback histories from source tables, opt-out banner). ADR `docs/adr/ADR-2026-06-10-buyer-profile-provenance.md`. Verification: `tests/test_buyer_card_offers.py` (8 passed, incl. DB-level no-overwrite assertion + cross-brokerage field isolation); persona-path smoke run. *(Linear: Done)*
8. [x] **DAL-165: Offer log.** Shipped 2026-06-10: first-class `offers` with thread state machine (`draft_pending_confirm → submitted → countered → …`); offer escalations with extracted amounts create drafts anchored to the buyer's source message (no amount → no draft, no hallucination); agent confirm required before `submitted` (dashboard confirm/discard + manual log + counter/accept/reject transitions, all compliance-logged); offer strip on conversation detail + history on buyer card; hot-list boost prefers the structured record over message signals (single branch — no double count). Verification: `tests/test_buyer_card_offers.py`. *(Linear: Done)*
9. [x] **DAL-166: Post-viewing follow-up draft CTA.** Shipped 2026-06-10 behind `FEATURE_FOLLOWUP_DRAFT_CTA` (default off — CTA absent, endpoint 404): one CTA on received buyer feedback → review-only draft grounded on feedback + confirmed-only qualification + ≤3 same-brokerage alternatives (simple filter match, zero-match → plain follow-up, never padded); reuses the existing draft machinery, no new send paths. Verification: `tests/test_post_viewing_followup.py` (4 passed). *(Linear: Done)*

Open questions to answer before P2 starts (full list in the spec): Luqman's actual lead delivery path (decides DAL-163 Path 2), first-touch template variants (submit this week), voice reply mode B1 vs B2, relay hold window, hot-buyer push threshold, transcription confidence threshold, Twilio sandbox `Forwarded` flag availability.

### Marketing site

- [x] **DAL-178: Marketing site positioning fix + composition/proof/stats refresh.** Shipped 2026-06-18: removed all "Mahoroba Realty" references from the marketing surface (`frontend/src/app/(marketing)` + `components/marketing` + the two linked mockups), reworded to "each listing is operated by a RERA-licensed brokerage" since Dalya is software not the licensee. Design pass from a `/critique` review: Pillars section rebuilt as an alternating wide/narrow bento (breaks the uniform 3-up grid); pilot-scorecard stat row de-templated (`<60s / 1 list / Live` → honest measure→value cards, no non-numbers at big-number scale); illegible `scale(0.5)` pointer-events-none dashboard iframes replaced with crisp 2× screenshots via `next/image` (legible on mobile, no CLS, lazy, not falsely interactive) across homepage + agents + brokerages. Verification: `tsc --noEmit` clean, `eslint` clean, all 6 marketing routes 200, no horizontal overflow at 390/1440. *(Linear: Done)* Note: `.impeccable.md` is stale (describes retired navy/gold consumer design) — flagged for separate cleanup.
- [x] **DAL-179: Align marketing copy with current MVP.** Shipped 2026-06-18 (stacked on DAL-178): aligned all marketing copy to the actual four-block MVP (24/7 inquiry concierge, smart escalation, hot list + follow-up, viewing logistics) and removed deferred/unbuilt capabilities. Homepage Pillars: 6 cards → the 4 MVP blocks (added Smart Escalation, dropped Listing acquisition / Negotiation / Seller-side; removed dead snippet components). Per Eric's decision, removed owner-level analytics entirely: homepage Surfaces is now a single agent surface (was agent + owner dashboard), hero "revenue per agent" floating card → hot-list card, stat-row intro de-owner-ified. Brokerages page reframed around the agent MVP ("the sharpest version of every agent you have"): owner-analytics hero tiles → agent-workflow cards, owner-dashboard surface → agent surface, "metrics you check Monday" grid → "four workflows, every agent," removed `OfferRow`/`MetricIcon` helpers. how-it-works step 06 "Report" (owner analytics) → "Follow up" with a hot-list/drafts snippet; dropped seller-update + owner-view copy. Contact focus option "Listing acquisition" → "Serious-offer escalation". About principle reworded off revenue-per-agent. Verification: `tsc --noEmit` clean, `eslint` clean, all 6 marketing routes 200, no horizontal overflow at 390/1440. *(Linear: Done)*

## Foundation hardening (B2B-blocking)

Status: backend foundation complete for the current MVP. The next epics can build on these primitives without inventing their own access, compliance, aggregation, or brokerage-config rules. Remaining work is product-surface polish, not a blocker for Hot List / Smart Escalation / Viewing Logistics.

### 1. Universal brokerage scoping

- [x] Make brokerage scope explicit on agent-facing product rows and read paths. Listings are brokerage-wide; conversations are assigned/shared/private by thread.
- [x] Remove normal-route reliance on legacy defaults for agent/brokerage surfaces. Legacy fallback remains only for unresolved old chatbot listings.
- [x] Treat platform aggregation as a separate output path via `app/core/platform_aggregation.py`, with identifier checks before storage.

### 2. Auth and route enforcement

- [x] Back Supabase role checks with actual brokerage membership for the agent and brokerage surfaces.
- [x] Enforce brokerage scope and conversation visibility in protected route handlers.
- [x] Make `brokerage_id` the default context input for workspace APIs touched by the current MVP paths.

### 3. Compliance and audit layer

- [x] Propagate buyer opt-out across every agent in the same brokerage.
- [x] Log outbound messages, blocked sends, escalations, regulatory requests, conversation shares/reassignments, and brokerage-config updates in `DBComplianceEvent`.
- [x] Add the queryable backend audit trail that the owner-visible compliance surface will consume.

### 4. Safe aggregation layer

- [x] Define the anonymized platform-intelligence contract for pricing/community signals.
- [x] Strip and reject listing, buyer, brokerage, unit, phone, email, and agent identifiers before aggregate storage.
- [x] Require minimum sample size and at least two brokerages before cross-brokerage aggregate storage.

### 5. Brokerage configuration management

- [x] Make prompt config, managing-agent naming, fee framing, language defaults, dashboard URL, and handoff defaults brokerage-configurable.
- [x] Make prompt context and agent config endpoints consume the same typed runtime config.
- [x] Add owner/team-lead API support at `/api/v1/agent/brokerage/config` so brokerage setup is operational rather than manual-only.

### Remaining non-blocking foundation polish

- [ ] Build the owner-visible compliance dashboard surface on top of `DBComplianceEvent`.
- [ ] Add a scheduled aggregation job once the first MVP customers have enough volume for useful samples.
- [ ] Add a thin admin UI for brokerage config; backend API is complete.

## Pillar 1 — Buyer engagement extensions (new for B2B)

- [x] **Priority 4: Ready-property intelligence layer.** Built document upload/parsing, `listing_documents`, `listing_facts`, `listing_knowledge_summaries`, extracted fact verification, buyer-safe/internal summaries, missing facts, risk flags, and ready-property prompt grounding. MVP deterministic extraction supports title deed, Oqood, Ejari, tenancy contract, service charge statement, NOC, valuation, mortgage liability letter, floor plan, snagging report, DEWA/utility info, building rules, agent inspection notes, and seller disclosure notes.
- [x] **Voice-note transcription foundation.** Buyer sends a WhatsApp voice note → transcription → intent classification → response or escalation flows through the same engine. Live provider credential verification remains production hardening, not a separate MVP feature.
- [x] **Ready-property prompt branch.** Bot distinguishes off-plan-anchored questions from ready-anchored questions, receives unit profile plus buyer-safe extracted facts, prefers verified structured facts, and treats available ready-property facts as covering service-charge/occupancy/parking/view info-gap checks.
- [ ] **Deferred: Mandarin production support.** Keep EN/AR/RU/HI for MVP. Mandarin moves after launch-critical agent workflows.
- [ ] **Deferred: AI buyer matching launch surface.** Existing buyer preference and match scaffolding can remain, but do not productize AI buyer matching for MVP.

## Smart Escalation to Agents

Status: backend handoff loop is complete for the current MVP. Escalations route to the listing's managing agent through the brokerage's Agents AI number, and agent replies with the envelope reference now relay back to the buyer through the brokerage's buyer-facing number.

- [x] **Agents AI escalation route records.** Escalation alerts mint `DBAgentMessageRoute` rows with envelope tokens, listing, buyer, agent, tags, and 7-day expiry.
- [x] **Agent reply relay service.** `app/core/agent_relay.py` validates token, brokerage, agent phone, expiry, opt-out status, and destination before relaying text/media to the buyer.
- [x] **Webhook branch for Agents AI replies.** `/api/v1/whatsapp/webhook` detects messages sent to `agents_ai_number`, bypasses buyer debounce/chatbot processing, and runs the relay path.
- [x] **Timeline and audit persistence.** Successful relays are stored as `agent_relay` conversation messages, `DBLeadAction` rows, and `DBComplianceEvent` records; blocked attempts are compliance events.
- [x] **Threaded escalation inbox foundation.** Linear `DAL-132` through `DAL-136` delivered the MVP implementation: persistent `escalation_threads`, ordered `escalation_thread_questions`, deterministic category matching, append-only WhatsApp update messages that reuse the original `[Ref:]` token, one-agent-reply resolution semantics, and focused simulated-transport tests for multi-question escalation/reply timing.
- [x] **Escalation threading hardening.** Linear `DAL-137` added database-backed initial debounce, update debounce, offer/legal bypass, 24h timeout closure, buyer opt-out closure, thread isolation, question-cap formatting, and compliance events for thread create/append/update/resolve/timeout/opt-out.
- [x] **Escalation threading ADR and audit.** Linear `DAL-138` documented the Q1-Q18 product decisions in `docs/adr/ADR-2026-06-05-smart-escalation-threading.md` and the Q19-Q25 current-code audit in `docs/adr/AUDIT-2026-06-05-smart-escalation-threading.md`.
- [x] **Escalation threading harness and full-suite report.** Linear `DAL-139` expanded `tests/test_escalation_threading_harness.py` to cover debounce bundling, update token reuse, different-category split, resolution, stale-window recreation, bypass, opt-out, isolation, update-format assertions, and question caps. Verification artifact: `reports/escalation_threading_pytest/index.html`; full suite result: 183 passed, 1 skipped, 0 failed, 0 errors.
- [x] **Escalation threading race/compatibility fixes.** Linear `DAL-141` added duplicate-open-thread `IntegrityError` retry/refetch, locked keyword-first info-gap category mapping, removed BRN from immediate debounce bypass, cleared legacy pending questions after threaded sends, prevented successful threaded sends from falling through to legacy Telegram, and verified `thread_id = NULL` route relay compatibility. Verification: 18/18 focused escalation tests passing; report at `reports/escalation_threading_dal141/index.html`.
- [x] **Escalation threading final report refresh.** Linear `DAL-142` corrected the pytest HTML report's locked-decision bypass text and archived a fresh post-DAL-141 full-suite report. Verification: focused report `reports/escalation_threading_dal141/index.html`; full-suite report `reports/escalation_threading_full_20260606/index.html` with 189 passed, 1 skipped, 0 failures/errors.
- [x] **Linear `DAL-144`: handover-stub info-gap fix.** Tightened the off-plan handover shortcut so it only answers handover-first questions; yield/appreciation/service-charge gaps now reach info-gap threading, payment-left questions reach the remaining-payment branch, and document “review” no longer false-matches view/orientation. Verification: targeted report `reports/chatbot_threading_targeted_20260606_v3/index.html`; full baseline `reports/chatbot_threading_baseline_full_20260606/index.html`.

### Remaining Smart Escalation MVP work

- [x] **Priority 1: Dashboard reply composer.** Added `POST /api/v1/agent/escalations/{thread_id}/reply`, `/agent/escalations` and `/agent/conversations/[id]` composers, Send to Buyer, timeline persistence as `agent_relay`, compliance event, thread resolution, consumed-route blocking, and regression coverage for existing `[Ref: TOKEN]` relay.
- [ ] Add richer stuck-handoff monitoring for expired escalation routes with no agent response.
- [x] Add dashboard UI for escalation threads so agents can resolve, filter, and reply without relying only on WhatsApp quote-token preservation.
- [x] **Linear `DAL-140`: persona-level escalation threading metrics.** Extended the persona harness with run/persona CSV metrics and HTML panels for thread count, question count, average questions per thread, append rate, debounce bundle rate, bypass rate, timeout rate, category distribution, and false positive/negative thread checks. Verification: `tests/test_chatbot_full_test_output.py` 8/8 passing; targeted persona report at `reports/chatbot_thread_metrics_escalation_subset/index.html` with 2 threads across `offer` and `regulatory_documents`.
- [x] **Linear `DAL-145`: threading-specific persona controls and full baseline.** Added rapid-fees, post-alert follow-up, and cross-category threading personas; added debounce fast-forward hooks, end-of-persona simulated debounce flushing, and `CHATBOT_FULL_TEST_MAX_CONCURRENT`; fixed the live partial unique index so open `offer` threads are excluded from duplicate-open-thread protection. Verification: targeted report `reports/chatbot_threading_targeted_20260606_v3/index.html` with non-zero append/bundle rates; full 30-persona baseline at `reports/chatbot_threading_baseline_full_20260606/index.html` with 35 threads, 52 questions, append_rate `0.3269`, debounce_bundle_rate `0.3429`, bypass_rate `0.4286`.
- [x] **Linear `DAL-146`: residual baseline cleanup and re-run.** Full baseline completed 30/30 but still flagged residual checks. Triage found the current report's false negatives are not PDPL or affordability failures: PDPL deletion escalates correctly and affordability answers directly. The real residuals were stale route checks from pre-end-flush report generation, a Raj project-reference check that did not accept the valid short name "Shams", a Sara Return prior-offer continuity message being treated as a fresh offer, and direct-answer vs escalation expectation drift. The harness now flushes simulated debounced threads at persona end, accepts valid project short names, treats prior-offer follow-ups as continuity unless the buyer clearly revises/increases the offer, and allows parking to pass via either a direct villa-parking answer or escalation. Verification: `reports/chatbot_threading_residual_20260607/index.html` completed 9/9 residual/dependent personas with all issue lists empty, false_positive_threads `0`, and false_negative_threads `0`.
- [x] **Linear `DAL-147`: webapp escalation inbox and manual resolve.** Added brokerage-scoped `/api/v1/agent/escalations` and `/api/v1/agent/escalations/{thread_id}/resolve`, enforcing existing conversation visibility so agents only see their own/invited buyer conversations while owners/team leads/admins can see brokerage threads. Added ordered questions, category, urgency, state, listing/buyer, envelope token, latest route metadata, dashboard escalation metric/panel, and route-backed `/agent/escalations` with state/category filters and manual resolve. Verification: `tests/test_escalation_inbox_api.py` 2/2 passing, Python compile passing, and frontend `npm run build` passing.
- [x] **Linear `DAL-148`: persistent Mahoroba/Eric full-flow workspace run.** Added `scripts/chatbot_full_test.py --persist-agent-workspace` to collapse the canonical harness into a single Mahoroba Test Brokerage workspace under Eric, preserve seeded run data after execution, write `persistent_agent_workspace.json`, attach reviewable conversation summaries, and refresh hot-list assignments/tasks. Added the agent dashboard conversation inbox slice so `/agent` shows all live buyer threads, not just hot leads. Verification artifact: `reports/agent_workspace_demo_20260608/index.html` completed 30/30 personas; workspace snapshot after reply testing has 10 listings assigned to Eric/Mahoroba, 26 conversations, 409 messages, 19 offers, 35 escalation threads, 2 resolved agent-reply threads, 33 open routes, 26 hot-list assignments, and 26 lead tasks. API verification: `/api/v1/agent/dashboard` returned live data (`sample_data=false`) and `/api/v1/agent/escalations` returned 35 threads. Simulated Eric reply through an escalation token relayed to the buyer, consumed the route, resolved the thread, and persisted an `agent_relay` message.
- [ ] **360dialog Coexistence confirmation.** Verify production BSP path for Brokerage AI + Agents AI numbers before live WhatsApp shipment: inbound parsing, outbound buyer sends, outbound agent sends, `[Ref:]` preservation, media relay, webhook retries, and coexistence constraints.
- [ ] Expose per-brokerage debounce timing overrides after pilot feedback; current MVP uses code-level defaults.

## Viewing Logistics Automation + Pre-Viewing Report

Status: Phase 1B is complete for the current MVP as a draft-and-approve workflow. The platform can store per-listing logistics, learn building-level defaults, protect tenant contact data, propose compliant slots without live API spend, confirm viewings, generate pre-viewing briefs, show webapp logistics/calendar/detail pages, and generate notification drafts. Live sends and live Google/Maps calls remain integration follow-ups.

### Phase 1A built

- [x] **Per-listing logistics schema.** `DBListingLogistics` stores Access, Keys, Tenant, and Owner sections for each brokerage listing.
- [x] **Building/community knowledge graph foundation.** `DBBuildingProfile` stores provisional building keys, community keys, access/security/notice defaults, contributor count, and confidence. New listings in the same building get draft prefill.
- [x] **Tenant PII scoping.** Same-brokerage agents can see listing logistics, but tenant name/phone/email are redacted unless the user is the assigned/logistics agent or brokerage owner/team lead/admin.
- [x] **PDPL tenant consent/audit.** `DBTenantConsent` records lawful basis, opt-in status, retention date, assigned visibility, and audit events when tenant contact data is added or changed.
- [x] **Agent availability foundation.** `DBAgentAvailabilityBlock` supports weekday working hours, date overrides, recurring time-off, labels, and per-block prep buffer metadata.
- [x] **Calendar provider settings.** `DBAgentCalendarConnection` stores provider status, selected calendar IDs, sync direction, scopes, and token references only; no raw OAuth tokens or event titles.
- [x] **Viewing slot proposal engine.** `app/core/viewing_logistics.py` proposes slots from availability, security hours, building notice, tenant notice, prep floor, and rush-hour/community-pair travel fallback.
- [x] **Viewing confirmation flow.** `DBViewing` stores proposed slots and confirmation status; confirming a viewing stamps scheduled time, tenant notice requirement, calendar/provider status, and logistics summary.
- [x] **Pre-viewing brief scaffold.** `/api/v1/agent/viewings/{viewing_id}/brief` returns buyer profile, stated priorities, mapped property highlights, likely objections, comparable viewed units placeholder, logistics summary, and confirmation status.
- [x] **Focused tests.** `tests/test_viewing_logistics.py` covers building prefill, lockbox rejection, consent/audit, tenant redaction, availability/calendar settings, dynamic buffers, viewing confirmation, and brief generation.

### Phase 1B built

- [x] **Webapp logistics pages.** Added route-backed listing Logistics tab under `/dashboard/listings/[id]/logistics` with Access / Keys / Tenant / Owner sections, building confidence, and save through the Phase 1A API.
- [x] **Agent viewing calendar/list.** Added `/agent/viewings` for proposed/confirmed/completed viewing rows with schedule, listing, buyer, logistics, tenant notice, and confirmation status.
- [x] **Viewing detail and brief page.** Added `/agent/viewings/[id]` with pre-viewing brief, logistics summary, confirmation status, and notification draft review.
- [x] **Draft-and-approve notifications.** Backend generates and stores T-24h buyer confirmation, T-1h reminder, tenant notice, running-late, and reschedule drafts without auto-sending.
- [x] **Viewing dashboard navigation.** The agent dashboard's viewing panel links to the viewing calendar and detail pages.

### Live integration next

- [x] **Priority 5: Live Google Calendar integration.** OAuth URL/callback endpoints, token-ref connection settings, selected calendar IDs, free/busy filtering in slot proposals, event creation after viewing confirmation, event update on reschedule, and event removal/cancel on cancellation are implemented. Production token storage remains external via `token_ref`; Dalya does not store raw OAuth tokens.
- [ ] **Basic Google Maps travel buffer.** Use Distance Matrix `duration_in_traffic` where credentials/billing allow; keep deterministic fallback. Advanced route optimization is explicitly deferred.
- [x] **Priority 6: Tenant WhatsApp confirmation flow.** Sends approved tenant notices, supports confirm/reschedule/decline/free-text replies via webhook interception, updates viewing state, notifies the agent through Agents AI, and preserves tenant PII boundaries.
- [x] **Priority 7: Viewing logistics completion.** Approved buyer confirmation, buyer reminder, running-late, and reschedule sends are live; tenant state and Google Calendar write-back are connected; confirmed viewings can be marked completed manually or by `scripts/complete_due_viewings.py`; completion creates the post-viewing feedback task and draft.
- [x] **Priority 8: Post-viewing capture.** Four hours after viewing end, `scripts/request_post_viewing_feedback.py` and the agent API request buyer feedback plus an Agents AI prompt; buyer WhatsApp replies and agent dashboard notes are parsed into `viewing_feedback`, update hot-list/task state, and appear on viewing detail.

### Deferred / blockers

- [ ] **Lockbox encryption decision.** Choose KMS/vault approach before accepting raw lockbox codes; current API rejects `lockbox_code` and accepts encrypted-token-shaped data only.
- [ ] **Canonical building IDs.** Decide DLD area codes vs Property Finder taxonomy vs internal canonical table. Phase 1A uses provisional normalized building/community keys.
- [ ] **Luqman's viewing volume per agent per week.** Determines whether batching/route optimization moves earlier.
- [ ] **Ready vs off-plan inventory mix.** Off-plan site visits/developer sales office logistics need a separate schema branch before broad rollout.
- [x] **Post-viewing capture flow.** Agent text/form feedback and buyer WhatsApp replies now structure post-viewing feedback into `viewing_feedback`; voice dictation remains a later input-mode enhancement.
- [ ] **Live unit intelligence capture.** Agent dictates inspection notes while walking the unit; output augments document-extracted data and grounds future bot answers.
- [ ] **Multilingual real-time viewing translation.** Agent and buyer in different languages during a physical viewing; phone app translates inline.

## Pillar 3 — Listing acquisition (deferred until after MVP)

`GOAL_SPEC_0609` explicitly defers owner outreach, owner CSV upload, campaign builder, listing-acquisition automation, and AI property one-pager generation. These may become Mahoroba's internal advantage before being productized.

- [ ] **Deferred: DLD ownership integration.** Public-record access to ownership tenure, transaction history, capital-gain proxies.
- [ ] **Deferred: Owner prioritization model.** Score owners by likelihood-to-sell.
- [ ] **Deferred: Per-owner WhatsApp opener generator.** Draft messages grounded in unit-specific owner data.
- [ ] **Deferred: Just-listed / just-sold neighbor outreach automation.**
- [ ] **Deferred: Owner-specific market intelligence reports.**
- [ ] **Deferred: Newsletter generation per community / developer.**
- [ ] **Deferred: Form A expiry tracking.**
- [ ] **Deferred: Pricing conversation support.**
- [ ] **Deferred: Owner sentiment tracking.**
- [ ] **Deferred: Off-market listing aggregation.**
- [ ] **Deferred: Seller-facing landing page generator.**

## Pillar 4 — Daily agent workflow

Status: Morning Hot List + Follow-Up Engine backend is complete for the current MVP. The agent dashboard now refreshes deterministic hot-list assignments, open queue tasks, and review-only follow-up drafts from real brokerage-scoped rows.

- [x] **Hot list ranking model.** Buyer engagement signal + recency + escalation history + deal-stage progression → ranked queue. Implemented in `app/core/hot_list.py`, feeding `/api/v1/agent/hot-list` and `/api/v1/agent/dashboard`.
- [x] **Follow-up nudge drafter.** For buyers gone quiet >N days, draft a check-in message; agent reviews and one-taps to send. Stale buyers get one open follow-up task and one active `DBDraftReply`, deduped by conversation.
- [x] **Agent dashboard conversation inbox.** `/api/v1/agent/dashboard` now includes brokerage-visible conversation rows with buyer/listing, summary, latest message, message count, offer count, and open escalation count. The `/agent` dashboard renders these as a compact live inbox above the buyer digest.
- [ ] **One-tap conversation takeover.** Agent enters live bot conversation; full prior context preserved; bot pauses; agent speaks with their own voice.
- [ ] **Draft-and-send mode.** AI drafts replies for the agent's review/approval when the agent is actively in the loop (vs autopilot mode where the bot just sends).
- [ ] **Agent performance feedback.** Personal performance dashboard per agent — conversations, response times, escalation conversion, viewings booked, deals closed. Visibility only to that agent + their brokerage owner.

### Remaining Daily Agent Workflow MVP work

- [x] **Priority 2: Draft approval queue.** Added `/agent/drafts` with edit/send/reject/snooze/view-conversation controls, category normalization for urgent/today/stale buyer/viewing/offer/financing/general nurture drafts, no auto-send behavior, timeline persistence, lead actions, and compliance logging.
- [x] **Priority 3: Scheduled morning refresh.** Added `hotlist_refresh_runs`, `scripts/run_daily_hotlist_refresh.py`, deduped assignment/task/draft refresh, `/api/v1/agent/hot-list/refresh`, last-refreshed status, and manual refresh on `/agent`.
- [x] **Priority 9: Agent performance dashboard.** `/agent` now shows current-agent metrics for today, 7 days, and 30 days with no brokerage owner rollups.
- [ ] **Deferred: owner-level performance rollups.** Build only after the individual agent workflow is sticky.

## Pillar 5 — Negotiation and closing support (extension)

- [ ] **On-demand comparable lookup.** Inside any conversation, agent types `/comparables` or taps a button; system surfaces relevant comparables.
- [ ] **Negotiation co-pilot.** Offer comes in → system surfaces (a) comparables for the unit, (b) the seller's flexibility signals, (c) suggested counters. Not autopilot; agent decides.
- [ ] **Ready-property closing mechanics in prompt.** Adapt Phase 8.4 (trustees-office, NOC, MOU sequence) for ready-property closings — similar but fewer NOC dependencies, more title-deed and Ejari handling.

## Pillar 6 — Seller-side workflow

- [ ] **Weekly seller update generator.** Friday one-page report per active listing: inquiries, viewings, offers, market context. Agent reviews; one-tap send.

## Document layer (Priority 4 engineering blocker for ready-stock)

- [x] **Ready-property document upload surface and API.** `POST/GET /api/v1/listings/{id}/documents`, reprocess endpoint, status lifecycle, extracted text preview, parsed facts, confidence, and dashboard knowledge tab.
- [ ] **Title deed parser** (replaces SPA at handover; pre-handover Oqood).
- [ ] **Oqood parser** where applicable.
- [ ] **Ejari parser** (tenancy contracts; ~30–40% of Dubai ready resale).
- [ ] **Service charge statement parser.**
- [ ] **NOC parser** for ready-property handover-completed cases.
- [ ] **Valuation report parser.**
- [ ] **Mortgage liability letter parser** for encumbered units.
- [ ] **Floor plan parser/uploader.**
- [ ] **Snagging report parser.**
- [ ] **DEWA / utility info parser.**
- [ ] **Building/community rules parser.**
- [x] **Listing facts and knowledge summary.** Store extracted facts, buyer-safe summary, internal summary, missing fact keys, risk flags, confidence, and agent verification status.

## Open product decisions

- [ ] **Aggregation contract language.** Exact language for the data-rights clause negotiated with Luqman. Sets the precedent for customer 6. Brokerage-specific data stays siloed; aggregated anonymized signal feeds platform intelligence; both parties sign on what falls in which bucket.
- [ ] **Pricing model.** Deferred until stickiness is proven with Luqman. Likely seat-based subscription (per agent / month) with a brokerage floor. Pricing is the negotiation we win once stickiness is proven, not the lever we lead with.
- [ ] **Agent recruitment messaging for Mahoroba.** Deferred to year 2–3. Endgame, not near-term focus.
- [ ] **Decide which "Eric" role each customer brokerage maps to.** Owner? Managing director? Senior broker named in BOT_RULES.md prompt template? Configurable per-brokerage.

---

# Mahoroba consumer-direct backlog (legacy)

The items below were queued for the original consumer-direct brokerage strategy and reflect that scope: sellers list directly with Dalya at 0.15% commission, buyer-facing dashboard surfaces, asking-price formatting decisions for portal listings. Some are still applicable in the B2B context (multilingual extensions, regulatory tooling, summarizer infrastructure); some are not (seller self-onboarding for direct listings, buyer portal). Each is annotated where the call is non-obvious.

## Under Consideration

### Seller self-onboarding via dashboard (Phase 8.11, dashboard work)
When a buyer-mode conversation pivots toward "I want to sell my unit" (Khalifa-style — existing owner asking about listing fees / process), the bot already fires `new_listing_inquiry` escalation (Phase 7.6.7c). The chat-side response now also points to dalya.ai/dashboard for SPA upload.

To complete the flow, the dashboard needs a `dalya.ai/dashboard/list-property` page that handles:
1. SPA PDF upload (parser already shipped)
2. Listing details capture (asking, threshold, photos, description)
3. Floor plan / render upload (when Phase 7.10 floor plan agent ships)
4. "Submit for review" → notification to Eric with a draft listing

Eric can approve, request clarification, or decline (with reason logged). This unblocks sellers immediately while still routing through Eric for the personalised onboarding call.

This is product/dashboard work, not a chatbot fix. Chatbot continues firing `new_listing_inquiry` escalation on intent detection.

### NOC threshold + paid-pct schema fields per listing (Phase 7.6.1c, deferred)
Spec wanted explicit per-project `noc_threshold_pct` and `current_paid_pct` so the prompt can frame: "Unit is at X% paid; NOC eligibility is at Y%; seller will pay the remaining Z% (AED N) to reach NOC threshold once an offer is accepted." Currently the prompt uses `compute_paid_to_date` (date-driven inference) and a static "40% NOC" assumption. To ship: add `noc_threshold_pct` to SPA schema (Emaar typically 30-40%, Sobha 50%), seed values per real listing, update `prompt_builder` NOC framing block. ~30 min.

### `listed_at` timestamp + time-on-market response (Phase 7.6.7a, deferred)
Add `listed_at: datetime` to `DBListing`; bot uses `(now - listed_at).days` for time-on-market questions. Frame by bucket: <30 days = "actively marketing for N days", 30-90 = "active market interest at this price point", >90 = "marketing for a few months, let me know if pricing flexibility might help". Currently bot says "I don't have that detail" which is honest but a missed engagement opportunity. ~20 min schema + prompt.

### Asking-price bold formatting (Phase 7.6.1a, deferred — needs WhatsApp strategy)
Spec wanted asking price wrapped in `**AED X**` with markdown stripper whitelisting that pattern. Trade-off: WhatsApp does NOT render markdown bold (it uses single-asterisk `*X*`), so `**AED X**` would appear literal. Two options to revisit: (a) strip universally (current behaviour), accept plain "AED 17,253,444"; (b) use single-asterisk for WhatsApp + markdown bold for the dashboard via separate render paths. Punted to a presentation-layer decision.

### Address-branded sub-projects in The Oasis KB (Phase 7.6.1b, deferred — needs research)
Eric flagged that Address (in addition to Palace) is also a branded Emaar sub-collection in The Oasis. Currently the bot may treat Palace as the only branded option. Need to research the full list of Emaar Oasis branded sub-projects and update `knowledge_base/emaar_oasis.json` so the bot stops implying Palace is the only one. ~1 hr research + data update.

### Maid's room + layout features per listing (Phase 7.6.3, deferred — partly absorbed by floor plan agent)
Palace Villas Ostra has a maid's room but the SPA parser didn't capture it; bot says "I don't have that detail in the specs" when asked. Short-term: hand-fill `maids_room: true` and similar layout fields on existing listings. Long-term: covered by the floor plan auto-scrape + vision feature extractor below.

### Daily conversation summarizer (Phase 7.9, deferred — design ready)
Per Eric's spec: summarize conversations with 3+ messages, key by `(buyer_phone, listing_id)`. When user returns on same phone for same listing, surface prior summary as context in the system prompt so continuity holds. Schema: `ConversationSummary` table with `summary_id`, `buyer_phone`, `listing_id`, `last_message_at`, `summary_text`, `offers_made`, `intent_signals`. Cron job at 23:00 UAE time daily. Wire prior-summary injection into `chatbot_engine.handle_message` and detect explicit continuity references ("earlier", "previously", "last time"). ~3-4 hrs build.

### Floor plan + render auto-scrape agent (Phase 7.10, deferred)
Build a multi-step agent that scrapes developer sites for floor plans and renders when a SPA is uploaded. Three implementation paths:
- **Option A** (long-term): Sobha SharePoint via Microsoft Graph API + Emaar broker portal via Selenium/Playwright. Programmatic fetch of floor plans + renders, then Claude Sonnet vision step extracts features (maid's room, study, parking, balconies). ~2 weeks build.
- **Option B** (short-term ship): Manual upload alongside SPA at listing creation. Vision step runs on uploaded PDF/images. ~2 days.
- **Option C**: Tavily web search + vision verification when no portal access. Quality lower than A or B.

Pipeline target: SPA upload → SPA parser → Floor Plan Agent → Vision feature extractor → Listing record updated → Admin review → Live. Currently floor plan absence causes bot to say "I don't have that detail" for layout questions (e.g., maid's room). Eric will revisit when prioritizing.

### Telegram edit-in-place for revised offers
When the same buyer revises an offer upward within 24h, the bot now prefixes the conversation summary with `[REVISED OFFER] AED X → Y → Z` (Phase 5.1) — but each revision still fires a fresh Telegram alert. Future improvement: edit the existing Telegram message rather than send a new one. Requires storing Telegram message_id alongside the OfferRecord and using `editMessageText` API. TODO comment already in code.

### "Palace Villas Ostra" listing tag for semantic matching
The `_infer_listing_tags` in `crud.py` emits `"the oasis"`, `"palace branded"`, `"5-bedroom"` for the real Ostra listing — but not the explicit project name `"palace villas ostra"`. Buyers who name the project explicitly may match less reliably than buyers who describe by attribute. Add the project name to the tags list.

---

## Seller Dashboard Enhancements

- [ ] **Real notification preferences** — Settings page toggles currently UI-only. Wire to backend: email on offer, WhatsApp for urgent alerts, weekly summary
- [ ] **Media upload UI** — Sellers upload renders, floor plans, photos from listing detail page. Backend `media_urls` already supports this
- [ ] **Listing performance metrics on dashboard** — Aggregate stats are now surfaced via seller-mode chatbot, but dashboard UI not built. Total views/inquiries over time, avg response time, conversion rate (inquiries → offers)
- [ ] **Engagement Funnel card** — Surface the "X buyers in payment discussion" / "Y active discussions (4+ messages)" insight on the Overview page
- [ ] **Commission calculator** — Show AED saved with Dalya's 0.15% vs 2% market rate based on actual asking price
- [ ] **Comparable market data** — Similar listings in the area with prices for seller context
- [ ] **Document vault** — Store original SPA PDF, NOC forms, DLD transfer docs in one place
- [ ] **Listing status ETAs** — Estimated timeline per processing stage (Trakheesi ~3 days, Portal listings ~24h, etc.)
- [ ] **Suspicious activity review surface** — `DBSuspiciousActivity` rows (bypass_attempt, broker_probe, scammer-pattern detections) now persist; surface them in admin/seller UI for review
- [ ] **Regulatory request workflow** — `regulatory_request` escalations need a compliance dashboard with 30-day PDPL-window timer + manual data-deletion action

---

## Phase 3 / Future

- [ ] **Buyer portal** — Saved searches, shortlisted properties, document checklist
- [ ] **NOC tracker** — Alert seller when their property crosses the NOC threshold (e.g. hits 40% paid)
- [ ] **Market comparables** — Pull live Property Finder data to give buyers real-time context on how this unit compares to the market
- [ ] **Voice AI** — Extend to phone call handling (Twilio Voice + speech-to-text) for buyers who prefer calling
- [ ] **RERA compliance audit** — Review all bot responses against RERA advertising standards before scaling
- [ ] **CRM integration** — Push escalated leads to HubSpot / Zoho CRM automatically (lower priority now that native CRM exists)
- [ ] **Per-instalment `actually_paid` UI** — Schema supports `actually_paid: bool` per payment milestone, but no admin UI to flip the flag when a real payment is confirmed (currently relies on date-based inference). When the seller actually receives confirmation of an instalment, they should be able to mark it paid in the dashboard so the bot's "% paid to date" reflects truth, not just inferred-from-date
- [ ] **Validate-on-upload SPA admin surface** — `validate_spa_parse` returns warnings (suspiciously round BUA, schedule != 100%, missing bedrooms on Villa) — currently logged at WARNING level only. Surface in the listing detail page so the seller/admin can see + correct before activation
- [ ] **`actually_paid` ground-truth backfill for existing listings** — Both real listings (Ostra, Seahaven) currently have `actually_paid=None` on every instalment, so `compute_paid_to_date` infers from date alone. When Eric has confirmation of which milestones have been paid for the active listings, set the flags so paid-pct stops drifting on date alone

---

## Open Product Decisions

- [ ] **Round-number heuristic for offer escalation** — In data-moat terms, offers like "5 million" (round) vs "5,780,000" (specific) signal speculation vs intent. The classifier extracts `is_firm_offer: true|false`, which captures most of this, but no separate priority signal yet. Decide whether to add a `round_number_offer` flag and downgrade alert priority for those.
- [ ] **Lawyer escalation when buyer name not yet captured** — Phase 6.2 ships `legitimate_conveyancing` requiring (a) lawyer self-id AND (b) named buyer with matching `OfferRecord`. If the buyer offered before the bot extracted their name (early-conversation gap), the lookup misses. Decide: fuzzy-match across all listings, or add a "lawyer claims X" intermediate state that escalates regardless of match.
- [ ] **`our team` referential phrase policy** — Phase 6.5 allows referential team mentions ("our compliance team", "Eric and the team"). If you want stricter brand voice (e.g., "Mahoroba" not "team"), update `DEFERRAL_PATTERNS` to include all referential variants too.

<!-- BEGIN:command-center-project-backlog -->
## Command Center Project Backlog

Dashboard project slug: `dalya`

These items should be mirrored into the Command Center task board and logged with `activity-log` when meaningful work is completed.

### Completed

- [ ] Chatbot QA history reconstruction - detailed run-level test history for persona tests, fixes, failures, and outcomes.

### Ongoing

- [ ] Brokerage workflow map - identify the highest-value AI workflow for real estate brokerages.

### Backlog

- [ ] CRM and dashboard workflow - clarify operator CRM flows, lead visibility, and brokerage follow-up tasks.
- [ ] Website and positioning refresh - turn brokerage AI positioning into public-facing site copy and product narrative.
- [ ] Distribution plan - build a repeatable go-to-market plan for brokerage outreach and pilot customers.
<!-- END:command-center-project-backlog -->
