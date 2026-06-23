# Focused Backend QA Runner

DAL-199 provides a local no-DB backend QA runner for the post-closeout focused suite. It uses a temporary venv at `/private/tmp/dalya-focused-backend-qa-venv`, installs only from `requirements.txt`, refuses Python 3.14 for the pinned dependency stack, and writes JSON evidence without env-file or secret contents.

The runner is intentionally fail-closed. It allows only tests that do not import the app DB session, do not need `DATABASE_URL`, and do not read env files through app import paths:

- `tests/test_legacy_telegram_removed.py`
- `tests/test_cors_live_env.py`
- `tests/test_verified_facts_seed_closing_costs.py`

Seller privacy, needs-reply priority, and verified-facts output-gate tests that need `DATABASE_URL`, `SessionLocal`, `load_dotenv()`, or app DB state are excluded until a safe DB harness exists. The classifier normalizes canonical paths, `./`-prefixed paths, repo-absolute paths, and package-style module selectors before comparing them to the no-DB allowlist and DB-backed denylist. Directory discovery such as `tests` is blocked because it can include DB-backed tests.

Canonical check-only proof:

```bash
python3 scripts/run_focused_backend_qa.py --check-only --evidence .omo/evidence/task-2-runtime-qa-check-red.json
```

Canonical no-DB focused run when Python 3.12 or 3.13 is available:

```bash
python3 scripts/run_focused_backend_qa.py --python python3.12 --evidence .omo/evidence/task-2-runtime-qa-green.json
```

Fallback blocked evidence when no compatible interpreter is installed:

```bash
python3 scripts/run_focused_backend_qa.py --check-only --evidence .omo/evidence/task-2-runtime-qa-blocked.json
```

DB-backed selection guardrail proof:

```bash
python3 scripts/run_focused_backend_qa.py --python python3.12 --evidence .omo/evidence/task-2-runtime-qa-db-suite-blocked.json -- tests/test_legacy_telegram_removed.py tests/test_cors_live_env.py tests/test_seller_lead_privacy.py tests/test_verified_facts_output_gate.py tests/test_verified_facts_seed_closing_costs.py tests/test_needs_reply_priority.py -q
```

Expected result: `BLOCKED` with a `db_backed_tests_disallowed` reason before venv creation, dependency installation, or pytest execution.

Path-normalization guardrail probes:

```bash
python3 scripts/run_focused_backend_qa.py --python python3 --evidence .omo/evidence/dal-199-task2-canonical-blocked.json -- tests/test_seller_lead_privacy.py -q
python3 scripts/run_focused_backend_qa.py --python python3 --evidence .omo/evidence/dal-199-task2-dot-blocked.json -- ./tests/test_seller_lead_privacy.py -q
python3 scripts/run_focused_backend_qa.py --python python3 --evidence .omo/evidence/dal-199-task2-absolute-blocked.json -- /Users/eric/dalya-ai/tests/test_seller_lead_privacy.py -q
python3 scripts/run_focused_backend_qa.py --python python3 --evidence .omo/evidence/dal-199-task2-directory-blocked.json -- tests -q
python3 scripts/run_focused_backend_qa.py --python python3 --evidence .omo/evidence/dal-199-task2-module-blocked.json -- tests.test_seller_lead_privacy -q
```

Expected result: each DB-backed selector returns `BLOCKED`, writes `commands: []`, and records `cleanup_reason: real_run_not_started`. The default check-only probe remains limited to the explicit no-DB allowlist and records `suite_policy: allowed_no_db_tests_only`.

Do not use this runner for DB-backed tests, migrations, live writes, production or staging commands, or dependency pin changes.
