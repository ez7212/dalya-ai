from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

from dotenv import load_dotenv

TEST_CLASS_ENVIRONMENTS = frozenset({"test", "staging", "development"})


class UnsafeTestDatabaseError(RuntimeError):
    """Raised when a test-data write path cannot prove it is off production."""


def load_test_environment_file(repo_root: Path | None = None) -> None:
    """
    Load only the test-specific dotenv file for test-data scripts.

    The app runtime may load `.env`, but harness/persona entry points should not
    source production `.env` as their test configuration. Exported shell values
    remain authoritative so CI can inject DATABASE_URL/DALYA_ENV directly.
    """
    root = repo_root or Path(__file__).resolve().parents[1]
    test_env = root / ".env.test"
    if test_env.exists():
        load_dotenv(test_env, override=True)


def _normalize_host(host: str | None) -> str:
    return (host or "").strip().lower().rstrip(".")


def _configured_prod_hosts(env: Mapping[str, str]) -> set[str]:
    raw = env.get("PROD_DB_HOST", "")
    return {_normalize_host(host) for host in raw.split(",") if _normalize_host(host)}


def assert_safe_test_database(
    *,
    database_url: str | None = None,
    environ: Mapping[str, str] | None = None,
    operation: str = "test database write",
) -> None:
    """
    Fail closed unless both safety checks prove this is a test-class database.

    Checks:
    1. DALYA_ENV must be explicitly allowlisted as test/staging/development.
    2. DATABASE_URL host must not match PROD_DB_HOST.
    """
    env = environ or os.environ
    dalya_env = (env.get("DALYA_ENV") or "").strip().lower()
    if dalya_env not in TEST_CLASS_ENVIRONMENTS:
        expected = ", ".join(sorted(TEST_CLASS_ENVIRONMENTS))
        raise UnsafeTestDatabaseError(
            f"BLOCKED {operation}: DALYA_ENV must be explicitly set to one of "
            f"{{{expected}}}. Current DALYA_ENV={dalya_env or '<unset>'!r}. "
            "Production/test-data writes are not allowed without a test-class environment."
        )

    target_url = database_url or env.get("DATABASE_URL") or ""
    if not target_url:
        raise UnsafeTestDatabaseError(
            f"BLOCKED {operation}: DATABASE_URL is not set. Refusing to guess a database target."
        )

    target_host = _normalize_host(urlparse(target_url).hostname)
    if not target_host:
        raise UnsafeTestDatabaseError(
            f"BLOCKED {operation}: DATABASE_URL host could not be parsed. Refusing to write."
        )

    prod_hosts = _configured_prod_hosts(env)
    if not prod_hosts:
        raise UnsafeTestDatabaseError(
            f"BLOCKED {operation}: PROD_DB_HOST is not set. Set it to the non-secret "
            "production DB hostname so test-data scripts can denylist production."
        )

    if target_host in prod_hosts:
        raise UnsafeTestDatabaseError(
            f"BLOCKED {operation}: DATABASE_URL host {target_host!r} matches PROD_DB_HOST. "
            "Refusing to write test or seed data to production."
        )
