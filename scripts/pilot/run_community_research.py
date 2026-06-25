#!/usr/bin/env python3
"""
Run (or re-run) a community-research job against the pilot environment.

Loads `.env.pilot` with override=True first, so the freshly-added TAVILY_API_KEY
and the pilot DATABASE_URL are used — independent of any already-running backend
whose process env predates the key.

Usage:
    PYTHONPATH=$(pwd) venv/bin/python scripts/pilot/run_community_research.py \
        --project "Dubai Hills Estate" --sub-community "Golf Grove" [--research-id 9] [--developer ""]

If --research-id is omitted, the matching row (by project_name + developer) is
reused if present, else a new pending row is created.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".omo" / "pilots" / "lazycodex-omo-pilot" / ".env.pilot"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--sub-community", default=None)
    p.add_argument("--developer", default="")
    p.add_argument("--research-id", type=int, default=None)
    args = p.parse_args()

    if not ENV_FILE.exists():
        print(f"FATAL: {ENV_FILE} not found", file=sys.stderr)
        return 2
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE, override=True)

    import os

    db_host = urllib.parse.urlparse(os.getenv("DATABASE_URL", "")).hostname or "?"
    if "ep-odd-pine" not in db_host:
        print(f"REFUSING: db_host {db_host} is not the pilot branch (ep-odd-pine).", file=sys.stderr)
        return 2
    if not os.getenv("TAVILY_API_KEY"):
        print("REFUSING: TAVILY_API_KEY is not set in the pilot env.", file=sys.stderr)
        return 2
    print(f"Env OK: db_host={db_host}, TAVILY set, ANTHROPIC {'set' if os.getenv('ANTHROPIC_API_KEY') else 'MISSING'}")

    from app.db.session import service_session, safe_commit
    from app.models.db_models import DBCommunityResearch
    from app.api.research import _run_research_job

    # Resolve / create the research row.
    with service_session(is_platform_admin=True) as db:
        if args.research_id is not None:
            record = db.query(DBCommunityResearch).filter_by(id=args.research_id).first()
        else:
            record = (
                db.query(DBCommunityResearch)
                .filter_by(project_name=args.project, developer=args.developer)
                .first()
            )
        if record is None:
            record = DBCommunityResearch(project_name=args.project, developer=args.developer, status="pending")
            db.add(record)
            safe_commit(db)
            db.refresh(record)
            print(f"Created research row id={record.id} for {args.project!r}")
        else:
            old_name = record.project_name
            record.project_name = args.project
            record.developer = args.developer
            record.status = "pending"
            record.audit_flags = []
            record.file_path = None
            safe_commit(db)
            print(f"Reusing research row id={record.id} ({old_name!r} → {args.project!r}) → reset to pending")
        research_id = record.id

    print(f"Running research: project={args.project!r} sub_community={args.sub_community!r} (this calls Claude + Tavily)...")
    asyncio.run(_run_research_job(research_id=research_id, project_name=args.project,
                                  developer=args.developer, sub_community=args.sub_community))

    with service_session(is_platform_admin=True) as db:
        rec = db.query(DBCommunityResearch).filter_by(id=research_id).first()
        print("\n=== RESULT ===")
        print("  status            :", rec.status)
        print("  file_path         :", rec.file_path)
        print("  research_confidence:", rec.research_confidence)
        print("  source_urls       :", len(rec.source_urls or []), "sources")
        print("  audit_flags       :", rec.audit_flags)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
