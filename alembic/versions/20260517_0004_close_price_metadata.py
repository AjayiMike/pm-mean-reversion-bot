"""add close price metadata to markets

Revision ID: 20260517_0004
Revises: 20260517_0003
Create Date: 2026-05-17 12:20:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260517_0004"
down_revision = "20260517_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("markets", sa.Column("close_price", sa.Float(), nullable=True))
    op.add_column("markets", sa.Column("close_price_source", sa.String(length=64), nullable=True))
    op.add_column(
        "markets",
        sa.Column("close_price_resolved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("markets", "close_price_resolved_at")
    op.drop_column("markets", "close_price_source")
    op.drop_column("markets", "close_price")
