from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from polymarket_scalper.domain.enums import AssetSymbol
from polymarket_scalper.recorder.clients.gamma import GammaClient
from polymarket_scalper.recorder.services.models import DiscoveredMarket
from polymarket_scalper.utils.logging import get_logger

SUPPORTED_ASSET_HINTS = {
    AssetSymbol.BTC: ("bitcoin", "btc"),
    AssetSymbol.ETH: ("ethereum", "eth"),
    AssetSymbol.SOL: ("solana", "sol"),
    AssetSymbol.BNB: ("bnb", "binance coin"),
    AssetSymbol.XRP: ("xrp", "ripple"),
}

ASSET_SLUG_PREFIXES = {
    AssetSymbol.BTC: "btc-updown-15m-",
    AssetSymbol.ETH: "eth-updown-15m-",
    AssetSymbol.SOL: "sol-updown-15m-",
    AssetSymbol.BNB: "bnb-updown-15m-",
    AssetSymbol.XRP: "xrp-updown-15m-",
}

ACCEPTED_WINDOW_HINTS = ("15m", "15-minute", "15 minute", "15 min")
DIRECTION_HINTS = (("up", "down"), ("above", "below"), ("higher", "lower"))


class MarketDiscoveryService:
    """Discover active 15-minute crypto markets from public Gamma slug resolution only."""

    def __init__(self, gamma_client: GammaClient) -> None:
        self.gamma_client = gamma_client
        self.logger = get_logger(__name__)

    async def discover_markets(
        self,
        supported_assets: list[AssetSymbol],
        max_markets_per_asset: int,
    ) -> list[DiscoveredMarket]:
        discovered_by_id: dict[str, DiscoveredMarket] = {}
        counts: dict[AssetSymbol, int] = {asset: 0 for asset in supported_assets}

        slug_candidates = build_candidate_slugs(supported_assets)
        for asset, slug in slug_candidates:
            if counts[asset] >= max_markets_per_asset:
                continue
            markets = await self.gamma_client.fetch_markets_by_slug(slug)
            if not markets:
                self.logger.info(
                    "market_slug_not_found",
                    extra={"asset": asset.value, "slug": slug},
                )
                continue
            candidate = parse_market_candidate(markets[0], fallback_asset=asset)
            if candidate is None:
                self.logger.info(
                    "market_slug_rejected",
                    extra={"asset": asset.value, "slug": slug, "market_id": markets[0].get("id")},
                )
                continue
            if candidate.id in discovered_by_id:
                continue
            discovered_by_id[candidate.id] = candidate
            counts[asset] += 1
            self.logger.info(
                "market_slug_accepted",
                extra={"market_id": candidate.id, "asset": candidate.asset.value, "slug": slug},
            )

        return list(discovered_by_id.values())


def extract_asset_symbol(text: str) -> AssetSymbol | None:
    lowered = text.lower()
    for asset, hints in SUPPORTED_ASSET_HINTS.items():
        if any(hint in lowered for hint in hints):
            return asset
    return None


def extract_asset_symbol_from_slug(slug: str) -> AssetSymbol | None:
    lowered = slug.lower()
    for asset, prefix in ASSET_SLUG_PREFIXES.items():
        if lowered.startswith(prefix):
            return asset
    return None


def is_candidate_15m_crypto_market(text: str, slug: str | None = None) -> bool:
    lowered = text.lower()
    has_window_hint = any(hint in lowered for hint in ACCEPTED_WINDOW_HINTS)
    has_direction_hint = any(all(token in lowered for token in pair) for pair in DIRECTION_HINTS)
    has_supported_asset = extract_asset_symbol(text) is not None
    if has_window_hint and has_direction_hint and has_supported_asset:
        return True
    if slug:
        return extract_asset_symbol_from_slug(slug) is not None and "updown-15m-" in slug.lower()
    return False


def parse_market_candidate(
    payload: dict[str, Any],
    fallback_asset: AssetSymbol | None = None,
) -> DiscoveredMarket | None:
    question = str(payload.get("question") or payload.get("title") or "").strip()
    slug = _first_string(payload, "slug")
    asset = extract_asset_symbol(question) or (
        extract_asset_symbol_from_slug(slug) if slug else None
    )
    asset = asset or fallback_asset
    token_ids = _coerce_list(payload.get("clobTokenIds") or payload.get("clobTokenids") or [])
    opening_price = _extract_opening_price(payload)
    close_price = _extract_close_price(payload)

    if not question or asset is None or not is_candidate_15m_crypto_market(question, slug=slug):
        return None
    if len(token_ids) < 2:
        return None

    return DiscoveredMarket(
        id=str(payload.get("id") or payload.get("conditionId") or payload.get("condition_id")),
        condition_id=_first_string(payload, "conditionId", "condition_id"),
        question=question,
        asset=asset,
        slug=slug,
        event_slug=_extract_event_slug(payload),
        start_time=_extract_market_window_start(payload, slug),
        end_time=_extract_market_window_end(payload, slug),
        opening_price=opening_price,
        opening_price_source="gamma_metadata" if opening_price is not None else None,
        close_price=close_price,
        close_price_source="gamma_metadata" if close_price is not None else None,
        up_token_id=str(token_ids[0]),
        down_token_id=str(token_ids[1]),
        active=bool(payload.get("active", True)),
        closed=bool(payload.get("closed", False)),
        archived=bool(payload.get("archived", False)),
        raw_payload_json=payload,
    )


def build_candidate_slugs(
    assets: list[AssetSymbol],
    reference_time: datetime | None = None,
) -> list[tuple[AssetSymbol, str]]:
    reference = reference_time.astimezone(UTC) if reference_time else datetime.now(UTC)
    epoch = current_quarter_epoch(reference)
    slugs: list[tuple[AssetSymbol, str]] = []
    for asset in assets:
        prefix = ASSET_SLUG_PREFIXES.get(asset)
        if prefix is None:
            continue
        slugs.append((asset, f"{prefix}{epoch}"))
    return slugs


def current_quarter_epoch(reference_time: datetime) -> int:
    quarter_start = get_quarter_start(reference_time)
    return int(quarter_start.timestamp())


def get_quarter_start(reference_time: datetime) -> datetime:
    normalized = reference_time.astimezone(UTC)
    quarter_start_minute = (normalized.minute // 15) * 15
    return normalized.replace(minute=quarter_start_minute, second=0, microsecond=0)


def _extract_opening_price(payload: dict[str, Any]) -> float | None:
    """Extract an explicit opening reference price only when Gamma exposes one directly.

    For current 15-minute crypto markets, live Gamma payloads expose the resolution source and
    the time window, but not the exact opening reference price used at the beginning of that
    window. In Phase 2, that value must remain nullable unless a dedicated market field is
    present. Later phases can reconstruct the reference price from recorded underlying ticks.
    """

    for key in (
        "openingPrice",
        "opening_price",
        "openPrice",
        "open_price",
        "strikePrice",
        "strike_price",
    ):
        value = payload.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

    event = payload.get("events", [{}])
    if isinstance(event, list) and event:
        first_event = event[0]
        if isinstance(first_event, dict):
            for key in ("openingPrice", "opening_price", "openPrice", "open_price"):
                value = first_event.get(key)
                if value is not None:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        return None
    return None


def _extract_close_price(payload: dict[str, Any]) -> float | None:
    for key in ("closePrice", "close_price", "endingPrice", "ending_price"):
        value = payload.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

    event = payload.get("events", [{}])
    if isinstance(event, list) and event:
        first_event = event[0]
        if isinstance(first_event, dict):
            for key in ("closePrice", "close_price"):
                value = first_event.get(key)
                if value is not None:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        return None
    return None


def _extract_event_slug(payload: dict[str, Any]) -> str | None:
    direct = _first_string(payload, "eventSlug", "event_slug")
    if direct is not None:
        return direct
    events = payload.get("events")
    if isinstance(events, list) and events and isinstance(events[0], dict):
        return _first_string(events[0], "slug")
    return None


def _extract_market_window_start(payload: dict[str, Any], slug: str | None) -> datetime | None:
    value = _first_string(payload, "eventStartTime", "event_start_time")
    if value is not None:
        return _parse_datetime(value)
    events = payload.get("events")
    if isinstance(events, list) and events and isinstance(events[0], dict):
        event_value = _first_string(events[0], "startTime", "eventStartTime")
        if event_value is not None:
            return _parse_datetime(event_value)
    if slug is not None:
        return _parse_slug_epoch(slug)
    return _parse_datetime(_first_string(payload, "startDate", "start_date", "gameStartTime"))


def _extract_market_window_end(payload: dict[str, Any], slug: str | None) -> datetime | None:
    value = _first_string(payload, "endDate", "end_date", "gameEndTime")
    if value is not None:
        return _parse_datetime(value)
    start_time = _extract_market_window_start(payload, slug)
    if start_time is not None:
        return start_time + timedelta(minutes=15)
    return None


def _parse_slug_epoch(slug: str) -> datetime | None:
    try:
        epoch = int(slug.rsplit("-", maxsplit=1)[-1])
    except ValueError:
        return None
    return datetime.fromtimestamp(epoch, tz=UTC)


def _coerce_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _first_string(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
