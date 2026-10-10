"""
APEX Dynamic Profit Ratchet & Trailing Volatility Harvest Module
================================================================
Monitors peak account equity and systematically ratchets up a minimum
profit floor to ensure major unrealized swings (+2%, +4%, etc.) are
banked into realized cash rather than given back to market reversals.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class RatchetReport:
    peak_equity: float
    current_equity: float
    unrealized_profit: float
    ratchet_floor_equity: float
    locked_profit_amount: float
    is_ratchet_active: bool
    should_harvest: bool
    status_summary: str


class ProfitRatchet:
    """
    Dynamic Profit Ratchet & Trailing Capital Lock.
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        activation_hurdle_pct: float = 0.015,  # Activates when profit >= +1.5%
        trail_pullback_pct: float = 0.015,     # Harvests if equity drops 1.5% from peak
        peak_equity: Optional[float] = None,
    ):
        self.initial_capital = initial_capital
        self.activation_hurdle_pct = activation_hurdle_pct
        self.trail_pullback_pct = trail_pullback_pct

        self.peak_equity = float(peak_equity) if peak_equity is not None else initial_capital
        self.ratchet_floor = initial_capital
        self.is_active = False
        self.harvest_triggered = False

        if self.peak_equity > self.initial_capital:
            self.update(self.peak_equity)

    def update(self, current_equity: float) -> RatchetReport:
        """
        Updates peak equity and evaluates whether profit ratchet floor is breached.
        """
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        profit_from_start = self.peak_equity - self.initial_capital
        profit_pct = profit_from_start / max(self.initial_capital, 1e-4)

        # Milestone Ratchet Schedule:
        # +1.5% -> Lock +0.8%
        # +2.5% -> Lock +1.5%
        # +4.0% -> Lock +2.8%
        # +6.0% -> Lock +4.5%
        if profit_pct >= 0.06:
            self.is_active = True
            self.ratchet_floor = self.initial_capital + (self.initial_capital * 0.045)
        elif profit_pct >= 0.04:
            self.is_active = True
            self.ratchet_floor = self.initial_capital + (self.initial_capital * 0.028)
        elif profit_pct >= 0.025:
            self.is_active = True
            self.ratchet_floor = self.initial_capital + (self.initial_capital * 0.015)
        elif profit_pct >= self.activation_hurdle_pct:
            self.is_active = True
            self.ratchet_floor = self.initial_capital + (self.initial_capital * 0.008)
        else:
            self.is_active = False
            self.ratchet_floor = self.initial_capital

        # Trailing pullback check: Also ensure floor is at least (peak - 1.5%)
        if self.is_active:
            trailing_floor = self.peak_equity * (1.0 - self.trail_pullback_pct)
            self.ratchet_floor = max(self.ratchet_floor, trailing_floor)

        # Evaluate if harvest is triggered
        should_harvest = False
        if self.is_active and current_equity < self.ratchet_floor:
            should_harvest = True
            self.harvest_triggered = True

        locked_amount = max(0.0, self.ratchet_floor - self.initial_capital)
        current_profit = current_equity - self.initial_capital

        if should_harvest:
            summary = f"HARVEST_TRIGGERED: Equity ${current_equity:,.2f} below floor ${self.ratchet_floor:,.2f}"
        elif self.is_active:
            summary = f"RATCHET_ENGAGED: Locked +${locked_amount:,.2f} Floor | Peak ${self.peak_equity:,.2f}"
        else:
            summary = "STANDBY: Awaiting +1.5% profit hurdle to engage ratchet"

        return RatchetReport(
            peak_equity=self.peak_equity,
            current_equity=current_equity,
            unrealized_profit=current_profit,
            ratchet_floor_equity=self.ratchet_floor,
            locked_profit_amount=locked_amount,
            is_ratchet_active=self.is_active,
            should_harvest=should_harvest,
            status_summary=summary,
        )
