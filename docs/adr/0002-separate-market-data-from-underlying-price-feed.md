# ADR 0002: Separate market data from underlying price feed

## Status

Accepted

## Context

Polymarket CLOB market data describes the prediction market itself: UP/DOWN bid/ask, order book state, trade activity, and market microstructure. Underlying asset price data describes the reference crypto asset price movement. The strategy requires both, but they are not the same thing.

## Decision

Keep prediction-market data and underlying asset price data separate.
Preserve separate models/components and retain the `UnderlyingPriceFeed` abstraction for underlying prices.

## Consequences

- Recorder architecture remains explicit and auditable.
- Future providers can change without rewriting market snapshot logic.
- Replay/backtesting can validate alignment between contract odds and underlying movement.

## Alternatives Considered

- Treat underlying prices as another field emitted directly by the market data listener.
- Collapse both concerns into a single feed abstraction.

## Notes

This separation is already reflected in the recorder schema and feed layer.
