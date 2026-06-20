from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.core.media_assets import (
    delete_media_for_buyer_request,
    media_asset_ids_from_metadata,
)
from app.models.db_models import DBComplianceEvent, DBConversation, DBMediaAsset, DBMessage


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.rows)


class FakeDb:
    def __init__(self, *, conversations, messages, assets):
        self.conversations = conversations
        self.messages = messages
        self.assets = {asset.media_asset_id: asset for asset in assets}
        self.added = []
        self.commits = 0

    def query(self, entity):
        if entity is DBConversation:
            return FakeQuery(self.conversations)
        if entity is DBMessage:
            return FakeQuery(self.messages)
        return FakeQuery(
            [SimpleNamespace(media_asset_id=asset.media_asset_id) for asset in self.assets.values()]
        )

    def get(self, model, key):
        if model is DBMediaAsset:
            return self.assets.get(key)
        return None

    def add(self, row):
        self.added.append(row)

    def commit(self):
        self.commits += 1

    def refresh(self, _row):
        return None


def _conversation(conversation_id="conv-a", brokerage_id="brokerage-a", buyer_phone="+971500000001"):
    return DBConversation(
        conversation_id=conversation_id,
        brokerage_id=brokerage_id,
        listing_id="listing-a",
        buyer_phone=buyer_phone,
    )


def _message(metadata):
    return DBMessage(
        conversation_id="conv-a",
        role="user",
        content="media",
        metadata_json=metadata,
    )


def _asset(media_asset_id, brokerage_id="brokerage-a", storage_ref=None):
    return DBMediaAsset(
        media_asset_id=media_asset_id,
        brokerage_id=brokerage_id,
        mime_type="image/png",
        size_bytes=4,
        storage_ref=storage_ref or f"{brokerage_id}/{media_asset_id}.png",
        original_filename=f"{media_asset_id}.png",
        signing_nonce=f"nonce-{media_asset_id}",
        source="buyer_inbound",
    )


def test_media_asset_ids_from_metadata_discovers_inbound_voice_and_media_refs():
    ids = media_asset_ids_from_metadata(
        {
            "inbound_media_assets": [{"media_asset_id": "asset-image"}],
            "voice_note": {"media_asset_id": "asset-voice", "audio_url": "https://provider.test/raw.ogg"},
            "media": [{"media_asset_id": "asset-outbound", "url": "https://dalya.test/media/asset-outbound"}],
        }
    )

    assert ids == {"asset-image", "asset-voice", "asset-outbound"}


def test_pdpl_media_deletion_revokes_deletes_redacts_and_audits(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    image_asset = _asset("asset-image")
    voice_asset = _asset("asset-voice", storage_ref="brokerage-a/asset-voice.ogg")
    for asset in (image_asset, voice_asset):
        path = tmp_path / asset.storage_ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"data")
    message = _message(
        {
            "inbound_media_assets": [
                {
                    "media_asset_id": image_asset.media_asset_id,
                    "provider_url": "https://api.twilio.test/media/image.png",
                    "content_type": "image/png",
                }
            ],
            "voice_note": {
                "media_asset_id": voice_asset.media_asset_id,
                "audio_url": "https://api.twilio.test/media/audio.ogg",
            },
        }
    )
    db = FakeDb(
        conversations=[_conversation()],
        messages=[message],
        assets=[image_asset, voice_asset],
    )

    result = delete_media_for_buyer_request(
        db,
        brokerage_id="brokerage-a",
        conversation_id="conv-a",
        actor_user_id="agent-a",
    )

    assert result["media_asset_count"] == 2
    assert sorted(result["deleted_media_asset_ids"]) == ["asset-image", "asset-voice"]
    for asset in (image_asset, voice_asset):
        assert asset.revoked_at is not None
        assert asset.deleted_at is not None
        assert asset.original_filename == "[redacted]"
        assert not (tmp_path / asset.storage_ref).exists()
        assert asset.metadata_json["lifecycle"]["metadata_redacted_reason"] == "pdpl_media_deletion"
    metadata = message.metadata_json
    assert "provider_url" not in metadata["inbound_media_assets"][0]
    assert metadata["inbound_media_assets"][0]["redacted"] is True
    assert "audio_url" not in metadata["voice_note"]
    assert metadata["voice_note"]["redacted"] is True
    compliance_events = [row for row in db.added if isinstance(row, DBComplianceEvent)]
    assert len(compliance_events) == 1
    event = compliance_events[0]
    assert event.event_type == "pdpl_media_deleted"
    assert event.buyer_phone is None
    assert event.details["media_asset_count"] == 2


def test_pdpl_media_deletion_skips_cross_brokerage_asset(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    scoped = _asset("asset-scoped", brokerage_id="brokerage-a")
    other = _asset("asset-other", brokerage_id="brokerage-b")
    for asset in (scoped, other):
        path = tmp_path / asset.storage_ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"data")
    message = _message(
        {
            "inbound_media_assets": [
                {"media_asset_id": scoped.media_asset_id},
                {"media_asset_id": other.media_asset_id},
            ]
        }
    )
    db = FakeDb(
        conversations=[_conversation()],
        messages=[message],
        assets=[scoped, other],
    )

    result = delete_media_for_buyer_request(
        db,
        brokerage_id="brokerage-a",
        conversation_id="conv-a",
    )

    assert result["deleted_media_asset_ids"] == ["asset-scoped"]
    assert result["skipped_media_asset_ids"] == ["asset-other"]
    assert scoped.deleted_at is not None
    assert other.deleted_at is None
    assert (tmp_path / other.storage_ref).exists()
