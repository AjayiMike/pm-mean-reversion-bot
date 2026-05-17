from __future__ import annotations

from datetime import UTC, datetime

from polymarket_scalper.domain.enums import AssetSymbol
from polymarket_scalper.recorder.feeds.base import UnderlyingPriceFeed
from polymarket_scalper.recorder.services.models import UnderlyingPriceTick


class MockUnderlyingPriceFeed(UnderlyingPriceFeed):
    provider_name = "mock"

    def __init__(self, seed_prices: dict[AssetSymbol, float] | None = None) -> None:
        prices = seed_prices or {
            AssetSymbol.BTC: 65000.0,
            AssetSymbol.ETH: 3200.0,
            AssetSymbol.SOL: 150.0,
            AssetSymbol.BNB: 550.0,
            AssetSymbol.XRP: 0.6,
        }
        self._ticks = {
            asset: UnderlyingPriceTick(
                asset=asset,
                symbol=f"{asset.value.lower()}usdt",
                timestamp=datetime.now(UTC),
                price=price,
                provider=self.provider_name,
                raw_payload_json={"mock": True, "asset": asset.value, "price": price},
            )
            for asset, price in prices.items()
        }

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    def latest_tick(self, asset: AssetSymbol) -> UnderlyingPriceTick | None:
        return self._ticks.get(asset)

    def supported_assets(self) -> list[AssetSymbol]:
        return list(self._ticks.keys())
