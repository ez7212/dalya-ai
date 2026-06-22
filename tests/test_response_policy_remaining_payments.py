from __future__ import annotations

import re

from app.core.chatbot_engine import ChatbotEngine
from app.core.verified_facts import VerifiedFact
from app.schemas.spa import PaymentInstalment, SPAParseResult


def _dld_fact() -> VerifiedFact:
    return VerifiedFact.from_raw(
        {
            "key": "dld_registration_fee_pct",
            "category": "fees",
            "domain": "dubai_real_estate",
            "scope": "global",
            "text": "The standard Dubai Land Department (DLD) property registration fee is 4% of the purchase price, paid by the buyer.",
            "source_label": "DLD fee schedule",
            "source_ref": "S1",
            "status": "confirmed",
            "transaction_specific": False,
            "active": True,
        }
    )


def _offplan_spa() -> SPAParseResult:
    return SPAParseResult(
        project="The Oasis",
        unit_number="V-12",
        developer="Emaar",
        property_type="Villa",
        purchase_price_aed=15_000_000,
        property_status="Under Construction",
        estimated_completion_date="2028-12-31",
        payment_schedule=[
            PaymentInstalment(
                instalment_number=1,
                milestone="Remaining on handover",
                percentage=20,
                amount_aed=3_000_000,
                amount_incl_vat_aed=3_000_000,
                due_date="2028-12-31",
            )
        ],
    )


def _ready_spa() -> SPAParseResult:
    return SPAParseResult(
        project="Address JBR",
        unit_number="3105",
        developer="Emaar",
        property_type="Apartment",
        purchase_price_aed=2_800_000,
        property_status="Ready",
        payment_schedule=[],
    )


def _aed_amounts(text: str) -> set[str]:
    return set(re.findall(r"AED\s+([0-9][0-9,]*)", text))


def test_offplan_total_fees_uses_agent_confirmation_without_seller_equity_pair():
    response = ChatbotEngine._compose_total_fees_response(
        _offplan_spa(),
        16_500_000,
        property_type="off_plan",
        dld_fee_fact=_dld_fact(),
    )
    lowered = response.lower()

    assert "seller-equity" not in lowered
    assert "seller equity" not in lowered
    assert "developer balance" not in lowered
    assert "splits between" not in lowered
    assert "13,500,000" not in response
    assert not ({"13,500,000", "3,000,000"} <= _aed_amounts(response))
    assert "confirm" in lowered
    assert "before you rely on" in lowered


def test_remaining_payment_response_keeps_developer_balance_without_seller_equity_language():
    response = ChatbotEngine._compose_remaining_payment_response(
        _offplan_spa(),
        property_type="off_plan",
        seller_asking_price=16_500_000,
    )
    lowered = response.lower()

    assert "AED 3,000,000" in response
    assert "seller-equity" not in lowered
    assert "seller equity" not in lowered
    assert "seller-side" not in lowered
    assert "13,500,000" not in response
    assert not ({"13,500,000", "3,000,000"} <= _aed_amounts(response))


def test_ready_property_keeps_no_developer_payment_schedule_behavior():
    response = ChatbotEngine._compose_remaining_payment_response(
        _ready_spa(),
        property_type="ready",
        seller_asking_price=2_800_000,
    )
    lowered = response.lower()

    assert "ready property" in lowered
    assert "no remaining developer payment plan" in lowered
    assert "seller-equity amount" not in lowered
    assert "take over" in lowered
