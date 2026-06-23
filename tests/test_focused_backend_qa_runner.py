from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "run_focused_backend_qa.py"


def load_runner() -> ModuleType:
    scripts_path = str(ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location("focused_backend_qa_runner_under_test", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = load_runner()


class FocusedBackendQaRunnerPolicyTest(unittest.TestCase):
    def test_db_backed_test_selectors_are_blocked_when_path_form_varies(self) -> None:
        # Given: DB-backed pytest selections expressed in valid pytest path forms.
        variants = (
            "tests/test_seller_lead_privacy.py",
            "./tests/test_seller_lead_privacy.py",
            str(ROOT / "tests" / "test_seller_lead_privacy.py"),
            "tests",
            "tests.test_seller_lead_privacy",
        )

        for variant in variants:
            with self.subTest(variant=variant):
                # When: the focused runner classifies the requested suite.
                reason = RUNNER._suite_policy_error((variant, "-q"))

                # Then: it refuses the selection before any runtime QA side effects.
                self.assertIsNotNone(reason)
                self.assertIn("db_backed", reason)

    def test_no_db_default_and_equivalent_safe_paths_remain_allowed(self) -> None:
        # Given: the default no-DB focused suite and equivalent safe path forms.
        variants = (
            (),
            ("./tests/test_legacy_telegram_removed.py", "-q"),
            (str(ROOT / "tests" / "test_cors_live_env.py"), "-q"),
            ("tests.test_verified_facts_seed_closing_costs", "-q"),
        )

        for variant in variants:
            with self.subTest(variant=variant):
                # When: the focused runner classifies the requested suite.
                reason = RUNNER._suite_policy_error(variant)

                # Then: no-DB selections stay eligible for check-only/real runner use.
                self.assertIsNone(reason)


if __name__ == "__main__":
    unittest.main()
