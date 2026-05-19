from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from polymarket_scalper.config.settings import AppSettings
from polymarket_scalper.recorder.clients.frontend import PolymarketFrontendClient
from polymarket_scalper.recorder.clients.gamma import GammaClient
from polymarket_scalper.recorder.clients.market_websocket import PolymarketMarketWebSocketClient
from polymarket_scalper.recorder.db.repository import RecorderRepository
from polymarket_scalper.recorder.db.session import DatabaseSessionFactory
from polymarket_scalper.recorder.feeds.factory import build_underlying_price_feed
from polymarket_scalper.recorder.feeds.polymarket_rtds import PolymarketRtdsPriceFeed
from polymarket_scalper.recorder.services.discovery import MarketDiscoveryService
from polymarket_scalper.recorder.services.models import DiscoveredMarket, RecorderHealth
from polymarket_scalper.recorder.services.opening_price import (
    OPENING_PRICE_SOURCE_UNDERLYING_TICK,
    OpeningPriceResolver,
)
from polymarket_scalper.recorder.services.orderbook import OrderBookStore
from polymarket_scalper.recorder.services.snapshots import build_market_snapshot
from polymarket_scalper.utils.logging import get_logger

INITIAL_MARKET_DATA_WAIT_SECONDS = 3.0
INITIAL_UNDERLYING_DATA_WAIT_SECONDS = 3.0
FRONTEND_RECONCILIATION_INTERVAL_SECONDS = 15.0
FRONTEND_RECONCILIATION_LOOKBACK = timedelta(minutes=30)
SHUTDOWN_FRONTEND_RECONCILIATION_TIMEOUT_SECONDS = 15.0


class RecorderService:
    def __init__(self, settings: AppSettings) -> None:
        if settings.database_url is None:
            raise ValueError("DATABASE_URL is required for record mode")

        self.settings = settings
        self.logger = get_logger(__name__)
        self.db = DatabaseSessionFactory(settings.database_url)
        self.gamma_client = GammaClient(settings.polymarket_gamma_api_base)
        self.frontend_client = PolymarketFrontendClient()
        self.discovery = MarketDiscoveryService(self.gamma_client)
        self.opening_price_resolver = OpeningPriceResolver(self.db, self.frontend_client)
        self.price_feed = build_underlying_price_feed(
            settings.recorder_underlying_price_provider,
            rtds_url=settings.polymarket_rtds_url,
            assets=settings.supported_assets,
            message_handler=self.handle_underlying_price_message,
        )
        self.order_books = OrderBookStore()
        self.discovered_markets: list[DiscoveredMarket] = []
        self.last_market_refresh_time: datetime | None = None
        self.last_polymarket_message_time: datetime | None = None
        self.last_underlying_price_tick_time: datetime | None = None
        self.snapshots_written = 0
        self._run_id: int | None = None
        self._active_market_signature: tuple[str, ...] = ()
        self._shutdown_reason: str | None = None
        self._last_frontend_reconciliation_time: datetime | None = None

    async def refresh_markets(self) -> list[DiscoveredMarket]:
        # The recorder only tracks the currently-live quarter-hour market for each
        # supported asset. Every refresh therefore has two jobs:
        # 1. upsert the new current market set
        # 2. retire any market we just rotated away from
        markets = await self.discovery.discover_markets(
            supported_assets=self.settings.supported_assets,
            max_markets_per_asset=self.settings.recorder_max_markets_per_asset,
        )
        if not markets and self.discovered_markets:
            self.logger.warning("market_refresh_empty_result")
            return self.discovered_markets
        await self.opening_price_resolver.resolve_markets(markets)
        with self.db.session() as session:
            repo = RecorderRepository(session)
            for market in markets:
                repo.upsert_market(market)
            repo.deactivate_markets_except(
                {market.id for market in markets},
                as_of=datetime.now(UTC),
            )
            session.commit()
        self.discovered_markets = markets
        self._active_market_signature = self._market_signature(markets)
        self.order_books.retain_tokens(set(self._market_token_ids(markets)))
        self.last_market_refresh_time = datetime.now(UTC)
        self._update_run_progress()
        return markets

    async def discover_only(self) -> list[DiscoveredMarket]:
        markets = await self.refresh_markets()
        self.logger.info("discover_only_completed", extra={"count": len(markets)})
        return markets

    def handle_market_message(self, message: dict[str, Any]) -> None:
        token_map = {market.up_token_id: "UP" for market in self.discovered_markets} | {
            market.down_token_id: "DOWN" for market in self.discovered_markets
        }
        self.order_books.update_from_message(message, token_map)
        self.last_polymarket_message_time = datetime.now(UTC)

    def handle_underlying_price_message(self, message: dict[str, Any]) -> None:
        if isinstance(self.price_feed, PolymarketRtdsPriceFeed):
            tick = self.price_feed.handle_message(message)
            if tick is None:
                return
            self._persist_underlying_tick(tick)
            self.last_underlying_price_tick_time = tick.timestamp

    async def write_snapshots_once(self) -> int:
        written = 0
        with self.db.session() as session:
            repo = RecorderRepository(session)
            for market in self.discovered_markets:
                snapshot = build_market_snapshot(market, self.order_books, self.price_feed)
                repo.insert_market_snapshot(snapshot)
                if up_state := self.order_books.latest(market.up_token_id):
                    repo.insert_order_book_snapshot(
                        market.id,
                        up_state,
                        self.settings.recorder_write_raw_payloads,
                    )
                if down_state := self.order_books.latest(market.down_token_id):
                    repo.insert_order_book_snapshot(
                        market.id,
                        down_state,
                        self.settings.recorder_write_raw_payloads,
                    )
                written += 1
            session.commit()
        self.snapshots_written += written
        self._update_run_progress()
        self.logger.info("snapshot_batch_written", extra={"count": written})
        return written

    async def run_once(self) -> None:
        await self.price_feed.connect()
        markets = await self.refresh_markets()
        self.logger.info(
            "recorder_markets_loaded",
            extra={"count": len(markets), "provider": self.price_feed.provider_name},
        )
        market_ws_client = self._build_market_ws_client()
        market_ws_task = None
        try:
            if market_ws_client is not None:
                market_ws_task = asyncio.create_task(market_ws_client.connect_once())
                await self._wait_for_initial_market_data()
            await self._wait_for_initial_underlying_data()
            await self._persist_available_underlying_ticks()
            await self.write_snapshots_once()
        finally:
            if market_ws_task is not None:
                market_ws_task.cancel()
                await asyncio.gather(market_ws_task, return_exceptions=True)
            await self.price_feed.disconnect()

    async def health(self) -> RecorderHealth:
        database_reachable = False
        try:
            with self.db.session() as session:
                session.execute(text("SELECT 1"))
                database_reachable = True
        except Exception:  # noqa: BLE001
            database_reachable = False

        return RecorderHealth(
            database_reachable=database_reachable,
            active_underlying_price_provider=self.settings.recorder_underlying_price_provider,
            last_market_refresh_time=self.last_market_refresh_time,
            active_markets_count=len(self.discovered_markets),
            last_polymarket_message_time=self.last_polymarket_message_time,
            last_underlying_price_tick_time=self.last_underlying_price_tick_time,
            snapshots_written=self.snapshots_written,
        )

    @asynccontextmanager
    async def recorder_run(self):
        with self.db.session() as session:
            repo = RecorderRepository(session)
            stale_runs = repo.interrupt_stale_runs("superseded_by_new_recorder_run")
            run = repo.create_run([asset.value for asset in self.settings.supported_assets])
            session.commit()
            self._run_id = run.id
        if stale_runs:
            self.logger.warning("stale_recorder_runs_interrupted", extra={"count": stale_runs})
        try:
            yield
        except BaseException as exc:
            is_interrupted = isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError))
            status = "interrupted" if is_interrupted else "failed"
            error_message = None if status == "interrupted" else self._describe_exception(exc)
            self._finalize_run(status, error_message=error_message)
            raise
        else:
            status = "interrupted" if self._shutdown_reason is not None else "completed"
            self._finalize_run(status, error_message=self._shutdown_reason)

    def _finalize_run(self, status: str, error_message: str | None = None) -> None:
        if self._run_id is None:
            return
        with self.db.session() as session:
            repo = RecorderRepository(session)
            repo.finish_run(
                run_id=self._run_id,
                status=status,
                markets_discovered=len(self.discovered_markets),
                snapshots_written=self.snapshots_written,
                error_message=error_message,
            )
            session.commit()
        self._run_id = None

    def _update_run_progress(self) -> None:
        if self._run_id is None:
            return
        with self.db.session() as session:
            repo = RecorderRepository(session)
            repo.update_run_progress(
                run_id=self._run_id,
                markets_discovered=len(self.discovered_markets),
                snapshots_written=self.snapshots_written,
            )
            session.commit()

    def request_shutdown(self, reason: str) -> None:
        self._shutdown_reason = reason

    def _describe_exception(self, exc: BaseException) -> str:
        message = str(exc).strip()
        if message:
            return f"{exc.__class__.__name__}: {message}"
        return exc.__class__.__name__

    async def run_loop(self, stop_event: asyncio.Event | None = None) -> None:
        async with self.recorder_run():
            await self.price_feed.connect()
            await self.refresh_markets()
            market_ws_client = self._build_market_ws_client()
            self.logger.info(
                "recorder_started",
                extra={
                    "provider": self.price_feed.provider_name,
                    "market_count": len(self.discovered_markets),
                },
            )
            market_ws_task = None
            try:
                if market_ws_client is not None:
                    market_ws_task = asyncio.create_task(market_ws_client.connect_once())
                    await self._wait_for_initial_market_data()
                await self._wait_for_initial_underlying_data()
                while True:
                    if stop_event is not None and stop_event.is_set():
                        self.logger.info(
                            "recorder_stopping",
                            extra={"reason": self._shutdown_reason},
                        )
                        break
                    market_ws_task = await self._refresh_market_subscriptions_if_needed(
                        market_ws_task
                    )
                    await self._reconcile_frontend_market_metadata_if_needed()
                    await self._persist_available_underlying_ticks()
                    await self.write_snapshots_once()
                    if stop_event is None:
                        await asyncio.sleep(self.settings.recorder_snapshot_interval_seconds)
                        continue
                    try:
                        await asyncio.wait_for(
                            stop_event.wait(),
                            timeout=self.settings.recorder_snapshot_interval_seconds,
                        )
                    except TimeoutError:
                        continue
            finally:
                await self._reconcile_frontend_market_metadata_on_shutdown()
                if market_ws_task is not None:
                    market_ws_task.cancel()
                    await asyncio.gather(market_ws_task, return_exceptions=True)
                await self.price_feed.disconnect()

    def _build_market_ws_client(self) -> PolymarketMarketWebSocketClient | None:
        asset_ids = self._market_token_ids(self.discovered_markets)
        if not asset_ids:
            return None
        return PolymarketMarketWebSocketClient(
            endpoint=self.settings.polymarket_ws_url,
            asset_ids=asset_ids,
            handler=self.handle_market_message,
        )

    async def _wait_for_initial_market_data(self) -> None:
        deadline = asyncio.get_running_loop().time() + INITIAL_MARKET_DATA_WAIT_SECONDS
        while asyncio.get_running_loop().time() < deadline:
            if self.order_books.latest_all():
                self.logger.info(
                    "initial_market_data_received",
                    extra={"books": len(self.order_books.latest_all())},
                )
                return
            await asyncio.sleep(0.2)
        self.logger.warning("initial_market_data_timeout")

    async def _wait_for_initial_underlying_data(self) -> None:
        if not isinstance(self.price_feed, PolymarketRtdsPriceFeed):
            return
        deadline = asyncio.get_running_loop().time() + INITIAL_UNDERLYING_DATA_WAIT_SECONDS
        while asyncio.get_running_loop().time() < deadline:
            tick_count = sum(
                1
                for asset in self.settings.supported_assets
                if self.price_feed.latest_tick(asset) is not None
            )
            if tick_count:
                self.logger.info("initial_underlying_data_received", extra={"ticks": tick_count})
                return
            await asyncio.sleep(0.2)
        self.logger.warning("initial_underlying_data_timeout")

    async def _persist_available_underlying_ticks(self) -> int:
        # RTDS ticks are persisted on websocket receipt in
        # `handle_underlying_price_message()`. Re-reading the cached latest tick
        # here would double-write the same `(asset, timestamp, provider)` tuple.
        if isinstance(self.price_feed, PolymarketRtdsPriceFeed):
            return 0

        written = 0
        for asset in self.settings.supported_assets:
            tick = self.price_feed.latest_tick(asset)
            if tick is None:
                continue
            self._persist_underlying_tick(tick)
            self.last_underlying_price_tick_time = tick.timestamp
            written += 1
        if written:
            self.logger.info("underlying_ticks_persisted", extra={"count": written})
        return written

    def _persist_underlying_tick(self, tick) -> None:
        with self.db.session() as session:
            repo = RecorderRepository(session)
            repo.insert_underlying_price_tick(tick, self.settings.recorder_write_raw_payloads)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()

    def _market_token_ids(self, markets: list[DiscoveredMarket]) -> list[str]:
        return [
            token_id
            for market in markets
            for token_id in (market.up_token_id, market.down_token_id)
        ]

    def _market_signature(self, markets: list[DiscoveredMarket]) -> tuple[str, ...]:
        return tuple(sorted(market.slug or market.id for market in markets))

    def _should_refresh_markets(self, now: datetime) -> bool:
        if self.last_market_refresh_time is None:
            return True
        # The primary rollover trigger is time-based: the moment the current market
        # window ends, the recorder should refresh on the next snapshot cycle.
        if any(
            market.end_time is not None and market.end_time <= now
            for market in self.discovered_markets
        ):
            return True
        # `closePrice` is a stronger "this market is over" signal when the frontend
        # has already exposed it.
        if any(market.close_price is not None for market in self.discovered_markets):
            return True
        elapsed = (now - self.last_market_refresh_time).total_seconds()
        return elapsed >= self.settings.recorder_market_refresh_interval_seconds

    async def _refresh_market_subscriptions_if_needed(
        self,
        market_ws_task: asyncio.Task[None] | None,
    ) -> asyncio.Task[None] | None:
        now = datetime.now(UTC)
        if not self._should_refresh_markets(now):
            return market_ws_task

        previous_signature = self._active_market_signature
        try:
            markets = await self.refresh_markets()
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "market_refresh_failed",
                extra={"error": self._describe_exception(exc)},
            )
            return market_ws_task
        new_signature = self._market_signature(markets)
        if new_signature == previous_signature:
            return market_ws_task

        self.logger.info(
            "active_market_set_changed",
            extra={"previous": previous_signature, "current": new_signature},
        )
        if market_ws_task is not None:
            market_ws_task.cancel()
            await asyncio.gather(market_ws_task, return_exceptions=True)

        market_ws_client = self._build_market_ws_client()
        if market_ws_client is None:
            return None

        new_task = asyncio.create_task(market_ws_client.connect_once())
        await self._wait_for_initial_market_data()
        return new_task

    async def _reconcile_frontend_market_metadata_if_needed(self) -> None:
        now = datetime.now(UTC)
        if self._last_frontend_reconciliation_time is not None:
            elapsed = (now - self._last_frontend_reconciliation_time).total_seconds()
            if elapsed < FRONTEND_RECONCILIATION_INTERVAL_SECONDS:
                return
        await self._reconcile_frontend_market_metadata(now)

    async def _reconcile_frontend_market_metadata_on_shutdown(self) -> None:
        # Shutdown is the last safe place to upgrade tick-derived opening prices and
        # backfill close prices before the process loses network access.
        try:
            await asyncio.wait_for(
                self._reconcile_frontend_market_metadata(datetime.now(UTC)),
                timeout=SHUTDOWN_FRONTEND_RECONCILIATION_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            self.logger.warning("frontend_market_reconciliation_timeout_on_shutdown")
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "frontend_market_reconciliation_failed_on_shutdown",
                extra={"error": str(exc)},
            )

    async def _reconcile_frontend_market_metadata(self, now: datetime) -> None:
        candidates = self._load_frontend_reconciliation_candidates(now)
        if not candidates:
            self._last_frontend_reconciliation_time = now
            return

        reconciled = 0
        with self.db.session() as session:
            repo = RecorderRepository(session)
            for market in candidates:
                await self.opening_price_resolver.resolve_market(market)
                repo.upsert_market(market)
                reconciled += 1
            session.commit()

        # Keep in-memory active markets consistent when an upgrade landed for a market
        # that is still part of the currently subscribed set.
        by_id = {market.id: market for market in candidates}
        self.discovered_markets = [
            by_id.get(market.id, market) for market in self.discovered_markets
        ]
        self._last_frontend_reconciliation_time = now
        self.logger.info(
            "frontend_market_reconciliation_completed",
            extra={"count": reconciled},
        )

    def _load_frontend_reconciliation_candidates(
        self,
        now: datetime,
    ) -> list[DiscoveredMarket]:
        since = now - FRONTEND_RECONCILIATION_LOOKBACK
        with self.db.session() as session:
            repo = RecorderRepository(session)
            ended = repo.list_recently_ended_markets_missing_close_price(now, since)
            tick_open = repo.list_recent_markets_needing_frontend_open_upgrade(
                since=since,
                source=OPENING_PRICE_SOURCE_UNDERLYING_TICK,
            )

        records_by_id = {record.id: record for record in [*ended, *tick_open]}
        return [self._record_to_discovered_market(record) for record in records_by_id.values()]

    def _record_to_discovered_market(self, record) -> DiscoveredMarket:
        return DiscoveredMarket(
            id=record.id,
            condition_id=record.condition_id,
            question=record.question,
            asset=record.asset,
            slug=record.slug,
            event_slug=record.event_slug,
            start_time=record.start_time,
            end_time=record.end_time,
            opening_price=record.opening_price,
            opening_price_source=record.opening_price_source,
            opening_price_reference_timestamp=record.opening_price_reference_timestamp,
            opening_price_reference_provider=record.opening_price_reference_provider,
            opening_price_resolved_at=record.opening_price_resolved_at,
            close_price=record.close_price,
            close_price_source=record.close_price_source,
            close_price_resolved_at=record.close_price_resolved_at,
            up_token_id=record.up_token_id,
            down_token_id=record.down_token_id,
            active=record.active,
            closed=record.closed,
            archived=record.archived,
            raw_payload_json=record.raw_payload_json,
        )
