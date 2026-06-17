from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import safe_commit
from app.models.db_models import DBListing, DBPlatformAggregate

IDENTIFIER_KEYS = {
    "agent_id",
    "agent_phone",
    "agent_user_id",
    "assigned_agent_id",
    "brokerage_id",
    "buyer_name",
    "buyer_phone",
    "conversation_id",
    "email",
    "listing_id",
    "member_id",
    "phone",
    "profile_id",
    "seller_id",
    "seller_phone",
    "unit_number",
    "user_id",
    "whatsapp_phone",
}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\s().-]?){8,}")


@dataclass(frozen=True)
class AggregateSignal:
    signal_type: str
    scope_key: str
    period_key: str
    sample_count: int
    brokerage_count: int
    payload: dict[str, Any]

    def as_record_payload(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "scope_key": self.scope_key,
            "period_key": self.period_key,
            "sample_count": self.sample_count,
            "brokerage_count": self.brokerage_count,
            "payload": self.payload,
        }


def _normalise_scope_part(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"


def _round_aed(value: float | None) -> int | None:
    if value is None:
        return None
    return int(round(value / 10_000) * 10_000)


def _listing_price(listing: DBListing) -> float | None:
    spa = listing.spa_data or {}
    price = listing.seller_asking_price or spa.get("purchase_price_aed")
    return float(price) if isinstance(price, (int, float)) and price > 0 else None


def _listing_size(listing: DBListing) -> float | None:
    spa = listing.spa_data or {}
    size = spa.get("bua_sqft") or spa.get("size_sqft") or spa.get("plot_sqft")
    return float(size) if isinstance(size, (int, float)) and size > 0 else None


def _listing_group_key(listing: DBListing) -> tuple[str, str, str]:
    spa = listing.spa_data or {}
    community = listing.community or spa.get("sub_community") or spa.get("community") or spa.get("project")
    property_type = listing.property_type or spa.get("property_type") or "unknown"
    bedrooms = spa.get("bedrooms") or "unknown"
    return (
        _normalise_scope_part(community),
        _normalise_scope_part(property_type),
        _normalise_scope_part(bedrooms),
    )


def contains_identifier(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in IDENTIFIER_KEYS:
                return True
            if contains_identifier(child):
                return True
        return False
    if isinstance(value, list):
        return any(contains_identifier(child) for child in value)
    if isinstance(value, str):
        return bool(EMAIL_RE.search(value) or PHONE_RE.search(value))
    return False


def validate_aggregate_signal(signal: AggregateSignal, *, min_sample_count: int = 3) -> None:
    if signal.sample_count < min_sample_count:
        raise ValueError("aggregate sample_count is below the anonymization threshold")
    if signal.brokerage_count < 2:
        raise ValueError("aggregate must include at least two brokerages")
    if contains_identifier(signal.as_record_payload()):
        raise ValueError("aggregate payload contains a direct identifier")


def build_listing_price_aggregates(
    db: Session,
    *,
    min_sample_count: int = 3,
    period_key: str | None = None,
) -> list[AggregateSignal]:
    period = period_key or datetime.utcnow().strftime("%Y-%m")
    groups: dict[tuple[str, str, str], list[DBListing]] = defaultdict(list)
    listings = (
        db.query(DBListing)
        .filter(DBListing.brokerage_id.isnot(None))
        .all()
    )
    for listing in listings:
        if _listing_price(listing) is None:
            continue
        groups[_listing_group_key(listing)].append(listing)

    signals: list[AggregateSignal] = []
    for (community_key, property_type_key, bedrooms_key), rows in groups.items():
        brokerages = {row.brokerage_id for row in rows if row.brokerage_id}
        if len(rows) < min_sample_count or len(brokerages) < 2:
            continue

        prices = [_listing_price(row) for row in rows]
        prices = [price for price in prices if price is not None]
        sizes = [_listing_size(row) for row in rows]
        sizes = [size for size in sizes if size is not None]
        payload = {
            "community_key": community_key,
            "property_type": property_type_key,
            "bedrooms": bedrooms_key,
            "avg_asking_price_aed": _round_aed(mean(prices)),
            "min_asking_price_aed": _round_aed(min(prices)),
            "max_asking_price_aed": _round_aed(max(prices)),
            "avg_size_sqft": int(round(mean(sizes))) if sizes else None,
            "sample_count": len(rows),
            "brokerage_count": len(brokerages),
        }
        signal = AggregateSignal(
            signal_type="listing_price",
            scope_key=f"{community_key}:{property_type_key}:{bedrooms_key}",
            period_key=period,
            sample_count=len(rows),
            brokerage_count=len(brokerages),
            payload=payload,
        )
        validate_aggregate_signal(signal, min_sample_count=min_sample_count)
        signals.append(signal)
    return signals


def store_aggregate_signals(
    db: Session,
    signals: list[AggregateSignal],
    *,
    source: str = "system",
    min_sample_count: int = 3,
) -> list[DBPlatformAggregate]:
    records: list[DBPlatformAggregate] = []
    for signal in signals:
        validate_aggregate_signal(signal, min_sample_count=min_sample_count)
        record = (
            db.query(DBPlatformAggregate)
            .filter(
                DBPlatformAggregate.signal_type == signal.signal_type,
                DBPlatformAggregate.scope_key == signal.scope_key,
                DBPlatformAggregate.period_key == signal.period_key,
            )
            .first()
        )
        if not record:
            record = DBPlatformAggregate(
                signal_type=signal.signal_type,
                scope_key=signal.scope_key,
                period_key=signal.period_key,
                source=source,
            )
            db.add(record)
        record.sample_count = signal.sample_count
        record.brokerage_count = signal.brokerage_count
        record.payload = signal.payload
        record.source = source
        record.updated_at = datetime.utcnow()
        records.append(record)
    safe_commit(db)
    for record in records:
        db.refresh(record)
    return records
