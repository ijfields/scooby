from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, LargeBinary, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.generation_job import GenerationJob
    from app.models.scene import Scene
    from app.models.story import Story


class Episode(Base, TimestampMixin):
    __tablename__ = "episodes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200))
    target_duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, server_default="90")
    visual_style_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("style_presets.id"))
    voice_style_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("style_presets.id"))
    music_style_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("style_presets.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    composition_json: Mapped[dict | None] = mapped_column(JSONB)
    final_video_url: Mapped[str | None] = mapped_column(Text)
    # Final rendered MP4 stored in Postgres so it survives worker restarts
    # (worker /tmp is ephemeral). Use deferred() so list/detail queries don't
    # pull the blob unless explicitly requested.
    final_video_data: Mapped[bytes | None] = deferred(mapped_column(LargeBinary, nullable=True))
    final_video_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    final_video_mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    final_video_duration_sec: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    script_pdf_url: Mapped[str | None] = mapped_column(Text)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    series_angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="standard"
    )  # standard | enhanced | movie_lite | movie | movie_pro

    story: Mapped["Story"] = relationship(back_populates="episodes")
    scenes: Mapped[list["Scene"]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_episodes_story_id", "story_id"),
        Index("idx_episodes_status", "status"),
    )
