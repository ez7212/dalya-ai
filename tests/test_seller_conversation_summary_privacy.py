from __future__ import annotations

import json

import pytest

from app.core.seller_summary_privacy import JsonValue, sanitize_seller_ai_summary
from scripts.seller_summary_privacy_contract import (
    BUYER_NAME,
    BUYER_PHONE,
    CONVERSATION_ID,
    SAFE_CONTEXT,
    SELLER_SUMMARY_KEYS,
    pure_phone_redaction_passes,
    privacy_context,
    recursive_redaction_expected,
    recursive_redaction_input,
    seeded_ai_summary,
    seeded_secrets,
)
from scripts.seller_summary_privacy_isolation import install_isolated_app_database

ISOLATED_DATABASE = install_isolated_app_database("pytest")


@pytest.fixture
def seller_summary_rows() -> None:
    from scripts.seller_summary_privacy_app_probe import cleanup_rows, seed_rows

    cleanup_rows()
    seed_rows()
    try:
        yield
    finally:
        cleanup_rows()


def _assert_seeded_pii_absent(rendered: str) -> None:
    for secret in seeded_secrets():
        assert secret not in rendered


def test_seller_conversations_redact_nested_ai_summary_without_mutating_stored_summary(
    seller_summary_rows: None,
) -> None:
    from scripts.seller_summary_privacy_app_probe import run_app_probe

    result = run_app_probe()
    rendered = json.dumps(result.seller_payload, sort_keys=True)

    assert result.seller_status_code == 200, result.seller_text
    _assert_seeded_pii_absent(rendered)
    assert SAFE_CONTEXT in rendered
    assert result.placeholders == (
        "[redacted buyer]",
        "[redacted phone]",
        "[redacted email]",
        "[redacted whatsapp]",
        "[redacted id]",
    )
    assert isinstance(result.seller_payload, dict)
    conversations = result.seller_payload["conversations"]
    assert isinstance(conversations, list)
    first_conversation = conversations[0]
    assert isinstance(first_conversation, dict)
    summary = first_conversation["summary"]
    assert isinstance(summary, dict)
    assert set(summary) <= SELLER_SUMMARY_KEYS
    assert first_conversation["buyer_label"] == "Buyer 1"
    assert result.stored_summary_unchanged is True
    assert result.stored_conversation_identity_preserved is True
    assert result.sqlite_database_path == str(ISOLATED_DATABASE.path)


def test_seller_summary_sanitizer_redacts_first_name_only_buyer_mention() -> None:
    summary: JsonValue = {"buyer_context": "Sara wants a viewing tomorrow"}

    sanitized = sanitize_seller_ai_summary(summary, privacy_context())

    assert sanitized == {"buyer_context": f"[redacted buyer] {SAFE_CONTEXT}"}


def test_seller_summary_sanitizer_redacts_plus_country_code_phone_numbers() -> None:
    assert pure_phone_redaction_passes() is True


def test_seller_summary_sanitizer_recursively_redacts_nested_contract_values() -> None:
    sanitized = sanitize_seller_ai_summary(recursive_redaction_input(), privacy_context())

    assert sanitized == recursive_redaction_expected()


def test_agent_dashboard_still_exposes_authorized_buyer_identity(
    seller_summary_rows: None,
) -> None:
    from scripts.seller_summary_privacy_app_probe import run_app_probe

    result = run_app_probe()

    assert result.agent_status_code == 200
    assert result.agent_identity_preserved is True
    assert result.stored_conversation_identity_preserved is True


def test_seller_conversations_cross_seller_access_remains_forbidden(
    seller_summary_rows: None,
) -> None:
    from scripts.seller_summary_privacy_app_probe import run_app_probe

    result = run_app_probe()

    assert result.forbidden_status_code == 403
    assert result.forbidden_response_leak_free is True


def test_seeded_ai_summary_fixture_contains_contract_pii() -> None:
    rendered = json.dumps(seeded_ai_summary(), sort_keys=True)

    assert BUYER_NAME in rendered
    assert BUYER_PHONE in rendered
    assert CONVERSATION_ID in rendered
