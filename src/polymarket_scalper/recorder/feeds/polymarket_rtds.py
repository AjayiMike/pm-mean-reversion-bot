from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import websockets

from polymarket_scalper.domain.enums import AssetSymbol
from polymarket_scalper.recorder.feeds.base import UnderlyingPriceFeed
from polymarket_scalper.recorder.services.models import UnderlyingPriceTick
from polymarket_scalper.utils.logging import get_logger

RTDS_BINANCE_SYMBOL_MAP = {
    "btcusdt": AssetSymbol.BTC,
    "ethusdt": AssetSymbol.ETH,
    "solusdt": AssetSymbol.SOL,
    "bnbusdt": AssetSymbol.BNB,
    "xrpusdt": AssetSymbol.XRP,
}

RTDS_CHAINLINK_SYMBOL_MAP = {
    "btc/usd": AssetSymbol.BTC,
    "eth/usd": AssetSymbol.ETH,
    "sol/usd": AssetSymbol.SOL,
    "xrp/usd": AssetSymbol.XRP,
}

MessageHandler = Callable[[dict[str, Any]], None]


class PolymarketRtdsPriceFeed(UnderlyingPriceFeed):
    """Live underlying price feed backed by Polymarket RTDS."""

    provider_name = "polymarket_rtds"

    def __init__(
        self,
        endpoint: str,
        assets: list[AssetSymbol],
        message_handler: MessageHandler | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.assets = list(dict.fromkeys(assets))
        self.message_handler = message_handler
        self.logger = get_logger(__name__)
        self._connected = False
        self._latest_ticks: dict[AssetSymbol, UnderlyingPriceTick] = {}
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def connect(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_forever())

    async def disconnect(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        self._connected = False

    def latest_tick(self, asset: AssetSymbol) -> UnderlyingPriceTick | None:
        return self._latest_ticks.get(asset)

    def supported_assets(self) -> list[AssetSymbol]:
        return list(RTDS_BINANCE_SYMBOL_MAP.values())

    def handle_message(self, message: dict[str, Any]) -> UnderlyingPriceTick | None:
        topic = str(message.get("topic", ""))
        payload = message.get("payload") or {}
        symbol = str(payload.get("symbol", "")).lower()
        price = payload.get("value")
        timestamp_ms = payload.get("timestamp") or message.get("timestamp")

        asset = None
        provider = self.provider_name
        if topic == "crypto_prices":
            asset = RTDS_BINANCE_SYMBOL_MAP.get(symbol)
            provider = f"{self.provider_name}:binance"
        elif topic == "crypto_prices_chainlink":
            asset = RTDS_CHAINLINK_SYMBOL_MAP.get(symbol)
            provider = f"{self.provider_name}:chainlink"

        if asset is None or price is None or timestamp_ms is None:
            return None

        tick = UnderlyingPriceTick(
            asset=asset,
            symbol=symbol,
            timestamp=datetime.fromtimestamp(float(timestamp_ms) / 1000, tz=UTC),
            price=float(price),
            provider=provider,
            raw_payload_json=message,
        )
        self._latest_ticks[asset] = tick
        return tick

    def build_subscriptions(self) -> list[dict[str, Any]]:
        if not self.assets:
            return []
        return [
            {
                "topic": "crypto_prices",
                "type": "update",
            },
            {
                "topic": "crypto_prices_chainlink",
                "type": "*",
                "filters": "",
            },
        ]

    async def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._connect_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self._connected = False
                self.logger.warning("underlying_rtds_reconnect", extra={"error": str(exc)})
                await asyncio.sleep(1)

    async def _connect_once(self) -> None:
        subscriptions = self.build_subscriptions()
        if not subscriptions:
            self.logger.warning("underlying_rtds_no_subscriptions")
            return

        async with websockets.connect(self.endpoint) as websocket:
            self._connected = True
            self.logger.info(
                "underlying_rtds_connected",
                extra={"subscription_count": len(subscriptions)},
            )
            await websocket.send(
                json.dumps(
                    {
                        "action": "subscribe",
                        "subscriptions": subscriptions,
                    }
                )
            )
            heartbeat = asyncio.create_task(self._heartbeat_loop(websocket))
            try:
                async for raw_message in websocket:
                    if isinstance(raw_message, bytes):
                        raw_message = raw_message.decode("utf-8")
                    if raw_message in {"", "PONG"}:
                        continue
                    try:
                        message = json.loads(raw_message)
                    except json.JSONDecodeError:
                        self.logger.warning("underlying_rtds_malformed_message")
                        continue
                    if not isinstance(message, dict):
                        continue
                    if self.message_handler is not None:
                        self.message_handler(message)
                    else:
                        self.handle_message(message)
            finally:
                heartbeat.cancel()
                self._connected = False
                self.logger.info("underlying_rtds_disconnected")

    async def _heartbeat_loop(self, websocket: Any) -> None:
        while True:
            await asyncio.sleep(5)
            await websocket.send("PING")
