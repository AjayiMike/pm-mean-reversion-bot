# Risk Management

## Position Sizing

Use small fixed notional sizes at the start.

Phase 1 default:
- max position size: `$10`

This is a placeholder for later phases. Do not add dynamic sizing logic until the strategy is validated with recorded data and replay testing.

## Max Trades Per Market

Default:
- max trades per market: `2`

This limits overtrading inside a single 15-minute window and prevents repeated attempts to force a market to behave as expected.

## Max Open Positions

Default:
- max open positions: `2`

The bot should avoid stacking correlated exposure across multiple crypto assets at the same time.

## Daily Loss Limit

Default:
- daily max loss: `$50`

Once reached:
- disable new entries
- allow exits only
- require operator review before resuming

## Market-Level Loss Limit

Default:
- max loss per market: `$10`

After this threshold is reached for a market window, no further entries should be allowed for that market.

## Kill Switch

A kill switch must exist in later executable phases.

It should trigger on conditions such as:
- stale price feed
- stale order book data
- repeated API or execution errors
- abnormal slippage
- unexpected open position state
- daily loss limit breach
- behavior that diverges from expected strategy logic

## Time Stop

Default force exit threshold:
- exit when time remaining falls below `180` seconds

The intent is to avoid turning a short-duration scalp into a last-minute binary bet.

## Stop Loss

Default:
- stop loss: `25%` of position price deterioration

This threshold exists to cap damage when the expected odds rebound does not materialize.

## Invalidation Exit

An invalidation exit should close a position when the original reason for entry no longer holds.

Examples:
- holding `UP` and the underlying continues accelerating downward
- holding `DOWN` and the underlying continues accelerating upward
- distance from open exceeds the acceptable threshold after entry

## Why Failed Scalps Must Not Become Forced Expiry Gambles

This strategy is built around pre-expiry repricing, not around being correct at final settlement every time.

If a scalp fails, holding until resolution changes the strategy profile:
- holding time increases
- realized risk increases
- odds become more path-dependent near expiry
- the position turns into a directional gamble rather than a controlled scalp

That behavior must be treated as a strategy failure, not as a fallback.
