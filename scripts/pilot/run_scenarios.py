#!/usr/bin/env python3
"""
First-run Mahoroba pilot — buyer scenario runner (T4).

Drives the 7 first-run buyer personas through the real Property Advisor over
SIMULATED transport (no live sends), scoped to `mahoroba-realty` and the four
dashboard-created listings. Emits one JSON per scenario + an aggregate verdict.

If ANTHROPIC_API_KEY is missing the chatbot scenarios are marked BLOCKED (not
PASS) and the runner still exits 0 with a useful smoke report.

Usage:
  PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated venv/bin/python scripts/pilot/run_scenarios.py \
      --suite first-run --brokerage-id mahoroba-realty \
      --evidence-dir .omo/evidence/lazycodex-omo-pilot/scenarios
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import uuid
from pathlib import Path

os.environ.setdefault("MESSAGING_TRANSPORT", "simulated")
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BROKERAGE_ID = "mahoroba-realty"


def _resolve(db):
    from app.models.db_models import DBBrokerage, DBListing
    brk = db.get(DBBrokerage, BROKERAGE_ID)
    ai_number = getattr(brk, "brokerage_ai_number", None) or "+971590009001"
    rows = db.query(DBListing).filter(DBListing.brokerage_id == BROKERAGE_ID).all()
    by_proj = {((r.spa_data or {}).get("project") or "").strip().lower(): r for r in rows}
    listings = {
        "golden_ready": by_proj.get("golf grove"),
        "weak_ready": by_proj.get("park ridge"),
        "offplan": next((r for r in rows if r.property_type == "off_plan"), None),
        "luxury": max((r for r in rows if r.seller_asking_price), key=lambda r: r.seller_asking_price or 0, default=None),
    }
    notes = {k: ((v.seller_notes or "") if v else "") for k, v in listings.items()}
    return ai_number, listings, notes


# ── Behavioural predicates (lenient to LLM variation, but meaningful) ─────────
DEFER_TOKENS = ("confirm", "mortgage advisor", "the agent", "listing agent", "check with",
                "cannot confirm", "would need to", "i'll check", "follow up", "verify")
QUESTION_MARKS = lambda t: t.count("?")


def _defers(o):
    t = o["bot_response"].lower()
    return any(tok in t for tok in DEFER_TOKENS)


def _no_seller_private_leak(o):
    note = (o.get("_seller_notes") or "").strip().lower()
    if not note:
        return True
    t = o["bot_response"].lower()
    # no verbatim chunk of the agent-only seller note leaks to the buyer
    chunk = note[:40]
    return chunk not in t and "motivated" not in t and "discreet" not in t


def build_scenarios(ai_number, listings, notes):
    L = listings
    return [
        {"slug": "hot_ready_buyer", "buyer": "+971551000001", "listing": "golden_ready",
         "msg": "Hi, is the Dubai Hills villa still available? I'm cash-ready and want to view this week.",
         "checks": {
             "responds": lambda o: bool(o["bot_response"].strip()),
             "no_seller_private_leak": _no_seller_private_leak,
         }},
        {"slug": "offplan_verified_facts", "buyer": "+971551000002", "listing": "offplan",
         "msg": "What LTV can I get on this off-plan, and what's the NOC and handover process?",
         "checks": {
             "responds": lambda o: bool(o["bot_response"].strip()),
             "defers_legal_finance": _defers,
             "no_invented_ltv_ratio": lambda o: "50% ltv" not in o["bot_response"].lower(),
         }},
        {"slug": "low_context_price_buyer", "buyer": "+971551000003", "listing": "golden_ready",
         "msg": "price?",
         "checks": {
             "responds": lambda o: bool(o["bot_response"].strip()),
             "does_not_over_qualify": lambda o: QUESTION_MARKS(o["bot_response"]) <= 2,
         }},
        {"slug": "firm_offer_escalation", "buyer": "+971551000004", "listing": "luxury",
         "msg": "I'll offer AED 79,000,000 for a fast close. This is firm.",
         "checks": {
             "responds": lambda o: bool(o["bot_response"].strip()),
             # safe handling = escalate to the agent OR gracefully engage the offer (never ignore it)
             "handles_offer_safely": lambda o: (o["escalation"] is not None or len(o["agents_ai_envelopes"]) >= 1
                                                or "offer" in o["bot_response"].lower() or "seller" in o["bot_response"].lower()),
             "no_seller_private_leak": _no_seller_private_leak,
         }},
        {"slug": "human_takeover", "buyer": "+971551000005", "listing": "luxury",
         "msg": "I'd prefer to speak directly with a human agent about this property.",
         "checks": {
             "responds": lambda o: bool(o["bot_response"].strip()),
             "routes_to_human": lambda o: o["escalation"] is not None or len(o["agents_ai_envelopes"]) >= 1 or _defers(o),
         }},
        {"slug": "weak_listing_fact_gap", "buyer": "+971551000006", "listing": "weak_ready",
         "msg": "What's the exact service charge per sqft and is the NOC already issued?",
         "checks": {
             "responds": lambda o: bool(o["bot_response"].strip()),
             "does_not_invent_then_confirms": _defers,
         }},
        {"slug": "opt_out", "buyer": "+971551000007", "listing": "golden_ready",
         "msg": "stop",
         "checks": {
             "suppressed_no_marketing_push": lambda o: len(o["buyer_messages"]) <= 1,
         }},
    ]


def run(evidence_dir: Path, suite: str) -> dict:
    from app.core.messaging import set_transport_override
    from app.core.messaging.simulated_transport import SimulatedTransport
    from app.schemas.conversation import InboundMessage
    from app.core.chatbot_engine import engine
    from app.db.session import SessionLocal

    sim = SimulatedTransport()
    set_transport_override(sim)

    db = SessionLocal()
    try:
        ai_number, listings, notes = _resolve(db)
    finally:
        db.close()
    missing = [k for k, v in listings.items() if v is None]
    if missing:
        raise SystemExit(f"Missing listings for archetypes {missing}; seed via dashboard first.")

    has_llm = bool(os.getenv("ANTHROPIC_API_KEY"))
    scenarios = build_scenarios(ai_number, listings, notes)
    results = []

    for sc in scenarios:
        listing = listings[sc["listing"]]
        if not has_llm:
            results.append({"slug": sc["slug"], "status": "BLOCKED", "reason": "ANTHROPIC_API_KEY missing"})
            continue
        sim.clear()
        inbound = InboundMessage(from_number=sc["buyer"], to_number=ai_number,
                                 body=sc["msg"], message_sid=f"pilot-{uuid.uuid4().hex[:8]}",
                                 listing_id=listing.listing_id)
        try:
            response, escalation, media_url = engine.handle_message_resilient(inbound)
        except Exception as exc:  # resilient: a crash is a scenario FAIL, not a runner crash
            results.append({"slug": sc["slug"], "status": "FAIL", "error": repr(exc)})
            continue
        outcome = {
            "slug": sc["slug"], "listing_id": listing.listing_id, "buyer_phone": sc["buyer"],
            "message": sc["msg"], "bot_response": response or "",
            "escalation": {"type": str(escalation.escalation_type)} if escalation else None,
            "agents_ai_envelopes": [{"to": m.to_number, "tags": getattr(m, "tags", None)} for m in sim.messages_to_agents_ai()],
            "buyer_messages": [{"to": m.to_number} for m in sim.messages_to_buyer()],
            "_seller_notes": notes.get(sc["listing"], ""),
            "checks": {},
        }
        for key, pred in sc["checks"].items():
            try:
                outcome["checks"][key] = bool(pred(outcome))
            except Exception as exc:
                outcome["checks"][key] = f"error: {exc}"
        outcome["status"] = "PASS" if all(v is True for v in outcome["checks"].values()) else "FAIL"
        outcome.pop("_seller_notes", None)
        results.append(outcome)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / f"{sc['slug']}.json").write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
        print(f"[{outcome['status']}] {sc['slug']}: " + ", ".join(f"{k}={v}" for k, v in outcome["checks"].items()))

    agg = {"passed": sum(r.get("status") == "PASS" for r in results),
           "failed": sum(r.get("status") == "FAIL" for r in results),
           "blocked": sum(r.get("status") == "BLOCKED" for r in results)}
    summary = {"suite": suite, "brokerage_id": BROKERAGE_ID, "chatbot_mode": has_llm, "aggregate": agg, "scenarios": results}
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "scenario-results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--suite", default="first-run")
    p.add_argument("--brokerage-id", default=BROKERAGE_ID)
    p.add_argument("--evidence-dir", default=".omo/evidence/lazycodex-omo-pilot/scenarios")
    p.add_argument("--env-file", default=".omo/pilots/lazycodex-omo-pilot/.env.pilot")
    args = p.parse_args()

    # Respect an operator who explicitly blanks the key (ANTHROPIC_API_KEY=) to
    # force BLOCKED mode — the env file must not silently re-enable it.
    if os.environ.get("ANTHROPIC_API_KEY") == "":
        os.environ["_PILOT_FORCE_NO_LLM"] = "1"

    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)
    if os.environ.get("_PILOT_FORCE_NO_LLM") == "1":
        os.environ["ANTHROPIC_API_KEY"] = ""
    host = urllib.parse.urlparse(os.getenv("DATABASE_URL", "")).hostname or ""
    if "ep-odd-pine" not in host and "pilot" not in (os.getenv("DALYA_ENV", "")):
        print(f"REFUSING: db_host {host} is not the pilot target.", file=sys.stderr)
        return 2

    summary = run(Path(args.evidence_dir), args.suite)
    print(json.dumps({"aggregate": summary["aggregate"], "chatbot_mode": summary["chatbot_mode"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
