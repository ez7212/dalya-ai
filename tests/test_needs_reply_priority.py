from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.db import crud
from app.db.session import Base, SessionLocal, engine, safe_commit
from app.main import app
from app.models.db_models import (
    DBAIDraft,
    DBBrokerage,
    DBBrokerageBuyerProfile,
    DBBrokerageMember,
    DBBuyerProfileField,
    DBBuyerSuppression,
    DBConversation,
    DBDraftReply,
    DBEscalationThread,
    DBHotlistRefreshRun,
    DBLeadAction,
    DBLeadAssignment,
    DBLeadTask,
    DBListing,
    DBMessage,
    DBOfferRecord,
    DBOutreachDraft,
)

Base.metadata.create_all(bind=engine)


def _make_brokerage(db, suffix):
    brokerage_id = f"nrp-brokerage-{suffix}"
    agent_id = f"nrp-agent-{suffix}"
    listing_id = f"nrp-listing-{suffix}"
    db.add(DBBrokerage(
        brokerage_id=brokerage_id,
        name="Needs Reply Priority Brokerage",
        slug=f"nrp-{suffix}",
        status="active",
        brokerage_ai_number=f"+97150103{suffix[:4]}",
        agents_ai_number=f"+97150104{suffix[:4]}",
    ))
    db.add(DBBrokerageMember(
        brokerage_id=brokerage_id,
        user_id=agent_id,
        email=f"{agent_id}@example.com",
        display_name="Agent",
        role="agent",
        status="active",
    ))
    db.add(DBListing(
        listing_id=listing_id,
        brokerage_id=brokerage_id,
        assigned_agent_id=agent_id,
        spa_data={"project": "Priority Tower", "unit_number": "1201", "bedrooms": 2},
        seller_asking_price=2_000_000,
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
    return brokerage_id, agent_id, listing_id


def _add_conversation(db, brokerage_id, agent_id, listing_id, phone, messages, *, name="Buyer"):
    conv = crud.get_or_create_conversation(db, phone, listing_id)
    conv.brokerage_id = brokerage_id
    conv.assigned_agent_id = agent_id
    conv.buyer_name = name
    now = datetime.utcnow()
    for role, content, minutes_ago in messages:
        db.add(DBMessage(
            conversation_id=conv.conversation_id,
            role=role,
            content=content,
            timestamp=now - timedelta(minutes=minutes_ago),
        ))
    safe_commit(db)
    return conv.conversation_id


@pytest.fixture
def nrp_seed():
    suffix = uuid.uuid4().hex[:8]
    created_brokerages = []

    with SessionLocal() as db:
        brokerage_id, agent_id, listing_id = _make_brokerage(db, suffix)
        created_brokerages.append(brokerage_id)

    state = {
        "suffix": suffix,
        "brokerage_id": brokerage_id,
        "agent_id": agent_id,
        "listing_id": listing_id,
        "_brokerages": created_brokerages,
    }
    try:
        yield state
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        with SessionLocal() as db:
            for bid in created_brokerages:
                conv_ids = [c.conversation_id for c in db.query(DBConversation).filter(DBConversation.brokerage_id == bid).all()]
                for model in (DBLeadTask, DBLeadAssignment, DBDraftReply, DBAIDraft, DBOutreachDraft, DBHotlistRefreshRun):
                    db.query(model).filter(model.brokerage_id == bid).delete(synchronize_session=False)
                if conv_ids:
                    db.query(DBEscalationThread).filter(DBEscalationThread.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
                    db.query(DBLeadAction).filter(DBLeadAction.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
                    db.query(DBOfferRecord).filter(DBOfferRecord.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
                    db.query(DBMessage).filter(DBMessage.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
                    db.query(DBConversation).filter(DBConversation.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
                db.query(DBBuyerSuppression).filter(DBBuyerSuppression.brokerage_id == bid).delete(synchronize_session=False)
                db.query(DBBuyerProfileField).filter(DBBuyerProfileField.brokerage_id == bid).delete(synchronize_session=False)
                db.query(DBBrokerageBuyerProfile).filter(DBBrokerageBuyerProfile.brokerage_id == bid).delete(synchronize_session=False)
                db.query(DBListing).filter(DBListing.brokerage_id == bid).delete(synchronize_session=False)
                db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == bid).delete(synchronize_session=False)
                db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == bid).delete(synchronize_session=False)
            safe_commit(db)


def _as_user(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=user_id, email=f"{user_id}@example.com")


def _dashboard(client):
    resp = client.get("/api/v1/agent/dashboard")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _conv(payload, conversation_id):
    for conversation in payload["conversations"]:
        if conversation["conversation_id"] == conversation_id:
            return conversation
    raise AssertionError(f"conversation {conversation_id} not in payload")


def test_high_intent_needs_reply_outranks_low_intent_acknowledgement(client, nrp_seed):
    # Given: four unanswered buyer messages, with the acknowledgement most recent.
    suffix = nrp_seed["suffix"][:4]
    with SessionLocal() as db:
        ack = _add_conversation(
            db,
            nrp_seed["brokerage_id"],
            nrp_seed["agent_id"],
            nrp_seed["listing_id"],
            f"+97155201{suffix}",
            [("assistant", "Details sent.", 40), ("user", "ok thanks 👍", 1)],
            name="Acknowledgement",
        )
        viewing = _add_conversation(
            db,
            nrp_seed["brokerage_id"],
            nrp_seed["agent_id"],
            nrp_seed["listing_id"],
            f"+97155202{suffix}",
            [("assistant", "Happy to help.", 50), ("user", "Can I view tomorrow?", 30)],
            name="Viewing",
        )
        offer = _add_conversation(
            db,
            nrp_seed["brokerage_id"],
            nrp_seed["agent_id"],
            nrp_seed["listing_id"],
            f"+97155203{suffix}",
            [("assistant", "The asking price is AED 2M.", 55), ("user", "Would the seller take AED 1,900,000?", 25)],
            name="Offer",
        )
        process = _add_conversation(
            db,
            nrp_seed["brokerage_id"],
            nrp_seed["agent_id"],
            nrp_seed["listing_id"],
            f"+97155204{suffix}",
            [("assistant", "It is a ready property.", 60), ("user", "What documents are needed for NOC transfer?", 20)],
            name="Process",
        )

    # When: the agent loads the dashboard.
    _as_user(nrp_seed["agent_id"])
    payload = _dashboard(client)
    ids = [conversation["conversation_id"] for conversation in payload["conversations"]]

    # Then: true buyer questions stay needs_reply and rank above the acknowledgement.
    for conversation_id in (viewing, offer, process, ack):
        assert _conv(payload, conversation_id)["needs_reply"] is True
    assert ids.index(viewing) < ids.index(ack)
    assert ids.index(offer) < ids.index(ack)
    assert ids.index(process) < ids.index(ack)
    assert _conv(payload, viewing)["needs_reply_priority"] == "high"
    assert _conv(payload, offer)["needs_reply_priority"] == "high"
    assert _conv(payload, process)["needs_reply_priority"] == "high"
    assert _conv(payload, ack)["needs_reply_priority"] == "low"


def test_new_concrete_question_after_open_escalation_stays_actionable(client, nrp_seed):
    # Given: an open escalation covers an earlier buyer message, then the buyer asks a new viewing question.
    phone = f"+97155205{nrp_seed['suffix'][:4]}"
    with SessionLocal() as db:
        cid = _add_conversation(
            db,
            nrp_seed["brokerage_id"],
            nrp_seed["agent_id"],
            nrp_seed["listing_id"],
            phone,
            [
                ("assistant", "I escalated this to the agent.", 60),
                ("user", "Thanks, please check.", 40),
                ("user", "Can I view tomorrow afternoon?", 5),
            ],
            name="New viewing question",
        )
        now = datetime.utcnow()
        db.add(DBEscalationThread(
            brokerage_id=nrp_seed["brokerage_id"],
            conversation_id=cid,
            listing_id=nrp_seed["listing_id"],
            buyer_phone=phone,
            agent_user_id=nrp_seed["agent_id"],
            category="viewing",
            state="open",
            escalation_type="viewing_request",
            last_buyer_message_at=now - timedelta(minutes=40),
            updated_at=now - timedelta(minutes=35),
        ))
        safe_commit(db)

    # When: the agent loads the dashboard.
    _as_user(nrp_seed["agent_id"])
    item = _conv(_dashboard(client), cid)

    # Then: the new concrete question is not hidden by the older open escalation.
    assert item["needs_reply"] is True
    assert item["needs_reply_reason"] == "viewing_request"
    assert item["needs_reply_priority"] == "high"


def test_open_escalation_suppresses_represented_low_priority_acknowledgement(client, nrp_seed):
    # Given: the latest buyer acknowledgement is already represented in an open escalation.
    phone = f"+97155206{nrp_seed['suffix'][:4]}"
    with SessionLocal() as db:
        cid = _add_conversation(
            db,
            nrp_seed["brokerage_id"],
            nrp_seed["agent_id"],
            nrp_seed["listing_id"],
            phone,
            [("assistant", "I escalated this to the agent.", 60), ("user", "ok thanks", 10)],
            name="Covered acknowledgement",
        )
        now = datetime.utcnow()
        db.add(DBEscalationThread(
            brokerage_id=nrp_seed["brokerage_id"],
            conversation_id=cid,
            listing_id=nrp_seed["listing_id"],
            buyer_phone=phone,
            agent_user_id=nrp_seed["agent_id"],
            category="general",
            state="open",
            escalation_type="agent_review",
            last_buyer_message_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=9),
        ))
        safe_commit(db)

    # When: the agent loads the dashboard.
    _as_user(nrp_seed["agent_id"])
    item = _conv(_dashboard(client), cid)

    # Then: the open escalation carries the low-priority acknowledgement, so no duplicate needs_reply row is created.
    assert item["open_escalation_count"] == 1
    assert item["needs_reply"] is False
    assert item["needs_reply_reason"] == "covered_by_open_escalation"
    assert item["needs_reply_priority"] == "low"
