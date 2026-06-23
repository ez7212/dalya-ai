from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.deal_readiness import compute_readiness
from app.core.hot_list_readiness import build_hot_list_readiness_shadow, readiness_ranking_input


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
        "urgency_score": 76,
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
        spa_data={"project": "Readiness Tower"},
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


def test_viewing_ready_readiness_adds_bounded_ranking_input():
    metadata = build_hot_list_readiness_shadow(
        effective_buyer_fields=_effective(
            budget_max_aed=2_000_000,
            financing="cash",
            purpose="end_user",
            timeline="this month",
            target_areas=["Dubai Hills"],
            viewing_availability="tomorrow afternoon",
            in_dubai_now="yes",
            other_agent_status="not_working_with_agent",
        ),
        conversation=_conversation(),
        score=_score(urgency_score=76),
    )

    assert metadata["mode"] == "ranking_input"
    assert metadata["used_for_ranking"] is True
    assert metadata["used_for_thresholds"] is False
    assert metadata["used_for_tasks"] is False
    assert metadata["ranking_delta"] == 15
    assert metadata["ranked_urgency_score"] == 91
    assert metadata["deal_readiness"]["stage"] == "viewing_ready"
    assert "Viewing-ready" in metadata["ranking_reason"]


def test_viewing_ready_buyer_can_outrank_recent_low_readiness_buyer():
    recent_low = build_hot_list_readiness_shadow(
        effective_buyer_fields=_effective(budget_max_aed=2_200_000),
        conversation=_conversation(latest_intent=None),
        score=_score(signal="budget_matched", next_action="follow_up", urgency_score=88),
    )
    viewing_ready = build_hot_list_readiness_shadow(
        effective_buyer_fields=_effective(
            budget_max_aed=2_000_000,
            financing="cash",
            purpose="end_user",
            timeline="this month",
            target_areas=["Dubai Hills"],
            viewing_availability="tomorrow afternoon",
            in_dubai_now="yes",
            other_agent_status="not_working_with_agent",
        ),
        conversation=_conversation(),
        score=_score(urgency_score=76),
    )

    assert recent_low["ranking_delta"] == 0
    assert viewing_ready["ranking_delta"] == 15
    assert viewing_ready["ranked_urgency_score"] > recent_low["ranked_urgency_score"]


def test_ordinary_qualified_readiness_keeps_old_urgency_dominant():
    profile = compute_readiness(
        {
            "budget_max_aed": 3_000_000,
            "financing": "cash",
            "purpose": "end_user",
            "timeline": "this month",
            "target_areas": ["Dubai Hills"],
            "other_agent_status": "not_working_with_agent",
        },
        conversation_ctx={"responsive": False},
        listing_ctx={"listing_id": "listing-1"},
    )

    ranking = readiness_ranking_input(profile)

    assert profile.stage.value == "qualified"
    assert ranking.delta == 0
    assert ranking.reason is None


def test_missing_and_malformed_readiness_falls_back_to_prior_urgency():
    score = _score(signal="cold", next_action="follow_up", urgency_score=68)
    metadata = build_hot_list_readiness_shadow(
        effective_buyer_fields={
            "budget_max_aed": {"suggestion": {"value": 2_000_000}},
            "financing": "cash",
        },
        conversation=_conversation(detected_budget=None, latest_intent=None),
        score=score,
    )

    assert metadata["deal_readiness"]["stage"] == "new"
    assert metadata["used_for_ranking"] is False
    assert metadata["ranking_delta"] == 0
    assert metadata["base_urgency_score"] == 68
    assert metadata["ranked_urgency_score"] == 68


def test_readiness_input_stays_out_of_task_creation_scope():
    metadata = build_hot_list_readiness_shadow(
        effective_buyer_fields=_effective(
            budget_max_aed=2_000_000,
            financing="cash",
            purpose="end_user",
            timeline="this month",
            target_areas=["Dubai Hills"],
            viewing_availability="tomorrow afternoon",
        ),
        conversation=_conversation(),
        score=_score(),
    )

    assert metadata["used_for_tasks"] is False
    assert "task_key" not in metadata
