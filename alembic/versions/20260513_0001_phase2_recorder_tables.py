"""phase2 recorder tables

Revision ID: 20260513_0001
Revises:
Create Date: 2026-05-13 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260513_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "markets",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("condition_id", sa.String(length=128), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("asset", sa.String(length=16), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("event_slug", sa.String(length=255), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_price", sa.Float(), nullable=True),
        sa.Column("up_token_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("down_token_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("closed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_markets_condition_id", "markets", ["condition_id"])
    op.create_index("ix_markets_asset", "markets", ["asset"])
    op.create_index("ix_markets_slug", "markets", ["slug"])
    op.create_index("ix_markets_event_slug", "markets", ["event_slug"])

    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset", sa.String(length=16), nullable=False),
        sa.Column("opening_price", sa.Float(), nullable=True),
        sa.Column("underlying_price", sa.Float(), nullable=True),
        sa.Column("time_remaining_seconds", sa.Integer(), nullable=True),
        sa.Column("up_bid", sa.Float(), nullable=True),
        sa.Column("up_ask", sa.Float(), nullable=True),
        sa.Column("down_bid", sa.Float(), nullable=True),
        sa.Column("down_ask", sa.Float(), nullable=True),
        sa.Column("up_mid", sa.Float(), nullable=True),
        sa.Column("down_mid", sa.Float(), nullable=True),
        sa.Column("up_spread", sa.Float(), nullable=True),
        sa.Column("down_spread", sa.Float(), nullable=True),
        sa.Column("up_depth", sa.Float(), nullable=True),
        sa.Column("down_depth", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_market_snapshots_market_id", "market_snapshots", ["market_id"])
    op.create_index("ix_market_snapshots_timestamp", "market_snapshots", ["timestamp"])
    op.create_index("ix_market_snapshots_asset", "market_snapshots", ["asset"])

    op.create_table(
        "order_book_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("token_id", sa.String(length=128), nullable=False),
        sa.Column("side_label", sa.String(length=16), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("best_bid", sa.Float(), nullable=True),
        sa.Column("best_ask", sa.Float(), nullable=True),
        sa.Column("spread", sa.Float(), nullable=True),
        sa.Column("depth_at_best_bid", sa.Float(), nullable=True),
        sa.Column("depth_at_best_ask", sa.Float(), nullable=True),
        sa.Column("total_bid_depth", sa.Float(), nullable=True),
        sa.Column("total_ask_depth", sa.Float(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_order_book_snapshots_market_id", "order_book_snapshots", ["market_id"])
    op.create_index("ix_order_book_snapshots_token_id", "order_book_snapshots", ["token_id"])
    op.create_index("ix_order_book_snapshots_side_label", "order_book_snapshots", ["side_label"])
    op.create_index("ix_order_book_snapshots_timestamp", "order_book_snapshots", ["timestamp"])

    op.create_table(
        "underlying_price_ticks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("asset", sa.String(length=16), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("asset", "timestamp", "provider", name="uq_tick_asset_time_provider"),
    )
    op.create_index("ix_underlying_price_ticks_asset", "underlying_price_ticks", ["asset"])
    op.create_index("ix_underlying_price_ticks_symbol", "underlying_price_ticks", ["symbol"])
    op.create_index("ix_underlying_price_ticks_timestamp", "underlying_price_ticks", ["timestamp"])
    op.create_index("ix_underlying_price_ticks_provider", "underlying_price_ticks", ["provider"])

    op.create_table(
        "recorder_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assets", sa.String(length=255), nullable=False),
        sa.Column("markets_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshots_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_recorder_runs_status", "recorder_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_recorder_runs_status", table_name="recorder_runs")
    op.drop_table("recorder_runs")
    op.drop_index("ix_underlying_price_ticks_provider", table_name="underlying_price_ticks")
    op.drop_index("ix_underlying_price_ticks_timestamp", table_name="underlying_price_ticks")
    op.drop_index("ix_underlying_price_ticks_symbol", table_name="underlying_price_ticks")
    op.drop_index("ix_underlying_price_ticks_asset", table_name="underlying_price_ticks")
    op.drop_table("underlying_price_ticks")
    op.drop_index("ix_order_book_snapshots_timestamp", table_name="order_book_snapshots")
    op.drop_index("ix_order_book_snapshots_side_label", table_name="order_book_snapshots")
    op.drop_index("ix_order_book_snapshots_token_id", table_name="order_book_snapshots")
    op.drop_index("ix_order_book_snapshots_market_id", table_name="order_book_snapshots")
    op.drop_table("order_book_snapshots")
    op.drop_index("ix_market_snapshots_asset", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_timestamp", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_market_id", table_name="market_snapshots")
    op.drop_table("market_snapshots")
    op.drop_index("ix_markets_event_slug", table_name="markets")
    op.drop_index("ix_markets_slug", table_name="markets")
    op.drop_index("ix_markets_asset", table_name="markets")
    op.drop_index("ix_markets_condition_id", table_name="markets")
    op.drop_table("markets")
