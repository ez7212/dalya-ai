from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import inspect, text

from app.db.session import engine
from scripts.migrate_tenant_root_normalization import dry_run_report


SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}


@dataclass
class Finding:
    severity: str
    check: str
    table: str
    summary: str
    count: int | None = None
    sample: list[dict[str, Any]] | None = None


TENANT_OWNED_TABLES = {
    "agent_availability_blocks",
    "agent_calendar_connections",
    "agent_chatbot_configs",
    "agent_community_remarks",
    "agent_message_routes",
    "agent_notifications",
    "agent_profiles",
    "agent_relay_sessions",
    "agent_verifications",
    "agent_voice_reply_holds",
    "ai_drafts",
    "brokerage_buyer_profiles",
    "brokerage_members",
    "buyer_listing_matches",
    "buyer_preference_profiles",
    "buyer_profile_fields",
    "buyer_suppressions",
    "campaign_recipients",
    "campaign_uploads",
    "campaigns",
    "compliance_events",
    "conversations",
    "draft_replies",
    "escalation_threads",
    "inbound_provider_events",
    "lead_actions",
    "lead_assignments",
    "lead_ingests",
    "lead_tasks",
    "listing_documents",
    "listing_facts",
    "listing_inquiries",
    "listing_knowledge_summaries",
    "listing_logistics",
    "listings",
    "marketing_events",
    "marketing_pages",
    "media_assets",
    "offers",
    "offer_records",
    "outreach_drafts",
    "owner_leads",
    "relay_outbox",
    "suspicious_activity",
    "tenant_consents",
    "tenant_viewing_confirmations",
    "viewing_feedback",
    "viewings",
}

NULL_ALLOWED_WITH_REVIEW = {"inbound_provider_events"}

DERIVED_TENANT_TABLES = {
    "messages": "conversation_id -> conversations.brokerage_id",
    "message_queue": "to_number/listing_id/provider context",
    "telegram_reply_routes": "conversation_id/listing_id",
    "listing_amenities": "listing_id -> listings.brokerage_id",
    "listing_anchor_times": "listing_id -> listings.brokerage_id",
    "enrichment_runs": "listing_id -> listings.brokerage_id",
    "escalation_thread_questions": "thread_id -> escalation_threads.brokerage_id",
}

MISMATCH_CHECKS = [
    (
        "offers",
        "conversation brokerage mismatch",
        """
        SELECT o.offer_id AS id, o.brokerage_id AS child_brokerage_id, c.brokerage_id AS parent_brokerage_id
        FROM offers o
        JOIN conversations c ON c.conversation_id = o.conversation_id
        WHERE o.brokerage_id IS DISTINCT FROM c.brokerage_id
        LIMIT 20
        """,
    ),
    (
        "offers",
        "listing brokerage mismatch",
        """
        SELECT o.offer_id AS id, o.brokerage_id AS child_brokerage_id, l.brokerage_id AS parent_brokerage_id
        FROM offers o
        JOIN listings l ON l.listing_id = o.listing_id
        WHERE o.brokerage_id IS DISTINCT FROM l.brokerage_id
        LIMIT 20
        """,
    ),
    (
        "draft_replies",
        "conversation brokerage mismatch",
        """
        SELECT d.draft_id AS id, d.brokerage_id AS child_brokerage_id, c.brokerage_id AS parent_brokerage_id
        FROM draft_replies d
        JOIN conversations c ON c.conversation_id = d.conversation_id
        WHERE d.brokerage_id IS DISTINCT FROM c.brokerage_id
        LIMIT 20
        """,
    ),
    (
        "viewings",
        "conversation brokerage mismatch",
        """
        SELECT v.viewing_id AS id, v.brokerage_id AS child_brokerage_id, c.brokerage_id AS parent_brokerage_id
        FROM viewings v
        JOIN conversations c ON c.conversation_id = v.conversation_id
        WHERE v.brokerage_id IS DISTINCT FROM c.brokerage_id
        LIMIT 20
        """,
    ),
    (
        "media_assets",
        "conversation brokerage mismatch",
        """
        SELECT m.media_asset_id AS id, m.brokerage_id AS child_brokerage_id, c.brokerage_id AS parent_brokerage_id
        FROM media_assets m
        JOIN conversations c ON c.conversation_id = m.conversation_id
        WHERE m.brokerage_id IS DISTINCT FROM c.brokerage_id
        LIMIT 20
        """,
    ),
    (
        "lead_assignments",
        "conversation brokerage mismatch",
        """
        SELECT a.assignment_id AS id, a.brokerage_id AS child_brokerage_id, c.brokerage_id AS parent_brokerage_id
        FROM lead_assignments a
        JOIN conversations c ON c.conversation_id = a.conversation_id
        WHERE a.brokerage_id IS DISTINCT FROM c.brokerage_id
        LIMIT 20
        """,
    ),
    (
        "buyer_profile_fields",
        "profile brokerage mismatch",
        """
        SELECT f.field_id AS id, f.brokerage_id AS child_brokerage_id, p.brokerage_id AS parent_brokerage_id
        FROM buyer_profile_fields f
        JOIN brokerage_buyer_profiles p ON p.profile_id = f.profile_id
        WHERE f.brokerage_id IS DISTINCT FROM p.brokerage_id
        LIMIT 20
        """,
    ),
]


def _has_table(tables: set[str], table: str) -> bool:
    return table in tables


def _has_column(columns: dict[str, set[str]], table: str, column: str) -> bool:
    return column in columns.get(table, set())


def _rows(conn, sql: str) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(text(sql)).mappings().all()]


def _scalar(conn, sql: str) -> int:
    value = conn.execute(text(sql)).scalar()
    return int(value or 0)


def _table_count(conn, table: str) -> int:
    return _scalar(conn, f"SELECT count(*) FROM {table}")


def _add_schema_findings(findings: list[Finding], tables: set[str], columns: dict[str, set[str]], nullable: dict[tuple[str, str], bool]) -> None:
    for table in sorted(TENANT_OWNED_TABLES):
        if not _has_table(tables, table):
            findings.append(Finding("INFO", "missing_table", table, "Table not present in this database."))
            continue
        if not _has_column(columns, table, "brokerage_id"):
            findings.append(
                Finding("CRITICAL", "missing_brokerage_id", table, "Tenant-owned table has no direct brokerage_id column.")
            )
            continue
        if nullable.get((table, "brokerage_id"), False):
            severity = "MEDIUM" if table in NULL_ALLOWED_WITH_REVIEW else "CRITICAL"
            findings.append(
                Finding(severity, "nullable_brokerage_id", table, "Tenant-owned table has nullable brokerage_id.")
            )

    for table, derivation in sorted(DERIVED_TENANT_TABLES.items()):
        if _has_table(tables, table) and not _has_column(columns, table, "brokerage_id"):
            findings.append(
                Finding(
                    "HIGH",
                    "derived_tenant_only",
                    table,
                    f"Table has tenant-bearing data but no direct brokerage_id; current tenant is derived via {derivation}.",
                )
            )


def _add_null_row_findings(conn, findings: list[Finding], tables: set[str], columns: dict[str, set[str]]) -> None:
    safe_samples = {
        "listings": "SELECT listing_id, brokerage_id, assigned_agent_id, seller_id FROM listings WHERE brokerage_id IS NULL LIMIT 5",
        "conversations": "SELECT conversation_id, brokerage_id, listing_id, assigned_agent_id, right(buyer_phone, 4) AS buyer_phone_tail FROM conversations WHERE brokerage_id IS NULL LIMIT 5",
        "listing_inquiries": "SELECT id, brokerage_id, listing_id, right(buyer_phone, 4) AS buyer_phone_tail FROM listing_inquiries WHERE brokerage_id IS NULL LIMIT 5",
        "offer_records": "SELECT offer_id, brokerage_id, listing_id, conversation_id, right(buyer_phone, 4) AS buyer_phone_tail FROM offer_records WHERE brokerage_id IS NULL LIMIT 5",
        "suspicious_activity": "SELECT activity_id, brokerage_id, listing_id, conversation_id, right(buyer_phone, 4) AS buyer_phone_tail, category FROM suspicious_activity WHERE brokerage_id IS NULL LIMIT 5",
        "buyer_profiles": "SELECT right(phone, 4) AS phone_tail, brokerage_id, lead_source FROM buyer_profiles WHERE brokerage_id IS NULL LIMIT 5",
    }
    for table in sorted(TENANT_OWNED_TABLES):
        if not _has_table(tables, table) or not _has_column(columns, table, "brokerage_id"):
            continue
        null_count = _scalar(conn, f"SELECT count(*) FROM {table} WHERE brokerage_id IS NULL")
        if null_count:
            severity = "MEDIUM" if table in NULL_ALLOWED_WITH_REVIEW else "CRITICAL"
            sample = _rows(conn, safe_samples.get(table, f"SELECT brokerage_id FROM {table} WHERE brokerage_id IS NULL LIMIT 5"))
            findings.append(
                Finding(severity, "null_brokerage_rows", table, "Rows have NULL brokerage_id.", null_count, sample)
            )


def _add_mismatch_findings(conn, findings: list[Finding], tables: set[str]) -> None:
    for table, label, sql in MISMATCH_CHECKS:
        if not _has_table(tables, table):
            continue
        rows = _rows(conn, sql)
        if rows:
            findings.append(
                Finding(
                    "CRITICAL",
                    "child_parent_brokerage_mismatch",
                    table,
                    label,
                    len(rows),
                    rows,
                )
            )


def _add_legacy_buyer_findings(conn, findings: list[Finding], tables: set[str], columns: dict[str, set[str]]) -> None:
    if _has_table(tables, "buyer_profiles"):
        findings.append(
            Finding(
                "HIGH",
                "global_buyer_profile_key",
                "buyer_profiles",
                "Legacy buyer_profiles are keyed globally by phone, which is unsafe as a tenant boundary.",
                _table_count(conn, "buyer_profiles"),
            )
        )
        if _has_column(columns, "buyer_profiles", "brokerage_id"):
            null_count = _scalar(conn, "SELECT count(*) FROM buyer_profiles WHERE brokerage_id IS NULL")
            if null_count:
                findings.append(
                    Finding(
                        "CRITICAL",
                        "legacy_buyer_profile_null_tenant",
                        "buyer_profiles",
                        "Legacy buyer profiles have NULL brokerage_id.",
                        null_count,
                    )
                )

    if _has_table(tables, "brokerage_buyer_profiles"):
        rows = _rows(
            conn,
            """
            SELECT right(buyer_phone, 4) AS buyer_phone_tail, count(DISTINCT brokerage_id) AS brokerage_count
            FROM brokerage_buyer_profiles
            GROUP BY buyer_phone
            HAVING count(DISTINCT brokerage_id) > 1
            LIMIT 20
            """,
        )
        if rows:
            findings.append(
                Finding(
                    "INFO",
                    "same_phone_across_brokerages",
                    "brokerage_buyer_profiles",
                    "Same buyer phone appears in multiple brokerages. This is valid only if fields/conversations remain isolated.",
                    len(rows),
                    rows,
                )
            )

    if _has_table(tables, "listing_inquiries") and _has_table(tables, "buyer_profiles"):
        rows = _rows(
            conn,
            """
            SELECT i.id, i.brokerage_id AS inquiry_brokerage_id, p.brokerage_id AS buyer_profile_brokerage_id, right(i.buyer_phone, 4) AS buyer_phone_tail
            FROM listing_inquiries i
            JOIN buyer_profiles p ON p.phone = i.buyer_phone
            WHERE p.brokerage_id IS NULL OR p.brokerage_id IS DISTINCT FROM i.brokerage_id
            LIMIT 20
            """,
        )
        if rows:
            findings.append(
                Finding(
                    "HIGH",
                    "legacy_buyer_profile_linked_into_tenant_flow",
                    "listing_inquiries",
                    "Tenant-specific inquiry rows reference global or mismatched legacy buyer profiles.",
                    len(rows),
                    rows,
                )
            )


def _add_domain_findings(conn, findings: list[Finding], tables: set[str], columns: dict[str, set[str]]) -> None:
    if _has_table(tables, "listings"):
        null_count = _scalar(conn, "SELECT count(*) FROM listings WHERE brokerage_id IS NULL")
        if null_count:
            findings.append(Finding("CRITICAL", "listing_null_tenant", "listings", "Listings have NULL brokerage_id.", null_count))
        findings.append(
            Finding(
                "INFO",
                "global_listing_id_primary_key",
                "listings",
                "listing_id is globally unique today; DAL-170 must decide whether tenant identity is listing_id or (brokerage_id, listing_id).",
            )
        )

    if _has_table(tables, "conversations"):
        null_count = _scalar(conn, "SELECT count(*) FROM conversations WHERE brokerage_id IS NULL")
        if null_count:
            findings.append(
                Finding("CRITICAL", "conversation_null_tenant", "conversations", "Conversations have NULL brokerage_id.", null_count)
            )

    if _has_table(tables, "offer_records"):
        if _has_column(columns, "offer_records", "brokerage_id"):
            null_count = _scalar(conn, "SELECT count(*) FROM offer_records WHERE brokerage_id IS NULL")
            if null_count:
                findings.append(Finding("HIGH", "offer_record_null_tenant", "offer_records", "Legacy offer records have NULL brokerage_id.", null_count))
        rows = _rows(
            conn,
            """
            SELECT o.offer_id AS id, o.brokerage_id AS offer_brokerage_id, c.brokerage_id AS conversation_brokerage_id
            FROM offer_records o
            JOIN conversations c ON c.conversation_id = o.conversation_id
            WHERE o.brokerage_id IS NULL OR o.brokerage_id IS DISTINCT FROM c.brokerage_id
            LIMIT 20
            """,
        )
        if rows:
            findings.append(Finding("HIGH", "offer_record_mismatch", "offer_records", "Legacy offer records are null-tenant or mismatched.", len(rows), rows))

    if _has_table(tables, "media_assets"):
        orphan_count = _scalar(
            conn,
            """
            SELECT count(*) FROM media_assets
            WHERE conversation_id IS NULL AND listing_id IS NULL
            """,
        )
        if orphan_count:
            findings.append(
                Finding("MEDIUM", "media_without_parent", "media_assets", "Media assets have brokerage_id but no conversation/listing parent.", orphan_count)
            )

    if _has_table(tables, "inbound_provider_events") and _has_column(columns, "inbound_provider_events", "brokerage_id"):
        rows = _rows(
            conn,
            """
            SELECT COALESCE(status, 'unknown') AS status, count(*) AS count
            FROM inbound_provider_events
            WHERE brokerage_id IS NULL
            GROUP BY COALESCE(status, 'unknown')
            ORDER BY count DESC
            LIMIT 20
            """,
        )
        if rows:
            findings.append(
                Finding(
                    "MEDIUM",
                    "inbound_provider_events_null_tenant",
                    "inbound_provider_events",
                    "Inbound provider events have NULL brokerage_id; acceptable only for unresolved/pre-resolution ledgers.",
                    sum(int(row["count"]) for row in rows),
                    rows,
                )
            )


def audit() -> list[Finding]:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    columns: dict[str, set[str]] = {}
    nullable: dict[tuple[str, str], bool] = {}
    for table in tables:
        table_columns = inspector.get_columns(table)
        columns[table] = {column["name"] for column in table_columns}
        for column in table_columns:
            nullable[(table, column["name"])] = bool(column.get("nullable"))

    findings: list[Finding] = []
    _add_schema_findings(findings, tables, columns, nullable)
    with engine.connect() as conn:
        _add_null_row_findings(conn, findings, tables, columns)
        _add_mismatch_findings(conn, findings, tables)
        _add_legacy_buyer_findings(conn, findings, tables, columns)
        _add_domain_findings(conn, findings, tables, columns)
        normalization = dry_run_report(conn)
        for table in normalization["tables"]:
            findings.append(
                Finding(
                    "INFO",
                    "normalization_candidate_summary",
                    table["table"],
                    "Dry-run normalization counts for this root table.",
                    table["high_confidence_backfill_candidates"] + table["low_confidence_review_needed"] + table["quarantine"],
                    [
                        {
                            "high_confidence": table["high_confidence_backfill_candidates"],
                            "low_confidence": table["low_confidence_review_needed"],
                            "quarantine": table["quarantine"],
                        }
                    ],
                )
            )

    findings.sort(key=lambda item: (SEVERITY_ORDER[item.severity], item.table, item.check))
    return findings


def print_human(findings: list[Finding]) -> None:
    print("Dalya Tenant Isolation Audit")
    print("============================")
    print("Read-only audit. Findings indicate risk visibility, not script failure.")
    print()
    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for finding in findings:
        counts[finding.severity] += 1
    print("Summary")
    for severity in SEVERITY_ORDER:
        print(f"- {severity}: {counts[severity]}")
    print()

    for severity in SEVERITY_ORDER:
        severity_findings = [finding for finding in findings if finding.severity == severity]
        if not severity_findings:
            continue
        print(severity)
        print("-" * len(severity))
        for finding in severity_findings:
            suffix = f" count={finding.count}" if finding.count is not None else ""
            print(f"* [{finding.table}] {finding.check}: {finding.summary}{suffix}")
            if finding.sample:
                print(f"  sample={json.dumps(finding.sample[:3], default=str)}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only tenant isolation audit for Dalya.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    findings = audit()
    if args.json:
        print(json.dumps([asdict(finding) for finding in findings], default=str, indent=2))
    else:
        print_human(findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
