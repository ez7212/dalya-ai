#!/usr/bin/env python3
"""
Validate all community knowledge base files against the canonical schema.

Usage:
    python scripts/validate_kb.py              # validate all files
    python scripts/validate_kb.py --verbose    # include warnings
    python scripts/validate_kb.py --file emaar_oasis.json  # validate one file
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path so imports work when run as a script
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from app.core.schema_validator import ValidationResult, validate_all, validate_community_file

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"


def print_result(name: str, result: ValidationResult, verbose: bool = False) -> None:
    status = PASS if result.valid else FAIL
    print(f"  {status}  {name}")

    if result.errors:
        for err in result.errors:
            print(f"         \033[91mERROR\033[0m  {err}")

    if verbose:
        for warn in result.warnings:
            print(f"         {WARN}   {warn}")
        if result.missing_fields:
            print(f"         Missing recommended fields: {', '.join(result.missing_fields)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate community knowledge base files against schema.json"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show warnings and missing recommended fields",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        default=None,
        help="Validate a single file (filename only, e.g. emaar_oasis.json)",
    )
    args = parser.parse_args()

    print()
    print("Dalya AI — Knowledge Base Validator")
    print("=" * 40)

    if args.file:
        kb_dir = _project_root / "knowledge_base"
        path = kb_dir / args.file
        result = validate_community_file(str(path))
        results = {args.file: result}
    else:
        results = validate_all()

    if not results:
        print("  No knowledge base files found.")
        return 1

    total = len(results)
    passed = 0
    failed = 0
    total_errors = 0
    total_warnings = 0

    for name, result in results.items():
        print_result(name, result, verbose=args.verbose)
        if result.valid:
            passed += 1
        else:
            failed += 1
        total_errors += len(result.errors)
        total_warnings += len(result.warnings)

    print()
    print(f"  {total} files checked: {passed} passed, {failed} failed")
    print(f"  {total_errors} errors, {total_warnings} warnings")
    print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
