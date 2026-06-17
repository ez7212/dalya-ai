from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.session import safe_commit
from app.models.db_models import DBAgentProfile, DBBrokerage


SUPPORTED_LANGUAGE_CODES = {"en", "ar", "ru", "hi", "zh"}


@dataclass(frozen=True)
class BrokerageRuntimeConfig:
    brokerage_id: str
    brokerage_name: str
    brokerage_slug: str
    brokerage_short: str
    brokerage_arabic: str
    default_language: str
    enabled_languages: tuple[str, ...]
    managing_agent_name: str
    managing_agent_title: str
    managing_agent_phone: str
    managing_agent_user_id: Optional[str]
    market_benchmark_rate: float
    default_commission_rate: float
    fee_narrative: str
    dashboard_url: str
    brokerage_ai_number: str
    agents_ai_number: str
    legacy_telegram_alerts: bool


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _str(value, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _float(value, fallback: float) -> float:
    return float(value) if isinstance(value, (int, float)) else fallback


def _language_list(value) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ("en", "ar", "ru", "hi")
    cleaned = []
    for item in value:
        code = str(item or "").strip().lower()
        if code in SUPPORTED_LANGUAGE_CODES and code not in cleaned:
            cleaned.append(code)
    return tuple(cleaned or ["en", "ar", "ru", "hi"])


def runtime_config_for_brokerage(
    brokerage: DBBrokerage,
    *,
    agent: Optional[DBAgentProfile] = None,
) -> BrokerageRuntimeConfig:
    prompt_cfg = _dict(brokerage.prompt_config)
    fee_framing = _dict(brokerage.default_fee_framing)
    settings = _dict(brokerage.settings)
    language_defaults = _dict(settings.get("language_defaults"))

    enabled_languages = _language_list(
        language_defaults.get("enabled")
        or prompt_cfg.get("enabled_languages")
        or settings.get("enabled_languages")
    )
    default_language = _str(
        language_defaults.get("default")
        or prompt_cfg.get("default_language")
        or settings.get("default_language"),
        "en",
    ).lower()
    if default_language not in SUPPORTED_LANGUAGE_CODES:
        default_language = "en"
    if default_language not in enabled_languages:
        enabled_languages = (default_language, *tuple(lang for lang in enabled_languages if lang != default_language))

    brokerage_short = _str(
        prompt_cfg.get("short_name")
        or fee_framing.get("brokerage_short")
        or brokerage.name,
        "the brokerage",
    )
    brokerage_arabic = _str(prompt_cfg.get("name_arabic"), brokerage.name)
    managing_agent_title = _str(
        prompt_cfg.get("managing_agent_title")
        or fee_framing.get("managing_agent_title")
        or brokerage.escalation_contact_title,
        "agent managing this listing",
    )
    managing_agent_name = _str(
        (agent.chatbot_display_name if agent else None)
        or (agent.display_name if agent else None)
        or brokerage.escalation_contact_name,
        "the managing agent",
    )
    managing_agent_phone = _str(
        (agent.chatbot_handoff_phone if agent else None)
        or (agent.whatsapp_phone if agent else None)
        or brokerage.escalation_contact_phone,
    )

    return BrokerageRuntimeConfig(
        brokerage_id=brokerage.brokerage_id,
        brokerage_name=brokerage.name,
        brokerage_slug=brokerage.slug,
        brokerage_short=brokerage_short,
        brokerage_arabic=brokerage_arabic,
        default_language=default_language,
        enabled_languages=enabled_languages,
        managing_agent_name=managing_agent_name,
        managing_agent_title=managing_agent_title,
        managing_agent_phone=managing_agent_phone,
        managing_agent_user_id=agent.user_id if agent else None,
        market_benchmark_rate=_float(fee_framing.get("market_benchmark"), 0.02),
        default_commission_rate=_float(fee_framing.get("commission_rate"), 0.0),
        fee_narrative=_str(fee_framing.get("narrative"), ""),
        dashboard_url=_str(settings.get("dashboard_url"), "dalya.ai/dashboard"),
        brokerage_ai_number=_str(brokerage.brokerage_ai_number),
        agents_ai_number=_str(brokerage.agents_ai_number),
        legacy_telegram_alerts=bool(settings.get("legacy_telegram_alerts", False)),
    )


def serialize_runtime_config(config: BrokerageRuntimeConfig) -> dict:
    return {
        "brokerage_id": config.brokerage_id,
        "brokerage_name": config.brokerage_name,
        "brokerage_slug": config.brokerage_slug,
        "brokerage_short": config.brokerage_short,
        "brokerage_arabic": config.brokerage_arabic,
        "default_language": config.default_language,
        "enabled_languages": list(config.enabled_languages),
        "managing_agent_name": config.managing_agent_name,
        "managing_agent_title": config.managing_agent_title,
        "managing_agent_phone": config.managing_agent_phone,
        "managing_agent_user_id": config.managing_agent_user_id,
        "market_benchmark_rate": config.market_benchmark_rate,
        "default_commission_rate": config.default_commission_rate,
        "fee_narrative": config.fee_narrative,
        "dashboard_url": config.dashboard_url,
        "brokerage_ai_number": config.brokerage_ai_number,
        "agents_ai_number": config.agents_ai_number,
        "legacy_telegram_alerts": config.legacy_telegram_alerts,
    }


def apply_brokerage_config_update(
    db: Session,
    brokerage: DBBrokerage,
    *,
    prompt_config: Optional[dict] = None,
    default_fee_framing: Optional[dict] = None,
    settings: Optional[dict] = None,
    escalation_contact_name: Optional[str] = None,
    escalation_contact_title: Optional[str] = None,
    escalation_contact_phone: Optional[str] = None,
) -> DBBrokerage:
    if prompt_config:
        brokerage.prompt_config = {**_dict(brokerage.prompt_config), **prompt_config}
    if default_fee_framing:
        brokerage.default_fee_framing = {**_dict(brokerage.default_fee_framing), **default_fee_framing}
    if settings:
        current_settings = _dict(brokerage.settings)
        language_defaults = settings.pop("language_defaults", None)
        if isinstance(language_defaults, dict):
            current_language_defaults = _dict(current_settings.get("language_defaults"))
            current_settings["language_defaults"] = {**current_language_defaults, **language_defaults}
        brokerage.settings = {**current_settings, **settings}
    if escalation_contact_name is not None:
        brokerage.escalation_contact_name = escalation_contact_name
    if escalation_contact_title is not None:
        brokerage.escalation_contact_title = escalation_contact_title
    if escalation_contact_phone is not None:
        brokerage.escalation_contact_phone = escalation_contact_phone
    brokerage.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(brokerage)
    return brokerage
