import copy
import json

import pytest

from tests.harness.builder import build_harness_plan, snapshot_name

pytestmark = pytest.mark.no_db


def _write_snapshot(snapshot_dir, url, *, price=2_500_000, ptype="ready", handover=None):
    snapshot = {
        "source_url": url,
        "source": "bayut" if "bayut" in url else "property_finder",
        "scraped_at": "2026-05-28T00:00:00Z",
        "scrape": {
            "source": "bayut" if "bayut" in url else "property_finder",
            "source_url": url,
            "property_type": "Apartment",
            "listing_title": "Harness 2BR Apartment",
            "listing_reference": "REF",
            "portal_listing_id": "123",
            "portal_reference": "REF",
            "purpose": "sale",
            "completion_status": "under construction" if ptype == "off_plan" else "completed",
            "furnishing": None,
            "community": "Dubai Marina",
            "subcommunity": "Marina Gate",
            "building_or_project": "Marina Gate",
            "unit_number": None,
            "bedrooms": 2,
            "bathrooms": 2,
            "size_sqft": 1200,
            "plot_size_sqft": None,
            "asking_price_aed": price,
            "price_per_sqft_aed": None,
            "latitude": None,
            "longitude": None,
            "developer": "Harness Developer",
            "handover_date": "2028-10-01" if ptype == "off_plan" else None,
            "permit_number": None,
            "permit_validation_url": None,
            "broker_name": None,
            "broker_license": None,
            "agent_name": None,
            "agent_email": None,
            "agent_phone": None,
            "agent_license": None,
            "amenities": ["Pool"],
            "image_urls": ["https://images.example.test/1.webp"],
            "description": "Harness listing",
            "raw_extracts": {},
        },
        "verification": {
            "property_type": ptype,
            "asking_price_aed": price,
            "community_or_building": "Dubai Marina",
            "bedrooms": 2,
            "size_sqft": 1200,
            "handover_quarter": handover,
            "image_count": 1,
            "missing_fields": [],
        },
    }
    (snapshot_dir / snapshot_name(url)).write_text(json.dumps(snapshot, indent=2))


def test_harness_plan_is_deterministic_and_uses_snapshots(tmp_path):
    config_path = tmp_path / "config.json"
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    config = {
        "version": 1,
        "prefix": "HARNESS",
        "seed": 42,
        "current_year": 2026,
        "current_month": 5,
        "randomization": {
            "threshold_discount_pct": [0.02, 0.08],
            "commission_rate": [0.005, 0.02],
            "paid_percent_options": [30, 40, 50],
            "spa_discount_pct": [0.10, 0.25],
            "additional_fee_count": [1, 2],
        },
        "community_research": {"mode": "stub"},
        "agent_generation": {"count_per_brokerage": 2, "origins": ["south_asian", "arab", "western", "filipino"]},
        "brokerages": [
            {"id": "harness-a", "name": "Harness A", "slug": "harness-a", "brokerage_ai_number": "+9711", "agents_ai_number": "+9712"},
            {"id": "harness-b", "name": "Harness B", "slug": "harness-b", "brokerage_ai_number": "+9713", "agents_ai_number": "+9714"},
        ],
        "listings": [
            {"brokerage_id": "harness-a", "source_url": "https://www.bayut.com/property/details-1.html", "property_type_override": "ready"},
            {"brokerage_id": "harness-b", "source_url": "https://www.bayut.com/property/details-2.html", "property_type_override": "off_plan", "handover_quarter": "2028-Q4"},
        ],
    }
    config_path.write_text(json.dumps(config))
    for listing in config["listings"]:
        _write_snapshot(
            snapshot_dir,
            listing["source_url"],
            ptype=listing["property_type_override"],
            handover=listing.get("handover_quarter"),
        )

    first = build_harness_plan(config_path, snapshot_dir)
    second = build_harness_plan(config_path, snapshot_dir)

    assert first == second
    assert len(first.brokerages) == 2
    assert len(first.agents) == 4
    assert len(first.listings) == 2
    for listing in first.listings:
        assert 0.02 <= listing.threshold_discount_pct <= 0.08
        assert 0.005 <= listing.commission_rate <= 0.02
        assert listing.media_urls == ["https://images.example.test/1.webp"]

    off_plan = next(listing for listing in first.listings if listing.property_type == "off_plan")
    assert off_plan.spa_data["total_paid_percent"] in {30, 40, 50, 100}
    assert off_plan.spa_data["purchase_price_aed"] < off_plan.asking_price_aed
    assert off_plan.spa_data["payment_schedule"][-1]["percentage"] == 40.0
    assert sum(item["percentage"] for item in off_plan.spa_data["payment_schedule"]) + off_plan.spa_data["total_paid_percent"] == 100

    ready = next(listing for listing in first.listings if listing.property_type == "ready")
    assert ready.spa_data["payment_schedule"] == []
    assert ready.spa_data["total_paid_percent"] is None
    assert ready.spa_data["noc_eligible"] is None
    assert ready.spa_data["estimated_completion_date"] is None


def test_harness_reclassifies_under_construction_snapshot_even_if_verification_is_stale(tmp_path):
    config_path = tmp_path / "config.json"
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    config = {
        "version": 1,
        "prefix": "HARNESS",
        "seed": 42,
        "current_year": 2026,
        "current_month": 5,
        "randomization": {
            "threshold_discount_pct": [0.02, 0.08],
            "commission_rate": [0.005, 0.02],
            "paid_percent_options": [30, 40, 50],
            "spa_discount_pct": [0.10, 0.25],
            "additional_fee_count": [1, 1],
        },
        "community_research": {"mode": "stub"},
        "agent_generation": {"count_per_brokerage": 1, "origins": ["south_asian"]},
        "brokerages": [{"id": "harness-a", "name": "Harness A", "slug": "harness-a"}],
        "listings": [{"brokerage_id": "harness-a", "source_url": "https://www.bayut.com/property/details-1.html"}],
    }
    config_path.write_text(json.dumps(config))
    _write_snapshot(snapshot_dir, config["listings"][0]["source_url"], ptype="off_plan")
    snapshot_path = snapshot_dir / snapshot_name(config["listings"][0]["source_url"])
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["scrape"]["completion_status"] = "under-construction"
    snapshot["scrape"]["handover_date"] = None
    snapshot["scrape"]["building_or_project"] = {
        "completionDetails": {"completionDate": 1830196800.0},
        "completionStatus": "under-construction",
        "title": "Palmiera",
    }
    snapshot["verification"]["property_type"] = "ready"
    snapshot["verification"]["handover_quarter"] = None
    snapshot_path.write_text(json.dumps(snapshot, indent=2))

    seed = build_harness_plan(config_path, snapshot_dir)
    listing = seed.listings[0]

    assert listing.property_type == "off_plan"
    assert listing.spa_data["estimated_completion_date"] == "2027-10-01"
    assert listing.spa_data["total_paid_percent"] in {30, 40, 50}
    assert sum(item["percentage"] for item in listing.spa_data["payment_schedule"]) + listing.spa_data["total_paid_percent"] == 100


def test_harness_drops_mirrored_villa_plot_size(tmp_path):
    config_path = tmp_path / "config.json"
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    config = {
        "version": 1,
        "prefix": "HARNESS",
        "seed": 42,
        "current_year": 2026,
        "current_month": 5,
        "randomization": {
            "threshold_discount_pct": [0.02, 0.08],
            "commission_rate": [0.005, 0.02],
            "paid_percent_options": [30, 40, 50],
            "spa_discount_pct": [0.10, 0.25],
            "additional_fee_count": [1, 1],
        },
        "community_research": {"mode": "stub"},
        "agent_generation": {"count_per_brokerage": 1, "origins": ["south_asian"]},
        "brokerages": [{"id": "harness-a", "name": "Harness A", "slug": "harness-a"}],
        "listings": [{"brokerage_id": "harness-a", "source_url": "https://www.bayut.com/property/details-villa.html"}],
    }
    config_path.write_text(json.dumps(config))
    _write_snapshot(snapshot_dir, config["listings"][0]["source_url"], ptype="off_plan")
    snapshot_path = snapshot_dir / snapshot_name(config["listings"][0]["source_url"])
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["scrape"]["property_type"] = "Villa"
    snapshot["scrape"]["listing_title"] = "Palmiera 4BR Villa"
    snapshot["scrape"]["size_sqft"] = 9075
    snapshot["scrape"]["plot_size_sqft"] = 9076
    snapshot_path.write_text(json.dumps(snapshot, indent=2))

    seed = build_harness_plan(config_path, snapshot_dir)
    listing = seed.listings[0]

    assert listing.spa_data["property_type"] == "Villa"
    assert listing.spa_data["bua_sqft"] == 9075
    assert listing.spa_data["plot_sqft"] is None


def test_config_only_third_brokerage_adds_cleanly(tmp_path):
    config_path = tmp_path / "config.json"
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    base_config = {
        "version": 1,
        "prefix": "HARNESS",
        "seed": 7,
        "current_year": 2026,
        "current_month": 5,
        "randomization": {
            "threshold_discount_pct": [0.02, 0.08],
            "commission_rate": [0.005, 0.02],
            "paid_percent_options": [30, 40, 50],
            "spa_discount_pct": [0.10, 0.25],
            "additional_fee_count": [1, 1],
        },
        "community_research": {"mode": "stub"},
        "agent_generation": {"count_per_brokerage": 1, "origins": ["south_asian", "arab", "western", "filipino"]},
        "brokerages": [{"id": "harness-a", "name": "Harness A", "slug": "harness-a"}],
        "listings": [{"brokerage_id": "harness-a", "source_url": "https://www.bayut.com/property/details-10.html"}],
    }
    config = copy.deepcopy(base_config)
    config["brokerages"].append({"id": "harness-c", "name": "Harness C", "slug": "harness-c"})
    config["listings"].append({"brokerage_id": "harness-c", "source_url": "https://www.bayut.com/property/details-30.html"})
    config_path.write_text(json.dumps(config))
    for listing in config["listings"]:
        _write_snapshot(snapshot_dir, listing["source_url"])

    plan = build_harness_plan(config_path, snapshot_dir)

    assert {b["id"] for b in plan.brokerages} == {"harness-a", "harness-c"}
    assert {listing.brokerage_id for listing in plan.listings} == {"harness-a", "harness-c"}
