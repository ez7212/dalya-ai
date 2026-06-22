from __future__ import annotations

import pytest

from app.core.runtime_config import (
    debug_routes_enabled,
    public_url_required_for_webhooks,
)


LIVE_CLASS_ENVS = ["production", "prod", "staging", "stage", "preview", "live"]
LOCAL_CLASS_ENVS = ["local", "test", "testing", "development", "dev", "ci"]


@pytest.mark.parametrize("dalya_env", LIVE_CLASS_ENVS)
def test_debug_routes_blocked_for_live_environments_even_with_flag(monkeypatch, dalya_env):
    # Given: a live-class environment with debug routes explicitly requested.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "true")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    # When / Then: the live-class environment wins over the flag.
    assert debug_routes_enabled() is False


@pytest.mark.parametrize("dalya_env", LIVE_CLASS_ENVS)
def test_public_url_required_for_live_webhooks(monkeypatch, dalya_env):
    # Given: a live-class environment.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    # When / Then: provider webhooks require a stable public URL.
    assert public_url_required_for_webhooks() is True


@pytest.mark.parametrize("dalya_env", LOCAL_CLASS_ENVS)
def test_debug_routes_preserve_local_default_and_flag(monkeypatch, dalya_env):
    # Given: an explicit local/test/dev environment.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ENABLE_DEBUG_ROUTES", raising=False)

    # When / Then: local ergonomics keep debug routes enabled by default.
    assert debug_routes_enabled() is True

    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "false")
    assert debug_routes_enabled() is False

    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "true")
    assert debug_routes_enabled() is True


@pytest.mark.parametrize("dalya_env", LOCAL_CLASS_ENVS)
def test_public_url_not_required_for_local_webhooks(monkeypatch, dalya_env):
    # Given: an explicit local/test/dev environment.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    # When / Then: local webhook simulations do not need PUBLIC_URL.
    assert public_url_required_for_webhooks() is False
