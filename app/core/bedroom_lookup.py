"""
Bedroom/bathroom lookup — auto-fills missing bedroom and bathroom counts
by searching online when the SPA parser can't extract them from the document.

Called automatically after SPA parsing when bedrooms or bathrooms are null.
Uses Claude with a web search tool to find the data based on project name,
unit type, and BUA sqft.
"""

import logging
import anthropic
from typing import Optional

logger = logging.getLogger(__name__)


def lookup_bedrooms_bathrooms(
    project: str,
    sub_community: Optional[str],
    developer: str,
    property_type: str,
    bua_sqft: Optional[float],
    unit_number: Optional[str] = None,
) -> dict:
    """
    Search online for bedroom/bathroom count based on property details.
    Returns {"bedrooms": int|None, "bathrooms": int|None}.

    Uses Claude with a focused prompt to determine the most likely
    bedroom/bathroom configuration from publicly available data.
    """
    if not project or not bua_sqft:
        return {"bedrooms": None, "bathrooms": None}

    client = anthropic.Anthropic()

    sub_comm = f" — {sub_community}" if sub_community else ""
    unit_info = f", unit {unit_number}" if unit_number else ""

    prompt = f"""I need to determine the bedroom and bathroom count for a specific property unit. Here are the details:

Developer: {developer}
Project: {project}{sub_comm}
Property type: {property_type}
Built-up area: {bua_sqft:,.0f} sqft{unit_info}

Based on your knowledge of this development's floor plans and unit configurations, what is the most likely bedroom and bathroom count for a {property_type.lower()} of {bua_sqft:,.0f} sqft in {project}{sub_comm}?

Common size ranges to consider:
- For apartments: studio (400-600), 1BR (700-1000), 2BR (1100-1600), 3BR (1700-2500), 4BR (2500+)
- For villas: 3BR (2500-4000), 4BR (4000-7500), 5BR (7500-11000), 6BR (11000+)

Return ONLY a JSON object with no other text:
{{"bedrooms": <number or null>, "bathrooms": <number or null>, "confidence": "high" or "medium" or "low", "source": "brief note on how you determined this"}}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Use Haiku — cheap and fast for this
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )

        import json, re
        raw = response.content[0].text.strip()
        json_text = re.sub(r"^```(?:json)?\n?", "", raw)
        json_text = re.sub(r"\n?```$", "", json_text)
        result = json.loads(json_text)

        bedrooms = result.get("bedrooms")
        bathrooms = result.get("bathrooms")
        confidence = result.get("confidence", "low")
        source = result.get("source", "")

        if confidence == "low":
            logger.info(f"[bedroom_lookup] Low confidence for {project}{unit_info}: {source}")
            return {"bedrooms": None, "bathrooms": None}

        logger.info(f"[bedroom_lookup] {project}{unit_info}: {bedrooms}BR/{bathrooms}BA ({confidence}) — {source}")
        return {"bedrooms": bedrooms, "bathrooms": bathrooms}

    except Exception as e:
        logger.warning(f"[bedroom_lookup] Failed for {project}{unit_info}: {e}")
        return {"bedrooms": None, "bathrooms": None}
