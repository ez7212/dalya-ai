"""
DAL-158 — Live conversation takeover (pause/resume AI).

Covers the spec verification checklist:
  1. Pause → buyer message arrives → no AI reply, raw forward on Agents AI,
     inbox shows the message unanswered.
  2. Pause via TAKEOVER quote-reply → confirmation received → state persisted
     with source "whatsapp".
  3. Pending drafts auto-snoozed with reason "takeover".
  4. RESUME restores normal concierge behavior on the next buyer message.
  5. Keyword messages never reach the buyer.
  6. Compliance events written for both transitions.
  7. Cross-tenant: takeover state/commands isolated between brokerages.
  8. Default ai_mode is "active" — takeover off by default, persona-harness
     baseline untouched.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.core.conversation_takeover import (
    AI_MODE_ACTIVE,
    AI_MODE_AGENT_CONTROLLED,
    find_agent_controlled_conversation,
    handle_agents_ai_mode_keyword,
    parse_mode_keyword,
    set_ai_mode,
)
from app.core.debounce_worker import _handle_batch
from app.core.hot_list import HotListScore, ensure_follow_up_draft
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBAgentMessageRoute,
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageMember,
    DBComplianceEvent,
    DBConversation,
    DBDraftReply,
    DBLeadAction,
    DBLeadAssignment,
    DBListing,
    DBMessage,
    DBMessageQueue,
)


@pytest.fixture
def takeover_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"tko-brokerage-{suffix}"
    listing_id = f"tko-listing-{suffix}"
    buyer_phone = f"+97156611{suffix[:4]}"
    agent_phone = f"+97157711{suffix[:4]}"
    brokerage_ai_number = f"+97158811{suffix[:4]}"
    agents_ai_number = f"+97159911{suffix[:4]}"
    agent_user_id = f"tko-agent-{suffix}"
    token = f"T{suffix.upper()}"

    # Second brokerage for cross-tenant isolation checks.
    other_brokerage_id = f"tko-other-{suffix}"
    other_agents_ai_number = f"+97159922{suffix[:4]}"
    other_agent_phone = f"+97157722{suffix[:4]}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Takeover Brokerage",
            slug=f"tko-{suffix}",
            status="active",
            brokerage_ai_number=brokerage_ai_number,
            agents_ai_number=agents_ai_number,
        ))
        db.add(DBBrokerage(
            brokerage_id=other_brokerage_id,
            name="Other Brokerage",
            slug=f"tko-other-{suffix}",
            status="active",
            brokerage_ai_number=f"+97158822{suffix[:4]}",
            agents_ai_number=other_agents_ai_number,
        ))
        db.add(DBBrokerageMember(
            brokerage_id=brokerage_id,
            user_id=agent_user_id,
            role="agent",
            status="active",
        ))
        db.add(DBAgentProfile(
            brokerage_id=brokerage_id,
            user_id=agent_user_id,
            full_name="Takeover Agent",
            display_name="Takeover Agent",
            whatsapp_phone=agent_phone,
            rera_broker_card_number=f"BRN-{suffix}",
        ))
        db.add(DBListing(
            listing_id=listing_id,
            brokerage_id=brokerage_id,
            assigned_agent_id=agent_user_id,
            spa_data={
                "project": "Takeover Towers",
                "unit_number": "1107",
                "developer": "Emaar",
                "property_type": "Apartment",
                "bedrooms": 1,
                "purchase_price_aed": 1_500_000,
            },
            seller_asking_price=1_500_000,
            negotiation_threshold_aed=1_400_000,
            commission_rate=0.02,
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
        conv.buyer_name = "Ahmed"
        conv.assigned_agent_id = agent_user_id
        db.add(DBAgentMessageRoute(
            brokerage_id=brokerage_id,
            conversation_id=conv.conversation_id,
            listing_id=listing_id,
            buyer_phone=buyer_phone,
            agent_user_id=agent_user_id,
            agent_phone=agent_phone,
            agents_ai_envelope_token=token,
            escalation_type="info_gap",
            tags=["info_gap"],
            expires_at=datetime.utcnow() + timedelta(days=7),
        ))
        safe_commit(db)
        conversation_id = conv.conversation_id

    transport = SimulatedTransport()
    set_transport_override(transport)

    try:
        yield {
            "brokerage_id": brokerage_id,
            "other_brokerage_id": other_brokerage_id,
            "listing_id": listing_id,
            "conversation_id": conversation_id,
            "buyer_phone": buyer_phone,
            "agent_phone": agent_phone,
            "other_agent_phone": other_agent_phone,
            "brokerage_ai_number": brokerage_ai_number,
            "agents_ai_number": agents_ai_number,
            "other_agents_ai_number": other_agents_ai_number,
            "agent_user_id": agent_user_id,
            "token": token,
            "transport": transport,
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        set_transport_override(None)
        with SessionLocal() as db:
            from app.models.db_models import DBAgentNotification, DBAgentRelaySession, DBRelayOutboxItem

            for brokerage in (brokerage_id, other_brokerage_id):
                db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBAgentNotification).filter(DBAgentNotification.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBRelayOutboxItem).filter(DBRelayOutboxItem.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBAgentRelaySession).filter(DBAgentRelaySession.brokerage_id == brokerage).delete(synchronize_session=False)
            db.query(DBLeadAction).filter(DBLeadAction.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBDraftReply).filter(DBDraftReply.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBAgentMessageRoute).filter(DBAgentMessageRoute.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBMessageQueue).filter(
                DBMessageQueue.from_number.in_([buyer_phone, agent_phone])
            ).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([brokerage_id, other_brokerage_id])).delete(synchronize_session=False)
            safe_commit(db)


def _pause(seed, source="dashboard"):
    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_id"])
        return set_ai_mode(
            db,
            conv,
            mode=AI_MODE_AGENT_CONTROLLED,
            actor_user_id=seed["agent_user_id"],
            source=source,
        )


# ── Checklist 8: default off — baseline untouched ──────────────────────────────


def test_new_conversations_default_to_active(takeover_seed):
    seed = takeover_seed
    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_id"])
        assert conv.ai_mode == AI_MODE_ACTIVE
        assert find_agent_controlled_conversation(
            db,
            brokerage_id=seed["brokerage_id"],
            buyer_phone=seed["buyer_phone"],
            listing_id=seed["listing_id"],
        ) is None


def test_keyword_parser_only_matches_bare_keywords():
    assert parse_mode_keyword("TAKEOVER") == "takeover"
    assert parse_mode_keyword("  resume  ") == "resume"
    assert parse_mode_keyword("Takeover.\n\n[Ref: ABC1234]", "ABC1234") == "takeover"
    assert parse_mode_keyword("Please take over this one") is None
    assert parse_mode_keyword("resume the viewing tomorrow") is None
    assert parse_mode_keyword("") is None


# ── Checklist 1: pause via dashboard → raw forward, no AI reply ────────────────


def test_paused_conversation_forwards_raw_and_never_answers(takeover_seed):
    seed = takeover_seed
    transport = seed["transport"]
    result = _pause(seed, source="dashboard")
    assert result["changed"] is True

    with SessionLocal() as db:
        db.add(DBMessageQueue(
            from_number=seed["buyer_phone"],
            to_number=seed["brokerage_ai_number"],
            body="Is the unit still available? What floor is it on?",
            message_sid=f"tko-msg-{uuid.uuid4().hex[:8]}",
            listing_id=seed["listing_id"],
        ))
        safe_commit(db)
        queue_ids = [
            row.id
            for row in db.query(DBMessageQueue)
            .filter(DBMessageQueue.from_number == seed["buyer_phone"])
            .all()
        ]

    asyncio.run(_handle_batch(
        phone=seed["buyer_phone"],
        combined_body="Is the unit still available? What floor is it on?",
        listing_id=seed["listing_id"],
        to_number=seed["brokerage_ai_number"],
        message_sid=f"tko-batch-{uuid.uuid4().hex[:8]}",
        media_urls=[],
        media_content_types=[],
        metadata_items=[],
        ids=queue_ids,
    ))

    # No AI reply to the buyer.
    assert transport.messages_to_buyer(seed["buyer_phone"]) == []
    # Raw forward to the agent on Agents AI, with a [Ref: …] route.
    forwards = [
        send for send in transport.messages_to_agents_ai()
        if send.escalation_type == "takeover_forward"
    ]
    assert len(forwards) == 1
    assert "Is the unit still available?" in forwards[0].body
    assert "[Ref:" in forwards[0].body
    assert forwards[0].to_number == seed["agent_phone"]

    with SessionLocal() as db:
        # Inbox shows the buyer message as unanswered (persisted, role=user, no reply after it).
        messages = (
            db.query(DBMessage)
            .filter(DBMessage.conversation_id == seed["conversation_id"])
            .order_by(DBMessage.timestamp.asc())
            .all()
        )
        assert messages[-1].role == "user"
        assert messages[-1].metadata_json.get("source") == "takeover_raw_forward"
        # Queue rows consumed.
        pending = (
            db.query(DBMessageQueue)
            .filter(
                DBMessageQueue.from_number == seed["buyer_phone"],
                DBMessageQueue.status == "pending",
            )
            .count()
        )
        assert pending == 0
        # The forward minted a consumable route for the agent's quote-reply.
        route = (
            db.query(DBAgentMessageRoute)
            .filter(
                DBAgentMessageRoute.conversation_id == seed["conversation_id"],
                DBAgentMessageRoute.escalation_type == "takeover_forward",
            )
            .one()
        )
        assert route.agent_phone == seed["agent_phone"]
        event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.conversation_id == seed["conversation_id"],
                DBComplianceEvent.event_type == "takeover_buyer_message_forwarded",
            )
            .one()
        )
        assert event.details["forwarded"] is True


# ── Checklist 2 + 5: TAKEOVER quote-reply via webhook ──────────────────────────


def test_takeover_keyword_via_webhook_persists_whatsapp_source(client, monkeypatch, takeover_seed):
    seed = takeover_seed
    transport = seed["transport"]
    monkeypatch.setattr("app.api.whatsapp.TWILIO_AUTH_TOKEN", "")

    response = client.post(
        "/api/v1/whatsapp/webhook",
        data={
            "From": f"whatsapp:{seed['agent_phone']}",
            "To": f"whatsapp:{seed['agents_ai_number']}",
            "Body": f"TAKEOVER\n\n[Ref: {seed['token']}]",
            "MessageSid": f"tko-keyword-{uuid.uuid4().hex[:8]}",
            "NumMedia": "0",
        },
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_id"])
        assert conv.ai_mode == AI_MODE_AGENT_CONTROLLED
        assert conv.ai_mode_change_source == "whatsapp"
        assert conv.ai_mode_changed_by == seed["agent_user_id"]

    # Confirmation received on Agents AI; keyword never reaches the buyer.
    confirmations = [
        send for send in transport.messages_to_agents_ai()
        if "AI paused for" in send.body
    ]
    assert len(confirmations) == 1
    assert "Ahmed" in confirmations[0].body
    assert "RESUME" in confirmations[0].body
    assert transport.messages_to_buyer(seed["buyer_phone"]) == []


def test_takeover_keyword_without_ref_asks_for_quote_and_never_guesses(takeover_seed):
    seed = takeover_seed
    transport = seed["transport"]

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        inbound = transport.parse_inbound({
            "From": seed["agent_phone"],
            "To": seed["agents_ai_number"],
            "Body": "TAKEOVER",
            "MessageSid": f"tko-noref-{uuid.uuid4().hex[:8]}",
        })
        result = handle_agents_ai_mode_keyword(db, brokerage=brokerage, inbound=inbound)
        assert result is not None
        assert result.status == "missing_ref"

        conv = db.get(DBConversation, seed["conversation_id"])
        assert conv.ai_mode == AI_MODE_ACTIVE  # never guessed

    prompts = [
        send for send in transport.messages_to_agents_ai()
        if "quote-reply" in send.body.lower()
    ]
    assert prompts
    assert transport.messages_to_buyer(seed["buyer_phone"]) == []


def test_non_keyword_agent_reply_still_relays(takeover_seed):
    seed = takeover_seed
    transport = seed["transport"]

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        inbound = transport.inject_agent_reply(
            envelope_token=seed["token"],
            body_without_token="Yes it's available — 11th floor.",
            agents_ai_number=seed["agents_ai_number"],
            agent_phone=seed["agent_phone"],
        )
        assert handle_agents_ai_mode_keyword(db, brokerage=brokerage, inbound=inbound) is None


# ── Checklist 3: drafts auto-snoozed ───────────────────────────────────────────


def test_pending_drafts_auto_snoozed_with_takeover_reason(takeover_seed):
    seed = takeover_seed
    with SessionLocal() as db:
        db.add(DBDraftReply(
            brokerage_id=seed["brokerage_id"],
            conversation_id=seed["conversation_id"],
            listing_id=seed["listing_id"],
            buyer_phone=seed["buyer_phone"],
            agent_user_id=seed["agent_user_id"],
            intent="follow_up",
            draft_text="Hi Ahmed, just checking in.",
            source="morning_hot_list",
            status="draft",
        ))
        safe_commit(db)

    result = _pause(seed)
    assert len(result["snoozed_draft_ids"]) == 1

    with SessionLocal() as db:
        draft = (
            db.query(DBDraftReply)
            .filter(DBDraftReply.conversation_id == seed["conversation_id"])
            .one()
        )
        assert draft.status == "snoozed"
        assert draft.metadata_json["snooze_reason"] == "takeover"
        assert draft.metadata_json["snoozed_until"]


def test_hot_list_refresh_skips_draft_creation_while_agent_controlled(takeover_seed):
    seed = takeover_seed
    _pause(seed)
    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_id"])
        score = HotListScore(
            signal="stale",
            urgency_score=70,
            next_action="follow_up",
            next_action_reason="No reply in 4 days",
            status="active",
            task_type="whatsapp",
            task_title="Follow up with Ahmed",
            task_description="Check in on Takeover Towers interest",
            task_priority="normal",
            due_at=datetime.utcnow(),
            last_buyer_message_at=None,
            latest_message_at=None,
            buyer_message_count=1,
            stale=True,
        )
        draft = ensure_follow_up_draft(
            db,
            conv,
            agent_user_id=seed["agent_user_id"],
            score=score,
        )
        assert draft is None


# ── Checklist 4 + 6: resume + compliance events ────────────────────────────────


def test_resume_keyword_restores_concierge_and_writes_compliance_events(takeover_seed):
    seed = takeover_seed
    transport = seed["transport"]
    _pause(seed, source="dashboard")

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        inbound = transport.inject_agent_reply(
            envelope_token=seed["token"],
            body_without_token="RESUME",
            agents_ai_number=seed["agents_ai_number"],
            agent_phone=seed["agent_phone"],
        )
        result = handle_agents_ai_mode_keyword(db, brokerage=brokerage, inbound=inbound)
        assert result is not None
        assert result.status == "mode_set"
        assert result.mode == AI_MODE_ACTIVE

        conv = db.get(DBConversation, seed["conversation_id"])
        assert conv.ai_mode == AI_MODE_ACTIVE
        assert conv.ai_mode_change_source == "whatsapp"

        # Next buyer message is NOT gated: the takeover lookup finds nothing.
        assert find_agent_controlled_conversation(
            db,
            brokerage_id=seed["brokerage_id"],
            buyer_phone=seed["buyer_phone"],
            listing_id=seed["listing_id"],
        ) is None

        # Compliance events for both transitions (checklist 6).
        events = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.conversation_id == seed["conversation_id"],
                DBComplianceEvent.event_type == "conversation_ai_mode_changed",
            )
            .order_by(DBComplianceEvent.created_at.asc())
            .all()
        )
        modes = [event.details["mode"] for event in events]
        assert modes == [AI_MODE_AGENT_CONTROLLED, AI_MODE_ACTIVE]
        sources = [event.details["source"] for event in events]
        assert sources == ["dashboard", "whatsapp"]

    # Keyword consumed — nothing sent to the buyer (checklist 5).
    assert transport.messages_to_buyer(seed["buyer_phone"]) == []
    resumed = [
        send for send in transport.messages_to_agents_ai()
        if "AI resumed for" in send.body
    ]
    assert len(resumed) == 1


# ── Checklist 7: cross-tenant isolation ────────────────────────────────────────


def test_takeover_token_is_brokerage_scoped(takeover_seed):
    seed = takeover_seed
    transport = seed["transport"]

    with SessionLocal() as db:
        other = db.get(DBBrokerage, seed["other_brokerage_id"])
        # Agent of brokerage B presents brokerage A's token on B's Agents AI.
        inbound = transport.parse_inbound({
            "From": seed["other_agent_phone"],
            "To": seed["other_agents_ai_number"],
            "Body": f"TAKEOVER\n\n[Ref: {seed['token']}]",
            "MessageSid": f"tko-cross-{uuid.uuid4().hex[:8]}",
        })
        result = handle_agents_ai_mode_keyword(db, brokerage=other, inbound=inbound)
        assert result is not None
        assert result.status == "unknown_ref"

        conv = db.get(DBConversation, seed["conversation_id"])
        assert conv.ai_mode == AI_MODE_ACTIVE  # untouched


def test_wrong_agent_phone_cannot_toggle_mode(takeover_seed):
    seed = takeover_seed
    transport = seed["transport"]

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        inbound = transport.parse_inbound({
            "From": seed["other_agent_phone"],
            "To": seed["agents_ai_number"],
            "Body": f"TAKEOVER\n\n[Ref: {seed['token']}]",
            "MessageSid": f"tko-wrong-{uuid.uuid4().hex[:8]}",
        })
        result = handle_agents_ai_mode_keyword(db, brokerage=brokerage, inbound=inbound)
        assert result is not None
        assert result.status == "wrong_agent"

        conv = db.get(DBConversation, seed["conversation_id"])
        assert conv.ai_mode == AI_MODE_ACTIVE


def test_dashboard_ai_mode_endpoint_scoped_to_brokerage(client, takeover_seed):
    seed = takeover_seed

    # Agent of the owning brokerage can pause.
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seed["agent_user_id"],
        email="tko@example.com",
    )
    response = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/ai-mode",
        json={"mode": AI_MODE_AGENT_CONTROLLED},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ai_mode"] == AI_MODE_AGENT_CONTROLLED
    assert payload["changed"] is True
    assert payload["ai_mode_change_source"] == "dashboard"

    # A user with no membership in that brokerage gets a 403/404 — never the row.
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=f"outsider-{uuid.uuid4().hex[:6]}",
        email="outsider@example.com",
    )
    response = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/ai-mode",
        json={"mode": AI_MODE_ACTIVE},
    )
    assert response.status_code in {403, 404}

    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_id"])
        assert conv.ai_mode == AI_MODE_AGENT_CONTROLLED  # outsider changed nothing
