from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EpisodeResponse(BaseModel):
    id: str
    story_id: str
    title: str | None
    target_duration_sec: int
    status: str
    visual_style_id: str | None
    voice_style_id: str | None
    music_style_id: str | None
    final_video_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EpisodeUpdate(BaseModel):
    title: str | None = None
    target_duration_sec: int | None = None
    visual_style_id: str | None = None
    voice_style_id: str | None = None
    music_style_id: str | None = None


class SceneResponse(BaseModel):
    id: str
    episode_id: str
    scene_order: int
    beat_label: str
    visual_description: str
    narration_text: str | None
    dialogue_text: str | None
    duration_sec: float | None
    image_prompt: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SceneUpdate(BaseModel):
    visual_description: str | None = None
    narration_text: str | None = None
    dialogue_text: str | None = None
    duration_sec: float | None = None
    scene_order: int | None = None


class GenerationJobResponse(BaseModel):
    id: str
    episode_id: str
    job_type: str
    status: str
    progress: float | None
    stage: str | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
