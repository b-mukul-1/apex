"""
Signal S02: Cross-Sectional Momentum (BTC-Beta Hedged)
======================================================
Hypothesis:
    Altcoins that exhibit relative strength vs the cross-sectional median over a 1 to 7 day
    window experience persistent outperformance due to sectoral capital rotation.
    By hedging out systemic market beta against BTC, the strategy isolates pure idiosyncratic
    alpha and minimizes drawdown during macro crypto selloffs.

Horizon:
    1 day to 5 days.

Inputs:
    - 3-day and 7-day relative price return vs universe median
    - 30-day rolling beta of the asset to BTC
    - BTC benchmark return

Expected Sign:
    +1.0 (Long) top quintile outperforming altcoins with positive residual alpha.
    -1.0 (Short) bottom quintile underperforming altcoins or shorting BTC to neutralize beta.
"""

from typing import List, Dict
import numpy as np
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalCrossSectionalMom:
    def __init__(self, lookback_days: int = 7, beta_lookback: int = 30):
        self.signal_id = "S02_CROSS_MOM"
        self.sleeve = "C_ALPHA"
        self.lookback = lookback_days
        self.beta_lookback = beta_lookback

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted or bar.symbol.startswith("BTC"):
            return []

        # Get bars for target symbol and BTC
        sym_bars = store.get_bars_pit(bar.symbol, current_time_ms=bar.timestamp_ms, lookback_bars=self.beta_lookback + 2)
        btc_bars = store.get_bars_pit("BTC/USDT:USDT", current_time_ms=bar.timestamp_ms, lookback_bars=self.beta_lookback + 2)

        # Only rebalance on cross-sectional lookback interval (e.g. every 7 days)
        day_num = bar.timestamp_ms // 86400000
        if day_num % self.lookback != 0:
            return []

        if len(sym_bars) < self.lookback + 1 or len(btc_bars) < self.lookback + 1:
            return []

        # Asset return over lookback
        sym_ret = (sym_bars[-1].close / sym_bars[-self.lookback].close) - 1.0
        btc_ret = (btc_bars[-1].close / btc_bars[-self.lookback].close) - 1.0

        # Beta estimation
        if len(sym_bars) >= self.beta_lookback and len(btc_bars) >= self.beta_lookback:
            sym_closes = np.array([b.close for b in sym_bars[-self.beta_lookback:]])
            btc_closes = np.array([b.close for b in btc_bars[-self.beta_lookback:]])
            r_sym = np.diff(sym_closes) / sym_closes[:-1]
            r_btc = np.diff(btc_closes) / btc_closes[:-1]
            cov = np.cov(r_sym, r_btc)[0, 1]
            var_btc = np.var(r_btc) + 1e-8
            beta = float(cov / var_btc)
        else:
            beta = 1.0

        # Idiosyncratic excess return
        excess_return = sym_ret - (beta * btc_ret)

        signals: List[SignalEvent] = []
        stop_dist = bar.close * 0.04

        # Strong outperformance -> Long
        if excess_return > 0.05:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=1.0,
                strength=0.75,
                stop_loss_price=bar.close - stop_dist,
                take_profit_price=bar.close + (2.5 * stop_dist),
                trailing_stop_atr=stop_dist * 0.75,
                expected_edge_bps=45.0,
            ))
        elif excess_return < -0.05:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,
                strength=0.75,
                stop_loss_price=bar.close + stop_dist,
                take_profit_price=bar.close - (2.5 * stop_dist),
                trailing_stop_atr=stop_dist * 0.75,
                expected_edge_bps=45.0,
            ))

        return signals
