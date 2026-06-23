# Final Post-Closeout F4 Remediation

status: PASS_WITH_LOCAL_DEPENDENCY_BLOCK

## Scope

Owned files changed:

- `tests/test_seller_conversation_summary_privacy.py`
- `scripts/verify_seller_conversation_summary_privacy.py`
- `scripts/seller_summary_privacy_contract.py`
- `scripts/seller_summary_privacy_isolation.py`
- `scripts/seller_summary_privacy_app_probe.py`
- `.omo/evidence/task-4-seller-summary-api.json`
- `.omo/evidence/task-4-seller-summary-privacy-pure.json`
- `.omo/evidence/final-post-closeout-f4-remediation.md`

No dependency or lockfile edits. No migration/schema files. No production/staging env-file content reads.

## Remediation

The oversized pytest and verifier files were split into three helpers:

- `scripts/seller_summary_privacy_contract.py`: seeded privacy constants and pure sanitizer contract checks.
- `scripts/seller_summary_privacy_isolation.py`: fail-closed SQLite isolation harness that blocks `dotenv.load_dotenv` before app DB import and patches SQLAlchemy engine creation to local SQLite only.
- `scripts/seller_summary_privacy_app_probe.py`: DB-backed seed/probe helpers that assert the active app engine is isolated SQLite before any `Base.metadata.create_all(bind=engine)` call.

The public test and verifier entry points no longer import `SessionLocal`, `engine`, or `Base` directly. DB-backed code is reachable only after `install_isolated_app_database(...)`.

## Validation

### Pure Sanitizer Probe

Scenario: pure seller summary sanitizer redacts first-name, phone, email, WhatsApp, conversation ID, nested dict keys, and recursive nested values without importing the app DB.

Invocation:

```bash
PYTHONPATH=. python3 -c "import json; from pathlib import Path; from scripts.seller_summary_privacy_contract import SAFE_CONTEXT, pure_first_name_redaction_passes, pure_phone_redaction_passes, pure_recursive_redaction_passes, recursive_redaction_input, privacy_context, seeded_secrets; from app.core.seller_summary_privacy import sanitize_seller_ai_summary; sanitized=sanitize_seller_ai_summary(recursive_redaction_input(), privacy_context()); rendered=json.dumps(sanitized, sort_keys=True); result={'status':'PASS' if pure_first_name_redaction_passes() and pure_phone_redaction_passes() and pure_recursive_redaction_passes() and SAFE_CONTEXT in rendered and not [secret for secret in seeded_secrets() if secret in rendered] else 'FAIL','scenario':'pure seller summary sanitizer redacts first-name, phones, email, WhatsApp, conversation IDs, nested dict keys, and recursive nested values without app DB imports','safe_context_preserved': SAFE_CONTEXT in rendered,'seeded_secrets_absent': not [secret for secret in seeded_secrets() if secret in rendered],'pure_first_name_redaction': pure_first_name_redaction_passes(),'pure_phone_redaction': pure_phone_redaction_passes(),'pure_recursive_preservation': pure_recursive_redaction_passes(),'redacted_output': sanitized}; path=Path('.omo/evidence/task-4-seller-summary-privacy-pure.json'); path.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n'); print(json.dumps({'status':result['status'],'evidence':str(path)}, sort_keys=True))"
```

Observable: exit 0, JSON output `{"evidence": ".omo/evidence/task-4-seller-summary-privacy-pure.json", "status": "PASS"}`.

Artifact path: `.omo/evidence/task-4-seller-summary-privacy-pure.json`.

### Python Compile

Scenario: changed Python files are syntactically valid.

Invocation:

```bash
python3 -m py_compile tests/test_seller_conversation_summary_privacy.py scripts/verify_seller_conversation_summary_privacy.py scripts/seller_summary_privacy_contract.py scripts/seller_summary_privacy_isolation.py scripts/seller_summary_privacy_app_probe.py
```

Observable: PASS, exit 0, empty output.

Artifact path: `.omo/evidence/final-post-closeout-f4-remediation.md`.

### Focused Pytest

Scenario: DB-backed seller privacy pytest entry point.

Invocation:

```bash
PYTHONPATH=. python3 -m pytest --noconftest tests/test_seller_conversation_summary_privacy.py -q
```

Observable: BLOCKED, exit 2. Captured blocker: `ModuleNotFoundError: No module named 'sqlalchemy'` from `scripts/seller_summary_privacy_isolation.py` before `app.db.session` import.

Artifact path: `.omo/evidence/final-post-closeout-f4-remediation.md`.

### API Verifier

Scenario: DB-backed seller privacy verifier with fail-closed DB isolation.

Invocation:

```bash
PYTHONPATH=. python3 scripts/verify_seller_conversation_summary_privacy.py --evidence .omo/evidence/task-4-seller-summary-api.json
```

Observable: BLOCKED, exit 1, JSON output `{"evidence": ".omo/evidence/task-4-seller-summary-api.json", "status": "BLOCKED"}`.

Captured artifact fields:

- `status`: `BLOCKED`
- `forbidden_runtime_blocker`: `missing_module:sqlalchemy`
- `failed_before_app_db_import`: `true`
- `dotenv_reads_blocked`: `true`
- pure sanitizer checks: `true`

Artifact path: `.omo/evidence/task-4-seller-summary-api.json`.

### Diff Hygiene

Scenario: repository whitespace diff check.

Invocation:

```bash
git diff --check
```

Observable: PASS, exit 0, empty output.

Artifact path: `.omo/evidence/final-post-closeout-f4-remediation.md`.

### Size Check

Scenario: pure LOC check for changed Python files.

Captured output:

```text
tests/test_seller_conversation_summary_privacy.py       88
scripts/verify_seller_conversation_summary_privacy.py       99
scripts/seller_summary_privacy_contract.py      133
scripts/seller_summary_privacy_isolation.py       56
scripts/seller_summary_privacy_app_probe.py      201
```

Observable: PASS, every changed Python file is at or below 250 pure LOC.

Artifact path: `.omo/evidence/final-post-closeout-f4-remediation.md`.

### Conflict Scan

Scenario: conflict marker scan on owned remediation files and evidence.

Invocation:

```bash
rg -n '^(<<<<<<<|=======|>>>>>>>)' tests/test_seller_conversation_summary_privacy.py scripts/verify_seller_conversation_summary_privacy.py scripts/seller_summary_privacy_contract.py scripts/seller_summary_privacy_isolation.py scripts/seller_summary_privacy_app_probe.py .omo/evidence/final-post-closeout-f4-remediation.md .omo/evidence/task-4-dalya-post-closeout-hardening.md .omo/evidence/task-4-seller-summary-api.json .omo/evidence/task-4-seller-summary-privacy-pure.json
```

Observable: PASS/no matches, exit 1, empty output.

Artifact path: `.omo/evidence/final-post-closeout-f4-remediation.md`.

## Residual Risk

Local Python 3.14 lacks `sqlalchemy`, so DB-backed TestClient behavior could not run to PASS here. The verifier and pytest fail closed before app DB import, and the verifier evidence proves env-file reads were blocked before the missing dependency stopped execution.
