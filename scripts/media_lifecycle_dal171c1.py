#!/usr/bin/env python
"""DAL-171C1 media lifecycle schema and retention cleanup helper.

Dry-run/print-only by default. Mutations are intended for local/test/rehearsal
only and are guarded against staging/production-like targets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy import create_engine, text


ALLOWED_MUTATION_ENVS = {"test", "local", "development", "dev", "ci", "rehearsal"}
LIVE_ENV_MARKERS = ("production", "prod", "staging", "stage", "preview", "live")
SAFE_IDENTITY_MARKERS = (
    "test",
    "local",
    "localhost",
    "127.0.0.1",
    "ci",
    "dev",
    "development",
    "rehearsal",
)


SCHEMA_SQL = [
    "alter table media_assets add column if not exists signing_nonce text",
    """
    update media_assets
    set signing_nonce = media_asset_id || '-' || substr(md5(media_asset_id || now()::text || random()::text), 1, 24)
    where signing_nonce is null or signing_nonce = ''
    """,
    "alter table media_assets alter column signing_nonce set not null",
    "alter table media_assets add column if not exists revoked_at timestamp",
    "alter table media_assets add column if not exists deleted_at timestamp",
    "alter table media_assets add column if not exists retention_until timestamp",
    "create index if not exists ix_media_assets_revoked_at on media_assets (revoked_at)",
    "create index if not exists ix_media_assets_deleted_at on media_assets (deleted_at)",
    "create index if not exists ix_media_assets_retention_until on media_assets (retention_until)",
]


def _target_metadata(database_url: str) -> dict:
    parsed = urlparse(database_url or "")
    return {
        "host": parsed.hostname or "",
        "database": (parsed.path or "").lstrip("/"),
        "username": parsed.username or "",
        "scheme": parsed.scheme or "",
    }


def _contains_live_marker(value: str) -> bool:
    lowered = (value or "").lower()
    return any(marker in lowered for marker in LIVE_ENV_MARKERS)


def _contains_safe_marker(value: str) -> bool:
    lowered = (value or "").lower()
    return any(marker in lowered for marker in SAFE_IDENTITY_MARKERS)


def assert_mutation_allowed() -> None:
    env = (os.getenv("DALYA_ENV") or "").strip().lower()
    if env not in ALLOWED_MUTATION_ENVS:
        raise SystemExit(
            "Refusing media lifecycle mutation: DALYA_ENV must be one of "
            f"{sorted(ALLOWED_MUTATION_ENVS)}."
        )

    if os.getenv("DALYA_ALLOW_MEDIA_LIFECYCLE_MUTATION") != "1":
        raise SystemExit(
            "Refusing media lifecycle mutation: set "
            "DALYA_ALLOW_MEDIA_LIFECYCLE_MUTATION=1."
        )

    database_url = os.getenv("DATABASE_URL") or ""
    if not database_url:
        raise SystemExit("Refusing media lifecycle mutation: DATABASE_URL is missing.")

    metadata = _target_metadata(database_url)
    prod_host = (os.getenv("PROD_DB_HOST") or "").strip().lower()
    target_values = [
        database_url,
        metadata["host"],
        metadata["database"],
        metadata["username"],
    ]
    if prod_host and prod_host in metadata["host"].lower():
        raise SystemExit("Refusing media lifecycle mutation: host matches PROD_DB_HOST.")
    if any(_contains_live_marker(value) for value in target_values):
        raise SystemExit("Refusing media lifecycle mutation: target looks live/staging.")
    if not any(_contains_safe_marker(value) for value in target_values):
        raise SystemExit(
            "Refusing media lifecycle mutation: target metadata lacks a safe "
            "test/local/dev/ci/rehearsal marker."
        )


def run_schema_apply() -> None:
    assert_mutation_allowed()
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.begin() as conn:
        for statement in SCHEMA_SQL:
            conn.execute(text(statement))
    print(json.dumps({"applied": "schema", "statements": len(SCHEMA_SQL)}, indent=2))


def run_cleanup_expired(*, dry_run: bool, limit: int) -> None:
    if not dry_run:
        assert_mutation_allowed()

    from app.core.media_assets import delete_media_asset_bytes
    from app.db.session import SessionLocal
    from app.models.db_models import DBMediaAsset

    with SessionLocal() as db:
        rows = (
            db.query(DBMediaAsset)
            .filter(
                DBMediaAsset.retention_until.isnot(None),
                DBMediaAsset.retention_until < datetime.utcnow(),
                DBMediaAsset.deleted_at.is_(None),
            )
            .order_by(DBMediaAsset.retention_until.asc())
            .limit(limit)
            .all()
        )
        if dry_run:
            print(json.dumps({
                "dry_run": True,
                "eligible": [
                    {
                        "media_asset_id": asset.media_asset_id,
                        "brokerage_id": asset.brokerage_id,
                        "source": asset.source,
                        "retention_until": asset.retention_until.isoformat() if asset.retention_until else None,
                    }
                    for asset in rows
                ],
            }, indent=2))
            return
        for asset in rows:
            delete_media_asset_bytes(db, asset, reason="retention_expired")
        print(json.dumps({"deleted": len(rows)}, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-sql", action="store_true", help="Print schema SQL and exit.")
    parser.add_argument("--apply-schema", action="store_true", help="Apply schema changes; guarded.")
    parser.add_argument("--cleanup-expired", action="store_true", help="Process expired media retention rows.")
    parser.add_argument("--apply", action="store_true", help="Mutate cleanup rows; guarded. Default cleanup is dry-run.")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)

    if args.limit <= 0:
        raise SystemExit("--limit must be positive")

    if args.print_sql or (not args.apply_schema and not args.cleanup_expired):
        print(json.dumps({"schema_sql": SCHEMA_SQL, "dry_run_default": True}, indent=2))
        return 0
    if args.apply_schema:
        run_schema_apply()
    if args.cleanup_expired:
        run_cleanup_expired(dry_run=not args.apply, limit=args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
