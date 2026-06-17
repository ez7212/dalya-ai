from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.core.auth import CurrentUser
from app.core.brokerage_access import (
    can_view_conversation,
    grant_conversation_access,
    is_buyer_suppressed,
    is_opt_out_message,
    mark_buyer_opted_out,
    reassign_conversation,
)
from app.core.platform_aggregation import (
    build_listing_price_aggregates,
    contains_identifier,
    store_aggregate_signals,
)
from app.api.whatsapp import send_whatsapp_reply
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBBuyerSuppression,
    DBBrokerage,
    DBBrokerageMember,
    DBComplianceEvent,
    DBConversation,
    DBConversationAccessGrant,
    DBDraftReply,
    DBLeadAssignment,
    DBLeadTask,
    DBListing,
    DBMessage,
    DBPlatformAggregate,
)
from app.core.auth import get_current_user


pytestmark = pytest.mark.usefixtures("client")


TEST_BUYER_PHONE = "+971500009999"


@pytest.fixture
def seeded_brokerage_conversation():
    brokerage_id = f"brokerage-{uuid.uuid4().hex[:8]}"
    listing_id = f"listing-{uuid.uuid4().hex[:8]}"
    conversation_id = None
    owner_id = f"owner-{uuid.uuid4().hex[:8]}"
    viewer_id = f"viewer-{uuid.uuid4().hex[:8]}"
    outsider_id = f"outsider-{uuid.uuid4().hex[:8]}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Foundation Brokerage",
            slug=f"foundation-{uuid.uuid4().hex[:8]}",
            status="active",
            brokerage_ai_number="+971500000111",
            agents_ai_number="+971500000112",
        ))
        db.add_all([
            DBBrokerageMember(
                brokerage_id=brokerage_id,
                user_id=owner_id,
                email=f"{owner_id}@example.com",
                display_name="Owner",
                role="owner",
                status="active",
            ),
            DBBrokerageMember(
                brokerage_id=brokerage_id,
                user_id=viewer_id,
                email=f"{viewer_id}@example.com",
                display_name="Viewer",
                role="agent",
                status="active",
            ),
        ])
        db.add(DBListing(
            listing_id=listing_id,
            brokerage_id=brokerage_id,
            assigned_agent_id=owner_id,
            spa_data={
                "project": "Foundation Residence",
                "unit_number": "1102",
                "developer": "Emaar",
                "property_type": "Apartment",
                "bedrooms": 2,
                "purchase_price_aed": 1_750_000,
            },
            seller_asking_price=1_750_000,
            seller_notes="Seed listing for foundation tests",
            negotiation_threshold_aed=1_650_000,
            commission_rate=0.015,
            property_type="ready",
            additional_fees=[],
            seller_qa=[],
            media_urls=[],
            unit_profile={},
            unit_profile_history=[],
            processing_stages={},
        ))
        safe_commit(db)
        conv = crud.get_or_create_conversation(db, TEST_BUYER_PHONE, listing_id)
        conversation_id = conv.conversation_id
        safe_commit(db)

    try:
        yield {
            "brokerage_id": brokerage_id,
            "listing_id": listing_id,
            "conversation_id": conversation_id,
            "owner_id": owner_id,
            "viewer_id": viewer_id,
            "outsider_id": outsider_id,
        }
    finally:
        with SessionLocal() as db:
            db.query(DBComplianceEvent).filter(
                DBComplianceEvent.brokerage_id == brokerage_id,
            ).delete(synchronize_session=False)
            db.query(DBConversationAccessGrant).filter(
                DBConversationAccessGrant.brokerage_id == brokerage_id,
            ).delete(synchronize_session=False)
            db.query(DBBuyerSuppression).filter(
                DBBuyerSuppression.brokerage_id == brokerage_id,
            ).delete(synchronize_session=False)
            db.query(DBPlatformAggregate).filter(
                DBPlatformAggregate.scope_key.like("foundation-residence:%"),
            ).delete(synchronize_session=False)
            db.query(DBMessage).filter(
                DBMessage.conversation_id == conversation_id,
            ).delete(synchronize_session=False)
            db.query(DBDraftReply).filter(
                DBDraftReply.conversation_id == conversation_id,
            ).delete(synchronize_session=False)
            db.query(DBLeadTask).filter(
                DBLeadTask.conversation_id == conversation_id,
            ).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(
                DBLeadAssignment.conversation_id == conversation_id,
            ).delete(synchronize_session=False)
            db.query(DBConversation).filter(
                DBConversation.conversation_id == conversation_id,
            ).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == brokerage_id).delete(synchronize_session=False)
            safe_commit(db)


def test_conversation_visibility_requires_explicit_access(seeded_brokerage_conversation):
    seed = seeded_brokerage_conversation
    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_id"])
        assert conv is not None
        assert can_view_conversation(
            db,
            conv,
            user_id=seed["owner_id"],
            brokerage_id=seed["brokerage_id"],
            role="owner",
        )
        assert not can_view_conversation(
            db,
            conv,
            user_id=seed["viewer_id"],
            brokerage_id=seed["brokerage_id"],
            role="agent",
        )

        grant = grant_conversation_access(
            db,
            conversation=conv,
            agent_user_id=seed["viewer_id"],
            granted_by_user_id=seed["owner_id"],
            access_level="viewer",
            reason="Bring viewer into the thread",
        )
        assert grant.active is True
        assert can_view_conversation(
            db,
            conv,
            user_id=seed["viewer_id"],
            brokerage_id=seed["brokerage_id"],
            role="agent",
        )

        updated = reassign_conversation(
            db,
            conversation=conv,
            new_agent_user_id=seed["viewer_id"],
            assigned_by_user_id=seed["owner_id"],
        )
        assert updated.assigned_agent_id == seed["viewer_id"]

        assignment = db.query(DBLeadAssignment).filter_by(conversation_id=seed["conversation_id"]).one()
        assert assignment.assigned_agent_id == seed["viewer_id"]

        event_types = {
            event.event_type
            for event in db.query(DBComplianceEvent)
            .filter(DBComplianceEvent.conversation_id == seed["conversation_id"])
            .all()
        }
        assert "conversation_access_granted" in event_types
        assert "conversation_reassigned" in event_types


def test_opt_out_is_brokerage_scoped(seeded_brokerage_conversation):
    seed = seeded_brokerage_conversation
    other_brokerage_id = f"brokerage-{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=other_brokerage_id,
            name="Other Brokerage",
            slug=f"other-{uuid.uuid4().hex[:8]}",
            status="active",
        ))
        safe_commit(db)

        assert is_opt_out_message("Please stop contacting me")
        assert not is_buyer_suppressed(db, seed["brokerage_id"], TEST_BUYER_PHONE)
        assert not is_buyer_suppressed(db, other_brokerage_id, TEST_BUYER_PHONE)

        mark_buyer_opted_out(
            db,
            brokerage_id=seed["brokerage_id"],
            buyer_phone=TEST_BUYER_PHONE,
            conversation_id=seed["conversation_id"],
            listing_id=seed["listing_id"],
            suppressed_by_user_id=seed["owner_id"],
            reason="Buyer requested no further contact",
        )

        assert is_buyer_suppressed(db, seed["brokerage_id"], TEST_BUYER_PHONE)
        assert not is_buyer_suppressed(db, other_brokerage_id, TEST_BUYER_PHONE)

        event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                DBComplianceEvent.event_type == "buyer_opt_out",
            )
            .one()
        )
        assert event.direction == "inbound"

        suppression = (
            db.query(DBBuyerSuppression)
            .filter(
                DBBuyerSuppression.brokerage_id == seed["brokerage_id"],
                DBBuyerSuppression.buyer_phone == TEST_BUYER_PHONE,
            )
            .one()
        )
        assert suppression.active is True

        db.query(DBComplianceEvent).filter(
            DBComplianceEvent.brokerage_id == other_brokerage_id,
        ).delete(synchronize_session=False)
        db.query(DBBuyerSuppression).filter(
            DBBuyerSuppression.brokerage_id == other_brokerage_id,
        ).delete(synchronize_session=False)
        db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == other_brokerage_id).delete(synchronize_session=False)
        safe_commit(db)


def test_suppressed_buyer_does_not_trigger_outbound_send(monkeypatch, seeded_brokerage_conversation):
    seed = seeded_brokerage_conversation
    class DummyTransport:
        def __init__(self):
            self.calls = []

        def send_to_buyer(self, message):
            self.calls.append(message)
            return SimpleNamespace(ok=True, transport_message_id="sent-1")

    dummy = DummyTransport()
    monkeypatch.setattr("app.core.messaging.get_transport", lambda: dummy)

    with SessionLocal() as db:
        mark_buyer_opted_out(
            db,
            brokerage_id=seed["brokerage_id"],
            buyer_phone=TEST_BUYER_PHONE,
            conversation_id=seed["conversation_id"],
            listing_id=seed["listing_id"],
            suppressed_by_user_id=seed["owner_id"],
            reason="Buyer requested no further contact",
        )

    send_whatsapp_reply(
        to_number=f"whatsapp:{TEST_BUYER_PHONE}",
        body="This should not send.",
        brokerage_id=seed["brokerage_id"],
        conversation_id=seed["conversation_id"],
        listing_id=seed["listing_id"],
    )

    assert dummy.calls == []


def test_safe_aggregation_contract_strips_identifiers(seeded_brokerage_conversation):
    seed = seeded_brokerage_conversation
    other_brokerage_id = f"brokerage-{uuid.uuid4().hex[:8]}"
    extra_listing_ids = [f"listing-{uuid.uuid4().hex[:8]}" for _ in range(2)]
    try:
        with SessionLocal() as db:
            db.add(DBBrokerage(
                brokerage_id=other_brokerage_id,
                name="Other Aggregation Brokerage",
                slug=f"agg-other-{uuid.uuid4().hex[:8]}",
                status="active",
            ))
            for idx, listing_id in enumerate(extra_listing_ids):
                db.add(DBListing(
                    listing_id=listing_id,
                    brokerage_id=other_brokerage_id if idx == 1 else seed["brokerage_id"],
                    assigned_agent_id=f"agent-secret-{idx}",
                    seller_phone=f"+97150000{idx:04d}",
                    community="Foundation Residence",
                    spa_data={
                        "project": "Foundation Residence",
                        "unit_number": f"SECRET-{idx}",
                        "developer": "Emaar",
                        "property_type": "ready",
                        "bedrooms": 2,
                        "purchase_price_aed": 1_800_000 + idx * 50_000,
                        "bua_sqft": 1200 + idx * 25,
                    },
                    seller_asking_price=1_800_000 + idx * 50_000,
                    commission_rate=0.015,
                    property_type="ready",
                    additional_fees=[],
                    seller_qa=[],
                    media_urls=[],
                    unit_profile={},
                    unit_profile_history=[],
                    processing_stages={},
                ))
            safe_commit(db)

            signals = build_listing_price_aggregates(db, min_sample_count=3, period_key="2026-06")
            target = [signal for signal in signals if signal.scope_key.startswith("foundation-residence:ready:2")]
            assert len(target) == 1
            signal = target[0]
            assert signal.sample_count >= 3
            assert signal.brokerage_count >= 2
            assert not contains_identifier(signal.as_record_payload())
            assert "listing_id" not in signal.payload
            assert "brokerage_id" not in signal.payload
            assert "buyer_phone" not in signal.payload
            assert "unit_number" not in signal.payload

            records = store_aggregate_signals(db, target, source="foundation_test")
            assert len(records) == 1
            assert records[0].sample_count == signal.sample_count
    finally:
        with SessionLocal() as db:
            db.query(DBPlatformAggregate).filter(DBPlatformAggregate.source == "foundation_test").delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id.in_(extra_listing_ids)).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == other_brokerage_id).delete(synchronize_session=False)
            safe_commit(db)


def test_brokerage_config_api_updates_runtime_config(client, seeded_brokerage_conversation):
    seed = seeded_brokerage_conversation
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seed["owner_id"],
        email=f'{seed["owner_id"]}@example.com',
    )
    try:
        response = client.patch(
            "/api/v1/agent/brokerage/config",
            json={
                "prompt_config": {
                    "short_name": "Foundation",
                    "name_arabic": "Foundation Arabic",
                    "managing_agent_title": "Lead Broker",
                },
                "default_fee_framing": {
                    "market_benchmark": 0.02,
                    "commission_rate": 0.01,
                    "narrative": "buyer pays lower configured brokerage fee",
                },
                "settings": {
                    "dashboard_url": "https://foundation.example/dashboard",
                    "language_defaults": {
                        "default": "ar",
                        "enabled": ["ar", "en", "zh"],
                    },
                },
                "escalation_contact_name": "Maya",
                "escalation_contact_title": "Managing Partner",
                "escalation_contact_phone": "+971500009000",
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["brokerage_short"] == "Foundation"
        assert payload["brokerage_arabic"] == "Foundation Arabic"
        assert payload["managing_agent_title"] == "Lead Broker"
        assert payload["default_language"] == "ar"
        assert payload["enabled_languages"] == ["ar", "en", "zh"]
        assert payload["market_benchmark_rate"] == 0.02
        assert payload["default_commission_rate"] == 0.01
        assert payload["dashboard_url"] == "https://foundation.example/dashboard"

        with SessionLocal() as db:
            event = (
                db.query(DBComplianceEvent)
                .filter(
                    DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                    DBComplianceEvent.event_type == "brokerage_config_updated",
                )
                .first()
            )
            assert event is not None
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_agent_hot_list_hides_private_threads_until_shared(client, seeded_brokerage_conversation):
    seed = seeded_brokerage_conversation
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seed["viewer_id"],
        email=f'{seed["viewer_id"]}@example.com',
    )
    try:
        response = client.get("/api/v1/agent/hot-list")
        assert response.status_code == 200
        assert response.json()["leads"] == []

        detail = client.get(f"/api/v1/agent/leads/{seed['conversation_id']}")
        assert detail.status_code == 404

        with SessionLocal() as db:
            conv = db.get(DBConversation, seed["conversation_id"])
            assert conv is not None
            grant_conversation_access(
                db,
                conversation=conv,
                agent_user_id=seed["viewer_id"],
                granted_by_user_id=seed["owner_id"],
                access_level="viewer",
                reason="Invite viewer to thread",
            )

        response = client.get("/api/v1/agent/hot-list")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["leads"]) == 1
        assert payload["leads"][0]["conversation_id"] == seed["conversation_id"]

        detail = client.get(f"/api/v1/agent/leads/{seed['conversation_id']}")
        assert detail.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
