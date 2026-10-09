"""
APEX Signal Decay Monitor
=========================
Monitors real-time / out-of-sample cumulative P&L for each signal against its
expected backtest confidence bands.
Automatically dispatches alerts and disarms (disables) a signal if its cumulative
underperformance breaches the 2-sigma lower confidence bound.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class SignalHealth:
    signal_id: str
    total_trades: int
    cumulative_pnl: float
    expected_pnl_per_trade: float
    pnl_std_per_trade: float
    lower_bound_2sigma: float
    is_active: bool
    status_reason: str


class SignalDecayMonitor:
    """
    Monitors signals for structural edge degradation.
    """

    def __init__(self, confidence_std_multiplier: float = 2.0):
        self.mult = confidence_std_multiplier
        self.signal_stats: Dict[str, Dict] = {}

    def register_signal_baseline(
        self,
        signal_id: str,
        expected_pnl_per_trade: float,
        pnl_std_per_trade: float,
    ) -> None:
        self.signal_stats[signal_id] = {
            "expected_pnl": expected_pnl_per_trade,
            "pnl_std": max(pnl_std_per_trade, 10.0),
            "trades": 0,
            "cum_pnl": 0.0,
            "is_active": True,
            "status_reason": "HEALTHY",
        }

    def record_trade_result(self, signal_id: str, pnl: float) -> SignalHealth:
        if signal_id not in self.signal_stats:
            self.register_signal_baseline(signal_id, 25.0, 50.0)

        stats = self.signal_stats[signal_id]
        stats["trades"] += 1
        stats["cum_pnl"] += pnl
        n = stats["trades"]

        expected_cum = stats["expected_pnl"] * n
        band_width = self.mult * stats["pnl_std"] * np.sqrt(n)
        lower_bound = expected_cum - band_width

        # Check breach
        if stats["cum_pnl"] < lower_bound and n >= 10:
            stats["is_active"] = False
            stats["status_reason"] = f"AUTO-DISABLED: PnL (${stats['cum_pnl']:.2f}) breached 2-sigma lower band (${lower_bound:.2f})"
        else:
            stats["status_reason"] = "HEALTHY"

        return SignalHealth(
            signal_id=signal_id,
            total_trades=n,
            cumulative_pnl=stats["cum_pnl"],
            expected_pnl_per_trade=stats["expected_pnl"],
            pnl_std_per_trade=stats["pnl_std"],
            lower_bound_2sigma=lower_bound,
            is_active=stats["is_active"],
            status_reason=stats["status_reason"],
        )

    def is_signal_active(self, signal_id: str) -> bool:
        if signal_id not in self.signal_stats:
            return True
        return bool(self.signal_stats[signal_id]["is_active"])
