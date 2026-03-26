import uuid
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Scene(Base, TimestampMixin):
    __tablename__ = "scenes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    episode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False
    )
    scene_order: Mapped[int] = mapped_column(Integer, nullable=False)
    beat_label: Mapped[str] = mapped_column(String(50), nullable=False)
    visual_description: Mapped[str] = mapped_column(Text, nullable=False)
    narration_text: Mapped[str | None] = mapped_column(Text)
    dialogue_text: Mapped[str | None] = mapped_column(Text)
    duration_sec: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    image_prompt: Mapped[str | None] = mapped_column(Text)
    start_frame: Mapped[int | None] = mapped_column(Integer)
    end_frame: Mapped[int | None] = mapped_column(Integer)

    episode: Mapped["Episode"] = relationship(back_populates="scenes")  # noqa: F821
    video_assets: Mapped[list["VideoAsset"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan"
    )  # noqa: F821

    __table_args__ = (
        UniqueConstraint("episode_id", "scene_order"),
        Index("idx_scenes_episode_id", "episode_id"),
        Index("idx_scenes_order", "episode_id", "scene_order"),
    )
