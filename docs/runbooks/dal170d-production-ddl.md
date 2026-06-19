# DAL-170D Production DDL Runbook

DAL-170D DDL is additive tenant-integrity work for Postgres/Neon. It is not a data backfill, not RLS, and not constraint validation.

Production DDL remains on hold until Eric approves the rehearsal evidence, DB identity check, and lock strategy.

## Scope

Allowed DAL-170D phases:

- `parent-keys`
- `child-indexes`
- `first-fks`
- `second-fks`

Each phase must run separately. Do not run production DDL for RLS, NOT NULL constraints, `VALIDATE CONSTRAINT`, tenant backfills, `suspicious_activity`, `listing_inquiries`, `offer_records`, lead workflow FKs, relay FKs, or private media work through this runbook.

## Fresh Neon Branch Rehearsal

1. Create a fresh dedicated Neon branch from the production or staging source that will be used for the release rehearsal.
2. Confirm the branch is not the shared `.env.test` baseline. Compare the full unmasked host privately against both production and `.env.test` before any apply, but do not paste secrets or full URLs into Linear/artifacts.
3. Use a dedicated branch env file, such as `.env.dal170d_rehearsal`; do not use `.env`, `.env.test`, or production env files for rehearsal.
4. Confirm `PROD_DB_HOST` is set to the non-secret production hostname denylist before any rehearsal/test apply. A non-production apply refuses to run without this denylist unless an explicit approved rehearsal override is supplied. The override still requires an artifact directory plus either an approved DB fingerprint or host+database confirmation.
5. Print and save the DB fingerprint:

   ```bash
   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170d_rehearsal run -- \
     venv/bin/python scripts/migrate_tenant_constraints_dal170d.py \
     --print-db-fingerprint \
     --phase parent-keys \
     --json
   ```

6. Run read-only preflight:

   ```bash
   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170d_rehearsal run -- \
     venv/bin/python scripts/audit_tenant_constraints_dal170d.py --json
   ```

7. Dry-run each phase and save output:

   ```bash
   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170d_rehearsal run -- \
     venv/bin/python scripts/migrate_tenant_constraints_dal170d.py --dry-run --phase parent-keys

   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170d_rehearsal run -- \
     venv/bin/python scripts/migrate_tenant_constraints_dal170d.py --dry-run --phase child-indexes

   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170d_rehearsal run -- \
     venv/bin/python scripts/migrate_tenant_constraints_dal170d.py --dry-run --phase first-fks

   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170d_rehearsal run -- \
     venv/bin/python scripts/migrate_tenant_constraints_dal170d.py --dry-run --phase second-fks
   ```

8. Apply one phase at a time on the fresh branch with an artifact directory:

   ```bash
   PYTHONPATH=$(pwd) venv/bin/python -m dotenv -f .env.dal170d_rehearsal run -- \
     venv/bin/python scripts/migrate_tenant_constraints_dal170d.py \
     --apply \
     --phase parent-keys \
     --expected-db-fingerprint "<approved-rehearsal-fingerprint>" \
     --artifact-dir artifacts/dal170d/rehearsal/parent-keys \
     --lock-timeout-ms 10000 \
     --statement-timeout-ms 120000
   ```

9. Repeat only after each phase has completed cleanly.
10. Confirm all expected indexes/constraints exist.
11. Confirm all DAL-170D FK constraints remain `convalidated=false`.
12. Run security + tenant regression.
13. Run broader regression.
14. Attach the fingerprint, preflight, dry-run SQL, rollback SQL, apply artifacts, and test results to Linear.

## Production Apply Procedure

Production apply requires all of the following:

- `DALYA_ENV=production`
- `ALLOW_PRODUCTION_TENANT_CONSTRAINTS=true`
- `PROD_DB_HOST` set to the approved non-secret production DB hostname denylist
- explicit `--apply`
- exactly one explicit `--phase`
- `--artifact-dir`
- either `--expected-db-fingerprint <hash>` or both `--confirm-db-host <host-fragment>` and `--confirm-db-name <database-name>`
- approved maintenance window or approved lock strategy

Example:

```bash
PYTHONPATH=$(pwd) DALYA_ENV=production ALLOW_PRODUCTION_TENANT_CONSTRAINTS=true \
  venv/bin/python scripts/migrate_tenant_constraints_dal170d.py \
  --apply \
  --phase parent-keys \
  --expected-db-fingerprint "<approved-fingerprint>" \
  --artifact-dir artifacts/dal170d/production/parent-keys \
  --lock-timeout-ms 10000 \
  --statement-timeout-ms 120000
```

Do not run more than one phase in a single command.

## Lock Strategy

The current production path does not implement `CREATE INDEX CONCURRENTLY`. Index creation and `ALTER TABLE ADD CONSTRAINT ... NOT VALID` can still take locks and should be treated as maintenance-window work until a separate concurrent/autocommit path is designed and reviewed.

`--lock-timeout-ms` and `--statement-timeout-ms` reduce blast radius by failing instead of waiting indefinitely. They do not eliminate lock risk.

Stop if:

- lock timeout errors appear
- application writes time out
- Neon shows lock waits or CPU/IO saturation
- preflight blockers appear
- fingerprint differs from approved evidence

## Rollback

Each apply writes:

- `db_fingerprint.json`
- `preflight_summary.json`
- `dry_run_sql.sql`
- `rollback_sql.sql`
- `apply_plan.json`

Rollback SQL is printed before production execution and stored in the artifact bundle. Roll back only the phase that was just applied unless Eric and the DBA/operator approve broader rollback.

Failed statements before commit do not require rollback for that statement. Partially completed prior phases should be rolled back only if the release decision says to remove them.

## Linear Evidence

Attach:

- DB fingerprint JSON
- preflight JSON
- dry-run output for every phase
- apply artifact directory listing
- rollback SQL
- `pg_constraint` evidence showing FKs are `convalidated=false`
- security + tenant regression output
- broader regression output
- operator notes about lock behavior and maintenance window
