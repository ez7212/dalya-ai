import json

import pytest

from app.core import intent_classifier


class _FakeContent:
    def __init__(self, text: str):
        self.text = text


class _FakeMessages:
    def __init__(self, payload: dict):
        self.payload = payload

    def create(self, **_kwargs):
        return type("Resp", (), {"content": [_FakeContent(json.dumps(self.payload))]})()


class _FakeClient:
    def __init__(self, payload: dict):
        self.messages = _FakeMessages(payload)


@pytest.mark.no_db
def test_detect_intent_claude_sanitizes_non_string_intent(monkeypatch):
    monkeypatch.setattr(
        intent_classifier,
        "_get_client",
        lambda: _FakeClient(
            {
                "intent": {"value": "offer_submission"},
                "is_firm_offer": True,
                "offer_amount_aed": 1_500_000,
                "confidence": {"value": 0.9},
                "language_detected": {"value": "en"},
            }
        ),
    )

    result = intent_classifier.detect_intent_claude("I offer AED 1,500,000")

    assert isinstance(result["intent"], str)
    assert result["intent"] != {"value": "offer_submission"}
    assert result["confidence"] == 0.8
    assert result["language_detected"] == "en"
