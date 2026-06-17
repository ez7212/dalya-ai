"""
Database session management.
Uses SQLAlchemy 2.0 with psycopg2 for PostgreSQL.
"""

import logging
import os
from urllib.parse import urlparse, urlunparse, quote, parse_qs, urlencode
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
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


def get_db():
    """Dependency for FastAPI routes that need a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
