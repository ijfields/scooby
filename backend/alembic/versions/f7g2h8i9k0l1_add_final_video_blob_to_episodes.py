"""Add final_video_data blob columns to episodes

Stores the rendered MP4 bytes directly in Postgres so they survive worker
container restarts (worker /tmp is ephemeral on Railway). Mirrors the
LargeBinary pattern used by video_assets.

Revision ID: f7g2h8i9k0l1
Revises: e6f1g5h7i9j4
Create Date: 2026-04-26

"""
from alembic import op
import sqlalchemy as sa


revision = "f7g2h8i9k0l1"
down_revision = "e6f1g5h7i9j4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "episodes",
        sa.Column("final_video_data", sa.LargeBinary, nullable=True),
    )
    op.add_column(
        "episodes",
        sa.Column("final_video_size_bytes", sa.BigInteger, nullable=True),
    )
    op.add_column(
        "episodes",
        sa.Column("final_video_mime_type", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("episodes", "final_video_mime_type")
    op.drop_column("episodes", "final_video_size_bytes")
    op.drop_column("episodes", "final_video_data")
