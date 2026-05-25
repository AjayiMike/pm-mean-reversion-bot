# ADR 0004: Use strict audit as canonical backtest dataset

## Status

Accepted

## Context

Recorder output can contain interrupted windows, incomplete windows, stale-feed periods, or timing gaps. Phase 2.5 added an audit command that classifies windows as `usable`, `flagged`, or `active` under strict defaults, with optional relaxed thresholds for diagnostics.

## Decision

Treat completed market windows with strict audit `usable=true` as the canonical dataset for Phase 3. Exclude `flagged` windows by default. Treat relaxed thresholds as diagnostic only. The backtester must not consume raw windows directly by default.

## Consequences

- Backtesting stays closer to real-time conditions.
- Fewer windows are eligible by default, but quality is higher.
- Any inclusion of flagged data should require an explicit non-default option.

## Alternatives Considered

- Use all completed markets by default.
- Use relaxed thresholds as the standard dataset.
- Ignore audit results and let replay infer data quality dynamically.

## Notes

Observed production audit results show snapshot gap strictness is the main exclusion driver, which supports keeping strict mode canonical and relaxed mode diagnostic.
