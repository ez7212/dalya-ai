"""
Community Knowledge Base Re-Audit Worker

Runs daily and checks approved community KB files for staleness.
If a file's last_audited_at is 30+ days ago (or never audited),
runs a lightweight re-audit using Haiku + web search to detect
outdated prices, unit availability, or construction status.

Rate-limited to 3 communities per daily run to control API costs.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

import anthropic

from app.db.session import safe_commit, service_session
from app.models.db_models import DBCommunityResearch

logger = logging.getLogger(__name__)

# Haiku 4.5 — cheap and fast, good enough for diff detection
MODEL = "claude-haiku-4-5-20251001"
AUDIT_INTERVAL_SECONDS = int(os.getenv("AUDIT_INTERVAL_SECONDS", "604800"))    # 7 days
STARTUP_DELAY_SECONDS = 60        # let app boot before first run
STALE_THRESHOLD_DAYS = 30
MIN_COMMUNITIES_PER_RUN = 3
MAX_COMMUNITIES_PER_RUN = 15
KB_BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge_base")


async def run_audit_worker():
    """
    Daily worker that checks community KB files for staleness.
    If a file's last_audited_at is 30+ days ago (or never audited),
    runs a lightweight re-audit using Haiku + web search.
    """
    logger.info(
        f"Research audit worker started "
        f"(check every {AUDIT_INTERVAL_SECONDS}s, "
        f"stale threshold {STALE_THRESHOLD_DAYS} days, "
        f"max {MAX_COMMUNITIES_PER_RUN} per run)"
    )
    await asyncio.sleep(STARTUP_DELAY_SECONDS)

    while True:
        try:
            await _audit_stale_communities()
        except Exception as e:
            logger.error(f"Research audit worker error: {e}", exc_info=True)
        await asyncio.sleep(AUDIT_INTERVAL_SECONDS)


async def _audit_stale_communities():
    """Find approved KB records that are 30+ days old and re-audit them."""
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        logger.warning("TAVILY_API_KEY not set — skipping research audit")
        return

    cutoff = datetime.utcnow() - timedelta(days=STALE_THRESHOLD_DAYS)

    with service_session(is_platform_admin=True) as db:
        # Dynamic rate: audit enough per day to cover all communities within the
        # stale threshold window. At 90 communities, that's ceil(90/30) = 3/day.
        # At 300, ceil(300/30) = 10/day. Capped at MIN..MAX range.
        import math
        total_approved = db.query(DBCommunityResearch).filter_by(status="approved").count()
        communities_per_run = max(
            MIN_COMMUNITIES_PER_RUN,
            min(MAX_COMMUNITIES_PER_RUN, math.ceil(total_approved / STALE_THRESHOLD_DAYS)),
        )

        stale_records = (
            db.query(DBCommunityResearch)
            .filter(DBCommunityResearch.status == "approved")
            .filter(
                (DBCommunityResearch.last_audited_at.is_(None))
                | (DBCommunityResearch.last_audited_at < cutoff)
            )
            .order_by(DBCommunityResearch.last_audited_at.asc().nullsfirst())
            .limit(communities_per_run)
            .all()
        )

        if not stale_records:
            logger.info("No stale community KB records found (total approved: %d)", total_approved)
            return

        logger.info(
            "Auditing %d stale community KB records (rate: %d/day for %d total approved)",
            len(stale_records), communities_per_run, total_approved,
        )

        for record in stale_records:
            try:
                await _audit_single_community(db, record, tavily_key)
            except Exception as e:
                logger.error(
                    f"Failed to audit community KB {record.project_name}: {e}",
                    exc_info=True,
                )

        safe_commit(db)


async def _audit_single_community(db, record: DBCommunityResearch, tavily_key: str):
    """Run web search + Haiku comparison for a single community KB file."""
    # Read the current KB file
    if not record.file_path:
        logger.warning(f"Community KB {record.project_name} has no file_path — skipping")
        return

    kb_path = os.path.normpath(os.path.join(KB_BASE_DIR, record.file_path))
    if not os.path.exists(kb_path):
        logger.warning(f"KB file not found: {kb_path} — skipping")
        return

    with open(kb_path, "r") as f:
        kb_content = f.read()

    # Run targeted web searches via Tavily
    project = record.project_name
    developer = record.developer
    search_label = f"{project} {developer}"

    queries = [
        f'"{project}" latest price update 2026',
        f'"{project}" construction progress completion',
        f'"{project}" sold out available units',
        f'"{project}" property finder bayut new listings',
    ]

    search_results = await _run_tavily_searches(tavily_key, queries)

    if not search_results:
        logger.warning(f"No search results for {search_label} — skipping audit")
        record.last_audited_at = datetime.utcnow()
        return

    # Send to Haiku for comparison
    audit_result = await _compare_with_haiku(kb_content, search_results, search_label)

    if audit_result is None:
        return

    stale_fields = audit_result.get("stale_fields", [])
    now = datetime.utcnow()

    if stale_fields:
        record.status = "stale"
        record.audit_flags = stale_fields
        record.last_audited_at = now
        logger.warning(
            f"Community KB {project} has {len(stale_fields)} stale fields: "
            f"{', '.join(stale_fields[:5])}"
        )
    else:
        record.last_audited_at = now
        record.audit_flags = []
        logger.info(f"Community KB {project} is up to date")


async def _run_tavily_searches(tavily_key: str, queries: list[str]) -> str:
    """Run multiple Tavily searches and return combined results as text."""
    from tavily import TavilyClient

    client = TavilyClient(api_key=tavily_key)
    loop = asyncio.get_event_loop()
    all_results = []

    for query in queries:
        try:
            response = await loop.run_in_executor(
                None,
                lambda q=query: client.search(q, max_results=3),
            )
            results = response.get("results", [])
            for r in results:
                title = r.get("title", "")
                content = r.get("content", "")
                url = r.get("url", "")
                all_results.append(f"[{title}]({url})\n{content}")
        except Exception as e:
            logger.warning(f"Tavily search failed for '{query}': {e}")

    return "\n\n---\n\n".join(all_results)


async def _compare_with_haiku(
    kb_content: str, search_results: str, project_label: str
) -> dict | None:
    """Send KB + search results to Haiku for staleness comparison."""
    system_prompt = (
        "You are auditing a community knowledge base file for a Dubai real estate platform. "
        "Compare the existing data with the latest web search results. "
        "Identify fields that may be outdated — prices, unit availability, "
        "construction status, completion dates, etc.\n\n"
        "Return a JSON object with:\n"
        '- "stale_fields": list of field paths that appear to have changed (e.g. "pricing.avg_price_per_sqft")\n'
        '- "suggested_updates": dict mapping field_path to suggested new value\n'
        '- "confidence": float 0-1 indicating overall confidence in the staleness assessment\n'
        '- "summary": one paragraph describing what changed\n\n'
        "If nothing appears stale, return an empty stale_fields list. "
        "Output ONLY valid JSON, no markdown fences."
    )

    user_message = (
        f"## Current Knowledge Base for {project_label}\n\n"
        f"```json\n{kb_content[:8000]}\n```\n\n"
        f"## Latest Web Search Results\n\n{search_results[:6000]}"
    )

    try:
        client = anthropic.Anthropic()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            ),
        )

        raw = response.content[0].text.strip()
        # Strip markdown fences if present despite instructions
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3].rstrip()

        result = json.loads(raw)
        logger.info(
            f"Audit for {project_label} complete "
            f"(input: {response.usage.input_tokens}, "
            f"output: {response.usage.output_tokens}, "
            f"confidence: {result.get('confidence', '?')})"
        )
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Haiku returned invalid JSON for {project_label}: {e}")
        return None
    except Exception as e:
        logger.error(f"Haiku audit call failed for {project_label}: {e}", exc_info=True)
        return None
