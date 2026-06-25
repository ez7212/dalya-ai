#!/usr/bin/env python3
"""
First-run Mahoroba pilot — surgical reset (T3).

Deletes ONLY pilot-marked dependent rows seeded by seed_mahoroba_pilot.py:
- string PKs prefixed `pilot_`
- buyer phones in the +971551000xxx pilot range
Never touches non-pilot Mahoroba records (listings, Eric's membership/profile,
real conversations). Refuses to run without DALYA_PILOT_CONFIRM=mahoroba-realty.

Usage:
  # dry-run (lists counts, deletes nothing):
  PYTHONPATH=$(pwd) venv/bin/python scripts/pilot/reset_mahoroba_pilot.py --env-file .omo/pilots/lazycodex-omo-pilot/.env.pilot --dry-run
  # apply:
  DALYA_PILOT_CONFIRM=mahoroba-realty PYTHONPATH=$(pwd) venv/bin/python scripts/pilot/reset_mahoroba_pilot.py --env-file .omo/pilots/lazycodex-omo-pilot/.env.pilot --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BROKERAGE_ID = "mahoroba-realty"
ERIC_USER_ID = "df53e1fb-29e7-4d9f-8f28-a12cfc3f7b02"
PILOT_PHONE_PREFIX = "+97155100000"  # pilot buyer range


def _plan(db):
    """Return ordered (label, model, filter) delete steps — FK-safe order."""
    from app.models.db_models import (
        DBAgentProfile, DBAIDraft, DBBrokerageMember, DBBuyerProfile, DBConversation,
        DBEscalationThread, DBEscalationThreadQuestion, DBMessage, DBOfferRecord, DBViewing,
    )
    pilot_conv_ids = [c.conversation_id for c in db.query(DBConversation.conversation_id)
                      .filter(DBConversation.conversation_id.like("pilot\\_%", escape="\\")).all()]
    steps = [
        ("escalation_questions", DBEscalationThreadQuestion, DBEscalationThreadQuestion.question_id.like("pilot\\_%", escape="\\")),
        ("escalation_threads", DBEscalationThread, DBEscalationThread.thread_id.like("pilot\\_%", escape="\\")),
        ("drafts", DBAIDraft, DBAIDraft.draft_id.like("pilot\\_%", escape="\\")),
        ("viewings", DBViewing, DBViewing.viewing_id.like("pilot\\_%", escape="\\")),
        ("offers", DBOfferRecord, DBOfferRecord.offer_id.like("pilot\\_%", escape="\\")),
        ("messages", DBMessage, DBMessage.conversation_id.in_(pilot_conv_ids) if pilot_conv_ids else DBMessage.id.is_(None)),
        ("conversations", DBConversation, DBConversation.conversation_id.like("pilot\\_%", escape="\\")),
        ("buyers", DBBuyerProfile, DBBuyerProfile.phone.like(f"{PILOT_PHONE_PREFIX}%")),
        # supporting agents only — NEVER Eric's real membership/profile
        ("agent_profiles", DBAgentProfile, DBAgentProfile.profile_id.like("pilot\\_profile\\_%", escape="\\") & (DBAgentProfile.user_id != ERIC_USER_ID)),
        ("members", DBBrokerageMember, DBBrokerageMember.member_id.like("pilot\\_member\\_%", escape="\\") & (DBBrokerageMember.user_id != ERIC_USER_ID)),
    ]
    return steps


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env-file", default=".omo/pilots/lazycodex-omo-pilot/.env.pilot")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    # Capture the operator's confirm token BEFORE loading the env file. The env
    # file may also define DALYA_PILOT_CONFIRM; that value must NEVER satisfy the
    # delete guard — only an explicit token in the operator's shell counts.
    operator_confirm = os.environ.get("DALYA_PILOT_CONFIRM")

    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)

    host = urllib.parse.urlparse(os.getenv("DATABASE_URL", "")).hostname or ""
    if "ep-odd-pine" not in host and "pilot" not in (os.getenv("DALYA_ENV", "")):
        print(f"REFUSING: db_host {host} / env {os.getenv('DALYA_ENV')} is not the pilot target.", file=sys.stderr)
        return 2

    # A wrong (typo'd) confirm token refuses outright — even on dry-run.
    if operator_confirm is not None and operator_confirm != BROKERAGE_ID:
        print(f"REFUSING: DALYA_PILOT_CONFIRM={operator_confirm!r} is not {BROKERAGE_ID!r}.", file=sys.stderr)
        return 2
    if args.apply and operator_confirm != BROKERAGE_ID:
        print(f"REFUSING apply: set DALYA_PILOT_CONFIRM={BROKERAGE_ID} in your shell to delete pilot rows.", file=sys.stderr)
        return 2

    from app.db.session import SessionLocal
    db = SessionLocal()
    counts = {}
    try:
        for label, model, flt in _plan(db):
            q = db.query(model).filter(flt)
            counts[label] = q.count()
            if args.apply:
                q.delete(synchronize_session=False)
        if args.apply:
            db.commit()
            mode = "DELETED"
        else:
            db.rollback()
            mode = "DRY-RUN (nothing deleted)"
    finally:
        db.close()

    print(json.dumps({"brokerage_id": BROKERAGE_ID, "mode": mode, "pilot_rows": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
