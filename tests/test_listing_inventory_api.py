from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageMember,
    DBConversation,
    DBListing,
    DBListingKnowledgeSummary,
    DBMessage,
    DBOfferRecord,
    DBViewing,
)

LEAN_LISTING_KEYS = (
    "id title property_type community subcommunity building_or_project unit_number bedrooms bathrooms size_sqft asking_price_aed "
    "price_per_sqft_aed status lead_count escalated_count source_url first_image_url reference_document_count created_at last_activity_at "
    "assigned_agent_name knowledge_status missing_fact_count active_viewing_count open_offer_count buyer_conversation_count logistics_status primary_next_action"
).split()


@contextmanager
def _as_user(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=user_id, email=f"{user_id}@example.com")
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def _brokerage(brokerage_id: str, name: str) -> DBBrokerage:
    return DBBrokerage(brokerage_id=brokerage_id, name=name, slug=brokerage_id, status="active", settings={"legacy_telegram_alerts": False})


def _member(brokerage_id: str, user_id: str, display_name: str | None = None) -> DBBrokerageMember:
    return DBBrokerageMember(brokerage_id=brokerage_id, user_id=user_id, display_name=display_name, role="agent", status="active")


def _profile(brokerage_id: str, user_id: str, display_name: str) -> DBAgentProfile:
    phone_suffix = sum(ord(char) for char in brokerage_id + user_id) % 10_000_000
    card_token = f"{brokerage_id[-8:]}-{user_id[-8:]}"
    return DBAgentProfile(
        brokerage_id=brokerage_id,
        user_id=user_id,
        full_name=display_name,
        display_name=display_name,
        whatsapp_phone=f"+97158{phone_suffix:07d}",
        rera_broker_card_number=f"T-{card_token}",
        onboarding_status="active",
    )


def _delete_listing_records(db, listing_ids: list[str], conversation_id: str | None) -> None:
    db.query(DBViewing).filter(DBViewing.listing_id.in_(listing_ids)).delete(synchronize_session=False)
    db.query(DBOfferRecord).filter(DBOfferRecord.listing_id.in_(listing_ids)).delete(synchronize_session=False)
    db.query(DBListingKnowledgeSummary).filter(DBListingKnowledgeSummary.listing_id.in_(listing_ids)).delete(synchronize_session=False)
    if conversation_id:
        db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id).delete(synchronize_session=False)
        db.query(DBConversation).filter(DBConversation.conversation_id == conversation_id).delete(synchronize_session=False)
    db.query(DBListing).filter(DBListing.listing_id.in_(listing_ids)).delete(synchronize_session=False)


def _delete_brokerages(db, brokerage_ids: list[str]) -> None:
    db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
    db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
    db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)


def _detail_code(response) -> str:
    return response.json()["detail"]["code"]


def _listing_ids(response) -> set[str]:
    return {item["id"] for item in response.json()["listings"]}


def _listing_by_id(response, listing_id: str):
    return next(item for item in response.json()["listings"] if item["id"] == listing_id)


@pytest.fixture
def inventory_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"t3-brokerage-{suffix}"
    assigned_agent = f"t3-agent-{suffix}"
    other_agent = f"t3-other-{suffix}"
    listing_id = f"t3-listing-{suffix}"
    hidden_listing_id = f"t3-hidden-{suffix}"
    conversation_id = f"t3-conversation-{suffix}"
    now = datetime.now(UTC).replace(tzinfo=None)
    buyer_phone = f"+971501{int(suffix, 16) % 100000:05d}"

    with SessionLocal() as db:
        db.add_all([
            _brokerage(brokerage_id, "T3 Brokerage"),
            _member(brokerage_id, assigned_agent, "Assigned Inventory Agent"),
            _member(brokerage_id, other_agent, "Other Inventory Agent"),
            _profile(brokerage_id, assigned_agent, "Assigned Inventory Agent"),
            DBListing(
                listing_id=listing_id,
                brokerage_id=brokerage_id,
                assigned_agent_id=assigned_agent,
                seller_id=assigned_agent,
                spa_data={"project": "T3 Ready Tower", "unit_number": "T3-101", "property_type": "Apartment", "imported_listing": {"title": "T3 Missing Knowledge Ready Unit", "community": "Business Bay", "size_sqft": 1200}},
                seller_asking_price=2_400_000,
                commission_rate=0.02,
                property_type="ready",
                community="Business Bay",
                source_url=f"https://example.test/t3/{suffix}",
                created_at=now - timedelta(days=2),
            ),
            DBListing(listing_id=hidden_listing_id, brokerage_id=brokerage_id, assigned_agent_id=other_agent, seller_id=other_agent, spa_data={"project": "T3 Hidden Tower", "unit_number": "T3-999"}, seller_asking_price=9_900_000, commission_rate=0.02, property_type="ready", source_url=f"https://example.test/t3/hidden/{suffix}", created_at=now - timedelta(days=1)),
            DBConversation(conversation_id=conversation_id, listing_id=listing_id, brokerage_id=brokerage_id, assigned_agent_id=assigned_agent, buyer_phone=buyer_phone, buyer_name="T3 Buyer", escalation_triggered=True, created_at=now - timedelta(hours=3), updated_at=now - timedelta(hours=1)),
            DBMessage(conversation_id=conversation_id, role="user", content="Can I view this ready unit?", timestamp=now - timedelta(hours=1)),
            DBListingKnowledgeSummary(brokerage_id=brokerage_id, listing_id=listing_id, buyer_safe_summary=None, missing_information=[{"fact_group": "viewing", "label": "Access instructions"}], risk_flags=[], status="needs_review", updated_at=now - timedelta(minutes=30)),
        ])
        safe_commit(db)
        db.add_all([
            DBOfferRecord(brokerage_id=brokerage_id, listing_id=listing_id, conversation_id=conversation_id, buyer_phone=buyer_phone, offer_amount_aed=2_250_000, asking_price_aed=2_400_000, gap_pct=6.25, above_threshold=True, escalated=True, created_at=now - timedelta(minutes=20)),
            DBViewing(brokerage_id=brokerage_id, listing_id=listing_id, conversation_id=conversation_id, buyer_phone=buyer_phone, agent_user_id=assigned_agent, status="proposed", created_at=now - timedelta(minutes=10), updated_at=now - timedelta(minutes=5)),
        ])
        safe_commit(db)

    yield {
        "assigned_agent": assigned_agent,
        "listing_id": listing_id,
        "hidden_listing_id": hidden_listing_id,
        "expected_last_activity_at": (now - timedelta(minutes=5)).isoformat(),
    }

    with SessionLocal() as db:
        _delete_listing_records(db, [listing_id, hidden_listing_id], conversation_id)
        _delete_brokerages(db, [brokerage_id])
        safe_commit(db)


@pytest.fixture
def multi_brokerage_inventory_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_a = f"t9-inventory-a-{suffix}"
    brokerage_b = f"t9-inventory-b-{suffix}"
    user_id = f"t9-inventory-user-{suffix}"
    listing_a = f"t9-listing-a-{suffix}"
    listing_b = f"t9-listing-b-{suffix}"
    now = datetime.now(UTC).replace(tzinfo=None)

    with SessionLocal() as db:
        db.add_all([
            _brokerage(brokerage_a, "T9 Inventory Brokerage A"),
            _brokerage(brokerage_b, "T9 Inventory Brokerage B"),
            _member(brokerage_a, user_id, "T9 Multi Agent A"),
            _member(brokerage_b, user_id, "T9 Multi Agent B"),
            _profile(brokerage_a, user_id, "T9 Multi Agent A"),
            _profile(brokerage_b, user_id, "T9 Multi Agent B"),
            DBListing(listing_id=listing_a, brokerage_id=brokerage_a, assigned_agent_id=user_id, seller_id=user_id, spa_data={"project": "T9 Brokerage A Tower", "unit_number": "A-901"}, seller_asking_price=1_900_000, commission_rate=0.02, property_type="ready", source_url=f"https://example.test/t9/a/{suffix}", created_at=now - timedelta(days=4)),
            DBListing(listing_id=listing_b, brokerage_id=brokerage_b, assigned_agent_id=user_id, seller_id=user_id, spa_data={"project": "T9 Brokerage B Tower", "unit_number": "B-901"}, seller_asking_price=2_900_000, commission_rate=0.02, property_type="ready", source_url=f"https://example.test/t9/b/{suffix}", created_at=now - timedelta(days=3)),
        ])
        safe_commit(db)

    yield {"brokerage_b": brokerage_b, "user_id": user_id, "listing_b": listing_b}

    with SessionLocal() as db:
        _delete_listing_records(db, [listing_a, listing_b], None)
        _delete_brokerages(db, [brokerage_a, brokerage_b])
        safe_commit(db)


def test_my_listings_flags_missing_knowledge_and_logistics_for_attention(client, inventory_seed):
    # Given: a ready listing has buyer activity, an offer, a viewing, missing buyer-safe knowledge, and no logistics.
    with _as_user(inventory_seed["assigned_agent"]):
        # When: the assigned agent loads their inventory index.
        response = client.get("/api/v1/listings/mine")

    # Then: the lean response exposes only index-level health fields and routes attention to knowledge review.
    assert response.status_code == 200
    listing = _listing_by_id(response, inventory_seed["listing_id"])
    assert set(listing) == set(LEAN_LISTING_KEYS)
    assert listing["title"] == "T3 Missing Knowledge Ready Unit"
    assert listing["status"] == "live"
    assert listing["asking_price_aed"] == 2_400_000
    assert listing["assigned_agent_name"] == "Assigned Inventory Agent"
    assert listing["knowledge_status"] == "needs_attention"
    assert listing["missing_fact_count"] == 1
    assert listing["logistics_status"] == "needs_attention"
    assert listing["primary_next_action"] == "review_knowledge"
    assert listing["buyer_conversation_count"] == 1
    assert listing["active_viewing_count"] == 1
    assert listing["open_offer_count"] == 1
    assert listing["last_activity_at"] == inventory_seed["expected_last_activity_at"]


def test_my_listings_routes_ready_knowledge_missing_logistics_to_set_logistics(client):
    # Given: a ready listing has buyer-safe knowledge ready, but no ready-property logistics record.
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"t9-logistics-{suffix}"
    user_id = f"t9-logistics-agent-{suffix}"
    listing_id = f"t9-logistics-listing-{suffix}"
    with SessionLocal() as db:
        db.add_all([
            _brokerage(brokerage_id, "T9 Logistics Brokerage"),
            _member(brokerage_id, user_id, "T9 Logistics Agent"),
            _profile(brokerage_id, user_id, "T9 Logistics Agent"),
            DBListing(listing_id=listing_id, brokerage_id=brokerage_id, assigned_agent_id=user_id, seller_id=user_id, spa_data={"project": "T9 Logistics Tower", "unit_number": "L-901", "imported_listing": {"title": "T9 Logistics Ready Unit"}}, seller_asking_price=3_100_000, commission_rate=0.02, property_type="ready", source_url=f"https://example.test/t9/logistics/{suffix}"),
            DBListingKnowledgeSummary(brokerage_id=brokerage_id, listing_id=listing_id, buyer_safe_summary="Buyer-safe facts are ready.", missing_information=[], risk_flags=[], status="ready"),
        ])
        safe_commit(db)

    try:
        with _as_user(user_id):
            # When: the assigned agent loads their inventory index.
            response = client.get("/api/v1/listings/mine")

        # Then: logistics becomes the primary next action and the row stays lean.
        assert response.status_code == 200
        listing = _listing_by_id(response, listing_id)
        assert set(listing) == set(LEAN_LISTING_KEYS)
        assert listing["knowledge_status"] == "ready"
        assert listing["missing_fact_count"] == 0
        assert listing["logistics_status"] == "needs_attention"
        assert listing["primary_next_action"] == "set_logistics"
    finally:
        with SessionLocal() as db:
            _delete_listing_records(db, [listing_id], None)
            _delete_brokerages(db, [brokerage_id])
            safe_commit(db)


def test_my_listings_keeps_non_manager_scoped_to_own_or_assigned_listings(client, inventory_seed):
    # Given: one assigned listing and one listing owned by another agent in the same brokerage.
    with _as_user(inventory_seed["assigned_agent"]):
        # When: the non-managing agent loads inventory.
        response = client.get("/api/v1/listings/mine")

    # Then: only their own or assigned listing is visible.
    assert response.status_code == 200
    assert inventory_seed["listing_id"] in _listing_ids(response)
    assert inventory_seed["hidden_listing_id"] not in _listing_ids(response)


def test_my_listings_returns_empty_counts_for_empty_brokerage(client):
    # Given: an active brokerage member whose brokerage has no listings.
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"t3-empty-{suffix}"
    user_id = f"t3-empty-user-{suffix}"
    with SessionLocal() as db:
        db.add_all([_brokerage(brokerage_id, "T3 Empty Brokerage"), _member(brokerage_id, user_id)])
        safe_commit(db)

    try:
        with _as_user(user_id):
            # When: the agent loads inventory.
            response = client.get("/api/v1/listings/mine")

        # Then: the payload is empty and aggregate counts are zero.
        assert response.status_code == 200
        assert response.json() == {"listings": [], "total_listings": 0, "total_conversations": 0, "total_escalated": 0}
    finally:
        with SessionLocal() as db:
            _delete_brokerages(db, [brokerage_id])
            safe_commit(db)


def test_my_listings_multi_brokerage_user_without_header_fails_closed(client, multi_brokerage_inventory_seed):
    # Given: the same user has active inventory memberships in two brokerages.
    with _as_user(multi_brokerage_inventory_seed["user_id"]):
        # When: the agent loads inventory without selecting a brokerage context.
        response = client.get("/api/v1/listings/mine")

    # Then: the route refuses to guess which brokerage inventory should be visible.
    assert response.status_code == 409
    assert _detail_code(response) == "brokerage_context_required"


def test_my_listings_respects_explicit_brokerage_context_for_multi_membership_user(client, multi_brokerage_inventory_seed):
    # Given: the same assigned agent has one listing in brokerage A and one listing in brokerage B.
    with _as_user(multi_brokerage_inventory_seed["user_id"]):
        # When: the agent selects brokerage B explicitly.
        response = client.get("/api/v1/listings/mine", headers={"X-Brokerage-Id": multi_brokerage_inventory_seed["brokerage_b"]})

    # Then: only brokerage B inventory is returned, preventing cross-brokerage leakage.
    assert response.status_code == 200
    assert _listing_ids(response) == {multi_brokerage_inventory_seed["listing_b"]}
