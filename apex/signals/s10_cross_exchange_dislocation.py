"""
Signal S10: Cross-Exchange Price Dislocations
==============================================
Hypothesis:
    Transient liquidity fragmentation across major venues (Binance, OKX, Bybit) causes
    isolated price dislocations between identical perpetual contracts. When the spread exceeds
    the combined round-trip taker/maker fee threshold plus latency buffer (>15 bps), mean-reverting
    cross-exchange arbitrage yields statistical edge.

Horizon:
    1 minute to 15 minutes.

Inputs:
    - Cross-venue price divergence: (Price_VenueA - Price_VenueB) / Price_VenueB
    - Minimum executable spread hurdle (e.g. 15 bps)

Expected Sign:
    +1.0 (Long underpriced venue) / -1.0 (Short overpriced venue).
"""

from typing import List
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalCrossExchangeDislocation:
    def __init__(self, min_spread_bps: float = 15.0):
        self.signal_id = "S10_CROSS_EXCHANGE"
        self.sleeve = "C_ALPHA"
        self.min_spread_bps = min_spread_bps

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted:
            return []

        # Mark-to-Index divergence as proxy for exchange dislocation
        dislocation_bps = ((bar.close - bar.index_price) / max(bar.index_price, 1e-4)) * 10_000.0
        signals: List[SignalEvent] = []
        stop_dist = bar.close * 0.015

        if dislocation_bps > self.min_spread_bps:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,
                strength=0.65,
                stop_loss_price=bar.close + stop_dist,
                take_profit_price=bar.index_price,
                expected_edge_bps=dislocation_bps,
            ))
        elif dislocation_bps < -self.min_spread_bps:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=1.0,
                strength=0.65,
                stop_loss_price=bar.close - stop_dist,
                take_profit_price=bar.index_price,
                expected_edge_bps=abs(dislocation_bps),
            ))

        return signals
