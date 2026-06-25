# 03 — Agent Workstreams (task packets)

Hand each packet to one coding agent. Packets are self-contained: scope, inputs, steps, outputs, and
"do not." Dependencies are stated. Every agent appends its raw commands to
`reports/claude-pilot-<date>/commands/<agent>.md`.

Global rules for all agents: `MESSAGING_TRANSPORT=simulated`, test DB only, no live WhatsApp, no edits
to unrelated code, document-and-continue on soft failures, hard-stop on anything touching production.

---

## Agent A — Infra & Seed  (Phases 0,1,2) — BLOCKS ALL OTHERS

**Scope:** stand up the safe environment, write the idempotent pilot seed + reset, resolve Eric's login.

**Steps**
1. Run the Phase 0 gate exactly as in `00-EXECUTION-PLAN.md §1`. Prove `SimulatedTransport` and the
   safety guard. If the gate fails, stop and write the blocker.
2. Write `scripts/pilot/seed_mahoroba_pilot.py`:
   - Idempotent (upsert by pilot id). Calls `assert_safe_test_database()` first.
   - Creates everything in `02-SEED-DATASET.md §1–10` except live message volume.
   - Tags every row with the pilot marker. Prints a summary table (counts per entity) at the end.
   - Reuses model-insert patterns from `scripts/chatbot_full_test.py` and
     `scripts/seed_agent_dashboard_v1.py`. Off-plan listings set `community`/`project` to KB names.
3. Write `scripts/pilot/reset_mahoroba_pilot.py`: deletes only pilot-marked rows; refuses unless
   `DALYA_PILOT_CONFIRM=mahoroba-realty`; never touches non-pilot rows; calls the safety guard.
4. Resolve Eric login per `02-SEED-DATASET.md §Auth` (preferred: real Supabase test user). Record the
   chosen path, the uuid used, and how to obtain a JWT. Set `ADMIN_USER_ID` to Eric's uuid.
5. Run seed; verify counts; hand off the seed summary + login recipe to B/C/D/E.

**Outputs:** seed + reset scripts, seed summary, login recipe, Phase-0 gate evidence.
**Do not:** create production auth flows, enable live transport, run RLS production rollout.

---

## Agent B — Buyer Simulation  (Phases 3,7) — depends on A

**Scope:** drive all 7 buyer personas through the Property Advisor over simulated transport; capture
buyer reply + escalation + DB deltas. Acts as `dalya-chatbot-master`.

**Steps**
1. Write `scripts/pilot/run_scenarios.py` modeled on `scripts/simulate_multitenant_flow.py`
   (`MESSAGING_TRANSPORT=simulated`, `set_transport_override(SimulatedTransport())`). Named scenarios:
   `hot_ready_buyer, offplan_verified_facts, low_context_price_buyer, firm_offer_escalation,
   human_takeover, opt_out, viewing_coordination, media_voice`.
2. For each scenario, send the persona's messages (from `05-DEMO-SCRIPTS.md`), one turn at a time, and
   assert the expected behaviors:
   - one-question-at-a-time qualification; listing-aware answers; off-plan vs ready behavior;
     verified-facts guardrails; safe escalation on legal/process/fee uncertainty; no unsupported
     claims; no seller-sensitive leakage; no raw internal notes in buyer text.
3. Record per turn: buyer-facing text, intent, escalation type/thread, readiness stage transition,
   and the resulting DB rows (conversation, messages, offers, escalations, suppression).
4. Emit `reports/.../scenarios/<name>.json` with expected-vs-actual and a pass/fail per assertion.
5. In Phase 7, pair with Agent E to run golden + stress demo end to end.

**Outputs:** scenario runner + per-scenario JSON + a buyer-side findings list (chatbot quality, safety).
**Do not:** weaken safety assertions to make a scenario "pass"; if media/voice can't be simulated
locally, **document the limitation** rather than faking it.

---

## Agent C — Backend / API smoke  (Phase 4) — depends on A

**Scope:** hit every pilot-critical endpoint with Eric's JWT + `X-Brokerage-Id: mahoroba-realty`;
confirm correct data and DB writes. No UI.

**Steps**
1. Write `tests/pilot/test_pilot_smoke.py` (pytest, reuse `client()`/`send()` from `tests/conftest.py`).
   Narrow + deterministic. Cover the endpoint list in `01-REPO-FINDINGS.md §Pilot-critical endpoints`.
2. For each surface assert: 200 + brokerage-scoped payload shape; mutations persist (re-GET reflects
   change); cross-checks — e.g. `POST /agent/offers` then `GET /agent/offers` shows it; draft `send`
   writes message+action+compliance event; escalation `reply` updates thread; `resolve` closes it;
   viewing lifecycle transitions; lead ingest creates `DBLeadIngestRecord` + conversation + first-touch.
3. Probe failure modes: dashboard must **not** return fabricated fallback rows on a healthy call;
   hot-list refresh works or fails cleanly (no 500 swallow).
4. Record each endpoint: method, status, key assertions, pass/fail, notes (file:line refs).

**Outputs:** `test_pilot_smoke.py`, API results table, backend findings (bugs vs gaps).
**Do not:** add a broad new test framework; keep it to pilot-critical paths.

---

## Agent D — Safety / Verified Facts / Security  (Phase 5) — depends on A

**Scope:** prove the safety posture. Acts as `dalya-security-researcher`.

**Steps**
1. **Verified Facts gate:** drive Priya-style questions (DLD fees, NOC, mortgage/LTV, remaining
   payment, tenancy, conveyancing, commission/extra fees) at L3/L4. Confirm direct answers only when
   verified+buyer_safe; unsupported → rewritten to agent-confirmation; do-not-state / seller-private
   facts never leak. Reuse `scripts/verify_verified_facts_output_gate.py`,
   `tests/test_verified_facts_output_gate.py`.
2. **Seller-leak / privacy:** reuse `scripts/seller_summary_privacy_*.py` and
   `scripts/verify_seller_conversation_summary_privacy.py`; confirm seller notes / motivation / agent-only
   fields never reach buyer text or buyer-visible summaries.
3. **Tenant isolation:** reuse `scripts/audit_tenant_isolation.py`. Confirm `mahoroba-realty` data never
   appears under another brokerage context (seed a throwaway second brokerage if needed). Confirm
   wrong-agent / unauthenticated access to buyer/conversation/escalation endpoints is denied (401/403).
4. **Debug & media posture:** confirm debug routes are gated by `ENABLE_DEBUG_ROUTES` (disabled in
   live-class envs) — or document that it's only testable locally. Confirm media URLs are private/signed,
   not public, where testable (`DBMediaAsset`).
5. **RLS note:** do NOT run the production RLS rollout. Reference `scripts/rls_rehearsal_dal170e1.py` /
   `db_role_rehearsal_dal170e4b.py` and state RLS/app-role remains a separate gate.

**Outputs:** safety matrix (each check pass/fail/blocked), any leak/isolation findings with refs.
**Do not:** attempt production RLS enablement; treat results as live-customer certification.

---

## Agent E — Frontend / UI walkthrough  (Phases 2-support,6,7) — depends on A + B data

**Scope:** log into `/agent` as Eric, walk every surface, verify it matches seeded/simulated data and
that **no demo-fallback rows** render on a healthy load. Acts as `dalya-ux-designer`.

**Steps (use `verify`/`run` skills or a browser):** backend on :8000, frontend on :3001, signed in as Eric.
1. **Dashboard `/agent`:** loads without fallback rows (`fallback-data.ts` must not show); metrics sane;
   Today Queue ordered (critical escalations → overdue tasks → needs-reply → actionable viewings →
   reply drafts → hot buyers → future follow-ups); each item has title/subject/reason/status/timestamp
   + working href; escalation items route to `/agent/escalations?thread=<id>`; hot-list refresh works.
2. **Buyers `/agent/buyers`:** filters (all / open offer / viewing scheduled / stale), sorts (score /
   last activity / name). Open buyer cards: qualification fields, provenance (inferred vs confirmed),
   editable/confirmable fields, DealReadiness panel, conversations, viewings, offer history, escalation
   count, opt-out state.
3. **Conversation `/agent/conversations/[id]`:** timeline, listing snapshot, AI mode, media state,
   brief, summary, next action, active escalation, offer strip, listing-assets shortcut. Test pause AI
   + resume AI (confirmation dialog). Confirm Eric can act **without reading raw transcripts**.
4. **Drafts `/agent/drafts`:** categories; edit/send/reject/snooze; draft-assist shows verified-fact
   metadata + missing facts + readiness + suggested question.
5. **Escalations `/agent/escalations`:** open seeded threads; reply from dashboard; `[Ref: TOKEN]` relay
   reply resolves/updates; manual resolve; bundling shows (no dup spam).
6. **Viewings `/agent/viewings`:** V1 ready full flow incl. tenant notice; V2 off-plan shows no physical
   logistics push; confirmation states; complete + feedback.
7. Note every UX gap that would make a live demo confusing/unimpressive (with component file refs).

**Outputs:** per-surface UI walkthrough notes, demo-fallback verification, UX findings.
**Do not:** redesign or polish surfaces; this is observe-and-report.

---

## Agent F — Lead / Synthesis  (Phase 8) — depends on all

**Scope:** own `04-TEST-MATRIX.md`, merge B/C/D/E findings, dedupe, write the report per
`06-DELIVERABLES.md`, assign the verdict, write blockers + suggested PRs (one branch each).

**Steps**
1. Collect each agent's results + command logs.
2. Fill the test matrix (surface, scenario, expected, actual, status, notes).
3. Classify findings: **bug** vs **UX gap** vs **data/seed gap**; prioritize by demo impact (confusing
   / unsafe / unimpressive first), each with file/endpoint ref.
4. Write golden-path + stress-path as runnable scripts (from `05-DEMO-SCRIPTS.md`, updated to reality).
5. Assign Green/Yellow/Red + one-sentence reason. Write the pre-external-pilot blocker list.
6. Emit `reports/claude-pilot-<date>/PILOT-REPORT.md` + suggested tickets.

**Outputs:** the final pilot report.
