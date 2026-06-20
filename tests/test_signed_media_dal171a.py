from __future__ import annotations

import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from starlette.routing import Mount

from app.core.media_assets import (
    public_media_url,
    sign_media_url_payload,
    signed_media_url,
)
from app.db.session import get_db
from app.main import app
from app.models.db_models import DBMediaAsset


@pytest.fixture
def client():
    return TestClient(app)


def _asset(
    *,
    media_asset_id: str = "asset-1",
    brokerage_id: str = "brokerage-1",
    storage_ref: str = "brokerage-1/asset-1.jpg",
    mime_type: str = "image/jpeg",
    original_filename: str | None = "floorplan.jpg",
    signing_nonce: str = "nonce-1",
) -> DBMediaAsset:
    return DBMediaAsset(
        media_asset_id=media_asset_id,
        brokerage_id=brokerage_id,
        mime_type=mime_type,
        size_bytes=4,
        storage_ref=storage_ref,
        original_filename=original_filename,
        signing_nonce=signing_nonce,
        source="composer_upload",
    )


def _request_target(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.path}?{parts.query}"


def _override_db(asset: DBMediaAsset | None):
    def _get(model, key):
        if model is DBMediaAsset and key == getattr(asset, "media_asset_id", None):
            return asset
        return None

    fake_db = SimpleNamespace(get=_get)
    app.dependency_overrides[get_db] = lambda: fake_db


def _clear_override():
    app.dependency_overrides.pop(get_db, None)


def test_signed_media_url_builder_includes_exp_and_sig(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("PUBLIC_URL", "https://dalya.test")
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")

    url = signed_media_url(_asset(), ttl_seconds=60)
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "dalya.test"
    assert parsed.path == "/media/asset-1"
    assert int(query["exp"][0]) >= int(time.time())
    assert query["sig"][0]


def test_public_media_url_alias_returns_signed_local_url(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("PUBLIC_URL", "https://dalya.test")
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")

    url = public_media_url(_asset())

    assert url.startswith("https://dalya.test/media/asset-1?")
    assert "sig=" in url


def test_external_storage_ref_passes_through(monkeypatch):
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")
    asset = _asset(storage_ref="https://cdn.example.com/listing.pdf")

    assert signed_media_url(asset) == "https://cdn.example.com/listing.pdf"


def test_signing_secret_required_in_production(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.delenv("MEDIA_URL_SIGNING_SECRET", raising=False)

    with pytest.raises(RuntimeError):
        signed_media_url(_asset(), ttl_seconds=60)


def test_valid_signed_media_url_streams_file(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("PUBLIC_URL", "https://dalya.test")
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    asset = _asset()
    path = tmp_path / asset.storage_ref
    path.parent.mkdir(parents=True)
    path.write_bytes(b"JPEG")
    _override_db(asset)
    try:
        response = client.get(_request_target(signed_media_url(asset, ttl_seconds=60)))
    finally:
        _clear_override()

    assert response.status_code == 200
    assert response.content == b"JPEG"
    assert response.headers["content-type"].startswith("image/jpeg")


def test_expired_signed_media_url_returns_403(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    asset = _asset()
    exp = int(time.time()) - 1
    sig = sign_media_url_payload(
        media_asset_id=asset.media_asset_id,
        brokerage_id=asset.brokerage_id,
        exp=exp,
        signing_nonce=asset.signing_nonce,
    )
    _override_db(asset)
    try:
        response = client.get(f"/media/{asset.media_asset_id}?exp={exp}&sig={sig}")
    finally:
        _clear_override()

    assert response.status_code == 403


def test_tampered_signature_returns_403(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    asset = _asset()
    _override_db(asset)
    try:
        response = client.get(f"/media/{asset.media_asset_id}?exp={int(time.time()) + 60}&sig=bad")
    finally:
        _clear_override()

    assert response.status_code == 403


def test_signature_for_wrong_brokerage_returns_403(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    asset = _asset()
    exp = int(time.time()) + 60
    sig = sign_media_url_payload(
        media_asset_id=asset.media_asset_id,
        brokerage_id="other-brokerage",
        exp=exp,
        signing_nonce=asset.signing_nonce,
    )
    _override_db(asset)
    try:
        response = client.get(f"/media/{asset.media_asset_id}?exp={exp}&sig={sig}")
    finally:
        _clear_override()

    assert response.status_code == 403


def test_missing_asset_or_file_returns_404(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("MEDIA_URL_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path))
    missing = _asset(media_asset_id="missing")
    url = signed_media_url(missing, ttl_seconds=60)
    _override_db(None)
    try:
        missing_asset = client.get(_request_target(url))
    finally:
        _clear_override()

    asset = _asset(media_asset_id="file-missing", storage_ref="brokerage-1/file-missing.jpg")
    _override_db(asset)
    try:
        missing_file = client.get(_request_target(signed_media_url(asset, ttl_seconds=60)))
    finally:
        _clear_override()

    assert missing_asset.status_code == 404
    assert missing_file.status_code == 404


def test_public_static_media_mount_is_gone():
    assert not any(isinstance(route, Mount) and route.path == "/media" for route in app.routes)
