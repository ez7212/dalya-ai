# Multi-Agent Execution Lanes

Use these lanes when Eric starts execution. Agents must not overwrite each
other's work, and each lane owns a distinct surface.

## Lane A - Infra, Safety, And Seed

Owns:
- Phase 0 safety gate.
- Disposable local DB or dedicated Neon `pilot` branch guard.
- Loading `.omo/pilots/lazycodex-omo-pilot/.env.pilot` without printing secret
  values.
- `MESSAGING_TRANSPORT=simulated` proof.
- Canonical `mahoroba-realty` seed/reset.
- Eric Supabase membership/profile wiring once uuid is provided.
- Dependent pilot seed rows after dashboard-created listing ids exist.

Suggested files:
- `scripts/pilot/check_safety_gate.py`
- `scripts/pilot/seed_mahoroba_pilot.py`
- `scripts/pilot/reset_mahoroba_pilot.py`
- `tests/safety.py`
- `scripts/chatbot_full_test.py`
- `scripts/seed_agent_dashboard_v1.py`
- `scripts/migrate_multitenant_phase1.py`
- `app/api/listings.py`
- `app/core/listing_scraper.py`
- `tests/harness/snapshots/`
- `scripts/refresh_harness_snapshots.py`

Must not:
- Create a new fake brokerage id for the first run.
- Delete non-pilot rows.
- Delete or overwrite existing non-pilot Mahoroba records, settings, agents,
  listings, conversations, or memberships.
- Print, copy, summarize, or inspect secrets from approved test/dev env files.
- Read production env files.
- Create schema/DDL on shared staging.
- Enable live transport.
- Create listings directly through scripts/API for the full pass; direct API
  listing creation is diagnostic or smoke evidence only.
- Treat lead ingest as part of listing creation; first-run listing creation uses
  the agent dashboard, not portal lead ingestion.

## Lane B - Buyer Simulation

Owns:
- First-run scenario runner over simulated transport.
- Seven buyer scenarios.
- Golden/stress expected-vs-actual state transitions.
- BLOCKED behavior when `ANTHROPIC_API_KEY` is missing.

Suggested files:
- `scripts/pilot/run_scenarios.py`
- `scripts/simulate_multitenant_flow.py`
- `scripts/chatbot_full_test.py`
- `app/core/messaging/simulated_transport.py`
- `app/core/chatbot_engine.py`
- `app/core/verified_facts_output_gate.py`

Must not:
- Require media/voice or lead ingest in first run.
- Fake chatbot PASS when the LLM key is missing.

## Lane C - Backend/API Smoke

Owns:
- Pilot-critical endpoint smoke.
- Mutation/re-GET checks.
- Wrong-context denial where auth allows testing.
- API evidence JSON.
- Separation between service/test-context smoke and real Eric auth pass.

Suggested files:
- `tests/pilot/test_pilot_smoke.py`
- `scripts/pilot/verify_api_smoke.py`
- `app/api/agent_dashboard.py`
- `app/api/agent.py`
- `app/api/viewings.py`
- `tests/conftest.py`

Must not:
- Build a broad new test framework.
- Make lead ingest/media required first-run checks.
- Mark API checks without Eric JWT as full PASS; they are `SMOKE PASS` only and
  cannot satisfy browser/auth readiness.

## Lane D - Frontend Browser QA

Owns:
- Creating all four pilot listings through `/listings/new/portal` as Eric.
- Pasting `PILOT_LISTING_*_URL` values into the dashboard, reviewing drafts,
  publishing, and capturing listing ids.
- `/agent` browser walkthrough as Eric.
- Fallback-data rejection.
- Today Queue route checks.
- Screenshots/action transcript.
- Browser BLOCKED state if Supabase auth is unavailable.

Suggested files:
- `frontend/src/app/(app)/agent/**`
- `frontend/src/components/agent-dashboard/fallback-data.ts`
- `frontend/src/components/agent-dashboard/AgentDashboard.tsx`
- `frontend/src/components/conversations/ConversationDetail.tsx`
- `frontend/src/components/buyers/**`
- `frontend/src/components/drafts/DraftQueue.tsx`
- `frontend/src/components/escalations/EscalationInbox.tsx`
- `frontend/src/components/viewings/**`

Must not:
- Use fallback/static data as proof.
- Count direct API/script listing creation as the full listing pass.
- Redesign surfaces during the pilot.

## Lane E - Minimal Safety Sanity

Owns:
- No live sends.
- Opt-out suppression.
- Wrong brokerage/wrong agent/unauth denial on pilot-critical resources where
  testable.
- Verified Facts unsupported-claim deferral.
- No seller-private leakage in buyer text.

Suggested files:
- `scripts/pilot/verify_minimal_safety.py`
- `tests/test_brokerage_context_dal172.py`
- `tests/test_security_p0_hardening.py`
- `tests/test_verified_facts_output_gate.py`
- `docs/runbooks/dalya-friendly-pilot-readiness-runbook.md`

Must not:
- Run production RLS/app-role rollout.
- Turn this into a full tenant/security audit.

## Lane F - Report And Synthesis

Owns:
- Umbrella issue/backlog status capture.
- Report generator.
- Filled matrix.
- Golden/stress demo script updated to reality.
- Green/Yellow/Red internal-demo verdict.
- Execution-mode disclosure: Smoke mode yes/no, Chatbot mode yes/no, Browser
  mode yes/no.
- Suggested next PRs/tickets.

Suggested outputs:
- `reports/internal_pilot/mahoroba_first_run/PILOT-REPORT.md`
- `reports/internal_pilot/mahoroba_first_run/matrix.md`
- `reports/internal_pilot/mahoroba_first_run/scenario-results.json`
- `reports/internal_pilot/mahoroba_first_run/commands/`
- `reports/internal_pilot/mahoroba_first_run/screenshots/`

Must not:
- Claim external/friendly/live readiness from first-run evidence.
- Treat a partial smoke run as stronger than the modes actually executed.
