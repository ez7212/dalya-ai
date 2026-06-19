from __future__ import annotations

from contextlib import contextmanager
import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageMember,
    DBHotlistRefreshRun,
    DBListing,
)


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
def brokerage_context_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_a = f"dal172-a-{suffix}"
    brokerage_b = f"dal172-b-{suffix}"
    single_user = f"dal172-single-{suffix}"
    multi_user = f"dal172-multi-{suffix}"
    agent_b = f"dal172-agent-b-{suffix}"
    inactive_user = f"dal172-inactive-{suffix}"
    zero_user = f"dal172-zero-{suffix}"
    listing_a = f"dal172-listing-a-{suffix}"

    with SessionLocal() as db:
        db.add_all(
            [
                DBBrokerage(
                    brokerage_id=brokerage_a,
                    name="DAL-172 Brokerage A",
                    slug=brokerage_a,
                    status="active",
                    brokerage_ai_number=f"+9715200{int(suffix, 16) % 10000:04d}",
                    agents_ai_number=f"+9715300{int(suffix, 16) % 10000:04d}",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerage(
                    brokerage_id=brokerage_b,
                    name="DAL-172 Brokerage B",
                    slug=brokerage_b,
                    status="active",
                    brokerage_ai_number=f"+9715400{int(suffix, 16) % 10000:04d}",
                    agents_ai_number=f"+9715500{int(suffix, 16) % 10000:04d}",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_a,
                    user_id=single_user,
                    role="agent",
                    status="active",
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
                    brokerage_id=brokerage_b,
                    user_id=agent_b,
                    role="agent",
                    status="active",
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_a,
                    user_id=inactive_user,
                    role="agent",
                    status="active",
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_b,
                    user_id=inactive_user,
                    role="agent",
                    status="inactive",
                ),
                DBAgentProfile(
                    brokerage_id=brokerage_a,
                    user_id=single_user,
                    full_name="DAL-172 Single",
                    display_name="DAL-172 Single",
                    whatsapp_phone=f"+9715600{int(suffix, 16) % 10000:04d}",
                    rera_broker_card_number=f"DAL172-S-{suffix}",
                    onboarding_status="active",
                ),
                DBAgentProfile(
                    brokerage_id=brokerage_a,
                    user_id=multi_user,
                    full_name="DAL-172 Multi A",
                    display_name="DAL-172 Multi A",
                    whatsapp_phone=f"+9715610{int(suffix, 16) % 10000:04d}",
                    rera_broker_card_number=f"DAL172-MA-{suffix}",
                    onboarding_status="active",
                ),
                DBAgentProfile(
                    brokerage_id=brokerage_b,
                    user_id=multi_user,
                    full_name="DAL-172 Multi B",
                    display_name="DAL-172 Multi B",
                    whatsapp_phone=f"+9715620{int(suffix, 16) % 10000:04d}",
                    rera_broker_card_number=f"DAL172-MB-{suffix}",
                    onboarding_status="active",
                ),
                DBListing(
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    assigned_agent_id=single_user,
                    spa_data={"project": "DAL-172 Tower", "unit_number": "172A"},
                    seller_asking_price=1_720_000,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=f"https://example.test/dal172/{suffix}",
                ),
            ]
        )
        safe_commit(db)

    yield {
        "brokerage_a": brokerage_a,
        "brokerage_b": brokerage_b,
        "agent_b": agent_b,
        "single_user": single_user,
        "multi_user": multi_user,
        "inactive_user": inactive_user,
        "zero_user": zero_user,
        "listing_a": listing_a,
    }

    with SessionLocal() as db:
        brokerage_ids = [brokerage_a, brokerage_b]
        db.query(DBHotlistRefreshRun).filter(DBHotlistRefreshRun.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
        db.query(DBListing).filter(DBListing.source_url.like(f"https://example.test/dal172-create/%{suffix}%")).delete(synchronize_session=False)
        db.query(DBListing).filter(DBListing.listing_id == listing_a).delete(synchronize_session=False)
        db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
        db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
        db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
        safe_commit(db)


def _detail_code(response) -> str:
    return response.json()["detail"]["code"]


def test_single_membership_without_header_uses_mvp_fallback(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["single_user"]):
        response = client.get("/api/v1/agent/dashboard")

    assert response.status_code == 200
    assert response.json()["brokerage"]["brokerage_id"] == brokerage_context_seed["brokerage_a"]


def test_multi_membership_without_header_fails_closed(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["multi_user"]):
        response = client.get("/api/v1/agent/dashboard")

    assert response.status_code == 409
    assert _detail_code(response) == "brokerage_context_required"


def test_multi_membership_with_valid_header_selects_requested_brokerage(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["multi_user"]):
        response = client.get(
            "/api/v1/agent/dashboard",
            headers={"X-Brokerage-Id": brokerage_context_seed["brokerage_b"]},
        )

    assert response.status_code == 200
    assert response.json()["brokerage"]["brokerage_id"] == brokerage_context_seed["brokerage_b"]
    assert response.json()["agent"]["role"] == "team_lead"


def test_invalid_brokerage_header_fails_forbidden(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["single_user"]):
        response = client.get(
            "/api/v1/agent/dashboard",
            headers={"X-Brokerage-Id": brokerage_context_seed["brokerage_b"]},
        )

    assert response.status_code == 403
    assert _detail_code(response) == "brokerage_context_forbidden"


def test_inactive_brokerage_membership_header_fails_forbidden(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["inactive_user"]):
        response = client.get(
            "/api/v1/agent/dashboard",
            headers={"X-Brokerage-Id": brokerage_context_seed["brokerage_b"]},
        )

    assert response.status_code == 403
    assert _detail_code(response) == "brokerage_context_forbidden"


def test_zero_active_memberships_fail_closed(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["zero_user"]):
        response = client.get("/api/v1/agent/dashboard")

    assert response.status_code == 403
    assert _detail_code(response) == "no_active_brokerage_membership"


def test_me_brokerages_returns_safe_active_membership_inventory(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["multi_user"]):
        response = client.get("/api/v1/me/brokerages")

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_selection"] is True
    assert payload["default_brokerage_id"] is None
    brokerage_ids = {row["brokerage_id"] for row in payload["active_brokerages"]}
    assert brokerage_ids == {
        brokerage_context_seed["brokerage_a"],
        brokerage_context_seed["brokerage_b"],
    }
    assert all({"brokerage_id", "name", "role", "membership_id"} <= set(row) for row in payload["active_brokerages"])


def test_onboarding_me_does_not_choose_first_brokerage_for_multi_membership_user(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["multi_user"]):
        response = client.get("/api/v1/onboarding/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_selection"] is True
    assert payload["default_brokerage_id"] is None
    assert payload["brokerage"] is None
    assert payload["can_access_agent_workspace"] is False
    brokerage_ids = {row["brokerage_id"] for row in payload["active_brokerages"]}
    assert brokerage_ids == {
        brokerage_context_seed["brokerage_a"],
        brokerage_context_seed["brokerage_b"],
    }


def test_onboarding_me_respects_explicit_brokerage_context(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["multi_user"]):
        response = client.get(
            "/api/v1/onboarding/me",
            headers={"X-Brokerage-Id": brokerage_context_seed["brokerage_b"]},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_selection"] is False
    assert payload["brokerage"]["brokerage_id"] == brokerage_context_seed["brokerage_b"]
    assert payload["role"] == "team_lead"
    assert payload["can_access_agent_workspace"] is True


def test_onboarding_me_rejects_invalid_explicit_brokerage_context(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["single_user"]):
        response = client.get(
            "/api/v1/onboarding/me",
            headers={"X-Brokerage-Id": brokerage_context_seed["brokerage_b"]},
        )

    assert response.status_code == 403
    assert _detail_code(response) == "brokerage_context_forbidden"


def test_spa_parse_requires_explicit_context_for_multi_membership_user(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["multi_user"]):
        response = client.post(
            "/api/v1/parse-spa",
            files={"file": ("spa.pdf", b"%PDF-1.4\n", "application/pdf")},
        )

    assert response.status_code == 409
    assert _detail_code(response) == "brokerage_context_required"


def test_listing_knowledge_requires_explicit_context_for_multi_membership_user(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["multi_user"]):
        response = client.get(f"/api/v1/listings/{brokerage_context_seed['listing_a']}/knowledge")

    assert response.status_code == 409
    assert _detail_code(response) == "brokerage_context_required"


def test_listing_knowledge_respects_explicit_context(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["multi_user"]):
        response = client.get(
            f"/api/v1/listings/{brokerage_context_seed['listing_a']}/knowledge",
            headers={"X-Brokerage-Id": brokerage_context_seed["brokerage_a"]},
        )

    assert response.status_code == 200
    assert response.json()["listing_id"] == brokerage_context_seed["listing_a"]


def _listing_payload(seed: dict, *, managing_agent_user_id: str | None = None) -> dict:
    payload = {
        "property_type": "ready",
        "listing_title": "DAL-172 Test Listing",
        "building_or_project": "DAL-172 Tower",
        "unit_number": "172",
        "asking_price_aed": 1_720_000,
        "commission_rate": 0.02,
        "source_url": f"https://example.test/dal172-create/{seed['listing_a']}",
    }
    if managing_agent_user_id:
        payload["managing_agent_user_id"] = managing_agent_user_id
    return payload


def test_listing_creation_allows_self_assignment(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["single_user"]):
        response = client.post(
            "/api/v1/listings",
            json=_listing_payload(brokerage_context_seed),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["brokerage_id"] == brokerage_context_seed["brokerage_a"]
    assert payload["managing_agent_user_id"] == brokerage_context_seed["single_user"]


def test_listing_creation_allows_manager_assigning_same_brokerage_agent(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["multi_user"]):
        response = client.post(
            "/api/v1/listings",
            headers={"X-Brokerage-Id": brokerage_context_seed["brokerage_b"]},
            json=_listing_payload(
                brokerage_context_seed,
                managing_agent_user_id=brokerage_context_seed["agent_b"],
            ),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["brokerage_id"] == brokerage_context_seed["brokerage_b"]
    assert payload["managing_agent_user_id"] == brokerage_context_seed["agent_b"]


def test_listing_creation_blocks_non_manager_assigning_another_agent(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["single_user"]):
        response = client.post(
            "/api/v1/listings",
            json=_listing_payload(
                brokerage_context_seed,
                managing_agent_user_id=brokerage_context_seed["multi_user"],
            ),
        )

    assert response.status_code == 403
    assert "Managing-agent access required" in response.json()["detail"]


def test_listing_creation_blocks_cross_brokerage_managing_agent(client, brokerage_context_seed):
    with _as_user(brokerage_context_seed["multi_user"]):
        response = client.post(
            "/api/v1/listings",
            headers={"X-Brokerage-Id": brokerage_context_seed["brokerage_b"]},
            json=_listing_payload(
                brokerage_context_seed,
                managing_agent_user_id=brokerage_context_seed["single_user"],
            ),
        )

    assert response.status_code == 403
    assert "active member" in response.json()["detail"]
