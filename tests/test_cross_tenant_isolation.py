from types import SimpleNamespace

import pytest

from scripts import chatbot_full_test as suite

pytestmark = pytest.mark.no_db


def _seed():
    brokerages = {
        "a": {"name": "Harness Brokerage A"},
        "b": {"name": "Irwin Real Estate"},
        "c": {"name": "Third Brokerage"},
    }
    agents = {
        "agent-a": SimpleNamespace(
            user_id="agent-a",
            brokerage_id="a",
            full_name="Aisha Khan",
            display_name="Aisha",
            phone="+971590000001",
        ),
        "agent-b": SimpleNamespace(
            user_id="agent-b",
            brokerage_id="b",
            full_name="Benjamin Hart",
            display_name="Ben",
            phone="+971590000002",
        ),
        "agent-c": SimpleNamespace(
            user_id="agent-c",
            brokerage_id="c",
            full_name="Carla Mendes",
            display_name="Carla",
            phone="+971590000003",
        ),
    }
    listings = [
        SimpleNamespace(
            listing_id="LISTING_A",
            brokerage_id="a",
            assigned_agent_id="agent-a",
            community_key="shared_project",
            spa_data={
                "project": "Shared Creek Tower",
                "building": "Shared Creek Tower",
                "community": "Dubai Marina",
                "developer": "Emaar",
                "unit_number": "A-101",
            },
        ),
        SimpleNamespace(
            listing_id="LISTING_B",
            brokerage_id="b",
            assigned_agent_id="agent-b",
            community_key="shared_project",
            spa_data={
                "project": "Shared Creek Tower",
                "building": "Shared Creek Tower",
                "community": "Dubai Marina",
                "developer": "Emaar",
                "unit_number": "B-202",
            },
        ),
        SimpleNamespace(
            listing_id="LISTING_C",
            brokerage_id="c",
            assigned_agent_id="agent-c",
            community_key="unique_cove",
            spa_data={
                "project": "Unique Cove Residences",
                "building": "Unique Cove Residences",
                "community": "Unique Cove",
                "developer": "Boutique Developer",
                "unit_number": "C-303",
            },
        ),
    ]
    return SimpleNamespace(agents=list(agents.values()), listings=listings), brokerages, agents


def _install_index():
    seed, brokerages, agents = _seed()
    suite._IDENTIFIER_INDEX.clear()
    suite._IDENTIFIER_INDEX.update(
        suite.build_cross_tenant_identifier_index(seed, brokerages, agents)
    )


def test_private_other_brokerage_terms_are_forbidden():
    _install_index()
    forbidden = set(suite.forbidden_cross_tenant_terms_for_brokerage("a"))

    assert "irwin real estate" in forbidden
    assert "benjamin hart" in forbidden
    assert "+971590000002" in forbidden
    assert "listing b" in forbidden
    assert "b-202" in forbidden


def test_public_and_shared_terms_are_not_forbidden():
    _install_index()
    forbidden = set(suite.forbidden_cross_tenant_terms_for_brokerage("a"))

    assert "emaar" not in forbidden
    assert "dubai marina" not in forbidden
    assert "shared creek tower" not in forbidden


def test_unique_other_property_terms_are_forbidden():
    _install_index()
    forbidden = set(suite.forbidden_cross_tenant_terms_for_brokerage("a"))

    assert "unique cove residences" in forbidden
    assert "unique cove" in forbidden


def test_no_other_brokerage_leak_flags_real_leaks_but_not_public_terms():
    _install_index()
    suite._LISTING_CONTEXTS.clear()
    suite._LISTING_CONTEXTS["LISTING_A"] = {
        "brokerage_id": "a",
        "brokerage_agent_phones": ["+971590000001"],
    }
    persona = {"listing_id": "LISTING_A"}
    check = suite.no_other_brokerage_leak(persona)

    ok, evidence = check([], "Emaar and Dubai Marina are public context.")
    assert ok, evidence

    ok, evidence = check([], "Call Benjamin Hart at +971590000002 about LISTING_B.")
    assert not ok
    assert "benjamin hart" in evidence


def test_no_other_brokerage_leak_flags_bad_agent_routes():
    _install_index()
    suite._LISTING_CONTEXTS.clear()
    suite._LISTING_CONTEXTS["LISTING_A"] = {
        "brokerage_id": "a",
        "brokerage_agent_phones": ["+971590000001"],
    }
    persona = {"listing_id": "LISTING_A"}

    ok, evidence = suite.no_other_brokerage_leak(persona)(
        [{"agents_ai_messages": [{"to_agent_phone": "+971590000002"}]}],
        "",
    )

    assert not ok
    assert "+971590000002" in evidence
