from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Iterable
from typing import Any

import websockets

from polymarket_scalper.utils.logging import get_logger

MessageHandler = Callable[[dict[str, Any]], None]


class PolymarketMarketWebSocketClient:
    """Thin public market-channel websocket client.

    This subscribes by public asset IDs only and never uses authenticated user-channel features.
    """

    def __init__(self, endpoint: str, asset_ids: list[str], handler: MessageHandler) -> None:
        self.endpoint = endpoint
        self.asset_ids = asset_ids
        self.handler = handler
        self.logger = get_logger(__name__)
        self._ws: Any | None = None

    async def connect_once(self) -> None:
        if not self.asset_ids:
            self.logger.info("market_ws_skipped_no_assets")
            return
        async with websockets.connect(self.endpoint) as websocket:
            self._ws = websocket
            self.logger.info("market_ws_connected", extra={"asset_count": len(self.asset_ids)})
            await websocket.send(
                json.dumps(
                    {
                        "assets_ids": self.asset_ids,
                        "type": "market",
                        "custom_feature_enabled": True,
                    }
                )
            )
            heartbeat = asyncio.create_task(self._heartbeat_loop(websocket))
            try:
                async for raw_message in websocket:
                    if isinstance(raw_message, bytes):
                        raw_message = raw_message.decode("utf-8")
                    if raw_message == "PONG":
                        continue
                    try:
                        for message in iter_market_messages(json.loads(raw_message)):
                            self.handler(message)
                    except json.JSONDecodeError:
                        self.logger.warning("market_ws_malformed_message")
                    except Exception as exc:  # noqa: BLE001
                        self.logger.exception("market_ws_handler_error", extra={"error": str(exc)})
            finally:
                heartbeat.cancel()
                self.logger.info("market_ws_disconnected")

    async def _heartbeat_loop(self, websocket: Any) -> None:
        while True:
            await asyncio.sleep(10)
            await websocket.send("PING")


def iter_market_messages(payload: Any) -> Iterable[dict[str, Any]]:
    """Normalize public websocket payloads into individual event dictionaries."""

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return

    if not isinstance(payload, dict):
        return

    for key in ("events", "messages", "data"):
        value = payload.get(key)
        if not isinstance(value, list):
            continue
        wrapper = {
            wrapper_key: wrapper_value
            for wrapper_key, wrapper_value in payload.items()
            if wrapper_key != key
        }
        for item in value:
            if isinstance(item, dict):
                yield {**wrapper, **item}
        return

    yield payload
