from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final, TypeAlias, assert_never

JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]

EMAIL_RE: Final = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
WHATSAPP_RE: Final = re.compile(
    r"\b(?:wa\.me/|whatsapp:\s*)\+?\d[\d\s().-]{6,}\d\b",
    re.IGNORECASE,
)
UAE_PHONE_RE: Final = re.compile(r"(?<!\d)\+?971[\s().-]*(?:\d[\s().-]*){9}(?!\d)")
UAE_LOCAL_MOBILE_RE: Final = re.compile(
    r"(?<!\d)0[\s().-]*5[\s().-]*(?:\d[\s().-]*){8}(?!\d)",
)
INTERNATIONAL_PHONE_RE: Final = re.compile(r"(?<!\d)\+[1-9]\d{0,2}(?:[\s().-]*\d){7,14}(?!\d)")
CONVERSATION_TOKEN_RE: Final = re.compile(r"\bconv_[A-Za-z0-9][A-Za-z0-9_-]{7,}\b")
MIN_NAME_TOKEN_LENGTH: Final = 3
COMMON_NAME_TOKENS: Final = frozenset((
    "a",
    "an",
    "and",
    "buyer",
    "client",
    "customer",
    "dr",
    "lead",
    "mr",
    "mrs",
    "ms",
    "sir",
    "the",
))
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


@dataclass(frozen=True, slots=True)
class SellerSummaryRedactionContext:
    buyer_name: str | None
    buyer_phone: str
    conversation_id: str


def sanitize_seller_ai_summary(summary: JsonValue, context: SellerSummaryRedactionContext) -> JsonValue:
    match summary:
        case str():
            return _redact_text(summary, context)
        case list():
            return _sanitize_list(summary, context)
        case dict():
            return {
                key: _sanitize_json_value(value, context)
                for key, value in summary.items()
                if key in SELLER_SUMMARY_KEYS
            }
        case None | bool() | int() | float():
            return summary
        case unreachable:
            assert_never(unreachable)


def _redact_text(text: str, context: SellerSummaryRedactionContext) -> str:
    redacted = WHATSAPP_RE.sub("[redacted whatsapp]", text)
    redacted = EMAIL_RE.sub("[redacted email]", redacted)
    redacted = _redact_exact(redacted, context.conversation_id, "[redacted id]")
    redacted = CONVERSATION_TOKEN_RE.sub("[redacted id]", redacted)
    redacted = _phone_pattern(context.buyer_phone).sub("[redacted phone]", redacted)
    redacted = UAE_PHONE_RE.sub("[redacted phone]", redacted)
    redacted = UAE_LOCAL_MOBILE_RE.sub("[redacted phone]", redacted)
    redacted = INTERNATIONAL_PHONE_RE.sub("[redacted phone]", redacted)
    redacted = _redact_exact(redacted, context.buyer_name, "[redacted buyer]")
    for name_part in _buyer_name_parts(context.buyer_name):
        redacted = _redact_word(redacted, name_part, "[redacted buyer]")
    return redacted


def _sanitize_json_value(value: JsonValue, context: SellerSummaryRedactionContext) -> JsonValue:
    match value:
        case str():
            return _redact_text(value, context)
        case list():
            return _sanitize_list(value, context)
        case dict():
            return _sanitize_dict(value, context)
        case None | bool() | int() | float():
            return value
        case unreachable:
            assert_never(unreachable)


def _sanitize_dict(values: dict[str, JsonValue], context: SellerSummaryRedactionContext) -> dict[str, JsonValue]:
    return {_redact_text(key, context): _sanitize_json_value(value, context) for key, value in values.items()}


def _sanitize_list(values: list[JsonValue], context: SellerSummaryRedactionContext) -> list[JsonValue]:
    sanitized: list[JsonValue] = []
    for value in values:
        sanitized.append(_sanitize_json_value(value, context))
    return sanitized


def _redact_exact(text: str, secret: str | None, placeholder: str) -> str:
    if not secret:
        return text
    return re.sub(re.escape(secret), placeholder, text, flags=re.IGNORECASE)


def _redact_word(text: str, secret: str, placeholder: str) -> str:
    return re.sub(rf"(?<!\w){re.escape(secret)}(?!\w)", placeholder, text, flags=re.IGNORECASE)


def _buyer_name_parts(buyer_name: str | None) -> tuple[str, ...]:
    if not buyer_name:
        return ()
    parts: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[^\W\d_][^\W\d_'-]*(?:['-][^\W\d_]+)*", buyer_name, flags=re.UNICODE):
        normalized = token.casefold()
        if (
            len(normalized) >= MIN_NAME_TOKEN_LENGTH
            and normalized not in COMMON_NAME_TOKENS
            and normalized not in seen
        ):
            parts.append(token)
            seen.add(normalized)
    return tuple(parts)


def _phone_pattern(phone: str) -> re.Pattern[str]:
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return re.compile(r"a^")
    digit_pattern = r"[\s().-]*".join(re.escape(digit) for digit in digits)
    return re.compile(rf"(?<!\d)\+?{digit_pattern}(?!\d)")
