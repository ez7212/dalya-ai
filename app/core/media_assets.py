"""
Outbound media for buyer conversations (DAL-160).

Storage layer + send pipeline shared by the dashboard composer (this
change-set) and the WhatsApp agent relay (DAL-161):

  upload → persist DBMediaAsset (brokerage-scoped storage ref, sha256)
         → send via the transport's media API, one message per file
         → timeline message with file chips
         → compliance event per media send

Rules encoded here, not in the UI:
  - per-transport size limits (MessagingTransport.media_limit_bytes)
  - the 24-hour session window: media sends are session messages; when the
    buyer's last inbound is older than 24h the send is blocked and the caller
    surfaces the template-first reopen flow (existing behavior — reused, no
    media template path in this change-set).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.brokerage_access import is_buyer_suppressed, record_compliance_event
from app.core.messaging import get_transport
from app.core.messaging.types import OutboundBuyerMessage
from app.core.runtime_config import env_name, is_production
from app.db.session import safe_commit
from app.models.db_models import (
    DBBrokerage,
    DBConversation,
    DBLeadAction,
    DBListing,
    DBMediaAsset,
    DBMessage,
)

logger = logging.getLogger(__name__)

SESSION_WINDOW = timedelta(hours=24)
MAX_ATTACHMENTS_PER_SEND = 10
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
ALLOWED_INBOUND_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "audio/aac",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
}
DEFAULT_MEDIA_URL_TTL_SECONDS = 900
DEFAULT_MEDIA_INBOUND_MAX_BYTES = 10 * 1024 * 1024
_NON_PRODUCTION_MEDIA_ENVS = {"test", "local", "development", "dev", "ci", "rehearsal"}
_LOCAL_MEDIA_SIGNING_SECRET = "dalya-local-media-url-signing-secret"


def media_storage_dir() -> Path:
    configured = os.getenv("MEDIA_STORAGE_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "static" / "media"


def local_media_asset_path(asset: DBMediaAsset) -> Path:
    storage_root = media_storage_dir().resolve()
    candidate = (storage_root / asset.storage_ref).resolve()
    if not candidate.is_relative_to(storage_root):
        raise MediaValidationError("Media asset path is outside the configured storage directory.")
    return candidate


def media_url_ttl_seconds() -> int:
    raw = os.getenv("MEDIA_URL_TTL_SECONDS")
    if raw is None:
        return DEFAULT_MEDIA_URL_TTL_SECONDS
    try:
        ttl = int(raw)
    except ValueError as exc:
        raise RuntimeError("MEDIA_URL_TTL_SECONDS must be an integer") from exc
    if ttl <= 0:
        raise RuntimeError("MEDIA_URL_TTL_SECONDS must be positive")
    return ttl


def media_inbound_max_bytes() -> int:
    raw = os.getenv("MEDIA_INBOUND_MAX_BYTES")
    if raw is None:
        return DEFAULT_MEDIA_INBOUND_MAX_BYTES
    try:
        limit = int(raw)
    except ValueError as exc:
        raise RuntimeError("MEDIA_INBOUND_MAX_BYTES must be an integer") from exc
    if limit <= 0:
        raise RuntimeError("MEDIA_INBOUND_MAX_BYTES must be positive")
    return limit


def media_url_signing_secret() -> str:
    secret = os.getenv("MEDIA_URL_SIGNING_SECRET")
    if secret:
        return secret
    if is_production():
        raise RuntimeError("MEDIA_URL_SIGNING_SECRET is required in production")
    if env_name() in _NON_PRODUCTION_MEDIA_ENVS:
        return _LOCAL_MEDIA_SIGNING_SECRET
    raise RuntimeError("MEDIA_URL_SIGNING_SECRET is required for media URL signing")


def media_signature_payload(*, media_asset_id: str, brokerage_id: str, exp: int) -> str:
    return f"{media_asset_id}.{brokerage_id}.{exp}"


def sign_media_url_payload(*, media_asset_id: str, brokerage_id: str, exp: int) -> str:
    return hmac.new(
        media_url_signing_secret().encode("utf-8"),
        media_signature_payload(
            media_asset_id=media_asset_id,
            brokerage_id=brokerage_id,
            exp=exp,
        ).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def media_signature_is_valid(*, media_asset_id: str, brokerage_id: str, exp: int, sig: str) -> bool:
    expected = sign_media_url_payload(
        media_asset_id=media_asset_id,
        brokerage_id=brokerage_id,
        exp=exp,
    )
    return hmac.compare_digest(expected, sig or "")


class MediaValidationError(ValueError):
    """Agent-facing validation failure — nothing was sent."""


class SessionWindowClosedError(RuntimeError):
    """The buyer's 24h session window is closed; free-form media is blocked."""

    def __init__(self, last_inbound_at: Optional[datetime]):
        self.last_inbound_at = last_inbound_at
        super().__init__("session_window_closed")


@dataclass
class MediaSendOutcome:
    message_id: Optional[str]
    sent_assets: list[dict]
    caption: str


def last_buyer_inbound_at(db: Session, conversation_id: str) -> Optional[datetime]:
    row = (
        db.query(DBMessage.timestamp)
        .filter(
            DBMessage.conversation_id == conversation_id,
            DBMessage.role == "user",
        )
        .order_by(DBMessage.timestamp.desc())
        .first()
    )
    return row.timestamp if row else None


def session_window_state(db: Session, conversation_id: str, now: Optional[datetime] = None) -> dict:
    now = now or datetime.utcnow()
    last_inbound = last_buyer_inbound_at(db, conversation_id)
    open_window = bool(last_inbound and last_inbound >= now - SESSION_WINDOW)
    return {
        "open": open_window,
        "last_inbound_at": last_inbound.isoformat() if last_inbound else None,
        "expires_at": (last_inbound + SESSION_WINDOW).isoformat() if last_inbound else None,
    }


def _extension_for_mime(mime_type: str, filename: Optional[str]) -> str:
    mapping = {
        "application/pdf": ".pdf",
        "audio/aac": ".aac",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/ogg": ".ogg",
        "image/jpeg": ".jpg",
        "image/png": ".png",
    }
    if mime_type in mapping:
        return mapping[mime_type]
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ".bin"


def validate_media_upload(*, mime_type: str, size_bytes: int) -> None:
    """Raise MediaValidationError when the file can't be sent — names the limit."""
    if mime_type not in ALLOWED_MIME_TYPES:
        raise MediaValidationError(
            f"Unsupported file type {mime_type or 'unknown'}. Allowed: PDF, JPEG, PNG."
        )
    limit = get_transport().media_limit_bytes(mime_type)
    if size_bytes > limit:
        limit_mb = limit / (1024 * 1024)
        raise MediaValidationError(
            f"File is too large ({size_bytes / (1024 * 1024):.1f} MB). "
            f"The limit for {mime_type} on this channel is {limit_mb:.0f} MB."
        )


def validate_inbound_media(*, mime_type: str, size_bytes: int) -> None:
    normalized_mime = (mime_type or "").strip().lower()
    if normalized_mime not in ALLOWED_INBOUND_MIME_TYPES:
        raise MediaValidationError(
            f"Unsupported inbound media type {mime_type or 'unknown'}."
        )
    limit = media_inbound_max_bytes()
    if size_bytes > limit:
        raise MediaValidationError(
            f"Inbound media is too large ({size_bytes / (1024 * 1024):.1f} MB)."
        )


def store_media_asset(
    db: Session,
    *,
    brokerage_id: str,
    agent_user_id: Optional[str],
    conversation_id: Optional[str],
    listing_id: Optional[str],
    content: bytes,
    mime_type: str,
    original_filename: Optional[str] = None,
    source: str = "composer_upload",
) -> DBMediaAsset:
    """Persist bytes under the brokerage-scoped media dir + a media_assets row."""
    asset = DBMediaAsset(
        brokerage_id=brokerage_id,
        agent_user_id=agent_user_id,
        conversation_id=conversation_id,
        listing_id=listing_id,
        mime_type=mime_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        original_filename=original_filename,
        source=source,
        storage_ref="",  # set below once the asset_id exists
    )
    db.add(asset)
    db.flush()

    extension = _extension_for_mime(mime_type, original_filename)
    relative = Path(brokerage_id) / f"{asset.media_asset_id}{extension}"
    target = media_storage_dir() / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    asset.storage_ref = str(relative)
    safe_commit(db)
    db.refresh(asset)
    return asset


def _provider_media_filename(media_url: str) -> Optional[str]:
    parsed = urlparse(media_url)
    candidate = Path(parsed.path).name if parsed.path else ""
    return candidate[:120] or None


def download_provider_media_bytes(
    media_url: str,
    *,
    auth: Optional[tuple[str, str]] = None,
    max_bytes: Optional[int] = None,
) -> bytes:
    """Download provider media bytes without persisting the provider URL."""
    limit = max_bytes if max_bytes is not None else media_inbound_max_bytes()
    if media_url.startswith("/") or media_url.startswith("file://"):
        path = Path(media_url.removeprefix("file://"))
        size = path.stat().st_size
        if size > limit:
            raise MediaValidationError(
                f"Inbound media is too large ({size / (1024 * 1024):.1f} MB)."
            )
        return path.read_bytes()
    if media_url.startswith("http://") or media_url.startswith("https://"):
        if not auth or not auth[0] or not auth[1]:
            raise MediaValidationError("Provider media auth is required for HTTP(S) downloads.")
    else:
        raise MediaValidationError("Unsupported inbound provider media URL.")
    with httpx.Client(timeout=30) as client:
        with client.stream("GET", media_url, auth=auth) as response:
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    declared_size = int(content_length)
                except ValueError:
                    declared_size = 0
                if declared_size > limit:
                    raise MediaValidationError(
                        f"Inbound media is too large ({declared_size / (1024 * 1024):.1f} MB)."
                    )
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > limit:
                    raise MediaValidationError(
                        f"Inbound media is too large ({total / (1024 * 1024):.1f} MB)."
                    )
                chunks.append(chunk)
            return b"".join(chunks)


def store_inbound_provider_media_asset(
    db: Session,
    *,
    brokerage_id: str,
    media_url: str,
    mime_type: str,
    auth: Optional[tuple[str, str]] = None,
    conversation_id: Optional[str] = None,
    listing_id: Optional[str] = None,
    source: str = "buyer_inbound",
) -> DBMediaAsset:
    """Download provider-hosted inbound media and re-host it as tenant-scoped media."""
    if not brokerage_id:
        raise MediaValidationError("brokerage_id is required to persist inbound media.")
    normalized_mime = (mime_type or "").strip().lower()
    validate_inbound_media(mime_type=normalized_mime, size_bytes=0)
    content = download_provider_media_bytes(
        media_url,
        auth=auth,
        max_bytes=media_inbound_max_bytes(),
    )
    validate_inbound_media(mime_type=normalized_mime, size_bytes=len(content))
    return store_media_asset(
        db,
        brokerage_id=brokerage_id,
        agent_user_id=None,
        conversation_id=conversation_id,
        listing_id=listing_id,
        content=content,
        mime_type=normalized_mime,
        original_filename=_provider_media_filename(media_url),
        source=source,
    )


def cleanup_media_assets(db: Session, assets: list[DBMediaAsset]) -> None:
    """Best-effort cleanup for assets persisted before a failed batch queue."""
    for asset in assets:
        try:
            if asset.storage_ref and not asset.storage_ref.startswith(("http://", "https://")):
                local_media_asset_path(asset).unlink(missing_ok=True)
        except Exception:
            logger.warning("Failed to delete media file during cleanup: %s", asset.media_asset_id, exc_info=True)
        try:
            db.delete(asset)
        except Exception:
            logger.warning("Failed to mark media asset for cleanup: %s", asset.media_asset_id, exc_info=True)
    safe_commit(db)


def inbound_media_asset_metadata(asset: DBMediaAsset, *, content_type: Optional[str]) -> dict:
    return {
        "media_asset_id": asset.media_asset_id,
        "brokerage_id": asset.brokerage_id,
        "content_type": content_type or asset.mime_type,
        "mime_type": asset.mime_type,
        "source": asset.source,
    }


def register_external_media_asset(
    db: Session,
    *,
    brokerage_id: str,
    agent_user_id: Optional[str],
    conversation_id: Optional[str],
    listing_id: Optional[str],
    url: str,
    mime_type: str = "application/octet-stream",
    source: str = "listing_asset",
) -> DBMediaAsset:
    """A media_assets row for an asset already hosted elsewhere (listing media)."""
    asset = DBMediaAsset(
        brokerage_id=brokerage_id,
        agent_user_id=agent_user_id,
        conversation_id=conversation_id,
        listing_id=listing_id,
        mime_type=mime_type,
        size_bytes=0,
        sha256=None,
        original_filename=url.rsplit("/", 1)[-1][:120] or None,
        source=source,
        storage_ref=url,
    )
    db.add(asset)
    safe_commit(db)
    db.refresh(asset)
    return asset


def signed_media_url(asset: DBMediaAsset, *, ttl_seconds: int | None = None) -> str:
    """Short-lived transport-fetchable URL for an asset.

    External refs pass through because those bytes are already hosted by the
    listing/source provider. Local Dalya media is never returned as a static
    public path; callers receive a signed endpoint URL instead.
    """
    if asset.storage_ref.startswith("http://") or asset.storage_ref.startswith("https://"):
        return asset.storage_ref
    ttl = ttl_seconds if ttl_seconds is not None else media_url_ttl_seconds()
    if ttl <= 0:
        raise RuntimeError("media URL TTL must be positive")
    exp = int(time.time()) + ttl
    sig = sign_media_url_payload(
        media_asset_id=asset.media_asset_id,
        brokerage_id=asset.brokerage_id,
        exp=exp,
    )
    base = os.getenv("PUBLIC_URL", "").rstrip("/")
    query = urlencode({"exp": str(exp), "sig": sig})
    return f"{base}/media/{asset.media_asset_id}?{query}"


def public_media_url(asset: DBMediaAsset) -> str:
    """Deprecated alias: returns signed URLs for local Dalya media."""
    return signed_media_url(asset)


def listing_assets_for_attachment(db: Session, listing: DBListing) -> list[dict]:
    """The listing's already-in-system media — the attach-from-listing 80% case."""
    items: list[dict] = []
    for url in list(listing.media_urls or []):
        items.append({"kind": "listing_media", "url": url, "label": url.rsplit("/", 1)[-1][:80]})
    for document in listing.documents or []:
        if document.source_url:
            items.append({
                "kind": "listing_document",
                "url": document.source_url,
                "label": document.label or document.document_type,
            })
    return items


def send_conversation_media(
    db: Session,
    *,
    brokerage: DBBrokerage,
    conversation: DBConversation,
    agent_user_id: Optional[str],
    assets: list[DBMediaAsset],
    caption: str = "",
    source: str = "dashboard_composer",
    routing_method: Optional[str] = None,
    now: Optional[datetime] = None,
    enforce_session_window: bool = True,
) -> MediaSendOutcome:
    """
    Send stored assets to the buyer, one WhatsApp message per file with the
    caption on the first. Persists a single timeline message with file chips
    and a compliance event per media send.
    """
    now = now or datetime.utcnow()
    if not assets:
        raise MediaValidationError("No attachments to send.")
    if len(assets) > MAX_ATTACHMENTS_PER_SEND:
        raise MediaValidationError(
            f"Too many attachments ({len(assets)}). Limit is {MAX_ATTACHMENTS_PER_SEND} per send."
        )

    if enforce_session_window:
        window = session_window_state(db, conversation.conversation_id, now=now)
        if not window["open"]:
            raise SessionWindowClosedError(
                datetime.fromisoformat(window["last_inbound_at"]) if window["last_inbound_at"] else None
            )

    if is_buyer_suppressed(db, brokerage.brokerage_id, conversation.buyer_phone):
        raise MediaValidationError("This buyer has opted out — sends are blocked.")

    transport = get_transport()
    sent_assets: list[dict] = []
    caption = (caption or "").strip()

    for index, asset in enumerate(assets):
        url = signed_media_url(asset)
        body = caption if (index == 0 and caption) else ""
        send_result = transport.send_to_buyer(
            OutboundBuyerMessage(
                brokerage_id=brokerage.brokerage_id,
                brokerage_ai_number=brokerage.brokerage_ai_number,
                buyer_phone=conversation.buyer_phone,
                body=body,
                conversation_id=conversation.conversation_id,
                listing_id=conversation.listing_id,
                media_url=url,
            )
        )
        if not send_result.ok:
            raise MediaValidationError(
                f"Sending {asset.original_filename or asset.media_asset_id} failed: "
                f"{send_result.error or 'transport error'}"
            )
        sent_assets.append({
            "media_asset_id": asset.media_asset_id,
            "url": url,
            "mime_type": asset.mime_type,
            "filename": asset.original_filename,
            "size_bytes": asset.size_bytes,
            "transport_message_id": send_result.transport_message_id,
        })
        record_compliance_event(
            db,
            brokerage_id=brokerage.brokerage_id,
            conversation_id=conversation.conversation_id,
            listing_id=conversation.listing_id,
            buyer_phone=conversation.buyer_phone,
            actor_user_id=agent_user_id,
            event_type="agent_media_sent",
            direction="outbound",
            details={
                "media_asset_id": asset.media_asset_id,
                "mime_type": asset.mime_type,
                "size_bytes": asset.size_bytes,
                "sha256": asset.sha256,
                "storage_ref": asset.storage_ref,
                "caption_preview": caption[:200] if index == 0 else None,
                "source": source,
                # DAL-161: audit trail for routing-method tuning.
                "routing_method": routing_method,
                "transport_message_id": send_result.transport_message_id,
            },
        )

    message = DBMessage(
        conversation_id=conversation.conversation_id,
        role="assistant",
        content=caption or f"[{len(sent_assets)} attachment{'s' if len(sent_assets) != 1 else ''}]",
        intent="agent_media",
        metadata_json={
            "source": source,
            "agent_user_id": agent_user_id,
            "routing_method": routing_method,
            "media": sent_assets,
        },
    )
    db.add(message)
    conversation.updated_at = now
    db.add(DBLeadAction(
        brokerage_id=brokerage.brokerage_id,
        conversation_id=conversation.conversation_id,
        listing_id=conversation.listing_id,
        buyer_phone=conversation.buyer_phone,
        agent_user_id=agent_user_id,
        action_type="agent_media_sent",
        outcome=source,
        note=caption[:500] if caption else f"{len(sent_assets)} attachment(s)",
        payload={"media": sent_assets},
    ))
    safe_commit(db)
    db.refresh(message)
    return MediaSendOutcome(
        message_id=str(message.id),
        sent_assets=sent_assets,
        caption=caption,
    )
