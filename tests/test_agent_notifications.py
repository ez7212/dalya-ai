"""
DAL-162 — Agent notification framework.

Covers the spec verification checklist:
  1. Each catalog event fires exactly once for its trigger (dedupe key honored
     on retried webhooks/jobs).
  2. Quiet hours: hot-buyer reply at 23:30 GST queues for the morning digest;
     a tenant decline at 23:30 still sends immediately.
  3. Deep links resolve to the correct conversation for the correct agent.
  4. Preference toggle off → event suppressed AND recorded (audit row exists).
  5. Rate guard collapses a forced flood into one overflow message.
  6. Cross-tenant + assignment scoping: notification rows are agent-scoped.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.core.agent_notifications import (
    RATE_GUARD_PER_HOUR,
    notify_agent,
    send_morning_digest,
)
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBAgentNotification,
    DBAgentProfile,
    DBBrokerage,
    DBConversation,
    DBDraftReply,
    DBLeadAssignment,
    DBListing,
    DBMessage,
)


def _gst(hour: int, minute: int = 0) -> datetime:
    """A UTC instant that is the given local wall time in Asia/Dubai (GST, UTC+4)."""
    local = datetime(2026, 6, 10, hour, minute, tzinfo=ZoneInfo("Asia/Dubai"))
    return local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


@pytest.fixture
def notify_seed(monkeypatch):
    monkeypatch.setenv("DASHBOARD_BASE_URL", "https://app.dalya.test")

    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"ntf-brokerage-{suffix}"
    listing_id = f"ntf-listing-{suffix}"
    buyer_phone = f"+97156677{suffix[:4]}"
    agent_user_id = f"ntf-agent-{suffix}"
    other_agent_user_id = f"ntf-agent2-{suffix}"
    agent_phone = f"+97157777{suffix[:4]}"
    other_agent_phone = f"+97157778{suffix[:4]}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Notify Brokerage",
            slug=f"ntf-{suffix}",
            status="active",
            brokerage_ai_number=f"+97158877{suffix[:4]}",
            agents_ai_number=f"+97159977{suffix[:4]}",
        ))
        for user_id, phone in ((agent_user_id, agent_phone), (other_agent_user_id, other_agent_phone)):
            db.add(DBAgentProfile(
                brokerage_id=brokerage_id,
                user_id=user_id,
                full_name=f"Agent {user_id[-4:]}",
                display_name=f"Agent {user_id[-4:]}",
                whatsapp_phone=phone,
                rera_broker_card_number=f"BRN-NTF-{user_id[-4:]}",
            ))
        db.add(DBListing(
            listing_id=listing_id,
            brokerage_id=brokerage_id,
            assigned_agent_id=agent_user_id,
            spa_data={"project": "Notify Heights", "unit_number": "901"},
            seller_asking_price=1_000_000,
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
        conv.buyer_name = "Noor"
        safe_commit(db)
        conversation_id = conv.conversation_id

    transport = SimulatedTransport()
    set_transport_override(transport)

    try:
        yield {
            "brokerage_id": brokerage_id,
            "listing_id": listing_id,
            "conversation_id": conversation_id,
            "buyer_phone": buyer_phone,
            "agent_user_id": agent_user_id,
            "other_agent_user_id": other_agent_user_id,
            "agent_phone": agent_phone,
            "other_agent_phone": other_agent_phone,
            "transport": transport,
        }
    finally:
        set_transport_override(None)
        with SessionLocal() as db:
            db.query(DBAgentNotification).filter(DBAgentNotification.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBDraftReply).filter(DBDraftReply.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == brokerage_id).delete(synchronize_session=False)
            safe_commit(db)


# ── Checklist 1: dedupe — exactly once per trigger ─────────────────────────────


def test_dedupe_key_prevents_double_push_on_retry(notify_seed):
    seed = notify_seed
    transport = seed["transport"]
    dedupe_key = f"hot_buyer_reply:{uuid.uuid4().hex[:8]}"

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        first = notify_agent(
            db,
            brokerage=brokerage,
            agent_user_id=seed["agent_user_id"],
            event_type="hot_buyer_reply",
            body="Your hot buyer Noor just replied.",
            dedupe_key=dedupe_key,
            conversation_id=seed["conversation_id"],
            now=_gst(11, 0),
        )
        retry = notify_agent(
            db,
            brokerage=brokerage,
            agent_user_id=seed["agent_user_id"],
            event_type="hot_buyer_reply",
            body="Your hot buyer Noor just replied.",
            dedupe_key=dedupe_key,
            conversation_id=seed["conversation_id"],
            now=_gst(11, 0),
        )
        assert first.notification_id == retry.notification_id

        rows = (
            db.query(DBAgentNotification)
            .filter(DBAgentNotification.dedupe_key == dedupe_key)
            .all()
        )
        assert len(rows) == 1

    pushes = [send for send in transport.messages_to_agents_ai() if "Noor just replied" in send.body]
    assert len(pushes) == 1


# ── Checklist 2: quiet hours — queue vs still-send ─────────────────────────────


def test_quiet_hours_queue_hot_reply_but_send_tenant_decline(notify_seed):
    seed = notify_seed
    transport = seed["transport"]
    late_night = _gst(23, 30)

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        queued = notify_agent(
            db,
            brokerage=brokerage,
            agent_user_id=seed["agent_user_id"],
            event_type="hot_buyer_reply",
            body="Hot buyer replied at 23:30.",
            dedupe_key=f"ntf-q-{uuid.uuid4().hex[:8]}",
            now=late_night,
        )
        assert queued.status == "queued_digest"
        assert queued.metadata_json.get("queued_reason") == "quiet_hours"

        sent = notify_agent(
            db,
            brokerage=brokerage,
            agent_user_id=seed["agent_user_id"],
            event_type="tenant_confirmation",
            body="Tenant declined tomorrow's viewing.",
            dedupe_key=f"ntf-t-{uuid.uuid4().hex[:8]}",
            now=late_night,
        )
        assert sent.status == "sent"

    bodies = [send.body for send in transport.messages_to_agents_ai()]
    assert any("Tenant declined" in body for body in bodies)
    assert not any("23:30" in body for body in bodies)

    # The queued item appears in the morning digest.
    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        digest = send_morning_digest(
            db,
            brokerage=brokerage,
            agent_user_id=seed["agent_user_id"],
            now=_gst(8, 0) + timedelta(days=1),
        )
        assert digest is not None
        assert "Hot buyer replied at 23:30." in digest.body

        requeued = (
            db.query(DBAgentNotification)
            .filter(
                DBAgentNotification.agent_user_id == seed["agent_user_id"],
                DBAgentNotification.status == "queued_digest",
            )
            .count()
        )
        assert requeued == 0  # digested

    digests = [send for send in transport.messages_to_agents_ai() if "Morning hot list" in send.body]
    assert len(digests) == 1


# ── Checklist 3: deep links ────────────────────────────────────────────────────


def test_deep_link_resolves_to_conversation_surface(notify_seed):
    seed = notify_seed
    transport = seed["transport"]

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        row = notify_agent(
            db,
            brokerage=brokerage,
            agent_user_id=seed["agent_user_id"],
            event_type="viewing_buyer_update",
            body="Noor confirmed the viewing.",
            dedupe_key=f"ntf-dl-{uuid.uuid4().hex[:8]}",
            conversation_id=seed["conversation_id"],
            deep_link_path=f"/agent/conversations/{seed['conversation_id']}",
            now=_gst(12, 0),
        )
        assert row.deep_link == f"https://app.dalya.test/agent/conversations/{seed['conversation_id']}"

    push = [send for send in transport.messages_to_agents_ai() if "Noor confirmed" in send.body][0]
    assert f"https://app.dalya.test/agent/conversations/{seed['conversation_id']}" in push.body
    assert push.to_number == seed["agent_phone"]  # the correct agent


# ── Checklist 4: preference off → suppressed and recorded ──────────────────────


def test_preference_toggle_off_suppresses_with_audit_row(notify_seed):
    seed = notify_seed
    transport = seed["transport"]

    with SessionLocal() as db:
        profile = (
            db.query(DBAgentProfile)
            .filter(
                DBAgentProfile.brokerage_id == seed["brokerage_id"],
                DBAgentProfile.user_id == seed["agent_user_id"],
            )
            .one()
        )
        profile.settings = {"notifications": {"events": {"feedback_received": False}}}
        safe_commit(db)

        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        row = notify_agent(
            db,
            brokerage=brokerage,
            agent_user_id=seed["agent_user_id"],
            event_type="feedback_received",
            body="Noor left feedback.",
            dedupe_key=f"ntf-sup-{uuid.uuid4().hex[:8]}",
            now=_gst(12, 0),
        )
        assert row.status == "suppressed_pref"
        # Audit row exists — not silently dropped.
        assert (
            db.query(DBAgentNotification)
            .filter(DBAgentNotification.notification_id == row.notification_id)
            .count()
            == 1
        )

    assert not any("left feedback" in send.body for send in transport.messages_to_agents_ai())


# ── Checklist 5: rate guard collapse ───────────────────────────────────────────


def test_rate_guard_collapses_flood_into_single_overflow_message(notify_seed):
    seed = notify_seed
    transport = seed["transport"]
    now = _gst(12, 0)

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        flood = RATE_GUARD_PER_HOUR + 5
        for index in range(flood):
            notify_agent(
                db,
                brokerage=brokerage,
                agent_user_id=seed["agent_user_id"],
                event_type="viewing_buyer_update",
                body=f"Update {index}",
                dedupe_key=f"ntf-flood-{uuid.uuid4().hex[:8]}",
                now=now,
            )
        sent = (
            db.query(DBAgentNotification)
            .filter(
                DBAgentNotification.agent_user_id == seed["agent_user_id"],
                DBAgentNotification.status == "sent",
            )
            .count()
        )
        collapsed = (
            db.query(DBAgentNotification)
            .filter(
                DBAgentNotification.agent_user_id == seed["agent_user_id"],
                DBAgentNotification.status == "collapsed_rate",
            )
            .count()
        )
        assert sent == RATE_GUARD_PER_HOUR
        assert collapsed == 5

    overflow = [send for send in transport.messages_to_agents_ai() if "more updates" in send.body]
    assert len(overflow) == 1  # one overflow message, not five


# ── Checklist 6: scoping is assignment-level, not just brokerage-level ────────


def test_notifications_are_agent_scoped_within_brokerage(notify_seed):
    seed = notify_seed
    transport = seed["transport"]

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        notify_agent(
            db,
            brokerage=brokerage,
            agent_user_id=seed["agent_user_id"],
            event_type="viewing_buyer_update",
            body="Noor rescheduled to Friday.",
            dedupe_key=f"ntf-scope-{uuid.uuid4().hex[:8]}",
            now=_gst(12, 0),
        )
        # Rows are scoped to the assigned agent only.
        other_rows = (
            db.query(DBAgentNotification)
            .filter(
                DBAgentNotification.brokerage_id == seed["brokerage_id"],
                DBAgentNotification.agent_user_id == seed["other_agent_user_id"],
            )
            .count()
        )
        assert other_rows == 0

    # The push went to agent A's phone; agent B's phone got nothing.
    pushes = [send for send in transport.messages_to_agents_ai() if "rescheduled" in send.body]
    assert len(pushes) == 1
    assert pushes[0].to_number == seed["agent_phone"]
    assert not any(
        send.to_number == seed["other_agent_phone"] for send in transport.messages_to_agents_ai()
    )


# ── Digest extras: drafts pending + stale takeover ride along ──────────────────


def test_morning_digest_includes_drafts_and_stale_takeover(notify_seed):
    seed = notify_seed
    transport = seed["transport"]
    now = _gst(8, 0)

    with SessionLocal() as db:
        db.add(DBDraftReply(
            brokerage_id=seed["brokerage_id"],
            conversation_id=seed["conversation_id"],
            listing_id=seed["listing_id"],
            buyer_phone=seed["buyer_phone"],
            agent_user_id=seed["agent_user_id"],
            intent="follow_up",
            draft_text="Checking in.",
            source="morning_hot_list",
            status="draft",
        ))
        conv = db.get(DBConversation, seed["conversation_id"])
        conv.assigned_agent_id = seed["agent_user_id"]
        conv.ai_mode = "agent_controlled"
        conv.ai_mode_changed_at = now - timedelta(hours=49)
        safe_commit(db)

        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        digest = send_morning_digest(
            db,
            brokerage=brokerage,
            agent_user_id=seed["agent_user_id"],
            now=now,
        )
        assert digest is not None
        assert "1 AI draft" in digest.body
        assert "still paused for Noor" in digest.body

    digests = [send for send in transport.messages_to_agents_ai() if "Morning hot list" in send.body]
    assert len(digests) == 1
