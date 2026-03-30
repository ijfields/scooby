"""add share_tokens table

Revision ID: c4d9e3f5a7b2
Revises: b3c8f2a1d9e4
Create Date: 2026-03-29 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d9e3f5a7b2"
down_revision: Union[str, None] = "b3c8f2a1d9e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "share_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("episode_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("idx_share_tokens_token", "share_tokens", ["token"])
    op.create_index("idx_share_tokens_episode_id", "share_tokens", ["episode_id"])


def downgrade() -> None:
    op.drop_index("idx_share_tokens_episode_id", table_name="share_tokens")
    op.drop_index("idx_share_tokens_token", table_name="share_tokens")
    op.drop_table("share_tokens")
