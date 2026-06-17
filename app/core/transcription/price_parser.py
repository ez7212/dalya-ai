from __future__ import annotations

import re
from decimal import Decimal

from app.core.transcription.models import LowConfidenceSegment, PriceExtraction, TranscriptionContext


NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

PRICE_CONTEXT_RE = re.compile(
    r"\b(?:offer|asking|price|budget|pay|sell|accept|aed|dirhams?|million|thousand|m)\b",
    re.IGNORECASE,
)
NUMERIC_PRICE_RE = re.compile(
    r"\b(?:AED\s*)?(\d+(?:\.\d+)?)\s*(m|mn|million|k|thousand|dirhams?|aed)?\b",
    re.IGNORECASE,
)
POINT_WORD_RE = re.compile(
    r"\b((?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty)(?:\s+and\s+a\s+half|\s+point\s+(?:one|two|three|four|five|six|seven|eight|nine)|\s+m\s+(?:one|two|three|four|five|six|seven|eight|nine))?)\s*(million|m|dirhams?|aed)?\b",
    re.IGNORECASE,
)
HUNDRED_THOUSAND_RE = re.compile(
    r"\b((?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[-\s]?(?:one|two|three|four|five|six|seven|eight|nine)?)\s+hundred\s+thousand\b",
    re.IGNORECASE,
)


def extract_prices(
    transcript: str,
    context: TranscriptionContext | None = None,
) -> tuple[list[PriceExtraction], list[LowConfidenceSegment]]:
    context = context or TranscriptionContext()
    prices: list[PriceExtraction] = []
    low_segments: list[LowConfidenceSegment] = []
    spans: list[tuple[int, int]] = []

    ambiguous = _extract_ambiguous_numeric_options(transcript, context)
    if ambiguous:
        prices.extend(ambiguous)
        for item in ambiguous:
            low_segments.append(
                LowConfidenceSegment(
                    source_phrase=item.source_phrase,
                    reason="Multiple possible price candidates were spoken together.",
                    candidates=[str(amount) for amount in item.candidate_amounts],
                )
            )

    for match in HUNDRED_THOUSAND_RE.finditer(transcript):
        amount = _word_number(match.group(1))
        if amount is None:
            continue
        prices.append(
            PriceExtraction(
                amount=amount * 100_000,
                confidence="high",
                source_phrase=match.group(0),
            )
        )
        spans.append(match.span())

    for match in POINT_WORD_RE.finditer(transcript):
        if _overlaps(match.span(), spans):
            continue
        amount_millions = _parse_spoken_millions(match.group(1))
        if amount_millions is None:
            continue
        unit = match.group(2)
        inferred = not unit
        confidence = _implicit_confidence(transcript, match.span(), context) if inferred else "high"
        prices.append(
            PriceExtraction(
                amount=int(amount_millions * Decimal("1000000")),
                confidence=confidence,
                source_phrase=match.group(0),
                unit_inferred=inferred,
                note="Unit inferred from conversation context." if inferred else None,
            )
        )
        if inferred and confidence == "low":
            low_segments.append(
                LowConfidenceSegment(
                    source_phrase=match.group(0),
                    reason="Price unit was implicit and inferred from context.",
                )
            )
        spans.append(match.span())

    for match in NUMERIC_PRICE_RE.finditer(transcript):
        if _overlaps(match.span(), spans):
            continue
        phrase = match.group(0)
        if len(match.group(1)) <= 2 and not match.group(2):
            continue
        amount = Decimal(match.group(1))
        unit = (match.group(2) or "").lower()
        if not PRICE_CONTEXT_RE.search(_window(transcript, match.start(), match.end())) and not (
            context.asking_price_aed and amount < 100
        ):
            continue
        inferred = not unit
        multiplier = _unit_multiplier(unit)
        confidence = "high"
        note = None
        if inferred:
            multiplier = _infer_unit_multiplier(amount, context)
            confidence = "low"
            note = "Unit inferred from conversation context."
        prices.append(
            PriceExtraction(
                amount=int(amount * multiplier),
                confidence=confidence,
                source_phrase=phrase,
                unit_inferred=inferred,
                note=note,
            )
        )
        if inferred:
            low_segments.append(
                LowConfidenceSegment(
                    source_phrase=phrase,
                    reason="Numeric price was spoken without an explicit unit.",
                )
            )

    return _dedupe_prices(prices), low_segments


def _extract_ambiguous_numeric_options(
    transcript: str,
    context: TranscriptionContext,
) -> list[PriceExtraction]:
    results: list[PriceExtraction] = []
    for match in re.finditer(r"\b(\d+(?:\.\d+)?)\s+or\s+(\d+(?:\.\d+)?)\b", transcript, re.IGNORECASE):
        if not PRICE_CONTEXT_RE.search(_window(transcript, match.start(), match.end())):
            continue
        amounts = [int(Decimal(value) * _infer_unit_multiplier(Decimal(value), context)) for value in match.groups()]
        group = f"ambiguous-price-{match.start()}"
        for amount, source in zip(amounts, match.groups()):
            results.append(
                PriceExtraction(
                    amount=amount,
                    confidence="low",
                    source_phrase=source,
                    unit_inferred=True,
                    ambiguity_group=group,
                    candidate_amounts=amounts,
                    note="Ambiguous alternative price candidate.",
                )
            )
    return results


def _parse_spoken_millions(phrase: str) -> Decimal | None:
    phrase = phrase.lower().replace("-", " ")
    if "and a half" in phrase:
        first = phrase.split()[0]
        base = NUMBER_WORDS.get(first)
        return Decimal(base) + Decimal("0.5") if base is not None else None
    if " point " in phrase:
        left, right = phrase.split(" point ", 1)
        left_value = NUMBER_WORDS.get(left.strip())
        right_value = NUMBER_WORDS.get(right.strip())
        if left_value is None or right_value is None:
            return None
        return Decimal(left_value) + (Decimal(right_value) / Decimal(10))
    if " m " in phrase:
        left, right = phrase.split(" m ", 1)
        left_value = NUMBER_WORDS.get(left.strip())
        right_value = NUMBER_WORDS.get(right.strip())
        if left_value is None or right_value is None:
            return None
        return Decimal(left_value) + (Decimal(right_value) / Decimal(10))
    value = NUMBER_WORDS.get(phrase.strip())
    if value is None or value > 20:
        return None
    return Decimal(value)


def _word_number(phrase: str) -> int | None:
    total = 0
    for part in phrase.lower().replace("-", " ").split():
        value = NUMBER_WORDS.get(part)
        if value is None:
            return None
        total += value
    return total


def _unit_multiplier(unit: str) -> Decimal:
    if unit in {"m", "mn", "million"}:
        return Decimal("1000000")
    if unit in {"k", "thousand"}:
        return Decimal("1000")
    return Decimal("1")


def _infer_unit_multiplier(amount: Decimal, context: TranscriptionContext) -> Decimal:
    anchors = [context.asking_price_aed or 0, *context.recent_offer_amounts_aed]
    if amount < 100 and any(anchor >= 1_000_000 for anchor in anchors):
        return Decimal("1000000")
    if amount < 100 and not anchors:
        return Decimal("1000000")
    return Decimal("1")


def _implicit_confidence(
    transcript: str,
    span: tuple[int, int],
    context: TranscriptionContext,
) -> str:
    nearby = _window(transcript, span[0], span[1])
    if re.search(r"\b(offer|pay|asking|price|budget)\b", nearby, re.IGNORECASE) and context.asking_price_aed:
        return "high"
    return "low"


def _window(text: str, start: int, end: int, size: int = 45) -> str:
    return text[max(0, start - size) : min(len(text), end + size)]


def _overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    return any(span[0] < existing[1] and existing[0] < span[1] for existing in spans)


def _dedupe_prices(prices: list[PriceExtraction]) -> list[PriceExtraction]:
    seen: set[tuple[str, int | None, str | None]] = set()
    result: list[PriceExtraction] = []
    for price in prices:
        key = (price.source_phrase.casefold(), price.amount, price.ambiguity_group)
        if key in seen:
            continue
        seen.add(key)
        result.append(price)
    return result
