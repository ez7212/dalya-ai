#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run scripts/verify_seller_conversation_summary_privacy.py --evidence .omo/evidence/task-4-seller-summary-api.json
# 3. Or make executable and run:
#      chmod +x scripts/verify_seller_conversation_summary_privacy.py && ./scripts/verify_seller_conversation_summary_privacy.py --evidence .omo/evidence/task-4-seller-summary-api.json
# ──────────────────
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import TypeAlias

from app.core.seller_summary_privacy import JsonValue
from scripts.seller_summary_privacy_contract import (
    SAFE_CONTEXT,
    pure_first_name_redaction_passes,
    pure_phone_redaction_passes,
    pure_recursive_redaction_passes,
)
from scripts.seller_summary_privacy_isolation import (
    UnsafeDatabaseHarnessError,
    install_isolated_app_database,
)

Evidence: TypeAlias = dict[str, JsonValue]


def _dotenv_reads_blocked() -> bool:
    dotenv_module = sys.modules.get("dotenv")
    load_dotenv = getattr(dotenv_module, "load_dotenv", None)
    return getattr(load_dotenv, "__name__", "") == "_blocked_load_dotenv"


def _base_result(status: str) -> Evidence:
    return {
        "status": status,
        "seller_status_code": -1,
        "agent_status_code": -1,
        "forbidden_status_code": -1,
        "safe_context_preserved": False,
        "seller_redaction_placeholders_present": [],
        "stored_summary_unchanged": False,
        "stored_conversation_identity_preserved": False,
        "agent_identity_preserved": False,
        "forbidden_response_leak_free": False,
        "pure_first_name_redaction": pure_first_name_redaction_passes(),
        "pure_phone_redaction": pure_phone_redaction_passes(),
        "pure_recursive_preservation": pure_recursive_redaction_passes(),
        "isolated_sqlite_database": None,
        "dotenv_reads_blocked": _dotenv_reads_blocked(),
        "failed_before_app_db_import": "app.db.session" not in sys.modules,
        "forbidden_runtime_blocker": None,
    }


def _blocked_result(reason: str) -> Evidence:
    result = _base_result("BLOCKED")
    result["forbidden_runtime_blocker"] = reason
    return result


def _pass_fail_result() -> Evidence:
    isolated_database = install_isolated_app_database("verifier")
    from scripts.seller_summary_privacy_app_probe import cleanup_rows, run_app_probe, seed_rows

    cleanup_rows()
    try:
        seed_rows()
        probe = run_app_probe()
    finally:
        cleanup_rows()

    status = "PASS" if all((
        probe.passed,
        pure_first_name_redaction_passes(),
        pure_phone_redaction_passes(),
        pure_recursive_redaction_passes(),
        probe.sqlite_database_path == str(isolated_database.path),
    )) else "FAIL"
    return {
        "status": status,
        "seller_status_code": probe.seller_status_code,
        "agent_status_code": probe.agent_status_code,
        "forbidden_status_code": probe.forbidden_status_code,
        "safe_context_preserved": SAFE_CONTEXT in probe.seller_text,
        "seller_redaction_placeholders_present": list(probe.placeholders),
        "stored_summary_unchanged": probe.stored_summary_unchanged,
        "stored_conversation_identity_preserved": probe.stored_conversation_identity_preserved,
        "agent_identity_preserved": probe.agent_identity_preserved,
        "forbidden_response_leak_free": probe.forbidden_response_leak_free,
        "pure_first_name_redaction": pure_first_name_redaction_passes(),
        "pure_phone_redaction": pure_phone_redaction_passes(),
        "pure_recursive_preservation": pure_recursive_redaction_passes(),
        "isolated_sqlite_database": probe.sqlite_database_path,
        "dotenv_reads_blocked": isolated_database.dotenv_reads_blocked,
        "failed_before_app_db_import": False,
        "forbidden_runtime_blocker": None,
    }


def _verify() -> Evidence:
    try:
        return _pass_fail_result()
    except ModuleNotFoundError as exc:
        return _blocked_result(f"missing_module:{exc.name}")
    except UnsafeDatabaseHarnessError as exc:
        return _blocked_result(f"unsafe_database_harness:{exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    result = _verify()
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "evidence": str(args.evidence)}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
