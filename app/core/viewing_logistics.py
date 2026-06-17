from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.brokerage_access import record_compliance_event
from app.db.session import safe_commit
from app.models.db_models import (
    DBAgentAvailabilityBlock,
    DBBuildingProfile,
    DBComplianceEvent,
    DBConversation,
    DBListing,
    DBListingLogistics,
    DBMessage,
    DBTenantConsent,
    DBViewing,
)


TENANT_PII_FIELDS = {"name", "whatsapp_number", "phone", "email"}
DEFAULT_WORK_START = "10:00"
DEFAULT_WORK_END = "18:00"
DEFAULT_PREP_BUFFER_MIN = 15
DEFAULT_VIEWING_DURATION_MIN = 45


@dataclass
class SlotProposal:
    starts_at: datetime
    ends_at: datetime
    buffer_minutes: int
    tenant_notice_required: bool
    constraints: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat(),
            "buffer_minutes": self.buffer_minutes,
            "tenant_notice_required": self.tenant_notice_required,
            "constraints": self.constraints,
        }


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return cleaned or "unknown"


def _spa(listing: DBListing) -> dict[str, Any]:
    return listing.spa_data or {}


def listing_building_name(listing: DBListing) -> str:
    spa = _spa(listing)
    for key in ("building_or_project", "building", "project", "project_name"):
        if spa.get(key):
            return str(spa[key])
    return listing.listing_id


def listing_community_name(listing: DBListing) -> str:
    spa = _spa(listing)
    for key in ("community", "sub_community", "area", "district"):
        if spa.get(key):
            return str(spa[key])
    if listing.community:
        return listing.community
    return ""


def derive_building_key(listing: DBListing) -> str:
    return f"{_slug(listing_community_name(listing))}:{_slug(listing_building_name(listing))}"


def ensure_building_profile(db: Session, listing: DBListing) -> DBBuildingProfile:
    building_key = derive_building_key(listing)
    profile = (
        db.query(DBBuildingProfile)
        .filter(DBBuildingProfile.building_key == building_key)
        .first()
    )
    if profile:
        return profile

    profile = DBBuildingProfile(
        building_key=building_key,
        community_key=_slug(listing_community_name(listing)),
        display_name=listing_building_name(listing),
        canonical_source="provisional_slug",
        access_defaults={},
        security_defaults={},
        notice_defaults={},
        metadata_json={
            "source_listing_id": listing.listing_id,
            "canonical_id_blocker": "Choose DLD area code, Property Finder taxonomy, or another building ID source.",
        },
    )
    db.add(profile)
    safe_commit(db)
    db.refresh(profile)
    return profile


def get_listing_logistics(db: Session, listing_id: str, brokerage_id: str) -> Optional[DBListingLogistics]:
    return (
        db.query(DBListingLogistics)
        .filter(
            DBListingLogistics.listing_id == listing_id,
            DBListingLogistics.brokerage_id == brokerage_id,
        )
        .first()
    )


def build_logistics_prefill(db: Session, listing: DBListing) -> dict[str, Any]:
    building = ensure_building_profile(db, listing)
    return {
        "building_id": building.building_id,
        "building_key": building.building_key,
        "display_name": building.display_name,
        "community_key": building.community_key,
        "contributor_count": building.contributor_count,
        "confidence": building.confidence,
        "draft": {
            "access": dict(building.access_defaults or {}),
            "keys": {},
            "tenant": {},
            "owner_permissions": {},
        },
        "source": "building_profile" if building.contributor_count else "empty_building_profile",
    }


def _copy_known(mapping: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: mapping.get(key) for key in keys if mapping.get(key) is not None}


def _building_defaults_from_logistics(logistics: DBListingLogistics) -> tuple[dict, dict, dict]:
    access = logistics.access or {}
    tenant = logistics.tenant or {}
    access_defaults = _copy_known(access, (
        "type",
        "noc_required",
        "advance_notice_hours",
        "visitor_parking_pass_required",
        "buyer_emirates_id_preregistration_required",
        "security_office_hours",
    ))
    security_defaults = _copy_known(access, (
        "security_office_hours",
        "visitor_parking_pass_required",
        "buyer_emirates_id_preregistration_required",
    ))
    notice_defaults = {}
    if tenant.get("status") == "tenanted":
        notice_defaults["tenant_notice_hours"] = tenant.get("notice_period_hours", 48)
    if access.get("advance_notice_hours") is not None:
        notice_defaults["building_advance_notice_hours"] = access.get("advance_notice_hours")
    return access_defaults, security_defaults, notice_defaults


def _recalculate_building_confidence(db: Session, building: DBBuildingProfile) -> None:
    contributor_count = (
        db.query(DBListingLogistics)
        .filter(
            DBListingLogistics.building_id == building.building_id,
            DBListingLogistics.confirmed_at.isnot(None),
        )
        .count()
    )
    building.contributor_count = contributor_count
    building.confidence = min(0.95, 0.35 + contributor_count * 0.2) if contributor_count else 0.0
    building.updated_at = datetime.utcnow()


def upsert_listing_logistics(
    db: Session,
    *,
    listing: DBListing,
    brokerage_id: str,
    agent_user_id: str,
    access: Optional[dict[str, Any]] = None,
    keys: Optional[dict[str, Any]] = None,
    tenant: Optional[dict[str, Any]] = None,
    owner_permissions: Optional[dict[str, Any]] = None,
    confirmed: bool = True,
) -> DBListingLogistics:
    if keys and keys.get("lockbox_code"):
        raise ValueError("Raw lockbox_code is not accepted. Store lockbox_code_encrypted after KMS is configured.")

    building = ensure_building_profile(db, listing)
    logistics = get_listing_logistics(db, listing.listing_id, brokerage_id)
    previous_tenant = dict(logistics.tenant or {}) if logistics else {}
    if not logistics:
        logistics = DBListingLogistics(
            brokerage_id=brokerage_id,
            listing_id=listing.listing_id,
            building_id=building.building_id,
            agent_user_id=agent_user_id,
            access={},
            keys={},
            tenant={},
            owner_permissions={},
        )
        db.add(logistics)

    logistics.building_id = building.building_id
    logistics.agent_user_id = agent_user_id or logistics.agent_user_id
    if access is not None:
        logistics.access = access
    if keys is not None:
        logistics.keys = keys
    if tenant is not None:
        logistics.tenant = tenant
    if owner_permissions is not None:
        logistics.owner_permissions = owner_permissions
    if confirmed:
        logistics.confirmed_at = logistics.confirmed_at or datetime.utcnow()
    logistics.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(logistics)

    if confirmed:
        access_defaults, security_defaults, notice_defaults = _building_defaults_from_logistics(logistics)
        if access_defaults:
            building.access_defaults = {**(building.access_defaults or {}), **access_defaults}
        if security_defaults:
            building.security_defaults = {**(building.security_defaults or {}), **security_defaults}
        if notice_defaults:
            building.notice_defaults = {**(building.notice_defaults or {}), **notice_defaults}
        _recalculate_building_confidence(db, building)

    if tenant is not None and _tenant_contact_changed(previous_tenant, tenant):
        record_tenant_contact_update(
            db,
            brokerage_id=brokerage_id,
            listing_id=listing.listing_id,
            actor_user_id=agent_user_id,
            tenant=tenant,
        )
    safe_commit(db)
    db.refresh(logistics)
    return logistics


def _tenant_contact_changed(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    return any((previous or {}).get(field) != (current or {}).get(field) for field in TENANT_PII_FIELDS)


def _tenant_contact_key(tenant: dict[str, Any]) -> Optional[str]:
    value = tenant.get("whatsapp_number") or tenant.get("phone") or tenant.get("email")
    return str(value).strip().lower() if value else None


def record_tenant_contact_update(
    db: Session,
    *,
    brokerage_id: str,
    listing_id: str,
    actor_user_id: str,
    tenant: dict[str, Any],
) -> Optional[DBTenantConsent]:
    contact_key = _tenant_contact_key(tenant)
    if not contact_key:
        record_compliance_event(
            db,
            brokerage_id=brokerage_id,
            listing_id=listing_id,
            actor_user_id=actor_user_id,
            event_type="tenant_logistics_updated",
            direction="system",
            details={"tenant_status": tenant.get("status"), "contact_present": False},
        )
        return None

    now = datetime.utcnow()
    consent = (
        db.query(DBTenantConsent)
        .filter(
            DBTenantConsent.brokerage_id == brokerage_id,
            DBTenantConsent.listing_id == listing_id,
            DBTenantConsent.tenant_contact_key == contact_key,
        )
        .first()
    )
    if not consent:
        consent = DBTenantConsent(
            brokerage_id=brokerage_id,
            listing_id=listing_id,
            tenant_contact_key=contact_key,
            lawful_basis=tenant.get("lawful_basis") or "listing_viewing_coordination",
            opt_in_status=tenant.get("opt_in_status") or "pending",
            opt_in_requested_at=now,
            retention_until=now + timedelta(days=int(tenant.get("retention_days") or 90)),
            visible_to_agent_user_id=actor_user_id,
            metadata_json={"preferred_contact_method": tenant.get("preferred_contact_method")},
        )
        db.add(consent)
    else:
        consent.lawful_basis = tenant.get("lawful_basis") or consent.lawful_basis
        consent.opt_in_status = tenant.get("opt_in_status") or consent.opt_in_status
        consent.retention_until = consent.retention_until or (now + timedelta(days=90))
        consent.visible_to_agent_user_id = consent.visible_to_agent_user_id or actor_user_id
        consent.updated_at = now

    record_compliance_event(
        db,
        brokerage_id=brokerage_id,
        listing_id=listing_id,
        actor_user_id=actor_user_id,
        event_type="tenant_contact_recorded",
        direction="system",
        details={
            "contact_key": contact_key,
            "lawful_basis": consent.lawful_basis,
            "opt_in_status": consent.opt_in_status,
            "retention_until": consent.retention_until.isoformat() if consent.retention_until else None,
        },
    )
    safe_commit(db)
    db.refresh(consent)
    return consent


def redact_logistics(logistics: DBListingLogistics, *, can_view_tenant_pii: bool) -> dict[str, Any]:
    tenant = dict(logistics.tenant or {})
    if not can_view_tenant_pii:
        for field in TENANT_PII_FIELDS:
            if field in tenant:
                tenant[field] = None
        tenant["redacted"] = True
    return {
        "logistics_id": logistics.logistics_id,
        "listing_id": logistics.listing_id,
        "building_id": logistics.building_id,
        "agent_user_id": logistics.agent_user_id,
        "access": logistics.access or {},
        "keys": logistics.keys or {},
        "tenant": tenant,
        "owner_permissions": logistics.owner_permissions or {},
        "confirmed_at": logistics.confirmed_at.isoformat() if logistics.confirmed_at else None,
        "updated_at": logistics.updated_at.isoformat() if logistics.updated_at else None,
    }


def _parse_hhmm(value: str) -> tuple[int, int]:
    hour, minute = (value or "00:00").split(":", 1)
    return int(hour), int(minute)


def _at(date_value: datetime, hhmm: str) -> datetime:
    hour, minute = _parse_hhmm(hhmm)
    return date_value.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _availability_for_day(
    db: Session,
    *,
    brokerage_id: str,
    agent_user_id: str,
    day: datetime,
) -> tuple[list[tuple[datetime, datetime]], list[tuple[datetime, datetime]], int]:
    blocks = (
        db.query(DBAgentAvailabilityBlock)
        .filter(
            DBAgentAvailabilityBlock.brokerage_id == brokerage_id,
            DBAgentAvailabilityBlock.agent_user_id == agent_user_id,
            DBAgentAvailabilityBlock.active.is_(True),
        )
        .all()
    )
    day_str = day.date().isoformat()
    weekday = day.weekday()
    working: list[tuple[datetime, datetime]] = []
    busy: list[tuple[datetime, datetime]] = []
    prep_floor = DEFAULT_PREP_BUFFER_MIN

    for block in blocks:
        if block.date and block.date != day_str:
            continue
        if block.date is None and block.weekday is not None and block.weekday != weekday:
            continue
        start = _at(day, block.start_time)
        end = _at(day, block.end_time)
        if end <= start:
            continue
        if block.block_type == "working_hours":
            working.append((start, end))
            meta = block.metadata_json or {}
            prep_floor = max(prep_floor, int(meta.get("prep_buffer_minutes") or DEFAULT_PREP_BUFFER_MIN))
        elif block.block_type in {"time_off", "busy_override"}:
            busy.append((start, end))

    if not working:
        working = [(_at(day, DEFAULT_WORK_START), _at(day, DEFAULT_WORK_END))]
    return working, busy, prep_floor


def _security_windows(logistics: Optional[DBListingLogistics], day: datetime) -> list[tuple[datetime, datetime]]:
    access = (logistics.access or {}) if logistics else {}
    hours = access.get("security_office_hours") or {}
    start = hours.get("start") or DEFAULT_WORK_START
    end = hours.get("end") or DEFAULT_WORK_END
    return [(_at(day, start), _at(day, end))]


def _window_intersections(
    first: list[tuple[datetime, datetime]],
    second: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    windows = []
    for a_start, a_end in first:
        for b_start, b_end in second:
            start = max(a_start, b_start)
            end = min(a_end, b_end)
            if end > start:
                windows.append((start, end))
    return windows


def _overlaps(start: datetime, end: datetime, windows: list[tuple[datetime, datetime]]) -> bool:
    return any(start < busy_end and end > busy_start for busy_start, busy_end in windows)


def _rush_hour_multiplier(start: datetime) -> float:
    minutes = start.hour * 60 + start.minute
    if 7 * 60 + 30 <= minutes <= 9 * 60 + 30:
        return 1.35
    if 17 * 60 <= minutes <= 20 * 60:
        return 1.35
    return 1.0


def compute_travel_buffer_minutes(
    *,
    origin_community: Optional[str],
    destination_community: Optional[str],
    starts_at: datetime,
    prep_floor_minutes: int,
    pair_lookup: Optional[dict[str, int]] = None,
) -> int:
    origin = _slug(origin_community or "")
    dest = _slug(destination_community or "")
    pair_key = f"{origin}:{dest}"
    base = (pair_lookup or {}).get(pair_key)
    if base is None:
        base = 15 if origin and origin == dest else 30
    return max(prep_floor_minutes, int(round(base * _rush_hour_multiplier(starts_at))))


def _notice_cutoff(now: datetime, logistics: Optional[DBListingLogistics]) -> tuple[datetime, bool, list[str]]:
    constraints: list[str] = []
    access = (logistics.access or {}) if logistics else {}
    tenant = (logistics.tenant or {}) if logistics else {}
    required_hours = 0
    tenant_notice_required = tenant.get("status") == "tenanted"
    if tenant_notice_required:
        notice_hours = int(tenant.get("notice_period_hours") or 48)
        required_hours = max(required_hours, notice_hours)
        constraints.append(f"tenant_notice_{notice_hours}h")
    if access.get("advance_notice_hours") is not None:
        building_hours = int(access.get("advance_notice_hours") or 0)
        required_hours = max(required_hours, building_hours)
        constraints.append(f"building_notice_{building_hours}h")
    return now + timedelta(hours=required_hours), tenant_notice_required, constraints


def propose_viewing_slots(
    db: Session,
    *,
    brokerage_id: str,
    agent_user_id: str,
    listing: DBListing,
    logistics: Optional[DBListingLogistics],
    now: Optional[datetime] = None,
    count: int = 3,
    duration_minutes: int = DEFAULT_VIEWING_DURATION_MIN,
    origin_community: Optional[str] = None,
    pair_lookup: Optional[dict[str, int]] = None,
    external_busy_windows: Optional[list[tuple[datetime, datetime]]] = None,
) -> list[SlotProposal]:
    now = (now or datetime.utcnow()).replace(second=0, microsecond=0)
    earliest, tenant_notice_required, notice_constraints = _notice_cutoff(now, logistics)
    destination_community = listing_community_name(listing)
    proposals: list[SlotProposal] = []

    for day_offset in range(0, 21):
        day = now + timedelta(days=day_offset)
        working, busy, prep_floor = _availability_for_day(
            db,
            brokerage_id=brokerage_id,
            agent_user_id=agent_user_id,
            day=day,
        )
        busy = [*busy, *(external_busy_windows or [])]
        windows = _window_intersections(working, _security_windows(logistics, day))
        for win_start, win_end in windows:
            cursor = max(win_start, earliest)
            minute_remainder = cursor.minute % 30
            if minute_remainder:
                cursor += timedelta(minutes=30 - minute_remainder)
            cursor = cursor.replace(second=0, microsecond=0)
            while cursor + timedelta(minutes=duration_minutes) <= win_end:
                buffer_min = compute_travel_buffer_minutes(
                    origin_community=origin_community,
                    destination_community=destination_community,
                    starts_at=cursor,
                    prep_floor_minutes=prep_floor,
                    pair_lookup=pair_lookup,
                )
                slot_start = cursor
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                protected_start = slot_start - timedelta(minutes=buffer_min)
                if protected_start >= now and not _overlaps(protected_start, slot_end, busy):
                    proposals.append(SlotProposal(
                        starts_at=slot_start,
                        ends_at=slot_end,
                        buffer_minutes=buffer_min,
                        tenant_notice_required=tenant_notice_required,
                        constraints=[*notice_constraints, f"prep_or_travel_buffer_{buffer_min}m"],
                    ))
                    if len(proposals) >= count:
                        return proposals
                cursor += timedelta(minutes=30)
    return proposals


def create_viewing_proposal(
    db: Session,
    *,
    conversation: DBConversation,
    listing: DBListing,
    agent_user_id: str,
    slots: list[SlotProposal],
) -> DBViewing:
    viewing = DBViewing(
        brokerage_id=conversation.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=listing.listing_id,
        buyer_phone=conversation.buyer_phone,
        agent_user_id=agent_user_id,
        status="proposed",
        tenant_notice_required=any(slot.tenant_notice_required for slot in slots),
        metadata_json={"proposed_slots": [slot.as_dict() for slot in slots]},
    )
    db.add(viewing)
    safe_commit(db)
    db.refresh(viewing)
    return viewing


def confirm_viewing(
    db: Session,
    *,
    viewing: DBViewing,
    scheduled_for: datetime,
    logistics: Optional[DBListingLogistics],
    confirmed_by_user_id: str,
) -> DBViewing:
    tenant = (logistics.tenant or {}) if logistics else {}
    viewing.scheduled_for = scheduled_for
    viewing.status = "confirmed"
    viewing.tenant_notice_required = tenant.get("status") == "tenanted"
    viewing.updated_at = datetime.utcnow()
    viewing.metadata_json = {
        **(viewing.metadata_json or {}),
        "confirmed_by_user_id": confirmed_by_user_id,
        "confirmation_status": {
            "buyer": "draft_pending",
            "tenant": "draft_pending" if viewing.tenant_notice_required else "not_required",
            "calendar": "provider_pending",
        },
        "logistics_summary": logistics_summary(logistics),
    }
    safe_commit(db)
    db.refresh(viewing)
    return viewing


def logistics_summary(logistics: Optional[DBListingLogistics]) -> dict[str, Any]:
    if not logistics:
        return {"configured": False}
    access = logistics.access or {}
    keys = logistics.keys or {}
    tenant = logistics.tenant or {}
    return {
        "configured": True,
        "access_type": access.get("type"),
        "meet_point": access.get("meet_point") or access.get("type"),
        "parking": "pass required" if access.get("visitor_parking_pass_required") else "not specified",
        "key_location": keys.get("location"),
        "key_kit": keys.get("key_kit_checklist") or [],
        "tenant_status": tenant.get("status") or "unknown",
        "tenant_notice_hours": tenant.get("notice_period_hours") if tenant.get("status") == "tenanted" else None,
    }


def generate_pre_viewing_brief(
    db: Session,
    *,
    viewing: DBViewing,
    conversation: DBConversation,
    listing: DBListing,
    logistics: Optional[DBListingLogistics],
) -> dict[str, Any]:
    spa = listing.spa_data or {}
    summary = conversation.ai_summary or {}
    messages = (
        db.query(DBMessage)
        .filter(DBMessage.conversation_id == conversation.conversation_id)
        .order_by(DBMessage.timestamp.desc())
        .limit(8)
        .all()
    )
    user_messages = [m.content for m in messages if m.role == "user"]
    priorities = summary.get("topics") or summary.get("stated_priorities") or _infer_priorities(user_messages)
    highlights = _property_highlights(spa, listing, priorities)
    objections = _likely_objections(user_messages, listing, logistics)
    return {
        "viewing_id": viewing.viewing_id,
        "scheduled_for": viewing.scheduled_for.isoformat() if viewing.scheduled_for else None,
        "buyer_profile": {
            "name": conversation.buyer_name,
            "phone": conversation.buyer_phone,
            "budget_aed": conversation.detected_budget,
            "summary": summary.get("one_line") or summary.get("next_step_hint"),
            "stated_priorities": priorities,
        },
        "property": {
            "listing_id": listing.listing_id,
            "project": spa.get("project"),
            "unit_number": spa.get("unit_number"),
            "asking_price_aed": listing.seller_asking_price or spa.get("purchase_price_aed"),
            "bedrooms": spa.get("bedrooms"),
            "property_type": spa.get("property_type"),
        },
        "property_highlights": highlights,
        "likely_objections": objections,
        "comparable_units_already_viewed": summary.get("viewed_units") or [],
        "logistics": logistics_summary(logistics),
        "confirmation_status": (viewing.metadata_json or {}).get("confirmation_status", {}),
    }


def _infer_priorities(messages: list[str]) -> list[str]:
    joined = " ".join(messages).lower()
    priorities = []
    for keyword in ("school", "metro", "handover", "finance", "yield", "view", "parking", "tenant"):
        if keyword in joined:
            priorities.append(keyword)
    return priorities or ["fit", "price", "timing"]


def _property_highlights(spa: dict[str, Any], listing: DBListing, priorities: list[str]) -> list[str]:
    highlights = []
    if spa.get("bedrooms"):
        highlights.append(f"{spa.get('bedrooms')}-bed layout")
    if listing.seller_asking_price or spa.get("purchase_price_aed"):
        highlights.append(f"AED {(listing.seller_asking_price or spa.get('purchase_price_aed')):,.0f} asking price")
    if "handover" in priorities and spa.get("estimated_completion_date"):
        highlights.append(f"Handover target: {spa.get('estimated_completion_date')}")
    if spa.get("parking"):
        highlights.append(f"Parking: {spa.get('parking')}")
    return highlights[:5]


def _likely_objections(
    messages: list[str],
    listing: DBListing,
    logistics: Optional[DBListingLogistics],
) -> list[dict[str, str]]:
    joined = " ".join(messages).lower()
    objections = []
    if "finance" in joined or "mortgage" in joined:
        objections.append({
            "objection": "Financing terms",
            "response": "Keep bank-specific LTV/rate details with the lender; confirm property-side readiness and documents.",
        })
    if logistics and (logistics.tenant or {}).get("status") == "tenanted":
        objections.append({
            "objection": "Vacant possession timing",
            "response": "Do not imply automatic vacancy; confirm notice status and tenant cooperation before committing.",
        })
    if listing.property_type == "off_plan":
        objections.append({
            "objection": "Move-in timing",
            "response": "Anchor to the SPA handover date and be explicit if it misses the buyer's target school year.",
        })
    return objections or [{
        "objection": "Price and comparables",
        "response": "Use current listing and transaction data before taking a firm pricing position.",
    }]


def _format_datetime_for_message(value: Optional[datetime]) -> str:
    if not value:
        return "the confirmed viewing time"
    return value.strftime("%A %d %b at %I:%M %p").replace(" 0", " ")


def _project_label(listing: DBListing) -> str:
    spa = listing.spa_data or {}
    project = spa.get("project") or "the property"
    unit = spa.get("unit_number")
    return f"{project}, unit {unit}" if unit else str(project)


def _tenant_label(logistics: Optional[DBListingLogistics]) -> str:
    tenant = (logistics.tenant or {}) if logistics else {}
    return tenant.get("name") or "the tenant"


def generate_notification_drafts(
    *,
    viewing: DBViewing,
    conversation: DBConversation,
    listing: DBListing,
    logistics: Optional[DBListingLogistics],
    draft_types: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    """
    Deterministic draft-and-approve copy for viewing logistics.

    This intentionally does not send messages. Sending stays behind a future
    approval path once WhatsApp templates and tenant opt-in handling are wired.
    """
    all_types = [
        "buyer_confirmation_t24",
        "buyer_reminder_t1",
        "tenant_notice",
        "running_late",
        "reschedule",
    ]
    selected = draft_types or all_types
    scheduled = _format_datetime_for_message(viewing.scheduled_for)
    project = _project_label(listing)
    buyer_name = conversation.buyer_name or "there"
    buyer_phone = conversation.buyer_phone
    logistics_data = logistics_summary(logistics)
    meet_point = logistics_data.get("meet_point") or "the agreed meet point"
    parking = logistics_data.get("parking") or "parking details to be confirmed"
    tenant = (logistics.tenant or {}) if logistics else {}
    tenant_contact = tenant.get("whatsapp_number") or tenant.get("phone") or tenant.get("email")
    tenant_name = _tenant_label(logistics)
    notice_hours = tenant.get("notice_period_hours") or logistics_data.get("tenant_notice_hours") or 48

    templates = {
        "buyer_confirmation_t24": {
            "recipient_type": "buyer",
            "recipient": buyer_phone,
            "body": (
                f"Hi {buyer_name}, confirming your viewing for {project} on {scheduled}. "
                f"We'll meet at {meet_point}. {parking.capitalize()}."
            ),
        },
        "buyer_reminder_t1": {
            "recipient_type": "buyer",
            "recipient": buyer_phone,
            "body": (
                f"Hi {buyer_name}, quick reminder for your viewing of {project} at {scheduled}. "
                "Please bring your Emirates ID if building security asks for registration."
            ),
        },
        "tenant_notice": {
            "recipient_type": "tenant",
            "recipient": tenant_contact,
            "body": (
                f"Hi {tenant_name}, this is a viewing notice for {project} scheduled for {scheduled}. "
                f"We are giving at least {notice_hours} hours' notice. Please confirm whether this time works."
            ),
        },
        "running_late": {
            "recipient_type": "buyer_and_tenant",
            "recipient": "buyer_and_tenant",
            "body": (
                f"Running about 10 minutes late for the {project} viewing. "
                "The viewing is still going ahead; I will update you again if timing changes."
            ),
        },
        "reschedule": {
            "recipient_type": "buyer_and_tenant",
            "recipient": "buyer_and_tenant",
            "body": (
                f"We need to reschedule the {project} viewing. "
                "I'll propose a new time that still respects the building and tenant notice window."
            ),
        },
    }

    drafts = []
    now = datetime.utcnow().isoformat()
    for draft_type in selected:
        template = templates.get(draft_type)
        if not template:
            continue
        drafts.append({
            "draft_id": f"{viewing.viewing_id}:{draft_type}",
            "type": draft_type,
            "channel": "whatsapp",
            "status": "draft",
            "created_at": now,
            **template,
        })
    return drafts


def store_notification_drafts(
    db: Session,
    *,
    viewing: DBViewing,
    conversation: DBConversation,
    listing: DBListing,
    logistics: Optional[DBListingLogistics],
    draft_types: Optional[list[str]] = None,
    actor_user_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    drafts = generate_notification_drafts(
        viewing=viewing,
        conversation=conversation,
        listing=listing,
        logistics=logistics,
        draft_types=draft_types,
    )
    existing = (viewing.metadata_json or {}).get("notification_drafts") or {}
    for draft in drafts:
        existing[draft["type"]] = draft
    viewing.metadata_json = {
        **(viewing.metadata_json or {}),
        "notification_drafts": existing,
    }
    viewing.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(viewing)
    record_compliance_event(
        db,
        brokerage_id=viewing.brokerage_id,
        conversation_id=viewing.conversation_id,
        listing_id=viewing.listing_id,
        buyer_phone=viewing.buyer_phone,
        actor_user_id=actor_user_id,
        event_type="viewing_notification_drafts_generated",
        direction="system",
        details={
            "viewing_id": viewing.viewing_id,
            "draft_types": [draft["type"] for draft in drafts],
            "auto_sent": False,
        },
    )
    return drafts
