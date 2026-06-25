# dalya-internal-omo-pilot - Work Plan

## TL;DR (For humans)
**What you'll get:** A smaller first-run internal Mahoroba pilot rehearsal that proves whether Eric can demo Dalya as an agent command center from `/agent`: local pilot env intake, normal-agent dashboard listing creation from PF/Bayut links, safe dependent seed/reset, simulated buyer scenarios, pilot-critical API smoke, browser walkthrough, and one final report.

**Why this approach:** Claude's repo-grounded plan is the spine: use canonical `mahoroba-realty`, real Supabase/JWT constraints, `SimulatedTransport`, `scripts/pilot/`, and the actual `/agent` route tree. Codex contributes the product verdict questions and golden/stress framing. LazyCodex contributes lanes, evidence discipline, and final verification.

**What it will NOT do:** It will not use real customer data, send live WhatsApp, use 360dialog, run production RLS/app-role rollout, live-write Google Calendar, or turn the first rehearsal into an exhaustive product-hardening epic.

**Effort:** Medium-large
**Risk:** Medium - the main blockers are safe DB target, Eric Supabase auth/JWT, and Anthropic key availability, not the pilot design.
**Decisions to sanity-check:** Eric should fill `.omo/pilots/lazycodex-omo-pilot/.env.pilot` with a disposable local DB or dedicated Neon test branch named `pilot`, four Property Finder/Bayut listing URLs, Eric auth path, pilot-marked DB writes/reset, and Anthropic key for chatbot mode. Buyer details can default to generated safe pilot data.

Your next move: say `$start-work` or equivalent when you want coding agents to execute this updated first-run plan. Full execution detail follows below.

---

> TL;DR (machine): Hybrid Claude-spine first-run pilot plan: canonical `mahoroba-realty`, simulated-only messaging, 4 listings, 7 buyers, core `/agent` surfaces, umbrella tracking, evidence-first execution, deferred broad checks.

## Scope
### Must have
- A separate pilot control folder under `.omo/pilots/lazycodex-omo-pilot/`.
- Local untracked env file `.omo/pilots/lazycodex-omo-pilot/.env.pilot` for manual inputs and secrets.
- Formal OMO plan under `.omo/plans/dalya-internal-omo-pilot.md`.
- Canonical brokerage id `mahoroba-realty`; no new fake brokerage unless explicitly isolated later.
- One umbrella Linear issue or nearest active issue if Linear is available; if SaaS write is blocked, record the tracking item in `BACKLOG.md` and continue execution.
- Safe Phase 0 gate proving disposable local DB or dedicated Neon test branch named `pilot` is preferred; shared staging is allowed only if Eric explicitly confirms it is isolated and safe for pilot writes. Gate must also prove `DALYA_ENV`, `PROD_DB_HOST`, `MESSAGING_TRANSPORT=simulated`, and no live-send posture.
- Four listings created through the normal agent dashboard flow at `/listings/new/portal`: paste Property Finder/Bayut URL, review prefilled draft, complete required fields, publish, capture listing id, then open `/dashboard/listings/<id>`.
- The existing authenticated `POST /api/v1/listings/draft-from-url` scraper API is used as the backend mechanism behind the dashboard flow and for supporting diagnostics, not as a substitute for the full dashboard listing-creation pass.
- Safe first-run dependent seed/reset under `scripts/pilot/`, using pilot markers and refusing non-pilot deletes or overwrites under canonical `mahoroba-realty`; seed buyers/conversations/tasks against the dashboard-created listing ids instead of creating listings directly.
- Four listing archetypes:
  - Dubai Hills ready villa for golden path.
  - Dubai Hills ready listing with incomplete facts.
  - Emaar/Oasis off-plan listing for Verified Facts and off-plan behavior.
  - Luxury/high-ticket ready listing for premium qualification and takeover.
- Seven buyer personas:
  - Adam Miller hot ready buyer.
  - Priya Shah off-plan analytical buyer.
  - Low-context buyer.
  - Hassan Ali offer buyer.
  - Mei Chen human-takeover buyer.
  - Tom Becker weak-listing buyer.
  - Opt-out buyer.
- Core surfaces:
  - `/agent`
  - Today Queue
  - `/agent/conversations/<id>`
  - `/agent/buyers`
  - `/agent/buyers/<id>`
  - `/agent/drafts`
  - `/agent/escalations?thread=<id>`
  - offers in conversation/buyer context
  - `/agent/viewings`
  - `/agent/viewings/<id>`
  - `/listings/new/portal`
  - `/dashboard/listings/<id>`
- Pilot-critical API smoke:
  - dashboard and hot-list refresh
  - buyers and buyer card
  - conversation detail and AI mode
  - drafts list/edit/send/reject/snooze
  - escalations list/reply/resolve
  - offers create/confirm/discard/transition
  - viewings list/detail/propose/confirm/complete
- Minimal safety sanity:
  - wrong brokerage/wrong agent/unauth access denied for pilot-critical resources
  - opt-out suppression blocks sends
  - no live WhatsApp
  - no fallback/sample dashboard rows on healthy load
  - unsupported Verified Facts claims defer/escalate
- Golden-path and stress-path demo scripts with pass/fail/blocked status.
- Final report with verdict, demo script, filled matrix, screenshots/transcripts, top findings, blockers before external pilot, and suggested next tickets.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- No real customer data.
- No production/live external customer pilot claim.
- No live WhatsApp or Twilio production send in first run.
- No 360dialog/BSP pilot.
- No production DDL. No schema creation/DDL on shared staging. Staging writes are allowed only after Eric explicitly confirms the target is isolated and pilot-safe; no production RLS/app-role rollout or Task 10b certification.
- No live Google Calendar write in first run.
- No broad tenant/security sweep beyond first-run sanity checks.
- No media/voice flow as a required first-run pass; document graceful fallback or defer.
- No lead ingest as a required first-run pass; keep it deferred unless it already works cleanly and costs little to run.
- No owner dashboard, campaign, broad CRM, or legacy marketplace polish.
- No broad abstractions just for test data.
- No modification of unrelated code.
- No fallback/sample dashboard rows as success.

## Verification strategy
> Zero human intervention for verification after required manual inputs are supplied.
- Test decision: tests-after for new pilot tooling; characterization before refactors; none for pure report/template edits.
- Frameworks: pytest/TestClient for backend/API, existing `SimulatedTransport`/chatbot harness patterns for scenarios, browser automation for `/agent`, JSON/Markdown artifacts for evidence.
- Evidence root: `.omo/evidence/lazycodex-omo-pilot/`.
- Report root: `reports/internal_pilot/mahoroba_first_run/`.
- Execution modes:
  - **Smoke mode:** seed/API checks, and browser checks only when auth exists, without live chatbot if `ANTHROPIC_API_KEY` is missing. API checks run without Eric JWT using service/test context must be marked `SMOKE PASS`, not full `PASS`.
  - **Chatbot mode:** scenario runner through Property Advisor; requires `ANTHROPIC_API_KEY`.
  - **Browser mode:** `/agent` as Eric; requires Supabase auth user/JWT/session.
  - **Live/sandbox transport mode:** explicitly out of first run; separate approval only.
- Required evidence:
  - Safety gate transcript proving no production DB/live transport.
  - Dashboard listing-creation evidence for all four source URLs: screenshots/action transcript, scraper draft status, publish status, listing ids, and `/dashboard/listings/<id>` confirmation.
  - Seed summary with entity counts, pilot markers, and linkage to dashboard-created listing ids.
  - Scenario JSON for golden and stress buyers, or explicit BLOCKED state per missing dependency.
  - API smoke JSON with endpoint status and state assertions.
  - Browser screenshots plus action transcript for route-backed surfaces.
  - Final report Markdown and matrix, including explicit yes/no for Smoke mode, Chatbot mode, Browser mode, and a verdict based only on the modes actually run.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except final/report) means you under-split.
- Wave 0: Create/attach one umbrella tracking issue if available, or record `BACKLOG.md` fallback; run safety gate; resolve manual blockers.
- Wave 1: Build dashboard listing-creation harness, dependent seed/reset, scenario runner, and report skeleton in parallel after the safety gate.
- Wave 2: Run buyer simulation, API smoke, minimal safety sanity, and browser walkthrough in parallel after seed.
- Wave 3: Pair buyer simulation + browser QA for golden/stress demos; synthesize final report.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| T1 | none | T10 | T2 |
| T2 | DB approval | T3, T6, T7, T8, T9 | T1, T4, T5 planning work |
| T3 | T2 + Eric browser auth | T4, T6, T7, T8, T9 | T5 |
| T4 | T3 | T6, T8, T9 | T5 |
| T5 | T2 | T9, T10 | T3, T4 |
| T6 | T3, T4 | T8, T9 | T7 |
| T7 | T3 | T8, T9 | T6 |
| T8 | T6, T7 | T10 | none |
| T9 | T6, T7 | T10 | T8 |
| T10 | T8, T9 | final verification | none |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [ ] 1. Kick off umbrella tracking and confirm manual blockers.
  What to do / Must NOT do: Create or attach one umbrella Linear issue for the first-run internal Mahoroba pilot if Linear is available. If external SaaS writes are blocked, record one umbrella tracking item in `BACKLOG.md` and continue instead of blocking execution. Confirm required inputs through `.omo/pilots/lazycodex-omo-pilot/.env.pilot`: safe DB target + `PROD_DB_HOST`, four Property Finder/Bayut listing URLs, Eric Supabase auth/JWT path for browser mode, pilot seed/reset permission, and `ANTHROPIC_API_KEY` for chatbot mode. Do not create per-subtask ticket sprawl before the first rehearsal. Do not print or summarize env secret values.
  Parallelization: Wave 0 | Blocked by: none | Blocks: T10 tracking closeout only
  References (executor has NO interview context - be exhaustive): `AGENTS.md` delivery tracking; `BACKLOG.md`; `claude-pilot/07-MANUAL-INPUTS.md`; `.omo/pilots/lazycodex-omo-pilot/manual-inputs.md`
  Acceptance criteria (agent-executable): Final report records either the umbrella Linear issue id or the `BACKLOG.md` fallback tracking entry; `BACKLOG.md` names the pilot run; missing hard blockers are marked BLOCKED with exact fallback mode.
  QA scenarios (name the exact tool + invocation): happy `test -f .omo/pilots/lazycodex-omo-pilot/.env.pilot && rg -n "internal Mahoroba pilot|lazycodex-omo-pilot|Linear|BACKLOG fallback" BACKLOG.md reports/internal_pilot/mahoroba_first_run/PILOT-REPORT.md`; failure simulate blocked Linear write or omit Linear credentials and prove `BACKLOG.md` fallback exists while later safety/seed work is still allowed to proceed. Evidence `.omo/evidence/lazycodex-omo-pilot/task-1-tracking.txt`
  Commit: Y | docs(pilot): track first-run Mahoroba pilot

- [ ] 2. Build Phase 0 safety gate and reset policy.
  What to do / Must NOT do: Add or reuse `scripts/pilot/check_safety_gate.py` and reset policy for first-run pilot. Preferred DB target is disposable local DB or a dedicated Neon test branch named `pilot`. Shared staging is allowed only if Eric explicitly confirms it is isolated and safe for pilot writes. Prove `DALYA_ENV` is `development|test|pilot` or explicitly confirmed isolated `staging`, `DATABASE_URL` host differs from `PROD_DB_HOST`, `MESSAGING_TRANSPORT=simulated`, and reset can delete only rows carrying `dalya_pilot=mahoroba-first-run` or `pilot_` ids. Agents may load an approved test/dev env file to run commands, but must not print, copy, summarize, or inspect secrets; production env files are out of scope. Do not create schema/DDL on shared staging and do not bypass `tests.safety.assert_safe_test_database()`.
  Parallelization: Wave 0 | Blocked by: DB approval | Blocks: T3, T6, T7, T8, T9
  References: `tests/harness/README.md`; `tests/safety.py`; `docs/runbooks/dalya-friendly-pilot-readiness-runbook.md`; `claude-pilot/08-SAFETY-GUARDRAILS.md`; `app/core/messaging/factory.py`; `app/core/runtime_config.py`
  Acceptance criteria: Gate command passes on approved local/test/Neon-`pilot` env and refuses production-like env; shared staging is refused unless an explicit isolation confirmation is recorded; reset dry-run lists only pilot-marked records; live transport is refused.
  QA scenarios: happy `PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated venv/bin/python scripts/pilot/check_safety_gate.py --pilot-marker mahoroba-first-run`; failure `DALYA_ENV=production DATABASE_URL=postgresql://example.invalid/prod PROD_DB_HOST=example.invalid MESSAGING_TRANSPORT=twilio venv/bin/python scripts/pilot/check_safety_gate.py --pilot-marker mahoroba-first-run` exits non-zero before any DB write; failure shared staging without explicit isolation confirmation exits non-zero before DDL or data writes. Evidence `.omo/evidence/lazycodex-omo-pilot/task-2-safety.json`
  Commit: Y | chore(pilot): add first-run safety gate

- [ ] 3. Create four listings through the normal agent dashboard flow, then build dependent seed/reset.
  What to do / Must NOT do: Load `.env.pilot` without printing secret values. Read `PILOT_LISTING_GOLDEN_READY_URL`, `PILOT_LISTING_INCOMPLETE_READY_URL`, `PILOT_LISTING_OFFPLAN_URL`, and `PILOT_LISTING_LUXURY_READY_URL`. As Eric in the browser, open `/listings/new`, choose "Paste from Property Finder / Bayut", paste each URL into `/listings/new/portal`, wait for the scraper-prefilled draft, review/complete required fields such as commission/threshold when needed, publish, capture the "Listing created" state, listing id, and `/dashboard/listings/<id>` page. Use `POST /api/v1/listings/draft-from-url` and `POST /api/v1/listings` only as the authenticated backend calls made by the dashboard or for diagnostics; direct script/API creation cannot satisfy the full listing-creation pass. After the four dashboard-created listing ids exist, add or reuse `scripts/pilot/seed_mahoroba_pilot.py` and `scripts/pilot/reset_mahoroba_pilot.py` for dependent pilot rows: Eric membership/profile if needed, Sara/Omar/Lina supporting agents, 7 generated buyers, conversations/messages, 2-3 drafts, 2 offers, 1-2 viewings, and 3-4 escalation threads linked to the created listings. Tag every dependent row. Seed/reset may add pilot-marked child rows under `mahoroba-realty`, but must never delete or overwrite existing non-pilot Mahoroba records, settings, agents, listings, conversations, or memberships. Do not create `mahoroba-internal-pilot` or any new brokerage id in first run. Do not invent portal-only listing facts that were not scraped, shown in the dashboard draft, or explicitly provided.
  Parallelization: Wave 1 | Blocked by: T2 + Eric browser auth + four listing URLs | Blocks: T4, T6, T7, T8, T9
  References: `frontend/src/app/(app)/listings/new/page.tsx`; `frontend/src/app/(app)/listings/new/portal/page.tsx`; `frontend/src/components/listings/NewListingFlow.tsx`; `frontend/src/components/listings/FinishedListingFlow.tsx`; `app/api/listings.py`; `app/core/listing_scraper.py`; `claude-pilot/01-REPO-FINDINGS.md`; `claude-pilot/02-SEED-DATASET.md`; `scripts/chatbot_full_test.py`; `scripts/seed_agent_dashboard_v1.py`; `scripts/migrate_multitenant_phase1.py`; `app/models/db_models.py`
  Acceptance criteria: Browser evidence shows four listing creations through `/listings/new/portal`, each with source URL classification, scraper draft status, publish status, listing id, and `/dashboard/listings/<id>` confirmation; seed is idempotent for dependent rows; seed summary reports canonical brokerage `mahoroba-realty`, 4 dashboard-created listings, 7 buyers, expected drafts/offers/viewings/escalations; reset refuses without `DALYA_PILOT_CONFIRM=mahoroba-realty` and deletes only pilot-marked dependent rows; non-pilot Mahoroba records are read-only collision context and never overwritten.
  QA scenarios: happy start backend/frontend, sign in as Eric, create all four listings via `/listings/new/portal`, then run `PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated venv/bin/python scripts/pilot/seed_mahoroba_pilot.py --env-file .omo/pilots/lazycodex-omo-pilot/.env.pilot --use-dashboard-listing-ids .omo/evidence/lazycodex-omo-pilot/listing-creation/listing-ids.json --apply --summary .omo/evidence/lazycodex-omo-pilot/seed-summary.json`; failure missing browser auth or missing URL marks listing creation BLOCKED, not PASS; failure direct script/API listing creation alone is labeled `SMOKE PASS` or diagnostic only, not full listing pass; failure rerun seed and assert dependent counts unchanged, then `DALYA_PILOT_CONFIRM=wrong venv/bin/python scripts/pilot/reset_mahoroba_pilot.py --dry-run` exits non-zero. Evidence `.omo/evidence/lazycodex-omo-pilot/task-3-dashboard-listings-and-seed.json`
  Commit: Y | test(pilot): create pilot listings through dashboard flow

- [ ] 4. Build first-run scenario runner over simulated transport.
  What to do / Must NOT do: Add `scripts/pilot/run_scenarios.py` modeled on `scripts/simulate_multitenant_flow.py` and existing chatbot harness patterns. Required scenarios: `hot_ready_buyer`, `offplan_verified_facts`, `low_context_price_buyer`, `firm_offer_escalation`, `human_takeover`, `weak_listing_fact_gap`, `opt_out`. If `ANTHROPIC_API_KEY` is missing, runner must mark chatbot scenarios BLOCKED and still emit a useful smoke-mode report if possible. Do not require media/voice or lead ingest in first run.
  Parallelization: Wave 1 | Blocked by: T2 | Blocks: T6, T8, T9
  References: `scripts/simulate_multitenant_flow.py`; `scripts/chatbot_full_test.py`; `app/core/messaging/simulated_transport.py`; `app/api/whatsapp.py`; `app/core/chatbot_engine.py`; `app/core/verified_facts_output_gate.py`; `claude-pilot/05-DEMO-SCRIPTS.md`; `.omo/pilots/lazycodex-omo-pilot/scenario-matrix.md`
  Acceptance criteria: Runner emits one JSON per scenario plus aggregate pass/fail/blocked; required assertions cover one-question qualification, Verified Facts deferral, offer escalation/history, human takeover/AI pause, weak listing safe failure, opt-out suppression, and no seller-private leakage.
  QA scenarios: happy `PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated venv/bin/python scripts/pilot/run_scenarios.py --suite first-run --brokerage-id mahoroba-realty --evidence-dir .omo/evidence/lazycodex-omo-pilot/scenarios`; failure `ANTHROPIC_API_KEY= PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated venv/bin/python scripts/pilot/run_scenarios.py --suite first-run --brokerage-id mahoroba-realty --evidence-dir .omo/evidence/lazycodex-omo-pilot/scenarios-no-llm` exits 0 with scenarios marked BLOCKED, not PASS. Evidence `.omo/evidence/lazycodex-omo-pilot/task-4-scenarios.json`
  Commit: Y | test(pilot): add first-run buyer scenarios

- [ ] 5. Build report skeleton and matrix generator.
  What to do / Must NOT do: Add or reuse a report generator that outputs `reports/internal_pilot/mahoroba_first_run/PILOT-REPORT.md`, `matrix.md`, `scenario-results.json`, command logs, and screenshot references. It must show Smoke mode yes/no, Chatbot mode yes/no, Browser mode yes/no, and the full first-run verdict based on which modes actually ran. It should make missing artifacts BLOCKED, not PASS. Do not hand-write final status from memory.
  Parallelization: Wave 1 | Blocked by: T2 | Blocks: T9, T10
  References: `claude-pilot/04-TEST-MATRIX.md`; `claude-pilot/06-DELIVERABLES.md`; `.omo/pilots/lazycodex-omo-pilot/report-template.md`; `scripts/generate_test_report.py`
  Acceptance criteria: Report generator creates the expected directory, renders partial evidence with explicit BLOCKED rows, labels service/test-context API checks as `SMOKE PASS`, and includes Green/Yellow/Red thresholds.
  QA scenarios: happy `venv/bin/python scripts/pilot/generate_report.py --input .omo/evidence/lazycodex-omo-pilot --output reports/internal_pilot/mahoroba_first_run`; failure `venv/bin/python scripts/pilot/generate_report.py --input .omo/evidence/lazycodex-omo-pilot/missing --output /tmp/dalya-mahoroba-pilot-missing` marks required sections BLOCKED. Evidence `.omo/evidence/lazycodex-omo-pilot/task-5-report.json`
  Commit: Y | docs(pilot): generate first-run report

- [ ] 6. Run pilot-critical API smoke.
  What to do / Must NOT do: Add `tests/pilot/test_pilot_smoke.py` or `scripts/pilot/verify_api_smoke.py` covering only first-run critical endpoints: dashboard/hot-list, buyers/card, conversation detail/AI mode, drafts, escalations, offers, viewings. Use Eric JWT + `X-Brokerage-Id: mahoroba-realty` when available; otherwise mark auth-gated browser/API paths BLOCKED and run safe service/test-context smoke only if existing test patterns allow it. API checks run without Eric JWT must be labeled `SMOKE PASS`, not full `PASS`, and cannot satisfy browser/auth readiness. Do not include lead ingest/media as required first-run checks.
  Parallelization: Wave 2 | Blocked by: T3, T4 | Blocks: T8, T9
  References: `claude-pilot/01-REPO-FINDINGS.md`; `app/api/agent_dashboard.py`; `app/api/agent.py`; `app/api/viewings.py`; `tests/conftest.py`; `tests/test_escalation_inbox_api.py`; `tests/test_draft_queue_api.py`; `tests/test_viewing_logistics.py`
  Acceptance criteria: Smoke output records method, endpoint, auth mode, status, key assertion, and pass/fail/blocked; mutations re-GET correctly; fallback rows are not treated as success; service/test-context checks are explicitly separated from real Eric auth checks.
  QA scenarios: happy `PYTHONPATH=$(pwd) venv/bin/python -m pytest tests/pilot/test_pilot_smoke.py -q --pilot-brokerage-id=mahoroba-realty`; failure run wrong brokerage context and assert buyer/conversation/escalation access is denied or blocked with explicit auth limitation. Evidence `.omo/evidence/lazycodex-omo-pilot/task-6-api-smoke.json`
  Commit: Y | test(pilot): smoke first-run agent APIs

- [ ] 7. Run `/agent` browser walkthrough as Eric.
  What to do / Must NOT do: Drive the real frontend routes after Eric auth is available: `/agent`, Today Queue links, `/agent/conversations/<id>`, `/agent/buyers`, `/agent/buyers/<id>`, `/agent/drafts`, `/agent/escalations?thread=<id>`, `/agent/viewings`, `/agent/viewings/<id>`. Capture desktop screenshots and action transcript. If Supabase login/JWT is missing, mark browser mode BLOCKED and do not fake it with static HTML or fallback data.
  Parallelization: Wave 2 | Blocked by: T3 | Blocks: T8, T9
  References: `claude-pilot/01-REPO-FINDINGS.md`; `frontend/src/app/(app)/agent/**`; `frontend/src/components/agent-dashboard/fallback-data.ts`; `frontend/src/components/agent-dashboard/AgentDashboard.tsx`; `frontend/src/components/conversations/ConversationDetail.tsx`; `frontend/src/components/buyers/**`; `frontend/src/components/drafts/DraftQueue.tsx`; `frontend/src/components/escalations/EscalationInbox.tsx`; `frontend/src/components/viewings/**`; `frontend/src/lib/api.ts`
  Acceptance criteria: Browser evidence proves healthy seeded data, no fallback warning/banner/rows, working Today Queue links, and visible next actions. Missing auth is a top blocker, not a pass.
  QA scenarios: happy start backend on `:8000`, frontend on `:3001`, open `http://localhost:3001/agent`, sign in as Eric, save screenshots/transcript under `.omo/evidence/lazycodex-omo-pilot/browser/`; failure clear `localStorage['dalya:selected-brokerage-id']` or use wrong brokerage and assert context-required/denied behavior rather than fake rows. Evidence `.omo/evidence/lazycodex-omo-pilot/task-7-browser.json`
  Commit: Y | test(pilot): verify first-run agent UI

- [ ] 8. Run golden and stress rehearsal.
  What to do / Must NOT do: Execute the golden path and stress path from the updated scenario matrix. Golden: Adam ready buyer -> Today Queue -> conversation brief -> viewing -> draft. Stress: Priya Verified Facts, low-context buyer, Hassan offer, Mei takeover, Tom weak listing, opt-out. Pair scenario runner evidence with browser/API state. Do not broaden into lead ingest/media/Google live write.
  Parallelization: Wave 3 | Blocked by: T6, T7 | Blocks: T10
  References: `claude-pilot/05-DEMO-SCRIPTS.md`; `.omo/pilots/lazycodex-omo-pilot/scenario-matrix.md`; `app/core/deal_readiness.py`; `app/core/hot_list.py`; `app/core/conversation_takeover.py`; `app/core/offers.py`; `app/core/verified_facts_output_gate.py`
  Acceptance criteria: Golden/stress report has step-by-step expected vs actual, DB/API/screenshot evidence for each step, and a verdict of PASS/FAIL/BLOCKED for each scenario.
  QA scenarios: happy `PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated venv/bin/python scripts/pilot/run_scenarios.py --suite demo --brokerage-id mahoroba-realty --evidence-dir .omo/evidence/lazycodex-omo-pilot/demo` plus browser replay of generated links; failure remove/mark missing L2 facts and prove Tom's answer defers/escalates rather than inventing. Evidence `.omo/evidence/lazycodex-omo-pilot/task-8-demo.json`
  Commit: Y | test(pilot): capture first-run demo rehearsal

- [ ] 9. Run minimal safety sanity.
  What to do / Must NOT do: Verify no live sends, opt-out suppression, wrong brokerage/wrong agent/unauth denial on pilot-critical resources, no seller-private leakage in buyer text, and Verified Facts unsupported claims defer/escalate. This is not a full tenant/security audit. Do not run production RLS/app-role rollout.
  Parallelization: Wave 3 | Blocked by: T6, T7 | Blocks: T10
  References: `claude-pilot/08-SAFETY-GUARDRAILS.md`; `docs/runbooks/dalya-friendly-pilot-readiness-runbook.md`; `tests/test_brokerage_context_dal172.py`; `tests/test_security_p0_hardening.py`; `tests/test_verified_facts_output_gate.py`; `tests/test_conversation_takeover.py`; `app/core/brokerage_access.py`; `app/core/verified_facts_output_gate.py`
  Acceptance criteria: Safety JSON states PASS/FAIL/BLOCKED for each minimal check and explicitly says full tenant audit, media signing depth, live provider readiness, and RLS/app-role are deferred.
  QA scenarios: happy `PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated venv/bin/python scripts/pilot/verify_minimal_safety.py --brokerage-id mahoroba-realty --evidence .omo/evidence/lazycodex-omo-pilot/minimal-safety.json`; failure wrong brokerage/wrong-agent probe must return denied or BLOCKED due to missing auth, never PASS. Evidence `.omo/evidence/lazycodex-omo-pilot/task-9-safety.json`
  Commit: Y | test(pilot): verify minimal pilot safety

- [ ] 10. Assemble final first-run report and next tickets.
  What to do / Must NOT do: Merge evidence into `reports/internal_pilot/mahoroba_first_run/PILOT-REPORT.md`: executive verdict, execution modes run, dashboard listing-creation status/source URL categories, demo script, matrix, top findings, seed dataset as run, golden path, stress path, blockers before real customer pilot, commands run, suggested next PRs/tickets. Update `BACKLOG.md` delivered status for the umbrella issue or fallback tracking item. Do not claim external/friendly/live readiness if any guardrail remains blocked.
  Parallelization: Wave 3 final | Blocked by: T8, T9 | Blocks: final verification
  References: `claude-pilot/06-DELIVERABLES.md`; `.omo/pilots/lazycodex-omo-pilot/report-template.md`; `BACKLOG.md`; `docs/runbooks/dalya-friendly-pilot-readiness-runbook.md`
  Acceptance criteria: Report exists, links every evidence artifact, names the single biggest verdict driver, lists manual inputs still missing, converts failures into small suggested tickets, and applies demo pass thresholds: Green means Browser mode + Chatbot mode + API smoke all pass for golden path and stress path has no unsafe claims; Yellow means golden path is demo-able but some stress/API/browser items are blocked or rough; Red means `/agent` cannot load real pilot data, fallback rows appear, unsafe claims leak, or agent actions cannot be completed.
  QA scenarios: happy `venv/bin/python scripts/pilot/generate_report.py --input .omo/evidence/lazycodex-omo-pilot --output reports/internal_pilot/mahoroba_first_run --final`; failure missing browser evidence marks browser mode BLOCKED and verdict cannot be Green. Evidence `.omo/evidence/lazycodex-omo-pilot/task-10-final-report.json`
  Commit: Y | docs(pilot): publish first-run Mahoroba report

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit: verify each todo has evidence, missing dependencies are BLOCKED not PASS, and either one umbrella Linear issue or one `BACKLOG.md` fallback tracking item is recorded.
- [ ] F2. Code quality review: audit any new `scripts/pilot/` and `tests/pilot/` files for idempotency, safe deletes, tenant scoping, no live sends, and no broad framework drift.
- [ ] F3. Real browser QA: drive `/agent` from the report's exact demo script and verify screenshots/transcripts match seeded data with no fallback rows.
- [ ] F4. Scope fidelity: verify first run did not drift into lead ingest/media/voice/Google live write/full tenant sweep/production RLS/360dialog/real customer data.

## Commit strategy
- Use atomic Conventional Commits if Eric authorizes commits.
- Do not auto-commit from planning mode.
- Suggested execution commits:
  - `docs(pilot): track first-run Mahoroba pilot`
  - `chore(pilot): add first-run safety gate`
  - `test(pilot): seed canonical Mahoroba first run`
  - `test(pilot): add first-run buyer scenarios`
  - `test(pilot): smoke first-run agent APIs`
  - `test(pilot): verify first-run agent UI`
  - `docs(pilot): publish first-run Mahoroba report`
- Final commit footer, if committed from this plan:
  `Plan: .omo/plans/dalya-internal-omo-pilot.md`

## Success criteria
- Safety gate proves test/dev DB, non-production host, simulated transport, and reset-only pilot rows.
- Four listings are created through `/listings/new/portal` as Eric, using the four `.env.pilot` Property Finder/Bayut URLs; direct API/script creation alone cannot count as the full listing pass.
- Seed loads canonical `mahoroba-realty` workspace with pilot-marked dependent rows linked to dashboard-created listings and no duplicate rerun behavior.
- Eric can open `/agent` in browser mode, or missing Supabase auth is marked as the top blocker.
- `/agent` healthy load shows seeded data, not fallback/sample rows.
- Today Queue links route to real conversation/escalation/viewing/draft/buyer work.
- Golden path proves Adam from inquiry to readiness/viewing/draft/agent action.
- Stress path proves Priya, low-context buyer, Hassan, Mei, Tom, and opt-out behavior without unsafe claims.
- API smoke proves pilot-critical endpoints or marks auth/env blockers precisely.
- API checks without Eric JWT are labeled `SMOKE PASS` and cannot satisfy browser/auth readiness.
- Minimal safety proves no live sends, opt-out suppression, wrong-context denial where testable, no seller-private leakage, and Verified Facts deferral.
- Final report gives Smoke/Chatbot/Browser mode yes/no, Green/Yellow/Red internal-demo verdict, demo script, matrix, evidence links, blockers before external pilot, and suggested next tickets.
