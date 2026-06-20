"""
DAL-160 — Outbound media via dashboard composer.

Covers the spec verification checklist items owned by DAL-160:
  1.  3 PDFs + caption → buyer receives all, timeline shows chips, compliance
      events written.
  2.  "Attach from listing" pulls existing listing assets without re-upload.
  3.  Media send blocked when the 24h session window is closed; reopen flow
      surfaced.
  11. Oversize file → agent-facing error naming the limit, nothing partially
      sent.
  12. Cross-tenant: media asset storage refs scoped by brokerage_id.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBBrokerage,
    DBBrokerageMember,
    DBComplianceEvent,
    DBConversation,
    DBLeadAction,
    DBLeadAssignment,
    DBListing,
    DBMediaAsset,
    DBMessage,
)

PDF_BYTES = b"%PDF-1.4 fake brochure content"


@pytest.fixture
def media_seed(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("PUBLIC_URL", "https://dalya.test")

    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"med-brokerage-{suffix}"
    other_brokerage_id = f"med-other-{suffix}"
    listing_id = f"med-listing-{suffix}"
    buyer_phone = f"+97156644{suffix[:4]}"
    brokerage_ai_number = f"+97158844{suffix[:4]}"
    agent_user_id = f"med-agent-{suffix}"
    outsider_user_id = f"med-outsider-{suffix}"
    brochure_url = f"https://cdn.example.com/brochures/{suffix}.pdf"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Media Brokerage",
            slug=f"med-{suffix}",
            status="active",
            brokerage_ai_number=brokerage_ai_number,
            agents_ai_number=f"+97159944{suffix[:4]}",
        ))
        db.add(DBBrokerage(
            brokerage_id=other_brokerage_id,
            name="Other Media Brokerage",
            slug=f"med-other-{suffix}",
            status="active",
        ))
        db.add(DBBrokerageMember(
            brokerage_id=brokerage_id,
            user_id=agent_user_id,
            role="agent",
            status="active",
        ))
        db.add(DBBrokerageMember(
            brokerage_id=other_brokerage_id,
            user_id=outsider_user_id,
            role="agent",
            status="active",
        ))
        db.add(DBListing(
            listing_id=listing_id,
            brokerage_id=brokerage_id,
            assigned_agent_id=agent_user_id,
            spa_data={
                "project": "Media Mansions",
                "unit_number": "501",
                "developer": "Emaar",
                "property_type": "Apartment",
                "bedrooms": 3,
                "purchase_price_aed": 3_000_000,
            },
            seller_asking_price=3_000_000,
            commission_rate=0.02,
            property_type="ready",
            additional_fees=[],
            seller_qa=[],
            media_urls=[brochure_url],
            unit_profile={},
            unit_profile_history=[],
            processing_stages={},
        ))
        safe_commit(db)
        conv = crud.get_or_create_conversation(db, buyer_phone, listing_id)
        conv.buyer_name = "Omar"
        conv.assigned_agent_id = agent_user_id
        # Fresh buyer inbound → 24h session window open.
        db.add(DBMessage(
            conversation_id=conv.conversation_id,
            role="user",
            content="Can you send the brochure?",
        ))
        safe_commit(db)
        conversation_id = conv.conversation_id

    transport = SimulatedTransport()
    set_transport_override(transport)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=agent_user_id, email="media-agent@example.com",
    )

    try:
        yield {
            "brokerage_id": brokerage_id,
            "other_brokerage_id": other_brokerage_id,
            "listing_id": listing_id,
            "conversation_id": conversation_id,
            "buyer_phone": buyer_phone,
            "agent_user_id": agent_user_id,
            "outsider_user_id": outsider_user_id,
            "brochure_url": brochure_url,
            "transport": transport,
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        set_transport_override(None)
        with SessionLocal() as db:
            for brokerage in (brokerage_id, other_brokerage_id):
                db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBMediaAsset).filter(DBMediaAsset.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == brokerage).delete(synchronize_session=False)
            db.query(DBLeadAction).filter(DBLeadAction.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([brokerage_id, other_brokerage_id])).delete(synchronize_session=False)
            safe_commit(db)


def _pdf_files(count: int):
    return [
        ("files", (f"brochure-{index}.pdf", io.BytesIO(PDF_BYTES), "application/pdf"))
        for index in range(count)
    ]


# ── Checklist 1: 3 PDFs + caption ──────────────────────────────────────────────


def test_three_pdfs_with_caption_reach_buyer_with_chips_and_compliance(client, media_seed):
    seed = media_seed
    transport = seed["transport"]

    response = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/media",
        files=_pdf_files(3),
        data={"caption": "Here is everything on Media Mansions 501."},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["sent"] is True
    assert len(payload["attachments"]) == 3

    sends = transport.messages_to_buyer(seed["buyer_phone"])
    assert len(sends) == 3
    assert all(send.media_url for send in sends)
    assert sends[0].body == "Here is everything on Media Mansions 501."
    assert sends[1].body == "" and sends[2].body == ""

    signed_urls = [urlsplit(send.media_url) for send in sends]
    assert all(parsed.path.startswith("/media/") for parsed in signed_urls)
    assert all(seed["brokerage_id"] not in parsed.path for parsed in signed_urls)
    assert all(parse_qs(parsed.query).get("exp") for parsed in signed_urls)
    assert all(parse_qs(parsed.query).get("sig") for parsed in signed_urls)

    with SessionLocal() as db:
        message = (
            db.query(DBMessage)
            .filter(
                DBMessage.conversation_id == seed["conversation_id"],
                DBMessage.intent == "agent_media",
            )
            .one()
        )
        chips = message.metadata_json["media"]
        assert len(chips) == 3
        assert all(chip["mime_type"] == "application/pdf" for chip in chips)

        events = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.conversation_id == seed["conversation_id"],
                DBComplianceEvent.event_type == "agent_media_sent",
            )
            .all()
        )
        assert len(events) == 3
        assert all(event.details["sha256"] for event in events)

        assets = (
            db.query(DBMediaAsset)
            .filter(DBMediaAsset.brokerage_id == seed["brokerage_id"])
            .all()
        )
        assert len(assets) == 3
        assert {parsed.path for parsed in signed_urls} == {
            f"/media/{asset.media_asset_id}" for asset in assets
        }
        assert all(asset.brokerage_id == seed["brokerage_id"] for asset in assets)
        assert all(asset.storage_ref.startswith(seed["brokerage_id"]) for asset in assets)
        assert all(asset.size_bytes == len(PDF_BYTES) for asset in assets)


# ── Checklist 2: attach from listing without re-upload ─────────────────────────


def test_attach_from_listing_sends_existing_assets_without_reupload(client, media_seed):
    seed = media_seed
    transport = seed["transport"]

    assets_response = client.get(f"/api/v1/agent/listings/{seed['listing_id']}/assets")
    assert assets_response.status_code == 200
    asset_urls = [item["url"] for item in assets_response.json()["assets"]]
    assert seed["brochure_url"] in asset_urls

    response = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/media/from-listing",
        json={"urls": [seed["brochure_url"]], "caption": "Brochure attached."},
    )
    assert response.status_code == 200, response.text

    sends = transport.messages_to_buyer(seed["buyer_phone"])
    assert len(sends) == 1
    assert sends[0].media_url == seed["brochure_url"]  # passed through, no re-upload
    assert sends[0].body == "Brochure attached."

    with SessionLocal() as db:
        asset = (
            db.query(DBMediaAsset)
            .filter(
                DBMediaAsset.brokerage_id == seed["brokerage_id"],
                DBMediaAsset.source == "listing_asset",
            )
            .one()
        )
        assert asset.storage_ref == seed["brochure_url"]

    # A URL that is not a listing asset is rejected — no fuzzy passthrough.
    forged = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/media/from-listing",
        json={"urls": ["https://cdn.example.com/not-ours.pdf"]},
    )
    assert forged.status_code == 422


# ── Checklist 3: 24h window closed → blocked + surfaced ────────────────────────


def test_media_blocked_when_session_window_closed(client, media_seed):
    seed = media_seed
    transport = seed["transport"]

    with SessionLocal() as db:
        db.query(DBMessage).filter(
            DBMessage.conversation_id == seed["conversation_id"],
            DBMessage.role == "user",
        ).update(
            {"timestamp": datetime.utcnow() - timedelta(hours=25)},
            synchronize_session=False,
        )
        safe_commit(db)

    response = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/media",
        files=_pdf_files(1),
        data={"caption": ""},
    )
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["reason"] == "session_window_closed"
    assert transport.messages_to_buyer(seed["buyer_phone"]) == []

    # Buyer replies → window reopens → send succeeds.
    with SessionLocal() as db:
        db.add(DBMessage(
            conversation_id=seed["conversation_id"],
            role="user",
            content="Yes please send it",
        ))
        safe_commit(db)

    retry = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/media",
        files=_pdf_files(1),
        data={"caption": ""},
    )
    assert retry.status_code == 200, retry.text
    assert len(transport.messages_to_buyer(seed["buyer_phone"])) == 1


# ── Checklist 11: oversize file names the limit, nothing partially sent ───────


def test_oversize_file_rejected_naming_limit_nothing_sent(client, media_seed):
    seed = media_seed
    transport = seed["transport"]
    oversize = b"x" * (16 * 1024 * 1024 + 1)

    response = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/media",
        files=[
            ("files", ("ok.pdf", io.BytesIO(PDF_BYTES), "application/pdf")),
            ("files", ("huge.pdf", io.BytesIO(oversize), "application/pdf")),
        ],
        data={"caption": ""},
    )
    assert response.status_code == 422
    assert "16 MB" in response.json()["detail"]
    # Validation is all-up-front: the valid file did not send either.
    assert transport.messages_to_buyer(seed["buyer_phone"]) == []
    with SessionLocal() as db:
        assert (
            db.query(DBMediaAsset)
            .filter(DBMediaAsset.brokerage_id == seed["brokerage_id"])
            .count()
            == 0
        )


def test_unsupported_mime_type_rejected(client, media_seed):
    seed = media_seed
    response = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/media",
        files=[("files", ("notes.txt", io.BytesIO(b"hello"), "text/plain"))],
        data={"caption": ""},
    )
    assert response.status_code == 422
    assert "Unsupported file type" in response.json()["detail"]


# ── Checklist 12: cross-tenant scoping ─────────────────────────────────────────


def test_cross_tenant_media_access_blocked(client, media_seed):
    seed = media_seed
    transport = seed["transport"]

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seed["outsider_user_id"], email="outsider@example.com",
    )

    response = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/media",
        files=_pdf_files(1),
        data={"caption": ""},
    )
    assert response.status_code in {403, 404}

    assets_response = client.get(f"/api/v1/agent/listings/{seed['listing_id']}/assets")
    assert assets_response.status_code == 404

    assert transport.messages_to_buyer(seed["buyer_phone"]) == []
    with SessionLocal() as db:
        assert (
            db.query(DBMediaAsset)
            .filter(DBMediaAsset.brokerage_id == seed["other_brokerage_id"])
            .count()
            == 0
        )
