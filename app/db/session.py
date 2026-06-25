"""
Database session management.
Uses SQLAlchemy 2.0 with psycopg2 for PostgreSQL.
"""

import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from urllib.parse import urlparse, urlunparse, quote, parse_qs, urlencode
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

logger = logging.getLogger(__name__)

_raw_url = os.getenv("DATABASE_URL", "")

if not _raw_url:
    raise RuntimeError("DATABASE_URL environment variable not set")

# Parse and rebuild the URL to URL-encode the password
# (handles special characters like '!' safely)
_parsed = urlparse(_raw_url)
_password = quote(_parsed.password or "", safe="")
_port = f":{_parsed.port}" if _parsed.port else ""
_netloc = f"{_parsed.username}:{_password}@{_parsed.hostname}{_port}"

# Preserve existing query params (sslmode, channel_binding, etc.)
_query_params = parse_qs(_parsed.query)
_query_string = urlencode({k: v[0] for k, v in _query_params.items()})

DATABASE_URL = urlunparse((
    _parsed.scheme,
    _netloc,
    _parsed.path,
    _parsed.params,
    _query_string,
    _parsed.fragment,
))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,       # Recycle connections every 5 min — prevents Neon sleep timeout
    pool_timeout=10,        # Don't wait more than 10s for a connection from the pool
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

RLS_CONTEXT_INFO_KEY = "dalya_rls_context"
_DEFAULT_RLS_CONTEXT: ContextVar[dict[str, object] | None] = ContextVar(
    "dalya_default_rls_context",
    default=None,
)
_UNSET = object()
_RLS_CONTEXT_KEYS = (
    "app.user_id",
    "app.brokerage_id",
    "app.is_service",
    "app.is_platform_admin",
)


class Base(DeclarativeBase):
    pass


class TransientDatabaseError(RuntimeError):
    """Raised when a DB write failed for a retryable connection reason."""


_TRANSIENT_DB_MARKERS = (
    "connection already closed",
    "connection not open",
    "could not connect to server",
    "could not receive data from server",
    "could not send data to server",
    "server closed the connection unexpectedly",
    "terminating connection",
    "timeout expired",
    "operation timed out",
    "ssl syscall error",
    "ssl connection has been closed unexpectedly",
    "lost connection",
    "connection refused",
)


def is_transient_db_error(exc: BaseException) -> bool:
    """Return True for DB connectivity failures that are safe to retry."""
    if isinstance(exc, (OperationalError, InterfaceError)):
        return True
    if isinstance(exc, DBAPIError):
        if getattr(exc, "connection_invalidated", False):
            return True
        original = str(getattr(exc, "orig", exc)).lower()
        return any(marker in original for marker in _TRANSIENT_DB_MARKERS)
    return False


def reset_db_connections() -> None:
    """Drop pooled connections so the next attempt opens fresh DB sockets."""
    try:
        engine.dispose()
    except Exception as exc:
        logger.warning("Failed to dispose DB engine after transient error: %s", exc)


def safe_commit(db) -> None:
    """
    Commit a unit of work and convert transient connection failures into a
    retryable application-level exception.
    """
    try:
        db.commit()
    except DBAPIError as exc:
        try:
            db.rollback()
        except Exception as rollback_exc:
            logger.warning("DB rollback failed after commit error: %s", rollback_exc)
        if is_transient_db_error(exc):
            reset_db_connections()
            raise TransientDatabaseError(str(exc)) from exc
        raise


def _normalise_context_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _apply_rls_context_to_connection(connection, context: dict[str, object]) -> None:
    """Apply request-scoped DB context to the current transaction only.

    All RLS keys are set in a SINGLE round-trip — on a high-latency database the
    prior per-key statements (one network round-trip each) dominated request
    time. SET LOCAL semantics (transaction-scoped) are unchanged.
    """
    selects = ", ".join(
        f"set_config(:name_{i}, :val_{i}, true)" for i in range(len(_RLS_CONTEXT_KEYS))
    )
    params: dict[str, object] = {}
    for i, key in enumerate(_RLS_CONTEXT_KEYS):
        params[f"name_{i}"] = key
        params[f"val_{i}"] = _normalise_context_value(context.get(key))
    connection.execute(text(f"SELECT {selects}"), params)


@event.listens_for(SASession, "after_begin")
def _apply_rls_context_after_begin(session, transaction, connection) -> None:
    """Reapply SET LOCAL context whenever SQLAlchemy opens a transaction."""
    context = session.info.get(RLS_CONTEXT_INFO_KEY)
    if not context:
        default_context = _DEFAULT_RLS_CONTEXT.get()
        if default_context:
            context = dict(default_context)
            session.info[RLS_CONTEXT_INFO_KEY] = context
    if context:
        _apply_rls_context_to_connection(connection, context)


def set_db_session_context(
    db,
    *,
    user_id: object = _UNSET,
    brokerage_id: object = _UNSET,
    is_service: object = _UNSET,
    is_platform_admin: object = _UNSET,
) -> None:
    """
    Store request/service DB context on the SQLAlchemy Session.

    The after_begin hook applies this context with SET LOCAL for every new
    transaction. If a transaction is already open, apply immediately so callers
    can safely resolve a user first and then add brokerage context.
    """
    context = dict(db.info.get(RLS_CONTEXT_INFO_KEY, {}))
    updates = {
        "app.user_id": user_id,
        "app.brokerage_id": brokerage_id,
        "app.is_service": is_service,
        "app.is_platform_admin": is_platform_admin,
    }
    for key, value in updates.items():
        if value is not _UNSET:
            context[key] = value

    db.info[RLS_CONTEXT_INFO_KEY] = context
    if db.in_transaction():
        _apply_rls_context_to_connection(db.connection(), context)


def set_service_db_session_context(
    db,
    *,
    brokerage_id: object = None,
    is_platform_admin: bool = False,
) -> None:
    """Mark a server-side DB session as explicit service/admin context."""
    set_db_session_context(
        db,
        brokerage_id=brokerage_id,
        is_service=True,
        is_platform_admin=is_platform_admin,
    )


def _service_context_dict(
    *,
    brokerage_id: object = None,
    is_platform_admin: bool = False,
) -> dict[str, object]:
    return {
        "app.brokerage_id": brokerage_id,
        "app.is_service": True,
        "app.is_platform_admin": is_platform_admin,
    }


@contextmanager
def service_db_context_scope(
    *,
    brokerage_id: object = None,
    is_platform_admin: bool = False,
):
    """Apply service context to nested SessionLocal instances in this scope."""
    token = _DEFAULT_RLS_CONTEXT.set(
        _service_context_dict(
            brokerage_id=brokerage_id,
            is_platform_admin=is_platform_admin,
        )
    )
    try:
        yield
    finally:
        _DEFAULT_RLS_CONTEXT.reset(token)


@contextmanager
def service_session(
    *,
    brokerage_id: object = None,
    is_platform_admin: bool = False,
):
    """Open a SessionLocal with explicit service/admin RLS context."""
    db = SessionLocal()
    try:
        set_service_db_session_context(
            db,
            brokerage_id=brokerage_id,
            is_platform_admin=is_platform_admin,
        )
        yield db
    finally:
        db.close()


def clear_db_session_context(db) -> None:
    """Clear stored DB context for tests or explicit session reuse."""
    db.info.pop(RLS_CONTEXT_INFO_KEY, None)
    if db.in_transaction():
        _apply_rls_context_to_connection(db.connection(), {})


def get_db_session_context(db) -> dict[str, object]:
    """Return a copy of the stored DB context for assertions/diagnostics."""
    return dict(db.info.get(RLS_CONTEXT_INFO_KEY, {}))


def get_db():
    """Dependency for FastAPI routes that need a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
