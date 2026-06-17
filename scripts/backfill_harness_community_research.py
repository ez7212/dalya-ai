from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import or_

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.safety import UnsafeTestDatabaseError, assert_safe_test_database, load_test_environment_file

load_test_environment_file()

from tests.harness.builder import DEFAULT_SNAPSHOT_DIR, build_harness_plan, snapshot_name


REPO_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_BASE_DIR = REPO_ROOT / "knowledge_base"
NEEDS_REVIEW_DIR = KNOWLEDGE_BASE_DIR / "needs_review"


DEVELOPER_OVERRIDES = {
    "address_harbour_point": "Emaar Properties",
    "sidra_villas": "Emaar Properties",
    "dubai_marina": "LIV Developers",
    "the_address_jumeirah_resort_and_spa": "Dubai Holding",
}


@dataclass
class HarnessCommunity:
    key: str
    display_name: str
    developer: str
    sub_communities: set[str] = field(default_factory=set)
    source_urls: set[str] = field(default_factory=set)
    listing_ids: set[str] = field(default_factory=set)


def _slug_text(value: str | None) -> str:
    return (value or "").replace("_", " ").strip()


def _parse_maybe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            parsed = ast.literal_eval(value)
            return parsed if isinstance(parsed, dict) else {}
        except (SyntaxError, ValueError):
            return {}
    return {}


def _developer_from_snapshot(scrape: dict[str, Any], community_key: str) -> str:
    if scrape.get("developer"):
        return str(scrape["developer"])
    project = _parse_maybe_dict(scrape.get("building_or_project"))
    agency = project.get("agency") if isinstance(project.get("agency"), dict) else {}
    for key in ("name", "name_l2", "name_l3"):
        if agency.get(key):
            return str(agency[key])
    if community_key in DEVELOPER_OVERRIDES:
        return DEVELOPER_OVERRIDES[community_key]
    return "Unknown Developer"


def _display_name_from_snapshot(scrape: dict[str, Any], community_key: str) -> str:
    return str(scrape.get("community") or _slug_text(community_key))


def _sub_community_from_snapshot(scrape: dict[str, Any]) -> str | None:
    sub = scrape.get("subcommunity") or scrape.get("building_or_project")
    project = _parse_maybe_dict(sub)
    if project.get("title"):
        return str(project["title"])
    if isinstance(sub, str) and not sub.strip().startswith("{"):
        return sub
    return None


def enumerate_harness_communities() -> list[HarnessCommunity]:
    seed = build_harness_plan()
    by_key: dict[str, HarnessCommunity] = {}
    for listing in seed.listings:
        if not listing.community_key:
            continue
        snapshot_path = Path(DEFAULT_SNAPSHOT_DIR) / snapshot_name(listing.source_url)
        snapshot = json.loads(snapshot_path.read_text())
        scrape = snapshot["scrape"]
        community = by_key.setdefault(
            listing.community_key,
            HarnessCommunity(
                key=listing.community_key,
                display_name=_display_name_from_snapshot(scrape, listing.community_key),
                developer=_developer_from_snapshot(scrape, listing.community_key),
            ),
        )
        sub = _sub_community_from_snapshot(scrape)
        if sub:
            community.sub_communities.add(sub)
        community.source_urls.add(listing.source_url)
        community.listing_ids.add(listing.listing_id)
    return sorted(by_key.values(), key=lambda item: item.key)


def _safe_filename(path: str | None) -> Path | None:
    if not path:
        return None
    candidate = (KNOWLEDGE_BASE_DIR / path).resolve()
    if KNOWLEDGE_BASE_DIR.resolve() not in candidate.parents and candidate != KNOWLEDGE_BASE_DIR.resolve():
        return None
    return candidate


def _load_research_payload(file_path: str | None) -> dict[str, Any] | None:
    path = _safe_filename(file_path)
    if not path or not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _prompt_data_from_payload(payload: dict[str, Any], community: HarnessCommunity) -> dict[str, Any]:
    prompt_data = payload.get("prompt_data") if isinstance(payload.get("prompt_data"), dict) else {}
    data = dict(prompt_data)
    data.setdefault("community", payload.get("name") or community.display_name)
    data.setdefault("developer", payload.get("developer") or community.developer)
    data.setdefault("source", "community_research_backfill")
    return data


def _is_real_research(record) -> bool:
    if not record or record.status not in {"approved", "needs_review"}:
        return False
    if not record.file_path or record.file_path.startswith("harness/"):
        return False
    payload = _load_research_payload(record.file_path)
    if not payload:
        return False
    return bool(payload.get("prompt_data") and payload.get("aliases"))


def _assert_parse_clean_result(community: HarnessCommunity, payload: dict[str, Any]) -> None:
    flags = payload.get("metadata", {}).get("audit_flags", [])
    parse_flags = [
        str(flag)
        for flag in flags
        if "json parse failure" in str(flag).lower()
    ]
    if parse_flags:
        raise RuntimeError(
            f"Community research for {community.key} contains model JSON parse fallback flags; "
            f"refusing to approve degraded research: {parse_flags}"
        )
    if not payload.get("prompt_data"):
        raise RuntimeError(f"Community research for {community.key} has no prompt_data; refusing to approve.")
    if not payload.get("aliases"):
        raise RuntimeError(f"Community research for {community.key} has no aliases; refusing to approve.")


def _find_record(db, community: HarnessCommunity):
    from app.models.db_models import DBCommunityResearch

    return (
        db.query(DBCommunityResearch)
        .filter(
            or_(
                DBCommunityResearch.project_name == community.key,
                DBCommunityResearch.project_name == community.display_name,
            ),
            DBCommunityResearch.developer == community.developer,
        )
        .first()
    )


def _approve_draft_file(file_path: str) -> str:
    source = _safe_filename(file_path)
    if not source or not source.exists():
        raise FileNotFoundError(f"Researcher output file does not exist: {file_path}")
    if source.parent == KNOWLEDGE_BASE_DIR:
        return source.name
    target = KNOWLEDGE_BASE_DIR / source.name
    shutil.copyfile(source, target)
    return target.name


def _update_harness_listings(db, community: HarnessCommunity, payload: dict[str, Any]) -> int:
    from app.models.db_models import DBListing

    prompt_data = _prompt_data_from_payload(payload, community)
    rows = (
        db.query(DBListing)
        .filter(DBListing.listing_id.in_(list(community.listing_ids)))
        .all()
    )
    for row in rows:
        row.community_data = prompt_data
        stages = dict(row.processing_stages or {})
        stages["community_research"] = {
            "status": "complete",
            "at": datetime.now(timezone.utc).isoformat(),
            "source": "harness_community_research_backfill",
            "community_key": community.key,
        }
        row.processing_stages = stages
    return len(rows)


async def _research_one(community: HarnessCommunity) -> dict[str, Any]:
    from app.core.community_researcher import CommunityResearcher

    researcher = CommunityResearcher()
    sub = sorted(community.sub_communities)[0] if community.sub_communities else None
    return await researcher.research_community(
        project_name=community.display_name,
        developer=community.developer,
        sub_community=sub,
    )


def _research_filename(community: HarnessCommunity) -> str:
    dev = re.sub(r"[^a-z0-9]+", "_", community.developer.lower().split()[0]).strip("_")
    name = re.sub(r"^the\s+", "", community.display_name.lower())
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    digest = hashlib.md5(f"{community.key}:{community.developer}".encode()).hexdigest()[:6]
    return f"{dev}_{name}_{digest}.json"


def _existing_bounded_result(community: HarnessCommunity) -> dict[str, Any] | None:
    relative_path = f"needs_review/{_research_filename(community)}"
    payload = _load_research_payload(relative_path)
    if not payload:
        payload = _load_research_payload(_research_filename(community))
        relative_path = _research_filename(community) if payload else relative_path
    if not payload:
        return None
    _assert_parse_clean_result(community, payload)
    metadata = payload.get("metadata", {})
    return {
        "file_path": relative_path,
        "research_confidence": metadata.get("research_confidence"),
        "source_urls": metadata.get("source_urls", []) or list(community.source_urls),
        "audit_flags": metadata.get("audit_flags", []),
    }


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


async def _research_one_bounded(community: HarnessCommunity) -> dict[str, Any]:
    """
    Bounded harness backfill path.

    The full CommunityResearcher performs several whole-file rewrites and has
    been returning malformed JSON for these harness communities. This path
    still uses the existing researcher client/search helpers and writes the
    same KB schema, but constrains the task to one researched JSON object so it
    can run reliably as a test-harness backfill.
    """
    from app.core.community_researcher import CommunityResearcher

    researcher = CommunityResearcher()
    sub_names = sorted(community.sub_communities)
    queries = [
        f'"{community.display_name}" Dubai overview amenities location schools',
        f'"{community.display_name}" "{community.developer}" Dubai developer community',
        f'"{community.display_name}" Dubai transport connectivity mall metro schools hospitals',
        f'"{community.display_name}" Dubai ROI rental yield property prices',
        f'"{community.display_name}" Bayut Property Finder Dubai',
    ]
    for sub in sub_names[:3]:
        queries.append(f'"{community.display_name}" "{sub}" Dubai amenities handover unit types')

    results = await researcher._search_web(queries)
    if not results:
        raise RuntimeError(f"No web results returned for {community.key}; refusing to create research.")

    sources_text = researcher._format_web_results(results[:16])
    now = datetime.now(timezone.utc).isoformat()
    aliases = [
        community.display_name,
        community.key.replace("_", " "),
        *sub_names,
    ]
    source_urls = list(dict.fromkeys(r.get("url", "") for r in results if r.get("url")))
    prompt = f"""You are creating a real community knowledge-base JSON file for Dalya's property advisor.

Return ONLY valid JSON. Keep the output concise, factual, and source-grounded.
Use null or sparse arrays where public data is not available. Do not invent exact
distances, ROI, fees, handover dates, or school details unless supported by the sources.

Community:
- key: {community.key}
- display name: {community.display_name}
- developer: {community.developer}
- sub-communities/buildings from harness listings: {json.dumps(sub_names, ensure_ascii=False)}
- source listing URLs: {json.dumps(sorted(community.source_urls), ensure_ascii=False)}

Required JSON shape:
{{
  "name": string,
  "developer": string,
  "last_updated": "YYYY-MM-DD",
  "researcher_notes": [string],
  "master_development": {{
    "overview": object,
    "location_connectivity": object,
    "shared_amenities": object,
    "nearby_infrastructure": object,
    "investment_data": object,
    "developer_profile": object
  }},
  "sub_developments": {{
    "<slug>": {{
      "aliases": [string],
      "prompt_data_overrides": {{
        "sub_community": string,
        "investment_overrides": object,
        "sales_talking_points": object
      }}
    }}
  }},
  "sales_talking_points": {{
    "development_level": {{
      "headline_stats": string,
      "scarcity_argument": string,
      "lifestyle_pitch": string,
      "investment_pitch": string,
      "objection_handling": string
    }},
    "per_sub_development": object
  }},
  "aliases": [string],
  "developer_keywords": [string],
  "prompt_data": {{
    "developer": string,
    "community": string,
    "location": {{
      "area": string,
      "description": string,
      "distances": object
    }},
    "community_amenities": [string],
    "nearby": {{
      "schools": [object],
      "healthcare": [object],
      "retail": [object]
    }},
    "investment": {{
      "ownership": string,
      "golden_visa_eligible": boolean,
      "projected_roi_percent": string|null,
      "branded_premium_note": string|null
    }},
    "sales_talking_points": object,
    "developer_track_record": string|null
  }},
  "metadata": {{
    "schema_version": "1.0",
    "last_researched_at": "{now}",
    "last_audited_at": null,
    "research_confidence": number,
    "source_urls": [string],
    "audit_flags": [string]
  }}
}}

Minimum requirements:
- aliases must include these harness aliases: {json.dumps(aliases, ensure_ascii=False)}
- prompt_data must be useful for answering buyer questions about schools, amenities,
  connectivity, ownership, nearby retail/healthcare, and market trajectory.
- audit_flags should list sparse or unverified areas. It must not include JSON parse failure flags.
- source_urls must be populated from the provided sources.

Web sources:
{sources_text}
"""

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: researcher.anthropic.messages.create(
            model=researcher.MODEL_SONNET,
            max_tokens=12000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        ),
    )
    raw = response.content[0].text
    try:
        payload = json.loads(_strip_json_fences(raw))
    except json.JSONDecodeError as exc:
        repaired = await researcher._repair_json_response(raw, model=researcher.MODEL_SONNET, parse_error=exc)
        if repaired is None:
            raise RuntimeError(f"Bounded research returned malformed JSON for {community.key}: {exc}") from exc
        payload = repaired

    payload.setdefault("name", community.display_name)
    payload.setdefault("developer", community.developer)
    payload.setdefault("last_updated", datetime.now(timezone.utc).date().isoformat())
    payload.setdefault("aliases", [])
    for alias in aliases:
        if alias and alias not in payload["aliases"]:
            payload["aliases"].append(alias)
    payload.setdefault("developer_keywords", [])
    dev_keyword = community.developer.split()[0].lower()
    if dev_keyword and dev_keyword not in payload["developer_keywords"]:
        payload["developer_keywords"].append(dev_keyword)
    payload.setdefault("metadata", {})
    payload["metadata"].setdefault("schema_version", "1.0")
    payload["metadata"].setdefault("last_researched_at", now)
    payload["metadata"].setdefault("last_audited_at", None)
    payload["metadata"].setdefault("research_confidence", 0.65)
    payload["metadata"]["source_urls"] = source_urls
    payload["metadata"].setdefault("audit_flags", [])

    _assert_parse_clean_result(community, payload)
    NEEDS_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    relative_path = f"needs_review/{_research_filename(community)}"
    target = KNOWLEDGE_BASE_DIR / relative_path
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "file_path": relative_path,
        "research_confidence": payload["metadata"].get("research_confidence"),
        "source_urls": source_urls,
        "audit_flags": payload["metadata"].get("audit_flags", []),
    }


async def backfill(force: bool = False, dry_run: bool = False, full_agent: bool = False) -> int:
    load_test_environment_file()
    if not dry_run:
        try:
            assert_safe_test_database(operation="harness community research backfill")
        except UnsafeTestDatabaseError as exc:
            raise SystemExit(f"\n*** DALYA TEST DATABASE SAFETY GUARD ***\n{exc}\n") from exc
        if not os.getenv("TAVILY_API_KEY"):
            raise SystemExit(
                "TAVILY_API_KEY is required to run the existing CommunityResearcher. "
                "Add it to .env.test or export it in the test shell."
            )

    communities = enumerate_harness_communities()
    print(f"harness communities={len(communities)}")
    for community in communities:
        print(
            f"- {community.key}: {community.display_name} "
            f"developer={community.developer} listings={len(community.listing_ids)} "
            f"subs={', '.join(sorted(community.sub_communities)) or '-'}"
        )
    if dry_run:
        return 0

    from app.db.session import SessionLocal, safe_commit
    from app.models.db_models import DBCommunityResearch

    researched = 0
    with SessionLocal() as db:
        for community in communities:
            record = _find_record(db, community)
            if _is_real_research(record) and not force:
                payload = _load_research_payload(record.file_path)
                updated = _update_harness_listings(db, community, payload or {})
                safe_commit(db)
                print(f"SKIP real research exists: {community.key} file={record.file_path} listings_updated={updated}")
                continue

            if record:
                print(f"RESEARCH refresh: {community.key} previous_status={record.status} file={record.file_path}")
                record.status = "researching"
                record.audit_flags = []
            else:
                print(f"RESEARCH new: {community.key}")
                record = DBCommunityResearch(
                    project_name=community.key,
                    developer=community.developer,
                    status="researching",
                )
                db.add(record)
            safe_commit(db)
            db.refresh(record)

            result = None if force or full_agent else _existing_bounded_result(community)
            if result:
                print(f"REUSE local bounded research: {community.key} file={result['file_path']}")
            else:
                result = await (_research_one(community) if full_agent else _research_one_bounded(community))
            approved_path = _approve_draft_file(result["file_path"])
            payload = _load_research_payload(approved_path) or {}
            _assert_parse_clean_result(community, payload)

            record.project_name = community.key
            record.developer = community.developer
            record.status = "approved"
            record.file_path = approved_path
            record.research_confidence = result.get("research_confidence")
            record.source_urls = result.get("source_urls", []) or list(community.source_urls)
            record.audit_flags = result.get("audit_flags", [])
            record.last_researched_at = datetime.now(timezone.utc)
            updated = _update_harness_listings(db, community, payload)
            safe_commit(db)
            researched += 1
            print(
                f"DONE {community.key}: file={approved_path} "
                f"confidence={record.research_confidence} listings_updated={updated}"
            )
    return researched


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill real community research for canonical harness communities.")
    parser.add_argument("--force", action="store_true", help="Refresh communities even when real research already exists.")
    parser.add_argument("--list", action="store_true", help="List required harness communities without writing to the database.")
    parser.add_argument("--full-agent", action="store_true", help="Use the full multi-pass CommunityResearcher instead of the bounded harness backfill path.")
    args = parser.parse_args()
    researched = asyncio.run(backfill(force=args.force, dry_run=args.list, full_agent=args.full_agent))
    if not args.list:
        print(f"researched={researched}")


if __name__ == "__main__":
    main()
