"""DAL-173A — Verified Facts loader/registry tests.

Pure unit tests (no DB, no network). Validate structure, source-tagging,
status->runtime_policy mapping, validation rejections, active-retrieval
exclusion, category/domain filtering, and global/tenant separation.
"""
from __future__ import annotations

import json

import pytest

from app.core.verified_facts import (
    DEFAULT_SOURCE,
    FactScope,
    FactStatus,
    RuntimePolicy,
    VerifiedFact,
    VerifiedFactError,
    VerifiedFactRegistry,
    load_verified_facts,
)


def _raw(**overrides):
    base = {
        "key": "k1",
        "category": "fees",
        "domain": "dubai_real_estate",
        "scope": "global",
        "text": "Some fact.",
        "source_label": "DLD",
        "source_ref": "S1",
        "status": "confirmed",
        "transaction_specific": False,
        "active": True,
    }
    base.update(overrides)
    return base


def _write(tmp_path, facts):
    path = tmp_path / "facts.json"
    path.write_text(json.dumps({"facts": facts}))
    return path


# ── Seed fixture loads and is well-formed ──────────────────────────────────────

def test_seed_fixture_loads_and_is_valid():
    facts = load_verified_facts()
    assert facts, "seed fixture should contain facts"
    assert DEFAULT_SOURCE.exists()
    # every fact is source-tagged and carries a derived runtime policy
    for fact in facts:
        assert fact.source_label
        assert isinstance(fact.runtime_policy, RuntimePolicy)
        assert isinstance(fact.status, FactStatus)


def test_valid_facts_load_from_fixture(tmp_path):
    path = _write(tmp_path, [_raw(), _raw(key="k2", category="process")])
    facts = load_verified_facts(path)
    assert {f.key for f in facts} == {"k1", "k2"}


# ── status -> runtime_policy mapping ───────────────────────────────────────────

def test_confirmed_general_is_direct():
    fact = VerifiedFact.from_raw(_raw(status="confirmed", transaction_specific=False))
    assert fact.runtime_policy is RuntimePolicy.DIRECT
    assert fact.is_directly_answerable is True


def test_confirmed_transaction_specific_is_draft_only():
    fact = VerifiedFact.from_raw(_raw(status="confirmed", transaction_specific=True))
    assert fact.runtime_policy is RuntimePolicy.DRAFT_FOR_AGENT_ONLY
    assert fact.is_directly_answerable is False


def test_listing_specific_and_do_not_state_and_pending_map_correctly():
    assert VerifiedFact.from_raw(_raw(status="listing-specific only")).runtime_policy is RuntimePolicy.LISTING_SPECIFIC_ONLY
    assert VerifiedFact.from_raw(_raw(status="do not state")).runtime_policy is RuntimePolicy.DO_NOT_STATE
    assert VerifiedFact.from_raw(_raw(status="Eric decision required")).runtime_policy is RuntimePolicy.DRAFT_FOR_AGENT_ONLY
    assert VerifiedFact.from_raw(_raw(status="repo-asserted (unverified)")).runtime_policy is RuntimePolicy.DRAFT_FOR_AGENT_ONLY


# ── validation rejections ──────────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["key", "category", "text", "source_label", "status"])
def test_missing_required_field_rejected(field):
    raw = _raw()
    raw[field] = None
    with pytest.raises(VerifiedFactError):
        VerifiedFact.from_raw(raw)


def test_missing_source_label_rejected():
    with pytest.raises(VerifiedFactError):
        VerifiedFact.from_raw(_raw(source_label=""))


def test_unrecognized_status_rejected_not_guessed():
    with pytest.raises(VerifiedFactError):
        VerifiedFact.from_raw(_raw(status="probably_fine"))


def test_duplicate_keys_rejected(tmp_path):
    path = _write(tmp_path, [_raw(), _raw()])
    with pytest.raises(VerifiedFactError):
        load_verified_facts(path)


def test_missing_source_file_rejected(tmp_path):
    with pytest.raises(VerifiedFactError):
        load_verified_facts(tmp_path / "nope.json")


# ── active retrieval excludes inactive + do_not_state ──────────────────────────

def test_inactive_excluded_from_active_retrieval(tmp_path):
    path = _write(tmp_path, [_raw(key="live"), _raw(key="dead", active=False)])
    reg = VerifiedFactRegistry.from_source(path)
    active_keys = {f.key for f in reg.active()}
    assert "live" in active_keys
    assert "dead" not in active_keys
    # but still retrievable by key
    assert reg.get("dead") is not None


def test_do_not_state_excluded_from_active_retrieval(tmp_path):
    path = _write(tmp_path, [_raw(key="ok"), _raw(key="secret", status="do not state", category="privacy")])
    reg = VerifiedFactRegistry.from_source(path)
    active_keys = {f.key for f in reg.active()}
    assert "ok" in active_keys
    assert "secret" not in active_keys
    assert reg.get("secret").runtime_policy is RuntimePolicy.DO_NOT_STATE


# ── category / domain filtering ────────────────────────────────────────────────

def test_category_and_domain_filtering(tmp_path):
    path = _write(tmp_path, [
        _raw(key="fee1", category="fees", domain="dubai_real_estate"),
        _raw(key="proc1", category="process", domain="dubai_real_estate"),
        _raw(key="other", category="fees", domain="other_domain"),
    ])
    reg = VerifiedFactRegistry.from_source(path)
    assert {f.key for f in reg.by_category("fees")} == {"fee1", "other"}
    assert {f.key for f in reg.by_category("process")} == {"proc1"}
    assert {f.key for f in reg.by_domain("dubai_real_estate")} == {"fee1", "proc1"}
    assert {f.key for f in reg.by_domain("other_domain")} == {"other"}


# ── global / tenant separation ─────────────────────────────────────────────────

def test_tenant_global_distinction_preserved(tmp_path):
    path = _write(tmp_path, [
        _raw(key="g1", scope="global", brokerage_id=None),
        _raw(key="t1", scope="tenant", brokerage_id="brokerage-A"),
        _raw(key="t2", scope="tenant", brokerage_id="brokerage-B"),
    ])
    reg = VerifiedFactRegistry.from_source(path)
    assert {f.key for f in reg.global_facts()} == {"g1"}
    assert {f.key for f in reg.tenant_facts("brokerage-A")} == {"t1"}
    assert {f.key for f in reg.tenant_facts("brokerage-B")} == {"t2"}
    assert reg.get("t1").scope is FactScope.TENANT


def test_tenant_scope_requires_brokerage_id():
    with pytest.raises(VerifiedFactError):
        VerifiedFact.from_raw(_raw(scope="tenant", brokerage_id=None))


def test_global_scope_rejects_brokerage_id():
    with pytest.raises(VerifiedFactError):
        VerifiedFact.from_raw(_raw(scope="global", brokerage_id="brokerage-A"))
