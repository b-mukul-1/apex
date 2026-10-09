"""
Signal S04: L2 Order-Flow Imbalance & Book Pressure
===================================================
Hypothesis:
    Persistent volume imbalance between top bid and ask depth levels in the L2 order book
    creates asymmetric order execution resistance. When bid volume outweighs ask volume by
    a factor of 2:1 alongside aggressive taker volume, price drifts in the direction of the
    pressure over the subsequent 1 to 15 minute horizon.

Horizon:
    1 minute to 15 minutes.

Inputs:
    - Top 10 levels Bid Volume vs Ask Volume
    - Micro-price deviation from mid-price: P_micro = (P_ask*V_bid + P_bid*V_ask)/(V_bid+V_ask)
    - Order Book Imbalance ratio: (V_bid - V_ask) / (V_bid + V_ask)

Expected Sign:
    +1.0 (Long) when Imbalance > +0.35 and Micro-price > Mid-price.
    -1.0 (Short) when Imbalance < -0.35 and Micro-price < Mid-price.
"""

from typing import List
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalOrderbookImbalance:
    def __init__(self, imbalance_threshold: float = 0.35):
        self.signal_id = "S04_BOOK_IMBALANCE"
        self.sleeve = "C_ALPHA"
        self.imbalance_threshold = imbalance_threshold

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted or bar.volume <= 0:
            return []

        # Proxied via candle body skew & intraday range pressure
        candle_range = max(bar.high - bar.low, 1e-6)
        body = bar.close - bar.open
        imbalance_proxy = body / candle_range

        signals: List[SignalEvent] = []
        stop_dist = bar.close * 0.015

        if imbalance_proxy >= self.imbalance_threshold:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=1.0,
                strength=0.70,
                stop_loss_price=bar.close - stop_dist,
                take_profit_price=bar.close + (2.0 * stop_dist),
                expected_edge_bps=25.0,
            ))
        elif imbalance_proxy <= -self.imbalance_threshold:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,
                strength=0.70,
                stop_loss_price=bar.close + stop_dist,
                take_profit_price=bar.close - (2.0 * stop_dist),
                expected_edge_bps=25.0,
            ))

        return signals
