"""DAL-173C6 hot-list readiness shadow metadata tests.

Pure helper coverage only: no DB, network, WhatsApp send, chatbot, drafts,
lead ingest, frontend, migrations, RLS, task creation, or notifications.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from app.core.hot_list_readiness import build_hot_list_readiness_shadow


@dataclass(frozen=True)
class Score:
    signal: str
    urgency_score: int
    next_action: str
    next_action_reason: str
    status: str
    task_type: str
    task_title: str
    task_description: str
    task_priority: str
    due_at: datetime
    last_buyer_message_at: datetime | None
    latest_message_at: datetime | None
    buyer_message_count: int
    stale: bool
    base_urgency_score: int | None = None
    readiness_ranking_delta: int | None = None


@dataclass
class Listing:
    listing_id: str
    brokerage_id: str
    property_type: str
    spa_data: dict


@dataclass
class Message:
    conversation_id: str
    role: str
    content: str
    intent: str | None
    timestamp: datetime


@dataclass
class Conversation:
    conversation_id: str
    brokerage_id: str
    listing_id: str
    buyer_phone: str
    buyer_name: str
    detected_budget: int | None
    escalation_reason: str | None = None
    listing: Listing | None = None
    messages: list[Message] | None = None


def _score(**overrides) -> Score:
    now = datetime(2026, 6, 21, 9, 0, 0)
    base = {
        "signal": "ready_to_view",
        "urgency_score": 78,
        "next_action": "book_viewing",
        "next_action_reason": "Buyer asked about viewing.",
        "status": "viewing",
        "task_type": "viewing",
        "task_title": "Book viewing: Sara",
        "task_description": "Confirm slots.",
        "task_priority": "high",
        "due_at": now + timedelta(minutes=30),
        "last_buyer_message_at": now,
        "latest_message_at": now,
        "buyer_message_count": 2,
        "stale": False,
    }
    base.update(overrides)
    return Score(**base)


def _conversation(*, detected_budget=None, latest_intent="viewing_request") -> Conversation:
    listing = Listing(
        listing_id="listing-1",
        brokerage_id="brokerage-1",
        property_type="ready",
        spa_data={"project": "Shadow Tower"},
    )
    conv = Conversation(
        conversation_id="conversation-1",
        brokerage_id="brokerage-1",
        listing_id="listing-1",
        buyer_phone="+971501234567",
        buyer_name="Sara",
        detected_budget=detected_budget,
    )
    conv.listing = listing
    conv.messages = [
        Message(
            conversation_id="conversation-1",
            role="user",
            content="Can I view it tomorrow?",
            intent=latest_intent,
            timestamp=datetime(2026, 6, 21, 9, 0, 0),
        )
    ]
    return conv


def _effective(**values):
    return {
        field: {
            "value": value,
            "provenance": "agent_confirmed",
            "confidence": None,
            "source_message_id": None,
            "confirmed_by": "agent-1",
            "updated_at": "2026-06-21T00:00:00",
            "suggestion": None,
        }
        for field, value in values.items()
    }


def test_readiness_shadow_metadata_appears_for_profile_fields():
    shadow = build_hot_list_readiness_shadow(
        effective_buyer_fields=_effective(
            budget_max_aed=2_000_000,
            financing="cash",
            purpose="end_user",
            viewing_availability="tomorrow afternoon",
            other_agent_status="not_working_with_agent",
        ),
        conversation=_conversation(),
        score=_score(),
    )

    assert shadow["mode"] == "ranking_input"
    assert shadow["used_for_ranking"] is True
    assert shadow["ranking_delta"] > 0
    assert shadow["used_for_thresholds"] is False
    assert shadow["used_for_tasks"] is False
    assert shadow["deal_readiness"]["stage"] == "viewing_ready"
    assert shadow["deal_readiness"]["present_fields"]["budget_max_aed"] == 2_000_000
    assert "viewing_availability" in shadow["deal_readiness"]["present_fields"]


def test_missing_readiness_data_still_produces_shadow_without_dropping_candidate():
    shadow = build_hot_list_readiness_shadow(
        effective_buyer_fields={},
        conversation=_conversation(detected_budget=None),
        score=_score(signal="cold", urgency_score=20, next_action="follow_up"),
    )

    assert shadow["mode"] == "ranking_input"
    assert shadow["used_for_ranking"] is False
    assert shadow["ranking_delta"] == 0
    assert shadow["ranked_urgency_score"] == 20
    assert shadow["deal_readiness"]["stage"] == "new"
    assert "budget" in shadow["deal_readiness"]["missing_fields"]


def test_ranking_input_does_not_mutate_hot_list_score_objects():
    score_a = _score(urgency_score=90, signal="firm_offer", next_action="review_offer")
    score_b = _score(urgency_score=70, signal="ready_to_view", next_action="book_viewing")
    before_a = asdict(score_a)
    before_b = asdict(score_b)

    shadow_a = build_hot_list_readiness_shadow(
        effective_buyer_fields=_effective(budget_max_aed=2_000_000),
        conversation=_conversation(),
        score=score_a,
    )
    build_hot_list_readiness_shadow(
        effective_buyer_fields={},
        conversation=_conversation(),
        score=score_b,
    )

    assert asdict(score_a) == before_a
    assert asdict(score_b) == before_b
    assert shadow_a["base_urgency_score"] == 90


def test_shadow_metadata_does_not_reference_side_effect_scope():
    shadow = build_hot_list_readiness_shadow(
        effective_buyer_fields=_effective(financing="cash"),
        conversation=_conversation(),
        score=_score(),
    )
    rendered = str(shadow).lower()

    assert "whatsapp" not in rendered
    assert "send" not in rendered
    assert "notification" not in rendered
    assert "draft" not in rendered
    assert "lead ingest" not in rendered
    assert "verified facts" not in rendered
