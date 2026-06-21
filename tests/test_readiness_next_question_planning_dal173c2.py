"""DAL-173C2 — DealReadiness next-question planning tests.

Pure unit tests for the optional chatbot planning metadata. These tests do not
touch the network, WhatsApp send path, hot-list ranking, drafts, lead ingest, or
a real database.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.core.chatbot_engine import ChatbotEngine
from app.core.prompt_builder import (
    build_readiness_next_question_section,
    buyer_message_allows_readiness_question,
)
from app.schemas.conversation import BuyerIntent


class _FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class _ReadOnlyFakeDb:
    def __init__(self, profile):
        self.profile = profile
        self.queries = []

    def query(self, model):
        self.queries.append(getattr(model, "__name__", str(model)))
        return _FakeQuery(self.profile)

    def add(self, *_args, **_kwargs):  # pragma: no cover - called only on regression
        raise AssertionError("readiness planning must not write")

    def commit(self):  # pragma: no cover - called only on regression
        raise AssertionError("readiness planning must not commit")

    def flush(self):  # pragma: no cover - called only on regression
        raise AssertionError("readiness planning must not flush")


def _profile():
    return SimpleNamespace(profile_id="profile-1")


def _effective(values):
    return {name: {"value": value} for name, value in values.items()}


def test_missing_viewing_availability_asks_one_question(monkeypatch):
    monkeypatch.setattr(
        "app.core.buyer_profiles.effective_fields",
        lambda _db, _profile: _effective(
            {
                "budget_max_aed": 3_000_000,
                "purpose": "end_user",
                "financing": "cash",
                "target_areas": ["Dubai Hills"],
            }
        ),
    )
    question = ChatbotEngine._deal_readiness_next_question_for_prompt(
        _ReadOnlyFakeDb(_profile()),
        brokerage_id="brokerage-1",
        buyer_phone="+971500000000",
        intent=BuyerIntent.viewing_request,
        fallback_budget_aed=None,
        listing_id="listing-1",
    )

    assert question == "What viewing window works for you?"
    assert question.count("?") == 1


def test_missing_other_agent_status_can_be_asked(monkeypatch):
    monkeypatch.setattr(
        "app.core.buyer_profiles.effective_fields",
        lambda _db, _profile: _effective(
            {
                "budget_max_aed": 2_500_000,
                "purpose": "investment",
                "financing": "cash",
                "timeline": "this quarter",
                "target_areas": ["JVC"],
            }
        ),
    )
    question = ChatbotEngine._deal_readiness_next_question_for_prompt(
        _ReadOnlyFakeDb(_profile()),
        brokerage_id="brokerage-1",
        buyer_phone="+971500000000",
        intent=BuyerIntent.general_enquiry,
        fallback_budget_aed=None,
        listing_id="listing-1",
    )

    assert question == "Are you already working with another agent on this search?"


def test_existing_confirmed_viewing_availability_is_not_reasked(monkeypatch):
    monkeypatch.setattr(
        "app.core.buyer_profiles.effective_fields",
        lambda _db, _profile: _effective(
            {
                "budget_max_aed": 3_000_000,
                "purpose": "end_user",
                "financing": "cash",
                "target_areas": ["Dubai Hills"],
                "viewing_availability": "Friday afternoon",
            }
        ),
    )
    question = ChatbotEngine._deal_readiness_next_question_for_prompt(
        _ReadOnlyFakeDb(_profile()),
        brokerage_id="brokerage-1",
        buyer_phone="+971500000000",
        intent=BuyerIntent.viewing_request,
        fallback_budget_aed=None,
        listing_id="listing-1",
    )

    assert question is None


def test_direct_buyer_question_is_not_replaced_by_qualification():
    assert not buyer_message_allows_readiness_question("What is the asking price?")
    assert buyer_message_allows_readiness_question("This is interesting")
    assert (
        build_readiness_next_question_section(
            "What budget range should I keep in mind?",
            latest_buyer_message="What is the asking price?",
        )
        == ""
    )


def test_prompt_section_is_one_question_and_planning_only():
    section = build_readiness_next_question_section(
        "What buying timeline are you working with?",
        latest_buyer_message="Looks interesting",
    )

    assert section.count("?") == 1
    assert "exactly this one question" in section
    lowered = section.lower()
    assert "whatsapp" not in lowered
    assert "hot-list" not in lowered
    assert "ranking" not in lowered
    assert "draft" not in lowered


def test_low_signal_or_unavailable_profile_preserves_existing_behavior(monkeypatch):
    monkeypatch.setattr("app.core.buyer_profiles.effective_fields", lambda _db, _profile: {})
    question = ChatbotEngine._deal_readiness_next_question_for_prompt(
        _ReadOnlyFakeDb(_profile()),
        brokerage_id="brokerage-1",
        buyer_phone="+971500000000",
        intent=BuyerIntent.general_enquiry,
        fallback_budget_aed=None,
        listing_id="listing-1",
    )
    no_profile_question = ChatbotEngine._deal_readiness_next_question_for_prompt(
        _ReadOnlyFakeDb(None),
        brokerage_id="brokerage-1",
        buyer_phone="+971500000000",
        intent=BuyerIntent.viewing_request,
        fallback_budget_aed=None,
        listing_id="listing-1",
    )

    assert question is None
    assert no_profile_question is None
