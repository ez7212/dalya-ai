"""
Test fixtures for Dalya chatbot tests.

Uses a real test listing inserted directly into the DB so tests don't
require uploading a PDF. All test data uses a "TEST_" prefix so it's
easy to identify and clean up.
"""

import pytest
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import Base, SessionLocal, engine
from app.db import crud
import app.models.db_models as db_models  # noqa: F401
from app.models.db_models import DBAgentProfile, DBBrokerage, DBLeadAssignment
from app.schemas.spa import SPAParseResult, PaymentInstalment


Base.metadata.create_all(bind=engine)


TEST_LISTING_ID = "test-ostra-2805-fixture"
TEST_BUYER_PHONE = "+971500000001"
TEST_BROKERAGE_ID = "test-chatbot-brokerage"
TEST_AGENT_USER_ID = "test-chatbot-agent"

TEST_SPA = SPAParseResult(
    project="Palace Villas Ostra",
    unit_number="2805",
    developer="Emaar Properties",
    property_type="Villa",
    property_use="Single Family Residential Use",
    bua_sqft=7200.0,
    plot_sqft=9100.0,
    parking="3 covered spaces within villa",
    purchase_price_aed=15_173_230.0,
    vat_percent=0.0,
    property_status="Under Construction",
    handover_condition="Finished",
    estimated_completion_date="2029-09-30",
    total_paid_percent=30.0,
    noc_eligible=False,
    parse_confidence=0.95,
    payment_schedule=[
        PaymentInstalment(
            instalment_number=1,
            due_date="2023-01-01",
            milestone="Down Payment",
            percentage=10.0,
            amount_aed=1_517_323.0,
            vat_amount_aed=0.0,
            amount_incl_vat_aed=1_517_323.0,
        ),
        PaymentInstalment(
            instalment_number=2,
            due_date="2023-06-01",
            milestone="20% Construction",
            percentage=10.0,
            amount_aed=1_517_323.0,
            vat_amount_aed=0.0,
            amount_incl_vat_aed=1_517_323.0,
        ),
        PaymentInstalment(
            instalment_number=3,
            due_date="2024-01-01",
            milestone="40% Construction",
            percentage=10.0,
            amount_aed=1_517_323.0,
            vat_amount_aed=0.0,
            amount_incl_vat_aed=1_517_323.0,
        ),
        PaymentInstalment(
            instalment_number=4,
            due_date="2029-09-30",
            milestone="Handover",
            percentage=70.0,
            amount_aed=10_621_261.0,
            vat_amount_aed=0.0,
            amount_incl_vat_aed=10_621_261.0,
        ),
    ],
)


@pytest.fixture(scope="session")
def test_listing():
    """
    Register the test listing in the DB once per test session.
    Cleans up conversations for the test buyer between runs but keeps
    the listing so re-runs are fast.
    """
    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, TEST_BROKERAGE_ID)
        if not brokerage:
            db.add(DBBrokerage(
                brokerage_id=TEST_BROKERAGE_ID,
                name="Mahoroba Test Brokerage",
                slug=TEST_BROKERAGE_ID,
                status="active",
                brokerage_ai_number="+971500009001",
                agents_ai_number="+971500009002",
                settings={"legacy_telegram_alerts": False},
            ))
        agent = (
            db.query(DBAgentProfile)
            .filter_by(brokerage_id=TEST_BROKERAGE_ID, user_id=TEST_AGENT_USER_ID)
            .first()
        )
        if not agent:
            db.add(DBAgentProfile(
                brokerage_id=TEST_BROKERAGE_ID,
                user_id=TEST_AGENT_USER_ID,
                email="test-agent@dalya.local",
                full_name="Test Agent",
                display_name="Test Agent",
                whatsapp_phone="+971500009003",
                rera_broker_card_number="TEST-BRN",
                verification_status="approved",
                onboarding_status="active",
            ))
        db.commit()

        # Upsert the listing
        crud.save_listing(
            db=db,
            listing_id=TEST_LISTING_ID,
            spa=TEST_SPA,
            seller_asking_price=16_500_000.0,
            seller_notes="Motivated seller. Open to serious offers.",
        )
        listing = crud.get_listing(db, TEST_LISTING_ID)
        listing.brokerage_id = TEST_BROKERAGE_ID
        listing.assigned_agent_id = TEST_AGENT_USER_ID
        listing.notification_threshold_aed = 15_000_000.0
        listing.negotiation_threshold_aed = 15_000_000.0
        db.commit()
    yield TEST_LISTING_ID


@pytest.fixture(autouse=True)
def clean_test_conversation(request):
    """
    Delete any existing conversation for the test buyer before each test
    so each test starts with a fresh conversation.
    """
    if request.node.get_closest_marker("no_db"):
        yield
        return

    with SessionLocal() as db:
        existing = (
            db.query(__import__(
                "app.models.db_models", fromlist=["DBConversation"]
            ).DBConversation)
            .filter_by(buyer_phone=TEST_BUYER_PHONE, listing_id=TEST_LISTING_ID)
            .first()
        )
        if existing:
            # Delete messages first (FK constraint)
            db.query(DBLeadAssignment).filter_by(
                conversation_id=existing.conversation_id
            ).delete()
            db.query(__import__(
                "app.models.db_models", fromlist=["DBMessage"]
            ).DBMessage).filter_by(
                conversation_id=existing.conversation_id
            ).delete()
            db.query(__import__(
                "app.models.db_models", fromlist=["DBSuspiciousActivity"]
            ).DBSuspiciousActivity).filter_by(
                conversation_id=existing.conversation_id
            ).delete()
            db.query(__import__(
                "app.models.db_models", fromlist=["DBOfferRecord"]
            ).DBOfferRecord).filter_by(
                conversation_id=existing.conversation_id
            ).delete()
            db.query(__import__(
                "app.models.db_models", fromlist=["DBConversationAccessGrant"]
            ).DBConversationAccessGrant).filter_by(
                conversation_id=existing.conversation_id
            ).delete()
            db.query(__import__(
                "app.models.db_models", fromlist=["DBComplianceEvent"]
            ).DBComplianceEvent).filter_by(
                conversation_id=existing.conversation_id
            ).delete()
            db.query(__import__(
                "app.models.db_models", fromlist=["DBBuyerSuppression"]
            ).DBBuyerSuppression).filter_by(
                buyer_phone=TEST_BUYER_PHONE
            ).delete()
            db.delete(existing)
            db.commit()
    yield


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def send(client, listing_id: str, message: str, phone: str = TEST_BUYER_PHONE) -> dict:
    """Helper: send a test message and return the response dict."""
    resp = client.post(
        "/api/v1/whatsapp/send-test",
        params={
            "listing_id": listing_id,
            "buyer_phone": phone,
            "message": message,
        },
    )
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"
    return resp.json()
