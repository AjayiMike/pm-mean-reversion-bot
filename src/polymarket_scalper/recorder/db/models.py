from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from polymarket_scalper.recorder.db.base import Base


class MarketRecord(Base):
    __tablename__ = "markets"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    condition_id: Mapped[str | None] = mapped_column(String(128), index=True)
    question: Mapped[str] = mapped_column(Text)
    asset: Mapped[str] = mapped_column(String(16), index=True)
    slug: Mapped[str | None] = mapped_column(String(255), index=True)
    event_slug: Mapped[str | None] = mapped_column(String(255), index=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opening_price: Mapped[float | None] = mapped_column(Float)
    opening_price_source: Mapped[str | None] = mapped_column(String(64))
    opening_price_reference_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    opening_price_reference_provider: Mapped[str | None] = mapped_column(String(64))
    opening_price_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_price: Mapped[float | None] = mapped_column(Float)
    close_price_source: Mapped[str | None] = mapped_column(String(64))
    close_price_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    up_token_id: Mapped[str] = mapped_column(String(128), unique=True)
    down_token_id: Mapped[str] = mapped_column(String(128), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    closed: Mapped[bool] = mapped_column(Boolean, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketSnapshotRecord(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(String(128), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    asset: Mapped[str] = mapped_column(String(16), index=True)
    opening_price: Mapped[float | None] = mapped_column(Float)
    opening_price_source: Mapped[str | None] = mapped_column(String(64))
    opening_price_reference_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    opening_price_reference_provider: Mapped[str | None] = mapped_column(String(64))
    opening_price_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    underlying_price: Mapped[float | None] = mapped_column(Float)
    time_remaining_seconds: Mapped[int | None] = mapped_column(Integer)
    up_bid: Mapped[float | None] = mapped_column(Float)
    up_ask: Mapped[float | None] = mapped_column(Float)
    down_bid: Mapped[float | None] = mapped_column(Float)
    down_ask: Mapped[float | None] = mapped_column(Float)
    up_mid: Mapped[float | None] = mapped_column(Float)
    down_mid: Mapped[float | None] = mapped_column(Float)
    up_spread: Mapped[float | None] = mapped_column(Float)
    down_spread: Mapped[float | None] = mapped_column(Float)
    up_depth: Mapped[float | None] = mapped_column(Float)
    down_depth: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrderBookSnapshotRecord(Base):
    __tablename__ = "order_book_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(String(128), index=True)
    token_id: Mapped[str] = mapped_column(String(128), index=True)
    side_label: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    best_bid: Mapped[float | None] = mapped_column(Float)
    best_ask: Mapped[float | None] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)
    depth_at_best_bid: Mapped[float | None] = mapped_column(Float)
    depth_at_best_ask: Mapped[float | None] = mapped_column(Float)
    total_bid_depth: Mapped[float | None] = mapped_column(Float)
    total_ask_depth: Mapped[float | None] = mapped_column(Float)
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UnderlyingPriceTickRecord(Base):
    __tablename__ = "underlying_price_ticks"
    __table_args__ = (
        UniqueConstraint("asset", "timestamp", "provider", name="uq_tick_asset_time_provider"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset: Mapped[str] = mapped_column(String(16), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    price: Mapped[float] = mapped_column(Float)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecorderRunRecord(Base):
    __tablename__ = "recorder_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), index=True)
    assets: Mapped[str] = mapped_column(String(255))
    markets_discovered: Mapped[int] = mapped_column(Integer, default=0)
    snapshots_written: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
