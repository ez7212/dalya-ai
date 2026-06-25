#!/usr/bin/env python3
"""
First-run Mahoroba pilot — dependent seed (T3).

Seeds pilot-marked CHILD rows under the canonical `mahoroba-realty` brokerage,
linked to the FOUR listings Eric created through the dashboard (resolved by
project name). Never creates listings, never touches non-pilot Mahoroba rows,
never sends anything.

Every pilot row is reset-safe:
- string PKs are prefixed `pilot_`
- buyer phones are in the dedicated +971551000xxx pilot range
- metadata carries {"dalya_pilot": "mahoroba-first-run"}

Usage:
  PYTHONPATH=$(pwd) MESSAGING_TRANSPORT=simulated venv/bin/python scripts/pilot/seed_mahoroba_pilot.py \
      --env-file .omo/pilots/lazycodex-omo-pilot/.env.pilot --apply \
      --summary .omo/evidence/lazycodex-omo-pilot/seed-summary.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BROKERAGE_ID = "mahoroba-realty"
ERIC_USER_ID = "df53e1fb-29e7-4d9f-8f28-a12cfc3f7b02"
PILOT_MARK = {"dalya_pilot": "mahoroba-first-run"}
NOW = datetime(2026, 6, 25, 12, 0, 0)  # fixed stamp (Date.now is unavailable; deterministic seed)

# Supporting agents (data-only; Eric is the real Supabase user)
AGENTS = [
    {"key": "sara", "user_id": "pilot_sara", "name": "Sara Khan", "phone": "+971500000011", "specialty": "Dubai Hills ready villas"},
    {"key": "omar", "user_id": "pilot_omar", "name": "Omar Haddad", "phone": "+971500000012", "specialty": "Emaar / off-plan"},
    {"key": "lina", "user_id": "pilot_lina", "name": "Lina Petrova", "phone": "+971500000013", "specialty": "viewing coordination"},
]

# Buyer personas → listing archetype key + assigned agent
BUYERS = [
    {"key": "adam", "phone": "+971551000001", "name": "Adam Miller", "budget": 6_500_000, "listing": "golden_ready", "agent": ERIC_USER_ID, "stage": "hot"},
    {"key": "priya", "phone": "+971551000002", "name": "Priya Shah", "budget": 13_000_000, "listing": "offplan", "agent": "pilot_omar", "stage": "engaged"},
    {"key": "lowctx", "phone": "+971551000003", "name": None, "budget": None, "listing": "golden_ready", "agent": ERIC_USER_ID, "stage": "new"},
    {"key": "hassan", "phone": "+971551000004", "name": "Hassan Ali", "budget": 80_000_000, "listing": "luxury", "agent": ERIC_USER_ID, "stage": "offer"},
    {"key": "mei", "phone": "+971551000005", "name": "Mei Chen", "budget": 85_000_000, "listing": "luxury", "agent": ERIC_USER_ID, "stage": "engaged"},
    {"key": "tom", "phone": "+971551000006", "name": "Tom Becker", "budget": 4_000_000, "listing": "weak_ready", "agent": "pilot_sara", "stage": "engaged"},
    {"key": "optout", "phone": "+971551000007", "name": "Opt-out Buyer", "budget": None, "listing": "golden_ready", "agent": ERIC_USER_ID, "stage": "suppressed"},
]


def _resolve_listings(db):
    """Map archetype keys → the dashboard-created listing ids by project name."""
    from app.models.db_models import DBListing
    rows = db.query(DBListing).filter(DBListing.brokerage_id == BROKERAGE_ID).all()
    by_project = {}
    for r in rows:
        spa = r.spa_data if isinstance(r.spa_data, dict) else {}
        proj = (spa.get("project") or "").strip().lower()
        by_project[proj] = r

    def pick(*names):
        for n in names:
            if n in by_project:
                return by_project[n]
        return None

    golden = pick("golf grove")
    weak = pick("park ridge")
    offplan = next((r for r in rows if r.property_type == "off_plan"), None)
    luxury = max((r for r in rows if r.seller_asking_price), key=lambda r: r.seller_asking_price or 0, default=None)
    mapping = {"golden_ready": golden, "weak_ready": weak, "offplan": offplan, "luxury": luxury}
    return {k: v for k, v in mapping.items() if v is not None}


def _upsert(db, model, pk_name, pk_value, fields):
    obj = db.get(model, pk_value)
    if obj is None:
        obj = model(**{pk_name: pk_value}, **fields)
        db.add(obj)
    else:
        for k, v in fields.items():
            setattr(obj, k, v)
    return obj


def seed(db, apply: bool) -> dict:
    from app.models.db_models import (
        DBAgentProfile, DBAIDraft, DBBrokerageMember, DBBuyerProfile, DBConversation,
        DBEscalationThread, DBEscalationThreadQuestion, DBMessage, DBOfferRecord, DBViewing,
    )

    listings = _resolve_listings(db)
    counts = {"listings_resolved": len(listings)}
    if len(listings) < 3:
        raise SystemExit(f"Only resolved {len(listings)} listings under {BROKERAGE_ID}; create them via the dashboard first.")

    # ── Agents (member + profile) ──────────────────────────────────────────
    for a in AGENTS:
        _upsert(db, DBBrokerageMember, "member_id", f"pilot_member_{a['key']}", {
            "brokerage_id": BROKERAGE_ID, "user_id": a["user_id"], "email": f"{a['key']}+dalya-pilot@example.com",
            "display_name": a["name"], "phone": a["phone"], "role": "agent", "status": "active",
            "settings": dict(PILOT_MARK), "updated_at": NOW,
        })
        _upsert(db, DBAgentProfile, "profile_id", f"pilot_profile_{a['key']}", {
            "brokerage_id": BROKERAGE_ID, "user_id": a["user_id"], "email": f"{a['key']}+dalya-pilot@example.com",
            "full_name": a["name"], "display_name": a["name"], "whatsapp_phone": a["phone"],
            "rera_broker_card_number": f"BRN-PILOT-{a['key'].upper()}", "verification_status": "approved",
            "onboarding_status": "active", "settings": dict(PILOT_MARK), "updated_at": NOW,
        })
    counts["agents"] = len(AGENTS)

    # ── Buyers + conversations + messages ──────────────────────────────────
    conv_by_buyer = {}
    for b in BUYERS:
        listing = listings.get(b["listing"]) or next(iter(listings.values()))
        _upsert(db, DBBuyerProfile, "phone", b["phone"], {
            "brokerage_id": BROKERAGE_ID, "name": b["name"], "budget_aed": b["budget"],
            "lead_stage": b["stage"], "lead_source": "pilot", "tags": ["pilot", "mahoroba-first-run"],
            "updated_at": NOW,
        })
        conv = _upsert(db, DBConversation, "conversation_id", f"pilot_conv_{b['key']}", {
            "listing_id": listing.listing_id, "brokerage_id": BROKERAGE_ID, "assigned_agent_id": b["agent"],
            "buyer_phone": b["phone"], "buyer_name": b["name"], "detected_budget": b["budget"],
            "ai_mode": "paused" if b["key"] == "mei" else "active",
            "escalation_triggered": b["key"] in {"mei", "tom", "hassan", "priya"},
            "ai_summary": {"interest_level": "high" if b["stage"] in ("hot", "offer") else "medium"},
            "updated_at": NOW - timedelta(minutes=10),
        })
        conv_by_buyer[b["key"]] = (conv, listing)
        if apply:
            db.flush()
        if not db.query(DBMessage).filter(DBMessage.conversation_id == conv.conversation_id).first():
            opener = _opener_for(b["key"])
            db.add_all([
                DBMessage(conversation_id=conv.conversation_id, role="user", content=opener, intent="general_enquiry", timestamp=NOW - timedelta(minutes=30)),
                DBMessage(conversation_id=conv.conversation_id, role="assistant", content="Thanks for your interest — happy to help with this listing.", intent="general_enquiry", timestamp=NOW - timedelta(minutes=29)),
            ])
    counts["buyers"] = len(BUYERS)
    counts["conversations"] = len(BUYERS)

    # ── Offers (Hassan below threshold on the luxury listing) ───────────────
    offers = 0
    hassan_conv, hassan_listing = conv_by_buyer["hassan"]
    asking = hassan_listing.seller_asking_price or 85_500_000
    threshold = hassan_listing.notification_threshold_aed or round(asking * 0.95)
    offer_amt = round(asking * 0.91)
    _upsert(db, DBOfferRecord, "offer_id", "pilot_offer_hassan", {
        "brokerage_id": BROKERAGE_ID, "listing_id": hassan_listing.listing_id, "conversation_id": hassan_conv.conversation_id,
        "buyer_phone": "+971551000004", "buyer_name": "Hassan Ali", "offer_amount_aed": float(offer_amt),
        "asking_price_aed": float(asking), "gap_pct": round((offer_amt - asking) / asking * 100, 2),
        "above_threshold": offer_amt >= (threshold or 0), "threshold_aed": float(threshold) if threshold else None,
        "escalated": True, "escalation_reason": "firm_offer_below_threshold", "raw_message": f"I'll offer AED {offer_amt:,.0f} for a fast close.",
        "turn_number": 4,
    })
    offers += 1
    counts["offers"] = offers

    # ── Viewing (Adam, Golf Grove, proposed) ───────────────────────────────
    adam_conv, adam_listing = conv_by_buyer["adam"]
    _upsert(db, DBViewing, "viewing_id", "pilot_viewing_adam", {
        "brokerage_id": BROKERAGE_ID, "conversation_id": adam_conv.conversation_id, "listing_id": adam_listing.listing_id,
        "buyer_phone": "+971551000001", "agent_user_id": ERIC_USER_ID, "scheduled_for": NOW + timedelta(days=1, hours=6),
        "status": "proposed", "tenant_notice_required": True, "access_notes": "Coordinate via Lina; 24h tenant notice.",
        "metadata_json": dict(PILOT_MARK), "updated_at": NOW,
    })
    counts["viewings"] = 1

    # ── Drafts (follow-ups for Adam + Tom) ─────────────────────────────────
    drafts = 0
    for key, title, body in [
        ("adam", "Confirm viewing slot", "Hi Adam, confirming a weekday-evening viewing this week — shall I lock tomorrow 6pm?"),
        ("tom", "Fact gaps to confirm", "Tom, I'm confirming the service charge, NOC status, and access details with the seller and will revert."),
    ]:
        conv, listing = conv_by_buyer[key]
        _upsert(db, DBAIDraft, "draft_id", f"pilot_draft_{key}", {
            "brokerage_id": BROKERAGE_ID, "agent_user_id": conv.assigned_agent_id, "conversation_id": conv.conversation_id,
            "listing_id": listing.listing_id, "buyer_phone": conv.buyer_phone, "draft_type": "follow_up",
            "title": title, "body": body, "status": "pending", "source": "pilot_seed",
            "metadata_json": dict(PILOT_MARK), "updated_at": NOW,
        })
        drafts += 1
    counts["drafts"] = drafts

    # ── Escalation threads (Mei takeover, Tom fact-gap, Priya legal) ────────
    esc = 0
    for key, category, subtype, qtext in [
        ("mei", "human_takeover", "speak_to_human", "Can I speak to a human agent directly?"),
        ("tom", "fact_gap", "service_charge", "What's the service charge and is the NOC ready?"),
        ("priya", "legal_process", "noc_mortgage", "What LTV can I get and what's the NOC/handover process?"),
    ]:
        conv, listing = conv_by_buyer[key]
        _upsert(db, DBEscalationThread, "thread_id", f"pilot_thread_{key}", {
            "brokerage_id": BROKERAGE_ID, "conversation_id": conv.conversation_id, "listing_id": listing.listing_id,
            "buyer_phone": conv.buyer_phone, "agent_user_id": conv.assigned_agent_id, "category": category,
            "state": "open", "escalation_type": category, "escalation_subtype": subtype, "opened_at": NOW - timedelta(minutes=20),
            "last_buyer_message_at": NOW - timedelta(minutes=20), "question_count": 1, "metadata_json": dict(PILOT_MARK), "updated_at": NOW,
        })
        _upsert(db, DBEscalationThreadQuestion, "question_id", f"pilot_q_{key}", {
            "thread_id": f"pilot_thread_{key}", "question_text": qtext, "category": category,
            "escalation_subtype": subtype, "sort_order": 0, "metadata_json": dict(PILOT_MARK),
        })
        esc += 1
    counts["escalation_threads"] = esc

    return counts


def _opener_for(key: str) -> str:
    return {
        "adam": "Hi, is the Dubai Hills villa still available? I'm cash-ready and want to view this week.",
        "priya": "Interested in the Emaar off-plan — what's the payment plan and NOC situation?",
        "lowctx": "price?",
        "hassan": "What's the lowest you'd take? I can move fast.",
        "mei": "I'd prefer to speak with a human agent about this property.",
        "tom": "What's the service charge and is there a tenant?",
        "optout": "stop",
    }.get(key, "Hi, is this still available?")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env-file", default=".omo/pilots/lazycodex-omo-pilot/.env.pilot")
    p.add_argument("--apply", action="store_true", help="Commit (default: dry-run rollback).")
    p.add_argument("--summary", default=None)
    args = p.parse_args()

    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)

    import os
    import urllib.parse
    host = urllib.parse.urlparse(os.getenv("DATABASE_URL", "")).hostname or ""
    if "ep-odd-pine" not in host and "pilot" not in (os.getenv("DALYA_ENV", "")):
        print(f"REFUSING: db_host {host} / env {os.getenv('DALYA_ENV')} is not the pilot target.", file=sys.stderr)
        return 2

    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        counts = seed(db, args.apply)
        if args.apply:
            db.commit()
            mode = "APPLIED"
        else:
            db.rollback()
            mode = "DRY-RUN (rolled back)"
    finally:
        db.close()

    summary = {"brokerage_id": BROKERAGE_ID, "mode": mode, "marker": "mahoroba-first-run", "counts": counts}
    print(json.dumps(summary, indent=2))
    if args.summary:
        Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
