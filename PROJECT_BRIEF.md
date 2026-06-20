# Dalya Project Brief

*Five-minute human-readable overview for a smart outside reader. Read this once, you'll know what the project is and how to navigate the rest of the repo.*

*Last updated: 2026-06-20 (`DAL-170E1` RLS session context + rehearsal policies)*

## Mission

**Build B2B AI infrastructure for Dubai real estate brokerages.** The MVP is now explicitly agent-platform production readiness: buyer WhatsApp inquiries, dashboard/WhatsApp escalations, draft follow-ups, morning hot list, ready-property knowledge, viewing logistics, calendar/tenant coordination, post-viewing capture, and personal agent metrics.

The product is the platform. The customer is the brokerage. The launch user is the agent. The buyer is consumed via the bot, not as a customer of Dalya. Owner dashboards and listing-acquisition workflows are deferred until the agent workflow is sticky.

## Current product

Dalya started as an AI-powered off-plan resale marketplace operating directly on Mahoroba Realty's RERA licence, using a fixed low-commission buyer-side model and competing with traditional brokerages. **On 2026-05-15 we pivoted** to B2B AI infrastructure for brokerages. Mahoroba Realty remains alive in maintenance mode and is held in reserve as an eventual agent-recruitment destination once the platform is sticky.

Customer one (current design partner): **Luqman's brokerage**, 60–90 day design partnership with agent stickiness as the success criterion. Pricing is deferred until stickiness is proven.

The product expands beyond off-plan resale to include **ready-property resale and tenanted resale**, with a document layer that now needs to handle SPA, title deed, Ejari (tenancy), service charge statements, NOC, valuation, snagging, and mortgage paperwork.

The legacy seller dashboard is now retired from the active product path and preserved only as `/seller-dashboard-archive` for reference. Active app work should target `/agent` and the agent workflow APIs first; admin/owner dashboards come later after agent stickiness is proven.

Onboarding is brokerage-first. Dalya registers/approves a brokerage first, records its DLD `RealEstateNumber`, and only then can agents create profiles under it. Agents cannot self-create unknown brokerages during the first rollout; if their RERA card's registered brokerage number is not active on Dalya, they are routed to contact Dalya.

## Product surface model

- **MVP surface: Individual agent workspace** (mobile-first, WhatsApp-adjacent): hot list, conversation thread, escalation support, dashboard reply composer, draft approval queue, viewing logistics, ready-property knowledge, calendar/tenant coordination, post-viewing capture, and personal performance.
- **Deferred surface: Brokerage owner dashboard** (desktop): aggregate performance, listing pipeline, listing acquisition signal, RERA + PDPL compliance audit trail. Do not build owner login, owner rollups, or leaderboards for MVP.

Shared data layer. One platform.

## Features built (carry over from the consumer-direct work, all valid for B2B)

- Multilingual buyer responder (EN/AR/RU/HI; Mandarin in backlog) with `is_firm_offer` discrimination, currency normalization, multilingual intent classification
- Above-threshold offer escalation with deterministic template (Phase 8.1)
- Three-message engagement gate to suppress spam/probe escalations (Phase 5.1 + 8.3)
- Conveyancing privacy unification: lawyer queries never confirm offer existence (Phase 8.7)
- Form A / RERA / Trakheesi co-broker compliance escalation (Phase 8.6)
- BRN-only requests routed to a distinct escalation type (Phase 9.6)
- Soft-offer detection — buyer floated an amount then paused, captured as warm lead (Phase 8.5)
- Returning-buyer detection — surfaces prior offers on T1/T2 (Phase 9.10)
- Promise → escalation invariant — bot's word matches the system's action (Phase 8.10)
- Managing-agent first-mention introduction (Phase 9.1 generalized) — resolves through brokerage-specific runtime config
- SPA price arithmetic protection — never disclose seller's purchase price (Phase 8.2)
- DLD trustees-office closing mechanics encoded in prompt (Phase 8.4)
- Universal response validator: em-dash / deferral / reflexive-closer / markdown-bold / emoji stripping (Phase 7.5)
- SPA parsing → live listing pipeline (off-plan)
- Seller portal: Supabase auth, dashboard, edit listing, SPA upload
- Admin CRM at `/admin` (Listings, CRM by phone, Knowledge Base viewer)
- 27-persona test suite with rubric checks, fleet quality metrics, repeated-refusal probes, and stable single-folder HTML report publishing

Full feature inventory in [`FEATURES.md`](./FEATURES.md).

## MVP feature set

The current MVP is still framed by four product blocks, but `GOAL_SPEC_0609` now defines the concrete launch order in [`MVP_ROADMAP_0609.md`](./MVP_ROADMAP_0609.md).

1. **24/7 Inquiry Concierge.** EN/AR/RU/HI inquiry handling, voice-note transcription, buyer qualification, off-plan and ready-property document grounding, and agent-authored unit notes. Mandarin is deferred.
2. **Smart Escalation to Agents.** Brokerage AI escalates serious/unanswerable questions to Agents AI; agents can reply by `[Ref: TOKEN]` WhatsApp relay or dashboard composer.
3. **Morning Hot List + Follow-Up Engine.** Automatic morning refresh, ranked active buyers, deduped tasks, and approval-only follow-up drafts.
4. **Viewing Logistics Automation + Pre-Viewing Report.** Ready-property logistics, slot proposal, buyer/tenant confirmation, Google Calendar, reminders, pre-viewing brief, and post-viewing feedback.

Full backlog with platform-infrastructure blockers in [`BACKLOG.md`](./BACKLOG.md).

### Final MVP completion order

1. `DAL-149` Dashboard reply composer.
2. `DAL-150` Draft approval queue.
3. `DAL-151` Scheduled hot-list refresh.
4. `DAL-152` Ready property intelligence layer. Built and verified.
5. `DAL-153` Google Calendar integration. Built and verified.
6. `DAL-154` Tenant WhatsApp confirmation flow. Built and verified.
7. `DAL-155` Viewing logistics completion. Built and verified.
8. `DAL-156` Post-viewing capture. Built and verified.
9. `DAL-157` Agent performance dashboard. Built and verified.
10. `DAL-143` WhatsApp/BSP production verification. Report complete; Twilio path verified, 360dialog BSP blocked pending WABA approval/implementation.

### MVP gap closure (`GOAL_SPEC_0610`, shipped 2026-06-10)

Nine tickets closing the gaps from the June 10 MVP review — the agent-trust layer:

1. `DAL-158` Live conversation takeover — per-conversation kill switch (`TAKEOVER`/`RESUME` on WhatsApp, dashboard toggle); raw forwards while paused, draft suppression. Built and verified.
2. `DAL-159` Voice note handling — language auto-detect, transcription stored on the message record, agent voice replies delivered as text with confidence-gated `SEND` confirm, `media_unprocessable` escalation on failure. Persona harness re-baselined: 30/30, 0 issues (27.1% append / 28.6% bundle / 42.9% bypass). Built and verified.
3. `DAL-160` Dashboard composer media — `media_assets` storage, attach-from-listing, per-transport size limits, 24h-window enforcement. Built and verified.
4. `DAL-161` WhatsApp relay media — four-tier routing (caption token / quote-reply ref sessions / 30s-held sessions with UNDO / media-request escalation match), parked-media batches, forwarded-caption stripping (PDPL). Built and verified.
5. `DAL-162` Agent notification framework — 13-event catalog, dedupe, quiet hours, rate guard, morning digest, per-agent preferences. Built and verified.
6. `DAL-163` Portal lead ingestion + AI first-touch — versioned PF/Bayut email parsers, dead-letter queue, template-locked auto first-touch (the one bounded exception to draft-and-approve) with PDPL consent evidence, 48h review-only nudges. Built and verified; **WABA template submission is the remaining external dependency**.
7. `DAL-164` Buyer card & list — brokerage-scoped profiles, field-level provenance with a structural no-overwrite guard, suggestion chips. Built and verified.
8. `DAL-165` Offer log — first-class offer threads with a confirm-gated state machine, hot-list boost preferring structured records. Built and verified.
9. `DAL-166` Post-viewing follow-up draft CTA — flag-gated (`FEATURE_FOLLOWUP_DRAFT_CTA`), feedback-grounded review-only drafts with same-brokerage alternatives. Built and verified.

ADRs: relay ref sessions, first-touch template exception, buyer-profile provenance (`docs/adr/`).

### Explicit MVP deferrals

Mandarin production support, owner outreach/campaigns, AI buyer matching launch surface, brokerage owner dashboard/owner rollups, and advanced Google Maps route optimization are deferred until after the MVP.

## Foundation hardening

Phase 0 backend hardening is complete for the current MVP. The platform now has:

1. **Universal brokerage scoping.** Listings are visible across a brokerage, while buyer conversations are private unless assigned, managing-agent visible, or explicitly shared.
2. **Auth and route enforcement.** Agent and dashboard routes use brokerage membership plus conversation-level visibility checks.
3. **Compliance and audit layer.** Opt-outs, outbound sends, blocked sends, escalations, regulatory requests, conversation shares/reassignments, and brokerage-config updates write to a queryable audit trail.
4. **Safe aggregation layer.** Cross-brokerage platform intelligence has a separate anonymized output path with minimum sample sizes and identifier rejection before storage.
5. **Brokerage configuration management.** Prompt identity, managing-agent naming, fee framing, language defaults, dashboard URL, and handoff contacts resolve through brokerage-specific runtime config.

Security hardening is now moving through the DAL-169/DAL-172 sequence. `DAL-169` is merge-ready after production route/webhook/PII/replay hardening and broader regression. `DAL-170A` added the first hard tenant-isolation audit and regression baseline: a read-only Neon/Postgres audit script plus cross-tenant API tests for lead detail/list, hot list, buyer cards, offers, drafts, viewings, media metadata, share/reassign, same-phone buyer profiles, and lead-ingest tenant attribution. `DAL-170B` closed the highest-risk externally reachable listing-route slice: legacy listing activate / portal links / stats / conversations / media endpoints are admin-gated, and `/parse-spa` is now read-only plus active-brokerage-member gated so it no longer leaks global stable-listing existence or writes tenantless listings. `DAL-170C1/C2/C3` are now split and merged: C1 covers tenant normalization audit/dry-run tooling, C2 covers runtime null-tenant and buyer-profile quarantine guardrails, and C3 stops portal lead ingest from writing active buyer-source state into the legacy/global phone-keyed buyer profile table. `DAL-170D1/D2/PROD` added production-blocked tenant-constraint preflight, safe parent/child index tooling, NOT VALID tenant FK phases, DB fingerprint/artifact/rollback guardrails, and the production DDL hold decision; the DDL rehearsal and staging rollout passed, but production DDL remains intentionally held until official onboarding / real production data. `DAL-172A/B` closed explicit brokerage context end to end: backend routes validate `X-Brokerage-Id` and fail closed for multi-brokerage users without context, while the frontend requires explicit brokerage selection before authenticated brokerage-scoped API calls. `DAL-170E1` now adds the first RLS foundation without enabling production/staging RLS: SQLAlchemy sessions store request/service DB context, an `after_begin` hook applies transaction-local `SET LOCAL` values and reapplies after `safe_commit()`, `/me/brokerages` works with user context before selection, lead ingest sets explicit resolver-derived service context, and a test/local-only rehearsal policy script covers the first direct-root tables under a non-owner rehearsal role. No broad all-table RLS, production/staging RLS, production DDL, data backfill, derived/no-root table policies, chatbot behavior, WhatsApp send behavior, or frontend behavior changed in E1. Remaining RLS work is staged: expand only after app-role context, pooling safety, and first-table rehearsal behavior remain stable.

Testing and backfill policy: unit and integration tests are expected to create and clean up their own fixture data. Shared `.env.test` is a shared validation branch, not a permanent candidate baseline; real backfill validation should use a dedicated Neon branch per migration so candidate counts cannot drift under unrelated test activity.

Clean branch recovery split: `DAL-170C1` is scoped to tenant normalization audit/dry-run tooling, focused tests, and docs only. It intentionally does not reintroduce runtime null-tenant guardrails, buyer-profile quarantine changes, chatbot behavior, lead ingest behavior, WhatsApp send behavior, RLS, DDL enforcement, migrations, or real data backfills; those remain separate follow-up work under `DAL-170C2+`.

`DAL-170C2` now covers the runtime guardrail slice without schema or backfill work: active CRUD helpers hide null-tenant listings/conversations from brokerage-scoped surfaces, listing inquiries resolve/refuse tenant roots instead of creating active null-root rows, and tenant-scoped buyer-profile conversion ignores legacy/global buyer-profile state so same-phone buyers across brokerages remain isolated. Chatbot behavior, lead ingest, WhatsApp send behavior, hot-list/draft behavior, frontend, RLS, DDL, migrations, production backfills, Verified Facts, and DealReadiness runtime remain separate.

## Build plan

Build from the agent's daily workflow outward, not from a generic CRM feature map. The first product wedge is a mobile-first agent command surface that makes each agent better briefed, faster to follow up, and less likely to miss serious buyer intent. The owner dashboard comes later; MVP success is an agent operating without sample data through the live agent workspace.

Phase 0 is backend-complete. The remaining foundation work is product polish: owner-facing compliance UI, a scheduled aggregation job once customer volume justifies it, and an admin UI for brokerage config.

Phase 1 backend is now complete for the Morning Hot List + Follow-Up Engine. The agent dashboard refreshes a deterministic hot-list engine that ranks visible buyer conversations, persists `DBLeadAssignment` state, creates deduped open `DBLeadTask` rows, and drafts review-only follow-up nudges for stale buyers.

Remaining Phase 1 work is now MVP-critical: scheduled morning refresh instead of refresh-on-dashboard-load, a dedicated draft approval queue, and real send/reject/snooze controls for follow-up drafts.

Phase 2 Smart Escalation backend handoff is now complete for the current MVP. Escalations route to the listing's managing agent through the brokerage's Agents AI number, persist an envelope route, and production webhook replies with `[Ref: TOKEN]` relay back to the buyer through the brokerage's buyer-facing number after token, agent-phone, expiry, opt-out, and brokerage checks. Escalations now have a product-level thread model: same-brokerage/same-buyer/same-listing questions in the same category append to an open `escalation_thread`, the agent receives append-only WhatsApp updates using the original reference token, and a successful agent reply resolves all open questions on that thread. The thread layer also has database-backed initial debounce, update debounce, offer/legal bypass, 24h timeout closure, buyer opt-out closure, question-cap formatting, compliance events for create/append/update/resolve/timeout/opt-out, duplicate-open-thread retry around the partial unique index, keyword-first category mapping for info gaps, BRN normal debounce behavior, legacy pending-question cleanup, and backwards-compatible relay for old routes with no thread ID. `agent_message_routes` remains the transport token layer rather than the product work item.

Remaining Phase 2 work is now limited to stuck-handoff monitoring and per-brokerage debounce timing unless pilot feedback makes either launch-critical. Dashboard reply composition is built; 360dialog/BSP production-path confirmation remains the final production verification gate.

Latest Smart Escalation verification artifacts: focused DAL-141 threading report at `reports/escalation_threading_dal141/index.html` and post-DAL-141 full-suite archive at `reports/escalation_threading_full_20260606/index.html` with 189 passed, 1 skipped, 0 failures/errors.

Persona-level Smart Escalation metrics are now in the chatbot harness. Reports include run/persona thread count, question count, average questions per thread, append rate, bundle rate, bypass rate, timeout rate, category distribution, and false positive/negative thread checks. The harness now includes threading-specific controls for rapid same-category fees, post-alert follow-up updates, and cross-category isolation, plus simulated debounce fast-forwarding and single-concurrency runs for DB stability. Latest full baseline: `reports/chatbot_threading_baseline_full_20260606/index.html` completed 30/30 personas with 35 threads, 52 questions, append_rate `0.3269`, debounce_bundle_rate `0.3429`, bypass_rate `0.4286`, and timeout_rate `0.0`. Residual cleanup is complete in `reports/chatbot_threading_residual_20260607/index.html`: 9/9 residual/dependent personas completed with all issue lists empty, false_positive_threads `0`, and false_negative_threads `0`.

The Smart Escalation webapp inbox is now live in the agent workspace. The backend exposes brokerage-scoped escalation thread listing and manual resolve endpoints, with the existing conversation visibility rules enforced so agents only see their own or invited buyer conversations while brokerage owners/team leads/admins can see all brokerage threads. The frontend now shows an escalation metric and compact dashboard panel, plus a route-backed `/agent/escalations` inbox with state/category filters, ordered buyer questions, urgency/category/state badges, `[Ref:]` token visibility, route expiry metadata, and manual resolve.

The agent dashboard now also includes a live conversation inbox. `/api/v1/agent/dashboard` returns brokerage-visible conversations with buyer/listing context, AI summary, latest message, message count, offer count, and open escalation count; `/agent` renders those rows above the buyer digest. The persistent full-flow harness mode `scripts/chatbot_full_test.py --persist-agent-workspace` collapses all canonical harness listings into Mahoroba Test Brokerage under Eric, preserves the resulting run data, writes `persistent_agent_workspace.json`, and refreshes hot-list assignments/tasks for review in the agent workspace.

Latest persistent workspace verification: `reports/agent_workspace_demo_20260608/index.html` completed 30/30 personas. Final saved state after simulated agent-reply verification: 10 listings assigned to Eric/Mahoroba, 26 conversations, 409 messages, 19 offers, 35 escalation threads, 2 resolved agent-reply threads, 33 open routes, 26 hot-list assignments, and 26 lead tasks. `/api/v1/agent/dashboard` returned live data (`sample_data=false`) with 26 conversations, 25 hot leads, 26 tasks, and 25 open escalation rows. `/api/v1/agent/escalations` returned 35 threads. A simulated Eric reply through an escalation `[Ref:]` token relayed to the buyer, consumed the route, resolved the thread with `agent_reply`, and persisted an `agent_relay` message. Two persona-check issues remained in the report: no-listing portfolio honesty and Raj's project/developer reference check.

Phase 3 Viewing Logistics Phase 1B is complete as a draft-and-approve foundation, and the Google Calendar plus tenant confirmation MVP integrations are now built. The platform has provider-ready records and APIs for per-listing Access / Keys / Tenant / Owner logistics, building-level prefill with contributor confidence, tenant PII redaction, PDPL tenant consent/audit, agent availability blocks, token-ref Google Calendar connection settings, free/busy-aware slot proposals, viewing confirmation with event create/update/delete, tenant notice sends, tenant confirm/reschedule/decline/free-text reply handling, notification draft generation, and pre-viewing brief generation. The webapp now includes `/dashboard/listings/[id]/logistics`, `/agent/viewings`, `/agent/viewings/[id]`, and `/agent/calendar`. MVP completion still requires viewing status lifecycle, buyer reminders, completion detection, and post-viewing capture.

Phase 4 ready-property intelligence is now built for MVP. Agents can upload/process ready-property document text, review extracted facts, verify facts, mark them buyer-safe or internal, flag risks, see missing core facts, and ground Dalya's property advisor in the buyer-safe knowledge summary. Existing buyer preference and matching scaffolding is deferred from MVP as a product surface.

Do not build a broad CRM, owner-marketing layer, owner dashboard, or AI buyer-matching launch surface before the ten MVP completion priorities are done.

Implementation status: backend schema now includes brokerage membership, lead assignments, lead tasks, lead actions, viewings, tenant viewing confirmations, draft replies, hot-list refresh runs, escalation threads/questions, agent message routes, building profiles, listing logistics, tenant consent, availability blocks, calendar connection settings, ready-property documents, listing facts, and listing knowledge summaries. The active frontend entry is `/agent`; `/dashboard` redirects there. The agent surface now has real hot-list ranking, persisted/manual/scheduled hot-list refresh status, conversation inbox, follow-up draft data, production-safe Agents AI reply relay, threaded escalation persistence/update semantics, escalation inbox/manual resolve, dashboard escalation reply composition, `/agent/drafts`, `/agent/conversations/[id]`, Viewing Logistics APIs, listing logistics tabs, viewing calendar/list, viewing detail, pre-viewing brief UI, `/dashboard/listings/[id]/knowledge`, and `/agent/calendar`. It still needs completed viewing lifecycle, post-viewing capture, personal performance metrics, and production WhatsApp/BSP verification.

Agent onboarding implementation now includes agent profiles, DLD/RERA broker-card verification records, agent chatbot handoff configuration, and a protected `/onboarding/agent` flow. New login defaults route agents through onboarding before the workspace. If DLD matches the agent's RERA card to a brokerage already registered/enabled in Dalya, the agent membership and chatbot handoff activate immediately.

Agent onboarding is now simplified with a DLD/RERA card lookup. Agents enter only their RERA broker card number; Dalya calls the DLD gateway server-side, reads the returned `RealEstateNumber`, checks whether that brokerage is registered/enabled in Dalya, prefills legal name, WhatsApp/mobile, card expiry, brokerage office, photo/logo metadata, and lets the agent edit display name and prefilled fields before submission. Display name should be normalized for customer-facing handoff (title case, not DLD all caps). Languages are selected via multi-select chips. Service areas are not collected during signup; keep them for the later Agent Profile edit surface. The DLD `consumer-id` is configurable via `DLD_GATEWAY_CONSUMER_ID`; do not assume a browser-observed value is approved or stable for production.

Operational scripts now support the first controlled rollout:
`scripts/create_brokerage_signup.py` creates/enables a brokerage record and stores its DLD `RealEstateNumber`. The legacy join-code field can remain for admin/debug use, but agent onboarding now matches by DLD brokerage number,
`scripts/approve_agent_profile.py` remains available as an override utility for unusual cases but is not part of the default signup path.
`scripts/activate_dld_matched_agents.py` backfills active status for DLD-matched agents created before the approval gate was removed.

The chatbot migration now has a current-structure simulation path. `scripts/chatbot_full_test.py` defaults to simulated transport mode, seeds Mahoroba and Irwin as brokerages with separate Brokerage AI / Agents AI numbers, assigns multiple agents and listings under each, and verifies that escalations route to the listing's managing agent. Offer routing uses the migrated three-band policy: below threshold band handled only, within 5% below notification threshold escalated with a near-threshold tag, and at/above threshold escalated directly.

Next feature slice now tracked in Linear:
`DAL-5` now has an initial backend implementation: shared transcription service, Speechmatics default provider adapter, AssemblyAI fallback adapter, `transcription/dictionary.yaml`, Claude Haiku post-processing with deterministic fallback, structured AED price extraction, raw-audio deletion, cost metadata logging, and focused unit tests. Live provider verification still needs Speechmatics, AssemblyAI, and Anthropic credentials plus a consented real sample audio set.
`DAL-7` now has an initial backend implementation: buyer voice notes can enter the debounced WhatsApp flow, run through the shared transcription service, persist transcript/price-confidence metadata on conversation messages, and feed confidence-aware offer handling. High/medium-confidence voice prices can flow into the existing offer pipeline; low-confidence ambiguous prices trigger a verify-amount response instead of confirmed escalation. Agent voice replies can be sent as actual audio to buyers via the active messaging transport while the internal transcript and audit metadata are stored on the lead timeline. The simulated transport supports buyer and agent voice-note payloads.
`DAL-8` now has an initial implementation: listings store a structured `unit_profile` and append-only `unit_profile_history`; the agent API accepts inspection notes from typed transcript, base64 MediaRecorder audio, or test audio path; audio uses the shared transcription service, then a Sonnet structuring pass with deterministic fallback categorizes layout, condition, view, building/community quirks, AC/utilities, parking, neighbor situation, and subjective notes. The listing detail dashboard exposes an `Inspection Notes` panel with mobile-friendly recording and typed-note fallback. The Property Advisor prompt receives the agent-authored unit profile as high-trust listing-specific context and is instructed to prefer it for sensory/practical questions over generic community data.
`DAL-6` now has an initial implementation: a brokerage-scoped `buyer_preference_profiles` table, conservative buyer preference extraction with Sonnet support and deterministic fallback, inquiry-history-based inferred preferences, deterministic same-brokerage listing matching, and alternative-listing gating so the Property Advisor only sees alternatives when the buyer asks or signals mismatch. This remains useful scaffolding, but AI buyer matching is no longer a launch MVP surface.
`DAL-9` now has an initial implementation: new listings generate persisted same-brokerage `buyer_listing_matches`, the agent API exposes ranked matched buyers with aligned-preference reasons and draft outreach, and the listing detail dashboard shows a "Buyers who may be interested" panel with copy-to-clipboard for manual WhatsApp Business sending. This is deferred from MVP productization by `GOAL_SPEC_0609`.
`DAL-10` now centralizes the dashboard UI shared by these flows: `InspectionAudioInput`, `ConversationView`, `DraftMessageCard`, `InterestedBuyersPanel`, and `UnitProfileView` live under `frontend/src/components/shared-ui`, with shared light/slate tokens in `frontend/src/lib/shared-ui-tokens.ts`. The listing detail page now consumes the shared unit-profile and interested-buyers components, and `/component-showcase` is a permanent internal fixture for reviewing states including voice transcription flags, low-confidence price chips, multiple matches, empty states, and multiple inspection-note sessions.

The component showcase has repo-native visual verification through `npm run verify:component-showcase` in `frontend/`. The script starts or reuses the local Next server, opens `/component-showcase` in Playwright Chromium at a 380px mobile viewport, asserts the key shared components and transcript/offer text are visible, confirms the conversation view has no audio player, and writes screenshots to `frontend/test-results/component-showcase`.

`DAL-11` and `DAL-12` now formalize the canonical multi-brokerage test harness. `tests/harness/config.json` defines brokerages, generated agents, listing URLs, and deterministic randomization; `tests/harness/snapshots/` freezes PF/Bayut scrape outputs with image references; `tests/harness/scrape_report.md` reports required fields per URL. The reusable builder in `tests/harness/builder.py` exposes `build_harness_plan`, `build_harness`, `get_harness_seed`, `teardown_harness`, and `refresh_snapshots`. `scripts/build_harness.py plan|build|summary|teardown` is the default command path and reads frozen snapshots unless `scripts/refresh_harness_snapshots.py` is explicitly run. The chatbot persona runners now consume this canonical harness instead of maintaining separate `chatbot-full-*` brokerages/listings or legacy wiped listing IDs. The multitenant migration now adopts an existing `mahoroba-realty` slug row instead of failing on duplicates, and it deliberately leaves commissions per-listing rather than backfilling a Mahoroba percentage. Production database contents were reset on 2026-05-28 while preserving schema; harness/persona write paths now require physical isolation through a Neon test branch plus the shared `tests.safety.assert_safe_test_database()` guard. Test writes require `DALYA_ENV` in `test|staging|development`, a test `DATABASE_URL`, and a non-secret `PROD_DB_HOST` denylist; `DALYA_ENV=test` with a production-host URL is blocked before DB connection.
The harness payment model now treats `under-construction`, `under construction`, `off_plan`, and `off-plan` as off-plan, while `completed` listings remain ready/finished. The current 10-listing harness split is 5 off-plan and 5 ready. Off-plan rows get deterministic synthetic SPA/original-price and remaining-payment schedules validated by invariant checks; ready listings carry no paid percentage, NOC flag, handover date, or remaining developer schedule.
`DAL-13` re-grounded the chatbot persona suite on canonical harness listing values. The suite no longer asserts legacy Ostra/Seahaven prices, developers, project names, SPA prices, or wiped listing hashes; price/developer/confidential-value checks now derive from each persona's assigned harness listing and skip type-specific checks where they do not apply. It also adds the first explicit cross-tenant isolation persona and universal cross-tenant leak check, plus ordinary-buyer coverage for hesitant logistics, mortgage/affordability, and ready-property tenancy flows. The simulated transport is serialized per turn so parallel persona runs do not cross-contaminate Agents AI route captures.

After the `chatbot_test_2026-05-30` review, the Property Advisor and harness now have tighter factual-integrity guardrails. Ready listings no longer inherit off-plan payment, future-handover, NOC-threshold, or take-over-developer-payments language. Remaining-to-developer math uses the rendered remaining schedule as source of truth for harness-style off-plan fixtures, while ready listings compute zero remaining developer balance. The prompt no longer exposes stored seller phone numbers to the LLM, no longer defaults unresolved buyer-facing identity to Mahoroba, and no longer appends a savings pitch to fee answers by default. The harness builder now normalizes obvious portal area-unit slips from listing descriptions, validates apartment/villa area plausibility, enforces off-plan schedule reconciliation including 40% handover instalments, uses mock brokerage names (`Best Homes`, `Gemini Realty`), and applies commission as a brokerage-level policy rather than randomized per listing. Linear issues `DAL-17` through `DAL-30` track the full review workstream set.

The 24-persona chatbot suite now assigns personas across all 10 canonical harness properties instead of four high/mid role buckets. Dependent flows stay on the same property where continuity matters (Sara offer/return/PDPL and seller-acceptance; seller performance/price-change), while the rest of the suite spreads across the remaining listings. Persona scripts are adapted after binding to a listing so villa/apartment/townhouse language, plot-vs-BUA questions, off-plan handover/payment-plan/NOC questions, and ready-property tenancy/transfer questions match the assigned property. Cross-marketing coverage now explicitly checks that same-brokerage alternatives can be surfaced while cross-tenant inventory remains isolated.

Run-2 remediation after `1780419862167` added Linear issues `DAL-31` through `DAL-42` for the missed escalation, identity, blank-response, tenant-scoping, seller-context, fixture, data, and language defects. Implemented fixes include promise-language-to-escalation wiring, deterministic offer threshold handling, viewing and lawyer/MOU handoffs, seller-action recognition without PII echoing, no-listing tenant scoping and top-N limits, agent descriptor/codename sanitization, off-plan fee double-count wording, PDPL first-turn identity, returning-buyer follow-up escalation, ready-property NOC language, villa/townhouse plot validation, Shams townhouse normalization, and same-brokerage comparable-unit trigger expansion.

Run-3 remediation after `1780476909034` added Linear issues `DAL-43` through `DAL-55`. Run 4 review `1780498154408` confirmed several fixes from that workstream landed: `info_gap`, the off-plan/ready viewing split, Arabic fee breakdown and seller-PII localization, Arabic sqft-to-sqm conversion, offer-floor enforcement, seller price-change escalation, P22 furnishing/pet defaults, off-plan "delivered turnkey at handover" wording, and seller-conveyancer/pre-closing NOC framing.

Run 4 also reopened or added the chatbot QA backlog: `DAL-43` refusal variation/firmness ladder, `DAL-48` recurring text stitching, `DAL-27` single-listing tenant portfolio cross-sell, `DAL-45` escalation consolidation, `DAL-53` low-engagement offer escalation flags, `DAL-51` top-N ranking plus NOC/document-fee reconciliation, `DAL-57` cross-tenant co-brokerage over-promise, `DAL-58` broader `info_gap` scope, `DAL-59` seller-state leaks and duplicate offer actions, `DAL-60` off-plan mortgage and offers-through-Dalya KB corrections, `DAL-62` list formatting, and `DAL-63` clearer affordability-gap language. Those fixes are now implemented in the Property Advisor response layer and harness. The repeated-refusal coverage is live as personas 25-27 and verifies seller-PII refusal variation, out-of-scope refusal variation, threshold handoff, and post-escalation hold behavior.

The Maps/places enrichment work now has an offline deterministic harness implementation for all 10 canonical test properties. `app/core/listing_enrichment.py` defines existing Google-Places-style POIs, planned developer-brochure amenities for off-plan communities, drive-time anchors, and KHDA school metadata with match confidence. `scripts/enrich_harness_listings.py` persists that data to the test DB, and prompt building includes source/status provenance so planned amenities are not described as open. This does not require a live Google Maps API key for the deterministic harness; a future live provider should use `GOOGLE_MAPS_API_KEY`.

The latest completed full run artifact is `reports/chatbot_test_multitenant/index.html` from 2026-06-04 21:43 Asia/Dubai: 27/27 personas completed, all fleet quality metrics passing, and two harness-check issues remaining (`persona_22_hesitant_end_user` parking-info-gap expectation and `persona_20_sara_return` exact-offer-restatement escalation expectation). Linear `DAL-67` and `DAL-81` were marked Done from this run: terminal-punctuation/stitch scans were clean, and Khalid's Arabic off-plan opener no longer contains the bad `تام الصرف` / finished-condition wording. The Run 8 regression pass is tracked in `DAL-92` through `DAL-96` and tightened the WhatsApp formatter so list stacking no longer splits headers/names/tower numbers, made ready-tenancy answers deterministic with Dubai 12-month notary/registered-mail notice language, rotated document-request privacy refusals, collapsed duplicated managing-agent role phrases, removed unsupported developer-rating/performance puffery, and cleaned circular info-gap/LTV/repeat wording. The immediate formatting follow-up added literal WhatsApp few-shots to the buyer and professional prompts, deterministic list stacking for schools/properties/units, hard-line portfolio output with prices, scaffolding-phrase stripping, and regression coverage for the exact Run 7/8 inline-list failures. Successful full runs publish only to the stable `reports/chatbot_test_multitenant/` directory; incomplete runs stay in a temporary work directory and are not published. Targeted reruns can now use `venv/bin/python scripts/chatbot_full_test.py --personas 2,11,12,19,21-24`, which expands dependent personas automatically and publishes to `reports/chatbot_test_multitenant_subset/` by default so partial reports do not overwrite the canonical full-suite artifact.

## Brand attributes

**Trustworthy. Calm. Sharp.** In priority order. Operationally defined in [`brand/BRAND.md`](./brand/BRAND.md) and [`brand/01-foundations.md`](./brand/01-foundations.md). Replaces the pre-pivot "Precise. Inviting. Modern." consumer-marketing triplet.

**Visual system locked** in Phase 1–3: gold fully retired; slate-blue `#3D5A80` as sole primary; Inter + IBM Plex Mono + IBM Plex Sans Arabic typography stack; 4px hybrid spacing; light-default with parallel-designed dark mode (currently disabled in Phase 3 build review). Six locked HTML mockups in [`brand/applications/`](./brand/applications/) demonstrate the system under real content.

**Voice posture:** factual, brief, specific. Quiet-by-omission visually; Dubai-functional in vocabulary. Bot voice (buyer-facing) governed by [`BOT_RULES.md`](./BOT_RULES.md); product voice (agent-facing) by [`brand/08-voice-tone.md`](./brand/08-voice-tone.md). They share posture, diverge in register.

## Positioning — agent lift

Dalya improves the agent day by organizing the work around every deal: buyer qualification, repetitive questions, midnight WhatsApp replies, viewing coordination overhead, follow-up nudges, and offer context. The product language should make agents feel sharper, better briefed, and more effective. Do not lead with automation volume or imply headcount reduction.

The agent dashboard should frame outcomes as "your agents are faster, better briefed, and closing from a cleaner pipeline", not "Dalya handled the work." Same underlying capability, different customer psychology.

## Users and customers

- **Customer (buyer of the product):** brokerage owners. Luqman is customer 1.
- **Daily user:** individual agents (entry-level, team leads, senior brokers) at customer brokerages.
- **Operational secondary:** office managers, support staff, paperwork-only workers at customer brokerages.
- **Consumed via the bot (not a customer):** UAE-based buyers, mostly expat, mostly WhatsApp-preferred.

Mahoroba Realty's residual buyer/seller-facing surfaces continue to operate in maintenance mode but are not the primary product.

## Marketing and distribution

- Direct sales to small-to-medium Dubai brokerages
- Design partnerships are the wedge — Luqman first, expand to 10–25 in Phase 2
- Pricing deferred until stickiness is proven
- No content-marketing SEO play (the pre-pivot research for this is archived in [`reports/_archive/pre-pivot-research/`](./reports/_archive/pre-pivot-research/))
- Eventual endgame: Mahoroba activates as a recruitment destination for top agents (years 2–3), or the platform is acquired by Property Finder / Bayut / a CRM player as the agent infrastructure layer

## Key decisions

- B2B agent infrastructure, not consumer-direct brokerage (2026-05-15)
- Agent-platform MVP completion order from `GOAL_SPEC_0609` is now canonical (2026-06-09): dashboard reply, draft queue, scheduled hot-list refresh, ready-property intelligence, Google Calendar, and tenant WhatsApp confirmation are built/verified; remaining priorities are viewing completion, post-viewing capture, agent metrics, and WhatsApp/BSP verification.
- Root agent instructions are aligned to the B2B brokerage platform direction (2026-06-16): agents should treat `/agent` and brokerage-owned workflows as active product scope, and legacy Mahoroba consumer-direct marketplace surfaces as maintenance/reference unless explicitly requested.
- Brokerage-first rollout: Dalya approves the brokerage before agents can join; unknown brokerages contact Dalya instead of self-registering.
- Gold fully retired; slate-blue `#3D5A80` is the sole brand-driven UI color (Phase 1–2)
- Inter replaces Plus Jakarta Sans; IBM Plex Mono replaces JetBrains Mono (Phase 2)
- Aggregated and anonymized data feeds platform intelligence through an explicit aggregate output path; specific listings, buyers, conversations, and agent performance stay siloed per brokerage (contract precedent set with Luqman)
- Agent-lift framing is the load-bearing product frame: make agents feel improved, not threatened.
- Use Command Center as the shared project observability layer
- Canonical test harness runs against a physically separate Neon test branch with a hard `DALYA_ENV` + production-host denylist guard; harness community research is real shared KB data, not stubs.

## Important files and artifacts

| File | What's in it |
|---|---|
| [`brand/BRAND.md`](./brand/BRAND.md) | Canonical brand document — start here |
| [`brand/STRATEGIC-PIVOT-2026-05-15.md`](./brand/STRATEGIC-PIVOT-2026-05-15.md) | Permanent record of the B2B pivot |
| [`brand/`](./brand/) | Phase 1–3 brand docs + locked HTML mockups |
| [`CLAUDE.md`](./CLAUDE.md) | Project context for Claude Code |
| [`AGENTS.md`](./AGENTS.md) | Agent operating instructions |
| [`BOT_RULES.md`](./BOT_RULES.md) | Bot voice + escalation logic, canonical |
| [`FEATURES.md`](./FEATURES.md) | Shipped + planned (B2B pillars at top, Mahoroba legacy below) |
| [`BACKLOG.md`](./BACKLOG.md) | MVP feature set for Luqman + B2B platform backlog |
| [`MVP_ROADMAP_0609.md`](./MVP_ROADMAP_0609.md) | Canonical 2026-06-09 MVP completion order, acceptance criteria, and deferrals |
| [`docs/product/deal-readiness-v1.md`](./docs/product/deal-readiness-v1.md) | Shared buyer-readiness model (profile fields, stages, NextBestAction) feeding chatbot, hot list, buyer card, handoff — spec, not yet implemented |
| [`docs/product/chatbot-qualification-rules-v1.md`](./docs/product/chatbot-qualification-rules-v1.md) | One-question-per-turn qualification rules, response-planner outcomes, bad-vs-better examples — spec |
| [`docs/product/agent-handoff-summary-v1.md`](./docs/product/agent-handoff-summary-v1.md) · [`docs/product/hot-list-scoring-v1.md`](./docs/product/hot-list-scoring-v1.md) | 15-second handoff card format; deal-readiness-driven hot-list scoring — specs |
| [`docs/domain/dubai-real-estate-verified-facts.md`](./docs/domain/dubai-real-estate-verified-facts.md) · [`docs/domain/dubai-real-estate-facts-to-verify.md`](./docs/domain/dubai-real-estate-facts-to-verify.md) | Verified Dubai facts register (filled + confirmed by Eric 2026-06-19, DLD/RERA sources [S1]–[S15]) + the reconciled verification checklist — exact regulatory/fee/process claims route through here before the bot may state them |
| [`docs/product/verified-facts-runtime-handoff.md`](./docs/product/verified-facts-runtime-handoff.md) | Implementation handoff: how a future loader + chatbot should consume the verified-facts policy labels (`direct` / `draft_for_agent_only` / `do_not_state` / `listing_specific_only`). Docs only — not to be built during DAL-172A |
| [`reports/chatbot_test_multitenant/index.html`](./reports/chatbot_test_multitenant/index.html) | Latest completed 27-persona multitenant harness run: 27/27 complete, two harness-check issues, stable single-folder publishing |
| [`reports/chatbot_test_multitenant/RUN_7_POST_FIX_DEEP_DIVE.md`](./reports/chatbot_test_multitenant/RUN_7_POST_FIX_DEEP_DIVE.md) | Post-run deep dive for the Run 7 fix pass, with every persona reviewed and next-fix queue documented |
| [`tests/harness/`](./tests/harness/) | Canonical config-driven multibrokerage harness, frozen scrape snapshots, safety docs, and scrape report |
| [`knowledge_base/`](./knowledge_base/) | Per-community + per-developer knowledge bases, including harness community backfills |
| [`archive/pre-pivot-brand/`](./archive/pre-pivot-brand/) | Pre-pivot brand and marketing artifacts (historical) |

## Open questions

- Which surface does Luqman's first agent open every morning, and what's the one-action default? (Hot list ranking is the answer hypothesis; ship and measure.)
- What's the exact aggregation contract language? The software boundary exists; the customer/legal wording still sets the precedent for customer 6.
- Pricing model and timing: seat-based per agent? Brokerage floor? When do we test it (after stickiness, before Luqman renews, or later)?
- How should Mahoroba's residual consumer-direct surfaces be separated from the public Dalya B2B site so prospects never see mixed positioning?
