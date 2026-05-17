from __future__ import annotations

from typing import Annotated

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from polymarket_scalper.domain.enums import AssetSymbol, BotMode


class AppSettings(BaseSettings):
    """Environment-backed application settings.

    Record mode requires only public market data configuration plus a database URL.
    Live credentials remain optional unless the application is explicitly placed in live mode.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        enable_decoding=False,
    )

    app_env: str = "development"
    app_mode: BotMode = BotMode.SPEC
    log_level: str = "INFO"
    timezone: str = "UTC"

    database_url: str | None = None
    redis_url: str | None = None

    polymarket_gamma_api_base: str = "https://gamma-api.polymarket.com"
    polymarket_clob_api_base: str = "https://clob.polymarket.com"
    polymarket_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    polymarket_rtds_url: str = "wss://ws-live-data.polymarket.com"
    polymarket_relayer_url: str = "https://relayer-v2.polymarket.com/"
    polymarket_relayer_chain_id: int = 137
    polymarket_chain_id: int = 137
    polymarket_signature_type: int = 2

    polymarket_ctf_address: str = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
    polymarket_usdc_address: str = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

    crypto_price_provider: str = "polymarket_rtds"
    crypto_price_api_key: SecretStr | None = None

    supported_assets: Annotated[
        list[AssetSymbol],
        Field(
            default_factory=lambda: [
                AssetSymbol.BTC,
                AssetSymbol.ETH,
                AssetSymbol.SOL,
                AssetSymbol.BNB,
                AssetSymbol.XRP,
            ]
        ),
    ]
    max_position_size_usd: float = Field(default=10.0, gt=0)
    daily_max_loss_usd: float = Field(default=50.0, gt=0)

    recorder_snapshot_interval_seconds: int = Field(default=1, gt=0)
    recorder_market_refresh_interval_seconds: int = Field(default=60, gt=0)
    recorder_max_markets_per_asset: int = Field(default=1, ge=1)
    recorder_write_raw_payloads: bool = True
    recorder_underlying_price_provider: str = "polymarket_rtds"

    builder_api_key: SecretStr | None = None
    builder_secret: SecretStr | None = None
    builder_pass_phrase: SecretStr | None = None
    funder_address: str | None = None
    private_key: SecretStr | None = None

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")
        return normalized

    @field_validator("supported_assets", mode="before")
    @classmethod
    def parse_supported_assets(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator(
        "database_url",
        "redis_url",
        "funder_address",
        mode="before",
    )
    @classmethod
    def empty_strings_to_none_for_plain_fields(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "crypto_price_api_key",
        "builder_api_key",
        "builder_secret",
        "builder_pass_phrase",
        "private_key",
        mode="before",
    )
    @classmethod
    def empty_strings_to_none_for_secret_fields(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "crypto_price_provider",
        "recorder_underlying_price_provider",
        mode="before",
    )
    @classmethod
    def normalize_provider_name(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            return "polymarket_rtds"
        return value.strip().lower()

    @field_validator("crypto_price_provider", "recorder_underlying_price_provider")
    @classmethod
    def validate_provider_name(cls, value: str) -> str:
        allowed = {"polymarket_rtds", "mock"}
        if value not in allowed:
            raise ValueError(f"underlying price provider must be one of {sorted(allowed)}")
        return value

    @model_validator(mode="after")
    def validate_runtime_requirements(self) -> AppSettings:
        if not self.supported_assets:
            raise ValueError("SUPPORTED_ASSETS cannot be empty")

        if self.app_mode is BotMode.RECORD and not self.database_url:
            raise ValueError("DATABASE_URL is required when APP_MODE=record")

        if self.crypto_price_provider != self.recorder_underlying_price_provider:
            raise ValueError(
                "CRYPTO_PRICE_PROVIDER and RECORDER_UNDERLYING_PRICE_PROVIDER must match"
            )

        if self.app_mode is BotMode.LIVE:
            required = {
                "BUILDER_API_KEY": self.builder_api_key,
                "BUILDER_SECRET": self.builder_secret,
                "BUILDER_PASS_PHRASE": self.builder_pass_phrase,
                "PRIVATE_KEY": self.private_key,
                "FUNDER_ADDRESS": self.funder_address,
            }
            missing = [name for name, value in required.items() if not self._has_value(value)]
            if missing:
                raise ValueError(f"live mode requires credentials: {', '.join(missing)}")
        return self

    @staticmethod
    def _has_value(value: SecretStr | str | None) -> bool:
        if value is None:
            return False
        if isinstance(value, SecretStr):
            return bool(value.get_secret_value())
        return bool(value.strip())

    def redacted_summary(self) -> dict[str, object]:
        return {
            "app_env": self.app_env,
            "app_mode": self.app_mode.value,
            "log_level": self.log_level.upper(),
            "timezone": self.timezone,
            "supported_assets": [asset.value for asset in self.supported_assets],
            "database_configured": bool(self.database_url),
            "redis_configured": bool(self.redis_url),
            "underlying_price_provider": self.recorder_underlying_price_provider,
            "recorder_snapshot_interval_seconds": self.recorder_snapshot_interval_seconds,
            "recorder_market_refresh_interval_seconds": (
                self.recorder_market_refresh_interval_seconds
            ),
            "recorder_max_markets_per_asset": self.recorder_max_markets_per_asset,
            "builder_credentials_configured": all(
                self._has_value(value)
                for value in [
                    self.builder_api_key,
                    self.builder_secret,
                    self.builder_pass_phrase,
                ]
            ),
            "wallet_configured": self._has_value(self.funder_address)
            and self._has_value(self.private_key),
        }
