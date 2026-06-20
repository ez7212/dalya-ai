from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from scripts.db_role_rehearsal_dal170e4b import (
    _assert_role_rehearsal_mutation_allowed,
    _execute,
    _quote_ident,
    apply_sql,
    apply_sql_text,
    drop_sql,
    drop_sql_text,
    main as role_rehearsal_main,
)


def _set_role_rehearsal_env(
    monkeypatch,
    *,
    dalya_env: str | None = "test",
    database_url: str | None = "postgresql://dalya_test_user:secret@test-db.local/dalya_test",
    owner_database_url: str | None = "postgresql://dalya_owner:secret@test-db.local/dalya_test",
) -> None:
    monkeypatch.setenv("DALYA_ALLOW_DB_ROLE_REHEARSAL_MUTATION", "1")
    monkeypatch.setenv("PROD_DB_HOST", "prod-db.example.com")
    if dalya_env is None:
        monkeypatch.delenv("DALYA_ENV", raising=False)
    else:
        monkeypatch.setenv("DALYA_ENV", dalya_env)
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)
    if owner_database_url is None:
        monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_OWNER_URL", raising=False)
    else:
        monkeypatch.setenv("MIGRATION_DATABASE_URL", owner_database_url)
        monkeypatch.delenv("DATABASE_OWNER_URL", raising=False)


@pytest.mark.parametrize("dalya_env", ["production", "prod", "staging", "stage", "preview", "live", "qa", None])
def test_role_rehearsal_mutation_refuses_live_missing_or_unknown_env(monkeypatch, dalya_env):
    _set_role_rehearsal_env(monkeypatch, dalya_env=dalya_env)

    with pytest.raises(SystemExit):
        _assert_role_rehearsal_mutation_allowed(allow_rehearsal_mutation=True)


def test_role_rehearsal_mutation_requires_explicit_approval(monkeypatch):
    _set_role_rehearsal_env(monkeypatch)
    monkeypatch.delenv("DALYA_ALLOW_DB_ROLE_REHEARSAL_MUTATION", raising=False)

    with pytest.raises(SystemExit):
        _assert_role_rehearsal_mutation_allowed()


@pytest.mark.parametrize(
    ("database_url", "owner_database_url"),
    [
        (
            "postgresql://dalya_test_user:secret@prod-db.example.com/dalya_test",
            "postgresql://dalya_owner:secret@test-db.local/dalya_test",
        ),
        (
            "postgresql://dalya_test_user:secret@test-db.local/dalya_test",
            "postgresql://dalya_owner:secret@prod-db.example.com/dalya_test",
        ),
        (
            "postgresql://dalya_test_user:secret@rehearsal-prod.example.com/dalya_test",
            "postgresql://dalya_owner:secret@test-db.local/dalya_test",
        ),
        (
            "postgresql://dalya_test_user:secret@test-db.local/dalya_staging",
            "postgresql://dalya_owner:secret@test-db.local/dalya_test",
        ),
        (
            "postgresql://prod_user:secret@test-db.local/dalya_test",
            "postgresql://dalya_owner:secret@test-db.local/dalya_test",
        ),
    ],
)
def test_role_rehearsal_mutation_refuses_production_like_database_identity(
    monkeypatch,
    database_url,
    owner_database_url,
):
    _set_role_rehearsal_env(
        monkeypatch,
        database_url=database_url,
        owner_database_url=owner_database_url,
    )

    with pytest.raises(SystemExit):
        _assert_role_rehearsal_mutation_allowed(allow_rehearsal_mutation=True)


@pytest.mark.parametrize(
    ("database_url", "owner_database_url"),
    [
        (None, "postgresql://dalya_owner:secret@test-db.local/dalya_test"),
        ("postgresql://dalya_test_user:secret@test-db.local/dalya_test", None),
        ("not-a-url", "postgresql://dalya_owner:secret@test-db.local/dalya_test"),
        ("postgresql:///dalya_test", "postgresql://dalya_owner:secret@test-db.local/dalya_test"),
    ],
)
def test_role_rehearsal_mutation_refuses_missing_or_ambiguous_database_identity(
    monkeypatch,
    database_url,
    owner_database_url,
):
    _set_role_rehearsal_env(
        monkeypatch,
        database_url=database_url,
        owner_database_url=owner_database_url,
    )

    with pytest.raises(SystemExit):
        _assert_role_rehearsal_mutation_allowed(allow_rehearsal_mutation=True)


def test_role_rehearsal_dry_run_sql_is_available_without_mutation_env(monkeypatch):
    monkeypatch.delenv("DALYA_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_OWNER_URL", raising=False)
    monkeypatch.delenv("DALYA_ALLOW_DB_ROLE_REHEARSAL_MUTATION", raising=False)

    sql = apply_sql_text()
    assert "create role \"dal170e4b_app_runtime\"" in sql
    assert "nobypassrls" in sql
    assert "grant select, insert, update, delete on table" in sql
    assert "grant usage, select on all sequences in schema public" in sql
    assert "drop role \"dal170e4b_app_runtime\"" in drop_sql_text()


@pytest.mark.parametrize("mode", ["--apply", "--drop"])
def test_role_rehearsal_apply_and_drop_cli_are_gated(monkeypatch, mode):
    _set_role_rehearsal_env(monkeypatch)
    monkeypatch.delenv("DALYA_ALLOW_DB_ROLE_REHEARSAL_MUTATION", raising=False)
    monkeypatch.setattr("sys.argv", ["db_role_rehearsal_dal170e4b.py", mode])

    with pytest.raises(SystemExit):
        role_rehearsal_main()


def test_role_rehearsal_role_name_rejects_injection():
    with pytest.raises(SystemExit):
        apply_sql("dal170e4b_app_runtime;drop table brokerages")


def test_role_rehearsal_app_role_grants_and_non_owner_behavior(monkeypatch):
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for DB-backed role rehearsal behavior")

    role_name = f"dal170e4b_{uuid.uuid4().hex[:12]}"
    role_ident = _quote_ident(role_name)
    probe_table = f"dal170e4b_probe_{uuid.uuid4().hex[:12]}"
    _set_role_rehearsal_env(
        monkeypatch,
        dalya_env=os.getenv("DALYA_ENV") or "test",
        database_url=database_url,
        owner_database_url=os.getenv("MIGRATION_DATABASE_URL") or os.getenv("DATABASE_OWNER_URL") or database_url,
    )
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        _execute(apply_sql(role_name), role_name=role_name, allow_rehearsal_mutation=True)

        with engine.begin() as conn:
            role_row = conn.execute(
                text(
                    """
                    select rolsuper, rolcreatedb, rolcreaterole, rolbypassrls
                    from pg_roles
                    where rolname = :role_name
                    """
                ),
                {"role_name": role_name},
            ).mappings().one()
            assert role_row["rolsuper"] is False
            assert role_row["rolcreatedb"] is False
            assert role_row["rolcreaterole"] is False
            assert role_row["rolbypassrls"] is False
            assert conn.execute(
                text("select has_schema_privilege(:role_name, 'public', 'usage')"),
                {"role_name": role_name},
            ).scalar_one()
            assert not conn.execute(
                text("select has_schema_privilege(:role_name, 'public', 'create')"),
                {"role_name": role_name},
            ).scalar_one()
            assert conn.execute(
                text("select has_table_privilege(:role_name, 'public.brokerages', 'select,insert,update,delete')"),
                {"role_name": role_name},
            ).scalar_one()
            assert conn.execute(
                text("select tableowner <> :role_name from pg_tables where schemaname = 'public' and tablename = 'brokerages'"),
                {"role_name": role_name},
            ).scalar_one()

        with engine.connect() as conn:
            trans = conn.begin()
            conn.execute(text(f"set local role {role_ident}"))
            with pytest.raises(DBAPIError):
                conn.execute(text(f"create table public.{_quote_ident(probe_table)} (id integer)"))
            trans.rollback()

        brokerage_id = f"{probe_table}_brokerage"
        with engine.connect() as conn:
            trans = conn.begin()
            conn.execute(text(f"set local role {role_ident}"))
            conn.execute(
                text(
                    """
                    insert into brokerages (brokerage_id, name, slug, status)
                    values (:brokerage_id, 'DAL-170E4B Role Test', :slug, 'active')
                    """
                ),
                {"brokerage_id": brokerage_id, "slug": brokerage_id},
            )
            assert conn.execute(
                text("select name from brokerages where brokerage_id = :brokerage_id"),
                {"brokerage_id": brokerage_id},
            ).scalar_one() == "DAL-170E4B Role Test"
            conn.execute(
                text("update brokerages set name = 'DAL-170E4B Role Test Updated' where brokerage_id = :brokerage_id"),
                {"brokerage_id": brokerage_id},
            )
            assert conn.execute(
                text("select name from brokerages where brokerage_id = :brokerage_id"),
                {"brokerage_id": brokerage_id},
            ).scalar_one() == "DAL-170E4B Role Test Updated"
            conn.execute(
                text("delete from brokerages where brokerage_id = :brokerage_id"),
                {"brokerage_id": brokerage_id},
            )
            assert conn.execute(
                text("select count(*) from brokerages where brokerage_id = :brokerage_id"),
                {"brokerage_id": brokerage_id},
            ).scalar_one() == 0
            trans.rollback()
    finally:
        _execute(drop_sql(role_name), role_name=role_name, allow_rehearsal_mutation=True)
