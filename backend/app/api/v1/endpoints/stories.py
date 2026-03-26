from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import get_current_user
from app.models.story import Story
from app.models.user import User
from app.schemas.story import StoryCreate, StoryListResponse, StoryResponse, StoryUpdate

router = APIRouter()


@router.post("/", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    body: StoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Story:
    word_count = len(body.raw_text.split())
    story = Story(
        user_id=user.id,
        title=body.title,
        raw_text=body.raw_text,
        word_count=word_count,
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)
    return story


@router.get("/", response_model=StoryListResponse)
async def list_stories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    count_result = await db.execute(
        select(func.count()).select_from(Story).where(Story.user_id == user.id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Story)
        .where(Story.user_id == user.id)
        .order_by(Story.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    stories = result.scalars().all()
    return {"stories": stories, "total": total}


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Story:
    result = await db.execute(
        select(Story).where(Story.id == story_id, Story.user_id == user.id)
    )
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story not found"
        )
    return story


@router.patch("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: str,
    body: StoryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Story:
    result = await db.execute(
        select(Story).where(Story.id == story_id, Story.user_id == user.id)
    )
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story not found"
        )

    if body.title is not None:
        story.title = body.title
    if body.raw_text is not None:
        story.raw_text = body.raw_text
        story.word_count = len(body.raw_text.split())

    await db.commit()
    await db.refresh(story)
    return story


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(
    story_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Story).where(Story.id == story_id, Story.user_id == user.id)
    )
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story not found"
        )
    await db.delete(story)
    await db.commit()
