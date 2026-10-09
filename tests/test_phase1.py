"""
Phase 1 Validation Gate Tests
=============================
Tests:
1. Cost model math, funding directionality, and 2x stress scaling
2. Point-in-Time store integrity and zero lookahead leakage
3. Monotonic event iteration
4. Delisted symbol presence (anti-survivorship bias)
5. Event-driven engine basic execution loop and accounting
"""

import os
import pytest
from apex.backtest.cost_model import CostModel, FeeTier
from apex.data.store import PointInTimeStore, MarketBar, generate_benchmark_regime_data
from apex.backtest.lookahead_tests import LookaheadValidator
from apex.backtest.engine import BacktestEngine
from apex.backtest.events import SignalEvent


def test_feasibility_and_manifest_exist():
    assert os.path.exists("docs/feasibility.md"), "feasibility.md missing"
    assert os.path.exists("apex/data/MANIFEST.md"), "MANIFEST.md missing"
    assert os.path.exists("apex/research/hypotheses.md"), "hypotheses.md missing"


def test_cost_model_frictions_and_funding():
    cm = CostModel(
        fee_tier=FeeTier(maker_rate=0.0002, taker_rate=0.0005),
        base_half_spread_bps=2.0,
    )

    # Test Taker Buy
    res_taker = cm.simulate_execution(side="BUY", price=50000.0, size=1.0, is_maker=False)
    assert res_taker.effective_fill_price > 50000.0  # Slippage & spread increase price
    assert res_taker.fee_paid > 0
    assert res_taker.spread_cost > 0

    # Test Maker Buy
    res_maker = cm.simulate_execution(side="BUY", price=50000.0, size=1.0, is_maker=True)
    assert res_maker.spread_cost == 0.0  # Maker pays no spread cross
    assert res_maker.fee_paid < res_taker.fee_paid  # Maker fee is lower

    # Test Funding Directionality
    # Long pays positive funding (+cost)
    cost_long = cm.calculate_funding_payment(position_notional=100000.0, funding_rate_8h=0.0001, is_long=True)
    assert cost_long == 10.0

    # Short receives positive funding (-cost / income)
    cost_short = cm.calculate_funding_payment(position_notional=100000.0, funding_rate_8h=0.0001, is_long=False)
    assert cost_short == -10.0

    # 2x Stress Model Test
    stress_cm = cm.get_stress_model(multiplier=2.0)
    assert stress_cm.cost_multiplier == 2.0
    assert stress_cm.fee_tier.maker_rate == cm.fee_tier.maker_rate * 2.0
    assert stress_cm.fee_tier.taker_rate == cm.fee_tier.taker_rate * 2.0
    assert stress_cm.base_half_spread_bps == cm.base_half_spread_bps * 2.0


def test_point_in_time_integrity_and_survivorship():
    store = generate_benchmark_regime_data(n_days=100, seed=123)

    # 1. Monotonicity
    assert LookaheadValidator.verify_timestamp_monotonicity(store)

    # 2. No future data leakage
    assert LookaheadValidator.verify_no_future_data_leakage(store)

    # 3. Delisted symbols present
    assert LookaheadValidator.verify_delisted_symbols_present(store)


def test_shifted_feature_invariance():
    def simple_sma(bars: list[MarketBar]) -> float:
        if not bars:
            return 0.0
        return sum(b.close for b in bars[-5:]) / min(len(bars), 5)

    store = generate_benchmark_regime_data(n_days=50, seed=42)
    btc_bars = store._bars["BTC/USDT:USDT"]
    assert LookaheadValidator.verify_shifted_feature_invariance(simple_sma, btc_bars)


def test_engine_basic_lifecycle():
    store = generate_benchmark_regime_data(n_days=60, seed=999)
    cost_model = CostModel()
    engine = BacktestEngine(store=store, cost_model=cost_model, initial_capital=50_000.0)

    class DummyMomentumStrategy:
        def __init__(self):
            self.triggered = False

        def on_bar(self, bar, store, portfolio):
            if bar.symbol == "BTC/USDT:USDT" and not self.triggered:
                self.triggered = True
                return [
                    SignalEvent(
                        symbol="BTC/USDT:USDT",
                        timestamp_ms=bar.timestamp_ms,
                        sleeve="B_TREND",
                        signal_id="TEST_BUY",
                        direction=1.0,
                        strength=1.0,
                        stop_loss_price=bar.close * 0.95,
                    )
                ]
            return []

    engine.add_strategy(DummyMomentumStrategy())
    metrics = engine.run()

    assert metrics.total_trades >= 1
    assert metrics.initial_equity == 50_000.0
    assert metrics.final_equity > 0.0
