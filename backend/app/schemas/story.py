from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class StoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    raw_text: str = Field(..., min_length=100, max_length=5000)


class StoryUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    raw_text: str | None = Field(None, min_length=100, max_length=5000)


class StoryResponse(BaseModel):
    id: str
    user_id: str
    title: str
    raw_text: str
    word_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StoryListResponse(BaseModel):
    stories: list[StoryResponse]
    total: int
