"""
Signal S08: VWAP & Volume-Profile Deviation
===========================================
Hypothesis:
    Intraday price auctions rotate around the Volume-Weighted Average Price (VWAP).
    Prices deviating beyond 2.0 standard deviations from the daily anchored VWAP in
    low-volatility range regimes represent statistical extremes that revert to the mean.
    Conversely, continuation past 2.5 standard deviations indicates trend-day regime expansion.

Horizon:
    15 minutes to 4 hours.

Inputs:
    - Anchored Daily VWAP: sum(TypicalPrice * Volume) / sum(Volume)
    - VWAP Standard Deviation Bands
    - Current Close vs VWAP Z-score

Expected Sign:
    +1.0 (Long) when price is oversold at lower VWAP 2-sigma band in ranging market.
    -1.0 (Short) when price is overbought at upper VWAP 2-sigma band in ranging market.
"""

from typing import List
import numpy as np
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalVwapDeviation:
    def __init__(self, lookback_bars: int = 24, z_band: float = 2.0):
        self.signal_id = "S08_VWAP_DEV"
        self.sleeve = "C_ALPHA"
        self.lookback = lookback_bars
        self.z_band = z_band

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted:
            return []

        bars = store.get_bars_pit(bar.symbol, current_time_ms=bar.timestamp_ms, lookback_bars=self.lookback)
        if len(bars) < self.lookback:
            return []

        typ_prices = np.array([(b.high + b.low + b.close) / 3.0 for b in bars])
        vols = np.array([max(b.volume, 1.0) for b in bars])

        vwap = float(np.sum(typ_prices * vols) / np.sum(vols))
        var = float(np.sum(vols * ((typ_prices - vwap) ** 2)) / np.sum(vols))
        vwap_std = np.sqrt(var) if var > 0 else (bar.close * 0.01)

        z_vwap = (bar.close - vwap) / max(vwap_std, 1e-4)
        signals: List[SignalEvent] = []
        stop_dist = vwap_std * 1.5

        if z_vwap < -self.z_band:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=1.0,
                strength=0.75,
                stop_loss_price=bar.close - stop_dist,
                take_profit_price=vwap,
                expected_edge_bps=30.0,
            ))
        elif z_vwap > self.z_band:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,
                strength=0.75,
                stop_loss_price=bar.close + stop_dist,
                take_profit_price=vwap,
                expected_edge_bps=30.0,
            ))

        return signals
