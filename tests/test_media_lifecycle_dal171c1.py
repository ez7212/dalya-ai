from __future__ import annotations

import time
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.core.media_assets import (
    MediaValidationError,
    delete_media_asset_bytes,
    media_signature_is_valid,
    rotate_media_signing_nonce,
    signed_media_url,
    soft_delete_media_asset,
    revoke_media_asset,
)
from app.db.session import get_db
from app.main import app
from app.models.db_models import DBMediaAsset


class FakeDb:
    def commit(self):
        return None

    def refresh(self, _asset):
        return None


def _asset(
    *,
    media_asset_id: str = "asset-life-1",
    brokerage_id: str = "brokerage-life",
    storage_ref: str = "brokerage-life/asset-life-1.jpg",
    signing_nonce: str = "nonce-before",
    revoked_at=None,
    deleted_at=None,
) -> DBMediaAsset:
    return DBMediaAsset(
        media_asset_id=media_asset_id,
        brokerage_id=brokerage_id,
        mime_type="image/jpeg",
        size_bytes=4,
        storage_ref=storage_ref,
        original_filename="photo.jpg",
        signing_nonce=signing_nonce,
        revoked_at=revoked_at,
        deleted_at=deleted_at,
        source="composer_upload",
    )


def _override_db(asset: DBMediaAsset | None):
    def _get(model, key):
        if model is DBMediaAsset and key == getattr(asset, "media_asset_id", None):
            return asset
        return None

    fake_db = SimpleNamespace(get=_get)
    app.dependency_overrides[get_db] = lambda: fake_db


def _clear_override():
    app.dependency_overrides.pop(get_db, None)


def _request_target(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.path}?{parts.query}"


def test_signing_nonce_is_part_of_signature(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")
    exp = int(time.time()) + 60
    asset = _asset(signing_nonce="nonce-a")
    sig = media_signature_is_valid(
        media_asset_id=asset.media_asset_id,
        brokerage_id=asset.brokerage_id,
        exp=exp,
        signing_nonce="nonce-a",
        sig="bad",
    )
    assert sig is False

    signed_url = signed_media_url(asset, ttl_seconds=60)
    query = parse_qs(urlsplit(signed_url).query)
    assert media_signature_is_valid(
        media_asset_id=asset.media_asset_id,
        brokerage_id=asset.brokerage_id,
        exp=int(query["exp"][0]),
        signing_nonce="nonce-b",
        sig=query["sig"][0],
    ) is False


def test_rotating_nonce_invalidates_old_url(monkeypatch, tmp_path):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("PUBLIC_URL", "https://dalya.test")
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    asset = _asset()
    path = tmp_path / asset.storage_ref
    path.parent.mkdir(parents=True)
    path.write_bytes(b"JPEG")
    old_url = signed_media_url(asset, ttl_seconds=60)

    rotate_media_signing_nonce(FakeDb(), asset, reason="test-rotation")

    client = TestClient(app)
    _override_db(asset)
    try:
        old_response = client.get(_request_target(old_url))
        new_response = client.get(_request_target(signed_media_url(asset, ttl_seconds=60)))
    finally:
        _clear_override()

    assert old_response.status_code == 403
    assert new_response.status_code == 200
    assert new_response.content == b"JPEG"


def test_revoked_and_deleted_assets_do_not_mint_urls():
    with pytest.raises(MediaValidationError):
        signed_media_url(_asset(revoked_at=datetime.utcnow()))
    with pytest.raises(MediaValidationError):
        signed_media_url(_asset(deleted_at=datetime.utcnow()))


def test_revoked_asset_stream_returns_404(monkeypatch, tmp_path):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("PUBLIC_URL", "https://dalya.test")
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    asset = _asset()
    path = tmp_path / asset.storage_ref
    path.parent.mkdir(parents=True)
    path.write_bytes(b"JPEG")
    url = signed_media_url(asset, ttl_seconds=60)
    revoke_media_asset(FakeDb(), asset, reason="test-revoke")

    client = TestClient(app)
    _override_db(asset)
    try:
        response = client.get(_request_target(url))
    finally:
        _clear_override()

    assert response.status_code == 404


def test_delete_media_asset_bytes_deletes_local_file_and_blocks_access(monkeypatch, tmp_path):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    asset = _asset()
    path = tmp_path / asset.storage_ref
    path.parent.mkdir(parents=True)
    path.write_bytes(b"JPEG")

    delete_media_asset_bytes(FakeDb(), asset, reason="test-delete")

    assert not path.exists()
    assert asset.revoked_at is not None
    assert asset.deleted_at is not None
    with pytest.raises(MediaValidationError):
        signed_media_url(asset, ttl_seconds=60)


def test_soft_delete_blocks_without_physical_delete(monkeypatch, tmp_path):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    asset = _asset()
    path = tmp_path / asset.storage_ref
    path.parent.mkdir(parents=True)
    path.write_bytes(b"JPEG")

    soft_delete_media_asset(FakeDb(), asset, reason="test-soft-delete")

    assert path.exists()
    assert asset.revoked_at is not None
    assert asset.deleted_at is not None
    with pytest.raises(MediaValidationError):
        signed_media_url(asset, ttl_seconds=60)
