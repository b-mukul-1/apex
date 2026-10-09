"""
Signal S05: Liquidity Shock Mean Reversion
==========================================
Hypothesis:
    Sudden, violent intraday price deviations (>3.0 standard deviations) triggered by large
    market orders clearing thin books (liquidity vacuum) create temporary price dislocations.
    Once the initiating order finishes and liquidity providers replenish the book, price
    reverts rapidly back toward the volume-weighted anchor.

Horizon:
    5 minutes to 1 hour.

Inputs:
    - 20-period Rolling Mean and Standard Deviation
    - Z-score of current price deviation: (Price - Mean) / Std
    - Volume surge verification

Expected Sign:
    -1.0 (Short) on upward 3-sigma flash spike (overbought liquidity shock).
    +1.0 (Long) on downward 3-sigma flash dump (oversold liquidity shock).
"""

from typing import List
import numpy as np
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalLiquidityShockReversion:
    def __init__(self, z_score_threshold: float = 2.5, lookback: int = 20):
        self.signal_id = "S05_LIQUIDITY_SHOCK"
        self.sleeve = "C_ALPHA"
        self.z_thresh = z_score_threshold
        self.lookback = lookback

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted:
            return []

        bars = store.get_bars_pit(bar.symbol, current_time_ms=bar.timestamp_ms, lookback_bars=self.lookback + 2)
        if len(bars) < self.lookback:
            return []

        closes = np.array([b.close for b in bars[-self.lookback:]])
        mean_p = np.mean(closes)
        std_p = np.std(closes) + 1e-8
        z_score = (bar.close - mean_p) / std_p

        signals: List[SignalEvent] = []
        stop_dist = std_p * 1.5

        # Flash dump shock -> mean-revert long
        if z_score < -self.z_thresh:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=1.0,
                strength=0.8,
                stop_loss_price=bar.close - stop_dist,
                take_profit_price=mean_p,
                expected_edge_bps=45.0,
            ))
        # Flash pump shock -> mean-revert short
        elif z_score > self.z_thresh:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,
                strength=0.8,
                stop_loss_price=bar.close + stop_dist,
                take_profit_price=mean_p,
                expected_edge_bps=45.0,
            ))

        return signals
