from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.verified_facts_output_rules import (
    CLAIM_RULES,
    NUMERIC_CLAIM_RE,
    OutputClaimRule,
)
from app.core.verified_facts import (
    FactStatus,
    RuntimePolicy,
    VerifiedFact,
    VerifiedFactGrounding,
    VerifiedFactRegistry,
    default_verified_fact_registry,
    direct_fact_for_key,
    verified_facts_grounding_for_message,
)


@dataclass(frozen=True)
class VerifiedFactsOutputGateResult:
    response: str
    rewrite_count: int
    topics: tuple[str, ...]


def apply_verified_facts_output_gate(
    response: str,
    *,
    latest_buyer_message: str | None = None,
    brokerage_id: str | None = None,
    registry: VerifiedFactRegistry | None = None,
) -> VerifiedFactsOutputGateResult:
    if not response:
        return VerifiedFactsOutputGateResult(response=response, rewrite_count=0, topics=())

    fact_registry = registry or default_verified_fact_registry()
    parts = re.split(r"(?<=[.!?])(\s+)", response.strip())
    rewritten: list[str] = []
    rewrite_count = 0
    topics: list[str] = []

    for index in range(0, len(parts), 2):
        sentence = parts[index]
        separator = parts[index + 1] if index + 1 < len(parts) else ""
        rule = _first_unsupported_rule(
            sentence,
            latest_buyer_message=latest_buyer_message,
            brokerage_id=brokerage_id,
            registry=fact_registry,
        )
        if rule is None:
            rewritten.append(sentence + separator)
            continue
        rewritten.append(rule.deferral + separator)
        rewrite_count += 1
        if rule.topic not in topics:
            topics.append(rule.topic)

    return VerifiedFactsOutputGateResult(
        response="".join(rewritten).strip(),
        rewrite_count=rewrite_count,
        topics=tuple(topics),
    )


def _first_unsupported_rule(
    sentence: str,
    *,
    latest_buyer_message: str | None,
    brokerage_id: str | None,
    registry: VerifiedFactRegistry,
) -> OutputClaimRule | None:
    if not sentence.strip():
        return None
    for rule in CLAIM_RULES:
        if not _matches_rule(sentence, rule):
            continue
        grounding = verified_facts_grounding_for_message(
            _grounding_message(latest_buyer_message, sentence),
            registry=registry,
            brokerage_id=brokerage_id,
        )
        if _is_do_not_state_claim(rule, registry=registry, brokerage_id=brokerage_id):
            return rule
        if _is_supported_by_direct_fact(
            sentence,
            rule,
            grounding=grounding,
            brokerage_id=brokerage_id,
            registry=registry,
        ):
            continue
        return rule
    return None


def _matches_rule(sentence: str, rule: OutputClaimRule) -> bool:
    return any(pattern.search(sentence) for pattern in rule.patterns)


def _is_supported_by_direct_fact(
    sentence: str,
    rule: OutputClaimRule,
    *,
    grounding: VerifiedFactGrounding | None,
    brokerage_id: str | None,
    registry: VerifiedFactRegistry,
) -> bool:
    if rule.fact_key is None:
        return False
    fact = _grounded_direct_fact(rule, grounding)
    if fact is None:
        fact = direct_fact_for_key(registry, rule.fact_key, brokerage_id=brokerage_id)
    if fact is None:
        return False
    if not rule.require_numeric_fact_match:
        return True
    claim_tokens = _numeric_claim_tokens(sentence)
    fact_tokens = _numeric_claim_tokens(fact.text)
    return bool(claim_tokens) and claim_tokens.issubset(fact_tokens)


def _grounding_message(latest_buyer_message: str | None, sentence: str) -> str:
    return "\n".join(part for part in (latest_buyer_message, sentence) if part)


def _grounded_direct_fact(
    rule: OutputClaimRule,
    grounding: VerifiedFactGrounding | None,
) -> VerifiedFact | None:
    if rule.fact_key is None or grounding is None:
        return None
    for fact in grounding.direct_facts:
        if fact.key == rule.fact_key:
            return fact
    return None


def _is_do_not_state_claim(
    rule: OutputClaimRule,
    *,
    registry: VerifiedFactRegistry,
    brokerage_id: str | None,
) -> bool:
    if rule.fact_key is None:
        return False
    return any(
        fact.active
        and fact.key == rule.fact_key
        and (
            fact.status is FactStatus.DO_NOT_STATE
            or fact.runtime_policy is RuntimePolicy.DO_NOT_STATE
        )
        for fact in _candidate_facts(rule.fact_key, registry=registry, brokerage_id=brokerage_id)
    )


def _candidate_facts(
    key: str,
    *,
    registry: VerifiedFactRegistry,
    brokerage_id: str | None,
) -> tuple[VerifiedFact, ...]:
    facts: list[VerifiedFact] = []
    if brokerage_id:
        facts.extend(
            fact
            for fact in registry.tenant_facts(brokerage_id, active_only=False)
            if fact.key == key
        )
    facts.extend(
        fact
        for fact in registry.global_facts(active_only=False)
        if fact.key == key
    )
    return tuple(facts)


def _numeric_claim_tokens(text: str) -> set[str]:
    return {
        re.sub(r"\s+", "", match.group(0).lower()).replace("dhs", "aed").replace("dh", "aed")
        for match in NUMERIC_CLAIM_RE.finditer(text)
    }
