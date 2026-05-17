from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymarket_scalper.config.strategy import StrategyConfig


def test_valid_default_strategy_configuration() -> None:
    config = StrategyConfig()
    assert config.bot.mode.value == "spec"
    assert config.entry.max_entry_price == 0.35
    assert len(config.assets.supported) == 5
    assert config.recorder.snapshot_interval_seconds == 1


def test_invalid_entry_price_above_one_fails() -> None:
    with pytest.raises(ValidationError):
        StrategyConfig(entry={"max_entry_price": 1.1})


def test_min_time_remaining_must_be_less_than_max() -> None:
    with pytest.raises(ValidationError):
        StrategyConfig(
            entry={
                "min_time_remaining_seconds": 720,
                "max_time_remaining_seconds": 720,
            }
        )
