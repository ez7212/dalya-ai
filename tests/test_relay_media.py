"""
DAL-161 — Outbound media via WhatsApp agent relay (batching window).

Covers checklist items 4–10, 12–23 of the combined DAL-160/161 list: tiered
routing (caption token / quote-reply session / held session / escalation
match), UNDO, parking + burst batches + expiry, caption hygiene on forwards,
per-item 24h windows, cross-tenant token isolation, and routing-method audit.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.core.agent_relay import relay_agent_reply
from app.core.escalation_threads import is_media_request, mark_thread_media_requested
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.core.relay_media import (
    IMPLICIT_HOLD_SECONDS,
    active_session,
    handle_agents_ai_undo_keyword,
    process_relay_outbox,
    route_agents_ai_inbound,
)
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBAgentMessageRoute,
    DBAgentProfile,
    DBAgentRelaySession,
    DBBrokerage,
    DBComplianceEvent,
    DBConversation,
    DBEscalationThread,
    DBLeadAction,
    DBLeadAssignment,
    DBListing,
    DBMediaAsset,
    DBMessage,
    DBRelayOutboxItem,
)

PDF_BYTES = b"%PDF-1.4 relay fixture"


def _listing_kwargs(listing_id, brokerage_id, agent_user_id, project, unit):
    return dict(
        listing_id=listing_id,
        brokerage_id=brokerage_id,
        assigned_agent_id=agent_user_id,
        spa_data={
            "project": project,
            "unit_number": unit,
            "developer": "Emaar",
            "property_type": "Apartment",
            "bedrooms": 2,
            "purchase_price_aed": 2_000_000,
        },
        seller_asking_price=2_000_000,
        commission_rate=0.02,
        property_type="ready",
        additional_fees=[],
        seller_qa=[],
        media_urls=[],
        unit_profile={},
        unit_profile_history=[],
        processing_stages={},
    )


@pytest.fixture
def relay_media_seed(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("PUBLIC_URL", "https://dalya.test")

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(PDF_BYTES)

    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"rly-brokerage-{suffix}"
    other_brokerage_id = f"rly-other-{suffix}"
    agent_user_id = f"rly-agent-{suffix}"
    agent_phone = f"+97157755{suffix[:4]}"
    other_agent_phone = f"+97157766{suffix[:4]}"
    agents_ai_number = f"+97159955{suffix[:4]}"
    other_agents_ai_number = f"+97159966{suffix[:4]}"
    brokerage_ai_number = f"+97158855{suffix[:4]}"

    buyers = {
        "A": (f"+97156655{suffix[:4]}", f"rly-listing-a-{suffix}", f"TOKA{suffix[:6].upper()}", "Ahmed"),
        "B": (f"+97156656{suffix[:4]}", f"rly-listing-b-{suffix}", f"TOKB{suffix[:6].upper()}", "Bilal"),
        "C": (f"+97156657{suffix[:4]}", f"rly-listing-c-{suffix}", f"TOKC{suffix[:6].upper()}", "Chloe"),
    }

    conversations: dict[str, str] = {}
    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Relay Media Brokerage",
            slug=f"rly-{suffix}",
            status="active",
            brokerage_ai_number=brokerage_ai_number,
            agents_ai_number=agents_ai_number,
        ))
        db.add(DBBrokerage(
            brokerage_id=other_brokerage_id,
            name="Relay Other Brokerage",
            slug=f"rly-other-{suffix}",
            status="active",
            brokerage_ai_number=f"+97158866{suffix[:4]}",
            agents_ai_number=other_agents_ai_number,
        ))
        db.add(DBAgentProfile(
            brokerage_id=brokerage_id,
            user_id=agent_user_id,
            full_name="Relay Agent",
            display_name="Relay Agent",
            whatsapp_phone=agent_phone,
            rera_broker_card_number=f"BRN-RLY-{suffix}",
        ))
        for key, (buyer_phone, listing_id, token, name) in buyers.items():
            db.add(DBListing(**_listing_kwargs(
                listing_id, brokerage_id, agent_user_id, f"Relay Tower {key}", f"{key}01",
            )))
        safe_commit(db)
        for key, (buyer_phone, listing_id, token, name) in buyers.items():
            conv = crud.get_or_create_conversation(db, buyer_phone, listing_id)
            conv.buyer_name = name
            db.add(DBMessage(
                conversation_id=conv.conversation_id,
                role="user",
                content=f"Hi, interested in Relay Tower {key}",
            ))
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
            conversations[key] = conv.conversation_id
        safe_commit(db)

    transport = SimulatedTransport()
    set_transport_override(transport)

    try:
        yield {
            "brokerage_id": brokerage_id,
            "other_brokerage_id": other_brokerage_id,
            "agent_user_id": agent_user_id,
            "agent_phone": agent_phone,
            "other_agent_phone": other_agent_phone,
            "agents_ai_number": agents_ai_number,
            "other_agents_ai_number": other_agents_ai_number,
            "brokerage_ai_number": brokerage_ai_number,
            "buyers": buyers,
            "conversations": conversations,
            "pdf_path": str(pdf_path),
            "transport": transport,
        }
    finally:
        set_transport_override(None)
        with SessionLocal() as db:
            from app.models.db_models import DBEscalationThreadQuestion

            conversation_ids = list(conversations.values())
            for brokerage in (brokerage_id, other_brokerage_id):
                db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBRelayOutboxItem).filter(DBRelayOutboxItem.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBAgentRelaySession).filter(DBAgentRelaySession.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBMediaAsset).filter(DBMediaAsset.brokerage_id == brokerage).delete(synchronize_session=False)
                thread_ids = [
                    row.thread_id
                    for row in db.query(DBEscalationThread.thread_id)
                    .filter(DBEscalationThread.brokerage_id == brokerage)
                    .all()
                ]
                if thread_ids:
                    db.query(DBEscalationThreadQuestion).filter(
                        DBEscalationThreadQuestion.thread_id.in_(thread_ids)
                    ).delete(synchronize_session=False)
                db.query(DBEscalationThread).filter(DBEscalationThread.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBAgentMessageRoute).filter(DBAgentMessageRoute.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id == brokerage).delete(synchronize_session=False)
            db.query(DBLeadAction).filter(DBLeadAction.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
            for _, listing_id, _, _ in buyers.values():
                db.query(DBListing).filter(DBListing.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([brokerage_id, other_brokerage_id])).delete(synchronize_session=False)
            safe_commit(db)


def _media_inbound(seed, *, body="", token_quote=None, forwarded=False, message_sid=None, files=1, agent_phone=None, agents_number=None):
    transport = seed["transport"]
    form = {
        "From": agent_phone or seed["agent_phone"],
        "To": agents_number or seed["agents_ai_number"],
        "Body": f"{body}\n\n[Ref: {token_quote}]" if token_quote else body,
        "MessageSid": message_sid or f"rly-media-{uuid.uuid4().hex[:8]}",
        "NumMedia": str(files),
    }
    for index in range(files):
        form[f"MediaUrl{index}"] = seed["pdf_path"]
        form[f"MediaContentType{index}"] = "application/pdf"
    if forwarded:
        form["Forwarded"] = "true"
    return transport.parse_inbound(form)


def _text_inbound(seed, body, *, token_quote=None, agent_phone=None, agents_number=None):
    transport = seed["transport"]
    return transport.parse_inbound({
        "From": agent_phone or seed["agent_phone"],
        "To": agents_number or seed["agents_ai_number"],
        "Body": f"{body}\n\n[Ref: {token_quote}]" if token_quote else body,
        "MessageSid": f"rly-text-{uuid.uuid4().hex[:8]}",
    })


def _route(db, seed, inbound, now=None):
    brokerage = db.get(DBBrokerage, seed["brokerage_id"])
    return route_agents_ai_inbound(db, brokerage=brokerage, inbound=inbound, now=now)


def _seed_media_request_thread(seed, key, *, alerted_hours_ago=1.0, state="open"):
    buyer_phone, listing_id, _, _ = seed["buyers"][key]
    with SessionLocal() as db:
        thread = DBEscalationThread(
            brokerage_id=seed["brokerage_id"],
            conversation_id=seed["conversations"][key],
            listing_id=listing_id,
            buyer_phone=buyer_phone,
            agent_user_id=seed["agent_user_id"],
            agent_phone=seed["agent_phone"],
            category="regulatory_documents",
            state=state,
            escalation_type="materials_request",
            alerted_at=datetime.utcnow() - timedelta(hours=alerted_hours_ago),
            last_buyer_message_at=datetime.utcnow(),
        )
        mark_thread_media_requested(thread)
        db.add(thread)
        safe_commit(db)
        return thread.thread_id


# ── Checklist 4: sequential batch via session ──────────────────────────────────


def test_sequential_quote_then_unquoted_files_route_via_session(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    now = datetime.utcnow()
    buyer_a = seed["buyers"]["A"][0]
    token_a = seed["buyers"]["A"][2]

    # Quote buyer A's ref with a short text — relays AND opens the session.
    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        inbound = transport.inject_agent_reply(
            envelope_token=token_a,
            body_without_token="Brochure coming.",
            agents_ai_number=seed["agents_ai_number"],
            agent_phone=seed["agent_phone"],
        )
        result = relay_agent_reply(db, brokerage=brokerage, inbound=inbound)
        assert result.relayed is True
        assert active_session(db, brokerage_id=seed["brokerage_id"], agent_phone=seed["agent_phone"]) is not None

    # Four unquoted follow-up PDFs route tier-3 with recipient-naming acks.
    item_ids = []
    for _ in range(4):
        with SessionLocal() as db:
            routed = _route(db, seed, _media_inbound(seed), now=now)
            assert routed.status == "held"
            assert routed.routing_method == "session"
            item_ids.extend(routed.item_ids)

    acks = [send for send in transport.messages_to_agents_ai() if "sending in" in send.body]
    assert len(acks) == 4
    assert all("Ahmed" in ack.body and "UNDO" in ack.body for ack in acks)
    # Held — nothing has reached the buyer yet beyond the quoted text.
    assert len([send for send in transport.messages_to_buyer(buyer_a) if send.media_url]) == 0

    # Hold expires → all four released to buyer A.
    with SessionLocal() as db:
        stats = process_relay_outbox(db, now=now + timedelta(seconds=IMPLICIT_HOLD_SECONDS + 1))
        assert stats["released"] == 4

    media_sends = [send for send in transport.messages_to_buyer(buyer_a) if send.media_url]
    assert len(media_sends) == 4
    with SessionLocal() as db:
        events = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.conversation_id == seed["conversations"]["A"],
                DBComplianceEvent.event_type == "agent_media_sent",
            )
            .all()
        )
        assert all(event.details["routing_method"] == "session" for event in events)


# ── Checklist 5: interleaved caption tokens ────────────────────────────────────


def test_interleaved_caption_tokens_route_immediately_without_session(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    token_a, token_b = seed["buyers"]["A"][2], seed["buyers"]["B"][2]
    buyer_a, buyer_b = seed["buyers"]["A"][0], seed["buyers"]["B"][0]

    for token in (token_a, token_b, token_a):
        with SessionLocal() as db:
            routed = _route(db, seed, _media_inbound(seed, body=f"Floor plan #{token}"))
            assert routed.status == "sent"
            assert routed.routing_method == "caption_token"

    sends_a = [send for send in transport.messages_to_buyer(buyer_a) if send.media_url]
    sends_b = [send for send in transport.messages_to_buyer(buyer_b) if send.media_url]
    assert len(sends_a) == 2 and len(sends_b) == 1
    # Tokens stripped from the delivered caption.
    assert all(f"#{token_a}" not in (send.body or "") for send in sends_a)
    assert all(f"#{token_b}" not in (send.body or "") for send in sends_b)
    assert any("Floor plan" in (send.body or "") for send in sends_a)

    with SessionLocal() as db:
        # No session created or consumed by caption-token routing.
        assert active_session(db, brokerage_id=seed["brokerage_id"], agent_phone=seed["agent_phone"]) is None


# ── Checklist 6: caption typo never fuzzy-matches ──────────────────────────────


def test_caption_token_typo_falls_through_never_fuzzy(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    buyer_a = seed["buyers"]["A"][0]

    # No session → media with a typo token parks (the media bounce path).
    with SessionLocal() as db:
        routed = _route(db, seed, _media_inbound(seed, body="#WRONGTOK99 here you go"))
        assert routed.status == "parked"
    assert [send for send in transport.messages_to_buyer(buyer_a) if send.media_url] == []

    # With an active session for A, the typo falls through to the session (held).
    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        relay_agent_reply(db, brokerage=brokerage, inbound=transport.inject_agent_reply(
            envelope_token=seed["buyers"]["A"][2],
            body_without_token="opening session",
            agents_ai_number=seed["agents_ai_number"],
            agent_phone=seed["agent_phone"],
        ))
        routed = _route(db, seed, _media_inbound(seed, body="#WRONGTOK99 again"))
        assert routed.status == "held"
        assert routed.routing_method == "session"
        assert routed.conversation_id == seed["conversations"]["A"]


# ── Checklist 7: UNDO cancels all held items ───────────────────────────────────


def test_undo_cancels_all_held_items_before_release(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    buyer_a = seed["buyers"]["A"][0]
    now = datetime.utcnow()

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        relay_agent_reply(db, brokerage=brokerage, inbound=transport.inject_agent_reply(
            envelope_token=seed["buyers"]["A"][2],
            body_without_token="files coming",
            agents_ai_number=seed["agents_ai_number"],
            agent_phone=seed["agent_phone"],
        ))
        for _ in range(2):
            _route(db, seed, _media_inbound(seed), now=now)

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        undo = handle_agents_ai_undo_keyword(
            db, brokerage=brokerage, inbound=_text_inbound(seed, "UNDO"), now=now
        )
        assert undo is not None
        assert undo.details["cancelled_count"] == 2

        items = (
            db.query(DBRelayOutboxItem)
            .filter(DBRelayOutboxItem.brokerage_id == seed["brokerage_id"])
            .all()
        )
        assert all(item.status == "cancelled" for item in items)
        assert all(item.cancelled_reason == "undo" for item in items)

        # Release pass sends nothing.
        stats = process_relay_outbox(db, now=now + timedelta(seconds=IMPLICIT_HOLD_SECONDS + 1))
        assert stats["released"] == 0

    assert [send for send in transport.messages_to_buyer(buyer_a) if send.media_url] == []
    confirmations = [send for send in transport.messages_to_agents_ai() if "Cancelled" in send.body]
    assert confirmations


# ── Checklist 8: session expiry at minute 11 ───────────────────────────────────


def test_session_expired_text_bounces_with_routing_prompt(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    now = datetime.utcnow()

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        relay_agent_reply(db, brokerage=brokerage, inbound=transport.inject_agent_reply(
            envelope_token=seed["buyers"]["A"][2],
            body_without_token="opening session",
            agents_ai_number=seed["agents_ai_number"],
            agent_phone=seed["agent_phone"],
        ))

    with SessionLocal() as db:
        routed = _route(db, seed, _text_inbound(seed, "And tell him about parking"), now=now + timedelta(minutes=11))
        assert routed.status == "bounced_no_route"

    bounces = [send for send in transport.messages_to_agents_ai() if "couldn't tell which buyer" in send.body]
    assert bounces
    assert [send for send in transport.messages_to_buyer(seed["buyers"]["A"][0]) if "parking" in (send.body or "")] == []


# ── Checklist 9: new quote closes old session; old holds keep their buyer ─────


def test_new_quote_mid_session_releases_old_holds_to_old_buyer(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    now = datetime.utcnow()
    buyer_a, buyer_b = seed["buyers"]["A"][0], seed["buyers"]["B"][0]

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        relay_agent_reply(db, brokerage=brokerage, inbound=transport.inject_agent_reply(
            envelope_token=seed["buyers"]["A"][2],
            body_without_token="A's files coming",
            agents_ai_number=seed["agents_ai_number"],
            agent_phone=seed["agent_phone"],
        ))
        held = _route(db, seed, _media_inbound(seed), now=now)
        assert held.conversation_id == seed["conversations"]["A"]

        # Quote B's ref mid-session: closes A's session, routes this file to B.
        routed_b = _route(db, seed, _media_inbound(seed, token_quote=seed["buyers"]["B"][2]), now=now)
        assert routed_b.routing_method == "quote_reply"
        assert routed_b.conversation_id == seed["conversations"]["B"]

        sessions = (
            db.query(DBAgentRelaySession)
            .filter(
                DBAgentRelaySession.brokerage_id == seed["brokerage_id"],
                DBAgentRelaySession.status == "active",
            )
            .all()
        )
        assert len(sessions) == 1
        assert sessions[0].conversation_id == seed["conversations"]["B"]

        # A's still-held item releases to A — closing a session never re-routes in-flight items.
        stats = process_relay_outbox(db, now=now + timedelta(seconds=IMPLICIT_HOLD_SECONDS + 1))
        assert stats["released"] == 1

    assert len([send for send in transport.messages_to_buyer(buyer_a) if send.media_url]) == 1
    assert len([send for send in transport.messages_to_buyer(buyer_b) if send.media_url]) == 1


# ── Checklist 10: three-buyer fan-out with mixed window states ────────────────


def test_fan_out_mixed_window_states(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    buyer_a, buyer_b, buyer_c = (seed["buyers"][key][0] for key in "ABC")

    with SessionLocal() as db:
        # Close B's 24h window.
        db.query(DBMessage).filter(
            DBMessage.conversation_id == seed["conversations"]["B"],
            DBMessage.role == "user",
        ).update({"timestamp": datetime.utcnow() - timedelta(hours=25)}, synchronize_session=False)
        safe_commit(db)

    for key in "ABC":
        with SessionLocal() as db:
            routed = _route(db, seed, _media_inbound(seed, body=f"#{seed['buyers'][key][2]}"))
            assert routed.routing_method == "caption_token"

    assert len([send for send in transport.messages_to_buyer(buyer_a) if send.media_url]) == 1
    assert [send for send in transport.messages_to_buyer(buyer_b) if send.media_url] == []
    assert len([send for send in transport.messages_to_buyer(buyer_c) if send.media_url]) == 1
    bounces = [send for send in transport.messages_to_agents_ai() if "session window is closed" in send.body]
    assert len(bounces) == 1 and "Bilal" in bounces[0].body
    with SessionLocal() as db:
        cancelled = (
            db.query(DBRelayOutboxItem)
            .filter(
                DBRelayOutboxItem.conversation_id == seed["conversations"]["B"],
                DBRelayOutboxItem.status == "cancelled",
            )
            .one()
        )
        assert cancelled.cancelled_reason == "session_window_closed"


# ── Checklist 12: token forgery is brokerage-scoped ────────────────────────────


def test_cross_tenant_token_resolves_to_nothing(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    token_a = seed["buyers"]["A"][2]
    buyer_a = seed["buyers"]["A"][0]

    with SessionLocal() as db:
        other = db.get(DBBrokerage, seed["other_brokerage_id"])
        inbound = _media_inbound(
            seed,
            body=f"#{token_a}",
            agent_phone=seed["other_agent_phone"],
            agents_number=seed["other_agents_ai_number"],
        )
        routed = route_agents_ai_inbound(db, brokerage=other, inbound=inbound)
        # Token from brokerage A presented on brokerage B resolves to nothing → parked.
        assert routed.status == "parked"

    assert [send for send in transport.messages_to_buyer(buyer_a) if send.media_url] == []


# ── Checklists 13–16: parking, bursts, caption hygiene, expiry ─────────────────


def test_forwarded_pdf_parks_and_quote_reply_releases(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    buyer_a = seed["buyers"]["A"][0]

    with SessionLocal() as db:
        routed = _route(db, seed, _media_inbound(seed, body="Here you go Fatima — 2.1M list", forwarded=True))
        assert routed.status == "parked"

    prompts = [send for send in transport.messages_to_agents_ai() if "where should these go" in send.body]
    assert len(prompts) == 1

    # Quote-reply answer releases the batch immediately to the right buyer.
    with SessionLocal() as db:
        answer = _route(db, seed, _text_inbound(seed, "", token_quote=seed["buyers"]["A"][2]))
        assert answer.status == "parked_batch_routed"
        assert answer.item_ids

    sends = [send for send in transport.messages_to_buyer(buyer_a) if send.media_url]
    assert len(sends) == 1
    # Checklist 15: forwarded caption was stripped before delivery (PDPL).
    assert "Fatima" not in (sends[0].body or "")
    with SessionLocal() as db:
        events = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.conversation_id == seed["conversations"]["A"],
                DBComplianceEvent.event_type == "agent_media_sent",
            )
            .all()
        )
        assert [event.details["routing_method"] for event in events] == ["parking_prompt"]


def test_burst_forward_groups_into_one_batch_one_prompt(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    buyer_a = seed["buyers"]["A"][0]
    now = datetime.utcnow()

    with SessionLocal() as db:
        for _ in range(3):
            routed = _route(db, seed, _media_inbound(seed, forwarded=True), now=now)
            assert routed.status == "parked"
        batch_ids = {
            item.parked_batch_id
            for item in db.query(DBRelayOutboxItem)
            .filter(DBRelayOutboxItem.brokerage_id == seed["brokerage_id"], DBRelayOutboxItem.status == "parked")
            .all()
        }
        assert len(batch_ids) == 1

    prompts = [send for send in transport.messages_to_agents_ai() if "where should these go" in send.body or "who are these for" in send.body]
    assert len(prompts) == 1

    with SessionLocal() as db:
        answer = _route(db, seed, _text_inbound(seed, f"#{seed['buyers']['A'][2]}"), now=now)
        assert answer.status == "parked_batch_routed"
        assert len(answer.item_ids) == 3

    assert len([send for send in transport.messages_to_buyer(buyer_a) if send.media_url]) == 3


def test_direct_media_keeps_caption_minus_token(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    token_a = seed["buyers"]["A"][2]

    with SessionLocal() as db:
        _route(db, seed, _media_inbound(seed, body=f"Latest floor plan #{token_a}"))

    sends = [send for send in transport.messages_to_buyer(seed["buyers"]["A"][0]) if send.media_url]
    assert sends[0].body == "Latest floor plan"


def test_parked_media_expires_after_30_minutes_with_notice(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    now = datetime.utcnow()

    with SessionLocal() as db:
        routed = _route(db, seed, _media_inbound(seed, forwarded=True), now=now)
        assert routed.status == "parked"
        item_id = routed.item_ids[0]

    with SessionLocal() as db:
        # Force the parked item past expiry, then run the worker.
        db.query(DBRelayOutboxItem).filter(DBRelayOutboxItem.item_id == item_id).update(
            {"created_at": now - timedelta(minutes=31)}, synchronize_session=False
        )
        safe_commit(db)
        stats = process_relay_outbox(db, now=now)
        assert stats["expired"] == 1

        item = db.get(DBRelayOutboxItem, item_id)
        assert item.status == "expired"
        # Media asset retained per retention policy — never sent.
        asset = db.get(DBMediaAsset, item.media_asset_id)
        assert asset is not None

    notices = [send for send in transport.messages_to_agents_ai() if "discarded" in send.body]
    assert len(notices) == 1
    assert all(send.media_url is None for send in transport.messages_to_buyer(seed["buyers"]["A"][0]))


# ── Checklists 17–21: tier 4 escalation match ──────────────────────────────────


def test_session_takes_precedence_over_media_request_escalation(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    _seed_media_request_thread(seed, "B")

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        relay_agent_reply(db, brokerage=brokerage, inbound=transport.inject_agent_reply(
            envelope_token=seed["buyers"]["A"][2],
            body_without_token="session for A",
            agents_ai_number=seed["agents_ai_number"],
            agent_phone=seed["agent_phone"],
        ))
        routed = _route(db, seed, _media_inbound(seed, body="forwarded caption", forwarded=True))
        assert routed.routing_method == "session"
        assert routed.conversation_id == seed["conversations"]["A"]
        item = db.get(DBRelayOutboxItem, routed.item_ids[0])
        assert item.body == ""  # forwarded caption stripped on tier-3 too


def test_single_media_request_escalation_auto_routes_held_with_basis(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    now = datetime.utcnow()
    _seed_media_request_thread(seed, "B")

    with SessionLocal() as db:
        routed = _route(db, seed, _media_inbound(seed, forwarded=True), now=now)
        assert routed.status == "held"
        assert routed.routing_method == "escalation_match"
        assert routed.conversation_id == seed["conversations"]["B"]

    acks = [send for send in transport.messages_to_agents_ai() if "matched your open escalation" in send.body]
    assert len(acks) == 1 and "Bilal" in acks[0].body

    # UNDO during the hold cancels it.
    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        undo = handle_agents_ai_undo_keyword(db, brokerage=brokerage, inbound=_text_inbound(seed, "undo"), now=now)
        assert undo.details["cancelled_count"] == 1
    assert [send for send in transport.messages_to_buyer(seed["buyers"]["B"][0]) if send.media_url] == []


def test_two_media_request_escalations_park_with_numbered_options(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    _seed_media_request_thread(seed, "A")
    _seed_media_request_thread(seed, "B")

    with SessionLocal() as db:
        routed = _route(db, seed, _media_inbound(seed, forwarded=True))
        assert routed.status == "parked"

    prompts = [send for send in transport.messages_to_agents_ai() if "who are these for" in send.body]
    assert len(prompts) == 1
    assert "1 =" in prompts[0].body and "2 =" in prompts[0].body

    # Numeric reply releases the batch to the chosen buyer.
    with SessionLocal() as db:
        prompt_options = (
            db.query(DBRelayOutboxItem)
            .filter(DBRelayOutboxItem.brokerage_id == seed["brokerage_id"], DBRelayOutboxItem.status == "parked")
            .first()
            .metadata_json["routing_options"]
        )
        answer = _route(db, seed, _text_inbound(seed, "2"))
        assert answer.status == "parked_batch_routed"
        chosen = prompt_options[1]["conversation_id"]
        assert answer.conversation_id == chosen

    with SessionLocal() as db:
        chosen_conv = db.get(DBConversation, chosen)
    assert len([send for send in transport.messages_to_buyer(chosen_conv.buyer_phone) if send.media_url]) == 1


def test_stale_media_request_escalation_not_tier4_eligible(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    _seed_media_request_thread(seed, "B", alerted_hours_ago=49)

    with SessionLocal() as db:
        routed = _route(db, seed, _media_inbound(seed, forwarded=True))
        assert routed.status == "parked"

    prompts = [send for send in transport.messages_to_agents_ai() if "where should these go" in send.body]
    assert len(prompts) == 1  # plain prompt, no numbered options


def test_thread_resolved_before_forward_never_matches_but_hold_proceeds_after_routing(relay_media_seed):
    seed = relay_media_seed
    now = datetime.utcnow()

    # Resolved BEFORE the forward arrives → never matches tier 4.
    thread_id = _seed_media_request_thread(seed, "B", state="resolved")
    with SessionLocal() as db:
        routed = _route(db, seed, _media_inbound(seed, forwarded=True), now=now)
        assert routed.status == "parked"
        db.query(DBRelayOutboxItem).filter(DBRelayOutboxItem.brokerage_id == seed["brokerage_id"]).delete(synchronize_session=False)
        safe_commit(db)

    # Open at routing time, resolved before release → the hold proceeds.
    open_thread_id = _seed_media_request_thread(seed, "B", state="open")
    with SessionLocal() as db:
        routed = _route(db, seed, _media_inbound(seed, forwarded=True), now=now)
        assert routed.routing_method == "escalation_match"
        thread = db.get(DBEscalationThread, open_thread_id)
        thread.state = "resolved"
        safe_commit(db)
        stats = process_relay_outbox(db, now=now + timedelta(seconds=IMPLICIT_HOLD_SECONDS + 1))
        assert stats["released"] == 1


# ── Checklist 22: classifier sets the flag; routing reads stored state ────────


def test_media_request_rubric_and_stored_state():
    assert is_media_request("can you send the floor plan?") is True
    assert is_media_request("Could I get the brochure and some photos?") is True
    assert is_media_request("what's the service charge?") is False
    assert is_media_request("how far is the metro?") is False


def test_classifier_sets_flag_on_thread_via_escalation_path(relay_media_seed):
    seed = relay_media_seed
    from app.core.escalation_threads import send_initial_or_update
    from app.schemas.conversation import EscalationAlert

    class _Agent:
        user_id = seed["agent_user_id"]
        whatsapp_phone = seed["agent_phone"]

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        alert = EscalationAlert(
            escalation_type="info_gap",
            conversation_id=seed["conversations"]["A"],
            listing_id=seed["buyers"]["A"][1],
            buyer_phone=seed["buyers"]["A"][0],
            trigger_message="Can you send the floor plan?",
        )
        result = send_initial_or_update(
            db,
            brokerage=brokerage,
            alert=alert,
            managing_agent=_Agent(),
            envelope_body="[INFO_GAP] floor plan request",
            tags=["info_gap"],
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        assert result.thread is not None
        assert (result.thread.metadata_json or {}).get("media_requested") is True

        non_media = EscalationAlert(
            escalation_type="info_gap",
            conversation_id=seed["conversations"]["C"],
            listing_id=seed["buyers"]["C"][1],
            buyer_phone=seed["buyers"]["C"][0],
            trigger_message="What's the service charge?",
        )
        result2 = send_initial_or_update(
            db,
            brokerage=brokerage,
            alert=non_media,
            managing_agent=_Agent(),
            envelope_body="[INFO_GAP] service charge",
            tags=["info_gap"],
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        assert (result2.thread.metadata_json or {}).get("media_requested") is None


# ── Checklist 23: routing method recorded for every method ─────────────────────


def test_routing_methods_recorded_on_compliance_events(relay_media_seed):
    seed = relay_media_seed
    transport = seed["transport"]
    now = datetime.utcnow()
    token_a = seed["buyers"]["A"][2]

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        # caption_token
        _route(db, seed, _media_inbound(seed, body=f"#{token_a}"), now=now)
        # quote_reply (media)
        _route(db, seed, _media_inbound(seed, token_quote=token_a), now=now)
        # session (held → released)
        held = _route(db, seed, _media_inbound(seed), now=now)
        assert held.routing_method == "session"
        process_relay_outbox(db, now=now + timedelta(seconds=IMPLICIT_HOLD_SECONDS + 1))
        # escalation_match for C (no session interference: close it first)
        undo_sessions = (
            db.query(DBAgentRelaySession)
            .filter(DBAgentRelaySession.brokerage_id == seed["brokerage_id"], DBAgentRelaySession.status == "active")
            .all()
        )
        for session in undo_sessions:
            session.status = "closed"
            session.closed_reason = "test"
        safe_commit(db)
        _seed_media_request_thread(seed, "C")
        held_c = _route(db, seed, _media_inbound(seed, forwarded=True), now=now)
        assert held_c.routing_method == "escalation_match"
        process_relay_outbox(db, now=now + timedelta(seconds=IMPLICIT_HOLD_SECONDS + 1))
        # parking_prompt for B (close C session created? escalation match doesn't open sessions)
        parked = _route(db, seed, _media_inbound(seed, forwarded=True, agent_phone=seed["agent_phone"]), now=now)
        # only C's escalation is open → it would tier-4 again; cancel by resolving thread first
        if parked.routing_method == "escalation_match":
            process_relay_outbox(db, now=now + timedelta(seconds=IMPLICIT_HOLD_SECONDS + 1))

    with SessionLocal() as db:
        methods = {
            event.details.get("routing_method")
            for event in db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                DBComplianceEvent.event_type == "agent_media_sent",
            )
            .all()
        }
        assert {"caption_token", "quote_reply", "session", "escalation_match"} <= methods
