from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final


ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_TESTS: Final = (
    "tests/test_legacy_telegram_removed.py",
    "tests/test_cors_live_env.py",
    "tests/test_verified_facts_seed_closing_costs.py",
    "-q",
)
ALLOWED_NO_DB_TESTS: Final = frozenset(DEFAULT_TESTS) - {"-q"}
DB_BACKED_TESTS: Final = {
    "tests/test_seller_lead_privacy.py": "imports SessionLocal and writes/deletes app DB rows",
    "tests/test_needs_reply_priority.py": "imports SessionLocal/engine and writes/deletes app DB rows",
    "tests/test_verified_facts_output_gate.py": "imports ChatbotEngine/WhatsApp paths that reach dotenv/SessionLocal",
}


@dataclass(frozen=True, slots=True)
class PytestSelection:
    raw: str
    normalized: str
    is_directory: bool


def pytest_args(args: tuple[str, ...]) -> list[str]:
    selected = list(args or DEFAULT_TESTS)
    if "--noconftest" not in selected:
        selected.insert(0, "--noconftest")
    return selected


def suite_policy_error(args: tuple[str, ...]) -> str | None:
    selected = _pytest_selections(pytest_args(args))
    if args and not selected:
        return "pytest_discovery_disallowed:no_explicit_allowlisted_tests"

    directories = [selection for selection in selected if selection.is_directory]
    if directories:
        details = ",".join(
            f"{selection.normalized}(could_include_db_backed_tests:{';'.join(DB_BACKED_TESTS)})"
            for selection in directories
        )
        return f"db_backed_directory_discovery_disallowed:{details}"

    disallowed = [selection.normalized for selection in selected if selection.normalized in DB_BACKED_TESTS]
    if disallowed:
        details = ",".join(f"{path}({DB_BACKED_TESTS[path]})" for path in disallowed)
        return f"db_backed_tests_disallowed:{details}"

    unknown = [selection.normalized for selection in selected if selection.normalized not in ALLOWED_NO_DB_TESTS]
    if unknown:
        return f"unclassified_tests_disallowed:{','.join(unknown)}"
    return None


def _pytest_selections(args: list[str]) -> list[PytestSelection]:
    selections: list[PytestSelection] = []
    for arg in args:
        normalized = _normalize_selector(arg)
        if normalized is not None:
            selections.append(PytestSelection(arg, normalized, _is_directory(normalized)))
    return selections


def _normalize_selector(raw: str) -> str | None:
    selector = raw.split("::", 1)[0]
    if selector == "" or selector.startswith("-"):
        return None
    module_path = _normalize_module_selector(selector)
    if module_path is not None:
        return module_path
    if not _looks_like_path_selector(selector):
        return None
    return _normalize_path_selector(selector)


def _normalize_module_selector(selector: str) -> str | None:
    if not selector.startswith("tests."):
        return None
    normalized = Path(*selector.split(".")).as_posix()
    if (ROOT / normalized).is_dir():
        return normalized
    return f"{normalized}.py"


def _looks_like_path_selector(selector: str) -> bool:
    path = Path(selector).expanduser()
    return (
        path.is_absolute()
        or selector == "."
        or selector == "tests"
        or selector.startswith(("./", "../", "tests/"))
        or "/" in selector
    )


def _normalize_path_selector(selector: str) -> str:
    path = Path(selector).expanduser()
    resolved = path.resolve() if path.is_absolute() else (ROOT / path).resolve()
    try:
        normalized = resolved.relative_to(ROOT).as_posix()
    except ValueError:
        normalized = path.as_posix().rstrip("/")
    candidate = ROOT / normalized
    py_candidate = ROOT / f"{normalized}.py"
    if not candidate.exists() and candidate.suffix == "" and py_candidate.exists():
        return f"{normalized}.py"
    return normalized or "."


def _is_directory(normalized: str) -> bool:
    return normalized == "." or (ROOT / normalized).is_dir()
