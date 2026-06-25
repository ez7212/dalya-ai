# 01 — Repo Findings (reuse, don't rebuild)

Verified by direct inspection on 2026-06-24. These are the existing assets the pilot leans on. Agents
must reuse these conventions; only build the smallest missing piece.

## Stack & run commands

- **Backend:** FastAPI, SQLAlchemy 2.0 + psycopg2, Postgres (Neon). Entrypoint `app/main.py`
  (`app = FastAPI(title="Dalya API")`). No Alembic — schema is **declarative**; tables auto-create via
  `Base.metadata.create_all` when `DALYA_ALLOW_RUNTIME_CREATE_ALL=1` (and in `tests/conftest.py`).
  - Run: `PYTHONPATH=$(pwd) venv/bin/uvicorn app.main:app --reload --port 8000`
  - Health: `GET /health` · Docs: `/docs`
- **Frontend:** Next.js + Tailwind v4, Supabase JS client. Run: `cd frontend && npm run dev` →
  **localhost:3001** (3000 is reserved). `next.config.ts` rewrites `/api/v1/*` → `localhost:8000`.
- **API prefix:** all backend routes are under `/api/v1`.

## Auth (how Eric reaches `/agent`)

- `app/core/auth.py` — `get_current_user()` verifies a **Supabase JWT (ES256)** via the JWKS endpoint.
  `Authorization: Bearer <jwt>`. `require_admin()` gates on `ADMIN_USER_ID`.
- Brokerage context: `app/core/brokerage_access.py` — `resolve_request_brokerage_context()` requires an
  **active `DBBrokerageMember`** for the user; the brokerage is chosen by membership or an explicit
  `X-Brokerage-Id` header (frontend stores it in `localStorage['dalya:selected-brokerage-id']`).
- `app/core/multitenant_context.py` — `legacy_default_context()` returns the **pre-migration
  Mahoroba/Eric** context (test/fallback only). Mahoroba is the canonical legacy tenant.
- **Implication:** to log in as Eric, there must be (a) a real Supabase auth user, (b) a
  `DBBrokerageMember(user_id=<that uuid>, brokerage_id="mahoroba-realty", status="active")`, and
  (c) a `DBAgentProfile`. The seed creates (b)+(c); (a) is a **manual input** — see `07-MANUAL-INPUTS.md §6`.

## Existing Mahoroba/Eric seed identity (reuse these)

- `scripts/migrate_multitenant_phase1.py`: `MAHOROBA_BROKERAGE_ID = "mahoroba-realty"`,
  `MAHOROBA_REAL_ESTATE_NUMBER = "1858"`, `DEFAULT_MAHOROBA_AGENTS_AI = "+971500000099"`,
  Brokerage AI from `DALYA_PHONE_NUMBER` (default `+971500000001`). Eric: user_id `eric-mahoroba-seed`,
  email `ericzhu0702@gmail.com`, phone `+971500000010`, RERA `BRN-PLACEHOLDER-ERIC`.
- `scripts/chatbot_full_test.py`: already seeds a one-workspace Mahoroba/Eric setup —
  member `demo-member-eric-mahoroba`, profile `demo-agent-profile-eric-mahoroba`,
  chatbot config `demo-agent-chatbot-config-eric-mahoroba`, email `eric@mahoroba.local`. Good template
  for the pilot seed's agent/profile/config rows.
- `scripts/seed_agent_dashboard_v1.py`: idempotent dashboard seed (brokerage, agent, listing,
  conversation, viewing, `DBDraftReply`, `DBAIDraft`, campaign). Template for dashboard-visible rows.

## Messaging — simulated transport (the safe path)

- `app/core/messaging/factory.py` — `get_transport()` keyed off `MESSAGING_TRANSPORT`
  (`twilio` default / `dialog360` stub / `simulated`). `simulated` is **blocked in live envs**
  (`is_live_environment()`), so `DALYA_ENV` must be `development`/`test`/`staging`.
  `set_transport_override()` injects a transport directly in tests.
- `app/core/messaging/simulated_transport.py` — `SimulatedTransport` captures every outbound in
  `outbox` and lets the caller inject inbound buyer/agent-reply messages — full round-trip with no
  live WhatsApp.
- `scripts/simulate_multitenant_flow.py` — **the model for the scenario runner.** Runs
  buyer → Property Advisor → escalation → Agents AI → agent reply → relay-back, all simulated. Verifies
  cross-brokerage isolation and offer bands. Run:
  `PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated venv/bin/python scripts/simulate_multitenant_flow.py`.

## Buyer-facing chatbot (Property Advisor)

- `app/core/chatbot_engine.py` (large) — `ChatbotEngine.handle_message_resilient()` is the main entry.
  Model `claude-haiku-4-5-20251001`. Flow: debounce → intent (`app/core/intent_classifier.py`) → prompt
  (`app/core/prompt_builder.py`) → Haiku response → validate/rewrite → escalation detect → persist →
  send → alert agent.
- Escalation types: `offer`, `marginal_offer`, `soft_offer`, `form_a`, `brn`, `regulatory`,
  `unanswerable_question`, `viewing_request`, `financing_query`.
- Inbound webhook: `POST /api/v1/whatsapp/webhook`. Debug test injectors (debug routes only):
  `POST /api/v1/whatsapp/send-test`, `/whatsapp/send-test-voice`.

## DealReadiness & Verified Facts

- `app/core/deal_readiness.py` — readiness stages:
  `new → partially_qualified → qualified → hot → viewing_ready → offer_ready → agent_takeover_required`;
  emits next-best-action / next-best-question. Surfaced in dashboard, buyer list/card, draft assist,
  hot list.
- `app/core/verified_facts.py` + seed `app/core/data/verified_facts_seed.json` (source
  `docs/domain/dubai-real-estate-verified-facts.md`) loaded into `DBListingFact`/verified-fact tables.
  Buyer answers only state facts that are verified + `buyer_safe`; otherwise rewritten to
  agent-confirmation language. Validators:
  `scripts/verify_verified_facts_output_gate.py`, `tests/test_verified_facts_output_gate.py`,
  `tests/test_verified_facts_seed_closing_costs.py`.

## Pilot-critical endpoints (full list for Agent C)

- Dashboard: `GET /agent/dashboard`, `POST /agent/hot-list/refresh`, `GET /agent/hot-list`
- Buyers: `GET /agent/buyers`, `GET /agent/buyers/{profile_id}`, `PATCH /agent/buyers/{profile_id}/fields`
- Conversation: `GET /agent/leads/{conversation_id}`, `POST /agent/leads/{id}/ai-mode`,
  `POST /agent/leads/{id}/actions`, `POST /agent/leads/{id}/draft-reply`, `POST /agent/leads/{id}/reassign`
- Escalations: `GET /agent/escalations`, `POST /agent/escalations/{thread_id}/reply`,
  `POST /agent/escalations/{thread_id}/resolve`
- Drafts: `GET /agent/drafts`, `PATCH /agent/drafts/{id}`, `POST /agent/drafts/{id}/send|reject|snooze`
- Tasks: `POST /agent/tasks/{id}/done|snooze`
- Offers: `POST /agent/offers`, `GET /agent/offers`, `POST /agent/offers/{id}/confirm|discard|transition`
- Viewings: `GET/PATCH /agent/listings/{id}/logistics`, `GET/POST /agent/availability-blocks`,
  `POST /agent/leads/{id}/viewings/propose`, `GET /agent/viewings`, `GET /agent/viewings/{id}`,
  `POST /agent/viewings/{id}/confirm|cancel|complete`, `/notification-drafts`, `/tenant-notice/send`,
  `/feedback/request|agent|draft-follow-up`, `GET /agent/viewings/{id}/brief`
- Media: `POST /agent/leads/{id}/media`, `/media/from-listing`, `GET /agent/listings/{id}/assets`
- Lead ingest: `POST /api/v1/leads/ingest/email` (secret-guarded via `LEAD_INGEST_SECRET`; parsers
  `property_finder:v1`, `bayut:v1` in `app/core/lead_ingest.py`)
- Listings/knowledge: `POST /listings`, `/listings/draft-from-url`, `/listings/{id}/documents`,
  `GET /listings/{id}/knowledge`, `PATCH /listings/{id}/facts/{fact_id}`

## Frontend `/agent` route tree

| Route | Component | Loads |
|-------|-----------|-------|
| `/agent` | `AgentDashboard` | `GET /agent/dashboard` |
| `/agent/buyers` | `BuyerList` | `GET /agent/buyers?filter=&sort=` |
| `/agent/buyers/[id]` | `BuyerCard` | `GET /agent/buyers/{id}` |
| `/agent/conversations/[id]` | `ConversationDetail` | `GET /agent/leads/{id}` |
| `/agent/drafts` | `DraftQueue` | `GET /agent/drafts` |
| `/agent/escalations` | `EscalationInbox` | `GET /agent/escalations` |
| `/agent/viewings` + `/[id]` | `ViewingCalendar`/`ViewingDetail` | `GET /agent/viewings` |
| `/agent/calendar` | calendar OAuth form | `GET /agent/calendar-connection` |

**⚠ Demo-fallback data to watch for:** `frontend/src/components/agent-dashboard/fallback-data.ts`
(14 tasks / 9 buyers / 4 viewings / 3 escalations) renders on **API error**, with a warning banner.
`live-shell-data.ts` is the empty first-load shell. A healthy seeded load must show **pilot data, not
fallback rows** — confirming this is an explicit pilot check (the brief calls it out).

## Key DB models (in `app/models/db_models.py`, 63 total)

`DBBrokerage`, `DBBrokerageMember`, `DBAgentProfile`, `DBAgentChatbotConfig`, `DBListing`,
`DBListingLogistics`, `DBListingDocument`, `DBListingFact`, `DBListingKnowledgeSummary`,
`DBConversation`, `DBMessage`, `DBBrokerageBuyerProfile`, `DBBuyerProfile`, `DBBuyerProfileField`
(provenance: `ai_inferred` vs `agent_confirmed`), `DBBuyerSuppression` (opt-out), `DBOffer`/
`DBOfferRecord`, `DBEscalationThread`/`DBEscalationThreadQuestion`, `DBViewing`/`DBViewingFeedback`/
`DBTenantViewingConfirmation`, `DBDraftReply`/`DBAIDraft`, `DBLeadAssignment`/`DBLeadTask`,
`DBLeadIngestRecord`, `DBAgentMessageRoute`/`DBAgentRelaySession` (the `[Ref: TOKEN]` relay),
`DBMediaAsset`, `DBComplianceEvent`, `DBSuspiciousActivity`, `DBMessageQueue`.

## Reusable test/validation scripts

- `scripts/build_harness.py {plan|build|summary|teardown}` + `tests/harness/` — canonical multi-brokerage
  seed (Best Homes / Gemini Realty, NOT Mahoroba). Use as a reference and for chatbot persona infra.
- `scripts/chatbot_full_test.py` (24-persona QA, simulated) · `scripts/chatbot_test.py`
- `scripts/audit_tenant_isolation.py`, `scripts/audit_tenant_constraints_dal170d.py`
- `scripts/seller_summary_privacy_{contract,isolation,app_probe}.py`,
  `scripts/verify_seller_conversation_summary_privacy.py`
- `scripts/verify_verified_facts_output_gate.py`, `scripts/verify_verified_facts_rule_keys.py`
- `scripts/rls_rehearsal_dal170e1.py`, `scripts/db_role_rehearsal_dal170e4b.py` (RLS/app-role — the
  separate production gate)
- `tests/conftest.py` — `client()`, `send()`, autouse `clean_test_conversation()`. `tests/safety.py` —
  `assert_safe_test_database()`.

## Knowledge base (for off-plan listings)

`knowledge_base/*.json` (schema `knowledge_base/schema.json`), auto-loaded by `app/core/community_data.py`.
Existing: `emaar_oasis.json` (canonical; holds the "15–25% resale premium" — Oasis only),
`sobha_seahaven.json`, `emaar_address_harbour_point.json`, `nshama_town_square_*.json`,
`liv_dubai_marina_*.json`, etc. Off-plan pilot listings should map to one of these communities so
community research/verified facts render.
