"""
APEX 8-Hour Funding Arbitrage Harvester Module
==============================================
Monitors exchange 8-hour funding rates across the universe to capture pure
cash funding yields right before payout timestamps (00:00, 08:00, 16:00 UTC).
"""

from dataclasses import dataclass
import time
from typing import Dict, List, Optional
import pandas as pd

from apex.backtest.events import SignalEvent
from apex.data.store import PointInTimeStore


@dataclass
class FundingOpportunity:
    symbol: str
    funding_rate_8h: float
    annualized_apr: float
    recommended_side: str          # "SHORT" to receive positive funding from longs, "LONG" if negative
    priority_score: float


@dataclass
class HarvesterReport:
    next_payout_utc: str
    minutes_until_payout: int
    is_harvest_window_active: bool
    top_opportunities: List[FundingOpportunity]
    estimated_annualized_yield_pct: float
    status_summary: str


class FundingHarvester:
    """
    Arbitrage Harvester for Binance 8-hour perpetual funding payments.
    """

    def __init__(self, min_annualized_apr: float = 0.12):  # Minimum 12% APR to trade
        self.min_apr = min_annualized_apr

    def evaluate(self, store: PointInTimeStore, symbols: List[str], current_time_ms: int) -> HarvesterReport:
        now_sec = current_time_ms // 1000
        # Payouts occur at 00:00, 08:00, 16:00 UTC (every 28,800 seconds)
        payout_cycle_sec = 8 * 3600
        next_payout_sec = ((now_sec // payout_cycle_sec) + 1) * payout_cycle_sec
        sec_until = next_payout_sec - now_sec
        min_until = sec_until // 60

        next_payout_str = pd.to_datetime(next_payout_sec, unit="s", utc=True).strftime("%H:%M UTC")

        # Harvest window is active within 30 minutes before cutoff
        is_window = min_until <= 30

        opportunities: List[FundingOpportunity] = []
        for sym in symbols:
            bars = store.get_bars_pit(sym, current_time_ms=current_time_ms, lookback_bars=1)
            if not bars:
                continue
            fr = bars[-1].funding_rate_8h
            # Annualized APR = fr * 3 * 365
            apr = fr * 3.0 * 365.0

            if abs(apr) >= self.min_apr:
                # If funding is positive, longs pay shorts -> Go SHORT to receive cash
                side = "SHORT" if fr > 0 else "LONG"
                opp = FundingOpportunity(
                    symbol=sym,
                    funding_rate_8h=fr,
                    annualized_apr=apr * 100.0,
                    recommended_side=side,
                    priority_score=abs(apr),
                )
                opportunities.append(opp)

        opportunities.sort(key=lambda o: o.priority_score, reverse=True)
        top_3 = opportunities[:3]
        mean_yield = sum(o.annualized_apr for o in top_3) / len(top_3) if top_3 else 0.0

        if is_window and top_3:
            summary = f"HARVEST_ACTIVE: {min_until}m to {next_payout_str} payout | Top: {top_3[0].symbol} ({top_3[0].annualized_apr:.1f}% APR)"
        else:
            summary = f"COUNTDOWN: Next payout {next_payout_str} ({min_until}m remaining) | Carry ready"

        return HarvesterReport(
            next_payout_utc=next_payout_str,
            minutes_until_payout=int(min_until),
            is_harvest_window_active=is_window,
            top_opportunities=top_3,
            estimated_annualized_yield_pct=mean_yield,
            status_summary=summary,
        )
