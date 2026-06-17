import pytest

from tests.safety import UnsafeTestDatabaseError, assert_safe_test_database

pytestmark = pytest.mark.no_db


PROD_HOST = "ep-prod-pooler.example.neon.tech"
TEST_HOST = "ep-test-branch-pooler.example.neon.tech"


def _env(**overrides):
    env = {
        "DALYA_ENV": "test",
        "DATABASE_URL": f"postgresql://user:pass@{TEST_HOST}/neondb?sslmode=require",
        "PROD_DB_HOST": PROD_HOST,
    }
    env.update(overrides)
    return env


def test_guard_blocks_unset_dalya_env():
    env = _env()
    env.pop("DALYA_ENV")

    with pytest.raises(UnsafeTestDatabaseError, match="DALYA_ENV"):
        assert_safe_test_database(environ=env, operation="test write")


def test_guard_blocks_production_dalya_env():
    with pytest.raises(UnsafeTestDatabaseError, match="production"):
        assert_safe_test_database(environ=_env(DALYA_ENV="production"), operation="test write")


def test_guard_blocks_test_env_when_database_url_points_at_prod_host():
    with pytest.raises(UnsafeTestDatabaseError, match="matches PROD_DB_HOST"):
        assert_safe_test_database(
            environ=_env(DATABASE_URL=f"postgresql://user:pass@{PROD_HOST}/neondb"),
            operation="test write",
        )


def test_guard_allows_test_env_on_non_production_host():
    assert_safe_test_database(environ=_env(), operation="test write")


def test_guard_fails_closed_without_prod_db_host():
    env = _env()
    env.pop("PROD_DB_HOST")

    with pytest.raises(UnsafeTestDatabaseError, match="PROD_DB_HOST"):
        assert_safe_test_database(environ=env, operation="test write")
