# DAL-201 / Task 4 Runtime QA Path Investigation

Date: 2026-06-23
Workspace: `/Users/eric/dalya-ai`
Mode: read-only product files; evidence writes only under `.omo/evidence/`

## Verdict

BLOCKED for API/TestClient runtime QA.

PASS for the pure sanitizer check that imports only `app.core.seller_summary_privacy` and does not import FastAPI, TestClient, app DB, or environment-backed session code.

Minimum external condition needed to unblock API/TestClient QA: a working Python 3.12 or 3.13 environment with the repo's pinned dependencies installed, including `fastapi`, `pytest`, and `python-dotenv`, plus a proven in-memory/SQLite TestClient harness that does not read `DATABASE_URL` or touch external DBs. The current test and verifier paths are DB-backed by code inspection and cannot be treated as in-memory.

## Environment Facts

- `pwd`
  - stdout: `/Users/eric/dalya-ai`
- `command -v python3`
  - stdout: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`
- `python3 --version`
  - stdout: `Python 3.14.3`
- `/usr/bin/python3 --version`
  - stdout: `Python 3.9.6`
- `/usr/bin/python3 -m pytest --version`
  - exit: 1
  - stderr summary: `/Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest`
- `python3 -m pytest --version`
  - stdout: `pytest 8.3.0`
- Common-path Python 3.12/3.13 search:
  - invocation: `find /opt/homebrew/bin /usr/local/bin /usr/bin /Library/Frameworks/Python.framework/Versions /Users/eric/.pyenv /Users/eric/.asdf /Users/eric/.local /Users/eric/.uv -maxdepth 4 -type f \( -name 'python3.12' -o -name 'python3.13' -o -name 'python3' -o -name 'python' \) 2>/dev/null`
  - exit: 1
  - stdout: `/usr/bin/python3`
  - conclusion: no local Python 3.12 or 3.13 executable found in queried common paths.
- Repo env search:
  - invocation: `find . -maxdepth 3 -type d \( -name 'venv' -o -name '.venv' -o -name 'env' \) 2>/dev/null`
  - stdout: `./venv`
- Existing repo venv:
  - `ls -l venv/bin/python venv/bin/python3 venv/bin/pytest`
  - stdout summary: `venv/bin/python -> python3.13`, `venv/bin/python3 -> python3.13`, `venv/bin/pytest` exists.
  - `ls -la venv/bin` showed `python3.13 -> /opt/homebrew/opt/python@3.13/bin/python3.13`.
  - `venv/bin/python --version`
    - exit: 127
    - stderr: `zsh:1: no such file or directory: venv/bin/python`
  - `venv/bin/pytest --version`
    - exit: 127
    - stderr: `zsh:1: venv/bin/pytest: bad interpreter: /Users/eric/dalya-ai/venv/bin/python3.13: no such file or directory`
  - conclusion: repo venv is present but broken by a missing Python 3.13 symlink target.
- Dependency files found:
  - `requirements.txt`
  - `chatbot/requirements.txt`
- Relevant source facts:
  - `tests/test_seller_conversation_summary_privacy.py` imports `fastapi.testclient`, `app.db.session`, `app.main`, and DB models at collection time, then calls `Base.metadata.create_all(bind=engine)`.
  - `tests/conftest.py` imports `app.db.session`, `app.main`, and also calls `Base.metadata.create_all(bind=engine)`.
  - `scripts/verify_seller_conversation_summary_privacy.py` imports the pure sanitizer at module import, but its cleanup/seed/verify path imports `app.db.session`, `app.main`, and DB models.
  - `app/db/session.py` calls `load_dotenv()`, reads `DATABASE_URL`, raises if missing, and creates a SQLAlchemy engine from that URL. No in-memory/SQLite override path was identified.

## Command Results

### Exact Requested Pytest Invocation

Surface: local Python pytest collection for seller conversation summary privacy.

Invocation:

```bash
PYTHONPATH=. python3 -m pytest --noconftest tests/test_seller_conversation_summary_privacy.py -q
```

Exit: 2

stdout/stderr summary:

```text
ERROR collecting tests/test_seller_conversation_summary_privacy.py
ModuleNotFoundError: No module named 'fastapi'
1 error during collection
```

Conclusion: BLOCKED before tests run. No DB write occurred. The test is also DB-backed by inspection because it imports `app.db.session` and calls `Base.metadata.create_all(bind=engine)` at module import.

### Exact Requested Verifier Invocation

Surface: local Python verifier script for seller conversation summary privacy.

Invocation:

```bash
PYTHONPATH=. python3 scripts/verify_seller_conversation_summary_privacy.py --evidence .omo/evidence/task-4-seller-summary-api.qa.json
```

Exit: 1

stdout:

```json
{"evidence": ".omo/evidence/task-4-seller-summary-api.qa.json", "status": "BLOCKED"}
```

Evidence file written by verifier: `.omo/evidence/task-4-seller-summary-api.qa.json`

Evidence content summary:

```json
{
  "status": "BLOCKED",
  "forbidden_runtime_blocker": "missing_module:dotenv",
  "seller_status_code": -1,
  "agent_status_code": -1,
  "forbidden_status_code": -1
}
```

Conclusion: BLOCKED before cleanup/seed/verify can run. No DB write occurred. The script cannot be treated as an in-memory TestClient verifier because its runtime path imports `app.db.session`, which reads `DATABASE_URL` and constructs an engine.

### Safe Pure Sanitizer Check

Surface: pure Python sanitizer function only.

Invocation:

```bash
PYTHONPATH=. python3 -c "import json; from app.core.seller_summary_privacy import SellerSummaryRedactionContext, sanitize_seller_ai_summary; ctx=SellerSummaryRedactionContext(buyer_name='Sara Privacy', buyer_phone='+971501112222', conversation_id='conv_01HPIISECRET1234567890'); data={'topics':['Sara Privacy asked about parking', {'raw':'wa.me/971501112222 and whatsapp:+971501112222; call +971 50 111 2222'}], 'key_question':'Can Sara Privacy get a viewing? wants a viewing tomorrow', 'next_step_hint':'Email sara@example.com and mention 971501112222.', 'buyer_context': {'name':'Sara Privacy','phone':'+971501112222','conversation_id':'conv_01HPIISECRET1234567890','nested':['stored row id conv_01HPIISECRET1234567890', {'raw_text':'Sara Privacy: sara@example.com; wants a viewing tomorrow'}]}, 'summary': {'one_line':'Sara Privacy at +971501112222 wants a viewing tomorrow; thread conv_01HPIISECRET1234567890'}, '_fallback':'Sara Privacy wants a viewing tomorrow'}; red=sanitize_seller_ai_summary(data, ctx); rendered=json.dumps(red, sort_keys=True); secrets=('Sara Privacy','+971501112222','sara@example.com','wa.me/971501112222','whatsapp:+971501112222','+971 50 111 2222','971501112222','conv_01HPIISECRET1234567890'); assert not [s for s in secrets if s in rendered], rendered; assert 'wants a viewing tomorrow' in rendered; assert '[redacted buyer]' in rendered and '[redacted phone]' in rendered and '[redacted email]' in rendered and '[redacted whatsapp]' in rendered and '[redacted id]' in rendered; print(json.dumps({'status':'PASS','safe_context_preserved': True, 'placeholders_present':['[redacted buyer]','[redacted phone]','[redacted email]','[redacted whatsapp]','[redacted id]']}, sort_keys=True))"
```

Exit: 0

stdout:

```json
{"placeholders_present": ["[redacted buyer]", "[redacted phone]", "[redacted email]", "[redacted whatsapp]", "[redacted id]"], "safe_context_preserved": true, "status": "PASS"}
```

Conclusion: PASS for pure sanitizer behavior only. This did not import FastAPI/TestClient or DB session code.

## Cleanup

- No product files were edited.
- No dependencies were installed.
- No external DB tests or live writes were attempted.
- Evidence written:
  - `.omo/evidence/task-4-runtime-qa-investigation.md`
  - `.omo/evidence/task-4-seller-summary-api.qa.json`

## manualQa

### surfaceEvidence

| scenario id | criterion reference | surface | exact invocation | verdict | artifactRefs |
|---|---|---|---|---|---|
| S1 | Python 3.12/3.13 availability | Local interpreter inventory | `find /opt/homebrew/bin /usr/local/bin /usr/bin /Library/Frameworks/Python.framework/Versions /Users/eric/.pyenv /Users/eric/.asdf /Users/eric/.local /Users/eric/.uv -maxdepth 4 -type f \( -name 'python3.12' -o -name 'python3.13' -o -name 'python3' -o -name 'python' \) 2>/dev/null` | BLOCKED | A1 |
| S2 | Existing repo venv usability | Repo venv command surface | `venv/bin/python --version`; `venv/bin/pytest --version` | BLOCKED | A1 |
| S3 | Pure sanitizer checks without FastAPI/TestClient | Python function invocation | `PYTHONPATH=. python3 -c "... sanitize_seller_ai_summary ..."` | PASS | A1 |
| S4 | Exact pytest blocker | Pytest collection | `PYTHONPATH=. python3 -m pytest --noconftest tests/test_seller_conversation_summary_privacy.py -q` | BLOCKED | A1 |
| S5 | Exact verifier blocker | Verifier script | `PYTHONPATH=. python3 scripts/verify_seller_conversation_summary_privacy.py --evidence .omo/evidence/task-4-seller-summary-api.qa.json` | BLOCKED | A1, A2 |
| S6 | In-memory/SQLite TestClient eligibility | Static/runtime path inspection | `sed -n '1,220p' app/db/session.py`; `sed -n '1,240p' tests/test_seller_conversation_summary_privacy.py`; `sed -n '1,260p' scripts/verify_seller_conversation_summary_privacy.py` | BLOCKED | A1 |

### adversarialCases

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| A-C1 | No hidden runtime assumption | Broken repo venv despite scripts existing | QA must not assume `venv/bin/pytest` is usable when interpreter target is missing | PASS | A1 |
| A-C2 | No dependency installation | Missing FastAPI/dotenv in active Python | QA must record blocker rather than install or mutate lockfiles | PASS | A1, A2 |
| A-C3 | No production/staging env reads | DB-backed app session imports | QA must not read env or run DB-backed path unless in-memory path is proven | PASS | A1 |
| A-C4 | No policy bypass | Task 2 runner DB-backed seller tests | QA must not bypass DB-backed seller-test policy without proof of in-memory/TestClient no-external-DB path | PASS | A1 |
| A-C5 | Pure logic isolation | Sanitizer-only import path | Pure sanitizer can run and must redact buyer PII while preserving safe context | PASS | A1 |

### artifactRefs

| id | kind | description | path |
|---|---|---|---|
| A1 | markdown | This runtime QA investigation report with command invocations and output summaries | `.omo/evidence/task-4-runtime-qa-investigation.md` |
| A2 | json | Verifier-generated BLOCKED evidence for seller summary API path | `.omo/evidence/task-4-seller-summary-api.qa.json` |
