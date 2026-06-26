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


def _ensure_local_postgres(db_host: str, db_url: str) -> None:
    """When the pilot points at a LOCAL Postgres, make sure the cluster is running
    (start it if not). No-op for remote DBs (Neon). Override the data dir with
    PILOT_LOCAL_PGDATA; defaults to ~/.dalya-pilot-pg."""
    if db_host not in ("localhost", "127.0.0.1"):
        return
    import os
    import socket
    import subprocess
    import time

    port = urllib.parse.urlparse(db_url).port or 5432

    def _accepting() -> bool:
        try:
            with socket.create_connection((db_host, port), timeout=1):
                return True
        except OSError:
            return False

    if _accepting():
        return

    pgdata = os.path.expanduser(os.getenv("PILOT_LOCAL_PGDATA", "~/.dalya-pilot-pg"))
    candidates = ["/opt/homebrew/opt/postgresql@17/bin/pg_ctl", "/usr/local/opt/postgresql@17/bin/pg_ctl"]
    try:
        prefix = subprocess.run(["brew", "--prefix", "postgresql@17"], capture_output=True, text=True, timeout=10).stdout.strip()
        if prefix:
            candidates.insert(0, f"{prefix}/bin/pg_ctl")
    except Exception:
        pass
    pg_ctl = next((c for c in candidates if Path(c).exists()), None)

    if not pg_ctl or not Path(pgdata).exists():
        print(f"WARNING: local Postgres on :{port} is down and could not auto-start "
              f"(pg_ctl={pg_ctl}, pgdata={pgdata}). Start it manually.", file=sys.stderr)
        return

    print(f"Local Postgres not running on :{port} — starting cluster at {pgdata} ...")
    log = os.path.expanduser("~/.dalya-pilot-pg.log")
    subprocess.run([pg_ctl, "-D", pgdata, "-l", log, "-o", f"-p {port}", "start"], check=False)
    for _ in range(40):
        if _accepting():
            print("Local Postgres is up.")
            return
        time.sleep(0.5)
    print("WARNING: local Postgres did not become ready in time.", file=sys.stderr)


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

    # Auto-start the co-located local Postgres when the pilot points at it.
    _ensure_local_postgres(db_host, os.getenv("DATABASE_URL", ""))

    if db_host in ("localhost", "127.0.0.1"):
        print("Using LOCAL co-located Postgres (fast). Switch back to Neon via .env.pilot.neonbak.")
    elif "ep-odd-pine" not in db_host:
        print(f"WARNING: db_host {db_host} is not the expected pilot branch (ep-odd-pine).", file=sys.stderr)

    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
