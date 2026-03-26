from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import get_current_user
from app.models.episode import Episode
from app.models.generation_job import GenerationJob
from app.models.scene import Scene
from app.models.story import Story
from app.models.user import User
from app.schemas.episode import (
    EpisodeResponse,
    EpisodeUpdate,
    GenerationJobResponse,
    SceneResponse,
    SceneUpdate,
)

router = APIRouter()


@router.post(
    "/from-story/{story_id}",
    response_model=EpisodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_episode_from_story(
    story_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Episode:
    """Create an episode from a story and kick off scene breakdown."""
    result = await db.execute(
        select(Story).where(Story.id == story_id, Story.user_id == user.id)
    )
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story not found"
        )

    episode = Episode(story_id=story.id, title=story.title)
    db.add(episode)
    await db.flush()

    # Create a generation job
    job = GenerationJob(
        episode_id=episode.id,
        job_type="scene_breakdown",
    )
    db.add(job)

    # Update story status
    story.status = "processing"

    await db.commit()
    await db.refresh(episode)

    # Dispatch Celery task
    from app.tasks.ai import generate_scene_breakdown_task

    generate_scene_breakdown_task.delay(str(episode.id), story.raw_text)

    return episode


@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    episode_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Episode:
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
    return episode


@router.patch("/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    episode_id: str,
    body: EpisodeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Episode:
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

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(episode, field, value)

    await db.commit()
    await db.refresh(episode)
    return episode


@router.get("/{episode_id}/scenes", response_model=list[SceneResponse])
async def list_scenes(
    episode_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Scene]:
    # Verify ownership
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
        select(Scene).where(Scene.episode_id == episode_id).order_by(Scene.scene_order)
    )
    return list(result.scalars().all())


@router.patch("/{episode_id}/scenes/{scene_id}", response_model=SceneResponse)
async def update_scene(
    episode_id: str,
    scene_id: str,
    body: SceneUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Scene:
    # Verify ownership
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
        select(Scene).where(Scene.id == scene_id, Scene.episode_id == episode_id)
    )
    scene = result.scalar_one_or_none()
    if scene is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found"
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(scene, field, value)

    await db.commit()
    await db.refresh(scene)
    return scene


@router.delete(
    "/{episode_id}/scenes/{scene_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_scene(
    episode_id: str,
    scene_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
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
        select(Scene).where(Scene.id == scene_id, Scene.episode_id == episode_id)
    )
    scene = result.scalar_one_or_none()
    if scene is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found"
        )
    await db.delete(scene)
    await db.commit()


@router.get("/{episode_id}/jobs", response_model=list[GenerationJobResponse])
async def list_jobs(
    episode_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GenerationJob]:
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
        .where(GenerationJob.episode_id == episode_id)
        .order_by(GenerationJob.created_at.desc())
    )
    return list(result.scalars().all())
