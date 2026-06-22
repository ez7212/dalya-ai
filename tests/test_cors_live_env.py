from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware


API_MODULES = (
    "agent",
    "agent_dashboard",
    "crm",
    "leads",
    "listings",
    "media",
    "onboarding",
    "research",
    "seller",
    "spa_parser",
    "viewings",
    "whatsapp",
)


def _install_api_route_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    for module_name in API_MODULES:
        module = ModuleType(f"app.api.{module_name}")
        module.router = APIRouter()
        monkeypatch.setitem(sys.modules, f"app.api.{module_name}", module)


def _import_main(monkeypatch: pytest.MonkeyPatch):
    _install_api_route_stubs(monkeypatch)
    sys.modules.pop("app.main", None)
    return importlib.import_module("app.main")


def _cors_kwargs(app_module) -> dict:
    for middleware in app_module.app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return middleware.kwargs
    raise AssertionError("CORSMiddleware was not registered")


def test_local_test_environment_uses_localhost_cors_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: local/test runtime without an explicit CORS env var.
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DALYA_CORS_ORIGINS", raising=False)

    # When: the app is constructed.
    app_module = _import_main(monkeypatch)

    # Then: credentials are allowed only for explicit localhost origins.
    cors = _cors_kwargs(app_module)
    assert cors["allow_credentials"] is True
    assert cors["allow_origins"] == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_configured_pilot_origins_are_reflected_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a live-class runtime with an explicit pilot allowlist.
    monkeypatch.setenv("DALYA_ENV", "staging")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv(
        "DALYA_CORS_ORIGINS",
        "https://pilot.dalya.ai, https://agents.dalya.ai",
    )

    # When: the app is constructed.
    app_module = _import_main(monkeypatch)

    # Then: FastAPI receives the exact configured origins after comma trimming.
    assert _cors_kwargs(app_module)["allow_origins"] == [
        "https://pilot.dalya.ai",
        "https://agents.dalya.ai",
    ]


@pytest.mark.parametrize("dalya_env", ["production", "staging", "preview", "live"])
def test_live_class_environment_refuses_to_start_without_cors_origins(
    monkeypatch: pytest.MonkeyPatch,
    dalya_env: str,
) -> None:
    # Given: a live-class runtime without an explicit CORS allowlist.
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DALYA_CORS_ORIGINS", raising=False)

    # When / Then: app construction fails closed before wildcard CORS can be installed.
    with pytest.raises(RuntimeError, match="DALYA_CORS_ORIGINS"):
        _import_main(monkeypatch)


@pytest.mark.parametrize("cors_origins", ["*", "https://pilot.dalya.ai,*"])
def test_live_class_environment_rejects_wildcard_cors_with_credentials(
    monkeypatch: pytest.MonkeyPatch,
    cors_origins: str,
) -> None:
    # Given: a live-class runtime configured with a wildcard origin.
    monkeypatch.setenv("DALYA_ENV", "preview")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("DALYA_CORS_ORIGINS", cors_origins)

    # When / Then: wildcard plus credentials is impossible.
    with pytest.raises(RuntimeError, match="wildcard"):
        _import_main(monkeypatch)
