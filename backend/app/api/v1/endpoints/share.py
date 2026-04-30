"""Shareable preview link endpoints."""

from __future__ import annotations

import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.api.deps import get_db
from app.core.auth import get_current_user
from app.models.episode import Episode
from app.models.scene import Scene
from app.models.share_token import ShareToken
from app.models.story import Story
from app.models.user import User
from app.models.video_asset import VideoAsset

router = APIRouter()


# --- Schemas ---


class ShareTokenResponse(BaseModel):
    token: str
    share_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SharedAssetInfo(BaseModel):
    id: UUID
    asset_type: str
    mime_type: str | None
    url: str


class SharedScene(BaseModel):
    id: UUID
    scene_order: int
    beat_label: str
    visual_description: str
    narration_text: str | None
    duration_sec: float | None
    assets: list[SharedAssetInfo]


class AttributionInfo(BaseModel):
    channel: str | None = None
    video_title: str | None = None
    youtube_url: str | None = None


class SharedPreviewResponse(BaseModel):
    title: str | None
    target_duration_sec: int
    scenes: list[SharedScene]
    attribution: AttributionInfo | None = None
    final_video_size_bytes: int | None = None
    final_video_mime_type: str | None = None


# --- Authenticated: create/manage share links ---


@router.post(
    "/episodes/{episode_id}/share",
    response_model=ShareTokenResponse,
)
async def create_share_link(
    episode_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareTokenResponse:
    """Create a shareable preview link for an episode."""
    # Verify ownership
    result = await db.execute(
        select(Episode).join(Story).where(Episode.id == episode_id, Story.user_id == user.id)
    )
    episode = result.scalar_one_or_none()
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")

    # Reuse existing token if one exists
    existing = await db.execute(
        select(ShareToken).where(ShareToken.episode_id == episode_id)
    )
    share_token = existing.scalar_one_or_none()

    if share_token is None:
        share_token = ShareToken(episode_id=episode.id)
        db.add(share_token)
        await db.commit()
        await db.refresh(share_token)

    return ShareTokenResponse(
        token=share_token.token,
        share_url=f"/share/{share_token.token}",
        created_at=share_token.created_at,
    )


# --- Public: view shared preview (no auth) ---


@router.get(
    "/shared/{token}",
    response_model=SharedPreviewResponse,
)
async def get_shared_preview(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> SharedPreviewResponse:
    """Get preview data for a shared episode. No authentication required."""
    result = await db.execute(
        select(ShareToken).where(ShareToken.token == token)
    )
    share_token = result.scalar_one_or_none()

    if share_token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")

    # Check expiry
    if share_token.expires_at and share_token.expires_at < datetime.now(share_token.expires_at.tzinfo):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link has expired")

    # Load episode
    ep_result = await db.execute(
        select(Episode).where(Episode.id == share_token.episode_id)
    )
    episode = ep_result.scalar_one_or_none()
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")

    # Load scenes with assets
    scenes_result = await db.execute(
        select(Scene)
        .where(Scene.episode_id == episode.id)
        .order_by(Scene.scene_order)
    )
    scenes = list(scenes_result.scalars().all())

    shared_scenes: list[SharedScene] = []
    for scene in scenes:
        assets_result = await db.execute(
            select(VideoAsset)
            .where(
                VideoAsset.scene_id == scene.id,
                VideoAsset.is_active.is_(True),
                VideoAsset.file_data.isnot(None),
            )
            .order_by(VideoAsset.created_at.desc())
        )
        assets = list(assets_result.scalars().all())

        seen_types: set[str] = set()
        asset_infos: list[SharedAssetInfo] = []
        for asset in assets:
            if asset.asset_type not in seen_types:
                seen_types.add(asset.asset_type)
                asset_infos.append(
                    SharedAssetInfo(
                        id=asset.id,
                        asset_type=asset.asset_type,
                        mime_type=asset.mime_type,
                        url=f"/api/v1/assets/{asset.id}/file",
                    )
                )

        shared_scenes.append(
            SharedScene(
                id=scene.id,
                scene_order=scene.scene_order,
                beat_label=scene.beat_label,
                visual_description=scene.visual_description,
                narration_text=scene.narration_text,
                duration_sec=scene.duration_sec,
                assets=asset_infos,
            )
        )

    # Check if this episode comes from a YouTube source
    attribution = None
    story_result = await db.execute(
        select(Story).where(Story.id == episode.story_id)
    )
    story = story_result.scalar_one_or_none()
    if story and story.source_type == "youtube" and story.source_meta:
        attribution = AttributionInfo(
            channel=story.source_meta.get("channel"),
            video_title=story.source_meta.get("video_title"),
            youtube_url=story.source_meta.get("youtube_url"),
        )

    return SharedPreviewResponse(
        title=episode.title,
        target_duration_sec=episode.target_duration_sec,
        scenes=shared_scenes,
        attribution=attribution,
        final_video_size_bytes=episode.final_video_size_bytes,
        final_video_mime_type=episode.final_video_mime_type,
    )


@router.get("/shared/{token}/video")
async def get_shared_video(
    token: str,
    inline: bool = Query(default=True, description="Content-Disposition: inline (default) for in-browser <video>, attachment to force download"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream the final rendered MP4 for a shared episode. No authentication —
    the share token is the credential. Mirrors /episodes/{id}/download/video
    but accepts a share token instead of a Clerk JWT."""
    result = await db.execute(
        select(ShareToken).where(ShareToken.token == token)
    )
    share_token = result.scalar_one_or_none()
    if share_token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    if share_token.expires_at and share_token.expires_at < datetime.now(share_token.expires_at.tzinfo):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link has expired")

    ep_result = await db.execute(
        select(Episode)
        .where(Episode.id == share_token.episode_id)
        .options(undefer(Episode.final_video_data))
    )
    episode = ep_result.scalar_one_or_none()
    if episode is None or not episode.final_video_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rendered video available for this share link",
        )

    title_slug = (episode.title or "video").lower().replace(" ", "-")[:30]
    disposition = "inline" if inline else "attachment"
    return StreamingResponse(
        io.BytesIO(episode.final_video_data),
        media_type=episode.final_video_mime_type or "video/mp4",
        headers={
            "Content-Length": str(episode.final_video_size_bytes or len(episode.final_video_data)),
            "Content-Disposition": f'{disposition}; filename="{title_slug}.mp4"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=300",
        },
    )
