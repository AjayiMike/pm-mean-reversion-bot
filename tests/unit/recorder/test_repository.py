from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from polymarket_scalper.domain.enums import AssetSymbol
from polymarket_scalper.recorder.clients.frontend import FrontendMarketPrices
from polymarket_scalper.recorder.db.base import Base
from polymarket_scalper.recorder.db.models import MarketRecord, RecorderRunRecord
from polymarket_scalper.recorder.db.repository import RecorderRepository
from polymarket_scalper.recorder.services.models import DiscoveredMarket, UnderlyingPriceTick
from polymarket_scalper.recorder.services.opening_price import (
    MAX_TICK_STALENESS_SECONDS,
    OPENING_PRICE_SOURCE_UNDERLYING_TICK,
    OpeningPriceResolver,
)


def test_repository_market_upsert_and_tick_insert() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = RecorderRepository(session)
        market = DiscoveredMarket(
            id="market-1",
            question="BTC 15-minute market: up or down?",
            asset=AssetSymbol.BTC,
            up_token_id="up-token",
            down_token_id="down-token",
        )
        repo.upsert_market(market)
        tick = UnderlyingPriceTick(
            asset=AssetSymbol.BTC,
            symbol="btcusdt",
            timestamp=datetime.now(UTC),
            price=65000.0,
            provider="mock",
        )
        repo.insert_underlying_price_tick(tick, write_raw_payloads=False)
        session.commit()

        rows = repo.list_active_markets(["BTC"])
        assert len(rows) == 1
        assert rows[0].asset == "BTC"


def test_repository_duplicate_underlying_tick_is_ignored() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    tick = UnderlyingPriceTick(
        asset=AssetSymbol.BTC,
        symbol="btcusdt",
        timestamp=datetime(2026, 5, 21, 23, 25, 57, tzinfo=UTC),
        price=108000.0,
        provider="polymarket_rtds:binance",
    )

    with Session(engine) as session:
        repo = RecorderRepository(session)
        inserted_first = repo.insert_underlying_price_tick(tick, write_raw_payloads=False)
        inserted_second = repo.insert_underlying_price_tick(tick, write_raw_payloads=False)
        session.commit()

        count = session.execute(
            text("select count(*) from underlying_price_ticks")
        ).scalar_one()

        assert inserted_first is True
        assert inserted_second is False
        assert count == 1


def test_repository_deactivate_markets_except_marks_stale_rows_inactive() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = RecorderRepository(session)
        current = DiscoveredMarket(
            id="market-current",
            question="BTC 15-minute market: up or down?",
            asset=AssetSymbol.BTC,
            end_time=datetime(2026, 5, 17, 0, 45, tzinfo=UTC),
            up_token_id="up-current",
            down_token_id="down-current",
        )
        stale = DiscoveredMarket(
            id="market-stale",
            question="ETH 15-minute market: up or down?",
            asset=AssetSymbol.ETH,
            end_time=datetime(2026, 5, 17, 0, 15, tzinfo=UTC),
            up_token_id="up-stale",
            down_token_id="down-stale",
        )
        repo.upsert_market(current)
        repo.upsert_market(stale)
        session.commit()

        updated = repo.deactivate_markets_except(
            {"market-current"},
            as_of=datetime(2026, 5, 17, 0, 30, tzinfo=UTC),
        )
        session.commit()

        assert updated == 1
        current_row = session.get(MarketRecord, "market-current")
        stale_row = session.get(MarketRecord, "market-stale")
        assert current_row is not None and current_row.active is True
        assert stale_row is not None and stale_row.active is False
        assert stale_row.closed is True


def test_repository_lists_recent_markets_needing_frontend_reconciliation() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = RecorderRepository(session)
        ended_without_close = DiscoveredMarket(
            id="market-ended",
            question="BTC 15-minute market: up or down?",
            asset=AssetSymbol.BTC,
            slug="btc-updown-15m-1",
            start_time=datetime(2026, 5, 17, 0, 0, tzinfo=UTC),
            end_time=datetime(2026, 5, 17, 0, 15, tzinfo=UTC),
            up_token_id="up-ended",
            down_token_id="down-ended",
            active=False,
            closed=True,
        )
        tick_open = DiscoveredMarket(
            id="market-tick-open",
            question="ETH 15-minute market: up or down?",
            asset=AssetSymbol.ETH,
            slug="eth-updown-15m-1",
            start_time=datetime(2026, 5, 17, 0, 15, tzinfo=UTC),
            end_time=datetime(2026, 5, 17, 0, 30, tzinfo=UTC),
            opening_price=1234.5,
            opening_price_source=OPENING_PRICE_SOURCE_UNDERLYING_TICK,
            up_token_id="up-tick",
            down_token_id="down-tick",
        )
        already_closed = DiscoveredMarket(
            id="market-closed",
            question="SOL 15-minute market: up or down?",
            asset=AssetSymbol.SOL,
            slug="sol-updown-15m-1",
            start_time=datetime(2026, 5, 17, 0, 0, tzinfo=UTC),
            end_time=datetime(2026, 5, 17, 0, 15, tzinfo=UTC),
            close_price=55.0,
            close_price_source="polymarket_frontend_dehydrated_state",
            up_token_id="up-closed",
            down_token_id="down-closed",
            active=False,
            closed=True,
        )
        repo.upsert_market(ended_without_close)
        repo.upsert_market(tick_open)
        repo.upsert_market(already_closed)
        session.commit()

        ended = repo.list_recently_ended_markets_missing_close_price(
            as_of=datetime(2026, 5, 17, 0, 20, tzinfo=UTC),
            since=datetime(2026, 5, 16, 23, 50, tzinfo=UTC),
        )
        tick_upgrades = repo.list_recent_markets_needing_frontend_open_upgrade(
            since=datetime(2026, 5, 17, 0, 10, tzinfo=UTC),
            source=OPENING_PRICE_SOURCE_UNDERLYING_TICK,
        )

        assert [record.id for record in ended] == ["market-ended"]
        assert [record.id for record in tick_upgrades] == ["market-tick-open"]


def test_repository_run_progress_and_finish() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = RecorderRepository(session)
        run = repo.create_run(["BTC", "ETH"])
        session.commit()

        repo.update_run_progress(run.id, markets_discovered=5, snapshots_written=42)
        repo.finish_run(
            run.id,
            status="interrupted",
            markets_discovered=5,
            snapshots_written=42,
        )
        session.commit()

        stored = session.get(RecorderRunRecord, run.id)
        assert stored is not None
        assert stored.status == "interrupted"
        assert stored.markets_discovered == 5
        assert stored.snapshots_written == 42
        assert stored.stopped_at is not None


def test_repository_interrupt_stale_runs() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repo = RecorderRepository(session)
        first = repo.create_run(["BTC"])
        second = repo.create_run(["ETH"])
        session.commit()

        interrupted = repo.interrupt_stale_runs("superseded_by_new_recorder_run")
        session.commit()

        assert interrupted == 2
        first_stored = session.get(RecorderRunRecord, first.id)
        second_stored = session.get(RecorderRunRecord, second.id)
        assert first_stored is not None
        assert second_stored is not None
        assert first_stored.status == "interrupted"
        assert second_stored.status == "interrupted"
        assert first_stored.stopped_at is not None
        assert second_stored.stopped_at is not None


def test_opening_price_resolver_uses_real_db_tick_when_frontend_is_unavailable() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    class StubDb:
        def session(self) -> Session:
            return Session(engine)

    class StubFrontendClient:
        async def fetch_market_prices(self, **kwargs) -> FrontendMarketPrices:  # noqa: ARG002
            return FrontendMarketPrices()

    with Session(engine) as session:
        repo = RecorderRepository(session)
        repo.insert_underlying_price_tick(
            UnderlyingPriceTick(
                asset=AssetSymbol.BTC,
                symbol="btcusdt",
                timestamp=datetime(2026, 5, 17, 0, 29, 59, tzinfo=UTC),
                price=88888.0,
                provider="polymarket_rtds:binance",
            ),
            write_raw_payloads=False,
        )
        session.commit()

    resolver = OpeningPriceResolver(StubDb(), StubFrontendClient())
    market = DiscoveredMarket(
        id="market-1",
        question="BTC 15-minute market: up or down?",
        asset=AssetSymbol.BTC,
        slug="btc-updown-15m-1778977800",
        start_time=datetime(2026, 5, 17, 0, 30, tzinfo=UTC),
        end_time=datetime(2026, 5, 17, 0, 45, tzinfo=UTC),
        up_token_id="up-token",
        down_token_id="down-token",
    )

    import asyncio

    asyncio.run(resolver.resolve_market(market))

    assert market.opening_price == 88888.0
    assert market.opening_price_source == OPENING_PRICE_SOURCE_UNDERLYING_TICK
    assert market.opening_price_reference_provider == "polymarket_rtds:binance"
    assert market.opening_price_reference_timestamp == datetime(2026, 5, 17, 0, 29, 59, tzinfo=UTC)
    assert market.opening_price_resolved_at is not None


def test_opening_price_resolver_uses_frontend_when_tick_is_stale() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    class StubDb:
        def session(self) -> Session:
            return Session(engine)

    class StubFrontendClient:
        async def fetch_market_prices(self, **kwargs) -> FrontendMarketPrices:  # noqa: ARG002
            return FrontendMarketPrices(open_price=91234.5)

    with Session(engine) as session:
        repo = RecorderRepository(session)
        repo.insert_underlying_price_tick(
            UnderlyingPriceTick(
                asset=AssetSymbol.BTC,
                symbol="btcusdt",
                timestamp=datetime(2026, 5, 17, 0, 30, tzinfo=UTC),
                price=88888.0,
                provider="polymarket_rtds:binance",
            ),
            write_raw_payloads=False,
        )
        session.commit()

    resolver = OpeningPriceResolver(StubDb(), StubFrontendClient())
    market = DiscoveredMarket(
        id="market-2",
        question="BTC 15-minute market: up or down?",
        asset=AssetSymbol.BTC,
        slug="btc-updown-15m-1778979600",
        start_time=datetime(2026, 5, 17, 0, 30, tzinfo=UTC)
        + timedelta(seconds=MAX_TICK_STALENESS_SECONDS + 10),
        end_time=datetime(2026, 5, 17, 0, 45, tzinfo=UTC),
        up_token_id="up-token",
        down_token_id="down-token",
    )

    import asyncio

    asyncio.run(resolver.resolve_market(market))

    assert market.opening_price == 91234.5
    assert market.opening_price_source == "polymarket_frontend_dehydrated_state"
    assert market.opening_price_reference_provider == "polymarket_frontend_dehydrated_state"
    assert market.opening_price_reference_timestamp == market.start_time
    assert market.opening_price_resolved_at is not None


def test_opening_price_resolver_captures_frontend_close_price() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    class StubDb:
        def session(self) -> Session:
            return Session(engine)

    class StubFrontendClient:
        async def fetch_market_prices(self, **kwargs) -> FrontendMarketPrices:  # noqa: ARG002
            return FrontendMarketPrices(open_price=91234.5, close_price=91321.0)

    resolver = OpeningPriceResolver(StubDb(), StubFrontendClient())
    market = DiscoveredMarket(
        id="market-3",
        question="BTC 15-minute market: up or down?",
        asset=AssetSymbol.BTC,
        slug="btc-updown-15m-1778979600",
        start_time=datetime(2026, 5, 17, 0, 30, tzinfo=UTC),
        end_time=datetime(2026, 5, 17, 0, 45, tzinfo=UTC),
        up_token_id="up-token",
        down_token_id="down-token",
    )

    import asyncio

    asyncio.run(resolver.resolve_market(market))

    assert market.opening_price == 91234.5
    assert market.close_price == 91321.0
    assert market.close_price_source == "polymarket_frontend_dehydrated_state"
    assert market.close_price_resolved_at is not None
    assert market.closed is True
    assert market.active is False


def test_opening_price_resolver_upgrades_tick_opening_price_to_frontend() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    class StubDb:
        def session(self) -> Session:
            return Session(engine)

    class StubFrontendClient:
        async def fetch_market_prices(self, **kwargs) -> FrontendMarketPrices:  # noqa: ARG002
            return FrontendMarketPrices(open_price=91555.0)

    resolver = OpeningPriceResolver(StubDb(), StubFrontendClient())
    market = DiscoveredMarket(
        id="market-4",
        question="BTC 15-minute market: up or down?",
        asset=AssetSymbol.BTC,
        slug="btc-updown-15m-1778979600",
        start_time=datetime(2026, 5, 17, 0, 30, tzinfo=UTC),
        end_time=datetime(2026, 5, 17, 0, 45, tzinfo=UTC),
        opening_price=91000.0,
        opening_price_source=OPENING_PRICE_SOURCE_UNDERLYING_TICK,
        opening_price_reference_timestamp=datetime(2026, 5, 17, 0, 30, tzinfo=UTC),
        opening_price_reference_provider="polymarket_rtds:binance",
        up_token_id="up-token",
        down_token_id="down-token",
    )

    import asyncio

    asyncio.run(resolver.resolve_market(market))

    assert market.opening_price == 91555.0
    assert market.opening_price_source == "polymarket_frontend_dehydrated_state"
    assert market.opening_price_reference_provider == "polymarket_frontend_dehydrated_state"
    assert market.opening_price_reference_timestamp == market.start_time
