"""
Community Knowledge Base Schema Validator

Validates KB JSON files in knowledge_base/ against the canonical JSON Schema
(knowledge_base/schema.json). Used by scripts/validate_kb.py and available
for import in tests or CI pipelines.

Usage:
    from app.core.schema_validator import validate_community_file, validate_all

    result = validate_community_file("knowledge_base/emaar_oasis.json")
    print(result.valid, result.errors, result.warnings)

    all_results = validate_all()
    for name, result in all_results.items():
        print(f"{name}: {'PASS' if result.valid else 'FAIL'}")
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema import Draft202012Validator, ValidationError
except ImportError:
    raise ImportError(
        "jsonschema is required for KB validation. "
        "Install it with: pip install jsonschema"
    )

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_SCHEMA_PATH = _PROJECT_ROOT / "knowledge_base" / "schema.json"
_KNOWLEDGE_BASE_DIR = _PROJECT_ROOT / "knowledge_base"

# Cached schema
_schema: dict | None = None


@dataclass
class ValidationResult:
    """Result of validating a single community KB file."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)


def _load_schema() -> dict:
    """Load and cache the JSON Schema."""
    global _schema
    if _schema is None:
        with open(_SCHEMA_PATH) as f:
            _schema = json.load(f)
    return _schema


def _check_prompt_data_quality(data: dict, warnings: list[str]) -> list[str]:
    """
    Check recommended (but not schema-required) fields in prompt_data
    and return missing field paths as warnings.
    """
    missing: list[str] = []
    pd = data.get("prompt_data", {})

    # Recommended prompt_data fields
    recommended = {
        "developer_track_record": "prompt_data.developer_track_record",
        "sales_talking_points": "prompt_data.sales_talking_points",
    }
    for key, path in recommended.items():
        if key not in pd or pd[key] is None:
            missing.append(path)
            warnings.append(f"Recommended field missing: {path}")

    # Check location.description
    loc = pd.get("location", {})
    if not loc.get("description"):
        missing.append("prompt_data.location.description")
        warnings.append("Recommended field missing: prompt_data.location.description")

    # Check location.distances has entries
    if not loc.get("distances"):
        missing.append("prompt_data.location.distances")
        warnings.append("Recommended field missing: prompt_data.location.distances")

    # Check investment has key fields
    inv = pd.get("investment", {})
    for inv_key in ["ownership", "golden_visa_eligible"]:
        if inv_key not in inv:
            path = f"prompt_data.investment.{inv_key}"
            missing.append(path)
            warnings.append(f"Recommended field missing: {path}")

    # Check nearby.schools is populated
    nearby = pd.get("nearby", {})
    if not nearby.get("schools"):
        missing.append("prompt_data.nearby.schools")
        warnings.append("Recommended field missing: prompt_data.nearby.schools")

    return missing


def _check_metadata_presence(data: dict, warnings: list[str]) -> list[str]:
    """
    Existing files may lack the new metadata block. This is a warning,
    not an error, since the schema marks it required for new files but
    we want to be lenient during migration.
    """
    missing: list[str] = []
    if "metadata" not in data:
        missing.append("metadata")
        warnings.append(
            "Missing 'metadata' block. Existing files should add metadata "
            "with schema_version, last_researched_at, and research_confidence."
        )
    else:
        meta = data["metadata"]
        if not meta.get("source_urls"):
            warnings.append(
                "metadata.source_urls is empty — consider adding research source URLs."
            )
        if meta.get("research_confidence") is not None and meta["research_confidence"] < 0.5:
            warnings.append(
                f"metadata.research_confidence is {meta['research_confidence']} (below 0.5) "
                "— this file should be re-researched."
            )
        if meta.get("last_audited_at") is None:
            warnings.append("metadata.last_audited_at is null — file has never been audited.")
    return missing


def _check_sub_development_aliases(data: dict, warnings: list[str]) -> None:
    """Warn if sub_developments exist but lack aliases or prompt_data_overrides."""
    subs = data.get("sub_developments", {})
    for sub_key, sub_data in subs.items():
        if not isinstance(sub_data, dict):
            continue
        if not sub_data.get("aliases"):
            warnings.append(
                f"sub_developments.{sub_key} has no 'aliases' — "
                "it will never be matched by community_data.py."
            )
        if not sub_data.get("prompt_data_overrides"):
            warnings.append(
                f"sub_developments.{sub_key} has no 'prompt_data_overrides' — "
                "matched listings will use parent prompt_data without sub-specific enrichment."
            )


def validate_community_file(file_path: str) -> ValidationResult:
    """
    Validate a single community KB JSON file against the schema.

    Args:
        file_path: Path to the JSON file (absolute or relative to project root).

    Returns:
        ValidationResult with valid flag, errors, warnings, and missing fields.
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = _PROJECT_ROOT / path

    errors: list[str] = []
    warnings: list[str] = []
    missing_fields: list[str] = []

    # Load file
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return ValidationResult(
            valid=False,
            errors=[f"File not found: {path}"],
        )
    except json.JSONDecodeError as e:
        return ValidationResult(
            valid=False,
            errors=[f"Invalid JSON: {e}"],
        )

    # Schema validation — run with metadata optional for existing files
    schema = _load_schema()

    # For existing files that lack metadata, validate against a relaxed
    # version of the schema where metadata is not required.
    has_metadata = "metadata" in data
    if not has_metadata:
        # Validate without metadata requirement
        relaxed_schema = {**schema}
        relaxed_required = [r for r in schema.get("required", []) if r != "metadata"]
        relaxed_schema["required"] = relaxed_required

        validator = Draft202012Validator(relaxed_schema)
    else:
        validator = Draft202012Validator(schema)

    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        error_path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"[{error_path}] {error.message}")

    # Quality checks (warnings only)
    missing_fields.extend(_check_metadata_presence(data, warnings))
    missing_fields.extend(_check_prompt_data_quality(data, warnings))
    _check_sub_development_aliases(data, warnings)

    # Check aliases are non-empty strings
    for i, alias in enumerate(data.get("aliases", [])):
        if not alias or not alias.strip():
            warnings.append(f"aliases[{i}] is empty or whitespace-only.")

    # Check developer_keywords are non-empty
    for i, kw in enumerate(data.get("developer_keywords", [])):
        if not kw or not kw.strip():
            warnings.append(f"developer_keywords[{i}] is empty or whitespace-only.")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        missing_fields=missing_fields,
    )


def validate_all() -> dict[str, ValidationResult]:
    """
    Validate all .json files in knowledge_base/ (excluding schema.json).

    Returns:
        Dict keyed by filename, values are ValidationResult instances.
    """
    results: dict[str, ValidationResult] = {}

    if not _KNOWLEDGE_BASE_DIR.exists():
        logger.error(f"Knowledge base directory not found: {_KNOWLEDGE_BASE_DIR}")
        return results

    for path in sorted(_KNOWLEDGE_BASE_DIR.glob("*.json")):
        if path.name == "schema.json":
            continue
        results[path.name] = validate_community_file(str(path))

    return results
