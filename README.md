# Polymarket 15-Minute Crypto Scalper

Phase 2 builds a market data recorder for Polymarket 15-minute crypto prediction markets. Phase 2 records public market data only. It does not trade. It does not require private keys. It does not require builder credentials.

## Strategy Summary

The long-term bot is intended to trade short-duration pre-expiry odds movement in Polymarket crypto UP/DOWN markets.

The refined strategy is not "always buy the cheaper side." The strategy is "buy the cheaper side only when conditions suggest the odds are likely to rebound before expiry."

The bot is designed to scalp pre-expiry odds movement. It is not designed to hold every position until resolution. Failed scalps must not silently become expiry gambles.

## Current Phase

Phase 2 only:
- public current-market discovery with rollover to the next live quarter-hour market
- public Polymarket market-data listener scaffolding
- underlying crypto price feed abstraction
- frontend-backed market boundary metadata capture (`openPrice` / `closePrice`)
- PostgreSQL persistence and migrations
- normalized snapshot writing for later replay/backtesting

Intentionally not implemented yet:
- live trading
- order placement
- order signing
- private-key usage
- builder credential usage
- paper trading
- backtesting engine
- dashboard
- Redis runtime dependency

## Key Docs

- `build-doc.md`: master product/build document
- `docs/strategy-spec.md`: strategy rules and boundaries
- `docs/market-data-recorder.md`: Phase 2 recorder design and operations
- `docs/operations-runbook.md`: local and Docker commands
- `docs/development-roadmap.md`: phase sequence

## Setup

```bash
make install
cp .env.example .env
```

For Phase 2, set:
- `APP_MODE=record`
- `POSTGRES_PASSWORD` to a strong unique value before starting Docker Compose
- `DATABASE_URL=postgresql+psycopg://postgres:<password>@localhost:5432/polymarket_scalper` for local host usage
- or keep the compose default host `postgres` when running inside Docker

Alembic prefers `DATABASE_URL` from the environment, so `make db-migrate` works in
both local and containerized environments when that host value matches the runtime.

## Commands

```bash
make test
make lint
make format
make db-up
make db-migrate
make record
make health
make docker-build
make docker-record
make docker-test
```

## Docker

```bash
docker compose up -d postgres
docker compose run --rm app python -m alembic upgrade head
docker compose run --rm recorder
docker compose run --rm test
```

Security note:
- do not publish PostgreSQL on a public host port in production
- connect to the database through Docker's internal network or an SSH tunnel
- never leave `postgres/postgres` credentials in a public deployment

## Phase Gate

Move to Phase 3 only when:
- market discovery is reliable enough to track the current target 15-minute crypto markets and roll cleanly at expiry
- bid/ask snapshots are consistently recorded
- underlying crypto price ticks are recorded with provider labels
- timestamps align well enough for replay
- data quality gaps are understood and documented

Known Phase 2 gap:
- current live Gamma market metadata for 15-minute crypto markets does not expose the exact opening reference price directly, so the recorder resolves `opening_price` via fallback paths and stores an `opening_price_source` label to make provenance explicit
- `close_price` is now captured from the Polymarket frontend when it becomes available, but it still depends on a frontend-derived contract rather than a formal public API field
