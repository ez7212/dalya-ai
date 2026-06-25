#!/usr/bin/env python3
"""
First-run Mahoroba pilot — API smoke (T6).

Hits the pilot-critical agent endpoints on the live pilot server. Without Eric's
Supabase JWT the authenticated data path cannot be exercised, so each check is a
SMOKE PASS proving the endpoint is wired and auth-protected (403 unauth) — NOT a
full PASS. Full data verification with Eric's JWT is reported BLOCKED.

Usage:
  PYTHONPATH=$(pwd) venv/bin/python scripts/pilot/verify_api_smoke.py \
      --base-url http://localhost:8000 --brokerage-id mahoroba-realty \
      --evidence .omo/evidence/lazycodex-omo-pilot/task-6-api-smoke.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

PILOT_CRITICAL = [
    ("GET", "/api/v1/agent/hot-list", "hot-list / today queue"),
    ("GET", "/api/v1/agent/buyers", "buyers list / card"),
    ("GET", "/api/v1/agent/drafts", "draft queue"),
    ("GET", "/api/v1/agent/escalations", "escalation inbox"),
    ("GET", "/api/v1/agent/offers", "offers"),
    ("GET", "/api/v1/agent/viewings", "viewings"),
    ("GET", "/api/v1/agent/leads/pilot_conv_adam", "conversation detail"),
]


def _status(base_url: str, method: str, path: str, headers: dict) -> int:
    req = urllib.request.Request(base_url + path, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--brokerage-id", default="mahoroba-realty")
    p.add_argument("--jwt", default=os.getenv("ERIC_PILOT_JWT"), help="Eric Supabase JWT (enables full PASS).")
    p.add_argument("--evidence", default=".omo/evidence/lazycodex-omo-pilot/task-6-api-smoke.json")
    args = p.parse_args()

    has_jwt = bool(args.jwt)
    checks = []
    for method, path, label in PILOT_CRITICAL:
        # 1) unauth must be rejected (route wired + protected)
        unauth = _status(args.base_url, method, path, {})
        protected = unauth in (401, 403)
        row = {"method": method, "endpoint": path, "label": label, "auth_mode": "unauth",
               "status": unauth, "assertion": "rejects unauthenticated (401/403)",
               "result": "SMOKE PASS" if protected else "FAIL"}
        # 2) wrong-brokerage header without JWT is still rejected (no context bypass)
        wrong = _status(args.base_url, method, path, {"X-Brokerage-Id": "irwin-real-estate"})
        row["wrong_brokerage_status"] = wrong
        row["wrong_brokerage_rejected"] = wrong in (401, 403)
        if not row["wrong_brokerage_rejected"]:
            row["result"] = "FAIL"
        # 3) full authed data path
        if has_jwt:
            authed = _status(args.base_url, method, path,
                             {"Authorization": f"Bearer {args.jwt}", "X-Brokerage-Id": args.brokerage_id})
            row["authed_status"] = authed
            row["auth_mode"] = "eric-jwt"
            row["result"] = "PASS" if authed == 200 else "FAIL"
        else:
            row["full_auth"] = "BLOCKED — no Eric JWT (set --jwt or ERIC_PILOT_JWT)"
        checks.append(row)

    agg = {
        "smoke_pass": sum(c["result"] == "SMOKE PASS" for c in checks),
        "pass": sum(c["result"] == "PASS" for c in checks),
        "fail": sum(c["result"] == "FAIL" for c in checks),
        "full_auth_blocked": (not has_jwt),
    }
    out = {
        "base_url": args.base_url, "brokerage_id": args.brokerage_id, "auth_available": has_jwt,
        "note": "Unauth/wrong-brokerage smoke proves routing + tenant-auth guard. Full data PASS needs Eric's JWT.",
        "aggregate": agg, "checks": checks,
    }
    print(json.dumps(out, indent=2))
    Path(args.evidence).parent.mkdir(parents=True, exist_ok=True)
    Path(args.evidence).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return 0 if agg["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
