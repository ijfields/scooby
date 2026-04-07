"""YouTube import API endpoints.

Three-endpoint staged flow:
1. POST /youtube/import — accept URL, kick off transcript fetch + series planning
2. GET  /youtube/{story_id}/plan — return series plan for user review
3. POST /youtube/{story_id}/approve — approve plan, create episodes, run breakdowns
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import get_current_user
from app.models.story import Story
from app.models.user import User
from app.schemas.series_plan import SeriesApproveRequest, SeriesPlan, SeriesPlanResponse
from app.schemas.story import StoryCreateFromYouTube, StoryResponse

router = APIRouter()


@router.post("/import", response_model=StoryResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_youtube(
    body: StoryCreateFromYouTube,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Story:
    """Import a YouTube video and start transcript fetch + series planning.

    Creates a Story with source_type="youtube" and dispatches an async
    Celery task to fetch the transcript and plan the series.
    """
    if not body.fair_use_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fair use acknowledgment is required",
        )

    # Create placeholder Story
    story = Story(
        user_id=user.id,
        title="Importing...",
        raw_text="Transcript will be fetched from YouTube.",
        word_count=0,
        status="importing",
        source_type="youtube",
        source_url=body.youtube_url,
        source_meta={
            "relationship": body.relationship,
        },
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)

    # Dispatch async task
    from app.tasks.youtube import fetch_and_plan_task

    fetch_and_plan_task.delay(
        str(story.id),
        body.youtube_url,
        body.relationship,
    )

    return story


@router.get("/{story_id}/plan", response_model=SeriesPlanResponse)
async def get_series_plan(
    story_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the series plan for a YouTube-imported story.

    Returns the plan if ready, or current status if still processing.
    """
    result = await db.execute(
        select(Story).where(Story.id == story_id, Story.user_id == user.id)
    )
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.source_type != "youtube":
        raise HTTPException(
            status_code=400,
            detail="This story was not imported from YouTube",
        )

    plan = None
    if story.source_meta and "series_plan" in story.source_meta:
        plan = SeriesPlan.model_validate(story.source_meta["series_plan"])

    return {
        "story_id": str(story.id),
        "status": story.status,
        "plan": plan,
    }


@router.post("/{story_id}/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve_series(
    story_id: str,
    body: SeriesApproveRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve the series plan and start episode generation.

    Optionally pass episode edits (title/angle overrides, removals).
    Creates Episode rows and dispatches scene breakdown tasks.
    """
    result = await db.execute(
        select(Story).where(Story.id == story_id, Story.user_id == user.id)
    )
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status != "plan_ready":
        raise HTTPException(
            status_code=400,
            detail=f"Story status is '{story.status}', expected 'plan_ready'",
        )

    from app.tasks.youtube import approve_series_task

    approved_episodes = None
    if body and body.episodes:
        approved_episodes = [ep.model_dump() for ep in body.episodes]

    approve_series_task.delay(str(story.id), approved_episodes)

    return {
        "message": "Series approved. Episode generation started.",
        "story_id": str(story.id),
    }
