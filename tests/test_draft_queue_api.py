from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBBrokerage,
    DBBrokerageMember,
    DBComplianceEvent,
    DBConversation,
    DBDraftReply,
    DBLeadAction,
    DBLeadAssignment,
    DBListing,
    DBMessage,
)


@pytest.fixture
def draft_queue_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"draft-brokerage-{suffix}"
    agent_id = f"draft-agent-{suffix}"
    other_agent_id = f"draft-other-{suffix}"
    listing_id = f"draft-listing-{suffix}"
    hidden_listing_id = f"draft-hidden-listing-{suffix}"
    buyer_phone = f"+97156610{suffix[:4]}"
    other_buyer_phone = f"+97156620{suffix[:4]}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Draft Brokerage",
            slug=f"draft-{suffix}",
            status="active",
            brokerage_ai_number=f"+97158810{suffix[:4]}",
            agents_ai_number=f"+97159910{suffix[:4]}",
        ))
        db.add_all([
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
                spa_data={"project": "Draft Tower", "unit_number": "1201", "purchase_price_aed": 2_000_000},
                seller_asking_price=2_100_000,
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
                listing_id=hidden_listing_id,
                brokerage_id=brokerage_id,
                assigned_agent_id=other_agent_id,
                spa_data={"project": "Hidden Tower", "unit_number": "2201", "purchase_price_aed": 1_500_000},
                seller_asking_price=1_600_000,
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
        hidden_conversation = crud.get_or_create_conversation(db, other_buyer_phone, hidden_listing_id)
        hidden_conversation.brokerage_id = brokerage_id
        hidden_conversation.assigned_agent_id = other_agent_id
        hidden_conversation.buyer_name = "Omar"
        safe_commit(db)

        visible_draft = DBDraftReply(
            brokerage_id=brokerage_id,
            conversation_id=conversation.conversation_id,
            listing_id=listing_id,
            buyer_phone=buyer_phone,
            agent_user_id=agent_id,
            intent="follow_up",
            draft_text="Hi Sara, are you still considering Draft Tower?",
            source="morning_hot_list",
            status="draft",
            metadata_json={"created_from": "morning_hot_list"},
        )
        second_draft = DBDraftReply(
            brokerage_id=brokerage_id,
            conversation_id=conversation.conversation_id,
            listing_id=listing_id,
            buyer_phone=buyer_phone,
            agent_user_id=agent_id,
            intent="offer_ack",
            draft_text="Hi Sara, I am reviewing your offer.",
            source="template",
            status="draft",
            metadata_json={},
        )
        hidden_draft = DBDraftReply(
            brokerage_id=brokerage_id,
            conversation_id=hidden_conversation.conversation_id,
            listing_id=hidden_listing_id,
            buyer_phone=other_buyer_phone,
            agent_user_id=other_agent_id,
            intent="follow_up",
            draft_text="Hidden draft",
            source="template",
            status="draft",
            metadata_json={},
        )
        db.add_all([visible_draft, second_draft, hidden_draft])
        safe_commit(db)
        db.refresh(visible_draft)
        db.refresh(second_draft)
        db.refresh(hidden_draft)
        conversation_id = conversation.conversation_id
        hidden_conversation_id = hidden_conversation.conversation_id
        visible_draft_id = visible_draft.draft_id
        second_draft_id = second_draft.draft_id
        hidden_draft_id = hidden_draft.draft_id

    try:
        yield {
            "brokerage_id": brokerage_id,
            "agent_id": agent_id,
            "other_agent_id": other_agent_id,
            "listing_id": listing_id,
            "hidden_listing_id": hidden_listing_id,
            "conversation_id": conversation_id,
            "hidden_conversation_id": hidden_conversation_id,
            "buyer_phone": buyer_phone,
            "visible_draft_id": visible_draft_id,
            "second_draft_id": second_draft_id,
            "hidden_draft_id": hidden_draft_id,
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        set_transport_override(None)
        with SessionLocal() as db:
            db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBLeadAction).filter(DBLeadAction.conversation_id.in_([conversation_id, hidden_conversation_id])).delete(synchronize_session=False)
            db.query(DBDraftReply).filter(DBDraftReply.draft_id.in_([visible_draft_id, second_draft_id, hidden_draft_id])).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id.in_([conversation_id, hidden_conversation_id])).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id.in_([conversation_id, hidden_conversation_id])).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id.in_([conversation_id, hidden_conversation_id])).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id.in_([listing_id, hidden_listing_id])).delete(synchronize_session=False)
            db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == brokerage_id).delete(synchronize_session=False)
            safe_commit(db)


def _as_user(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id,
        email=f"{user_id}@example.com",
    )


def test_draft_queue_lists_only_visible_agent_drafts(client, draft_queue_seed):
    seed = draft_queue_seed
    _as_user(seed["agent_id"])

    response = client.get("/api/v1/agent/drafts")

    assert response.status_code == 200, response.text
    draft_ids = {draft["draft_id"] for draft in response.json()["drafts"]}
    assert seed["visible_draft_id"] in draft_ids
    assert seed["second_draft_id"] in draft_ids
    assert seed["hidden_draft_id"] not in draft_ids
    categories = {draft["category"] for draft in response.json()["drafts"]}
    assert {"stale_buyer", "offer_follow_up"}.issubset(categories)


def test_draft_queue_edit_send_reject_and_snooze_actions(client, draft_queue_seed):
    seed = draft_queue_seed
    _as_user(seed["agent_id"])
    transport = SimulatedTransport()
    set_transport_override(transport)

    edit_response = client.patch(
        f"/api/v1/agent/drafts/{seed['visible_draft_id']}",
        json={"body": "Hi Sara, I can send updated availability for Draft Tower today."},
    )
    assert edit_response.status_code == 200, edit_response.text
    assert edit_response.json()["status"] == "edited"

    send_response = client.post(
        f"/api/v1/agent/drafts/{seed['visible_draft_id']}/send",
        json={"body": "Hi Sara, updated availability is ready. Would you like the latest options?"},
    )
    assert send_response.status_code == 200, send_response.text
    assert send_response.json()["sent"] is True
    assert send_response.json()["status"] == "sent"
    assert transport.messages_to_buyer(seed["buyer_phone"])

    snooze_response = client.post(
        f"/api/v1/agent/drafts/{seed['second_draft_id']}/snooze",
        json={"minutes": 180, "reason": "Wait for offer review"},
    )
    assert snooze_response.status_code == 200, snooze_response.text
    assert snooze_response.json()["status"] == "snoozed"

    hidden_after_snooze = client.get("/api/v1/agent/drafts")
    assert hidden_after_snooze.status_code == 200, hidden_after_snooze.text
    assert seed["second_draft_id"] not in {draft["draft_id"] for draft in hidden_after_snooze.json()["drafts"]}

    visible_with_snooze = client.get("/api/v1/agent/drafts?include_snoozed=true")
    assert visible_with_snooze.status_code == 200, visible_with_snooze.text
    assert seed["second_draft_id"] in {draft["draft_id"] for draft in visible_with_snooze.json()["drafts"]}

    reject_response = client.post(
        f"/api/v1/agent/drafts/{seed['second_draft_id']}/reject",
        json={"reason": "No longer relevant"},
    )
    assert reject_response.status_code == 200, reject_response.text
    assert reject_response.json()["status"] == "discarded"

    with SessionLocal() as db:
        message = (
            db.query(DBMessage)
            .filter(
                DBMessage.conversation_id == seed["conversation_id"],
                DBMessage.intent == "agent_draft_reply",
            )
            .one()
        )
        assert "updated availability" in message.content
        event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.conversation_id == seed["conversation_id"],
                DBComplianceEvent.event_type == "draft_reply_sent",
            )
            .one()
        )
        assert event.direction == "outbound"
