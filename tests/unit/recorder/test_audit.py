from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from polymarket_scalper.domain.enums import AssetSymbol
from polymarket_scalper.recorder.db.base import Base
from polymarket_scalper.recorder.db.repository import RecorderRepository
from polymarket_scalper.recorder.db.session import DatabaseSessionFactory
from polymarket_scalper.recorder.services.audit import RecorderAuditService
from polymarket_scalper.recorder.services.models import (
    DiscoveredMarket,
    NormalizedMarketSnapshot,
    NormalizedOrderBookState,
    OrderBookLevel,
    UnderlyingPriceTick,
)


def test_audit_report_flags_run_coverage_and_missing_close_price(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = RecorderRepository(session)
        run = repo.create_run(["BTC"])
        session.flush()
        repo.finish_run(
            run.id,
            status="failed",
            markets_discovered=1,
            snapshots_written=10,
            error_message="boom",
        )

        market = DiscoveredMarket(
            id="market-1",
            question="BTC 15-minute market: up or down?",
            asset=AssetSymbol.BTC,
            slug="btc-updown-15m-1",
            start_time=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
            end_time=datetime(2026, 5, 24, 12, 15, tzinfo=UTC),
            opening_price=108000.0,
            opening_price_source="frontend",
            up_token_id="up-token-1",
            down_token_id="down-token-1",
            active=False,
            closed=True,
        )
        repo.upsert_market(market)
        repo.insert_market_snapshot(
            NormalizedMarketSnapshot(
                market_id="market-1",
                timestamp=datetime(2026, 5, 24, 12, 0, 10, tzinfo=UTC),
                asset="BTC",
                opening_price=108000.0,
                underlying_price=108010.0,
                time_remaining_seconds=890,
                source="test",
            )
        )
        repo.insert_market_snapshot(
            NormalizedMarketSnapshot(
                market_id="market-1",
                timestamp=datetime(2026, 5, 24, 12, 14, 50, tzinfo=UTC),
                asset="BTC",
                opening_price=108000.0,
                underlying_price=108050.0,
                time_remaining_seconds=10,
                source="test",
            )
        )
        repo.insert_order_book_snapshot(
            "market-1",
            NormalizedOrderBookState(
                token_id="up-token-1",
                side_label="UP",
                timestamp=datetime(2026, 5, 24, 12, 0, 10, tzinfo=UTC),
                bids=[OrderBookLevel(price=0.4, size=100)],
                asks=[OrderBookLevel(price=0.41, size=120)],
            ),
            write_raw_payloads=False,
        )
        repo.insert_underlying_price_tick(
            UnderlyingPriceTick(
                asset=AssetSymbol.BTC,
                symbol="btcusdt",
                timestamp=datetime(2026, 5, 24, 12, 0, 15, tzinfo=UTC),
                price=108020.0,
                provider="mock",
            ),
            write_raw_payloads=False,
        )
        session.commit()

    report = RecorderAuditService(DatabaseSessionFactory(database_url)).build_report(
        lookback_hours=24,
        limit=10,
    )

    assert report.market_count == 1
    row = report.rows[0]
    assert row.market_id == "market-1"
    assert row.snapshot_count == 2
    assert row.orderbook_count == 1
    assert row.underlying_tick_count == 1
    assert row.usable is False
    assert row.quality == "flagged"
    assert "missing_close_price" in row.flags
    assert "run_coverage_gap" in row.flags


def test_audit_report_marks_active_windows_active(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-active.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = RecorderRepository(session)
        repo.create_run(["ETH"])
        market = DiscoveredMarket(
            id="market-2",
            question="ETH 15-minute market: up or down?",
            asset=AssetSymbol.ETH,
            slug="eth-updown-15m-1",
            start_time=datetime.now(UTC),
            end_time=None,
            opening_price=2500.0,
            opening_price_source="frontend",
            up_token_id="up-token-2",
            down_token_id="down-token-2",
        )
        repo.upsert_market(market)
        session.commit()

    report = RecorderAuditService(DatabaseSessionFactory(database_url)).build_report(
        lookback_hours=24,
        limit=10,
    )

    assert report.market_count == 1
    assert report.rows[0].quality == "active"
    assert report.rows[0].usable is False


def test_audit_report_can_filter_by_asset(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-asset.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = RecorderRepository(session)
        repo.create_run(["BTC", "ETH"])

        btc_market = DiscoveredMarket(
            id="btc-market",
            question="BTC 15-minute market: up or down?",
            asset=AssetSymbol.BTC,
            slug="btc-updown-15m-filter",
            start_time=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
            end_time=datetime(2026, 5, 24, 12, 15, tzinfo=UTC),
            opening_price=108000.0,
            opening_price_source="frontend",
            close_price=108100.0,
            close_price_source="frontend",
            up_token_id="up-token-btc",
            down_token_id="down-token-btc",
            active=False,
            closed=True,
        )
        eth_market = DiscoveredMarket(
            id="eth-market",
            question="ETH 15-minute market: up or down?",
            asset=AssetSymbol.ETH,
            slug="eth-updown-15m-filter",
            start_time=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
            end_time=datetime(2026, 5, 24, 12, 15, tzinfo=UTC),
            opening_price=2500.0,
            opening_price_source="frontend",
            close_price=2510.0,
            close_price_source="frontend",
            up_token_id="up-token-eth",
            down_token_id="down-token-eth",
            active=False,
            closed=True,
        )
        repo.upsert_market(btc_market)
        repo.upsert_market(eth_market)
        session.commit()

    service = RecorderAuditService(DatabaseSessionFactory(database_url))
    report = service.build_report(lookback_hours=24, limit=10, asset="BTC")

    assert report.asset == "BTC"
    assert report.market_count == 1
    assert report.rows[0].asset == "BTC"


def test_audit_report_marks_complete_windows_usable(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-usable.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = RecorderRepository(session)
        run = repo.create_run(["BTC"])
        session.flush()
        run.started_at = datetime(2026, 5, 24, 12, 0, 0, tzinfo=UTC)
        repo.finish_run(
            run.id,
            status="completed",
            markets_discovered=1,
            snapshots_written=3,
        )
        run.stopped_at = datetime(2026, 5, 24, 12, 15, 5, tzinfo=UTC)

        market = DiscoveredMarket(
            id="market-usable",
            question="BTC 15-minute market: up or down?",
            asset=AssetSymbol.BTC,
            slug="btc-updown-15m-usable",
            start_time=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
            end_time=datetime(2026, 5, 24, 12, 15, tzinfo=UTC),
            opening_price=108000.0,
            opening_price_source="frontend",
            close_price=108100.0,
            close_price_source="frontend",
            up_token_id="up-token-usable",
            down_token_id="down-token-usable",
            active=False,
            closed=True,
        )
        repo.upsert_market(market)
        for offset_seconds in range(5, 896, 5):
            repo.insert_market_snapshot(
                NormalizedMarketSnapshot(
                    market_id="market-usable",
                    timestamp=datetime(2026, 5, 24, 12, 0, 0, tzinfo=UTC)
                    + timedelta(seconds=offset_seconds),
                    asset="BTC",
                    opening_price=108000.0,
                    underlying_price=108010.0 + offset_seconds,
                    time_remaining_seconds=max(0, 900 - offset_seconds),
                    source="test",
                )
            )
        repo.insert_order_book_snapshot(
            "market-usable",
            NormalizedOrderBookState(
                token_id="up-token-usable",
                side_label="UP",
                timestamp=datetime(2026, 5, 24, 12, 0, 5, tzinfo=UTC),
                bids=[OrderBookLevel(price=0.4, size=100)],
                asks=[OrderBookLevel(price=0.41, size=120)],
            ),
            write_raw_payloads=False,
        )
        for offset_seconds in range(5, 896, 15):
            repo.insert_underlying_price_tick(
                UnderlyingPriceTick(
                    asset=AssetSymbol.BTC,
                    symbol="btcusdt",
                    timestamp=datetime(2026, 5, 24, 12, 0, 0, tzinfo=UTC)
                    + timedelta(seconds=offset_seconds),
                    price=108000.0,
                    provider="mock",
                ),
                write_raw_payloads=False,
            )
        session.commit()

    report = RecorderAuditService(DatabaseSessionFactory(database_url)).build_report(
        lookback_hours=24,
        limit=10,
    )

    assert report.market_count == 1
    row = report.rows[0]
    assert row.quality == "usable"
    assert row.usable is True
    assert row.flags == []
