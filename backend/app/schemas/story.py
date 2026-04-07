from __future__ import annotations

from datetime import datetime
from uuid import UUID

from typing import Any

from pydantic import BaseModel, Field


class StoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    raw_text: str = Field(..., min_length=100, max_length=5000)


class StoryCreateFromYouTube(BaseModel):
    youtube_url: str = Field(..., pattern=r"(youtube\.com|youtu\.be)")
    relationship: str = Field(
        ...,
        description="User's relationship to the content",
        pattern=r"^(creator|permission|fair_use)$",
    )
    fair_use_acknowledged: bool = Field(
        ...,
        description="User confirms they have the right to create derivative content",
    )


class StoryUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    raw_text: str | None = Field(None, min_length=100, max_length=5000)


class StoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    raw_text: str
    word_count: int
    status: str
    source_type: str
    source_url: str | None
    source_meta: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StoryListResponse(BaseModel):
    stories: list[StoryResponse]
    total: int
