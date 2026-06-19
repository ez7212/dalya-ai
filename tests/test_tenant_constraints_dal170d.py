from __future__ import annotations

import os
import subprocess
import sys
import uuid
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBDraftReply,
    DBBrokerage,
    DBBrokerageBuyerProfile,
    DBBuyerProfileField,
    DBConversation,
    DBLeadAssignment,
    DBListing,
    DBMediaAsset,
    DBOffer,
    DBViewing,
)
from scripts import audit_tenant_constraints_dal170d as preflight
from scripts import migrate_tenant_constraints_dal170d as migration


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(os.environ.get("DALYA_TEST_PYTHON", sys.executable))
_FIRST_FK_STATUS: tuple[bool, str] | None = None
_SECOND_FK_STATUS: tuple[bool, str] | None = None


def _phone(suffix: str, offset: int = 0) -> str:
    digits = (int(suffix, 16) + offset) % 10000
    return f"+9715701{digits:04d}"


def _run_migration(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env_file_override = os.environ.get("DALYA_TEST_ENV_FILE")
    env_file = Path(env_file_override) if env_file_override else ROOT / ".env.test"
    script = "scripts/migrate_tenant_constraints_dal170d.py"
    if env_file.exists():
        cmd = [
            str(PYTHON),
            "-m",
            "dotenv",
            "-f",
            str(env_file),
            "run",
            "--",
            str(PYTHON),
            script,
            *args,
        ]
    else:
        if env_file_override:
            raise AssertionError(f"DALYA_TEST_ENV_FILE does not exist: {env_file}")
        cmd = [str(PYTHON), script, *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        check=False,
    )


def _child_readiness(name: str) -> dict:
    return preflight.audit_child_candidate(name)


def _constraint_exists(name: str) -> bool:
    with SessionLocal() as db:
        return bool(
            db.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_constraint
                    WHERE connamespace = current_schema()::regnamespace
                      AND conname = :name
                    """
                ),
                {"name": name},
            ).scalar()
        )


def _cleanup_dal170d_rows() -> None:
    """Remove DAL-170D fixture rows before/after tests so aborted runs do not poison preflight."""
    with SessionLocal() as db:
        db.query(DBOffer).filter(DBOffer.offer_id.like("dal170d-%")).delete(synchronize_session=False)
        db.query(DBDraftReply).filter(DBDraftReply.draft_id.like("dal170d-%")).delete(synchronize_session=False)
        db.query(DBViewing).filter(DBViewing.viewing_id.like("dal170d-%")).delete(synchronize_session=False)
        db.query(DBMediaAsset).filter(DBMediaAsset.media_asset_id.like("dal170d-%")).delete(synchronize_session=False)
        db.query(DBLeadAssignment).filter(DBLeadAssignment.assignment_id.like("dal170d-%")).delete(synchronize_session=False)
        db.query(DBBuyerProfileField).filter(DBBuyerProfileField.field_id.like("dal170d-%")).delete(synchronize_session=False)
        db.query(DBBrokerageBuyerProfile).filter(DBBrokerageBuyerProfile.profile_id.like("dal170d-%")).delete(
            synchronize_session=False
        )
        db.query(DBConversation).filter(DBConversation.conversation_id.like("dal170d-%")).delete(
            synchronize_session=False
        )
        db.query(DBListing).filter(DBListing.listing_id.like("dal170d-%")).delete(synchronize_session=False)
        db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.like("dal170d-%")).delete(synchronize_session=False)
        safe_commit(db)


@pytest.fixture(scope="module", autouse=True)
def clean_dal170d_fixture_rows():
    _cleanup_dal170d_rows()
    yield
    _cleanup_dal170d_rows()


def _ensure_parent_and_child_ddl() -> None:
    migration.apply_phase("parent-keys")
    migration.apply_phase("child-indexes")


def _ensure_first_fks_or_refusal() -> tuple[bool, str]:
    global _FIRST_FK_STATUS
    if _FIRST_FK_STATUS is not None:
        return _FIRST_FK_STATUS
    _ensure_parent_and_child_ddl()
    try:
        migration.apply_phase("first-fks")
    except RuntimeError as exc:
        _FIRST_FK_STATUS = (False, str(exc))
        return _FIRST_FK_STATUS
    _FIRST_FK_STATUS = (True, "")
    return _FIRST_FK_STATUS


def _ensure_second_fks_or_refusal() -> tuple[bool, str]:
    global _SECOND_FK_STATUS
    if _SECOND_FK_STATUS is not None:
        return _SECOND_FK_STATUS
    _ensure_parent_and_child_ddl()
    try:
        migration.apply_phase("second-fks")
    except RuntimeError as exc:
        _SECOND_FK_STATUS = (False, str(exc))
        return _SECOND_FK_STATUS
    _SECOND_FK_STATUS = (True, "")
    return _SECOND_FK_STATUS


@pytest.fixture
def constraint_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_a = f"dal170d-a-{suffix}"
    brokerage_b = f"dal170d-b-{suffix}"
    listing_a = f"dal170d-listing-a-{suffix}"
    listing_b = f"dal170d-listing-b-{suffix}"
    conversation_a = f"dal170d-conv-a-{suffix}"
    conversation_b = f"dal170d-conv-b-{suffix}"
    profile_a = f"dal170d-profile-a-{suffix}"
    profile_b = f"dal170d-profile-b-{suffix}"
    buyer_phone = _phone(suffix)

    with SessionLocal() as db:
        db.add_all(
            [
                DBBrokerage(
                    brokerage_id=brokerage_a,
                    name="DAL-170D Brokerage A",
                    slug=brokerage_a,
                    status="active",
                    brokerage_ai_number=f"+9715803{int(suffix, 16) % 10000:04d}",
                    agents_ai_number=f"+9715903{int(suffix, 16) % 10000:04d}",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerage(
                    brokerage_id=brokerage_b,
                    name="DAL-170D Brokerage B",
                    slug=brokerage_b,
                    status="active",
                    brokerage_ai_number=f"+9715804{int(suffix, 16) % 10000:04d}",
                    agents_ai_number=f"+9715904{int(suffix, 16) % 10000:04d}",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBListing(
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    spa_data={"project": "DAL-170D A", "unit_number": "A"},
                    seller_asking_price=1_000_000,
                    commission_rate=0.02,
                    property_type="ready",
                ),
                DBListing(
                    listing_id=listing_b,
                    brokerage_id=brokerage_b,
                    spa_data={"project": "DAL-170D B", "unit_number": "B"},
                    seller_asking_price=2_000_000,
                    commission_rate=0.02,
                    property_type="ready",
                ),
                DBConversation(
                    conversation_id=conversation_a,
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    buyer_phone=buyer_phone,
                    buyer_name="Tenant A Buyer",
                    updated_at=datetime.utcnow(),
                ),
                DBConversation(
                    conversation_id=conversation_b,
                    listing_id=listing_b,
                    brokerage_id=brokerage_b,
                    buyer_phone=buyer_phone,
                    buyer_name="Tenant B Buyer",
                    updated_at=datetime.utcnow() + timedelta(seconds=1),
                ),
                DBBrokerageBuyerProfile(
                    profile_id=profile_a,
                    brokerage_id=brokerage_a,
                    buyer_phone=buyer_phone,
                    name="Profile A",
                    source="dal170d",
                ),
                DBBrokerageBuyerProfile(
                    profile_id=profile_b,
                    brokerage_id=brokerage_b,
                    buyer_phone=buyer_phone,
                    name="Profile B",
                    source="dal170d",
                ),
            ]
        )
        safe_commit(db)

    try:
        yield {
            "suffix": suffix,
            "brokerage_a": brokerage_a,
            "brokerage_b": brokerage_b,
            "listing_a": listing_a,
            "listing_b": listing_b,
            "conversation_a": conversation_a,
            "conversation_b": conversation_b,
            "profile_a": profile_a,
            "profile_b": profile_b,
            "buyer_phone": buyer_phone,
        }
    finally:
        with SessionLocal() as db:
            db.query(DBOffer).filter(DBOffer.offer_id.like(f"dal170d-offer-%-{suffix}")).delete(synchronize_session=False)
            db.query(DBDraftReply).filter(DBDraftReply.draft_id.like(f"dal170d-draft-%-{suffix}")).delete(synchronize_session=False)
            db.query(DBViewing).filter(DBViewing.viewing_id.like(f"dal170d-viewing-%-{suffix}")).delete(synchronize_session=False)
            db.query(DBMediaAsset).filter(DBMediaAsset.media_asset_id.like(f"dal170d-media-%-{suffix}")).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.assignment_id.like(f"dal170d-assignment-%-{suffix}")).delete(synchronize_session=False)
            db.query(DBBuyerProfileField).filter(DBBuyerProfileField.field_id.like(f"dal170d-field-%-{suffix}")).delete(synchronize_session=False)
            db.query(DBBrokerageBuyerProfile).filter(DBBrokerageBuyerProfile.profile_id.in_([profile_a, profile_b])).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id.in_([conversation_a, conversation_b])).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id.in_([listing_a, listing_b])).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
            safe_commit(db)


def _commit_or_constraint_rejects(row) -> bool:
    with SessionLocal() as db:
        db.add(row)
        try:
            safe_commit(db)
        except IntegrityError:
            db.rollback()
            return False
    return True


def test_preflight_reports_mixed_tenant_offer_blocker(constraint_seed):
    offer_id = f"dal170d-offer-dirty-{constraint_seed['suffix']}"
    inserted = _commit_or_constraint_rejects(
        DBOffer(
            offer_id=offer_id,
            brokerage_id=constraint_seed["brokerage_a"],
            conversation_id=constraint_seed["conversation_b"],
            listing_id=constraint_seed["listing_a"],
            buyer_profile_id=constraint_seed["profile_a"],
            buyer_phone=constraint_seed["buyer_phone"],
            thread_key=f"{constraint_seed['conversation_b']}:{constraint_seed['listing_a']}",
            amount=950_000,
            direction="buyer_offer",
            status="draft_pending_confirm",
            source="agent_logged",
        )
    )
    if not inserted:
        assert _constraint_exists("dal170d_fk_offers_conversation_tenant")
        return
    try:
        row = _child_readiness("offers_to_conversations")
        assert row["mixed_tenant_rows"] >= 1
        assert "mixed_tenant_rows" in row["blockers"]
    finally:
        with SessionLocal() as db:
            db.query(DBOffer).filter(DBOffer.offer_id == offer_id).delete(synchronize_session=False)
            safe_commit(db)


def test_preflight_reports_mixed_tenant_draft_reply_blocker(constraint_seed):
    draft_id = f"dal170d-draft-dirty-{constraint_seed['suffix']}"
    inserted = _commit_or_constraint_rejects(
        DBDraftReply(
            draft_id=draft_id,
            brokerage_id=constraint_seed["brokerage_a"],
            conversation_id=constraint_seed["conversation_b"],
            listing_id=constraint_seed["listing_a"],
            buyer_phone=constraint_seed["buyer_phone"],
            intent="follow_up",
            draft_text="dirty",
            status="draft",
        )
    )
    if not inserted:
        assert _constraint_exists("dal170d_fk_draft_replies_conversation_tenant")
        return
    try:
        row = _child_readiness("draft_replies_to_conversations")
        assert row["mixed_tenant_rows"] >= 1
    finally:
        with SessionLocal() as db:
            db.query(DBDraftReply).filter(DBDraftReply.draft_id == draft_id).delete(synchronize_session=False)
            safe_commit(db)


def test_preflight_reports_mixed_tenant_viewing_blocker(constraint_seed):
    viewing_id = f"dal170d-viewing-dirty-{constraint_seed['suffix']}"
    inserted = _commit_or_constraint_rejects(
        DBViewing(
            viewing_id=viewing_id,
            brokerage_id=constraint_seed["brokerage_a"],
            conversation_id=constraint_seed["conversation_b"],
            listing_id=constraint_seed["listing_a"],
            buyer_phone=constraint_seed["buyer_phone"],
            scheduled_for=datetime.utcnow() + timedelta(days=1),
            status="proposed",
        )
    )
    if not inserted:
        assert _constraint_exists("dal170d_fk_viewings_conversation_tenant")
        return
    try:
        row = _child_readiness("viewings_to_conversations")
        assert row["mixed_tenant_rows"] >= 1
    finally:
        with SessionLocal() as db:
            db.query(DBViewing).filter(DBViewing.viewing_id == viewing_id).delete(synchronize_session=False)
            safe_commit(db)


def test_preflight_reports_mixed_tenant_media_blocker(constraint_seed):
    media_id = f"dal170d-media-dirty-{constraint_seed['suffix']}"
    inserted = _commit_or_constraint_rejects(
        DBMediaAsset(
            media_asset_id=media_id,
            brokerage_id=constraint_seed["brokerage_a"],
            conversation_id=constraint_seed["conversation_b"],
            listing_id=constraint_seed["listing_a"],
            mime_type="image/jpeg",
            size_bytes=100,
            storage_ref=f"dal170d/{media_id}.jpg",
            source="composer_upload",
        )
    )
    if not inserted:
        assert _constraint_exists("dal170d_fk_media_assets_conversation_tenant")
        return
    try:
        row = _child_readiness("media_assets_to_conversations")
        assert row["mixed_tenant_rows"] >= 1
    finally:
        with SessionLocal() as db:
            db.query(DBMediaAsset).filter(DBMediaAsset.media_asset_id == media_id).delete(synchronize_session=False)
            safe_commit(db)


def test_preflight_reports_dirty_offers_to_listings_blocker(constraint_seed):
    offer_id = f"dal170d-offer-listing-dirty-{constraint_seed['suffix']}"
    inserted = _commit_or_constraint_rejects(
        DBOffer(
            offer_id=offer_id,
            brokerage_id=constraint_seed["brokerage_a"],
            conversation_id=constraint_seed["conversation_a"],
            listing_id=constraint_seed["listing_b"],
            buyer_profile_id=constraint_seed["profile_a"],
            buyer_phone=constraint_seed["buyer_phone"],
            thread_key=f"{constraint_seed['conversation_a']}:{constraint_seed['listing_b']}",
            amount=950_000,
            direction="buyer_offer",
            status="draft_pending_confirm",
            source="agent_logged",
        )
    )
    if not inserted:
        assert _constraint_exists("dal170d2_fk_offers_listing_tenant")
        return
    try:
        row = _child_readiness("offers_to_listings")
        assert row["mixed_tenant_rows"] >= 1
        assert "mixed_tenant_rows" in row["blockers"]
    finally:
        with SessionLocal() as db:
            db.query(DBOffer).filter(DBOffer.offer_id == offer_id).delete(synchronize_session=False)
            safe_commit(db)


def test_preflight_reports_dirty_draft_replies_to_listings_blocker(constraint_seed):
    draft_id = f"dal170d-draft-listing-dirty-{constraint_seed['suffix']}"
    inserted = _commit_or_constraint_rejects(
        DBDraftReply(
            draft_id=draft_id,
            brokerage_id=constraint_seed["brokerage_a"],
            conversation_id=constraint_seed["conversation_a"],
            listing_id=constraint_seed["listing_b"],
            buyer_phone=constraint_seed["buyer_phone"],
            intent="follow_up",
            draft_text="dirty",
            status="draft",
        )
    )
    if not inserted:
        assert _constraint_exists("dal170d2_fk_draft_replies_listing_tenant")
        return
    try:
        row = _child_readiness("draft_replies_to_listings")
        assert row["mixed_tenant_rows"] >= 1
    finally:
        with SessionLocal() as db:
            db.query(DBDraftReply).filter(DBDraftReply.draft_id == draft_id).delete(synchronize_session=False)
            safe_commit(db)


def test_preflight_reports_dirty_viewings_to_listings_blocker(constraint_seed):
    viewing_id = f"dal170d-viewing-listing-dirty-{constraint_seed['suffix']}"
    inserted = _commit_or_constraint_rejects(
        DBViewing(
            viewing_id=viewing_id,
            brokerage_id=constraint_seed["brokerage_a"],
            conversation_id=constraint_seed["conversation_a"],
            listing_id=constraint_seed["listing_b"],
            buyer_phone=constraint_seed["buyer_phone"],
            scheduled_for=datetime.utcnow() + timedelta(days=1),
            status="proposed",
        )
    )
    if not inserted:
        assert _constraint_exists("dal170d2_fk_viewings_listing_tenant")
        return
    try:
        row = _child_readiness("viewings_to_listings")
        assert row["mixed_tenant_rows"] >= 1
    finally:
        with SessionLocal() as db:
            db.query(DBViewing).filter(DBViewing.viewing_id == viewing_id).delete(synchronize_session=False)
            safe_commit(db)


def test_preflight_reports_dirty_media_assets_to_listings_blocker(constraint_seed):
    media_id = f"dal170d-media-listing-dirty-{constraint_seed['suffix']}"
    inserted = _commit_or_constraint_rejects(
        DBMediaAsset(
            media_asset_id=media_id,
            brokerage_id=constraint_seed["brokerage_a"],
            conversation_id=constraint_seed["conversation_a"],
            listing_id=constraint_seed["listing_b"],
            mime_type="image/jpeg",
            size_bytes=100,
            storage_ref=f"dal170d/{media_id}.jpg",
            source="composer_upload",
        )
    )
    if not inserted:
        assert _constraint_exists("dal170d2_fk_media_assets_listing_tenant")
        return
    try:
        row = _child_readiness("media_assets_to_listings")
        assert row["mixed_tenant_rows"] >= 1
    finally:
        with SessionLocal() as db:
            db.query(DBMediaAsset).filter(DBMediaAsset.media_asset_id == media_id).delete(synchronize_session=False)
            safe_commit(db)


def test_preflight_reports_child_brokerage_null_when_listing_ref_non_null(constraint_seed):
    media_id = f"dal170d-media-null-child-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        try:
            db.execute(
                text(
                    """
                    INSERT INTO media_assets (
                        media_asset_id, brokerage_id, conversation_id, listing_id,
                        mime_type, size_bytes, storage_ref, source
                    )
                    VALUES (
                        :media_id, NULL, NULL, :listing_id,
                        'image/jpeg', 100, :storage_ref, 'composer_upload'
                    )
                    """
                ),
                {
                    "media_id": media_id,
                    "listing_id": constraint_seed["listing_a"],
                    "storage_ref": f"dal170d/{media_id}.jpg",
                },
            )
            safe_commit(db)
        except IntegrityError:
            db.rollback()
            is_nullable = db.execute(
                text(
                    """
                    SELECT is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'media_assets'
                      AND column_name = 'brokerage_id'
                    """
                )
            ).scalar()
            assert is_nullable == "NO"
            return
    try:
        row = _child_readiness("media_assets_to_listings")
        assert row["null_child_tenant_rows"] >= 1
        assert "null_child_tenant" in row["blockers"]
        assert row["classification"] == "blocked_by_null_child_tenant"
    finally:
        with SessionLocal() as db:
            db.query(DBMediaAsset).filter(DBMediaAsset.media_asset_id == media_id).delete(synchronize_session=False)
            safe_commit(db)


def test_preflight_reports_dal170c_backfill_dependencies():
    report = preflight.audit()
    deferred = {row["table"]: row["classification"] for row in report["deferred"]}
    assert deferred["listing_inquiries"] == "requires_dal170c_apply"
    assert deferred["offer_records"] == "requires_dal170c_apply"
    assert deferred["suspicious_activity"] == "deferred_compliance"


def test_parent_composite_unique_index_migration_is_idempotent():
    first = migration.apply_phase("parent-keys")
    second = migration.apply_phase("parent-keys")
    assert first["phase"] == "parent-keys"
    assert second["phase"] == "parent-keys"
    assert any(row["name"] == "dal170d_uq_bbp_brokerage_profile" for row in second["statements"])


def test_child_supporting_index_migration_is_idempotent():
    first = migration.apply_phase("child-indexes")
    second = migration.apply_phase("child-indexes")
    assert first["phase"] == "child-indexes"
    assert second["phase"] == "child-indexes"
    assert any(row["name"] == "dal170d_ix_bpf_brokerage_profile" for row in second["statements"])


def test_first_fks_migration_refuses_dirty_data(constraint_seed):
    _ensure_parent_and_child_ddl()
    offer_id = f"dal170d-offer-dirty-{constraint_seed['suffix']}"
    inserted = _commit_or_constraint_rejects(
        DBOffer(
            offer_id=offer_id,
            brokerage_id=constraint_seed["brokerage_a"],
            conversation_id=constraint_seed["conversation_b"],
            listing_id=constraint_seed["listing_a"],
            buyer_profile_id=constraint_seed["profile_a"],
            buyer_phone=constraint_seed["buyer_phone"],
            thread_key=f"{constraint_seed['conversation_b']}:{constraint_seed['listing_a']}",
            amount=950_000,
            direction="buyer_offer",
            status="draft_pending_confirm",
            source="agent_logged",
        )
    )
    if not inserted:
        assert _constraint_exists("dal170d_fk_offers_conversation_tenant")
        return
    try:
        with pytest.raises(RuntimeError, match="Preflight blockers prevent applying phase first-fks"):
            migration.apply_phase("first-fks")
    finally:
        with SessionLocal() as db:
            db.query(DBOffer).filter(DBOffer.offer_id == offer_id).delete(synchronize_session=False)
            safe_commit(db)


def test_second_fks_migration_refuses_dirty_data(constraint_seed):
    _ensure_parent_and_child_ddl()
    offer_id = f"dal170d-offer-listing-dirty-{constraint_seed['suffix']}"
    inserted = _commit_or_constraint_rejects(
        DBOffer(
            offer_id=offer_id,
            brokerage_id=constraint_seed["brokerage_a"],
            conversation_id=constraint_seed["conversation_a"],
            listing_id=constraint_seed["listing_b"],
            buyer_profile_id=constraint_seed["profile_a"],
            buyer_phone=constraint_seed["buyer_phone"],
            thread_key=f"{constraint_seed['conversation_a']}:{constraint_seed['listing_b']}",
            amount=950_000,
            direction="buyer_offer",
            status="draft_pending_confirm",
            source="agent_logged",
        )
    )
    if not inserted:
        assert _constraint_exists("dal170d2_fk_offers_listing_tenant")
        return
    try:
        with pytest.raises(RuntimeError, match="Preflight blockers prevent applying phase second-fks"):
            migration.apply_phase("second-fks")
    finally:
        with SessionLocal() as db:
            db.query(DBOffer).filter(DBOffer.offer_id == offer_id).delete(synchronize_session=False)
            safe_commit(db)


def test_second_fks_refuses_missing_listing_parent_identity(monkeypatch):
    tables, columns, constraints, indexes = migration._existing_schema()
    second_fk_constraints = {
        "dal170d2_fk_offers_listing_tenant",
        "dal170d2_fk_draft_replies_listing_tenant",
        "dal170d2_fk_viewings_listing_tenant",
        "dal170d2_fk_media_assets_listing_tenant",
    }

    def missing_listing_parent_identity():
        return (
            tables,
            columns,
            constraints - second_fk_constraints,
            indexes - {"dal170d_uq_listings_brokerage_listing"},
        )

    monkeypatch.setattr(migration, "_existing_schema", missing_listing_parent_identity)
    result = migration.plan_phase("second-fks")
    assert any(
        blocker.get("type") == "missing_parent_identity"
        and blocker.get("required_index") == "dal170d_uq_listings_brokerage_listing"
        for blocker in result["blockers"]
    )
    with pytest.raises(RuntimeError, match="missing_parent_identity"):
        migration.apply_phase("second-fks")


def test_second_fks_migration_is_idempotent():
    _ensure_parent_and_child_ddl()
    first = migration.apply_phase("second-fks")
    second = migration.apply_phase("second-fks")
    assert first["phase"] == "second-fks"
    assert second["phase"] == "second-fks"
    assert any(
        row["name"] == "dal170d2_fk_offers_listing_tenant"
        and row["reason"] == "constraint_already_exists"
        for row in second["skipped"]
    )


def test_same_tenant_buyer_profile_field_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    field_id = f"dal170d-field-clean-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBBuyerProfileField(
                field_id=field_id,
                profile_id=constraint_seed["profile_a"],
                brokerage_id=constraint_seed["brokerage_a"],
                field="timeline",
                value="this_month",
                provenance="agent_confirmed",
            )
        )
        safe_commit(db)
        db.query(DBBuyerProfileField).filter(DBBuyerProfileField.field_id == field_id).delete(synchronize_session=False)
        safe_commit(db)


def test_cross_tenant_buyer_profile_field_rejected_after_fk(constraint_seed):
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    with SessionLocal() as db:
        db.add(
            DBBuyerProfileField(
                field_id=f"dal170d-field-dirty-{constraint_seed['suffix']}",
                profile_id=constraint_seed["profile_b"],
                brokerage_id=constraint_seed["brokerage_a"],
                field="timeline",
                value="this_month",
                provenance="agent_confirmed",
            )
        )
        with pytest.raises(IntegrityError):
            safe_commit(db)
        db.rollback()


def test_same_tenant_offer_conversation_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    offer_id = f"dal170d-offer-fk-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBOffer(
                offer_id=offer_id,
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_a"],
                buyer_profile_id=constraint_seed["profile_a"],
                buyer_phone=constraint_seed["buyer_phone"],
                thread_key=f"{constraint_seed['conversation_a']}:{constraint_seed['listing_a']}",
                amount=950_000,
                direction="buyer_offer",
                status="draft_pending_confirm",
                source="agent_logged",
            )
        )
        safe_commit(db)
        db.query(DBOffer).filter(DBOffer.offer_id == offer_id).delete(synchronize_session=False)
        safe_commit(db)


def test_mixed_tenant_offer_conversation_rejected_after_fk(constraint_seed):
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    with SessionLocal() as db:
        db.add(
            DBOffer(
                offer_id=f"dal170d-offer-dirty-{constraint_seed['suffix']}",
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_b"],
                listing_id=constraint_seed["listing_a"],
                buyer_profile_id=constraint_seed["profile_a"],
                buyer_phone=constraint_seed["buyer_phone"],
                thread_key=f"{constraint_seed['conversation_b']}:{constraint_seed['listing_a']}",
                amount=950_000,
                direction="buyer_offer",
                status="draft_pending_confirm",
                source="agent_logged",
            )
        )
        with pytest.raises(IntegrityError):
            safe_commit(db)
        db.rollback()


def test_same_tenant_draft_reply_conversation_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    draft_id = f"dal170d-draft-clean-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBDraftReply(
                draft_id=draft_id,
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_a"],
                buyer_phone=constraint_seed["buyer_phone"],
                intent="follow_up",
                draft_text="clean",
                status="draft",
            )
        )
        safe_commit(db)
        db.query(DBDraftReply).filter(DBDraftReply.draft_id == draft_id).delete(synchronize_session=False)
        safe_commit(db)


def test_mixed_tenant_draft_reply_conversation_rejected_after_fk(constraint_seed):
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    with SessionLocal() as db:
        db.add(
            DBDraftReply(
                draft_id=f"dal170d-draft-dirty-{constraint_seed['suffix']}",
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_b"],
                listing_id=constraint_seed["listing_a"],
                buyer_phone=constraint_seed["buyer_phone"],
                intent="follow_up",
                draft_text="dirty",
                status="draft",
            )
        )
        with pytest.raises(IntegrityError):
            safe_commit(db)
        db.rollback()


def test_same_tenant_viewing_conversation_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    viewing_id = f"dal170d-viewing-clean-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBViewing(
                viewing_id=viewing_id,
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_a"],
                buyer_phone=constraint_seed["buyer_phone"],
                scheduled_for=datetime.utcnow() + timedelta(days=1),
                status="proposed",
            )
        )
        safe_commit(db)
        db.query(DBViewing).filter(DBViewing.viewing_id == viewing_id).delete(synchronize_session=False)
        safe_commit(db)


def test_mixed_tenant_viewing_conversation_rejected_after_fk(constraint_seed):
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    with SessionLocal() as db:
        db.add(
            DBViewing(
                viewing_id=f"dal170d-viewing-dirty-{constraint_seed['suffix']}",
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_b"],
                listing_id=constraint_seed["listing_a"],
                buyer_phone=constraint_seed["buyer_phone"],
                scheduled_for=datetime.utcnow() + timedelta(days=1),
                status="proposed",
            )
        )
        with pytest.raises(IntegrityError):
            safe_commit(db)
        db.rollback()


def test_same_tenant_media_conversation_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    media_id = f"dal170d-media-clean-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBMediaAsset(
                media_asset_id=media_id,
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_a"],
                mime_type="image/jpeg",
                size_bytes=100,
                storage_ref=f"dal170d/{media_id}.jpg",
                source="composer_upload",
            )
        )
        safe_commit(db)
        db.query(DBMediaAsset).filter(DBMediaAsset.media_asset_id == media_id).delete(synchronize_session=False)
        safe_commit(db)


def test_mixed_tenant_media_conversation_rejected_after_fk(constraint_seed):
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    with SessionLocal() as db:
        db.add(
            DBMediaAsset(
                media_asset_id=f"dal170d-media-dirty-{constraint_seed['suffix']}",
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_b"],
                listing_id=constraint_seed["listing_a"],
                mime_type="image/jpeg",
                size_bytes=100,
                storage_ref=f"dal170d/dirty-{constraint_seed['suffix']}.jpg",
                source="composer_upload",
            )
        )
        with pytest.raises(IntegrityError):
            safe_commit(db)
        db.rollback()


def test_same_tenant_offer_listing_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    offer_id = f"dal170d-offer-listing-clean-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBOffer(
                offer_id=offer_id,
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_a"],
                buyer_profile_id=constraint_seed["profile_a"],
                buyer_phone=constraint_seed["buyer_phone"],
                thread_key=f"{constraint_seed['conversation_a']}:{constraint_seed['listing_a']}",
                amount=950_000,
                direction="buyer_offer",
                status="draft_pending_confirm",
                source="agent_logged",
            )
        )
        safe_commit(db)
        db.query(DBOffer).filter(DBOffer.offer_id == offer_id).delete(synchronize_session=False)
        safe_commit(db)


def test_mixed_tenant_offer_listing_rejected_after_fk(constraint_seed):
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    with SessionLocal() as db:
        db.add(
            DBOffer(
                offer_id=f"dal170d-offer-listing-dirty-{constraint_seed['suffix']}",
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_b"],
                buyer_profile_id=constraint_seed["profile_a"],
                buyer_phone=constraint_seed["buyer_phone"],
                thread_key=f"{constraint_seed['conversation_a']}:{constraint_seed['listing_b']}",
                amount=950_000,
                direction="buyer_offer",
                status="draft_pending_confirm",
                source="agent_logged",
            )
        )
        with pytest.raises(IntegrityError):
            safe_commit(db)
        db.rollback()


def test_same_tenant_draft_reply_listing_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    draft_id = f"dal170d-draft-listing-clean-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBDraftReply(
                draft_id=draft_id,
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_a"],
                buyer_phone=constraint_seed["buyer_phone"],
                intent="follow_up",
                draft_text="clean",
                status="draft",
            )
        )
        safe_commit(db)
        db.query(DBDraftReply).filter(DBDraftReply.draft_id == draft_id).delete(synchronize_session=False)
        safe_commit(db)


def test_null_draft_reply_listing_id_remains_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    draft_id = f"dal170d-draft-null-listing-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBDraftReply(
                draft_id=draft_id,
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=None,
                buyer_phone=constraint_seed["buyer_phone"],
                intent="follow_up",
                draft_text="null listing is allowed",
                status="draft",
            )
        )
        safe_commit(db)
        db.query(DBDraftReply).filter(DBDraftReply.draft_id == draft_id).delete(synchronize_session=False)
        safe_commit(db)


def test_mixed_tenant_draft_reply_listing_rejected_after_fk(constraint_seed):
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    with SessionLocal() as db:
        db.add(
            DBDraftReply(
                draft_id=f"dal170d-draft-listing-dirty-{constraint_seed['suffix']}",
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_b"],
                buyer_phone=constraint_seed["buyer_phone"],
                intent="follow_up",
                draft_text="dirty",
                status="draft",
            )
        )
        with pytest.raises(IntegrityError):
            safe_commit(db)
        db.rollback()


def test_same_tenant_viewing_listing_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    viewing_id = f"dal170d-viewing-listing-clean-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBViewing(
                viewing_id=viewing_id,
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_a"],
                buyer_phone=constraint_seed["buyer_phone"],
                scheduled_for=datetime.utcnow() + timedelta(days=1),
                status="proposed",
            )
        )
        safe_commit(db)
        db.query(DBViewing).filter(DBViewing.viewing_id == viewing_id).delete(synchronize_session=False)
        safe_commit(db)


def test_mixed_tenant_viewing_listing_rejected_after_fk(constraint_seed):
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    with SessionLocal() as db:
        db.add(
            DBViewing(
                viewing_id=f"dal170d-viewing-listing-dirty-{constraint_seed['suffix']}",
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_b"],
                buyer_phone=constraint_seed["buyer_phone"],
                scheduled_for=datetime.utcnow() + timedelta(days=1),
                status="proposed",
            )
        )
        with pytest.raises(IntegrityError):
            safe_commit(db)
        db.rollback()


def test_same_tenant_media_listing_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    media_id = f"dal170d-media-listing-clean-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBMediaAsset(
                media_asset_id=media_id,
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_a"],
                mime_type="image/jpeg",
                size_bytes=100,
                storage_ref=f"dal170d/{media_id}.jpg",
                source="composer_upload",
            )
        )
        safe_commit(db)
        db.query(DBMediaAsset).filter(DBMediaAsset.media_asset_id == media_id).delete(synchronize_session=False)
        safe_commit(db)


def test_null_media_asset_listing_id_remains_allowed_after_fk(constraint_seed):
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    media_id = f"dal170d-media-null-listing-{constraint_seed['suffix']}"
    with SessionLocal() as db:
        db.add(
            DBMediaAsset(
                media_asset_id=media_id,
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=None,
                mime_type="image/jpeg",
                size_bytes=100,
                storage_ref=f"dal170d/{media_id}.jpg",
                source="composer_upload",
            )
        )
        safe_commit(db)
        db.query(DBMediaAsset).filter(DBMediaAsset.media_asset_id == media_id).delete(synchronize_session=False)
        safe_commit(db)


def test_mixed_tenant_media_listing_rejected_after_fk(constraint_seed):
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    with SessionLocal() as db:
        db.add(
            DBMediaAsset(
                media_asset_id=f"dal170d-media-listing-dirty-{constraint_seed['suffix']}",
                brokerage_id=constraint_seed["brokerage_a"],
                conversation_id=constraint_seed["conversation_a"],
                listing_id=constraint_seed["listing_b"],
                mime_type="image/jpeg",
                size_bytes=100,
                storage_ref=f"dal170d/dirty-listing-{constraint_seed['suffix']}.jpg",
                source="composer_upload",
            )
        )
        with pytest.raises(IntegrityError):
            safe_commit(db)
        db.rollback()


def test_production_apply_is_blocked_by_default(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.delenv("ALLOW_PRODUCTION_TENANT_CONSTRAINTS", raising=False)
    with pytest.raises(RuntimeError, match="Production DDL is blocked by default"):
        migration.apply_phase("parent-keys")
    with pytest.raises(RuntimeError, match="Production DDL is blocked by default"):
        migration.apply_phase("second-fks")


def test_print_db_fingerprint_does_not_expose_secrets():
    result = _run_migration("--print-db-fingerprint", "--phase", "parent-keys", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["fingerprint"]
    assert payload["database_url_host_masked"]
    assert "postgresql://" not in result.stdout
    assert "DATABASE_URL" not in result.stdout
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        assert database_url not in result.stdout


def test_production_apply_refuses_without_db_fingerprint_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.setenv("ALLOW_PRODUCTION_TENANT_CONSTRAINTS", "true")
    monkeypatch.setattr(migration, "get_db_fingerprint", lambda phase: {"fingerprint": "expected", "phase": phase})
    with pytest.raises(RuntimeError, match="requires --expected-db-fingerprint"):
        migration.apply_phase("parent-keys", artifact_dir=str(tmp_path))


def test_production_apply_refuses_fingerprint_mismatch(monkeypatch, tmp_path):
    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.setenv("ALLOW_PRODUCTION_TENANT_CONSTRAINTS", "true")
    monkeypatch.setattr(migration, "get_db_fingerprint", lambda phase: {"fingerprint": "actual", "phase": phase})
    with pytest.raises(RuntimeError, match="fingerprint mismatch"):
        migration.apply_phase(
            "parent-keys",
            expected_db_fingerprint="expected",
            artifact_dir=str(tmp_path),
        )


def test_apply_refuses_production_like_database_url_with_non_production_env(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setattr(migration, "get_db_fingerprint", lambda phase: {"fingerprint": "expected", "phase": phase})
    monkeypatch.setattr(migration, "_database_url_looks_production_like", lambda: True)
    with pytest.raises(RuntimeError, match="looks production-like"):
        migration.apply_phase("parent-keys")


def test_non_production_apply_refuses_when_prod_db_host_missing(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-example.neon.tech/neondb")
    monkeypatch.delenv("PROD_DB_HOST", raising=False)
    monkeypatch.setattr(migration, "get_db_fingerprint", lambda phase: {"fingerprint": "expected", "phase": phase})
    with pytest.raises(RuntimeError, match="PROD_DB_HOST is not set"):
        migration.apply_phase("parent-keys")


def test_non_production_apply_refuses_exact_prod_db_host_match(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-example.neon.tech/neondb")
    monkeypatch.setenv("PROD_DB_HOST", "ep-example.neon.tech")
    monkeypatch.setattr(migration, "get_db_fingerprint", lambda phase: {"fingerprint": "expected", "phase": phase})
    with pytest.raises(RuntimeError, match="looks production-like"):
        migration.apply_phase("parent-keys")


def test_non_production_rehearsal_override_requires_confirmation_artifacts(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-example.neon.tech/neondb")
    monkeypatch.delenv("PROD_DB_HOST", raising=False)
    monkeypatch.setattr(migration, "get_db_fingerprint", lambda phase: {"fingerprint": "expected", "phase": phase})
    with pytest.raises(RuntimeError, match="Production-like rehearsal DDL apply requires --artifact-dir"):
        migration.apply_phase(
            "parent-keys",
            allow_production_like_url_without_production_env=True,
        )


def test_non_production_apply_allows_confirmed_rehearsal_override(monkeypatch, tmp_path):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-example.neon.tech/neondb")
    monkeypatch.delenv("PROD_DB_HOST", raising=False)
    monkeypatch.setattr(
        migration,
        "get_db_fingerprint",
        lambda phase: {
            "fingerprint": "expected",
            "phase": phase,
            "dalya_env": "test",
            "database_url_host_masked": "ep***.neon.tech",
            "database_url_database": "neondb",
        },
    )
    monkeypatch.setattr(
        migration,
        "plan_phase",
        lambda phase, **kwargs: {
            "environment": "test",
            "phase": phase,
            "blockers": [],
            "statements": [],
            "skipped": [],
            "rollback_sql": [],
            "preflight_summary": {"blocker_count": 0},
            "timeouts": {
                "lock_timeout_ms": kwargs["lock_timeout_ms"],
                "statement_timeout_ms": kwargs["statement_timeout_ms"],
            },
        },
    )
    monkeypatch.setattr(migration, "_execute_plan_statements", lambda *args, **kwargs: [])
    result = migration.apply_phase(
        "parent-keys",
        allow_production_like_url_without_production_env=True,
        expected_db_fingerprint="expected",
        artifact_dir=str(tmp_path),
    )
    assert result["applied"] == []
    assert result["artifact_path"]


def test_production_apply_writes_artifact_bundle_before_execution(monkeypatch, tmp_path):
    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.setenv("ALLOW_PRODUCTION_TENANT_CONSTRAINTS", "true")
    monkeypatch.setattr(
        migration,
        "get_db_fingerprint",
        lambda phase: {
            "fingerprint": "expected",
            "phase": phase,
            "dalya_env": "production",
            "database_url_host_masked": "pr***.example.com",
            "database_url_database": "dalya",
        },
    )
    monkeypatch.setattr(
        migration,
        "plan_phase",
        lambda phase, **kwargs: {
            "environment": "production",
            "phase": phase,
            "blockers": [],
            "statements": [
                {
                    "name": "dal170d_test_statement",
                    "sql": "SELECT 1",
                    "rollback_sql": "SELECT 1",
                    "table": "test",
                    "required_columns": [],
                    "kind": "test",
                }
            ],
            "skipped": [],
            "rollback_sql": ["SELECT 1"],
            "preflight_summary": {"blocker_count": 0},
            "timeouts": {
                "lock_timeout_ms": kwargs["lock_timeout_ms"],
                "statement_timeout_ms": kwargs["statement_timeout_ms"],
            },
        },
    )

    def stop_before_execution(*args, **kwargs):
        raise RuntimeError("stop before ddl")

    monkeypatch.setattr(migration, "_execute_plan_statements", stop_before_execution)
    with pytest.raises(RuntimeError, match="stop before ddl"):
        migration.apply_phase(
            "parent-keys",
            expected_db_fingerprint="expected",
            artifact_dir=str(tmp_path),
        )
    bundles = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(bundles) == 1
    expected_files = {
        "db_fingerprint.json",
        "preflight_summary.json",
        "dry_run_sql.sql",
        "rollback_sql.sql",
        "apply_plan.json",
    }
    assert expected_files == {path.name for path in bundles[0].iterdir()}
    assert "SELECT 1" in (bundles[0] / "rollback_sql.sql").read_text()


def test_apply_requires_explicit_phase():
    result = _run_migration("--apply")
    assert result.returncode != 0
    assert "--phase is required" in result.stderr


def test_unsupported_phase_is_rejected():
    result = _run_migration("--dry-run", "--phase", "all")
    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_timeout_settings_are_printed_in_dry_run():
    result = _run_migration(
        "--dry-run",
        "--phase",
        "parent-keys",
        "--lock-timeout-ms",
        "1234",
        "--statement-timeout-ms",
        "5678",
    )
    assert result.returncode == 0, result.stderr
    assert "Lock timeout: 1234ms" in result.stdout
    assert "Statement timeout: 5678ms" in result.stdout


def test_rollback_sql_is_printed():
    result = _run_migration("--dry-run", "--phase", "parent-keys")
    assert result.returncode == 0, result.stderr
    assert "Rollback SQL" in result.stdout
    assert "DROP INDEX IF EXISTS dal170d_uq_bbp_brokerage_profile" in result.stdout
    second = _run_migration("--dry-run", "--phase", "second-fks")
    assert second.returncode == 0, second.stderr
    assert "ALTER TABLE offers DROP CONSTRAINT IF EXISTS dal170d2_fk_offers_listing_tenant" in second.stdout


def test_no_rls_policies_are_created_by_dal170d_scripts():
    _ensure_parent_and_child_ddl()
    with SessionLocal() as db:
        policy_count = db.execute(
            text(
                """
                SELECT count(*)
                FROM pg_policies
                WHERE schemaname = current_schema()
                  AND policyname LIKE 'dal170d_%'
                """
            )
        ).scalar()
    assert int(policy_count or 0) == 0


def test_no_not_null_constraints_are_added_to_nullable_roots():
    _ensure_parent_and_child_ddl()
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT table_name, column_name, is_nullable
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND (table_name, column_name) IN (
                    ('listings', 'brokerage_id'),
                    ('conversations', 'brokerage_id'),
                    ('offer_records', 'brokerage_id'),
                    ('listing_inquiries', 'brokerage_id'),
                    ('suspicious_activity', 'brokerage_id'),
                    ('buyer_profiles', 'brokerage_id')
                  )
                """
            )
        ).mappings().all()
    assert rows
    assert {row["is_nullable"] for row in rows} == {"YES"}


def test_first_fks_remain_not_valid():
    ok, reason = _ensure_first_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    expected = {
        "dal170d_fk_bpf_profile_tenant",
        "dal170d_fk_offers_conversation_tenant",
        "dal170d_fk_draft_replies_conversation_tenant",
        "dal170d_fk_viewings_conversation_tenant",
        "dal170d_fk_media_assets_conversation_tenant",
    }
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT conname, convalidated
                FROM pg_constraint
                WHERE connamespace = current_schema()::regnamespace
                  AND conname = ANY(:names)
                """
            ),
            {"names": sorted(expected)},
        ).mappings().all()
    assert {row["conname"] for row in rows} == expected
    assert {row["convalidated"] for row in rows} == {False}


def test_second_fks_remain_not_valid():
    ok, reason = _ensure_second_fks_or_refusal()
    if not ok:
        assert "Preflight blockers" in reason
        return
    expected = {
        "dal170d2_fk_offers_listing_tenant",
        "dal170d2_fk_draft_replies_listing_tenant",
        "dal170d2_fk_viewings_listing_tenant",
        "dal170d2_fk_media_assets_listing_tenant",
    }
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT conname, convalidated
                FROM pg_constraint
                WHERE connamespace = current_schema()::regnamespace
                  AND conname = ANY(:names)
                """
            ),
            {"names": sorted(expected)},
        ).mappings().all()
    assert {row["conname"] for row in rows} == expected
    assert {row["convalidated"] for row in rows} == {False}
