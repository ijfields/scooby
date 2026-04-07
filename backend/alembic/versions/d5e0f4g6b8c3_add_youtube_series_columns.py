"""add youtube series columns to stories and episodes

Revision ID: d5e0f4g6b8c3
Revises: c4d9e3f5a7b2
Create Date: 2026-03-31 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e0f4g6b8c3"
down_revision: Union[str, None] = "c4d9e3f5a7b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Stories: add source tracking columns
    op.add_column(
        "stories",
        sa.Column("source_type", sa.String(20), nullable=False, server_default="original"),
    )
    op.add_column(
        "stories",
        sa.Column("source_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "stories",
        sa.Column("source_meta", JSONB(), nullable=True),
    )

    # Episodes: add series columns
    op.add_column(
        "episodes",
        sa.Column("episode_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "episodes",
        sa.Column("series_angle", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("episodes", "series_angle")
    op.drop_column("episodes", "episode_number")
    op.drop_column("stories", "source_meta")
    op.drop_column("stories", "source_url")
    op.drop_column("stories", "source_type")
