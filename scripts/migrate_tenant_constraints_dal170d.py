from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from sqlalchemy import inspect, text

from app.core.runtime_config import env_bool, env_name, is_production
from app.db.session import engine
from scripts.audit_tenant_constraints_dal170d import audit


PRODUCTION_DDL_GUARD = "ALLOW_PRODUCTION_TENANT_CONSTRAINTS"
PRODUCTION_DDL_FINGERPRINT_OVERRIDE = "ALLOW_PRODUCTION_LIKE_DB_URL_WITHOUT_PRODUCTION_ENV"
DEFAULT_LOCK_TIMEOUT_MS = 10_000
DEFAULT_STATEMENT_TIMEOUT_MS = 120_000
Phase = Literal["parent-keys", "child-indexes", "first-fks", "second-fks"]


@dataclass(frozen=True)
class DdlStatement:
    name: str
    sql: str
    rollback_sql: str
    table: str
    required_columns: tuple[str, ...]
    kind: str


PARENT_KEY_STATEMENTS: tuple[DdlStatement, ...] = (
    DdlStatement(
        "dal170d_uq_bbp_brokerage_profile",
        "CREATE UNIQUE INDEX IF NOT EXISTS dal170d_uq_bbp_brokerage_profile ON brokerage_buyer_profiles (brokerage_id, profile_id)",
        "DROP INDEX IF EXISTS dal170d_uq_bbp_brokerage_profile",
        "brokerage_buyer_profiles",
        ("brokerage_id", "profile_id"),
        "unique_index",
    ),
    DdlStatement(
        "dal170d_uq_conversations_brokerage_conversation",
        "CREATE UNIQUE INDEX IF NOT EXISTS dal170d_uq_conversations_brokerage_conversation ON conversations (brokerage_id, conversation_id)",
        "DROP INDEX IF EXISTS dal170d_uq_conversations_brokerage_conversation",
        "conversations",
        ("brokerage_id", "conversation_id"),
        "unique_index",
    ),
    DdlStatement(
        "dal170d_uq_listings_brokerage_listing",
        "CREATE UNIQUE INDEX IF NOT EXISTS dal170d_uq_listings_brokerage_listing ON listings (brokerage_id, listing_id)",
        "DROP INDEX IF EXISTS dal170d_uq_listings_brokerage_listing",
        "listings",
        ("brokerage_id", "listing_id"),
        "unique_index",
    ),
    DdlStatement(
        "dal170d_uq_viewings_brokerage_viewing",
        "CREATE UNIQUE INDEX IF NOT EXISTS dal170d_uq_viewings_brokerage_viewing ON viewings (brokerage_id, viewing_id)",
        "DROP INDEX IF EXISTS dal170d_uq_viewings_brokerage_viewing",
        "viewings",
        ("brokerage_id", "viewing_id"),
        "unique_index",
    ),
    DdlStatement(
        "dal170d_uq_media_assets_brokerage_media",
        "CREATE UNIQUE INDEX IF NOT EXISTS dal170d_uq_media_assets_brokerage_media ON media_assets (brokerage_id, media_asset_id)",
        "DROP INDEX IF EXISTS dal170d_uq_media_assets_brokerage_media",
        "media_assets",
        ("brokerage_id", "media_asset_id"),
        "unique_index",
    ),
    DdlStatement(
        "dal170d_uq_escalation_threads_brokerage_thread",
        "CREATE UNIQUE INDEX IF NOT EXISTS dal170d_uq_escalation_threads_brokerage_thread ON escalation_threads (brokerage_id, thread_id)",
        "DROP INDEX IF EXISTS dal170d_uq_escalation_threads_brokerage_thread",
        "escalation_threads",
        ("brokerage_id", "thread_id"),
        "unique_index",
    ),
    DdlStatement(
        "dal170d_uq_listing_documents_brokerage_document",
        "CREATE UNIQUE INDEX IF NOT EXISTS dal170d_uq_listing_documents_brokerage_document ON listing_documents (brokerage_id, document_id)",
        "DROP INDEX IF EXISTS dal170d_uq_listing_documents_brokerage_document",
        "listing_documents",
        ("brokerage_id", "document_id"),
        "unique_index",
    ),
)


CHILD_INDEX_STATEMENTS: tuple[DdlStatement, ...] = (
    DdlStatement(
        "dal170d_ix_bpf_brokerage_profile",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_bpf_brokerage_profile ON buyer_profile_fields (brokerage_id, profile_id)",
        "DROP INDEX IF EXISTS dal170d_ix_bpf_brokerage_profile",
        "buyer_profile_fields",
        ("brokerage_id", "profile_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_offers_brokerage_conversation",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_offers_brokerage_conversation ON offers (brokerage_id, conversation_id)",
        "DROP INDEX IF EXISTS dal170d_ix_offers_brokerage_conversation",
        "offers",
        ("brokerage_id", "conversation_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_offers_brokerage_listing",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_offers_brokerage_listing ON offers (brokerage_id, listing_id)",
        "DROP INDEX IF EXISTS dal170d_ix_offers_brokerage_listing",
        "offers",
        ("brokerage_id", "listing_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_offers_brokerage_buyer_profile",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_offers_brokerage_buyer_profile ON offers (brokerage_id, buyer_profile_id)",
        "DROP INDEX IF EXISTS dal170d_ix_offers_brokerage_buyer_profile",
        "offers",
        ("brokerage_id", "buyer_profile_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_draft_replies_brokerage_conversation",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_draft_replies_brokerage_conversation ON draft_replies (brokerage_id, conversation_id)",
        "DROP INDEX IF EXISTS dal170d_ix_draft_replies_brokerage_conversation",
        "draft_replies",
        ("brokerage_id", "conversation_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_draft_replies_brokerage_listing",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_draft_replies_brokerage_listing ON draft_replies (brokerage_id, listing_id)",
        "DROP INDEX IF EXISTS dal170d_ix_draft_replies_brokerage_listing",
        "draft_replies",
        ("brokerage_id", "listing_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_viewings_brokerage_conversation",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_viewings_brokerage_conversation ON viewings (brokerage_id, conversation_id)",
        "DROP INDEX IF EXISTS dal170d_ix_viewings_brokerage_conversation",
        "viewings",
        ("brokerage_id", "conversation_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_viewings_brokerage_listing",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_viewings_brokerage_listing ON viewings (brokerage_id, listing_id)",
        "DROP INDEX IF EXISTS dal170d_ix_viewings_brokerage_listing",
        "viewings",
        ("brokerage_id", "listing_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_media_assets_brokerage_conversation",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_media_assets_brokerage_conversation ON media_assets (brokerage_id, conversation_id)",
        "DROP INDEX IF EXISTS dal170d_ix_media_assets_brokerage_conversation",
        "media_assets",
        ("brokerage_id", "conversation_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_media_assets_brokerage_listing",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_media_assets_brokerage_listing ON media_assets (brokerage_id, listing_id)",
        "DROP INDEX IF EXISTS dal170d_ix_media_assets_brokerage_listing",
        "media_assets",
        ("brokerage_id", "listing_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_lead_assignments_brokerage_conversation",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_lead_assignments_brokerage_conversation ON lead_assignments (brokerage_id, conversation_id)",
        "DROP INDEX IF EXISTS dal170d_ix_lead_assignments_brokerage_conversation",
        "lead_assignments",
        ("brokerage_id", "conversation_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_lead_tasks_brokerage_conversation",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_lead_tasks_brokerage_conversation ON lead_tasks (brokerage_id, conversation_id)",
        "DROP INDEX IF EXISTS dal170d_ix_lead_tasks_brokerage_conversation",
        "lead_tasks",
        ("brokerage_id", "conversation_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_lead_tasks_brokerage_listing",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_lead_tasks_brokerage_listing ON lead_tasks (brokerage_id, listing_id)",
        "DROP INDEX IF EXISTS dal170d_ix_lead_tasks_brokerage_listing",
        "lead_tasks",
        ("brokerage_id", "listing_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_lead_actions_brokerage_conversation",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_lead_actions_brokerage_conversation ON lead_actions (brokerage_id, conversation_id)",
        "DROP INDEX IF EXISTS dal170d_ix_lead_actions_brokerage_conversation",
        "lead_actions",
        ("brokerage_id", "conversation_id"),
        "index",
    ),
    DdlStatement(
        "dal170d_ix_lead_actions_brokerage_listing",
        "CREATE INDEX IF NOT EXISTS dal170d_ix_lead_actions_brokerage_listing ON lead_actions (brokerage_id, listing_id)",
        "DROP INDEX IF EXISTS dal170d_ix_lead_actions_brokerage_listing",
        "lead_actions",
        ("brokerage_id", "listing_id"),
        "index",
    ),
)


FK_STATEMENTS: tuple[DdlStatement, ...] = (
    DdlStatement(
        "dal170d_fk_bpf_profile_tenant",
        """
        ALTER TABLE buyer_profile_fields
        ADD CONSTRAINT dal170d_fk_bpf_profile_tenant
        FOREIGN KEY (brokerage_id, profile_id)
        REFERENCES brokerage_buyer_profiles (brokerage_id, profile_id)
        NOT VALID
        """,
        "ALTER TABLE buyer_profile_fields DROP CONSTRAINT IF EXISTS dal170d_fk_bpf_profile_tenant",
        "buyer_profile_fields",
        ("brokerage_id", "profile_id"),
        "not_valid_fk",
    ),
    DdlStatement(
        "dal170d_fk_offers_conversation_tenant",
        """
        ALTER TABLE offers
        ADD CONSTRAINT dal170d_fk_offers_conversation_tenant
        FOREIGN KEY (brokerage_id, conversation_id)
        REFERENCES conversations (brokerage_id, conversation_id)
        NOT VALID
        """,
        "ALTER TABLE offers DROP CONSTRAINT IF EXISTS dal170d_fk_offers_conversation_tenant",
        "offers",
        ("brokerage_id", "conversation_id"),
        "not_valid_fk",
    ),
    DdlStatement(
        "dal170d_fk_draft_replies_conversation_tenant",
        """
        ALTER TABLE draft_replies
        ADD CONSTRAINT dal170d_fk_draft_replies_conversation_tenant
        FOREIGN KEY (brokerage_id, conversation_id)
        REFERENCES conversations (brokerage_id, conversation_id)
        NOT VALID
        """,
        "ALTER TABLE draft_replies DROP CONSTRAINT IF EXISTS dal170d_fk_draft_replies_conversation_tenant",
        "draft_replies",
        ("brokerage_id", "conversation_id"),
        "not_valid_fk",
    ),
    DdlStatement(
        "dal170d_fk_viewings_conversation_tenant",
        """
        ALTER TABLE viewings
        ADD CONSTRAINT dal170d_fk_viewings_conversation_tenant
        FOREIGN KEY (brokerage_id, conversation_id)
        REFERENCES conversations (brokerage_id, conversation_id)
        NOT VALID
        """,
        "ALTER TABLE viewings DROP CONSTRAINT IF EXISTS dal170d_fk_viewings_conversation_tenant",
        "viewings",
        ("brokerage_id", "conversation_id"),
        "not_valid_fk",
    ),
    DdlStatement(
        "dal170d_fk_media_assets_conversation_tenant",
        """
        ALTER TABLE media_assets
        ADD CONSTRAINT dal170d_fk_media_assets_conversation_tenant
        FOREIGN KEY (brokerage_id, conversation_id)
        REFERENCES conversations (brokerage_id, conversation_id)
        NOT VALID
        """,
        "ALTER TABLE media_assets DROP CONSTRAINT IF EXISTS dal170d_fk_media_assets_conversation_tenant",
        "media_assets",
        ("brokerage_id", "conversation_id"),
        "not_valid_fk",
    ),
)


SECOND_FK_STATEMENTS: tuple[DdlStatement, ...] = (
    DdlStatement(
        "dal170d2_fk_offers_listing_tenant",
        """
        ALTER TABLE offers
        ADD CONSTRAINT dal170d2_fk_offers_listing_tenant
        FOREIGN KEY (brokerage_id, listing_id)
        REFERENCES listings (brokerage_id, listing_id)
        NOT VALID
        """,
        "ALTER TABLE offers DROP CONSTRAINT IF EXISTS dal170d2_fk_offers_listing_tenant",
        "offers",
        ("brokerage_id", "listing_id"),
        "not_valid_fk",
    ),
    DdlStatement(
        "dal170d2_fk_draft_replies_listing_tenant",
        """
        ALTER TABLE draft_replies
        ADD CONSTRAINT dal170d2_fk_draft_replies_listing_tenant
        FOREIGN KEY (brokerage_id, listing_id)
        REFERENCES listings (brokerage_id, listing_id)
        NOT VALID
        """,
        "ALTER TABLE draft_replies DROP CONSTRAINT IF EXISTS dal170d2_fk_draft_replies_listing_tenant",
        "draft_replies",
        ("brokerage_id", "listing_id"),
        "not_valid_fk",
    ),
    DdlStatement(
        "dal170d2_fk_viewings_listing_tenant",
        """
        ALTER TABLE viewings
        ADD CONSTRAINT dal170d2_fk_viewings_listing_tenant
        FOREIGN KEY (brokerage_id, listing_id)
        REFERENCES listings (brokerage_id, listing_id)
        NOT VALID
        """,
        "ALTER TABLE viewings DROP CONSTRAINT IF EXISTS dal170d2_fk_viewings_listing_tenant",
        "viewings",
        ("brokerage_id", "listing_id"),
        "not_valid_fk",
    ),
    DdlStatement(
        "dal170d2_fk_media_assets_listing_tenant",
        """
        ALTER TABLE media_assets
        ADD CONSTRAINT dal170d2_fk_media_assets_listing_tenant
        FOREIGN KEY (brokerage_id, listing_id)
        REFERENCES listings (brokerage_id, listing_id)
        NOT VALID
        """,
        "ALTER TABLE media_assets DROP CONSTRAINT IF EXISTS dal170d2_fk_media_assets_listing_tenant",
        "media_assets",
        ("brokerage_id", "listing_id"),
        "not_valid_fk",
    ),
)


FK_TO_PREFLIGHT_NAME = {
    "dal170d_fk_bpf_profile_tenant": "buyer_profile_fields_to_brokerage_buyer_profiles",
    "dal170d_fk_offers_conversation_tenant": "offers_to_conversations",
    "dal170d_fk_draft_replies_conversation_tenant": "draft_replies_to_conversations",
    "dal170d_fk_viewings_conversation_tenant": "viewings_to_conversations",
    "dal170d_fk_media_assets_conversation_tenant": "media_assets_to_conversations",
    "dal170d2_fk_offers_listing_tenant": "offers_to_listings",
    "dal170d2_fk_draft_replies_listing_tenant": "draft_replies_to_listings",
    "dal170d2_fk_viewings_listing_tenant": "viewings_to_listings",
    "dal170d2_fk_media_assets_listing_tenant": "media_assets_to_listings",
}

FK_PARENT_INDEX_REQUIREMENTS = {
    "dal170d_fk_bpf_profile_tenant": "dal170d_uq_bbp_brokerage_profile",
    "dal170d_fk_offers_conversation_tenant": "dal170d_uq_conversations_brokerage_conversation",
    "dal170d_fk_draft_replies_conversation_tenant": "dal170d_uq_conversations_brokerage_conversation",
    "dal170d_fk_viewings_conversation_tenant": "dal170d_uq_conversations_brokerage_conversation",
    "dal170d_fk_media_assets_conversation_tenant": "dal170d_uq_conversations_brokerage_conversation",
    "dal170d2_fk_offers_listing_tenant": "dal170d_uq_listings_brokerage_listing",
    "dal170d2_fk_draft_replies_listing_tenant": "dal170d_uq_listings_brokerage_listing",
    "dal170d2_fk_viewings_listing_tenant": "dal170d_uq_listings_brokerage_listing",
    "dal170d2_fk_media_assets_listing_tenant": "dal170d_uq_listings_brokerage_listing",
}


def _database_url_parts() -> dict[str, str]:
    parsed = urlparse(os.getenv("DATABASE_URL", ""))
    return {
        "host": parsed.hostname or "",
        "database": parsed.path.lstrip("/").split("?")[0] if parsed.path else "",
    }


def _normalize_host(host: str | None) -> str:
    return (host or "").strip().lower().rstrip(".")


def _configured_prod_hosts() -> set[str]:
    raw = os.getenv("PROD_DB_HOST", "")
    return {_normalize_host(host) for host in raw.split(",") if _normalize_host(host)}


def _mask_host(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) >= 3:
        return f"{parts[0][:2]}***.{'.'.join(parts[-2:])}"
    if len(host) <= 4:
        return "***"
    return f"{host[:2]}***{host[-2:]}"


def _database_url_looks_production_like() -> bool:
    host = _normalize_host(_database_url_parts()["host"])
    if not host:
        return False
    prod_hosts = _configured_prod_hosts()
    if prod_hosts and host in prod_hosts:
        return True
    return any(marker in host for marker in ("prod", "production"))


def get_db_fingerprint(phase: str | None = None) -> dict[str, Any]:
    url_parts = _database_url_parts()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  current_database() AS current_database,
                  current_user AS current_user,
                  inet_server_addr()::text AS inet_server_addr,
                  current_setting('server_version') AS server_version
                """
            )
        ).mappings().one()
    stable_identity = {
        "database_url_host": url_parts["host"],
        "database_url_database": url_parts["database"],
        "current_database": row["current_database"],
        "current_user": row["current_user"],
        "inet_server_addr": row["inet_server_addr"],
        "server_version": row["server_version"],
    }
    fingerprint_hash = hashlib.sha256(
        json.dumps(stable_identity, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return {
        "database_url_host_masked": _mask_host(url_parts["host"]),
        "database_url_database": url_parts["database"],
        "current_database": row["current_database"],
        "current_user": row["current_user"],
        "inet_server_addr": row["inet_server_addr"],
        "server_version": row["server_version"],
        "dalya_env": env_name(),
        "phase": phase,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fingerprint": fingerprint_hash,
    }


def _fingerprint_matches_host_confirmation(confirm_db_host: str | None) -> bool:
    if not confirm_db_host:
        return True
    host = _database_url_parts()["host"].lower()
    return confirm_db_host.lower() in host


def _fingerprint_matches_database_confirmation(confirm_db_name: str | None) -> bool:
    if not confirm_db_name:
        return True
    database = _database_url_parts()["database"].lower()
    return confirm_db_name.lower() == database


def _guard_apply_safety(
    *,
    phase: Phase,
    fingerprint: dict[str, Any],
    artifact_dir: str | None,
    expected_db_fingerprint: str | None,
    confirm_db_host: str | None,
    confirm_db_name: str | None,
    allow_production_like_url_without_production_env: bool,
) -> None:
    def require_apply_evidence(context: str) -> None:
        if not artifact_dir:
            raise RuntimeError(f"{context} requires --artifact-dir so rollback and plan evidence is written before execution.")
        if not expected_db_fingerprint and not (confirm_db_host and confirm_db_name):
            raise RuntimeError(f"{context} requires --expected-db-fingerprint or both --confirm-db-host and --confirm-db-name.")
        if expected_db_fingerprint and expected_db_fingerprint != fingerprint["fingerprint"]:
            raise RuntimeError(f"{context} refused: database fingerprint mismatch.")
        if not _fingerprint_matches_host_confirmation(confirm_db_host):
            raise RuntimeError(f"{context} refused: --confirm-db-host did not match DATABASE_URL host.")
        if not _fingerprint_matches_database_confirmation(confirm_db_name):
            raise RuntimeError(f"{context} refused: --confirm-db-name did not match DATABASE_URL database.")

    if not is_production() and not allow_production_like_url_without_production_env:
        target_host = _normalize_host(_database_url_parts()["host"])
        if not target_host:
            raise RuntimeError("DATABASE_URL host could not be parsed. Refusing non-production DDL apply.")
        prod_hosts = _configured_prod_hosts()
        if not prod_hosts:
            raise RuntimeError(
                "PROD_DB_HOST is not set. Refusing non-production DDL apply because production cannot be denylisted. "
                f"Set {PRODUCTION_DDL_FINGERPRINT_OVERRIDE}=true only for an explicitly approved rehearsal."
            )
        if _database_url_looks_production_like():
            raise RuntimeError(
                "DATABASE_URL looks production-like but DALYA_ENV is not production. "
                f"Set {PRODUCTION_DDL_FINGERPRINT_OVERRIDE}=true only for an explicitly approved rehearsal."
            )
    if not is_production() and allow_production_like_url_without_production_env:
        require_apply_evidence("Production-like rehearsal DDL apply")
    if not is_production():
        return
    if (os.getenv("DALYA_ENV") or "").strip().lower() != "production":
        raise RuntimeError("Production DDL apply requires DALYA_ENV=production explicitly.")
    if not env_bool(PRODUCTION_DDL_GUARD, default=False):
        raise RuntimeError(
            f"Production DDL is blocked by default. Set {PRODUCTION_DDL_GUARD}=true for an explicitly approved production run."
        )
    require_apply_evidence("Production DDL apply")


def _artifact_safe_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "environment": plan["environment"],
        "phase": plan["phase"],
        "blockers": plan["blockers"],
        "statements": plan["statements"],
        "skipped": plan["skipped"],
        "rollback_sql": plan["rollback_sql"],
        "timeouts": plan["timeouts"],
    }


def _write_artifact_bundle(
    *,
    artifact_dir: str,
    plan: dict[str, Any],
    fingerprint: dict[str, Any],
    mode: str,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_dir = Path(artifact_dir) / f"dal170d-{plan['phase']}-{timestamp}"
    bundle_dir.mkdir(parents=True, exist_ok=False)
    preflight_summary = {
        "summary": plan.get("preflight_summary"),
        "blockers": plan["blockers"],
    }
    dry_run_sql = "\n\n".join(statement["sql"].strip() + ";" for statement in plan["statements"])
    rollback_sql = "\n".join(sql.strip() + ";" for sql in plan["rollback_sql"])
    apply_plan = {
        **_artifact_safe_plan(plan),
        "mode": mode,
        "artifact_created_at": datetime.now(timezone.utc).isoformat(),
        "production_guard": {
            "dalya_env": env_name(),
            "is_production": is_production(),
            PRODUCTION_DDL_GUARD: env_bool(PRODUCTION_DDL_GUARD, default=False),
        },
    }
    (bundle_dir / "db_fingerprint.json").write_text(json.dumps(fingerprint, indent=2, sort_keys=True, default=str) + "\n")
    (bundle_dir / "preflight_summary.json").write_text(json.dumps(preflight_summary, indent=2, sort_keys=True, default=str) + "\n")
    (bundle_dir / "dry_run_sql.sql").write_text(dry_run_sql + ("\n" if dry_run_sql else ""))
    (bundle_dir / "rollback_sql.sql").write_text(rollback_sql + ("\n" if rollback_sql else ""))
    (bundle_dir / "apply_plan.json").write_text(json.dumps(apply_plan, indent=2, sort_keys=True, default=str) + "\n")
    return str(bundle_dir)


def _apply_timeouts(conn, *, lock_timeout_ms: int, statement_timeout_ms: int) -> None:
    conn.execute(text(f"SET LOCAL lock_timeout = '{int(lock_timeout_ms)}ms'"))
    conn.execute(text(f"SET LOCAL statement_timeout = '{int(statement_timeout_ms)}ms'"))


def _execute_plan_statements(
    plan: dict[str, Any],
    *,
    lock_timeout_ms: int,
    statement_timeout_ms: int,
) -> list[str]:
    applied: list[str] = []
    with engine.begin() as conn:
        _apply_timeouts(conn, lock_timeout_ms=lock_timeout_ms, statement_timeout_ms=statement_timeout_ms)
        for statement in plan["statements"]:
            conn.execute(text(statement["sql"]))
            applied.append(statement["name"])
    return applied


def _print_pre_execution_sql(plan: dict[str, Any]) -> None:
    print("DAL-170D Production DDL Pre-Execution Plan")
    print("=========================================")
    print(f"Phase: {plan['phase']}")
    print(f"Statements: {len(plan['statements'])}")
    print(f"Lock timeout: {plan['timeouts']['lock_timeout_ms']}ms")
    print(f"Statement timeout: {plan['timeouts']['statement_timeout_ms']}ms")
    print()
    print("SQL")
    print("---")
    for statement in plan["statements"]:
        print(statement["sql"].strip() + ";")
    print()
    print("Rollback SQL")
    print("------------")
    for rollback_sql in plan["rollback_sql"]:
        print(rollback_sql.strip() + ";")


def _existing_schema() -> tuple[set[str], dict[str, set[str]], set[str], set[str]]:
    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        columns = {table: {column["name"] for column in inspector.get_columns(table)} for table in tables}
        constraints = {
            row.name
            for row in conn.execute(
                text(
                    """
                    SELECT conname AS name
                    FROM pg_constraint
                    WHERE connamespace = current_schema()::regnamespace
                    """
                )
            )
        }
        indexes = {
            row.name
            for row in conn.execute(
                text(
                    """
                    SELECT indexname AS name
                    FROM pg_indexes
                    WHERE schemaname = current_schema()
                    """
                )
            )
        }
    return tables, columns, constraints, indexes


def _statement_supported(statement: DdlStatement, tables: set[str], columns: dict[str, set[str]]) -> bool:
    return statement.table in tables and all(column in columns.get(statement.table, set()) for column in statement.required_columns)


def _phase_statements(phase: Phase) -> tuple[DdlStatement, ...]:
    if phase == "parent-keys":
        return PARENT_KEY_STATEMENTS
    if phase == "child-indexes":
        return CHILD_INDEX_STATEMENTS
    if phase == "first-fks":
        return FK_STATEMENTS
    return SECOND_FK_STATEMENTS


def _preflight_blockers_for_phase(phase: Phase, report: dict[str, Any]) -> list[dict[str, Any]]:
    if phase == "parent-keys":
        return [
            row
            for row in report["parents"]
            if row["table"] in {statement.table for statement in PARENT_KEY_STATEMENTS}
            and row.get("duplicate_pairs")
        ]
    if phase == "child-indexes":
        return []
    phase_fk_statements = FK_STATEMENTS if phase == "first-fks" else SECOND_FK_STATEMENTS
    fk_names = {FK_TO_PREFLIGHT_NAME[statement.name] for statement in phase_fk_statements}
    return [
        row
        for row in report["children"]
        if row["name"] in fk_names and row.get("blockers")
    ]


def _constraint_validation_state(names: set[str]) -> dict[str, bool]:
    if not names:
        return {}
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT conname, convalidated
                FROM pg_constraint
                WHERE connamespace = current_schema()::regnamespace
                  AND conname = ANY(:names)
                """
            ),
            {"names": sorted(names)},
        ).mappings().all()
    return {row["conname"]: bool(row["convalidated"]) for row in rows}


def plan_phase(
    phase: Phase,
    *,
    lock_timeout_ms: int = DEFAULT_LOCK_TIMEOUT_MS,
    statement_timeout_ms: int = DEFAULT_STATEMENT_TIMEOUT_MS,
) -> dict[str, Any]:
    report = audit() if phase != "child-indexes" else {"parents": [], "children": [], "blockers": []}
    tables, columns, constraints, indexes = _existing_schema()
    blockers = _preflight_blockers_for_phase(phase, report)
    statements: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for statement in _phase_statements(phase):
        if not _statement_supported(statement, tables, columns):
            skipped.append({**asdict(statement), "reason": "missing_table_or_columns"})
            continue
        if statement.kind == "not_valid_fk" and statement.name in constraints:
            skipped.append({**asdict(statement), "reason": "constraint_already_exists"})
            continue
        if statement.kind == "not_valid_fk":
            required_index = FK_PARENT_INDEX_REQUIREMENTS.get(statement.name)
            if required_index and required_index not in indexes:
                blockers.append(
                    {
                        "type": "missing_parent_identity",
                        "constraint": statement.name,
                        "required_index": required_index,
                    }
                )
                skipped.append({**asdict(statement), "reason": "missing_parent_identity"})
                continue
        statements.append(asdict(statement))
    return {
        "environment": env_name(),
        "phase": phase,
        "blockers": blockers,
        "statements": statements,
        "skipped": skipped,
        "rollback_sql": [row["rollback_sql"] for row in statements]
        + [
            row["rollback_sql"]
            for row in skipped
            if row.get("reason") == "constraint_already_exists"
        ],
        "preflight_summary": report.get("summary"),
        "timeouts": {
            "lock_timeout_ms": lock_timeout_ms,
            "statement_timeout_ms": statement_timeout_ms,
        },
    }


def apply_phase(
    phase: Phase,
    *,
    expected_db_fingerprint: str | None = None,
    confirm_db_host: str | None = None,
    confirm_db_name: str | None = None,
    artifact_dir: str | None = None,
    lock_timeout_ms: int = DEFAULT_LOCK_TIMEOUT_MS,
    statement_timeout_ms: int = DEFAULT_STATEMENT_TIMEOUT_MS,
    allow_production_like_url_without_production_env: bool | None = None,
) -> dict[str, Any]:
    fingerprint = get_db_fingerprint(phase)
    allow_production_like = (
        allow_production_like_url_without_production_env
        if allow_production_like_url_without_production_env is not None
        else env_bool(PRODUCTION_DDL_FINGERPRINT_OVERRIDE, default=False)
    )
    _guard_apply_safety(
        phase=phase,
        fingerprint=fingerprint,
        artifact_dir=artifact_dir,
        expected_db_fingerprint=expected_db_fingerprint,
        confirm_db_host=confirm_db_host,
        confirm_db_name=confirm_db_name,
        allow_production_like_url_without_production_env=allow_production_like,
    )
    plan = plan_phase(
        phase,
        lock_timeout_ms=lock_timeout_ms,
        statement_timeout_ms=statement_timeout_ms,
    )
    if plan["blockers"]:
        raise RuntimeError(f"Preflight blockers prevent applying phase {phase}: {json.dumps(plan['blockers'], default=str)}")
    artifact_path = None
    if artifact_dir:
        artifact_path = _write_artifact_bundle(
            artifact_dir=artifact_dir,
            plan=plan,
            fingerprint=fingerprint,
            mode="apply",
        )
    if is_production():
        _print_pre_execution_sql(plan)
    applied = _execute_plan_statements(
        plan,
        lock_timeout_ms=lock_timeout_ms,
        statement_timeout_ms=statement_timeout_ms,
    )
    validation_state = _constraint_validation_state(set(applied))
    unexpectedly_valid = [
        name
        for name, convalidated in validation_state.items()
        if convalidated
    ]
    if unexpectedly_valid:
        raise RuntimeError(f"NOT VALID FK unexpectedly validated during {phase}: {unexpectedly_valid}")
    return {
        **plan,
        "applied": applied,
        "constraint_validation": validation_state,
        "db_fingerprint": fingerprint,
        "artifact_path": artifact_path,
    }


def _human_print(plan: dict[str, Any], *, applied: bool) -> None:
    print("DAL-170D Tenant Constraint Migration")
    print("====================================")
    print(f"Environment: {plan['environment']}")
    print(f"Phase: {plan['phase']}")
    print(f"Mode: {'apply' if applied else 'dry-run'}")
    print(f"Statements: {len(plan['statements'])}")
    print(f"Skipped: {len(plan['skipped'])}")
    print(f"Blockers: {len(plan['blockers'])}")
    print(f"Lock timeout: {plan['timeouts']['lock_timeout_ms']}ms")
    print(f"Statement timeout: {plan['timeouts']['statement_timeout_ms']}ms")
    if applied:
        print(f"Applied: {len(plan.get('applied', []))}")
    if plan.get("artifact_path"):
        print(f"Artifacts: {plan['artifact_path']}")
    if plan["blockers"]:
        print()
        print("Blockers")
        print("--------")
        for blocker in plan["blockers"]:
            print(json.dumps(blocker, default=str, sort_keys=True))
    print()
    print("SQL")
    print("---")
    for statement in plan["statements"]:
        print(statement["sql"].strip() + ";")
    print()
    print("Rollback SQL")
    print("------------")
    for rollback_sql in plan["rollback_sql"]:
        print(rollback_sql.strip() + ";")
    if plan["skipped"]:
        print()
        print("Skipped")
        print("-------")
        for skipped in plan["skipped"]:
            print(f"{skipped['name']}: {skipped['reason']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="DAL-170D additive tenant constraint migration.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Print planned DDL without applying.")
    mode.add_argument("--apply", action="store_true", help="Apply the selected additive DDL phase.")
    mode.add_argument("--print-db-fingerprint", action="store_true", help="Print non-secret database identity and stable fingerprint.")
    parser.add_argument("--phase", choices=("parent-keys", "child-indexes", "first-fks", "second-fks"))
    parser.add_argument("--expected-db-fingerprint", help="Expected DB fingerprint hash required for production apply.")
    parser.add_argument("--confirm-db-host", help="Production confirmation host fragment alternative to fingerprint hash.")
    parser.add_argument("--confirm-db-name", help="Production confirmation database name alternative to fingerprint hash.")
    parser.add_argument("--artifact-dir", help="Directory where apply evidence artifacts should be written before DDL.")
    parser.add_argument("--lock-timeout-ms", type=int, default=DEFAULT_LOCK_TIMEOUT_MS)
    parser.add_argument("--statement-timeout-ms", type=int, default=DEFAULT_STATEMENT_TIMEOUT_MS)
    parser.add_argument(
        "--allow-production-like-url-without-production-env",
        action="store_true",
        help="Allow an apply against a production-like DATABASE_URL when DALYA_ENV is not production. Use only for approved rehearsals.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    if args.print_db_fingerprint:
        result = get_db_fingerprint(args.phase)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
        else:
            print("DAL-170D DB Fingerprint")
            print("=======================")
            print(f"DALYA_ENV: {result['dalya_env']}")
            print(f"Phase: {result['phase']}")
            print(f"Database URL host: {result['database_url_host_masked']}")
            print(f"Database URL database: {result['database_url_database']}")
            print(f"current_database(): {result['current_database']}")
            print(f"current_user: {result['current_user']}")
            print(f"inet_server_addr(): {result['inet_server_addr']}")
            print(f"server_version: {result['server_version']}")
            print(f"timestamp: {result['timestamp']}")
            print(f"fingerprint: {result['fingerprint']}")
        return 0

    if not args.phase:
        parser.error("--phase is required with --dry-run or --apply")

    if args.apply:
        result = apply_phase(
            args.phase,
            expected_db_fingerprint=args.expected_db_fingerprint,
            confirm_db_host=args.confirm_db_host,
            confirm_db_name=args.confirm_db_name,
            artifact_dir=args.artifact_dir,
            lock_timeout_ms=args.lock_timeout_ms,
            statement_timeout_ms=args.statement_timeout_ms,
            allow_production_like_url_without_production_env=args.allow_production_like_url_without_production_env,
        )
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
        else:
            _human_print(result, applied=True)
        return 0

    result = plan_phase(
        args.phase,
        lock_timeout_ms=args.lock_timeout_ms,
        statement_timeout_ms=args.statement_timeout_ms,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
    else:
        _human_print(result, applied=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
