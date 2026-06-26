"""Regression tests for buyer qualification signal extraction.

Locks in the fix where the classifier's extracted_purpose / extracted_area were
being dropped (every buyer showed "Missing: Purpose, Location"), plus the
cash-ready financing phrase.
"""
from app.core.buyer_profiles import extract_qualification_signals


def test_purpose_and_area_are_recorded_from_intent_data():
    signals = extract_qualification_signals(
        "Looking at options",
        intent_data={"extracted_purpose": "investment", "extracted_area": "Dubai Hills"},
    )
    assert signals["purpose"][0] == "investment"
    assert signals["target_areas"][0] == "Dubai Hills"


def test_null_purpose_and_area_are_ignored():
    signals = extract_qualification_signals(
        "hi",
        intent_data={"extracted_purpose": "null", "extracted_area": None},
    )
    assert "purpose" not in signals
    assert "target_areas" not in signals


def test_cash_ready_is_detected_as_cash_financing():
    signals = extract_qualification_signals("I'm cash-ready and want to buy", intent_data=None)
    assert signals["financing"][0] == "cash"


def test_full_message_captures_all_signals():
    signals = extract_qualification_signals(
        "I'm cash-ready and want to view this week",
        intent_data={"extracted_purpose": "end_user", "extracted_area": "Marina", "extracted_budget": 15000000},
    )
    assert signals["budget_max_aed"][0] == 15000000.0
    assert signals["financing"][0] == "cash"
    assert signals["timeline"][0] == "this week"
    assert signals["purpose"][0] == "end_user"
    assert signals["target_areas"][0] == "Marina"
