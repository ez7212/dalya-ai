from __future__ import annotations

import re
from typing import Any


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\s().-]*){8,15}\d(?!\w)")
_WHATSAPP_PHONE_RE = re.compile(r"whatsapp:\s*(?:\+?\d[\s().-]*){8,15}\d", re.IGNORECASE)
_TOKEN_RE = re.compile(r"\b(?:[A-Za-z0-9_-]{18,}|[0-9a-f]{24,})\b")


def redact_pii(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {key: redact_pii(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_pii(item) for item in value]
    if not isinstance(value, str):
        return value

    redacted = _WHATSAPP_PHONE_RE.sub("whatsapp:[redacted phone]", value)
    redacted = _EMAIL_RE.sub("[redacted email]", redacted)
    redacted = _PHONE_RE.sub("[redacted phone]", redacted)
    redacted = _TOKEN_RE.sub("[redacted token]", redacted)
    return redacted


def redacted_preview(value: str | None, limit: int = 200) -> str:
    return str(redact_pii(value or ""))[:limit]

