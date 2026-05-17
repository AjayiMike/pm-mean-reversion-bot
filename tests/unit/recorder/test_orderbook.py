from __future__ import annotations

from polymarket_scalper.recorder.clients.market_websocket import iter_market_messages
from polymarket_scalper.recorder.services.orderbook import OrderBookStore


def test_orderbook_normalization_best_prices_spread_mid_and_depth() -> None:
    store = OrderBookStore()
    message = {
        "event_type": "book",
        "asset_id": "token-1",
        "timestamp": 1710000000000,
        "bids": [[0.44, 120], [0.43, 80]],
        "asks": [[0.46, 110], [0.47, 90]],
    }
    store.update_from_message(message, {"token-1": "UP"})
    state = store.latest("token-1")
    assert state is not None
    assert state.best_bid == 0.44
    assert state.best_ask == 0.46
    assert state.spread == 0.02
    assert state.mid_price == 0.45
    assert state.total_bid_depth == 200
    assert state.total_ask_depth == 200


def test_orderbook_normalizes_nested_price_change_events() -> None:
    store = OrderBookStore()
    message = {
        "event_type": "price_change",
        "timestamp": 1710000000000,
        "price_changes": [
            {
                "asset_id": "token-1",
                "best_bid": 0.41,
                "best_ask": 0.43,
                "best_bid_size": 55,
                "best_ask_size": 65,
                "timestamp": 1710000000500,
            }
        ],
    }
    store.update_from_message(message, {"token-1": "UP"})
    state = store.latest("token-1")
    assert state is not None
    assert state.best_bid == 0.41
    assert state.best_ask == 0.43
    assert state.spread == 0.02
    assert state.mid_price == 0.42
    assert state.total_bid_depth == 55
    assert state.total_ask_depth == 65


def test_market_ws_message_iterator_expands_list_payloads() -> None:
    payload = [
        {"event_type": "book", "asset_id": "token-1"},
        {"event_type": "best_bid_ask", "asset_id": "token-2"},
    ]
    messages = list(iter_market_messages(payload))
    assert messages == payload


def test_market_ws_message_iterator_expands_wrapped_event_list() -> None:
    payload = {
        "type": "price_change",
        "data": [
            {"asset_id": "token-1", "best_bid": 0.33},
            {"asset_id": "token-2", "best_ask": 0.66},
        ],
    }
    messages = list(iter_market_messages(payload))
    assert messages == [
        {"type": "price_change", "asset_id": "token-1", "best_bid": 0.33},
        {"type": "price_change", "asset_id": "token-2", "best_ask": 0.66},
    ]


def test_orderbook_store_retain_tokens_prunes_stale_market_state() -> None:
    store = OrderBookStore()
    store.update_from_message(
        {"event_type": "book", "asset_id": "token-1", "bids": [[0.4, 10]], "asks": [[0.6, 5]]},
        {"token-1": "UP"},
    )
    store.update_from_message(
        {"event_type": "book", "asset_id": "token-2", "bids": [[0.2, 10]], "asks": [[0.8, 5]]},
        {"token-2": "DOWN"},
    )

    store.retain_tokens({"token-2"})

    assert store.latest("token-1") is None
    assert store.latest("token-2") is not None
