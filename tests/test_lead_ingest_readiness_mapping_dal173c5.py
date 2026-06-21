"""DAL-173C5 lead-ingest readiness mapping tests.

Pure helper coverage only: no DB, network, WhatsApp send, routing, assignment,
hot-list, draft, chatbot, frontend, migration, RLS, or Verified Facts paths.
"""
from __future__ import annotations

from app.core.lead_ingest import ParsedLead, _extract_lead_readiness_signals
from app.models.db_models import DBListing


def _parsed(message: str) -> ParsedLead:
    return ParsedLead(
        source="property_finder",
        parser_version="property_finder:v1",
        buyer_name="Test Buyer",
        buyer_phone="+971501234567",
        buyer_message=message,
        portal_listing_ref="PF-1",
        portal_listing_url="https://www.propertyfinder.ae/en/plp/buy/apartment-test.html",
    )


def _listing(property_type: str = "ready", status: str = "ready") -> DBListing:
    return DBListing(
        listing_id="listing-1",
        brokerage_id="brokerage-1",
        property_type=property_type,
        spa_data={"property_status": status},
    )


def _signals(message: str, *, listing: DBListing | None = None):
    return {
        field: value
        for field, (value, _confidence) in _extract_lead_readiness_signals(
            parsed=_parsed(message),
            raw_payload={"subject": "New lead", "body": f"Message: {message}"},
            listing=listing or _listing(),
        ).items()
    }


def test_maps_available_inbound_fields_to_readiness_profile_fields():
    signals = _signals(
        "Cash buyer, budget AED 2.4M, looking for a 3BR apartment for my family. "
        "I live in Dubai, can view this weekend, not working with another agent. "
        "Please WhatsApp me ASAP."
    )

    assert signals["budget_max_aed"] == 2_400_000
    assert signals["financing"] == "cash"
    assert signals["purpose"] == "end_user"
    assert signals["bedrooms"] == 3
    assert signals["property_type"] == "apartment"
    assert signals["in_dubai_now"] == "yes"
    assert signals["viewing_availability"] == "this weekend"
    assert signals["other_agent_status"] == "not_working_with_agent"
    assert signals["urgency"] == "high"
    assert signals["contact_preference"] == "whatsapp"


def test_ambiguous_or_missing_values_remain_missing():
    signals = _signals("Is this still available? Please send details.")

    assert "budget_max_aed" not in signals
    assert "purpose" not in signals
    assert "financing" not in signals
    assert "other_agent_status" not in signals
    assert "viewing_availability" not in signals


def test_off_plan_inquiry_does_not_infer_viewing_availability():
    signals = _signals(
        "Can I book a viewing this weekend? I am a cash buyer with budget AED 2M.",
        listing=_listing(property_type="off_plan", status="off-plan"),
    )

    assert signals["budget_max_aed"] == 2_000_000
    assert signals["financing"] == "cash"
    assert "viewing_availability" not in signals


def test_ready_property_inquiry_can_infer_viewing_availability():
    signals = _signals(
        "Can I book a viewing tomorrow?",
        listing=_listing(property_type="ready", status="ready"),
    )

    assert signals["viewing_availability"] == "tomorrow"


def test_no_send_routing_ranking_or_verified_facts_scope_terms():
    rendered = str(_extract_lead_readiness_signals(
        parsed=_parsed("Mortgage buyer, budget AED 3M, call me next week."),
        raw_payload={},
        listing=_listing(),
    )).lower()

    assert "whatsapp send" not in rendered
    assert "routing" not in rendered
    assert "assignment" not in rendered
    assert "hot-list" not in rendered
    assert "verified facts" not in rendered
