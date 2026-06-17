"""
Agent notification framework (DAL-162).

Anything that requires opening /agent to discover will be discovered hours
late. Every time-sensitive event pushes to the agent's WhatsApp via Agents AI
with a deep link to the exact /agent/... surface; review-class events queue
for the morning hot-list digest.

Event catalog (defaults; the existing escalation envelope is entry #1 and is
unchanged — it records here for audit):

  #   event_type            urgency     quiet-hours behavior
  1   escalation_alert      immediate   sends (existing behavior)
  2   lead_first_touch      immediate   sends (speed-to-lead at 11pm is the point)
  3   hot_buyer_reply       immediate   queues for morning digest
  4   viewing_buyer_update  immediate   sends
  5   tenant_confirmation   immediate   sends (declines put the viewing at risk)
  6   viewing_reminder      immediate   queues
  7   feedback_received     immediate   queues
  8   drafts_pending        digest      (drafts are review work, not interrupts)
  9   buyer_opt_out         immediate   sends (compliance-relevant)
  10  ai_failure            immediate   sends (silent failures forbidden)
  11  calendar_error        immediate   sends, once per error state (dedupe)
  12  takeover_stale        digest      (conversation agent_controlled > 48h)
  13  hot_list_ready        digest      anchor — events 8 and 12 ride along

Mechanics: dedupe keys prevent double pushes on retried webhooks/jobs;
per-agent preferences (per-event on/off + quiet hours) live on the agent
profile; a rate guard caps immediate pushes per agent per hour with an
overflow collapse. Suppressions are recorded, never silently dropped —
the audit row always exists.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.messaging import get_transport
from app.core.messaging.types import OutboundAgentMessage
from app.db.session import safe_commit
from app.models.db_models import (
    DBAgentNotification,
    DBAgentProfile,
    DBBrokerage,
    DBConversation,
    DBDraftReply,
)

logger = logging.getLogger(__name__)

RATE_GUARD_PER_HOUR = int(os.getenv("AGENT_NOTIFICATIONS_HOURLY_CAP", "20"))
DEFAULT_QUIET_START = "22:00"
DEFAULT_QUIET_END = "07:00"
TAKEOVER_STALE_AFTER = timedelta(hours=48)


@dataclass(frozen=True)
class EventSpec:
    urgency: str               # immediate | digest
    sends_in_quiet_hours: bool


EVENT_CATALOG: dict[str, EventSpec] = {
    "escalation_alert":     EventSpec("immediate", True),
    "lead_first_touch":     EventSpec("immediate", True),
    "hot_buyer_reply":      EventSpec("immediate", False),
    "viewing_buyer_update": EventSpec("immediate", True),
    "tenant_confirmation":  EventSpec("immediate", True),
    "viewing_reminder":     EventSpec("immediate", False),
    "feedback_received":    EventSpec("immediate", False),
    "drafts_pending":       EventSpec("digest", False),
    "buyer_opt_out":        EventSpec("immediate", True),
    "ai_failure":           EventSpec("immediate", True),
    "calendar_error":       EventSpec("immediate", True),
    "takeover_stale":       EventSpec("digest", False),
    "hot_list_ready":       EventSpec("digest", False),
}


def _agent_profile(db: Session, brokerage_id: str, agent_user_id: str) -> Optional[DBAgentProfile]:
    return (
        db.query(DBAgentProfile)
        .filter(
            DBAgentProfile.brokerage_id == brokerage_id,
            DBAgentProfile.user_id == agent_user_id,
        )
        .first()
    )


def notification_preferences(profile: Optional[DBAgentProfile]) -> dict:
    settings = profile.settings if profile and isinstance(profile.settings, dict) else {}
    prefs = settings.get("notifications") or {}
    return {
        "events": dict(prefs.get("events") or {}),  # event_type → bool (default on)
        "quiet_hours": {
            "start": str((prefs.get("quiet_hours") or {}).get("start") or DEFAULT_QUIET_START),
            "end": str((prefs.get("quiet_hours") or {}).get("end") or DEFAULT_QUIET_END),
        },
    }


def _brokerage_timezone(brokerage: Optional[DBBrokerage]) -> ZoneInfo:
    settings = brokerage.settings if brokerage and isinstance(brokerage.settings, dict) else {}
    name = str(settings.get("timezone") or settings.get("brokerage_timezone") or "Asia/Dubai")
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Asia/Dubai")


def _parse_clock(value: str, fallback: str) -> time:
    try:
        hour, minute = value.split(":")
        return time(int(hour), int(minute))
    except Exception:
        hour, minute = fallback.split(":")
        return time(int(hour), int(minute))


def in_quiet_hours(
    *,
    brokerage: DBBrokerage,
    prefs: dict,
    now: Optional[datetime] = None,
) -> bool:
    now = now or datetime.utcnow()
    local = now.replace(tzinfo=ZoneInfo("UTC")).astimezone(_brokerage_timezone(brokerage)).time()
    start = _parse_clock(prefs["quiet_hours"]["start"], DEFAULT_QUIET_START)
    end = _parse_clock(prefs["quiet_hours"]["end"], DEFAULT_QUIET_END)
    if start <= end:
        return start <= local < end
    return local >= start or local < end  # window crosses midnight


def _deep_link(brokerage: DBBrokerage, path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    base = ""
    if isinstance(brokerage.settings, dict):
        base = str(brokerage.settings.get("dashboard_url") or "")
    base = (base or os.getenv("DASHBOARD_BASE_URL", "")).rstrip("/")
    return f"{base}{path}" if base else path


def _rate_guard_state(db: Session, *, brokerage_id: str, agent_user_id: str, now: datetime) -> tuple[int, bool]:
    cutoff = now - timedelta(hours=1)
    sent_count = (
        db.query(DBAgentNotification)
        .filter(
            DBAgentNotification.brokerage_id == brokerage_id,
            DBAgentNotification.agent_user_id == agent_user_id,
            DBAgentNotification.status == "sent",
            DBAgentNotification.created_at >= cutoff,
        )
        .count()
    )
    collapsed_recent = (
        db.query(DBAgentNotification)
        .filter(
            DBAgentNotification.brokerage_id == brokerage_id,
            DBAgentNotification.agent_user_id == agent_user_id,
            DBAgentNotification.status == "collapsed_rate",
            DBAgentNotification.created_at >= cutoff,
        )
        .all()
    )
    overflow_notified = any(
        (row.metadata_json or {}).get("overflow_message_sent") for row in collapsed_recent
    )
    return sent_count, overflow_notified


def notify_agent(
    db: Session,
    *,
    brokerage: DBBrokerage,
    agent_user_id: str,
    event_type: str,
    body: str,
    dedupe_key: Optional[str] = None,
    conversation_id: Optional[str] = None,
    viewing_id: Optional[str] = None,
    listing_id: Optional[str] = None,
    deep_link_path: Optional[str] = None,
    record_only: bool = False,
    now: Optional[datetime] = None,
) -> DBAgentNotification:
    """
    Route one catalog event for one agent. Returns the audit row whatever the
    outcome — sent, queued for digest, suppressed by preference, or collapsed
    by the rate guard. `record_only` records an event whose push already went
    out on its own channel (e.g. the escalation envelope itself).
    """
    now = now or datetime.utcnow()
    spec = EVENT_CATALOG.get(event_type)
    if spec is None:
        raise ValueError(f"Unknown notification event_type: {event_type}")

    if dedupe_key:
        existing = (
            db.query(DBAgentNotification)
            .filter(DBAgentNotification.dedupe_key == dedupe_key)
            .first()
        )
        if existing:
            return existing  # retried webhook/job — exactly-once per trigger

    profile = _agent_profile(db, brokerage.brokerage_id, agent_user_id)
    prefs = notification_preferences(profile)
    deep_link = _deep_link(brokerage, deep_link_path)

    notification = DBAgentNotification(
        brokerage_id=brokerage.brokerage_id,
        agent_user_id=agent_user_id,
        event_type=event_type,
        urgency=spec.urgency,
        conversation_id=conversation_id,
        viewing_id=viewing_id,
        listing_id=listing_id,
        dedupe_key=dedupe_key,
        body=body,
        deep_link=deep_link,
        metadata_json={},
    )
    db.add(notification)

    # Preference toggle off → suppressed and recorded, never silently dropped.
    if prefs["events"].get(event_type) is False:
        notification.status = "suppressed_pref"
        safe_commit(db)
        return notification

    if record_only:
        notification.status = "sent"
        notification.sent_at = now
        notification.metadata_json = {"record_only": True}
        safe_commit(db)
        return notification

    if spec.urgency == "digest":
        notification.status = "queued_digest"
        safe_commit(db)
        return notification

    if in_quiet_hours(brokerage=brokerage, prefs=prefs, now=now) and not spec.sends_in_quiet_hours:
        notification.status = "queued_digest"
        notification.metadata_json = {"queued_reason": "quiet_hours"}
        safe_commit(db)
        return notification

    sent_count, overflow_notified = _rate_guard_state(
        db, brokerage_id=brokerage.brokerage_id, agent_user_id=agent_user_id, now=now
    )
    if sent_count >= RATE_GUARD_PER_HOUR:
        notification.status = "collapsed_rate"
        if not overflow_notified:
            notification.metadata_json = {"overflow_message_sent": True}
            _push(brokerage, profile, body=(
                "You have more updates than I can usefully push right now — "
                f"see the dashboard for everything new: {_deep_link(brokerage, '/agent') or '/agent'}"
            ))
        safe_commit(db)
        return notification

    push_body = body if not deep_link else f"{body}\n{deep_link}"
    sid = _push(brokerage, profile, body=push_body)
    if sid is None:
        notification.status = "failed"
    else:
        notification.status = "sent"
        notification.sent_at = now
        notification.whatsapp_message_sid = sid
    safe_commit(db)
    return notification


def _push(
    brokerage: DBBrokerage,
    profile: Optional[DBAgentProfile],
    *,
    body: str,
) -> Optional[str]:
    if not (brokerage.agents_ai_number and profile and profile.whatsapp_phone):
        return None
    result = get_transport().send_to_agents_ai(
        OutboundAgentMessage(
            brokerage_id=brokerage.brokerage_id,
            agents_ai_number=brokerage.agents_ai_number,
            agent_phone=profile.whatsapp_phone,
            body=body,
            conversation_id="",
            listing_id="",
            buyer_phone="",
            escalation_type="agent_notification",
        )
    )
    return result.transport_message_id if result.ok else None


# ── Morning digest (event #13 anchor; events 8 and 12 ride along) ─────────────


def send_morning_digest(
    db: Session,
    *,
    brokerage: DBBrokerage,
    agent_user_id: str,
    now: Optional[datetime] = None,
) -> Optional[DBAgentNotification]:
    """
    One message: queued digest items + pending draft count + conversations
    still in takeover for more than 48 hours.
    """
    now = now or datetime.utcnow()
    profile = _agent_profile(db, brokerage.brokerage_id, agent_user_id)

    queued = (
        db.query(DBAgentNotification)
        .filter(
            DBAgentNotification.brokerage_id == brokerage.brokerage_id,
            DBAgentNotification.agent_user_id == agent_user_id,
            DBAgentNotification.status == "queued_digest",
        )
        .order_by(DBAgentNotification.created_at.asc())
        .all()
    )
    draft_count = (
        db.query(DBDraftReply)
        .filter(
            DBDraftReply.brokerage_id == brokerage.brokerage_id,
            DBDraftReply.agent_user_id == agent_user_id,
            DBDraftReply.status.in_(["draft", "edited"]),
        )
        .count()
    )
    stale_takeovers = (
        db.query(DBConversation)
        .filter(
            DBConversation.brokerage_id == brokerage.brokerage_id,
            DBConversation.assigned_agent_id == agent_user_id,
            DBConversation.ai_mode == "agent_controlled",
            DBConversation.ai_mode_changed_at <= now - TAKEOVER_STALE_AFTER,
        )
        .all()
    )

    if not queued and not draft_count and not stale_takeovers:
        return None

    lines = ["Morning hot list is ready."]
    if queued:
        lines.append(f"\nWhile you were away ({len(queued)}):")
        for item in queued[:10]:
            lines.append(f"• {item.body}")
        if len(queued) > 10:
            lines.append(f"…and {len(queued) - 10} more on the dashboard.")
    if draft_count:
        lines.append(f"\n{draft_count} AI draft{'s' if draft_count != 1 else ''} waiting for your review.")
    for conversation in stale_takeovers:
        buyer = conversation.buyer_name or conversation.buyer_phone
        lines.append(f"\nDalya is still paused for {buyer} (over 48h) — reply RESUME on their thread or use the dashboard.")
    body = "\n".join(lines)

    for item in queued:
        item.status = "digested"
        metadata = dict(item.metadata_json or {})
        metadata["digested_at"] = now.isoformat()
        item.metadata_json = metadata

    digest = DBAgentNotification(
        brokerage_id=brokerage.brokerage_id,
        agent_user_id=agent_user_id,
        event_type="hot_list_ready",
        urgency="digest",
        body=body,
        deep_link=_deep_link(brokerage, "/agent"),
        metadata_json={
            "queued_count": len(queued),
            "draft_count": draft_count,
            "stale_takeover_count": len(stale_takeovers),
        },
    )
    db.add(digest)
    sid = _push(brokerage, profile, body=f"{body}\n{_deep_link(brokerage, '/agent') or ''}".strip())
    digest.status = "sent" if sid else "failed"
    digest.sent_at = now if sid else None
    digest.whatsapp_message_sid = sid
    safe_commit(db)
    return digest
