"""
Signal S03: Funding & Open Interest Crowding / Liquidation Cascade
==================================================================
Hypothesis:
    When perpetual funding rates reach extreme positive or negative deviations (>50% annualized)
    concurrent with rising Open Interest, market positioning becomes hyper-crowded and fragile.
    A counter-trend break forces sudden margin liquidation cascades, generating an explosive
    reversal in the opposite direction of crowded retail positioning.

Horizon:
    1 hour to 12 hours.

Inputs:
    - 8-hour Funding Rate (annualized > 50% or < -30%)
    - Open interest change over 24h
    - Rolling 14-period price range and counter-trend price impulse

Expected Sign:
    -1.0 (Short) when extreme positive funding long crowding begins to liquidate.
    +1.0 (Long) when extreme negative funding short crowding begins to squeeze upward.
"""

from typing import List
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalFundingCrowding:
    def __init__(
        self,
        high_funding_annualized: float = 0.50,   # +50% annualized funding
        low_funding_annualized: float = -0.30,   # -30% annualized funding
    ):
        self.signal_id = "S03_FUNDING_CROWD"
        self.sleeve = "C_ALPHA"
        # Convert to 8-hour rates
        self.high_rate_8h = high_funding_annualized / (365.0 * 3.0)
        self.low_rate_8h = low_funding_annualized / (365.0 * 3.0)

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted:
            return []

        funding = bar.funding_rate_8h
        signals: List[SignalEvent] = []
        stop_dist = bar.close * 0.03

        # Crowded Longs liquidation risk (funding extremely high, bar closes below open)
        if funding > self.high_rate_8h and bar.close < bar.open:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,
                strength=0.85,
                stop_loss_price=bar.close + stop_dist,
                take_profit_price=bar.close - (3.0 * stop_dist),
                expected_edge_bps=60.0,
            ))
        # Crowded Shorts squeeze risk (funding negative, bar closes above open)
        elif funding < self.low_rate_8h and bar.close > bar.open:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=1.0,
                strength=0.85,
                stop_loss_price=bar.close - stop_dist,
                take_profit_price=bar.close + (3.0 * stop_dist),
                expected_edge_bps=60.0,
            ))

        return signals
