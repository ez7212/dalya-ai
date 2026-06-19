"""
Onboarding API Router — controlled brokerage-first rollout.

Agents cannot self-create brokerages. Dalya creates/approves a brokerage first,
then agents join using that brokerage's signup code.
"""

from datetime import datetime
import os
from typing import Optional
import uuid

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db, safe_commit
from app.models.db_models import (
    DBAgentChatbotConfig,
    DBAgentProfile,
    DBAgentVerification,
    DBBrokerage,
    DBBrokerageMember,
)

router = APIRouter()


class BrokerageLookupRequest(BaseModel):
    signup_code: str


class ReraLookupRequest(BaseModel):
    rera_broker_card_number: str


class AgentOnboardingRequest(BaseModel):
    full_name: str
    display_name: Optional[str] = None
    whatsapp_phone: str
    rera_broker_card_number: str
    rera_card_expiry: Optional[str] = None
    broker_card_file_url: Optional[str] = None
    languages: list[str] = []
    service_areas: list[str] = []
    rera_lookup_payload: dict = {}


class ActiveBrokerageSummary(BaseModel):
    brokerage_id: str
    name: str
    role: str
    membership_id: str


class MyBrokeragesResponse(BaseModel):
    active_brokerages: list[ActiveBrokerageSummary]
    requires_selection: bool
    default_brokerage_id: Optional[str] = None


def _brokerage_context_forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "code": "brokerage_context_forbidden",
            "message": "You do not have access to this brokerage.",
        },
    )


def _clean_code(value: str) -> str:
    return value.strip().upper()


def _parse_optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid RERA card expiry date")


def _get_joinable_brokerage(db: Session, signup_code: str) -> DBBrokerage:
    brokerage = (
        db.query(DBBrokerage)
        .filter(DBBrokerage.agent_signup_code == _clean_code(signup_code))
        .first()
    )
    if not brokerage:
        raise HTTPException(
            status_code=404,
            detail="Brokerage is not registered with Dalya yet. Contact Dalya to add the brokerage before agents sign up.",
        )
    if brokerage.status != "active" or not brokerage.agent_signup_enabled:
        raise HTTPException(
            status_code=403,
            detail="Agent signup is not enabled for this brokerage yet.",
        )
    return brokerage


def _get_joinable_brokerage_by_real_estate_number(db: Session, real_estate_number: Optional[str]) -> DBBrokerage:
    if not real_estate_number:
        raise HTTPException(
            status_code=404,
            detail="DLD did not return a brokerage registration number for this RERA card.",
        )
    brokerage = (
        db.query(DBBrokerage)
        .filter(DBBrokerage.real_estate_number == real_estate_number.strip())
        .first()
    )
    if not brokerage:
        raise HTTPException(
            status_code=404,
            detail="Your registered brokerage is not active on Dalya yet. Ask your brokerage owner or team lead to contact Dalya.",
        )
    if brokerage.status != "active" or not brokerage.agent_signup_enabled:
        raise HTTPException(
            status_code=403,
            detail="Agent signup is not enabled for your registered brokerage yet.",
        )
    return brokerage


def _activate_verified_agent_if_possible(
    db: Session,
    member: Optional[DBBrokerageMember],
    profile: Optional[DBAgentProfile],
) -> bool:
    if not member or not profile:
        return False
    if profile.verification_status not in {"dld_matched", "verified"}:
        return False
    brokerage = db.get(DBBrokerage, member.brokerage_id)
    if not brokerage or brokerage.status != "active" or not brokerage.agent_signup_enabled:
        return False

    changed = False
    now = datetime.utcnow()
    if member.status != "active":
        member.status = "active"
        member.updated_at = now
        changed = True
    if profile.onboarding_status != "active":
        profile.onboarding_status = "active"
        profile.updated_at = now
        changed = True

    config = (
        db.query(DBAgentChatbotConfig)
        .filter(DBAgentChatbotConfig.agent_profile_id == profile.profile_id)
        .first()
    )
    if config and not config.active:
        config.active = True
        config.settings = {
            **(config.settings or {}),
            "activation": "dld_brokerage_match_self_healed",
        }
        config.updated_at = now
        changed = True

    if changed:
        safe_commit(db)
    return changed


def _normalise_uae_mobile(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    if not digits:
        return None
    if digits.startswith("971"):
        return f"+{digits}"
    if digits.startswith("0"):
        return f"+971{digits[1:]}"
    return f"+{digits}"


def _map_dld_card(card: dict) -> dict:
    return {
        "card_number": card.get("CardNumber"),
        "full_name_en": card.get("CardHolderNameEn"),
        "full_name_ar": card.get("CardHolderNameAr"),
        "card_issue_date": card.get("CardIssueDate"),
        "card_expiry_date": card.get("CardExpiryDate"),
        "phone": card.get("CardHolderPhone"),
        "mobile": _normalise_uae_mobile(card.get("CardHolderMobile")),
        "email": card.get("CardHolderEmail"),
        "real_estate_number": card.get("RealEstateNumber"),
        "license_number": card.get("LicenseNumber"),
        "office_name_en": card.get("OfficeNameEn"),
        "office_name_ar": card.get("OfficeNameAr"),
        "office_issue_date": card.get("OfficeIssueDate"),
        "office_expiry_date": card.get("OfficeExpiryDate"),
        "card_holder_photo": card.get("CardHolderPhoto"),
        "office_logo": card.get("OfficeLogo"),
        "office_rank": card.get("OfficeRank"),
        "card_rank": card.get("CardRank"),
        "search_match_type": card.get("SearchMatchTypeNameEn"),
    }


async def _lookup_rera_card(card_number: str) -> Optional[dict]:
    consumer_id = os.getenv("DLD_GATEWAY_CONSUMER_ID", "gkb3WvEG0rY9eilwXC0P2pTz8UzvLj9F")
    base_url = os.getenv(
        "DLD_CARD_SEARCH_URL",
        "https://gateway.dubailand.gov.ae/card/office/search",
    )
    if not consumer_id:
        return None

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            base_url,
            params={
                "searchKey": card_number.strip(),
                "consumer-id": consumer_id,
            },
        )
        response.raise_for_status()

    payload = response.json()
    errors = payload.get("Errors") or []
    if errors:
        raise HTTPException(status_code=502, detail="DLD lookup returned an error")
    cards = ((payload.get("Response") or {}).get("Cards") or [])
    if not cards:
        return None
    return _map_dld_card(cards[0])


@router.get("/onboarding/me")
async def onboarding_status(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_brokerage_id: Optional[str] = Header(default=None, alias="X-Brokerage-Id"),
):
    active_memberships = (
        db.query(DBBrokerageMember, DBBrokerage)
        .join(DBBrokerage, DBBrokerage.brokerage_id == DBBrokerageMember.brokerage_id)
        .filter(
            DBBrokerageMember.user_id == user.id,
            DBBrokerageMember.status == "active",
            DBBrokerage.status == "active",
        )
        .order_by(DBBrokerage.name.asc(), DBBrokerageMember.created_at.asc())
        .all()
    )
    active_brokerages = [
        {
            "brokerage_id": brokerage.brokerage_id,
            "name": brokerage.name,
            "role": membership.role,
            "membership_id": membership.member_id,
        }
        for membership, brokerage in active_memberships
    ]

    requested_brokerage_id = x_brokerage_id.strip() if x_brokerage_id else None
    selected_member: DBBrokerageMember | None = None
    selected_brokerage: DBBrokerage | None = None
    requires_selection = False

    if requested_brokerage_id:
        for membership, brokerage in active_memberships:
            if membership.brokerage_id == requested_brokerage_id:
                selected_member = membership
                selected_brokerage = brokerage
                break
        if selected_member is None:
            raise _brokerage_context_forbidden()
    elif len(active_memberships) == 1:
        selected_member, selected_brokerage = active_memberships[0]
    elif len(active_memberships) > 1:
        requires_selection = True
    else:
        selected_member = (
            db.query(DBBrokerageMember)
            .filter(DBBrokerageMember.user_id == user.id)
            .order_by(DBBrokerageMember.created_at.asc())
            .first()
        )
        selected_brokerage = db.get(DBBrokerage, selected_member.brokerage_id) if selected_member else None

    member = selected_member
    profile = (
        db.query(DBAgentProfile)
        .filter(DBAgentProfile.user_id == user.id)
        .order_by(DBAgentProfile.created_at.asc())
        .first()
    )
    _activate_verified_agent_if_possible(db, member, profile)
    if member:
        db.refresh(member)
    if profile:
        db.refresh(profile)
    brokerage = selected_brokerage
    return {
        "has_profile": profile is not None,
        "member_status": member.status if member else None,
        "role": member.role if member else None,
        "brokerage": {
            "brokerage_id": brokerage.brokerage_id,
            "name": brokerage.name,
            "slug": brokerage.slug,
        } if brokerage else None,
        "profile": {
            "profile_id": profile.profile_id,
            "full_name": profile.full_name,
            "display_name": profile.display_name,
            "whatsapp_phone": profile.whatsapp_phone,
            "rera_broker_card_number": profile.rera_broker_card_number,
            "verification_status": profile.verification_status,
            "onboarding_status": profile.onboarding_status,
        } if profile else None,
        "can_access_agent_workspace": bool(member and member.status == "active"),
        "active_brokerages": active_brokerages,
        "requires_selection": requires_selection,
        "default_brokerage_id": active_brokerages[0]["brokerage_id"] if len(active_brokerages) == 1 else None,
    }


@router.get("/me/brokerages", response_model=MyBrokeragesResponse)
async def my_brokerages(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memberships = (
        db.query(DBBrokerageMember, DBBrokerage)
        .join(DBBrokerage, DBBrokerage.brokerage_id == DBBrokerageMember.brokerage_id)
        .filter(
            DBBrokerageMember.user_id == user.id,
            DBBrokerageMember.status == "active",
            DBBrokerage.status == "active",
        )
        .order_by(DBBrokerage.name.asc(), DBBrokerageMember.created_at.asc())
        .all()
    )
    active_brokerages = [
        ActiveBrokerageSummary(
            brokerage_id=brokerage.brokerage_id,
            name=brokerage.name,
            role=membership.role,
            membership_id=membership.member_id,
        )
        for membership, brokerage in memberships
    ]
    return MyBrokeragesResponse(
        active_brokerages=active_brokerages,
        requires_selection=len(active_brokerages) > 1,
        default_brokerage_id=active_brokerages[0].brokerage_id if len(active_brokerages) == 1 else None,
    )


@router.post("/onboarding/brokerage-lookup")
async def brokerage_lookup(
    body: BrokerageLookupRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = user
    brokerage = _get_joinable_brokerage(db, body.signup_code)
    return {
        "brokerage_id": brokerage.brokerage_id,
        "name": brokerage.name,
        "slug": brokerage.slug,
    }


@router.post("/onboarding/rera-lookup")
async def rera_lookup(
    body: ReraLookupRequest,
    user: CurrentUser = Depends(get_current_user),
):
    _ = user
    card_number = body.rera_broker_card_number.strip()
    if not card_number:
        raise HTTPException(status_code=422, detail="RERA broker card number is required")

    try:
        card = await _lookup_rera_card(card_number)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"DLD lookup failed: {exc}") from exc

    if not card:
        raise HTTPException(status_code=404, detail="No RERA broker card found for that number")

    return {
        "found": True,
        "agent": card,
    }


@router.post("/onboarding/rera-brokerage-lookup")
async def rera_brokerage_lookup(
    body: ReraLookupRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = user
    card_number = body.rera_broker_card_number.strip()
    if not card_number:
        raise HTTPException(status_code=422, detail="RERA broker card number is required")

    try:
        card = await _lookup_rera_card(card_number)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"DLD lookup failed: {exc}") from exc

    if not card:
        raise HTTPException(status_code=404, detail="No RERA broker card found for that number")

    brokerage = _get_joinable_brokerage_by_real_estate_number(db, card.get("real_estate_number"))
    return {
        "found": True,
        "agent": card,
        "brokerage": {
            "brokerage_id": brokerage.brokerage_id,
            "name": brokerage.name,
            "slug": brokerage.slug,
            "real_estate_number": brokerage.real_estate_number,
        },
    }


@router.post("/onboarding/agent")
async def submit_agent_onboarding(
    body: AgentOnboardingRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dld_card = None
    try:
        dld_card = await _lookup_rera_card(body.rera_broker_card_number)
    except Exception:
        dld_card = None
    brokerage = _get_joinable_brokerage_by_real_estate_number(
        db,
        (dld_card or body.rera_lookup_payload or {}).get("real_estate_number"),
    )

    full_name = (body.full_name or (dld_card or {}).get("full_name_en") or "").strip()
    display_name = (body.display_name or full_name).strip()
    whatsapp_phone = (body.whatsapp_phone or (dld_card or {}).get("mobile") or "").strip()
    rera_number = body.rera_broker_card_number.strip()
    rera_expiry = body.rera_card_expiry or (dld_card or {}).get("card_expiry_date")

    if not full_name:
        raise HTTPException(status_code=422, detail="Full name is required")
    if not whatsapp_phone:
        raise HTTPException(status_code=422, detail="WhatsApp phone number is required")
    if not rera_number:
        raise HTTPException(status_code=422, detail="RERA broker card number is required")

    member = (
        db.query(DBBrokerageMember)
        .filter(
            DBBrokerageMember.brokerage_id == brokerage.brokerage_id,
            DBBrokerageMember.user_id == user.id,
        )
        .first()
    )
    if not member:
        member = DBBrokerageMember(
            member_id=str(uuid.uuid4()),
            brokerage_id=brokerage.brokerage_id,
            user_id=user.id,
            email=user.email,
            display_name=display_name,
            phone=whatsapp_phone,
            role="agent",
            status="active",
            settings={"source": "agent_onboarding"},
        )
        db.add(member)
    else:
        member.email = user.email
        member.display_name = display_name
        member.phone = whatsapp_phone
        member.updated_at = datetime.utcnow()

    profile = (
        db.query(DBAgentProfile)
        .filter(
            DBAgentProfile.brokerage_id == brokerage.brokerage_id,
            DBAgentProfile.user_id == user.id,
        )
        .first()
    )
    if not profile:
        profile = DBAgentProfile(
            profile_id=str(uuid.uuid4()),
            brokerage_id=brokerage.brokerage_id,
            user_id=user.id,
            email=user.email,
            full_name=full_name,
            display_name=display_name,
            whatsapp_phone=whatsapp_phone,
            rera_broker_card_number=rera_number,
            rera_card_expiry=_parse_optional_datetime(rera_expiry),
            broker_card_file_url=body.broker_card_file_url or (dld_card or {}).get("card_holder_photo"),
            languages=body.languages,
            service_areas=body.service_areas,
            verification_status="dld_matched" if dld_card else "submitted",
            verification_provider="dld_gateway" if dld_card else "manual",
            chatbot_display_name=display_name,
            chatbot_handoff_phone=whatsapp_phone,
            onboarding_status="active",
            settings={
                "source": "agent_onboarding",
                "dld_lookup": dld_card or body.rera_lookup_payload or {},
            },
        )
        db.add(profile)
    else:
        profile.email = user.email
        profile.full_name = full_name
        profile.display_name = display_name
        profile.whatsapp_phone = whatsapp_phone
        profile.rera_broker_card_number = rera_number
        profile.rera_card_expiry = _parse_optional_datetime(rera_expiry)
        profile.broker_card_file_url = body.broker_card_file_url or (dld_card or {}).get("card_holder_photo")
        profile.languages = body.languages
        profile.service_areas = body.service_areas
        profile.verification_status = "dld_matched" if dld_card else profile.verification_status
        profile.verification_provider = "dld_gateway" if dld_card else profile.verification_provider
        profile.chatbot_display_name = display_name
        profile.chatbot_handoff_phone = whatsapp_phone
        profile.onboarding_status = "active"
        profile.settings = {
            **(profile.settings or {}),
            "dld_lookup": dld_card or body.rera_lookup_payload or {},
        }
        profile.updated_at = datetime.utcnow()

    safe_commit(db)
    db.refresh(profile)

    verification = DBAgentVerification(
        verification_id=str(uuid.uuid4()),
        brokerage_id=brokerage.brokerage_id,
        agent_profile_id=profile.profile_id,
        user_id=user.id,
        provider="dld_gateway" if dld_card else "manual",
        status="dld_matched" if dld_card else "submitted",
        rera_broker_card_number=rera_number,
        raw_response={
            "source": "agent_onboarding",
            "dld_lookup": dld_card or body.rera_lookup_payload or {},
        },
    )
    db.add(verification)

    config = (
        db.query(DBAgentChatbotConfig)
        .filter(DBAgentChatbotConfig.agent_profile_id == profile.profile_id)
        .first()
    )
    if not config:
        config = DBAgentChatbotConfig(
            config_id=str(uuid.uuid4()),
            brokerage_id=brokerage.brokerage_id,
            agent_profile_id=profile.profile_id,
            agent_user_id=user.id,
            handoff_display_name=display_name,
            escalation_whatsapp_phone=whatsapp_phone,
            active=True,
            settings={"activation": "dld_brokerage_match"},
        )
        db.add(config)
    else:
        config.handoff_display_name = display_name
        config.escalation_whatsapp_phone = whatsapp_phone
        config.active = True
        config.settings = {
            **(config.settings or {}),
            "activation": "dld_brokerage_match",
        }
        config.updated_at = datetime.utcnow()

    safe_commit(db)

    return {
        "profile_id": profile.profile_id,
        "brokerage_id": brokerage.brokerage_id,
        "brokerage_name": brokerage.name,
        "member_status": member.status,
        "verification_status": profile.verification_status,
        "chatbot_config_active": True,
        "message": "Agent profile active. Your Dalya handoff is now configured for this brokerage.",
    }
