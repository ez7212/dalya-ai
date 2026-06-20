"""DAL-173A — Verified Facts loader and registry.

A pure, side-effect-free data layer that reads source-tagged Dubai real-estate
facts from a config-backed JSON fixture, validates them, derives each fact's
runtime consumption policy, and exposes query helpers.

This module deliberately does NOT wire anything into chatbot answer generation,
prompts, the dashboard, or the database. It is the standalone registry described
in docs/product/verified-facts-deal-readiness-spec.md (Part 1) and
docs/product/verified-facts-runtime-handoff.md.

Content source of truth: docs/domain/dubai-real-estate-verified-facts.md.
Update path: edit the JSON fixture (or pass a different source) and reload — no
schema, no migration.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

DEFAULT_SOURCE = Path(__file__).resolve().parent / "data" / "verified_facts_seed.json"

DEFAULT_DOMAIN = "dubai_real_estate"


class VerifiedFactError(ValueError):
    """Raised when a fact fails validation (missing/invalid required fields)."""


class FactStatus(str, Enum):
    """Markdown status labels from the verified-facts source legend."""

    CONFIRMED = "confirmed"
    DRAFT_FOR_AGENT_ONLY = "draft-for-agent only"
    ERIC_DECISION_REQUIRED = "Eric decision required"
    REPO_ASSERTED_UNVERIFIED = "repo-asserted (unverified)"
    LISTING_SPECIFIC_ONLY = "listing-specific only"
    DO_NOT_STATE = "do not state"


class RuntimePolicy(str, Enum):
    """Derived consumption policy a future chatbot/runtime would honour."""

    DIRECT = "direct"
    DRAFT_FOR_AGENT_ONLY = "draft_for_agent_only"
    LISTING_SPECIFIC_ONLY = "listing_specific_only"
    DO_NOT_STATE = "do_not_state"


class FactScope(str, Enum):
    """Global (Dalya-wide) facts vs brokerage-specific (tenant) facts."""

    GLOBAL = "global"
    TENANT = "tenant"


# Required keys every raw fact dict must provide.
_REQUIRED_FIELDS = ("key", "category", "text", "source_label", "status")


def _runtime_policy_for(status: FactStatus, *, transaction_specific: bool) -> RuntimePolicy:
    """Map a status label to a runtime policy.

    Hard rule (per spec): `direct` is granted ONLY to a `confirmed` fact that is
    not transaction/listing-specific. Source-confirmed != direct-safe.
    """
    if status is FactStatus.DO_NOT_STATE:
        return RuntimePolicy.DO_NOT_STATE
    if status is FactStatus.LISTING_SPECIFIC_ONLY:
        return RuntimePolicy.LISTING_SPECIFIC_ONLY
    if status is FactStatus.CONFIRMED and not transaction_specific:
        return RuntimePolicy.DIRECT
    # confirmed-but-transaction-specific, draft-for-agent only, Eric decision
    # required, repo-asserted (unverified) all fall back to draft-for-agent.
    return RuntimePolicy.DRAFT_FOR_AGENT_ONLY


@dataclass(frozen=True)
class VerifiedFact:
    key: str
    category: str
    domain: str
    scope: FactScope
    text: str
    source_label: str
    status: FactStatus
    runtime_policy: RuntimePolicy
    transaction_specific: bool = False
    source_ref: Optional[str] = None
    source_url: Optional[str] = None
    effective_date: Optional[str] = None
    version: Optional[str] = None
    brokerage_id: Optional[str] = None
    active: bool = True

    @property
    def is_directly_answerable(self) -> bool:
        return self.active and self.runtime_policy is RuntimePolicy.DIRECT

    @classmethod
    def from_raw(cls, raw: dict) -> "VerifiedFact":
        if not isinstance(raw, dict):
            raise VerifiedFactError(f"Verified fact must be an object, got {type(raw).__name__}")

        for field in _REQUIRED_FIELDS:
            value = raw.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise VerifiedFactError(f"Verified fact missing required field '{field}': {raw.get('key', '<unknown>')}")

        raw_status = raw["status"]
        try:
            status = FactStatus(raw_status)
        except ValueError as exc:
            raise VerifiedFactError(
                f"Verified fact '{raw['key']}' has unrecognized status '{raw_status}'"
            ) from exc

        scope_value = raw.get("scope", FactScope.GLOBAL.value)
        try:
            scope = FactScope(scope_value)
        except ValueError as exc:
            raise VerifiedFactError(
                f"Verified fact '{raw['key']}' has invalid scope '{scope_value}'"
            ) from exc

        brokerage_id = raw.get("brokerage_id")
        if scope is FactScope.TENANT and not brokerage_id:
            raise VerifiedFactError(f"Tenant-scoped fact '{raw['key']}' must carry a brokerage_id")
        if scope is FactScope.GLOBAL and brokerage_id:
            raise VerifiedFactError(f"Global fact '{raw['key']}' must not carry a brokerage_id")

        transaction_specific = bool(raw.get("transaction_specific", False))

        return cls(
            key=raw["key"],
            category=raw["category"],
            domain=raw.get("domain", DEFAULT_DOMAIN),
            scope=scope,
            text=raw["text"],
            source_label=raw["source_label"],
            status=status,
            runtime_policy=_runtime_policy_for(status, transaction_specific=transaction_specific),
            transaction_specific=transaction_specific,
            source_ref=raw.get("source_ref"),
            source_url=raw.get("source_url"),
            effective_date=raw.get("effective_date"),
            version=raw.get("version"),
            brokerage_id=brokerage_id,
            active=bool(raw.get("active", True)),
        )


def load_verified_facts(source: Optional[Path | str] = None) -> list[VerifiedFact]:
    """Parse and validate verified facts from a JSON fixture.

    Raises VerifiedFactError on the first invalid fact or duplicate key.
    """
    path = Path(source) if source is not None else DEFAULT_SOURCE
    if not path.exists():
        raise VerifiedFactError(f"Verified facts source not found: {path}")

    payload = json.loads(path.read_text())
    raw_facts = payload.get("facts") if isinstance(payload, dict) else payload
    if not isinstance(raw_facts, list):
        raise VerifiedFactError("Verified facts source must contain a 'facts' list")

    facts: list[VerifiedFact] = []
    seen: set[str] = set()
    for raw in raw_facts:
        fact = VerifiedFact.from_raw(raw)
        if fact.key in seen:
            raise VerifiedFactError(f"Duplicate verified fact key '{fact.key}'")
        seen.add(fact.key)
        facts.append(fact)
    return facts


class VerifiedFactRegistry:
    """In-memory, read-only registry over a set of VerifiedFact records."""

    def __init__(self, facts: Iterable[VerifiedFact]):
        self._facts: list[VerifiedFact] = list(facts)
        self._by_key: dict[str, VerifiedFact] = {fact.key: fact for fact in self._facts}

    @classmethod
    def from_source(cls, source: Optional[Path | str] = None) -> "VerifiedFactRegistry":
        return cls(load_verified_facts(source))

    def all(self) -> list[VerifiedFact]:
        return list(self._facts)

    def get(self, key: str) -> Optional[VerifiedFact]:
        return self._by_key.get(key)

    def active(self) -> list[VerifiedFact]:
        """Facts safe to surface on a buyer-facing query path.

        Excludes inactive facts and `do_not_state` facts (which exist so the
        system knows never to state them, but must never be retrieved to answer).
        """
        return [
            fact
            for fact in self._facts
            if fact.active and fact.runtime_policy is not RuntimePolicy.DO_NOT_STATE
        ]

    def by_category(self, category: str, *, active_only: bool = True) -> list[VerifiedFact]:
        pool = self.active() if active_only else self._facts
        return [fact for fact in pool if fact.category == category]

    def by_domain(self, domain: str, *, active_only: bool = True) -> list[VerifiedFact]:
        pool = self.active() if active_only else self._facts
        return [fact for fact in pool if fact.domain == domain]

    def by_scope(self, scope: FactScope, *, active_only: bool = True) -> list[VerifiedFact]:
        pool = self.active() if active_only else self._facts
        return [fact for fact in pool if fact.scope is scope]

    def global_facts(self, *, active_only: bool = True) -> list[VerifiedFact]:
        return self.by_scope(FactScope.GLOBAL, active_only=active_only)

    def tenant_facts(self, brokerage_id: str, *, active_only: bool = True) -> list[VerifiedFact]:
        return [
            fact
            for fact in self.by_scope(FactScope.TENANT, active_only=active_only)
            if fact.brokerage_id == brokerage_id
        ]

    def oldest_by_category(self) -> dict[str, Optional[str]]:
        """Freshness view: the oldest effective_date per category (None last)."""
        result: dict[str, Optional[str]] = {}
        for fact in self._facts:
            if not fact.active:
                continue
            current = result.get(fact.category, "unset")
            if current == "unset":
                result[fact.category] = fact.effective_date
            elif fact.effective_date is not None and (current is None or fact.effective_date < current):
                result[fact.category] = fact.effective_date
        return result
