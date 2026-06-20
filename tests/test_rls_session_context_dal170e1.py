from __future__ import annotations

from contextlib import contextmanager
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.auth import CurrentUser, get_current_user
from app.core.brokerage_access import resolve_request_brokerage_context
from app.core.lead_ingest import ingest_lead_email
from app.db.session import (
    SessionLocal,
    clear_db_session_context,
    engine,
    safe_commit,
    set_db_session_context,
)
from app.main import app
from app.models.db_models import (
    DBAgentNotification,
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageBuyerProfile,
    DBBrokerageMember,
    DBBuyerProfileField,
    DBComplianceEvent,
    DBConversation,
    DBLeadAssignment,
    DBLeadAction,
    DBLeadTask,
    DBLeadIngestRecord,
    DBListing,
    DBMessage,
)
from scripts.rls_rehearsal_dal170e1 import (
    APPLY_SQL,
    ROLLBACK_SQL,
    RUNTIME_ROLE,
    _assert_rehearsal_mutation_allowed,
    apply_sql_text,
    main as rls_rehearsal_main,
    rollback_sql_text,
)


def _execute_statements(statements: list[str]) -> None:
    with engine.begin() as conn:
        for statement in statements:
            if statement.strip():
                conn.execute(text(statement))


@contextmanager
def _runtime_connection(*, user_id: str | None = None, brokerage_id: str | None = None):
    with engine.connect() as conn:
        trans = conn.begin()
        conn.execute(text(f"set local role {RUNTIME_ROLE}"))
        if user_id is not None:
            conn.execute(
                text("select set_config('app.user_id', :value, true)"),
                {"value": user_id},
            )
        if brokerage_id is not None:
            conn.execute(
                text("select set_config('app.brokerage_id', :value, true)"),
                {"value": brokerage_id},
            )
        try:
            yield conn
        finally:
            trans.rollback()


@contextmanager
def _as_user(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id,
        email=f"{user_id}@example.com",
    )
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def _set_rehearsal_env(monkeypatch, *, dalya_env: str | None = "test", database_url: str | None = None) -> None:
    monkeypatch.setenv("DALYA_ALLOW_RLS_REHEARSAL_MUTATION", "1")
    monkeypatch.setenv("PROD_DB_HOST", "prod-db.example.com")
    if dalya_env is None:
        monkeypatch.delenv("DALYA_ENV", raising=False)
    else:
        monkeypatch.setenv("DALYA_ENV", dalya_env)
    if database_url is None:
        database_url = "postgresql://dalya_test_user:secret@test-db.local/dalya_test"
    monkeypatch.setenv("DATABASE_URL", database_url)


@pytest.mark.parametrize("dalya_env", ["production", "prod", "staging", "stage", "preview", "live", "qa", None])
def test_rehearsal_mutation_refuses_live_missing_or_unknown_env(monkeypatch, dalya_env):
    _set_rehearsal_env(monkeypatch, dalya_env=dalya_env)

    with pytest.raises(SystemExit):
        _assert_rehearsal_mutation_allowed(allow_rehearsal_mutation=True)


def test_rehearsal_mutation_requires_explicit_approval(monkeypatch):
    _set_rehearsal_env(monkeypatch)
    monkeypatch.delenv("DALYA_ALLOW_RLS_REHEARSAL_MUTATION", raising=False)

    with pytest.raises(SystemExit):
        _assert_rehearsal_mutation_allowed()


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://dalya_test_user:secret@prod-db.example.com/dalya_test",
        "postgresql://dalya_test_user:secret@rehearsal-prod.example.com/dalya_test",
        "postgresql://dalya_test_user:secret@test-db.local/dalya_staging",
        "postgresql://prod_user:secret@test-db.local/dalya_test",
    ],
)
def test_rehearsal_mutation_refuses_production_like_database_identity(monkeypatch, database_url):
    _set_rehearsal_env(monkeypatch, database_url=database_url)

    with pytest.raises(SystemExit):
        _assert_rehearsal_mutation_allowed(allow_rehearsal_mutation=True)


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "not-a-url",
        "postgresql:///dalya_test",
    ],
)
def test_rehearsal_mutation_refuses_missing_or_ambiguous_database_identity(monkeypatch, database_url):
    _set_rehearsal_env(monkeypatch, database_url=database_url)

    with pytest.raises(SystemExit):
        _assert_rehearsal_mutation_allowed(allow_rehearsal_mutation=True)


def test_rehearsal_dry_run_sql_is_available_without_mutation_env(monkeypatch):
    monkeypatch.delenv("DALYA_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DALYA_ALLOW_RLS_REHEARSAL_MUTATION", raising=False)

    assert "create policy dal170e1_listings_tenant" in apply_sql_text()
    assert "drop policy if exists dal170e1_listings_tenant" in rollback_sql_text()


@pytest.mark.parametrize("mode", ["--apply", "--rollback"])
def test_rehearsal_apply_and_rollback_cli_are_gated(monkeypatch, mode):
    _set_rehearsal_env(monkeypatch)
    monkeypatch.delenv("DALYA_ALLOW_RLS_REHEARSAL_MUTATION", raising=False)
    monkeypatch.setattr("sys.argv", ["rls_rehearsal_dal170e1.py", mode])

    with pytest.raises(SystemExit):
        rls_rehearsal_main()


@pytest.fixture
def rls_seed():
    suffix = uuid.uuid4().hex[:8]
    prefix = f"dal170e1-{suffix}"
    brokerage_a = f"{prefix}-a"
    brokerage_b = f"{prefix}-b"
    multi_user = f"{prefix}-multi"
    single_user = f"{prefix}-single"
    listing_a = f"{prefix}-listing-a"
    listing_b = f"{prefix}-listing-b"
    conversation_a = f"{prefix}-conversation-a"
    conversation_b = f"{prefix}-conversation-b"
    profile_a = f"{prefix}-profile-a"
    profile_b = f"{prefix}-profile-b"
    portal_phone = f"+97158{int(suffix, 16) % 10000000:07d}"
    source_url = f"https://www.propertyfinder.ae/en/plp/buy/villa-for-sale-dal170e1-{suffix}"

    _execute_statements(ROLLBACK_SQL)
    with SessionLocal() as db:
        db.add_all(
            [
                DBBrokerage(
                    brokerage_id=brokerage_a,
                    name="DAL-170E1 Brokerage A",
                    slug=brokerage_a,
                    status="active",
                    brokerage_ai_number=f"+9715201{int(suffix, 16) % 10000:04d}",
                    agents_ai_number=f"+9715301{int(suffix, 16) % 10000:04d}",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerage(
                    brokerage_id=brokerage_b,
                    name="DAL-170E1 Brokerage B",
                    slug=brokerage_b,
                    status="active",
                    brokerage_ai_number=f"+9715401{int(suffix, 16) % 10000:04d}",
                    agents_ai_number=f"+9715501{int(suffix, 16) % 10000:04d}",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_a,
                    user_id=multi_user,
                    role="agent",
                    status="active",
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_b,
                    user_id=multi_user,
                    role="team_lead",
                    status="active",
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_a,
                    user_id=single_user,
                    role="agent",
                    status="active",
                ),
                DBAgentProfile(
                    brokerage_id=brokerage_a,
                    user_id=single_user,
                    full_name="DAL-170E1 Single",
                    display_name="DAL-170E1 Single",
                    whatsapp_phone=f"+9715601{int(suffix, 16) % 10000:04d}",
                    rera_broker_card_number=f"DAL170E1-S-{suffix}",
                    onboarding_status="active",
                ),
                DBAgentProfile(
                    brokerage_id=brokerage_b,
                    user_id=multi_user,
                    full_name="DAL-170E1 Multi",
                    display_name="DAL-170E1 Multi",
                    whatsapp_phone=f"+9715602{int(suffix, 16) % 10000:04d}",
                    rera_broker_card_number=f"DAL170E1-M-{suffix}",
                    onboarding_status="active",
                ),
                DBListing(
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    spa_data={"project": "DAL-170E1 A", "unit_number": "A"},
                    seller_asking_price=1_700_001,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=source_url,
                ),
                DBListing(
                    listing_id=listing_b,
                    brokerage_id=brokerage_b,
                    spa_data={"project": "DAL-170E1 B", "unit_number": "B"},
                    seller_asking_price=1_700_002,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=f"https://example.test/{listing_b}",
                ),
                DBConversation(
                    conversation_id=conversation_a,
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    buyer_phone=f"+97150{int(suffix, 16) % 10000000:07d}",
                    buyer_name="Buyer A",
                ),
                DBConversation(
                    conversation_id=conversation_b,
                    listing_id=listing_b,
                    brokerage_id=brokerage_b,
                    buyer_phone=f"+97151{int(suffix, 16) % 10000000:07d}",
                    buyer_name="Buyer B",
                ),
                DBBrokerageBuyerProfile(
                    profile_id=profile_a,
                    brokerage_id=brokerage_a,
                    buyer_phone=f"+97152{int(suffix, 16) % 10000000:07d}",
                    name="Profile A",
                    source="test",
                ),
                DBBrokerageBuyerProfile(
                    profile_id=profile_b,
                    brokerage_id=brokerage_b,
                    buyer_phone=f"+97153{int(suffix, 16) % 10000000:07d}",
                    name="Profile B",
                    source="test",
                ),
                DBBuyerProfileField(
                    profile_id=profile_a,
                    brokerage_id=brokerage_a,
                    field="timeline",
                    value={"value": "now"},
                    provenance="agent_confirmed",
                ),
                DBBuyerProfileField(
                    profile_id=profile_b,
                    brokerage_id=brokerage_b,
                    field="timeline",
                    value={"value": "later"},
                    provenance="agent_confirmed",
                ),
            ]
        )
        safe_commit(db)

    _execute_statements(APPLY_SQL)
    yield {
        "prefix": prefix,
        "brokerage_a": brokerage_a,
        "brokerage_b": brokerage_b,
        "multi_user": multi_user,
        "single_user": single_user,
        "listing_a": listing_a,
        "listing_b": listing_b,
        "conversation_a": conversation_a,
        "conversation_b": conversation_b,
        "profile_a": profile_a,
        "profile_b": profile_b,
        "portal_phone": portal_phone,
        "source_url": source_url,
    }

    _execute_statements(ROLLBACK_SQL)
    with SessionLocal() as db:
        conversation_ids = [
            row[0]
            for row in db.query(DBConversation.conversation_id)
            .filter(DBConversation.brokerage_id.in_([brokerage_a, brokerage_b]))
            .all()
        ]
        db.query(DBAgentNotification).filter(DBAgentNotification.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBLeadTask).filter(DBLeadTask.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBLeadAction).filter(DBLeadAction.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBLeadAssignment).filter(DBLeadAssignment.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        if conversation_ids:
            db.query(DBMessage).filter(DBMessage.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBLeadIngestRecord).filter(DBLeadIngestRecord.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBBuyerProfileField).filter(DBBuyerProfileField.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBBrokerageBuyerProfile).filter(DBBrokerageBuyerProfile.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBConversation).filter(DBConversation.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBListing).filter(DBListing.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        safe_commit(db)


def test_no_brokerage_context_hides_protected_tenant_rows(rls_seed):
    with _runtime_connection() as conn:
        listing_ids = conn.execute(
            text("select listing_id from listings where listing_id in (:listing_a, :listing_b)"),
            {"listing_a": rls_seed["listing_a"], "listing_b": rls_seed["listing_b"]},
        ).fetchall()
    assert listing_ids == []


def test_brokerage_context_cannot_read_other_brokerage_rows(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        listing_ids = {
            row[0]
            for row in conn.execute(
                text("select listing_id from listings where listing_id in (:listing_a, :listing_b)"),
                {"listing_a": rls_seed["listing_a"], "listing_b": rls_seed["listing_b"]},
            ).fetchall()
        }
        profile_ids = {
            row[0]
            for row in conn.execute(
                text("select profile_id from brokerage_buyer_profiles where profile_id in (:profile_a, :profile_b)"),
                {"profile_a": rls_seed["profile_a"], "profile_b": rls_seed["profile_b"]},
            ).fetchall()
        }

    assert listing_ids == {rls_seed["listing_a"]}
    assert profile_ids == {rls_seed["profile_a"]}


def test_mismatched_tenant_insert_fails_with_selected_context(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        with pytest.raises(DBAPIError):
            conn.execute(
                text(
                    """
                    insert into listings (listing_id, brokerage_id, spa_data, commission_rate)
                    values (:listing_id, :brokerage_id, '{"project": "Bad Insert"}'::jsonb, 0.02)
                    """
                ),
                {
                    "listing_id": f"{rls_seed['prefix']}-bad-insert",
                    "brokerage_id": rls_seed["brokerage_b"],
                },
            )


def test_mismatched_tenant_update_fails_with_selected_context(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        with pytest.raises(DBAPIError):
            conn.execute(
                text("update listings set brokerage_id = :brokerage_b where listing_id = :listing_a"),
                {
                    "brokerage_b": rls_seed["brokerage_b"],
                    "listing_a": rls_seed["listing_a"],
                },
            )


def test_pooled_sessions_do_not_leak_brokerage_context(rls_seed):
    with SessionLocal() as db:
        set_db_session_context(db, brokerage_id=rls_seed["brokerage_a"])
        assert db.execute(text("select app.current_brokerage_id()")).scalar() == rls_seed["brokerage_a"]
        safe_commit(db)

    with SessionLocal() as db:
        clear_db_session_context(db)
        assert db.execute(text("select app.current_brokerage_id()")).scalar() is None


def test_set_local_context_reapplies_after_safe_commit(rls_seed):
    with SessionLocal() as db:
        set_db_session_context(db, brokerage_id=rls_seed["brokerage_a"])
        assert db.execute(text("select app.current_brokerage_id()")).scalar() == rls_seed["brokerage_a"]
        safe_commit(db)
        assert db.execute(text("select app.current_brokerage_id()")).scalar() == rls_seed["brokerage_a"]
        assert db.get(DBListing, rls_seed["listing_a"]) is not None


def test_me_brokerages_works_with_user_context_and_no_selected_brokerage(client, rls_seed):
    with _as_user(rls_seed["multi_user"]):
        response = client.get("/api/v1/me/brokerages")

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_selection"] is True
    assert {row["brokerage_id"] for row in payload["active_brokerages"]} == {
        rls_seed["brokerage_a"],
        rls_seed["brokerage_b"],
    }


def test_dal172_selected_route_still_sets_brokerage_context(client, rls_seed):
    with _as_user(rls_seed["multi_user"]):
        missing = client.get("/api/v1/agent/dashboard")
        selected = client.get(
            "/api/v1/agent/dashboard",
            headers={"X-Brokerage-Id": rls_seed["brokerage_b"]},
        )

    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "brokerage_context_required"
    assert selected.status_code == 200
    assert selected.json()["brokerage"]["brokerage_id"] == rls_seed["brokerage_b"]


def test_admin_user_normal_route_does_not_seed_platform_admin_bypass(monkeypatch, rls_seed):
    monkeypatch.setenv("ADMIN_USER_ID", rls_seed["multi_user"])
    with SessionLocal() as db:
        context = resolve_request_brokerage_context(
            db,
            CurrentUser(id=rls_seed["multi_user"], email="admin@example.com"),
            rls_seed["brokerage_a"],
            allow_platform_admin=False,
        )
        is_platform_admin = db.execute(text("select app.is_platform_admin()")).scalar()

    assert context.brokerage_id == rls_seed["brokerage_a"]
    assert context.is_platform_admin is False
    assert is_platform_admin is False


def test_platform_admin_bypass_requires_explicit_opt_in(monkeypatch, rls_seed):
    platform_user = f"{rls_seed['prefix']}-platform-admin"
    monkeypatch.setenv("ADMIN_USER_ID", platform_user)
    with SessionLocal() as db:
        context = resolve_request_brokerage_context(
            db,
            CurrentUser(id=platform_user, email="platform@example.com"),
            rls_seed["brokerage_a"],
            allow_platform_admin=True,
        )
        is_platform_admin = db.execute(text("select app.is_platform_admin()")).scalar()

    assert context.brokerage_id == rls_seed["brokerage_a"]
    assert context.role == "platform_admin"
    assert context.is_platform_admin is True
    assert is_platform_admin is True


def test_lead_ingest_sets_explicit_service_context(monkeypatch, rls_seed):
    sent_messages: list[dict] = []

    def fake_send_whatsapp_reply(to_number, body, **kwargs):
        sent_messages.append({"to": to_number, "body": body, **kwargs})

    monkeypatch.setattr("app.api.whatsapp.send_whatsapp_reply", fake_send_whatsapp_reply)

    payload = {
        "subject": "Property Finder lead",
        "body": (
            "Source: propertyfinder\n"
            "Name: DAL 170E Buyer\n"
            f"Phone: {rls_seed['portal_phone']}\n"
            "Message: I would like to view this property.\n"
            f"{rls_seed['source_url']}\n"
        ),
    }
    with SessionLocal() as db:
        outcome = ingest_lead_email(
            db,
            to_address=f"leads+{rls_seed['brokerage_a']}@example.test",
            payload=payload,
        )
        assert outcome.status == "ingested"
        assert outcome.conversation_id is not None
        context_brokerage = db.execute(text("select app.current_brokerage_id()")).scalar()
        context_service = db.execute(text("select app.is_service()")).scalar()
        profile = (
            db.query(DBBrokerageBuyerProfile)
            .filter(
                DBBrokerageBuyerProfile.brokerage_id == rls_seed["brokerage_a"],
                DBBrokerageBuyerProfile.buyer_phone == rls_seed["portal_phone"],
            )
            .one()
        )

    assert context_brokerage == rls_seed["brokerage_a"]
    assert context_service is True
    assert profile.source == "portal"
    assert sent_messages
