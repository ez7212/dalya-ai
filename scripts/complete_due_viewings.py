"""
Mark due confirmed viewings as completed and create post-viewing follow-up triggers.

Usage:
  PYTHONPATH=. venv/bin/python scripts/complete_due_viewings.py [brokerage_id]
"""

import sys

from app.core.viewing_lifecycle import complete_due_viewings
from app.db.session import SessionLocal


def main() -> None:
    brokerage_id = sys.argv[1] if len(sys.argv) > 1 else None
    with SessionLocal() as db:
        rows = complete_due_viewings(db, brokerage_id=brokerage_id)
        print(f"completed_due_viewings={len(rows)}")


if __name__ == "__main__":
    main()
