"""
Signal S01: Volatility Compression Breakout (Bollinger / Keltner Squeeze)
========================================================================
Hypothesis:
    When volatility compresses to extremes (Bollinger Bands contract entirely inside
    Keltner Channels), volatility regime expansion is statistically imminent. A subsequent
    breakout accompanied by high volume expansion signals aggressive institutional capital
    entry with strong directional follow-through.

Horizon:
    15-minute to 1-day bars (holding period 1 to 5 days).

Inputs:
    - 20-period Simple Moving Average & Standard Deviation (Bollinger Bands, 2.0 std)
    - 20-period EMA & ATR(14) (Keltner Channels, 1.5 atr)
    - 20-period Volume Mean & Standard Deviation (Volume Z-score)

Expected Sign:
    +1.0 (Long) on upward breakout out of squeeze with Volume Z-score > 1.5.
    -1.0 (Short) on downward breakdown out of squeeze with Volume Z-score > 1.5.
"""

from typing import List, Optional
import numpy as np
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SignalVolSqueeze:
    def __init__(
        self,
        bb_period: int = 20,
        bb_mult: float = 2.0,
        keltner_mult: float = 1.5,
        volume_z_threshold: float = 1.2,
    ):
        self.signal_id = "S01_VOL_SQUEEZE"
        self.sleeve = "C_ALPHA"
        self.bb_period = bb_period
        self.bb_mult = bb_mult
        self.keltner_mult = keltner_mult
        self.vol_z_thresh = volume_z_threshold

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted:
            return []

        bars = store.get_bars_pit(bar.symbol, current_time_ms=bar.timestamp_ms, lookback_bars=self.bb_period + 5)
        if len(bars) < self.bb_period + 1:
            return []

        closes = np.array([b.close for b in bars])
        highs = np.array([b.high for b in bars])
        lows = np.array([b.low for b in bars])
        volumes = np.array([b.volume for b in bars])

        # BB calculations
        sma = np.mean(closes[-self.bb_period:])
        std = np.std(closes[-self.bb_period:])
        bb_upper = sma + (self.bb_mult * std)
        bb_lower = sma - (self.bb_mult * std)

        # Keltner calculations
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1]))
        )
        atr = np.mean(tr[-14:]) if len(tr) >= 14 else std
        kc_upper = sma + (self.keltner_mult * atr)
        kc_lower = sma - (self.keltner_mult * atr)

        # Squeeze condition: BB inside Keltner
        in_squeeze = (bb_upper < kc_upper) and (bb_lower > kc_lower)

        # Check if squeeze occurred in recent 5 bars
        recent_squeeze = in_squeeze
        if not recent_squeeze:
            for lag in range(1, 5):
                if len(closes) >= self.bb_period + lag:
                    c_lag = closes[-self.bb_period - lag : -lag]
                    std_lag = np.std(c_lag)
                    sma_lag = np.mean(c_lag)
                    bbu = sma_lag + (self.bb_mult * std_lag)
                    bbl = sma_lag - (self.bb_mult * std_lag)
                    kcu = sma_lag + (self.keltner_mult * atr)
                    kcl = sma_lag - (self.keltner_mult * atr)
                    if (bbu < kcu) and (bbl > kcl):
                        recent_squeeze = True
                        break

        # Volume Z-score
        vol_mean = np.mean(volumes[-self.bb_period:])
        vol_std = np.std(volumes[-self.bb_period:]) + 1e-8
        vol_z = (bar.volume - vol_mean) / vol_std

        signals: List[SignalEvent] = []
        stop_dist = 2.0 * atr

        # Breakout trigger with confirmed squeeze and volume surge
        if recent_squeeze and bar.close > kc_upper and vol_z >= self.vol_z_thresh:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=1.0,
                strength=min(1.0, 0.5 + (vol_z / 4.0)),
                stop_loss_price=bar.close - stop_dist,
                take_profit_price=bar.close + (3.0 * stop_dist),
                trailing_stop_atr=1.5 * atr,
                expected_edge_bps=50.0,
            ))
        elif recent_squeeze and bar.close < kc_lower and vol_z >= self.vol_z_thresh:
            signals.append(SignalEvent(
                symbol=bar.symbol,
                timestamp_ms=bar.timestamp_ms,
                sleeve=self.sleeve,
                signal_id=self.signal_id,
                direction=-1.0,
                strength=min(1.0, 0.5 + (vol_z / 4.0)),
                stop_loss_price=bar.close + stop_dist,
                take_profit_price=bar.close - (3.0 * stop_dist),
                trailing_stop_atr=1.5 * atr,
                expected_edge_bps=50.0,
            ))

        return signals
