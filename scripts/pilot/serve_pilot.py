#!/usr/bin/env python3
"""
Launch the Dalya backend bound to the isolated pilot environment.

Loads `.omo/pilots/lazycodex-omo-pilot/.env.pilot` with override=True BEFORE the
app imports, so every in-app `load_dotenv()` (which loads `.env` with
override=False) keeps the pilot values. This avoids the fragile shell
`set -a; source .env.pilot` path, which breaks on any value the shell can't parse.

Never prints secrets — only the non-secret env name, transport, and DB host.

Usage:
    PYTHONPATH=$(pwd) venv/bin/python scripts/pilot/serve_pilot.py [--port 8000] [--reload]
"""
from __future__ import annotations

import argparse
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".omo" / "pilots" / "lazycodex-omo-pilot" / ".env.pilot"


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the Dalya backend on the pilot env.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if not ENV_FILE.exists():
        print(f"FATAL: pilot env file not found: {ENV_FILE}", file=sys.stderr)
        return 2

    from dotenv import load_dotenv

    load_dotenv(ENV_FILE, override=True)

    import os

    env_name = os.getenv("DALYA_ENV") or os.getenv("ENVIRONMENT") or "?"
    transport = os.getenv("MESSAGING_TRANSPORT") or "?"
    db_host = urllib.parse.urlparse(os.getenv("DATABASE_URL", "")).hostname or "?"
    print(f"Serving Dalya backend on pilot env: DALYA_ENV={env_name} transport={transport} db_host={db_host}")
    if "ep-odd-pine" not in db_host:
        print(f"WARNING: db_host {db_host} is not the expected pilot branch (ep-odd-pine).", file=sys.stderr)

    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
