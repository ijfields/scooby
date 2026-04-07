"""Add generation_tier to episodes

Revision ID: e6f1g5h7i9j4
Revises: d5e0f4g6b8c3
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e6f1g5h7i9j4"
down_revision = "d5e0f4g6b8c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "episodes",
        sa.Column(
            "generation_tier",
            sa.String(20),
            nullable=False,
            server_default="standard",
        ),
    )


def downgrade() -> None:
    op.drop_column("episodes", "generation_tier")
