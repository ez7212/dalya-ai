"""Supabase Storage helper for uploaded listing documents.

Uploads go to the `listing-documents` bucket via the Storage REST API (using the
service-role key) instead of the supabase-py SDK, to avoid pulling in a heavy new
dependency — httpx is already a project dependency.

PDF/plain-text uploads have their text extracted (PyMuPDF for PDFs) so the regular
fact-extraction pipeline can run. Images and other binaries are still stored and
made viewable, but carry no extracted text.
"""
from __future__ import annotations

import os
import unicodedata
import uuid
from dataclasses import dataclass

import httpx

BUCKET = "listing-documents"

# Mirror the /parse-spa limits so the two upload surfaces behave consistently.
# The `listing-documents` bucket restricts MIME types to PDF + images.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
PDF_MIME = "application/pdf"
IMAGE_MIMES = {"image/jpeg", "image/png", "image/jpg"}
ALLOWED_MIMES = {PDF_MIME, *IMAGE_MIMES}


class DocumentStorageError(RuntimeError):
    """Raised when the upload cannot be stored (config or upstream failure)."""


@dataclass
class StoredDocument:
    public_url: str
    storage_path: str
    content_text: str | None


def _supabase_config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise DocumentStorageError(
            "Supabase storage is not configured (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)."
        )
    return url, key


def _safe_filename(name: str) -> str:
    """ASCII-fold and strip a filename to a storage-safe slug, preserving extension."""
    cleaned = unicodedata.normalize("NFKD", name or "document").encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in cleaned).strip("-._")
    return cleaned[:80] or "document"


def extract_text(content: bytes, content_type: str) -> str | None:
    """Extract text for fact-extraction. PDFs via PyMuPDF, text/* decoded directly.
    Images and unknown types return None (stored but not text-mined)."""
    if content_type == PDF_MIME:
        import fitz  # PyMuPDF — already a dependency, used by the SPA parser

        doc = fitz.open(stream=content, filetype="pdf")
        try:
            text = "".join(page.get_text("text") + "\n" for page in doc)
        finally:
            doc.close()
        return text.strip() or None
    # Images are stored and viewable but carry no machine-extracted text.
    return None


def upload_listing_document(
    *, listing_id: str, content: bytes, content_type: str, filename: str
) -> StoredDocument:
    """Upload bytes to the bucket and return the public URL + extracted text.

    The object path is namespaced by listing so a listing's files are grouped.
    The bucket is expected to be public-read; we return the public object URL.
    """
    if content_type not in ALLOWED_MIMES:
        raise DocumentStorageError(
            f"Unsupported file type {content_type!r}. Allowed: PDF, JPEG, PNG, or plain text."
        )
    if len(content) > MAX_UPLOAD_BYTES:
        raise DocumentStorageError("File exceeds the 20 MB upload limit.")
    if not content:
        raise DocumentStorageError("Uploaded file is empty.")

    base_url, key = _supabase_config()
    storage_path = f"{listing_id}/{uuid.uuid4().hex}-{_safe_filename(filename)}"
    endpoint = f"{base_url}/storage/v1/object/{BUCKET}/{storage_path}"

    try:
        response = httpx.post(
            endpoint,
            content=content,
            headers={
                # New-style sb_secret_ keys require the apikey header; the bearer
                # alone is parsed as a JWT and rejected ("Invalid Compact JWS").
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": content_type,
                "x-upsert": "true",
                "cache-control": "3600",
            },
            timeout=30.0,
        )
    except httpx.HTTPError as exc:  # network/timeout
        raise DocumentStorageError(f"Could not reach storage: {exc}") from exc

    if response.status_code >= 300:
        raise DocumentStorageError(
            f"Storage upload failed ({response.status_code}): {response.text[:200]}"
        )

    public_url = f"{base_url}/storage/v1/object/public/{BUCKET}/{storage_path}"
    return StoredDocument(
        public_url=public_url,
        storage_path=storage_path,
        content_text=extract_text(content, content_type),
    )
