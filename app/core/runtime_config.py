from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Final
from urllib.parse import urlparse


_TRUE_VALUES: Final = {"1", "true", "yes", "on"}
_PRODUCTION_ENVS: Final = {"production", "prod"}
_LIVE_SCHEMA_ENVS: Final = {"production", "prod", "staging", "stage", "preview", "live"}
_RUNTIME_CREATE_ALL_ENVS: Final = {
    "local",
    "localhost",
    "test",
    "testing",
    "development",
    "dev",
    "ci",
}
_LOCAL_CORS_ORIGINS: Final = ("http://localhost:3000", "http://127.0.0.1:3000")
_HTTP_ORIGIN_SCHEMES: Final = {"http", "https"}


@dataclass(frozen=True, slots=True)
class UnsafeCorsConfigError(RuntimeError):
    detail: str

    def __str__(self) -> str:
        return self.detail


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


def cors_allow_origins() -> list[str]:
    raw_origins = os.getenv("DALYA_CORS_ORIGINS")
    if raw_origins is None or raw_origins.strip() == "":
        return _default_cors_origins()

    origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
    if not origins:
        return _default_cors_origins()

    for origin in origins:
        _ensure_explicit_http_origin(origin)
    return list(origins)


def _default_cors_origins() -> list[str]:
    if is_live_environment():
        raise UnsafeCorsConfigError(
            "DALYA_CORS_ORIGINS must be set to explicit HTTP/HTTPS origins "
            "in live-class environments."
        )
    return list(_LOCAL_CORS_ORIGINS)


def _ensure_explicit_http_origin(origin: str) -> None:
    if origin == "*":
        raise UnsafeCorsConfigError(
            "DALYA_CORS_ORIGINS cannot include wildcard origins when credentials are enabled."
        )

    parsed = urlparse(origin)
    if parsed.scheme not in _HTTP_ORIGIN_SCHEMES or parsed.netloc == "":
        raise UnsafeCorsConfigError(
            f"DALYA_CORS_ORIGINS contains an invalid HTTP/HTTPS origin: {origin}"
        )
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeCorsConfigError(
            f"DALYA_CORS_ORIGINS contains credentials in an origin: {origin}"
        )
    try:
        parsed.port
    except ValueError as exc:
        raise UnsafeCorsConfigError(
            f"DALYA_CORS_ORIGINS contains an invalid port in origin: {origin}"
        ) from exc
    if origin != f"{parsed.scheme}://{parsed.netloc}":
        raise UnsafeCorsConfigError(
            "DALYA_CORS_ORIGINS must contain origins only, without paths or "
            f"queries: {origin}"
        )


def debug_routes_enabled() -> bool:
    if is_live_environment():
        return False
    return env_bool("ENABLE_DEBUG_ROUTES", default=True)


def public_url_required_for_webhooks() -> bool:
    return is_live_environment()
