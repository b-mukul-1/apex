"""
Phase 5 Validation Gate Tests: Paper Trading Execution & Live Drift Monitoring
=============================================================================
Validates:
1. Paper trading order manager lifecycle (creation, maker limit logic, fill execution).
2. Cryptographic idempotency of client order IDs.
3. Position state reconciliation and mismatch alert detection.
4. Live vs Backtest execution telemetry and slippage drift evaluation.
"""

import pytest
from apex.risk.service import RiskService
from apex.backtest.cost_model import CostModel
from apex.backtest.portfolio import Portfolio
from apex.execution.order_manager import OrderManager
from apex.monitor.live_tracker import LiveVsBacktestMonitor


def test_order_manager_paper_lifecycle():
    risk = RiskService()
    cost_model = CostModel()
    portfolio = Portfolio(initial_capital=100_000.0)
    om = OrderManager(risk_service=risk, cost_model=cost_model, portfolio=portfolio)

    # Submit maker order
    success, order_id = om.submit_order(
        symbol="BTC/USDT:USDT",
        side="BUY",
        quantity=0.5,
        price=50000.0,
        is_maker=True,
    )
    assert success is True
    assert order_id in om.active_orders

    # Price hasn't reached limit (market price 50100 > limit 50000) -> no fill
    no_fill = om.simulate_order_fill(order_id, market_price=50100.0)
    assert no_fill is None
    assert order_id in om.active_orders

    # Market price touches limit (50000.0) -> fills order!
    fill = om.simulate_order_fill(order_id, market_price=50000.0)
    assert fill is not None
    assert fill.quantity == 0.5
    assert order_id not in om.active_orders
    assert portfolio.positions["BTC/USDT:USDT"].quantity == 0.5


def test_order_id_idempotency():
    risk = RiskService()
    cost_model = CostModel()
    portfolio = Portfolio()
    om = OrderManager(risk_service=risk, cost_model=cost_model, portfolio=portfolio)

    id1 = om.generate_idempotent_order_id("ETH/USDT:USDT", "BUY")
    id2 = om.generate_idempotent_order_id("ETH/USDT:USDT", "BUY")
    assert id1 != id2
    assert "APEX" in id1


def test_state_reconciliation():
    risk = RiskService()
    cost_model = CostModel()
    portfolio = Portfolio()
    om = OrderManager(risk_service=risk, cost_model=cost_model, portfolio=portfolio)

    # Clean match
    assert om.reconcile_state({"BTC/USDT:USDT": 0.0}) is True

    # Mismatch (exchange says position is 2.0 BTC, portfolio has 0.0)
    assert om.reconcile_state({"BTC/USDT:USDT": 2.0}) is False
    assert om.reconciliation_mismatches == 1


def test_live_vs_backtest_drift_evaluation():
    monitor = LiveVsBacktestMonitor(expected_slippage_bps=2.0)

    # In-band fills
    for _ in range(10):
        monitor.record_fill_telemetry(intended_price=50000.0, fill_price=50010.0, side="BUY", latency_ms=120.0)

    report_ok = monitor.evaluate_drift()
    assert report_ok.is_drift_detected is False
    assert "IN_BAND" in report_ok.status_summary

    # Drifting fills with severe slippage (intended 50000, filled 50200 = 40 bps)
    monitor_drift = LiveVsBacktestMonitor(expected_slippage_bps=2.0)
    for _ in range(10):
        monitor_drift.record_fill_telemetry(intended_price=50000.0, fill_price=50200.0, side="BUY", latency_ms=180.0)

    report_drift = monitor_drift.evaluate_drift()
    assert report_drift.is_drift_detected is True
    assert "DRIFT_WARNING" in report_drift.status_summary
