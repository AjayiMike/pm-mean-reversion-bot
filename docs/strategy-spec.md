# Strategy Specification

## Strategy Summary

This bot targets 15-minute Polymarket crypto UP/DOWN markets and is intended to trade short-term pre-expiry odds movement rather than final market resolution.

The strategy is not "always buy the cheaper side." The strategy is "buy the cheaper side only when conditions suggest the odds are likely to rebound before expiry."

The bot is designed to scalp pre-expiry odds movement. It is not designed to hold every position until resolution. Failed scalps must not silently become expiry gambles.

## What The Bot Is Trying To Exploit

The core hypothesis is that a sharp move in the underlying crypto asset can temporarily push one side of a binary market too cheap relative to the short-term probability of a rebound or stabilization before the 15-minute market expires.

The bot is attempting to capture:
- temporary overreaction in contract odds
- short-lived mean reversion in the underlying asset
- pre-expiry repricing of the cheaper contract

## Supported Assets

Initial supported assets:
- BTC
- ETH
- SOL
- BNB
- XRP

Additional assets may be evaluated later only after data quality and market quality are verified.

## Market Assumptions

- Markets are approximately 15 minutes long.
- Each market has an opening reference price.
- `UP` resolves to `$1` if the close is above the open.
- `DOWN` resolves to `$1` if the close is below the open.
- Executable prices matter more than midpoint prices.
- Bid/ask spread, depth, fees, and slippage can erase theoretical edge.
- The system must prefer exits before expiry when a scalp fails or degrades.

## Entry Conditions

A trade is only a candidate if all of the following are acceptable:
- one side is meaningfully cheaper than the other
- the cheap side ask is at or below the configured max entry price
- time remaining is within the allowed trading window
- distance from open is not already too extreme
- spread is within the configured maximum
- visible depth is sufficient for the intended position size
- short-term momentum or stabilization supports a rebound thesis
- risk limits still allow a new entry

Directional interpretation:
- Consider `UP` only when the asset is below the market opening price and conditions suggest downside momentum is slowing or reversing.
- Consider `DOWN` only when the asset is above the market opening price and conditions suggest upside momentum is slowing or reversing.

## Exit Conditions

The system must support the following exit types:
- take profit: exit after a favorable odds move reaches the configured profit target
- stop loss: exit when the position degrades to the configured loss threshold
- force exit: exit when remaining time falls below the configured minimum hold window
- invalidation exit: exit when the original entry thesis is no longer valid

Exit discipline is more important than entry frequency.

## Risk Limits

Initial Phase 1 defaults:
- max position size: `$10`
- max trades per market: `2`
- max open positions: `2`
- daily max loss: `$50`
- max loss per market: `$10`

These are conservative placeholders for later testing, not live-optimized values.

## Variables To Track

Required strategy variables:
- asset symbol
- market id
- opening price
- current underlying price
- time remaining
- `UP` bid/ask
- `DOWN` bid/ask
- spread by side
- top-of-book or usable order book depth
- recent returns over short windows
- realized short-term volatility
- distance from open in basis points
- momentum or stabilization score
- expected fee and slippage assumptions

## Data Needed In Later Phases

Phase 2 and beyond will need:
- active market discovery
- market start and end timestamps
- order book snapshots
- recent trades and volume
- underlying crypto price ticks
- synchronized timestamps across feeds
- final market resolutions

## What The Strategy Is Not Allowed To Do

- blindly buy the cheaper side
- hold failed scalps into expiry by default
- place trades when spread, liquidity, or time remaining are unacceptable
- assume midpoint prices are executable
- enter new positions after daily loss controls trigger
- require live credentials in Phase 1
- place real orders in Phase 1

## Stage Gate For Phase 2

Move to Phase 2 only when:
- entry logic is documented clearly enough to implement without guesswork
- exit rules are explicit and testable
- risk limits are defined
- required data inputs are known
- the non-goals and exclusions are clear

Phase 2 is the market data recorder, not live trading.
