from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest

from app.core.agent_relay import relay_agent_reply
from app.core.auth import CurrentUser, get_current_user
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.db import crud
from app.db.session import Base, SessionLocal, engine, safe_commit
from app.main import app
from app.models.db_models import (
    DBAgentMessageRoute,
    DBBrokerage,
    DBBrokerageMember,
    DBComplianceEvent,
    DBConversation,
    DBEscalationThread,
    DBEscalationThreadQuestion,
    DBLeadAction,
    DBLeadAssignment,
    DBListing,
    DBMessage,
)


Base.metadata.create_all(bind=engine)


@pytest.fixture
def escalation_inbox_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"inbox-brokerage-{suffix}"
    owner_id = f"inbox-owner-{suffix}"
    agent_id = f"inbox-agent-{suffix}"
    other_agent_id = f"inbox-other-{suffix}"
    listing_id = f"inbox-listing-{suffix}"
    other_listing_id = f"inbox-listing-other-{suffix}"
    buyer_phone = f"+97155511{suffix[:4]}"
    other_buyer_phone = f"+97155522{suffix[:4]}"
    now = datetime.utcnow()

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Inbox Brokerage",
            slug=f"inbox-{suffix}",
            status="active",
            brokerage_ai_number=f"+97150001{suffix[:4]}",
            agents_ai_number=f"+97150002{suffix[:4]}",
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
                user_id=agent_id,
                email=f"{agent_id}@example.com",
                display_name="Agent",
                role="agent",
                status="active",
            ),
            DBBrokerageMember(
                brokerage_id=brokerage_id,
                user_id=other_agent_id,
                email=f"{other_agent_id}@example.com",
                display_name="Other Agent",
                role="agent",
                status="active",
            ),
        ])
        db.add_all([
            DBListing(
                listing_id=listing_id,
                brokerage_id=brokerage_id,
                assigned_agent_id=agent_id,
                spa_data={
                    "project": "Inbox Tower",
                    "unit_number": "1204",
                    "developer": "Emaar",
                    "property_type": "Apartment",
                    "bedrooms": 2,
                    "purchase_price_aed": 2_000_000,
                },
                seller_asking_price=2_200_000,
                negotiation_threshold_aed=2_050_000,
                commission_rate=0.015,
                property_type="ready",
                additional_fees=[],
                seller_qa=[],
                media_urls=[],
                unit_profile={},
                unit_profile_history=[],
                processing_stages={},
            ),
            DBListing(
                listing_id=other_listing_id,
                brokerage_id=brokerage_id,
                assigned_agent_id=other_agent_id,
                spa_data={
                    "project": "Private Tower",
                    "unit_number": "2201",
                    "developer": "Meraas",
                    "property_type": "Apartment",
                    "bedrooms": 1,
                    "purchase_price_aed": 1_400_000,
                },
                seller_asking_price=1_550_000,
                negotiation_threshold_aed=1_500_000,
                commission_rate=0.015,
                property_type="ready",
                additional_fees=[],
                seller_qa=[],
                media_urls=[],
                unit_profile={},
                unit_profile_history=[],
                processing_stages={},
            ),
        ])
        safe_commit(db)

        conversation = crud.get_or_create_conversation(db, buyer_phone, listing_id)
        conversation.brokerage_id = brokerage_id
        conversation.assigned_agent_id = agent_id
        conversation.buyer_name = "Sara"
        other_conversation = crud.get_or_create_conversation(db, other_buyer_phone, other_listing_id)
        other_conversation.brokerage_id = brokerage_id
        other_conversation.assigned_agent_id = other_agent_id
        other_conversation.buyer_name = "Omar"
        db.add_all([
            DBMessage(
                conversation_id=conversation.conversation_id,
                role="user",
                content="What are the service charges and annual maintenance?",
                intent="info_gap",
            ),
            DBMessage(
                conversation_id=other_conversation.conversation_id,
                role="user",
                content="Can I get the title deed?",
                intent="regulatory_request",
            ),
        ])
        safe_commit(db)

        thread = DBEscalationThread(
            brokerage_id=brokerage_id,
            conversation_id=conversation.conversation_id,
            listing_id=listing_id,
            buyer_phone=buyer_phone,
            agent_user_id=agent_id,
            agent_phone="+971500009003",
            category="fees_and_charges",
            state="updated",
            escalation_type="info_gap",
            escalation_subtype="service_charges",
            envelope_token=f"I{suffix.upper()}",
            opened_at=now - timedelta(minutes=8),
            alerted_at=now - timedelta(minutes=7),
            last_buyer_message_at=now - timedelta(minutes=2),
            last_update_sent_at=now - timedelta(minutes=1),
            question_count=2,
        )
        hidden_thread = DBEscalationThread(
            brokerage_id=brokerage_id,
            conversation_id=other_conversation.conversation_id,
            listing_id=other_listing_id,
            buyer_phone=other_buyer_phone,
            agent_user_id=other_agent_id,
            agent_phone="+971500009004",
            category="regulatory_documents",
            state="open",
            escalation_type="regulatory_request",
            escalation_subtype="title_deed",
            envelope_token=f"H{suffix.upper()}",
            opened_at=now - timedelta(minutes=10),
            alerted_at=now - timedelta(minutes=9),
            last_buyer_message_at=now - timedelta(minutes=10),
            question_count=1,
        )
        db.add_all([thread, hidden_thread])
        safe_commit(db)

        db.add_all([
            DBEscalationThreadQuestion(
                thread_id=thread.thread_id,
                question_text="What are the service charges?",
                category="fees_and_charges",
                escalation_subtype="service_charges",
                sort_order=1,
                added_at=now - timedelta(minutes=8),
            ),
            DBEscalationThreadQuestion(
                thread_id=thread.thread_id,
                question_text="And annual maintenance?",
                category="fees_and_charges",
                escalation_subtype="service_charges",
                sort_order=2,
                added_at=now - timedelta(minutes=2),
            ),
            DBEscalationThreadQuestion(
                thread_id=hidden_thread.thread_id,
                question_text="Can I get the title deed?",
                category="regulatory_documents",
                escalation_subtype="title_deed",
                sort_order=1,
                added_at=now - timedelta(minutes=10),
            ),
            DBAgentMessageRoute(
                thread_id=thread.thread_id,
                brokerage_id=brokerage_id,
                conversation_id=conversation.conversation_id,
                listing_id=listing_id,
                buyer_phone=buyer_phone,
                agent_user_id=agent_id,
                agent_phone="+971500009003",
                agents_ai_envelope_token=thread.envelope_token,
                escalation_type="info_gap",
                tags=["fees_and_charges"],
                expires_at=now + timedelta(days=7),
            ),
        ])
        safe_commit(db)
        conversation_id = conversation.conversation_id
        other_conversation_id = other_conversation.conversation_id
        thread_id = thread.thread_id
        hidden_thread_id = hidden_thread.thread_id

    try:
        yield {
            "brokerage_id": brokerage_id,
            "owner_id": owner_id,
            "agent_id": agent_id,
            "other_agent_id": other_agent_id,
            "listing_id": listing_id,
            "other_listing_id": other_listing_id,
            "conversation_id": conversation_id,
            "other_conversation_id": other_conversation_id,
            "thread_id": thread_id,
            "hidden_thread_id": hidden_thread_id,
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        set_transport_override(None)
        with SessionLocal() as db:
            db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBLeadAction).filter(DBLeadAction.conversation_id.in_([conversation_id, other_conversation_id])).delete(synchronize_session=False)
            db.query(DBAgentMessageRoute).filter(DBAgentMessageRoute.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBEscalationThreadQuestion).filter(
                DBEscalationThreadQuestion.thread_id.in_([thread_id, hidden_thread_id])
            ).delete(synchronize_session=False)
            db.query(DBEscalationThread).filter(DBEscalationThread.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id.in_([conversation_id, other_conversation_id])).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id.in_([conversation_id, other_conversation_id])).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id.in_([conversation_id, other_conversation_id])).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id.in_([listing_id, other_listing_id])).delete(synchronize_session=False)
            db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == brokerage_id).delete(synchronize_session=False)
            safe_commit(db)


def _as_user(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id,
        email=f"{user_id}@example.com",
    )


def test_escalation_inbox_lists_only_visible_threads_for_agent(client, escalation_inbox_seed):
    seed = escalation_inbox_seed
    _as_user(seed["agent_id"])

    response = client.get("/api/v1/agent/escalations?state=active")

    assert response.status_code == 200, response.text
    payload = response.json()
    thread_ids = {thread["thread_id"] for thread in payload["threads"]}
    assert seed["thread_id"] in thread_ids
    assert seed["hidden_thread_id"] not in thread_ids

    thread = payload["threads"][0]
    assert thread["category"] == "fees_and_charges"
    assert thread["urgency"] == "high"
    assert thread["question_count"] == 2
    assert [question["question_text"] for question in thread["questions"]] == [
        "What are the service charges?",
        "And annual maintenance?",
    ]
    assert thread["envelope_token"].startswith("I")


def test_owner_can_filter_and_resolve_escalation_thread(client, escalation_inbox_seed):
    seed = escalation_inbox_seed
    _as_user(seed["owner_id"])

    list_response = client.get("/api/v1/agent/escalations?state=active&category=regulatory_documents")
    assert list_response.status_code == 200, list_response.text
    assert [thread["thread_id"] for thread in list_response.json()["threads"]] == [seed["hidden_thread_id"]]

    resolve_response = client.post(
        f"/api/v1/agent/escalations/{seed['hidden_thread_id']}/resolve",
        json={"reason": "manual", "note": "Handled by phone."},
    )
    assert resolve_response.status_code == 200, resolve_response.text
    assert resolve_response.json()["state"] == "resolved"

    with SessionLocal() as db:
        thread = db.get(DBEscalationThread, seed["hidden_thread_id"])
        assert thread.state == "resolved"
        assert thread.close_reason == "manual"
        assert all(
            question.resolved_at is not None
            for question in db.query(DBEscalationThreadQuestion).filter_by(thread_id=seed["hidden_thread_id"]).all()
        )
        event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                DBComplianceEvent.event_type == "escalation_thread_resolved",
                DBComplianceEvent.actor_user_id == seed["owner_id"],
            )
            .one()
        )
        assert event.details["resolution_source"] == "agent_dashboard"


def test_agent_can_reply_to_escalation_from_dashboard_and_consume_route(client, escalation_inbox_seed):
    seed = escalation_inbox_seed
    _as_user(seed["agent_id"])
    transport = SimulatedTransport()
    set_transport_override(transport)

    response = client.post(
        f"/api/v1/agent/escalations/{seed['thread_id']}/reply",
        json={
            "body": "Service charges are AED 22 per sqft. I will confirm the latest statement before offer.",
            "send_to_buyer": True,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["sent"] is True
    assert payload["state"] == "resolved"
    assert payload["close_reason"] == "agent_reply"

    buyer_messages = transport.messages_to_buyer()
    assert len(buyer_messages) == 1
    sent = buyer_messages[0]
    assert sent.from_number.startswith("+97150001")
    assert sent.to_number.startswith("+97155511")
    assert "Service charges are AED 22" in sent.body
    assert "[Ref:" not in sent.body

    with SessionLocal() as db:
        message = (
            db.query(DBMessage)
            .filter(
                DBMessage.conversation_id == seed["conversation_id"],
                DBMessage.intent == "agent_relay",
            )
            .one()
        )
        assert message.metadata_json["source"] == "agent_dashboard_reply"
        assert message.metadata_json["agent_user_id"] == seed["agent_id"]

        thread = db.get(DBEscalationThread, seed["thread_id"])
        assert thread.state == "resolved"
        assert thread.closed_at is not None
        assert all(
            question.resolved_at is not None
            for question in db.query(DBEscalationThreadQuestion)
            .filter_by(thread_id=seed["thread_id"])
            .all()
        )

        route = (
            db.query(DBAgentMessageRoute)
            .filter(DBAgentMessageRoute.thread_id == seed["thread_id"])
            .one()
        )
        assert route.consumed_at is not None

        action = (
            db.query(DBLeadAction)
            .filter(
                DBLeadAction.conversation_id == seed["conversation_id"],
                DBLeadAction.action_type == "agent_dashboard_reply_sent",
            )
            .one()
        )
        assert action.agent_user_id == seed["agent_id"]

        event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.conversation_id == seed["conversation_id"],
                DBComplianceEvent.event_type == "agent_dashboard_reply_sent",
            )
            .one()
        )
        assert event.direction == "outbound"
        assert event.actor_user_id == seed["agent_id"]

        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        reused = transport.inject_agent_reply(
            envelope_token=route.agents_ai_envelope_token,
            body_without_token="This duplicate should not relay.",
            agents_ai_number=brokerage.agents_ai_number,
            agent_phone=route.agent_phone,
        )
        result = relay_agent_reply(db, brokerage=brokerage, inbound=reused)
        assert result.relayed is False
        assert result.status == "agent_reply_blocked_consumed"
        assert len(transport.messages_to_buyer()) == 1
