"""
Live, on-demand location intelligence (Google Places New + Routes).

When a buyer asks about a commute to a named destination, or a specific nearby
POI (e.g. an IB school, a hospital, the nearest metro) that we don't already
have in the listing's stored enrichment, we look it up live ONCE, persist it
into the same enrichment store the prompt reads from (DBListingAmenity /
DBListingAnchorTime), and answer this turn. The next buyer who asks the same
thing is served from cache with no API call.

Cache-first → live on miss → persist → reuse. All network failures degrade
gracefully (return None / []), so callers can fall back to the normal
info-gap escalation rather than guessing.

Requires GOOGLE_MAPS_API_KEY (Places API New + Routes API). When the key is
absent, `live_enabled()` is False and every live entrypoint is a no-op, so the
harness fixture path is unaffected.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.listing_enrichment import AmenityFact, AnchorTimeFact, normalize_school_name
from app.models.db_models import (
    DBEnrichmentRun,
    DBKHDASchool,
    DBListing,
    DBListingAmenity,
    DBListingAnchorTime,
)

logger = logging.getLogger(__name__)

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

_PLACES_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location,"
    "places.primaryType,places.types,places.rating,places.businessStatus"
)
_ROUTES_FIELD_MASK = "routes.duration,routes.distanceMeters"

_DEFAULT_RADIUS_M = 20000.0
_HTTP_TIMEOUT_S = 12.0


# ── Config ──────────────────────────────────────────────────────────────────

def _api_key() -> Optional[str]:
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    return key.strip() if key else None


def live_enabled() -> bool:
    """Live lookups fire only when a key is present and not explicitly disabled."""
    if os.getenv("LOCATION_LOOKUP_ENABLED", "1") == "0":
        return False
    return bool(_api_key())


# ── Normalisation ───────────────────────────────────────────────────────────

_CATEGORY_PRIMARY_TYPE = {
    "school": "school",
    "nursery": "preschool",
    "healthcare": "hospital",
    "transit": "subway_station",
    "supermarket": "supermarket",
    "retail": "shopping_mall",
}


def anchor_key_for(destination_text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (destination_text or "").lower()).strip("_")
    return slug or "destination"


def _origin_query(listing: DBListing) -> str:
    spa = getattr(listing, "spa_data", None) or {}
    imported = spa.get("imported_listing") or {}
    parts = [
        spa.get("sub_community"),
        spa.get("project") or imported.get("title"),
        imported.get("community") or getattr(listing, "community", None),
        "Dubai",
    ]
    seen: list[str] = []
    for p in parts:
        p = str(p or "").strip()
        if p and p.lower() not in {s.lower() for s in seen}:
            seen.append(p)
    return ", ".join(seen) or "Dubai"


# ── Google HTTP ─────────────────────────────────────────────────────────────

def _places_text_search(
    text_query: str,
    *,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_m: float = _DEFAULT_RADIUS_M,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    key = _api_key()
    if not key:
        return []
    body: dict[str, Any] = {
        "textQuery": text_query,
        "maxResultCount": max(1, min(max_results, 10)),
        "languageCode": "en",
        "regionCode": "AE",
    }
    if lat is not None and lng is not None:
        body["locationBias"] = {
            "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radius_m)}
        }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": _PLACES_FIELD_MASK,
    }
    try:
        resp = httpx.post(PLACES_SEARCH_URL, json=body, headers=headers, timeout=_HTTP_TIMEOUT_S)
        resp.raise_for_status()
        return resp.json().get("places", []) or []
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("places_text_search failed for %r: %s", text_query[:60], exc)
        return []


def _route_drive(
    origin: tuple[float, float],
    *,
    dest_latlng: Optional[tuple[float, float]] = None,
    dest_address: Optional[str] = None,
) -> Optional[dict[str, float]]:
    """Return {'drive_min': float, 'distance_km': float} or None."""
    key = _api_key()
    if not key:
        return None
    if dest_latlng is None and not dest_address:
        return None
    destination = (
        {"location": {"latLng": {"latitude": dest_latlng[0], "longitude": dest_latlng[1]}}}
        if dest_latlng is not None
        else {"address": dest_address}
    )
    body = {
        "origin": {"location": {"latLng": {"latitude": origin[0], "longitude": origin[1]}}},
        "destination": destination,
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": _ROUTES_FIELD_MASK,
    }
    try:
        resp = httpx.post(ROUTES_URL, json=body, headers=headers, timeout=_HTTP_TIMEOUT_S)
        resp.raise_for_status()
        routes = resp.json().get("routes", []) or []
        if not routes:
            return None
        dur = routes[0].get("duration", "0s")
        seconds = float(str(dur).rstrip("s") or 0)
        meters = float(routes[0].get("distanceMeters", 0) or 0)
        if seconds <= 0:
            return None
        return {"drive_min": round(seconds / 60.0, 1), "distance_km": round(meters / 1000.0, 1)}
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("compute_routes failed: %s", exc)
        return None


# ── Origin (geocode once, cache on the listing) ─────────────────────────────

def origin_latlng(db: Session, listing: DBListing) -> Optional[tuple[float, float]]:
    stages = dict(getattr(listing, "processing_stages", None) or {})
    cached = stages.get("geo_origin")
    if isinstance(cached, dict) and cached.get("lat") is not None and cached.get("lng") is not None:
        return float(cached["lat"]), float(cached["lng"])
    if not live_enabled():
        return None
    places = _places_text_search(_origin_query(listing), max_results=1)
    if not places:
        return None
    loc = (places[0] or {}).get("location") or {}
    lat, lng = loc.get("latitude"), loc.get("longitude")
    if lat is None or lng is None:
        return None
    stages["geo_origin"] = {
        "lat": float(lat),
        "lng": float(lng),
        "query": _origin_query(listing),
        "at": datetime.utcnow().isoformat(),
    }
    listing.processing_stages = stages
    try:
        db.add(listing)
        db.flush()
    except SQLAlchemyError:
        db.rollback()
    return float(lat), float(lng)


# ── Cache reads (latest profile version) ────────────────────────────────────

def _latest_version(db: Session, listing_id: str) -> int:
    latest = (
        db.query(func.max(DBListingAmenity.profile_version))
        .filter(DBListingAmenity.listing_id == listing_id)
        .scalar()
    ) or 0
    latest_anchor = (
        db.query(func.max(DBListingAnchorTime.profile_version))
        .filter(DBListingAnchorTime.listing_id == listing_id)
        .scalar()
    ) or 0
    return int(max(latest, latest_anchor))


def cached_amenities(
    db: Session, listing_id: str, *, category: Optional[str] = None
) -> list[DBListingAmenity]:
    version = _latest_version(db, listing_id)
    if version == 0:
        return []
    q = db.query(DBListingAmenity).filter(
        DBListingAmenity.listing_id == listing_id,
        DBListingAmenity.profile_version == version,
    )
    if category:
        q = q.filter(DBListingAmenity.category == category)
    return q.order_by(DBListingAmenity.drive_time_min.asc().nullslast()).all()


def cached_anchor(db: Session, listing_id: str, anchor_key: str) -> Optional[DBListingAnchorTime]:
    version = _latest_version(db, listing_id)
    if version == 0:
        return None
    return (
        db.query(DBListingAnchorTime)
        .filter(
            DBListingAnchorTime.listing_id == listing_id,
            DBListingAnchorTime.profile_version == version,
            DBListingAnchorTime.anchor_key == anchor_key,
        )
        .first()
    )


# ── Persistence (append at latest version, never a new one) ─────────────────

def _persist_version(db: Session, listing_id: str) -> int:
    """Append into the latest existing profile version so live results sit
    alongside fixtures and BOTH are read by latest_listing_enrichment. If the
    listing has no enrichment yet, start at version 1."""
    return _latest_version(db, listing_id) or 1


def _record_run(db: Session, listing_id: str, version: int, places_calls: int, routes_calls: int) -> None:
    db.add(
        DBEnrichmentRun(
            listing_id=listing_id,
            profile_version=version,
            provider="google_live",
            mode="on_demand",
            sku_usage={
                "places_text_search": {"sku": "non_enterprise", "live_calls": places_calls},
                "routes_compute_routes": {"sku": "non_enterprise", "live_calls": routes_calls},
            },
            status="complete",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            metadata_json={"source": "google_live", "on_demand": True},
        )
    )


def _persist_amenities(db: Session, listing_id: str, facts: list[AmenityFact], routes_calls: int) -> None:
    if not facts:
        return
    version = _persist_version(db, listing_id)
    existing = {
        (a.category, (a.name or "").lower(), a.source, a.status)
        for a in cached_amenities(db, listing_id)
    }
    added = 0
    for fact in facts:
        key = (fact.category, (fact.name or "").lower(), fact.source, fact.status)
        if key in existing:
            continue
        existing.add(key)
        db.add(DBListingAmenity(listing_id=listing_id, profile_version=version, **asdict(fact)))
        added += 1
    if added:
        _record_run(db, listing_id, version, places_calls=1, routes_calls=routes_calls)


def _persist_anchor(db: Session, listing_id: str, anchor: AnchorTimeFact) -> None:
    version = _persist_version(db, listing_id)
    if cached_anchor(db, listing_id, anchor.anchor_key):
        return
    db.add(DBListingAnchorTime(listing_id=listing_id, profile_version=version, **asdict(anchor)))
    _record_run(db, listing_id, version, places_calls=0, routes_calls=1)


# ── Public lookups (cache-first, live on miss) ──────────────────────────────

def lookup_commute(db: Session, listing: DBListing, destination_text: str) -> Optional[AnchorTimeFact]:
    """Drive time from the listing to a named destination. Cache-first."""
    key = anchor_key_for(destination_text)
    hit = cached_anchor(db, listing.listing_id, key)
    if hit and hit.drive_time_min:
        return AnchorTimeFact(
            anchor_key=hit.anchor_key,
            anchor_name=hit.anchor_name,
            drive_time_min=hit.drive_time_min,
            distance_km=hit.distance_km,
            source=hit.source,
            metadata_json={"cached": True},
        )
    if not live_enabled():
        return None
    origin = origin_latlng(db, listing)
    if not origin:
        return None
    route = _route_drive(origin, dest_address=f"{destination_text}, Dubai")
    if not route:
        return None
    fact = AnchorTimeFact(
        anchor_key=key,
        anchor_name=destination_text.strip(),
        drive_time_min=route["drive_min"],
        distance_km=route["distance_km"],
        source="google_routes",
        metadata_json={"on_demand": True, "routing": "TRAFFIC_AWARE"},
    )
    _persist_anchor(db, listing.listing_id, fact)
    return fact


def lookup_pois(
    db: Session,
    listing: DBListing,
    *,
    category: str,
    text_query: str,
    curriculum: Optional[str] = None,
    max_results: int = 4,
) -> list[AmenityFact]:
    """Find nearby POIs of a category (optionally curriculum-filtered for
    schools). Cache-first: if a satisfying record already exists, return [] so
    the caller lets the normal (LLM) path answer from the stored prompt data."""
    cached = cached_amenities(db, listing.listing_id, category=category)
    if curriculum:
        want = curriculum.lower()
        if any(want in (c.curriculum or "").lower() for c in cached):
            return []  # already covered → no live call
    elif cached:
        return []  # category already covered

    if not live_enabled():
        return []
    origin = origin_latlng(db, listing)
    places = _places_text_search(
        text_query,
        lat=origin[0] if origin else None,
        lng=origin[1] if origin else None,
        max_results=max_results,
    )
    if not places:
        return []

    facts: list[AmenityFact] = []
    routes_calls = 0
    primary = _CATEGORY_PRIMARY_TYPE.get(category, category)
    for place in places[:max_results]:
        name = ((place.get("displayName") or {}).get("text") or "").strip()
        if not name:
            continue
        if str(place.get("businessStatus", "OPERATIONAL")).upper() not in {"OPERATIONAL", ""}:
            continue
        loc = place.get("location") or {}
        plat, plng = loc.get("latitude"), loc.get("longitude")
        drive_min = None
        dist_km = None
        if origin and plat is not None and plng is not None:
            route = _route_drive(origin, dest_latlng=(float(plat), float(plng)))
            routes_calls += 1
            if route:
                drive_min = route["drive_min"]
                dist_km = route["distance_km"]
        khda = _khda_lookup(db, name)
        facts.append(
            AmenityFact(
                category=category,
                name=name,
                source="google_places",
                status="existing",
                primary_type=place.get("primaryType") or primary,
                google_place_id=place.get("id"),
                latitude=float(plat) if plat is not None else None,
                longitude=float(plng) if plng is not None else None,
                straight_line_m=(dist_km * 1000.0) if dist_km is not None else None,
                drive_time_min=drive_min,
                khda_rating=(khda or {}).get("rating"),
                khda_rating_year=(khda or {}).get("rating_year"),
                curriculum=(khda or {}).get("curriculum") or (curriculum.upper() if curriculum else None),
                match_confidence=0.95 if khda else (0.6 if curriculum else 0.8),
                metadata_json={
                    "on_demand": True,
                    "search_query": text_query,
                    "curriculum_from": "khda" if khda and khda.get("curriculum") else ("search_term" if curriculum else None),
                    "rating": place.get("rating"),
                    "formatted_address": place.get("formattedAddress"),
                },
            )
        )
    _persist_amenities(db, listing.listing_id, facts, routes_calls=routes_calls)
    return facts


def _khda_lookup(db: Session, name: str) -> Optional[dict[str, Any]]:
    try:
        row = (
            db.query(DBKHDASchool)
            .filter(DBKHDASchool.normalized_name == normalize_school_name(name))
            .first()
        )
    except SQLAlchemyError:
        return None
    if not row:
        return None
    return {"rating": row.rating, "rating_year": row.rating_year, "curriculum": row.curriculum}
