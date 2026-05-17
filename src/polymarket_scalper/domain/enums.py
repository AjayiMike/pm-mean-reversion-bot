from enum import StrEnum


class AssetSymbol(StrEnum):
    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"
    BNB = "BNB"
    XRP = "XRP"


class MarketSide(StrEnum):
    UP = "UP"
    DOWN = "DOWN"


class BotMode(StrEnum):
    SPEC = "spec"
    RECORD = "record"
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class ExitReason(StrEnum):
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TIME_STOP = "time_stop"
    INVALIDATION = "invalidation"
    KILL_SWITCH = "kill_switch"


class SignalAction(StrEnum):
    ENTER = "enter"
    HOLD = "hold"
    EXIT = "exit"
    SKIP = "skip"
