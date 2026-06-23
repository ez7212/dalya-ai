from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
import tempfile
import types


@dataclass(frozen=True, slots=True)
class IsolatedDatabase:
    path: Path
    dotenv_reads_blocked: bool


@dataclass(frozen=True, slots=True)
class UnsafeDatabaseHarnessError(RuntimeError):
    detail: str

    def __str__(self) -> str:
        return self.detail


def install_isolated_app_database(label: str) -> IsolatedDatabase:
    if "app.db.session" in sys.modules:
        raise UnsafeDatabaseHarnessError("app.db.session imported before isolated database install")

    db_path = Path(tempfile.gettempdir()) / f"dalya-seller-summary-{label}-{os.getpid()}.sqlite"
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = "postgresql://isolated:isolated@127.0.0.1:1/blocked"
    os.environ["DALYA_ENV"] = "test"
    os.environ["APP_ENV"] = "test"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DALYA_CORS_ORIGINS"] = "http://127.0.0.1:3000"
    os.environ["DALYA_ALLOW_RUNTIME_CREATE_ALL"] = "0"
    os.environ["ENABLE_DEBOUNCE_WORKER"] = "0"
    os.environ["ENABLE_SUMMARY_WORKER"] = "0"
    os.environ["ENABLE_RESEARCH_AUDITOR"] = "0"
    os.environ["DALYA_ISOLATED_SQLITE_PATH"] = str(db_path)

    def _blocked_load_dotenv(*_args: str, **_kwargs: str) -> bool:
        return False

    dotenv_module = sys.modules.get("dotenv")
    if dotenv_module is None:
        dotenv_module = types.ModuleType("dotenv")
        sys.modules["dotenv"] = dotenv_module
    dotenv_module.load_dotenv = _blocked_load_dotenv

    import sqlalchemy

    real_create_engine = sqlalchemy.create_engine

    def _create_sqlite_engine(_url: str, **_kwargs: str):
        return real_create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )

    sqlalchemy.create_engine = _create_sqlite_engine
    return IsolatedDatabase(path=db_path, dotenv_reads_blocked=True)


def assert_isolated_sqlite_engine() -> str:
    from app.db.session import engine

    backend = engine.url.get_backend_name()
    database = engine.url.database
    expected_path = os.environ.get("DALYA_ISOLATED_SQLITE_PATH")
    if backend != "sqlite" or database != expected_path:
        raise UnsafeDatabaseHarnessError("app database engine is not isolated SQLite")
    return str(database)
