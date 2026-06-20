#!/usr/bin/env python
"""DAL-170E1 rehearsal-only RLS policies for the first direct-root tables.

This script is intentionally test/local-only. It prints SQL by default and
refuses staging/production applies. Production RLS rollout needs a later,
separately approved migration after this rehearsal shape is proven.
"""

from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import urlparse

from sqlalchemy import create_engine, text


ALLOWED_MUTATION_ENVS = {"test", "local", "development", "ci", "rehearsal"}
LIVE_ENV_MARKERS = ("production", "prod", "staging", "stage", "preview", "live")
SAFE_IDENTITY_MARKERS = ("test", "local", "localhost", "127.0.0.1", "ci", "dev", "development", "rehearsal")

FIRST_TABLE_POLICY_NAMES = (
    ("brokerages", "dal170e1_brokerages_select"),
    ("brokerage_members", "dal170e1_brokerage_members_select"),
    ("brokerage_members", "dal170e1_brokerage_members_write"),
    ("agent_profiles", "dal170e1_agent_profiles_tenant"),
    ("listings", "dal170e1_listings_tenant"),
    ("conversations", "dal170e1_conversations_tenant"),
    ("brokerage_buyer_profiles", "dal170e1_brokerage_buyer_profiles_tenant"),
    ("buyer_profile_fields", "dal170e1_buyer_profile_fields_tenant"),
)

E2_DIRECT_ROOT_TABLES = (
    "listing_documents",
    "listing_facts",
    "listing_knowledge_summaries",
    "listing_logistics",
    "tenant_consents",
    "listing_inquiries",
    "offers",
    "draft_replies",
    "ai_drafts",
    "lead_ingests",
    "lead_assignments",
    "lead_tasks",
    "lead_actions",
    "viewings",
    "tenant_viewing_confirmations",
    "viewing_feedback",
    "media_assets",
)

E2_POLICY_NAMES = tuple(
    (table, f"dal170e2_{table}_tenant")
    for table in E2_DIRECT_ROOT_TABLES
)

POLICY_NAMES = FIRST_TABLE_POLICY_NAMES + E2_POLICY_NAMES

RUNTIME_ROLE = "dal170e1_rls_runtime"

FIRST_TABLES = (
    "brokerages",
    "brokerage_members",
    "agent_profiles",
    "listings",
    "conversations",
    "brokerage_buyer_profiles",
    "buyer_profile_fields",
)

TABLES = FIRST_TABLES + E2_DIRECT_ROOT_TABLES

ROLE_SQL = [
    f"""
    do $$
    begin
        if not exists (select 1 from pg_roles where rolname = '{RUNTIME_ROLE}') then
            create role {RUNTIME_ROLE} nologin;
        end if;
        execute format('grant {RUNTIME_ROLE} to %I', current_user);
    end
    $$
    """,
    f"grant usage on schema public to {RUNTIME_ROLE}",
    f"grant select, insert, update, delete on {', '.join(TABLES)} to {RUNTIME_ROLE}",
]

HELPER_SQL = [
    "create schema if not exists app",
    """
    create or replace function app.current_user_id()
    returns text
    language sql
    stable
    as $$
        select nullif(current_setting('app.user_id', true), '')
    $$
    """,
    """
    create or replace function app.current_brokerage_id()
    returns text
    language sql
    stable
    as $$
        select nullif(current_setting('app.brokerage_id', true), '')
    $$
    """,
    """
    create or replace function app.is_service()
    returns boolean
    language sql
    stable
    as $$
        select coalesce(nullif(current_setting('app.is_service', true), '')::boolean, false)
    $$
    """,
    """
    create or replace function app.is_platform_admin()
    returns boolean
    language sql
    stable
    as $$
        select coalesce(nullif(current_setting('app.is_platform_admin', true), '')::boolean, false)
    $$
    """,
]

FIRST_POLICY_SQL = [
    """
    create policy dal170e1_brokerages_select on brokerages
    for select
    using (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
        or exists (
            select 1
            from brokerage_members bm
            where bm.brokerage_id = brokerages.brokerage_id
              and bm.user_id = app.current_user_id()
              and bm.status = 'active'
        )
    )
    """,
    """
    create policy dal170e1_brokerage_members_select on brokerage_members
    for select
    using (
        app.is_service()
        or app.is_platform_admin()
        or user_id = app.current_user_id()
        or brokerage_id = app.current_brokerage_id()
    )
    """,
    """
    create policy dal170e1_brokerage_members_write on brokerage_members
    for all
    using (app.is_service() or app.is_platform_admin())
    with check (app.is_service() or app.is_platform_admin())
    """,
    """
    create policy dal170e1_agent_profiles_tenant on agent_profiles
    for all
    using (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
    )
    with check (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
    )
    """,
    """
    create policy dal170e1_listings_tenant on listings
    for all
    using (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
    )
    with check (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
    )
    """,
    """
    create policy dal170e1_conversations_tenant on conversations
    for all
    using (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
    )
    with check (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
    )
    """,
    """
    create policy dal170e1_brokerage_buyer_profiles_tenant on brokerage_buyer_profiles
    for all
    using (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
    )
    with check (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
    )
    """,
    """
    create policy dal170e1_buyer_profile_fields_tenant on buyer_profile_fields
    for all
    using (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
    )
    with check (
        app.is_service()
        or app.is_platform_admin()
        or brokerage_id = app.current_brokerage_id()
    )
    """,
]

E2_POLICY_SQL = [
    f"""
    create policy dal170e2_{table}_tenant on {table}
    for all
    using (
        app.is_service()
        or brokerage_id = app.current_brokerage_id()
    )
    with check (
        app.is_service()
        or brokerage_id = app.current_brokerage_id()
    )
    """
    for table in E2_DIRECT_ROOT_TABLES
]

POLICY_SQL = FIRST_POLICY_SQL + E2_POLICY_SQL

ENABLE_SQL = [
    f"alter table {table} enable row level security" for table in TABLES
] + [
    f"alter table {table} force row level security" for table in TABLES
]

APPLY_SQL = ROLE_SQL + HELPER_SQL + [f"grant usage on schema app to {RUNTIME_ROLE}"] + POLICY_SQL + ENABLE_SQL

ROLLBACK_SQL = [
    f"drop policy if exists {policy} on {table}" for table, policy in POLICY_NAMES
] + [
    f"alter table {table} no force row level security" for table in TABLES
] + [
    f"alter table {table} disable row level security" for table in TABLES
] + [
    "drop function if exists app.is_platform_admin()",
    "drop function if exists app.is_service()",
    "drop function if exists app.current_brokerage_id()",
    "drop function if exists app.current_user_id()",
    f"""
    do $$
    begin
        if exists (select 1 from pg_roles where rolname = '{RUNTIME_ROLE}') then
            revoke select, insert, update, delete on {', '.join(TABLES)} from {RUNTIME_ROLE};
            revoke usage on schema app from {RUNTIME_ROLE};
            revoke usage on schema public from {RUNTIME_ROLE};
            execute format('revoke {RUNTIME_ROLE} from %I', current_user);
            drop role {RUNTIME_ROLE};
        end if;
    end
    $$
    """,
]


def _statement_block(statements: list[str]) -> str:
    return ";\n\n".join(statement.strip() for statement in statements if statement.strip()) + ";\n"


def apply_sql_text() -> str:
    return _statement_block(APPLY_SQL)


def rollback_sql_text() -> str:
    return _statement_block(ROLLBACK_SQL)


def _database_url_metadata(database_url: str) -> tuple[str, str, str]:
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    database = (parsed.path or "").lstrip("/").lower()
    username = (parsed.username or "").lower()
    if not host or not database or not username:
        raise SystemExit("Refusing DAL-170E1 rehearsal RLS mutation: DATABASE_URL metadata is incomplete")
    return host, database, username


def _contains_live_marker(value: str) -> bool:
    return any(marker in value for marker in LIVE_ENV_MARKERS)


def _has_safe_identity_marker(*values: str) -> bool:
    return any(any(marker in value for marker in SAFE_IDENTITY_MARKERS) for value in values)


def _database_url_is_production_like(database_url: str) -> bool:
    host, database, username = _database_url_metadata(database_url)
    prod_host = (os.getenv("PROD_DB_HOST") or "").lower()
    if prod_host and (host == prod_host or prod_host in host):
        return True
    return _contains_live_marker(host) or _contains_live_marker(database) or _contains_live_marker(username)


def _assert_rehearsal_mutation_allowed(*, allow_rehearsal_mutation: bool = False) -> None:
    dalya_env = (os.getenv("DALYA_ENV") or "").lower()
    database_url = os.getenv("DATABASE_URL") or ""
    mutation_allowed = allow_rehearsal_mutation or os.getenv("DALYA_ALLOW_RLS_REHEARSAL_MUTATION") == "1"
    if not mutation_allowed:
        raise SystemExit("Refusing DAL-170E1 rehearsal RLS mutation without explicit mutation approval")
    if not dalya_env or dalya_env not in ALLOWED_MUTATION_ENVS:
        raise SystemExit(f"Refusing DAL-170E1 rehearsal RLS mutation for DALYA_ENV={dalya_env or '<missing>'}")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    if _database_url_is_production_like(database_url):
        raise SystemExit("Refusing DAL-170E1 rehearsal RLS mutation against production/staging-like database identity")
    host, database, username = _database_url_metadata(database_url)
    if not _has_safe_identity_marker(dalya_env, host, database, username):
        raise SystemExit("Refusing DAL-170E1 rehearsal RLS mutation: database identity is not clearly test/local/rehearsal")


def _execute(statements: list[str], *, allow_rehearsal_mutation: bool = False) -> None:
    _assert_rehearsal_mutation_allowed(allow_rehearsal_mutation=allow_rehearsal_mutation)
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        for statement in statements:
            if statement.strip():
                conn.execute(text(statement))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply rehearsal RLS to a test/local database only")
    mode.add_argument("--rollback", action="store_true", help="Rollback DAL-170E1 rehearsal RLS from a test/local database")
    parser.add_argument("--print-rollback", action="store_true", help="Print rollback SQL instead of apply SQL")
    parser.add_argument(
        "--allow-rehearsal-mutation",
        action="store_true",
        help="Required for --apply/--rollback, in addition to a test/local/rehearsal DB identity",
    )
    args = parser.parse_args()

    if args.apply:
        _execute(APPLY_SQL, allow_rehearsal_mutation=args.allow_rehearsal_mutation)
        print("DAL-170E1 rehearsal RLS applied")
        return 0
    if args.rollback:
        _execute(ROLLBACK_SQL, allow_rehearsal_mutation=args.allow_rehearsal_mutation)
        print("DAL-170E1 rehearsal RLS rolled back")
        return 0

    print(rollback_sql_text() if args.print_rollback else apply_sql_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
