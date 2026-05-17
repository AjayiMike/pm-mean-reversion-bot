from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session

from polymarket_scalper.recorder.db.models import (
    MarketRecord,
    MarketSnapshotRecord,
    OrderBookSnapshotRecord,
    RecorderRunRecord,
    UnderlyingPriceTickRecord,
)
from polymarket_scalper.recorder.services.models import (
    DiscoveredMarket,
    NormalizedMarketSnapshot,
    NormalizedOrderBookState,
    UnderlyingPriceTick,
)


class RecorderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_market(self, market: DiscoveredMarket) -> MarketRecord:
        record = self.session.get(MarketRecord, market.id)
        if record is None:
            record = MarketRecord(id=market.id)
            self.session.add(record)

        record.condition_id = market.condition_id
        record.question = market.question
        record.asset = market.asset.value
        record.slug = market.slug
        record.event_slug = market.event_slug
        record.start_time = market.start_time
        record.end_time = market.end_time
        record.opening_price = market.opening_price
        record.opening_price_source = market.opening_price_source
        record.opening_price_reference_timestamp = market.opening_price_reference_timestamp
        record.opening_price_reference_provider = market.opening_price_reference_provider
        record.opening_price_resolved_at = market.opening_price_resolved_at
        record.close_price = market.close_price
        record.close_price_source = market.close_price_source
        record.close_price_resolved_at = market.close_price_resolved_at
        record.up_token_id = market.up_token_id
        record.down_token_id = market.down_token_id
        record.active = market.active
        record.closed = market.closed
        record.archived = market.archived
        record.raw_payload_json = market.raw_payload_json
        return record

    def deactivate_markets_except(self, active_market_ids: set[str], as_of: datetime) -> int:
        """Mark previously-active markets inactive once the recorder rotates away from them."""
        records = list(
            self.session.scalars(select(MarketRecord).where(MarketRecord.active.is_(True)))
        )
        updated = 0
        for record in records:
            if record.id in active_market_ids:
                continue
            record.active = False
            end_time = _normalize_utc(record.end_time)
            if end_time is not None and end_time <= as_of:
                record.closed = True
            updated += 1
        return updated

    def list_active_markets(self, assets: list[str] | None = None) -> list[MarketRecord]:
        stmt: Select[tuple[MarketRecord]] = select(MarketRecord).where(
            MarketRecord.active.is_(True)
        )
        if assets:
            stmt = stmt.where(MarketRecord.asset.in_(assets))
        return list(self.session.scalars(stmt.order_by(MarketRecord.asset, MarketRecord.id)))

    def list_recently_ended_markets_missing_close_price(
        self,
        as_of: datetime,
        since: datetime,
    ) -> list[MarketRecord]:
        stmt = (
            select(MarketRecord)
            .where(
                MarketRecord.slug.is_not(None),
                MarketRecord.end_time.is_not(None),
                MarketRecord.end_time <= as_of,
                MarketRecord.end_time >= since,
                MarketRecord.close_price.is_(None),
            )
            .order_by(MarketRecord.end_time, MarketRecord.asset)
        )
        return list(self.session.scalars(stmt))

    def list_recent_markets_needing_frontend_open_upgrade(
        self,
        since: datetime,
        source: str,
    ) -> list[MarketRecord]:
        stmt = (
            select(MarketRecord)
            .where(
                MarketRecord.slug.is_not(None),
                MarketRecord.start_time.is_not(None),
                MarketRecord.start_time >= since,
                MarketRecord.opening_price_source == source,
            )
            .order_by(MarketRecord.start_time, MarketRecord.asset)
        )
        return list(self.session.scalars(stmt))

    def insert_market_snapshot(self, snapshot: NormalizedMarketSnapshot) -> MarketSnapshotRecord:
        record = MarketSnapshotRecord(**snapshot.model_dump())
        self.session.add(record)
        return record

    def insert_order_book_snapshot(
        self,
        market_id: str,
        state: NormalizedOrderBookState,
        write_raw_payloads: bool,
    ) -> OrderBookSnapshotRecord:
        record = OrderBookSnapshotRecord(
            market_id=market_id,
            token_id=state.token_id,
            side_label=state.side_label,
            timestamp=state.timestamp,
            best_bid=state.best_bid,
            best_ask=state.best_ask,
            spread=state.spread,
            depth_at_best_bid=state.depth_at_best_bid,
            depth_at_best_ask=state.depth_at_best_ask,
            total_bid_depth=state.total_bid_depth,
            total_ask_depth=state.total_ask_depth,
            raw_payload_json=state.raw_payload_json if write_raw_payloads else None,
        )
        self.session.add(record)
        return record

    def insert_underlying_price_tick(
        self,
        tick: UnderlyingPriceTick,
        write_raw_payloads: bool,
    ) -> UnderlyingPriceTickRecord:
        record = UnderlyingPriceTickRecord(
            asset=tick.asset.value,
            symbol=tick.symbol,
            timestamp=tick.timestamp,
            price=tick.price,
            provider=tick.provider,
            raw_payload_json=tick.raw_payload_json if write_raw_payloads else None,
        )
        self.session.add(record)
        return record

    def create_run(self, assets: list[str]) -> RecorderRunRecord:
        record = RecorderRunRecord(status="running", assets=",".join(assets))
        self.session.add(record)
        self.session.flush()
        return record

    def interrupt_stale_runs(self, reason: str) -> int:
        records = list(
            self.session.scalars(
                select(RecorderRunRecord).where(
                    RecorderRunRecord.status == "running",
                    RecorderRunRecord.stopped_at.is_(None),
                )
            )
        )
        now = datetime.now(UTC)
        for record in records:
            record.status = "interrupted"
            record.error_message = reason
            record.stopped_at = now
        return len(records)

    def update_run_progress(
        self,
        run_id: int,
        markets_discovered: int,
        snapshots_written: int,
    ) -> RecorderRunRecord:
        record = self.session.get(RecorderRunRecord, run_id)
        if record is None:
            raise ValueError(f"recorder run {run_id} not found")
        record.markets_discovered = markets_discovered
        record.snapshots_written = snapshots_written
        return record

    def finish_run(
        self,
        run_id: int,
        status: str,
        markets_discovered: int,
        snapshots_written: int,
        error_message: str | None = None,
    ) -> RecorderRunRecord:
        record = self.session.get(RecorderRunRecord, run_id)
        if record is None:
            raise ValueError(f"recorder run {run_id} not found")
        record.status = status
        record.markets_discovered = markets_discovered
        record.snapshots_written = snapshots_written
        record.error_message = error_message
        record.stopped_at = datetime.now(UTC)
        return record

    def latest_run(self) -> RecorderRunRecord | None:
        stmt = select(RecorderRunRecord).order_by(desc(RecorderRunRecord.started_at)).limit(1)
        return self.session.scalar(stmt)

    def latest_underlying_tick_at_or_before(
        self,
        asset: str,
        cutoff: datetime,
        excluded_provider_prefixes: tuple[str, ...] = (),
    ) -> UnderlyingPriceTickRecord | None:
        stmt = (
            select(UnderlyingPriceTickRecord)
            .where(
                UnderlyingPriceTickRecord.asset == asset,
                UnderlyingPriceTickRecord.timestamp <= cutoff,
            )
            .order_by(desc(UnderlyingPriceTickRecord.timestamp))
            .limit(1)
        )
        for prefix in excluded_provider_prefixes:
            stmt = stmt.where(~UnderlyingPriceTickRecord.provider.startswith(prefix))
        return self.session.scalar(stmt)


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
