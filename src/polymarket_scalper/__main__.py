from __future__ import annotations

import argparse
import asyncio
import json
import signal

from polymarket_scalper.config.settings import AppSettings
from polymarket_scalper.domain.enums import BotMode
from polymarket_scalper.recorder.services.recorder import RecorderService
from polymarket_scalper.utils.logging import configure_logging, get_logger, log_settings_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Polymarket scalper project entrypoint")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["spec", "discover", "record", "record-once", "health"],
    )
    return parser


async def run_record_mode(settings: AppSettings, once: bool = False) -> None:
    service = RecorderService(settings)
    if once:
        async with service.recorder_run():
            await service.run_once()
        return

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_shutdown(signal_name: str) -> None:
        service.request_shutdown(signal_name)
        logger = get_logger(__name__)
        logger.info("recorder_shutdown_requested", extra={"signal": signal_name})
        stop_event.set()

    registered_signals: list[signal.Signals] = []
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_shutdown, sig.name)
            registered_signals.append(sig)
        except NotImplementedError:
            continue

    try:
        await service.run_loop(stop_event=stop_event)
    finally:
        for sig in registered_signals:
            loop.remove_signal_handler(sig)


async def run_discover_mode(settings: AppSettings) -> list[dict[str, object]]:
    service = RecorderService(settings)
    markets = await service.discover_only()
    return [
        {
            "id": market.id,
            "asset": market.asset.value,
            "slug": market.slug,
            "question": market.question,
            "up_token_id": market.up_token_id,
            "down_token_id": market.down_token_id,
            "start_time": market.start_time.isoformat() if market.start_time else None,
            "end_time": market.end_time.isoformat() if market.end_time else None,
            "opening_price": market.opening_price,
            "opening_price_source": market.opening_price_source,
            "opening_price_reference_timestamp": (
                market.opening_price_reference_timestamp.isoformat()
                if market.opening_price_reference_timestamp
                else None
            ),
            "opening_price_reference_provider": market.opening_price_reference_provider,
            "opening_price_resolved_at": (
                market.opening_price_resolved_at.isoformat()
                if market.opening_price_resolved_at
                else None
            ),
            "close_price": market.close_price,
            "close_price_source": market.close_price_source,
            "close_price_resolved_at": (
                market.close_price_resolved_at.isoformat()
                if market.close_price_resolved_at
                else None
            ),
        }
        for market in markets
    ]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = AppSettings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)
    log_settings_summary(logger, settings)

    command = args.command or settings.app_mode.value
    if command == "spec" or settings.app_mode is BotMode.SPEC and args.command is None:
        logger.info("phase_2_project_loaded", extra={"mode": settings.app_mode.value})
        return

    if command == "discover":
        discovered = asyncio.run(run_discover_mode(settings))
        print(json.dumps(discovered, indent=2))
        return

    if command == "record":
        asyncio.run(run_record_mode(settings, once=False))
        return

    if command == "record-once":
        try:
            asyncio.run(run_record_mode(settings, once=True))
        except KeyboardInterrupt:
            logger.info("recorder_interrupted")
        return

    if command == "health":
        service = RecorderService(settings)
        health = asyncio.run(service.health())
        print(json.dumps(health.model_dump(mode="json"), indent=2, default=str))
        return

    parser.error(f"unsupported command: {command}")


if __name__ == "__main__":
    main()
