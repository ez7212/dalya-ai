from __future__ import annotations

from contextlib import contextmanager
import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import DBAgentProfile, DBBrokerage, DBBrokerageMember


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


@pytest.fixture
def multi_brokerage_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_a = f"dal172-tenant-a-{suffix}"
    brokerage_b = f"dal172-tenant-b-{suffix}"
    user_id = f"dal172-tenant-multi-{suffix}"

    with SessionLocal() as db:
        db.add_all(
            [
                DBBrokerage(
                    brokerage_id=brokerage_a,
                    name="DAL-172 Tenant Brokerage A",
                    slug=brokerage_a,
                    status="active",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerage(
                    brokerage_id=brokerage_b,
                    name="DAL-172 Tenant Brokerage B",
                    slug=brokerage_b,
                    status="active",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_a,
                    user_id=user_id,
                    role="agent",
                    status="active",
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_b,
                    user_id=user_id,
                    role="agent",
                    status="active",
                ),
                DBAgentProfile(
                    brokerage_id=brokerage_a,
                    user_id=user_id,
                    full_name="DAL-172 Multi Tenant A",
                    display_name="DAL-172 Multi A",
                    whatsapp_phone=f"+9715600{int(suffix, 16) % 10000:04d}",
                    rera_broker_card_number=f"DAL172-TA-{suffix}",
                    onboarding_status="active",
                ),
                DBAgentProfile(
                    brokerage_id=brokerage_b,
                    user_id=user_id,
                    full_name="DAL-172 Multi Tenant B",
                    display_name="DAL-172 Multi B",
                    whatsapp_phone=f"+9715610{int(suffix, 16) % 10000:04d}",
                    rera_broker_card_number=f"DAL172-TB-{suffix}",
                    onboarding_status="active",
                ),
            ]
        )
        safe_commit(db)

    yield {
        "brokerage_a": brokerage_a,
        "brokerage_b": brokerage_b,
        "user_id": user_id,
    }

    with SessionLocal() as db:
        brokerage_ids = [brokerage_a, brokerage_b]
        db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
        db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
        db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
        safe_commit(db)


def test_multi_brokerage_user_without_explicit_context_fails_closed(client, multi_brokerage_seed):
    with _as_user(multi_brokerage_seed["user_id"]):
        response = client.get("/api/v1/agent/dashboard")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "brokerage_context_required"


def test_multi_brokerage_user_with_explicit_context_succeeds(client, multi_brokerage_seed):
    with _as_user(multi_brokerage_seed["user_id"]):
        response = client.get(
            "/api/v1/agent/dashboard",
            headers={"X-Brokerage-Id": multi_brokerage_seed["brokerage_b"]},
        )

    assert response.status_code == 200
    assert response.json()["brokerage"]["brokerage_id"] == multi_brokerage_seed["brokerage_b"]
