from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.db_models import (
    DBEnrichmentRun,
    DBKHDASchool,
    DBListing,
    DBListingAmenity,
    DBListingAnchorTime,
)

GOOGLE_PLACES_FIELD_MASK = (
    "places.id",
    "places.displayName",
    "places.location",
    "places.primaryType",
)


@dataclass(frozen=True)
class AmenityFact:
    category: str
    name: str
    source: str = "google_places"
    status: str = "existing"
    primary_type: str | None = None
    google_place_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    straight_line_m: float | None = None
    drive_time_min: float | None = None
    walk_time_min: float | None = None
    khda_rating: str | None = None
    khda_rating_year: int | None = None
    curriculum: str | None = None
    match_confidence: float | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnchorTimeFact:
    anchor_key: str
    anchor_name: str
    drive_time_min: float
    distance_km: float | None = None
    source: str = "google_routes"
    metadata_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnrichmentProfile:
    profile_key: str
    source_url_hint: str
    amenities: tuple[AmenityFact, ...]
    anchor_times: tuple[AnchorTimeFact, ...]
    metadata_json: dict[str, Any] = field(default_factory=dict)


def normalize_school_name(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", (name or "").lower())
    value = re.sub(r"\b(?:llc|school|academy|college|dubai|the)\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _place_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"harness-google-place:{slug}"


def _g(
    category: str,
    name: str,
    *,
    primary_type: str,
    drive: float,
    lat: float | None = None,
    lng: float | None = None,
    distance_m: float | None = None,
    walk: float | None = None,
    khda_rating: str | None = None,
    khda_rating_year: int | None = None,
    curriculum: str | None = None,
    match_confidence: float | None = None,
) -> AmenityFact:
    metadata: dict[str, Any] = {
        "field_mask": list(GOOGLE_PLACES_FIELD_MASK),
        "sku": "places_text_search_non_enterprise",
        "fixture": True,
    }
    if khda_rating:
        metadata["khda_match_method"] = "normalized_name_geo_threshold"
    return AmenityFact(
        category=category,
        name=name,
        source="google_places",
        status="existing",
        primary_type=primary_type,
        google_place_id=_place_id(name),
        latitude=lat,
        longitude=lng,
        straight_line_m=distance_m,
        drive_time_min=drive,
        walk_time_min=walk,
        khda_rating=khda_rating,
        khda_rating_year=khda_rating_year,
        curriculum=curriculum,
        match_confidence=match_confidence,
        metadata_json=metadata,
    )


def _planned(category: str, name: str, *, status_note: str) -> AmenityFact:
    return AmenityFact(
        category=category,
        name=name,
        source="developer_brochure",
        status="planned",
        metadata_json={"status_note": status_note, "fixture": True},
    )


def _anchor(key: str, name: str, drive: float, distance: float | None = None) -> AnchorTimeFact:
    return AnchorTimeFact(
        anchor_key=key,
        anchor_name=name,
        drive_time_min=drive,
        distance_km=distance,
        metadata_json={"sku": "routes_compute_routes_non_enterprise", "fixture": True},
    )


THE_OASIS = (
    _planned("planned", "The Oasis crystal lagoon and swimmable beach", status_note="master-plan amenity; not an existing public POI"),
    _planned("planned", "The Oasis retail and dining promenade", status_note="developer-planned community retail"),
    _planned("planned", "The Oasis community mosque", status_note="developer-planned community facility"),
    _g("school", "GEMS FirstPoint School", primary_type="school", drive=18, distance_m=9300, khda_rating="Good", khda_rating_year=2024, curriculum="UK", match_confidence=0.91),
    _g("school", "The Aquila School", primary_type="school", drive=20, distance_m=10400, khda_rating="Good", khda_rating_year=2024, curriculum="UK", match_confidence=0.9),
    _g("retail", "Dubai Outlet Mall", primary_type="shopping_mall", drive=12, distance_m=6500),
    _g("park", "Global Village", primary_type="tourist_attraction", drive=14, distance_m=7600),
    _g("healthcare", "Mediclinic Parkview Hospital", primary_type="hospital", drive=19, distance_m=11800),
)

SOBHA_CENTRAL = (
    _planned("planned", "Sobha Central retail podium", status_note="project amenity inside the master development"),
    _planned("planned", "Sobha Central residents' gym and lap pool", status_note="project amenity at completion"),
    _g("transit", "Jabal Ali Metro Station", primary_type="subway_station", drive=6, distance_m=2100),
    _g("retail", "Ibn Battuta Mall", primary_type="shopping_mall", drive=8, distance_m=3900),
    _g("school", "Dubai British School Jumeirah Park", primary_type="school", drive=13, distance_m=7700, khda_rating="Outstanding", khda_rating_year=2024, curriculum="UK", match_confidence=0.93),
    _g("school", "The Arbor School", primary_type="school", drive=14, distance_m=8300, khda_rating="Very Good", khda_rating_year=2024, curriculum="UK", match_confidence=0.91),
    _g("healthcare", "Mediclinic Meadows", primary_type="hospital", drive=15, distance_m=8500),
    _g("park", "Jumeirah Islands Pavilion", primary_type="shopping_mall", drive=12, distance_m=6800),
)

HARBOUR_POINT = (
    _g("retail", "Dubai Festival City Mall", primary_type="shopping_mall", drive=9, distance_m=3600),
    _g("park", "Ras Al Khor Wildlife Sanctuary", primary_type="tourist_attraction", drive=8, distance_m=3200),
    _g("transit", "Creek Metro Station", primary_type="subway_station", drive=11, distance_m=4500),
    _g("healthcare", "Mediclinic Creek Harbour", primary_type="hospital", drive=6, distance_m=1800),
    _g("school", "Swiss International Scientific School in Dubai", primary_type="school", drive=13, distance_m=6100, khda_rating="Good", khda_rating_year=2024, curriculum="IB", match_confidence=0.92),
    _g("retail", "Dubai Creek Harbour Marina", primary_type="marina", drive=4, distance_m=1200),
)

DUBAI_HILLS = (
    _g("retail", "Dubai Hills Mall", primary_type="shopping_mall", drive=7, distance_m=3000),
    _g("healthcare", "King's College Hospital London Dubai", primary_type="hospital", drive=6, distance_m=2300),
    _g("park", "Dubai Hills Park", primary_type="park", drive=5, distance_m=1600),
    _g("school", "GEMS Wellington Academy Al Khail", primary_type="school", drive=8, distance_m=3600, khda_rating="Very Good", khda_rating_year=2024, curriculum="UK/IB", match_confidence=0.92),
    _g("school", "GEMS International School Al Khail", primary_type="school", drive=9, distance_m=4200, khda_rating="Very Good", khda_rating_year=2024, curriculum="IB", match_confidence=0.9),
    _g("retail", "Geant Express Dubai Hills", primary_type="supermarket", drive=4, distance_m=1300),
)

ADDRESS_JBR = (
    _g("retail", "The Beach JBR", primary_type="shopping_mall", drive=5, distance_m=900, walk=10),
    _g("transit", "DMCC Metro Station", primary_type="subway_station", drive=9, distance_m=2600),
    _g("retail", "Dubai Marina Mall", primary_type="shopping_mall", drive=8, distance_m=2600),
    _g("healthcare", "Emirates Hospitals Clinic Marina", primary_type="hospital", drive=9, distance_m=3100),
    _g("school", "Dubai British School Jumeirah Park", primary_type="school", drive=17, distance_m=9800, khda_rating="Outstanding", khda_rating_year=2024, curriculum="UK", match_confidence=0.9),
    _g("park", "JBR Beach", primary_type="beach", drive=3, distance_m=500, walk=6),
)

ARABIAN_RANCHES = (
    _g("school", "Ranches Primary School", primary_type="school", drive=8, distance_m=3300, khda_rating="Very Good", khda_rating_year=2024, curriculum="UK", match_confidence=0.92),
    _g("retail", "Cityland Mall", primary_type="shopping_mall", drive=12, distance_m=6100),
    _g("park", "Global Village", primary_type="tourist_attraction", drive=10, distance_m=5200),
    _g("retail", "Carrefour Ranches Souk", primary_type="supermarket", drive=12, distance_m=5900),
    _g("healthcare", "Aster Clinic Arabian Ranches", primary_type="hospital", drive=13, distance_m=6400),
    _g("worship", "Al Rahman Mosque Arabian Ranches", primary_type="mosque", drive=11, distance_m=5600),
)

DUBAI_MARINA = (
    _g("transit", "DMCC Metro Station", primary_type="subway_station", drive=5, distance_m=1200, walk=14),
    _g("retail", "Dubai Marina Mall", primary_type="shopping_mall", drive=5, distance_m=900, walk=12),
    _g("retail", "Spinneys Dubai Marina", primary_type="supermarket", drive=4, distance_m=800, walk=10),
    _g("healthcare", "Medcare Medical Centre Marina", primary_type="hospital", drive=7, distance_m=1800),
    _g("park", "Dubai Marina Walk", primary_type="tourist_attraction", drive=3, distance_m=500, walk=6),
    _g("school", "Dubai British School Jumeirah Park", primary_type="school", drive=16, distance_m=8700, khda_rating="Outstanding", khda_rating_year=2024, curriculum="UK", match_confidence=0.89),
)

TOWN_SQUARE = (
    _g("park", "Town Square Park", primary_type="park", drive=4, distance_m=1100),
    _g("retail", "Carrefour Market Town Square", primary_type="supermarket", drive=4, distance_m=1200),
    _g("school", "Fairgreen International School", primary_type="school", drive=13, distance_m=7200, khda_rating="Very Good", khda_rating_year=2024, curriculum="IB", match_confidence=0.92),
    _g("school", "Jebel Ali School", primary_type="school", drive=14, distance_m=7800, khda_rating="Very Good", khda_rating_year=2024, curriculum="UK", match_confidence=0.91),
    _g("healthcare", "Aster Clinic Arabian Ranches", primary_type="hospital", drive=16, distance_m=9100),
    _g("worship", "Town Square Mosque", primary_type="mosque", drive=5, distance_m=1500),
)


PROFILE_FIXTURES: dict[str, EnrichmentProfile] = {
    "14395274": EnrichmentProfile(
        "the_oasis_palmiera",
        "14395274",
        THE_OASIS,
        (
            _anchor("downtown_dubai", "Downtown Dubai", 22, 24),
            _anchor("dxb_airport", "Dubai International Airport", 25, 28),
            _anchor("dubai_marina", "Dubai Marina", 28, 31),
        ),
        {"community": "The Oasis by Emaar", "mode": "off_plan_community"},
    ),
    "15223790": EnrichmentProfile(
        "the_oasis_mirage",
        "15223790",
        THE_OASIS,
        (
            _anchor("downtown_dubai", "Downtown Dubai", 23, 25),
            _anchor("dxb_airport", "Dubai International Airport", 26, 29),
            _anchor("dubai_marina", "Dubai Marina", 29, 32),
        ),
        {"community": "The Oasis by Emaar", "mode": "off_plan_community"},
    ),
    "14866538": EnrichmentProfile(
        "sobha_central_one_bed",
        "14866538",
        SOBHA_CENTRAL,
        (
            _anchor("dubai_marina", "Dubai Marina", 12, 9),
            _anchor("downtown_dubai", "Downtown Dubai", 25, 28),
            _anchor("al_maktoum_airport", "Al Maktoum International Airport", 28, 32),
        ),
        {"community": "Sobha Central", "mode": "off_plan_community"},
    ),
    "15069219": EnrichmentProfile(
        "sobha_central_two_bed",
        "15069219",
        SOBHA_CENTRAL,
        (
            _anchor("dubai_marina", "Dubai Marina", 12, 9),
            _anchor("downtown_dubai", "Downtown Dubai", 25, 28),
            _anchor("al_maktoum_airport", "Al Maktoum International Airport", 28, 32),
        ),
        {"community": "Sobha Central", "mode": "off_plan_community"},
    ),
    "15014530": EnrichmentProfile(
        "address_harbour_point",
        "15014530",
        HARBOUR_POINT,
        (
            _anchor("downtown_dubai", "Downtown Dubai", 14, 10),
            _anchor("dxb_airport", "Dubai International Airport", 18, 12),
            _anchor("business_bay", "Business Bay", 18, 13),
        ),
        {"community": "Address Harbour Point", "mode": "ready_secondary"},
    ),
    "92256451": EnrichmentProfile(
        "sidra_dubai_hills",
        "92256451",
        DUBAI_HILLS,
        (
            _anchor("downtown_dubai", "Downtown Dubai", 16, 14),
            _anchor("dubai_marina", "Dubai Marina", 20, 16),
            _anchor("dxb_airport", "Dubai International Airport", 25, 24),
        ),
        {"community": "Dubai Hills Estate", "mode": "ready_secondary"},
    ),
    "92697597": EnrichmentProfile(
        "address_jbr",
        "92697597",
        ADDRESS_JBR,
        (
            _anchor("downtown_dubai", "Downtown Dubai", 26, 23),
            _anchor("dubai_marina", "Dubai Marina", 8, 3),
            _anchor("dxb_airport", "Dubai International Airport", 33, 34),
        ),
        {"community": "JBR", "mode": "ready_secondary"},
    ),
    "89649726": EnrichmentProfile(
        "anya_arabian_ranches_3",
        "89649726",
        ARABIAN_RANCHES,
        (
            _anchor("downtown_dubai", "Downtown Dubai", 25, 25),
            _anchor("dubai_marina", "Dubai Marina", 28, 29),
            _anchor("al_maktoum_airport", "Al Maktoum International Airport", 26, 29),
        ),
        {"community": "Arabian Ranches 3", "mode": "ready_secondary"},
    ),
    "82376932": EnrichmentProfile(
        "liv_dubai_marina",
        "82376932",
        DUBAI_MARINA,
        (
            _anchor("downtown_dubai", "Downtown Dubai", 24, 22),
            _anchor("dxb_airport", "Dubai International Airport", 31, 33),
            _anchor("palm_jumeirah", "Palm Jumeirah", 13, 9),
        ),
        {"community": "Dubai Marina", "mode": "ready_secondary"},
    ),
    "92275744": EnrichmentProfile(
        "shams_town_square",
        "92275744",
        TOWN_SQUARE,
        (
            _anchor("downtown_dubai", "Downtown Dubai", 27, 28),
            _anchor("dubai_marina", "Dubai Marina", 29, 30),
            _anchor("al_maktoum_airport", "Al Maktoum International Airport", 24, 27),
        ),
        {"community": "Town Square", "mode": "ready_secondary"},
    ),
}


def profile_for_listing(listing: DBListing) -> EnrichmentProfile | None:
    source_url = (getattr(listing, "source_url", None) or "").lower()
    spa_data = getattr(listing, "spa_data", None) or {}
    imported = spa_data.get("imported_listing") or {}
    haystack = " ".join(
        str(v or "")
        for v in [
            source_url,
            spa_data.get("project"),
            imported.get("title"),
            imported.get("community"),
            imported.get("subcommunity"),
            imported.get("portal_listing_id"),
        ]
    ).lower()
    for hint, profile in PROFILE_FIXTURES.items():
        if hint.lower() in haystack:
            return profile
    return None


def next_profile_version(db: Session, listing_id: str) -> int:
    latest_amenity = (
        db.query(func.max(DBListingAmenity.profile_version))
        .filter(DBListingAmenity.listing_id == listing_id)
        .scalar()
    ) or 0
    latest_anchor = (
        db.query(func.max(DBListingAnchorTime.profile_version))
        .filter(DBListingAnchorTime.listing_id == listing_id)
        .scalar()
    ) or 0
    return int(max(latest_amenity, latest_anchor)) + 1


def _upsert_khda_school(db: Session, fact: AmenityFact) -> None:
    if not fact.khda_rating:
        return
    normalized = normalize_school_name(fact.name)
    existing = (
        db.query(DBKHDASchool)
        .filter(
            DBKHDASchool.normalized_name == normalized,
            DBKHDASchool.area == fact.metadata_json.get("area"),
        )
        .first()
    )
    if existing:
        existing.name = fact.name
        existing.rating = fact.khda_rating
        existing.rating_year = fact.khda_rating_year
        existing.curriculum = fact.curriculum
        existing.latitude = fact.latitude
        existing.longitude = fact.longitude
        existing.updated_at = datetime.utcnow()
        return
    db.add(
        DBKHDASchool(
            name=fact.name,
            normalized_name=normalized,
            area=fact.metadata_json.get("area"),
            rating=fact.khda_rating,
            rating_year=fact.khda_rating_year,
            curriculum=fact.curriculum,
            latitude=fact.latitude,
            longitude=fact.longitude,
            source_url="https://web.khda.gov.ae/",
            metadata_json={"fixture": True, "match_method": "normalized_name_geo_threshold"},
        )
    )


def persist_fixture_enrichment(db: Session, listing: DBListing) -> dict[str, Any] | None:
    profile = profile_for_listing(listing)
    if profile is None:
        return None

    version = next_profile_version(db, listing.listing_id)
    started_at = datetime.utcnow()
    run = DBEnrichmentRun(
        listing_id=listing.listing_id,
        profile_version=version,
        provider="harness_fixture",
        mode="batch",
        sku_usage={
            "places_text_search": {
                "sku": "non_enterprise",
                "field_mask": list(GOOGLE_PLACES_FIELD_MASK),
                "live_calls": 0,
            },
            "routes_compute_routes": {"sku": "non_enterprise", "live_calls": 0},
            "enterprise_sku_calls": 0,
        },
        status="complete",
        started_at=started_at,
        completed_at=datetime.utcnow(),
        metadata_json={
            **profile.metadata_json,
            "profile_key": profile.profile_key,
            "source_url_hint": profile.source_url_hint,
        },
    )
    db.add(run)

    for fact in profile.amenities:
        _upsert_khda_school(db, fact)
        db.add(
            DBListingAmenity(
                listing_id=listing.listing_id,
                profile_version=version,
                **asdict(fact),
            )
        )

    for fact in profile.anchor_times:
        db.add(
            DBListingAnchorTime(
                listing_id=listing.listing_id,
                profile_version=version,
                **asdict(fact),
            )
        )

    stages = dict(listing.processing_stages or {})
    stages["neighborhood_enrichment"] = {
        "status": "complete",
        "source": "harness_fixture",
        "profile_key": profile.profile_key,
        "profile_version": version,
        "amenity_count": len(profile.amenities),
        "anchor_time_count": len(profile.anchor_times),
        "field_mask": list(GOOGLE_PLACES_FIELD_MASK),
        "enterprise_sku_calls": 0,
        "at": datetime.utcnow().isoformat(),
    }
    listing.processing_stages = stages
    return {
        "listing_id": listing.listing_id,
        "profile_key": profile.profile_key,
        "profile_version": version,
        "amenity_count": len(profile.amenities),
        "anchor_time_count": len(profile.anchor_times),
    }


def latest_listing_enrichment(db: Session, listing_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        inspector = inspect(db.get_bind())
        if not inspector.has_table("listing_amenities") or not inspector.has_table("listing_anchor_times"):
            return [], []
        latest_version = (
            db.query(func.max(DBListingAmenity.profile_version))
            .filter(DBListingAmenity.listing_id == listing_id)
            .scalar()
        )
        if not latest_version:
            return [], []
        amenities = (
            db.query(DBListingAmenity)
            .filter(
                DBListingAmenity.listing_id == listing_id,
                DBListingAmenity.profile_version == latest_version,
            )
            .order_by(DBListingAmenity.category.asc(), DBListingAmenity.drive_time_min.asc().nullslast(), DBListingAmenity.name.asc())
            .all()
        )
        anchor_times = (
            db.query(DBListingAnchorTime)
            .filter(
                DBListingAnchorTime.listing_id == listing_id,
                DBListingAnchorTime.profile_version == latest_version,
            )
            .order_by(DBListingAnchorTime.drive_time_min.asc(), DBListingAnchorTime.anchor_name.asc())
            .all()
        )
    except SQLAlchemyError:
        return [], []

    amenity_dicts = [
        {
            "category": row.category,
            "name": row.name,
            "source": row.source,
            "status": row.status,
            "primary_type": row.primary_type,
            "drive_time_min": row.drive_time_min,
            "walk_time_min": row.walk_time_min,
            "straight_line_m": row.straight_line_m,
            "khda_rating": row.khda_rating,
            "khda_rating_year": row.khda_rating_year,
            "curriculum": row.curriculum,
            "match_confidence": row.match_confidence,
            "profile_version": row.profile_version,
        }
        for row in amenities
    ]
    anchor_dicts = [
        {
            "anchor_key": row.anchor_key,
            "anchor_name": row.anchor_name,
            "drive_time_min": row.drive_time_min,
            "distance_km": row.distance_km,
            "source": row.source,
            "profile_version": row.profile_version,
        }
        for row in anchor_times
    ]
    return amenity_dicts, anchor_dicts
