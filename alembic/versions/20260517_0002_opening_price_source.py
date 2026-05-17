"""add opening price source fields

Revision ID: 20260517_0002
Revises: 20260513_0001
Create Date: 2026-05-17 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260517_0002"
down_revision = "20260513_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("markets", sa.Column("opening_price_source", sa.String(length=64), nullable=True))
    op.add_column(
        "market_snapshots",
        sa.Column("opening_price_source", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("market_snapshots", "opening_price_source")
    op.drop_column("markets", "opening_price_source")
