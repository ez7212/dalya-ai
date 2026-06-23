from __future__ import annotations

from typing import Final

from app.core.seller_summary_privacy import (
    JsonValue,
    SellerSummaryRedactionContext,
    sanitize_seller_ai_summary,
)

BROKERAGE_ID: Final = "task-4-summary-privacy-brokerage"
SELLER_ID: Final = "task-4-summary-privacy-seller"
OTHER_SELLER_ID: Final = "task-4-summary-privacy-other-seller"
AGENT_ID: Final = "task-4-summary-privacy-agent"
LISTING_ID: Final = "task-4-summary-privacy-listing"
CONVERSATION_ID: Final = "conv_01HPIISECRET1234567890"
BUYER_NAME: Final = "Sara Privacy"
BUYER_FIRST_NAME: Final = "Sara"
BUYER_PHONE: Final = "+971501112222"
BUYER_EMAIL: Final = "sara@example.com"
BUYER_WHATSAPP_LINK: Final = "wa.me/971501112222"
BUYER_WHATSAPP_URI: Final = "whatsapp:+971501112222"
BUYER_SPACED_PHONE: Final = "+971 50 111 2222"
BUYER_DIGITS: Final = "971501112222"
BUYER_LOCAL_PHONE: Final = "0501112222"
BUYER_LOCAL_SPACED_PHONE: Final = "050 111 2222"
BUYER_UK_PHONE: Final = "+44 7700 900123"
BUYER_US_PHONE: Final = "+1 415 555 2671"
SAFE_CONTEXT: Final = "wants a viewing tomorrow"
SELLER_SUMMARY_KEYS: Final = frozenset((
    "topics",
    "interest_level",
    "sentiment",
    "key_question",
    "next_step_hint",
    "buyer_context",
    "summary",
    "_fallback",
))


def seeded_ai_summary() -> JsonValue:
    return {
        "topics": [
            f"{BUYER_NAME} asked about parking",
            f"{BUYER_FIRST_NAME} asked to view at {BUYER_LOCAL_PHONE}",
            {
                "raw": (
                    f"{BUYER_WHATSAPP_LINK} and {BUYER_WHATSAPP_URI}; "
                    f"call {BUYER_SPACED_PHONE}"
                ),
            },
        ],
        "sentiment": f"{BUYER_FIRST_NAME} {SAFE_CONTEXT}; alternate contact {BUYER_UK_PHONE}",
        "key_question": f"Can {BUYER_NAME} get a viewing? {SAFE_CONTEXT}",
        "next_step_hint": f"Email {BUYER_EMAIL}, {BUYER_WHATSAPP_LINK}, and {BUYER_LOCAL_PHONE}.",
        "buyer_context": (
            f"{BUYER_NAME} called from {BUYER_LOCAL_SPACED_PHONE}; "
            f"backup {BUYER_US_PHONE}; {SAFE_CONTEXT}"
        ),
        "summary": {
            "one_line": f"{BUYER_NAME} at {BUYER_PHONE} {SAFE_CONTEXT}",
            "reasons": [
                f"{BUYER_FIRST_NAME} asked about the view",
                {"raw": f"{BUYER_EMAIL}; {SAFE_CONTEXT}"},
            ],
        },
        f"prompt_{BUYER_NAME}_{BUYER_LOCAL_PHONE}": {
            "one_line": f"{BUYER_NAME} at {BUYER_PHONE} {SAFE_CONTEXT}; thread {CONVERSATION_ID}",
        },
        "_fallback": f"{BUYER_NAME} {CONVERSATION_ID} {SAFE_CONTEXT}",
    }


def seeded_secrets() -> tuple[str, ...]:
    return (
        BUYER_NAME,
        BUYER_FIRST_NAME,
        BUYER_PHONE,
        BUYER_EMAIL,
        BUYER_WHATSAPP_LINK,
        BUYER_WHATSAPP_URI,
        BUYER_SPACED_PHONE,
        BUYER_DIGITS,
        BUYER_LOCAL_PHONE,
        BUYER_LOCAL_SPACED_PHONE,
        BUYER_UK_PHONE,
        BUYER_US_PHONE,
        CONVERSATION_ID,
    )


def privacy_context() -> SellerSummaryRedactionContext:
    return SellerSummaryRedactionContext(BUYER_NAME, BUYER_PHONE, CONVERSATION_ID)


def pure_first_name_redaction_passes() -> bool:
    summary: JsonValue = {"buyer_context": f"{BUYER_FIRST_NAME} {SAFE_CONTEXT}"}
    sanitized = sanitize_seller_ai_summary(summary, privacy_context())
    return sanitized == {"buyer_context": f"[redacted buyer] {SAFE_CONTEXT}"}


def pure_phone_redaction_passes() -> bool:
    summary: JsonValue = {
        "buyer_context": f"Call {BUYER_UK_PHONE} or {BUYER_US_PHONE}; {SAFE_CONTEXT}",
    }
    sanitized = sanitize_seller_ai_summary(summary, privacy_context())
    return sanitized == {
        "buyer_context": f"Call [redacted phone] or [redacted phone]; {SAFE_CONTEXT}",
    }


def recursive_redaction_expected() -> JsonValue:
    return {
        "buyer_context": {"one_line": f"[redacted buyer] {SAFE_CONTEXT} [redacted phone]"},
        "summary": {
            "one_line": f"[redacted buyer] {SAFE_CONTEXT} [redacted phone]",
            "details": [
                "[redacted buyer] asked for documents via [redacted email]",
                {"raw": f"[redacted whatsapp]; {SAFE_CONTEXT}"},
            ],
        },
        "topics": [
            {"raw": f"[redacted buyer] {SAFE_CONTEXT} [redacted phone]"},
            {"[redacted buyer] [redacted phone]": SAFE_CONTEXT},
            ["[redacted buyer] asked to view at [redacted phone]"],
        ],
    }


def recursive_redaction_input() -> JsonValue:
    return {
        "buyer_context": {"one_line": f"{BUYER_NAME} {SAFE_CONTEXT} {BUYER_PHONE}"},
        "summary": {
            "one_line": f"{BUYER_NAME} {SAFE_CONTEXT} {BUYER_PHONE}",
            "details": [
                f"{BUYER_FIRST_NAME} asked for documents via {BUYER_EMAIL}",
                {"raw": f"{BUYER_WHATSAPP_URI}; {SAFE_CONTEXT}"},
            ],
        },
        "topics": [
            {"raw": f"{BUYER_NAME} {SAFE_CONTEXT} {BUYER_PHONE}"},
            {f"{BUYER_NAME} {BUYER_LOCAL_PHONE}": SAFE_CONTEXT},
            [f"{BUYER_FIRST_NAME} asked to view at {BUYER_LOCAL_PHONE}"],
        ],
        "raw_prompt": f"{BUYER_NAME} {BUYER_PHONE}",
    }


def pure_recursive_redaction_passes() -> bool:
    sanitized = sanitize_seller_ai_summary(recursive_redaction_input(), privacy_context())
    return sanitized == recursive_redaction_expected()
