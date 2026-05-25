# HANDOFF.md

## Current Objective

Prepare and maintain repo-memory / agent-handoff workflow before starting Phase 3.

## Current Status

- Phase 1 is complete.
- Phase 2 recorder is complete.
- Phase 2.5 audit is complete.
- Phase 3 is next.
- Phase 3 is not implemented in this task.
- Repo-memory workflow has now been added so future agents can continue from repository state instead of chat memory.
- Repo-memory validation for this task passed:
  - `make test`
  - `make lint`

## What Was Completed

Phase 1 delivered:
- project scaffold
- typed config
- domain models
- strategy stubs
- docs
- Docker tooling
- tests

Phase 2 delivered:
- live Polymarket 15-minute crypto market discovery
- Polymarket public market data listener
- Polymarket RTDS underlying price feed
- PostgreSQL persistence
- normalized market snapshots
- order book snapshots
- underlying price ticks
- recorder run tracking
- production hardening
- no live trading

Phase 2.5 delivered:
- `python -m polymarket_scalper audit`
- `make audit`
- per-market quality classification:
  - `usable`
  - `flagged`
  - `active`
- strict default thresholds
- asset filtering
- configurable thresholds for diagnostics
- production-tested audit results

Repo-memory workflow delivered:
- canonical `AGENTS.md`
- current-state `HANDOFF.md`
- project board in `TASKS.md`
- durable decision log in `DECISIONS.md`
- ADR set in `docs/adr/`
- Claude/Cursor-specific pointers and rules

## What Is Incomplete

- Phase 3 replay/backtesting engine
- backtest CLI and reporting
- Phase 4 paper trading
- later live trading phases

## Important Files and Areas

Start here:
- `AGENTS.md`
- `HANDOFF.md`
- `TASKS.md`
- `DECISIONS.md`
- `docs/adr/`

Relevant implementation areas:
- `src/polymarket_scalper/recorder/services/recorder.py`
- `src/polymarket_scalper/recorder/services/audit.py`
- `src/polymarket_scalper/recorder/db/models.py`
- `src/polymarket_scalper/recorder/db/repository.py`
- `src/polymarket_scalper/recorder/feeds/`
- `src/polymarket_scalper/__main__.py`

Supporting docs:
- `build-doc.md`
- `docs/strategy-spec.md`
- `docs/market-data-recorder.md`
- `docs/operations-runbook.md`
- `docs/development-roadmap.md`

## Known Issues / Watchouts

- Exact opening price still depends on fallback resolution paths and provenance labels.
- Phase 3 must not consume raw windows directly by default.
- Canonical dataset is strict audited completed windows with `usable=true`.
- Relaxed audit thresholds are diagnostic only.
- Production PostgreSQL must stay private.
- Do not reintroduce public Postgres exposure.
- Do not add live trading, private keys, or builder credentials before the correct phase.

## Commands Recently Used

```bash
make audit
python -m polymarket_scalper audit --asset BTC
python3 -m pytest tests/unit/recorder/test_audit.py tests/unit/recorder/test_repository.py tests/unit/recorder/test_recorder_service.py tests/unit/recorder/test_feeds.py
make test
make lint
```

Results:
- `make test`: `54 passed`
- `make lint`: passed

## Production Notes

Audit results already established:

72-hour all-assets sample:
- `markets=500`
- `active=5`
- `ended=495`
- `usable=285`
- `flagged=210`
- dominant flagged reason: `snapshot_gap_gt_5s`

24-hour per-asset strict mode:
- each asset had `markets=96`
- each asset had `active=1`
- each asset had `ended=95`
- each asset had `usable=55`
- each asset had `flagged=40`

24-hour per-asset relaxed mode with `--max-snapshot-gap-seconds 10`:
- each asset had `markets=96`
- each asset had `active=1`
- each asset had `ended=95`
- each asset had `usable=87`
- each asset had `flagged=8`

Policy:
- strict mode is canonical
- relaxed mode is diagnostic only

## Next Recommended Steps

Start Phase 3: offline replay/backtesting engine.

Requirements:
- do not implement live trading
- do not require private keys
- do not require builder credentials
- do not use authenticated trading endpoints
- do not bypass audit filtering
- load strict audited `usable=true` completed windows by default

## Instructions for the Next Agent

1. Read `AGENTS.md`, `HANDOFF.md`, `TASKS.md`, `DECISIONS.md`, and `docs/adr/` first.
2. Treat this repo as phase-gated.
3. Start Phase 3 only as an offline replay/backtesting effort.
4. Reuse audit logic programmatically instead of duplicating quality rules.
5. Keep backtest inputs limited to strict audited usable windows by default.
6. Update `HANDOFF.md` and `TASKS.md` before stopping.
