from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from polymarket_scalper.recorder.services.models import NormalizedOrderBookState, OrderBookLevel


class OrderBookStore:
    def __init__(self) -> None:
        self._states: dict[str, NormalizedOrderBookState] = {}

    def update_from_message(
        self,
        message: dict[str, Any],
        side_label_by_token: dict[str, str],
    ) -> None:
        for event_type, asset_id, payload in iter_order_book_events(message):
            bids = normalize_levels(
                payload.get("bids") or payload.get("buys") or [],
                descending=True,
            )
            asks = normalize_levels(
                payload.get("asks") or payload.get("sells") or [],
                descending=False,
            )

            if event_type in {"best_bid_ask", "price_change"} and not bids and not asks:
                best_bid = payload.get("best_bid") or payload.get("bid")
                best_ask = payload.get("best_ask") or payload.get("ask")
                bid_size = payload.get("bid_size") or payload.get("best_bid_size") or 0
                ask_size = payload.get("ask_size") or payload.get("best_ask_size") or 0
                bids = (
                    [OrderBookLevel(price=float(best_bid), size=float(bid_size))]
                    if best_bid
                    else []
                )
                asks = (
                    [OrderBookLevel(price=float(best_ask), size=float(ask_size))]
                    if best_ask
                    else []
                )

            state = NormalizedOrderBookState(
                token_id=asset_id,
                side_label=side_label_by_token.get(asset_id, "UNKNOWN"),
                timestamp=extract_message_timestamp(message, payload),
                bids=bids,
                asks=asks,
                raw_payload_json=message,
            )
            self._states[asset_id] = state

    def latest(self, token_id: str) -> NormalizedOrderBookState | None:
        return self._states.get(token_id)

    def latest_all(self) -> dict[str, NormalizedOrderBookState]:
        return dict(self._states)

    def retain_tokens(self, token_ids: set[str]) -> None:
        self._states = {
            token_id: state for token_id, state in self._states.items() if token_id in token_ids
        }


def normalize_levels(levels: list[Any], descending: bool) -> list[OrderBookLevel]:
    normalized: list[OrderBookLevel] = []
    for level in levels:
        if isinstance(level, dict):
            price = level.get("price")
            size = level.get("size") or level.get("amount") or level.get("quantity") or 0
        elif isinstance(level, (list, tuple)) and len(level) >= 2:
            price, size = level[0], level[1]
        else:
            continue
        normalized.append(OrderBookLevel(price=float(price), size=float(size)))

    return sorted(normalized, key=lambda item: item.price, reverse=descending)


def iter_order_book_events(message: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    event_type = str(message.get("event_type") or message.get("type") or "")
    if event_type not in {"book", "price_change", "best_bid_ask"}:
        return []

    payload = message.get("payload") if isinstance(message.get("payload"), dict) else message
    events: list[tuple[str, str, dict[str, Any]]] = []

    if event_type == "price_change":
        raw_changes = payload.get("price_changes") or payload.get("changes") or []
        if isinstance(raw_changes, list):
            for change in raw_changes:
                if not isinstance(change, dict):
                    continue
                asset_id = extract_asset_id(change) or extract_asset_id(message)
                if asset_id:
                    events.append((event_type, asset_id, change))
        if events:
            return events

    asset_id = extract_asset_id(payload) or extract_asset_id(message)
    if not asset_id:
        return []
    return [(event_type, asset_id, payload)]


def extract_asset_id(payload: dict[str, Any]) -> str:
    return str(
        payload.get("asset_id")
        or payload.get("assetId")
        or payload.get("token_id")
        or payload.get("tokenId")
        or payload.get("market")
        or ""
    )


def extract_message_timestamp(
    message: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> datetime:
    payload = payload or {}
    timestamp_value = (
        message.get("timestamp")
        or payload.get("timestamp")
        or message.get("payload", {}).get("timestamp")
        or datetime.now(UTC).timestamp() * 1000
    )
    return datetime.fromtimestamp(float(timestamp_value) / 1000, tz=UTC)
