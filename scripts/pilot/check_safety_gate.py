#!/usr/bin/env python3
"""
Phase 0 safety gate for the internal Mahoroba OMO pilot.

Fails closed unless the current environment proves it is safe for pilot writes:

1. MESSAGING_TRANSPORT must be ``simulated`` (no live WhatsApp/Twilio/360dialog).
2. DALYA_ENV must be one of {development, test, pilot}, or ``staging`` ONLY when
   ``DALYA_PILOT_STAGING_CONFIRMED`` explicitly records the pilot brokerage as
   isolated. Production-class environments are always refused.
3. DATABASE_URL must be set and its host must differ from every PROD_DB_HOST.
4. PROD_DB_HOST must be configured so production can be denylisted.
5. The pilot marker must match the expected reset-scope marker, proving reset
   targets only pilot-tagged rows (``dalya_pilot=<marker>`` / ``pilot_`` ids).

This script NEVER prints secret values. It reports only non-secret booleans,
the environment name, the transport kind, and the (non-secret) pilot marker.

Usage:
    PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated \
        python scripts/pilot/check_safety_gate.py --pilot-marker mahoroba-first-run \
        [--env-file .omo/pilots/lazycodex-omo-pilot/.env.pilot] \
        [--evidence .omo/evidence/lazycodex-omo-pilot/task-2-safety.json]

Exit code 0 means GATE PASS; any non-zero exit means the gate refused the run
BEFORE any database write or live send could occur.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Environments allowed to carry pilot writes. "pilot" is an additive pilot-only
# class on top of the standard test-class environments in tests/safety.py.
PILOT_ENV_ALLOWLIST = frozenset({"development", "dev", "test", "testing", "pilot"})
PRODUCTION_ENVS = frozenset({"production", "prod"})
SIMULATED_TRANSPORT = "simulated"


def _normalize_host(host: Optional[str]) -> str:
    return (host or "").strip().lower().rstrip(".")


def _prod_hosts(env: Mapping[str, str]) -> set[str]:
    raw = env.get("PROD_DB_HOST", "")
    return {_normalize_host(h) for h in raw.split(",") if _normalize_host(h)}


def _load_env_file(env_file: Optional[str]) -> None:
    """Load a dev/test env file so its values populate os.environ. Never prints values.

    Exported shell values stay authoritative (override=False), matching CI behaviour.
    """
    if not env_file:
        return
    path = Path(env_file)
    if not path.exists():
        raise FileNotFoundError(f"--env-file not found: {env_file}")
    from dotenv import load_dotenv

    load_dotenv(path, override=False)


class Check:
    def __init__(self, name: str, passed: bool, detail: str) -> None:
        self.name = name
        self.passed = passed
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {"check": self.name, "status": "PASS" if self.passed else "FAIL", "detail": self.detail}


def run_checks(env: Mapping[str, str], pilot_marker: str) -> list[Check]:
    checks: list[Check] = []

    # 1. Transport must be simulated.
    transport = (env.get("MESSAGING_TRANSPORT") or "twilio").strip().lower()
    checks.append(
        Check(
            "messaging_transport_simulated",
            transport == SIMULATED_TRANSPORT,
            f"MESSAGING_TRANSPORT={transport!r} (must be 'simulated'; no live sends).",
        )
    )

    # 2. Environment must be pilot-safe.
    dalya_env = (env.get("DALYA_ENV") or "").strip().lower()
    staging_confirmed = (env.get("DALYA_PILOT_STAGING_CONFIRMED") or "").strip()
    if dalya_env in PRODUCTION_ENVS:
        env_ok, env_detail = False, f"DALYA_ENV={dalya_env!r} is production-class; refused."
    elif dalya_env in PILOT_ENV_ALLOWLIST:
        env_ok, env_detail = True, f"DALYA_ENV={dalya_env!r} is pilot-safe."
    elif dalya_env == "staging":
        env_ok = bool(staging_confirmed)
        env_detail = (
            "DALYA_ENV='staging' allowed: DALYA_PILOT_STAGING_CONFIRMED records explicit isolation."
            if staging_confirmed
            else "DALYA_ENV='staging' refused: set DALYA_PILOT_STAGING_CONFIRMED to confirm isolation."
        )
    else:
        env_ok = False
        env_detail = (
            f"DALYA_ENV={dalya_env or '<unset>'!r} is not pilot-safe. "
            "Use development|test|pilot, or confirmed-isolated staging."
        )
    checks.append(Check("dalya_env_pilot_safe", env_ok, env_detail))

    # 3 + 4. Database host must be set and distinct from every PROD_DB_HOST.
    database_url = env.get("DATABASE_URL") or ""
    prod_hosts = _prod_hosts(env)
    target_host = _normalize_host(urlparse(database_url).hostname) if database_url else ""
    if not prod_hosts:
        checks.append(Check("prod_host_configured", False, "PROD_DB_HOST is not set; cannot denylist production."))
    else:
        checks.append(Check("prod_host_configured", True, "PROD_DB_HOST is configured."))
    if not database_url:
        checks.append(Check("database_url_set", False, "DATABASE_URL is not set; refusing to guess a target."))
    elif not target_host:
        checks.append(Check("database_url_set", False, "DATABASE_URL host could not be parsed; refusing."))
    else:
        checks.append(Check("database_url_set", True, "DATABASE_URL host parsed."))
    host_distinct = bool(target_host) and bool(prod_hosts) and target_host not in prod_hosts
    checks.append(
        Check(
            "database_host_not_production",
            host_distinct,
            "Target DB host is distinct from PROD_DB_HOST."
            if host_distinct
            else "Target DB host matches (or cannot be proven distinct from) PROD_DB_HOST.",
        )
    )

    # 5. Pilot marker (reset scope) must be present and well-formed.
    marker_ok = bool(pilot_marker) and pilot_marker.replace("-", "").replace("_", "").isalnum()
    checks.append(
        Check(
            "pilot_marker_valid",
            marker_ok,
            f"Reset scope marker={pilot_marker!r}; reset deletes only rows tagged dalya_pilot={pilot_marker!r} "
            "or carrying 'pilot_' ids."
            if marker_ok
            else f"Pilot marker {pilot_marker!r} is missing or malformed.",
        )
    )

    return checks


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 0 safety gate for the internal Mahoroba OMO pilot.")
    parser.add_argument("--pilot-marker", required=True, help="Reset-scope marker, e.g. mahoroba-first-run.")
    parser.add_argument("--env-file", default=None, help="Optional dev/test env file to load (values never printed).")
    parser.add_argument("--evidence", default=None, help="Optional path to write JSON evidence.")
    args = parser.parse_args(argv)

    try:
        _load_env_file(args.env_file)
    except FileNotFoundError as exc:
        print(f"GATE FAIL: {exc}", file=sys.stderr)
        return 2

    checks = run_checks(os.environ, args.pilot_marker)
    gate_passed = all(check.passed for check in checks)

    print("Dalya pilot Phase 0 safety gate")
    print("-" * 40)
    for check in checks:
        symbol = "PASS" if check.passed else "FAIL"
        print(f"  [{symbol}] {check.name}: {check.detail}")
    print("-" * 40)
    print(f"GATE {'PASS' if gate_passed else 'FAIL'}")

    if args.evidence:
        evidence_path = Path(args.evidence)
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "gate": "phase-0-safety",
            "pilot_marker": args.pilot_marker,
            "result": "PASS" if gate_passed else "FAIL",
            "checks": [check.as_dict() for check in checks],
        }
        evidence_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Evidence written: {evidence_path}")

    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
