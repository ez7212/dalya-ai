from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pytest

from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBBrokerage,
    DBBrokerageBuyerProfile,
    DBBuyerProfile,
    DBConversation,
    DBListing,
    DBListingInquiry,
    DBOfferRecord,
    DBSuspiciousActivity,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_ENV_FILE = ".env.test"
TEST_ENV_OVERRIDE = "DALYA_TEST_ENV_FILE"


def _phone(suffix: str, offset: int = 0) -> str:
    digits = (int(suffix, 16) + offset) % 10000
    return f"+9715601{digits:04d}"


def _read_dotenv_values(env_file: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _normalization_env_file() -> Path:
    override = os.environ.get(TEST_ENV_OVERRIDE)
    env_file = Path(override or DEFAULT_TEST_ENV_FILE)
    if not env_file.is_absolute():
        env_file = ROOT / env_file

    if override and not env_file.exists():
        raise AssertionError(f"{TEST_ENV_OVERRIDE} does not exist: {env_file}")
    if not env_file.exists():
        raise AssertionError(f"Default test env file does not exist: {env_file}")

    values = _read_dotenv_values(env_file)
    dalya_env = (values.get("DALYA_ENV") or "").strip().lower()
    database_url = values.get("DATABASE_URL") or ""
    database_host = urlparse(database_url).hostname or ""
    prod_host = values.get("PROD_DB_HOST") or os.environ.get("PROD_DB_HOST") or ""

    if dalya_env == "production":
        raise AssertionError(f"{TEST_ENV_OVERRIDE or 'test env file'} points to DALYA_ENV=production: {env_file}")
    if prod_host and database_host and database_host == prod_host:
        raise AssertionError(f"{TEST_ENV_OVERRIDE or 'test env file'} points to the configured production DB host: {env_file}")
    if database_host and any(marker in database_host.lower() for marker in ("prod", "production")):
        raise AssertionError(f"{TEST_ENV_OVERRIDE or 'test env file'} points to a production-like DB host: {env_file}")

    return env_file


def _build_script_command(*args: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "dotenv",
        "-f",
        str(_normalization_env_file()),
        "run",
        "--",
        sys.executable,
        *args,
    ]


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        _build_script_command(*args),
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        check=False,
    )


def _run_normalization(*args: str) -> subprocess.CompletedProcess[str]:
    return _run_script("scripts/migrate_tenant_root_normalization.py", *args)


@pytest.fixture
def tenant_root_tooling_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_a = f"dal170c1-a-{suffix}"
    brokerage_b = f"dal170c1-b-{suffix}"
    listing_a = f"dal170c1-listing-a-{suffix}"
    listing_b = f"dal170c1-listing-b-{suffix}"
    listing_null = f"dal170c1-listing-null-{suffix}"
    conversation_a = f"dal170c1-conv-a-{suffix}"
    conversation_conflict = f"dal170c1-conv-conflict-{suffix}"
    buyer_phone = _phone(suffix)
    lineage_phone = _phone(suffix, 1)
    orphan_phone = _phone(suffix, 2)
    offer_candidate = f"dal170c1-offer-candidate-{suffix}"
    offer_conflict = f"dal170c1-offer-conflict-{suffix}"
    activity_candidate = f"dal170c1-activity-candidate-{suffix}"
    activity_missing = f"dal170c1-activity-missing-{suffix}"

    with SessionLocal() as db:
        db.add_all(
            [
                DBBrokerage(
                    brokerage_id=brokerage_a,
                    name="DAL-170C1 Brokerage A",
                    slug=brokerage_a,
                    status="active",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerage(
                    brokerage_id=brokerage_b,
                    name="DAL-170C1 Brokerage B",
                    slug=brokerage_b,
                    status="active",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBuyerProfile(phone=buyer_phone, brokerage_id=None, name="DAL-170C1 Buyer"),
                DBBuyerProfile(phone=lineage_phone, brokerage_id=None, name="DAL-170C1 Lineage Buyer"),
                DBBuyerProfile(phone=orphan_phone, brokerage_id=None, name="DAL-170C1 Orphan Buyer"),
                DBBrokerageBuyerProfile(
                    profile_id=f"dal170c1-profile-lineage-{suffix}",
                    brokerage_id=brokerage_b,
                    buyer_phone=lineage_phone,
                    name="Lineage Buyer",
                    source="test",
                ),
                DBListing(
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    spa_data={"project": "Tenant A Tower", "unit_number": "A-170C1"},
                    seller_asking_price=1_500_000,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=f"https://example.test/dal170c1/a/{suffix}",
                ),
                DBListing(
                    listing_id=listing_b,
                    brokerage_id=brokerage_b,
                    spa_data={"project": "Tenant B Tower", "unit_number": "B-170C1"},
                    seller_asking_price=2_500_000,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=f"https://example.test/dal170c1/b/{suffix}",
                ),
                DBListing(
                    listing_id=listing_null,
                    brokerage_id=None,
                    spa_data={"project": "Tenant Null Tower", "unit_number": "N-170C1"},
                    seller_asking_price=900_000,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=f"https://example.test/dal170c1/null/{suffix}",
                ),
                DBConversation(
                    conversation_id=conversation_a,
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    buyer_phone=buyer_phone,
                    buyer_name="Buyer A",
                    updated_at=datetime.utcnow(),
                ),
                DBConversation(
                    conversation_id=conversation_conflict,
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    buyer_phone=buyer_phone,
                    buyer_name="Buyer Conflict",
                    updated_at=datetime.utcnow() + timedelta(seconds=1),
                ),
            ]
        )
        db.flush()
        candidate_inquiry = DBListingInquiry(
            brokerage_id=None,
            buyer_phone=buyer_phone,
            listing_id=listing_b,
            project="Tenant B Tower",
            unit_number="B-170C1",
            price_aed=2_500_000,
        )
        lineage_inquiry = DBListingInquiry(
            brokerage_id=None,
            buyer_phone=lineage_phone,
            listing_id=f"missing-listing-{suffix}",
            project="Missing Listing",
            unit_number="L-170C1",
            price_aed=1_100_000,
        )
        quarantine_inquiry = DBListingInquiry(
            brokerage_id=None,
            buyer_phone=orphan_phone,
            listing_id=listing_null,
            project="Tenant Null Tower",
            unit_number="N-170C1",
            price_aed=900_000,
        )
        db.add_all(
            [
                candidate_inquiry,
                lineage_inquiry,
                quarantine_inquiry,
                DBOfferRecord(
                    offer_id=offer_candidate,
                    brokerage_id=None,
                    listing_id=listing_a,
                    conversation_id=conversation_a,
                    buyer_phone=buyer_phone,
                    buyer_name="Buyer A",
                    offer_amount_aed=1_450_000,
                    asking_price_aed=1_500_000,
                    gap_pct=3.33,
                    above_threshold=False,
                    escalated=False,
                    raw_message="Offer candidate",
                ),
                DBOfferRecord(
                    offer_id=offer_conflict,
                    brokerage_id=None,
                    listing_id=listing_b,
                    conversation_id=conversation_conflict,
                    buyer_phone=buyer_phone,
                    buyer_name="Buyer Conflict",
                    offer_amount_aed=1_450_000,
                    asking_price_aed=2_500_000,
                    gap_pct=42.0,
                    above_threshold=False,
                    escalated=False,
                    raw_message="Offer conflict",
                ),
                DBSuspiciousActivity(
                    activity_id=activity_candidate,
                    brokerage_id=None,
                    listing_id=listing_a,
                    conversation_id=conversation_a,
                    buyer_phone=buyer_phone,
                    buyer_name="Buyer A",
                    category="bypass_attempt",
                    trigger_message="Suspicious candidate",
                    bot_response="",
                ),
                DBSuspiciousActivity(
                    activity_id=activity_missing,
                    brokerage_id=None,
                    listing_id=listing_null,
                    conversation_id=conversation_conflict,
                    buyer_phone=orphan_phone,
                    buyer_name="Buyer Missing",
                    category="bypass_attempt",
                    trigger_message="Suspicious missing roots",
                    bot_response="",
                ),
            ]
        )
        safe_commit(db)
        db.refresh(candidate_inquiry)
        db.refresh(lineage_inquiry)
        db.refresh(quarantine_inquiry)
        candidate_inquiry_id = candidate_inquiry.id
        lineage_inquiry_id = lineage_inquiry.id
        quarantine_inquiry_id = quarantine_inquiry.id

    yield {
        "brokerage_a": brokerage_a,
        "brokerage_b": brokerage_b,
        "listing_a": listing_a,
        "listing_b": listing_b,
        "listing_null": listing_null,
        "conversation_a": conversation_a,
        "conversation_conflict": conversation_conflict,
        "buyer_phone": buyer_phone,
        "lineage_phone": lineage_phone,
        "orphan_phone": orphan_phone,
        "candidate_inquiry_id": candidate_inquiry_id,
        "lineage_inquiry_id": lineage_inquiry_id,
        "quarantine_inquiry_id": quarantine_inquiry_id,
        "offer_candidate": offer_candidate,
        "offer_conflict": offer_conflict,
        "activity_candidate": activity_candidate,
        "activity_missing": activity_missing,
    }

    with SessionLocal() as db:
        db.query(DBSuspiciousActivity).filter(
            DBSuspiciousActivity.activity_id.in_([activity_candidate, activity_missing])
        ).delete(synchronize_session=False)
        db.query(DBOfferRecord).filter(
            DBOfferRecord.offer_id.in_([offer_candidate, offer_conflict])
        ).delete(synchronize_session=False)
        db.query(DBListingInquiry).filter(
            DBListingInquiry.id.in_([candidate_inquiry_id, lineage_inquiry_id, quarantine_inquiry_id])
        ).delete(synchronize_session=False)
        db.query(DBConversation).filter(
            DBConversation.conversation_id.in_([conversation_a, conversation_conflict])
        ).delete(synchronize_session=False)
        db.query(DBBrokerageBuyerProfile).filter(
            DBBrokerageBuyerProfile.brokerage_id.in_([brokerage_a, brokerage_b])
        ).delete(synchronize_session=False)
        db.query(DBBuyerProfile).filter(
            DBBuyerProfile.phone.in_([buyer_phone, lineage_phone, orphan_phone])
        ).delete(synchronize_session=False)
        db.query(DBListing).filter(
            DBListing.listing_id.in_([listing_a, listing_b, listing_null])
        ).delete(synchronize_session=False)
        db.query(DBBrokerage).filter(
            DBBrokerage.brokerage_id.in_([brokerage_a, brokerage_b])
        ).delete(synchronize_session=False)
        safe_commit(db)


def _row_ids(rows) -> set:
    return {row.primary_key for row in rows}


def test_normalization_subprocess_defaults_to_env_test(monkeypatch):
    monkeypatch.delenv(TEST_ENV_OVERRIDE, raising=False)
    original_exists = Path.exists
    original_read_text = Path.read_text

    def fake_exists(path: Path) -> bool:
        if path == ROOT / ".env.test":
            return True
        return original_exists(path)

    def fake_read_text(path: Path) -> str:
        if path == ROOT / ".env.test":
            return "\n".join(
                [
                    "DALYA_ENV=test",
                    "DATABASE_URL=postgresql://user:pass@test-db.example.test/neondb",
                    "PROD_DB_HOST=prod-db.example.test",
                ]
            )
        return original_read_text(path)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "read_text", fake_read_text)

    command = _build_script_command("scripts/migrate_tenant_root_normalization.py", "--dry-run")

    env_file = Path(command[command.index("-f") + 1])
    assert env_file == ROOT / ".env.test"


def test_normalization_subprocess_respects_env_override(monkeypatch, tmp_path):
    env_file = tmp_path / ".env.override"
    env_file.write_text(
        "\n".join(
            [
                "DALYA_ENV=test",
                "DATABASE_URL=postgresql://user:pass@test-db.example.test/neondb",
                "PROD_DB_HOST=prod-db.example.test",
            ]
        )
    )
    monkeypatch.setenv(TEST_ENV_OVERRIDE, str(env_file))

    command = _build_script_command("scripts/migrate_tenant_root_normalization.py", "--dry-run")

    assert Path(command[command.index("-f") + 1]) == env_file
    assert str(ROOT / ".env.test") not in command


def test_normalization_subprocess_missing_env_override_fails_loudly(monkeypatch):
    monkeypatch.setenv(TEST_ENV_OVERRIDE, ".env.does-not-exist")

    with pytest.raises(AssertionError, match=f"{TEST_ENV_OVERRIDE} does not exist"):
        _build_script_command("scripts/migrate_tenant_root_normalization.py", "--dry-run")


def test_normalization_subprocess_rejects_production_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env.production-like"
    env_file.write_text(
        "\n".join(
            [
                "DALYA_ENV=production",
                "DATABASE_URL=postgresql://user:pass@example.test/neondb",
                "PROD_DB_HOST=prod.example.test",
            ]
        )
    )
    monkeypatch.setenv(TEST_ENV_OVERRIDE, str(env_file))

    with pytest.raises(AssertionError, match="DALYA_ENV=production"):
        _build_script_command("scripts/migrate_tenant_root_normalization.py", "--dry-run")


def test_normalization_subprocess_rejects_production_db_host(monkeypatch, tmp_path):
    env_file = tmp_path / ".env.production-host"
    env_file.write_text(
        "\n".join(
            [
                "DALYA_ENV=staging",
                "DATABASE_URL=postgresql://user:pass@prod-db.example.test/neondb",
                "PROD_DB_HOST=prod-db.example.test",
            ]
        )
    )
    monkeypatch.setenv(TEST_ENV_OVERRIDE, str(env_file))

    with pytest.raises(AssertionError, match="configured production DB host"):
        _build_script_command("scripts/migrate_tenant_root_normalization.py", "--dry-run")


def test_normalization_plans_classify_candidate_and_quarantine_rows(tenant_root_tooling_seed):
    from scripts import migrate_tenant_root_normalization as normalization

    with SessionLocal() as db:
        listing_plan = normalization.build_table_plan(db, "listing_inquiries")
        offer_plan = normalization.build_table_plan(db, "offer_records")
        suspicious_plan = normalization.build_table_plan(db, "suspicious_activity")

    assert tenant_root_tooling_seed["candidate_inquiry_id"] in _row_ids(listing_plan.high_confidence_backfill_candidates)
    assert tenant_root_tooling_seed["lineage_inquiry_id"] in _row_ids(listing_plan.high_confidence_backfill_candidates)
    assert tenant_root_tooling_seed["quarantine_inquiry_id"] in _row_ids(listing_plan.quarantine)
    assert tenant_root_tooling_seed["offer_candidate"] in _row_ids(offer_plan.high_confidence_backfill_candidates)
    assert tenant_root_tooling_seed["offer_conflict"] in _row_ids(offer_plan.quarantine)
    assert tenant_root_tooling_seed["activity_candidate"] in _row_ids(suspicious_plan.high_confidence_backfill_candidates)
    assert tenant_root_tooling_seed["activity_missing"] in _row_ids(suspicious_plan.quarantine)


def test_audit_script_reports_offer_records(tenant_root_tooling_seed):
    result = _run_script("scripts/audit_tenant_isolation.py")

    assert result.returncode == 0, result.stderr
    assert "offer_records" in result.stdout


def test_normalization_script_defaults_to_dry_run_and_is_idempotent(tenant_root_tooling_seed):
    first = _run_normalization("--json")
    second = _run_normalization("--dry-run", "--json")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr

    first_report = json.loads(first.stdout)
    second_report = json.loads(second.stdout)
    assert first_report["mode"] == "dry-run"
    assert first_report["writes_performed"] is False
    assert second_report["writes_performed"] is False
    assert first_report == second_report
    assert any(table["table"] == "offer_records" for table in first_report["tables"])
    assert any(table["high_confidence_backfill_candidates"] >= 1 for table in first_report["tables"])


def test_normalization_apply_requires_table(tenant_root_tooling_seed):
    result = _run_normalization("--apply", "--expected-count", "1", "--export-dir", "/tmp/dalya-dal170c1-test")

    assert result.returncode != 0
    assert "--apply requires --table" in result.stderr


def test_normalization_apply_rejects_unsupported_tables(tenant_root_tooling_seed, tmp_path):
    result = _run_normalization(
        "--apply",
        "--table",
        "suspicious_activity",
        "--expected-count",
        "1",
        "--export-dir",
        str(tmp_path / "suspicious"),
    )

    assert result.returncode != 0
    assert "Apply is not allowed for table: suspicious_activity" in result.stderr


def test_normalization_apply_expected_count_mismatch_blocks_writes(tenant_root_tooling_seed, tmp_path):
    from scripts import migrate_tenant_root_normalization as normalization

    with SessionLocal() as db:
        before = normalization.build_table_plan(db, "listing_inquiries").candidate_count
        with pytest.raises(RuntimeError, match="Candidate count mismatch for listing_inquiries"):
            normalization.apply_table(
                db,
                "listing_inquiries",
                expected_count=before + 1,
                export_dir=tmp_path / "mismatch",
                commit=False,
            )
        db.rollback()
        inquiry = db.query(DBListingInquiry).filter(
            DBListingInquiry.id == tenant_root_tooling_seed["candidate_inquiry_id"]
        ).one()
        assert inquiry.brokerage_id is None


def test_normalization_apply_commit_false_exports_and_rolls_back(tenant_root_tooling_seed, tmp_path):
    from scripts import migrate_tenant_root_normalization as normalization

    export_dir = tmp_path / "exports"
    with SessionLocal() as db:
        plan = normalization.build_table_plan(db, "offer_records")
        assert tenant_root_tooling_seed["offer_candidate"] in _row_ids(plan.high_confidence_backfill_candidates)
        result = normalization.apply_table(
            db,
            "offer_records",
            expected_count=plan.candidate_count,
            export_dir=export_dir,
            commit=False,
        )
        assert result.updated_count == plan.candidate_count
        assert result.remaining_candidates == 0
        assert (export_dir / "offer_records" / "manifest.json").exists()
        assert (export_dir / "offer_records" / "candidates.ndjson").read_text().strip()
        assert (export_dir / "offer_records" / "rollback.ndjson").read_text().strip()
        db.rollback()

    with SessionLocal() as db:
        offer = db.get(DBOfferRecord, tenant_root_tooling_seed["offer_candidate"])
        assert offer.brokerage_id is None


def test_normalization_production_apply_blocked_by_default(monkeypatch):
    from scripts import migrate_tenant_root_normalization as normalization

    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.delenv("ALLOW_PRODUCTION_TENANT_BACKFILL", raising=False)

    with SessionLocal() as db:
        with pytest.raises(RuntimeError, match="Production writes are blocked by default"):
            normalization.apply_table(
                db,
                "listing_inquiries",
                expected_count=0,
                allow_production=False,
                commit=False,
            )
