# Polymarket 15-Minute Crypto Mean-Reversion Scalping Bot

## 1. Overview

This document describes an automated trading bot concept for Polymarket’s 15-minute crypto prediction markets.

The strategy is based on short-term contrarian scalping. The bot does **not** primarily aim to hold positions until market resolution. Instead, it aims to enter temporarily underpriced positions and exit before the 15-minute window ends once the odds move favorably.

The core idea is:

> When one side of a 15-minute crypto prediction market becomes significantly cheaper due to a sharp move in the underlying crypto price, the bot may buy the cheaper side if there is enough time, volatility, liquidity, and evidence of short-term price stabilization or reversal. The bot then exits once the position reaches a predefined profit target, stop loss, or time-based exit condition.

This strategy should be treated as an engineering and statistical trading experiment, not as guaranteed profit.

---

## 2. Market Context

Polymarket offers short-duration crypto prediction markets for assets such as:

- BTC
- ETH
- SOL
- BNB
- XRP
- Other supported crypto assets

Each market lasts approximately 15 minutes.

At the start of each market window, an opening/reference price is set for the crypto asset.

Participants can buy:

- `UP`: wins if the closing price is above the opening price
- `DOWN`: wins if the closing price is below the opening price

Each share resolves to:

- `$1` if correct
- `$0` if incorrect

However, traders do not need to hold until resolution. They can buy and sell positions before expiry, taking a profit or loss based on how the market odds move.

---

## 3. Refined Strategy Description

### 3.1 Original Manual Observation

Example:

- BTC market opens at `$80,534`
- A few minutes later, BTC drops to `$80,353`
- The market prices may shift to something like:
    - `DOWN`: `$0.69`
    - `UP`: `$0.31`

A manual trader may buy `UP` at `$0.31`, expecting that BTC may bounce slightly before the 15-minute window ends.

If BTC partially recovers, the price of `UP` may rise from `$0.31` to `$0.36`, `$0.40`, or higher.

The trader then sells before expiry for a short-term profit.

### 3.2 Refined Bot Strategy

The refined strategy is:

> Buy the temporarily cheaper side only when the bot estimates that the contract is underpriced relative to the probability of a short-term rebound before expiry.

The bot should not blindly buy the cheaper side.

Instead, it should evaluate:

- How far the current crypto price is from the opening price
- How much time remains in the 15-minute window
- How volatile the asset currently is
- Whether the recent price movement is slowing, stabilizing, or reversing
- Whether the Polymarket order book has enough liquidity
- Whether fees, spread, and slippage still allow profitable exit
- Whether the position can realistically be sold before expiry

The bot’s goal is not necessarily to predict the final outcome of the market.

The goal is to capture short-term odds movement.

---

## 4. Strategy Classification

This strategy can be classified as:

```
Short-duration contrarian mean-reversion scalping strategy
```

More specifically:

```
A pre-expiry odds-reversion trading strategy for binary crypto prediction markets
```

The bot is trying to profit from temporary overreaction in the market odds after sharp movements in the underlying crypto asset.

---

## 5. Core Hypothesis

The central hypothesis is:

> In some 15-minute crypto prediction markets, after a sharp short-term move in the underlying asset, the cheaper side of the market may become temporarily underpriced. If enough time remains and the underlying asset begins to stabilize or reverse, the cheaper side’s odds may rise enough to allow a profitable pre-expiry exit.

This hypothesis must be tested with data before live trading.

## 6. Important Clarification

The strategy is **not**:

```
Always buy the cheaper side.
```

The strategy is:

```
Buy the cheaper side only when market conditions suggest that the odds are likely to rebound before expiry.
```

This distinction is critical.

A cheap contract may be cheap because it is correctly priced. For example, if BTC has moved far below the opening price and only one minute remains, the `UP` side may be cheap but still not worth buying.

# 7. Key Variables to Track

The bot should track the following variables for every active market.

## 7.1 Market Variables

| Variable            | Description                                   |
| ------------------- | --------------------------------------------- |
| `asset`             | The crypto asset, e.g. BTC, ETH, SOL          |
| `market_id`         | Unique Polymarket market identifier           |
| `window_start_time` | Start time of the 15-minute market            |
| `window_end_time`   | End time of the 15-minute market              |
| `opening_price`     | Reference price at market start               |
| `current_price`     | Current live price of the crypto asset        |
| `time_elapsed`      | Time passed since market start                |
| `time_remaining`    | Time left before expiry                       |
| `up_price`          | Current price of UP contract                  |
| `down_price`        | Current price of DOWN contract                |
| `up_bid`            | Best available bid for UP                     |
| `up_ask`            | Best available ask for UP                     |
| `down_bid`          | Best available bid for DOWN                   |
| `down_ask`          | Best available ask for DOWN                   |
| `spread`            | Difference between bid and ask                |
| `order_book_depth`  | Available liquidity at different price levels |
| `last_trade_price`  | Most recent executed trade price              |
| `volume`            | Recent market trading volume                  |

## 7.2 Derived Variables

| Variable                 | Formula / Meaning                                  |
| ------------------------ | -------------------------------------------------- |
| `distance_from_open`     | Current price minus opening price                  |
| `distance_from_open_pct` | Percentage move from opening price                 |
| `distance_from_open_bps` | Basis point move from opening price                |
| `recent_return_15s`      | Price return over last 15 seconds                  |
| `recent_return_30s`      | Price return over last 30 seconds                  |
| `recent_return_60s`      | Price return over last 60 seconds                  |
| `realized_volatility`    | Short-term volatility estimate                     |
| `momentum_score`         | Whether price is continuing, slowing, or reversing |
| `cheap_side`             | Which side is cheaper, UP or DOWN                  |
| `cheap_side_price`       | Current executable ask price of cheaper side       |
| `estimated_fee`          | Estimated trading fee                              |
| `estimated_slippage`     | Estimated execution loss from liquidity/spread     |
| `expected_exit_price`    | Target price at which the bot expects to exit      |
| `expected_net_profit`    | Estimated profit after fees and slippage           |

# 8. Trading Logic

## 8.1 Entry Logic

The bot should consider entering a trade only when several conditions are met.

### For an UP Entry

The bot may consider buying `UP` when:

```
current_price < opening_price
```

This means the asset is currently below the opening price and `UP` may have become cheaper.

However, this alone is not enough.

Additional conditions should include:

```
UP ask price is below the maximum allowed entry price
time remaining is within the allowed trading window
distance from opening price is not too extreme
recent price movement shows stabilization or upward reversal
spread is not too wide
order book depth is sufficient
expected net profit is positive after fees and slippage
maximum trades per market has not been reached
daily risk limit has not been reached
```

Example entry condition:

```
IF:
  current_price < opening_price
  up_ask <= 0.35
  time_remaining >= 4 minutes
  time_remaining <= 12 minutes
  distance_from_open_bps >= -40 bps
  recent_return_30s > recent_return_60s
  spread <= 0.03
  order_book_depth >= desired_position_size * 3
  expected_net_profit > minimum_required_profit
THEN:
  buy UP
```

### For a DOWN Entry

The bot may consider buying `DOWN` when:

```
current_price > opening_price
```

This means the asset is currently above the opening price and `DOWN` may have become cheaper.

Example condition:

```
IF:
  current_price > opening_price
  down_ask <= 0.35
  time_remaining >= 4 minutes
  time_remaining <= 12 minutes
  distance_from_open_bps <= 40 bps
  recent_return_30s < recent_return_60s
  spread <= 0.03
  order_book_depth >= desired_position_size * 3
  expected_net_profit > minimum_required_profit
THEN:
  buy DOWN
```

---

## 8.2 Exit Logic

Exit logic is more important than entry logic.

The bot should exit using predefined rules.

### Profit-Taking Exit

```
Exit when position profit reaches target percentage.
```

Example:

```
Take profit if position value increases by 8% to 20%.
```

Example:

```
Bought UP at 0.31
Target profit = 15%
Target exit price = 0.31 * 1.15 = 0.3565
```

The bot may place a limit sell at around `0.36`, depending on spread and liquidity.

---

### Stop-Loss Exit

```
Exit when position loss reaches maximum allowed loss.
```

Example:

```
Stop loss if position value falls by 20% to 35%.
```

Example:

```
Bought UP at 0.31
Stop loss = 25%
Stop price = 0.31 * 0.75 = 0.2325
```

---

### Time-Based Exit

The bot should avoid accidentally holding losing scalps until expiry.

Example:

```
Exit if less than 2 or 3 minutes remain before expiry.
```

This prevents the strategy from becoming a pure binary gamble.

---

### Invalidation Exit

The bot should exit early if the original reason for entering the trade becomes invalid.

Example:

```
For UP:
  Exit if BTC continues moving sharply lower after entry.

For DOWN:
  Exit if BTC continues moving sharply higher after entry.
```

Example invalidation rule:

```
IF:
  holding UP
  current_price moves further below opening_price
  distance_from_open_bps exceeds maximum allowed distance
THEN:
  exit position
```

# 9. Risk Management Rules

Risk management should be built into the bot from the beginning.

## 9.1 Position Sizing

Start with small fixed position sizes.

Example:

```
position_size = $5 to $20 per trade during live testing
```

Later, position sizing may be adjusted based on:

- Liquidity
- Confidence score
- Historical win rate
- Market volatility
- Daily profit/loss

Do not use aggressive scaling until the strategy has proven positive expectancy.

---

## 9.2 Maximum Trades Per Market

The bot should limit the number of trades in each 15-minute market.

Example:

```
max_trades_per_market = 2
```

This prevents overtrading and revenge trading.

---

## 9.3 Maximum Open Positions

The bot should limit simultaneous exposure.

Example:

```
max_open_positions = 1 to 3
```

The bot should avoid opening many correlated positions at the same time, especially across crypto assets that move together.

---

## 9.4 Daily Loss Limit

The bot must stop trading if daily losses exceed a predefined amount.

Example:

```
daily_max_loss = $50
```

Once reached:

```
disable new entries for the rest of the day
allow exits only
```

---

## 9.5 Market-Level Loss Limit

The bot should stop trading a specific market after a loss.

Example:

```
max_loss_per_market = $10
```

---

## 9.6 Kill Switch

The bot must include a manual and automatic kill switch.

The kill switch should activate if:

```
API errors become frequent
price feed becomes stale
order book data becomes stale
unexpected position appears
daily loss limit is reached
abnormal slippage occurs
bot behavior differs from expected logic
```

# 10. Development Stages

The project should be built in stages.

Do not start with live trading.

Each stage has:

- Objective
- What to build
- How to build it
- Output
- Conditions for moving to the next stage

# Stage 1: Strategy Specification

## Objective

Clearly define the trading strategy, assumptions, rules, and measurable success criteria.

## What We Aim to Achieve

At this stage, the goal is to convert the trading idea into a precise system specification.

The bot should not be built yet.

We want to answer:

```
What exactly is the bot allowed to do?
When does it enter?
When does it exit?
When does it stay out?
How much can it risk?
What counts as success?
What counts as failure?
```

## What to Build

Create a written strategy specification containing:

- Supported assets
- Entry rules
- Exit rules
- Risk limits
- Required data feeds
- Minimum liquidity requirements
- Fee assumptions
- Slippage assumptions
- Backtesting requirements
- Paper trading requirements
- Live trading requirements

## How to Build It

Create a markdown or technical document that defines:

```
entry_conditions
exit_conditions
risk_limits
market_filters
position_sizing_rules
logging_requirements
performance_metrics
```

Example configuration:

```
supported_assets:
  - BTC
  - ETH
  - SOL

entry:
  max_cheap_side_price: 0.35
  min_time_remaining_seconds: 240
  max_time_remaining_seconds: 720
  max_spread: 0.03
  min_order_book_depth_multiplier: 3

exit:
  take_profit_pct: 0.15
  stop_loss_pct: 0.25
  force_exit_time_remaining_seconds: 180

risk:
  max_trades_per_market: 2
  max_open_positions: 2
  daily_max_loss_usd: 50
  max_position_size_usd: 10
```

## Output

A complete strategy specification document.

## Condition for Moving to Stage 2

Move to Stage 2 only when:

```
The strategy rules are specific enough that a developer or AI agent can implement them without guessing.
```

Do not move forward if:

```
Entry and exit conditions are vague.
Risk limits are undefined.
Success metrics are undefined.
Required data is unknown.
```

# Stage 2: Market Data Recorder

## Objective

Build a system that records live Polymarket market data and underlying crypto price data without placing trades.

## What We Aim to Achieve

The goal is to collect enough historical data to test whether the strategy has potential.

The recorder should capture what the bot would have seen in real time.

This stage answers:

```
How do these markets actually behave?
How often do cheap-side reversions happen?
How much does spread affect profitability?
How often is there enough liquidity to enter and exit?
```

## What to Build

Build a data recorder that collects:

- Active market IDs
- Asset symbol
- Market start time
- Market end time
- Opening price
- Live underlying price
- UP bid/ask
- DOWN bid/ask
- Order book depth
- Recent trades
- Volume
- Final market outcome
- Timestamped snapshots

## How to Build It

Use the following components:

```
1. Market discovery service
2. Polymarket order book WebSocket listener
3. Crypto price feed listener
4. Data normalizer
5. Database writer
6. Logging and monitoring
```

Recommended database tables:

```
markets
market_snapshots
order_book_snapshots
trades
underlying_price_ticks
resolutions
```

Example snapshot structure:

```
{
  "timestamp":"2026-01-01T07:03:15Z",
  "asset":"BTC",
  "market_id":"example_market_id",
  "opening_price":80534,
  "current_price":80353,
  "time_remaining_seconds":705,
  "up_bid":0.30,
  "up_ask":0.31,
  "down_bid":0.68,
  "down_ask":0.69,
  "up_depth":2500,
  "down_depth":2200,
  "spread_up":0.01,
  "spread_down":0.01
}
```

## Output

A live data recorder that can run continuously and store market data.

## Minimum Data Collection Target

Collect data for at least:

```
500 to 1,000 completed markets
```

Preferably across:

```
BTC, ETH, SOL, BNB, XRP
```

## Condition for Moving to Stage 3

Move to Stage 3 only when:

```
The recorder reliably captures complete market data from start to resolution.
At least 500 completed market windows have been recorded.
Data includes bid/ask prices, not only mid prices.
Data includes order book depth.
Data includes final market outcomes.
Data quality issues are understood and documented.
```

Do not move forward if:

```
Data has frequent gaps.
Opening prices are missing.
Bid/ask prices are missing.
Resolution data is missing.
Crypto price feed and Polymarket timestamps are not aligned.
```

# Stage 3: Backtesting and Replay Engine

## Objective

Build a replay engine that simulates how the bot would have traded using historical recorded data.

## What We Aim to Achieve

The goal is to test whether the strategy would have been profitable under realistic execution assumptions.

This stage answers:

```
Does the strategy have positive expectancy?
Which assets perform best?
Which time windows are safest?
Which entry thresholds work best?
Which exit rules work best?
How much do fees and spread affect returns?
```

## What to Build

Build a backtesting engine that can:

- Replay each market second by second
- Apply entry rules
- Apply exit rules
- Simulate executable buy and sell prices
- Include fees
- Include spread
- Include slippage
- Include missed fills
- Track performance metrics
- Compare different parameter sets

## How to Build It

The replay engine should not use future data.

At each timestamp, the bot can only see data available at that time.

For each market:

```
1. Load market snapshots in chronological order.
2. Calculate derived variables.
3. Check whether entry conditions are met.
4. Simulate entry using ask price.
5. Track open position.
6. Check exit conditions at each later timestamp.
7. Simulate exit using bid price.
8. Record profit/loss.
9. Continue until market ends.
```

Important execution rule:

```
Use ask price for buying.
Use bid price for selling.
Do not use mid-price as executable price.
```

## Backtest Metrics

Track:

| Metric                           | Meaning                             |
| -------------------------------- | ----------------------------------- |
| Total trades                     | Number of simulated trades          |
| Win rate                         | Percentage of profitable trades     |
| Average win                      | Average profit on winning trades    |
| Average loss                     | Average loss on losing trades       |
| Expected value per trade         | Average net profit per trade        |
| Profit factor                    | Gross profit divided by gross loss  |
| Max drawdown                     | Largest peak-to-trough loss         |
| Sharpe-like ratio                | Risk-adjusted consistency           |
| Average holding time             | Time between entry and exit         |
| Fee impact                       | How much fees reduce returns        |
| Slippage impact                  | How much slippage reduces returns   |
| Performance by asset             | BTC vs ETH vs SOL etc.              |
| Performance by time remaining    | When strategy works best            |
| Performance by volatility regime | Low vs high volatility environments |

## Parameter Experiments

Test variations such as:

```
max_entry_price:
  - 0.25
  - 0.30
  - 0.35
  - 0.40

take_profit_pct:
  - 0.08
  - 0.10
  - 0.15
  - 0.20

stop_loss_pct:
  - 0.15
  - 0.20
  - 0.25
  - 0.35

min_time_remaining_seconds:
  - 180
  - 240
  - 300

force_exit_time_remaining_seconds:
  - 60
  - 120
  - 180
```

## Output

A backtesting report showing:

- Whether the strategy appears profitable
- Best and worst parameter sets
- Performance by asset
- Performance by market condition
- Failure cases
- Recommended settings for paper trading

## Condition for Moving to Stage 4

Move to Stage 4 only when:

```
The backtest shows positive net expected value after fees, spread, and slippage.
The result is not dependent on one or two lucky trades.
The strategy works across a meaningful sample size.
Drawdowns are acceptable.
The bot has clear rules for when not to trade.
```

Suggested minimum thresholds:

```
minimum completed markets tested: 500
minimum simulated trades: 200
profit factor: greater than 1.2
positive expected value after fees
max drawdown within acceptable risk limit
no single asset or single day accounts for most profit
```

Do not move forward if:

```
The strategy is only profitable before fees.
The strategy relies on mid-price exits.
The strategy has large uncontrolled drawdowns.
The strategy only works on a tiny sample.
The strategy performs badly during trending markets.
```

# Stage 4: Paper Trading

## Objective

Run the bot live without placing real trades.

The bot should make simulated decisions in real time using live market data.

## What We Aim to Achieve

The goal is to verify that the strategy still works outside historical backtesting.

Paper trading answers:

```
Can the bot make decisions in real time?
Are live data feeds reliable?
Are simulated entries and exits realistic?
Are there latency problems?
Does performance match backtest expectations?
```

## What to Build

Build a paper trading system that includes:

- Live market listener
- Signal engine
- Simulated order manager
- Simulated portfolio
- Real-time logs
- Performance dashboard
- Alert system
- Daily summary report

## How to Build It

When the bot detects a trade:

```
1. Log the signal.
2. Simulate buying at the current ask.
3. Track the position.
4. Simulate selling at the current bid.
5. Include estimated fees.
6. Include estimated slippage.
7. Record the trade result.
```

The paper trading system should behave exactly like the live trading system, except that it does not send orders to Polymarket.

## Required Logs

Every decision should be logged.

Example trade log:

```
{
  "timestamp":"2026-01-01T07:04:12Z",
  "mode":"paper",
  "asset":"BTC",
  "market_id":"example_market_id",
  "action":"BUY_UP",
  "entry_price":0.31,
  "position_size":10,
  "opening_price":80534,
  "current_price":80353,
  "time_remaining_seconds":648,
  "reason":"UP cheap, price stabilizing, spread acceptable",
  "risk_check_passed":true
}
```

Example exit log:

```
{
  "timestamp":"2026-01-01T07:07:22Z",
  "mode":"paper",
  "asset":"BTC",
  "market_id":"example_market_id",
  "action":"SELL_UP",
  "exit_price":0.36,
  "entry_price":0.31,
  "net_profit":1.45,
  "exit_reason":"take_profit"
}
```

## Output

A paper trading report showing:

- Number of paper trades
- Win rate
- Net profit/loss
- Average profit per trade
- Average loss per trade
- Slippage assumptions
- Missed trade count
- Errors and data issues
- Comparison against backtest expectations

## Recommended Paper Trading Duration

Run paper trading for at least:

```
1 to 2 weeks
```

Or until the bot has generated at least:

```
200 to 500 paper trades
```

## Condition for Moving to Stage 5

Move to Stage 5 only when:

```
Paper trading remains positive after realistic costs.
Live behavior is close to backtest expectations.
The bot handles data interruptions safely.
All trades are fully logged.
Risk controls work correctly.
The bot does not overtrade.
The bot exits positions correctly.
```

Suggested minimum thresholds:

```
minimum paper trades: 200
positive net expected value
profit factor: greater than 1.1
no major unhandled errors
all stop-loss and time-exit rules tested successfully
daily loss limit tested successfully
kill switch tested successfully
```

Do not move forward if:

```
Paper trading is materially worse than backtesting.
The bot misses exits.
The bot enters duplicate positions unexpectedly.
Data feed interruptions cause bad decisions.
The strategy is only profitable before fees.
```

# Stage 5: Small Live Trading

## Objective

Deploy the bot with real money using very small position sizes.

## What We Aim to Achieve

The goal is not to maximize profit yet.

The goal is to verify that real execution matches simulation.

This stage answers:

```
Can the bot place real orders correctly?
Can the bot exit correctly?
How much real slippage occurs?
Are fees modeled correctly?
Does live performance match paper trading?
```

## What to Build

Build live execution features:

- Polymarket authentication
- Real order placement
- Position tracking
- Order status tracking
- Partial fill handling
- Cancel/replace logic
- Emergency exit logic
- Live risk manager
- Real-time alerts

## How to Build It

Start with conservative settings.

Example:

```
mode: live
max_position_size_usd: 5
max_trades_per_market: 1
max_open_positions: 1
daily_max_loss_usd: 20
take_profit_pct: 0.10
stop_loss_pct: 0.20
force_exit_time_remaining_seconds: 180
```

The live bot should:

```
1. Detect signal.
2. Check all risk limits.
3. Place order.
4. Confirm fill.
5. Track position.
6. Place exit order or monitor exit conditions.
7. Exit on take profit, stop loss, invalidation, or time stop.
8. Log everything.
```

## Output

A live trading report comparing:

- Expected entry price vs actual entry price
- Expected exit price vs actual exit price
- Estimated fees vs actual fees
- Expected slippage vs actual slippage
- Paper trading performance vs live trading performance
- Error events
- Manual intervention events

## Condition for Moving to Stage 6

Move to Stage 6 only when:

```
The bot executes correctly with real funds.
Position tracking is accurate.
Order handling is reliable.
Real slippage is within acceptable limits.
Live results are not materially worse than paper results.
Risk limits work in real conditions.
```

Suggested minimum thresholds:

```
minimum live trades: 100
no serious execution bugs
no untracked positions
no missed forced exits
daily loss limit works
kill switch works
actual slippage is within modeled assumptions
```

Do not move forward if:

```
The bot loses money due to execution errors.
The bot cannot reliably exit.
Orders remain open unexpectedly.
Position state becomes inaccurate.
Manual intervention is frequently required.
```

# Stage 6: Optimization and Scaling

## Objective

Improve the strategy and cautiously increase position size only if live results justify it.

## What We Aim to Achieve

The goal is to improve performance without overfitting.

At this stage, the bot should already be stable.

Optimization should focus on:

- Better entries
- Better exits
- Better asset selection
- Better volatility filters
- Better risk control
- Lower execution cost

## What to Build

Enhancements may include:

- Asset-specific parameters
- Volatility regime detection
- Momentum reversal scoring
- Dynamic position sizing
- Maker order entries
- Adaptive profit targets
- News/event avoidance filter
- Correlation exposure control
- Performance dashboard
- Automated daily reports

## How to Build It

Optimization should be based on evidence.

For each proposed improvement:

```
1. Form a hypothesis.
2. Test it on historical data.
3. Test it in paper trading.
4. Test it with small live size.
5. Keep it only if it improves risk-adjusted performance.
```

Example:

```
Hypothesis:
BTC and ETH have better liquidity and lower slippage than smaller assets.

Test:
Compare net expected value by asset after fees and slippage.

Decision:
Trade only assets with positive live expectancy.
```

## Output

An improved strategy report showing:

- Which parameters were changed
- Why they were changed
- Before/after performance
- Risk impact
- Whether the change was accepted or rejected

## Condition for Scaling Position Size

Increase position size only when:

```
Live trading is profitable after fees.
Execution is stable.
Drawdowns are controlled.
Performance is consistent across multiple days.
The strategy does not rely on rare lucky trades.
```

Example scaling rule:

```
Increase max position size by 25% only after every 200 profitable live trades,
provided max drawdown remains below the allowed threshold.
```

Do not scale if:

```
Recent performance is negative.
Slippage increases with size.
Liquidity is insufficient.
The bot is taking correlated trades.
There are unresolved execution errors.
```

# Stage 7: Production Hardening

## Objective

Make the bot reliable enough to run with minimal supervision.

## What We Aim to Achieve

The goal is operational safety.

The bot should be able to handle common failures without creating dangerous exposure.

## What to Build

Production features:

- Persistent state storage
- Restart recovery
- Position reconciliation
- Order reconciliation
- Error alerts
- Health checks
- Data feed monitoring
- Latency monitoring
- Automatic safe mode
- Manual dashboard
- Full audit logs
- Configuration versioning

## How to Build It

The bot should regularly compare:

```
internal_position_state
actual_polymarket_position_state
open_orders
available_balance
recent_fills
```

If anything does not match:

```
pause new entries
alert operator
attempt safe reconciliation
```

## Output

A production-ready system with:

- Monitoring
- Alerts
- Recovery logic
- Audit trail
- Tested failure handling

## Condition for Ongoing Operation

The bot may continue running only when:

```
Data feeds are healthy.
Position state is accurate.
Risk limits are active.
Logs are being written.
Kill switch is available.
Performance remains within expected range.
```

The bot should stop automatically when:

```
Data feed is stale.
API errors exceed threshold.
Unexpected position appears.
Daily loss limit is reached.
Unusual slippage is detected.
Market behavior changes significantly.
```

# 11. Suggested Technical Architecture

## 11.1 Main Components

```
1. Market Discovery Service
2. Crypto Price Feed Service
3. Polymarket Order Book Listener
4. Data Storage Layer
5. Feature Calculation Engine
6. Strategy Signal Engine
7. Risk Manager
8. Order Execution Engine
9. Position Manager
10. Backtesting Engine
11. Paper Trading Engine
12. Monitoring and Alerting System
13. Dashboard
```

---

## 11.2 Component Responsibilities

### Market Discovery Service

Find active 15-minute crypto markets and identify:

```
asset
market_id
UP token ID
DOWN token ID
start time
end time
opening price
```

### Crypto Price Feed Service

Track live asset prices from reliable crypto data sources.

The bot must ensure the price feed is aligned as closely as possible with the market’s official resolution source.

### Polymarket Order Book Listener

Listen to live Polymarket order book updates.

Track:

```
best bid
best ask
spread
depth
recent trades
```

### Feature Calculation Engine

Calculate:

```
distance from open
time remaining
recent returns
volatility
momentum score
liquidity score
expected profit
```

### Strategy Signal Engine

Decide whether a trade setup exists.

Output:

```
{
  "signal":"BUY_UP",
  "confidence":0.72,
  "reason":"UP cheap, BTC stabilizing, enough time remaining",
  "recommended_entry_price":0.31,
  "recommended_exit_price":0.36
}
```

### Risk Manager

Approve or reject signals based on risk rules.

Reject trades if:

```
daily loss limit reached
max trades per market reached
position size too large
spread too wide
liquidity too low
too little time remaining
correlated exposure too high
```

### Order Execution Engine

For live mode, place and manage orders.

For paper mode, simulate orders.

### Position Manager

Track:

```
open positions
entry price
entry time
current mark price
unrealized profit/loss
exit conditions
```

### Monitoring and Alerting System

Send alerts for:

```
trade entry
trade exit
stop loss
daily loss limit
data feed issue
API error
unexpected position
kill switch activation
```

# 12. Suggested Data Schema

## markets

```
CREATETABLE markets (
  id TEXTPRIMARYKEY,
  asset TEXT,
  start_timeTIMESTAMP,
  end_timeTIMESTAMP,
  opening_priceNUMERIC,
  final_priceNUMERIC,
  outcome TEXT,
  created_atTIMESTAMP
);
```

## market_snapshots

```
CREATETABLE market_snapshots (
  id BIGSERIALPRIMARYKEY,
  market_id TEXT,
timestampTIMESTAMP,
  current_priceNUMERIC,
  time_remaining_secondsINTEGER,
  up_bidNUMERIC,
  up_askNUMERIC,
  down_bidNUMERIC,
  down_askNUMERIC,
  up_depthNUMERIC,
  down_depthNUMERIC,
  spread_upNUMERIC,
  spread_downNUMERIC
);
```

## simulated_trades

```
CREATETABLE simulated_trades (
  id BIGSERIALPRIMARYKEY,
  market_id TEXT,
  asset TEXT,
  side TEXT,
  entry_timeTIMESTAMP,
  entry_priceNUMERIC,
  exit_timeTIMESTAMP,
  exit_priceNUMERIC,
  size_usdNUMERIC,
  gross_pnlNUMERIC,
  feesNUMERIC,
  slippageNUMERIC,
  net_pnlNUMERIC,
  exit_reason TEXT
);
```

## live_trades

```
CREATETABLE live_trades (
  id BIGSERIALPRIMARYKEY,
  market_id TEXT,
  asset TEXT,
  side TEXT,
  order_id TEXT,
  entry_timeTIMESTAMP,
  entry_priceNUMERIC,
  exit_timeTIMESTAMP,
  exit_priceNUMERIC,
  size_usdNUMERIC,
  feesNUMERIC,
  net_pnlNUMERIC,
  status TEXT,
  exit_reason TEXT
);
```

# 13. Example Bot Decision Flow

```
START

For each active 15-minute crypto market:

  Get opening price
  Get current underlying price
  Get UP/DOWN order book
  Calculate time remaining
  Calculate distance from opening price
  Calculate short-term momentum
  Calculate spread and liquidity
  Identify cheap side

  IF no trade setup:
    do nothing

  IF trade setup exists:
    send setup to risk manager

  IF risk manager rejects:
    log rejection reason
    do nothing

  IF risk manager approves:
    enter position

  WHILE position is open:
    update market data
    update unrealized PnL

    IF take profit hit:
      exit position

    ELSE IF stop loss hit:
      exit position

    ELSE IF invalidation condition hit:
      exit position

    ELSE IF force-exit time reached:
      exit position

    ELSE:
      continue monitoring

END
```

# 14. Example Strategy Configuration

```
bot:
  mode: paper

assets:
  - BTC
  - ETH
  - SOL

entry:
  max_entry_price: 0.35
  min_time_remaining_seconds: 240
  max_time_remaining_seconds: 720
  max_abs_distance_from_open_bps: 40
  max_spread: 0.03
  min_depth_multiplier: 3
  require_momentum_confirmation: true

exit:
  take_profit_pct: 0.15
  stop_loss_pct: 0.25
  force_exit_time_remaining_seconds: 180
  use_invalidation_exit: true

risk:
  max_position_size_usd: 10
  max_trades_per_market: 2
  max_open_positions: 2
  daily_max_loss_usd: 50
  max_loss_per_market_usd: 10

execution:
  prefer_limit_orders: true
  allow_marketable_limit_orders: true
  max_slippage: 0.02
  cancel_unfilled_order_after_seconds: 10

logging:
  log_all_signals: true
  log_rejected_signals: true
  log_order_book_snapshots: true
  log_position_updates: true
```

# 15. Success Metrics

The strategy should be evaluated using net results after all costs.

Important metrics:

```
net profit
expected value per trade
win rate
average win
average loss
profit factor
max drawdown
average holding time
fee impact
slippage impact
trade frequency
performance by asset
performance by time remaining
performance by volatility condition
```

The most important metric is:

```
positive expected value per trade after fees, spread, and slippage
```

---

#

# 16. Failure Conditions

The strategy should be considered weak or invalid if:

```
It is only profitable before fees.
It depends on unrealistic mid-price fills.
It loses heavily during trending markets.
It requires perfect exits.
It cannot handle slippage.
It has large drawdowns.
It only works on a small sample.
It performs much worse in paper trading than backtesting.
It performs much worse live than paper trading.
```

# 17. Initial MVP Recommendation

The first real MVP should not place trades.

The first MVP should be:

```
Market Data Recorder + Backtesting Engine
```

This MVP should answer:

```
Does the strategy have a measurable edge?
```

Only after this is answered should the project move toward paper trading or live trading.

Recommended MVP scope:

```
Assets: BTC and ETH only
Mode: data recording only
Duration: 1 to 2 weeks
Output: backtest-ready dataset
```

# 18. Final Implementation Roadmap

## Phase 1

```
Write complete strategy specification
```

## Phase 2

```
Build market data recorder
```

## Phase 3

```
Collect 500 to 1,000 completed market windows
```

## Phase 4

```
Build replay/backtesting engine
```

## Phase 5

```
Optimize and validate strategy parameters
```

## Phase 6

```
Run paper trading for 200 to 500 simulated live trades
```

## Phase 7

```
Deploy very small live trading bot
```

## Phase 8

```
Compare real execution against simulation
```

## Phase 9

```
Improve, harden, and cautiously scale
```

# 19. Guiding Principle

The bot should only move from one stage to the next when the previous stage proves that the strategy is still valid under more realistic conditions.

The progression should be:

```
Idea
→ Specification
→ Data collection
→ Backtesting
→ Paper trading
→ Small live trading
→ Optimization
→ Scaling
→ Production hardening
```

At every stage, the question is:

```
Does the strategy still work after adding more realism?
```

If the answer is no, the bot should not move forward.

---

# 20. Summary

This project aims to build a Polymarket 15-minute crypto prediction market bot that trades short-term odds reversions.

The bot will look for situations where one side of the market becomes temporarily cheap after a sharp underlying crypto price move.

The bot will only enter when:

```
the cheap side appears underpriced
there is enough time remaining
the price movement shows signs of stabilization or reversal
liquidity is sufficient
spread is acceptable
expected profit remains positive after costs
risk limits allow the trade
```

The bot will exit using:

```
take profit
stop loss
time stop
invalidation stop
```

The project should be built gradually, starting with data recording and backtesting before any live trading.

The most important rule is:

```
Do not automate real trading until the strategy shows positive expected value after fees, spread, slippage, and realistic execution assumptions.
```
