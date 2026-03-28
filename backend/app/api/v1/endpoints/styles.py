from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.style_preset import StylePreset
from app.schemas.style_preset import StylePresetResponse

router = APIRouter()


@router.get("", response_model=list[StylePresetResponse])
async def list_style_presets(
    category: str | None = Query(None, description="Filter by category: visual, voice, music"),
    db: AsyncSession = Depends(get_db),
) -> list[StylePreset]:
    query = select(StylePreset).where(StylePreset.is_active.is_(True))
    if category:
        query = query.where(StylePreset.category == category)
    query = query.order_by(StylePreset.category, StylePreset.sort_order)
    result = await db.execute(query)
    return list(result.scalars().all())
