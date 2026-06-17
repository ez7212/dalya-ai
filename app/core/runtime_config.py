from __future__ import annotations

import os


_TRUE_VALUES = {"1", "true", "yes", "on"}
_PRODUCTION_ENVS = {"production", "prod"}


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


def debug_routes_enabled() -> bool:
    if is_production():
        return False
    return env_bool("ENABLE_DEBUG_ROUTES", default=True)


def public_url_required_for_webhooks() -> bool:
    return is_production()
