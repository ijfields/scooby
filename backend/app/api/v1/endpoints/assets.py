"""Asset serving endpoints."""

from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.api.deps import get_db
from app.models.scene import Scene
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


@router.get("/episodes/{episode_id}/gallery", response_class=HTMLResponse)
async def episode_gallery(
    episode_id: str,
    db: AsyncSession = Depends(get_db),
) -> str:
    """HTML gallery page showing all generated assets for an episode."""
    scenes = list(
        (
            await db.execute(
                select(Scene)
                .where(Scene.episode_id == episode_id)
                .order_by(Scene.scene_order)
            )
        )
        .scalars()
        .all()
    )

    if not scenes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")

    cards_html = ""
    for scene in scenes:
        assets = list(
            (
                await db.execute(
                    select(VideoAsset)
                    .where(
                        VideoAsset.scene_id == scene.id,
                        VideoAsset.is_active.is_(True),
                        VideoAsset.file_data.isnot(None),
                    )
                    .order_by(VideoAsset.created_at.desc())
                )
            )
            .scalars()
            .all()
        )

        image = next((a for a in assets if a.asset_type == "image"), None)
        audio = next((a for a in assets if a.asset_type == "voiceover"), None)

        img_tag = ""
        if image:
            img_tag = f'<img src="/api/v1/assets/{image.id}/file" alt="Scene {scene.scene_order}" style="width:100%;border-radius:8px;">'

        audio_tag = ""
        if audio:
            audio_tag = f'<audio controls style="width:100%;margin-top:8px;"><source src="/api/v1/assets/{audio.id}/file" type="audio/mpeg"></audio>'

        narration = scene.narration_text or ""
        cards_html += f"""
        <div style="background:#1a1a2e;border-radius:12px;padding:16px;margin-bottom:20px;">
            <h3 style="color:#e0e0ff;margin:0 0 4px;">Scene {scene.scene_order}: {scene.beat_label or ''}</h3>
            <p style="color:#888;font-size:13px;margin:0 0 12px;font-style:italic;">{narration[:200]}</p>
            {img_tag}
            {audio_tag}
        </div>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Episode Gallery</title>
</head>
<body style="background:#0f0f23;color:#fff;font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:500px;margin:0 auto;padding:20px;">
    <h1 style="text-align:center;color:#e0e0ff;">Episode Gallery</h1>
    <p style="text-align:center;color:#888;">Generated scenes with AI images and narration</p>
    {cards_html}
    <p style="text-align:center;color:#555;font-size:12px;margin-top:30px;">Scooby — Canva for Stories</p>
</body>
</html>"""
    return html
