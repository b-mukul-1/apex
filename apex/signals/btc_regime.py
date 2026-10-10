"""
APEX BTC Macro-Regime Filter Module
====================================
Evaluates Bitcoin's broad-market volume-weighted trend and volatility state.
Protects altcoin alpha positions from broad market sell-offs by gating new longs
when Bitcoin breaks below its structural trend.
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from apex.data.store import MarketBar, PointInTimeStore


@dataclass
class BtcRegimeReport:
    regime: str                     # "BULL_EXPANSION", "NEUTRAL_CHOP", "BEAR_DEFENSIVE"
    btc_price: float
    ema_20: float
    distance_pct: float
    momentum_24h_pct: float
    altcoin_long_allowed: bool
    altcoin_size_multiplier: float
    status_summary: str


class BtcRegimeFilter:
    """
    Evaluates Bitcoin market trend to modulate portfolio altcoin risk.
    """

    def __init__(self, btc_symbol: str = "BTC/USDT:USDT", ema_period: int = 20):
        self.btc_symbol = btc_symbol
        self.ema_period = ema_period

    def evaluate(self, store: PointInTimeStore, current_time_ms: int) -> BtcRegimeReport:
        """
        Calculates BTC regime from Point-In-Time market bars.
        """
        bars = store.get_bars_pit(self.btc_symbol, current_time_ms=current_time_ms, lookback_bars=max(self.ema_period + 5, 25))
        if not bars or len(bars) < self.ema_period:
            return BtcRegimeReport(
                regime="NEUTRAL_CHOP",
                btc_price=80_000.0,
                ema_20=80_000.0,
                distance_pct=0.0,
                momentum_24h_pct=0.0,
                altcoin_long_allowed=True,
                altcoin_size_multiplier=1.0,
                status_summary="NEUTRAL_CHOP: Insufficient history, default normal size",
            )

        closes = np.array([b.close for b in bars], dtype=float)
        current_px = float(closes[-1])

        # Compute Exponential Moving Average (EMA)
        k = 2.0 / (self.ema_period + 1)
        ema = closes[0]
        for px in closes[1:]:
            ema = (px * k) + (ema * (1.0 - k))

        dist_pct = ((current_px / max(ema, 1e-4)) - 1.0) * 100.0
        mom_24h = ((current_px / max(closes[0], 1e-4)) - 1.0) * 100.0

        # Regime classification
        if dist_pct >= 0.5 and mom_24h >= 0.0:
            regime = "BULL_EXPANSION"
            long_allowed = True
            mult = 1.0
            summary = f"BULL_EXPANSION: BTC +{dist_pct:.2f}% above EMA20. Altcoin longs unrestricted (100% Size)."
        elif dist_pct <= -1.0 or mom_24h <= -2.0:
            regime = "BEAR_DEFENSIVE"
            long_allowed = False
            mult = 0.3
            summary = f"BEAR_DEFENSIVE: BTC {dist_pct:.2f}% below EMA20. New altcoin longs vetod; defensive hedging active."
        else:
            regime = "NEUTRAL_CHOP"
            long_allowed = True
            mult = 0.7
            summary = f"NEUTRAL_CHOP: BTC oscillating within {dist_pct:.2f}% of EMA20. Moderate sizing (70% Size)."

        return BtcRegimeReport(
            regime=regime,
            btc_price=current_px,
            ema_20=float(ema),
            distance_pct=dist_pct,
            momentum_24h_pct=mom_24h,
            altcoin_long_allowed=long_allowed,
            altcoin_size_multiplier=mult,
            status_summary=summary,
        )
