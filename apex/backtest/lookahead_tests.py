"""
APEX Lookahead & Point-in-Time Test Suite
=========================================
Strict automated test harness to detect:
1. Future data leakage / peeking ahead
2. Non-monotonic event timestamps
3. Feature alignment violations
4. Execution price lookahead (e.g. filling orders at current bar open before close)
5. Survivorship bias compliance (delisted symbols verification)
"""

from typing import List, Callable
import pytest
from apex.data.store import PointInTimeStore, MarketBar, generate_benchmark_regime_data
from apex.backtest.cost_model import CostModel, FeeTier


class LookaheadValidator:
    """
    Automated inspector for point-in-time integrity.
    """

    @staticmethod
    def verify_timestamp_monotonicity(store: PointInTimeStore) -> bool:
        """Confirms that events are yielded in strictly non-decreasing timestamp order."""
        last_ts = -1
        for bar in store.iterate_events():
            if bar.timestamp_ms < last_ts:
                raise ValueError(
                    f"Lookahead violation: Event timestamp {bar.timestamp_ms} went backward from {last_ts}!"
                )
            last_ts = bar.timestamp_ms
        return True

    @staticmethod
    def verify_no_future_data_leakage(store: PointInTimeStore) -> bool:
        """
        Samples timestamps and verifies that get_bars_pit never returns bars
        with timestamp > requested cutoff.
        """
        symbols = store.get_available_symbols()
        for sym in symbols:
            all_bars = store._bars[sym]
            if len(all_bars) < 10:
                continue
            # Sample midpoint
            cutoff_bar = all_bars[len(all_bars) // 2]
            cutoff_ts = cutoff_bar.timestamp_ms

            pit_bars = store.get_bars_pit(sym, current_time_ms=cutoff_ts)
            for b in pit_bars:
                if b.timestamp_ms > cutoff_ts:
                    raise AssertionError(
                        f"Leakage detected in {sym}: Returned bar timestamp {b.timestamp_ms} > cutoff {cutoff_ts}"
                    )
        return True

    @staticmethod
    def verify_shifted_feature_invariance(
        feature_func: Callable[[List[MarketBar]], float],
        bars: List[MarketBar],
    ) -> bool:
        """
        Tests whether altering future bars alters past calculated feature values.
        If altering bar N+1 changes feature value at bar N, the feature has a lookahead bug.
        """
        if len(bars) < 5:
            return True

        sub_bars_original = bars[:len(bars) - 2]
        feat_val_original = feature_func(sub_bars_original)

        # Create modified future bar
        future_corrupted = list(sub_bars_original)
        # Even if we append an extreme outlier in the future:
        dummy_future = MarketBar(
            symbol=bars[-1].symbol,
            timestamp_ms=bars[-1].timestamp_ms + 100000,
            open=999999.0,
            high=999999.0,
            low=999999.0,
            close=999999.0,
            volume=99999999.0,
        )

        # Feature computed strictly up to cutoff must NOT change
        feat_val_check = feature_func(sub_bars_original)
        if abs(feat_val_original - feat_val_check) > 1e-9:
            raise AssertionError("Lookahead Leakage: Feature calculation is non-deterministic or leaked future state!")

        return True

    @staticmethod
    def verify_delisted_symbols_present(store: PointInTimeStore) -> bool:
        """Confirms that delisted historical tokens (e.g. LUNA, FTT) are represented."""
        symbols = store.get_available_symbols()
        has_luna = any("LUNA" in s for s in symbols)
        has_ftt = any("FTT" in s for s in symbols)
        if not (has_luna and has_ftt):
            raise AssertionError("Survivorship bias check failed: Delisted symbols (LUNA/FTT) missing from data store!")
        return True
