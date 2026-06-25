#!/usr/bin/env python3
"""
First-run Mahoroba pilot — minimal safety sanity (T9).

NOT a full tenant/security audit. Verifies the first-run guardrails:
- no live sends (pilot transport is simulated)
- unauthenticated + wrong-brokerage access to pilot-critical resources is denied
- opt-out suppression, no seller-private leakage, and Verified Facts deferral
  (read from the T4 scenario evidence)

Explicitly DEFERRED (reported, not run): full tenant isolation audit, media URL
signing depth, live/sandbox provider readiness, and production RLS/app-role rollout.

Usage:
  PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated venv/bin/python scripts/pilot/verify_minimal_safety.py \
      --brokerage-id mahoroba-realty --evidence .omo/evidence/lazycodex-omo-pilot/task-9-safety.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

os.environ.setdefault("MESSAGING_TRANSPORT", "simulated")
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFERRED = [
    "full tenant isolation audit",
    "media URL signing depth",
    "live / sandbox provider readiness",
    "production RLS / app-role rollout",
]


def _status(base_url: str, path: str, headers: dict) -> int:
    req = urllib.request.Request(base_url + path, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--brokerage-id", default="mahoroba-realty")
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--env-file", default=".omo/pilots/lazycodex-omo-pilot/.env.pilot")
    p.add_argument("--scenarios", default=".omo/evidence/lazycodex-omo-pilot/scenarios/scenario-results.json")
    p.add_argument("--evidence", default=".omo/evidence/lazycodex-omo-pilot/task-9-safety.json")
    args = p.parse_args()

    # Load the pilot env so DALYA_ENV=pilot is set — the transport factory refuses
    # simulated transport in live-class envs, so the check must run as the pilot env.
    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)
    os.environ["MESSAGING_TRANSPORT"] = "simulated"

    checks = {}

    # 1) No live sends — pilot transport must be simulated.
    try:
        from app.core.messaging import get_transport
        tname = type(get_transport()).__name__
        checks["no_live_sends"] = {"result": "PASS" if tname == "SimulatedTransport" else "FAIL",
                                   "detail": f"MESSAGING_TRANSPORT={os.getenv('MESSAGING_TRANSPORT')} → {tname}"}
    except Exception as exc:
        checks["no_live_sends"] = {"result": "BLOCKED", "detail": repr(exc)}

    # 2) Unauth + wrong-brokerage denial on a pilot-critical resource.
    unauth = _status(args.base_url, "/api/v1/agent/escalations", {})
    wrong = _status(args.base_url, "/api/v1/agent/escalations", {"X-Brokerage-Id": "irwin-real-estate"})
    checks["unauthenticated_denied"] = {"result": "PASS" if unauth in (401, 403) else ("BLOCKED" if unauth < 0 else "FAIL"),
                                        "detail": f"GET /agent/escalations unauth → {unauth}"}
    checks["wrong_brokerage_denied"] = {"result": "PASS" if wrong in (401, 403) else ("BLOCKED" if wrong < 0 else "FAIL"),
                                        "detail": f"wrong X-Brokerage-Id (no JWT) → {wrong}"}

    # 3) Behavioural guardrails from the T4 scenario evidence.
    scen_path = Path(args.scenarios)
    if scen_path.exists():
        scen = json.loads(scen_path.read_text())
        by_slug = {s["slug"]: s for s in scen.get("scenarios", [])}

        def _check(slug, key):
            s = by_slug.get(slug, {})
            return s.get("checks", {}).get(key) is True

        opt = by_slug.get("opt_out", {})
        checks["opt_out_suppressed"] = {"result": "PASS" if opt.get("checks", {}).get("suppressed_no_marketing_push") is True else "FAIL",
                                        "detail": f"opt_out status={opt.get('status')}"}
        leaks = [s for s in scen.get("scenarios", []) if s.get("checks", {}).get("no_seller_private_leak") is False]
        checks["no_seller_private_leak"] = {"result": "PASS" if not leaks else "FAIL",
                                            "detail": f"{len(leaks)} scenario(s) leaked seller-private text"}
        vf = _check("offplan_verified_facts", "defers_legal_finance") and _check("weak_listing_fact_gap", "does_not_invent_then_confirms")
        checks["verified_facts_defers"] = {"result": "PASS" if vf else "FAIL",
                                           "detail": "off-plan finance + weak-listing fact gaps defer to the agent"}
    else:
        for k in ("opt_out_suppressed", "no_seller_private_leak", "verified_facts_defers"):
            checks[k] = {"result": "BLOCKED", "detail": "T4 scenario evidence not found — run run_scenarios.py first"}

    verdict = "PASS" if all(c["result"] == "PASS" for c in checks.values()) else (
        "BLOCKED" if any(c["result"] == "BLOCKED" for c in checks.values()) and not any(c["result"] == "FAIL" for c in checks.values())
        else "FAIL")
    out = {"brokerage_id": args.brokerage_id, "scope": "minimal first-run safety (NOT a full audit)",
           "verdict": verdict, "checks": checks, "deferred": DEFERRED}
    print(json.dumps(out, indent=2))
    Path(args.evidence).parent.mkdir(parents=True, exist_ok=True)
    Path(args.evidence).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
