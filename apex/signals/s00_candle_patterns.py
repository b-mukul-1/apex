"""
Signal S00: Control Group — Classic Candlestick & Chart Patterns
================================================================
Hypothesis:
    Textbook candlestick patterns (e.g. Bullish Engulfing, Hammer, Shooting Star)
    are publicly known retail heuristics. In institutional, fee-frictioned crypto markets,
    raw unconditioned candlestick patterns possess ZERO statistical edge net of spreads
    and trading fees.
    Expected outcome: Zero or negative net edge after cost.
    Any backtest showing large positive net Sharpe on raw candlestick patterns without
    order flow or regime conditioning must be treated as overfitted or bug-ridden.

Horizon:
    1 bar to 3 bars.

Inputs:
    - Current bar Open, High, Low, Close
    - Prior bar Open, High, Low, Close
"""

from typing import List
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalControlCandlestick:
    def __init__(self):
        self.signal_id = "S00_CONTROL_CANDLE"
        self.sleeve = "C_ALPHA"

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted:
            return []

        bars = store.get_bars_pit(bar.symbol, current_time_ms=bar.timestamp_ms, lookback_bars=2)
        if len(bars) < 2:
            return []

        prev = bars[0]
        curr = bar
        signals: List[SignalEvent] = []
        stop_dist = curr.close * 0.02

        # Pattern 1: Bullish Engulfing
        if (prev.close < prev.open) and (curr.close > curr.open) and (curr.close > prev.open) and (curr.open < prev.close):
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=1.0,
                strength=0.5,
                stop_loss_price=curr.close - stop_dist,
                take_profit_price=curr.close + stop_dist,
                expected_edge_bps=5.0,  # Small gross edge, eaten by fees
            ))
        # Pattern 2: Bearish Engulfing
        elif (prev.close > prev.open) and (curr.close < curr.open) and (curr.close < prev.open) and (curr.open > prev.close):
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,
                strength=0.5,
                stop_loss_price=curr.close + stop_dist,
                take_profit_price=curr.close - stop_dist,
                expected_edge_bps=5.0,
            ))

        return signals
