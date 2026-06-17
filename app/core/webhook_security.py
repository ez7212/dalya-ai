from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import safe_commit
from app.models.db_models import DBInboundProviderEvent

logger = logging.getLogger(__name__)


def payload_fingerprint(payload: Any) -> str:
    normalized = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def record_inbound_provider_event(
    db: Session,
    *,
    provider: str,
    endpoint: str,
    provider_event_id: Optional[str],
    payload: Any,
    brokerage_id: Optional[str] = None,
    processing_retry_after_seconds: int = 120,
) -> bool:
    """Return True when this inbound event is new, False for a replay."""
    event_id = (provider_event_id or "").strip() or None
    fingerprint = payload_fingerprint(payload)

    query = db.query(DBInboundProviderEvent).filter(
        DBInboundProviderEvent.provider == provider,
        DBInboundProviderEvent.endpoint == endpoint,
    )
    if event_id:
        existing = query.filter(DBInboundProviderEvent.provider_event_id == event_id).first()
    else:
        existing = query.filter(DBInboundProviderEvent.payload_fingerprint == fingerprint).first()
    if existing:
        retry_cutoff = datetime.utcnow() - timedelta(seconds=processing_retry_after_seconds)
        if existing.status == "failed":
            existing.status = "processing"
            existing.replayed_at = datetime.utcnow()
            existing.replay_count = (existing.replay_count or 0) + 1
            safe_commit(db)
            return True
        if existing.status == "processing" and existing.received_at <= retry_cutoff:
            existing.replayed_at = datetime.utcnow()
            existing.replay_count = (existing.replay_count or 0) + 1
            safe_commit(db)
            return True
        existing.replayed_at = datetime.utcnow()
        existing.replay_count = (existing.replay_count or 0) + 1
        safe_commit(db)
        return False

    db.add(
        DBInboundProviderEvent(
            event_id=str(uuid.uuid4()),
            provider=provider,
            endpoint=endpoint,
            provider_event_id=event_id,
            payload_fingerprint=fingerprint,
            brokerage_id=brokerage_id,
            status="processing",
        )
    )
    try:
        safe_commit(db)
    except IntegrityError:
        db.rollback()
        logger.info(
            "Duplicate inbound provider event ignored provider=%s endpoint=%s has_event_id=%s",
            provider,
            endpoint,
            bool(event_id),
        )
        return False
    return True


def mark_inbound_provider_event(
    db: Session,
    *,
    provider: str,
    endpoint: str,
    provider_event_id: Optional[str],
    payload: Any,
    status: str,
) -> None:
    event_id = (provider_event_id or "").strip() or None
    fingerprint = payload_fingerprint(payload)
    query = db.query(DBInboundProviderEvent).filter(
        DBInboundProviderEvent.provider == provider,
        DBInboundProviderEvent.endpoint == endpoint,
    )
    if event_id:
        event = query.filter(DBInboundProviderEvent.provider_event_id == event_id).first()
    else:
        event = query.filter(DBInboundProviderEvent.payload_fingerprint == fingerprint).first()
    if not event:
        return
    event.status = status
    safe_commit(db)
