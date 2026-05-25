# DECISIONS.md

This file records important project decisions that future agents should not rediscover or accidentally reverse.

## Decisions

### 2026-05-25: Use phase-gated development

Decision:
- Progress the project through explicit phases and do not jump ahead.
- Keep live trading out until the correct later phase.

Reason:
- The strategy, recorder, audit, replay, and live execution layers each have different risks and acceptance criteria.

Implication:
- Agents should only implement work appropriate for the current phase.
- Live trading code should not be introduced early.

Related ADR:
- `docs/adr/0001-use-phase-gated-development.md`

### 2026-05-25: Separate prediction-market data from underlying price data

Decision:
- Keep Polymarket market data separate from underlying crypto price data.
- Preserve the `UnderlyingPriceFeed` abstraction.

Reason:
- Strategy logic depends on comparing prediction-market odds against independent underlying asset movement.

Implication:
- Do not collapse order book / market snapshot logic into the underlying price feed layer.

Related ADR:
- `docs/adr/0002-separate-market-data-from-underlying-price-feed.md`

### 2026-05-25: Prefer Polymarket RTDS as the primary underlying price provider

Decision:
- Use Polymarket RTDS as the current primary underlying price feed.
- Keep providers swappable.

Reason:
- RTDS is the provider currently integrated and production-tested in this repo.

Implication:
- Future fallbacks may exist, but the system must not be hardcoded to Binance.

Related ADR:
- `docs/adr/0003-use-polymarket-rtds-as-primary-underlying-feed.md`

### 2026-05-25: Use PostgreSQL for recorder persistence

Decision:
- Use PostgreSQL as the durable store for recorder data.

Reason:
- Recorder data needs relational persistence, migrations, indexing, and stable operational tooling.

Implication:
- Recorder schema and migration workflows are first-class project concerns.

Related ADR:
- None yet.

### 2026-05-25: Keep PostgreSQL private and never publicly exposed

Decision:
- PostgreSQL must not be published on a public host interface in production.
- Access must remain internal or via SSH tunnel.

Reason:
- A prior public DB exposure incident resulted in malicious SQL attempts and forced a wipe and credential rotation.

Implication:
- Future deployment changes must preserve private DB access.

Related ADR:
- `docs/adr/0005-keep-postgres-private-and-access-via-ssh-tunnel.md`

### 2026-05-25: Use strict audited usable windows as the canonical Phase 3 dataset

Decision:
- Phase 3 should consume completed market windows with strict audit `usable=true` by default.
- Relaxed audit thresholds are diagnostic only.

Reason:
- Raw recorder output is not uniformly safe for replay because interruptions and timing gaps can degrade realism.

Implication:
- Future backtest code should default to strict audited windows and require explicit override to include flagged data.

Related ADR:
- `docs/adr/0004-use-strict-audit-as-canonical-backtest-dataset.md`

### 2026-05-25: Use repo-memory files for agent context preservation

Decision:
- Keep durable context for agents inside the repo through `AGENTS.md`, `HANDOFF.md`, `TASKS.md`, `DECISIONS.md`, and ADRs.

Reason:
- Work may continue across Codex, Cursor, Claude Code, and other tools with no shared chat history.

Implication:
- Agents must read and update these files as part of normal workflow.

Related ADR:
- None yet.
