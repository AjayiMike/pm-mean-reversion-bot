from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from polymarket_scalper.domain.enums import AssetSymbol, ExitReason, MarketSide, SignalAction


class MarketSnapshot(BaseModel):
    """Minimal snapshot model for future strategy evaluation.

    This intentionally stays small in Phase 1 and models only the inputs needed by
    configuration validation and rule stubs.
    """

    model_config = ConfigDict(extra="forbid")

    asset: AssetSymbol
    market_id: str
    opening_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    time_remaining_seconds: int = Field(ge=0)
    up_bid: float = Field(ge=0, le=1)
    up_ask: float = Field(ge=0, le=1)
    down_bid: float = Field(ge=0, le=1)
    down_ask: float = Field(ge=0, le=1)
    spread: float = Field(ge=0, le=1)
    depth_multiplier: float = Field(ge=0)
    distance_from_open_bps: float
    recent_return_30s: float = 0.0
    recent_return_60s: float = 0.0


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    side: MarketSide
    entry_price: float = Field(gt=0, lt=1)
    size_usd: float = Field(gt=0)


class TradeSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: SignalAction
    side: MarketSide | None = None
    reason: str
    candidate_price: float | None = None


class PositionExitDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    should_exit: bool
    reason: ExitReason | None = None
