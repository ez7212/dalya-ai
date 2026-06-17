# Canonical Multi-Brokerage Test Harness

This harness is the reusable seeded environment for tests that need realistic brokerage-scoped inventory.
It is not chatbot-specific.

## Database Isolation

Harness and persona tests must run against a physically separate test database, not production.
Use a dedicated Neon branch off production so the branch inherits the migrated schema while keeping test rows in a separate datastore.

Create the branch in Neon:

1. Open the Neon project that hosts production.
2. Create a new branch from the current production branch, for example `dalya-test`.
3. Confirm the branch has the migrated schema.
4. Copy the pooled PostgreSQL connection string for the test branch.
5. Store that test-branch connection string in `.env.test` or export it only in the shell running tests.

Example `.env.test`:

```bash
DALYA_ENV=test
DATABASE_URL=postgresql://USER:PASSWORD@TEST_BRANCH_HOST/neondb?sslmode=require
PROD_DB_HOST=PRODUCTION_HOST_ONLY_NO_PROTOCOL_OR_CREDENTIALS
```

`PROD_DB_HOST` is a non-secret denylist signal, for example the hostname portion of the production Neon URL.
Do not put the production connection string in `.env.test`.
Do not rely on the production `.env` for harness or persona tests.

Equivalent shell-scoped setup:

```bash
export DALYA_ENV=test
export DATABASE_URL='postgresql://USER:PASSWORD@TEST_BRANCH_HOST/neondb?sslmode=require'
export PROD_DB_HOST='PRODUCTION_HOST_ONLY_NO_PROTOCOL_OR_CREDENTIALS'
venv/bin/python scripts/build_harness.py build
```

`DALYA_ENV` is the canonical environment marker. Valid values are:

- `production`
- `staging`
- `test`
- `development`

For harness and persona write paths, only `test`, `staging`, and `development` are allowed. `production` is hard-blocked.

## Safety Guard

All DB-writing harness/persona entry points call the shared `assert_safe_test_database()` guard from `tests/safety.py`.
The guard must pass both checks before any DB write:

- Allowlist: `DALYA_ENV` must be present and one of `test`, `staging`, or `development`.
- Denylist: the hostname parsed from `DATABASE_URL` must not match `PROD_DB_HOST`.

If `DALYA_ENV` is absent, `DALYA_ENV=production`, `DATABASE_URL` is missing/unparseable, `PROD_DB_HOST` is missing, or `DATABASE_URL` points at the production host, the script aborts loudly before writing.
This specifically blocks the dangerous case where `DALYA_ENV=test` is set but `DATABASE_URL` still points at production.

The guard is invoked by:

- `scripts/build_harness.py build`
- `scripts/build_harness.py summary`
- `scripts/build_harness.py teardown`
- `scripts/backfill_harness_community_research.py`
- `tests.harness.build_harness()`
- `tests.harness.teardown_harness()`
- `scripts/chatbot_full_test.py`
- `scripts/chatbot_test.py`

The persona runners consume the canonical harness instead of maintaining their own seeded brokerages/listings:

- `scripts/chatbot_full_test.py` calls `build_harness()` in simulated mode, maps its persona roles onto harness listings across both brokerages, and routes through the harness brokerage AI numbers and assigned-agent phones.
- `scripts/chatbot_test.py` seeds the harness and maps its legacy high/low listing roles onto harness listings before calling the local test endpoint.

`scripts/build_harness.py plan` is dry-run only and does not connect to the database.
`scripts/refresh_harness_snapshots.py` writes frozen snapshot files and the scrape report only; it does not write to the database. If a future snapshot path writes to DB, it must call `assert_safe_test_database()` before that write.

## Community Research Backfill

The harness no longer relies on build-time stub community research by default.
`tests/harness/config.json` uses `community_research.mode = "backfill"`, which means `build_harness.py build` seeds brokerages, agents, and listings from frozen snapshots, then the idempotent backfill step ensures each harness community has real shared community research.

List the distinct harness communities without writing to the database:

```bash
venv/bin/python scripts/backfill_harness_community_research.py --list
```

Backfill missing or stubbed research into the active test database:

```bash
export DALYA_ENV=test
export DATABASE_URL='postgresql://USER:PASSWORD@TEST_BRANCH_HOST/neondb?sslmode=require'
export PROD_DB_HOST='PRODUCTION_HOST_ONLY_NO_PROTOCOL_OR_CREDENTIALS'
export TAVILY_API_KEY='...'
export ANTHROPIC_API_KEY='...'
venv/bin/python scripts/backfill_harness_community_research.py
```

The script:

- enumerates harness communities from frozen snapshots and existing harness community keys,
- uses `app.core.community_researcher.CommunityResearcher` clients/search helpers to generate the same KB schema through a bounded harness backfill path,
- replaces `harness/` stub `DBCommunityResearch` rows in place by community key,
- copies the generated draft into `knowledge_base/` and marks the DB row `approved` for harness use,
- updates seeded harness listings' `community_data` so the Property Advisor is grounded immediately,
- skips already real non-stub research by default,
- supports `--force` for intentional refreshes.

The original full multi-pass community researcher is still available with `--full-agent`, but the default harness path is intentionally bounded to avoid approving malformed whole-file JSON rewrites during test setup.
Because this runs real Tavily and Anthropic research, it may take minutes per new community and requires `TAVILY_API_KEY` plus `ANTHROPIC_API_KEY`.
The script uses the same `assert_safe_test_database()` guard as the rest of the harness and refuses production/non-test writes.

## Files

- `config.json` defines brokerages, generated-agent rules, listing source URLs, and deterministic randomization ranges.
- `snapshots/` contains frozen PF/Bayut scrape outputs with image URL references and redacted real contact fields.
- `scrape_report.md` summarizes required scrape fields per URL.
- `builder.py` exposes `build_harness_plan`, `build_harness`, `get_harness_seed`, `teardown_harness`, and `refresh_snapshots`.

## Commands

Preview the deterministic fixture plan without touching the database:

```bash
venv/bin/python scripts/build_harness.py plan
```

Seed the configured brokerages, agents, and listings into the active database:

```bash
export DALYA_ENV=test
export DATABASE_URL='postgresql://USER:PASSWORD@TEST_BRANCH_HOST/neondb?sslmode=require'
export PROD_DB_HOST='PRODUCTION_HOST_ONLY_NO_PROTOCOL_OR_CREDENTIALS'
venv/bin/python scripts/build_harness.py build
```

Read the current seeded harness entities:

```bash
venv/bin/python scripts/build_harness.py summary
```

Remove only harness-created entities:

```bash
export DALYA_ENV=test
export DATABASE_URL='postgresql://USER:PASSWORD@TEST_BRANCH_HOST/neondb?sslmode=require'
export PROD_DB_HOST='PRODUCTION_HOST_ONLY_NO_PROTOCOL_OR_CREDENTIALS'
venv/bin/python scripts/build_harness.py teardown
```

Refresh snapshots explicitly. This is the only path that should hit PF/Bayut:

```bash
venv/bin/python scripts/refresh_harness_snapshots.py
```

## Contract

Default harness building reads frozen snapshots only. Adding brokerages, agents, or listings should be a config edit, not a code edit. Harness-created IDs use the configured `HARNESS` prefix so teardown can remove only harness-created rows in the test database.

Teardown is hygiene, not safety. It keeps the test branch tidy between runs. Production safety comes from physical isolation via the Neon test branch plus the hard startup guard. If teardown fails, that should leave stale test data in the test branch only; it must never be relied on as the mechanism that protects production.
