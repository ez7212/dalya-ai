from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.core import escalation_threads as threading_service
from app.api.whatsapp import notify_managing_agent
from app.core.agent_relay import relay_agent_reply
from app.core.messaging.transport import mint_envelope_token
from app.core.escalation_threads import (
    close_open_threads_for_opt_out,
    escalation_bypasses_debounce,
    escalation_category,
    format_update_message,
    process_due_escalation_threads,
)
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBAgentMessageRoute,
    DBAgentProfile,
    DBBrokerage,
    DBComplianceEvent,
    DBConversation,
    DBEscalationThread,
    DBEscalationThreadQuestion,
    DBLeadAction,
    DBLeadAssignment,
    DBListing,
    DBMessage,
)
from app.schemas.conversation import EscalationAlert


@pytest.fixture
def threaded_escalation_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"thread-brokerage-{suffix}"
    listing_id = f"thread-listing-{suffix}"
    buyer_phone = f"+97152100{suffix[:4]}"
    agent_phone = f"+97152200{suffix[:4]}"
    brokerage_ai_number = f"+97152300{suffix[:4]}"
    agents_ai_number = f"+97152400{suffix[:4]}"
    agent_user_id = f"thread-agent-{suffix}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Threaded Brokerage",
            slug=f"threaded-{suffix}",
            status="active",
            brokerage_ai_number=brokerage_ai_number,
            agents_ai_number=agents_ai_number,
            settings={"legacy_telegram_alerts": False},
        ))
        db.add(DBAgentProfile(
            brokerage_id=brokerage_id,
            user_id=agent_user_id,
            email=f"agent-{suffix}@example.com",
            full_name="Karim Agent",
            display_name="Karim",
            whatsapp_phone=agent_phone,
            rera_broker_card_number=f"BRN{suffix}",
            verification_status="approved",
            onboarding_status="active",
        ))
        db.add(DBListing(
            listing_id=listing_id,
            brokerage_id=brokerage_id,
            assigned_agent_id=agent_user_id,
            spa_data={
                "project": "Thread Residence",
                "unit_number": "1204",
                "developer": "Sobha",
                "property_type": "Apartment",
                "bedrooms": 2,
                "purchase_price_aed": 3_100_000,
            },
            seller_asking_price=3_173_000,
            notification_threshold_aed=3_000_000,
            negotiation_threshold_aed=3_000_000,
            commission_rate=0.015,
            property_type="off_plan",
            additional_fees=[],
            seller_qa=[],
            media_urls=[],
            unit_profile={},
            unit_profile_history=[],
            processing_stages={},
        ))
        safe_commit(db)
        conv = crud.get_or_create_conversation(db, buyer_phone, listing_id)
        conv.buyer_name = "Mohammed"
        conv.brokerage_id = brokerage_id
        conv.assigned_agent_id = agent_user_id
        safe_commit(db)
        conversation_id = conv.conversation_id

    try:
        yield {
            "brokerage_id": brokerage_id,
            "listing_id": listing_id,
            "conversation_id": conversation_id,
            "buyer_phone": buyer_phone,
            "agent_phone": agent_phone,
            "brokerage_ai_number": brokerage_ai_number,
            "agents_ai_number": agents_ai_number,
            "agent_user_id": agent_user_id,
        }
    finally:
        set_transport_override(None)
        with SessionLocal() as db:
            thread_ids = [
                row.thread_id
                for row in db.query(DBEscalationThread.thread_id)
                .filter(DBEscalationThread.conversation_id == conversation_id)
                .all()
            ]
            if thread_ids:
                db.query(DBEscalationThreadQuestion).filter(
                    DBEscalationThreadQuestion.thread_id.in_(thread_ids)
                ).delete(synchronize_session=False)
            db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBLeadAction).filter(DBLeadAction.conversation_id == conversation_id).delete(synchronize_session=False)
            # Relay sessions/outbox (DAL-161) reference conversations — clear first.
            from app.models.db_models import DBAgentRelaySession, DBRelayOutboxItem
            db.query(DBRelayOutboxItem).filter(DBRelayOutboxItem.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBAgentRelaySession).filter(DBAgentRelaySession.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBAgentMessageRoute).filter(DBAgentMessageRoute.conversation_id == conversation_id).delete(synchronize_session=False)
            if thread_ids:
                # `offers` (DBOffer) FK-references escalation_threads (offers_thread_id_fkey) — clear before threads.
                from app.models.db_models import DBOffer
                db.query(DBOffer).filter(DBOffer.thread_id.in_(thread_ids)).delete(synchronize_session=False)
                db.query(DBEscalationThread).filter(DBEscalationThread.thread_id.in_(thread_ids)).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id == conversation_id).delete(synchronize_session=False)
            # Brokerage-scoped buyer rows the engine creates also FK-reference brokerages — clear before it.
            from app.models.db_models import DBBrokerageBuyerProfile, DBBuyerPreferenceProfile, DBBuyerProfile, DBLeadTask
            for _Model in (DBBrokerageBuyerProfile, DBBuyerProfile, DBBuyerPreferenceProfile, DBLeadTask):
                db.query(_Model).filter(_Model.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == brokerage_id).delete(synchronize_session=False)
            safe_commit(db)


def _info_gap(seed: dict, message: str, topic: str = "service charges") -> EscalationAlert:
    return EscalationAlert(
        escalation_type="info_gap",
        priority="normal",
        conversation_id=seed["conversation_id"],
        listing_id=seed["listing_id"],
        buyer_phone=seed["buyer_phone"],
        buyer_name="Mohammed",
        trigger_message=message,
        escalation_subtype="listing_fact_gap",
        payload={
            "topic": topic,
            "question_digest": message,
            "requested_action": "Confirm the missing listing fact and reply to the buyer.",
        },
    )


def _offer(seed: dict, amount: float = 3_050_000) -> EscalationAlert:
    return EscalationAlert(
        escalation_type="offer",
        priority="high",
        conversation_id=seed["conversation_id"],
        listing_id=seed["listing_id"],
        buyer_phone=seed["buyer_phone"],
        buyer_name="Mohammed",
        trigger_message=f"I can offer AED {amount:,.0f}",
        offer_amount_aed=amount,
        listing_price_aed=3_173_000,
        negotiation_threshold_aed=3_000_000,
        payload={"amount_aed": amount},
    )


def _brn(seed: dict) -> EscalationAlert:
    return EscalationAlert(
        escalation_type="brn_request",
        priority="normal",
        conversation_id=seed["conversation_id"],
        listing_id=seed["listing_id"],
        buyer_phone=seed["buyer_phone"],
        buyer_name="Mohammed",
        trigger_message="Can you share the agent BRN?",
        escalation_subtype="brn_request",
        payload={
            "doc_requested": "BRN / RERA card verification",
            "requested_action": "Send the correct agent registration details.",
        },
    )


def _flush_due_threads(seed: dict, *, now: datetime | None = None):
    now = now or datetime.utcnow()
    with SessionLocal() as db:
        for thread in db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).all():
            thread.debounce_until = now - timedelta(seconds=1)
            safe_commit(db)
        return process_due_escalation_threads(db, now=now)


def _thread(seed: dict, category: str | None = None):
    with SessionLocal() as db:
        query = db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"])
        if category:
            query = query.filter_by(category=category)
        return query.order_by(DBEscalationThread.created_at.asc()).all()


def test_info_gap_category_mapping_is_keyword_first(threaded_escalation_seed):
    seed = threaded_escalation_seed

    assert escalation_category(_info_gap(seed, "What are the service charges?")) == "fees_and_charges"
    assert escalation_category(_info_gap(
        seed,
        "What is the remaining payment plan?",
        topic="payment plan",
    )) == "payment_plan"
    assert escalation_category(_info_gap(
        seed,
        "What's the rental yield and expected capital appreciation by handover?",
        topic="rental yield and capital appreciation",
    )) == "market_analysis"
    assert escalation_category(_info_gap(
        seed,
        "1. What are the service charges?\n2. Can you confirm floor level and view?",
        topic="floor level and view and orientation",
    )) == "physical_property"
    assert escalation_category(_info_gap(seed, "Is the unit tenanted?", topic="tenancy")) == "tenancy_status"
    assert escalation_category(_info_gap(seed, "How many parking spaces?", topic="parking")) == "physical_property"


def test_brn_request_does_not_bypass_debounce(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    alert = _brn(seed)
    assert escalation_category(alert) == "regulatory_documents"
    assert escalation_bypasses_debounce(alert) is False

    asyncio.run(notify_managing_agent(alert))

    assert transport.messages_to_agents_ai() == []
    with SessionLocal() as db:
        thread = db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).one()
        assert thread.category == "regulatory_documents"
        assert thread.state == "debouncing"
        assert thread.debounce_until is not None


def test_create_thread_integrity_error_refetches_and_appends(monkeypatch, threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)
    original_create_thread = threading_service.create_thread
    fired = {"value": False}

    def racing_create_thread(*args, **kwargs):
        if not fired["value"]:
            fired["value"] = True
            with SessionLocal() as race_db:
                race_brokerage = race_db.get(DBBrokerage, seed["brokerage_id"])
                original_create_thread(
                    race_db,
                    brokerage=race_brokerage,
                    alert=_info_gap(seed, "What are the service charges?"),
                    agent_user_id=seed["agent_user_id"],
                    agent_phone=seed["agent_phone"],
                    category="fees_and_charges",
                    state="debouncing",
                    metadata_json={
                        "source": "race",
                        "envelope_body": "Race-created envelope",
                        "tags": ["info_gap"],
                        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                    },
                    now=kwargs["now"],
                )
                safe_commit(race_db)
            raise IntegrityError(
                "insert escalation_threads",
                {},
                Exception("uq_open_escalation_thread_scope"),
            )
        return original_create_thread(*args, **kwargs)

    monkeypatch.setattr(threading_service, "create_thread", racing_create_thread)

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        agent = db.query(DBAgentProfile).filter_by(user_id=seed["agent_user_id"]).one()
        result = threading_service.send_initial_or_update(
            db,
            brokerage=brokerage,
            alert=_info_gap(seed, "Are AC maintenance fees included?"),
            managing_agent=agent,
            envelope_body="Outer envelope",
            tags=["info_gap"],
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        assert result.action == "debounced"

    with SessionLocal() as db:
        threads = db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).all()
        assert len(threads) == 1
        thread = threads[0]
        assert thread.category == "fees_and_charges"
        assert thread.question_count == 2
        questions = [
            q.question_text
            for q in db.query(DBEscalationThreadQuestion)
            .filter_by(thread_id=thread.thread_id)
            .order_by(DBEscalationThreadQuestion.sort_order.asc())
            .all()
        ]
        assert questions == ["What are the service charges?", "Are AC maintenance fees included?"]
        assert transport.messages_to_agents_ai() == []


def test_initial_debounce_bundles_same_category_and_update_reuses_agent_token(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    asyncio.run(notify_managing_agent(_info_gap(seed, "What are the service charges?")))
    assert transport.messages_to_agents_ai() == []

    asyncio.run(notify_managing_agent(_info_gap(seed, "Are AC maintenance fees included?")))
    assert transport.messages_to_agents_ai() == []

    with SessionLocal() as db:
        thread = db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).one()
        assert thread.state == "debouncing"
        assert thread.question_count == 2
        created_event = db.query(DBComplianceEvent).filter_by(
            conversation_id=seed["conversation_id"],
            event_type="escalation_thread_created",
        ).one()
        assert created_event.details["category"] == "fees_and_charges"

    _flush_due_threads(seed)
    first_agent_message = transport.messages_to_agents_ai()[0]
    token = first_agent_message.envelope_token
    assert "What are the service charges?" in first_agent_message.body
    assert "Are AC maintenance fees included?" in first_agent_message.body

    asyncio.run(notify_managing_agent(_info_gap(seed, "Can you confirm when service charges are paid?")))
    assert len(transport.messages_to_agents_ai()) == 1

    with SessionLocal() as db:
        thread = db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).one()
        assert thread.state == "updated"
        assert thread.question_count == 3
        body = format_update_message(
            db,
            thread=thread,
            token=token,
            new_question="Can you confirm when service charges are paid?",
            now=datetime.utcnow() + timedelta(minutes=2),
        )
        assert body.splitlines()[0] == f"[Update on Ref: {token}]"
        assert "Buyer also asked:" in body
        assert "1. What are the service charges? (original," in body
        assert "2. Are AC maintenance fees included? (added," in body
        assert "3. Can you confirm when service charges are paid? (added," in body
        assert seed["buyer_phone"] not in body
        assert seed["listing_id"] not in body

    _flush_due_threads(seed)

    agent_messages = transport.messages_to_agents_ai()
    assert len(agent_messages) == 2
    assert agent_messages[1].envelope_token == token
    assert f"[Update on Ref: {token}]" in agent_messages[1].body
    assert "What are the service charges?" in agent_messages[1].body
    assert "Are AC maintenance fees included?" in agent_messages[1].body

    with SessionLocal() as db:
        routes = db.query(DBAgentMessageRoute).filter_by(conversation_id=seed["conversation_id"]).all()
        threads = db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).all()
        questions = db.query(DBEscalationThreadQuestion).filter_by(thread_id=threads[0].thread_id).all()
        assert len(routes) == 1
        assert len(threads) == 1
        assert threads[0].category == "fees_and_charges"
        assert threads[0].state == "updated"
        assert threads[0].question_count == 3
        assert len(questions) == 3
        assert db.query(DBComplianceEvent).filter_by(
            conversation_id=seed["conversation_id"],
            event_type="escalation_thread_question_appended",
        ).count() >= 2
        assert db.query(DBComplianceEvent).filter_by(
            conversation_id=seed["conversation_id"],
            event_type="escalation_thread_updated",
        ).count() == 1


def test_different_category_creates_new_thread_and_new_token(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    asyncio.run(notify_managing_agent(_info_gap(seed, "What are the service charges?")))
    _flush_due_threads(seed)
    first_token = transport.messages_to_agents_ai()[0].envelope_token
    asyncio.run(notify_managing_agent(_info_gap(
        seed,
        "How many parking spaces come with the unit?",
        topic="parking",
    )))
    _flush_due_threads(seed)
    second_token = transport.messages_to_agents_ai()[1].envelope_token

    assert first_token != second_token
    with SessionLocal() as db:
        threads = (
            db.query(DBEscalationThread)
            .filter_by(conversation_id=seed["conversation_id"])
            .order_by(DBEscalationThread.created_at.asc())
            .all()
        )
        assert len(threads) == 2
        assert {thread.category for thread in threads} == {"fees_and_charges", "physical_property"}


def test_same_category_after_thread_resolution_creates_new_thread(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    asyncio.run(notify_managing_agent(_info_gap(seed, "What are the service charges?")))
    _flush_due_threads(seed)
    token = transport.messages_to_agents_ai()[0].envelope_token

    inbound = transport.inject_agent_reply(
        envelope_token=token,
        body_without_token=(
            "Service charges are AED 21 per sqft annually, and AC maintenance is billed separately."
        ),
        agents_ai_number=seed["agents_ai_number"],
        agent_phone=seed["agent_phone"],
    )
    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        result = relay_agent_reply(db, brokerage=brokerage, inbound=inbound)
        assert result.relayed is True

    buyer_messages = transport.messages_to_buyer(seed["buyer_phone"])
    assert len(buyer_messages) == 1
    assert "AED 21 per sqft" in buyer_messages[0].body
    assert "[Ref:" not in buyer_messages[0].body

    asyncio.run(notify_managing_agent(_info_gap(seed, "Can Karim also confirm service charge payment timing?")))
    assert len(transport.messages_to_agents_ai()) == 1
    _flush_due_threads(seed)
    agent_messages = transport.messages_to_agents_ai()
    assert len(agent_messages) == 2
    assert agent_messages[1].envelope_token != token

    with SessionLocal() as db:
        resolved = (
            db.query(DBEscalationThread)
            .filter(
                DBEscalationThread.conversation_id == seed["conversation_id"],
                DBEscalationThread.envelope_token == token,
            )
            .one()
        )
        assert resolved.state == "resolved"
        assert resolved.close_reason == "agent_reply"
        assert all(
            question.resolved_at is not None
            for question in db.query(DBEscalationThreadQuestion).filter_by(thread_id=resolved.thread_id).all()
        )
        assert db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).count() == 2
        event = db.query(DBComplianceEvent).filter_by(
            conversation_id=seed["conversation_id"],
            event_type="escalation_thread_resolved",
        ).one()
        assert event.details["question_count"] == 1


def test_same_category_after_24h_window_creates_new_thread(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    asyncio.run(notify_managing_agent(_info_gap(seed, "What are the service charges?")))
    _flush_due_threads(seed)
    first_token = transport.messages_to_agents_ai()[0].envelope_token
    with SessionLocal() as db:
        thread = db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).one()
        old_time = datetime.utcnow() - timedelta(hours=25)
        thread.last_buyer_message_at = old_time
        thread.updated_at = old_time
        safe_commit(db)
        process_due_escalation_threads(db, now=datetime.utcnow())

    asyncio.run(notify_managing_agent(_info_gap(seed, "Can you confirm the annual maintenance charge too?")))
    _flush_due_threads(seed)

    assert len(transport.messages_to_agents_ai()) == 2
    assert transport.messages_to_agents_ai()[1].envelope_token != first_token
    with SessionLocal() as db:
        assert db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).count() == 2
        assert db.query(DBEscalationThread).filter_by(
            conversation_id=seed["conversation_id"],
            state="timed_out",
        ).count() == 1
        assert db.query(DBComplianceEvent).filter_by(
            conversation_id=seed["conversation_id"],
            event_type="escalation_thread_timed_out",
        ).count() == 1


def test_offer_bypasses_debounce_and_alerts_immediately(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    asyncio.run(notify_managing_agent(_offer(seed)))

    assert len(transport.messages_to_agents_ai()) == 1
    with SessionLocal() as db:
        thread = db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).one()
        assert thread.category == "offer"
        assert thread.state == "open"
        assert thread.debounce_until is None


def test_repeated_offers_create_distinct_open_threads(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    asyncio.run(notify_managing_agent(_offer(seed, 3_050_000)))
    asyncio.run(notify_managing_agent(_offer(seed, 3_100_000)))

    assert len(transport.messages_to_agents_ai()) == 2
    assert transport.messages_to_agents_ai()[0].envelope_token != transport.messages_to_agents_ai()[1].envelope_token
    with SessionLocal() as db:
        threads = (
            db.query(DBEscalationThread)
            .filter_by(conversation_id=seed["conversation_id"], category="offer")
            .all()
        )
        assert len(threads) == 2
        assert {thread.state for thread in threads} == {"open"}


def test_successful_threaded_initial_send_uses_agents_ai_only(monkeypatch, threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    class FailingAsyncClient:
        async def __aenter__(self):
            raise AssertionError("no external fallback should run after Agents AI send")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", FailingAsyncClient)

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        brokerage.settings = {"legacy_telegram_alerts": True}
        safe_commit(db)

    asyncio.run(notify_managing_agent(_offer(seed)))

    assert len(transport.messages_to_agents_ai()) == 1
    with SessionLocal() as db:
        assert db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).count() == 1


def test_thread_send_clears_legacy_pending_forwarded_questions(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_id"])
        conv.pending_forwarded_questions = ["What are the service charges?"]
        conv.alerted_questions = []
        safe_commit(db)

    asyncio.run(notify_managing_agent(_info_gap(seed, "What are the service charges?")))
    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_id"])
        assert conv.pending_forwarded_questions == ["What are the service charges?"]

    _flush_due_threads(seed)

    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_id"])
        assert conv.pending_forwarded_questions == []
        assert conv.alerted_questions == ["What are the service charges?"]


def test_opt_out_closes_open_threads(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    asyncio.run(notify_managing_agent(_info_gap(seed, "What are the service charges?")))
    with SessionLocal() as db:
        closed = close_open_threads_for_opt_out(
            db,
            brokerage_id=seed["brokerage_id"],
            buyer_phone=seed["buyer_phone"],
        )
        safe_commit(db)
        assert closed == 1
        thread = db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).one()
        assert thread.state == "opt_out_closed"
        assert thread.close_reason == "opt_out"
        assert db.query(DBComplianceEvent).filter_by(
            conversation_id=seed["conversation_id"],
            event_type="escalation_thread_opt_out_closed",
        ).count() == 1

    _flush_due_threads(seed)
    assert transport.messages_to_agents_ai() == []


def test_reply_to_one_thread_does_not_resolve_other_open_thread(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    asyncio.run(notify_managing_agent(_info_gap(seed, "What are the service charges?")))
    asyncio.run(notify_managing_agent(_info_gap(seed, "How many parking spaces?", topic="parking")))
    _flush_due_threads(seed)
    agent_messages = transport.messages_to_agents_ai()
    fee_token = next(msg.envelope_token for msg in agent_messages if "service charges" in msg.body)
    parking_token = next(msg.envelope_token for msg in agent_messages if "parking spaces" in msg.body)

    inbound = transport.inject_agent_reply(
        envelope_token=fee_token,
        body_without_token="Service charges are AED 21 per sqft.",
        agents_ai_number=seed["agents_ai_number"],
        agent_phone=seed["agent_phone"],
    )
    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        relay_agent_reply(db, brokerage=brokerage, inbound=inbound)
        fee_thread = db.query(DBEscalationThread).filter_by(envelope_token=fee_token).one()
        parking_thread = db.query(DBEscalationThread).filter_by(envelope_token=parking_token).one()
        assert fee_thread.state == "resolved"
        assert parking_thread.state == "open"


def test_update_message_caps_open_questions(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)

    asyncio.run(notify_managing_agent(_info_gap(seed, "What are the service charges?")))
    _flush_due_threads(seed)
    token = transport.messages_to_agents_ai()[0].envelope_token
    with SessionLocal() as db:
        thread = db.query(DBEscalationThread).filter_by(conversation_id=seed["conversation_id"]).one()
        for idx in range(2, 13):
            from app.core.escalation_threads import append_question
            append_question(
                db,
                thread=thread,
                question_text=f"Follow-up question {idx}?",
                category=thread.category,
                escalation_subtype=thread.escalation_subtype,
                now=datetime.utcnow() + timedelta(minutes=idx),
            )
        body = format_update_message(
            db,
            thread=thread,
            token=token,
            new_question="Follow-up question 12?",
            now=datetime.utcnow() + timedelta(minutes=20),
        )
        assert "10. Follow-up question 10?" in body
        assert "11. Follow-up question 11?" not in body
        assert "...and 2 more - see dashboard." in body


def test_legacy_null_thread_route_relay_still_succeeds(threaded_escalation_seed):
    seed = threaded_escalation_seed
    transport = SimulatedTransport()
    set_transport_override(transport)
    token = mint_envelope_token()

    with SessionLocal() as db:
        db.add(DBAgentMessageRoute(
            thread_id=None,
            brokerage_id=seed["brokerage_id"],
            conversation_id=seed["conversation_id"],
            listing_id=seed["listing_id"],
            buyer_phone=seed["buyer_phone"],
            agent_user_id=seed["agent_user_id"],
            agent_phone=seed["agent_phone"],
            agents_ai_envelope_token=token,
            escalation_type="info_gap",
            tags=["info_gap"],
            expires_at=datetime.utcnow() + timedelta(days=7),
        ))
        safe_commit(db)

    inbound = transport.inject_agent_reply(
        envelope_token=token,
        body_without_token="Service charges are AED 21 per sqft.",
        agents_ai_number=seed["agents_ai_number"],
        agent_phone=seed["agent_phone"],
    )
    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        result = relay_agent_reply(db, brokerage=brokerage, inbound=inbound)
        assert result.relayed is True
        message = db.query(DBMessage).filter_by(conversation_id=seed["conversation_id"], intent="agent_relay").one()
        assert message.metadata_json["thread_id"] is None
        event = db.query(DBComplianceEvent).filter_by(
            conversation_id=seed["conversation_id"],
            event_type="agent_reply_relayed",
        ).one()
        assert event.details["thread_id"] is None
        assert event.details["question_count"] is None

    buyer_messages = transport.messages_to_buyer(seed["buyer_phone"])
    assert len(buyer_messages) == 1
    assert buyer_messages[0].body == "Service charges are AED 21 per sqft."
