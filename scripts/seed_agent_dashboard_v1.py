"""
Seed a small v1 agent dashboard dataset for the active brokerage.

The script is idempotent. It prefers an existing active brokerage member, then
falls back to DEFAULT_BROKERAGE_ID and DEFAULT_AGENT_USER_ID/ADMIN_USER_ID.
"""

import os
from datetime import datetime, timedelta

from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBAIDraft,
    DBBrokerage,
    DBBrokerageMember,
    DBCampaign,
    DBCampaignRecipient,
    DBCampaignUpload,
    DBConversation,
    DBDraftReply,
    DBLeadAssignment,
    DBLeadTask,
    DBListing,
    DBMarketingEvent,
    DBMarketingPage,
    DBMessage,
    DBOwnerLead,
    DBOutreachDraft,
    DBViewing,
)


DEFAULT_BROKERAGE_ID = os.getenv("DEFAULT_BROKERAGE_ID", "dalya-internal")
DEFAULT_BROKERAGE_SLUG = os.getenv("DEFAULT_BROKERAGE_SLUG", "dalya-internal")
DEFAULT_BROKERAGE_NAME = os.getenv("DEFAULT_BROKERAGE_NAME", "Dalya Internal Pilot")
DEFAULT_AGENT_USER_ID = (
    os.getenv("DEFAULT_AGENT_USER_ID")
    or os.getenv("ADMIN_USER_ID")
    or "dalya-demo-agent"
)
DEFAULT_AGENT_EMAIL = os.getenv("DEFAULT_AGENT_EMAIL", "agent@dalya.local")


def _first_active_context(db):
    member = (
        db.query(DBBrokerageMember)
        .filter(DBBrokerageMember.status == "active")
        .order_by(DBBrokerageMember.created_at.asc())
        .first()
    )
    if member:
        brokerage = db.get(DBBrokerage, member.brokerage_id)
        if brokerage:
            return brokerage, member

    brokerage = db.get(DBBrokerage, DEFAULT_BROKERAGE_ID)
    if not brokerage:
        brokerage = DBBrokerage(
            brokerage_id=DEFAULT_BROKERAGE_ID,
            name=DEFAULT_BROKERAGE_NAME,
            slug=DEFAULT_BROKERAGE_SLUG,
            status="active",
        )
        db.add(brokerage)

    member = (
        db.query(DBBrokerageMember)
        .filter(
            DBBrokerageMember.brokerage_id == DEFAULT_BROKERAGE_ID,
            DBBrokerageMember.user_id == DEFAULT_AGENT_USER_ID,
        )
        .first()
    )
    if not member:
        member = DBBrokerageMember(
            brokerage_id=DEFAULT_BROKERAGE_ID,
            user_id=DEFAULT_AGENT_USER_ID,
            email=DEFAULT_AGENT_EMAIL,
            display_name="Dalya Demo Agent",
            role="agent",
            status="active",
        )
        db.add(member)
    return brokerage, member


def _upsert(db, model, key, values):
    row = db.get(model, key)
    if row is None:
        row = model(**{**values, _primary_key_name(model): key})
        db.add(row)
    else:
        for field, value in values.items():
            setattr(row, field, value)
    return row


def _primary_key_name(model) -> str:
    return next(iter(model.__table__.primary_key.columns)).name


def main() -> None:
    now = datetime.utcnow()
    with SessionLocal() as db:
        brokerage, member = _first_active_context(db)
        brokerage_id = brokerage.brokerage_id
        agent_user_id = member.user_id

        listing = _upsert(db, DBListing, "agent-dashboard-sample-listing-1", {
            "brokerage_id": brokerage_id,
            "assigned_agent_id": agent_user_id,
            "seller_id": "sample-seller-1",
            "seller_phone": "+971501110000",
            "spa_data": {
                "project": "Downtown resale apartment",
                "developer": "Emaar Properties",
                "unit_number": "A-2402",
                "unit_type": "2BR",
                "bedrooms": 2,
                "property_status": "ready",
                "noc_status": "eligible",
            },
            "community_data": {"area": "Downtown Dubai"},
            "seller_asking_price": 2450000,
            "seller_notes": "Demo listing for the agent dashboard.",
            "negotiation_threshold_aed": 2380000,
            "seller_qa": [],
            "media_urls": [],
            "processing_stages": {},
        })

        conv = _upsert(db, DBConversation, "agent-dashboard-sample-conv-1", {
            "listing_id": listing.listing_id,
            "brokerage_id": brokerage_id,
            "assigned_agent_id": agent_user_id,
            "buyer_phone": "+971502148821",
            "buyer_name": "Ahmed K.",
            "detected_budget": 2400000,
            "escalation_triggered": True,
            "escalation_reason": "viewing_request",
            "last_escalated_at": now - timedelta(minutes=20),
            "pending_forwarded_questions": [],
            "alerted_questions": [],
            "ai_summary": {
                "interest_level": "high",
                "key_question": "Evening viewing availability",
                "next_step_hint": "Confirm viewing slot and access",
            },
            "last_summarized_at": now - timedelta(minutes=15),
            "updated_at": now - timedelta(minutes=18),
        })
        db.flush()

        if not db.query(DBMessage).filter(DBMessage.conversation_id == conv.conversation_id).first():
            db.add_all([
                DBMessage(
                    conversation_id=conv.conversation_id,
                    role="user",
                    content="Hi, is this Downtown unit still available?",
                    intent="general_enquiry",
                    timestamp=now - timedelta(minutes=34),
                ),
                DBMessage(
                    conversation_id=conv.conversation_id,
                    role="assistant",
                    content="Yes, it is available. It is a 2BR Downtown resale listed at AED 2.45M.",
                    intent="general_enquiry",
                    timestamp=now - timedelta(minutes=32),
                ),
                DBMessage(
                    conversation_id=conv.conversation_id,
                    role="user",
                    content="Can I see it after 6 today?",
                    intent="viewing_request",
                    timestamp=now - timedelta(minutes=18),
                ),
            ])
            db.flush()

        _upsert(db, DBLeadAssignment, "agent-dashboard-sample-assignment-1", {
            "brokerage_id": brokerage_id,
            "conversation_id": conv.conversation_id,
            "listing_id": listing.listing_id,
            "buyer_phone": conv.buyer_phone,
            "assigned_agent_id": agent_user_id,
            "assigned_by": "seed_agent_dashboard_v1.py",
            "status": "viewing",
            "signal": "ready_to_view",
            "urgency_score": 94,
            "next_action": "call_now",
            "next_action_reason": "Confirmed budget and asked for evening viewing slots.",
            "due_at": now + timedelta(minutes=20),
            "last_buyer_message_at": now - timedelta(minutes=18),
            "metadata_json": {"seeded": True},
            "updated_at": now,
        })

        _upsert(db, DBLeadTask, "agent-dashboard-sample-task-1", {
            "task_key": f"{brokerage_id}:sample:call-ahmed",
            "brokerage_id": brokerage_id,
            "conversation_id": conv.conversation_id,
            "listing_id": listing.listing_id,
            "buyer_phone": conv.buyer_phone,
            "assigned_agent_id": agent_user_id,
            "task_type": "call",
            "title": "Call Ahmed K. about evening viewing",
            "description": "Buyer is ready to view and has budget fit.",
            "status": "open",
            "priority": "high",
            "source": "agent_dashboard_seed",
            "due_at": now + timedelta(minutes=20),
            "snoozed_until": None,
            "snooze_reason": None,
            "metadata_json": {"seeded": True},
            "updated_at": now,
        })

        _upsert(db, DBViewing, "agent-dashboard-sample-viewing-1", {
            "brokerage_id": brokerage_id,
            "conversation_id": conv.conversation_id,
            "listing_id": listing.listing_id,
            "buyer_phone": conv.buyer_phone,
            "agent_user_id": agent_user_id,
            "scheduled_for": now.replace(hour=18, minute=30, second=0, microsecond=0),
            "status": "proposed",
            "tenant_notice_required": False,
            "access_notes": "Confirm lobby access before sending calendar invite.",
            "post_viewing_notes": None,
            "metadata_json": {"seeded": True},
            "updated_at": now,
        })

        _upsert(db, DBDraftReply, "agent-dashboard-sample-reply-draft-1", {
            "brokerage_id": brokerage_id,
            "conversation_id": conv.conversation_id,
            "listing_id": listing.listing_id,
            "buyer_phone": conv.buyer_phone,
            "agent_user_id": agent_user_id,
            "intent": "viewing_slots",
            "draft_text": "Hi Ahmed, I can help with an evening viewing. I am checking access and will confirm the cleanest slot after 6.",
            "source": "template",
            "status": "draft",
            "metadata_json": {"seeded": True},
            "updated_at": now,
        })

        _upsert(db, DBAIDraft, "agent-dashboard-sample-ai-draft-1", {
            "brokerage_id": brokerage_id,
            "agent_user_id": agent_user_id,
            "conversation_id": conv.conversation_id,
            "listing_id": listing.listing_id,
            "buyer_phone": conv.buyer_phone,
            "draft_type": "whatsapp_reply",
            "title": "Viewing confirmation reply",
            "body": "Hi Ahmed, I have the context. I can call you now and confirm the best next step on the Downtown unit.",
            "status": "draft",
            "source": "agent_dashboard_seed",
            "confidence_score": 0.86,
            "metadata_json": {"seeded": True},
            "updated_at": now,
        })

        campaign = _upsert(db, DBCampaign, "agent-dashboard-sample-campaign-1", {
            "brokerage_id": brokerage_id,
            "owner_agent_id": agent_user_id,
            "name": "Oasis seller acquisition",
            "campaign_type": "owner_acquisition",
            "channel": "whatsapp",
            "status": "active",
            "audience": {"project": "The Oasis", "owners": 120},
            "offer": {"cta": "Upload your SPA"},
            "metrics": {"sent": 34, "replies": 5, "spa_uploads": 1},
            "starts_at": now - timedelta(days=2),
            "ends_at": None,
            "updated_at": now,
        })
        db.flush()

        _upsert(db, DBCampaignUpload, "agent-dashboard-sample-upload-1", {
            "campaign_id": campaign.campaign_id,
            "brokerage_id": brokerage_id,
            "uploaded_by": agent_user_id,
            "file_name": "oasis-owner-shortlist.csv",
            "file_url": None,
            "file_type": "text/csv",
            "row_count": 120,
            "status": "processed",
            "parsed_summary": {"owners": 120, "valid_phone_numbers": 92},
            "error": None,
            "processed_at": now - timedelta(days=2),
        })

        owner_lead = _upsert(db, DBOwnerLead, "agent-dashboard-sample-owner-lead-1", {
            "brokerage_id": brokerage_id,
            "campaign_id": campaign.campaign_id,
            "assigned_agent_id": agent_user_id,
            "owner_name": "Sara M.",
            "owner_phone": "+971551110000",
            "owner_email": None,
            "project": "The Oasis",
            "unit_number": "V-144",
            "property_type": "Villa",
            "estimated_value_aed": 8200000,
            "intent": "sell",
            "lead_source": "owner_acquisition_campaign",
            "stage": "new",
            "priority": "high",
            "last_contacted_at": None,
            "next_follow_up_at": now + timedelta(hours=2),
            "notes": "Asked for resale readiness context before uploading SPA.",
            "metadata_json": {"seeded": True},
            "updated_at": now,
        })
        db.flush()

        recipient = _upsert(db, DBCampaignRecipient, "agent-dashboard-sample-recipient-1", {
            "campaign_id": campaign.campaign_id,
            "brokerage_id": brokerage_id,
            "owner_lead_id": owner_lead.owner_lead_id,
            "recipient_key": f"{campaign.campaign_id}:+971551110000",
            "name": owner_lead.owner_name,
            "phone": owner_lead.owner_phone,
            "email": owner_lead.owner_email,
            "channel": "whatsapp",
            "status": "replied",
            "last_message_at": now - timedelta(hours=3),
            "last_response_at": now - timedelta(hours=2),
            "metadata_json": {"seeded": True},
            "updated_at": now,
        })
        db.flush()

        _upsert(db, DBOutreachDraft, "agent-dashboard-sample-outreach-draft-1", {
            "brokerage_id": brokerage_id,
            "campaign_id": campaign.campaign_id,
            "recipient_id": recipient.recipient_id,
            "owner_lead_id": owner_lead.owner_lead_id,
            "agent_user_id": agent_user_id,
            "channel": "whatsapp",
            "subject": None,
            "body": "Hi Sara, I noticed your Oasis villa may be approaching resale eligibility. Dalya can verify the SPA, NOC position, and likely buyer demand before you commit to listing.",
            "status": "draft",
            "source": "ai",
            "sent_at": None,
            "metadata_json": {"seeded": True},
            "updated_at": now,
        })

        page = _upsert(db, DBMarketingPage, "agent-dashboard-sample-page-1", {
            "brokerage_id": brokerage_id,
            "campaign_id": campaign.campaign_id,
            "slug": "oasis-resale-readiness",
            "title": "Oasis resale readiness",
            "page_type": "campaign_landing",
            "status": "published",
            "url": "/campaigns/oasis-resale-readiness",
            "content": {"cta": "Upload your SPA", "project": "The Oasis"},
            "metrics": {"views": 18, "whatsapp_clicks": 3},
            "published_at": now - timedelta(days=2),
            "updated_at": now,
        })
        db.flush()

        for idx, event_type in enumerate(["page_view", "page_view", "whatsapp_click"]):
            _upsert(db, DBMarketingEvent, f"agent-dashboard-sample-event-{idx + 1}", {
                "brokerage_id": brokerage_id,
                "page_id": page.page_id,
                "campaign_id": campaign.campaign_id,
                "owner_lead_id": owner_lead.owner_lead_id if event_type == "whatsapp_click" else None,
                "event_type": event_type,
                "visitor_id": f"sample-visitor-{idx + 1}",
                "source": "seed",
                "payload": {"seeded": True},
                "occurred_at": now - timedelta(hours=idx + 1),
            })

        safe_commit(db)
        print(
            "Agent dashboard v1 seed complete. "
            f"brokerage={brokerage_id} agent_user={agent_user_id}"
        )


if __name__ == "__main__":
    main()
