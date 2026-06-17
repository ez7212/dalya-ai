import pytest

from app.core.prompt_builder import build_system_prompt
from app.core.unit_profile import (
    append_unit_profile_history,
    structure_unit_profile_deterministic,
)
from tests.conftest import TEST_SPA

pytestmark = pytest.mark.no_db


def test_unit_profile_structures_inspection_dictation_categories():
    transcript = (
        "Master bedroom has west-facing windows so it gets afternoon sun, "
        "AC is the older Daikin system, two assigned parking spots in basement level B2, "
        "the elevator on the south side breaks down often, kitchen was upgraded in 2024 with quartz counters."
    )

    profile = structure_unit_profile_deterministic(transcript)

    assert any("Master bedroom" in item for item in profile.layout)
    assert any("west-facing" in item for item in profile.view)
    assert any("Daikin" in item for item in profile.ac_utilities)
    assert any("parking" in item for item in profile.parking)
    assert any("elevator" in item for item in profile.building_community_quirks)
    assert any("quartz" in item for item in profile.condition)
    assert profile.provenance == "agent-authored"


def test_unit_profile_history_is_append_only():
    profile = structure_unit_profile_deterministic("Two assigned parking spots in basement B2.")
    history = append_unit_profile_history(
        [],
        transcript="Two assigned parking spots in basement B2.",
        structured_profile=profile,
        source="transcript_text",
        agent_user_id="agent-1",
    )
    history = append_unit_profile_history(
        history,
        transcript="Kitchen was upgraded in 2024.",
        structured_profile=structure_unit_profile_deterministic("Kitchen was upgraded in 2024."),
        source="transcript_text",
        agent_user_id="agent-1",
    )

    assert len(history) == 2
    assert history[0]["transcript"] == "Two assigned parking spots in basement B2."
    assert history[1]["transcript"] == "Kitchen was upgraded in 2024."


def test_property_advisor_prompt_prefers_unit_profile_for_practical_questions():
    profile = structure_unit_profile_deterministic(
        "Master bedroom has west-facing windows so it gets afternoon sun. "
        "Two assigned parking spots in basement level B2."
    )

    prompt = build_system_prompt(
        TEST_SPA,
        seller_asking_price=17_000_000,
        property_type="ready",
        unit_profile=profile.model_dump(),
    )

    assert "AGENT-AUTHORED UNIT PROFILE" in prompt
    assert "high-trust source" in prompt
    assert "west-facing windows" in prompt
    assert "basement level B2" in prompt
    assert "Prefer it over generic community data" in prompt
