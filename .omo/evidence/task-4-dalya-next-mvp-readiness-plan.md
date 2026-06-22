# Task 4 Evidence - Restrict CORS by environment

Plan: `.omo/plans/dalya-next-mvp-readiness-plan.md`
Task: 4. Restrict CORS by environment.
Branch: `codex/restrict-cors-by-env`

## Changed files

- `.env.example`
- `app/core/runtime_config.py`
- `app/main.py`
- `tests/test_cors_live_env.py`
- `tests/test_runtime_config_live_env.py`
- `scripts/verify_cors_headers.py`

## RED proof

Command:

```bash
PATH=/private/tmp/dalya-task4-runtime-qa-venv/bin:$PATH PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest --noconftest tests/test_cors_live_env.py -q
```

Result before implementation: exit 1, 8 failed.

Right-reason failures:

- Local/test app middleware exposed `allow_origins == ["*"]` instead of localhost explicit origins.
- Configured pilot origins were ignored and app middleware still exposed `["*"]`.
- Live-class app construction did not raise when `DALYA_CORS_ORIGINS` was absent.
- Live-class app construction did not reject `*` or mixed wildcard origins.

## GREEN proof

Command:

```bash
PATH=/private/tmp/dalya-task4-runtime-qa-venv/bin:$PATH PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest --noconftest tests/test_cors_live_env.py -q
```

Result after implementation: exit 0, `8 passed, 40 warnings in 0.13s`.

## Focused regression

Command:

```bash
PATH=/private/tmp/dalya-task4-runtime-qa-venv/bin:$PATH PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest --noconftest tests/test_runtime_config_live_env.py tests/test_live_class_security_env.py -q
```

Result: exit 0, `44 passed in 0.11s`.

First attempt in the minimal temp venv failed only because `twilio` was not installed for an existing transport test. Installed pinned `twilio==9.3.0` from `requirements.txt` into the temp venv and reran the same command successfully.

## Manual CORS header surface

Command:

```bash
PATH=/private/tmp/dalya-task4-runtime-qa-venv/bin:$PATH PYTHONPATH=. DALYA_ENV=test DALYA_CORS_ORIGINS=http://localhost:3000 python3 scripts/verify_cors_headers.py --origin http://localhost:3000 --evidence .omo/evidence/task-4-cors.json
```

Result: exit 0.

Artifact: `.omo/evidence/task-4-cors.json`

Binary observable:

```json
{
  "access_control_allow_credentials": "true",
  "access_control_allow_origin": "http://localhost:3000",
  "configured_allow_origins": [
    "http://localhost:3000"
  ],
  "origin": "http://localhost:3000",
  "passed": true,
  "status_code": 200
}
```

## Static gates

Command:

```bash
python3 -m py_compile app/main.py app/core/runtime_config.py tests/test_cors_live_env.py tests/test_runtime_config_live_env.py scripts/verify_cors_headers.py
```

Result: exit 0.

Command:

```bash
git diff --check
```

Result: exit 0.

Command:

```bash
rg -n "<<<<<<<|=======|>>>>>>>" app/main.py app/core/runtime_config.py tests/test_cors_live_env.py tests/test_runtime_config_live_env.py scripts/verify_cors_headers.py .env.example
```

Result: exit 1 with no output, meaning no conflict markers.

Pure LOC check:

- `app/main.py`: 275 pure LOC. Existing oversized file; Task 4 changed only CORS import/use and did not refactor unrelated app routes.
- `app/core/runtime_config.py`: 90 pure LOC.
- `tests/test_cors_live_env.py`: 79 pure LOC.
- `tests/test_runtime_config_live_env.py`: 69 pure LOC.
- `scripts/verify_cors_headers.py`: 78 pure LOC.

## Temp runtime QA venv

Path: `/private/tmp/dalya-task4-runtime-qa-venv`

Reason: repo venv points to missing `/opt/homebrew/opt/python@3.13/bin/python3.13`; system Python lacked FastAPI.

Installed pinned/smallest-needed subset:

- `fastapi==0.115.0`
- `pytest==8.3.0`
- `httpx==0.27.0`
- `twilio==9.3.0`

Cleanup receipt:

```bash
rm -rf /private/tmp/dalya-task4-runtime-qa-venv
test ! -e /private/tmp/dalya-task4-runtime-qa-venv && echo removed
```

Result: exit 0, `removed`.

## Safety confirmations

- No production/staging env file contents read.
- No production/staging app starts.
- No production/staging DDL.
- No migrations, RLS, roles, grants, dependency files, or lockfiles edited.
- No external DB tests.
- No live writes.
- No Task 5+ work.
- CORS tests monkeypatch env only.

## Adversarial classes

- Malformed input: probed through parser rejection of wildcard origins and origin-shape validation in source; wildcard live-class cases covered by tests.
- Dirty worktree: checked `git status --short`; unrelated pre-existing untracked `.omo/` state preserved.
- Stale state: app import tests pop `app.main` before each scenario and stub route modules, so middleware is rebuilt from current monkeypatched env.
- Misleading success output: manual header verifier writes parsed JSON with status/header observables, not only stdout.
- Hung or long commands: pytest/manual/static commands completed within the focused QA window.
- Flaky tests: no sleeps, time, network, DB, or production env files in tests.
- Prompt injection: not applicable; no untrusted natural-language prompt handling changed.
- Cancel/resume: not applicable; no resumable flow changed.
- Mid-operation interrupts: not applicable; no multi-step external mutation except git/PR operations after verification.

## Git and PR

- Commit: recorded in final DoneClaim after Git assigns the committed artifact hash.
- PR: pending at commit time.
