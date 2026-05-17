from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from polymarket_scalper.domain.enums import AssetSymbol, BotMode

UnitInterval = Annotated[float, Field(gt=0, lt=1)]
ProbabilityInterval = Annotated[float, Field(ge=0, le=1)]
PositiveUsd = Annotated[float, Field(gt=0)]


class BotConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: BotMode = BotMode.SPEC
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return normalized


class AssetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supported: list[AssetSymbol] = Field(
        default_factory=lambda: [
            AssetSymbol.BTC,
            AssetSymbol.ETH,
            AssetSymbol.SOL,
            AssetSymbol.BNB,
            AssetSymbol.XRP,
        ]
    )

    @field_validator("supported")
    @classmethod
    def validate_supported_assets(cls, value: list[AssetSymbol]) -> list[AssetSymbol]:
        if not value:
            raise ValueError("supported assets cannot be empty")
        return value


class EntryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_entry_price: ProbabilityInterval = 0.35
    min_time_remaining_seconds: int = Field(default=240, gt=0)
    max_time_remaining_seconds: int = Field(default=720, gt=0)
    max_abs_distance_from_open_bps: int = Field(default=40, gt=0)
    max_spread: ProbabilityInterval = 0.03
    min_depth_multiplier: float = Field(default=3.0, ge=1.0)
    require_momentum_confirmation: bool = True

    @model_validator(mode="after")
    def validate_time_window(self) -> EntryConfig:
        if self.min_time_remaining_seconds >= self.max_time_remaining_seconds:
            raise ValueError(
                "min_time_remaining_seconds must be less than max_time_remaining_seconds"
            )
        return self


class ExitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    take_profit_pct: UnitInterval = 0.15
    stop_loss_pct: UnitInterval = 0.25
    force_exit_time_remaining_seconds: int = Field(default=180, gt=0)
    use_invalidation_exit: bool = True


class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_position_size_usd: PositiveUsd = 10.0
    max_trades_per_market: int = Field(default=2, ge=1)
    max_open_positions: int = Field(default=2, ge=1)
    daily_max_loss_usd: PositiveUsd = 50.0
    max_loss_per_market_usd: PositiveUsd = 10.0


class ExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prefer_limit_orders: bool = True
    allow_marketable_limit_orders: bool = True
    max_slippage: ProbabilityInterval = 0.02
    cancel_unfilled_order_after_seconds: int = Field(default=10, gt=0)


class RecorderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_interval_seconds: int = Field(default=1, gt=0)
    market_refresh_interval_seconds: int = Field(default=60, gt=0)
    max_markets_per_asset: int = Field(default=1, ge=1)
    write_raw_payloads: bool = True
    underlying_price_provider: str = "polymarket_rtds"

    @field_validator("underlying_price_provider")
    @classmethod
    def validate_underlying_price_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"polymarket_rtds", "mock"}
        if normalized not in allowed:
            raise ValueError(f"underlying_price_provider must be one of {sorted(allowed)}")
        return normalized


class StrategyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bot: BotConfig = Field(default_factory=BotConfig)
    assets: AssetConfig = Field(default_factory=AssetConfig)
    entry: EntryConfig = Field(default_factory=EntryConfig)
    exit: ExitConfig = Field(default_factory=ExitConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    recorder: RecorderConfig = Field(default_factory=RecorderConfig)
