# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run:
# PYTHONPATH=. python3 scripts/verify_verified_facts_output_gate.py --evidence .omo/evidence/task-6-verified-facts-output.json

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path

from app.core.response_validator import validate_and_rewrite_response
from app.core.verified_facts import VerifiedFact, VerifiedFactRegistry
from app.core.verified_facts_output_gate import apply_verified_facts_output_gate
from app.schemas.conversation import BuyerIntent


@dataclass(frozen=True)
class GateScenario:
    name: str
    generated: str
    blocked_terms: tuple[str, ...]


UNSAFE_SCENARIOS: tuple[GateScenario, ...] = (
    GateScenario("ltv", "Banks usually allow 50% LTV on this off-plan resale.", ("50% LTV",)),
    GateScenario("noc_duration", "The developer NOC should take 3-5 days once we apply.", ("3-5 days",)),
    GateScenario("closing_timeline", "The trustee transfer normally closes in 30-45 days.", ("30-45 days",)),
    GateScenario("noc_fee", "The generic developer NOC fee is AED 5,000.", ("AED 5,000",)),
    GateScenario("agency_fee", "The agency fee is 2% and the trustee fee is AED 4,000.", ("2%", "AED 4,000")),
    GateScenario("legal_tax", "There is no tax exposure here, so you do not need legal advice.", ("no tax exposure", "do not need legal advice")),
    GateScenario(
        "tenancy_process",
        "Vacant possession is guaranteed after 12 months because the tenant notice is automatic.",
        ("12 months", "guaranteed", "automatic"),
    ),
    GateScenario(
        "seller_paid_back_calculation",
        "The seller has paid AED 12,000,000 to date, so you only take over the AED 3,000,000 developer balance.",
        ("AED 12,000,000", "AED 3,000,000", "take over"),
    ),
    GateScenario(
        "seller_original_price",
        "The seller originally paid AED 12,000,000, so the premium is about 25%.",
        ("AED 12,000,000", "25%"),
    ),
)


def run_scenarios() -> list[dict[str, str | int | list[str]]]:
    results: list[dict[str, str | int | list[str]]] = []
    for scenario in UNSAFE_SCENARIOS:
        response, telemetry = validate_and_rewrite_response(
            scenario.generated,
            BuyerIntent.general_enquiry,
            latest_buyer_message="Can you give me exact finance, NOC, tax, and payment details?",
        )
        lowered = response.lower()
        blocked_remaining = [
            term for term in scenario.blocked_terms if term.lower() in lowered
        ]
        if blocked_remaining:
            raise AssertionError(f"{scenario.name} still contains blocked terms: {blocked_remaining}")
        rewrite_count = int(telemetry["verified_facts_output_rewrites"])
        if rewrite_count < 1:
            raise AssertionError(f"{scenario.name} did not record a Verified Facts output rewrite")
        results.append(
            {
                "name": scenario.name,
                "status": "rewritten",
                "rewrite_count": rewrite_count,
                "output": response,
            }
        )

    direct_fact = "The standard Dubai Land Department (DLD) property registration fee is 4% of the purchase price, paid by the buyer."
    response, telemetry = validate_and_rewrite_response(
        direct_fact,
        BuyerIntent.general_enquiry,
        latest_buyer_message="What is the DLD fee?",
    )
    if response != direct_fact:
        raise AssertionError("active direct DLD fact was rewritten")
    results.append(
        {
            "name": "active_direct_dld_fact",
            "status": "passed",
            "rewrite_count": int(telemetry["verified_facts_output_rewrites"]),
            "output": response,
        }
    )
    tenant_registry = VerifiedFactRegistry([
        VerifiedFact.from_raw(
            {
                "key": "specific_noc_transfer_timing",
                "category": "noc_transfer",
                "domain": "dubai_real_estate",
                "scope": "tenant",
                "brokerage_id": "brokerage-A",
                "text": "For brokerage A verified listing context, the developer NOC takes 7 days.",
                "source_label": "Brokerage A compliance note",
                "source_ref": "NOC1",
                "status": "confirmed",
                "transaction_specific": False,
                "active": True,
            }
        )
    ])
    tenant_result = apply_verified_facts_output_gate(
        "The developer NOC takes 7 days.",
        latest_buyer_message="How long does the NOC take?",
        brokerage_id="brokerage-A",
        registry=tenant_registry,
    )
    if tenant_result.response != "The developer NOC takes 7 days.":
        raise AssertionError("tenant-scoped direct NOC fact was rewritten")
    results.append(
        {
            "name": "tenant_direct_noc_fact",
            "status": "passed",
            "rewrite_count": tenant_result.rewrite_count,
            "output": tenant_result.response,
        }
    )
    remaining_payment = (
        "At the asking price of AED 16,500,000, the known remaining amount "
        "to the developer is AED 3,000,000, subject to agent confirmation "
        "against the listing documents."
    )
    response, telemetry = validate_and_rewrite_response(
        remaining_payment,
        BuyerIntent.payment_plan_query,
        latest_buyer_message="How much remains to the developer?",
    )
    if response != remaining_payment:
        raise AssertionError("deterministic remaining-payment wording was rewritten")
    results.append(
        {
            "name": "deterministic_remaining_payment",
            "status": "passed",
            "rewrite_count": int(telemetry["verified_facts_output_rewrites"]),
            "output": response,
        }
    )
    return results


def verify_path_wiring() -> list[dict[str, str]]:
    checks = [
        _assert_source_contains(
            Path("app/core/chatbot_engine.py"),
            "latest_buyer_message=latest_buyer_message",
            "engine_finalizer_passes_latest_buyer_message",
        ),
        _assert_source_contains(
            Path("app/core/chatbot_engine.py"),
            "brokerage_id=ctx.brokerage_id",
            "engine_finalizer_passes_brokerage_scope",
        ),
        _assert_source_contains(
            Path("app/api/whatsapp.py"),
            "body, _ = validate_and_rewrite_response(body, brokerage_id=brokerage_id)",
            "whatsapp_send_revalidates_body",
        ),
    ]
    _assert_callable_accepts_keywords(
        Path("app/core/response_validator.py"),
        "validate_and_rewrite_response",
        ("latest_buyer_message", "brokerage_id"),
    )
    checks.append({"name": "validator_accepts_output_gate_context", "status": "passed"})
    return checks


def _assert_source_contains(path: Path, needle: str, name: str) -> dict[str, str]:
    source = path.read_text()
    if needle not in source:
        raise AssertionError(f"{path} missing {needle!r}")
    return {"name": name, "status": "passed"}


def _assert_callable_accepts_keywords(path: Path, function_name: str, keyword_names: tuple[str, ...]) -> None:
    module = ast.parse(path.read_text())
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            present = {arg.arg for arg in node.args.args}
            missing = [name for name in keyword_names if name not in present]
            if missing:
                raise AssertionError(f"{function_name} missing parameters: {missing}")
            return
    raise AssertionError(f"{function_name} not found in {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.evidence)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results = run_scenarios()
    path_checks = verify_path_wiring()
    output_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "scenario_count": len(results),
                "scenarios": results,
                "path_checks": path_checks,
            },
            indent=2,
        )
    )
    print(f"PASS wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
