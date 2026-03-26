import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Story(Base, TimestampMixin):
    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )

    user: Mapped["User"] = relationship(back_populates="stories")  # noqa: F821
    episodes: Mapped[list["Episode"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )  # noqa: F821

    __table_args__ = (
        Index("idx_stories_user_id", "user_id"),
        Index("idx_stories_status", "status"),
    )
