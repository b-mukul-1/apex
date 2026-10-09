"""
Signal S06: BTC Lead / Altcoin Lag
==================================
Hypothesis:
    Price discovery for major market catalysts occurs first in high-liquidity BTC perpetuals.
    Secondary altcoins reflect this macroeconomic impulse with a 5 to 30 minute latency.
    Capturing this cross-asset propagation yields positive edge, provided the expected return
    exceeds 2x the combined round-trip execution cost.

Horizon:
    5 minutes to 1 hour.

Inputs:
    - BTC impulse return: R_btc = (Close_t / Close_{t-1}) - 1
    - Altcoin return over same period: R_alt
    - Cost-aware filter: |R_btc - R_alt| > 2x roundtrip fee (~15 bps)

Expected Sign:
    +1.0 (Long Altcoin) when BTC experiences a positive impulse that Altcoin has not yet followed.
    -1.0 (Short Altcoin) when BTC experiences a negative breakdown that Altcoin has not yet followed.
"""

from typing import List
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalBtcLeadLag:
    def __init__(self, min_lead_spread_pct: float = 0.015):
        self.signal_id = "S06_BTC_LEAD_LAG"
        self.sleeve = "C_ALPHA"
        self.min_spread = min_lead_spread_pct  # 1.5% lead spread hurdle

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted or bar.symbol.startswith("BTC"):
            return []

        # Get latest BTC bars and current symbol bars
        btc_bars = store.get_bars_pit("BTC/USDT:USDT", current_time_ms=bar.timestamp_ms, lookback_bars=3)
        alt_bars = store.get_bars_pit(bar.symbol, current_time_ms=bar.timestamp_ms, lookback_bars=3)

        if len(btc_bars) < 2 or len(alt_bars) < 2:
            return []

        btc_ret = (btc_bars[-1].close / btc_bars[-2].close) - 1.0
        alt_ret = (alt_bars[-1].close / alt_bars[-2].close) - 1.0
        lag_delta = btc_ret - alt_ret

        signals: List[SignalEvent] = []
        stop_dist = bar.close * 0.02

        # BTC surging, alt lagging behind
        if lag_delta > self.min_spread:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=1.0,
                strength=0.70,
                stop_loss_price=bar.close - stop_dist,
                take_profit_price=bar.close + (2.0 * stop_dist),
                expected_edge_bps=lag_delta * 10_000.0,
            ))
        elif lag_delta < -self.min_spread:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,
                strength=0.70,
                stop_loss_price=bar.close + stop_dist,
                take_profit_price=bar.close - (2.0 * stop_dist),
                expected_edge_bps=abs(lag_delta) * 10_000.0,
            ))

        return signals
