# ADR 0003: Use Polymarket RTDS as primary underlying feed

## Status

Accepted

## Context

The recorder needs live underlying crypto price ticks for BTC, ETH, SOL, BNB, and XRP. The current integrated provider is Polymarket RTDS. Future fallbacks may be useful, but the active production path should not become hardcoded to a non-swappable provider.

## Decision

Use Polymarket RTDS as the current primary underlying price provider. Keep the provider swappable behind `UnderlyingPriceFeed`. Do not hardcode Binance-specific assumptions into the recorder core.

## Consequences

- Current production behavior stays aligned with the integrated and tested provider.
- Future fallback providers remain possible.
- Provider-specific behavior should stay isolated in feed implementations.

## Alternatives Considered

- Hardcode Binance as the primary provider.
- Remove provider abstraction and treat the current provider as permanent.

## Notes

Binance or other providers may be added later, but only as swappable implementations.
