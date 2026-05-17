from __future__ import annotations

from datetime import UTC, datetime

from polymarket_scalper.recorder.clients.frontend import (
    FrontendMarketPrices,
    PolymarketFrontendClient,
)
from polymarket_scalper.recorder.db.repository import RecorderRepository
from polymarket_scalper.recorder.db.session import DatabaseSessionFactory
from polymarket_scalper.recorder.services.models import DiscoveredMarket
from polymarket_scalper.utils.logging import get_logger

OPENING_PRICE_SOURCE_GAMMA = "gamma_metadata"
OPENING_PRICE_SOURCE_UNDERLYING_TICK = "underlying_tick_reconstructed"
OPENING_PRICE_SOURCE_FRONTEND = "polymarket_frontend_dehydrated_state"
MAX_TICK_STALENESS_SECONDS = 5


class OpeningPriceResolver:
    """Resolve market boundary prices with conservative source precedence.

    The recorder trusts Polymarket's own public UI data when available. Exact RTDS
    boundary ticks remain a useful fallback, but only when they line up with the
    market start closely enough to be defensible.
    """

    def __init__(
        self,
        db: DatabaseSessionFactory,
        frontend_client: PolymarketFrontendClient,
    ) -> None:
        self.db = db
        self.frontend_client = frontend_client
        self.logger = get_logger(__name__)

    async def resolve_markets(self, markets: list[DiscoveredMarket]) -> None:
        for market in markets:
            await self.resolve_market(market)

    async def resolve_market(self, market: DiscoveredMarket) -> None:
        self._apply_gamma_defaults(market)

        frontend_prices = FrontendMarketPrices()
        if market.slug is not None:
            frontend_prices = await self._fetch_frontend_prices(market)
            self._apply_frontend_close_price(market, frontend_prices)
            # Frontend values are authoritative enough to upgrade an already-filled
            # opening price that originally came from Gamma metadata or an RTDS tick.
            self._apply_frontend_open_price(market, frontend_prices)
        if market.opening_price is not None:
            return

        self._apply_underlying_tick_open_price(market)

    def _apply_gamma_defaults(self, market: DiscoveredMarket) -> None:
        if market.opening_price is not None:
            market.opening_price_source = market.opening_price_source or OPENING_PRICE_SOURCE_GAMMA
            market.opening_price_resolved_at = market.opening_price_resolved_at or datetime.now(UTC)
        if market.close_price is not None:
            market.close_price_source = market.close_price_source or OPENING_PRICE_SOURCE_GAMMA
            market.close_price_resolved_at = market.close_price_resolved_at or datetime.now(UTC)

    async def _fetch_frontend_prices(self, market: DiscoveredMarket) -> FrontendMarketPrices:
        try:
            return await self.frontend_client.fetch_market_prices(
                slug=market.slug or "",
                asset=market.asset,
                start_time=market.start_time,
                end_time=market.end_time,
            )
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "opening_price_frontend_lookup_failed",
                extra={"market_id": market.id, "slug": market.slug, "error": str(exc)},
            )
            return FrontendMarketPrices()

    def _apply_frontend_open_price(
        self,
        market: DiscoveredMarket,
        frontend_prices: FrontendMarketPrices,
    ) -> None:
        if frontend_prices.open_price is None:
            return

        market.opening_price = frontend_prices.open_price
        market.opening_price_source = OPENING_PRICE_SOURCE_FRONTEND
        market.opening_price_reference_timestamp = market.start_time
        market.opening_price_reference_provider = OPENING_PRICE_SOURCE_FRONTEND
        market.opening_price_resolved_at = datetime.now(UTC)
        self.logger.info(
            "opening_price_resolved_from_frontend",
            extra={"market_id": market.id, "slug": market.slug},
        )

    def _apply_frontend_close_price(
        self,
        market: DiscoveredMarket,
        frontend_prices: FrontendMarketPrices,
    ) -> None:
        if frontend_prices.close_price is None:
            return

        market.close_price = frontend_prices.close_price
        market.close_price_source = OPENING_PRICE_SOURCE_FRONTEND
        market.close_price_resolved_at = datetime.now(UTC)
        market.closed = True
        market.active = False
        self.logger.info(
            "close_price_resolved_from_frontend",
            extra={"market_id": market.id, "slug": market.slug},
        )

    def _apply_underlying_tick_open_price(self, market: DiscoveredMarket) -> None:
        frontend_unavailable = market.slug is None

        if market.start_time is None:
            if frontend_unavailable:
                self.logger.info(
                    "opening_price_unresolved_no_start_time",
                    extra={"market_id": market.id},
                )
            return

        with self.db.session() as session:
            repo = RecorderRepository(session)
            tick = repo.latest_underlying_tick_at_or_before(
                market.asset.value,
                market.start_time,
                excluded_provider_prefixes=("mock",),
            )
        if tick is None:
            self.logger.info(
                "opening_price_unresolved_no_tick",
                extra={"market_id": market.id, "asset": market.asset.value},
            )
            return

        tick_timestamp = tick.timestamp
        if tick_timestamp.tzinfo is None:
            tick_timestamp = tick_timestamp.replace(tzinfo=UTC)

        staleness_seconds = (market.start_time - tick_timestamp).total_seconds()
        if staleness_seconds > MAX_TICK_STALENESS_SECONDS:
            self.logger.info(
                "opening_price_tick_too_stale",
                extra={
                    "market_id": market.id,
                    "asset": market.asset.value,
                    "tick_timestamp": tick_timestamp.isoformat(),
                    "staleness_seconds": round(staleness_seconds, 3),
                },
            )
            return

        market.opening_price = tick.price
        market.opening_price_source = OPENING_PRICE_SOURCE_UNDERLYING_TICK
        market.opening_price_reference_timestamp = tick_timestamp
        market.opening_price_reference_provider = tick.provider
        market.opening_price_resolved_at = datetime.now(UTC)
        self.logger.info(
            "opening_price_resolved_from_tick",
            extra={
                "market_id": market.id,
                "asset": market.asset.value,
                "tick_timestamp": tick_timestamp.isoformat(),
                "staleness_seconds": round(staleness_seconds, 3),
            },
        )
