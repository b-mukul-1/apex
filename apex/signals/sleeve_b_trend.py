"""
APEX Sleeve B: Multi-Asset Volatility-Targeted Trend Following
=============================================================
Hypothesis:
    Crypto asset markets exhibit persistent medium-to-long term momentum regimes
    due to structural retail momentum chasing, ETF inflows, and reflexive liquidity
    spirals. Sizing inversely to realized volatility (vol-targeting) and trailing winners
    with ATR bounds cuts losers early while allowing right-tail trend participation.

Horizon:
    4 hours to 1 day bars (holding period 2 days to 3 weeks).

Inputs:
    - 20-period and 50-period Exponential Moving Averages (EMA)
    - 20-period Donchian Channels (Breakout High / Breakdown Low)
    - 14-period Average True Range (ATR) for volatility targeting and trailing stops

Expected Sign:
    +1.0 (Long) on Donchian 20-period high breakout above 50 EMA.
    -1.0 (Short) on Donchian 20-period low breakdown below 50 EMA.
    0.0 (Flat) when trailing stop is hit.

Capital & Leverage Constraints:
    - Capital allocation: 20% - 30%
    - Max leverage: <= 2.0x
"""

from typing import List, Dict, Optional
import numpy as np
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SleeveBTrendStrategy:
    """
    Multi-asset trend following with Donchian breakout and ATR trailing stop.
    """

    def __init__(
        self,
        lookback_breakout: int = 20,
        ema_trend_filter: int = 50,
        atr_period: int = 14,
        atr_stop_multiplier: float = 2.0,
        target_allocation: float = 0.30,
    ):
        self.sleeve_id = "B_TREND"
        self.lookback = lookback_breakout
        self.ema_filter = ema_trend_filter
        self.atr_period = atr_period
        self.atr_mult = atr_stop_multiplier
        self.target_allocation = target_allocation

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        """
        Evaluates trend breakout condition at bar close using strictly PIT data.
        """
        if bar.is_delisted:
            return []

        # Retrieve historical PIT bars for this symbol
        bars = store.get_bars_pit(bar.symbol, current_time_ms=bar.timestamp_ms, lookback_bars=self.ema_filter + 5)
        if len(bars) < self.ema_filter:
            return []

        closes = np.array([b.close for b in bars])
        highs = np.array([b.high for b in bars])
        lows = np.array([b.low for b in bars])

        # Compute ATR(14)
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )
        atr = float(np.mean(tr[-self.atr_period:])) if len(tr) >= self.atr_period else (bar.close * 0.03)

        # 50-period EMA
        weights = np.exp(np.linspace(-1.0, 0.0, self.ema_filter))
        weights /= weights.sum()
        ema50 = float(np.dot(closes[-self.ema_filter:], weights))

        # Donchian channel over lookback bars (excluding current bar)
        donchian_high = float(np.max(highs[-self.lookback - 1:-1]))
        donchian_low = float(np.min(lows[-self.lookback - 1:-1]))

        signals: List[SignalEvent] = []
        current_pos = portfolio.positions.get(bar.symbol)
        is_long = current_pos and current_pos.quantity > 0
        is_short = current_pos and current_pos.quantity < 0

        # Long breakout: close breaks Donchian high and is above 50 EMA
        if bar.close > donchian_high and bar.close > ema50:
            stop_price = bar.close - (self.atr_mult * atr)
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve_id,
                signal_id="TREND_LONG_BREAKOUT",
                direction=1.0,
                strength=0.8,
                stop_loss_price=stop_price,
                trailing_stop_atr=self.atr_mult * atr,
                expected_edge_bps=50.0,
            ))
        # Short breakdown: close breaks Donchian low and is below 50 EMA
        elif bar.close < donchian_low and bar.close < ema50:
            stop_price = bar.close + (self.atr_mult * atr)
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve_id,
                signal_id="TREND_SHORT_BREAKDOWN",
                direction=-1.0,
                strength=0.8,
                stop_loss_price=stop_price,
                trailing_stop_atr=self.atr_mult * atr,
                expected_edge_bps=50.0,
            ))

        return signals
