from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StylePresetResponse(BaseModel):
    id: UUID
    name: str
    category: str
    description: str | None
    thumbnail_url: str | None
    preview_url: str | None
    config: dict
    is_active: bool
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}
