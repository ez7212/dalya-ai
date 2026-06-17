import pytest
from sqlalchemy.exc import OperationalError

from app.db import session as db_session


pytestmark = pytest.mark.no_db


class FakeDB:
    def __init__(self, error=None):
        self.error = error
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1
        if self.error:
            raise self.error

    def rollback(self):
        self.rollbacks += 1


def test_safe_commit_success_does_not_rollback():
    db = FakeDB()

    db_session.safe_commit(db)

    assert db.commits == 1
    assert db.rollbacks == 0


def test_safe_commit_wraps_transient_operational_error(monkeypatch):
    disposed = {"called": False}

    def fake_reset():
        disposed["called"] = True

    monkeypatch.setattr(db_session, "reset_db_connections", fake_reset)
    db = FakeDB(
        OperationalError(
            "COMMIT",
            {},
            Exception("server closed the connection unexpectedly"),
        )
    )

    with pytest.raises(db_session.TransientDatabaseError):
        db_session.safe_commit(db)

    assert db.rollbacks == 1
    assert disposed["called"] is True
