from __future__ import annotations

from datetime import UTC, datetime

from polymarket_scalper.domain.enums import AssetSymbol
from polymarket_scalper.recorder.clients.frontend import (
    extract_market_prices_from_next_data,
    extract_next_data_from_html,
)
from polymarket_scalper.recorder.feeds.factory import build_underlying_price_feed
from polymarket_scalper.recorder.feeds.mock import MockUnderlyingPriceFeed
from polymarket_scalper.recorder.feeds.polymarket_rtds import PolymarketRtdsPriceFeed


def test_underlying_price_provider_selection_polymarket_rtds() -> None:
    feed = build_underlying_price_feed(
        "polymarket_rtds",
        rtds_url="wss://ws-live-data.polymarket.com",
        assets=[AssetSymbol.BTC],
    )
    assert isinstance(feed, PolymarketRtdsPriceFeed)


def test_underlying_price_provider_selection_mock() -> None:
    feed = build_underlying_price_feed("mock")
    assert isinstance(feed, MockUnderlyingPriceFeed)


def test_unsupported_underlying_price_provider_fails() -> None:
    try:
        build_underlying_price_feed("unsupported")
    except ValueError as exc:
        assert "unsupported underlying price provider" in str(exc)
    else:
        raise AssertionError("expected provider selection to fail")


def test_underlying_price_tick_normalization() -> None:
    feed = PolymarketRtdsPriceFeed(
        endpoint="wss://ws-live-data.polymarket.com",
        assets=[AssetSymbol.BTC],
    )
    tick = feed.handle_message(
        {
            "topic": "crypto_prices",
            "type": "update",
            "timestamp": 1753314064237,
            "payload": {"symbol": "btcusdt", "timestamp": 1753314064213, "value": 67234.5},
        }
    )
    assert tick is not None
    assert tick.asset is AssetSymbol.BTC
    assert tick.symbol == "btcusdt"
    assert tick.price == 67234.5
    assert tick.provider == "polymarket_rtds:binance"


def test_rtds_builds_chainlink_and_binance_subscriptions() -> None:
    feed = PolymarketRtdsPriceFeed(
        endpoint="wss://ws-live-data.polymarket.com",
        assets=[AssetSymbol.BTC, AssetSymbol.BNB, AssetSymbol.XRP],
    )
    subscriptions = feed.build_subscriptions()
    assert subscriptions == [
        {"topic": "crypto_prices", "type": "update"},
        {"topic": "crypto_prices_chainlink", "type": "*", "filters": ""},
    ]


def test_frontend_next_data_html_extractor_handles_attribute_order() -> None:
    html = '<script type="application/json" data-test="x" id="__NEXT_DATA__">{"ok":true}</script>'
    parsed = extract_next_data_from_html(html, slug="sample-slug")
    assert parsed == {"ok": True}


def test_frontend_market_price_extractor_reads_open_and_close_price() -> None:
    root = {
        "pageProps": {
            "dehydratedState": {
                "queries": [
                    {
                        "queryKey": [
                            "crypto-prices",
                            "price",
                            "BTC",
                            "2026-05-17T09:45:00Z",
                            "fifteen",
                            "2026-05-17T10:00:00Z",
                        ],
                        "state": {
                            "dataUpdatedAt": 2,
                            "data": {"openPrice": 100001.5, "closePrice": 100123.4},
                        },
                    }
                ]
            }
        }
    }

    prices = extract_market_prices_from_next_data(
        root,
        AssetSymbol.BTC,
        start_time=datetime(2026, 5, 17, 9, 45, tzinfo=UTC),
        end_time=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
    )

    assert prices.open_price == 100001.5
    assert prices.close_price == 100123.4
