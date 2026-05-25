# ADR 0001: Use phase-gated development

## Status

Accepted

## Context

This project spans strategy design, recorder reliability, audit quality, replay/backtesting, paper trading, live trading, and production hardening. Mixing those phases increases risk and encourages agents to add premature live behavior.

## Decision

Use explicit development phases with acceptance criteria:
- Phase 1: strategy specification and project foundation
- Phase 2: market data recorder
- Phase 2.5: recorder data audit
- Phase 3: replay/backtesting
- Phase 4: paper trading
- Phase 5: small live trading
- Phase 6: optimization/scaling
- Phase 7: production hardening

Agents must not jump ahead. Live trading must not be added before the correct phase.

## Consequences

- Work stays scoped and reviewable.
- High-risk capabilities are deferred until earlier evidence exists.
- Agents need to check current phase before implementing new functionality.

## Alternatives Considered

- Build recorder, replay, and live trading in parallel.
- Add execution code early and disable it with flags.

## Notes

Phase 3 is the next planned phase as of 2026-05-25.
