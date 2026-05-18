from __future__ import annotations

import asyncio
from datetime import UTC, datetime

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
