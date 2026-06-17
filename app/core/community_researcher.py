"""
Community Knowledge Base Researcher

Automated research engine that uses Claude Opus + Tavily web search to generate
structured community KB JSON files. Multi-round pipeline optimized for ACCURACY
over speed (~15-20 minutes per community):

  Round 1 — Broad discovery: 8 general queries, Opus extracts master-level data
  Round 2 — Gap fill: targeted queries for fields that came back null
  Round 3 — Sub-development deep dive: per-tower/phase/cluster research
  Round 4 — Source verification: cross-reference key claims against Property Finder + Bayut
  Round 5 — Self-audit: Opus reviews the full draft skeptically

Output lands in knowledge_base/needs_review/ for admin approval before going live.

Usage:
    researcher = CommunityResearcher()
    result = await researcher.research_community("The Oasis", "Emaar Properties")
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import anthropic
from tavily import TavilyClient

logger = logging.getLogger(__name__)


# ── Tavily search cache ──────────────────────────────────────────────────
# Caches search results by normalized query for 24 hours.
# Two communities in the same area share "schools near X" results.
# Re-research reuses recent results instead of re-fetching.

import hashlib
import time as _time

_search_cache: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL_SECONDS = 86400  # 24 hours


def _cache_key(query: str) -> str:
    """Normalize query to a stable cache key."""
    normalized = " ".join(query.lower().split())
    return hashlib.md5(normalized.encode()).hexdigest()


def _get_cached(query: str) -> list[dict] | None:
    """Return cached results if fresh, else None."""
    key = _cache_key(query)
    if key in _search_cache:
        ts, results = _search_cache[key]
        if _time.time() - ts < _CACHE_TTL_SECONDS:
            return results
        del _search_cache[key]
    return None


def _set_cached(query: str, results: list[dict]):
    """Cache search results."""
    key = _cache_key(query)
    _search_cache[key] = (_time.time(), results)

    # Evict oldest entries if cache grows too large (>500 queries)
    if len(_search_cache) > 500:
        oldest_key = min(_search_cache, key=lambda k: _search_cache[k][0])
        del _search_cache[oldest_key]


# ── Raw content sanitization ─────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<script[^>]*>[\s\S]*?</script>", re.IGNORECASE)
_STYLE_RE = re.compile(r"<style[^>]*>[\s\S]*?</style>", re.IGNORECASE)
_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
_INJECTION_LINE_RE = re.compile(
    r"^(ignore|system|you are|assistant|<\|im_start\||<\|im_end\|).*$",
    re.IGNORECASE | re.MULTILINE,
)
_WHITESPACE_COLLAPSE_RE = re.compile(r"\n{3,}")


def _sanitize_raw_content(text: str) -> str:
    """
    Strip HTML, script blocks, comments, and potential prompt injection lines
    from raw web content before feeding to Opus.
    """
    if not text:
        return ""
    text = _SCRIPT_RE.sub("", text)
    text = _STYLE_RE.sub("", text)
    text = _COMMENT_RE.sub("", text)
    text = _HTML_TAG_RE.sub("", text)
    text = _INJECTION_LINE_RE.sub("", text)
    text = _WHITESPACE_COLLAPSE_RE.sub("\n\n", text)
    return text.strip()

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_KNOWLEDGE_BASE_DIR = _PROJECT_ROOT / "knowledge_base"
_NEEDS_REVIEW_DIR = _KNOWLEDGE_BASE_DIR / "needs_review"
_SCHEMA_PATH = _KNOWLEDGE_BASE_DIR / "schema.json"


def _load_schema_text() -> str:
    """Load the canonical JSON schema as a string for prompt inclusion."""
    with open(_SCHEMA_PATH) as f:
        return f.read()


def _normalize_filename(developer: str, project_name: str) -> str:
    """
    Normalize to a safe filename: lowercase, spaces to underscores,
    strip special chars, e.g. 'Emaar Properties' + 'The Oasis' -> 'emaar_oasis.json'
    """
    dev_brand = developer.lower().split()[0]
    project = project_name.lower()
    project = re.sub(r"^the\s+", "", project)
    combined = f"{dev_brand}_{project}"
    combined = re.sub(r"[\s\-]+", "_", combined)
    combined = re.sub(r"[^a-z0-9_]", "", combined)
    combined = re.sub(r"_+", "_", combined).strip("_")
    return f"{combined}.json"


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences from an Opus response containing JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ── Example KB summary for research prompts ──────────────────────────────

_EXAMPLE_STRUCTURE = """
{
  "name": "The Oasis by Emaar",
  "developer": "Emaar Properties PJSC",
  "last_updated": "2026-03-27",
  "researcher_notes": ["Data compiled from ... Fields marked null require verification."],
  "master_development": {
    "overview": { "official_name": "...", "developer": "...", "launch_date": "...", "total_residential_units": 3100, "freehold": true, ... },
    "location_connectivity": { "drive_times_minutes": { "downtown_dubai_burj_khalifa": 20, ... }, ... },
    "shared_amenities": { "lagoons": { ... }, "cycling_track_km": 54, ... },
    "nearby_infrastructure": { "schools": [...], "healthcare": [...], "retail": [...] },
    "investment_data": { "price_range": {...}, "golden_visa_eligible": true, "projected_roi_range": "...", ... },
    "developer_profile": { "legal_name": "...", "track_record": "...", ... }
  },
  "sub_developments": {
    "palmiera": {
      "aliases": ["palmiera", "palmiera 1", "palmiera at the oasis"],
      "prompt_data_overrides": {
        "sub_community": "Palmiera",
        "investment_overrides": { "price_range_aed": "4,700,000 – 12,000,000", ... },
        "sales_talking_points": { "scarcity_argument": "...", ... }
      },
      "overview": { ... },
      "unit_mix": { ... }
    }
  },
  "sales_talking_points": {
    "development_level": { "headline_stats": "...", "scarcity_argument": "...", "lifestyle_pitch": "...", "investment_pitch": "...", "objection_handling": "..." },
    "per_sub_development": { "palmiera": { ... } }
  },
  "aliases": ["the oasis", "oasis emaar", "emaar oasis", "oasis by emaar", ...],
  "developer_keywords": ["emaar"],
  "prompt_data": {
    "developer": "Emaar Properties PJSC",
    "community": "The Oasis by Emaar",
    "location": { "area": "Dubailand, Dubai", "description": "...", "distances": { "downtown_dubai_burj_khalifa": 20, ... } },
    "community_amenities": ["Swimmable crystal lagoons", "54 km cycling track", ...],
    "nearby": { "schools": [...], "healthcare": [...], "retail": [...] },
    "investment": { "ownership": "Freehold", "golden_visa_eligible": true, "projected_roi_percent": "5 to 8", ... },
    "sales_talking_points": { "scarcity_argument": "...", "lifestyle_pitch": "...", "investment_pitch": "..." },
    "developer_track_record": "Emaar Properties PJSC is the developer of Burj Khalifa and Dubai Mall..."
  },
  "metadata": {
    "schema_version": "1.0",
    "last_researched_at": "2026-03-27T14:00:00Z",
    "last_audited_at": null,
    "research_confidence": 0.82,
    "source_urls": ["https://..."],
    "audit_flags": ["Tower C handover date conflict unresolved"]
  }
}
"""


class CommunityResearcher:
    """
    Automated community KB research engine — multi-round pipeline.

    Pipeline (5 rounds, ~15-20 minutes total):
    1. Broad discovery (Opus)  — 8 general queries → master-level data, schema synthesis
    2. Gap fill (Sonnet)       — targeted queries for null fields → structured slot filling
    3. Sub-dev deep dive (Sonnet, batched) — all sub-devs in one call → unit/price/BUA data
    4. Source verification (Sonnet) — Property Finder + Bayut cross-reference → price validation
    5. Self-audit (Opus)       — strongest model reviews weaker models' work → quality gate
    """

    # Model selection: Opus for synthesis/judgment, Sonnet for structured extraction
    MODEL_OPUS = "claude-opus-4-6"      # Rounds 1 (synthesis) and 5 (audit)
    MODEL_SONNET = "claude-sonnet-4-6"  # Rounds 2 (gap fill), 3 (sub-dev), 4 (verification)

    def __init__(self):
        self.anthropic = anthropic.Anthropic()
        self.tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    async def research_community(
        self,
        project_name: str,
        developer: str,
        sub_community: str | None = None,
    ) -> dict:
        """
        Full multi-round research pipeline.

        Returns:
            dict with keys: file_path, research_confidence, source_urls, audit_flags
        """
        logger.info(
            "Starting community research: project=%s, developer=%s, sub=%s",
            project_name, developer, sub_community,
        )

        all_source_urls: list[str] = []

        # ── Round 1: Broad discovery ──────────────────────────────────────
        logger.info("Round 1/5: Broad discovery searches")
        broad_queries = self._build_broad_queries(project_name, developer, sub_community)
        broad_results = await self._search_web(broad_queries)
        all_source_urls.extend(r["url"] for r in broad_results)
        logger.info("Round 1 complete: %d results from %d queries", len(broad_results), len(broad_queries))

        if not broad_results:
            raise ValueError(
                f"No web search results found for '{project_name}' by {developer}. "
                "Cannot proceed with research."
            )

        # Initial research pass — extract master-level data
        logger.info("Round 1: Research pass (Opus)...")
        draft = await self._research_pass(project_name, developer, sub_community, broad_results)
        logger.info(
            "Round 1 draft complete. Confidence: %s",
            draft.get("metadata", {}).get("research_confidence", "unknown"),
        )

        # ── Round 2: Gap fill ─────────────────────────────────────────────
        logger.info("Round 2/5: Gap-fill searches for null fields")
        null_fields = self._find_null_fields(draft)
        if null_fields:
            gap_queries = self._build_gap_fill_queries(project_name, developer, null_fields)
            gap_results = await self._search_web(gap_queries)
            all_source_urls.extend(r["url"] for r in gap_results)
            logger.info("Round 2: %d gap-fill results for %d null fields", len(gap_results), len(null_fields))

            if gap_results:
                draft = await self._gap_fill_pass(draft, project_name, gap_results, null_fields)
                logger.info("Round 2 gap-fill pass complete")
        else:
            logger.info("Round 2: No null fields found — skipping")

        # ── Round 3: Sub-development deep dive (batched into one Sonnet call) ─
        logger.info("Round 3/5: Sub-development deep dive")
        sub_devs = self._extract_sub_development_names(draft)
        if sub_devs:
            # Search for all sub-devs, then batch into one enrichment call
            all_sub_results: list[dict] = []
            for sub_name in sub_devs:
                logger.info("Round 3: Searching for sub-development '%s'", sub_name)
                sub_queries = self._build_sub_dev_queries(project_name, developer, sub_name)
                sub_results = await self._search_web(sub_queries)
                all_source_urls.extend(r["url"] for r in sub_results)
                all_sub_results.extend(sub_results)

            if all_sub_results:
                draft = await self._batched_sub_dev_enrichment(
                    draft, project_name, sub_devs, all_sub_results
                )
            logger.info("Round 3 complete: enriched %d sub-developments in one pass", len(sub_devs))
        else:
            logger.info("Round 3: No sub-developments identified — skipping")

        # ── Round 4: Source verification (Property Finder + Bayut) ────────
        logger.info("Round 4/5: Source verification via portal listings")
        verification_queries = [
            f'site:propertyfinder.ae "{project_name}" for sale',
            f'site:bayut.com "{project_name}" for sale',
            f'"{project_name}" {developer} DLD transaction prices 2024 2025',
            f'"{project_name}" resale secondary market price',
            f'"{project_name}" floor plan brochure unit types',
        ]
        verification_results = await self._search_web(verification_queries)
        all_source_urls.extend(r["url"] for r in verification_results)
        logger.info("Round 4: %d verification results", len(verification_results))

        if verification_results:
            draft = await self._verification_pass(draft, project_name, verification_results)
            logger.info("Round 4 verification pass complete")

        # ── Round 5: Self-audit ───────────────────────────────────────────
        logger.info("Round 5/5: Self-audit pass")
        # Combine all results for the audit context
        all_results = broad_results + (gap_results if null_fields and gap_results else [])
        all_results += verification_results if verification_results else []
        audited = await self._audit_pass(draft, project_name, all_results)

        # Stamp source URLs
        audited.setdefault("metadata", {})
        audited["metadata"]["source_urls"] = list(set(all_source_urls))

        audit_flags = audited.get("metadata", {}).get("audit_flags", [])
        logger.info("Round 5 complete. %d audit flags raised.", len(audit_flags))

        # ── Save draft ────────────────────────────────────────────────────
        file_path = self._save_draft(audited, project_name, developer)
        logger.info("Research complete. Draft saved to %s", file_path)

        return {
            "file_path": file_path,
            "research_confidence": audited.get("metadata", {}).get("research_confidence"),
            "source_urls": list(set(all_source_urls)),
            "audit_flags": audit_flags,
        }

    # ── Search query builders ─────────────────────────────────────────────

    def _build_broad_queries(
        self, project_name: str, developer: str, sub_community: str | None = None,
    ) -> list[str]:
        """Round 1: 8 broad discovery queries."""
        queries = [
            f'"{project_name}" {developer} Dubai overview units total',
            f'"{project_name}" Dubai amenities community features facilities',
            f'"{project_name}" Dubai payment plan off-plan prices 2024 2025',
            f'"{project_name}" Dubai location area map nearby schools hospitals',
            f'"{project_name}" property finder',
            f'"{project_name}" bayut',
            f'"{project_name}" construction update completion handover date',
            f'"{project_name}" {developer} ROI rental yield investment Dubai',
        ]
        if sub_community:
            queries.append(
                f'"{project_name}" "{sub_community}" {developer} Dubai units floor plan'
            )
        return queries

    def _build_gap_fill_queries(
        self, project_name: str, developer: str, null_fields: list[str],
    ) -> list[str]:
        """Round 2: Targeted queries for specific missing data."""
        field_query_map = {
            "total_residential_units": f'"{project_name}" {developer} total units number of villas apartments',
            "launch_date": f'"{project_name}" {developer} launch date announced year',
            "estimated_completion": f'"{project_name}" {developer} completion date handover timeline',
            "golden_visa": f'"{project_name}" Dubai golden visa eligible property value',
            "service_charge": f'"{project_name}" {developer} service charge per sqft annual',
            "parking": f'"{project_name}" parking spaces per unit',
            "schools": f'schools near "{project_name}" Dubai nursery international school',
            "healthcare": f'hospitals clinics near "{project_name}" Dubai healthcare',
            "retail": f'shopping malls retail near "{project_name}" Dubai',
            "price_per_sqft": f'"{project_name}" price per sqft AED average 2024 2025',
            "roi": f'"{project_name}" rental yield ROI return investment percentage',
            "plot_area": f'"{project_name}" {developer} masterplan total area acres sqft',
            "freehold": f'"{project_name}" freehold leasehold ownership Dubai',
        }

        queries = []
        for field in null_fields:
            for key, query in field_query_map.items():
                if key in field.lower():
                    queries.append(query)
                    break
            else:
                # Generic query for unmapped fields
                clean_field = field.replace("_", " ").replace(".", " ")
                queries.append(f'"{project_name}" {developer} {clean_field}')

        # Deduplicate and cap
        seen = set()
        unique = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique.append(q)
        return unique[:10]

    def _build_sub_dev_queries(
        self, project_name: str, developer: str, sub_name: str,
    ) -> list[str]:
        """Round 3: Per-sub-development research queries."""
        return [
            f'"{project_name}" "{sub_name}" {developer} units floor plan bedrooms',
            f'"{project_name}" "{sub_name}" price AED payment plan',
            f'"{project_name}" "{sub_name}" completion handover date construction',
            f'"{project_name}" "{sub_name}" features amenities',
        ]

    # ── Web search ────────────────────────────────────────────────────────

    async def _search_web(self, queries: list[str]) -> list[dict]:
        """Run multiple Tavily searches, return combined deduplicated results. Uses 24h cache."""
        loop = asyncio.get_event_loop()
        all_results: list[dict] = []
        seen_urls: set[str] = set()
        cache_hits = 0

        for i, query in enumerate(queries):
            try:
                # Check cache first
                cached = _get_cached(query)
                if cached is not None:
                    cache_hits += 1
                    for result in cached:
                        url = result.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(result)
                    continue

                logger.debug("Tavily search %d/%d: %s", i + 1, len(queries), query[:80])
                response = await loop.run_in_executor(
                    None,
                    lambda q=query: self.tavily.search(
                        query=q,
                        search_depth="advanced",
                        include_raw_content=True,
                        max_results=5,
                    ),
                )
                query_results: list[dict] = []
                for result in response.get("results", []):
                    url = result.get("url", "")
                    if url:
                        raw = _sanitize_raw_content(
                            (result.get("raw_content") or "")[:15000]
                        )[:10000]
                        sanitized = {
                            "url": url,
                            "title": result.get("title", ""),
                            "content": _sanitize_raw_content(result.get("content", "")),
                            "raw_content": raw,
                            "score": result.get("score", 0),
                        }
                        query_results.append(sanitized)
                        if url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(sanitized)

                # Cache the sanitized results
                _set_cached(query, query_results)

            except Exception as e:
                logger.warning("Tavily search failed for query '%s': %s", query[:60], e)
                continue

        if cache_hits:
            logger.info("Search cache: %d/%d queries served from cache", cache_hits, len(queries))

        all_results.sort(key=lambda r: r.get("score", 0), reverse=True)
        return all_results

    # ── Opus passes ───────────────────────────────────────────────────────

    async def _research_pass(
        self,
        project_name: str,
        developer: str,
        sub_community: str | None,
        web_results: list[dict],
    ) -> dict:
        """Round 1: Claude Opus analyzes web results and generates structured KB JSON."""
        schema_text = _load_schema_text()
        sources_text = self._format_web_results(web_results)

        sub_note = ""
        if sub_community:
            sub_note = (
                f"\nThe initial SPA is from sub-community '{sub_community}' within "
                f"{project_name}. Include this as a sub_development, but also research "
                f"ALL other known sub-developments/towers/phases.\n"
            )

        prompt = f"""You are a Dubai real estate research analyst building a structured community knowledge base file for the Dalya AI property advisor — an AI-powered off-plan resale marketplace.

YOUR TASK: Analyse the web search results below and produce a single, complete JSON object that conforms to the Dalya AI community knowledge base schema.

PROJECT TO RESEARCH:
- Project name: {project_name}
- Developer: {developer}
{sub_note}
CANONICAL JSON SCHEMA (your output MUST conform to this):
{schema_text}

EXAMPLE OF A COMPLETED KB FILE (abbreviated — shows the expected structure and depth):
{_EXAMPLE_STRUCTURE}

WEB SEARCH RESULTS (your primary source data):
{sources_text}

CRITICAL INSTRUCTIONS:
1. Return ONLY valid JSON — no markdown, no commentary, no explanation outside the JSON.
2. Return null for ANY field you cannot verify from the provided sources. Do NOT hallucinate or invent data.
3. aliases MUST include:
   - The project name in various forms (with/without "The", with/without developer name)
   - Common misspellings and abbreviations buyers might use on WhatsApp
   - All sub-development/tower/phase names
   - At minimum 8-12 aliases for good matching
4. sub_developments should capture EVERY known tower, phase, cluster, or villa type — not just the one from the SPA. Each needs its own aliases and prompt_data_overrides.
5. All prices MUST be in AED. All areas MUST be in sqft.
6. investment data should include: price ranges, price per sqft, ROI estimates, comparable projects, golden visa eligibility, service charge estimates.
7. developer_keywords should contain the developer brand name in lowercase, e.g. ["emaar"], ["sobha"].
8. Include detailed researcher_notes listing:
   - Where each major data point came from
   - What couldn't be verified
   - Confidence level per section
   - Any contradictions between sources
9. metadata MUST include:
   - schema_version: "1.0"
   - last_researched_at: current ISO datetime
   - research_confidence: 0-1 reflecting overall data quality
   - source_urls: URLs you actually used
   - audit_flags: [] (populated later)
10. prompt_data is the MOST IMPORTANT section — it directly feeds the AI advisor chatbot. Make it thorough with specific numbers, not vague descriptions.
11. sales_talking_points need to be factual and compelling with specific AED figures, percentage gains, and comparable benchmarks.
12. For each sub-development, include: unit types, bedroom configurations, BUA ranges, price ranges, completion dates, unique features.

Produce the complete JSON now."""

        return await self._call_claude(prompt, model=self.MODEL_OPUS)

    async def _gap_fill_pass(
        self, draft: dict, project_name: str, gap_results: list[dict], null_fields: list[str],
    ) -> dict:
        """Round 2: Fill in null fields using targeted search results."""
        sources_text = self._format_web_results(gap_results)
        draft_text = json.dumps(draft, indent=2, ensure_ascii=False)

        prompt = f"""You are enriching a community knowledge base file for the Dalya AI property advisor.

The initial research pass produced the draft below, but these fields are null or incomplete:
{json.dumps(null_fields, indent=2)}

CURRENT DRAFT:
{draft_text}

NEW SEARCH RESULTS (targeted at the missing data):
{sources_text}

INSTRUCTIONS:
1. Return the COMPLETE updated JSON with null fields filled in where the new sources provide data.
2. Only update fields where the new sources provide VERIFIED information. Keep nulls for anything still unverified.
3. Update researcher_notes to document what was filled in this pass and from which source.
4. Update metadata.research_confidence if the fill improves overall quality.
5. Do NOT remove or change data that was already correctly populated.
6. Return ONLY valid JSON — no markdown, no commentary.

Return the enriched JSON now."""

        return await self._call_claude(prompt, model=self.MODEL_SONNET, fallback=draft)

    async def _batched_sub_dev_enrichment(
        self, draft: dict, project_name: str, sub_names: list[str], all_sub_results: list[dict],
    ) -> dict:
        """Round 3: Enrich ALL sub-developments in one Sonnet call (batched)."""
        sources_text = self._format_web_results(all_sub_results)
        draft_text = json.dumps(draft, indent=2, ensure_ascii=False)
        sub_list = ", ".join(f'"{s}"' for s in sub_names)

        prompt = f"""You are enriching ALL sub-developments in a community knowledge base file for the Dalya AI property advisor.

CURRENT DRAFT:
{draft_text}

SUB-DEVELOPMENTS TO ENRICH: {sub_list}

WEB SEARCH RESULTS (covering all sub-developments above):
{sources_text}

INSTRUCTIONS:
1. Return the COMPLETE updated JSON (entire file).
2. For EACH sub-development listed above, enrich with:
   - Unit types and bedroom configurations (1BR, 2BR, 3BR, etc.) with BUA sqft ranges
   - Price ranges per unit type in AED
   - Total units in this sub-development
   - Completion/handover date
   - Unique features or selling points
   - Floor count, height if available
   - Aliases including common abbreviations and misspellings
3. If a sub-development doesn't exist in the draft yet, create it under sub_developments.
4. Do NOT modify master-level data unless correcting a clear error.
5. Update researcher_notes for each sub-development with source attribution.
6. Return null for any sub-development field that cannot be verified from the provided sources.
7. Return ONLY valid JSON — no markdown, no commentary.

Return the enriched JSON now."""

        return await self._call_claude(prompt, model=self.MODEL_SONNET, fallback=draft)

    async def _verification_pass(
        self, draft: dict, project_name: str, verification_results: list[dict],
    ) -> dict:
        """Round 4: Cross-reference key claims against portal listings and DLD data."""
        sources_text = self._format_web_results(verification_results)
        draft_text = json.dumps(draft, indent=2, ensure_ascii=False)

        prompt = f"""You are verifying a community knowledge base file for the Dalya AI property advisor against real listing data from Property Finder, Bayut, and DLD transaction records.

CURRENT DRAFT:
{draft_text}

VERIFICATION SOURCES (Property Finder listings, Bayut listings, DLD data):
{sources_text}

YOUR VERIFICATION CHECKLIST:
1. PRICES: Do the price ranges in the draft match what's listed on Property Finder/Bayut? If portal prices are significantly different, update the draft with a note.
2. UNIT TYPES: Are all unit configurations (1BR, 2BR, etc.) in the draft reflected in portal listings? Any missing types?
3. AVAILABILITY: Are any sub-developments/phases marked as available but showing no listings? Could indicate sold-out status.
4. PRICE PER SQFT: Cross-check against portal listing calculations.
5. BUA RANGES: Do the listed BUA sqft ranges match the draft?
6. COMPLETION DATES: Any updates from recent listings about handover timelines?

INSTRUCTIONS:
1. Return the COMPLETE updated JSON with corrections applied.
2. For any field you corrected, add a note in researcher_notes explaining the source of the correction.
3. Add a "verification_status" field to researcher_notes: "verified", "partially_verified", or "unverified" for key data points.
4. Do NOT remove data — only correct or add.
5. Return ONLY valid JSON — no markdown, no commentary.

Return the verified JSON now."""

        return await self._call_claude(prompt, model=self.MODEL_SONNET, fallback=draft)

    async def _audit_pass(
        self, draft: dict, project_name: str, web_results: list[dict],
    ) -> dict:
        """Round 5: Self-audit — Opus reviews the full draft skeptically."""
        sources_text = self._format_web_results(web_results[:25])
        draft_text = json.dumps(draft, indent=2, ensure_ascii=False)

        prompt = f"""You are an independent auditor reviewing a community knowledge base file for the Dalya AI property advisor (a Dubai off-plan resale marketplace).

This file has gone through 4 rounds of research. Your job is the FINAL quality check before human review.

DRAFT KB FILE TO AUDIT:
{draft_text}

ORIGINAL WEB SEARCH RESULTS (for cross-referencing):
{sources_text}

YOUR AUDIT CHECKLIST:
1. Internal contradictions — do numbers in master_development match prompt_data? Do sub-development details contradict the overview? Do unit count sums add up to the total?
2. Math errors — price ranges consistent? Percentages add up? BUA ranges make sense for the unit types?
3. Null fields that should be filled — is data available in the sources but was missed in earlier rounds?
4. Claims not supported by sources — flag any data point that cannot be traced to the provided search results. Be specific about which claims lack sources.
5. Stale/outdated information — flag data referencing old dates or likely-changed figures.
6. Aliases completeness — are there enough aliases (8+)? Are common misspellings included? Do sub-developments have their own aliases?
7. prompt_data quality — is it thorough enough for an AI advisor to give useful, specific answers? Does it include actual AED figures, not vague descriptions?
8. sales_talking_points — are they factual with specific numbers? Would a buyer find them compelling?
9. sub_developments — does each one have: aliases, unit types, price ranges, completion dates, BUA ranges?
10. researcher_notes — are gaps and caveats properly documented?

INSTRUCTIONS:
1. Return the CORRECTED JSON object with all fixes applied.
2. In metadata.audit_flags, list EVERY issue you found — both issues you FIXED and issues that NEED HUMAN REVIEW.
3. Format audit_flags as specific, actionable items, e.g.:
   - "FIXED: Tower A unit count was 323 but sources show 310 — corrected"
   - "NEEDS REVIEW: Tower C completion date conflicts between sources (2027 vs 2028)"
   - "UNVERIFIED: ROI figure of 7.2% has no source — may be hallucinated"
4. Update metadata.research_confidence based on your final assessment.
5. Return ONLY valid JSON — no markdown, no commentary outside the JSON.
6. Do NOT remove null values that are genuinely unknown — leave them null and note in audit_flags.

Return the audited JSON now."""

        return await self._call_claude(prompt, model=self.MODEL_OPUS, fallback=draft)

    # ── Helpers ───────────────────────────────────────────────────────────

    async def _call_claude(
        self, prompt: str, model: str | None = None, fallback: dict | None = None,
    ) -> dict:
        """Call Claude and parse JSON response. Falls back to provided dict on parse failure."""
        model = model or self.MODEL_OPUS
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.anthropic.messages.create(
                model=model,
                max_tokens=16000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            ),
        )

        raw_text = response.content[0].text
        json_text = _strip_json_fences(raw_text)
        model_short = "opus" if "opus" in model else "sonnet"

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse %s JSON response: %s", model_short, e)
            logger.debug("Raw response (first 2000 chars): %s", raw_text[:2000])
            repaired = await self._repair_json_response(raw_text, model=model, parse_error=e)
            if repaired is not None:
                logger.info("Repaired %s JSON response after parse failure", model_short)
                return repaired
            if fallback is not None:
                logger.warning("Falling back to previous draft due to %s JSON parse failure", model_short)
                fallback.setdefault("metadata", {})
                fallback["metadata"].setdefault("audit_flags", [])
                fallback["metadata"]["audit_flags"].append(
                    f"{model_short} JSON parse failure in one pass: {e}"
                )
                return fallback
            raise ValueError(f"Claude {model_short} returned invalid JSON: {e}") from e

    async def _repair_json_response(
        self,
        raw_text: str,
        model: str,
        parse_error: json.JSONDecodeError,
    ) -> dict | None:
        """Ask the model once to repair malformed JSON before falling back."""
        repair_prompt = f"""Repair this malformed JSON response.

Return ONLY one complete valid JSON object. Do not summarize, do not add markdown,
and do not change factual content except where required to make the JSON valid.

Parse error:
{parse_error}

Malformed JSON:
{raw_text}
"""
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.anthropic.messages.create(
                    model=model,
                    max_tokens=20000,
                    temperature=0,
                    messages=[{"role": "user", "content": repair_prompt}],
                ),
            )
            repaired_text = _strip_json_fences(response.content[0].text)
            return json.loads(repaired_text)
        except Exception as repair_error:
            logger.error("JSON repair failed: %s", repair_error)
            return None

    def _find_null_fields(self, draft: dict, prefix: str = "") -> list[str]:
        """Recursively find null or empty fields in the draft for gap-fill targeting."""
        null_fields = []
        # Key fields we care about filling
        important_keys = {
            "total_residential_units", "launch_date", "estimated_completion",
            "freehold", "golden_visa_eligible", "service_charge_per_sqft",
            "price_range", "price_per_sqft", "projected_roi_range",
            "schools", "healthcare", "retail", "drive_times_minutes",
            "unit_mix", "total_units", "completion_date", "floor_count",
        }

        if isinstance(draft, dict):
            for key, value in draft.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if value is None and key in important_keys:
                    null_fields.append(full_key)
                elif isinstance(value, dict):
                    null_fields.extend(self._find_null_fields(value, full_key))
                elif isinstance(value, list) and len(value) == 0 and key in important_keys:
                    null_fields.append(full_key)
        return null_fields[:15]  # Cap to avoid too many gap-fill queries

    def _extract_sub_development_names(self, draft: dict) -> list[str]:
        """Extract sub-development names from the draft for Round 3 deep dive."""
        sub_devs = draft.get("sub_developments", {})
        if not isinstance(sub_devs, dict):
            return []
        # Filter out null entries
        return [name for name, data in sub_devs.items() if data is not None]

    def _validate_against_schema(self, data: dict) -> list[str]:
        """Validate data against the canonical schema. Returns list of errors (empty = valid)."""
        try:
            import jsonschema
            schema = json.loads(_load_schema_text())
            jsonschema.validate(data, schema)
            return []
        except jsonschema.ValidationError as e:
            return [f"Schema validation: {e.message} (at {'.'.join(str(p) for p in e.absolute_path)})"]
        except Exception as e:
            return [f"Schema validation failed to run: {e}"]

    def _save_draft(self, data: dict, project_name: str, developer: str) -> str:
        """Save to knowledge_base/needs_review/. Returns relative path from knowledge_base/."""
        _NEEDS_REVIEW_DIR.mkdir(parents=True, exist_ok=True)

        filename = _normalize_filename(developer, project_name)
        file_path = _NEEDS_REVIEW_DIR / filename

        data.setdefault("metadata", {})
        data["metadata"]["schema_version"] = "1.0"
        if not data["metadata"].get("last_researched_at"):
            data["metadata"]["last_researched_at"] = (
                datetime.now(timezone.utc).isoformat()
            )

        # Validate against canonical schema — log warnings but don't block save
        schema_errors = self._validate_against_schema(data)
        if schema_errors:
            logger.warning("Draft has schema issues: %s", schema_errors)
            data["metadata"].setdefault("audit_flags", [])
            data["metadata"]["audit_flags"].extend(schema_errors)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        relative_path = f"needs_review/{filename}"
        logger.info("Saved draft KB file: %s", file_path)
        return relative_path

    def _format_web_results(self, results: list[dict]) -> str:
        """Format web results into a readable text block for prompts."""
        parts = []
        for i, r in enumerate(results, 1):
            content = r.get("raw_content") or r.get("content", "")
            if len(content) > 8000:
                content = content[:8000] + "\n... [truncated]"
            parts.append(
                f"--- SOURCE {i} ---\n"
                f"URL: {r['url']}\n"
                f"Title: {r['title']}\n"
                f"Content:\n{content}\n"
            )
        return "\n".join(parts)
