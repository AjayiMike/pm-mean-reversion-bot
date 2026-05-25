# AGENTS.md

## Purpose

This file is the canonical repo-level instruction file for coding agents working in this repository. Read it first. It exists so Codex, Cursor, Claude Code, and other agentic tools can continue work safely without relying on prior chat context.

## Project Summary

This repository contains a Polymarket 15-minute crypto mean-reversion scalping bot.

The long-term strategy:
- watches 15-minute Polymarket crypto UP/DOWN markets
- looks for short-term odds dislocations
- does not blindly buy the cheaper side
- buys the cheaper side only when conditions suggest the odds are likely to rebound before expiry
- is intended to scalp pre-expiry odds movement rather than hold every trade to resolution
- must not silently convert failed scalps into expiry gambles

Supported assets:
- `BTC`
- `ETH`
- `SOL`
- `BNB`
- `XRP`

## Current Phase Status

Completed:
- Phase 1: strategy specification and project foundation
- Phase 2: market data recorder
- Phase 2.5: recorder data audit

Next:
- Phase 3: offline replay/backtesting engine

Phase 3 has not been implemented in this task.

## Tech Stack

- Python 3.12
- SQLAlchemy / Alembic
- PostgreSQL 16
- Docker / Docker Compose
- pytest
- Ruff
- Polymarket public market data
- Polymarket RTDS for underlying price ticks

## Important Commands

Setup:
```bash
make install
cp .env.example .env
```

Quality:
```bash
make test
make lint
make format
```

Database / migrations:
```bash
make db-up
make db-migrate
```

Recorder / health:
```bash
make record
make health
python -m polymarket_scalper health
```

Audit:
```bash
make audit
python -m polymarket_scalper audit
python -m polymarket_scalper audit --asset BTC
```

Docker:
```bash
make docker-build
make docker-record
make docker-test
make docker-down
```

## Architecture Overview

Core areas:
- `src/polymarket_scalper/recorder/services/recorder.py`: live recorder loop
- `src/polymarket_scalper/recorder/services/audit.py`: data-audit command and quality classification
- `src/polymarket_scalper/recorder/db/models.py`: recorder schema
- `src/polymarket_scalper/recorder/db/repository.py`: persistence layer
- `src/polymarket_scalper/recorder/feeds/`: underlying price feed abstraction and providers
- `src/polymarket_scalper/__main__.py`: CLI entrypoints

Persistence model:
- `markets`
- `market_snapshots`
- `order_book_snapshots`
- `underlying_price_ticks`
- `recorder_runs`

Data separation is intentional:
- prediction-market data comes from Polymarket CLOB / market streams
- underlying crypto price data comes from the `UnderlyingPriceFeed` abstraction

## Phase Discipline

Work must remain phase-gated:
- Phase 1: foundation
- Phase 2: recorder
- Phase 2.5: data audit
- Phase 3: replay/backtesting
- Phase 4: paper trading
- Phase 5: small live trading
- Phase 6: optimization/scaling
- Phase 7: production hardening

Do not jump phases.

Do not add live trading code before the live trading phase.

## Security Rules

- Do not commit `.env`.
- Do not log secrets.
- Do not log private keys or builder credentials.
- Do not expose PostgreSQL publicly.
- Production PostgreSQL access should remain internal or via SSH tunnel only.
- Do not require private keys before the live trading phase.
- Do not require builder credentials before the live trading phase.
- Do not use authenticated trading endpoints before the live trading phase.

## Data Rules

- Bid/ask are executable prices, not midpoints.
- For buys, use the ask.
- For sells, use the bid.
- Phase 3 canonical dataset is strict audited completed windows with `usable=true`.
- Relaxed audit thresholds are diagnostic only.
- Do not use future data in replay.
- Treat each asset's market stream independently when that improves audit or backtest correctness.

## Testing Rules

- Before claiming completion, run the relevant tests.
- Prefer the existing Makefile commands.
- Do not introduce tests that require real network calls unless they are explicitly integration/manual.
- If a command fails, report the failure and whether it is related to your change.

## Coding Standards

- Inspect existing code patterns before changing behavior.
- Keep changes scoped to the task.
- Preserve typed/configured abstractions already in use.
- Do not collapse prediction-market data and underlying feed data into one component.
- Update documentation when behavior or workflow changes.

## Agent Workflow

Before changes:
1. Read `AGENTS.md`.
2. Read `HANDOFF.md`.
3. Read `TASKS.md`.
4. Read `DECISIONS.md`.
5. Read relevant files in `docs/adr/`.
6. Read the relevant phase docs before changing implementation.

During changes:
- inspect existing patterns
- keep changes scoped
- avoid unrelated refactors
- use strict audited windows as the default assumption for future Phase 3 work

Before stopping:
- run relevant tests/lint
- update `HANDOFF.md`
- update `TASKS.md`
- update `DECISIONS.md` or add/update an ADR if a meaningful decision was made

## Files Agents Must Read Before Work

- `AGENTS.md`
- `HANDOFF.md`
- `TASKS.md`
- `DECISIONS.md`
- `docs/adr/`
- relevant phase docs, especially:
  - `build-doc.md`
  - `docs/strategy-spec.md`
  - `docs/market-data-recorder.md`
  - `docs/development-roadmap.md`
  - `docs/operations-runbook.md`

## Files Agents Must Update Before Stopping

- `HANDOFF.md`
- `TASKS.md`
- `DECISIONS.md` when a new meaningful decision was made
- `docs/adr/` when a decision deserves a durable ADR

## What Agents Must Not Do

- Do not implement live trading before the correct phase.
- Do not expose Postgres publicly.
- Do not commit secrets.
- Do not bypass the audit filter for Phase 3 default behavior.
- Do not require private keys or builder credentials before live trading.
- Do not mix underlying price data and prediction-market data into one abstraction.
- Do not treat relaxed audit thresholds as canonical.
- Do not make unrelated changes when doing phase-scoped work.

## Current Next Step

Phase 3: build the offline replay/backtesting engine.

Requirements for that phase:
- offline only
- no trading
- no private keys
- no builder credentials
- no authenticated trading endpoints
- use strict audited completed windows with `usable=true` by default
