from __future__ import annotations

from datetime import UTC, datetime

from polymarket_scalper.recorder.feeds.base import UnderlyingPriceFeed
from polymarket_scalper.recorder.services.models import DiscoveredMarket, NormalizedMarketSnapshot
from polymarket_scalper.recorder.services.orderbook import OrderBookStore


def build_market_snapshot(
    market: DiscoveredMarket,
    order_books: OrderBookStore,
    price_feed: UnderlyingPriceFeed,
    timestamp: datetime | None = None,
) -> NormalizedMarketSnapshot:
    now = timestamp or datetime.now(UTC)
    up_state = order_books.latest(market.up_token_id)
    down_state = order_books.latest(market.down_token_id)
    tick = price_feed.latest_tick(market.asset)

    if market.end_time is not None:
        time_remaining_seconds = max(int((market.end_time - now).total_seconds()), 0)
    else:
        time_remaining_seconds = None

    return NormalizedMarketSnapshot(
        market_id=market.id,
        timestamp=now,
        asset=market.asset.value,
        opening_price=market.opening_price,
        opening_price_source=market.opening_price_source,
        opening_price_reference_timestamp=market.opening_price_reference_timestamp,
        opening_price_reference_provider=market.opening_price_reference_provider,
        opening_price_resolved_at=market.opening_price_resolved_at,
        underlying_price=tick.price if tick else None,
        time_remaining_seconds=time_remaining_seconds,
        up_bid=up_state.best_bid if up_state else None,
        up_ask=up_state.best_ask if up_state else None,
        down_bid=down_state.best_bid if down_state else None,
        down_ask=down_state.best_ask if down_state else None,
        up_mid=up_state.mid_price if up_state else None,
        down_mid=down_state.mid_price if down_state else None,
        up_spread=up_state.spread if up_state else None,
        down_spread=down_state.spread if down_state else None,
        up_depth=up_state.total_bid_depth if up_state else None,
        down_depth=down_state.total_bid_depth if down_state else None,
        source="polymarket_clob+underlying_price_feed",
    )
