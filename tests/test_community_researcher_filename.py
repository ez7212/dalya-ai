"""Regression: _normalize_filename must not crash when developer is empty.

A listing added with no developer (e.g. "Bulgari Resort & Residences") used to
fail community research with "list index out of range" because the code did
`developer.split()[0]` on an empty string.
"""
from app.core.community_researcher import _normalize_filename


def test_empty_developer_falls_back_to_project_only():
    assert _normalize_filename("", "Bulgari Resort & Residences 6") == "bulgari_resort_residences_6.json"


def test_whitespace_developer_does_not_crash():
    assert _normalize_filename("   ", "Palace Ostra") == "palace_ostra.json"


def test_normal_developer_unchanged():
    assert _normalize_filename("Emaar Properties", "The Oasis") == "emaar_oasis.json"
