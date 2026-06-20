from __future__ import annotations

import time
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.media_assets import (
    MediaValidationError,
    local_media_asset_path,
    media_signature_is_valid,
)
from app.db.session import get_db
from app.models.db_models import DBMediaAsset


router = APIRouter()


@router.get("/media/{media_asset_id}")
def get_signed_media(
    media_asset_id: str,
    exp: int | None = Query(default=None),
    sig: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if exp is None or not sig:
        raise HTTPException(status_code=403, detail="media_signature_required")

    if exp < int(time.time()):
        raise HTTPException(status_code=403, detail="media_signature_expired")

    asset = db.get(DBMediaAsset, media_asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="media_not_found")

    if asset.storage_ref.startswith("http://") or asset.storage_ref.startswith("https://"):
        raise HTTPException(status_code=404, detail="media_not_found")

    if not media_signature_is_valid(
        media_asset_id=asset.media_asset_id,
        brokerage_id=asset.brokerage_id,
        exp=exp,
        sig=sig,
    ):
        raise HTTPException(status_code=403, detail="media_signature_forbidden")

    try:
        path = local_media_asset_path(asset)
    except MediaValidationError:
        raise HTTPException(status_code=404, detail="media_not_found")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="media_not_found")

    return FileResponse(
        path,
        media_type=asset.mime_type,
        filename=asset.original_filename or path.name,
    )
