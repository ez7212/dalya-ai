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
import secrets
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
    DBComplianceEvent,
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
_MEDIA_LIFECYCLE_METADATA_KEY = "lifecycle"
_REDACTED_FILENAME = "[redacted]"


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


def generate_media_signing_nonce() -> str:
    return secrets.token_urlsafe(24)


def media_asset_signing_nonce(asset: DBMediaAsset) -> str:
    nonce = (getattr(asset, "signing_nonce", None) or "").strip()
    if not nonce:
        raise MediaValidationError("Media asset signing nonce is missing.")
    return nonce


def media_asset_is_revoked_or_deleted(asset: DBMediaAsset) -> bool:
    return bool(getattr(asset, "revoked_at", None) or getattr(asset, "deleted_at", None))


def ensure_media_asset_accessible(asset: DBMediaAsset) -> None:
    if getattr(asset, "deleted_at", None):
        raise MediaValidationError("Media asset has been deleted.")
    if getattr(asset, "revoked_at", None):
        raise MediaValidationError("Media asset has been revoked.")


def media_signature_payload(
    *,
    media_asset_id: str,
    brokerage_id: str,
    exp: int,
    signing_nonce: str,
) -> str:
    return f"{media_asset_id}.{brokerage_id}.{exp}.{signing_nonce}"


def sign_media_url_payload(
    *,
    media_asset_id: str,
    brokerage_id: str,
    exp: int,
    signing_nonce: str,
) -> str:
    return hmac.new(
        media_url_signing_secret().encode("utf-8"),
        media_signature_payload(
            media_asset_id=media_asset_id,
            brokerage_id=brokerage_id,
            exp=exp,
            signing_nonce=signing_nonce,
        ).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def media_signature_is_valid(
    *,
    media_asset_id: str,
    brokerage_id: str,
    exp: int,
    sig: str,
    signing_nonce: str,
) -> bool:
    expected = sign_media_url_payload(
        media_asset_id=media_asset_id,
        brokerage_id=brokerage_id,
        exp=exp,
        signing_nonce=signing_nonce,
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
        signing_nonce=generate_media_signing_nonce(),
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
        signing_nonce=generate_media_signing_nonce(),
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
    ensure_media_asset_accessible(asset)
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
        signing_nonce=media_asset_signing_nonce(asset),
    )
    base = os.getenv("PUBLIC_URL", "").rstrip("/")
    query = urlencode({"exp": str(exp), "sig": sig})
    return f"{base}/media/{asset.media_asset_id}?{query}"


def public_media_url(asset: DBMediaAsset) -> str:
    """Deprecated alias: returns signed URLs for local Dalya media."""
    return signed_media_url(asset)


def _lifecycle_metadata(
    asset: DBMediaAsset,
    *,
    action: str,
    reason: Optional[str],
    actor_user_id: Optional[str],
    at: datetime,
) -> dict:
    metadata = dict(asset.metadata_json or {})
    lifecycle = dict(metadata.get(_MEDIA_LIFECYCLE_METADATA_KEY) or {})
    history = list(lifecycle.get("history") or [])
    event = {
        "action": action,
        "at": at.isoformat(),
    }
    if reason:
        event["reason"] = reason
    if actor_user_id:
        event["actor_user_id"] = actor_user_id
    history.append(event)
    lifecycle.update(
        {
            "last_action": action,
            "last_action_at": at.isoformat(),
            "history": history[-20:],
        }
    )
    if reason:
        lifecycle["last_reason"] = reason
    metadata[_MEDIA_LIFECYCLE_METADATA_KEY] = lifecycle
    return metadata


def rotate_media_signing_nonce(
    db: Session,
    asset: DBMediaAsset,
    *,
    reason: Optional[str] = None,
    actor_user_id: Optional[str] = None,
) -> DBMediaAsset:
    now = datetime.utcnow()
    asset.signing_nonce = generate_media_signing_nonce()
    asset.metadata_json = _lifecycle_metadata(
        asset,
        action="signing_nonce_rotated",
        reason=reason,
        actor_user_id=actor_user_id,
        at=now,
    )
    safe_commit(db)
    db.refresh(asset)
    return asset


def revoke_media_asset(
    db: Session,
    asset: DBMediaAsset,
    *,
    reason: Optional[str] = None,
    actor_user_id: Optional[str] = None,
) -> DBMediaAsset:
    now = datetime.utcnow()
    asset.revoked_at = asset.revoked_at or now
    asset.signing_nonce = generate_media_signing_nonce()
    asset.metadata_json = _lifecycle_metadata(
        asset,
        action="revoked",
        reason=reason,
        actor_user_id=actor_user_id,
        at=now,
    )
    safe_commit(db)
    db.refresh(asset)
    return asset


def soft_delete_media_asset(
    db: Session,
    asset: DBMediaAsset,
    *,
    reason: Optional[str] = None,
    actor_user_id: Optional[str] = None,
) -> DBMediaAsset:
    now = datetime.utcnow()
    asset.revoked_at = asset.revoked_at or now
    asset.deleted_at = asset.deleted_at or now
    asset.signing_nonce = generate_media_signing_nonce()
    asset.metadata_json = _lifecycle_metadata(
        asset,
        action="soft_deleted",
        reason=reason,
        actor_user_id=actor_user_id,
        at=now,
    )
    safe_commit(db)
    db.refresh(asset)
    return asset


def delete_local_media_file(asset: DBMediaAsset) -> bool:
    """Delete local media bytes without allowing path traversal."""
    if asset.storage_ref.startswith(("http://", "https://")):
        return False
    path = local_media_asset_path(asset)
    if not path.exists():
        return False
    path.unlink()
    return True


def delete_media_asset_bytes(
    db: Session,
    asset: DBMediaAsset,
    *,
    reason: Optional[str] = None,
    actor_user_id: Optional[str] = None,
) -> DBMediaAsset:
    """Revoke, remove local bytes, and mark the asset deleted."""
    now = datetime.utcnow()
    asset.revoked_at = asset.revoked_at or now
    asset.signing_nonce = generate_media_signing_nonce()
    bytes_deleted = False
    try:
        bytes_deleted = delete_local_media_file(asset)
    except FileNotFoundError:
        bytes_deleted = False
    asset.deleted_at = asset.deleted_at or datetime.utcnow()
    metadata = _lifecycle_metadata(
        asset,
        action="bytes_deleted",
        reason=reason,
        actor_user_id=actor_user_id,
        at=datetime.utcnow(),
    )
    metadata[_MEDIA_LIFECYCLE_METADATA_KEY]["bytes_deleted"] = bytes_deleted
    metadata[_MEDIA_LIFECYCLE_METADATA_KEY]["bytes_deleted_at"] = asset.deleted_at.isoformat()
    asset.metadata_json = metadata
    safe_commit(db)
    db.refresh(asset)
    return asset


def media_asset_ids_from_metadata(metadata: Optional[dict]) -> set[str]:
    """Extract durable media asset references without reading provider URLs."""
    if not isinstance(metadata, dict):
        return set()

    media_asset_ids: set[str] = set()
    for item in list(metadata.get("inbound_media_assets") or []):
        if isinstance(item, dict) and item.get("media_asset_id"):
            media_asset_ids.add(str(item["media_asset_id"]))

    voice_note = metadata.get("voice_note")
    if isinstance(voice_note, dict) and voice_note.get("media_asset_id"):
        media_asset_ids.add(str(voice_note["media_asset_id"]))

    for item in list(metadata.get("media") or []):
        if isinstance(item, dict) and item.get("media_asset_id"):
            media_asset_ids.add(str(item["media_asset_id"]))

    if metadata.get("media_asset_id"):
        media_asset_ids.add(str(metadata["media_asset_id"]))

    return media_asset_ids


def redact_media_metadata(metadata: Optional[dict], *, media_asset_ids: set[str]) -> dict:
    """Redact provider/filename detail while preserving safe asset references."""
    if not isinstance(metadata, dict):
        return {}

    redacted = dict(metadata)
    inbound_assets = []
    for item in list(redacted.get("inbound_media_assets") or []):
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        if str(next_item.get("media_asset_id") or "") in media_asset_ids:
            next_item.pop("provider_url", None)
            next_item.pop("url", None)
            next_item.pop("source_url", None)
            next_item["filename"] = _REDACTED_FILENAME
            next_item["redacted"] = True
        inbound_assets.append(next_item)
    if inbound_assets:
        redacted["inbound_media_assets"] = inbound_assets

    voice_note = redacted.get("voice_note")
    if isinstance(voice_note, dict) and str(voice_note.get("media_asset_id") or "") in media_asset_ids:
        next_voice = dict(voice_note)
        next_voice.pop("audio_url", None)
        next_voice["redacted"] = True
        redacted["voice_note"] = next_voice

    media_items = []
    for item in list(redacted.get("media") or []):
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        if str(next_item.get("media_asset_id") or "") in media_asset_ids:
            next_item.pop("url", None)
            next_item["filename"] = _REDACTED_FILENAME
            next_item["redacted"] = True
        media_items.append(next_item)
    if media_items:
        redacted["media"] = media_items

    return redacted


def redact_media_asset_record(
    db: Session,
    asset: DBMediaAsset,
    *,
    reason: str,
    actor_user_id: Optional[str] = None,
) -> DBMediaAsset:
    metadata = dict(asset.metadata_json or {})
    lifecycle = dict(metadata.get(_MEDIA_LIFECYCLE_METADATA_KEY) or {})
    lifecycle["metadata_redacted_at"] = datetime.utcnow().isoformat()
    lifecycle["metadata_redacted_reason"] = reason
    if actor_user_id:
        lifecycle["metadata_redacted_by_user_id"] = actor_user_id
    metadata[_MEDIA_LIFECYCLE_METADATA_KEY] = lifecycle
    asset.metadata_json = metadata
    asset.original_filename = _REDACTED_FILENAME
    safe_commit(db)
    db.refresh(asset)
    return asset


def media_asset_ids_for_buyer_deletion(
    db: Session,
    *,
    brokerage_id: str,
    buyer_phone: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> set[str]:
    """Find media referenced by tenant-scoped buyer messages and durable metadata."""
    if not brokerage_id:
        return set()

    conversations = db.query(DBConversation).filter(DBConversation.brokerage_id == brokerage_id)
    if conversation_id:
        conversations = conversations.filter(DBConversation.conversation_id == conversation_id)
    if buyer_phone:
        conversations = conversations.filter(DBConversation.buyer_phone == buyer_phone)
    conversation_ids = [row.conversation_id for row in conversations.all()]
    if not conversation_ids:
        return set()

    media_asset_ids: set[str] = set()
    messages = db.query(DBMessage).filter(DBMessage.conversation_id.in_(conversation_ids)).all()
    for message in messages:
        media_asset_ids.update(media_asset_ids_from_metadata(message.metadata_json or {}))

    direct_assets = (
        db.query(DBMediaAsset.media_asset_id)
        .filter(
            DBMediaAsset.brokerage_id == brokerage_id,
            DBMediaAsset.conversation_id.in_(conversation_ids),
        )
        .all()
    )
    media_asset_ids.update(str(row.media_asset_id) for row in direct_assets)
    return media_asset_ids


def delete_media_for_buyer_request(
    db: Session,
    *,
    brokerage_id: str,
    buyer_phone: Optional[str] = None,
    conversation_id: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    reason: str = "pdpl_media_deletion",
) -> dict:
    """Revoke/delete buyer-linked media bytes and redact durable metadata.

    This helper is intentionally tenant-scoped. It does not infer a brokerage
    from global phone state and does not inspect raw provider URLs.
    """
    if not brokerage_id:
        raise MediaValidationError("brokerage_id is required for media deletion.")
    if not buyer_phone and not conversation_id:
        raise MediaValidationError("buyer_phone or conversation_id is required for media deletion.")

    media_asset_ids = media_asset_ids_for_buyer_deletion(
        db,
        brokerage_id=brokerage_id,
        buyer_phone=buyer_phone,
        conversation_id=conversation_id,
    )
    deleted_ids: list[str] = []
    skipped_ids: list[str] = []

    for media_asset_id in sorted(media_asset_ids):
        asset = db.get(DBMediaAsset, media_asset_id)
        if not asset or asset.brokerage_id != brokerage_id:
            skipped_ids.append(media_asset_id)
            continue
        revoke_media_asset(db, asset, reason=reason, actor_user_id=actor_user_id)
        delete_media_asset_bytes(db, asset, reason=reason, actor_user_id=actor_user_id)
        redact_media_asset_record(db, asset, reason=reason, actor_user_id=actor_user_id)
        deleted_ids.append(media_asset_id)

    if deleted_ids:
        conversations = db.query(DBConversation).filter(DBConversation.brokerage_id == brokerage_id)
        if conversation_id:
            conversations = conversations.filter(DBConversation.conversation_id == conversation_id)
        if buyer_phone:
            conversations = conversations.filter(DBConversation.buyer_phone == buyer_phone)
        conversation_ids = [row.conversation_id for row in conversations.all()]
        messages = db.query(DBMessage).filter(DBMessage.conversation_id.in_(conversation_ids)).all()
        deleted_id_set = set(deleted_ids)
        for message in messages:
            if media_asset_ids_from_metadata(message.metadata_json or {}).intersection(deleted_id_set):
                message.metadata_json = redact_media_metadata(
                    message.metadata_json or {},
                    media_asset_ids=deleted_id_set,
                )
        db.add(DBComplianceEvent(
            brokerage_id=brokerage_id,
            conversation_id=conversation_id,
            buyer_phone=None,
            actor_user_id=actor_user_id,
            event_type="pdpl_media_deleted",
            direction="system",
            details={
                "media_asset_count": len(deleted_ids),
                "media_asset_ids": deleted_ids,
                "reason": reason,
                "scope": "conversation" if conversation_id else "buyer",
            },
        ))
        safe_commit(db)

    return {
        "deleted_media_asset_ids": deleted_ids,
        "skipped_media_asset_ids": skipped_ids,
        "media_asset_count": len(deleted_ids),
    }


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
