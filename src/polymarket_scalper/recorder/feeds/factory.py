from __future__ import annotations

from collections.abc import Callable

from polymarket_scalper.domain.enums import AssetSymbol
from polymarket_scalper.recorder.feeds.base import UnderlyingPriceFeed
from polymarket_scalper.recorder.feeds.mock import MockUnderlyingPriceFeed
from polymarket_scalper.recorder.feeds.polymarket_rtds import PolymarketRtdsPriceFeed


def build_underlying_price_feed(
    provider_name: str,
    *,
    rtds_url: str | None = None,
    assets: list[AssetSymbol] | None = None,
    message_handler: Callable[[dict], None] | None = None,
) -> UnderlyingPriceFeed:
    normalized = provider_name.strip().lower()
    if normalized == "polymarket_rtds":
        return PolymarketRtdsPriceFeed(
            endpoint=rtds_url or "wss://ws-live-data.polymarket.com",
            assets=assets or [],
            message_handler=message_handler,
        )
    if normalized == "mock":
        return MockUnderlyingPriceFeed()
    raise ValueError(f"unsupported underlying price provider: {provider_name}")
