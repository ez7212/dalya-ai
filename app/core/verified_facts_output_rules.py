from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal, TypedDict


AGENT_CONFIRMATION_LINE = (
    "The listing agent needs to confirm that specific finance, fee, legal, timeline, or payment detail before you rely on it."
)
QUALIFIED_ADVISOR_LINE = (
    "That legal or tax position needs confirmation from the listing agent or a qualified advisor before you rely on it."
)


@dataclass(frozen=True)
class OutputClaimRule:
    topic: str
    fact_key: str | None
    patterns: tuple[re.Pattern[str], ...]
    deferral: str
    require_numeric_fact_match: bool = True


class ExpectedMissingOutputGateFactKey(TypedDict):
    reason: str
    runtime_policy: str


OutputRuleFactKeyIntegrityProblem = Literal[
    "expected_missing_empty_reason",
    "expected_missing_runtime_policy",
    "missing_seed_fact_key",
]


@dataclass(frozen=True)
class OutputRuleFactKeyIntegrityFailure:
    fact_key: str
    topic: str | None
    problem: OutputRuleFactKeyIntegrityProblem


EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS: Final[dict[str, ExpectedMissingOutputGateFactKey]] = {
    "off_plan_mortgage_ltv_policy": {
        "reason": "Mortgage and LTV terms vary by buyer, bank, and listing; output claims must defer until the agent confirms deal-specific finance context.",
        "runtime_policy": "defer_only",
    },
    "generic_noc_fee": {
        "reason": "Developer NOC fees are transaction-specific and intentionally absent from direct seed facts; generic buyer-facing amounts must defer to the agent.",
        "runtime_policy": "defer_only",
    },
    "off_plan_payment_process_mechanics": {
        "reason": "Paid-to-date, seller cash, and developer-balance mechanics are listing-specific payment assertions that must defer unless grounded by transaction documents.",
        "runtime_policy": "defer_only",
    },
}


def verify_claim_rule_fact_keys(
    rules: Sequence[OutputClaimRule],
    seeded_fact_keys: Collection[str],
    *,
    expected_missing: Mapping[str, ExpectedMissingOutputGateFactKey] = EXPECTED_MISSING_OUTPUT_GATE_FACT_KEYS,
) -> tuple[OutputRuleFactKeyIntegrityFailure, ...]:
    failures: list[OutputRuleFactKeyIntegrityFailure] = []

    for fact_key, metadata in expected_missing.items():
        if not metadata["reason"].strip():
            failures.append(
                OutputRuleFactKeyIntegrityFailure(
                    fact_key=fact_key,
                    topic=None,
                    problem="expected_missing_empty_reason",
                )
            )
        if metadata["runtime_policy"] != "defer_only":
            failures.append(
                OutputRuleFactKeyIntegrityFailure(
                    fact_key=fact_key,
                    topic=None,
                    problem="expected_missing_runtime_policy",
                )
            )

    for rule in rules:
        if rule.fact_key is None:
            continue
        if rule.fact_key in seeded_fact_keys:
            continue
        if rule.fact_key in expected_missing:
            continue
        failures.append(
            OutputRuleFactKeyIntegrityFailure(
                fact_key=rule.fact_key,
                topic=rule.topic,
                problem="missing_seed_fact_key",
            )
        )

    return tuple(failures)


MONEY_PATTERN = r"(?:AED|Dh|Dhs)\s*\d[\d,]*(?:\.\d+)?"
NUMBER_DURATION_PATTERN = r"\d+(?:\s*[-–]\s*\d+)?\s*(?:business\s+)?(?:days?|weeks?|months?)"
PERCENT_PATTERN = r"\d+(?:\.\d+)?\s*%"
NUMERIC_CLAIM_RE = re.compile(
    rf"(?:{MONEY_PATTERN}|{NUMBER_DURATION_PATTERN}|{PERCENT_PATTERN})",
    re.IGNORECASE,
)

CLAIM_RULES: tuple[OutputClaimRule, ...] = (
    OutputClaimRule(
        topic="dld_fee",
        fact_key="dld_registration_fee_pct",
        patterns=(
            re.compile(
                rf"\b(?:dld|dubai\s+land\s+department)\b[^.?!\n]{{0,120}}(?:{PERCENT_PATTERN}|{MONEY_PATTERN})",
                re.IGNORECASE,
            ),
            re.compile(
                rf"\b(?:transfer|registration|government)\s+fees?\b[^.?!\n]{{0,120}}(?:{PERCENT_PATTERN}|{MONEY_PATTERN})",
                re.IGNORECASE,
            ),
        ),
        deferral=AGENT_CONFIRMATION_LINE,
    ),
    OutputClaimRule(
        topic="generic_fee_amount",
        fact_key=None,
        patterns=(
            re.compile(
                rf"\b(?:brokerage|broker|agency|agent|trustee|service|admin|processing)\s+fees?\b[^.?!\n]{{0,120}}(?:{PERCENT_PATTERN}|{MONEY_PATTERN})",
                re.IGNORECASE,
            ),
            re.compile(
                rf"(?:{PERCENT_PATTERN}|{MONEY_PATTERN})[^.?!\n]{{0,80}}\b(?:brokerage|broker|agency|agent|trustee|service|admin|processing)\s+fees?\b",
                re.IGNORECASE,
            ),
        ),
        deferral=AGENT_CONFIRMATION_LINE,
    ),
    OutputClaimRule(
        topic="mortgage_ltv",
        fact_key="off_plan_mortgage_ltv_policy",
        patterns=(
            re.compile(
                rf"\b(?:ltv|loan[-\s]?to[-\s]?value|mortgage|finance|financing|bank)\b[^.?!\n]{{0,120}}{PERCENT_PATTERN}",
                re.IGNORECASE,
            ),
            re.compile(
                rf"{PERCENT_PATTERN}[^.?!\n]{{0,80}}\b(?:ltv|loan[-\s]?to[-\s]?value|mortgage|finance|financing|bank)\b",
                re.IGNORECASE,
            ),
        ),
        deferral=AGENT_CONFIRMATION_LINE,
    ),
    OutputClaimRule(
        topic="noc_timeline",
        fact_key="specific_noc_transfer_timing",
        patterns=(
            re.compile(
                rf"\bnoc\b[^.?!\n]{{0,120}}{NUMBER_DURATION_PATTERN}",
                re.IGNORECASE,
            ),
            re.compile(
                rf"{NUMBER_DURATION_PATTERN}[^.?!\n]{{0,80}}\bnoc\b",
                re.IGNORECASE,
            ),
        ),
        deferral=AGENT_CONFIRMATION_LINE,
    ),
    OutputClaimRule(
        topic="trustee_closing_timeline",
        fact_key="specific_noc_transfer_timing",
        patterns=(
            re.compile(
                rf"\b(?:trustee|closing|transfer|mou|form\s*f)\b[^.?!\n]{{0,120}}{NUMBER_DURATION_PATTERN}",
                re.IGNORECASE,
            ),
        ),
        deferral=AGENT_CONFIRMATION_LINE,
    ),
    OutputClaimRule(
        topic="noc_fee",
        fact_key="generic_noc_fee",
        patterns=(
            re.compile(
                rf"\bnoc\b[^.?!\n]{{0,120}}(?:fee|cost|charge)[^.?!\n]{{0,80}}{MONEY_PATTERN}",
                re.IGNORECASE,
            ),
            re.compile(
                rf"{MONEY_PATTERN}[^.?!\n]{{0,80}}\bnoc\b[^.?!\n]{{0,80}}(?:fee|cost|charge)",
                re.IGNORECASE,
            ),
        ),
        deferral=AGENT_CONFIRMATION_LINE,
    ),
    OutputClaimRule(
        topic="legal_tax_advice",
        fact_key=None,
        patterns=(
            re.compile(
                r"\b(?:no\s+tax(?:\s+exposure)?|tax[-\s]?free|no\s+legal\s+(?:issue|risk)|do\s+not\s+need\s+legal\s+advice|don't\s+need\s+(?:a\s+)?lawyer|legally\s+(?:safe|allowed|guaranteed))\b",
                re.IGNORECASE,
            ),
        ),
        deferral=QUALIFIED_ADVISOR_LINE,
        require_numeric_fact_match=False,
    ),
    OutputClaimRule(
        topic="tenancy_legal_process",
        fact_key=None,
        patterns=(
            re.compile(
                rf"\b(?:tenant|tenanted|tenancy|vacant\s+possession|eviction|rental\s+notice|lease)\b[^.?!\n]{{0,140}}(?:{NUMBER_DURATION_PATTERN}|notary\s+public|registered\s+mail|guaranteed|automatic)",
                re.IGNORECASE,
            ),
            re.compile(
                rf"(?:{NUMBER_DURATION_PATTERN}|notary\s+public|registered\s+mail|guaranteed|automatic)[^.?!\n]{{0,100}}\b(?:tenant|tenanted|tenancy|vacant\s+possession|eviction|rental\s+notice|lease)\b",
                re.IGNORECASE,
            ),
        ),
        deferral=QUALIFIED_ADVISOR_LINE,
        require_numeric_fact_match=False,
    ),
    OutputClaimRule(
        topic="off_plan_payment_mechanics",
        fact_key="off_plan_payment_process_mechanics",
        patterns=(
            re.compile(
                rf"\b(?:seller\s+has\s+paid|paid\s+to\s+date|paid\s+so\s+far)\b[^.?!\n]{{0,160}}{MONEY_PATTERN}[^.?!\n]{{0,160}}\b(?:remaining|developer\s+balance|take\s+over|pay\s+developer)\b",
                re.IGNORECASE,
            ),
            re.compile(
                rf"\b(?:remaining|developer\s+balance|take\s+over|pay\s+developer)\b[^.?!\n]{{0,160}}{MONEY_PATTERN}[^.?!\n]{{0,160}}\b(?:seller\s+has\s+paid|paid\s+to\s+date|paid\s+so\s+far)\b",
                re.IGNORECASE,
            ),
            re.compile(
                rf"\b(?:cash\s+to\s+seller|pay\s+seller)\b[^.?!\n]{{0,160}}{MONEY_PATTERN}[^.?!\n]{{0,160}}\b(?:developer\s+balance|remaining|take\s+over)\b",
                re.IGNORECASE,
            ),
        ),
        deferral=AGENT_CONFIRMATION_LINE,
    ),
    OutputClaimRule(
        topic="seller_original_price",
        fact_key="seller_original_purchase_price",
        patterns=(
            re.compile(
                rf"\b(?:seller\s+(?:originally\s+)?(?:paid|bought|purchased)|original\s+purchase\s+price|seller'?s\s+cost\s+basis)\b[^.?!\n]{{0,160}}(?:{MONEY_PATTERN}|{PERCENT_PATTERN})",
                re.IGNORECASE,
            ),
            re.compile(
                rf"(?:{MONEY_PATTERN}|{PERCENT_PATTERN})[^.?!\n]{{0,120}}\b(?:seller\s+(?:originally\s+)?(?:paid|bought|purchased)|original\s+purchase\s+price|seller'?s\s+cost\s+basis|seller\s+profit|back[-\s]?calculat)",
                re.IGNORECASE,
            ),
        ),
        deferral=AGENT_CONFIRMATION_LINE,
    ),
)
