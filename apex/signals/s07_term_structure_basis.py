"""
Signal S07: Basis / Term-Structure Dislocations
================================================
Hypothesis:
    Dislocations between the perpetual contract mark price and underlying index price
    beyond fair cash-and-carry bounds represent transient liquidity stress that mean-reverts
    once order flow re-equilibrates.

Horizon:
    1 hour to 1 day.

Inputs:
    - Mark Price vs Index Price basis: (Mark - Index) / Index
    - Annualized Basis Spread

Expected Sign:
    -1.0 (Short Perp) when Mark trades at extreme premium > +0.8% over Index.
    +1.0 (Long Perp) when Mark trades at extreme discount < -0.8% below Index.
"""

from typing import List
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalBasisDislocation:
    def __init__(self, basis_threshold_pct: float = 0.008):
        self.signal_id = "S07_BASIS_DISLOCATION"
        self.sleeve = "C_ALPHA"
        self.threshold = basis_threshold_pct

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted or bar.index_price <= 0:
            return []

        basis_pct = (bar.mark_price - bar.index_price) / bar.index_price
        signals: List[SignalEvent] = []
        stop_dist = bar.close * 0.02

        if basis_pct > self.threshold:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,
                strength=0.75,
                stop_loss_price=bar.close + stop_dist,
                take_profit_price=bar.index_price,
                expected_edge_bps=basis_pct * 10_000.0,
            ))
        elif basis_pct < -self.threshold:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=1.0,
                strength=0.75,
                stop_loss_price=bar.close - stop_dist,
                take_profit_price=bar.index_price,
                expected_edge_bps=abs(basis_pct) * 10_000.0,
            ))

        return signals
