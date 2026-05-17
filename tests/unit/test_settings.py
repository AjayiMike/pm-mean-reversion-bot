from __future__ import annotations

import logging
from io import StringIO

import pytest
from pydantic import ValidationError

from polymarket_scalper.config.settings import AppSettings
from polymarket_scalper.utils.logging import configure_logging, get_logger, log_settings_summary


@pytest.fixture(autouse=True)
def clear_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "APP_MODE",
        "DATABASE_URL",
        "SUPPORTED_ASSETS",
        "MAX_POSITION_SIZE_USD",
        "DAILY_MAX_LOSS_USD",
        "PRIVATE_KEY",
        "FUNDER_ADDRESS",
        "BUILDER_API_KEY",
        "BUILDER_SECRET",
        "BUILDER_PASS_PHRASE",
        "RECORDER_SNAPSHOT_INTERVAL_SECONDS",
        "CRYPTO_PRICE_PROVIDER",
        "RECORDER_UNDERLYING_PRICE_PROVIDER",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_live_credentials_not_required_in_spec_mode() -> None:
    settings = AppSettings(_env_file=None)
    assert settings.app_mode.value == "spec"
    assert settings.private_key is None
    assert settings.builder_api_key is None


def test_database_url_required_in_record_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_MODE", "record")
    with pytest.raises(ValidationError):
        AppSettings(_env_file=None)


def test_database_url_not_required_in_spec_mode() -> None:
    settings = AppSettings(app_mode="spec", _env_file=None)
    assert settings.database_url is None


def test_invalid_negative_position_size_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_POSITION_SIZE_USD", "-1")
    with pytest.raises(ValidationError):
        AppSettings(_env_file=None)


def test_empty_asset_list_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPPORTED_ASSETS", "")
    with pytest.raises(ValidationError):
        AppSettings(_env_file=None)


def test_invalid_bot_mode_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_MODE", "invalid")
    with pytest.raises(ValidationError):
        AppSettings(_env_file=None)


def test_recorder_interval_must_be_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RECORDER_SNAPSHOT_INTERVAL_SECONDS", "0")
    with pytest.raises(ValidationError):
        AppSettings(_env_file=None)


def test_private_credentials_not_required_in_record_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_MODE", "record")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    settings = AppSettings(_env_file=None)
    assert settings.private_key is None
    assert settings.builder_api_key is None


def test_secrets_are_redacted_in_repr() -> None:
    settings = AppSettings(
        private_key="super-secret",
        builder_api_key="another-secret",
        _env_file=None,
    )
    rendered = repr(settings)
    assert "super-secret" not in rendered
    assert "another-secret" not in rendered


def test_secrets_are_not_logged_in_summary() -> None:
    buffer = StringIO()
    handler = logging.StreamHandler(buffer)

    configure_logging("INFO")
    handler.setFormatter(logging.getLogger().handlers[0].formatter)
    root = logging.getLogger()
    root.handlers = [handler]

    settings = AppSettings(
        private_key="super-secret",
        builder_api_key="another-secret",
        _env_file=None,
    )
    logger = get_logger("test")
    log_settings_summary(logger, settings)

    output = buffer.getvalue()
    assert "super-secret" not in output
    assert "another-secret" not in output
    assert "settings_loaded" in output
