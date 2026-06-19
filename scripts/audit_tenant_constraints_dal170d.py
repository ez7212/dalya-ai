from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from app.db.session import engine


@dataclass(frozen=True)
class ParentCandidate:
    table: str
    tenant_column: str
    id_column: str
    nullable_tenant_allowed: bool = False
    rls_candidate: bool = True


@dataclass(frozen=True)
class ChildFkCandidate:
    name: str
    child_table: str
    child_tenant_column: str
    child_ref_column: str
    parent_table: str
    parent_tenant_column: str
    parent_ref_column: str
    nullable_ref_allowed: bool = False
    category: str = "first_fks"
    required_parent_identity: str | None = None


PARENT_CANDIDATES: tuple[ParentCandidate, ...] = (
    ParentCandidate("brokerage_buyer_profiles", "brokerage_id", "profile_id"),
    ParentCandidate("conversations", "brokerage_id", "conversation_id", nullable_tenant_allowed=True),
    ParentCandidate("listings", "brokerage_id", "listing_id", nullable_tenant_allowed=True),
    ParentCandidate("viewings", "brokerage_id", "viewing_id"),
    ParentCandidate("media_assets", "brokerage_id", "media_asset_id"),
    ParentCandidate("escalation_threads", "brokerage_id", "thread_id"),
    ParentCandidate("listing_documents", "brokerage_id", "document_id"),
    ParentCandidate("offers", "brokerage_id", "offer_id"),
    ParentCandidate("draft_replies", "brokerage_id", "draft_id"),
)


FIRST_FK_CANDIDATES: tuple[ChildFkCandidate, ...] = (
    ChildFkCandidate(
        "buyer_profile_fields_to_brokerage_buyer_profiles",
        "buyer_profile_fields",
        "brokerage_id",
        "profile_id",
        "brokerage_buyer_profiles",
        "brokerage_id",
        "profile_id",
    ),
    ChildFkCandidate(
        "offers_to_conversations",
        "offers",
        "brokerage_id",
        "conversation_id",
        "conversations",
        "brokerage_id",
        "conversation_id",
    ),
    ChildFkCandidate(
        "offers_to_listings",
        "offers",
        "brokerage_id",
        "listing_id",
        "listings",
        "brokerage_id",
        "listing_id",
        category="second_fks",
        required_parent_identity="dal170d_uq_listings_brokerage_listing",
    ),
    ChildFkCandidate(
        "offers_to_brokerage_buyer_profiles",
        "offers",
        "brokerage_id",
        "buyer_profile_id",
        "brokerage_buyer_profiles",
        "brokerage_id",
        "profile_id",
        nullable_ref_allowed=True,
        category="later_clean_fk",
    ),
    ChildFkCandidate(
        "draft_replies_to_conversations",
        "draft_replies",
        "brokerage_id",
        "conversation_id",
        "conversations",
        "brokerage_id",
        "conversation_id",
    ),
    ChildFkCandidate(
        "draft_replies_to_listings",
        "draft_replies",
        "brokerage_id",
        "listing_id",
        "listings",
        "brokerage_id",
        "listing_id",
        nullable_ref_allowed=True,
        category="second_fks",
        required_parent_identity="dal170d_uq_listings_brokerage_listing",
    ),
    ChildFkCandidate(
        "viewings_to_conversations",
        "viewings",
        "brokerage_id",
        "conversation_id",
        "conversations",
        "brokerage_id",
        "conversation_id",
    ),
    ChildFkCandidate(
        "viewings_to_listings",
        "viewings",
        "brokerage_id",
        "listing_id",
        "listings",
        "brokerage_id",
        "listing_id",
        category="second_fks",
        required_parent_identity="dal170d_uq_listings_brokerage_listing",
    ),
    ChildFkCandidate(
        "media_assets_to_conversations",
        "media_assets",
        "brokerage_id",
        "conversation_id",
        "conversations",
        "brokerage_id",
        "conversation_id",
        nullable_ref_allowed=True,
    ),
    ChildFkCandidate(
        "media_assets_to_listings",
        "media_assets",
        "brokerage_id",
        "listing_id",
        "listings",
        "brokerage_id",
        "listing_id",
        nullable_ref_allowed=True,
        category="second_fks",
        required_parent_identity="dal170d_uq_listings_brokerage_listing",
    ),
    ChildFkCandidate(
        "lead_assignments_to_conversations",
        "lead_assignments",
        "brokerage_id",
        "conversation_id",
        "conversations",
        "brokerage_id",
        "conversation_id",
        category="later_clean_fk",
    ),
    ChildFkCandidate(
        "lead_assignments_to_listings",
        "lead_assignments",
        "brokerage_id",
        "listing_id",
        "listings",
        "brokerage_id",
        "listing_id",
        category="later_clean_fk",
    ),
    ChildFkCandidate(
        "lead_tasks_to_conversations",
        "lead_tasks",
        "brokerage_id",
        "conversation_id",
        "conversations",
        "brokerage_id",
        "conversation_id",
        category="later_clean_fk",
    ),
    ChildFkCandidate(
        "lead_tasks_to_listings",
        "lead_tasks",
        "brokerage_id",
        "listing_id",
        "listings",
        "brokerage_id",
        "listing_id",
        nullable_ref_allowed=True,
        category="later_clean_fk",
    ),
    ChildFkCandidate(
        "lead_actions_to_conversations",
        "lead_actions",
        "brokerage_id",
        "conversation_id",
        "conversations",
        "brokerage_id",
        "conversation_id",
        category="later_clean_fk",
    ),
    ChildFkCandidate(
        "lead_actions_to_listings",
        "lead_actions",
        "brokerage_id",
        "listing_id",
        "listings",
        "brokerage_id",
        "listing_id",
        nullable_ref_allowed=True,
        category="later_clean_fk",
    ),
    ChildFkCandidate(
        "agent_message_routes_to_escalation_threads",
        "agent_message_routes",
        "brokerage_id",
        "thread_id",
        "escalation_threads",
        "brokerage_id",
        "thread_id",
        nullable_ref_allowed=True,
        category="later_clean_fk",
    ),
    ChildFkCandidate(
        "agent_message_routes_to_conversations",
        "agent_message_routes",
        "brokerage_id",
        "conversation_id",
        "conversations",
        "brokerage_id",
        "conversation_id",
        category="later_clean_fk",
    ),
    ChildFkCandidate(
        "agent_message_routes_to_listings",
        "agent_message_routes",
        "brokerage_id",
        "listing_id",
        "listings",
        "brokerage_id",
        "listing_id",
        category="later_clean_fk",
    ),
)


EXPLICIT_DEFERRED = (
    {
        "table": "listing_inquiries",
        "classification": "requires_dal170c_apply",
        "reason": "Backfill apply must be proven on a fresh dedicated Neon branch before tenant FKs.",
    },
    {
        "table": "offer_records",
        "classification": "requires_dal170c_apply",
        "reason": "Backfill apply must be proven on a fresh dedicated Neon branch before tenant FKs.",
    },
    {
        "table": "suspicious_activity",
        "classification": "deferred_compliance",
        "reason": "Compliance/audit ownership decision required before tenant backfill or constraints.",
    },
    {
        "table": "messages",
        "classification": "requires_new_column",
        "reason": "Tenant is derived through conversations; no direct brokerage_id exists.",
    },
    {
        "table": "message_queue",
        "classification": "requires_new_column",
        "reason": "Tenant is derived during processing; no direct brokerage_id exists.",
    },
    {
        "table": "telegram_reply_routes",
        "classification": "requires_new_column",
        "reason": "Legacy route table has no direct brokerage_id or database FKs.",
    },
    {
        "table": "listing_amenities",
        "classification": "requires_new_column",
        "reason": "Tenant is derived through listings; no direct brokerage_id exists.",
    },
    {
        "table": "listing_anchor_times",
        "classification": "requires_new_column",
        "reason": "Tenant is derived through listings; no direct brokerage_id exists.",
    },
    {
        "table": "enrichment_runs",
        "classification": "requires_new_column",
        "reason": "Tenant is derived through listings; no direct brokerage_id exists.",
    },
    {
        "table": "escalation_thread_questions",
        "classification": "requires_new_column",
        "reason": "Tenant is derived through escalation_threads; no direct brokerage_id exists.",
    },
)


def _has_table(tables: set[str], table: str) -> bool:
    return table in tables


def _has_columns(columns: dict[str, set[str]], table: str, required: tuple[str, ...]) -> bool:
    return table in columns and all(column in columns[table] for column in required)


def _scalar(conn: Connection, sql: str, params: dict[str, Any] | None = None) -> int:
    value = conn.execute(text(sql), params or {}).scalar()
    return int(value or 0)


def _samples(conn: Connection, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(row._mapping) for row in conn.execute(text(sql), params or {}).fetchmany(5)]


def _parent_readiness(conn: Connection, tables: set[str], columns: dict[str, set[str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for candidate in PARENT_CANDIDATES:
        required = (candidate.tenant_column, candidate.id_column)
        if not _has_table(tables, candidate.table):
            results.append(
                {
                    **asdict(candidate),
                    "exists": False,
                    "duplicate_pairs": None,
                    "null_brokerage_rows": None,
                    "supports_non_partial_unique_fk_target": False,
                    "classification": "missing_table",
                    "blockers": ["missing_table"],
                }
            )
            continue
        if not _has_columns(columns, candidate.table, required):
            results.append(
                {
                    **asdict(candidate),
                    "exists": True,
                    "duplicate_pairs": None,
                    "null_brokerage_rows": None,
                    "supports_non_partial_unique_fk_target": False,
                    "classification": "requires_new_column",
                    "blockers": ["missing_column"],
                }
            )
            continue

        duplicate_pairs = _scalar(
            conn,
            f"""
            SELECT count(*) FROM (
                SELECT {candidate.tenant_column}, {candidate.id_column}, count(*) AS n
                FROM {candidate.table}
                GROUP BY {candidate.tenant_column}, {candidate.id_column}
                HAVING count(*) > 1
            ) dupes
            """,
        )
        null_brokerage_rows = _scalar(
            conn,
            f"SELECT count(*) FROM {candidate.table} WHERE {candidate.tenant_column} IS NULL",
        )
        blockers: list[str] = []
        if duplicate_pairs:
            blockers.append("duplicate_composite_identity")
        if null_brokerage_rows and not candidate.nullable_tenant_allowed:
            blockers.append("null_tenant_key")

        classification = "safe_now" if not blockers else "blocked_by_null_roots"
        if duplicate_pairs:
            classification = "blocked_by_mixed_tenant_rows"

        results.append(
            {
                **asdict(candidate),
                "exists": True,
                "duplicate_pairs": duplicate_pairs,
                "null_brokerage_rows": null_brokerage_rows,
                "supports_non_partial_unique_fk_target": duplicate_pairs == 0,
                "classification": classification,
                "blockers": blockers,
                "note": (
                    "Composite identity can support an FK target, but nullable brokerage_id still leaves null-root risk."
                    if null_brokerage_rows
                    else ""
                ),
            }
        )
    return results


def _child_readiness(
    conn: Connection,
    tables: set[str],
    columns: dict[str, set[str]],
    indexes: set[str],
    candidates: tuple[ChildFkCandidate, ...] = FIRST_FK_CANDIDATES,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for candidate in candidates:
        child_required = (candidate.child_tenant_column, candidate.child_ref_column)
        parent_required = (candidate.parent_tenant_column, candidate.parent_ref_column)
        base = asdict(candidate)
        if not _has_table(tables, candidate.child_table) or not _has_table(tables, candidate.parent_table):
            results.append(
                {
                    **base,
                    "exists": False,
                    "checked_rows": None,
                    "missing_parent_rows": None,
                    "mixed_tenant_rows": None,
                    "null_child_tenant_rows": None,
                    "null_parent_tenant_rows": None,
                    "nullable_ref_skipped_rows": None,
                    "missing_parent_identity": bool(candidate.required_parent_identity),
                    "classification": "missing_table",
                    "blockers": ["missing_table"],
                    "samples": [],
                }
            )
            continue
        if not _has_columns(columns, candidate.child_table, child_required) or not _has_columns(columns, candidate.parent_table, parent_required):
            results.append(
                {
                    **base,
                    "exists": True,
                    "checked_rows": None,
                    "missing_parent_rows": None,
                    "mixed_tenant_rows": None,
                    "null_child_tenant_rows": None,
                    "null_parent_tenant_rows": None,
                    "nullable_ref_skipped_rows": None,
                    "missing_parent_identity": bool(candidate.required_parent_identity),
                    "classification": "requires_new_column",
                    "blockers": ["missing_column"],
                    "samples": [],
                }
            )
            continue

        ref_filter = f"c.{candidate.child_ref_column} IS NOT NULL"
        checked_filter = (
            f"{ref_filter} "
            f"AND c.{candidate.child_tenant_column} IS NOT NULL"
        )
        checked_rows = _scalar(conn, f"SELECT count(*) FROM {candidate.child_table} c WHERE {ref_filter}")
        null_child_tenant_rows = _scalar(
            conn,
            f"""
            SELECT count(*) FROM {candidate.child_table} c
            WHERE {ref_filter}
              AND c.{candidate.child_tenant_column} IS NULL
            """,
        )
        nullable_ref_skipped_rows = _scalar(
            conn,
            f"""
            SELECT count(*) FROM {candidate.child_table} c
            WHERE c.{candidate.child_ref_column} IS NULL
            """,
        )
        missing_parent_rows = _scalar(
            conn,
            f"""
            SELECT count(*)
            FROM {candidate.child_table} c
            LEFT JOIN {candidate.parent_table} p
              ON p.{candidate.parent_ref_column} = c.{candidate.child_ref_column}
            WHERE {checked_filter}
              AND p.{candidate.parent_ref_column} IS NULL
            """,
        )
        null_parent_tenant_rows = _scalar(
            conn,
            f"""
            SELECT count(*)
            FROM {candidate.child_table} c
            JOIN {candidate.parent_table} p
              ON p.{candidate.parent_ref_column} = c.{candidate.child_ref_column}
            WHERE {checked_filter}
              AND p.{candidate.parent_tenant_column} IS NULL
            """,
        )
        mixed_tenant_rows = _scalar(
            conn,
            f"""
            SELECT count(*)
            FROM {candidate.child_table} c
            JOIN {candidate.parent_table} p
              ON p.{candidate.parent_ref_column} = c.{candidate.child_ref_column}
            WHERE {checked_filter}
              AND p.{candidate.parent_tenant_column} IS NOT NULL
              AND c.{candidate.child_tenant_column} IS DISTINCT FROM p.{candidate.parent_tenant_column}
            """,
        )
        samples = _samples(
            conn,
            f"""
            SELECT
              md5(c.{candidate.child_ref_column}::text) AS child_ref_hash,
              md5(coalesce(c.{candidate.child_tenant_column}::text, 'NULL')) AS child_brokerage_hash,
              md5(coalesce(p.{candidate.parent_tenant_column}::text, 'NULL')) AS parent_brokerage_hash,
              md5(coalesce(p.{candidate.parent_ref_column}::text, 'NULL')) AS parent_ref_hash
            FROM {candidate.child_table} c
            LEFT JOIN {candidate.parent_table} p
              ON p.{candidate.parent_ref_column} = c.{candidate.child_ref_column}
            WHERE {ref_filter}
              AND (
                c.{candidate.child_tenant_column} IS NULL
                OR
                p.{candidate.parent_ref_column} IS NULL
                OR p.{candidate.parent_tenant_column} IS NULL
                OR c.{candidate.child_tenant_column} IS DISTINCT FROM p.{candidate.parent_tenant_column}
              )
            LIMIT 5
            """,
        )

        blockers = []
        missing_parent_identity = bool(candidate.required_parent_identity and candidate.required_parent_identity not in indexes)
        if missing_parent_identity:
            blockers.append("missing_parent_identity")
        if missing_parent_rows:
            blockers.append("missing_parent")
        if null_child_tenant_rows:
            blockers.append("null_child_tenant")
        if null_parent_tenant_rows:
            blockers.append("null_parent_tenant")
        if mixed_tenant_rows:
            blockers.append("mixed_tenant_rows")

        if candidate.child_table in {"listing_inquiries", "offer_records"}:
            classification = "requires_dal170c_apply"
        elif candidate.child_table == "suspicious_activity":
            classification = "deferred_compliance"
        elif missing_parent_identity:
            classification = "missing_parent_identity"
        elif missing_parent_rows:
            classification = "missing_parent"
        elif null_child_tenant_rows:
            classification = "blocked_by_null_child_tenant"
        elif null_parent_tenant_rows:
            classification = "blocked_by_null_parent_tenant"
        elif mixed_tenant_rows:
            classification = "blocked_by_mixed_tenant_rows"
        else:
            classification = "safe_now"

        results.append(
            {
                **base,
                "exists": True,
                "checked_rows": checked_rows,
                "missing_parent_rows": missing_parent_rows,
                "mixed_tenant_rows": mixed_tenant_rows,
                "null_child_tenant_rows": null_child_tenant_rows,
                "null_parent_tenant_rows": null_parent_tenant_rows,
                "nullable_ref_skipped_rows": nullable_ref_skipped_rows,
                "missing_parent_identity": missing_parent_identity,
                "classification": classification,
                "blockers": blockers,
                "samples": samples,
            }
        )
    return results


def _rls_readiness(tables: set[str], columns: dict[str, set[str]], parent_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parent_by_table = {row["table"]: row for row in parent_results}
    target_tables = sorted(
        {
            "brokerage_buyer_profiles",
            "buyer_profile_fields",
            "conversations",
            "listings",
            "offers",
            "draft_replies",
            "viewings",
            "media_assets",
            "lead_assignments",
            "lead_tasks",
            "lead_actions",
            "agent_message_routes",
            "escalation_threads",
            "listing_inquiries",
            "offer_records",
            "suspicious_activity",
            "messages",
            "message_queue",
            "telegram_reply_routes",
            "listing_amenities",
            "listing_anchor_times",
            "enrichment_runs",
            "escalation_thread_questions",
            "inbound_provider_events",
        }
    )
    results: list[dict[str, Any]] = []
    for table in target_tables:
        exists = table in tables
        direct_tenant_key = exists and "brokerage_id" in columns.get(table, set())
        tenant_key_nullable = None
        if direct_tenant_key:
            tenant_key_nullable = parent_by_table.get(table, {}).get("null_brokerage_rows")
        derived_only = exists and not direct_tenant_key
        deferred = next((item for item in EXPLICIT_DEFERRED if item["table"] == table), None)
        ready = bool(direct_tenant_key and not tenant_key_nullable and not deferred)
        results.append(
            {
                "table": table,
                "exists": exists,
                "direct_tenant_key": direct_tenant_key,
                "tenant_key_nullable": tenant_key_nullable,
                "derived_only": derived_only,
                "parent_relationships_structurally_enforceable": direct_tenant_key and table not in {"listing_inquiries", "offer_records", "suspicious_activity", "inbound_provider_events"},
                "ready_for_rls_candidate": ready,
                "deferred_reason": deferred["reason"] if deferred else "",
            }
        )
    return results


def audit() -> dict[str, Any]:
    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        columns = {table: {column["name"] for column in inspector.get_columns(table)} for table in tables}
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
        parent_results = _parent_readiness(conn, tables, columns)
        child_results = _child_readiness(conn, tables, columns, indexes)
        blockers = [
            {"type": "parent", **row}
            for row in parent_results
            if row.get("blockers")
        ] + [
            {"type": "child", **row}
            for row in child_results
            if row.get("category") in {"first_fks", "second_fks"} and row.get("blockers")
        ]
        return {
            "summary": {
                "parent_candidates": len(parent_results),
                "child_candidates": len(child_results),
                "blocker_count": len(blockers),
                "safe_first_fk_count": sum(
                    1
                    for row in child_results
                    if row.get("category") == "first_fks" and row.get("classification") == "safe_now"
                ),
                "safe_second_fk_count": sum(
                    1
                    for row in child_results
                    if row.get("category") == "second_fks" and row.get("classification") == "safe_now"
                ),
            },
            "parents": parent_results,
            "children": child_results,
            "deferred": list(EXPLICIT_DEFERRED),
            "rls_readiness": _rls_readiness(tables, columns, parent_results),
            "blockers": blockers,
        }


def audit_child_candidate(name: str) -> dict[str, Any]:
    candidate = next((row for row in FIRST_FK_CANDIDATES if row.name == name), None)
    if candidate is None:
        raise ValueError(f"Unknown child FK candidate: {name}")
    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        columns = {table: {column["name"] for column in inspector.get_columns(table)} for table in tables}
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
        return _child_readiness(conn, tables, columns, indexes, (candidate,))[0]


def _human_print(report: dict[str, Any]) -> None:
    print("DAL-170D Tenant Constraint Preflight")
    print("====================================")
    print(f"Parent candidates: {report['summary']['parent_candidates']}")
    print(f"Child candidates: {report['summary']['child_candidates']}")
    print(f"First-FK safe now: {report['summary']['safe_first_fk_count']}")
    print(f"Second-FK safe now: {report['summary']['safe_second_fk_count']}")
    print(f"Blockers: {report['summary']['blocker_count']}")
    print()
    print("Parent composite identity readiness")
    print("-----------------------------------")
    for row in report["parents"]:
        print(
            f"{row['table']}({row['tenant_column']}, {row['id_column']}): "
            f"{row['classification']} duplicates={row['duplicate_pairs']} null_brokerage={row['null_brokerage_rows']}"
        )
        if row.get("note"):
            print(f"  note: {row['note']}")
    print()
    print("Child composite FK readiness")
    print("----------------------------")
    for row in report["children"]:
        print(
            f"{row['name']}: {row['classification']} "
            f"missing_parent={row['missing_parent_rows']} mixed={row['mixed_tenant_rows']} "
            f"null_child={row['null_child_tenant_rows']} null_parent={row['null_parent_tenant_rows']} "
            f"missing_identity={row['missing_parent_identity']} skipped_null_ref={row['nullable_ref_skipped_rows']}"
        )
    print()
    print("Explicit deferrals")
    print("------------------")
    for row in report["deferred"]:
        print(f"{row['table']}: {row['classification']} - {row['reason']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only DAL-170D tenant constraint preflight.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--fail-on-blockers", action="store_true", help="Exit non-zero if first-pass blockers exist.")
    args = parser.parse_args()

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        _human_print(report)
    if args.fail_on_blockers and report["summary"]["blocker_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
