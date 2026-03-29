"""Asset serving endpoints."""

from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.api.deps import get_db
from app.models.video_asset import VideoAsset

router = APIRouter()


@router.get("/assets/{asset_id}/file")
async def serve_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Serve a generated asset (image or audio) from the database."""
    result = await db.execute(
        select(VideoAsset)
        .where(VideoAsset.id == asset_id)
        .options(undefer(VideoAsset.file_data))
    )
    asset = result.scalar_one_or_none()

    if asset is None or asset.file_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    return StreamingResponse(
        io.BytesIO(asset.file_data),
        media_type=asset.mime_type or "application/octet-stream",
        headers={
            "Content-Length": str(asset.file_size_bytes or len(asset.file_data)),
            "Cache-Control": "max-age=3600, immutable",
        },
    )
