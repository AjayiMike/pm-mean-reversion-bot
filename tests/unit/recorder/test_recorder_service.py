from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from polymarket_scalper.config.settings import AppSettings
from polymarket_scalper.domain.enums import AssetSymbol
from polymarket_scalper.recorder.feeds.polymarket_rtds import PolymarketRtdsPriceFeed
from polymarket_scalper.recorder.services.models import UnderlyingPriceTick
from polymarket_scalper.recorder.services.recorder import RecorderService


def test_persist_available_underlying_ticks_skips_rtds_cached_ticks() -> None:
    settings = AppSettings(app_mode="record", database_url="sqlite:///:memory:")
    service = RecorderService(settings)
    service.price_feed = PolymarketRtdsPriceFeed("wss://example.invalid", settings.supported_assets)
    service.price_feed._latest_ticks[AssetSymbol.BTC] = UnderlyingPriceTick(
        asset=AssetSymbol.BTC,
        symbol="btcusdt",
        timestamp=datetime(2026, 5, 18, 0, 9, 35, tzinfo=UTC),
        price=103_000.0,
        provider="polymarket_rtds:binance",
    )

    persisted: list[UnderlyingPriceTick] = []
    service._persist_underlying_tick = persisted.append  # type: ignore[method-assign]

    written = asyncio.run(service._persist_available_underlying_ticks())

    assert written == 0
    assert persisted == []
    assert service.last_underlying_price_tick_time is None


def test_persist_available_underlying_ticks_uses_cached_ticks_for_mock_feed() -> None:
    settings = AppSettings(
        app_mode="record",
        database_url="sqlite:///:memory:",
        crypto_price_provider="mock",
        recorder_underlying_price_provider="mock",
    )
    service = RecorderService(settings)

    persisted: list[UnderlyingPriceTick] = []
    service._persist_underlying_tick = persisted.append  # type: ignore[method-assign]

    written = asyncio.run(service._persist_available_underlying_ticks())

    assert written == len(settings.supported_assets)
    assert [tick.asset for tick in persisted] == settings.supported_assets
    assert service.last_underlying_price_tick_time is not None


def test_describe_exception_includes_type_when_message_is_empty() -> None:
    settings = AppSettings(app_mode="record", database_url="sqlite:///:memory:")
    service = RecorderService(settings)

    exc = TimeoutError()

    assert service._describe_exception(exc) == "TimeoutError"


def test_refresh_market_subscriptions_if_needed_keeps_running_on_refresh_failure() -> None:
    settings = AppSettings(app_mode="record", database_url="sqlite:///:memory:")
    service = RecorderService(settings)
    service._active_market_signature = ("market-1",)
    service.last_market_refresh_time = None
    service.refresh_markets = AsyncMock(side_effect=TimeoutError())  # type: ignore[method-assign]

    sentinel_task = object()

    result = asyncio.run(service._refresh_market_subscriptions_if_needed(sentinel_task))  # type: ignore[arg-type]

    assert result is sentinel_task


def test_ensure_underlying_feed_is_fresh_allows_recent_rtds_ticks() -> None:
    settings = AppSettings(app_mode="record", database_url="sqlite:///:memory:")
    service = RecorderService(settings)
    service.price_feed = PolymarketRtdsPriceFeed("wss://example.invalid", settings.supported_assets)
    service.last_underlying_message_received_at = datetime.now(UTC) - timedelta(seconds=30)
    service.last_underlying_price_tick_time = datetime.now(UTC) - timedelta(seconds=31)

    service._ensure_underlying_feed_is_fresh()


def test_ensure_underlying_feed_is_fresh_raises_for_stalled_rtds_feed() -> None:
    settings = AppSettings(
        app_mode="record",
        database_url="sqlite:///:memory:",
        recorder_underlying_stale_after_seconds=60,
    )
    service = RecorderService(settings)
    service.price_feed = PolymarketRtdsPriceFeed("wss://example.invalid", settings.supported_assets)
    service.last_underlying_message_received_at = datetime.now(UTC) - timedelta(seconds=61)
    service.last_underlying_price_tick_time = datetime.now(UTC) - timedelta(seconds=62)

    with pytest.raises(RuntimeError, match="underlying RTDS feed stalled"):
        service._ensure_underlying_feed_is_fresh()
