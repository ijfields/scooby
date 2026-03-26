"""Export & download API endpoints."""

from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import get_current_user
from app.models.episode import Episode
from app.models.scene import Scene
from app.models.story import Story
from app.models.user import User

router = APIRouter()


@router.get("/episodes/{episode_id}/download/video")
async def download_video(
    episode_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get download info for the final rendered video."""
    result = await db.execute(
        select(Episode)
        .join(Story)
        .where(Episode.id == episode_id, Story.user_id == user.id)
    )
    episode = result.scalar_one_or_none()
    if episode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found"
        )

    if not episode.final_video_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rendered video available",
        )

    title_slug = (episode.title or "video").lower().replace(" ", "-")[:30]

    return {
        "download_url": episode.final_video_url,
        "filename": f"{title_slug}.mp4",
        "duration_sec": episode.final_video_duration_sec,
        "resolution": "1080x1920",
    }


@router.get("/episodes/{episode_id}/download/script")
async def download_script(
    episode_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Generate and download the episode script as a text document."""
    result = await db.execute(
        select(Episode)
        .join(Story)
        .where(Episode.id == episode_id, Story.user_id == user.id)
    )
    episode = result.scalar_one_or_none()
    if episode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found"
        )

    scenes_result = await db.execute(
        select(Scene).where(Scene.episode_id == episode_id).order_by(Scene.scene_order)
    )
    scenes = list(scenes_result.scalars().all())

    # Build plain text script (PDF generation would require extra deps)
    lines: list[str] = []
    lines.append(f"SCRIPT: {episode.title or 'Untitled'}")
    lines.append("=" * 50)
    lines.append("")

    total_duration = 0.0
    for scene in scenes:
        dur = float(scene.duration_sec or 0)
        total_duration += dur
        lines.append(f"SCENE {scene.scene_order}: {scene.beat_label.upper()}")
        lines.append(f"Duration: {dur:.1f}s")
        lines.append("")
        lines.append(f"  Visual: {scene.visual_description}")
        lines.append("")
        if scene.narration_text:
            lines.append(f"  Narration: {scene.narration_text}")
            lines.append("")
        if scene.dialogue_text:
            lines.append(f"  Dialogue: {scene.dialogue_text}")
            lines.append("")
        lines.append("-" * 50)
        lines.append("")

    lines.append(f"Total Duration: {total_duration:.1f}s")
    lines.append(f"Total Scenes: {len(scenes)}")

    content = "\n".join(lines)
    title_slug = (episode.title or "script").lower().replace(" ", "-")[:30]

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{title_slug}-script.txt"'
        },
    )
