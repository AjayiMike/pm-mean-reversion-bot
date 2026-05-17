from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from polymarket_scalper.domain.enums import AssetSymbol


class DiscoveredMarket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    condition_id: str | None = None
    question: str
    asset: AssetSymbol
    slug: str | None = None
    event_slug: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    opening_price: float | None = Field(default=None, gt=0)
    opening_price_source: str | None = None
    opening_price_reference_timestamp: datetime | None = None
    opening_price_reference_provider: str | None = None
    opening_price_resolved_at: datetime | None = None
    close_price: float | None = Field(default=None, gt=0)
    close_price_source: str | None = None
    close_price_resolved_at: datetime | None = None
    up_token_id: str
    down_token_id: str
    active: bool = True
    closed: bool = False
    archived: bool = False
    raw_payload_json: dict[str, Any] | None = None


class OrderBookLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price: float = Field(ge=0, le=1)
    size: float = Field(ge=0)


class NormalizedOrderBookState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token_id: str
    side_label: str
    timestamp: datetime
    bids: list[OrderBookLevel] = Field(default_factory=list)
    asks: list[OrderBookLevel] = Field(default_factory=list)
    raw_payload_json: dict[str, Any] | None = None

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return round(self.best_ask - self.best_bid, 8)

    @property
    def mid_price(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return round((self.best_bid + self.best_ask) / 2, 8)

    @property
    def depth_at_best_bid(self) -> float | None:
        return self.bids[0].size if self.bids else None

    @property
    def depth_at_best_ask(self) -> float | None:
        return self.asks[0].size if self.asks else None

    @property
    def total_bid_depth(self) -> float:
        return round(sum(level.size for level in self.bids), 8)

    @property
    def total_ask_depth(self) -> float:
        return round(sum(level.size for level in self.asks), 8)


class UnderlyingPriceTick(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset: AssetSymbol
    symbol: str
    timestamp: datetime
    price: float = Field(gt=0)
    provider: str
    raw_payload_json: dict[str, Any] | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.lower()


class NormalizedMarketSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    timestamp: datetime
    asset: str
    opening_price: float | None = None
    opening_price_source: str | None = None
    opening_price_reference_timestamp: datetime | None = None
    opening_price_reference_provider: str | None = None
    opening_price_resolved_at: datetime | None = None
    underlying_price: float | None = None
    time_remaining_seconds: int | None = None
    up_bid: float | None = None
    up_ask: float | None = None
    down_bid: float | None = None
    down_ask: float | None = None
    up_mid: float | None = None
    down_mid: float | None = None
    up_spread: float | None = None
    down_spread: float | None = None
    up_depth: float | None = None
    down_depth: float | None = None
    source: str


class RecorderHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    database_reachable: bool
    active_underlying_price_provider: str
    last_market_refresh_time: datetime | None = None
    active_markets_count: int = 0
    last_polymarket_message_time: datetime | None = None
    last_underlying_price_tick_time: datetime | None = None
    snapshots_written: int = 0
