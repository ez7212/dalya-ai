"""
Portal lead ingestion + AI first-touch (DAL-163).

85–95% of buyer inquiries arrive as Property Finder/Bayut leads delivered by
email. Each brokerage gets a dedicated ingest address
(`leads+{brokerage_slug}@…`); the agent auto-forwards their portal lead inbox
to it.

Parsers are per-portal-template **data with a parser_version** — portal email
formats change. Unparseable emails land in a dead-letter queue with an
AI-failure notification; nothing is silently dropped.

First-touch is the ONE bounded exception to draft-and-approve: the content is
template-locked with variable slots only (no free-form AI content is ever
auto-sent), sent on ingestion because speed-to-lead is the whole point, with
the agent notified simultaneously (DAL-162 event #2). The consent basis —
buyer submitted their number on a portal lead form expecting contact — is
recorded on the compliance trail with the lead email retained as evidence.
See docs/adr/ADR-2026-06-10-first-touch-template-exception.md.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional, Protocol

from sqlalchemy.orm import Session

from app.core.brokerage_access import is_buyer_suppressed, record_compliance_event
from app.core.buyer_profiles import get_or_create_profile as get_or_create_buyer_profile
from app.db.session import safe_commit
from app.models.db_models import (
    DBBrokerage,
    DBConversation,
    DBDraftReply,
    DBLeadAssignment,
    DBLeadIngestRecord,
    DBListing,
    DBMessage,
)

logger = logging.getLogger(__name__)

DUPLICATE_WINDOW = timedelta(days=7)
NUDGE_AFTER = timedelta(hours=48)
LEAD_RECENCY_SCORE = 88  # strong recency score — a fresh lead outranks stale threads

# Template-locked first-touch (utility category; marketing fallback in the ADR).
# Variables: 1=buyer first name, 2=listing/project, 3=portal, 4=brokerage name.
FIRST_TOUCH_TEMPLATE_NAME = "lead_first_touch_utility"
FIRST_TOUCH_TEMPLATE_VERSION = "v1"
FIRST_TOUCH_TEMPLATE = (
    "Hi {buyer_name}, thanks for your enquiry about {listing_label} on {portal}. "
    "I'm the AI assistant for {brokerage_name} — happy to answer questions or "
    "arrange a viewing. Reply STOP to opt out."
)


@dataclass
class ParsedLead:
    source: str                      # property_finder | bayut
    parser_version: str
    buyer_name: Optional[str]
    buyer_phone: str                 # E.164
    buyer_message: Optional[str]
    portal_listing_ref: Optional[str] = None
    portal_listing_url: Optional[str] = None


@dataclass
class IngestOutcome:
    status: str   # ingested | attached | duplicate | dead_letter
    record: Optional[DBLeadIngestRecord] = None
    conversation_id: Optional[str] = None
    first_touch_sent: bool = False
    details: dict = field(default_factory=dict)


class LeadIngestAdapter(Protocol):
    """
    Adapter interface for lead sources. The email parser is the first
    implementation; Luqman's CRM (or absence of one) determines the second —
    GOAL_SPEC_0610 open question #1.
    """

    name: str

    def parse(self, payload: dict) -> Optional[ParsedLead]:
        ...


def normalize_phone(raw: str) -> Optional[str]:
    """Best-effort E.164 normalization for UAE-style portal leads."""
    if not raw:
        return None
    cleaned = re.sub(r"[^\d+]", "", raw.strip())
    if not cleaned:
        return None
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    elif cleaned.startswith("05") and len(cleaned) == 10:
        cleaned = "+971" + cleaned[1:]
    elif cleaned.startswith("971") and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    elif not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    digits = cleaned[1:]
    if not digits.isdigit() or not 7 <= len(digits) <= 15:
        return None
    return cleaned


# ── Per-portal email parsers (templates as data, versioned) ────────────────────


def _field(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def _parse_property_finder_v1(payload: dict) -> Optional[ParsedLead]:
    body = payload.get("body") or ""
    subject = payload.get("subject") or ""
    haystack = f"{subject}\n{body}"
    if "propertyfinder" not in haystack.lower() and "property finder" not in haystack.lower():
        return None
    phone = normalize_phone(_field(r"(?:Phone|Mobile)[:\s]+([+\d][\d\s\-()]{6,20})", body) or "")
    if not phone:
        return None
    url_match = re.search(r"(https?://(?:www\.)?propertyfinder\.ae/\S+)", body)
    return ParsedLead(
        source="property_finder",
        parser_version="property_finder:v1",
        buyer_name=_field(r"(?:Name|Client)[:\s]+(.+)$", body),
        buyer_phone=phone,
        buyer_message=_field(r"(?:Message|Comments?)[:\s]+([\s\S]+?)(?:\n\s*\n|$)", body),
        portal_listing_ref=_field(r"(?:Reference|Ref(?:erence)? ?(?:No|#)?)[.:\s]+([A-Za-z0-9\-]+)", body),
        portal_listing_url=url_match.group(1) if url_match else None,
    )


def _parse_bayut_v1(payload: dict) -> Optional[ParsedLead]:
    body = payload.get("body") or ""
    subject = payload.get("subject") or ""
    haystack = f"{subject}\n{body}"
    if "bayut" not in haystack.lower():
        return None
    phone = normalize_phone(_field(r"(?:Phone|Mobile|Contact)[:\s]+([+\d][\d\s\-()]{6,20})", body) or "")
    if not phone:
        return None
    url_match = re.search(r"(https?://(?:www\.)?bayut\.com/\S+)", body)
    return ParsedLead(
        source="bayut",
        parser_version="bayut:v1",
        buyer_name=_field(r"(?:Name|Lead Name)[:\s]+(.+)$", body),
        buyer_phone=phone,
        buyer_message=_field(r"(?:Message|Enquiry)[:\s]+([\s\S]+?)(?:\n\s*\n|$)", body),
        portal_listing_ref=_field(r"(?:Reference|Property ID)[.:\s]+([A-Za-z0-9\-]+)", body),
        portal_listing_url=url_match.group(1) if url_match else None,
    )


EMAIL_PARSERS: list[Callable[[dict], Optional[ParsedLead]]] = [
    _parse_property_finder_v1,
    _parse_bayut_v1,
]


class EmailLeadAdapter:
    """First LeadIngestAdapter implementation: PF/Bayut notification emails."""

    name = "email"

    def parse(self, payload: dict) -> Optional[ParsedLead]:
        for parser in EMAIL_PARSERS:
            try:
                parsed = parser(payload)
            except Exception:  # pragma: no cover — a broken template never kills ingestion
                logger.warning("Lead parser crashed", exc_info=True)
                continue
            if parsed:
                return parsed
        return None



def _detach_record(db: Session, record: Optional[DBLeadIngestRecord]) -> Optional[DBLeadIngestRecord]:
    """Return the record usable after the session closes (refresh + expunge)."""
    if record is not None:
        db.refresh(record)
        db.expunge(record)
    return record


def resolve_brokerage_by_ingest_address(db: Session, to_address: str) -> Optional[DBBrokerage]:
    """
    `leads+{brokerage_slug}@…` → brokerage. The slug is the tenant boundary:
    brokerage A's address can never create conversations in brokerage B.
    """
    match = re.search(r"\+([a-z0-9\-]+)@", (to_address or "").lower())
    if not match:
        return None
    slug = match.group(1)
    return (
        db.query(DBBrokerage)
        .filter(DBBrokerage.slug == slug, DBBrokerage.status == "active")
        .first()
    )


# ── Listing resolution ─────────────────────────────────────────────────────────


def _resolve_listing(
    db: Session,
    *,
    brokerage_id: str,
    parsed: ParsedLead,
) -> tuple[Optional[DBListing], str]:
    listings = (
        db.query(DBListing)
        .filter(DBListing.brokerage_id == brokerage_id)
        .all()
    )
    # 1. Portal URL captured at listing creation.
    if parsed.portal_listing_url:
        for listing in listings:
            if listing.source_url and listing.source_url.strip().rstrip("/") == parsed.portal_listing_url.strip().rstrip("/"):
                return listing, "matched_url"
    # 2. Permit / Trakheesi number if present in the email.
    if parsed.portal_listing_ref:
        ref = parsed.portal_listing_ref.strip().lower()
        for listing in listings:
            spa = listing.spa_data or {}
            for key in ("trakheesi_number", "permit_number", "dld_permit", "rera_permit"):
                value = str(spa.get(key) or "").strip().lower()
                if value and value == ref:
                    return listing, "matched_permit"
    # 3. Fuzzy: project name appears in the subject/message — flagged for
    #    agent confirmation, never silently trusted.
    haystack = " ".join(filter(None, [parsed.buyer_message, parsed.portal_listing_url])).lower()
    if haystack:
        for listing in listings:
            project = str((listing.spa_data or {}).get("project") or "").lower()
            if project and len(project) > 4 and project in haystack:
                return listing, "fuzzy_pending"
    return None, "unresolved"


# ── Ingestion pipeline ─────────────────────────────────────────────────────────


def ingest_lead_email(
    db: Session,
    *,
    to_address: str,
    payload: dict,
    now: Optional[datetime] = None,
) -> IngestOutcome:
    """
    Path 1 (email, universal MVP). Never blocks a lead on listing resolution;
    never silently drops anything.
    """
    now = now or datetime.utcnow()
    brokerage = resolve_brokerage_by_ingest_address(db, to_address)
    if not brokerage:
        # Wrong/unknown ingest address — refuse without creating any tenant data.
        return IngestOutcome(status="dead_letter", details={"reason": "unknown_ingest_address"})

    parsed = EmailLeadAdapter().parse(payload)
    if not parsed:
        record = DBLeadIngestRecord(
            brokerage_id=brokerage.brokerage_id,
            source="unknown",
            status="dead_letter",
            error="unparseable_email",
            raw_payload=dict(payload),
        )
        db.add(record)
        record_compliance_event(
            db,
            brokerage_id=brokerage.brokerage_id,
            event_type="lead_email_dead_letter",
            direction="inbound",
            details={"subject": (payload.get("subject") or "")[:200]},
        )
        safe_commit(db)
        _notify_dead_letter(db, brokerage=brokerage, record=record)
        return IngestOutcome(status="dead_letter", record=_detach_record(db, record))

    return ingest_parsed_lead(db, brokerage=brokerage, parsed=parsed, raw_payload=payload, now=now)


def ingest_parsed_lead(
    db: Session,
    *,
    brokerage: DBBrokerage,
    parsed: ParsedLead,
    raw_payload: dict,
    now: Optional[datetime] = None,
) -> IngestOutcome:
    from app.db import crud

    now = now or datetime.utcnow()
    record = DBLeadIngestRecord(
        brokerage_id=brokerage.brokerage_id,
        source=parsed.source,
        parser_version=parsed.parser_version,
        buyer_name=parsed.buyer_name,
        buyer_phone=parsed.buyer_phone,
        buyer_message=parsed.buyer_message,
        portal_listing_ref=parsed.portal_listing_ref,
        portal_listing_url=parsed.portal_listing_url,
        raw_payload=dict(raw_payload),
        updated_at=now,
    )
    db.add(record)
    db.flush()

    listing, resolution = _resolve_listing(db, brokerage_id=brokerage.brokerage_id, parsed=parsed)
    record.listing_id = listing.listing_id if listing else None
    record.listing_resolution = resolution

    # Duplicate guard: same phone + same listing within 7 days → timeline only.
    if listing:
        duplicate = (
            db.query(DBLeadIngestRecord)
            .filter(
                DBLeadIngestRecord.brokerage_id == brokerage.brokerage_id,
                DBLeadIngestRecord.buyer_phone == parsed.buyer_phone,
                DBLeadIngestRecord.listing_id == listing.listing_id,
                DBLeadIngestRecord.ingest_id != record.ingest_id,
                DBLeadIngestRecord.first_touch_sent.is_(True),
                DBLeadIngestRecord.created_at >= now - DUPLICATE_WINDOW,
            )
            .first()
        )
        if duplicate:
            record.status = "duplicate"
            record.conversation_id = duplicate.conversation_id
            if duplicate.conversation_id:
                db.add(DBMessage(
                    conversation_id=duplicate.conversation_id,
                    role="user",
                    content=parsed.buyer_message or "[Repeat portal lead]",
                    intent="portal_lead_repeat",
                    metadata_json={"lead_ingest": {"ingest_id": record.ingest_id, "source": parsed.source}},
                ))
            safe_commit(db)
            duplicate_conversation_id = duplicate.conversation_id
            return IngestOutcome(status="duplicate", record=_detach_record(db, record), conversation_id=duplicate_conversation_id)

    # Existing conversation for this phone (any listing in the brokerage) →
    # attach as a timeline event, notify the agent, no duplicate first-touch.
    existing = (
        db.query(DBConversation)
        .filter(
            DBConversation.brokerage_id == brokerage.brokerage_id,
            DBConversation.buyer_phone == parsed.buyer_phone,
        )
        .order_by(DBConversation.updated_at.desc())
        .first()
    )
    if existing:
        record.status = "attached"
        record.conversation_id = existing.conversation_id
        db.add(DBMessage(
            conversation_id=existing.conversation_id,
            role="user",
            content=parsed.buyer_message or f"[New {parsed.source} lead for this buyer]",
            intent="portal_lead",
            metadata_json={"lead_ingest": {"ingest_id": record.ingest_id, "source": parsed.source}},
        ))
        existing.updated_at = now
        safe_commit(db)
        _notify_lead_event(
            db,
            brokerage=brokerage,
            agent_user_id=existing.assigned_agent_id,
            record=record,
            conversation_id=existing.conversation_id,
            body=f"Portal lead from {parsed.buyer_name or parsed.buyer_phone} attached to an existing conversation.",
        )
        return IngestOutcome(status="attached", record=_detach_record(db, record), conversation_id=existing.conversation_id)

    if not listing:
        # Never block a lead on listing resolution — record it, flag it,
        # surface it. Without a listing there is no conversation to create.
        record.status = "ingested"
        safe_commit(db)
        _notify_dead_letter(
            db,
            brokerage=brokerage,
            record=record,
            body=(
                f"New {parsed.source} lead from {parsed.buyer_name or parsed.buyer_phone} "
                "couldn't be matched to a listing — review and start the conversation manually."
            ),
        )
        return IngestOutcome(status="ingested", record=_detach_record(db, record), details={"listing": "unresolved"})

    conversation = crud.get_or_create_conversation(db, parsed.buyer_phone, listing.listing_id)
    if conversation is None:
        record.status = "ingested"
        record.error = "conversation_tenant_guard_blocked"
        safe_commit(db)
        _notify_dead_letter(
            db,
            brokerage=brokerage,
            record=record,
            body=(
                f"New {parsed.source} lead from {parsed.buyer_name or parsed.buyer_phone} "
                "landed on a listing without tenant-safe conversation context and was quarantined for review."
            ),
        )
        return IngestOutcome(
            status="ingested",
            record=_detach_record(db, record),
            details={"conversation": "quarantined"},
        )
    if parsed.buyer_name and not conversation.buyer_name:
        conversation.buyer_name = parsed.buyer_name
    record.conversation_id = conversation.conversation_id
    db.add(DBMessage(
        conversation_id=conversation.conversation_id,
        role="user",
        content=parsed.buyer_message or f"[{parsed.source} enquiry]",
        intent="portal_lead",
        metadata_json={
            "lead_ingest": {
                "ingest_id": record.ingest_id,
                "source": parsed.source,
                "state": "lead_ingested",
                "listing_resolution": resolution,
            }
        },
    ))

    # Hot-list entry with a strong recency score — a fresh lead outranks
    # stale conversations until the next scheduled re-score.
    from app.core.brokerage_access import get_or_create_lead_assignment

    assignment = get_or_create_lead_assignment(db, conversation)
    assignment.urgency_score = max(assignment.urgency_score or 0, LEAD_RECENCY_SCORE)
    assignment.signal = "new_portal_lead"
    assignment.next_action = "call_now"
    assignment.next_action_reason = "Fresh portal lead — speed-to-lead window is open."
    assignment.updated_at = now

    # Buyer profile source.
    profile = get_or_create_buyer_profile(
        db,
        brokerage_id=brokerage.brokerage_id,
        buyer_phone=parsed.buyer_phone,
        name=parsed.buyer_name,
        source="portal",
    )
    if not profile.source:
        profile.source = "portal"
    safe_commit(db)

    first_touch = _send_first_touch(
        db,
        brokerage=brokerage,
        record=record,
        conversation=conversation,
        listing=listing,
        now=now,
    )

    _notify_lead_event(
        db,
        brokerage=brokerage,
        agent_user_id=conversation.assigned_agent_id or listing.assigned_agent_id,
        record=record,
        conversation_id=conversation.conversation_id,
        body=(
            f"New {parsed.source.replace('_', ' ')} lead: "
            f"{parsed.buyer_name or parsed.buyer_phone} on {(listing.spa_data or {}).get('project', listing.listing_id)}. "
            + ("First-touch sent." if first_touch else "First-touch NOT sent — check the conversation.")
        ),
    )
    conversation_id = conversation.conversation_id
    return IngestOutcome(
        status="ingested",
        record=_detach_record(db, record),
        conversation_id=conversation_id,
        first_touch_sent=first_touch,
        details={"listing_resolution": resolution},
    )


def _send_first_touch(
    db: Session,
    *,
    brokerage: DBBrokerage,
    record: DBLeadIngestRecord,
    conversation: DBConversation,
    listing: DBListing,
    now: datetime,
) -> bool:
    """
    Template-locked auto-send — the one exception to draft-and-approve.
    Variable slots only; no free-form AI content.
    """
    from app.api.whatsapp import send_whatsapp_reply

    if is_buyer_suppressed(db, brokerage.brokerage_id, conversation.buyer_phone):
        record_compliance_event(
            db,
            brokerage_id=brokerage.brokerage_id,
            conversation_id=conversation.conversation_id,
            listing_id=listing.listing_id,
            buyer_phone=conversation.buyer_phone,
            event_type="lead_first_touch_blocked_opt_out",
            direction="outbound",
            details={"ingest_id": record.ingest_id},
        )
        safe_commit(db)
        return False

    spa = listing.spa_data or {}
    body = FIRST_TOUCH_TEMPLATE.format(
        buyer_name=(record.buyer_name or "there").split(" ")[0],
        listing_label=spa.get("project") or "the property",
        portal=record.source.replace("_", " ").title(),
        brokerage_name=brokerage.name,
    )
    send_whatsapp_reply(
        f"whatsapp:{conversation.buyer_phone}",
        body,
        from_number=brokerage.brokerage_ai_number,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=listing.listing_id,
    )
    db.add(DBMessage(
        conversation_id=conversation.conversation_id,
        role="assistant",
        content=body,
        intent="lead_first_touch",
        metadata_json={
            "template_name": FIRST_TOUCH_TEMPLATE_NAME,
            "template_version": FIRST_TOUCH_TEMPLATE_VERSION,
            "ingest_id": record.ingest_id,
        },
    ))
    record.first_touch_sent = True
    record.first_touch_template = f"{FIRST_TOUCH_TEMPLATE_NAME}:{FIRST_TOUCH_TEMPLATE_VERSION}"
    record.updated_at = now
    record_compliance_event(
        db,
        brokerage_id=brokerage.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=listing.listing_id,
        buyer_phone=conversation.buyer_phone,
        event_type="lead_first_touch_sent",
        direction="outbound",
        details={
            "template_name": FIRST_TOUCH_TEMPLATE_NAME,
            "template_version": FIRST_TOUCH_TEMPLATE_VERSION,
            "consent_basis": "portal_lead_form_submission",
            "consent_evidence": f"lead_ingests:{record.ingest_id}",
            "source": record.source,
        },
    )
    safe_commit(db)
    return True


def _notify_lead_event(
    db: Session,
    *,
    brokerage: DBBrokerage,
    agent_user_id: Optional[str],
    record: DBLeadIngestRecord,
    conversation_id: Optional[str],
    body: str,
) -> None:
    """DAL-162 catalog event #2 — the highest-urgency event in the system."""
    if not agent_user_id:
        return
    try:
        from app.core.agent_notifications import notify_agent

        notify_agent(
            db,
            brokerage=brokerage,
            agent_user_id=agent_user_id,
            event_type="lead_first_touch",
            body=body,
            dedupe_key=f"lead_first_touch:{record.ingest_id}",
            conversation_id=conversation_id,
            listing_id=record.listing_id,
            deep_link_path=(
                f"/agent/conversations/{conversation_id}" if conversation_id else "/agent"
            ),
        )
    except Exception:  # pragma: no cover
        logger.warning("lead_first_touch notification failed", exc_info=True)


def _notify_dead_letter(
    db: Session,
    *,
    brokerage: DBBrokerage,
    record: DBLeadIngestRecord,
    body: Optional[str] = None,
) -> None:
    """Event #10 (ai_failure) for the dead-letter queue — never silent."""
    try:
        from app.core.agent_notifications import notify_agent
        from app.models.db_models import DBAgentProfile

        # No listing → no assigned agent; route to the brokerage's first agent
        # profile so a human always sees the dead letter.
        agent = (
            db.query(DBAgentProfile)
            .filter(DBAgentProfile.brokerage_id == brokerage.brokerage_id)
            .order_by(DBAgentProfile.created_at.asc())
            .first()
        )
        if not agent:
            return
        notify_agent(
            db,
            brokerage=brokerage,
            agent_user_id=agent.user_id,
            event_type="ai_failure",
            body=body or "A portal lead email couldn't be parsed — check the lead inbox.",
            dedupe_key=f"lead_dead_letter:{record.ingest_id}",
            deep_link_path="/agent",
        )
    except Exception:  # pragma: no cover
        logger.warning("dead-letter notification failed", exc_info=True)


# ── 48h nudge (review-only draft, normal approval flow) ───────────────────────


def create_first_touch_nudge_drafts(db: Session, *, now: Optional[datetime] = None) -> int:
    """
    One review-only draft per lead whose first-touch got no reply in 48h.
    Enters the agent's normal draft queue — never auto-sent.
    """
    now = now or datetime.utcnow()
    candidates = (
        db.query(DBLeadIngestRecord)
        .filter(
            DBLeadIngestRecord.first_touch_sent.is_(True),
            DBLeadIngestRecord.nudge_draft_id.is_(None),
            DBLeadIngestRecord.conversation_id.isnot(None),
            DBLeadIngestRecord.created_at <= now - NUDGE_AFTER,
        )
        .all()
    )
    created = 0
    for record in candidates:
        replied = (
            db.query(DBMessage)
            .filter(
                DBMessage.conversation_id == record.conversation_id,
                DBMessage.role == "user",
                DBMessage.timestamp > record.created_at,
                DBMessage.intent.notin_(["portal_lead", "portal_lead_repeat"]),
            )
            .count()
            > 0
        )
        if replied:
            record.nudge_draft_id = "not_needed"
            continue
        if is_buyer_suppressed(db, record.brokerage_id, record.buyer_phone):
            record.nudge_draft_id = "suppressed"  # STOP propagated — no nudge
            continue
        conversation = db.get(DBConversation, record.conversation_id)
        if not conversation:
            continue
        buyer = (record.buyer_name or "there").split(" ")[0]
        draft = DBDraftReply(
            brokerage_id=record.brokerage_id,
            conversation_id=record.conversation_id,
            listing_id=record.listing_id,
            buyer_phone=record.buyer_phone,
            agent_user_id=conversation.assigned_agent_id,
            intent="follow_up",
            draft_text=(
                f"Hi {buyer}, following up on your enquiry — would you like more "
                "details or a viewing this week?"
            ),
            source="lead_first_touch_nudge",
            status="draft",
            metadata_json={"ingest_id": record.ingest_id},
        )
        db.add(draft)
        db.flush()
        record.nudge_draft_id = draft.draft_id
        record.updated_at = now
        created += 1
    safe_commit(db)
    return created
