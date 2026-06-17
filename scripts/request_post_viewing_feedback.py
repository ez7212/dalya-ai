"""Request post-viewing feedback for due completed viewings.

Usage:
  PYTHONPATH=. venv/bin/python scripts/request_post_viewing_feedback.py [brokerage_id]
"""

import sys

from app.core.post_viewing_capture import request_due_post_viewing_feedback
from app.db.session import SessionLocal


def main() -> None:
    brokerage_id = sys.argv[1] if len(sys.argv) > 1 else None
    with SessionLocal() as db:
        rows = request_due_post_viewing_feedback(db, brokerage_id=brokerage_id)
        print(f"requested_post_viewing_feedback={len(rows)}")
        for viewing in rows:
            print(f"- {viewing.viewing_id} conversation={viewing.conversation_id} buyer={viewing.buyer_phone}")


if __name__ == "__main__":
    main()
