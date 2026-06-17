"""
DAL-163 — Portal lead ingestion + AI first-touch.

Covers the spec verification checklist:
  1. PF-format and Bayut-format fixture emails parse; parser_version recorded.
  2. Malformed email → dead-letter queue + notification; nothing silent.
  3. Duplicate lead (same phone, same listing, <7 days) → no second
     first-touch; timeline event only.
  4. Existing conversation match → lead attached, no new conversation.
  5. Unresolved listing → lead still ingested and routed with flag.
  6. First-touch recorded with template name/version + consent-basis
     compliance event.
  7. STOP → opt-out enforced; no nudge draft created.
  8. Hot-list ranks a fresh lead above stale conversations.
  9. Cross-tenant: brokerage A's ingest address cannot create conversations
     in brokerage B (forged-forward test).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from app.core.brokerage_access import mark_buyer_opted_out
from app.core.lead_ingest import (
    FIRST_TOUCH_TEMPLATE_NAME,
    FIRST_TOUCH_TEMPLATE_VERSION,
    create_first_touch_nudge_drafts,
    ingest_lead_email,
    normalize_phone,
)
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBAgentNotification,
    DBAgentProfile,
    DBBrokerage,
    DBBuyerProfile,
    DBBuyerSuppression,
    DBComplianceEvent,
    DBConversation,
    DBDraftReply,
    DBLeadAssignment,
    DBLeadIngestRecord,
    DBListing,
    DBMessage,
)


def _pf_email(buyer_phone: str, listing_url: str, name: str = "Imran Khan") -> dict:
    return {
        "sender": "leads@propertyfinder.ae",
        "subject": "New lead from Property Finder",
        "body": (
            "You have received a new lead from Property Finder.\n\n"
            f"Name: {name}\n"
            f"Phone: {buyer_phone}\n"
            "Email: imran@example.com\n"
            "Message: Is this unit still available? What are the service charges?\n\n"
            f"Listing: {listing_url}\n"
            "Reference: PF-12345\n"
        ),
    }


def _bayut_email(buyer_phone: str, listing_url: str) -> dict:
    return {
        "sender": "noreply@bayut.com",
        "subject": "Bayut — New enquiry on your listing",
        "body": (
            "A client has enquired via Bayut.\n\n"
            "Lead Name: Priya Sharma\n"
            f"Contact: {buyer_phone}\n"
            "Enquiry: Can I book a viewing this weekend?\n\n"
            f"{listing_url}\n"
            "Property ID: BYT-777\n"
        ),
    }


@pytest.fixture
def lead_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"lead-brokerage-{suffix}"
    other_brokerage_id = f"lead-other-{suffix}"
    slug = f"lead-{suffix}"
    other_slug = f"lead-other-{suffix}"
    listing_id = f"lead-listing-{suffix}"
    agent_user_id = f"lead-agent-{suffix}"
    agent_phone = f"+97157788{suffix[:4]}"
    listing_url = f"https://www.propertyfinder.ae/en/plp/buy/apartment-{suffix}.html"
    # Phones must be all-digits — the parser normalizes to E.164.
    digits = f"{int(suffix, 16) % 10000:04d}"
    buyer_phone = f"+97156688{digits}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Lead Brokerage",
            slug=slug,
            status="active",
            brokerage_ai_number=f"+97158888{suffix[:4]}",
            agents_ai_number=f"+97159988{suffix[:4]}",
        ))
        db.add(DBBrokerage(
            brokerage_id=other_brokerage_id,
            name="Other Lead Brokerage",
            slug=other_slug,
            status="active",
            brokerage_ai_number=f"+97158889{suffix[:4]}",
            agents_ai_number=f"+97159989{suffix[:4]}",
        ))
        db.add(DBAgentProfile(
            brokerage_id=brokerage_id,
            user_id=agent_user_id,
            full_name="Lead Agent",
            display_name="Lead Agent",
            whatsapp_phone=agent_phone,
            rera_broker_card_number=f"BRN-LEAD-{suffix}",
        ))
        db.add(DBListing(
            listing_id=listing_id,
            brokerage_id=brokerage_id,
            assigned_agent_id=agent_user_id,
            spa_data={"project": "Lead Lagoons", "unit_number": "1502"},
            seller_asking_price=1_800_000,
            commission_rate=0.02,
            property_type="ready",
            source_url=listing_url,
            additional_fees=[],
            seller_qa=[],
            media_urls=[],
            unit_profile={},
            unit_profile_history=[],
            processing_stages={},
        ))
        safe_commit(db)

    transport = SimulatedTransport()
    set_transport_override(transport)

    try:
        yield {
            "brokerage_id": brokerage_id,
            "other_brokerage_id": other_brokerage_id,
            "slug": slug,
            "other_slug": other_slug,
            "listing_id": listing_id,
            "listing_url": listing_url,
            "agent_user_id": agent_user_id,
            "agent_phone": agent_phone,
            "buyer_phone": buyer_phone,
            "transport": transport,
        }
    finally:
        set_transport_override(None)
        with SessionLocal() as db:
            conversation_ids = [
                row.conversation_id
                for row in db.query(DBConversation.conversation_id)
                .filter(DBConversation.brokerage_id.in_([brokerage_id, other_brokerage_id]))
                .all()
            ]
            for brokerage in (brokerage_id, other_brokerage_id):
                db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBAgentNotification).filter(DBAgentNotification.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBLeadIngestRecord).filter(DBLeadIngestRecord.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBDraftReply).filter(DBDraftReply.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBBuyerSuppression).filter(DBBuyerSuppression.brokerage_id == brokerage).delete(synchronize_session=False)
            if conversation_ids:
                db.query(DBMessage).filter(DBMessage.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
                db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
                db.query(DBConversation).filter(DBConversation.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
            db.query(DBBuyerProfile).filter(DBBuyerProfile.phone == buyer_phone).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([brokerage_id, other_brokerage_id])).delete(synchronize_session=False)
            safe_commit(db)


def _ingest(seed, payload, slug=None):
    with SessionLocal() as db:
        return ingest_lead_email(
            db,
            to_address=f"leads+{slug or seed['slug']}@dalya.ai",
            payload=payload,
        )


# ── Checklist 1: parser fixtures + parser_version ──────────────────────────────


def test_phone_normalization():
    assert normalize_phone("+971 50 123 4567") == "+971501234567"
    assert normalize_phone("0501234567") == "+971501234567"
    assert normalize_phone("971501234567") == "+971501234567"
    assert normalize_phone("00441234567890") == "+441234567890"
    assert normalize_phone("garbage") is None


def test_pf_and_bayut_emails_parse_with_parser_version(lead_seed):
    seed = lead_seed
    outcome = _ingest(seed, _pf_email(seed["buyer_phone"], seed["listing_url"]))
    assert outcome.status == "ingested"
    assert outcome.record.parser_version == "property_finder:v1"
    assert outcome.record.buyer_name == "Imran Khan"
    assert outcome.record.buyer_phone == seed["buyer_phone"]
    assert "service charges" in outcome.record.buyer_message
    assert outcome.record.listing_resolution == "matched_url"
    assert outcome.record.listing_id == seed["listing_id"]

    bayut_phone = seed["buyer_phone"].replace("+971566", "+971557")
    outcome2 = _ingest(seed, _bayut_email(bayut_phone, "https://www.bayut.com/property/details-99.html"))
    assert outcome2.record.parser_version == "bayut:v1"
    assert outcome2.record.source == "bayut"
    # Bayut URL doesn't match the PF source_url → falls through (fuzzy/unresolved OK)
    assert outcome2.record.listing_resolution in {"fuzzy_pending", "unresolved"}

    # cleanup the bayut buyer's conversation rows happens via fixture (brokerage scope)


# ── Checklist 2: malformed email → dead letter, never silent ───────────────────


def test_malformed_email_dead_letters_with_notification(lead_seed):
    seed = lead_seed
    transport = seed["transport"]
    outcome = _ingest(seed, {"sender": "x@y.z", "subject": "FWD: hello", "body": "no structured fields here"})
    assert outcome.status == "dead_letter"
    assert outcome.record is not None
    assert outcome.record.error == "unparseable_email"

    with SessionLocal() as db:
        event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                DBComplianceEvent.event_type == "lead_email_dead_letter",
            )
            .one()
        )
        assert event is not None
        notification = (
            db.query(DBAgentNotification)
            .filter(
                DBAgentNotification.brokerage_id == seed["brokerage_id"],
                DBAgentNotification.event_type == "ai_failure",
            )
            .one()
        )
        assert notification.status == "sent"
    assert any("couldn't be parsed" in send.body for send in transport.messages_to_agents_ai())


# ── Checklists 3 + 6: first touch + duplicates ─────────────────────────────────


def test_first_touch_template_locked_and_duplicate_suppressed(lead_seed):
    seed = lead_seed
    transport = seed["transport"]

    outcome = _ingest(seed, _pf_email(seed["buyer_phone"], seed["listing_url"]))
    assert outcome.first_touch_sent is True

    sends = transport.messages_to_buyer(seed["buyer_phone"])
    assert len(sends) == 1
    assert "thanks for your enquiry about Lead Lagoons on Property Finder" in sends[0].body
    assert "Reply STOP to opt out" in sends[0].body
    assert "Lead Brokerage" in sends[0].body

    with SessionLocal() as db:
        event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                DBComplianceEvent.event_type == "lead_first_touch_sent",
            )
            .one()
        )
        assert event.details["template_name"] == FIRST_TOUCH_TEMPLATE_NAME
        assert event.details["template_version"] == FIRST_TOUCH_TEMPLATE_VERSION
        assert event.details["consent_basis"] == "portal_lead_form_submission"
        assert event.details["consent_evidence"].startswith("lead_ingests:")
        # Agent notified simultaneously (event #2).
        notification = (
            db.query(DBAgentNotification)
            .filter(
                DBAgentNotification.brokerage_id == seed["brokerage_id"],
                DBAgentNotification.event_type == "lead_first_touch",
            )
            .one()
        )
        assert notification.status == "sent"

    # Duplicate within 7 days: timeline event only, no second first-touch.
    duplicate = _ingest(seed, _pf_email(seed["buyer_phone"], seed["listing_url"]))
    assert duplicate.status in {"duplicate", "attached"}
    assert duplicate.first_touch_sent is False
    assert len(transport.messages_to_buyer(seed["buyer_phone"])) == 1


# ── Checklist 4: existing conversation → attach, no new conversation ───────────


def test_existing_conversation_attaches_lead(lead_seed):
    seed = lead_seed
    transport = seed["transport"]

    with SessionLocal() as db:
        conv = crud.get_or_create_conversation(db, seed["buyer_phone"], seed["listing_id"])
        conv.assigned_agent_id = seed["agent_user_id"]
        db.add(DBMessage(conversation_id=conv.conversation_id, role="user", content="Hi, saw your listing"))
        safe_commit(db)
        conversation_id = conv.conversation_id
        before = db.query(DBConversation).filter(DBConversation.brokerage_id == seed["brokerage_id"]).count()

    outcome = _ingest(seed, _pf_email(seed["buyer_phone"], seed["listing_url"]))
    assert outcome.status == "attached"
    assert outcome.conversation_id == conversation_id
    assert outcome.first_touch_sent is False
    assert transport.messages_to_buyer(seed["buyer_phone"]) == []  # no first touch

    with SessionLocal() as db:
        after = db.query(DBConversation).filter(DBConversation.brokerage_id == seed["brokerage_id"]).count()
        assert after == before  # no new conversation
        timeline = (
            db.query(DBMessage)
            .filter(
                DBMessage.conversation_id == conversation_id,
                DBMessage.intent == "portal_lead",
            )
            .count()
        )
        assert timeline == 1


# ── Checklist 5: unresolved listing still ingests with a flag ──────────────────


def test_unresolved_listing_still_ingested_and_flagged(lead_seed):
    seed = lead_seed
    transport = seed["transport"]
    email = _pf_email(seed["buyer_phone"], "https://www.propertyfinder.ae/en/plp/some-other-listing.html")
    email["body"] = email["body"].replace("Is this unit still available? What are the service charges?", "Looking for a 2BR")
    outcome = _ingest(seed, email)

    assert outcome.status == "ingested"
    assert outcome.record.listing_resolution == "unresolved"
    assert outcome.record.listing_id is None
    assert outcome.conversation_id is None
    # Routed to a human — never silent.
    assert any("couldn't be matched" in send.body for send in transport.messages_to_agents_ai())


# ── Checklist 7: STOP → opt-out enforced, no nudge draft ───────────────────────


def test_stop_propagates_and_no_nudge_draft(lead_seed):
    seed = lead_seed
    transport = seed["transport"]

    outcome = _ingest(seed, _pf_email(seed["buyer_phone"], seed["listing_url"]))
    assert outcome.first_touch_sent is True

    with SessionLocal() as db:
        mark_buyer_opted_out(
            db,
            brokerage_id=seed["brokerage_id"],
            buyer_phone=seed["buyer_phone"],
            conversation_id=outcome.conversation_id,
            source="buyer_message",
            reason="STOP reply to first touch",
        )

    # 48h later: the nudge job runs — suppressed buyer gets no draft.
    with SessionLocal() as db:
        record = db.get(DBLeadIngestRecord, outcome.record.ingest_id)
        record.created_at = datetime.utcnow() - timedelta(hours=49)
        safe_commit(db)
        created = create_first_touch_nudge_drafts(db)
        assert created == 0
        record = db.get(DBLeadIngestRecord, outcome.record.ingest_id)
        assert record.nudge_draft_id == "suppressed"
        drafts = (
            db.query(DBDraftReply)
            .filter(DBDraftReply.brokerage_id == seed["brokerage_id"])
            .count()
        )
        assert drafts == 0

    # A further first-touch for the same buyer is blocked by suppression.
    with SessionLocal() as db:
        db.query(DBLeadIngestRecord).filter(
            DBLeadIngestRecord.brokerage_id == seed["brokerage_id"]
        ).delete(synchronize_session=False)
        safe_commit(db)
    before = len(transport.messages_to_buyer(seed["buyer_phone"]))
    again = _ingest(seed, _pf_email(seed["buyer_phone"], seed["listing_url"]))
    assert again.first_touch_sent is False
    assert len(transport.messages_to_buyer(seed["buyer_phone"])) == before


def test_nudge_draft_created_when_no_reply_after_48h(lead_seed):
    seed = lead_seed
    outcome = _ingest(seed, _pf_email(seed["buyer_phone"], seed["listing_url"]))
    assert outcome.first_touch_sent is True

    with SessionLocal() as db:
        record = db.get(DBLeadIngestRecord, outcome.record.ingest_id)
        record.created_at = datetime.utcnow() - timedelta(hours=49)
        safe_commit(db)
        created = create_first_touch_nudge_drafts(db)
        assert created == 1
        draft = (
            db.query(DBDraftReply)
            .filter(DBDraftReply.brokerage_id == seed["brokerage_id"])
            .one()
        )
        assert draft.status == "draft"  # review-only, never auto-sent
        assert draft.source == "lead_first_touch_nudge"
        # Running again does not double-create.
        assert create_first_touch_nudge_drafts(db) == 0


# ── Checklist 8: fresh lead outranks stale conversations ───────────────────────


def test_fresh_lead_gets_strong_recency_score(lead_seed):
    seed = lead_seed
    outcome = _ingest(seed, _pf_email(seed["buyer_phone"], seed["listing_url"]))

    with SessionLocal() as db:
        assignment = (
            db.query(DBLeadAssignment)
            .filter(DBLeadAssignment.conversation_id == outcome.conversation_id)
            .one()
        )
        assert assignment.urgency_score >= 85
        assert assignment.signal == "new_portal_lead"


# ── Checklist 9: forged-forward cross-tenant test ──────────────────────────────


def test_ingest_address_is_tenant_boundary(lead_seed):
    seed = lead_seed
    # A forwards to B's address: the lead lands in B only — and B has no
    # matching listing, so no conversation is created anywhere.
    outcome = _ingest(seed, _pf_email(seed["buyer_phone"], seed["listing_url"]), slug=seed["other_slug"])
    assert outcome.record.brokerage_id == seed["other_brokerage_id"]
    assert outcome.conversation_id is None

    with SessionLocal() as db:
        a_conversations = (
            db.query(DBConversation)
            .filter(
                DBConversation.brokerage_id == seed["brokerage_id"],
                DBConversation.buyer_phone == seed["buyer_phone"],
            )
            .count()
        )
        assert a_conversations == 0  # nothing crossed into brokerage A

    # An unknown slug creates nothing at all.
    with SessionLocal() as db:
        nothing = ingest_lead_email(
            db,
            to_address="leads+does-not-exist@dalya.ai",
            payload=_pf_email(seed["buyer_phone"], seed["listing_url"]),
        )
        assert nothing.status == "dead_letter"
        assert nothing.record is None
