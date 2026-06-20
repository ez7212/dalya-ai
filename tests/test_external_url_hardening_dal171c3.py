from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.media_assets import (
    MediaValidationError,
    listing_assets_for_attachment,
    register_external_media_asset,
    signed_media_url,
    validate_external_url,
)
from app.models.db_models import DBMediaAsset


class FakeDb:
    def __init__(self):
        self.rows = []

    def add(self, row):
        self.rows.append(row)

    def commit(self):
        return None

    def refresh(self, row):
        if not row.media_asset_id:
            row.media_asset_id = "asset-external"


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "data:text/plain,hello",
        "ftp://example.com/file.pdf",
        "http://example.com/file.pdf",
        "https://localhost/file.pdf",
        "https://127.0.0.1/file.pdf",
        "https://10.0.0.5/file.pdf",
        "https://169.254.169.254/latest/meta-data",
        "https://metadata.google.internal/computeMetadata/v1",
        "https://internal/file.pdf",
        "not a url",
    ],
)
def test_external_url_validator_rejects_unsafe_urls(url):
    with pytest.raises(MediaValidationError):
        validate_external_url(url)


def test_external_url_validator_allows_https_public_urls():
    assert (
        validate_external_url("https://www.propertyfinder.ae/en/plp/buy/apartment-1")
        == "https://www.propertyfinder.ae/en/plp/buy/apartment-1"
    )


def test_register_external_media_asset_rejects_unsafe_storage_ref():
    with pytest.raises(MediaValidationError):
        register_external_media_asset(
            FakeDb(),
            brokerage_id="brokerage-a",
            agent_user_id="agent-a",
            conversation_id="conversation-a",
            listing_id="listing-a",
            url="http://example.com/floorplan.pdf",
        )


def test_signed_media_external_pass_through_requires_safe_https():
    safe = DBMediaAsset(
        media_asset_id="asset-safe",
        brokerage_id="brokerage-a",
        mime_type="application/pdf",
        size_bytes=0,
        storage_ref="https://cdn.example.com/floorplan.pdf",
        signing_nonce="nonce-safe",
        source="listing_asset",
    )
    unsafe = DBMediaAsset(
        media_asset_id="asset-unsafe",
        brokerage_id="brokerage-a",
        mime_type="application/pdf",
        size_bytes=0,
        storage_ref="http://cdn.example.com/floorplan.pdf",
        signing_nonce="nonce-unsafe",
        source="listing_asset",
    )

    assert signed_media_url(safe) == safe.storage_ref
    with pytest.raises(MediaValidationError):
        signed_media_url(unsafe)


def test_listing_assets_for_attachment_filters_unsafe_external_urls():
    listing = SimpleNamespace(
        listing_id="listing-a",
        media_urls=[
            "https://cdn.example.com/image.jpg",
            "http://cdn.example.com/insecure.jpg",
            "https://127.0.0.1/private.jpg",
        ],
        documents=[
            SimpleNamespace(
                source_url="https://docs.example.com/service-charge.pdf",
                label="Service charge",
                document_type="service_charge_statement",
            ),
            SimpleNamespace(
                source_url="file:///tmp/title-deed.pdf",
                label="Unsafe",
                document_type="title_deed",
            ),
        ],
    )

    assets = listing_assets_for_attachment(FakeDb(), listing)

    assert [asset["url"] for asset in assets] == [
        "https://cdn.example.com/image.jpg",
        "https://docs.example.com/service-charge.pdf",
    ]
