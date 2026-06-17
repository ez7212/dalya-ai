"""
Date-driven compute_paid_to_date — replaces stored total_paid_percent snapshots.
Off-plan payments are tied to construction milestones, not just dates, so a
per-instalment `actually_paid` override is supported. When None, fall back to
date-based inference (assume paid if due_date is in the past).
"""
from __future__ import annotations
from datetime import date
from typing import Optional

from app.schemas.spa import PaymentInstalment, SPAParseResult


def compute_paid_to_date(
    spa: SPAParseResult,
    as_of: Optional[date] = None,
) -> dict:
    """
    Returns:
        {
            "paid_pct": float,        # 0.0–100.0
            "paid_aed": float,
            "remaining_pct": float,
            "remaining_aed": float,
            "paid_instalments": [PaymentInstalment, ...],
            "pending_instalments": [PaymentInstalment, ...],
            "needs_verification": bool,  # True if any instalment past due_date but actually_paid is None
            "as_of": date,
        }
    """
    as_of = as_of or date.today()

    status = (spa.property_status or "").strip().lower()
    if status in {"ready", "completed", "complete", "handed over", "handover complete"} and not spa.payment_schedule:
        return {
            "paid_pct": 100.0,
            "paid_aed": spa.purchase_price_aed or 0.0,
            "remaining_pct": 0.0,
            "remaining_aed": 0.0,
            "paid_instalments": [],
            "pending_instalments": [],
            "needs_verification": False,
            "as_of": as_of,
        }

    paid_pct = 0.0
    paid_list: list[PaymentInstalment] = []
    pending_list: list[PaymentInstalment] = []
    needs_verification = False

    for inst in (spa.payment_schedule or []):
        explicit = getattr(inst, "actually_paid", None)
        due = getattr(inst, "due_date", None)
        # Coerce due to date if it's a string or datetime
        if isinstance(due, str):
            try:
                due = date.fromisoformat(due[:10])
            except ValueError:
                due = None
        elif hasattr(due, "date") and not isinstance(due, date):
            due = due.date()

        if explicit is True:
            paid_pct += inst.percentage or 0.0
            paid_list.append(inst)
        elif explicit is False:
            pending_list.append(inst)
        else:
            # Unknown — infer from due date
            if due is not None and due <= as_of:
                paid_pct += inst.percentage or 0.0
                paid_list.append(inst)
                needs_verification = True
            else:
                pending_list.append(inst)

    # Harness synthetic schedules store only the remaining developer payments,
    # with total_paid_percent carrying the paid-to-date state. Use it when the
    # schedule itself contains no paid installments.
    if paid_pct == 0.0 and spa.total_paid_percent is not None:
        explicit_paid_present = any(
            getattr(inst, "actually_paid", None) is True
            for inst in (spa.payment_schedule or [])
        )
        if not explicit_paid_present:
            paid_pct = float(spa.total_paid_percent or 0.0)

    pending_pct = sum(float(inst.percentage or 0.0) for inst in pending_list)
    pending_aed = sum(float(inst.amount_aed or 0.0) for inst in pending_list)

    paid_aed = (spa.purchase_price_aed or 0.0) * paid_pct / 100.0
    remaining_pct = pending_pct if pending_list else max(0.0, 100.0 - paid_pct)
    remaining_aed = pending_aed if pending_list else (spa.purchase_price_aed or 0.0) * remaining_pct / 100.0
    return {
        "paid_pct": paid_pct,
        "paid_aed": paid_aed,
        "remaining_pct": remaining_pct,
        "remaining_aed": remaining_aed,
        "paid_instalments": paid_list,
        "pending_instalments": pending_list,
        "needs_verification": needs_verification,
        "as_of": as_of,
    }
