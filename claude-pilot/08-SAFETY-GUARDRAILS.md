# 08 — Safety Guardrails & Scope Guard

The pilot is a **seeded rehearsal**, not a live-customer certification. These rules are hard.

## Environment (the only safe configuration)
```bash
export DALYA_ENV=development            # allowlist: development | test | staging. NEVER production.
export DATABASE_URL='postgresql://...TEST_BRANCH_HOST/...'   # Neon TEST branch, never prod
export PROD_DB_HOST='PROD_HOSTNAME_ONLY' # denylist signal; must NOT equal DATABASE_URL host
export MESSAGING_TRANSPORT=simulated     # in-memory; no live WhatsApp
export ENABLE_DEBUG_ROUTES=true          # local only (for /whatsapp/send-test)
```
- `DALYA_ENV` **defaults to `production`** if unset (`app/core/runtime_config.py`). Always set it
  explicitly. Simulated/360dialog transports are blocked in live-class envs by design.
- The shared guard `tests/safety.py::assert_safe_test_database()` must pass before ANY DB write. Every
  pilot script calls it first. If it raises, **stop** — do not bypass it.

## The do-not list
- ❌ No real customer data. Personas/listings/buyers are fabricated and marked `dalya_pilot`.
- ❌ No live WhatsApp sends (no Twilio/360dialog live transport). Simulated only.
- ❌ No writes to the production database. Test/staging branch only.
- ❌ No production RLS / app-role rollout. That is a **separate approval gate** —
  reference-only via `scripts/rls_rehearsal_dal170e1.py`, `scripts/db_role_rehearsal_dal170e4b.py`.
- ❌ No edits to unrelated code. New files live under `scripts/pilot/`, `tests/pilot/`,
  `claude-pilot/`, `reports/claude-pilot-<date>/`. Touch product code only to fix a pilot-blocking bug,
  and only with a clear note + the smallest diff (prefer filing a ticket instead).
- ❌ Do not build: production onboarding, live-send paths, broad new test frameworks, owner/admin/
  campaign polish, or new abstractions just for test data.

## Reset safety
- `scripts/pilot/reset_mahoroba_pilot.py` deletes **only** pilot-marked rows, refuses to run unless
  `DALYA_PILOT_CONFIRM=mahoroba-realty`, and calls the safety guard first. It must never delete
  non-pilot rows, and must be safe to re-run.

## RLS / production boundary (state in the report)
Production RLS and Postgres app-role rollout remain gated behind a separate approval. A green pilot
verdict does **not** clear that gate. The report's blocker section must say so explicitly, alongside:
- live WhatsApp provider readiness (Twilio production / 360dialog — `dialog360_transport.py` is a stub,
  not signature-verified, raises `NotImplementedError` on use),
- any dashboard/chatbot gaps found during the run.

## If the environment can't support a full DB-backed run
Document exactly what's blocked, then run the closest available simulation, in this order:
1. API-level simulation against a disposable local Postgres (declarative ORM auto-creates schema).
2. Chatbot engine test harness / `run_scenarios.py` over simulated transport.
3. Existing fixtures/tests (`tests/`, `scripts/chatbot_full_test.py`).
Record "DB-backed flow blocked: <reason> — ran <fallback> instead" so the verdict is honest.
