#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
# How to run
# python3 scripts/run_focused_backend_qa.py --check-only --evidence .omo/evidence/task-2-runtime-qa-check-red.json
# python3 scripts/run_focused_backend_qa.py --python python3.12 --evidence .omo/evidence/task-2-runtime-qa-green.json
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

from focused_backend_qa_policy import pytest_args as _pytest_args
from focused_backend_qa_policy import suite_policy_error as _suite_policy_error


ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_VENV: Final = Path("/private/tmp/dalya-focused-backend-qa-venv")
REQUIREMENTS: Final = ROOT / "requirements.txt"
SUPPORTED_MINORS: Final = {(3, 12), (3, 13)}


class Status(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class RunnerArgs:
    check_only: bool
    python: str
    evidence: Path
    venv: Path
    pytest_args: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommandRecord:
    argv: list[str]
    cwd: str
    exit_code: int | None
    duration_seconds: float
    timed_out: bool


@dataclass(frozen=True, slots=True)
class InterpreterProbe:
    requested: str
    resolved: str | None
    version: str | None
    major: int | None
    minor: int | None
    compatible: bool
    reason: str


@dataclass(frozen=True, slots=True)
class RepoVenvProbe:
    path: str
    exists: bool
    is_symlink: bool
    symlink_target: str | None
    resolved: str | None
    reason: str


def _parse_args() -> RunnerArgs:
    parser = argparse.ArgumentParser(description="Run focused no-DB backend QA.")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--python", default="python3")
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--venv", default=DEFAULT_VENV, type=Path)
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    raw = parser.parse_args()
    return RunnerArgs(
        check_only=raw.check_only,
        python=raw.python,
        evidence=raw.evidence,
        venv=raw.venv,
        pytest_args=tuple(arg for arg in raw.pytest_args if arg != "--"),
    )


def _resolve_python(requested: str) -> str | None:
    path = Path(requested).expanduser()
    if path.is_absolute() or path.parent != Path("."):
        return str(path) if path.exists() else None
    return shutil.which(requested)


def _probe_python(requested: str) -> InterpreterProbe:
    resolved = _resolve_python(requested)
    if resolved is None:
        return InterpreterProbe(requested, None, None, None, None, False, f"interpreter_not_found:{requested}")
    command = [
        resolved,
        "-c",
        "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return InterpreterProbe(requested, resolved, None, None, None, False, "version_probe_timed_out")
    if result.returncode != 0:
        return InterpreterProbe(
            requested, resolved, None, None, None, False, f"version_probe_failed:{result.returncode}"
        )
    version = result.stdout.strip()
    parts = version.split(".")
    major, minor = int(parts[0]), int(parts[1])
    if (major, minor) not in SUPPORTED_MINORS:
        reason = f"python_{major}.{minor}_refused_for_pinned_deps_expected_3.12_or_3.13"
        return InterpreterProbe(requested, resolved, version, major, minor, False, reason)
    return InterpreterProbe(requested, resolved, version, major, minor, True, "compatible_python_3.12_or_3.13")


def _probe_repo_venv() -> RepoVenvProbe:
    path = ROOT / "venv" / "bin" / "python"
    target = os.readlink(path) if path.is_symlink() else None
    if path.exists():
        return RepoVenvProbe(str(path), True, path.is_symlink(), target, str(path.resolve()), "repo_venv_python_exists")
    reason = f"repo_venv_python_broken_symlink:{target}" if path.is_symlink() else "repo_venv_python_missing"
    return RepoVenvProbe(str(path), False, path.is_symlink(), target, None, reason)


def _run(argv: list[str], timeout_seconds: int) -> CommandRecord:
    started = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CommandRecord(argv, str(ROOT), None, round(time.monotonic() - started, 3), True)
    return CommandRecord(argv, str(ROOT), result.returncode, round(time.monotonic() - started, 3), False)


def _prepare_venv(path: Path) -> str | None:
    if not path.exists():
        return None
    if not (path / "pyvenv.cfg").exists():
        return f"temp_venv_path_exists_but_is_not_a_venv:{path}"
    shutil.rmtree(path)
    return None


def _cleanup_venv(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return True, "temp_venv_absent"
    try:
        shutil.rmtree(path)
    except OSError as exc:
        return False, f"cleanup_failed:{type(exc).__name__}:{exc}"
    return True, "temp_venv_removed"


def _emit(
    args: RunnerArgs,
    status: Status,
    reason: str,
    probe: InterpreterProbe,
    repo_venv: RepoVenvProbe,
    commands: list[CommandRecord],
    cleanup: tuple[bool, str],
    started: float,
) -> int:
    payload = {
        "status": status.value,
        "reason": reason,
        "selected_interpreter": asdict(probe),
        "repo_venv_python": asdict(repo_venv),
        "temp_venv_path": str(args.venv),
        "requirements_file": str(REQUIREMENTS),
        "check_only": args.check_only,
        "pytest_args": _pytest_args(args.pytest_args),
        "suite_policy": _suite_policy_error(args.pytest_args) or "allowed_no_db_tests_only",
        "commands": [asdict(command) for command in commands],
        "cleanup_occurred": cleanup[0],
        "cleanup_reason": cleanup[1],
        "duration_seconds": round(time.monotonic() - started, 3),
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status.value, "reason": reason}, sort_keys=True))
    match status:
        case Status.PASS:
            return 0
        case Status.BLOCKED:
            return 2
        case Status.FAIL:
            return 1


def _run_real(args: RunnerArgs, probe: InterpreterProbe, repo_venv: RepoVenvProbe, started: float) -> int:
    commands: list[CommandRecord] = []
    if not probe.compatible:
        return _emit(args, Status.BLOCKED, probe.reason, probe, repo_venv, commands, _cleanup_venv(args.venv), started)
    if not REQUIREMENTS.exists():
        reason = f"requirements_file_missing:{REQUIREMENTS}"
        return _emit(args, Status.BLOCKED, reason, probe, repo_venv, commands, _cleanup_venv(args.venv), started)
    prepare_error = _prepare_venv(args.venv)
    if prepare_error is not None:
        return _emit(args, Status.BLOCKED, prepare_error, probe, repo_venv, commands, (False, "refused_non_venv"), started)

    status = Status.FAIL
    reason = "focused_backend_pytest_not_started"
    try:
        commands.append(_run([probe.resolved or args.python, "-m", "venv", str(args.venv)], 120))
        if commands[-1].timed_out or commands[-1].exit_code != 0:
            status = Status.BLOCKED
            reason = "venv_creation_timed_out" if commands[-1].timed_out else "venv_creation_failed"
        else:
            venv_python = str(args.venv / "bin" / "python")
            commands.append(_run([venv_python, "-m", "pip", "install", "-r", str(REQUIREMENTS)], 900))
            if commands[-1].timed_out or commands[-1].exit_code != 0:
                status = Status.BLOCKED
                reason = "requirements_install_timed_out" if commands[-1].timed_out else "requirements_install_failed"
            else:
                commands.append(_run([venv_python, "-m", "pytest", *_pytest_args(args.pytest_args)], 300))
                if commands[-1].timed_out:
                    status, reason = Status.FAIL, "pytest_timed_out"
                elif commands[-1].exit_code == 0:
                    status, reason = Status.PASS, "focused_backend_pytest_passed"
                else:
                    status, reason = Status.FAIL, f"focused_backend_pytest_failed:{commands[-1].exit_code}"
    finally:
        cleanup = _cleanup_venv(args.venv)

    if status is Status.PASS and not cleanup[0]:
        status, reason = Status.FAIL, cleanup[1]
    return _emit(args, status, reason, probe, repo_venv, commands, cleanup, started)


def main() -> int:
    started = time.monotonic()
    args = _parse_args()
    probe = _probe_python(args.python)
    repo_venv = _probe_repo_venv()
    suite_error = _suite_policy_error(args.pytest_args)
    if suite_error is not None:
        return _emit(args, Status.BLOCKED, suite_error, probe, repo_venv, [], (False, "real_run_not_started"), started)
    if args.check_only:
        status = Status.PASS if probe.compatible else Status.BLOCKED
        reason = probe.reason if repo_venv.exists else f"{probe.reason};{repo_venv.reason}"
        return _emit(args, status, reason, probe, repo_venv, [], (False, "real_run_not_started"), started)
    return _run_real(args, probe, repo_venv, started)


if __name__ == "__main__":
    raise SystemExit(main())
