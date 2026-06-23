from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json

from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.db.session import Base, SessionLocal, engine, safe_commit
from app.main import app
from app.models import db_models as models
from scripts.seller_summary_privacy_contract import (
    AGENT_ID,
    BROKERAGE_ID,
    BUYER_NAME,
    BUYER_PHONE,
    CONVERSATION_ID,
    LISTING_ID,
    OTHER_SELLER_ID,
    SAFE_CONTEXT,
    SELLER_ID,
    JsonValue,
    seeded_ai_summary,
    seeded_secrets,
)
from scripts.seller_summary_privacy_isolation import assert_isolated_sqlite_engine


@dataclass(frozen=True, slots=True)
class AppProbeResult:
    seller_status_code: int
    agent_status_code: int
    forbidden_status_code: int
    seller_payload: JsonValue
    seller_text: str
    leaked_secrets: tuple[str, ...]
    placeholders: tuple[str, ...]
    stored_summary_unchanged: bool
    stored_conversation_identity_preserved: bool
    agent_identity_preserved: bool
    forbidden_response_leak_free: bool
    sqlite_database_path: str

    @property
    def passed(self) -> bool:
        return all((
            self.seller_status_code == 200,
            not self.leaked_secrets,
            SAFE_CONTEXT in json.dumps(self.seller_payload, sort_keys=True),
            len(self.placeholders) == 5,
            self.stored_summary_unchanged,
            self.stored_conversation_identity_preserved,
            self.agent_identity_preserved,
            self.forbidden_status_code == 403,
            self.forbidden_response_leak_free,
        ))


def create_schema() -> str:
    sqlite_path = assert_isolated_sqlite_engine()
    Base.metadata.create_all(bind=engine)
    return sqlite_path


def set_user(user_id: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id,
        email=f"{user_id}@example.com",
    )


def clear_user() -> None:
    app.dependency_overrides.pop(get_current_user, None)


def cleanup_rows() -> None:
    create_schema()
    clear_user()
    with SessionLocal() as db:
        for model in (
            models.DBLeadTask,
            models.DBLeadAssignment,
            models.DBAIDraft,
            models.DBDraftReply,
            models.DBOutreachDraft,
            models.DBHotlistRefreshRun,
        ):
            db.query(model).filter(model.brokerage_id == BROKERAGE_ID).delete(synchronize_session=False)
        for model in (models.DBEscalationThread, models.DBLeadAction, models.DBMessage, models.DBConversation):
            db.query(model).filter(model.conversation_id == CONVERSATION_ID).delete(synchronize_session=False)
        db.query(models.DBListing).filter(models.DBListing.listing_id == LISTING_ID).delete(synchronize_session=False)
        db.query(models.DBBrokerageMember).filter(models.DBBrokerageMember.brokerage_id == BROKERAGE_ID).delete(
            synchronize_session=False,
        )
        db.query(models.DBBrokerage).filter(models.DBBrokerage.brokerage_id == BROKERAGE_ID).delete(
            synchronize_session=False,
        )
        safe_commit(db)


def seed_rows() -> None:
    create_schema()
    with SessionLocal() as db:
        db.add(models.DBBrokerage(
            brokerage_id=BROKERAGE_ID,
            name="Task 4 Summary Privacy Brokerage",
            slug=BROKERAGE_ID,
            status="active",
        ))
        db.add(models.DBBrokerageMember(
            brokerage_id=BROKERAGE_ID,
            user_id=AGENT_ID,
            email="task-4-summary-agent@example.com",
            display_name="Task 4 Summary Agent",
            role="agent",
            status="active",
        ))
        db.add(models.DBListing(
            listing_id=LISTING_ID,
            brokerage_id=BROKERAGE_ID,
            seller_id=SELLER_ID,
            assigned_agent_id=AGENT_ID,
            spa_data={"project": "Task 4 Seller Summary Tower", "unit_number": "1901"},
            seller_asking_price=3_200_000,
            negotiation_threshold_aed=3_000_000,
            commission_rate=0.02,
            property_type="ready",
            additional_fees=[],
            seller_qa=[],
            media_urls=[],
            unit_profile={},
            unit_profile_history=[],
            processing_stages={},
        ))
        db.add(models.DBConversation(
            conversation_id=CONVERSATION_ID,
            listing_id=LISTING_ID,
            brokerage_id=BROKERAGE_ID,
            assigned_agent_id=AGENT_ID,
            buyer_phone=BUYER_PHONE,
            buyer_name=BUYER_NAME,
            ai_summary=seeded_ai_summary(),
            created_at=datetime(2026, 6, 23, 8, 0, 0),
            updated_at=datetime(2026, 6, 23, 8, 5, 0),
        ))
        db.add(models.DBMessage(
            conversation_id=CONVERSATION_ID,
            role="user",
            content=f"{BUYER_NAME} says {SAFE_CONTEXT}. Call {BUYER_PHONE}.",
            intent="viewing_request",
            timestamp=datetime(2026, 6, 23, 8, 1, 0),
        ))
        db.add(models.DBMessage(
            conversation_id=CONVERSATION_ID,
            role="assistant",
            content="I can help with viewing availability.",
            timestamp=datetime(2026, 6, 23, 8, 2, 0),
        ))
        safe_commit(db)


def stored_rows_preserved() -> tuple[bool, bool]:
    with SessionLocal() as db:
        stored = db.get(models.DBConversation, CONVERSATION_ID)
        if stored is None:
            return False, False
        summary_preserved = stored.ai_summary == seeded_ai_summary()
        identity_preserved = stored.buyer_name == BUYER_NAME and stored.buyer_phone == BUYER_PHONE
        return summary_preserved, identity_preserved


def run_app_probe() -> AppProbeResult:
    sqlite_path = create_schema()
    client = TestClient(app)
    set_user(SELLER_ID)
    seller_response = client.get(f"/api/v1/seller/listings/{LISTING_ID}/conversations")
    seller_payload = seller_response.json()
    seller_text = seller_response.text
    set_user(AGENT_ID)
    agent_response = client.get("/api/v1/agent/dashboard")
    agent_identity = _agent_identity_preserved(agent_response.status_code, agent_response.json())
    set_user(OTHER_SELLER_ID)
    forbidden_response = client.get(f"/api/v1/seller/listings/{LISTING_ID}/conversations")
    stored_summary, stored_identity = stored_rows_preserved()
    return AppProbeResult(
        seller_status_code=seller_response.status_code,
        agent_status_code=agent_response.status_code,
        forbidden_status_code=forbidden_response.status_code,
        seller_payload=seller_payload,
        seller_text=seller_text,
        leaked_secrets=tuple(secret for secret in seeded_secrets() if secret in seller_text),
        placeholders=_placeholders(seller_text),
        stored_summary_unchanged=stored_summary,
        stored_conversation_identity_preserved=stored_identity,
        agent_identity_preserved=agent_identity,
        forbidden_response_leak_free=all(secret not in forbidden_response.text for secret in seeded_secrets()),
        sqlite_database_path=sqlite_path,
    )


def _agent_identity_preserved(status_code: int, payload: JsonValue) -> bool:
    if status_code != 200 or not isinstance(payload, dict):
        return False
    conversations = payload.get("conversations")
    if not isinstance(conversations, list):
        return False
    for item in conversations:
        if isinstance(item, dict) and item.get("conversation_id") == CONVERSATION_ID:
            return item.get("buyer") == {"name": BUYER_NAME, "phone": BUYER_PHONE, "budget_aed": None}
    return False


def _placeholders(response_text: str) -> tuple[str, ...]:
    return tuple(
        placeholder
        for placeholder in (
            "[redacted buyer]",
            "[redacted phone]",
            "[redacted email]",
            "[redacted whatsapp]",
            "[redacted id]",
        )
        if placeholder in response_text
    )
