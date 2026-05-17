from __future__ import annotations

from datetime import UTC, datetime

from polymarket_scalper.domain.enums import AssetSymbol
from polymarket_scalper.recorder.clients.frontend import extract_opening_price_from_next_data
from polymarket_scalper.recorder.services.discovery import (
    build_candidate_slugs,
    current_quarter_epoch,
    extract_asset_symbol,
    extract_asset_symbol_from_slug,
    get_quarter_start,
    is_candidate_15m_crypto_market,
    parse_market_candidate,
)


def test_asset_symbol_extraction_from_market_text() -> None:
    assert extract_asset_symbol("Will Bitcoin go up in the next 15 minutes?") is AssetSymbol.BTC
    assert extract_asset_symbol("Will Solana move higher over the next 15m?") is AssetSymbol.SOL
    assert extract_asset_symbol("Unrelated market") is None


def test_market_filtering_logic_accepts_15m_crypto_market() -> None:
    assert is_candidate_15m_crypto_market("BTC 15-minute market: up or down?") is True
    assert is_candidate_15m_crypto_market("Will ETH be above or below open in 15 min?") is True
    assert is_candidate_15m_crypto_market("BTC market", slug="btc-updown-15m-1747396800") is True
    assert is_candidate_15m_crypto_market("Will Bitcoin hit 100k by 2027?") is False


def test_parse_market_candidate() -> None:
    payload = {
        "id": "market-1",
        "conditionId": "condition-1",
        "question": "BTC 15-minute market: up or down?",
        "slug": "btc-15m-up-down",
        "eventSlug": "btc-15m",
        "clobTokenIds": ["up-token", "down-token"],
        "active": True,
        "closed": False,
        "archived": False,
        "eventStartTime": "2026-05-13T12:00:00Z",
        "endDate": "2026-05-13T12:15:00Z",
    }
    market = parse_market_candidate(payload)
    assert market is not None
    assert market.asset is AssetSymbol.BTC
    assert market.up_token_id == "up-token"
    assert market.down_token_id == "down-token"
    assert market.opening_price is None
    assert market.start_time == datetime(2026, 5, 13, 12, 0, tzinfo=UTC)


def test_parse_market_candidate_extracts_explicit_opening_price() -> None:
    payload = {
        "id": "market-1",
        "conditionId": "condition-1",
        "question": "BTC 15-minute market: up or down?",
        "slug": "btc-15m-up-down",
        "clobTokenIds": ["up-token", "down-token"],
        "openingPrice": "104250.5",
    }
    market = parse_market_candidate(payload)
    assert market is not None
    assert market.opening_price == 104250.5
    assert market.opening_price_source == "gamma_metadata"


def test_extract_asset_symbol_from_slug() -> None:
    assert extract_asset_symbol_from_slug("btc-updown-15m-1747396800") is AssetSymbol.BTC
    assert extract_asset_symbol_from_slug("eth-updown-15m-1747396800") is AssetSymbol.ETH
    assert extract_asset_symbol_from_slug("other-market") is None


def test_quarter_epoch_slug_generation() -> None:
    reference = datetime(2026, 5, 17, 12, 7, tzinfo=UTC)
    quarter_start = get_quarter_start(reference)
    assert quarter_start == datetime(2026, 5, 17, 12, 0, tzinfo=UTC)

    epoch = current_quarter_epoch(reference)
    assert epoch == int(quarter_start.timestamp())

    slugs = build_candidate_slugs([AssetSymbol.BTC], reference)
    assert slugs == [(AssetSymbol.BTC, f"btc-updown-15m-{epoch}")]


def test_frontend_next_data_open_price_extraction_uses_matching_window() -> None:
    root = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "queryKey": [
                                "crypto-prices",
                                "price",
                                "BTC",
                                "2026-05-17T00:15:00Z",
                                "fifteen",
                                "2026-05-17T00:30:00Z",
                            ],
                            "state": {"data": {"openPrice": 90123.45}, "dataUpdatedAt": 1},
                        },
                        {
                            "queryKey": [
                                "crypto-prices",
                                "price",
                                "BTC",
                                "2026-05-17T00:30:00Z",
                                "fifteen",
                                "2026-05-17T00:45:00Z",
                            ],
                            "state": {"data": {"openPrice": 90234.56}, "dataUpdatedAt": 2},
                        },
                    ]
                }
            }
        }
    }
    opening_price = extract_opening_price_from_next_data(
        root=root,
        asset=AssetSymbol.BTC,
        start_time=datetime(2026, 5, 17, 0, 30, tzinfo=UTC),
        end_time=datetime(2026, 5, 17, 0, 45, tzinfo=UTC),
    )
    assert opening_price == 90234.56
