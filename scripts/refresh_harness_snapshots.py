from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.safety import load_test_environment_file


def main() -> None:
    # Snapshot refresh writes only frozen files and the scrape report, not DB rows.
    # Keep it off production `.env` anyway so future DB-writing additions must be explicit.
    load_test_environment_file()
    from tests.harness import DEFAULT_CONFIG_PATH, DEFAULT_REPORT_PATH, DEFAULT_SNAPSHOT_DIR, refresh_snapshots

    snapshots = refresh_snapshots(
        config_path=DEFAULT_CONFIG_PATH,
        snapshot_dir=DEFAULT_SNAPSHOT_DIR,
        report_path=DEFAULT_REPORT_PATH,
    )
    print(f"refreshed {len(snapshots)} harness snapshots")
    print(f"snapshots: {Path(DEFAULT_SNAPSHOT_DIR)}")
    print(f"report: {Path(DEFAULT_REPORT_PATH)}")


if __name__ == "__main__":
    main()
