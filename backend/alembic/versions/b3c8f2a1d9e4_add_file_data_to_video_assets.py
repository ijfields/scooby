"""add file_data to video_assets

Revision ID: b3c8f2a1d9e4
Revises: 7a6b1e776e8f
Create Date: 2026-03-28 22:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c8f2a1d9e4"
down_revision: Union[str, None] = "7a6b1e776e8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("video_assets", sa.Column("file_data", sa.LargeBinary(), nullable=True))
    op.alter_column("video_assets", "file_url", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.alter_column("video_assets", "file_url", existing_type=sa.Text(), nullable=False)
    op.drop_column("video_assets", "file_data")
