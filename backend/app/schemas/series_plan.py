from __future__ import annotations

from pydantic import BaseModel, Field


class EpisodePlan(BaseModel):
    episode_number: int = Field(..., ge=1, le=8)
    title: str = Field(..., max_length=200)
    angle: str = Field(..., description="The thesis or angle for this episode")
    key_content: str = Field(
        ...,
        description="Condensed transcript excerpt for scene breakdown (1000-2000 words)",
    )
    target_duration_sec: int = Field(default=75, ge=60, le=90)
    hook_suggestion: str = Field(
        ..., description="Suggested opening hook for this episode"
    )


class SeriesPlan(BaseModel):
    series_title: str = Field(..., max_length=200)
    series_thesis: str = Field(
        ..., description="The overarching argument or theme of the series"
    )
    total_episodes: int = Field(..., ge=3, le=8)
    episodes: list[EpisodePlan]


class SeriesPlanResponse(BaseModel):
    story_id: str
    status: str
    plan: SeriesPlan | None = None


class EpisodePlanEdit(BaseModel):
    episode_number: int
    title: str | None = None
    angle: str | None = None
    remove: bool = False


class SeriesApproveRequest(BaseModel):
    episodes: list[EpisodePlanEdit] | None = Field(
        None,
        description="Optionally override episode titles/angles. If None, use plan as-is.",
    )
