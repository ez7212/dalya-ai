from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageBuyerProfile,
    DBBrokerageMember,
    DBBuyerProfile,
    DBBuyerProfileField,
    DBConversation,
    DBLeadAssignment,
    DBListing,
    DBListingInquiry,
    DBMessage,
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


def _phone(suffix: str, offset: int = 0) -> str:
    digits = (int(suffix, 16) + offset) % 10000
    return f"+9715620{digits:04d}"


@pytest.fixture
def runtime_guard_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_a = f"dal170c2-a-{suffix}"
    brokerage_b = f"dal170c2-b-{suffix}"
    owner_a = f"dal170c2-owner-a-{suffix}"
    owner_b = f"dal170c2-owner-b-{suffix}"
    listing_a = f"dal170c2-listing-a-{suffix}"
    listing_b = f"dal170c2-listing-b-{suffix}"
    listing_null = f"dal170c2-listing-null-{suffix}"
    conversation_a = f"dal170c2-conv-a-{suffix}"
    conversation_b = f"dal170c2-conv-b-{suffix}"
    buyer_phone = _phone(suffix)
    null_buyer_phone = _phone(suffix, 1)
    profile_a = f"dal170c2-profile-a-{suffix}"
    profile_b = f"dal170c2-profile-b-{suffix}"

    with SessionLocal() as db:
        db.add_all(
            [
                DBBrokerage(
                    brokerage_id=brokerage_a,
                    name="DAL-170C2 Brokerage A",
                    slug=brokerage_a,
                    status="active",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerage(
                    brokerage_id=brokerage_b,
                    name="DAL-170C2 Brokerage B",
                    slug=brokerage_b,
                    status="active",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerageMember(brokerage_id=brokerage_a, user_id=owner_a, role="owner", status="active"),
                DBBrokerageMember(brokerage_id=brokerage_b, user_id=owner_b, role="owner", status="active"),
                DBAgentProfile(
                    brokerage_id=brokerage_a,
                    user_id=owner_a,
                    full_name="DAL-170C2 Owner A",
                    display_name="Owner A",
                    whatsapp_phone=_phone(suffix, 10),
                    rera_broker_card_number=f"DAL170C2-A-{suffix}",
                    onboarding_status="active",
                ),
                DBAgentProfile(
                    brokerage_id=brokerage_b,
                    user_id=owner_b,
                    full_name="DAL-170C2 Owner B",
                    display_name="Owner B",
                    whatsapp_phone=_phone(suffix, 11),
                    rera_broker_card_number=f"DAL170C2-B-{suffix}",
                    onboarding_status="active",
                ),
                DBListing(
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    assigned_agent_id=owner_a,
                    spa_data={"project": "Tenant A Tower", "unit_number": "A-170C2"},
                    seller_asking_price=1_700_000,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=f"https://example.test/dal170c2/a/{suffix}",
                ),
                DBListing(
                    listing_id=listing_b,
                    brokerage_id=brokerage_b,
                    assigned_agent_id=owner_b,
                    spa_data={"project": "Tenant B Tower", "unit_number": "B-170C2"},
                    seller_asking_price=2_700_000,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=f"https://example.test/dal170c2/b/{suffix}",
                ),
                DBListing(
                    listing_id=listing_null,
                    brokerage_id=None,
                    spa_data={"project": "Null Tenant Tower", "unit_number": "N-170C2"},
                    seller_asking_price=900_000,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=f"https://example.test/dal170c2/null/{suffix}",
                ),
                DBConversation(
                    conversation_id=conversation_a,
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    assigned_agent_id=owner_a,
                    buyer_phone=buyer_phone,
                    buyer_name="Buyer A",
                    updated_at=datetime.utcnow(),
                ),
                DBConversation(
                    conversation_id=conversation_b,
                    listing_id=listing_b,
                    brokerage_id=brokerage_b,
                    assigned_agent_id=owner_b,
                    buyer_phone=buyer_phone,
                    buyer_name="Buyer B",
                    updated_at=datetime.utcnow() + timedelta(seconds=1),
                ),
                DBBuyerProfile(
                    phone=buyer_phone,
                    brokerage_id=None,
                    name="Legacy Global Buyer",
                    budget_aed=9_900_000,
                    bedroom_preferences=[5],
                    area_preferences=["Global Legacy Area"],
                ),
                DBBuyerProfile(
                    phone=null_buyer_phone,
                    brokerage_id=None,
                    name="Legacy Inquiry FK Buyer",
                    bedroom_preferences=[],
                    area_preferences=[],
                ),
                DBBrokerageBuyerProfile(
                    profile_id=profile_a,
                    brokerage_id=brokerage_a,
                    buyer_phone=buyer_phone,
                    name="Buyer A",
                    source="test",
                ),
                DBBrokerageBuyerProfile(
                    profile_id=profile_b,
                    brokerage_id=brokerage_b,
                    buyer_phone=buyer_phone,
                    name="Buyer B",
                    source="test",
                ),
            ]
        )
        db.flush()
        db.add_all(
            [
                DBMessage(conversation_id=conversation_a, role="user", content="Tenant A message", intent="general"),
                DBMessage(conversation_id=conversation_b, role="user", content="Tenant B message", intent="general"),
                DBLeadAssignment(
                    brokerage_id=brokerage_a,
                    conversation_id=conversation_a,
                    listing_id=listing_a,
                    buyer_phone=buyer_phone,
                    assigned_agent_id=owner_a,
                    status="active",
                    signal="ready_to_view",
                    urgency_score=80,
                    next_action="call_now",
                    next_action_reason="Tenant A next step",
                    last_buyer_message_at=datetime.utcnow(),
                ),
                DBLeadAssignment(
                    brokerage_id=brokerage_b,
                    conversation_id=conversation_b,
                    listing_id=listing_b,
                    buyer_phone=buyer_phone,
                    assigned_agent_id=owner_b,
                    status="active",
                    signal="firm_offer",
                    urgency_score=95,
                    next_action="review_offer",
                    next_action_reason="Tenant B next step",
                    last_buyer_message_at=datetime.utcnow(),
                ),
                DBBuyerProfileField(
                    profile_id=profile_a,
                    brokerage_id=brokerage_a,
                    field="budget_max_aed",
                    value=1_800_000,
                    provenance="agent_confirmed",
                    confirmed_by=owner_a,
                ),
                DBBuyerProfileField(
                    profile_id=profile_b,
                    brokerage_id=brokerage_b,
                    field="budget_max_aed",
                    value=2_800_000,
                    provenance="agent_confirmed",
                    confirmed_by=owner_b,
                ),
                DBListingInquiry(
                    brokerage_id=brokerage_a,
                    buyer_phone=buyer_phone,
                    listing_id=listing_a,
                    project="Tenant A Tower",
                    unit_number="A-170C2",
                    price_aed=1_700_000,
                ),
                DBListingInquiry(
                    brokerage_id=brokerage_b,
                    buyer_phone=buyer_phone,
                    listing_id=listing_b,
                    project="Tenant B Tower",
                    unit_number="B-170C2",
                    price_aed=2_700_000,
                ),
                DBListingInquiry(
                    brokerage_id=None,
                    buyer_phone=buyer_phone,
                    listing_id=listing_null,
                    project="Null Tenant Tower",
                    unit_number="N-170C2",
                    price_aed=900_000,
                ),
            ]
        )
        safe_commit(db)

    yield {
        "brokerage_a": brokerage_a,
        "brokerage_b": brokerage_b,
        "owner_a": owner_a,
        "owner_b": owner_b,
        "listing_a": listing_a,
        "listing_b": listing_b,
        "listing_null": listing_null,
        "conversation_a": conversation_a,
        "conversation_b": conversation_b,
        "buyer_phone": buyer_phone,
        "null_buyer_phone": null_buyer_phone,
        "profile_a": profile_a,
        "profile_b": profile_b,
    }

    with SessionLocal() as db:
        db.query(DBListingInquiry).filter(
            DBListingInquiry.buyer_phone.in_([buyer_phone, null_buyer_phone])
        ).delete(synchronize_session=False)
        db.query(DBBuyerProfileField).filter(
            DBBuyerProfileField.profile_id.in_([profile_a, profile_b])
        ).delete(synchronize_session=False)
        db.query(DBBrokerageBuyerProfile).filter(
            DBBrokerageBuyerProfile.profile_id.in_([profile_a, profile_b])
        ).delete(synchronize_session=False)
        db.query(DBLeadAssignment).filter(
            DBLeadAssignment.conversation_id.in_([conversation_a, conversation_b])
        ).delete(synchronize_session=False)
        db.query(DBMessage).filter(
            DBMessage.conversation_id.in_([conversation_a, conversation_b])
        ).delete(synchronize_session=False)
        db.query(DBConversation).filter(
            DBConversation.conversation_id.in_([conversation_a, conversation_b])
        ).delete(synchronize_session=False)
        db.query(DBBuyerProfile).filter(
            DBBuyerProfile.phone.in_([buyer_phone, null_buyer_phone])
        ).delete(synchronize_session=False)
        db.query(DBListing).filter(
            DBListing.listing_id.in_([listing_a, listing_b, listing_null])
        ).delete(synchronize_session=False)
        db.query(DBAgentProfile).filter(
            DBAgentProfile.brokerage_id.in_([brokerage_a, brokerage_b])
        ).delete(synchronize_session=False)
        db.query(DBBrokerageMember).filter(
            DBBrokerageMember.brokerage_id.in_([brokerage_a, brokerage_b])
        ).delete(synchronize_session=False)
        db.query(DBBrokerage).filter(
            DBBrokerage.brokerage_id.in_([brokerage_a, brokerage_b])
        ).delete(synchronize_session=False)
        safe_commit(db)


def test_null_tenant_listing_is_not_returned_by_active_crud_helpers(runtime_guard_seed):
    with SessionLocal() as db:
        assert crud.get_listing(db, runtime_guard_seed["listing_null"]) is None
        assert crud.get_spa(db, runtime_guard_seed["listing_null"]) is None
        assert crud.get_conversations_for_listing(db, runtime_guard_seed["listing_null"]) == []
        assert crud.get_listing_stats_fast(db, runtime_guard_seed["listing_null"]) == {
            "listing_id": runtime_guard_seed["listing_null"],
            "total_conversations": 0,
            "total_messages": 0,
            "escalated_leads": 0,
            "active_buyers": [],
        }
        assert crud.get_or_create_conversation(
            db,
            runtime_guard_seed["null_buyer_phone"],
            runtime_guard_seed["listing_null"],
        ) is None

        null_conversation = (
            db.query(DBConversation)
            .filter_by(
                buyer_phone=runtime_guard_seed["null_buyer_phone"],
                listing_id=runtime_guard_seed["listing_null"],
            )
            .first()
        )
        assert null_conversation is None


def test_listing_inquiry_creation_is_brokerage_scoped_and_rejects_null_roots(runtime_guard_seed):
    with SessionLocal() as db:
        scoped_phone = runtime_guard_seed["null_buyer_phone"]
        crud.add_listing_inquiry(
            db,
            buyer_phone=scoped_phone,
            listing_id=runtime_guard_seed["listing_a"],
            project="Tenant A Tower",
            unit_number="A-170C2",
            price_aed=1_700_000,
        )
        crud.add_listing_inquiry(
            db,
            buyer_phone=scoped_phone,
            listing_id=runtime_guard_seed["listing_b"],
            project="Tenant B Tower",
            unit_number="B-170C2",
            price_aed=2_700_000,
            brokerage_id=runtime_guard_seed["brokerage_a"],
        )
        crud.add_listing_inquiry(
            db,
            buyer_phone=scoped_phone,
            listing_id=runtime_guard_seed["listing_null"],
            project="Null Tenant Tower",
            unit_number="N-170C2",
            price_aed=900_000,
        )

        rows = (
            db.query(DBListingInquiry)
            .filter(DBListingInquiry.buyer_phone == scoped_phone)
            .order_by(DBListingInquiry.listing_id.asc())
            .all()
        )

    assert [(row.listing_id, row.brokerage_id) for row in rows] == [
        (runtime_guard_seed["listing_a"], runtime_guard_seed["brokerage_a"])
    ]


def test_tenant_scoped_profile_schema_ignores_legacy_and_cross_brokerage_state(runtime_guard_seed):
    from app.core.buyer_profiles import profile_to_schema

    with SessionLocal() as db:
        profile = db.get(DBBrokerageBuyerProfile, runtime_guard_seed["profile_a"])
        payload = profile_to_schema(db, profile)

    assert payload.phone == runtime_guard_seed["buyer_phone"]
    assert payload.name == "Buyer A"
    assert payload.budget_aed == 1_800_000
    assert payload.bedroom_preferences == []
    assert payload.area_preferences == []
    assert [item.listing_id for item in payload.listings_inquired] == [runtime_guard_seed["listing_a"]]
    assert "Tenant B Tower" not in payload.model_dump_json()
    assert "Global Legacy Area" not in payload.model_dump_json()
    assert "9900000" not in payload.model_dump_json()


def test_agent_buyer_apis_do_not_expose_legacy_or_cross_brokerage_profile_data(client, runtime_guard_seed):
    with _as_user(runtime_guard_seed["owner_a"]):
        list_response = client.get("/api/v1/agent/buyers")
        card_response = client.get(f"/api/v1/agent/buyers/{runtime_guard_seed['profile_a']}")
        cross_profile_response = client.get(f"/api/v1/agent/buyers/{runtime_guard_seed['profile_b']}")

    assert list_response.status_code == 200, list_response.text
    assert card_response.status_code == 200, card_response.text
    assert cross_profile_response.status_code == 404

    list_text = list_response.text
    card_text = card_response.text
    assert runtime_guard_seed["profile_a"] in list_text
    assert runtime_guard_seed["profile_b"] not in list_text
    assert "Buyer B" not in list_text
    assert "Buyer B" not in card_text
    assert "2_800_000" not in card_text
    assert "9_900_000" not in card_text
    assert "Global Legacy Area" not in card_text
