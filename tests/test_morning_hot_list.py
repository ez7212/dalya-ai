from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.core.hot_list import refresh_hotlist_with_run, refresh_morning_hot_list, score_conversation
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBBrokerage,
    DBBrokerageMember,
    DBConversation,
    DBConversationAccessGrant,
    DBDraftReply,
    DBEscalationThread,
    DBHotlistRefreshRun,
    DBLeadAction,
    DBLeadAssignment,
    DBLeadTask,
    DBListing,
    DBMessage,
    DBOfferRecord,
    DBViewing,
)


@pytest.fixture
def hot_list_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"hot-list-brokerage-{suffix}"
    owner_id = f"hot-owner-{suffix}"
    agent_id = f"hot-agent-{suffix}"
    listing_ids = [f"hot-listing-{suffix}-{idx}" for idx in range(3)]
    buyer_phones = [f"+97155500{idx}{suffix[:4]}" for idx in range(3)]
    now = datetime.utcnow().replace(microsecond=0)

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Hot List Brokerage",
            slug=f"hot-list-{suffix}",
            status="active",
            brokerage_ai_number="+971500001111",
            agents_ai_number="+971500001112",
        ))
        db.add_all([
            DBBrokerageMember(
                brokerage_id=brokerage_id,
                user_id=owner_id,
                email=f"{owner_id}@example.com",
                display_name="Owner",
                role="owner",
                status="active",
            ),
            DBBrokerageMember(
                brokerage_id=brokerage_id,
                user_id=agent_id,
                email=f"{agent_id}@example.com",
                display_name="Agent",
                role="agent",
                status="active",
            ),
        ])
        for idx, listing_id in enumerate(listing_ids):
            db.add(DBListing(
                listing_id=listing_id,
                brokerage_id=brokerage_id,
                assigned_agent_id=owner_id if idx != 2 else None,
                spa_data={
                    "project": f"Hot List Residence {idx + 1}",
                    "unit_number": f"{1100 + idx}",
                    "developer": "Emaar",
                    "property_type": "Apartment",
                    "bedrooms": 2 + idx,
                    "purchase_price_aed": 2_000_000 + idx * 500_000,
                },
                seller_asking_price=2_000_000 + idx * 500_000,
                negotiation_threshold_aed=1_900_000 + idx * 500_000,
                commission_rate=0.015,
                property_type="ready",
                additional_fees=[],
                seller_qa=[],
                media_urls=[],
                unit_profile={},
                unit_profile_history=[],
                processing_stages={},
            ))
        safe_commit(db)

        offer_conv = crud.get_or_create_conversation(db, buyer_phones[0], listing_ids[0])
        viewing_conv = crud.get_or_create_conversation(db, buyer_phones[1], listing_ids[1])
        stale_conv = crud.get_or_create_conversation(db, buyer_phones[2], listing_ids[2])

        offer_conv.buyer_name = "Sara"
        offer_conv.escalation_triggered = True
        offer_conv.escalation_reason = "offer:1950000"
        offer_conv.updated_at = now - timedelta(minutes=12)
        viewing_conv.buyer_name = "Mohammed"
        viewing_conv.detected_budget = 2_700_000
        viewing_conv.updated_at = now - timedelta(minutes=45)
        stale_conv.buyer_name = "Priya"
        stale_conv.detected_budget = 3_200_000
        stale_conv.updated_at = now - timedelta(days=2)
        safe_commit(db)

        messages = [
            DBMessage(
                conversation_id=offer_conv.conversation_id,
                role="user",
                content="I can offer AED 1.95M.",
                intent="offer_submission",
                timestamp=now - timedelta(minutes=12),
            ),
            DBMessage(
                conversation_id=viewing_conv.conversation_id,
                role="user",
                content="Can I view it this evening?",
                intent="viewing_request",
                timestamp=now - timedelta(minutes=45),
            ),
            DBMessage(
                conversation_id=stale_conv.conversation_id,
                role="user",
                content="Budget is around 3.2M, send me anything good in this area.",
                intent="general_inquiry",
                timestamp=now - timedelta(days=2, hours=1),
            ),
            DBMessage(
                conversation_id=stale_conv.conversation_id,
                role="assistant",
                content="Noted, I can help compare options.",
                intent="general_response",
                timestamp=now - timedelta(days=2),
            ),
        ]
        db.add_all(messages)
        safe_commit(db)

        yield {
            "brokerage_id": brokerage_id,
            "owner_id": owner_id,
            "agent_id": agent_id,
            "listing_ids": listing_ids,
            "offer_conversation_id": offer_conv.conversation_id,
            "viewing_conversation_id": viewing_conv.conversation_id,
            "stale_conversation_id": stale_conv.conversation_id,
            "now": now,
        }

    with SessionLocal() as db:
        conversation_ids = [
            hot_list_seed_id
            for hot_list_seed_id in [
                locals().get("offer_conv").conversation_id if locals().get("offer_conv") else None,
                locals().get("viewing_conv").conversation_id if locals().get("viewing_conv") else None,
                locals().get("stale_conv").conversation_id if locals().get("stale_conv") else None,
            ]
            if hot_list_seed_id
        ]
        db.query(DBLeadAction).filter(DBLeadAction.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBEscalationThread).filter(DBEscalationThread.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBOfferRecord).filter(DBOfferRecord.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBViewing).filter(DBViewing.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBHotlistRefreshRun).filter(DBHotlistRefreshRun.brokerage_id == brokerage_id).delete(synchronize_session=False)
        db.query(DBDraftReply).filter(DBDraftReply.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBLeadTask).filter(DBLeadTask.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBConversationAccessGrant).filter(DBConversationAccessGrant.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBMessage).filter(DBMessage.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBConversation).filter(DBConversation.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBListing).filter(DBListing.listing_id.in_(listing_ids)).delete(synchronize_session=False)
        db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == brokerage_id).delete(synchronize_session=False)
        db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == brokerage_id).delete(synchronize_session=False)
        safe_commit(db)


def test_hot_list_scoring_ranks_offer_then_viewing_then_stale_follow_up(hot_list_seed):
    seed = hot_list_seed
    with SessionLocal() as db:
        offer = db.get(DBConversation, seed["offer_conversation_id"])
        viewing = db.get(DBConversation, seed["viewing_conversation_id"])
        stale = db.get(DBConversation, seed["stale_conversation_id"])

        offer_score = score_conversation(db, offer, now=seed["now"])
        viewing_score = score_conversation(db, viewing, now=seed["now"])
        stale_score = score_conversation(db, stale, now=seed["now"])

        assert offer_score.signal == "firm_offer"
        assert offer_score.next_action == "review_offer"
        assert viewing_score.signal == "ready_to_view"
        assert viewing_score.next_action == "book_viewing"
        assert stale_score.stale is True
        assert stale_score.next_action == "follow_up"
        assert offer_score.urgency_score > viewing_score.urgency_score > stale_score.urgency_score


def test_refresh_persists_assignments_tasks_and_single_follow_up_draft(hot_list_seed):
    seed = hot_list_seed
    with SessionLocal() as db:
        first = refresh_morning_hot_list(
            db,
            brokerage_id=seed["brokerage_id"],
            user_id=seed["owner_id"],
            role="owner",
            now=seed["now"],
        )
        second = refresh_morning_hot_list(
            db,
            brokerage_id=seed["brokerage_id"],
            user_id=seed["owner_id"],
            role="owner",
            now=seed["now"],
        )

        assert [row.conversation_id for row in first][:2] == [
            seed["offer_conversation_id"],
            seed["viewing_conversation_id"],
        ]
        assert [row.conversation_id for row in second][:2] == [
            seed["offer_conversation_id"],
            seed["viewing_conversation_id"],
        ]

        tasks = (
            db.query(DBLeadTask)
            .filter(
                DBLeadTask.brokerage_id == seed["brokerage_id"],
                DBLeadTask.source == "morning_hot_list",
                DBLeadTask.status == "open",
            )
            .all()
        )
        assert len(tasks) == 3
        assert len({task.task_key for task in tasks}) == 3

        drafts = (
            db.query(DBDraftReply)
            .filter(
                DBDraftReply.conversation_id == seed["stale_conversation_id"],
                DBDraftReply.intent == "follow_up",
                DBDraftReply.status == "draft",
            )
            .all()
        )
        assert len(drafts) == 1
        assert "Hot List Residence 3" in drafts[0].draft_text
        assert drafts[0].source == "morning_hot_list"


def test_hot_list_refresh_run_records_status_and_dedupes_outputs(hot_list_seed):
    seed = hot_list_seed
    with SessionLocal() as db:
        first = refresh_hotlist_with_run(
            db,
            brokerage_id=seed["brokerage_id"],
            requested_by_user_id=seed["owner_id"],
            role="owner",
            trigger="manual",
            now=seed["now"],
        )
        second = refresh_hotlist_with_run(
            db,
            brokerage_id=seed["brokerage_id"],
            requested_by_user_id=seed["owner_id"],
            role="owner",
            trigger="manual",
            now=seed["now"] + timedelta(minutes=5),
        )

        assert first.status == "complete"
        assert second.status == "complete"
        assert first.assignment_count == 3
        assert second.assignment_count == 3

        tasks = (
            db.query(DBLeadTask)
            .filter(
                DBLeadTask.brokerage_id == seed["brokerage_id"],
                DBLeadTask.source == "morning_hot_list",
                DBLeadTask.status == "open",
            )
            .all()
        )
        assert len(tasks) == 3
        assert len({task.task_key for task in tasks}) == 3

        drafts = (
            db.query(DBDraftReply)
            .filter(
                DBDraftReply.brokerage_id == seed["brokerage_id"],
                DBDraftReply.source == "morning_hot_list",
                DBDraftReply.status == "draft",
            )
            .all()
        )
        assert len(drafts) == 1


def test_agent_hot_list_manual_refresh_api_returns_run_status(client, hot_list_seed):
    seed = hot_list_seed
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seed["owner_id"],
        email=f'{seed["owner_id"]}@example.com',
    )
    try:
        refresh = client.post("/api/v1/agent/hot-list/refresh")
        assert refresh.status_code == 200, refresh.text
        payload = refresh.json()
        assert payload["status"] == "complete"
        assert payload["trigger"] == "manual"
        assert payload["assignment_count"] == 3
        assert payload["task_count"] == 3
        assert payload["draft_count"] == 1

        dashboard = client.get("/api/v1/agent/dashboard")
        assert dashboard.status_code == 200, dashboard.text
        assert dashboard.json()["hot_list_refresh"]["status"] == "complete"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_agent_dashboard_refreshes_hot_list_and_respects_private_visibility(client, hot_list_seed):
    seed = hot_list_seed
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seed["agent_id"],
        email=f'{seed["agent_id"]}@example.com',
    )
    try:
        response = client.get("/api/v1/agent/dashboard")
        assert response.status_code == 200, response.text
        payload = response.json()
        visible_ids = {lead["conversation_id"] for lead in payload["hot_leads"]}
        assert seed["offer_conversation_id"] not in visible_ids
        assert seed["viewing_conversation_id"] not in visible_ids
        assert seed["stale_conversation_id"] not in visible_ids

        with SessionLocal() as db:
            db.add(DBConversationAccessGrant(
                brokerage_id=seed["brokerage_id"],
                conversation_id=seed["viewing_conversation_id"],
                agent_user_id=seed["agent_id"],
                granted_by_user_id=seed["owner_id"],
                access_level="viewer",
                reason="Share viewing lead",
                active=True,
            ))
            safe_commit(db)

        response = client.get("/api/v1/agent/dashboard")
        assert response.status_code == 200, response.text
        payload = response.json()
        visible_ids = {lead["conversation_id"] for lead in payload["hot_leads"]}
        assert seed["viewing_conversation_id"] in visible_ids
        assert seed["offer_conversation_id"] not in visible_ids
        assert any(task["conversation_id"] == seed["viewing_conversation_id"] for task in payload["tasks"])
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_agent_dashboard_performance_metrics_are_current_agent_scoped(client, hot_list_seed):
    seed = hot_list_seed
    now = seed["now"]
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seed["agent_id"],
        email=f'{seed["agent_id"]}@example.com',
    )
    try:
        with SessionLocal() as db:
            agent_conv = db.get(DBConversation, seed["viewing_conversation_id"])
            owner_conv = db.get(DBConversation, seed["offer_conversation_id"])
            agent_conv.assigned_agent_id = seed["agent_id"]
            owner_conv.assigned_agent_id = seed["owner_id"]
            db.add(DBMessage(
                conversation_id=agent_conv.conversation_id,
                role="user",
                content="Can you send the next step?",
                intent="follow_up",
                timestamp=now - timedelta(minutes=25),
            ))
            db.add(DBLeadAction(
                brokerage_id=seed["brokerage_id"],
                conversation_id=agent_conv.conversation_id,
                listing_id=agent_conv.listing_id,
                buyer_phone=agent_conv.buyer_phone,
                agent_user_id=seed["agent_id"],
                action_type="draft_reply_sent",
                outcome="sent",
                created_at=now - timedelta(minutes=5),
            ))
            db.add(DBLeadAction(
                brokerage_id=seed["brokerage_id"],
                conversation_id=owner_conv.conversation_id,
                listing_id=owner_conv.listing_id,
                buyer_phone=owner_conv.buyer_phone,
                agent_user_id=seed["owner_id"],
                action_type="draft_reply_sent",
                outcome="sent",
                created_at=now - timedelta(minutes=3),
            ))
            db.add(DBDraftReply(
                brokerage_id=seed["brokerage_id"],
                conversation_id=agent_conv.conversation_id,
                listing_id=agent_conv.listing_id,
                buyer_phone=agent_conv.buyer_phone,
                agent_user_id=seed["agent_id"],
                intent="follow_up",
                draft_text="Following up after the viewing.",
                source="test",
                status="sent",
                sent_at=now - timedelta(minutes=5),
            ))
            db.add(DBViewing(
                brokerage_id=seed["brokerage_id"],
                conversation_id=agent_conv.conversation_id,
                listing_id=agent_conv.listing_id,
                buyer_phone=agent_conv.buyer_phone,
                agent_user_id=seed["agent_id"],
                scheduled_for=now - timedelta(hours=2),
                status="completed",
                updated_at=now - timedelta(minutes=10),
            ))
            db.add(DBViewing(
                brokerage_id=seed["brokerage_id"],
                conversation_id=owner_conv.conversation_id,
                listing_id=owner_conv.listing_id,
                buyer_phone=owner_conv.buyer_phone,
                agent_user_id=seed["owner_id"],
                scheduled_for=now - timedelta(hours=1),
                status="completed",
                updated_at=now - timedelta(minutes=8),
            ))
            db.add(DBOfferRecord(
                brokerage_id=seed["brokerage_id"],
                conversation_id=agent_conv.conversation_id,
                listing_id=agent_conv.listing_id,
                buyer_phone=agent_conv.buyer_phone,
                buyer_name=agent_conv.buyer_name,
                offer_amount_aed=2_300_000,
                asking_price_aed=2_500_000,
                gap_pct=8.0,
                above_threshold=True,
                threshold_aed=2_200_000,
                escalated=True,
                created_at=now - timedelta(minutes=20),
            ))
            db.add(DBEscalationThread(
                brokerage_id=seed["brokerage_id"],
                conversation_id=agent_conv.conversation_id,
                listing_id=agent_conv.listing_id,
                buyer_phone=agent_conv.buyer_phone,
                agent_user_id=seed["agent_id"],
                category="offer",
                state="resolved",
                escalation_type="offer",
                opened_at=now - timedelta(minutes=30),
                last_buyer_message_at=now - timedelta(minutes=30),
                closed_at=now - timedelta(minutes=4),
            ))
            db.add(DBEscalationThread(
                brokerage_id=seed["brokerage_id"],
                conversation_id=owner_conv.conversation_id,
                listing_id=owner_conv.listing_id,
                buyer_phone=owner_conv.buyer_phone,
                agent_user_id=seed["owner_id"],
                category="offer",
                state="resolved",
                escalation_type="offer",
                opened_at=now - timedelta(minutes=30),
                last_buyer_message_at=now - timedelta(minutes=30),
                closed_at=now - timedelta(minutes=4),
            ))
            db.add(DBLeadTask(
                task_key=f"performance-overdue:{agent_conv.conversation_id}",
                brokerage_id=seed["brokerage_id"],
                conversation_id=agent_conv.conversation_id,
                listing_id=agent_conv.listing_id,
                buyer_phone=agent_conv.buyer_phone,
                assigned_agent_id=seed["agent_id"],
                task_type="whatsapp",
                title="Follow up",
                status="open",
                due_at=now - timedelta(hours=1),
            ))
            safe_commit(db)

        response = client.get("/api/v1/agent/dashboard")
        assert response.status_code == 200, response.text
        performance = response.json()["performance"]
        assert performance["scope"] == "current_agent"
        assert performance["agent_user_id"] == seed["agent_id"]
        metrics = performance["primary"]["metrics"]
        assert metrics["new_buyer_conversations"] == 1
        assert metrics["escalations_handled"] == 1
        assert metrics["follow_ups_sent"] == 1
        assert metrics["viewings_proposed"] == 1
        assert metrics["viewings_confirmed"] == 1
        assert metrics["viewings_completed"] == 1
        assert metrics["offers_detected"] == 1
        assert metrics["tasks_overdue"] == 1
        assert metrics["hot_leads_active"] >= 1
        assert metrics["avg_response_minutes"] == 20.0
        assert {window["key"] for window in performance["windows"]} == {"today", "7d", "30d"}
    finally:
        app.dependency_overrides.pop(get_current_user, None)
