from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.runtime_config import env_bool, env_name, is_production
from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBBrokerageBuyerProfile,
    DBConversation,
    DBListing,
    DBListingInquiry,
    DBOfferRecord,
)


ALLOWED_APPLY_TABLES = {"listing_inquiries", "offer_records"}
REPORT_ONLY_TABLES = {"suspicious_activity"}
SUPPORTED_TABLES = ALLOWED_APPLY_TABLES | REPORT_ONLY_TABLES
PRODUCTION_BACKFILL_GUARD = "ALLOW_PRODUCTION_TENANT_BACKFILL"


@dataclass
class NormalizationRow:
    primary_key: Any
    current_brokerage_id: str | None
    derived_brokerage_id: str | None
    derivation_reason: str
    sources: dict[str, Any] = field(default_factory=dict)

    def export(self, table: str, env: str, mode: str) -> dict[str, Any]:
        payload = asdict(self)
        payload.update(
            {
                "table": table,
                "environment": env,
                "mode": mode,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        return payload


@dataclass
class TablePlan:
    table: str
    high_confidence_backfill_candidates: list[NormalizationRow] = field(default_factory=list)
    low_confidence_review_needed: list[NormalizationRow] = field(default_factory=list)
    quarantine: list[NormalizationRow] = field(default_factory=list)
    already_set: list[NormalizationRow] = field(default_factory=list)

    @property
    def candidate_count(self) -> int:
        return len(self.high_confidence_backfill_candidates)

    def summary(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "high_confidence_backfill_candidates": self.candidate_count,
            "low_confidence_review_needed": len(self.low_confidence_review_needed),
            "quarantine": len(self.quarantine),
            "already_set": len(self.already_set),
            "candidate_samples": [asdict(row) for row in self.high_confidence_backfill_candidates[:5]],
            "quarantine_samples": [asdict(row) for row in self.quarantine[:5]],
        }


@dataclass
class ApplyResult:
    table: str
    expected_count: int
    candidate_count: int
    updated_count: int
    remaining_candidates: int
    export_dir: str | None
    applied: bool
    rollback_strategy: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_phone(value: str | None) -> str | None:
    return value.strip() if value else None


def _load_listing_map(session: Session, listing_ids: set[str]) -> dict[str, DBListing]:
    if not listing_ids:
        return {}
    rows = session.execute(
        select(DBListing).where(DBListing.listing_id.in_(sorted(listing_ids)))
    ).scalars().all()
    return {row.listing_id: row for row in rows}


def _load_conversation_map(session: Session, conversation_ids: set[str]) -> dict[str, DBConversation]:
    if not conversation_ids:
        return {}
    rows = session.execute(
        select(DBConversation).where(DBConversation.conversation_id.in_(sorted(conversation_ids)))
    ).scalars().all()
    return {row.conversation_id: row for row in rows}


def _load_buyer_brokerage_map(session: Session, buyer_phones: set[str]) -> dict[str, set[str]]:
    if not buyer_phones:
        return {}
    rows = session.execute(
        select(DBBrokerageBuyerProfile.buyer_phone, DBBrokerageBuyerProfile.brokerage_id).where(
            DBBrokerageBuyerProfile.buyer_phone.in_(sorted(buyer_phones))
        )
    ).all()
    result: dict[str, set[str]] = {}
    for buyer_phone, brokerage_id in rows:
        if buyer_phone not in result:
            result[buyer_phone] = set()
        if brokerage_id:
            result[buyer_phone].add(brokerage_id)
    return result


def _listing_inquiries_plan(session: Session) -> TablePlan:
    plan = TablePlan(table="listing_inquiries")
    rows = session.query(DBListingInquiry).order_by(DBListingInquiry.id.asc()).all()
    listing_map = _load_listing_map(session, {row.listing_id for row in rows if row.listing_id})
    buyer_brokerage_map = _load_buyer_brokerage_map(session, {_normalize_phone(row.buyer_phone) or "" for row in rows})
    for row in rows:
        if row.brokerage_id:
            plan.already_set.append(
                NormalizationRow(
                    primary_key=row.id,
                    current_brokerage_id=row.brokerage_id,
                    derived_brokerage_id=row.brokerage_id,
                    derivation_reason="brokerage_id already populated",
                    sources={"listing_id": row.listing_id},
                )
            )
            continue

        listing = listing_map.get(row.listing_id)
        listing_brokerage_id = listing.brokerage_id if listing else None
        buyer_brokerages = buyer_brokerage_map.get(_normalize_phone(row.buyer_phone) or "", set())
        distinct_buyer_brokerages = {brokerage_id for brokerage_id in buyer_brokerages if brokerage_id}

        if listing_brokerage_id:
            plan.high_confidence_backfill_candidates.append(
                NormalizationRow(
                    primary_key=row.id,
                    current_brokerage_id=None,
                    derived_brokerage_id=listing_brokerage_id,
                    derivation_reason="linked listing has brokerage_id",
                    sources={
                        "listing_id": row.listing_id,
                        "listing_brokerage_id": listing_brokerage_id,
                        "buyer_brokerages": sorted(distinct_buyer_brokerages),
                    },
                )
            )
            continue

        if len(distinct_buyer_brokerages) == 1:
            derived_brokerage_id = next(iter(distinct_buyer_brokerages))
            plan.high_confidence_backfill_candidates.append(
                NormalizationRow(
                    primary_key=row.id,
                    current_brokerage_id=None,
                    derived_brokerage_id=derived_brokerage_id,
                    derivation_reason="unique brokerage_buyer_profiles lineage",
                    sources={
                        "listing_id": row.listing_id,
                        "buyer_brokerages": sorted(distinct_buyer_brokerages),
                    },
                )
            )
        else:
            plan.quarantine.append(
                NormalizationRow(
                    primary_key=row.id,
                    current_brokerage_id=None,
                    derived_brokerage_id=None,
                    derivation_reason="missing tenant listing and buyer lineage is ambiguous or absent",
                    sources={
                        "listing_id": row.listing_id,
                        "buyer_brokerages": sorted(distinct_buyer_brokerages),
                    },
                )
            )
    return plan


def _offer_records_plan(session: Session) -> TablePlan:
    plan = TablePlan(table="offer_records")
    rows = session.query(DBOfferRecord).order_by(DBOfferRecord.created_at.asc(), DBOfferRecord.offer_id.asc()).all()
    conversation_map = _load_conversation_map(session, {row.conversation_id for row in rows if row.conversation_id})
    listing_map = _load_listing_map(session, {row.listing_id for row in rows if row.listing_id})
    for row in rows:
        if row.brokerage_id:
            plan.already_set.append(
                NormalizationRow(
                    primary_key=row.offer_id,
                    current_brokerage_id=row.brokerage_id,
                    derived_brokerage_id=row.brokerage_id,
                    derivation_reason="brokerage_id already populated",
                    sources={
                        "conversation_id": row.conversation_id,
                        "listing_id": row.listing_id,
                    },
                )
            )
            continue

        sources: dict[str, str] = {}
        conversation = conversation_map.get(row.conversation_id)
        if conversation and conversation.brokerage_id:
            sources["conversation"] = conversation.brokerage_id

        listing = listing_map.get(row.listing_id)
        if listing and listing.brokerage_id:
            sources["listing"] = listing.brokerage_id

        distinct = {value for value in sources.values() if value}
        if not conversation or not listing:
            plan.quarantine.append(
                NormalizationRow(
                    primary_key=row.offer_id,
                    current_brokerage_id=None,
                    derived_brokerage_id=None,
                    derivation_reason="missing tenant conversation or listing root",
                    sources={
                        "conversation_id": row.conversation_id,
                        "listing_id": row.listing_id,
                    },
                )
            )
            continue

        if conversation.brokerage_id != listing.brokerage_id:
            plan.quarantine.append(
                NormalizationRow(
                    primary_key=row.offer_id,
                    current_brokerage_id=None,
                    derived_brokerage_id=None,
                    derivation_reason="conversation and listing brokerage signals conflict",
                    sources={
                        "conversation_id": row.conversation_id,
                        "listing_id": row.listing_id,
                        "signals": {
                            "conversation": conversation.brokerage_id if conversation else None,
                            "listing": listing.brokerage_id if listing else None,
                        },
                    },
                )
            )
            continue

        derived_brokerage_id = conversation.brokerage_id
        plan.high_confidence_backfill_candidates.append(
            NormalizationRow(
                primary_key=row.offer_id,
                current_brokerage_id=None,
                derived_brokerage_id=derived_brokerage_id,
                derivation_reason="conversation/listing tenant signals agree",
                sources={
                    "conversation_id": row.conversation_id,
                    "listing_id": row.listing_id,
                    "signals": {
                        "conversation": conversation.brokerage_id,
                        "listing": listing.brokerage_id,
                    },
                },
            )
        )
    return plan


def _suspicious_activity_plan(session: Session) -> TablePlan:
    plan = TablePlan(table="suspicious_activity")
    from app.models.db_models import DBSuspiciousActivity

    rows = session.query(DBSuspiciousActivity).order_by(DBSuspiciousActivity.created_at.asc(), DBSuspiciousActivity.activity_id.asc()).all()
    conversation_map = _load_conversation_map(session, {row.conversation_id for row in rows if row.conversation_id})
    listing_map = _load_listing_map(session, {row.listing_id for row in rows if row.listing_id})
    for row in rows:
        if row.brokerage_id:
            plan.already_set.append(
                NormalizationRow(
                    primary_key=row.activity_id,
                    current_brokerage_id=row.brokerage_id,
                    derived_brokerage_id=row.brokerage_id,
                    derivation_reason="brokerage_id already populated",
                    sources={"listing_id": row.listing_id, "conversation_id": row.conversation_id},
                )
            )
            continue

        sources: dict[str, str] = {}
        conversation = conversation_map.get(row.conversation_id) if row.conversation_id else None
        if conversation and conversation.brokerage_id:
            sources["conversation"] = conversation.brokerage_id
        listing = listing_map.get(row.listing_id) if row.listing_id else None
        if listing and listing.brokerage_id:
            sources["listing"] = listing.brokerage_id
        distinct = {value for value in sources.values() if value}
        if conversation and listing and conversation.brokerage_id == listing.brokerage_id and conversation.brokerage_id:
            plan.high_confidence_backfill_candidates.append(
                NormalizationRow(
                    primary_key=row.activity_id,
                    current_brokerage_id=None,
                    derived_brokerage_id=conversation.brokerage_id,
                    derivation_reason="conversation/listing tenant signals agree",
                    sources={
                        "listing_id": row.listing_id,
                        "conversation_id": row.conversation_id,
                        "signals": {
                            "conversation": conversation.brokerage_id if conversation else None,
                            "listing": listing.brokerage_id if listing else None,
                        },
                    },
                )
            )
        elif conversation or listing:
            plan.quarantine.append(
                NormalizationRow(
                    primary_key=row.activity_id,
                    current_brokerage_id=None,
                    derived_brokerage_id=None,
                    derivation_reason="conversation and listing brokerage signals conflict",
                    sources={
                        "listing_id": row.listing_id,
                        "conversation_id": row.conversation_id,
                        "signals": {
                            "conversation": conversation.brokerage_id if conversation else None,
                            "listing": listing.brokerage_id if listing else None,
                        },
                    },
                )
            )
        else:
            plan.quarantine.append(
                NormalizationRow(
                    primary_key=row.activity_id,
                    current_brokerage_id=None,
                    derived_brokerage_id=None,
                    derivation_reason="missing tenant conversation and listing roots",
                    sources={
                        "listing_id": row.listing_id,
                        "conversation_id": row.conversation_id,
                    },
                )
            )
    return plan


def build_table_plan(session: Session, table: str) -> TablePlan:
    if table not in SUPPORTED_TABLES:
        raise ValueError(f"Unsupported table: {table}")
    if table == "listing_inquiries":
        return _listing_inquiries_plan(session)
    if table == "offer_records":
        return _offer_records_plan(session)
    return _suspicious_activity_plan(session)


def dry_run_report(conn) -> dict[str, Any]:
    session = Session(bind=conn)
    try:
        plans = [build_table_plan(session, table) for table in ("listing_inquiries", "offer_records", "suspicious_activity")]
        return {
            "environment": env_name(),
            "mode": "dry-run",
            "writes_performed": False,
            "tables": [plan.summary() for plan in plans],
        }
    finally:
        session.close()


def _export_plan(plan: TablePlan, export_dir: Path, mode: str) -> tuple[Path, Path, Path]:
    export_dir.mkdir(parents=True, exist_ok=True)
    table_dir = export_dir / plan.table
    table_dir.mkdir(parents=True, exist_ok=True)

    manifest = table_dir / "manifest.json"
    candidates_file = table_dir / "candidates.ndjson"
    rollback_file = table_dir / "rollback.ndjson"

    common_rows = plan.high_confidence_backfill_candidates
    timestamp = _now()
    payload = {
        "table": plan.table,
        "environment": env_name(),
        "mode": mode,
        "timestamp_utc": timestamp,
        "candidate_count": len(common_rows),
        "quarantine_count": len(plan.quarantine),
        "already_set_count": len(plan.already_set),
        "rollback_strategy": "set brokerage_id back to NULL for rows listed in rollback.ndjson where brokerage_id matches the derived value",
    }
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with candidates_file.open("w", encoding="utf-8") as handle:
        for row in common_rows:
            handle.write(json.dumps(row.export(plan.table, env_name(), mode), sort_keys=True) + "\n")
    with rollback_file.open("w", encoding="utf-8") as handle:
        for row in common_rows:
            handle.write(
                json.dumps(
                    {
                        "table": plan.table,
                        "primary_key": row.primary_key,
                        "current_brokerage_id": row.current_brokerage_id,
                        "derived_brokerage_id": row.derived_brokerage_id,
                        "rollback_brokerage_id": row.current_brokerage_id,
                        "environment": env_name(),
                        "mode": mode,
                        "timestamp_utc": timestamp,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    return manifest, candidates_file, rollback_file


def _bulk_update_rows(session: Session, table: str, candidate_rows: list[NormalizationRow]) -> int:
    if not candidate_rows:
        return 0
    grouped: dict[str, list[Any]] = {}
    for row in candidate_rows:
        if not row.derived_brokerage_id:
            raise RuntimeError("candidate rows require a derived brokerage_id")
        grouped.setdefault(row.derived_brokerage_id, []).append(row.primary_key)

    total = 0
    for brokerage_id, candidate_ids in grouped.items():
        if table == "listing_inquiries":
            result = session.execute(
                update(DBListingInquiry)
                .where(DBListingInquiry.id.in_(candidate_ids))
                .where(DBListingInquiry.brokerage_id.is_(None))
                .values(brokerage_id=brokerage_id)
            )
        elif table == "offer_records":
            result = session.execute(
                update(DBOfferRecord)
                .where(DBOfferRecord.offer_id.in_(candidate_ids))
                .where(DBOfferRecord.brokerage_id.is_(None))
                .values(brokerage_id=brokerage_id)
            )
        else:
            raise ValueError(f"Unsupported apply table: {table}")
        total += int(result.rowcount or 0)
    return total


def apply_table(
    session: Session,
    table: str,
    *,
    expected_count: int | None = None,
    export_dir: Path | None = None,
    allow_production: bool = False,
    commit: bool = True,
) -> ApplyResult:
    if table not in ALLOWED_APPLY_TABLES:
        raise ValueError(f"Apply is not allowed for table: {table}")
    if is_production() and not allow_production:
        raise RuntimeError(
            f"Production writes are blocked by default. Set {PRODUCTION_BACKFILL_GUARD}=true to allow an explicit production backfill."
        )

    plan = build_table_plan(session, table)
    candidate_count = plan.candidate_count
    if expected_count is not None and candidate_count != expected_count:
        raise RuntimeError(
            f"Candidate count mismatch for {table}: expected {expected_count}, found {candidate_count}"
        )

    if export_dir is not None:
        _export_plan(plan, export_dir, mode="apply")

    if candidate_count == 0:
        return ApplyResult(
            table=table,
            expected_count=expected_count if expected_count is not None else 0,
            candidate_count=0,
            updated_count=0,
            remaining_candidates=0,
            export_dir=str(export_dir) if export_dir else None,
            applied=False,
            rollback_strategy="No-op. Re-run dry-run to confirm there are no remaining candidates.",
        )

    updated_count = _bulk_update_rows(session, table, plan.high_confidence_backfill_candidates)
    if updated_count != candidate_count:
        session.rollback()
        raise RuntimeError(
            f"Updated row count mismatch for {table}: expected {candidate_count}, wrote {updated_count}"
        )

    session.flush()
    if commit:
        safe_commit(session)

    remaining_plan = build_table_plan(session, table)
    return ApplyResult(
        table=table,
        expected_count=expected_count if expected_count is not None else candidate_count,
        candidate_count=candidate_count,
        updated_count=updated_count,
        remaining_candidates=remaining_plan.candidate_count,
        export_dir=str(export_dir) if export_dir else None,
        applied=True,
        rollback_strategy=(
            "Rollback by setting brokerage_id back to NULL for the rows listed in "
            f"{(export_dir / table / 'rollback.ndjson') if export_dir else 'the rollback export'}"
        ),
    )


def dry_run() -> dict[str, Any]:
    with SessionLocal() as session:
        plans = [build_table_plan(session, table) for table in ("listing_inquiries", "offer_records", "suspicious_activity")]
        return {
            "environment": env_name(),
            "mode": "dry-run",
            "writes_performed": False,
            "tables": [plan.summary() for plan in plans],
        }


def _human_print(report: dict[str, Any]) -> None:
    print("Dalya Tenant Root Normalization")
    print("================================")
    print(f"Environment: {report['environment']}")
    print(f"Mode: {report['mode']}")
    print(f"Writes performed: {report['writes_performed']}")
    print()
    for table in report["tables"]:
        print(table["table"])
        print("-" * len(table["table"]))
        print(f"high_confidence_backfill_candidates: {table['high_confidence_backfill_candidates']}")
        print(f"low_confidence_review_needed: {table['low_confidence_review_needed']}")
        print(f"quarantine: {table['quarantine']}")
        if table.get("candidate_samples"):
            print(f"candidate_samples: {json.dumps(table['candidate_samples'][:3], default=str)}")
        if table.get("quarantine_samples"):
            print(f"quarantine_samples: {json.dumps(table['quarantine_samples'][:3], default=str)}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Tenant root normalization audit/apply flow for Dalya.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan the backfill without writing.")
    mode.add_argument("--apply", action="store_true", help="Apply the approved backfill.")
    parser.add_argument("--table", choices=sorted(SUPPORTED_TABLES), help="Target table for apply or filtered reporting.")
    parser.add_argument("--expected-count", type=int, help="Assert the candidate count before writing.")
    parser.add_argument("--export-dir", type=Path, help="Export candidate and rollback manifests before apply.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        args.dry_run = True

    if args.apply and not args.table:
        parser.error("--apply requires --table")

    if args.apply and args.table not in ALLOWED_APPLY_TABLES:
        parser.error(f"Apply is not allowed for table: {args.table}")

    if args.apply and args.export_dir is None:
        parser.error("--apply requires --export-dir")

    if args.apply:
        with SessionLocal() as session:
            result = apply_table(
                session,
                args.table,
                expected_count=args.expected_count,
                export_dir=args.export_dir,
                allow_production=env_bool(PRODUCTION_BACKFILL_GUARD, default=False),
                commit=True,
            )
        payload = {
            "environment": env_name(),
            "mode": "apply",
            "writes_performed": True,
            "table": result.table,
            "candidate_count": result.candidate_count,
            "updated_count": result.updated_count,
            "remaining_candidates": result.remaining_candidates,
            "export_dir": result.export_dir,
            "rollback_strategy": result.rollback_strategy,
            "applied": result.applied,
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"Applied {result.updated_count} rows to {result.table}")
            print(f"Remaining candidates: {result.remaining_candidates}")
            print(f"Export dir: {result.export_dir}")
            print(f"Rollback strategy: {result.rollback_strategy}")
        return 0

    report = dry_run()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _human_print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
