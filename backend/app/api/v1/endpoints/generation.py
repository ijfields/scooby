"""Video generation pipeline API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import get_current_user
from app.models.episode import Episode
from app.models.generation_job import GenerationJob
from app.models.story import Story
from app.models.user import User
from app.schemas.episode import GenerationJobResponse

router = APIRouter()


@router.post(
    "/episodes/{episode_id}/generate",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_generation(
    episode_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationJob:
    """Trigger the full video generation pipeline for an episode."""
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

    if episode.status == "generating":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Generation already in progress",
        )

    if not episode.visual_style_id or not episode.voice_style_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visual and voice styles must be selected before generating",
        )

    episode.status = "generating"

    job = GenerationJob(
        episode_id=episode.id,
        job_type="full_pipeline",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from app.tasks.pipeline import run_full_pipeline_task

    run_full_pipeline_task.delay(str(episode.id))

    return job


@router.get(
    "/episodes/{episode_id}/generate/status",
    response_model=GenerationJobResponse | None,
)
async def get_generation_status(
    episode_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationJob | None:
    """Get the latest generation job status for an episode."""
    ep_result = await db.execute(
        select(Episode)
        .join(Story)
        .where(Episode.id == episode_id, Story.user_id == user.id)
    )
    if ep_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found"
        )

    result = await db.execute(
        select(GenerationJob)
        .where(
            GenerationJob.episode_id == episode_id,
            GenerationJob.job_type == "full_pipeline",
        )
        .order_by(GenerationJob.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
