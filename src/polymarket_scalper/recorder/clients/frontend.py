from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from polymarket_scalper.domain.enums import AssetSymbol

NEXT_DATA_PATTERN = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(?P<payload>.*?)</script>',
    re.DOTALL,
)


class PolymarketFrontendClient:
    """Read opening-price hints from the public event page's embedded Next.js state."""

    def __init__(
        self,
        base_url: str = "https://polymarket.com",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def fetch_opening_price(
        self,
        slug: str,
        asset: AssetSymbol,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> float | None:
        prices = await self.fetch_market_prices(slug, asset, start_time, end_time)
        return prices.open_price

    async def fetch_market_prices(
        self,
        slug: str,
        asset: AssetSymbol,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> FrontendMarketPrices:
        next_data = await self.fetch_next_data(slug)
        return extract_market_prices_from_next_data(next_data, asset, start_time, end_time)

    async def fetch_next_data(self, slug: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/event/{slug}")
            response.raise_for_status()
        return extract_next_data_from_html(response.text, slug)


@dataclass(frozen=True)
class FrontendMarketPrices:
    """Opening and closing prices exposed by the public Polymarket event page."""

    open_price: float | None = None
    close_price: float | None = None


def extract_opening_price_from_next_data(
    root: dict[str, Any],
    asset: AssetSymbol,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> float | None:
    return extract_market_prices_from_next_data(root, asset, start_time, end_time).open_price


def extract_market_prices_from_next_data(
    root: dict[str, Any],
    asset: AssetSymbol,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> FrontendMarketPrices:
    queries = _extract_queries(root)
    if not queries:
        return FrontendMarketPrices()

    start_iso = _to_utc_z(start_time)
    end_iso = _to_utc_z(end_time)
    exact_matches = [
        query
        for query in queries
        if is_market_price_query(query, asset)
        and (
            start_iso is None
            or end_iso is None
            or query_matches_window(query.get("queryKey"), start_iso, end_iso)
        )
    ]
    candidates = exact_matches or [
        query for query in queries if is_market_price_query(query, asset)
    ]
    if not candidates:
        return FrontendMarketPrices()

    latest = max(candidates, key=lambda item: item.get("state", {}).get("dataUpdatedAt") or 0)
    data = latest.get("state", {}).get("data", {})
    return FrontendMarketPrices(
        open_price=_coerce_optional_float(data.get("openPrice")),
        close_price=_coerce_optional_float(data.get("closePrice")),
    )


def is_market_price_query(query: dict[str, Any], asset: AssetSymbol) -> bool:
    key = query.get("queryKey") or []
    data = query.get("state", {}).get("data", {})
    return (
        isinstance(key, list)
        and len(key) >= 5
        and key[0] == "crypto-prices"
        and key[1] == "price"
        and key[2] == asset.value
        and key[4] == "fifteen"
        and (
            data.get("openPrice") is not None
            or data.get("closePrice") is not None
        )
    )


def query_matches_window(query_key: Any, start_iso: str, end_iso: str) -> bool:
    return isinstance(query_key, list) and start_iso in query_key and end_iso in query_key


def _extract_queries(root: dict[str, Any]) -> list[dict[str, Any]]:
    page_props = root.get("pageProps")
    if not isinstance(page_props, dict):
        page_props = root.get("props", {}).get("pageProps")
    if not isinstance(page_props, dict):
        return []
    dehydrated_state = page_props.get("dehydratedState") or {}
    queries = dehydrated_state.get("queries")
    return queries if isinstance(queries, list) else []


def _to_utc_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    normalized = value.astimezone(UTC).replace(microsecond=0)
    return normalized.isoformat().replace("+00:00", "Z")


def _coerce_optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def extract_next_data_from_html(html: str, slug: str | None = None) -> dict[str, Any]:
    match = NEXT_DATA_PATTERN.search(html)
    if match is None:
        slug_hint = f" for slug={slug}" if slug else ""
        raise ValueError(f"__NEXT_DATA__ payload not found{slug_hint}")
    return json.loads(match.group("payload"))
