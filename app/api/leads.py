"""
Lead ingestion webhook (DAL-163).

Inbound-email providers (Mailgun/SendGrid routes, or a forwarding worker)
POST parsed emails here. The `to` address carries the brokerage slug
(`leads+{slug}@…`) — the tenant boundary. A shared secret guards the
endpoint; a forged forward to another brokerage's address still cannot cross
tenants because the slug resolves the brokerage that owns the lead.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.lead_ingest import ingest_lead_email
from app.core.runtime_config import is_production
from app.core.webhook_security import mark_inbound_provider_event, record_inbound_provider_event
from app.db.session import get_db, set_service_db_session_context

router = APIRouter()
logger = logging.getLogger(__name__)


class InboundLeadEmail(BaseModel):
    to: str
    sender: Optional[str] = None
    subject: Optional[str] = None
    body: str


@router.post("/leads/ingest/email")
async def ingest_email(
    payload: InboundLeadEmail,
    x_ingest_secret: Optional[str] = Header(default=None),
    x_provider_event_id: Optional[str] = Header(default=None),
    x_provider: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    secret = os.getenv("LEAD_INGEST_SECRET", "")
    if is_production() and not secret:
        raise HTTPException(status_code=503, detail="Lead ingest verification is not configured")
    if secret and x_ingest_secret != secret:
        raise HTTPException(status_code=403, detail="Invalid ingest secret")

    provider = (x_provider or "lead_email").strip().lower() or "lead_email"
    payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    set_service_db_session_context(db)
    is_new_event = record_inbound_provider_event(
        db,
        provider=provider,
        endpoint="leads/ingest/email",
        provider_event_id=x_provider_event_id,
        payload=payload_dict,
    )
    if not is_new_event:
        return {
            "status": "duplicate",
            "ingest_id": None,
            "conversation_id": None,
            "first_touch_sent": False,
            "details": {"reason": "provider_event_replay"},
        }

    try:
        outcome = ingest_lead_email(
            db,
            to_address=payload.to,
            payload={
                "sender": payload.sender,
                "subject": payload.subject,
                "body": payload.body,
            },
        )
        mark_inbound_provider_event(
            db,
            provider=provider,
            endpoint="leads/ingest/email",
            provider_event_id=x_provider_event_id,
            payload=payload_dict,
            status="processed",
        )
        if outcome.status == "dead_letter" and outcome.record is None:
            # Unknown ingest address — nothing was created for any tenant.
            raise HTTPException(status_code=404, detail="Unknown ingest address")
        return {
            "status": outcome.status,
            "ingest_id": outcome.record.ingest_id if outcome.record else None,
            "conversation_id": outcome.conversation_id,
            "first_touch_sent": outcome.first_touch_sent,
            "details": outcome.details,
        }
    except HTTPException:
        raise
    except Exception:
        mark_inbound_provider_event(
            db,
            provider=provider,
            endpoint="leads/ingest/email",
            provider_event_id=x_provider_event_id,
            payload=payload_dict,
            status="failed",
        )
        raise
