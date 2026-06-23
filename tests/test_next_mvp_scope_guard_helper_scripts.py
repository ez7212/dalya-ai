from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = Path("/private/tmp/dalya-scope-guard-fixtures")
CHANGED_PATHS_FIXTURE = FIXTURE_DIR / "changed-paths.txt"
DIFF_FIXTURE = FIXTURE_DIR / "diff.patch"
OUTPUT_PATH = FIXTURE_DIR / "out.json"
BASE_COMMIT = "3482a7fb863c542836fa2aabef707ad8fd503b71"
ALLOWLIST_PATH = ".omo/evidence/task-1-helper-script-allowlist.json"


def test_scope_guard_rejects_unapproved_audit_and_migrate_helper_edits() -> None:
    # Given: fixture inputs with unapproved helper-script edits.
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    CHANGED_PATHS_FIXTURE.write_text(
        "\n".join(("scripts/migrate_fake.py", "scripts/audit_fake.py", "")),
        encoding="utf-8",
    )
    DIFF_FIXTURE.write_text(
        "\n".join(
            (
                "diff --git a/scripts/migrate_fake.py b/scripts/migrate_fake.py",
                "new file mode 100644",
                "--- /dev/null",
                "+++ b/scripts/migrate_fake.py",
                "@@ -0,0 +1 @@",
                "+print('migrate behavior changed')",
                "diff --git a/scripts/audit_fake.py b/scripts/audit_fake.py",
                "new file mode 100644",
                "--- /dev/null",
                "+++ b/scripts/audit_fake.py",
                "@@ -0,0 +1 @@",
                "+print('audit behavior changed')",
                "",
            )
        ),
        encoding="utf-8",
    )

    # When: the scope guard runs against the fixture inputs and Task 1 allowlist.
    result = subprocess.run(
        [
            "python3",
            "scripts/verify_next_mvp_scope_guard.py",
            "--base",
            BASE_COMMIT,
            "--output",
            str(OUTPUT_PATH),
            "--changed-paths-fixture",
            str(CHANGED_PATHS_FIXTURE),
            "--diff-fixture",
            str(DIFF_FIXTURE),
            "--helper-script-allowlist",
            ALLOWLIST_PATH,
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Then: the guard fails and records both unapproved helper-script names.
    assert result.returncode != 0, result.stdout
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    helper_results = [
        item
        for item in payload["results"]
        if item["label"] == "approved audit/migrate helper-script edits only"
    ]
    assert len(helper_results) == 1
    assert helper_results[0]["passed"] is False
    assert helper_results[0]["evidence"] == [
        "scripts/audit_fake.py",
        "scripts/migrate_fake.py",
    ]
