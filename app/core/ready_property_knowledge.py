from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import safe_commit
from app.models.db_models import DBListing, DBListingDocument, DBListingFact, DBListingKnowledgeSummary


DOCUMENT_TYPES = [
    "title_deed",
    "oqood",
    "ejari",
    "tenancy_contract",
    "service_charge_statement",
    "noc",
    "valuation_report",
    "mortgage_liability_letter",
    "floor_plan",
    "snagging_report",
    "dewa_utility_info",
    "building_rules",
    "agent_inspection_notes",
    "seller_disclosure_notes",
]

FACT_GROUP_LABELS = {
    "occupancy": "Occupancy",
    "charges": "Service charges",
    "parking": "Parking",
    "transfer": "Transfer readiness",
    "finance": "Finance and liabilities",
    "condition": "Condition",
    "utilities": "Utilities",
    "layout": "Layout and view",
    "building": "Building rules",
    "valuation": "Valuation",
}

CORE_READY_FACTS = [
    ("occupancy", "Occupancy or vacancy status"),
    ("charges", "Service charge or OA fee"),
    ("parking", "Parking allocation"),
    ("transfer", "NOC or transfer readiness"),
    ("condition", "Snagging, wear, or recent upgrade notes"),
    ("utilities", "AC, chiller, DEWA, or utility context"),
]

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<![\w-])(?:\+\d{1,3}[\s().-]*)?(?:\d[\s().-]*){8,}\d(?![\w-])")
EMIRATES_ID_RE = re.compile(r"\b784[-\s]?\d{4}[-\s]?\d{7}[-\s]?\d\b")


def redact_private_data(value: str | None) -> str:
    text = value or ""
    text = EMAIL_RE.sub("[redacted email]", text)
    text = EMIRATES_ID_RE.sub("[redacted Emirates ID]", text)
    text = PHONE_RE.sub("[redacted phone]", text)
    return text


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _sentence_containing(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    start = max(text.rfind(".", 0, match.start()), text.rfind("\n", 0, match.start()))
    end_dot = text.find(".", match.end())
    end_line = text.find("\n", match.end())
    end_candidates = [idx for idx in [end_dot, end_line] if idx != -1]
    end = min(end_candidates) if end_candidates else min(len(text), match.end() + 120)
    return _normalize_space(text[start + 1:end + 1])


def _first_money(text: str, window_pattern: str) -> str | None:
    sentence = _sentence_containing(text, window_pattern)
    if not sentence:
        return None
    money = re.search(r"(AED\s*)?([\d,]+(?:\.\d+)?)\s*(?:AED)?(?:\s*/\s*sq\s*ft|\s*per\s*sq\s*ft|\s*psf)?", sentence, re.IGNORECASE)
    if not money:
        return sentence
    return sentence


def _add_fact(
    facts: list[dict[str, Any]],
    *,
    fact_key: str,
    fact_group: str,
    value_text: str | None,
    confidence: float = 0.72,
    buyer_safe: bool = True,
    risk_flag: bool = False,
    value_json: dict[str, Any] | None = None,
) -> None:
    if not value_text:
        return
    cleaned = redact_private_data(_normalize_space(value_text))
    if not cleaned:
        return
    if any(f["fact_key"] == fact_key and f["value_text"].lower() == cleaned.lower() for f in facts):
        return
    facts.append(
        {
            "fact_key": fact_key,
            "fact_group": fact_group,
            "value_text": cleaned,
            "confidence": confidence,
            "buyer_safe": buyer_safe,
            "risk_flag": risk_flag,
            "value_json": value_json or {},
        }
    )


def extract_listing_facts(document_type: str, content_text: str | None) -> list[dict[str, Any]]:
    """MVP deterministic extraction for ready-property paperwork and notes."""
    text = content_text or ""
    if not text.strip():
        return []
    text = redact_private_data(text)

    lowered = text.lower()
    facts: list[dict[str, Any]] = []

    service_sentence = _first_money(text, r"service\s+charge|maintenance\s+fee|owners\s+association|oa\s+fee")
    if service_sentence:
        _add_fact(
            facts,
            fact_key="service_charge",
            fact_group="charges",
            value_text=service_sentence,
            confidence=0.82 if document_type == "service_charge_statement" else 0.72,
        )

    if re.search(r"\bvacant\b|\bvacant\s+on\s+transfer\b|\bvacant\s+possession\b", lowered):
        _add_fact(
            facts,
            fact_key="occupancy_status",
            fact_group="occupancy",
            value_text=_sentence_containing(text, r"vacant|vacant\s+possession") or "Vacant possession referenced.",
            confidence=0.8,
        )
    elif re.search(r"\btenanted\b|\btenant\b|\bejari\b|\blease\b|\bleased\b", lowered):
        _add_fact(
            facts,
            fact_key="occupancy_status",
            fact_group="occupancy",
            value_text=_sentence_containing(text, r"tenanted|tenant|ejari|lease|leased") or "Tenancy/Ejari referenced.",
            confidence=0.84 if document_type in {"ejari", "tenancy_contract"} else 0.7,
        )

    expiry = re.search(r"(?:lease|ejari|tenancy).*?(?:expiry|expires|until|end(?:s)?(?:\s+on)?)[^\d]*(\d{1,2}[\s/-][A-Za-z]{3,9}[\s/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}[\s/-]\d{1,2}[\s/-]\d{2,4})", text, re.IGNORECASE)
    if expiry:
        _add_fact(
            facts,
            fact_key="lease_expiry",
            fact_group="occupancy",
            value_text=f"Lease/Ejari expiry referenced: {expiry.group(1)}.",
            confidence=0.78,
        )

    parking = re.search(r"\b(\d+)\s+(?:allocated\s+)?(?:parking|car\s*park|bay|space|spaces|bays|spots)\b", text, re.IGNORECASE)
    if parking:
        _add_fact(
            facts,
            fact_key="parking_allocation",
            fact_group="parking",
            value_text=_sentence_containing(text, r"\b\d+\s+(?:allocated\s+)?(?:parking|car\s*park|bay|space|spaces|bays|spots)\b") or f"{parking.group(1)} parking space(s).",
            confidence=0.78,
        )

    if re.search(r"\bnoc\b|no objection certificate|transferable|transfer ready", lowered):
        risk = bool(re.search(r"not\s+(?:available|eligible|issued)|pending|blocked|outstanding", lowered))
        _add_fact(
            facts,
            fact_key="noc_status",
            fact_group="transfer",
            value_text=_sentence_containing(text, r"noc|no objection certificate|transferable|transfer ready") or "NOC/transfer readiness referenced.",
            confidence=0.76,
            risk_flag=risk,
        )

    if re.search(r"\bmortgage\b|liability letter|outstanding liability|settlement", lowered):
        risk = bool(re.search(r"outstanding|liability|settlement|mortgage", lowered)) and not bool(re.search(r"no mortgage|settled|clear", lowered))
        _add_fact(
            facts,
            fact_key="mortgage_liability",
            fact_group="finance",
            value_text=_sentence_containing(text, r"mortgage|liability letter|outstanding liability|settlement") or "Mortgage/liability position referenced.",
            confidence=0.74,
            risk_flag=risk,
        )

    floor = re.search(r"\b(\d{1,3})(?:st|nd|rd|th)?\s+floor\b|\bfloor\s+(\d{1,3})\b", text, re.IGNORECASE)
    if floor:
        value = floor.group(1) or floor.group(2)
        _add_fact(
            facts,
            fact_key="floor_level",
            fact_group="layout",
            value_text=_sentence_containing(text, r"floor") or f"Floor level: {value}.",
            confidence=0.73,
        )

    view_sentence = _sentence_containing(text, r"\b(?:sea|marina|park|golf|skyline|pool|community|road|canal|lagoon)\s+view\b|\bview\s+(?:of|towards|over)\b|\bfacing\b")
    if view_sentence:
        _add_fact(
            facts,
            fact_key="view_orientation",
            fact_group="layout",
            value_text=view_sentence,
            confidence=0.72,
        )

    size = re.search(r"\b([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*ft|sqft|square feet)\b", text, re.IGNORECASE)
    if size:
        _add_fact(
            facts,
            fact_key="documented_size",
            fact_group="layout",
            value_text=_sentence_containing(text, r"sq\.?\s*ft|sqft|square feet") or f"Documented size: {size.group(1)} sqft.",
            confidence=0.72,
        )

    if re.search(r"\bsnag|defect|wear|damage|repair|leak|crack|upgrade|renovat", lowered):
        risk = bool(re.search(r"defect|damage|repair|leak|crack|major|urgent", lowered))
        _add_fact(
            facts,
            fact_key="condition_notes",
            fact_group="condition",
            value_text=_sentence_containing(text, r"snag|defect|wear|damage|repair|leak|crack|upgrade|renovat") or "Condition/snagging notes referenced.",
            confidence=0.75,
            risk_flag=risk,
        )

    if re.search(r"\bdewa\b|\bchiller\b|\bdistrict cooling\b|\bac\b|air conditioning|utility", lowered):
        _add_fact(
            facts,
            fact_key="utility_notes",
            fact_group="utilities",
            value_text=_sentence_containing(text, r"dewa|chiller|district cooling|\bac\b|air conditioning|utility") or "Utility/AC details referenced.",
            confidence=0.72,
        )

    if re.search(r"pet[-\s]?friendly|pets?\s+(?:allowed|not allowed)|short[-\s]?term|holiday home|move[-\s]?in|building rules", lowered):
        _add_fact(
            facts,
            fact_key="building_rules",
            fact_group="building",
            value_text=_sentence_containing(text, r"pet|short[-\s]?term|holiday home|move[-\s]?in|building rules") or "Building rules referenced.",
            confidence=0.7,
        )

    valuation = _first_money(text, r"\bvaluation\b|market value|bank valuation")
    if valuation:
        _add_fact(
            facts,
            fact_key="valuation",
            fact_group="valuation",
            value_text=valuation,
            confidence=0.72,
            buyer_safe=False,
        )

    return facts


def process_listing_document(db: Session, document: DBListingDocument) -> list[DBListingFact]:
    db.query(DBListingFact).filter(DBListingFact.document_id == document.document_id).delete(synchronize_session=False)
    rows = []
    for extracted in extract_listing_facts(document.document_type, document.content_text):
        rows.append(
            DBListingFact(
                brokerage_id=document.brokerage_id,
                listing_id=document.listing_id,
                document_id=document.document_id,
                fact_key=extracted["fact_key"],
                fact_group=extracted["fact_group"],
                value_text=extracted["value_text"],
                value_json=extracted.get("value_json") or {},
                confidence=extracted["confidence"],
                source="document_extraction",
                verified=False,
                buyer_safe=extracted["buyer_safe"],
                risk_flag=extracted["risk_flag"],
            )
        )
    db.add_all(rows)
    document.status = "processed"
    document.extracted_at = datetime.utcnow()
    document.updated_at = datetime.utcnow()
    safe_commit(db)
    for row in rows:
        db.refresh(row)
    return rows


def rebuild_knowledge_summary(db: Session, listing: DBListing) -> DBListingKnowledgeSummary:
    facts = (
        db.query(DBListingFact)
        .filter(DBListingFact.listing_id == listing.listing_id)
        .order_by(DBListingFact.fact_group.asc(), DBListingFact.created_at.asc())
        .all()
    )
    buyer_safe_facts = [fact for fact in facts if fact.buyer_safe]
    risk_flags = [
        {
            "fact_id": fact.fact_id,
            "fact_key": fact.fact_key,
            "label": FACT_GROUP_LABELS.get(fact.fact_group, fact.fact_group),
            "value": fact.value_text,
        }
        for fact in facts
        if fact.risk_flag
    ]
    covered_groups = {fact.fact_group for fact in buyer_safe_facts}
    missing = [
        {"fact_group": group, "label": label}
        for group, label in CORE_READY_FACTS
        if group not in covered_groups
    ]

    summary_lines = []
    for fact in buyer_safe_facts[:16]:
        verified = "verified" if fact.verified else "unverified"
        label = FACT_GROUP_LABELS.get(fact.fact_group, fact.fact_group.replace("_", " "))
        summary_lines.append(f"- {label}: {redact_private_data(fact.value_text)} ({verified})")

    internal_lines = []
    if facts:
        internal_lines.append(f"{len(facts)} extracted fact(s), {len([f for f in facts if f.verified])} verified.")
    if risk_flags:
        internal_lines.append(f"{len(risk_flags)} risk flag(s) need agent review before relying on them.")
    if missing:
        internal_lines.append("Missing: " + ", ".join(item["label"] for item in missing) + ".")

    summary = (
        db.query(DBListingKnowledgeSummary)
        .filter(DBListingKnowledgeSummary.listing_id == listing.listing_id)
        .first()
    )
    if not summary:
        summary = DBListingKnowledgeSummary(
            brokerage_id=listing.brokerage_id,
            listing_id=listing.listing_id,
        )
        db.add(summary)

    summary.brokerage_id = listing.brokerage_id
    summary.buyer_safe_summary = "\n".join(summary_lines) or None
    summary.internal_notes = " ".join(internal_lines) or None
    summary.missing_information = missing
    summary.risk_flags = risk_flags
    summary.status = "ready" if buyer_safe_facts else "empty"
    summary.metadata_json = {
        "fact_count": len(facts),
        "buyer_safe_fact_count": len(buyer_safe_facts),
        "verified_fact_count": len([fact for fact in facts if fact.verified]),
        "document_count": db.query(DBListingDocument).filter(DBListingDocument.listing_id == listing.listing_id).count(),
    }
    summary.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(summary)
    return summary


def ready_property_knowledge_for_prompt(db: Session, listing_id: str) -> dict[str, Any] | None:
    summary = (
        db.query(DBListingKnowledgeSummary)
        .filter(DBListingKnowledgeSummary.listing_id == listing_id)
        .first()
    )
    facts = (
        db.query(DBListingFact)
        .filter(DBListingFact.listing_id == listing_id, DBListingFact.buyer_safe.is_(True))
        .order_by(DBListingFact.verified.desc(), DBListingFact.created_at.asc())
        .limit(20)
        .all()
    )
    documents = (
        db.query(DBListingDocument)
        .filter(DBListingDocument.listing_id == listing_id)
        .order_by(DBListingDocument.created_at.desc())
        .limit(12)
        .all()
    )
    if not summary and not facts and not documents:
        return None
    return {
        "buyer_safe_summary": summary.buyer_safe_summary if summary else None,
        "missing_information": summary.missing_information if summary else [],
        "risk_flags": summary.risk_flags if summary else [],
        "facts": [
            {
                "fact_key": fact.fact_key,
                "fact_group": fact.fact_group,
                "value_text": fact.value_text,
                "verified": fact.verified,
                "confidence": fact.confidence,
                "risk_flag": fact.risk_flag,
            }
            for fact in facts
        ],
        "documents": [
            {
                "document_type": doc.document_type,
                "label": doc.label,
                "status": doc.status,
            }
            for doc in documents
        ],
    }
