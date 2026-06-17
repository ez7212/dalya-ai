from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest

from app.core.agent_relay import relay_agent_reply
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBAgentMessageRoute,
    DBBrokerage,
    DBComplianceEvent,
    DBConversation,
    DBLeadAction,
    DBLeadAssignment,
    DBListing,
    DBMessage,
    DBMessageQueue,
)


@pytest.fixture
def relay_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"relay-brokerage-{suffix}"
    listing_id = f"relay-listing-{suffix}"
    buyer_phone = f"+97156600{suffix[:4]}"
    agent_phone = f"+97157700{suffix[:4]}"
    brokerage_ai_number = f"+97158800{suffix[:4]}"
    agents_ai_number = f"+97159900{suffix[:4]}"
    agent_user_id = f"relay-agent-{suffix}"
    token = f"R{suffix.upper()}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Relay Brokerage",
            slug=f"relay-{suffix}",
            status="active",
            brokerage_ai_number=brokerage_ai_number,
            agents_ai_number=agents_ai_number,
        ))
        db.add(DBListing(
            listing_id=listing_id,
            brokerage_id=brokerage_id,
            assigned_agent_id=agent_user_id,
            spa_data={
                "project": "Relay Residence",
                "unit_number": "2104",
                "developer": "Emaar",
                "property_type": "Apartment",
                "bedrooms": 2,
                "purchase_price_aed": 2_100_000,
            },
            seller_asking_price=2_100_000,
            negotiation_threshold_aed=2_000_000,
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
        conv = crud.get_or_create_conversation(db, buyer_phone, listing_id)
        conv.buyer_name = "Sara"
        db.add(DBMessage(
            conversation_id=conv.conversation_id,
            role="user",
            content="Can you get the seller to review AED 2M?",
            intent="offer_submission",
        ))
        db.add(DBAgentMessageRoute(
            brokerage_id=brokerage_id,
            conversation_id=conv.conversation_id,
            listing_id=listing_id,
            buyer_phone=buyer_phone,
            agent_user_id=agent_user_id,
            agent_phone=agent_phone,
            agents_ai_envelope_token=token,
            escalation_type="offer",
            tags=["at_or_above"],
            expires_at=datetime.utcnow() + timedelta(days=7),
        ))
        safe_commit(db)
        conversation_id = conv.conversation_id

    try:
        yield {
            "brokerage_id": brokerage_id,
            "listing_id": listing_id,
            "conversation_id": conversation_id,
            "buyer_phone": buyer_phone,
            "agent_phone": agent_phone,
            "wrong_agent_phone": f"+97157799{suffix[:4]}",
            "brokerage_ai_number": brokerage_ai_number,
            "agents_ai_number": agents_ai_number,
            "agent_user_id": agent_user_id,
            "token": token,
        }
    finally:
        set_transport_override(None)
        with SessionLocal() as db:
            from app.models.db_models import DBAgentRelaySession, DBRelayOutboxItem

            db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBLeadAction).filter(DBLeadAction.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBRelayOutboxItem).filter(DBRelayOutboxItem.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBAgentRelaySession).filter(DBAgentRelaySession.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBAgentMessageRoute).filter(DBAgentMessageRoute.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBMessageQueue).filter(
                (DBMessageQueue.from_number.in_([buyer_phone, agent_phone]))
                | (DBMessageQueue.to_number.in_([brokerage_ai_number, agents_ai_number]))
            ).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == brokerage_id).delete(synchronize_session=False)
            safe_commit(db)


def test_agent_reply_relay_service_sends_to_buyer_and_persists_timeline(relay_seed):
    seed = relay_seed
    transport = SimulatedTransport()
    set_transport_override(transport)
    inbound = transport.inject_agent_reply(
        envelope_token=seed["token"],
        body_without_token="Tell Sara the seller will review AED 2M today.",
        agents_ai_number=seed["agents_ai_number"],
        agent_phone=seed["agent_phone"],
    )

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        result = relay_agent_reply(db, brokerage=brokerage, inbound=inbound)

        assert result.relayed is True
        assert result.status == "relayed"
        assert transport.messages_to_buyer(seed["buyer_phone"])
        relayed = transport.messages_to_buyer(seed["buyer_phone"])[0]
        assert relayed.from_number == seed["brokerage_ai_number"]
        assert "[Ref:" not in relayed.body
        assert "seller will review" in relayed.body

        message = (
            db.query(DBMessage)
            .filter(
                DBMessage.conversation_id == seed["conversation_id"],
                DBMessage.intent == "agent_relay",
            )
            .one()
        )
        assert "seller will review" in message.content
        assert message.metadata_json["agent_user_id"] == seed["agent_user_id"]

        event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.conversation_id == seed["conversation_id"],
                DBComplianceEvent.event_type == "agent_reply_relayed",
            )
            .one()
        )
        assert event.direction == "outbound"


def test_agent_reply_relay_blocks_wrong_agent_and_expired_route(relay_seed):
    seed = relay_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        wrong_agent = transport.inject_agent_reply(
            envelope_token=seed["token"],
            body_without_token="Wrong phone should not relay.",
            agents_ai_number=seed["agents_ai_number"],
            agent_phone=seed["wrong_agent_phone"],
        )
        result = relay_agent_reply(db, brokerage=brokerage, inbound=wrong_agent)
        assert result.relayed is False
        assert result.status == "agent_reply_blocked_wrong_agent"
        assert transport.messages_to_buyer(seed["buyer_phone"]) == []

        route = (
            db.query(DBAgentMessageRoute)
            .filter(DBAgentMessageRoute.agents_ai_envelope_token == seed["token"])
            .one()
        )
        route.expires_at = datetime.utcnow() - timedelta(minutes=1)
        safe_commit(db)
        expired = transport.inject_agent_reply(
            envelope_token=seed["token"],
            body_without_token="Expired route should not relay.",
            agents_ai_number=seed["agents_ai_number"],
            agent_phone=seed["agent_phone"],
        )
        result = relay_agent_reply(db, brokerage=brokerage, inbound=expired)
        assert result.relayed is False
        assert result.status == "agent_reply_blocked_expired"
        assert transport.messages_to_buyer(seed["buyer_phone"]) == []


def test_agents_ai_webhook_branches_without_queueing_buyer_message(client, monkeypatch, relay_seed):
    seed = relay_seed
    transport = SimulatedTransport()
    set_transport_override(transport)
    monkeypatch.setattr("app.api.whatsapp.TWILIO_AUTH_TOKEN", "")

    response = client.post(
        "/api/v1/whatsapp/webhook",
        data={
            "From": f"whatsapp:{seed['agent_phone']}",
            "To": f"whatsapp:{seed['agents_ai_number']}",
            "Body": f"Yes, tell them we can discuss the MOU today.\n\n[Ref: {seed['token']}]",
            "MessageSid": f"relay-webhook-{uuid.uuid4().hex[:8]}",
            "NumMedia": "0",
        },
    )

    assert response.status_code == 200
    assert transport.messages_to_buyer(seed["buyer_phone"])
    assert "MOU today" in transport.messages_to_buyer(seed["buyer_phone"])[0].body

    with SessionLocal() as db:
        queued = (
            db.query(DBMessageQueue)
            .filter(DBMessageQueue.message_sid.like("relay-webhook-%"))
            .count()
        )
        assert queued == 0


def test_agents_ai_webhook_unknown_token_does_not_relay_or_queue(client, monkeypatch, relay_seed):
    seed = relay_seed
    transport = SimulatedTransport()
    set_transport_override(transport)
    monkeypatch.setattr("app.api.whatsapp.TWILIO_AUTH_TOKEN", "")
    message_sid = f"relay-unknown-{uuid.uuid4().hex[:8]}"

    response = client.post(
        "/api/v1/whatsapp/webhook",
        data={
            "From": f"whatsapp:{seed['agent_phone']}",
            "To": f"whatsapp:{seed['agents_ai_number']}",
            "Body": "This should not relay.\n\n[Ref: UNKNOWN1]",
            "MessageSid": message_sid,
            "NumMedia": "0",
        },
    )

    assert response.status_code == 200
    assert transport.messages_to_buyer(seed["buyer_phone"]) == []
    with SessionLocal() as db:
        queued = db.query(DBMessageQueue).filter(DBMessageQueue.message_sid == message_sid).count()
        assert queued == 0
        event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                DBComplianceEvent.event_type == "agent_reply_blocked_unknown_token",
            )
            .one()
        )
        assert event.details["reason"] == "unknown_envelope_token"


def test_buyer_webhook_dedupes_twilio_message_sid(client, monkeypatch, relay_seed):
    seed = relay_seed
    monkeypatch.setattr("app.api.whatsapp.TWILIO_AUTH_TOKEN", "")
    message_sid = f"buyer-duplicate-{uuid.uuid4().hex[:8]}"

    for _ in range(2):
        response = client.post(
            "/api/v1/whatsapp/webhook",
            data={
                "From": f"whatsapp:{seed['buyer_phone']}",
                "To": f"whatsapp:{seed['brokerage_ai_number']}",
                "Body": "Can you send me the details again?",
                "MessageSid": message_sid,
                "NumMedia": "0",
            },
        )
        assert response.status_code == 200, response.text

    with SessionLocal() as db:
        queued = db.query(DBMessageQueue).filter(DBMessageQueue.message_sid == message_sid).count()
        assert queued == 1
