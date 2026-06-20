#!/usr/bin/env python
"""DAL-170E4B test/local rehearsal for a least-privilege app DB role.

This script is intentionally dry-run by default. Apply/drop modes are for
test/local/rehearsal databases only and require explicit mutation approval.
Production role creation must use a later, separately approved runbook.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from urllib.parse import urlparse

from sqlalchemy import create_engine, text


ALLOWED_MUTATION_ENVS = {"test", "local", "development", "dev", "ci", "rehearsal"}
LIVE_ENV_MARKERS = ("production", "prod", "staging", "stage", "preview", "live")
DEFAULT_ROLE_NAME = "dal170e4b_app_runtime"
ROLE_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def _quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _validate_role_name(role_name: str) -> str:
    if not ROLE_NAME_RE.fullmatch(role_name):
        raise SystemExit("Refusing DAL-170E4B role rehearsal: invalid role name")
    return role_name


def _table_names() -> tuple[str, ...]:
    from app.db.session import Base
    import app.models.db_models  # noqa: F401 - registers mapped tables

    return tuple(sorted(table.name for table in Base.metadata.sorted_tables))


def _statement_block(statements: list[str]) -> str:
    return ";\n\n".join(statement.strip() for statement in statements if statement.strip()) + ";\n"


def apply_sql(role_name: str = DEFAULT_ROLE_NAME) -> list[str]:
    role_name = _validate_role_name(role_name)
    role_ident = _quote_ident(role_name)
    tables = ", ".join(f"public.{_quote_ident(table)}" for table in _table_names())
    return [
        f"""
        do $$
        begin
            if not exists (select 1 from pg_roles where rolname = '{role_name}') then
                create role {role_ident}
                    nologin
                    nosuperuser
                    nocreatedb
                    nocreaterole
                    noinherit
                    nobypassrls;
            else
                alter role {role_ident}
                    nologin
                    nosuperuser
                    nocreatedb
                    nocreaterole
                    noinherit
                    nobypassrls;
            end if;
            execute format('grant %I to %I', '{role_name}', current_user);
        end
        $$
        """,
        f"grant usage on schema public to {role_ident}",
        f"""
        do $$
        begin
            if exists (select 1 from information_schema.schemata where schema_name = 'app') then
                execute 'grant usage on schema app to {role_ident}';
            end if;
        end
        $$
        """,
        f"grant select, insert, update, delete on table {tables} to {role_ident}",
        f"grant usage, select on all sequences in schema public to {role_ident}",
    ]


def drop_sql(role_name: str = DEFAULT_ROLE_NAME) -> list[str]:
    role_name = _validate_role_name(role_name)
    role_ident = _quote_ident(role_name)
    return [
        f"revoke usage, select on all sequences in schema public from {role_ident}",
        f"revoke select, insert, update, delete on all tables in schema public from {role_ident}",
        f"""
        do $$
        begin
            if exists (select 1 from information_schema.schemata where schema_name = 'app') then
                execute 'revoke usage on schema app from {role_ident}';
            end if;
        exception
            when undefined_object then null;
        end
        $$
        """,
        f"revoke usage on schema public from {role_ident}",
        f"""
        do $$
        begin
            if exists (select 1 from pg_roles where rolname = '{role_name}') then
                execute format('revoke %I from %I', '{role_name}', current_user);
                drop role {role_ident};
            end if;
        end
        $$
        """,
    ]


def apply_sql_text(role_name: str = DEFAULT_ROLE_NAME) -> str:
    return _statement_block(apply_sql(role_name))


def drop_sql_text(role_name: str = DEFAULT_ROLE_NAME) -> str:
    return _statement_block(drop_sql(role_name))


def _database_url_metadata(url: str, *, label: str) -> tuple[str, str, str]:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    database = (parsed.path or "").lstrip("/").lower()
    username = (parsed.username or "").lower()
    if not host or not database or not username:
        raise SystemExit(f"Refusing DAL-170E4B role rehearsal: {label} metadata is incomplete")
    return host, database, username


def _contains_live_marker(value: str) -> bool:
    return any(marker in value for marker in LIVE_ENV_MARKERS)


def _url_is_production_like(url: str, *, label: str) -> bool:
    host, database, username = _database_url_metadata(url, label=label)
    prod_hosts = [
        value.strip().lower()
        for value in (os.getenv("PROD_DB_HOST") or "").split(",")
        if value.strip()
    ]
    if any(host == prod_host or prod_host in host for prod_host in prod_hosts):
        return True
    return _contains_live_marker(host) or _contains_live_marker(database) or _contains_live_marker(username)


def _owner_database_url() -> str:
    return os.getenv("MIGRATION_DATABASE_URL") or os.getenv("DATABASE_OWNER_URL") or ""


def _assert_role_rehearsal_mutation_allowed(
    *,
    allow_rehearsal_mutation: bool = False,
    database_url: str | None = None,
    owner_database_url: str | None = None,
) -> tuple[str, str]:
    dalya_env = (os.getenv("DALYA_ENV") or "").strip().lower()
    mutation_allowed = (
        allow_rehearsal_mutation
        or os.getenv("DALYA_ALLOW_DB_ROLE_REHEARSAL_MUTATION") == "1"
    )
    database_url = database_url if database_url is not None else os.getenv("DATABASE_URL", "")
    owner_database_url = owner_database_url if owner_database_url is not None else _owner_database_url()

    if not mutation_allowed:
        raise SystemExit("Refusing DAL-170E4B role rehearsal mutation without explicit approval")
    if not dalya_env or dalya_env not in ALLOWED_MUTATION_ENVS:
        raise SystemExit(f"Refusing DAL-170E4B role rehearsal mutation for DALYA_ENV={dalya_env or '<missing>'}")
    if not database_url:
        raise SystemExit("DATABASE_URL is required for DAL-170E4B role rehearsal mutation")
    if not owner_database_url:
        raise SystemExit("MIGRATION_DATABASE_URL or DATABASE_OWNER_URL is required for DAL-170E4B role rehearsal mutation")
    if _url_is_production_like(database_url, label="DATABASE_URL"):
        raise SystemExit("Refusing DAL-170E4B role rehearsal against production/staging-like DATABASE_URL")
    if _url_is_production_like(owner_database_url, label="owner database URL"):
        raise SystemExit("Refusing DAL-170E4B role rehearsal against production/staging-like owner database URL")

    return database_url, owner_database_url


def _execute(statements: list[str], *, role_name: str, allow_rehearsal_mutation: bool = False) -> None:
    _validate_role_name(role_name)
    _, owner_database_url = _assert_role_rehearsal_mutation_allowed(
        allow_rehearsal_mutation=allow_rehearsal_mutation
    )
    engine = create_engine(owner_database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        for statement in statements:
            if statement.strip():
                conn.execute(text(statement))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply rehearsal app-role grants to a test/local database only")
    mode.add_argument("--drop", action="store_true", help="Drop the rehearsal app runtime role from a test/local database")
    parser.add_argument("--print-drop", action="store_true", help="Print drop SQL instead of apply SQL")
    parser.add_argument("--role-name", default=DEFAULT_ROLE_NAME, help=f"Rehearsal role name, default: {DEFAULT_ROLE_NAME}")
    parser.add_argument(
        "--allow-rehearsal-mutation",
        action="store_true",
        help="Required for --apply/--drop, in addition to a test/local/rehearsal DB identity",
    )
    args = parser.parse_args()
    role_name = _validate_role_name(args.role_name)

    if args.apply:
        _execute(apply_sql(role_name), role_name=role_name, allow_rehearsal_mutation=args.allow_rehearsal_mutation)
        print(f"DAL-170E4B app-role rehearsal grants applied for role {role_name}")
        return 0
    if args.drop:
        _execute(drop_sql(role_name), role_name=role_name, allow_rehearsal_mutation=args.allow_rehearsal_mutation)
        print(f"DAL-170E4B app-role rehearsal role dropped: {role_name}")
        return 0

    print(drop_sql_text(role_name) if args.print_drop else apply_sql_text(role_name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
