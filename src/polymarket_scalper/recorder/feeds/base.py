from __future__ import annotations

from abc import ABC, abstractmethod

from polymarket_scalper.domain.enums import AssetSymbol
from polymarket_scalper.recorder.services.models import UnderlyingPriceTick


class UnderlyingPriceFeed(ABC):
    """Swappable abstraction for underlying crypto price ticks."""

    provider_name: str

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    def latest_tick(self, asset: AssetSymbol) -> UnderlyingPriceTick | None: ...

    @abstractmethod
    def supported_assets(self) -> list[AssetSymbol]: ...
