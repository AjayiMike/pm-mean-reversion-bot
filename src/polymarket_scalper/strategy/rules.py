from __future__ import annotations

from polymarket_scalper.config.strategy import StrategyConfig
from polymarket_scalper.domain.enums import ExitReason, MarketSide, SignalAction
from polymarket_scalper.domain.models import (
    MarketSnapshot,
    Position,
    PositionExitDecision,
    TradeSignal,
)


def identify_cheap_side(snapshot: MarketSnapshot) -> MarketSide:
    """Return the cheaper contract side for the current snapshot.

    Phase 1 note: this is a deterministic scaffold helper only. Future phases will
    incorporate executable prices, depth, and fee-aware candidate ranking.
    """

    return MarketSide.UP if snapshot.up_ask <= snapshot.down_ask else MarketSide.DOWN


def is_entry_candidate(snapshot: MarketSnapshot, config: StrategyConfig) -> TradeSignal:
    """Evaluate whether a snapshot is a basic entry candidate.

    Phase 1 intentionally does not connect to Polymarket or place orders. The goal is
    to codify the guardrails: do not blindly buy the cheaper side. Only identify a
    candidate when price, time, spread, liquidity, and basic momentum conditions are acceptable.
    """

    cheap_side = identify_cheap_side(snapshot)
    candidate_price = snapshot.up_ask if cheap_side is MarketSide.UP else snapshot.down_ask

    if candidate_price > config.entry.max_entry_price:
        return TradeSignal(
            action=SignalAction.SKIP,
            reason="candidate price above max entry",
            candidate_price=candidate_price,
        )

    if not (
        config.entry.min_time_remaining_seconds
        <= snapshot.time_remaining_seconds
        <= config.entry.max_time_remaining_seconds
    ):
        return TradeSignal(
            action=SignalAction.SKIP,
            reason="time remaining outside entry window",
            candidate_price=candidate_price,
        )

    if abs(snapshot.distance_from_open_bps) > config.entry.max_abs_distance_from_open_bps:
        return TradeSignal(
            action=SignalAction.SKIP,
            reason="distance from open too large",
            candidate_price=candidate_price,
        )

    if snapshot.spread > config.entry.max_spread:
        return TradeSignal(
            action=SignalAction.SKIP,
            reason="spread too wide",
            candidate_price=candidate_price,
        )

    if snapshot.depth_multiplier < config.entry.min_depth_multiplier:
        return TradeSignal(
            action=SignalAction.SKIP,
            reason="insufficient visible depth",
            candidate_price=candidate_price,
        )

    if config.entry.require_momentum_confirmation:
        if cheap_side is MarketSide.UP and snapshot.recent_return_30s < snapshot.recent_return_60s:
            return TradeSignal(
                action=SignalAction.SKIP,
                reason="up rebound not confirmed",
                candidate_price=candidate_price,
            )
        if (
            cheap_side is MarketSide.DOWN
            and snapshot.recent_return_30s > snapshot.recent_return_60s
        ):
            return TradeSignal(
                action=SignalAction.SKIP,
                reason="down rebound not confirmed",
                candidate_price=candidate_price,
            )

    if cheap_side is MarketSide.UP and snapshot.current_price >= snapshot.opening_price:
        return TradeSignal(
            action=SignalAction.SKIP,
            reason="up side not cheap for the intended setup",
            candidate_price=candidate_price,
        )

    if cheap_side is MarketSide.DOWN and snapshot.current_price <= snapshot.opening_price:
        return TradeSignal(
            action=SignalAction.SKIP,
            reason="down side not cheap for the intended setup",
            candidate_price=candidate_price,
        )

    return TradeSignal(
        action=SignalAction.ENTER,
        side=cheap_side,
        reason="phase 1 candidate satisfies baseline filters",
        candidate_price=candidate_price,
    )


def should_exit_position(
    position: Position,
    snapshot: MarketSnapshot,
    config: StrategyConfig,
) -> PositionExitDecision:
    """Return a placeholder exit decision based on simple Phase 1 rules.

    This stub exists to make exit logic explicit before any live execution code exists.
    Later phases will evaluate executable bid prices, fees, slippage, and richer invalidation rules.
    """

    mark_price = snapshot.up_bid if position.side is MarketSide.UP else snapshot.down_bid
    pnl_ratio = (mark_price - position.entry_price) / position.entry_price

    if pnl_ratio >= config.exit.take_profit_pct:
        return PositionExitDecision(should_exit=True, reason=ExitReason.TAKE_PROFIT)

    if pnl_ratio <= -config.exit.stop_loss_pct:
        return PositionExitDecision(should_exit=True, reason=ExitReason.STOP_LOSS)

    if snapshot.time_remaining_seconds <= config.exit.force_exit_time_remaining_seconds:
        return PositionExitDecision(should_exit=True, reason=ExitReason.TIME_STOP)

    if config.exit.use_invalidation_exit:
        if (
            position.side is MarketSide.UP
            and snapshot.distance_from_open_bps < -config.entry.max_abs_distance_from_open_bps
        ):
            return PositionExitDecision(should_exit=True, reason=ExitReason.INVALIDATION)
        if (
            position.side is MarketSide.DOWN
            and snapshot.distance_from_open_bps > config.entry.max_abs_distance_from_open_bps
        ):
            return PositionExitDecision(should_exit=True, reason=ExitReason.INVALIDATION)

    return PositionExitDecision(should_exit=False)
