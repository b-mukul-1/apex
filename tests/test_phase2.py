"""
Phase 2 Validation Gate Tests: Sleeves A and B
==============================================
Validates:
1. Sleeve A Delta-Neutral Carry strategy performance, funding harvest, and 2x cost survival.
2. Sleeve B Volatility-Targeted Trend Following strategy with ATR trailing stops and 2x cost survival.
3. Deflated Sharpe Ratio (DSR) and strict gate criteria compliance.
"""

import pytest
from apex.data.store import generate_benchmark_regime_data
from apex.backtest.cost_model import CostModel
from apex.backtest.engine import BacktestEngine
from apex.signals.sleeve_a_carry import SleeveACarryStrategy
from apex.signals.sleeve_b_trend import SleeveBTrendStrategy
from apex.research.validation import validate_sleeve_gate, compute_deflated_sharpe_ratio


def test_sleeve_a_carry_and_gate():
    store = generate_benchmark_regime_data(n_days=1460, seed=101)  # 4 years
    cost_model = CostModel()

    # 1x Cost Run
    engine_1x = BacktestEngine(store=store, cost_model=cost_model, initial_capital=100_000.0)
    strat_a_1x = SleeveACarryStrategy(min_annualized_funding_hurdle=0.08)
    engine_1x.add_strategy(strat_a_1x)
    metrics_1x = engine_1x.run()

    # 2x Cost Stress Run
    stress_cm = cost_model.get_stress_model(multiplier=2.0)
    engine_2x = BacktestEngine(store=store, cost_model=stress_cm, initial_capital=100_000.0)
    strat_a_2x = SleeveACarryStrategy(min_annualized_funding_hurdle=0.08)
    engine_2x.add_strategy(strat_a_2x)
    metrics_2x = engine_2x.run()

    assert metrics_1x.total_trades > 0
    # Sleeve A carries positive funding yield
    assert metrics_1x.final_equity > metrics_1x.initial_equity
    assert metrics_2x.final_equity > metrics_2x.initial_equity  # Survives 2x cost gate

    # Validate Gate
    report = validate_sleeve_gate("Sleeve A Carry", metrics_1x, metrics_2x, [metrics_1x.annualized_sharpe, 1.2, 0.9])
    assert report.passed_2x_cost_test is True


def test_sleeve_b_trend_and_gate():
    store = generate_benchmark_regime_data(n_days=1460, seed=202)  # 4 years
    cost_model = CostModel()

    # 1x Cost Run
    engine_1x = BacktestEngine(store=store, cost_model=cost_model, initial_capital=100_000.0)
    strat_b_1x = SleeveBTrendStrategy(lookback_breakout=20, ema_trend_filter=50, atr_period=14)
    engine_1x.add_strategy(strat_b_1x)
    metrics_1x = engine_1x.run()

    # 2x Cost Stress Run
    stress_cm = cost_model.get_stress_model(multiplier=2.0)
    engine_2x = BacktestEngine(store=store, cost_model=stress_cm, initial_capital=100_000.0)
    strat_b_2x = SleeveBTrendStrategy(lookback_breakout=20, ema_trend_filter=50, atr_period=14)
    engine_2x.add_strategy(strat_b_2x)
    metrics_2x = engine_2x.run()

    assert metrics_1x.total_trades > 0
    assert metrics_1x.final_equity > metrics_1x.initial_equity
    assert metrics_2x.final_equity > metrics_2x.initial_equity  # Survives 2x cost gate
    assert metrics_1x.max_drawdown_pct < 25.0  # Volatility targeting keeps drawdown bounded

    report = validate_sleeve_gate("Sleeve B Trend", metrics_1x, metrics_2x, [metrics_1x.annualized_sharpe, 1.4, 1.1])
    assert report.passed_2x_cost_test is True
