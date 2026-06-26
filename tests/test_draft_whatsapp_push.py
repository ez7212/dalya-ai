"""Push a reply draft to the agent's WhatsApp, then verify delete-on-handle.

Exercises the full loop with the simulated transport:
  push_draft_to_whatsapp -> mints an agent reply route linked to the draft
  agent replies from their phone -> relay_agent_reply consumes the route and
  discards the linked draft.
"""
import os
import uuid
from datetime import datetime

import pytest

os.environ.setdefault("MESSAGING_TRANSPORT", "simulated")

from app.core.agent_relay import relay_agent_reply
from app.core.messaging.types import InboundEnvelope
from app.db.session import SessionLocal
from app.models.db_models import (
    DBAgentMessageRoute,
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageMember,
    DBConversation,
    DBDraftReply,
    DBListing,
)


def _seed(db):
    bk_id = f"bk-{uuid.uuid4().hex[:8]}"
    db.add(DBBrokerage(
        brokerage_id=bk_id, name="Push Test Realty", slug=bk_id,
        agents_ai_number="+971590000001", brokerage_ai_number="+971590000002",
    ))
    listing = DBListing(
        listing_id=f"lst-{uuid.uuid4().hex[:8]}", brokerage_id=bk_id,
        spa_data={"imported_listing": {"project": "Test Tower"}}, commission_rate=0.02,
    )
    db.add(listing)
    db.flush()
    conv = DBConversation(
        conversation_id=f"conv-{uuid.uuid4().hex[:8]}", brokerage_id=bk_id,
        listing_id=listing.listing_id, buyer_phone="+971500001111", buyer_name="Test Buyer",
        assigned_agent_id="agent-push",
    )
    db.add(conv)
    db.add(DBBrokerageMember(brokerage_id=bk_id, user_id="agent-push", email="a@a.com", role="agent"))
    db.add(DBAgentProfile(
        brokerage_id=bk_id, user_id="agent-push", email="a@a.com",
        full_name="Agent Push", display_name="Agent Push",
        whatsapp_phone="+971555550000", rera_broker_card_number="RERA-1",
    ))
    draft = DBDraftReply(
        brokerage_id=bk_id, conversation_id=conv.conversation_id, listing_id=listing.listing_id,
        buyer_phone=conv.buyer_phone, agent_user_id="agent-push", intent="follow_up",
        draft_text="Hi! Following up on the Test Tower unit — still interested?", status="draft",
    )
    db.add(draft)
    db.commit()
    return bk_id, conv, draft


def test_push_then_agent_reply_discards_draft():
    db = SessionLocal()
    try:
        bk_id, conv, draft = _seed(db)
        brokerage = db.get(DBBrokerage, bk_id)

        # Push the draft to the agent's WhatsApp via the endpoint handler.
        from app.api.agent_dashboard import push_draft_to_whatsapp
        from app.core.auth import CurrentUser
        from app.core.brokerage_access import _REQUESTED_BROKERAGE_ID

        _REQUESTED_BROKERAGE_ID.set(bk_id)
        result = push_draft_to_whatsapp(
            draft_id=draft.draft_id, user=CurrentUser(id="agent-push", email="a@a.com"), db=db,
        )
        assert result["pushed_to_whatsapp"] is True

        route = (
            db.query(DBAgentMessageRoute)
            .filter(DBAgentMessageRoute.draft_id == draft.draft_id)
            .first()
        )
        assert route is not None
        assert route.escalation_type == "agent_draft_push"
        token = route.agents_ai_envelope_token
        assert token

        # Agent replies from their phone, quoting the [Ref: TOKEN].
        inbound = InboundEnvelope(
            transport="simulated",
            from_number="+971555550000",  # the agent's whatsapp_phone
            to_number="+971590000001",     # the brokerage agents_ai_number
            body=f"Yes still available, let's schedule a viewing.\n\n[Ref: {token}]",
            message_sid=f"sim-{uuid.uuid4().hex[:8]}",
            envelope_token=token,
        )
        relay_agent_reply(db, brokerage=brokerage, inbound=inbound, now=datetime.utcnow())
        db.commit()

        db.refresh(draft)
        db.refresh(route)
        assert route.consumed_at is not None
        assert draft.status == "discarded"
        assert (draft.metadata_json or {}).get("handled_via") == "agent_whatsapp_reply"
    finally:
        db.rollback()
        db.close()
