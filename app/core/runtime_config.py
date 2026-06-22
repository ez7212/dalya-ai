from __future__ import annotations

import os


_TRUE_VALUES = {"1", "true", "yes", "on"}
_PRODUCTION_ENVS = {"production", "prod"}
_LIVE_SCHEMA_ENVS = {"production", "prod", "staging", "stage", "preview", "live"}
_RUNTIME_CREATE_ALL_ENVS = {"local", "localhost", "test", "testing", "development", "dev", "ci"}


def env_name() -> str:
    return (
        os.getenv("DALYA_ENV")
        or os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or "production"
    ).strip().lower()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


def is_production() -> bool:
    return env_name() in _PRODUCTION_ENVS


def is_live_environment() -> bool:
    return env_name() in _LIVE_SCHEMA_ENVS


def runtime_create_all_allowed() -> bool:
    """
    Return True only for explicit local/test/dev schema bootstrap.

    Production-class environments must use migration-owner credentials and
    must never attempt schema DDL from the app runtime role.
    """
    environment = env_name()
    if environment in _LIVE_SCHEMA_ENVS:
        return False
    if environment not in _RUNTIME_CREATE_ALL_ENVS:
        return False
    return env_bool("DALYA_ALLOW_RUNTIME_CREATE_ALL", default=False)


def debug_routes_enabled() -> bool:
    if is_live_environment():
        return False
    return env_bool("ENABLE_DEBUG_ROUTES", default=True)


def public_url_required_for_webhooks() -> bool:
    return is_live_environment()
