from __future__ import annotations

import pytest

from app.core.runtime_config import (
    UnsafeCorsConfigError,
    cors_allow_origins,
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


def test_cors_origins_default_to_localhost_for_test_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: an explicit test environment without CORS env configuration.
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DALYA_CORS_ORIGINS", raising=False)

    # When / Then: local app construction gets an explicit localhost allowlist.
    assert cors_allow_origins() == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_cors_origins_reflect_configured_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a configured live-class pilot allowlist.
    monkeypatch.setenv("DALYA_ENV", "preview")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv(
        "DALYA_CORS_ORIGINS",
        "https://pilot.dalya.ai, https://agents.dalya.ai",
    )

    # When / Then: comma-separated origins are returned in configured order.
    assert cors_allow_origins() == [
        "https://pilot.dalya.ai",
        "https://agents.dalya.ai",
    ]


def test_cors_origins_fail_closed_without_live_class_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a production runtime without an explicit CORS allowlist.
    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DALYA_CORS_ORIGINS", raising=False)

    # When / Then: unsafe app construction is blocked.
    with pytest.raises(UnsafeCorsConfigError, match="DALYA_CORS_ORIGINS"):
        cors_allow_origins()


def test_cors_origins_reject_wildcard_with_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a live-class runtime configured with a wildcard origin.
    monkeypatch.setenv("DALYA_ENV", "staging")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("DALYA_CORS_ORIGINS", "*")

    # When / Then: wildcard origins cannot be combined with credentials.
    with pytest.raises(UnsafeCorsConfigError, match="wildcard"):
        cors_allow_origins()
