"""add opening price provenance fields

Revision ID: 20260517_0003
Revises: 20260517_0002
Create Date: 2026-05-17 00:30:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260517_0003"
down_revision = "20260517_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "markets",
        sa.Column("opening_price_reference_timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "markets",
        sa.Column("opening_price_reference_provider", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "markets",
        sa.Column("opening_price_resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "market_snapshots",
        sa.Column("opening_price_reference_timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "market_snapshots",
        sa.Column("opening_price_reference_provider", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "market_snapshots",
        sa.Column("opening_price_resolved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("market_snapshots", "opening_price_resolved_at")
    op.drop_column("market_snapshots", "opening_price_reference_provider")
    op.drop_column("market_snapshots", "opening_price_reference_timestamp")
    op.drop_column("markets", "opening_price_resolved_at")
    op.drop_column("markets", "opening_price_reference_provider")
    op.drop_column("markets", "opening_price_reference_timestamp")
