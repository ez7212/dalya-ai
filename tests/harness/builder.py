from __future__ import annotations

import copy
import hashlib
import ast
import json
import random
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.core.listing_scraper import ScrapedListing, scrape_any
from app.models.db_models import (
    DBAgentChatbotConfig,
    DBAgentMessageRoute,
    DBAgentProfile,
    DBAgentVerification,
    DBBrokerage,
    DBBrokerageMember,
    DBBuyerListingMatch,
    DBBuyerPreferenceProfile,
    DBCommunityResearch,
    DBConversation,
    DBEnrichmentRun,
    DBListing,
    DBListingAmenity,
    DBListingAnchorTime,
    DBListingInquiry,
    DBMessage,
    DBOfferRecord,
    DBSuspiciousActivity,
)
from tests.safety import assert_safe_test_database

HARNESS_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = HARNESS_DIR / "config.json"
DEFAULT_SNAPSHOT_DIR = HARNESS_DIR / "snapshots"
DEFAULT_REPORT_PATH = HARNESS_DIR / "scrape_report.md"

REQUIRED_FIELDS = ("property_type", "asking_price_aed", "community_or_building", "bedrooms", "size_sqft")
ORIGIN_NAMES = {
    "south_asian": [
        ("Aisha Khan", "Aisha"),
        ("Rohan Mehta", "Rohan"),
        ("Priya Nair", "Priya"),
        ("Imran Siddiqui", "Imran"),
    ],
    "arab": [
        ("Layla Hassan", "Layla"),
        ("Omar Khalifa", "Omar"),
        ("Mariam Al Nuaimi", "Mariam"),
        ("Karim Mansour", "Karim"),
    ],
    "western": [
        ("James Carter", "James"),
        ("Sophie Bennett", "Sophie"),
        ("Emma Clarke", "Emma"),
        ("Daniel Brooks", "Daniel"),
    ],
    "filipino": [
        ("Maria Santos", "Maria"),
        ("Paolo Reyes", "Paolo"),
        ("Angela Cruz", "Angela"),
        ("Miguel Garcia", "Miguel"),
    ],
}


@dataclass(frozen=True)
class HarnessAgent:
    brokerage_id: str
    user_id: str
    profile_id: str
    member_id: str
    chatbot_config_id: str
    full_name: str
    display_name: str
    phone: str
    rera_broker_card_number: str


@dataclass(frozen=True)
class HarnessListing:
    listing_id: str
    brokerage_id: str
    assigned_agent_id: str
    source_url: str
    property_type: str
    asking_price_aed: float
    threshold_discount_pct: float
    notification_threshold_aed: float
    commission_rate: float
    additional_fees: list[dict[str, Any]]
    spa_data: dict[str, Any]
    media_urls: list[str]
    community_key: str | None
    missing_fields: list[str]


@dataclass(frozen=True)
class HarnessSeed:
    brokerages: list[dict[str, Any]]
    agents: list[HarnessAgent]
    listings: list[HarnessListing]


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def snapshot_name(url: str) -> str:
    match = re.search(r"(?:details-|property/details-)(\d+)", url)
    if match:
        return f"bayut-{match.group(1)}.json"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"listing-{digest}.json"


def _slugify(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return cleaned or None


def _stable_uuid(*parts: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, ":".join(parts)))


def _quarter_from_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.match(r"(\d{4})-(\d{2})", value)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    quarter = ((month - 1) // 3) + 1
    return f"{year}-Q{quarter}"


def _handover_date_from_quarter(quarter: str | None) -> str | None:
    if not quarter:
        return None
    match = re.match(r"(\d{4})-Q([1-4])", quarter)
    if not match:
        return None
    month = {1: 1, 2: 4, 3: 7, 4: 10}[int(match.group(2))]
    return f"{int(match.group(1)):04d}-{month:02d}-01"


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


def _handover_quarter_from_scrape(scrape: dict[str, Any]) -> str | None:
    quarter = _quarter_from_date(scrape.get("handover_date"))
    if quarter:
        return quarter
    project = _parse_maybe_dict(scrape.get("building_or_project"))
    completion = project.get("completionDetails")
    if isinstance(completion, dict) and completion.get("completionDate"):
        try:
            dt = datetime.fromtimestamp(float(completion["completionDate"]))
        except (TypeError, ValueError, OSError):
            return None
        return f"{dt.year}-Q{((dt.month - 1) // 3) + 1}"
    return None


def _project_name_from_scrape(scrape: dict[str, Any]) -> str:
    project = _parse_maybe_dict(scrape.get("building_or_project"))
    if project.get("title"):
        return str(project["title"])
    value = scrape.get("building_or_project") or scrape.get("subcommunity") or scrape.get("community") or "Property"
    return str(value)


def _developer_from_scrape(scrape: dict[str, Any]) -> str:
    if scrape.get("developer"):
        return str(scrape["developer"])
    project = _parse_maybe_dict(scrape.get("building_or_project"))
    agency = project.get("agency")
    if isinstance(agency, dict):
        for key in ("name", "name_l2", "name_l3"):
            if agency.get(key):
                return str(agency[key])
    return ""


def _extract_sqft_from_description(description: str | None, *labels: str) -> float | None:
    if not description:
        return None
    label_alt = "|".join(re.escape(label) for label in labels)
    patterns = [
        rf"(?:{label_alt})\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*ft|sqft|square\s*feet)",
        r"([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*ft|sqft|square\s*feet)",
    ]
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if not match:
            continue
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            continue
    return None


def _normalise_area_fields(scrape: dict[str, Any]) -> tuple[float | None, float | None]:
    """Correct common portal unit slips before fixtures become listing truth."""
    property_type = str(scrape.get("property_type") or scrape.get("listing_title") or "").lower()
    description = scrape.get("description")
    size = scrape.get("size_sqft")
    plot = scrape.get("plot_size_sqft")

    if isinstance(size, (int, float)):
        size = float(size)
    else:
        size = None
    if isinstance(plot, (int, float)):
        plot = float(plot)
    else:
        plot = None
    raw_size = size
    raw_plot = plot

    extracted = _extract_sqft_from_description(
        description,
        "built up area",
        "built-up area",
        "bua",
        "property highlights",
    )
    is_villaish = any(token in property_type for token in ("villa", "townhouse"))
    is_apartment = "apartment" in property_type

    if is_apartment and size is not None and size < 200 and extracted and extracted >= 300:
        size = extracted
    elif is_apartment and size is not None and size < 250:
        size = round(size * 10.7639, 2)
    elif is_villaish and extracted and extracted > max(size or 0, 0) * 3:
        size = extracted
    elif is_villaish and size is not None and size < 1_500:
        size = round(size * 10.7639, 2)

    if is_villaish and raw_size is not None and raw_plot is not None and abs(raw_plot - raw_size) <= max(1.0, raw_size * 0.01):
        plot = None
    if is_villaish and plot is not None and plot < 2_000:
        plot = round(plot * 10.7639, 2)
    if is_villaish and size is not None and plot is not None and plot <= size * 1.05:
        plot = None

    return size, plot


def _normalise_property_type(scrape: dict[str, Any], raw_type: str | None) -> str:
    blob = " ".join(
        str(scrape.get(key) or "")
        for key in ("listing_title", "building_or_project", "subcommunity", "description")
    ).lower()
    if "townhouse" in blob:
        return "Townhouse"
    return raw_type or "Property"


def _classify_property_type(scrape: dict[str, Any], listing_cfg: dict[str, Any]) -> str:
    override = listing_cfg.get("property_type_override")
    if override == "finished":
        return "ready"
    if override in {"off_plan", "ready"}:
        return override
    status_blob = " ".join(
        str(scrape.get(key) or "")
        for key in ("completion_status", "handover_date", "description", "listing_title", "building_or_project")
    ).lower()
    if "completed" in status_blob or "complete" in status_blob:
        return "ready"
    if any(token in status_blob for token in ("off plan", "off-plan", "off_plan", "under construction", "under-construction")):
        return "off_plan"
    return "ready"


def _scrape_to_snapshot(scraped: ScrapedListing, listing_cfg: dict[str, Any]) -> dict[str, Any]:
    data = asdict(scraped)
    imported = copy.deepcopy(data)
    for key in ("broker_name", "broker_license", "agent_name", "agent_email", "agent_phone", "agent_license"):
        imported[key] = None
    if imported.get("description"):
        imported["description"] = _sanitize_text(imported["description"])
    property_type = _classify_property_type(imported, listing_cfg)
    handover_quarter = listing_cfg.get("handover_quarter") or _handover_quarter_from_scrape(imported)
    community_or_building = imported.get("community") or imported.get("building_or_project") or imported.get("subcommunity")
    missing = []
    if not property_type:
        missing.append("property_type")
    if not imported.get("asking_price_aed"):
        missing.append("asking_price_aed")
    if not community_or_building:
        missing.append("community_or_building")
    if imported.get("bedrooms") is None:
        missing.append("bedrooms")
    if imported.get("size_sqft") is None:
        missing.append("size_sqft")
    if property_type == "off_plan" and not handover_quarter:
        missing.append("handover_quarter")
    return {
        "source_url": imported["source_url"],
        "source": imported["source"],
        "scraped_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "scrape": imported,
        "verification": {
            "property_type": property_type,
            "asking_price_aed": imported.get("asking_price_aed"),
            "community_or_building": community_or_building,
            "bedrooms": imported.get("bedrooms"),
            "size_sqft": imported.get("size_sqft"),
            "handover_quarter": handover_quarter,
            "image_count": len(imported.get("image_urls") or []),
            "missing_fields": missing,
        },
    }


def _sanitize_text(value: str) -> str:
    value = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[redacted email]", value)
    value = re.sub(r"(?:\+?\d[\s().-]?){7,}", "[redacted phone number]", value)
    return value


def refresh_snapshots(
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    snapshot_dir: Path | str = DEFAULT_SNAPSHOT_DIR,
    report_path: Path | str = DEFAULT_REPORT_PATH,
) -> list[dict[str, Any]]:
    config = load_config(config_path)
    snapshot_dir = Path(snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for listing_cfg in config["listings"]:
        scraped = scrape_any(listing_cfg["source_url"])
        snapshot = _scrape_to_snapshot(scraped, listing_cfg)
        snapshots.append(snapshot)
        (snapshot_dir / snapshot_name(listing_cfg["source_url"])).write_text(
            json.dumps(snapshot, indent=2, sort_keys=True)
        )
    write_scrape_report(snapshots, report_path)
    return snapshots


def write_scrape_report(snapshots: list[dict[str, Any]], report_path: Path | str = DEFAULT_REPORT_PATH) -> None:
    lines = [
        "# Harness scrape verification report",
        "",
        "| URL | Type | Price | Community/building | Beds | Size | Handover | Images | Missing |",
        "| --- | --- | ---: | --- | ---: | ---: | --- | ---: | --- |",
    ]
    for snapshot in snapshots:
        v = snapshot["verification"]
        missing = ", ".join(v["missing_fields"]) if v["missing_fields"] else "none"
        lines.append(
            "| {url} | {ptype} | {price} | {community} | {beds} | {size} | {handover} | {images} | {missing} |".format(
                url=snapshot["source_url"],
                ptype=v.get("property_type") or "",
                price=f"{v.get('asking_price_aed'):,.0f}" if v.get("asking_price_aed") else "",
                community=v.get("community_or_building") or "",
                beds=v.get("bedrooms") if v.get("bedrooms") is not None else "",
                size=f"{v.get('size_sqft'):,.0f}" if v.get("size_sqft") else "",
                handover=v.get("handover_quarter") or "",
                images=v.get("image_count") or 0,
                missing=missing,
            )
        )
    Path(report_path).write_text("\n".join(lines) + "\n")


def _load_snapshot(url: str, snapshot_dir: Path | str = DEFAULT_SNAPSHOT_DIR) -> dict[str, Any]:
    path = Path(snapshot_dir) / snapshot_name(url)
    if not path.exists():
        raise FileNotFoundError(f"Missing frozen harness snapshot for {url}: {path}")
    return json.loads(path.read_text())


def _rng_for(config: dict[str, Any], *parts: str) -> random.Random:
    seed_material = f"{config['seed']}:" + ":".join(parts)
    seed = int(hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def _generate_agents(config: dict[str, Any], brokerage: dict[str, Any], brokerage_index: int) -> list[HarnessAgent]:
    explicit = brokerage.get("agents")
    count = len(explicit) if explicit else int(config.get("agent_generation", {}).get("count_per_brokerage", 2))
    origins = config.get("agent_generation", {}).get("origins") or list(ORIGIN_NAMES)
    agents = []
    for idx in range(count):
        rng = _rng_for(config, brokerage["id"], "agent", str(idx))
        if explicit:
            full_name = explicit[idx]["full_name"]
            display_name = explicit[idx].get("display_name") or full_name.split()[0]
            origin = explicit[idx].get("origin") or origins[idx % len(origins)]
        else:
            origin = origins[(brokerage_index * count + idx) % len(origins)]
            full_name, display_name = rng.choice(ORIGIN_NAMES[origin])
        user_id = f"{config['prefix']}_agent_{brokerage['slug']}_{idx + 1}"
        agents.append(
            HarnessAgent(
                brokerage_id=brokerage["id"],
                user_id=user_id,
                profile_id=f"{config['prefix']}_profile_{brokerage['slug']}_{idx + 1}",
                member_id=f"{config['prefix']}_member_{brokerage['slug']}_{idx + 1}",
                chatbot_config_id=f"{config['prefix']}_chatbot_{brokerage['slug']}_{idx + 1}",
                full_name=full_name,
                display_name=display_name,
                phone=f"+97159002{brokerage_index + 1:02d}{idx + 1:03d}",
                rera_broker_card_number=f"BRN-{rng.randint(10000, 99999)}",
            )
        )
    return agents


def _additional_fees(rng: random.Random, asking_price: float, count_range: list[int]) -> list[dict[str, Any]]:
    fee_catalog = {
        "Document processing": [1500, 2500],
        "Conveyancing support": [3000, 5000],
        "Trustee coordination": [2000, 4000],
        "NOC coordination": [4000, 5000],
    }
    labels = list(fee_catalog)
    count = rng.randint(int(count_range[0]), int(count_range[1]))
    chosen = rng.sample(labels, count)
    return [
        {
            "label": label,
            "amount_aed": rng.randrange(fee_catalog[label][0], fee_catalog[label][1] + 1, 500),
            "paid_by": "buyer",
            "public": True,
        }
        for label in chosen
    ]


def _payment_schedule(
    asking_price: float,
    paid_pct: int,
    handover_date: str,
    current_year: int,
    current_month: int,
) -> tuple[list[dict[str, Any]], int, bool]:
    year, month, _day = [int(part) for part in handover_date.split("-")]
    months_to_handover = (year - current_year) * 12 + (month - current_month)
    if months_to_handover <= 0:
        return [], 100, True
    if paid_pct not in {30, 40, 50}:
        raise ValueError(f"Invalid future-handover paid_pct={paid_pct}; expected one of 30, 40, 50")
    remaining_construction = max(0, 60 - paid_pct)
    construction_count = remaining_construction // 10
    schedule = []
    instalment_number = 1
    used_month_offsets: set[int] = set()
    for index in range(construction_count):
        raw_offset = round(1 + (months_to_handover - 2) * ((index + 1) / (construction_count + 1))) if construction_count else 0
        offset = max(1, min(months_to_handover - 1, raw_offset))
        while offset in used_month_offsets and offset < months_to_handover - 1:
            offset += 1
        used_month_offsets.add(offset)
        due_year = current_year + ((current_month - 1 + offset) // 12)
        due_month = ((current_month - 1 + offset) % 12) + 1
        schedule.append(
            {
                "instalment_number": instalment_number,
                "due_date": f"{due_year:04d}-{due_month:02d}-01",
                "milestone": f"{paid_pct + index * 10 + 10}% construction milestone",
                "percentage": 10.0,
                "amount_aed": round(asking_price * 0.10, 2),
                "vat_amount_aed": 0.0,
                "amount_incl_vat_aed": round(asking_price * 0.10, 2),
                "actually_paid": False,
            }
        )
        instalment_number += 1
    schedule.append(
        {
            "instalment_number": instalment_number,
            "due_date": handover_date,
            "milestone": "Handover",
            "percentage": 40.0,
            "amount_aed": round(asking_price * 0.40, 2),
            "vat_amount_aed": 0.0,
            "amount_incl_vat_aed": round(asking_price * 0.40, 2),
            "actually_paid": False,
        }
    )
    return schedule, paid_pct, paid_pct >= 40


def _build_spa_data(
    config: dict[str, Any],
    listing_cfg: dict[str, Any],
    snapshot: dict[str, Any],
    asking_price: float,
    property_type: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    scrape = snapshot["scrape"]
    verification = snapshot["verification"]
    rng = _rng_for(config, listing_cfg["source_url"], "spa")
    project = _project_name_from_scrape(scrape)
    bua_sqft, plot_sqft = _normalise_area_fields(scrape)
    handover_quarter = listing_cfg.get("handover_quarter") or _handover_quarter_from_scrape(scrape) or verification.get("handover_quarter")
    metadata: dict[str, Any] = {"handover_quarter": handover_quarter}
    spa_purchase_price = asking_price
    payment_schedule: list[dict[str, Any]] = []
    paid_pct: int | None = None
    noc_eligible = None
    handover_date = scrape.get("handover_date")
    if property_type == "off_plan":
        handover_date = _handover_date_from_quarter(handover_quarter) or handover_date
        if not handover_date:
            raise ValueError(f"Off-plan harness listing missing handover date/quarter: {listing_cfg['source_url']}")
        paid_pct = rng.choice(config["randomization"]["paid_percent_options"])
        payment_schedule, paid_pct, noc_eligible = _payment_schedule(
            asking_price,
            int(paid_pct),
            handover_date or f"{config['current_year']}-05-01",
            int(config["current_year"]),
            int(config["current_month"]),
        )
        discount_range = config["randomization"]["spa_discount_pct"]
        spa_discount_pct = rng.uniform(float(discount_range[0]), float(discount_range[1]))
        spa_purchase_price = round(asking_price * (1 - spa_discount_pct), 2)
        metadata["spa_discount_pct"] = round(spa_discount_pct, 6)
    spa = {
        "project": project,
        "unit_number": scrape.get("unit_number") or "",
        "developer": _developer_from_scrape(scrape),
        "property_type": _normalise_property_type(
            scrape,
            scrape.get("property_type") or scrape.get("listing_title") or ("Ready Property" if property_type == "ready" else "Off-Plan"),
        ),
        "property_use": "Residential",
        "bedrooms": scrape.get("bedrooms"),
        "bathrooms": scrape.get("bathrooms"),
        "bua_sqft": bua_sqft,
        "plot_sqft": plot_sqft,
        "purchase_price_aed": spa_purchase_price,
        "vat_percent": 0.0,
        "property_status": "Ready" if property_type == "ready" else "Under Construction",
        "estimated_completion_date": handover_date if property_type == "off_plan" else None,
        "total_paid_percent": paid_pct if property_type == "off_plan" else None,
        "noc_eligible": noc_eligible,
        "payment_schedule": payment_schedule,
        "purchasers": [],
        "imported_listing": {
            "title": scrape.get("listing_title"),
            "reference": scrape.get("listing_reference"),
            "portal_source": scrape.get("source"),
            "portal_listing_id": scrape.get("portal_listing_id"),
            "purpose": scrape.get("purpose"),
            "completion_status": scrape.get("completion_status"),
            "furnishing": scrape.get("furnishing"),
            "community": scrape.get("community"),
            "subcommunity": scrape.get("subcommunity"),
            "price_per_sqft_aed": scrape.get("price_per_sqft_aed"),
            "amenities": scrape.get("amenities") or [],
            "description": scrape.get("description"),
            "permit_number": scrape.get("permit_number"),
            "permit_validation_url": scrape.get("permit_validation_url"),
        },
    }
    if property_type == "off_plan":
        metadata["total_paid_percent"] = paid_pct
        metadata["noc_eligible"] = noc_eligible
    return spa, metadata


def _months_to_handover(handover_date: str, current_year: int, current_month: int) -> int:
    year, month, _day = [int(part) for part in handover_date.split("-")]
    return (year - current_year) * 12 + (month - current_month)


def _validate_harness_listing(
    *,
    listing_cfg: dict[str, Any],
    spa_data: dict[str, Any],
    property_type: str,
    asking_price: float,
    config: dict[str, Any],
) -> None:
    errors: list[str] = []
    schedule = spa_data.get("payment_schedule") or []
    paid_pct = spa_data.get("total_paid_percent")
    metadata = spa_data.get("harness_metadata") or {}

    if property_type == "off_plan":
        if paid_pct not in {30, 40, 50, 100}:
            errors.append(f"paid_pct={paid_pct!r} not in {{30,40,50,100}}")
        if spa_data.get("noc_eligible") != (paid_pct >= 40 if paid_pct is not None else None):
            errors.append("noc_eligible does not match paid_pct >= 40")
        purchase = float(spa_data.get("purchase_price_aed") or 0)
        if not (asking_price * 0.75 <= purchase <= asking_price * 0.90):
            errors.append(f"synthetic SPA price AED {purchase:,.0f} is not 75-90% of asking AED {asking_price:,.0f}")
        handover_date = spa_data.get("estimated_completion_date")
        if not handover_date:
            errors.append("off-plan listing missing estimated_completion_date")
        else:
            months = _months_to_handover(handover_date, int(config["current_year"]), int(config["current_month"]))
            if months <= 0:
                if paid_pct != 100:
                    errors.append("past/current handover must force paid_pct=100")
                if schedule:
                    errors.append("past/current handover must have empty remaining schedule")
                if spa_data.get("noc_eligible") is not True:
                    errors.append("past/current handover must be NOC eligible")
            elif paid_pct == 100:
                if schedule:
                    errors.append("100%-paid future handover must not have remaining schedule")
            else:
                remaining_pct = sum(float(item.get("percentage") or 0) for item in schedule)
                if round(float(paid_pct or 0) + remaining_pct, 4) != 100:
                    errors.append(f"paid_pct + remaining schedule = {float(paid_pct or 0) + remaining_pct}, expected 100")
                construction = [item for item in schedule if float(item.get("percentage") or 0) == 10.0]
                expected_construction_count = int((60 - paid_pct) / 10)
                if len(construction) != expected_construction_count:
                    errors.append(f"construction installments={len(construction)}, expected {expected_construction_count}")
                if not schedule or float(schedule[-1].get("percentage") or 0) != 40.0:
                    errors.append("future off-plan schedule must end with 40% handover lump")
                handover_amount = float(schedule[-1].get("amount_aed") or 0) if schedule else 0
                if abs(handover_amount - asking_price * 0.40) > 1:
                    errors.append("handover instalment amount must equal 40% of asking")
                schedule_amount = sum(float(item.get("amount_aed") or 0) for item in schedule)
                expected_remaining = asking_price * remaining_pct / 100.0
                if abs(schedule_amount - expected_remaining) > max(1, asking_price * 0.0001):
                    errors.append("remaining schedule amount must equal headline remaining-to-developer")
                dates = [item.get("due_date") for item in schedule if item.get("due_date")]
                if dates != sorted(dates) or len(dates) != len(set(dates)):
                    errors.append("remaining schedule dates must be strictly increasing")
        if not metadata.get("spa_discount_pct"):
            errors.append("off-plan listing missing synthetic SPA discount metadata")
    elif property_type == "ready":
        if schedule:
            errors.append("ready listing must not have payment_schedule")
        if paid_pct is not None:
            errors.append("ready listing must not have total_paid_percent")
        if spa_data.get("noc_eligible") is not None:
            errors.append("ready listing must not have noc_eligible")
        if spa_data.get("estimated_completion_date") is not None:
            errors.append("ready listing must not have estimated_completion_date")
        if metadata.get("spa_discount_pct"):
            errors.append("ready listing must not have synthetic SPA discount metadata")
    else:
        errors.append(f"unknown property_type={property_type!r}")

    ptype = str(spa_data.get("property_type") or "").lower()
    bua = spa_data.get("bua_sqft")
    plot = spa_data.get("plot_sqft")
    if "apartment" in ptype and bua is not None and not (250 <= float(bua) <= 20_000):
        errors.append(f"apartment BUA {bua} outside plausibility bounds")
    if any(token in ptype for token in ("villa", "townhouse")):
        if bua is not None and not (1_000 <= float(bua) <= 40_000):
            errors.append(f"villa/townhouse BUA {bua} outside plausibility bounds")
        if plot is not None and not (1_500 <= float(plot) <= 80_000):
            errors.append(f"villa/townhouse plot {plot} outside plausibility bounds")
        if bua is not None and plot is not None and float(plot) <= float(bua):
            errors.append(f"villa/townhouse plot {plot} must be greater than BUA {bua}")

    if errors:
        raise ValueError(
            "Invalid harness listing payment model for "
            f"{listing_cfg['source_url']} ({property_type}): " + "; ".join(errors)
        )


def build_harness_plan(
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    snapshot_dir: Path | str = DEFAULT_SNAPSHOT_DIR,
) -> HarnessSeed:
    config = load_config(config_path)
    agents_by_brokerage: dict[str, list[HarnessAgent]] = {}
    all_agents: list[HarnessAgent] = []
    for brokerage_index, brokerage in enumerate(config["brokerages"]):
        agents = _generate_agents(config, brokerage, brokerage_index)
        agents_by_brokerage[brokerage["id"]] = agents
        all_agents.extend(agents)

    planned_listings: list[HarnessListing] = []
    listing_counter_by_brokerage: dict[str, int] = {}
    for listing_cfg in config["listings"]:
        brokerage_id = listing_cfg["brokerage_id"]
        listing_counter_by_brokerage[brokerage_id] = listing_counter_by_brokerage.get(brokerage_id, 0) + 1
        snapshot = _load_snapshot(listing_cfg["source_url"], snapshot_dir)
        scrape = snapshot["scrape"]
        verification = snapshot["verification"]
        property_type = _classify_property_type(scrape, listing_cfg)
        asking_price = float(scrape.get("asking_price_aed") or listing_cfg.get("manual", {}).get("asking_price_aed") or 0)
        if asking_price <= 0:
            raise ValueError(f"Harness listing has no asking price: {listing_cfg['source_url']}")
        rng = _rng_for(config, listing_cfg["source_url"], "listing")
        threshold_range = config["randomization"]["threshold_discount_pct"]
        threshold_discount_pct = rng.uniform(float(threshold_range[0]), float(threshold_range[1]))
        threshold = round(asking_price * (1 - threshold_discount_pct), 2)
        brokerage_cfg = next(b for b in config["brokerages"] if b["id"] == brokerage_id)
        brokerage_fee = (brokerage_cfg.get("default_fee_framing") or {}).get("commission_rate")
        if not isinstance(brokerage_fee, (int, float)):
            commission_range = config["randomization"]["commission_rate"]
            brokerage_fee = rng.uniform(float(commission_range[0]), float(commission_range[1]))
        commission_rate = round(float(brokerage_fee), 6)
        agents = agents_by_brokerage[brokerage_id]
        assigned_agent = agents[rng.randrange(len(agents))]
        spa_data, spa_metadata = _build_spa_data(config, listing_cfg, snapshot, asking_price, property_type)
        community_key = _slugify(scrape.get("community") or scrape.get("building_or_project") or scrape.get("subcommunity"))
        metadata = {
            "source": "canonical_harness",
            "source_url": listing_cfg["source_url"],
            "threshold_discount_pct": round(threshold_discount_pct, 6),
            "commission_rate": commission_rate,
            "snapshot": snapshot_name(listing_cfg["source_url"]),
            **spa_metadata,
        }
        spa_data["harness_metadata"] = metadata
        _validate_harness_listing(
            listing_cfg=listing_cfg,
            spa_data=spa_data,
            property_type=property_type,
            asking_price=asking_price,
            config=config,
        )
        planned_listings.append(
            HarnessListing(
                listing_id=f"{config['prefix']}_listing_{listing_counter_by_brokerage[brokerage_id]:02d}_{hashlib.sha1(listing_cfg['source_url'].encode()).hexdigest()[:8]}",
                brokerage_id=brokerage_id,
                assigned_agent_id=assigned_agent.user_id,
                source_url=listing_cfg["source_url"],
                property_type=property_type,
                asking_price_aed=asking_price,
                threshold_discount_pct=round(threshold_discount_pct, 6),
                notification_threshold_aed=threshold,
                commission_rate=commission_rate,
                additional_fees=_additional_fees(rng, asking_price, config["randomization"]["additional_fee_count"]),
                spa_data=spa_data,
                media_urls=scrape.get("image_urls") or [],
                community_key=community_key,
                missing_fields=list(verification.get("missing_fields") or []),
            )
        )

    return HarnessSeed(
        brokerages=copy.deepcopy(config["brokerages"]),
        agents=all_agents,
        listings=planned_listings,
    )


def _upsert(db, model, pk_field: str, pk_value: str, **fields):
    obj = db.query(model).filter(getattr(model, pk_field) == pk_value).first()
    if obj:
        for key, value in fields.items():
            setattr(obj, key, value)
        return obj
    obj = model(**{pk_field: pk_value, **fields})
    db.add(obj)
    return obj


def build_harness(
    db,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    snapshot_dir: Path | str = DEFAULT_SNAPSHOT_DIR,
) -> HarnessSeed:
    assert_safe_test_database(database_url=str(db.get_bind().url), operation="canonical harness build")
    seed = build_harness_plan(config_path, snapshot_dir)
    now = datetime.utcnow()
    config = load_config(config_path)
    brokerage_by_id = {b["id"]: b for b in seed.brokerages}

    for brokerage in seed.brokerages:
        _upsert(
            db,
            DBBrokerage,
            "brokerage_id",
            brokerage["id"],
            name=brokerage["name"],
            slug=brokerage["slug"],
            real_estate_number=brokerage.get("real_estate_number"),
            agent_signup_code=f"{config['prefix']}-{brokerage['slug']}".upper()[:64],
            agent_signup_enabled=True,
            brokerage_ai_number=brokerage.get("brokerage_ai_number"),
            agents_ai_number=brokerage.get("agents_ai_number"),
            default_fee_framing=brokerage.get("default_fee_framing"),
            prompt_config={"source": "canonical_harness"},
            settings={"source": "canonical_harness"},
            status="active",
            created_at=now,
            updated_at=now,
        )

    for agent in seed.agents:
        _upsert(
            db,
            DBBrokerageMember,
            "member_id",
            agent.member_id,
            brokerage_id=agent.brokerage_id,
            user_id=agent.user_id,
            email=f"{agent.user_id.lower()}@example.test",
            display_name=agent.display_name,
            phone=agent.phone,
            role="agent",
            status="active",
            settings={"source": "canonical_harness"},
            created_at=now,
            updated_at=now,
        )
        _upsert(
            db,
            DBAgentProfile,
            "profile_id",
            agent.profile_id,
            brokerage_id=agent.brokerage_id,
            user_id=agent.user_id,
            email=f"{agent.user_id.lower()}@example.test",
            full_name=agent.full_name,
            display_name=agent.display_name,
            whatsapp_phone=agent.phone,
            rera_broker_card_number=agent.rera_broker_card_number,
            languages=["en"],
            service_areas=["Dubai"],
            verification_status="verified",
            verification_provider="manual",
            verification_notes="Seeded by canonical harness",
            chatbot_display_name=agent.display_name,
            chatbot_handoff_phone=agent.phone,
            onboarding_status="active",
            settings={"source": "canonical_harness"},
            created_at=now,
            updated_at=now,
        )
        _upsert(
            db,
            DBAgentVerification,
            "verification_id",
            f"{config['prefix']}_verification_{agent.profile_id}",
            brokerage_id=agent.brokerage_id,
            agent_profile_id=agent.profile_id,
            user_id=agent.user_id,
            provider="manual",
            status="verified",
            rera_broker_card_number=agent.rera_broker_card_number,
            raw_response={"source": "canonical_harness"},
            reviewed_by="canonical_harness",
            reviewed_at=now,
            notes="Verified fixture profile",
            created_at=now,
        )
        _upsert(
            db,
            DBAgentChatbotConfig,
            "config_id",
            agent.chatbot_config_id,
            brokerage_id=agent.brokerage_id,
            agent_profile_id=agent.profile_id,
            agent_user_id=agent.user_id,
            handoff_display_name=agent.display_name,
            escalation_whatsapp_phone=agent.phone,
            active=True,
            settings={"source": "canonical_harness"},
            created_at=now,
            updated_at=now,
        )

    queued_community_research: set[tuple[str, str]] = set()
    for listing in seed.listings:
        brokerage = brokerage_by_id[listing.brokerage_id]
        agent = next(a for a in seed.agents if a.user_id == listing.assigned_agent_id)
        community_data = None
        community_research_stage = {
            "status": "pending",
            "source": "canonical_harness_backfill",
            "community_key": listing.community_key,
        }
        if config.get("community_research", {}).get("mode") == "backfill":
            try:
                from app.core.community_data import get_community_data_for_listing

                community_data = get_community_data_for_listing(
                    listing.spa_data.get("project") or listing.community_key or "",
                    developer=listing.spa_data.get("developer"),
                )
            except Exception:
                community_data = None
            if community_data:
                community_research_stage["status"] = "complete"
            else:
                community_research_stage["status"] = "missing"
        else:
            community_data = {
                "summary": f"{listing.spa_data['project']} community research fixture.",
                "source": "canonical_harness_stub",
                "community": listing.community_key,
            }
            community_research_stage["status"] = "stub"
            community_research_stage["source"] = "canonical_harness_stub"
        # DAL-91: Sidra Villas I (ready villa) carries tenancy data so Persona 24
        # gets direct answers instead of a deflection loop on every occupancy turn.
        unit_profile: dict = {}
        seller_notes = None
        _src = (listing.source_url or "").lower()
        if "92256451" in _src or "sidra-villas-i" in _src:
            unit_profile = {
                "occupancy_status": "tenanted",
                "tenancy": {
                    "status": "tenanted",
                    "lease_term_months": 12,
                    "lease_start": "2026-01",
                    "lease_end": "2027-01",
                    "vacant_possession_at_transfer": False,
                },
                "tenancy_note": (
                    "This unit is currently tenanted on a 12-month lease running January 2026 to "
                    "January 2027. On transfer the existing tenant has the right to remain under the "
                    "lease — the lease transfers with the property and does not automatically end at "
                    "expiry. The buyer can "
                    "raise extension or move-out with the tenant up to 3 months before lease end; a "
                    "non-renewal/eviction notice requires 12 months' notice served via notary or "
                    "registered mail under Dubai rental law. So vacant possession is NOT available at "
                    "transfer mid-lease, and January 2027 is only a lease-expiry date unless valid "
                    "notice has already been served and the legal position is confirmed."
                ),
            }
            seller_notes = "Tenanted: 12-month lease, January 2026 to January 2027."
        _upsert(
            db,
            DBListing,
            "listing_id",
            listing.listing_id,
            brokerage_id=listing.brokerage_id,
            assigned_agent_id=listing.assigned_agent_id,
            seller_id=listing.assigned_agent_id,
            seller_phone=agent.phone,
            spa_data=listing.spa_data,
            community_data=community_data,
            seller_asking_price=listing.asking_price_aed,
            seller_notes=seller_notes,
            negotiation_threshold_aed=listing.notification_threshold_aed,
            notification_threshold_aed=listing.notification_threshold_aed,
            seller_qa=[],
            media_urls=listing.media_urls,
            unit_profile=unit_profile,
            unit_profile_history=[],
            processing_stages={
                "harness": {
                    "status": "seeded",
                    "at": now.isoformat(),
                    "metadata": listing.spa_data.get("harness_metadata", {}),
                    "missing_fields": listing.missing_fields,
                },
                "community_research": {
                    **community_research_stage,
                    "at": now.isoformat(),
                },
            },
            commission_rate=listing.commission_rate,
            additional_fees=listing.additional_fees,
            property_type=listing.property_type,
            source_url=listing.source_url,
            reference_documents=[],
            community=listing.community_key,
            created_at=now,
        )
        if listing.community_key and config.get("community_research", {}).get("mode") == "stub":
            developer = listing.spa_data.get("developer") or ""
            research_key = (listing.community_key, developer)
            if research_key in queued_community_research:
                continue
            existing = (
                db.query(DBCommunityResearch)
                .filter(
                    DBCommunityResearch.project_name == listing.community_key,
                    DBCommunityResearch.developer == developer,
                )
                .first()
            )
            if not existing:
                queued_community_research.add(research_key)
                db.add(
                    DBCommunityResearch(
                        project_name=listing.community_key,
                        developer=developer,
                        status="approved",
                        file_path=f"harness/{listing.community_key}.json",
                        source_urls=[listing.source_url],
                        audit_flags=[],
                        research_confidence=1.0,
                        last_researched_at=now,
                    )
                )

    db.commit()
    return seed


def get_harness_seed(
    db,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
) -> HarnessSeed:
    config = load_config(config_path)
    prefix = config["prefix"]
    brokerages = [
        {
            "id": b.brokerage_id,
            "name": b.name,
            "slug": b.slug,
            "brokerage_ai_number": b.brokerage_ai_number,
            "agents_ai_number": b.agents_ai_number,
        }
        for b in db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([x["id"] for x in config["brokerages"]])).all()
    ]
    agents = [
        HarnessAgent(
            brokerage_id=a.brokerage_id,
            user_id=a.user_id,
            profile_id=a.profile_id,
            member_id=f"{prefix}_member_{a.user_id}",
            chatbot_config_id=f"{prefix}_chatbot_{a.user_id}",
            full_name=a.full_name,
            display_name=a.display_name,
            phone=a.whatsapp_phone,
            rera_broker_card_number=a.rera_broker_card_number,
        )
        for a in db.query(DBAgentProfile).filter(DBAgentProfile.user_id.like(f"{prefix}_agent_%")).all()
    ]
    listings = [
        HarnessListing(
            listing_id=l.listing_id,
            brokerage_id=l.brokerage_id,
            assigned_agent_id=l.assigned_agent_id,
            source_url=l.source_url,
            property_type=l.property_type,
            asking_price_aed=l.seller_asking_price,
            threshold_discount_pct=(l.processing_stages or {}).get("harness", {}).get("metadata", {}).get("threshold_discount_pct", 0),
            notification_threshold_aed=l.notification_threshold_aed,
            commission_rate=l.commission_rate,
            additional_fees=l.additional_fees or [],
            spa_data=l.spa_data,
            media_urls=l.media_urls or [],
            community_key=l.community,
            missing_fields=(l.processing_stages or {}).get("harness", {}).get("missing_fields", []),
        )
        for l in db.query(DBListing).filter(DBListing.listing_id.like(f"{prefix}_listing_%")).all()
    ]
    return HarnessSeed(brokerages=brokerages, agents=agents, listings=listings)


def teardown_harness(db, config_path: Path | str = DEFAULT_CONFIG_PATH) -> None:
    assert_safe_test_database(database_url=str(db.get_bind().url), operation="canonical harness teardown")
    config = load_config(config_path)
    prefix = config["prefix"]
    brokerage_ids = [b["id"] for b in config["brokerages"]]
    listing_ids = [row.listing_id for row in db.query(DBListing).filter(DBListing.listing_id.like(f"{prefix}_listing_%")).all()]
    conversation_ids = [row.conversation_id for row in db.query(DBConversation).filter(DBConversation.listing_id.in_(listing_ids)).all()] if listing_ids else []

    if conversation_ids:
        db.query(DBAgentMessageRoute).filter(DBAgentMessageRoute.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBSuspiciousActivity).filter(DBSuspiciousActivity.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBMessage).filter(DBMessage.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBOfferRecord).filter(DBOfferRecord.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBConversation).filter(DBConversation.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
    if listing_ids:
        db.query(DBListingAmenity).filter(DBListingAmenity.listing_id.in_(listing_ids)).delete(synchronize_session=False)
        db.query(DBListingAnchorTime).filter(DBListingAnchorTime.listing_id.in_(listing_ids)).delete(synchronize_session=False)
        db.query(DBEnrichmentRun).filter(DBEnrichmentRun.listing_id.in_(listing_ids)).delete(synchronize_session=False)
        db.query(DBBuyerListingMatch).filter(DBBuyerListingMatch.listing_id.in_(listing_ids)).delete(synchronize_session=False)
        db.query(DBListingInquiry).filter(DBListingInquiry.listing_id.in_(listing_ids)).delete(synchronize_session=False)
        db.query(DBListing).filter(DBListing.listing_id.in_(listing_ids)).delete(synchronize_session=False)
    db.query(DBBuyerPreferenceProfile).filter(DBBuyerPreferenceProfile.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
    db.query(DBCommunityResearch).filter(DBCommunityResearch.file_path.like("harness/%")).delete(synchronize_session=False)
    db.query(DBAgentChatbotConfig).filter(DBAgentChatbotConfig.agent_user_id.like(f"{prefix}_agent_%")).delete(synchronize_session=False)
    db.query(DBAgentVerification).filter(DBAgentVerification.user_id.like(f"{prefix}_agent_%")).delete(synchronize_session=False)
    db.query(DBAgentProfile).filter(DBAgentProfile.user_id.like(f"{prefix}_agent_%")).delete(synchronize_session=False)
    db.query(DBBrokerageMember).filter(DBBrokerageMember.user_id.like(f"{prefix}_agent_%")).delete(synchronize_session=False)
    db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_(brokerage_ids)).delete(synchronize_session=False)
    db.commit()
