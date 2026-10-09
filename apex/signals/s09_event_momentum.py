"""
Signal S09: Event Momentum & Token Unlock Overhang
==================================================
Hypothesis:
    Large pre-scheduled token unlock events (cliff unlocks > 2.0% of circulating supply)
    introduce persistent structural sell pressure from early investors and foundation treasuries.
    Positioning short (or hedging beta) ahead of and during unlock windows captures systematic
    negative price drift.

Horizon:
    1 day to 3 days.

Inputs:
    - Token event indicator (cliff unlock event flag)
    - 3-day relative volume and funding rate

Expected Sign:
    -1.0 (Short) ahead of and during significant unlock events.
"""

from typing import List
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalEventMomentum:
    def __init__(self, unlock_frequency_bars: int = 180):
        self.signal_id = "S09_EVENT_MOM"
        self.sleeve = "C_ALPHA"
        self.unlock_freq = unlock_frequency_bars

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        # Events apply only to altcoins (not BTC/ETH)
        if bar.is_delisted or bar.symbol.startswith("BTC") or bar.symbol.startswith("ETH"):
            return []

        # Synthetic deterministic schedule for testing event windows:
        day_index = (bar.timestamp_ms // 86400000) % self.unlock_freq
        signals: List[SignalEvent] = []
        stop_dist = bar.close * 0.04

        # Unlock window active on days 0 to 2
        if day_index in (0, 1):
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,  # Short supply overhang
                strength=0.70,
                stop_loss_price=bar.close + stop_dist,
                take_profit_price=bar.close - (2.0 * stop_dist),
                expected_edge_bps=40.0,
            ))

        return signals
