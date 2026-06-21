"""DAL-170E5A — server-backed needs_reply signal on the agent dashboard.

Verifies the precise needs_reply semantics derived from message timestamps by
role, pending-draft representation, opt-out handling, needs_reply-first sorting,
and cross-brokerage isolation. All scoped to /api/v1/agent/dashboard.
"""
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
    DBOutreachDraft,
)

Base.metadata.create_all(bind=engine)


def _make_brokerage(db, suffix):
    brokerage_id = f"nr-brokerage-{suffix}"
    agent_id = f"nr-agent-{suffix}"
    listing_id = f"nr-listing-{suffix}"
    db.add(DBBrokerage(
        brokerage_id=brokerage_id,
        name="Needs Reply Brokerage",
        slug=f"nr-{suffix}",
        status="active",
        brokerage_ai_number=f"+97150003{suffix[:4]}",
        agents_ai_number=f"+97150004{suffix[:4]}",
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
        spa_data={"project": "NR Tower", "unit_number": "1001", "bedrooms": 2},
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
    """messages: list of (role, content, minutes_ago)."""
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
def nr_seed():
    suffix = uuid.uuid4().hex[:8]
    created_brokerages = []
    created_conversations = []

    with SessionLocal() as db:
        brokerage_id, agent_id, listing_id = _make_brokerage(db, suffix)
        created_brokerages.append(brokerage_id)

    state = {
        "suffix": suffix,
        "brokerage_id": brokerage_id,
        "agent_id": agent_id,
        "listing_id": listing_id,
        "_brokerages": created_brokerages,
        "_conversations": created_conversations,
    }
    try:
        yield state
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        with SessionLocal() as db:
            for bid in created_brokerages:
                conv_ids = [c.conversation_id for c in db.query(DBConversation).filter(DBConversation.brokerage_id == bid).all()]
                # Child rows created directly and by the dashboard's hot-list refresh.
                for model in (DBLeadTask, DBLeadAssignment, DBDraftReply, DBAIDraft, DBOutreachDraft, DBHotlistRefreshRun):
                    db.query(model).filter(model.brokerage_id == bid).delete(synchronize_session=False)
                if conv_ids:
                    db.query(DBEscalationThread).filter(DBEscalationThread.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
                    db.query(DBLeadAction).filter(DBLeadAction.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
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
    for c in payload["conversations"]:
        if c["conversation_id"] == conversation_id:
            return c
    raise AssertionError(f"conversation {conversation_id} not in payload")


def test_buyer_latest_message_needs_reply_true(client, nr_seed):
    phone = f"+97155901{nr_seed['suffix'][:4]}"
    with SessionLocal() as db:
        cid = _add_conversation(
            db, nr_seed["brokerage_id"], nr_seed["agent_id"], nr_seed["listing_id"], phone,
            [("assistant", "Hi, how can I help?", 30), ("user", "Can I view it today?", 5)],
        )
        profile = DBBrokerageBuyerProfile(
            brokerage_id=nr_seed["brokerage_id"],
            buyer_phone=phone,
            name="Buyer",
        )
        db.add(profile)
        db.flush()
        db.add(DBBuyerProfileField(
            profile_id=profile.profile_id,
            brokerage_id=nr_seed["brokerage_id"],
            field="budget_max_aed",
            value=2_000_000,
            provenance="agent_confirmed",
            confirmed_by=nr_seed["agent_id"],
        ))
        safe_commit(db)
    _as_user(nr_seed["agent_id"])
    item = _conv(_dashboard(client), cid)
    assert item["needs_reply"] is True
    assert item["needs_reply_reason"] == "buyer_awaiting"
    assert item["last_buyer_message_at"] is not None
    assert item["deal_readiness"]["stage"] == "partially_qualified"
    assert item["deal_readiness"]["present_fields"]["budget_max_aed"] == 2_000_000


def test_agent_replied_after_buyer_needs_reply_false(client, nr_seed):
    phone = f"+97155902{nr_seed['suffix'][:4]}"
    with SessionLocal() as db:
        cid = _add_conversation(
            db, nr_seed["brokerage_id"], nr_seed["agent_id"], nr_seed["listing_id"], phone,
            [("user", "Can I view it today?", 30), ("assistant", "Yes, 6pm works.", 2)],
        )
    _as_user(nr_seed["agent_id"])
    item = _conv(_dashboard(client), cid)
    assert item["needs_reply"] is False
    assert item["needs_reply_reason"] is None
    assert item["last_agent_response_at"] is not None


def test_pending_draft_is_represented(client, nr_seed):
    phone = f"+97155903{nr_seed['suffix'][:4]}"
    with SessionLocal() as db:
        cid = _add_conversation(
            db, nr_seed["brokerage_id"], nr_seed["agent_id"], nr_seed["listing_id"], phone,
            [("user", "What is the service charge?", 10)],
        )
        db.add(DBDraftReply(
            brokerage_id=nr_seed["brokerage_id"],
            conversation_id=cid,
            buyer_phone=phone,
            intent="follow_up",
            draft_text="The service charge is AED 15/sqft.",
            status="draft",
        ))
        safe_commit(db)
    _as_user(nr_seed["agent_id"])
    item = _conv(_dashboard(client), cid)
    assert item["needs_reply"] is True
    assert item["has_pending_draft"] is True
    assert item["needs_reply_reason"] == "draft_ready"


def test_opted_out_thread_not_needs_reply(client, nr_seed):
    """Opt-out (the only buyer-level 'closed' state in the schema) is excluded."""
    phone = f"+97155904{nr_seed['suffix'][:4]}"
    with SessionLocal() as db:
        cid = _add_conversation(
            db, nr_seed["brokerage_id"], nr_seed["agent_id"], nr_seed["listing_id"], phone,
            [("user", "Stop messaging me", 5)],
        )
        db.add(DBBuyerSuppression(
            brokerage_id=nr_seed["brokerage_id"],
            buyer_phone=phone,
            source="buyer_opt_out",
            active=True,
        ))
        safe_commit(db)
    _as_user(nr_seed["agent_id"])
    item = _conv(_dashboard(client), cid)
    assert item["needs_reply"] is False
    assert item["needs_reply_reason"] is None


def test_resolved_escalation_thread_not_needs_reply_even_when_buyer_latest(client, nr_seed):
    phone = f"+97155909{nr_seed['suffix'][:4]}"
    with SessionLocal() as db:
        cid = _add_conversation(
            db, nr_seed["brokerage_id"], nr_seed["agent_id"], nr_seed["listing_id"], phone,
            [("assistant", "I have escalated this.", 30), ("user", "Can you confirm the NOC?", 10)],
        )
        now = datetime.utcnow()
        db.add(DBEscalationThread(
            brokerage_id=nr_seed["brokerage_id"],
            conversation_id=cid,
            listing_id=nr_seed["listing_id"],
            buyer_phone=phone,
            agent_user_id=nr_seed["agent_id"],
            category="regulatory",
            state="resolved",
            escalation_type="regulatory_request",
            last_buyer_message_at=now - timedelta(minutes=10),
            closed_at=now - timedelta(minutes=2),
        ))
        safe_commit(db)
    _as_user(nr_seed["agent_id"])
    item = _conv(_dashboard(client), cid)
    assert item["last_message_role"] == "user"
    assert item["needs_reply"] is False
    assert item["needs_reply_reason"] is None


def test_needs_reply_items_sorted_first(client, nr_seed):
    answered_phone = f"+97155905{nr_seed['suffix'][:4]}"
    waiting_phone = f"+97155906{nr_seed['suffix'][:4]}"
    with SessionLocal() as db:
        # answered conversation is the most recently updated, but should rank below the waiting one
        answered = _add_conversation(
            db, nr_seed["brokerage_id"], nr_seed["agent_id"], nr_seed["listing_id"], answered_phone,
            [("user", "thanks", 20), ("assistant", "anytime", 1)], name="Answered",
        )
        waiting = _add_conversation(
            db, nr_seed["brokerage_id"], nr_seed["agent_id"], nr_seed["listing_id"], waiting_phone,
            [("assistant", "hello", 30), ("user", "still waiting?", 10)], name="Waiting",
        )
    _as_user(nr_seed["agent_id"])
    payload = _dashboard(client)
    ids = [c["conversation_id"] for c in payload["conversations"]]
    assert ids.index(waiting) < ids.index(answered)
    assert _conv(payload, waiting)["needs_reply"] is True
    assert _conv(payload, answered)["needs_reply"] is False


def test_cross_brokerage_isolation(client, nr_seed):
    """Another brokerage's waiting buyer must not appear or affect this agent's payload."""
    my_phone = f"+97155907{nr_seed['suffix'][:4]}"
    with SessionLocal() as db:
        my_cid = _add_conversation(
            db, nr_seed["brokerage_id"], nr_seed["agent_id"], nr_seed["listing_id"], my_phone,
            [("user", "any update?", 5)],
        )
        other_suffix = uuid.uuid4().hex[:8]
        other_bid, other_agent, other_listing = _make_brokerage(db, other_suffix)
        nr_seed["_brokerages"].append(other_bid)
        other_phone = f"+97155908{other_suffix[:4]}"
        other_cid = _add_conversation(
            db, other_bid, other_agent, other_listing, other_phone,
            [("user", "other brokerage buyer waiting", 5)],
        )
    _as_user(nr_seed["agent_id"])
    payload = _dashboard(client)
    ids = [c["conversation_id"] for c in payload["conversations"]]
    assert my_cid in ids
    assert other_cid not in ids
    # metric counts only this brokerage's needs_reply threads
    assert all(c["conversation_id"] != other_cid for c in payload["conversations"])
