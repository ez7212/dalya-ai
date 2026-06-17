"""
Run the scheduled daily hot-list refresh for all active brokerages.

Deploy this behind cron/platform scheduler at 08:00 in the target brokerage
timezone. The service records one `hotlist_refresh_runs` row per brokerage.
"""

from app.core.hot_list import run_scheduled_hotlist_refresh
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal() as db:
        runs = run_scheduled_hotlist_refresh(db)
        for run in runs:
            print(
                "hotlist_refresh "
                f"brokerage={run.brokerage_id} "
                f"run={run.run_id} "
                f"status={run.status} "
                f"assignments={run.assignment_count} "
                f"tasks={run.task_count} "
                f"drafts={run.draft_count}"
            )


if __name__ == "__main__":
    main()
