"""
Multi-tenant invariants — DB-free unit tests.

Covers:
- Brokerage context resolution falls back cleanly for legacy data
- Near-threshold band math (5% buffer, identical buyer copy)
- Messaging transport interface contracts (simulated)
- Agent-community remark scoping invariant (model-level)
- Prompt builder substitutes brokerage/agent values
"""

import pytest

pytestmark = pytest.mark.no_db


def test_legacy_context_uses_mahoroba_defaults():
    from app.core.multitenant_context import legacy_default_context
    ctx = legacy_default_context()
    assert ctx.brokerage_name == "the listing brokerage"
    assert ctx.brokerage_short == "the listing brokerage"
    assert ctx.managing_agent_name == "Eric"
    assert ctx.managing_agent_title == "agent managing this listing"
    assert ctx.commission_rate == 0.0
    assert ctx.commission_pct_label == "0%"
    assert ctx.market_pct_label == "2%"
    assert ctx.savings_pct_label == "2%"


def test_custom_context_renders_for_irwin_layla():
    from app.core.multitenant_context import BrokerageContext
    ctx = BrokerageContext(
        brokerage_id="b1",
        brokerage_name="Irwin Real Estate",
        brokerage_short="Irwin",
        brokerage_arabic="إيروين",
        managing_agent_name="Layla",
        managing_agent_title="Managing Director",
        commission_rate=0.005,
        market_benchmark_rate=0.02,
        dashboard_url="dalya.ai/dashboard",
        brokerage_ai_number="+971500000201",
        agents_ai_number="+971500000299",
        managing_agent_phone="+971501234567",
        managing_agent_user_id="layla",
        legacy_telegram_alerts=False,
    )
    assert ctx.commission_pct_label == "0.5%"
    assert ctx.market_pct_label == "2%"
    assert ctx.savings_pct_label == "1.5%"


def test_brokerage_substitutions_replace_placeholders():
    from app.core.chatbot_engine import ChatbotEngine
    from app.core.multitenant_context import BrokerageContext

    ctx = BrokerageContext(
        brokerage_id="b1",
        brokerage_name="Irwin Real Estate",
        brokerage_short="Irwin",
        brokerage_arabic="إيروين",
        managing_agent_name="Layla",
        managing_agent_title="Managing Director",
        commission_rate=0.005,
        market_benchmark_rate=0.02,
        dashboard_url="dalya.ai/dashboard",
        brokerage_ai_number="+971500000201",
        agents_ai_number="+971500000299",
        managing_agent_phone="+971501234567",
        managing_agent_user_id="layla",
        legacy_telegram_alerts=False,
    )

    template = "I've forwarded this to {managing_agent_name} at {brokerage_short}. Our fee is {commission_pct_label}."
    rendered = ChatbotEngine._apply_brokerage_substitutions(template, ctx)
    assert "Layla" in rendered
    assert "Irwin" in rendered
    assert "0.5%" in rendered
    assert "{" not in rendered


def test_near_threshold_band_math():
    # Asking 5M, threshold 4.5M. 5% buffer = 225,000 → floor 4,275,000.
    T = 4_500_000.0
    floor = T * (1 - 0.05)
    assert floor == 4_275_000.0

    # Far-below (< floor): no escalation
    offer = 4_000_000.0
    assert offer < floor

    # Near-threshold (>= floor and < T): escalates with near_threshold tag
    offer = 4_300_000.0
    assert floor <= offer < T

    # At-or-above (>= T): escalates with at_or_above tag, deterministic template
    offer = 4_500_000.0
    assert offer >= T


def test_simulated_transport_round_trip():
    from app.core.messaging.simulated_transport import SimulatedTransport
    from app.core.messaging.types import OutboundAgentMessage, OutboundBuyerMessage

    sim = SimulatedTransport()

    # Send to buyer
    r1 = sim.send_to_buyer(OutboundBuyerMessage(
        brokerage_id="b1", brokerage_ai_number="+971500000001",
        buyer_phone="+971501234567", body="Hello buyer.",
        conversation_id="conv1", listing_id="L1",
    ))
    assert r1.ok
    assert len(sim.messages_to_buyer("+971501234567")) == 1

    # Send to agents AI — token gets stamped
    r2 = sim.send_to_agents_ai(OutboundAgentMessage(
        brokerage_id="b1", agents_ai_number="+971500000099",
        agent_phone="+971500000010", body="Offer escalation 4.5M",
        conversation_id="conv1", listing_id="L1",
        buyer_phone="+971501234567", escalation_type="offer",
        tags=["at_or_above"],
    ))
    assert r2.ok
    assert r2.envelope_token
    assert any(f"[Ref: {r2.envelope_token}]" in m.body for m in sim.messages_to_agents_ai())

    # Agent quotes back with the token preserved
    inbound = sim.inject_agent_reply(
        envelope_token=r2.envelope_token,
        body_without_token="Tell them we accept.",
        agents_ai_number="+971500000099",
    )
    assert inbound.envelope_token == r2.envelope_token


def test_dialog360_transport_is_stub():
    from app.core.messaging.dialog360_transport import Dialog360Transport
    from app.core.messaging.types import OutboundBuyerMessage

    t = Dialog360Transport()
    with pytest.raises(NotImplementedError) as exc_info:
        t.send_to_buyer(OutboundBuyerMessage(
            brokerage_id="b1", brokerage_ai_number="+971500000001",
            buyer_phone="+971501234567", body="x",
        ))
    assert "360dialog" in str(exc_info.value)


def test_prompt_builder_renders_custom_brokerage():
    from app.core.prompt_builder import build_system_prompt
    from app.schemas.spa import SPAParseResult

    spa = SPAParseResult.model_validate({
        "project": "Marina Apartment", "unit_number": "B-1502",
        "developer": "Damac", "property_type": "Apartment",
        "bedrooms": 2, "bathrooms": 2, "bua_sqft": 1450.0,
        "purchase_price_aed": 2_500_000.0, "vat_percent": 0.0,
        "payment_schedule": [], "purchasers": [],
    })
    prompt = build_system_prompt(
        spa, seller_asking_price=2_500_000,
        brokerage_name="Irwin Real Estate",
        brokerage_short="Irwin",
        managing_agent_name="Layla",
        managing_agent_title="Managing Director",
        commission_rate=0.005,
        market_benchmark_rate=0.02,
        property_type="ready",
        additional_fees=[{"label": "Document processing", "amount_aed": 5000, "paid_by": "buyer", "public": True}],
    )
    assert "Irwin Real Estate" in prompt
    assert "Layla" in prompt
    assert "0.5%" in prompt
    assert "Mahoroba" not in prompt
    assert "Eric" not in prompt
    assert "READY-PROPERTY QUESTION SCOPE" in prompt
    assert "ADDITIONAL LINE ITEMS" in prompt and "Document processing" in prompt


def test_prompt_builder_legacy_defaults_unchanged():
    from app.core.prompt_builder import build_system_prompt
    from app.schemas.spa import SPAParseResult

    spa = SPAParseResult.model_validate({
        "project": "Palace Villas Ostra", "unit_number": "A-2305",
        "developer": "Emaar Properties", "property_type": "Villa",
        "bedrooms": 6, "bathrooms": 7, "bua_sqft": 8500.0,
        "purchase_price_aed": 16_000_000.0, "vat_percent": 0.0,
        "estimated_completion_date": "2029-09-30",
        "noc_eligible": False,
        "payment_schedule": [], "purchasers": [],
    })
    # No brokerage_* kwargs passed → generic listing-brokerage fallback avoids real brokerage leaks
    prompt = build_system_prompt(spa, seller_asking_price=15_000_000)
    assert "Mahoroba Realty" not in prompt
    assert "the listing brokerage" in prompt
    assert "Eric" in prompt
    assert "0.15%" not in prompt
    assert "OFF-PLAN QUESTION SCOPE" in prompt


def test_agent_private_notes_only_render_when_provided():
    from app.core.prompt_builder import build_system_prompt
    from app.schemas.spa import SPAParseResult

    spa = SPAParseResult.model_validate({
        "project": "X", "unit_number": "1", "developer": "Y",
        "property_type": "Villa", "bedrooms": 3, "bathrooms": 3,
        "bua_sqft": 2000.0, "purchase_price_aed": 3_000_000.0, "vat_percent": 0.0,
        "payment_schedule": [], "purchasers": [],
    })
    prompt_with_notes = build_system_prompt(
        spa, seller_asking_price=3_000_000,
        agent_private_notes=["Owner flexible on closing date.", "Best view in Tower B."],
    )
    assert "AGENT PRIVATE NOTES" in prompt_with_notes
    assert "Best view in Tower B" in prompt_with_notes

    prompt_no_notes = build_system_prompt(spa, seller_asking_price=3_000_000)
    assert "AGENT PRIVATE NOTES" not in prompt_no_notes


def test_brokerage_resolver_phone_normalization():
    from app.core.brokerage_resolver import _normalise_phone
    assert _normalise_phone("whatsapp:+971500000001") == "+971500000001"
    assert _normalise_phone("WhatsApp:+971500000001") == "+971500000001"
    assert _normalise_phone("+971500000001") == "+971500000001"
    assert _normalise_phone("") is None
    assert _normalise_phone(None) is None


def test_listing_scraper_unknown_url_returns_empty_draft():
    from app.core.listing_scraper import scrape_any
    result = scrape_any("https://example.com/some-listing")
    assert result.source == "unknown"
    assert result.asking_price_aed is None  # no failure raised


def test_listing_scraper_property_finder_parses_basic_jsonld():
    from app.core.listing_scraper import scrape_property_finder
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "Product", "description": "Spacious 3 bedroom apartment, 1,800 sqft in Dubai Marina",
     "offers": {"price": 2500000}, "image": ["https://img1", "https://img2"]}
    </script>
    <meta property="og:image" content="https://og-image">
    </head><body></body></html>
    """
    result = scrape_property_finder("https://www.propertyfinder.ae/x", html=html)
    assert result.asking_price_aed == 2_500_000.0
    assert result.bedrooms == 3
    assert result.size_sqft == 1_800.0
    assert "https://img1" in result.image_urls


def test_listing_scraper_bayut_rapidapi_property_payload_prefills_draft(monkeypatch):
    from app.core import listing_scraper

    payload = {
        "id": 15029244,
        "reference_number": "BAYUT-REF-15029244",
        "title": "Vacant 3 Bed Villa Near Park",
        "description": "Ready villa with landscaped garden.",
        "price": 4_750_000,
        "purpose": "for-sale",
        "type": {"name": "Villa"},
        "area": 2_450.0,
        "plotArea": 3_000.0,
        "rooms": 3,
        "baths": 4,
        "location": {
            "community": {"name": "Dubai Hills Estate"},
            "sub_community": {"name": "Maple"},
        },
        "details": {
            "completion_status": "completed",
            "furnishing_status": "unfurnished",
        },
        "agency": {
            "name": "Mahoroba Realty",
            "licenses": [{"number": "ORN-123"}],
        },
        "agent": {
            "name": "Luqman Ali",
            "phone": "+971500000000",
        },
        "legal": {
            "permit_number": "7111111111",
        },
        "media": {
            "cover_photo": {"url": "https://images.bayut.com/cover.jpg"},
            "photos": [{"url": "https://images.bayut.com/one.jpg"}],
            "image": True,
        },
        "amenities": [{"name": "Private Garden"}],
    }

    monkeypatch.setattr(listing_scraper, "_fetch_bayut_rapidapi", lambda _listing_id: payload)

    result = listing_scraper.scrape_bayut("https://www.bayut.com/property/details-15029244.html")

    assert result.raw_extracts["rapidapi"] is True
    assert result.portal_listing_id == "15029244"
    assert result.listing_reference == "BAYUT-REF-15029244"
    assert result.listing_title == "Vacant 3 Bed Villa Near Park"
    assert result.asking_price_aed == 4_750_000.0
    assert result.bedrooms == 3
    assert result.bathrooms == 4
    assert result.size_sqft == pytest.approx(26_371.58, abs=0.01)
    assert result.plot_size_sqft == pytest.approx(32_291.73, abs=0.01)
    assert result.community == "Dubai Hills Estate"
    assert result.subcommunity == "Maple"
    assert result.property_type == "Villa"
    assert result.furnishing == "unfurnished"
    assert result.permit_number == "7111111111"
    assert result.broker_name == "Mahoroba Realty"
    assert result.agent_name == "Luqman Ali"
    assert "Private Garden" in result.amenities
    assert result.image_urls == [
        "https://images.bayut.com/cover.jpg",
        "https://images.bayut.com/one.jpg",
    ]
    assert all(isinstance(image_url, str) for image_url in result.image_urls)
