# DAL-170E5A Production RLS Rollout Runbook

This runbook is the **plan** for enabling Postgres Row-Level Security (RLS) in
production once DAL-170E1/E2/E3/E4A/E4B/E4C are merged. It is **planning only**.

**This runbook does not enable RLS, does not run DDL, and does not change DB
roles or app runtime behaviour.** Production RLS remains on hold until Eric
approves the rehearsal evidence and explicitly authorises the apply.

## Task 10a friendly-pilot posture

Task 10a is a readiness record only. It does not authorize production/staging
DDL, RLS enablement, role/grant mutation, app-runtime role switching, or live
data writes.

Current Task 10a status:

- No dedicated `.env.dal170e5_rehearsal` file is present in this worktree.
- No approved DAL-170E5 rehearsal DB fingerprint is recorded in this runbook.
- Existing env files were inventoried by filename only; env-file contents were
  not read.
- The DAL-170E5 rehearsal/apply path remains blocked until a fresh dedicated
  rehearsal branch, approved DB fingerprint, rollback artifact, and maintenance
  window are provided.

Friendly-pilot data posture until that gate is cleared:

- Synthetic/internal demo data may be used if the rest of the product gates pass.
- Real-customer data, external brokerage pilot data, and live production data are
  blocked for this RLS/app-role risk area.
- Any approval to move beyond synthetic/internal data must be separate from this
  task and must include the target DB fingerprint, rollback artifact, and
  maintenance window required by the Eric approval gate below.

It builds on the DAL-170D DDL runbook conventions (`docs/runbooks/dal170d-production-ddl.md`):
fresh-branch rehearsal, DB-identity confirmation, artifact capture, explicit
production gates, rollback SQL, and an Eric approval gate.

> Note on legacy doc: `supabase_rls_setup.md` describes an earlier Supabase
> `service_role`-based RLS sketch. It is **superseded** by the DAL-170E
> GUC/session-context model described here and must not be used for production.

---

## What the DAL-170E series delivers (recap)

The runtime model is **GUC-based RLS**, not Supabase `service_role`:

- **Session context (E1).** The app sets four per-transaction settings with
  `SET LOCAL` via `set_config(..., true)` (see `app/db/session.py`):
  - `app.user_id`
  - `app.brokerage_id`
  - `app.is_service`
  - `app.is_platform_admin`
- **Helper functions (E1).** SQL functions read those settings:
  `app.current_user_id()`, `app.current_brokerage_id()`, `app.is_service()`,
  `app.is_platform_admin()`.
- **Policies (E1/E2/E3).** Per-table policies named `dal170e1_*`, `dal170e2_*`,
  `dal170e3_*`. Tenant rows are visible when
  `brokerage_id = app.current_brokerage_id()` (directly or via a parent), with a
  bypass for `app.is_service()` / `app.is_platform_admin()`. Service-only tables
  are restricted to service/admin context.
- **Runtime role (E1 rehearsal).** `dal170e1_rls_runtime` (`nologin`) is granted
  `SELECT, INSERT, UPDATE, DELETE` on the in-scope tables. RLS is only enforced
  against non-owner, non-`BYPASSRLS` roles, so the production app must connect as
  a least-privilege role.
- **Least-privilege app role (E4B rehearsal).** `dal170e4b_app_runtime` —
  least-privilege (`nocreaterole`), granted usage on `public` (+ `app` schema if
  present) and table/sequence DML. This is the shape the production app-runtime
  role must take.
- **Runtime schema-creation gate (E4A).** `runtime_create_all_allowed()`
  (`app/core/runtime_config.py`) defaults to **false**; `app/main.py` refuses
  `Base.metadata.create_all()` unless `DALYA_ALLOW_RUNTIME_CREATE_ALL=1`. In
  production the app must not own/create schema.
- **Service/admin DB context (E4C).** `set_service_db_session_context()`,
  `service_session()`, and `service_db_context_scope()` mark server-side work
  (workers, webhooks, admin) as `app.is_service=true`, so background jobs keep
  working under RLS.

### Environment variables / connection-role split

| Variable | Used by | Role intent |
| --- | --- | --- |
| `DATABASE_URL` | FastAPI app runtime, workers (`app/db/session.py`) | **Least-privilege, non-owner** role in prod (e.g. the `dal170e4b_app_runtime` shape). RLS is enforced against this role. |
| `MIGRATION_DATABASE_URL` | approved migration/role/policy scripts only | Schema **owner** / migration role. Never used by app runtime. |
| `DATABASE_OWNER_URL` | fallback owner URL for owner-only scripts | Schema **owner**. Never used by app runtime. |
| `PROD_DB_HOST` | rehearsal/test write guards | Non-secret production hostname **denylist** that refuses non-prod rehearsal writes against prod. |
| `DALYA_ENV` | runtime + scripts | `production` enables the production gates. |
| `DALYA_ALLOW_RUNTIME_CREATE_ALL` | `app/main.py` (E4A) | Must remain **unset/false** in production. |
| `DALYA_ALLOW_DB_ROLE_REHEARSAL_MUTATION` | E4B rehearsal script | Rehearsal-only; never set in production. |

---

## Preflight checklist

Do not start staging rehearsal until **all** are true:

- [ ] DAL-170E1, E2, E3, E4A, E4B, E4C are merged to `main` and CI is green.
- [ ] DAL-170D tenant-integrity DDL is applied/validated as required (RLS tenant
      predicates assume `brokerage_id` columns exist and are populated).
- [ ] Every in-scope table has a non-null `brokerage_id` (directly or via a
      resolvable parent). Run a row-count audit for `brokerage_id IS NULL` on the
      direct-root tables; **zero** is required before FORCE RLS.
- [ ] A least-privilege production app role exists or is scripted (E4B shape) and
      is **not** the schema owner and **not** `BYPASSRLS`.
- [ ] `MIGRATION_DATABASE_URL` / `DATABASE_OWNER_URL` (owner) and `DATABASE_URL`
      (least-privilege) are provisioned as **distinct** roles in production.
- [ ] `PROD_DB_HOST` denylist is set to the production hostname(s).
- [ ] Service/worker/webhook/admin code paths use service context (E4C) — confirm
      via `tests/test_service_admin_db_context_dal170e4c.py`.
- [ ] A staging Neon branch (fresh from prod or staging) is available with a
      dedicated env file (e.g. `.env.dal170e5_rehearsal`) — never `.env`,
      `.env.test`, or production env files.
- [ ] Maintenance window / low-traffic window agreed with Eric.
- [ ] Rollback SQL reviewed and stored (see Rollback section).

---

## Staging rehearsal steps (fresh Neon branch)

Rehearsal only. The E1/E4B scripts already refuse to mutate a production-like
`DATABASE_URL` and require explicit allow-mutation flags.

1. Create a fresh dedicated Neon branch from the production/staging source.
   Confirm privately it is **not** the `.env.test` baseline and **not**
   production (compare unmasked host privately; do not paste secrets into Linear).
2. Point `.env.dal170e5_rehearsal` `DATABASE_URL` at the fresh branch
   (least-privilege rehearsal role) and set `MIGRATION_DATABASE_URL` /
   `DATABASE_OWNER_URL` to the branch owner role.
3. Capture preflight evidence: row counts, `brokerage_id IS NULL` audit, and the
   current `pg_policies` / `pg_class.relrowsecurity` state (expected: no
   `dal170e*` policies, RLS disabled).
4. Print the canonical rollback SQL (no mutation) for review and storage. The
   apply SQL is defined in the script (`HELPER_SQL`, `POLICY_SQL`, `ROLE_SQL`,
   `ENABLE`/`FORCE` statements) — review it in the diff before applying:

   ```bash
   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170e5_rehearsal run -- \
     venv/bin/python scripts/rls_rehearsal_dal170e1.py --print-rollback
   ```

5. Apply the E4B least-privilege app role on the branch, then the E1 RLS
   policies/helpers/role + `ENABLE`/`FORCE ROW LEVEL SECURITY`:

   ```bash
   # Least-privilege app role (owner connection)
   DALYA_ALLOW_DB_ROLE_REHEARSAL_MUTATION=1 \
   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170e5_rehearsal run -- \
     venv/bin/python scripts/db_role_rehearsal_dal170e4b.py --apply

   # RLS helpers + policies + ENABLE/FORCE (owner connection)
   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170e5_rehearsal run -- \
     venv/bin/python scripts/rls_rehearsal_dal170e1.py --apply --allow-rehearsal-mutation
   ```

6. Point a rehearsal app instance at the branch using the **least-privilege**
   `DATABASE_URL` and run the smoke tests below.
7. Run the security + tenant isolation regression and the DAL-170E suites:

   ```bash
   venv/bin/python -m pytest \
     tests/test_rls_session_context_dal170e1.py \
     tests/test_runtime_schema_gate_dal170e4a.py \
     tests/test_db_role_rehearsal_dal170e4b.py \
     tests/test_service_admin_db_context_dal170e4c.py \
     tests/test_tenant_isolation_dal170.py \
     tests/test_brokerage_context_dal172.py \
     tests/test_needs_reply_signal_dal170e5.py -q
   ```

8. Capture: policy list, `relrowsecurity`/`relforcerowsecurity` per table,
   smoke-test output, regression output, and the printed rollback SQL.
9. Roll back the branch and re-verify a clean state:

   ```bash
   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170e5_rehearsal run -- \
     venv/bin/python scripts/rls_rehearsal_dal170e1.py --rollback --allow-rehearsal-mutation
   ```

10. Attach all evidence to Linear.

---

## RLS apply order (production)

Apply as the **owner/migration** role (`MIGRATION_DATABASE_URL` /
`DATABASE_OWNER_URL`). One group at a time; verify after each group before
proceeding.

0. **Roles & grants first** — ensure the least-privilege app role exists (E4B
   shape) and the runtime role is granted DML on the in-scope tables. Helpers:
   create `app.current_user_id()`, `app.current_brokerage_id()`,
   `app.is_service()`, `app.is_platform_admin()`.
1. **FIRST_TABLES** (root/tenant anchors): `brokerages`, `brokerage_members`,
   `agent_profiles`, `listings`, `conversations`, `brokerage_buyer_profiles`,
   `buyer_profile_fields` — policies `dal170e1_*`.
2. **E2 direct-root tables** (have `brokerage_id` directly): `listing_documents`,
   `listing_facts`, `listing_knowledge_summaries`, `listing_logistics`,
   `tenant_consents`, `listing_inquiries`, `offers`, `draft_replies`,
   `ai_drafts`, `lead_ingests`, `lead_assignments`, `lead_tasks`, `lead_actions`,
   `viewings`, `tenant_viewing_confirmations`, `viewing_feedback`, `media_assets`
   — policies `dal170e2_*_tenant`.
3. **E3 parent-derived tables** (tenant via a parent row): `escalation_threads`,
   `messages`, `escalation_thread_questions`, `telegram_reply_routes` — policies
   `dal170e3_*`.
4. **E3 nullable-root tables**: `offer_records`, `suspicious_activity`,
   `inbound_provider_events` — policies `dal170e3_*_tenant`.
5. **E3 service-only tables**: `message_queue`, `buyer_profiles` — policies
   `dal170e3_*_service_only` (reachable only under service/admin context).

For each table: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` then
`... FORCE ROW LEVEL SECURITY` (so the table owner is also subject to RLS). The
production app must already be connecting as the least-privilege role before
FORCE is applied to avoid a lockout of the table owner.

---

## App runtime DB role switch plan

1. Provision the production least-privilege role (E4B shape): not owner, not
   `BYPASSRLS`, `nocreaterole`, DML on in-scope tables + sequence usage.
2. Stage the new `DATABASE_URL` (least-privilege) as a secret **before**
   enabling FORCE. Keep the owner URL only in `MIGRATION_DATABASE_URL` /
   `DATABASE_OWNER_URL` for migrations.
3. Confirm `DALYA_ALLOW_RUNTIME_CREATE_ALL` is unset/false in production (E4A) so
   the least-privilege runtime never attempts `create_all`.
4. Deploy the app on the least-privilege `DATABASE_URL` and confirm normal
   tenant traffic works **before** FORCE RLS (policies are permissive until
   ENABLE/FORCE, so this validates grants without lockout risk).
5. Confirm workers/webhooks/admin run under service context (E4C) — they must set
   `app.is_service=true` (or platform-admin) so background flows bypass tenant
   predicates correctly.
6. Only then apply ENABLE/FORCE in the apply order above.

## Migration-owner credential plan

- The schema owner / migration role is supplied **only** via
  `MIGRATION_DATABASE_URL` (preferred) or `DATABASE_OWNER_URL`, used by approved
  scripts (`scripts/rls_rehearsal_dal170e1.py`, `scripts/db_role_rehearsal_dal170e4b.py`,
  DDL scripts). It is **never** placed in the app-runtime `DATABASE_URL`.
- Owner credentials are used for: creating helper functions, creating/altering
  policies, ENABLE/FORCE RLS, and role/grant changes.
- Rotate or scope-down the owner credential after the rollout; the app runtime
  must never hold owner rights.

---

## Smoke tests after enablement

Run against production immediately after each apply group, using the
**least-privilege** app role:

- [ ] An authenticated agent sees only their brokerage's listings/conversations
      (`/api/v1/agent/dashboard` returns rows; counts match the tenant).
- [ ] A second brokerage's data is **not** visible to the first (cross-tenant
      probe returns empty).
- [ ] Buyer inbound webhook + bot reply still write (service context, E4C).
- [ ] Worker/digest/summary jobs still read/write (service context).
- [ ] Platform-admin surface still sees across tenants (admin context).
- [ ] No `permission denied for table` / `row violates row-level security
      policy` errors in logs.
- [ ] `needs_reply` and escalation dashboards populate for the tenant.

---

## "Do not proceed if" blockers

Stop the rollout if any of these are true:

- Any in-scope table still has `brokerage_id IS NULL` rows (direct-root tables).
- The production app is still connecting as the schema owner or a `BYPASSRLS`
  role (FORCE RLS would not protect it / could lock it out).
- `DALYA_ALLOW_RUNTIME_CREATE_ALL` is enabled in production (E4A gate breached).
- The DB fingerprint/host does not match the approved production evidence.
- Staging rehearsal showed any tenant-isolation failure, smoke-test failure, or
  RLS error.
- Rollback SQL has not been printed, reviewed, and stored.
- Service/worker/webhook/admin paths are not confirmed to set service context
  (E4C) — background jobs would break under RLS.
- No agreed maintenance/low-traffic window, or active incident in progress.

---

## Rollback

RLS is reversible without data changes. Roll back the **most recently applied
group first**, in reverse apply order.

Per table (owner connection):

```sql
ALTER TABLE <table> NO FORCE ROW LEVEL SECURITY;
ALTER TABLE <table> DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS <policy_name> ON <table>;
```

- The E1 rehearsal script can print the canonical rollback SQL:
  `scripts/rls_rehearsal_dal170e1.py --print-rollback` (and `--rollback` on
  test/local). Use the printed statements as the production rollback source of
  truth (production execution is a manual, owner-run, Eric-approved step — this
  runbook does not auto-apply).
- Helper functions (`app.current_*`) and the runtime role can remain; they are
  inert without policies. Drop them only if the release decision says to.
- Fast mitigation if the app errors but data is safe: `DISABLE ROW LEVEL
  SECURITY` on the affected tables restores pre-RLS behaviour immediately, then
  investigate.

---

## Eric approval gate (before production)

Production RLS enablement requires Eric's explicit written approval of:

1. Staging rehearsal evidence (policy list, `relrowsecurity`/`relforcerowsecurity`,
   smoke + regression output, rollback SQL).
2. DB identity confirmation (fingerprint or host+database) for the production
   target.
3. The least-privilege app-role switch plan and confirmation the runtime is on
   the non-owner role.
4. The maintenance/low-traffic window and the rollback plan.

No production `ENABLE`/`FORCE ROW LEVEL SECURITY`, policy creation, or role/grant
change may run until this gate is cleared.

---

## Linear evidence to attach

- Preflight audit (row counts, `brokerage_id IS NULL` = 0).
- Printed apply SQL and printed rollback SQL.
- Staging policy list + `relrowsecurity`/`relforcerowsecurity` per table.
- Smoke-test output (tenant isolation pass, service/admin pass).
- DAL-170E + tenant + DAL-172 regression output.
- DB fingerprint/host confirmation for production.
- Operator notes (window, lock behaviour, any anomalies).
