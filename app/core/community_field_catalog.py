"""
Curated catalog of buyer-relevant community-research fields.

Maps a stable `key` (used by agent overrides — see DBAgentCommunityOverride)
to a human label, a UI group, and a dot-path into the community KB JSON. Stable
keys decouple agent overrides from the KB's nested shape: if the KB changes
structure or lacks a field, the override still resolves by key and the field
still renders (as "Not in research").
"""
from __future__ import annotations

from typing import Any, Optional


# (key, label, group, dot-path into the KB JSON)
COMMUNITY_FIELDS: list[dict[str, str]] = [
    # Overview
    {"key": "official_name", "label": "Official name", "group": "Overview", "path": "master_development.overview.official_name"},
    {"key": "developer", "label": "Developer", "group": "Overview", "path": "master_development.overview.developer"},
    {"key": "master_community", "label": "Master community", "group": "Overview", "path": "master_development.overview.master_community"},
    {"key": "status", "label": "Status", "group": "Overview", "path": "master_development.overview.status"},
    {"key": "completion_date", "label": "Completion date", "group": "Overview", "path": "master_development.overview.completion_date"},
    {"key": "total_units", "label": "Total units", "group": "Overview", "path": "master_development.overview.total_residential_units"},
    {"key": "property_types", "label": "Property types", "group": "Overview", "path": "master_development.overview.property_types"},
    {"key": "bedroom_configurations", "label": "Bedroom configurations", "group": "Overview", "path": "master_development.overview.bedroom_configurations"},
    {"key": "bua_range_sqft", "label": "BUA range (sqft)", "group": "Overview", "path": "master_development.overview.bua_range_sqft"},
    {"key": "freehold", "label": "Freehold", "group": "Overview", "path": "master_development.overview.freehold"},
    # Pricing & investment
    {"key": "resale_price_range", "label": "Current resale price range (AED)", "group": "Pricing & investment", "path": "master_development.investment_data.current_resale_price_range_aed"},
    {"key": "average_asking_price", "label": "Average asking price (AED)", "group": "Pricing & investment", "path": "master_development.investment_data.average_asking_price_aed"},
    {"key": "price_per_sqft", "label": "Price per sqft (AED)", "group": "Pricing & investment", "path": "master_development.investment_data.price_per_sqft_range_aed"},
    {"key": "rental_range", "label": "Rental range (AED/year)", "group": "Pricing & investment", "path": "master_development.investment_data.rental_range_aed_per_year"},
    {"key": "gross_roi", "label": "Estimated gross ROI", "group": "Pricing & investment", "path": "master_development.investment_data.estimated_gross_roi_percent"},
    {"key": "service_charge", "label": "Service charge (AED/sqft)", "group": "Pricing & investment", "path": "master_development.investment_data.service_charge_aed_per_sqft"},
    {"key": "golden_visa_eligible", "label": "Golden visa eligible", "group": "Pricing & investment", "path": "master_development.investment_data.golden_visa_eligible"},
    {"key": "launch_price", "label": "Original launch price (AED)", "group": "Pricing & investment", "path": "master_development.investment_data.original_launch_price_aed"},
    {"key": "active_sale_listings", "label": "Active sale listings", "group": "Pricing & investment", "path": "master_development.investment_data.active_sale_listings"},
    # Location
    {"key": "address", "label": "Address", "group": "Location", "path": "master_development.location_connectivity.address"},
    {"key": "highway_access", "label": "Highway access", "group": "Location", "path": "master_development.location_connectivity.highway_access"},
    {"key": "metro_access", "label": "Metro access", "group": "Location", "path": "master_development.location_connectivity.metro_access"},
    {"key": "drive_times", "label": "Drive times (min)", "group": "Location", "path": "master_development.location_connectivity.drive_times_minutes"},
    # Amenities
    {"key": "golf_course", "label": "Golf course", "group": "Amenities", "path": "master_development.shared_amenities.golf_course"},
    {"key": "amenities_note", "label": "Amenities summary", "group": "Amenities", "path": "master_development.shared_amenities.note"},
    # Nearby
    {"key": "schools", "label": "Nearby schools", "group": "Nearby", "path": "master_development.nearby_infrastructure.schools"},
    {"key": "healthcare", "label": "Nearby healthcare", "group": "Nearby", "path": "master_development.nearby_infrastructure.healthcare"},
    # Developer
    {"key": "developer_track_record", "label": "Developer track record", "group": "Developer", "path": "master_development.developer_profile.track_record"},
]

# Fast lookups
FIELD_BY_KEY: dict[str, dict[str, str]] = {f["key"]: f for f in COMMUNITY_FIELDS}


def _resolve_path(kb: dict[str, Any], path: str) -> Any:
    node: Any = kb
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def format_value(value: Any) -> Optional[str]:
    """Render a KB value as a readable single string for the review UI."""
    if value is None or value == "" or value == [] or value == {}:
        return None
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float, str)):
        return str(value)
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                # Prefer a name-ish field, else compact the dict.
                label = item.get("name") or item.get("school") or item.get("type") or None
                detail = item.get("distance_minutes") or item.get("distance") or item.get("rating")
                parts.append(f"{label}{f' ({detail})' if label and detail else ''}" if label else "; ".join(f"{k}: {v}" for k, v in item.items()))
            else:
                parts.append(str(item))
        return "; ".join(p for p in parts if p)
    if isinstance(value, dict):
        return "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in value.items() if v not in (None, "", [], {}))
    return str(value)


def resolve_fields(kb: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the catalog with each field's researched value resolved from `kb`."""
    out: list[dict[str, Any]] = []
    for field in COMMUNITY_FIELDS:
        raw = _resolve_path(kb, field["path"]) if isinstance(kb, dict) else None
        out.append({
            "key": field["key"],
            "label": field["label"],
            "group": field["group"],
            "researched_value": format_value(raw),
        })
    return out
