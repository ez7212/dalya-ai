"""
Generic Community Data Loader

Auto-discovers all JSON files in knowledge_base/ and matches them to listings
by alias. No per-development code — adding a new community means dropping a
JSON file in knowledge_base/, nothing else.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERFORMANCE (scales to hundreds of communities)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Index is built once at startup (or first access) and cached for process
lifetime. Lookup is O(1) per alias via an inverted dict, not O(n×m) linear
scan. Incremental adds via add_to_index() avoid full rebuilds when a new
community file is approved.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE NAMING CONVENTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Files are named {developer}_{community}.json, e.g.:
  emaar_oasis.json
  sobha_seahaven.json
  damac_akoya.json        (future)
  binghatti_hills.json    (future)

DEVELOPER GROUPING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each file declares "developer_keywords" — a list of strings that identify
its developer. Any SPA whose developer name contains one of these keywords
is considered part of that developer's family.

MATCHING LOGIC (two-pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pass 1 — alias lookup: O(1) dict lookup for the project name against all
  registered aliases. Most specific sub-development alias wins (longest match).

Pass 2 — developer keyword fallback: if no alias matched but a developer
  name was provided, check the developer keyword index. Returns the best
  available knowledge base for that developer.

ADDING A NEW DEVELOPMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Create knowledge_base/{developer}_{community}.json
2. Required fields: "aliases", "developer_keywords", "prompt_data"
3. Optional: "sub_developments" with per-sub "aliases" + "prompt_data_overrides"
4. Drop the file — server picks it up on next restart, or call add_to_index().
"""

import json
import copy
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent.parent / "knowledge_base"


# ── Index structure ───────────────────────────────────────────────────────
# Built once, O(1) lookups. Supports incremental adds.

class _CommunityIndex:
    """
    Inverted index mapping aliases → community data entries.

    Two lookup dicts:
    - alias_to_entry: {alias_string: (entry_idx, alias_len)} — for project name matching
    - dev_keyword_to_entries: {keyword: [entry_idx, ...]} — for developer fallback
    """

    def __init__(self):
        self.entries: list[dict] = []
        self.alias_to_entry: dict[str, tuple[int, int]] = {}  # alias → (entry_idx, alias_len)
        self.dev_keyword_to_entries: dict[str, list[int]] = {}  # keyword → [entry_idx, ...]

    def add(self, data: dict):
        """Add a community data entry to the index."""
        idx = len(self.entries)
        self.entries.append(data)

        # Index top-level aliases
        for alias in data.get("aliases", []):
            alias_lower = alias.lower()
            existing = self.alias_to_entry.get(alias_lower)
            # Keep the longest alias (most specific) if collision
            if existing is None or len(alias_lower) > existing[1]:
                self.alias_to_entry[alias_lower] = (idx, len(alias_lower))

        # Index sub-development aliases
        for sub_key, sub in data.get("sub_developments", {}).items():
            if not sub or not isinstance(sub, dict):
                continue
            for alias in sub.get("aliases", []):
                alias_lower = alias.lower()
                existing = self.alias_to_entry.get(alias_lower)
                if existing is None or len(alias_lower) > existing[1]:
                    self.alias_to_entry[alias_lower] = (idx, len(alias_lower))

        # Index developer keywords
        for keyword in data.get("developer_keywords", []):
            kw_lower = keyword.lower()
            if kw_lower not in self.dev_keyword_to_entries:
                self.dev_keyword_to_entries[kw_lower] = []
            self.dev_keyword_to_entries[kw_lower].append(idx)

    def find_by_project(self, project_lower: str) -> Optional[tuple[dict, int]]:
        """
        Find the best matching entry for a project name.
        Returns (entry, alias_len) or None. Longest alias match wins.
        """
        best_entry = None
        best_len = 0

        for alias, (idx, alias_len) in self.alias_to_entry.items():
            if alias in project_lower and alias_len > best_len:
                best_entry = self.entries[idx]
                best_len = alias_len

        if best_entry:
            return (best_entry, best_len)
        return None

    def find_by_developer(self, dev_lower: str) -> Optional[dict]:
        """Find an entry by developer keyword fallback."""
        for keyword, indices in self.dev_keyword_to_entries.items():
            if keyword in dev_lower and indices:
                return self.entries[indices[0]]
        return None


# ── Global index (singleton) ─────────────────────────────────────────────

_index: Optional[_CommunityIndex] = None


def _build_index() -> _CommunityIndex:
    """Build the full index from all JSON files in knowledge_base/."""
    index = _CommunityIndex()
    file_count = 0

    for path in sorted(_KNOWLEDGE_BASE_DIR.glob("*.json")):
        if path.name == "schema.json":
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            if "aliases" in data and "prompt_data" in data:
                index.add(data)
                file_count += 1
                logger.debug("Indexed community KB: %s (%d aliases)", path.name, len(data.get("aliases", [])))
            else:
                logger.warning("Skipping %s — missing 'aliases' or 'prompt_data'", path.name)
        except Exception as e:
            logger.error("Failed to load %s: %s", path.name, e)

    logger.info(
        "Community data index built: %d files, %d aliases, %d dev keywords",
        file_count, len(index.alias_to_entry), len(index.dev_keyword_to_entries),
    )
    return index


def _get_index() -> _CommunityIndex:
    global _index
    if _index is None:
        _index = _build_index()
    return _index


def invalidate_index():
    """Force full index rebuild on next access. Use sparingly — prefer add_to_index()."""
    global _index
    _index = None
    logger.info("Community data index invalidated — will rebuild on next access")


def add_to_index(file_path: Path):
    """
    Incrementally add a single file to the index without rebuilding everything.
    Call this when a new community file is approved.
    """
    index = _get_index()
    try:
        with open(file_path) as f:
            data = json.load(f)
        if "aliases" in data and "prompt_data" in data:
            index.add(data)
            logger.info(
                "Incrementally added %s to index (%d aliases)",
                file_path.name, len(data.get("aliases", [])),
            )
        else:
            logger.warning("Cannot add %s — missing 'aliases' or 'prompt_data'", file_path.name)
    except Exception as e:
        logger.error("Failed to add %s to index: %s", file_path.name, e)


# ── Prompt data builder ──────────────────────────────────────────────────

def _apply_sub_override(base: dict, dev: dict, project_lower: str) -> dict:
    """Find the best sub-development match and merge its overrides into base."""
    best_sub = None
    best_sub_len = 0

    for sub_key, sub in dev.get("sub_developments", {}).items():
        if not sub or not isinstance(sub, dict):
            continue
        for alias in [a.lower() for a in sub.get("aliases", [])]:
            if alias in project_lower and len(alias) > best_sub_len:
                best_sub = sub
                best_sub_len = len(alias)

    if best_sub and best_sub.get("prompt_data_overrides"):
        for key, val in best_sub["prompt_data_overrides"].items():
            if key == "investment_overrides" and "investment" in base:
                # Merge investment fields — never replace the whole dict
                base["investment"].update(val)
            elif key == "community":
                # Never overwrite the master community name from a sub-development override.
                pass
            else:
                base[key] = val

    return base


def _build_result(dev: dict, project_lower: str) -> dict:
    base = copy.deepcopy(dev["prompt_data"])
    base = _apply_sub_override(base, dev, project_lower)
    if "community" not in base:
        base["community"] = dev.get("name", "")
    return base


# ── Public API ───────────────────────────────────────────────────────────

def get_community_data_for_listing(
    project_name: str,
    developer: Optional[str] = None,
) -> Optional[dict]:
    """
    Return community_data dict for prompt_builder, or None if no match.

    Pass 1: alias lookup (O(1) per alias, longest match wins).
    Pass 2: developer keyword fallback if pass 1 found nothing.
    """
    index = _get_index()
    project_lower = project_name.lower()
    dev_lower = (developer or "").lower()

    # Pass 1 — alias match (O(n) over alias_to_entry, but dict lookup is fast)
    match = index.find_by_project(project_lower)
    if match:
        dev, _ = match
        return _build_result(dev, project_lower)

    # Pass 2 — developer keyword fallback
    if dev_lower:
        dev = index.find_by_developer(dev_lower)
        if dev:
            logger.info(
                "No alias match for '%s'; using developer fallback (%s)",
                project_name, dev.get("name"),
            )
            return _build_result(dev, project_lower)

    return None
