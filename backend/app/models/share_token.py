from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid

if TYPE_CHECKING:
    from app.models.episode import Episode


class ShareToken(Base):
    __tablename__ = "share_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    episode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=lambda: secrets.token_urlsafe(32)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    episode: Mapped["Episode"] = relationship()

    __table_args__ = (
        Index("idx_share_tokens_token", "token"),
        Index("idx_share_tokens_episode_id", "episode_id"),
    )
