from __future__ import annotations

import pytest

from app.core.runtime_config import runtime_create_all_allowed


@pytest.mark.parametrize("dalya_env", ["production", "prod", "staging", "stage", "preview", "live"])
def test_runtime_create_all_blocked_for_live_environments_even_with_flag(monkeypatch, dalya_env):
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.setenv("DALYA_ALLOW_RUNTIME_CREATE_ALL", "1")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    assert runtime_create_all_allowed() is False


@pytest.mark.parametrize("dalya_env", ["local", "test", "testing", "development", "dev", "ci"])
def test_runtime_create_all_requires_explicit_flag_for_safe_environments(monkeypatch, dalya_env):
    monkeypatch.setenv("DALYA_ENV", dalya_env)
    monkeypatch.delenv("DALYA_ALLOW_RUNTIME_CREATE_ALL", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    assert runtime_create_all_allowed() is False

    monkeypatch.setenv("DALYA_ALLOW_RUNTIME_CREATE_ALL", "1")

    assert runtime_create_all_allowed() is True


def test_runtime_create_all_blocks_unknown_environment_even_with_flag(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "qa")
    monkeypatch.setenv("DALYA_ALLOW_RUNTIME_CREATE_ALL", "1")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    assert runtime_create_all_allowed() is False


def test_startup_schema_helper_skips_when_gate_is_closed(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "runtime_create_all_allowed", lambda: False)

    assert main._create_runtime_schema_if_allowed() is False


def test_startup_schema_helper_calls_create_all_only_when_gate_is_open(monkeypatch):
    import app.main as main
    from app.db import session as db_session

    calls = []

    def fake_create_all(*, bind):
        calls.append(bind)

    monkeypatch.setattr(main, "runtime_create_all_allowed", lambda: True)
    monkeypatch.setattr(db_session.Base.metadata, "create_all", fake_create_all)

    assert main._create_runtime_schema_if_allowed() is True
    assert calls == [db_session.engine]
