# Market Data Recorder

## What Phase 2 Records

Phase 2 records public market data only:
- active Polymarket 15-minute crypto market metadata
- public Polymarket order book state for UP/DOWN tokens
- underlying crypto asset prices
- normalized timestamped snapshots for replay and later backtesting

It does not place trades, sign orders, or use private credentials.

## Two Separate Data Types

### Polymarket CLOB market data

This is prediction-market data:
- UP bid/ask
- DOWN bid/ask
- order book depth
- price changes
- trade and best-bid/ask events where available
- tick-size changes for contract pricing

### Underlying crypto asset price data

This is the real asset being predicted:
- BTC price
- ETH price
- SOL price
- BNB price
- XRP price

These are not interchangeable. The strategy later needs both.

## Why `UnderlyingPriceFeed` Exists

The recorder must keep the underlying asset price separate from the prediction contract state. That is why Phase 2 introduces a swappable `UnderlyingPriceFeed` abstraction.

Current provider order:
1. `polymarket_rtds`
2. `mock`
3. Binance fallback is documented as a later option if needed, but it is not hardcoded as the project default

## Why Polymarket RTDS Is Preferred First

Polymarket’s public RTDS currently documents crypto price streams without authentication. That makes it the cleanest first provider because it stays inside the Polymarket public data surface. The recorder keeps the provider swappable because this still needs validation against the eventual market resolution source before live trading phases.

## Market Discovery

The recorder uses public Gamma market metadata and applies conservative filtering:
- active markets only
- not closed
- question text must look like a 15-minute crypto market
- question text must contain an identifiable supported asset
- token IDs must be present for both sides

Accepted and rejected candidates are logged so naming-rule drift is visible.

For the current 15-minute crypto markets, discovery is slug-based because that is the path that is working reliably in live testing. The recorder resolves quarter-hour slugs such as `btc-updown-15m-<epoch>` and stores the market metadata returned by Gamma.
The recorder targets the current live quarter-hour window only. When that market window ends, the recorder refreshes discovery on the next snapshot cycle, switches to the next current slug, retires the stale market as inactive, and rotates the active listeners.

## WebSocket Market Data

The public Polymarket market channel is used for UP/DOWN token state.

The recorder normalizes:
- best bid
- best ask
- spread
- mid price
- visible depth
- raw payloads when configured

## Underlying Crypto Prices

The active `UnderlyingPriceFeed` stores normalized ticks with:
- asset
- symbol
- timestamp
- price
- provider
- optional raw payload

This allows later comparison between providers and easier replay of what the bot actually knew at each time.

## Market Boundary Price Handling

The recorder treats market boundary prices as a separate data-quality concern.

Resolution order:
- explicit market metadata field, if Gamma exposes one
- Polymarket event-page `__NEXT_DATA__` fallback, if the frontend dehydrated state exposes `openPrice`
- latest recorded underlying tick at or before the market window start, but only when the tick is fresh enough to be defensible

When an opening price is stored, the recorder also stores `opening_price_source` so metadata-derived, reconstructed, and frontend-derived values are distinguishable.
It also stores:
- `opening_price_reference_timestamp`
- `opening_price_reference_provider`
- `opening_price_resolved_at`

This makes it possible to audit exactly which timestamp and provider informed the resolved opening price.

The recorder also stores `close_price` on each market when the Polymarket frontend begins exposing `closePrice`. That gives the project an explicit record that the market has ended, which is useful for rollover audits and later replay validation.

## Database Schema

Phase 2 creates:
- `markets`
- `market_snapshots`
- `order_book_snapshots`
- `underlying_price_ticks`
- `recorder_runs`

The schema stores bid/ask data, not just mid prices.

## Run Locally

```bash
make install
cp .env.example .env
make db-up
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/polymarket_scalper
make db-migrate
APP_MODE=record make record
```

## Run With Docker

```bash
cp .env.example .env
docker compose up -d postgres
docker compose run --rm recorder
docker compose run --rm test
```

## Data Quality Issues To Watch

- exact opening price is not currently exposed in the live Gamma payloads we tested for 15-minute crypto markets
- the recorder therefore falls back to either recorded underlying ticks or the event page's frontend dehydrated state
- exact closing price is also treated as frontend-derived metadata for now
- frontend-derived opening prices are useful, but they are still based on a frontend-internal contract and should not be treated as the final live-trading source of truth without further validation
- market naming conventions may change, which can affect filter accuracy
- RTDS symbol availability and message shape must be validated continuously against real traffic
- missing or sparse order book updates can create snapshot gaps
- timestamps between CLOB and underlying price feeds must be compared before Phase 3 replay work

## Phase 3 Gate

Before moving to Phase 3:
- bid/ask snapshots must be recorded consistently
- underlying price ticks must be persisted with provider labels
- discovery quality must be good enough to capture the intended market set
- timestamp alignment must be understood
- raw payload retention must be sufficient to debug parsing gaps
