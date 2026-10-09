"""
APEX Regime Classifier
======================
Classifies market states into discrete regimes:
1. BULL_TREND: Strong upward momentum, expanding volatility, positive funding
2. BEAR_TREND: Strong downward momentum, spike in downside volatility
3. CHOP_RANGE: Low volatility, mean-reverting price action, tight spreads
4. CRISIS_LIQUIDATION: Extreme volatility spike, breakdown in liquidity, cascading liquidations
"""

from enum import Enum
from typing import List
import numpy as np
from apex.data.store import MarketBar, PointInTimeStore


class MarketRegime(Enum):
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    CHOP_RANGE = "CHOP_RANGE"
    CRISIS_LIQUIDATION = "CRISIS_LIQUIDATION"


class RegimeClassifier:
    def __init__(self, lookback_bars: int = 30):
        self.lookback = lookback_bars

    def classify(self, symbol: str, current_time_ms: int, store: PointInTimeStore) -> MarketRegime:
        bars = store.get_bars_pit(symbol, current_time_ms=current_time_ms, lookback_bars=self.lookback)
        if len(bars) < self.lookback:
            return MarketRegime.CHOP_RANGE

        closes = np.array([b.close for b in bars])
        vols = np.array([b.volume for b in bars])
        funding = bars[-1].funding_rate_8h

        # Compute return drift & volatility
        ret_total = (closes[-1] / closes[0]) - 1.0
        daily_returns = np.diff(closes) / closes[:-1]
        vol = np.std(daily_returns)

        # Crisis detection
        if vol > 0.06 or (funding < -0.0005) or (ret_total < -0.25):
            return MarketRegime.CRISIS_LIQUIDATION

        # Trend vs Range
        if ret_total > 0.10 and closes[-1] > np.mean(closes):
            return MarketRegime.BULL_TREND
        elif ret_total < -0.10 and closes[-1] < np.mean(closes):
            return MarketRegime.BEAR_TREND
        else:
            return MarketRegime.CHOP_RANGE
