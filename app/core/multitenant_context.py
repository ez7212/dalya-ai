"""
Multi-tenant context resolution for the buyer-facing Property Advisor.

`BrokerageContext` is the substitution context passed to every response
template, prompt builder, and escalation envelope. It collapses the
brokerage record, managing-agent profile, and listing-level fee fields into
one immutable bundle so every code path renders the same brokerage/agent
identity for a given listing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.brokerage_config import runtime_config_for_brokerage
from app.db.session import SessionLocal
from app.models.db_models import (
    DBAgentProfile,
    DBBrokerage,
    DBListing,
)


# Legacy single-tenant defaults. Used when a listing's brokerage isn't
# resolvable (e.g. listings ingested before the migration ran) so the
# pipeline still produces a coherent prompt.
_LEGACY_DEFAULTS = dict(
    brokerage_name="the listing brokerage",
    brokerage_short="the listing brokerage",
    brokerage_arabic="شركة الوساطة المسؤولة عن العقار",
    managing_agent_name="Eric",
    managing_agent_title="agent managing this listing",
    commission_rate=0.0,
    market_benchmark_rate=0.02,
    dashboard_url="dalya.ai/dashboard",
    brokerage_ai_number="",
    agents_ai_number="",
    managing_agent_phone="",
    managing_agent_user_id=None,
    legacy_telegram_alerts=True,
)


@dataclass(frozen=True)
class BrokerageContext:
    brokerage_id: Optional[str]
    brokerage_name: str
    brokerage_short: str
    brokerage_arabic: str
    managing_agent_name: str
    managing_agent_title: str
    commission_rate: float
    market_benchmark_rate: float
    dashboard_url: str
    brokerage_ai_number: str
    agents_ai_number: str
    managing_agent_phone: str
    managing_agent_user_id: Optional[str]
    legacy_telegram_alerts: bool

    @property
    def commission_pct_label(self) -> str:
        return _fmt_pct(self.commission_rate)

    @property
    def market_pct_label(self) -> str:
        return _fmt_pct(self.market_benchmark_rate)

    @property
    def savings_pct_label(self) -> str:
        savings = max(self.market_benchmark_rate - self.commission_rate, 0.0)
        return _fmt_pct(savings)


def _fmt_pct(rate: float) -> str:
    as_pct = (rate or 0.0) * 100
    if abs(as_pct - round(as_pct)) < 1e-9:
        return f"{int(round(as_pct))}%"
    return f"{as_pct:.2f}".rstrip("0").rstrip(".") + "%"


def legacy_default_context() -> BrokerageContext:
    """Return the pre-migration Mahoroba/Eric context. For test/fallback paths only."""
    return BrokerageContext(brokerage_id=None, **_LEGACY_DEFAULTS)


def context_for_listing(
    listing_id: Optional[str],
    db: Optional[Session] = None,
) -> BrokerageContext:
    """
    Resolve the full brokerage + managing-agent context for a listing.
    Falls back to legacy defaults if anything is missing so the pipeline
    never produces a half-rendered identity.
    """
    if not listing_id:
        return legacy_default_context()

    own_session = db is None
    session = db or SessionLocal()
    try:
        listing = session.get(DBListing, listing_id)
        if not listing or not listing.brokerage_id:
            return legacy_default_context()

        brokerage = session.get(DBBrokerage, listing.brokerage_id)
        if not brokerage:
            return legacy_default_context()

        agent: Optional[DBAgentProfile] = None
        if listing.assigned_agent_id:
            agent = (
                session.query(DBAgentProfile)
                .filter(
                    DBAgentProfile.brokerage_id == listing.brokerage_id,
                    DBAgentProfile.user_id == listing.assigned_agent_id,
                )
                .first()
            )

        commission_rate = listing.commission_rate
        if commission_rate is None:
            commission_rate = 0.0  # unknown commission; new listings must set this per listing

        runtime_cfg = runtime_config_for_brokerage(brokerage, agent=agent)

        return BrokerageContext(
            brokerage_id=brokerage.brokerage_id,
            brokerage_name=runtime_cfg.brokerage_name,
            brokerage_short=runtime_cfg.brokerage_short,
            brokerage_arabic=runtime_cfg.brokerage_arabic,
            managing_agent_name=runtime_cfg.managing_agent_name,
            managing_agent_title=runtime_cfg.managing_agent_title,
            commission_rate=float(commission_rate),
            market_benchmark_rate=float(runtime_cfg.market_benchmark_rate),
            dashboard_url=runtime_cfg.dashboard_url,
            brokerage_ai_number=runtime_cfg.brokerage_ai_number,
            agents_ai_number=runtime_cfg.agents_ai_number,
            managing_agent_phone=runtime_cfg.managing_agent_phone,
            managing_agent_user_id=runtime_cfg.managing_agent_user_id,
            legacy_telegram_alerts=runtime_cfg.legacy_telegram_alerts,
        )
    finally:
        if own_session:
            session.close()


def personalize(text: str, ctx: BrokerageContext) -> str:
    """
    Apply ctx-driven .format() substitutions to a template string.
    Templates use named placeholders like {managing_agent_name},
    {brokerage_short}, {commission_pct_label}, {market_pct_label},
    {savings_pct_label}, {dashboard_url}.
    """
    if not text:
        return text
    if "{" not in text:
        return text
    return text.format(
        managing_agent_name=ctx.managing_agent_name,
        managing_agent_title=ctx.managing_agent_title,
        brokerage_name=ctx.brokerage_name,
        brokerage_short=ctx.brokerage_short,
        brokerage_arabic=ctx.brokerage_arabic,
        commission_pct_label=ctx.commission_pct_label,
        market_pct_label=ctx.market_pct_label,
        savings_pct_label=ctx.savings_pct_label,
        dashboard_url=ctx.dashboard_url,
    )
