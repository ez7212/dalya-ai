# 00 — Master Execution Plan

**Pilot:** Dalya MVP full end-to-end internal rehearsal · **Brokerage:** Mahoroba Realty ·
**Main agent:** Eric Zhu · **Mode:** seeded rehearsal, simulated transport, test DB only.

This is the orchestration spine. It defines the phases, what runs in what order, which agent owns
what, and what "done" looks like. Task packets live in `03-AGENT-WORKSTREAMS.md`.

---

## 0. Definition of success

A green/yellow/red verdict on **"Can Eric demo Dalya live as Mahoroba's agent command center?"**,
backed by:
- A seeded Mahoroba workspace that loads at `/agent` with real (pilot) data, no demo-fallback rows.
- A repeatable golden-path demo (10–15 min) and stress-path demo (20–30 min).
- A filled test matrix (`04-TEST-MATRIX.md`) with pass/fail/blocked per surface×scenario.
- A prioritized findings list (bugs vs UX gaps vs data/seed gaps) with file/endpoint refs.
- A blocker list for the real external pilot (RLS/app-role, live WhatsApp/360dialog, gaps found).

---

## 1. Environment & safety preconditions (Phase 0 — gate, do not skip)

Owner: **Agent A (Infra & Seed)**. Nothing else starts until these pass.

```bash
# Test/staging DB ONLY. Never production. See 08-SAFETY-GUARDRAILS.md.
export DALYA_ENV=development          # allowlist: test | staging | development (NOT production)
export DATABASE_URL='postgresql://...TEST_BRANCH_HOST/neondb?sslmode=require'
export PROD_DB_HOST='PRODUCTION_HOST_HOSTNAME_ONLY'   # denylist signal — must NOT match DATABASE_URL host
export MESSAGING_TRANSPORT=simulated  # hard requirement — no live WhatsApp
export ANTHROPIC_API_KEY=...          # real key needed for chatbot/readiness/verified-facts LLM calls
export ENABLE_DEBUG_ROUTES=true       # local only; required for /whatsapp/send-test
export DALYA_ALLOW_RUNTIME_CREATE_ALL=1  # declarative ORM auto-creates tables on a fresh test branch
```

Gate checks (all must be green):
1. `python -c "from tests.safety import assert_safe_test_database; assert_safe_test_database()"` passes.
2. `DATABASE_URL` host ≠ `PROD_DB_HOST` (proven by the guard above).
3. `python -c "from app.core.messaging.factory import get_transport; print(type(get_transport()).__name__)"`
   prints `SimulatedTransport`.
4. Backend boots: `PYTHONPATH=$(pwd) venv/bin/uvicorn app.main:app --reload --port 8000`,
   `curl localhost:8000/health` returns ok.
5. Frontend boots: `cd frontend && npm run dev` → `http://localhost:3001` (3000 is reserved).

If any gate fails, the agent **stops and documents the blocker** instead of forcing it (e.g. no test
branch available → fall back to API/UI simulation against a disposable local Postgres, and record
"DB-backed flow blocked: <reason>" in the report).

---

## 2. Phase map (dependency-ordered)

```
Phase 0  Infra & safety gate            [Agent A]            ── blocks everything
Phase 1  Seed pilot dataset             [Agent A]            ── blocks 3,4,5,6
Phase 2  Auth/login as Eric@Mahoroba    [Agent A + human]    ── blocks UI phases (4,6)
Phase 3  Buyer-side simulation          [Agent B]  ─┐
Phase 4  Backend/API smoke              [Agent C]  ─┼─ run in PARALLEL after Phase 1
Phase 5  Safety / Verified Facts / sec  [Agent D]  ─┘
Phase 6  Frontend/UI walkthrough        [Agent E]            ── after Phase 2 + Phase 3 data exists
Phase 7  Golden-path + stress-path demo [Agent B+E pair]     ── after 3–6
Phase 8  Synthesis & report             [Agent F / lead]     ── after all
```

Critical path: **0 → 1 → 2 → 6 → 7 → 8**. Phases 3/4/5 fan out off Phase 1 and rejoin at 7/8.

---

## 3. Agent roster (6 agents + 1 lead)

| Agent | Role | Owns phases | Primary outputs |
|-------|------|-------------|-----------------|
| **A — Infra & Seed** | Stand up env, write/run idempotent pilot seed + reset, resolve auth | 0,1,2 | `scripts/pilot/seed_mahoroba_pilot.py`, `scripts/pilot/reset_mahoroba_pilot.py`, login recipe |
| **B — Buyer Sim** | Drive the 7 buyer personas through the chatbot via simulated transport | 3,7 | scenario runner output, transcript+escalation log |
| **C — Backend/API** | Smoke every pilot-critical endpoint; verify DB writes | 4 | API smoke results, endpoint pass/fail |
| **D — Safety/Sec** | Verified Facts gate, seller-leak checks, tenant isolation, authz | 5 | safety matrix, leak/isolation findings |
| **E — Frontend/UI** | Click through every `/agent` surface as Eric; verify no fallback rows | 2(support),6,7 | UI walkthrough notes, screenshots/observations |
| **F — Lead/Synthesis** | Own the test matrix, merge findings, write the report, dedupe | 8 | `reports/claude-pilot-<date>/PILOT-REPORT.md` |

Agents B, C, D run concurrently. Agents map cleanly to the Dalya reviewer subagents where useful:
`dalya-chatbot-master` (B), `dalya-security-researcher` (D), `dalya-ux-designer` (E),
`dalya-real-estate-guru` (cross-check on B/D fact correctness).

---

## 4. What agents may build (smallest safe version only)

Only if it does not already exist; reuse repo patterns first (see `01-REPO-FINDINGS.md`).

1. **`scripts/pilot/seed_mahoroba_pilot.py`** — idempotent pilot seed. Extends the existing
   Mahoroba/Eric seeding pattern in `scripts/chatbot_full_test.py` (member `demo-member-eric-mahoroba`,
   profile `demo-agent-profile-eric-mahoroba`) and `scripts/seed_agent_dashboard_v1.py`. Brokerage id
   `mahoroba-realty`. All rows tagged with a `dalya_pilot` marker (id prefix `pilot_` / metadata flag).
2. **`scripts/pilot/reset_mahoroba_pilot.py`** — deletes ONLY rows carrying the pilot marker, and
   refuses to run unless `DALYA_PILOT_CONFIRM=mahoroba-realty` is set. Calls
   `assert_safe_test_database()` first.
3. **`scripts/pilot/run_scenarios.py`** — named scenario runner over `MESSAGING_TRANSPORT=simulated`,
   modeled on `scripts/simulate_multitenant_flow.py`. Scenarios: `hot_ready_buyer`,
   `offplan_verified_facts`, `low_context_price_buyer`, `firm_offer_escalation`, `human_takeover`,
   `opt_out`, `viewing_coordination`, `media_voice` (or documents the limitation). Emits
   expected-vs-actual state diffs to JSON.
4. **`tests/pilot/test_pilot_smoke.py`** — narrow deterministic smoke over the pilot-critical
   endpoints (dashboard, buyers, buyer card, conversation detail, escalations list/reply/resolve,
   drafts list/send/reject/snooze, offers, viewings, lead ingest). Not a new framework — pytest +
   existing `client()`/`send()` fixtures from `tests/conftest.py`.
5. **`scripts/pilot/verify_frontend_payloads.py`** (optional) — asserts dashboard/Today-Queue/buyer
   payloads are present and correctly routed (escalations → `/agent/escalations?thread=<id>`).

**Do NOT build:** production onboarding, live WhatsApp send, RLS production rollout, owner/admin/
campaign polish, new abstractions for test data, or anything in the "do not write" list in the brief.

---

## 5. Execution sequence (the actual run)

1. **Agent A** runs Phase 0 gate → Phase 1 seed → prints a seed summary (counts per entity) → Phase 2
   resolves how Eric logs in (see `02-SEED-DATASET.md §Auth` and `07-MANUAL-INPUTS.md §6`).
2. **Agents B, C, D** start in parallel against the seeded data.
   - B runs `run_scenarios.py` for all 7 personas, captures buyer reply + escalation + DB deltas.
   - C runs `test_pilot_smoke.py` + manual `curl`/httpie probes with Eric's JWT, records each route.
   - D runs the Verified Facts / safety / isolation probes (reuse `scripts/verify_verified_facts_output_gate.py`,
     `scripts/seller_summary_privacy_*.py`, `scripts/audit_tenant_isolation.py`).
3. **Agent E** logs into `/agent` as Eric, walks every surface, confirms data matches what B/C seeded,
   and confirms **no demo-fallback rows** render (the `fallback-data.ts` path must NOT be visible on a
   healthy load).
4. **Agents B+E** run the golden-path then stress-path demo scripts (`05-DEMO-SCRIPTS.md`) end to end,
   noting every expected dashboard change vs actual.
5. **Agent F** merges everything into the report (`06-DELIVERABLES.md`), assigns the verdict, writes
   the blocker list and the suggested PRs/tickets (one branch each).

Each agent appends its raw command log to `reports/claude-pilot-<date>/commands/<agent>.md` so the
final "Commands run" section is just a merge.

---

## 6. Stop conditions

- **Hard stop:** safety gate fails, or any path would write to production / send live WhatsApp →
  document and halt that branch.
- **Soft stop (document, continue):** a surface 500s, a seed entity can't be created, a feature is
  missing → record as a finding with file/endpoint ref and move on. Do not "fix forward" into
  unrelated code.
- The pilot is **not** a live-customer-ready certification. RLS/app-role production rollout remains a
  separate approval gate regardless of pilot outcome (`08-SAFETY-GUARDRAILS.md §RLS`).
