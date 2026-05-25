# Development Roadmap

## 1. Strategy Specification

Objective: turn the trading idea into explicit rules and constraints.

What to build:
- strategy specification
- typed config models
- domain model scaffold
- stubbed strategy rules
- local development tooling

Output:
- implementation-ready Phase 1 repository

Conditions for moving to the next phase:
- strategy, exits, and risk limits are specific enough to implement without guessing

## 2. Market Data Recorder

Objective: capture what the bot would have seen in live markets without placing trades.

What to build:
- market discovery
- Polymarket order book listeners
- underlying price feed listeners
- snapshot normalizer
- durable storage for recorded data

Output:
- reliable recorder for completed market windows

Conditions for moving to the next phase:
- at least 500 completed markets recorded with acceptable data quality

## 2.5. Recorder Data Audit

Objective: classify recorded market windows by quality before replay uses them.

What to build:
- recorder data-audit command
- strict default quality thresholds
- per-market quality classification
- asset-filtered audit views
- configurable thresholds for diagnostics only

Output:
- auditable `usable`, `flagged`, and `active` market windows
- a strict canonical dataset gate for Phase 3

Conditions for moving to the next phase:
- strict audited usable windows are available for replay
- known recorder quality gaps are understood and documented
- repo-memory / handoff workflow is in place for cross-agent continuity

Status:
- complete

## 3. Backtesting/Replay Engine

Objective: replay recorded markets and simulate realistic execution.

Repo-memory / handoff workflow was added before Phase 3 so future agents can continue safely across Codex, Cursor, Claude Code, and other tools.

Phase 3 must consume strict audited `usable=true` completed windows by default. Raw recorder output is not the canonical replay dataset.

What to build:
- historical replay engine
- entry/exit simulation using bid/ask prices
- fee and slippage modeling
- performance reporting

Output:
- evidence for or against positive expectancy

Conditions for moving to the next phase:
- backtests are repeatable, realistic, and show enough promise to justify paper trading

## 4. Paper Trading

Objective: test live signal generation and paper execution without real capital.

What to build:
- live signal loop
- paper positions and PnL tracking
- operational dashboards/logging
- failure handling for stale feeds and missed fills

Output:
- real-time paper trading results and operational learnings

Conditions for moving to the next phase:
- stable runtime behavior and paper results consistent with replay expectations

## 5. Small Live Trading

Objective: validate execution with minimal size and strict risk limits.

What to build:
- authenticated execution path
- order lifecycle handling
- credential management
- kill-switch enforcement

Output:
- tightly controlled live trading pilot

Conditions for moving to the next phase:
- operational stability, acceptable slippage, and disciplined adherence to risk controls

## 6. Optimization/Scaling

Objective: improve expectancy and expand coverage without losing control.

What to build:
- parameter experiments
- market quality filters
- more robust monitoring and analytics
- optional infrastructure improvements only if justified

Output:
- data-backed strategy improvements

Conditions for moving to the next phase:
- performance gains justify additional operational complexity

## 7. Production Hardening

Objective: make the system reliable enough for longer-running unattended operation.

What to build:
- hardened deployment workflow
- better observability
- backup and recovery procedures
- security review for live credentials and wallet operations

Output:
- production-ready operating baseline

Conditions for continuing beyond this phase:
- reliability, security, and operational procedures are consistently acceptable
