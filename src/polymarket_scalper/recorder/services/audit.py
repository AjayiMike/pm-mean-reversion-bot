from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, select

from polymarket_scalper.recorder.db.models import (
    MarketRecord,
    MarketSnapshotRecord,
    OrderBookSnapshotRecord,
    RecorderRunRecord,
    UnderlyingPriceTickRecord,
)
from polymarket_scalper.recorder.db.session import DatabaseSessionFactory

SNAPSHOT_START_LAG_THRESHOLD_SECONDS = 30
SNAPSHOT_END_LAG_THRESHOLD_SECONDS = 5
SNAPSHOT_MAX_GAP_THRESHOLD_SECONDS = 5
UNDERLYING_START_LAG_THRESHOLD_SECONDS = 30
UNDERLYING_END_LAG_THRESHOLD_SECONDS = 30
UNDERLYING_MAX_GAP_THRESHOLD_SECONDS = 30


class MarketWindowAuditRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    asset: str
    slug: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    active: bool
    closed: bool
    opening_price_source: str | None = None
    close_price_present: bool
    snapshot_count: int
    first_snapshot: datetime | None = None
    last_snapshot: datetime | None = None
    orderbook_count: int
    first_orderbook: datetime | None = None
    last_orderbook: datetime | None = None
    underlying_tick_count: int
    first_underlying_tick: datetime | None = None
    last_underlying_tick: datetime | None = None
    covering_run_count: int
    overlapping_run_count: int
    start_lag_seconds: int | None = None
    end_lag_seconds: int | None = None
    underlying_start_lag_seconds: int | None = None
    underlying_end_lag_seconds: int | None = None
    max_snapshot_gap_seconds: int | None = None
    max_underlying_gap_seconds: int | None = None
    usable: bool
    flags: list[str]
    quality: str


class MarketWindowAuditReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    lookback_hours: int
    asset: str | None = None
    market_count: int
    active_market_count: int
    ended_market_count: int
    usable_market_count: int
    flagged_market_count: int
    rows: list[MarketWindowAuditRow]


class RecorderAuditService:
    def __init__(self, session_factory: DatabaseSessionFactory) -> None:
        self.session_factory = session_factory

    def build_report(
        self,
        lookback_hours: int = 24,
        limit: int = 50,
        asset: str | None = None,
    ) -> MarketWindowAuditReport:
        now = datetime.now(UTC)
        since = now - timedelta(hours=lookback_hours)
        asset_filter = asset.upper() if asset is not None else None

        with self.session_factory.session() as session:
            stmt = (
                select(MarketRecord)
                .where(MarketRecord.start_time.is_not(None), MarketRecord.start_time >= since)
                .order_by(desc(MarketRecord.start_time), MarketRecord.asset, MarketRecord.id)
                .limit(limit)
            )
            if asset_filter is not None:
                stmt = stmt.where(MarketRecord.asset == asset_filter)
            market_records = list(
                session.scalars(stmt)
            )

            market_ids = [record.id for record in market_records]
            snapshot_stats = self._snapshot_stats(session, market_ids)
            orderbook_stats = self._orderbook_stats(session, market_ids)
            runs = list(session.scalars(select(RecorderRunRecord).order_by(RecorderRunRecord.started_at)))

            rows = [
                self._build_row(
                    session=session,
                    market=market,
                    snapshot_stat=snapshot_stats.get(market.id),
                    orderbook_stat=orderbook_stats.get(market.id),
                    runs=runs,
                    now=now,
                )
                for market in market_records
            ]

        ended_market_count = sum(
            1
            for row in rows
            if row.end_time is not None and _normalize_utc(row.end_time) <= now
        )
        active_market_count = sum(1 for row in rows if row.quality == "active")
        usable_market_count = sum(1 for row in rows if row.usable)
        flagged_market_count = sum(1 for row in rows if row.quality == "flagged")

        return MarketWindowAuditReport(
            generated_at=now,
            lookback_hours=lookback_hours,
            asset=asset_filter,
            market_count=len(rows),
            active_market_count=active_market_count,
            ended_market_count=ended_market_count,
            usable_market_count=usable_market_count,
            flagged_market_count=flagged_market_count,
            rows=rows,
        )

    def _snapshot_stats(self, session, market_ids: list[str]) -> dict[str, tuple[int, datetime | None, datetime | None]]:
        if not market_ids:
            return {}

        rows = session.execute(
            select(
                MarketSnapshotRecord.market_id,
                func.count(MarketSnapshotRecord.id),
                func.min(MarketSnapshotRecord.timestamp),
                func.max(MarketSnapshotRecord.timestamp),
            )
            .where(MarketSnapshotRecord.market_id.in_(market_ids))
            .group_by(MarketSnapshotRecord.market_id)
        )
        return {
            market_id: (int(count), first_snapshot, last_snapshot)
            for market_id, count, first_snapshot, last_snapshot in rows
        }

    def _orderbook_stats(self, session, market_ids: list[str]) -> dict[str, tuple[int, datetime | None, datetime | None]]:
        if not market_ids:
            return {}

        rows = session.execute(
            select(
                OrderBookSnapshotRecord.market_id,
                func.count(OrderBookSnapshotRecord.id),
                func.min(OrderBookSnapshotRecord.timestamp),
                func.max(OrderBookSnapshotRecord.timestamp),
            )
            .where(OrderBookSnapshotRecord.market_id.in_(market_ids))
            .group_by(OrderBookSnapshotRecord.market_id)
        )
        return {
            market_id: (int(count), first_orderbook, last_orderbook)
            for market_id, count, first_orderbook, last_orderbook in rows
        }

    def _build_row(
        self,
        session,
        market: MarketRecord,
        snapshot_stat: tuple[int, datetime | None, datetime | None] | None,
        orderbook_stat: tuple[int, datetime | None, datetime | None] | None,
        runs: list[RecorderRunRecord],
        now: datetime,
    ) -> MarketWindowAuditRow:
        snapshot_count, first_snapshot, last_snapshot = snapshot_stat or (0, None, None)
        orderbook_count, first_orderbook, last_orderbook = orderbook_stat or (0, None, None)

        interval_start = _normalize_utc(market.start_time)
        interval_end = _normalize_utc(market.end_time)
        effective_end = interval_end or now
        snapshot_timestamps = self._market_snapshot_timestamps(session, market.id, interval_start, effective_end)
        underlying_timestamps = self._underlying_tick_timestamps(
            session,
            market.asset,
            interval_start,
            effective_end,
        )

        covering_run_count = 0
        overlapping_run_count = 0
        if interval_start is not None:
            for run in runs:
                run_start = _normalize_utc(run.started_at)
                run_stop = _normalize_utc(run.stopped_at) or now
                if run_start <= effective_end and run_stop >= interval_start:
                    overlapping_run_count += 1
                if interval_end is not None and run_start <= interval_start and run_stop >= interval_end:
                    covering_run_count += 1

        start_lag_seconds = None
        if interval_start is not None and first_snapshot is not None:
            start_lag_seconds = int((_normalize_utc(first_snapshot) - interval_start).total_seconds())

        end_lag_seconds = None
        if interval_end is not None and last_snapshot is not None and interval_end <= now:
            end_lag_seconds = int((interval_end - _normalize_utc(last_snapshot)).total_seconds())

        underlying_tick_count = len(underlying_timestamps)
        first_underlying_tick = underlying_timestamps[0] if underlying_timestamps else None
        last_underlying_tick = underlying_timestamps[-1] if underlying_timestamps else None

        underlying_start_lag_seconds = None
        if interval_start is not None and first_underlying_tick is not None:
            underlying_start_lag_seconds = int((first_underlying_tick - interval_start).total_seconds())

        underlying_end_lag_seconds = None
        if interval_end is not None and last_underlying_tick is not None and interval_end <= now:
            underlying_end_lag_seconds = int((interval_end - last_underlying_tick).total_seconds())

        max_snapshot_gap_seconds = _max_gap_seconds(snapshot_timestamps)
        max_underlying_gap_seconds = _max_gap_seconds(underlying_timestamps)

        flags: list[str] = []
        if market.opening_price is None:
            flags.append("missing_opening_price")
        if snapshot_count == 0:
            flags.append("missing_snapshots")
        if orderbook_count == 0:
            flags.append("missing_orderbooks")
        if underlying_tick_count == 0:
            flags.append("missing_underlying_ticks")
        if market.closed and market.close_price is None:
            flags.append("missing_close_price")
        if start_lag_seconds is not None and start_lag_seconds > SNAPSHOT_START_LAG_THRESHOLD_SECONDS:
            flags.append("start_lag_gt_30s")
        if end_lag_seconds is not None and end_lag_seconds > SNAPSHOT_END_LAG_THRESHOLD_SECONDS:
            flags.append("end_lag_gt_5s")
        if max_snapshot_gap_seconds is not None and max_snapshot_gap_seconds > SNAPSHOT_MAX_GAP_THRESHOLD_SECONDS:
            flags.append("snapshot_gap_gt_5s")
        if (
            underlying_start_lag_seconds is not None
            and underlying_start_lag_seconds > UNDERLYING_START_LAG_THRESHOLD_SECONDS
        ):
            flags.append("underlying_start_lag_gt_30s")
        if (
            underlying_end_lag_seconds is not None
            and underlying_end_lag_seconds > UNDERLYING_END_LAG_THRESHOLD_SECONDS
        ):
            flags.append("underlying_end_lag_gt_30s")
        if (
            max_underlying_gap_seconds is not None
            and max_underlying_gap_seconds > UNDERLYING_MAX_GAP_THRESHOLD_SECONDS
        ):
            flags.append("underlying_gap_gt_30s")
        if interval_end is not None and interval_end <= now and covering_run_count != 1:
            flags.append("run_coverage_gap")
        if overlapping_run_count > 1:
            flags.append("multi_run_overlap")
        if interval_end is not None and interval_end <= now and not market.closed:
            flags.append("ended_but_not_closed")

        quality = "active"
        usable = False
        if interval_end is not None and interval_end <= now:
            usable = not flags
            quality = "usable" if usable else "flagged"

        return MarketWindowAuditRow(
            market_id=market.id,
            asset=market.asset,
            slug=market.slug,
            start_time=market.start_time,
            end_time=market.end_time,
            active=market.active,
            closed=market.closed,
            opening_price_source=market.opening_price_source,
            close_price_present=market.close_price is not None,
            snapshot_count=snapshot_count,
            first_snapshot=first_snapshot,
            last_snapshot=last_snapshot,
            orderbook_count=orderbook_count,
            first_orderbook=first_orderbook,
            last_orderbook=last_orderbook,
            underlying_tick_count=underlying_tick_count,
            first_underlying_tick=first_underlying_tick,
            last_underlying_tick=last_underlying_tick,
            covering_run_count=covering_run_count,
            overlapping_run_count=overlapping_run_count,
            start_lag_seconds=start_lag_seconds,
            end_lag_seconds=end_lag_seconds,
            underlying_start_lag_seconds=underlying_start_lag_seconds,
            underlying_end_lag_seconds=underlying_end_lag_seconds,
            max_snapshot_gap_seconds=max_snapshot_gap_seconds,
            max_underlying_gap_seconds=max_underlying_gap_seconds,
            usable=usable,
            flags=flags,
            quality=quality,
        )

    def _market_snapshot_timestamps(
        self,
        session,
        market_id: str,
        interval_start: datetime | None,
        effective_end: datetime,
    ) -> list[datetime]:
        if interval_start is None:
            return []
        return [
            _normalize_utc(timestamp)
            for timestamp in session.scalars(
                select(MarketSnapshotRecord.timestamp)
                .where(
                    MarketSnapshotRecord.market_id == market_id,
                    MarketSnapshotRecord.timestamp >= interval_start,
                    MarketSnapshotRecord.timestamp <= effective_end,
                )
                .order_by(MarketSnapshotRecord.timestamp)
            )
        ]

    def _underlying_tick_timestamps(
        self,
        session,
        asset: str,
        interval_start: datetime | None,
        effective_end: datetime,
    ) -> list[datetime]:
        if interval_start is None:
            return []
        return [
            _normalize_utc(timestamp)
            for timestamp in session.scalars(
                select(UnderlyingPriceTickRecord.timestamp)
                .where(
                    UnderlyingPriceTickRecord.asset == asset,
                    UnderlyingPriceTickRecord.timestamp >= interval_start,
                    UnderlyingPriceTickRecord.timestamp <= effective_end,
                )
                .order_by(UnderlyingPriceTickRecord.timestamp)
            )
        ]


def format_audit_report(report: MarketWindowAuditReport) -> str:
    lines = [
        (
            "generated_at={generated_at} lookback_hours={lookback_hours} "
            "markets={market_count} active={active_market_count} ended={ended_market_count} "
            "usable={usable_market_count} flagged={flagged_market_count}"
        ).format(**report.model_dump()),
        "",
        (
            "asset | start | end | quality | usable | snaps | books | ticks | cover_runs | "
            "start_lag_s | end_lag_s | snap_gap_s | tick_gap_s | flags | slug"
        ),
    ]

    for row in report.rows:
        flags = ",".join(row.flags) if row.flags else "-"
        lines.append(
            " | ".join(
                [
                    row.asset,
                    _fmt_dt(row.start_time),
                    _fmt_dt(row.end_time),
                    row.quality,
                    str(row.usable).lower(),
                    str(row.snapshot_count),
                    str(row.orderbook_count),
                    str(row.underlying_tick_count),
                    str(row.covering_run_count),
                    _fmt_optional_int(row.start_lag_seconds),
                    _fmt_optional_int(row.end_lag_seconds),
                    _fmt_optional_int(row.max_snapshot_gap_seconds),
                    _fmt_optional_int(row.max_underlying_gap_seconds),
                    flags,
                    row.slug or "-",
                ]
            )
        )
    return "\n".join(lines)


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "-"
    return _normalize_utc(value).strftime("%Y-%m-%d %H:%M:%S")


def _fmt_optional_int(value: int | None) -> str:
    return "-" if value is None else str(value)


def _max_gap_seconds(timestamps: list[datetime]) -> int | None:
    if len(timestamps) < 2:
        return None
    return max(int((later - earlier).total_seconds()) for earlier, later in zip(timestamps, timestamps[1:]))


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
