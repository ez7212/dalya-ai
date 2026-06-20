from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.debounce_worker import _prepare_voice_inbound
from app.core.media_assets import (
    MediaValidationError,
    inbound_media_asset_metadata,
    store_inbound_provider_media_asset,
)
from app.core.transcription.models import TranscriptionResult
from app.core.voice_notes import transcription_result_metadata
from app.models.db_models import DBMediaAsset


class FakeDb:
    def __init__(self):
        self.assets: list[DBMediaAsset] = []

    def add(self, asset):
        self.assets.append(asset)

    def flush(self):
        for asset in self.assets:
            if not asset.media_asset_id:
                asset.media_asset_id = f"asset-{uuid.uuid4().hex[:8]}"

    def commit(self):
        return None

    def refresh(self, asset):
        return None


class FakeSession:
    def __init__(self, asset: DBMediaAsset | None):
        self.asset = asset

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get(self, _model, key):
        if self.asset and self.asset.media_asset_id == key:
            return self.asset
        return None


def _fake_result(text: str = "Can I see the floor plan?") -> TranscriptionResult:
    return TranscriptionResult(
        provider="speechmatics",
        raw_transcript=text,
        corrected_transcript=text,
        language="en",
        confidence=0.94,
    )


def test_inbound_image_persists_as_tenant_scoped_media_asset(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "app.core.media_assets.download_provider_media_bytes",
        lambda *args, **kwargs: b"PNG",
    )
    db = FakeDb()

    asset = store_inbound_provider_media_asset(
        db,
        brokerage_id="brokerage-a",
        media_url="https://api.twilio.test/media/image.png",
        mime_type="image/png",
        source="buyer_inbound",
    )

    assert asset.brokerage_id == "brokerage-a"
    assert asset.source == "buyer_inbound"
    assert asset.storage_ref.startswith("brokerage-a/")
    assert Path(tmp_path / asset.storage_ref).read_bytes() == b"PNG"
    assert inbound_media_asset_metadata(asset, content_type="image/png") == {
        "media_asset_id": asset.media_asset_id,
        "brokerage_id": "brokerage-a",
        "content_type": "image/png",
        "mime_type": "image/png",
        "source": "buyer_inbound",
    }


def test_inbound_pdf_persists_without_raw_provider_url(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "app.core.media_assets.download_provider_media_bytes",
        lambda *args, **kwargs: b"%PDF-1.4",
    )
    db = FakeDb()

    asset = store_inbound_provider_media_asset(
        db,
        brokerage_id="brokerage-b",
        media_url="https://api.twilio.test/media/document.pdf?token=secret",
        mime_type="application/pdf",
        source="buyer_inbound",
    )
    metadata = inbound_media_asset_metadata(asset, content_type="application/pdf")

    assert asset.brokerage_id == "brokerage-b"
    assert asset.original_filename == "document.pdf"
    assert "api.twilio.test" not in str(metadata)
    assert metadata["media_asset_id"] == asset.media_asset_id


def test_inbound_media_requires_tenant_root(monkeypatch):
    monkeypatch.setattr(
        "app.core.media_assets.download_provider_media_bytes",
        lambda *args, **kwargs: b"PNG",
    )

    with pytest.raises(MediaValidationError):
        store_inbound_provider_media_asset(
            FakeDb(),
            brokerage_id="",
            media_url="https://api.twilio.test/media/image.png",
            mime_type="image/png",
        )


def test_voice_note_metadata_prefers_media_asset_id_over_provider_url():
    metadata = transcription_result_metadata(
        _fake_result("Voice content"),
        direction="buyer_to_property_advisor",
        audio_url="https://api.twilio.test/raw-voice.ogg",
        media_asset_id="asset-voice",
    )

    voice_note = metadata["voice_note"]
    assert voice_note["media_asset_id"] == "asset-voice"
    assert "audio_url" not in voice_note


def test_prepare_voice_inbound_reads_persisted_audio_asset(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    asset = DBMediaAsset(
        media_asset_id="voice-asset",
        brokerage_id="brokerage-voice",
        mime_type="audio/ogg",
        size_bytes=5,
        storage_ref="brokerage-voice/voice-asset.ogg",
        original_filename="voice.ogg",
        source="buyer_inbound",
    )
    path = tmp_path / asset.storage_ref
    path.parent.mkdir(parents=True)
    path.write_bytes(b"voice")
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: FakeSession(asset))
    monkeypatch.setattr(
        "app.core.voice_notes.transcribe_audio_file",
        lambda *args, **kwargs: _fake_result("Stored voice"),
    )

    body, metadata = asyncio.run(
        _prepare_voice_inbound(
            combined_body="",
            listing_id=None,
            media_urls=[],
            media_content_types=[],
            metadata_items=[
                {
                    "inbound_media_assets": [
                        {
                            "media_asset_id": asset.media_asset_id,
                            "content_type": "audio/ogg",
                        }
                    ]
                }
            ],
        )
    )

    assert body == "Stored voice"
    voice_note = metadata["voice_note"]
    assert voice_note["media_asset_id"] == "voice-asset"
    assert "audio_url" not in voice_note
