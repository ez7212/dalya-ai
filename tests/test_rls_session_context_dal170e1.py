from __future__ import annotations

from contextlib import contextmanager
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.auth import CurrentUser, get_current_user
from app.core.brokerage_access import resolve_request_brokerage_context
from app.core.lead_ingest import ingest_lead_email
from app.db.session import (
    SessionLocal,
    clear_db_session_context,
    engine,
    safe_commit,
    set_db_session_context,
)
from app.main import app
from app.models.db_models import (
    DBAgentNotification,
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageBuyerProfile,
    DBBrokerageMember,
    DBBuyerProfileField,
    DBComplianceEvent,
    DBConversation,
    DBLeadAssignment,
    DBLeadAction,
    DBLeadTask,
    DBLeadIngestRecord,
    DBListing,
    DBMessage,
)
from scripts.rls_rehearsal_dal170e1 import (
    APPLY_SQL,
    E2_DIRECT_ROOT_TABLES,
    E3_NULLABLE_ROOT_TABLES,
    E3_SERVICE_ONLY_TABLES,
    ROLLBACK_SQL,
    RUNTIME_ROLE,
    _assert_rehearsal_mutation_allowed,
    apply_sql_text,
    main as rls_rehearsal_main,
    rollback_sql_text,
)


def _execute_statements(statements: list[str]) -> None:
    with engine.begin() as conn:
        for statement in statements:
            if statement.strip():
                conn.execute(text(statement))


@contextmanager
def _runtime_connection(
    *,
    user_id: str | None = None,
    brokerage_id: str | None = None,
    is_service: bool = False,
):
    with engine.connect() as conn:
        trans = conn.begin()
        conn.execute(text(f"set local role {RUNTIME_ROLE}"))
        if user_id is not None:
            conn.execute(
                text("select set_config('app.user_id', :value, true)"),
                {"value": user_id},
            )
        if brokerage_id is not None:
            conn.execute(
                text("select set_config('app.brokerage_id', :value, true)"),
                {"value": brokerage_id},
            )
        if is_service:
            conn.execute(
                text("select set_config('app.is_service', 'true', true)"),
            )
        try:
            yield conn
        finally:
            trans.rollback()


@contextmanager
def _as_user(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id,
        email=f"{user_id}@example.com",
    )
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def _e2_row_refs(seed: dict[str, object]) -> list[tuple[str, str, object, object]]:
    return [
        ("listing_documents", "document_id", seed["document_a"], seed["document_b"]),
        ("listing_facts", "fact_id", seed["fact_a"], seed["fact_b"]),
        ("listing_knowledge_summaries", "summary_id", seed["summary_a"], seed["summary_b"]),
        ("listing_logistics", "logistics_id", seed["logistics_a"], seed["logistics_b"]),
        ("tenant_consents", "consent_id", seed["consent_a"], seed["consent_b"]),
        ("listing_inquiries", "id", seed["inquiry_a"], seed["inquiry_b"]),
        ("offers", "offer_id", seed["offer_a"], seed["offer_b"]),
        ("draft_replies", "draft_id", seed["draft_reply_a"], seed["draft_reply_b"]),
        ("ai_drafts", "draft_id", seed["ai_draft_a"], seed["ai_draft_b"]),
        ("lead_ingests", "ingest_id", seed["lead_ingest_a"], seed["lead_ingest_b"]),
        ("lead_assignments", "assignment_id", seed["lead_assignment_a"], seed["lead_assignment_b"]),
        ("lead_tasks", "task_id", seed["lead_task_a"], seed["lead_task_b"]),
        ("lead_actions", "action_id", seed["lead_action_a"], seed["lead_action_b"]),
        ("viewings", "viewing_id", seed["viewing_a"], seed["viewing_b"]),
        ("tenant_viewing_confirmations", "confirmation_id", seed["tenant_confirmation_a"], seed["tenant_confirmation_b"]),
        ("viewing_feedback", "feedback_id", seed["viewing_feedback_a"], seed["viewing_feedback_b"]),
        ("media_assets", "media_asset_id", seed["media_asset_a"], seed["media_asset_b"]),
    ]


def _e3_parent_derived_row_refs(seed: dict[str, object]) -> list[tuple[str, str, object, object]]:
    return [
        ("escalation_threads", "thread_id", seed["thread_a"], seed["thread_b"]),
        ("messages", "id", seed["message_a"], seed["message_b"]),
        ("escalation_thread_questions", "question_id", seed["question_a"], seed["question_b"]),
        ("telegram_reply_routes", "id", seed["telegram_a"], seed["telegram_b"]),
    ]


def _e3_nullable_root_row_refs(seed: dict[str, object]) -> list[tuple[str, str, object, object, object]]:
    return [
        ("offer_records", "offer_id", seed["offer_record_a"], seed["offer_record_b"], seed["offer_record_null"]),
        ("suspicious_activity", "activity_id", seed["suspicious_a"], seed["suspicious_b"], seed["suspicious_null"]),
        ("inbound_provider_events", "event_id", seed["inbound_event_a"], seed["inbound_event_b"], seed["inbound_event_null"]),
    ]


def _e3_service_only_row_refs(seed: dict[str, object]) -> list[tuple[str, str, object, object]]:
    return [
        ("message_queue", "id", seed["message_queue_a"], seed["message_queue_b"]),
        ("buyer_profiles", "phone", seed["buyer_phone_a"], seed["buyer_phone_b"]),
    ]


def _seed_e2_rows(db, seed: dict[str, object]) -> dict[str, object]:
    prefix = seed["prefix"]
    rows = {
        "document_a": f"{prefix}-document-a",
        "document_b": f"{prefix}-document-b",
        "fact_a": f"{prefix}-fact-a",
        "fact_b": f"{prefix}-fact-b",
        "summary_a": f"{prefix}-summary-a",
        "summary_b": f"{prefix}-summary-b",
        "logistics_a": f"{prefix}-logistics-a",
        "logistics_b": f"{prefix}-logistics-b",
        "consent_a": f"{prefix}-consent-a",
        "consent_b": f"{prefix}-consent-b",
        "offer_a": f"{prefix}-offer-a",
        "offer_b": f"{prefix}-offer-b",
        "draft_reply_a": f"{prefix}-draft-reply-a",
        "draft_reply_b": f"{prefix}-draft-reply-b",
        "ai_draft_a": f"{prefix}-ai-draft-a",
        "ai_draft_b": f"{prefix}-ai-draft-b",
        "lead_ingest_a": f"{prefix}-lead-ingest-a",
        "lead_ingest_b": f"{prefix}-lead-ingest-b",
        "lead_assignment_a": f"{prefix}-lead-assignment-a",
        "lead_assignment_b": f"{prefix}-lead-assignment-b",
        "lead_task_a": f"{prefix}-lead-task-a",
        "lead_task_b": f"{prefix}-lead-task-b",
        "lead_action_a": f"{prefix}-lead-action-a",
        "lead_action_b": f"{prefix}-lead-action-b",
        "viewing_a": f"{prefix}-viewing-a",
        "viewing_b": f"{prefix}-viewing-b",
        "tenant_confirmation_a": f"{prefix}-tenant-confirmation-a",
        "tenant_confirmation_b": f"{prefix}-tenant-confirmation-b",
        "viewing_feedback_a": f"{prefix}-viewing-feedback-a",
        "viewing_feedback_b": f"{prefix}-viewing-feedback-b",
        "media_asset_a": f"{prefix}-media-asset-a",
        "media_asset_b": f"{prefix}-media-asset-b",
        "legacy_buyer_phone": f"+97159{int(seed['prefix'].rsplit('-', 1)[-1], 16) % 10000000:07d}",
        "message_a": f"{prefix}-message-a",
        "message_b": f"{prefix}-message-b",
        "thread_a": f"{prefix}-thread-a",
        "thread_b": f"{prefix}-thread-b",
        "question_a": f"{prefix}-question-a",
        "question_b": f"{prefix}-question-b",
        "offer_record_a": f"{prefix}-offer-record-a",
        "offer_record_b": f"{prefix}-offer-record-b",
        "offer_record_null": f"{prefix}-offer-record-null",
        "suspicious_a": f"{prefix}-suspicious-a",
        "suspicious_b": f"{prefix}-suspicious-b",
        "suspicious_null": f"{prefix}-suspicious-null",
        "inbound_event_a": f"{prefix}-inbound-event-a",
        "inbound_event_b": f"{prefix}-inbound-event-b",
        "inbound_event_null": f"{prefix}-inbound-event-null",
    }
    rows["buyer_phone_a"] = f"+97152{int(seed['prefix'].rsplit('-', 1)[-1], 16) % 10000000:07d}"
    rows["buyer_phone_b"] = f"+97153{int(seed['prefix'].rsplit('-', 1)[-1], 16) % 10000000:07d}"

    for side in ("a", "b"):
        brokerage_id = seed[f"brokerage_{side}"]
        listing_id = seed[f"listing_{side}"]
        conversation_id = seed[f"conversation_{side}"]
        buyer_phone = rows[f"buyer_phone_{side}"]
        document_id = rows[f"document_{side}"]
        viewing_id = rows[f"viewing_{side}"]

        db.execute(
            text(
                """
                insert into buyer_profiles (phone, brokerage_id, name)
                values (:phone, :brokerage_id, :name)
                on conflict (phone) do nothing
                """
            ),
            {"phone": buyer_phone, "brokerage_id": brokerage_id, "name": f"E2 Buyer {side}"},
        )
        db.execute(
            text(
                """
                insert into listing_documents
                    (document_id, brokerage_id, listing_id, document_type, label, status, metadata_json, created_at, updated_at)
                values (:document_id, :brokerage_id, :listing_id, 'spa', :label, 'processed', '{}'::jsonb, now(), now())
                """
            ),
            {"document_id": document_id, "brokerage_id": brokerage_id, "listing_id": listing_id, "label": f"E2 doc {side}"},
        )
        db.execute(
            text(
                """
                insert into listing_facts (
                    fact_id, brokerage_id, listing_id, document_id, fact_key, fact_group, value_text,
                    value_json, confidence, source, verified, buyer_safe, risk_flag, created_at, updated_at
                )
                values (
                    :fact_id, :brokerage_id, :listing_id, :document_id, :fact_key, 'property', :value_text,
                    '{}'::jsonb, 0.8, 'test', false, true, false, now(), now()
                )
                """
            ),
            {
                "fact_id": rows[f"fact_{side}"],
                "brokerage_id": brokerage_id,
                "listing_id": listing_id,
                "document_id": document_id,
                "fact_key": f"e2_fact_{side}_{prefix}",
                "value_text": f"value {side}",
            },
        )
        db.execute(
            text(
                """
                insert into listing_knowledge_summaries (
                    summary_id, brokerage_id, listing_id, buyer_safe_summary,
                    missing_information, risk_flags, status, metadata_json, created_at, updated_at
                )
                values (
                    :summary_id, :brokerage_id, :listing_id, :summary,
                    '[]'::jsonb, '[]'::jsonb, 'ready', '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "summary_id": rows[f"summary_{side}"],
                "brokerage_id": brokerage_id,
                "listing_id": listing_id,
                "summary": f"E2 summary {side}",
            },
        )
        db.execute(
            text(
                """
                insert into listing_logistics (
                    logistics_id, brokerage_id, listing_id, access, keys, tenant,
                    owner_permissions, source, metadata_json, created_at, updated_at
                )
                values (
                    :logistics_id, :brokerage_id, :listing_id, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                    '{}'::jsonb, 'agent_confirmed', '{}'::jsonb, now(), now()
                )
                """
            ),
            {"logistics_id": rows[f"logistics_{side}"], "brokerage_id": brokerage_id, "listing_id": listing_id},
        )
        db.execute(
            text(
                """
                insert into tenant_consents (
                    consent_id, brokerage_id, listing_id, tenant_contact_key, lawful_basis,
                    opt_in_status, metadata_json, created_at, updated_at
                )
                values (
                    :consent_id, :brokerage_id, :listing_id, :tenant_contact_key,
                    'listing_viewing_coordination', 'pending', '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "consent_id": rows[f"consent_{side}"],
                "brokerage_id": brokerage_id,
                "listing_id": listing_id,
                "tenant_contact_key": f"tenant-{side}-{prefix}",
            },
        )
        rows[f"inquiry_{side}"] = db.execute(
            text(
                """
                insert into listing_inquiries (brokerage_id, buyer_phone, listing_id, project, unit_number, price_aed)
                values (:brokerage_id, :buyer_phone, :listing_id, :project, :unit_number, :price_aed)
                returning id
                """
            ),
            {
                "brokerage_id": brokerage_id,
                "buyer_phone": buyer_phone,
                "listing_id": listing_id,
                "project": f"E2 Project {side}",
                "unit_number": side.upper(),
                "price_aed": 1_700_000,
            },
        ).scalar_one()
        db.execute(
            text(
                """
                insert into offers (
                    offer_id, brokerage_id, conversation_id, listing_id, buyer_phone, thread_key,
                    direction, status, financing_contingent, subject_to_viewing, source, metadata_json, created_at, updated_at
                )
                values (
                    :offer_id, :brokerage_id, :conversation_id, :listing_id, :buyer_phone, :thread_key,
                    'buyer_offer', 'draft_pending_confirm', false, false, 'agent_logged', '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "offer_id": rows[f"offer_{side}"],
                "brokerage_id": brokerage_id,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
                "buyer_phone": buyer_phone,
                "thread_key": f"{conversation_id}:{listing_id}",
            },
        )
        db.execute(
            text(
                """
                insert into draft_replies (
                    draft_id, brokerage_id, conversation_id, listing_id, intent, draft_text,
                    source, status, metadata_json, created_at, updated_at
                )
                values (
                    :draft_id, :brokerage_id, :conversation_id, :listing_id, 'follow_up', :draft_text,
                    'template', 'draft', '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "draft_id": rows[f"draft_reply_{side}"],
                "brokerage_id": brokerage_id,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
                "draft_text": f"E2 draft {side}",
            },
        )
        db.execute(
            text(
                """
                insert into ai_drafts (
                    draft_id, brokerage_id, conversation_id, listing_id, draft_type, body,
                    status, source, metadata_json, created_at, updated_at
                )
                values (
                    :draft_id, :brokerage_id, :conversation_id, :listing_id, 'whatsapp_reply', :body,
                    'draft', 'agent_dashboard', '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "draft_id": rows[f"ai_draft_{side}"],
                "brokerage_id": brokerage_id,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
                "body": f"E2 AI draft {side}",
            },
        )
        db.execute(
            text(
                """
                insert into lead_ingests (
                    ingest_id, brokerage_id, source, status, buyer_phone, listing_id, conversation_id,
                    first_touch_sent, raw_payload, created_at, updated_at
                )
                values (
                    :ingest_id, :brokerage_id, 'property_finder', 'ingested', :buyer_phone, :listing_id, :conversation_id,
                    false, '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "ingest_id": rows[f"lead_ingest_{side}"],
                "brokerage_id": brokerage_id,
                "buyer_phone": buyer_phone,
                "listing_id": listing_id,
                "conversation_id": conversation_id,
            },
        )
        db.execute(
            text(
                """
                insert into lead_assignments (
                    assignment_id, brokerage_id, conversation_id, listing_id, buyer_phone,
                    status, urgency_score, metadata_json, created_at, updated_at
                )
                values (
                    :assignment_id, :brokerage_id, :conversation_id, :listing_id, :buyer_phone,
                    'new', 0, '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "assignment_id": rows[f"lead_assignment_{side}"],
                "brokerage_id": brokerage_id,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
                "buyer_phone": buyer_phone,
            },
        )
        db.execute(
            text(
                """
                insert into lead_tasks (
                    task_id, brokerage_id, conversation_id, listing_id, buyer_phone, task_type, title,
                    status, priority, metadata_json, created_at, updated_at
                )
                values (
                    :task_id, :brokerage_id, :conversation_id, :listing_id, :buyer_phone, 'call', :title,
                    'open', 'normal', '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "task_id": rows[f"lead_task_{side}"],
                "brokerage_id": brokerage_id,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
                "buyer_phone": buyer_phone,
                "title": f"E2 task {side}",
            },
        )
        db.execute(
            text(
                """
                insert into lead_actions (
                    action_id, brokerage_id, conversation_id, listing_id, buyer_phone, action_type,
                    payload, created_at
                )
                values (
                    :action_id, :brokerage_id, :conversation_id, :listing_id, :buyer_phone, 'call_started',
                    '{}'::jsonb, now()
                )
                """
            ),
            {
                "action_id": rows[f"lead_action_{side}"],
                "brokerage_id": brokerage_id,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
                "buyer_phone": buyer_phone,
            },
        )
        db.execute(
            text(
                """
                insert into viewings (
                    viewing_id, brokerage_id, conversation_id, listing_id, buyer_phone,
                    status, tenant_notice_required, metadata_json, created_at, updated_at
                )
                values (
                    :viewing_id, :brokerage_id, :conversation_id, :listing_id, :buyer_phone,
                    'proposed', false, '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "viewing_id": viewing_id,
                "brokerage_id": brokerage_id,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
                "buyer_phone": buyer_phone,
            },
        )
        db.execute(
            text(
                """
                insert into tenant_viewing_confirmations
                    (confirmation_id, brokerage_id, viewing_id, listing_id, tenant_contact_key, status, metadata_json, created_at, updated_at)
                values (:confirmation_id, :brokerage_id, :viewing_id, :listing_id, :tenant_contact_key, 'pending', '{}'::jsonb, now(), now())
                """
            ),
            {
                "confirmation_id": rows[f"tenant_confirmation_{side}"],
                "brokerage_id": brokerage_id,
                "viewing_id": viewing_id,
                "listing_id": listing_id,
                "tenant_contact_key": f"viewing-tenant-{side}-{prefix}",
            },
        )
        db.execute(
            text(
                """
                insert into viewing_feedback
                    (
                        feedback_id, brokerage_id, viewing_id, conversation_id, listing_id,
                        participant_type, status, structured_json, source, metadata_json, created_at, updated_at
                    )
                values (
                    :feedback_id, :brokerage_id, :viewing_id, :conversation_id, :listing_id,
                    'buyer', 'requested', '{}'::jsonb, 'post_viewing_capture', '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "feedback_id": rows[f"viewing_feedback_{side}"],
                "brokerage_id": brokerage_id,
                "viewing_id": viewing_id,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
            },
        )
        db.execute(
            text(
                """
                insert into media_assets
                    (media_asset_id, brokerage_id, conversation_id, listing_id, mime_type, size_bytes, storage_ref, source, metadata_json, created_at)
                values (:media_asset_id, :brokerage_id, :conversation_id, :listing_id, 'image/jpeg', 1, :storage_ref, 'listing_asset', '{}'::jsonb, now())
                """
            ),
            {
                "media_asset_id": rows[f"media_asset_{side}"],
                "brokerage_id": brokerage_id,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
                "storage_ref": f"{brokerage_id}/e2/{side}.jpg",
            },
        )
        rows[f"message_{side}"] = db.execute(
            text(
                """
                insert into messages (conversation_id, role, content, intent, metadata_json, timestamp)
                values (:conversation_id, 'user', :content, 'general', '{}'::jsonb, now())
                returning id
                """
            ),
            {"conversation_id": conversation_id, "content": f"E3 message {side}"},
        ).scalar_one()
        db.execute(
            text(
                """
                insert into escalation_threads (
                    thread_id, brokerage_id, conversation_id, listing_id, buyer_phone, category,
                    state, escalation_type, opened_at, last_buyer_message_at, question_count, metadata_json,
                    created_at, updated_at
                )
                values (
                    :thread_id, :brokerage_id, :conversation_id, :listing_id, :buyer_phone, 'pricing',
                    'open', 'question', now(), now(), 1, '{}'::jsonb, now(), now()
                )
                """
            ),
            {
                "thread_id": rows[f"thread_{side}"],
                "brokerage_id": brokerage_id,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
                "buyer_phone": buyer_phone,
            },
        )
        db.execute(
            text(
                """
                insert into escalation_thread_questions (
                    question_id, thread_id, buyer_message_id, question_text, category, sort_order,
                    metadata_json, added_at
                )
                values (
                    :question_id, :thread_id, :buyer_message_id, :question_text, 'pricing', 1,
                    '{}'::jsonb, now()
                )
                """
            ),
            {
                "question_id": rows[f"question_{side}"],
                "thread_id": rows[f"thread_{side}"],
                "buyer_message_id": rows[f"message_{side}"],
                "question_text": f"E3 question {side}",
            },
        )
        rows[f"telegram_{side}"] = db.execute(
            text(
                """
                insert into telegram_reply_routes (
                    telegram_message_id, buyer_phone, conversation_id, listing_id, buyer_name, alert_questions, created_at
                )
                values (
                    :telegram_message_id, :buyer_phone, :conversation_id, :listing_id, :buyer_name, :alert_questions, now()
                )
                returning id
                """
            ),
            {
                "telegram_message_id": int(prefix.rsplit("-", 1)[-1], 16) % 1_000_000_000 + (1 if side == "a" else 2),
                "buyer_phone": buyer_phone,
                "conversation_id": conversation_id,
                "listing_id": listing_id,
                "buyer_name": f"E3 Buyer {side}",
                "alert_questions": f"E3 route {side}",
            },
        ).scalar_one()
        rows[f"message_queue_{side}"] = db.execute(
            text(
                """
                insert into message_queue (
                    from_number, to_number, body, message_sid, listing_id,
                    media_urls, media_content_types, metadata_json, status, received_at
                )
                values (
                    :from_number, :to_number, :body, :message_sid, :listing_id,
                    '[]'::jsonb, '[]'::jsonb, :metadata_json, 'pending', now()
                )
                returning id
                """
            ),
            {
                "from_number": buyer_phone,
                "to_number": f"+9715502{int(prefix.rsplit('-', 1)[-1], 16) % 10000:04d}",
                "body": f"E3 queue {side}",
                "message_sid": f"{prefix}-queue-{side}",
                "listing_id": listing_id,
                "metadata_json": f'{{"brokerage_id": "{brokerage_id}"}}',
            },
        ).scalar_one()
        db.execute(
            text(
                """
                insert into offer_records (
                    offer_id, brokerage_id, listing_id, conversation_id, buyer_phone, buyer_name,
                    offer_amount_aed, asking_price_aed, gap_pct, above_threshold, escalated, created_at
                )
                values (
                    :offer_id, :brokerage_id, :listing_id, :conversation_id, :buyer_phone, :buyer_name,
                    1500000, 1700000, 11.76, false, false, now()
                )
                """
            ),
            {
                "offer_id": rows[f"offer_record_{side}"],
                "brokerage_id": brokerage_id,
                "listing_id": listing_id,
                "conversation_id": conversation_id,
                "buyer_phone": buyer_phone,
                "buyer_name": f"E3 Buyer {side}",
            },
        )
        db.execute(
            text(
                """
                insert into suspicious_activity (
                    activity_id, brokerage_id, listing_id, conversation_id, buyer_phone, buyer_name,
                    category, trigger_message, created_at
                )
                values (
                    :activity_id, :brokerage_id, :listing_id, :conversation_id, :buyer_phone, :buyer_name,
                    'bypass_attempt', :trigger_message, now()
                )
                """
            ),
            {
                "activity_id": rows[f"suspicious_{side}"],
                "brokerage_id": brokerage_id,
                "listing_id": listing_id,
                "conversation_id": conversation_id,
                "buyer_phone": buyer_phone,
                "buyer_name": f"E3 Buyer {side}",
                "trigger_message": f"E3 suspicious {side}",
            },
        )
        db.execute(
            text(
                """
                insert into inbound_provider_events (
                    event_id, provider, endpoint, provider_event_id, payload_fingerprint,
                    brokerage_id, status, replay_count, received_at
                )
                values (
                    :event_id, 'twilio', :endpoint, :provider_event_id, :payload_fingerprint,
                    :brokerage_id, 'processed', 0, now()
                )
                """
            ),
            {
                "event_id": rows[f"inbound_event_{side}"],
                "endpoint": f"e3-{side}-{prefix}",
                "provider_event_id": f"{prefix}-provider-{side}",
                "payload_fingerprint": f"{prefix}-fingerprint-{side}",
                "brokerage_id": brokerage_id,
            },
        )

    db.execute(
        text(
            """
            insert into buyer_profiles (phone, name)
            values (:phone, 'Legacy Null Tenant')
            on conflict (phone) do nothing
            """
        ),
        {"phone": rows["legacy_buyer_phone"]},
    )
    db.execute(
        text(
            """
            insert into offer_records (
                offer_id, brokerage_id, listing_id, conversation_id, buyer_phone, buyer_name,
                offer_amount_aed, asking_price_aed, gap_pct, above_threshold, escalated, created_at
            )
            values (
                :offer_id, null, :listing_id, :conversation_id, :buyer_phone, 'Legacy Null Offer',
                1, 2, 50, false, false, now()
            )
            """
        ),
        {
            "offer_id": rows["offer_record_null"],
            "listing_id": seed["listing_a"],
            "conversation_id": seed["conversation_a"],
            "buyer_phone": rows["legacy_buyer_phone"],
        },
    )
    db.execute(
        text(
            """
            insert into suspicious_activity (
                activity_id, brokerage_id, listing_id, conversation_id, buyer_phone,
                category, trigger_message, created_at
            )
            values (
                :activity_id, null, :listing_id, :conversation_id, :buyer_phone,
                'bypass_attempt', 'Legacy null suspicious', now()
            )
            """
        ),
        {
            "activity_id": rows["suspicious_null"],
            "listing_id": seed["listing_a"],
            "conversation_id": seed["conversation_a"],
            "buyer_phone": rows["legacy_buyer_phone"],
        },
    )
    db.execute(
        text(
            """
            insert into inbound_provider_events (
                event_id, provider, endpoint, provider_event_id, payload_fingerprint,
                brokerage_id, status, replay_count, received_at
            )
            values (
                :event_id, 'twilio', :endpoint, :provider_event_id, :payload_fingerprint,
                null, 'processing', 0, now()
            )
            """
        ),
        {
            "event_id": rows["inbound_event_null"],
            "endpoint": f"e3-null-{prefix}",
            "provider_event_id": f"{prefix}-provider-null",
            "payload_fingerprint": f"{prefix}-fingerprint-null",
        },
    )
    rows["legacy_null_inquiry"] = db.execute(
        text(
            """
            insert into listing_inquiries (brokerage_id, buyer_phone, listing_id, project, unit_number, price_aed)
            values (null, :buyer_phone, :listing_id, 'Legacy Null Project', 'N', 1)
            returning id
            """
        ),
        {"buyer_phone": rows["legacy_buyer_phone"], "listing_id": seed["listing_a"]},
    ).scalar_one()
    return rows


def _set_rehearsal_env(monkeypatch, *, dalya_env: str | None = "test", database_url: str | None = None) -> None:
    monkeypatch.setenv("DALYA_ALLOW_RLS_REHEARSAL_MUTATION", "1")
    monkeypatch.setenv("PROD_DB_HOST", "prod-db.example.com")
    if dalya_env is None:
        monkeypatch.delenv("DALYA_ENV", raising=False)
    else:
        monkeypatch.setenv("DALYA_ENV", dalya_env)
    if database_url is None:
        database_url = "postgresql://dalya_test_user:secret@test-db.local/dalya_test"
    monkeypatch.setenv("DATABASE_URL", database_url)


@pytest.mark.parametrize("dalya_env", ["production", "prod", "staging", "stage", "preview", "live", "qa", None])
def test_rehearsal_mutation_refuses_live_missing_or_unknown_env(monkeypatch, dalya_env):
    _set_rehearsal_env(monkeypatch, dalya_env=dalya_env)

    with pytest.raises(SystemExit):
        _assert_rehearsal_mutation_allowed(allow_rehearsal_mutation=True)


def test_rehearsal_mutation_requires_explicit_approval(monkeypatch):
    _set_rehearsal_env(monkeypatch)
    monkeypatch.delenv("DALYA_ALLOW_RLS_REHEARSAL_MUTATION", raising=False)

    with pytest.raises(SystemExit):
        _assert_rehearsal_mutation_allowed()


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://dalya_test_user:secret@prod-db.example.com/dalya_test",
        "postgresql://dalya_test_user:secret@rehearsal-prod.example.com/dalya_test",
        "postgresql://dalya_test_user:secret@test-db.local/dalya_staging",
        "postgresql://prod_user:secret@test-db.local/dalya_test",
    ],
)
def test_rehearsal_mutation_refuses_production_like_database_identity(monkeypatch, database_url):
    _set_rehearsal_env(monkeypatch, database_url=database_url)

    with pytest.raises(SystemExit):
        _assert_rehearsal_mutation_allowed(allow_rehearsal_mutation=True)


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "not-a-url",
        "postgresql:///dalya_test",
    ],
)
def test_rehearsal_mutation_refuses_missing_or_ambiguous_database_identity(monkeypatch, database_url):
    _set_rehearsal_env(monkeypatch, database_url=database_url)

    with pytest.raises(SystemExit):
        _assert_rehearsal_mutation_allowed(allow_rehearsal_mutation=True)


def test_rehearsal_dry_run_sql_is_available_without_mutation_env(monkeypatch):
    monkeypatch.delenv("DALYA_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DALYA_ALLOW_RLS_REHEARSAL_MUTATION", raising=False)

    assert "create policy dal170e1_listings_tenant" in apply_sql_text()
    assert "drop policy if exists dal170e1_listings_tenant" in rollback_sql_text()


@pytest.mark.parametrize("mode", ["--apply", "--rollback"])
def test_rehearsal_apply_and_rollback_cli_are_gated(monkeypatch, mode):
    _set_rehearsal_env(monkeypatch)
    monkeypatch.delenv("DALYA_ALLOW_RLS_REHEARSAL_MUTATION", raising=False)
    monkeypatch.setattr("sys.argv", ["rls_rehearsal_dal170e1.py", mode])

    with pytest.raises(SystemExit):
        rls_rehearsal_main()


@pytest.fixture(scope="module")
def rls_policies():
    _execute_statements(ROLLBACK_SQL)
    _execute_statements(APPLY_SQL)
    yield
    _execute_statements(ROLLBACK_SQL)


@pytest.fixture
def rls_seed(rls_policies):
    suffix = uuid.uuid4().hex[:8]
    prefix = f"dal170e1-{suffix}"
    brokerage_a = f"{prefix}-a"
    brokerage_b = f"{prefix}-b"
    multi_user = f"{prefix}-multi"
    single_user = f"{prefix}-single"
    listing_a = f"{prefix}-listing-a"
    listing_b = f"{prefix}-listing-b"
    conversation_a = f"{prefix}-conversation-a"
    conversation_b = f"{prefix}-conversation-b"
    profile_a = f"{prefix}-profile-a"
    profile_b = f"{prefix}-profile-b"
    portal_phone = f"+97158{int(suffix, 16) % 10000000:07d}"
    source_url = f"https://www.propertyfinder.ae/en/plp/buy/villa-for-sale-dal170e1-{suffix}"

    with SessionLocal() as db:
        db.add_all(
            [
                DBBrokerage(
                    brokerage_id=brokerage_a,
                    name="DAL-170E1 Brokerage A",
                    slug=brokerage_a,
                    status="active",
                    brokerage_ai_number=f"+9715201{int(suffix, 16) % 10000:04d}",
                    agents_ai_number=f"+9715301{int(suffix, 16) % 10000:04d}",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerage(
                    brokerage_id=brokerage_b,
                    name="DAL-170E1 Brokerage B",
                    slug=brokerage_b,
                    status="active",
                    brokerage_ai_number=f"+9715401{int(suffix, 16) % 10000:04d}",
                    agents_ai_number=f"+9715501{int(suffix, 16) % 10000:04d}",
                    settings={"legacy_telegram_alerts": False},
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_a,
                    user_id=multi_user,
                    role="agent",
                    status="active",
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_b,
                    user_id=multi_user,
                    role="team_lead",
                    status="active",
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_a,
                    user_id=single_user,
                    role="agent",
                    status="active",
                ),
                DBAgentProfile(
                    brokerage_id=brokerage_a,
                    user_id=single_user,
                    full_name="DAL-170E1 Single",
                    display_name="DAL-170E1 Single",
                    whatsapp_phone=f"+9715601{int(suffix, 16) % 10000:04d}",
                    rera_broker_card_number=f"DAL170E1-S-{suffix}",
                    onboarding_status="active",
                ),
                DBAgentProfile(
                    brokerage_id=brokerage_b,
                    user_id=multi_user,
                    full_name="DAL-170E1 Multi",
                    display_name="DAL-170E1 Multi",
                    whatsapp_phone=f"+9715602{int(suffix, 16) % 10000:04d}",
                    rera_broker_card_number=f"DAL170E1-M-{suffix}",
                    onboarding_status="active",
                ),
                DBListing(
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    spa_data={"project": "DAL-170E1 A", "unit_number": "A"},
                    seller_asking_price=1_700_001,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=source_url,
                ),
                DBListing(
                    listing_id=listing_b,
                    brokerage_id=brokerage_b,
                    spa_data={"project": "DAL-170E1 B", "unit_number": "B"},
                    seller_asking_price=1_700_002,
                    commission_rate=0.02,
                    property_type="ready",
                    source_url=f"https://example.test/{listing_b}",
                ),
                DBConversation(
                    conversation_id=conversation_a,
                    listing_id=listing_a,
                    brokerage_id=brokerage_a,
                    buyer_phone=f"+97150{int(suffix, 16) % 10000000:07d}",
                    buyer_name="Buyer A",
                ),
                DBConversation(
                    conversation_id=conversation_b,
                    listing_id=listing_b,
                    brokerage_id=brokerage_b,
                    buyer_phone=f"+97151{int(suffix, 16) % 10000000:07d}",
                    buyer_name="Buyer B",
                ),
                DBBrokerageBuyerProfile(
                    profile_id=profile_a,
                    brokerage_id=brokerage_a,
                    buyer_phone=f"+97152{int(suffix, 16) % 10000000:07d}",
                    name="Profile A",
                    source="test",
                ),
                DBBrokerageBuyerProfile(
                    profile_id=profile_b,
                    brokerage_id=brokerage_b,
                    buyer_phone=f"+97153{int(suffix, 16) % 10000000:07d}",
                    name="Profile B",
                    source="test",
                ),
                DBBuyerProfileField(
                    profile_id=profile_a,
                    brokerage_id=brokerage_a,
                    field="timeline",
                    value={"value": "now"},
                    provenance="agent_confirmed",
                ),
                DBBuyerProfileField(
                    profile_id=profile_b,
                    brokerage_id=brokerage_b,
                    field="timeline",
                    value={"value": "later"},
                    provenance="agent_confirmed",
                ),
            ]
        )
        safe_commit(db)

    with SessionLocal() as db:
        e2_rows = _seed_e2_rows(
            db,
            {
                "prefix": prefix,
                "brokerage_a": brokerage_a,
                "brokerage_b": brokerage_b,
                "listing_a": listing_a,
                "listing_b": listing_b,
                "conversation_a": conversation_a,
                "conversation_b": conversation_b,
            },
        )
        safe_commit(db)

    seed = {
        "prefix": prefix,
        "brokerage_a": brokerage_a,
        "brokerage_b": brokerage_b,
        "multi_user": multi_user,
        "single_user": single_user,
        "listing_a": listing_a,
        "listing_b": listing_b,
        "conversation_a": conversation_a,
        "conversation_b": conversation_b,
        "profile_a": profile_a,
        "profile_b": profile_b,
        "portal_phone": portal_phone,
        "source_url": source_url,
    }
    seed.update(e2_rows)
    yield seed

    with SessionLocal() as db:
        conversation_ids = [
            row[0]
            for row in db.query(DBConversation.conversation_id)
            .filter(DBConversation.brokerage_id.in_([brokerage_a, brokerage_b]))
            .all()
        ]
        db.execute(text("delete from media_assets where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from viewing_feedback where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from tenant_viewing_confirmations where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from viewings where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from ai_drafts where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from draft_replies where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from offers where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from listing_inquiries where brokerage_id in (:a, :b) or id = :legacy_id"), {"a": brokerage_a, "b": brokerage_b, "legacy_id": e2_rows["legacy_null_inquiry"]})
        db.execute(text("delete from tenant_consents where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from listing_logistics where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from listing_facts where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from listing_knowledge_summaries where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(text("delete from listing_documents where brokerage_id in (:a, :b)"), {"a": brokerage_a, "b": brokerage_b})
        db.execute(
            text(
                """
                delete from inbound_provider_events
                where brokerage_id in (:a, :b)
                   or event_id in (:event_a, :event_b, :event_null)
                """
            ),
            {
                "a": brokerage_a,
                "b": brokerage_b,
                "event_a": e2_rows["inbound_event_a"],
                "event_b": e2_rows["inbound_event_b"],
                "event_null": e2_rows["inbound_event_null"],
            },
        )
        db.execute(
            text(
                """
                delete from message_queue
                where id in (:queue_a, :queue_b)
                   or metadata_json ->> 'brokerage_id' in (:a, :b)
                """
            ),
            {
                "queue_a": e2_rows["message_queue_a"],
                "queue_b": e2_rows["message_queue_b"],
                "a": brokerage_a,
                "b": brokerage_b,
            },
        )
        db.execute(
            text(
                """
                delete from telegram_reply_routes
                where id in (:telegram_a, :telegram_b)
                   or conversation_id in (:conversation_a, :conversation_b)
                """
            ),
            {
                "telegram_a": e2_rows["telegram_a"],
                "telegram_b": e2_rows["telegram_b"],
                "conversation_a": conversation_a,
                "conversation_b": conversation_b,
            },
        )
        db.execute(
            text("delete from escalation_thread_questions where thread_id in (:thread_a, :thread_b)"),
            {"thread_a": e2_rows["thread_a"], "thread_b": e2_rows["thread_b"]},
        )
        db.execute(
            text("delete from escalation_threads where brokerage_id in (:a, :b)"),
            {"a": brokerage_a, "b": brokerage_b},
        )
        db.execute(
            text(
                """
                delete from suspicious_activity
                where brokerage_id in (:a, :b)
                   or activity_id in (:suspicious_a, :suspicious_b, :suspicious_null)
                """
            ),
            {
                "a": brokerage_a,
                "b": brokerage_b,
                "suspicious_a": e2_rows["suspicious_a"],
                "suspicious_b": e2_rows["suspicious_b"],
                "suspicious_null": e2_rows["suspicious_null"],
            },
        )
        db.execute(
            text(
                """
                delete from offer_records
                where brokerage_id in (:a, :b)
                   or offer_id in (:offer_a, :offer_b, :offer_null)
                """
            ),
            {
                "a": brokerage_a,
                "b": brokerage_b,
                "offer_a": e2_rows["offer_record_a"],
                "offer_b": e2_rows["offer_record_b"],
                "offer_null": e2_rows["offer_record_null"],
            },
        )
        db.query(DBAgentNotification).filter(DBAgentNotification.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBLeadTask).filter(DBLeadTask.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBLeadAction).filter(DBLeadAction.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBLeadAssignment).filter(DBLeadAssignment.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        if conversation_ids:
            db.query(DBMessage).filter(DBMessage.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
        db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBLeadIngestRecord).filter(DBLeadIngestRecord.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBBuyerProfileField).filter(DBBuyerProfileField.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBBrokerageBuyerProfile).filter(DBBrokerageBuyerProfile.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBConversation).filter(DBConversation.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBListing).filter(DBListing.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.execute(
            text("delete from buyer_profiles where phone in (:buyer_a, :buyer_b, :legacy)"),
            {
                "buyer_a": e2_rows["buyer_phone_a"],
                "buyer_b": e2_rows["buyer_phone_b"],
                "legacy": e2_rows["legacy_buyer_phone"],
            },
        )
        db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([brokerage_a, brokerage_b])).delete(synchronize_session=False)
        safe_commit(db)


def test_no_brokerage_context_hides_protected_tenant_rows(rls_seed):
    with _runtime_connection() as conn:
        listing_ids = conn.execute(
            text("select listing_id from listings where listing_id in (:listing_a, :listing_b)"),
            {"listing_a": rls_seed["listing_a"], "listing_b": rls_seed["listing_b"]},
        ).fetchall()
    assert listing_ids == []


def test_brokerage_context_cannot_read_other_brokerage_rows(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        listing_ids = {
            row[0]
            for row in conn.execute(
                text("select listing_id from listings where listing_id in (:listing_a, :listing_b)"),
                {"listing_a": rls_seed["listing_a"], "listing_b": rls_seed["listing_b"]},
            ).fetchall()
        }
        profile_ids = {
            row[0]
            for row in conn.execute(
                text("select profile_id from brokerage_buyer_profiles where profile_id in (:profile_a, :profile_b)"),
                {"profile_a": rls_seed["profile_a"], "profile_b": rls_seed["profile_b"]},
            ).fetchall()
        }

    assert listing_ids == {rls_seed["listing_a"]}
    assert profile_ids == {rls_seed["profile_a"]}


def test_e2_policy_table_list_is_complete():
    assert set(E2_DIRECT_ROOT_TABLES) == {
        "listing_documents",
        "listing_facts",
        "listing_knowledge_summaries",
        "listing_logistics",
        "tenant_consents",
        "listing_inquiries",
        "offers",
        "draft_replies",
        "ai_drafts",
        "lead_ingests",
        "lead_assignments",
        "lead_tasks",
        "lead_actions",
        "viewings",
        "tenant_viewing_confirmations",
        "viewing_feedback",
        "media_assets",
    }


def test_e2_direct_root_tables_hide_rows_without_brokerage_context(rls_seed):
    with _runtime_connection() as conn:
        for table, key_column, key_a, key_b in _e2_row_refs(rls_seed):
            rows = conn.execute(
                text(f"select {key_column} from {table} where {key_column} in (:key_a, :key_b)"),
                {"key_a": key_a, "key_b": key_b},
            ).fetchall()
            assert rows == [], table


def test_e2_direct_root_tables_cannot_read_other_brokerage_rows(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        for table, key_column, key_a, key_b in _e2_row_refs(rls_seed):
            rows = {
                row[0]
                for row in conn.execute(
                    text(f"select {key_column} from {table} where {key_column} in (:key_a, :key_b)"),
                    {"key_a": key_a, "key_b": key_b},
                ).fetchall()
            }
            assert rows == {key_a}, table


def test_e2_listing_inquiries_hide_null_brokerage_legacy_rows(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        rows = conn.execute(
            text("select id from listing_inquiries where id = :legacy_id"),
            {"legacy_id": rls_seed["legacy_null_inquiry"]},
        ).fetchall()

    assert rows == []


def test_e2_direct_root_table_updates_with_mismatched_brokerage_fail(rls_seed):
    for table, key_column, key_a, _key_b in _e2_row_refs(rls_seed):
        with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
            with pytest.raises(DBAPIError):
                conn.execute(
                    text(f"update {table} set brokerage_id = :brokerage_b where {key_column} = :key_a"),
                    {"brokerage_b": rls_seed["brokerage_b"], "key_a": key_a},
                )


def test_e2_direct_root_insert_with_mismatched_brokerage_fails(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        with pytest.raises(DBAPIError):
            conn.execute(
                text(
                    """
                    insert into media_assets
                        (media_asset_id, brokerage_id, listing_id, mime_type, size_bytes, storage_ref)
                    values (:media_asset_id, :brokerage_b, :listing_a, 'image/jpeg', 1, 'bad/e2.jpg')
                    """
                ),
                {
                    "media_asset_id": f"{rls_seed['prefix']}-bad-media",
                    "brokerage_b": rls_seed["brokerage_b"],
                    "listing_a": rls_seed["listing_a"],
                },
            )


def test_e3_policy_table_groups_are_explicit():
    assert E3_NULLABLE_ROOT_TABLES == (
        "offer_records",
        "suspicious_activity",
        "inbound_provider_events",
    )
    assert E3_SERVICE_ONLY_TABLES == (
        "message_queue",
        "buyer_profiles",
    )


def test_e3_parent_derived_tables_hide_rows_without_context(rls_seed):
    with _runtime_connection() as conn:
        for table, key_column, key_a, key_b in _e3_parent_derived_row_refs(rls_seed):
            rows = conn.execute(
                text(f"select {key_column} from {table} where {key_column} in (:key_a, :key_b)"),
                {"key_a": key_a, "key_b": key_b},
            ).fetchall()
            assert rows == [], table


def test_e3_parent_derived_tables_cannot_read_other_brokerage_rows(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        for table, key_column, key_a, key_b in _e3_parent_derived_row_refs(rls_seed):
            rows = {
                row[0]
                for row in conn.execute(
                    text(f"select {key_column} from {table} where {key_column} in (:key_a, :key_b)"),
                    {"key_a": key_a, "key_b": key_b},
                ).fetchall()
            }
            assert rows == {key_a}, table


def test_e3_nullable_root_tables_hide_null_and_other_brokerage_rows(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        for table, key_column, key_a, key_b, key_null in _e3_nullable_root_row_refs(rls_seed):
            rows = {
                row[0]
                for row in conn.execute(
                    text(f"select {key_column} from {table} where {key_column} in (:key_a, :key_b, :key_null)"),
                    {"key_a": key_a, "key_b": key_b, "key_null": key_null},
                ).fetchall()
            }
            assert rows == {key_a}, table


def test_e3_service_only_tables_are_hidden_from_normal_tenant_context(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        for table, key_column, key_a, key_b in _e3_service_only_row_refs(rls_seed):
            rows = conn.execute(
                text(f"select {key_column} from {table} where {key_column} in (:key_a, :key_b)"),
                {"key_a": key_a, "key_b": key_b},
            ).fetchall()
            assert rows == [], table


def test_e3_service_context_can_access_service_only_rows(rls_seed):
    with _runtime_connection(is_service=True) as conn:
        for table, key_column, key_a, key_b in _e3_service_only_row_refs(rls_seed):
            rows = {
                row[0]
                for row in conn.execute(
                    text(f"select {key_column} from {table} where {key_column} in (:key_a, :key_b)"),
                    {"key_a": key_a, "key_b": key_b},
                ).fetchall()
            }
            assert rows == {key_a, key_b}, table


def test_e3_nullable_root_null_rows_are_service_only(rls_seed):
    with _runtime_connection(is_service=True) as conn:
        for table, key_column, _key_a, _key_b, key_null in _e3_nullable_root_row_refs(rls_seed):
            rows = conn.execute(
                text(f"select {key_column} from {table} where {key_column} = :key_null"),
                {"key_null": key_null},
            ).fetchall()
            assert rows == [(key_null,)], table


def test_e3_parent_derived_message_update_to_other_brokerage_fails(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        with pytest.raises(DBAPIError):
            conn.execute(
                text("update messages set conversation_id = :conversation_b where id = :message_a"),
                {
                    "conversation_b": rls_seed["conversation_b"],
                    "message_a": rls_seed["message_a"],
                },
            )


def test_e3_parent_derived_telegram_route_update_to_mismatched_parent_fails(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        with pytest.raises(DBAPIError):
            conn.execute(
                text("update telegram_reply_routes set listing_id = :listing_b where id = :telegram_a"),
                {
                    "listing_b": rls_seed["listing_b"],
                    "telegram_a": rls_seed["telegram_a"],
                },
            )


def test_mismatched_tenant_insert_fails_with_selected_context(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        with pytest.raises(DBAPIError):
            conn.execute(
                text(
                    """
                    insert into listings (listing_id, brokerage_id, spa_data, commission_rate)
                    values (:listing_id, :brokerage_id, '{"project": "Bad Insert"}'::jsonb, 0.02)
                    """
                ),
                {
                    "listing_id": f"{rls_seed['prefix']}-bad-insert",
                    "brokerage_id": rls_seed["brokerage_b"],
                },
            )


def test_mismatched_tenant_update_fails_with_selected_context(rls_seed):
    with _runtime_connection(user_id=rls_seed["multi_user"], brokerage_id=rls_seed["brokerage_a"]) as conn:
        with pytest.raises(DBAPIError):
            conn.execute(
                text("update listings set brokerage_id = :brokerage_b where listing_id = :listing_a"),
                {
                    "brokerage_b": rls_seed["brokerage_b"],
                    "listing_a": rls_seed["listing_a"],
                },
            )


def test_pooled_sessions_do_not_leak_brokerage_context(rls_seed):
    with SessionLocal() as db:
        set_db_session_context(db, brokerage_id=rls_seed["brokerage_a"])
        assert db.execute(text("select app.current_brokerage_id()")).scalar() == rls_seed["brokerage_a"]
        safe_commit(db)

    with SessionLocal() as db:
        clear_db_session_context(db)
        assert db.execute(text("select app.current_brokerage_id()")).scalar() is None


def test_set_local_context_reapplies_after_safe_commit(rls_seed):
    with SessionLocal() as db:
        set_db_session_context(db, brokerage_id=rls_seed["brokerage_a"])
        assert db.execute(text("select app.current_brokerage_id()")).scalar() == rls_seed["brokerage_a"]
        safe_commit(db)
        assert db.execute(text("select app.current_brokerage_id()")).scalar() == rls_seed["brokerage_a"]
        assert db.get(DBListing, rls_seed["listing_a"]) is not None


def test_me_brokerages_works_with_user_context_and_no_selected_brokerage(client, rls_seed):
    with _as_user(rls_seed["multi_user"]):
        response = client.get("/api/v1/me/brokerages")

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_selection"] is True
    assert {row["brokerage_id"] for row in payload["active_brokerages"]} == {
        rls_seed["brokerage_a"],
        rls_seed["brokerage_b"],
    }


def test_dal172_selected_route_still_sets_brokerage_context(client, rls_seed):
    with _as_user(rls_seed["multi_user"]):
        missing = client.get("/api/v1/agent/dashboard")
        selected = client.get(
            "/api/v1/agent/dashboard",
            headers={"X-Brokerage-Id": rls_seed["brokerage_b"]},
        )

    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "brokerage_context_required"
    assert selected.status_code == 200
    assert selected.json()["brokerage"]["brokerage_id"] == rls_seed["brokerage_b"]


def test_admin_user_normal_route_does_not_seed_platform_admin_bypass(monkeypatch, rls_seed):
    monkeypatch.setenv("ADMIN_USER_ID", rls_seed["multi_user"])
    with SessionLocal() as db:
        context = resolve_request_brokerage_context(
            db,
            CurrentUser(id=rls_seed["multi_user"], email="admin@example.com"),
            rls_seed["brokerage_a"],
            allow_platform_admin=False,
        )
        is_platform_admin = db.execute(text("select app.is_platform_admin()")).scalar()

    assert context.brokerage_id == rls_seed["brokerage_a"]
    assert context.is_platform_admin is False
    assert is_platform_admin is False


def test_platform_admin_bypass_requires_explicit_opt_in(monkeypatch, rls_seed):
    platform_user = f"{rls_seed['prefix']}-platform-admin"
    monkeypatch.setenv("ADMIN_USER_ID", platform_user)
    with SessionLocal() as db:
        context = resolve_request_brokerage_context(
            db,
            CurrentUser(id=platform_user, email="platform@example.com"),
            rls_seed["brokerage_a"],
            allow_platform_admin=True,
        )
        is_platform_admin = db.execute(text("select app.is_platform_admin()")).scalar()

    assert context.brokerage_id == rls_seed["brokerage_a"]
    assert context.role == "platform_admin"
    assert context.is_platform_admin is True
    assert is_platform_admin is True


def test_lead_ingest_sets_explicit_service_context(monkeypatch, rls_seed):
    sent_messages: list[dict] = []

    def fake_send_whatsapp_reply(to_number, body, **kwargs):
        sent_messages.append({"to": to_number, "body": body, **kwargs})

    monkeypatch.setattr("app.api.whatsapp.send_whatsapp_reply", fake_send_whatsapp_reply)

    payload = {
        "subject": "Property Finder lead",
        "body": (
            "Source: propertyfinder\n"
            "Name: DAL 170E Buyer\n"
            f"Phone: {rls_seed['portal_phone']}\n"
            "Message: I would like to view this property.\n"
            f"{rls_seed['source_url']}\n"
        ),
    }
    with SessionLocal() as db:
        outcome = ingest_lead_email(
            db,
            to_address=f"leads+{rls_seed['brokerage_a']}@example.test",
            payload=payload,
        )
        assert outcome.status == "ingested"
        assert outcome.conversation_id is not None
        context_brokerage = db.execute(text("select app.current_brokerage_id()")).scalar()
        context_service = db.execute(text("select app.is_service()")).scalar()
        profile = (
            db.query(DBBrokerageBuyerProfile)
            .filter(
                DBBrokerageBuyerProfile.brokerage_id == rls_seed["brokerage_a"],
                DBBrokerageBuyerProfile.buyer_phone == rls_seed["portal_phone"],
            )
            .one()
        )

    assert context_brokerage == rls_seed["brokerage_a"]
    assert context_service is True
    assert profile.source == "portal"
    assert sent_messages
