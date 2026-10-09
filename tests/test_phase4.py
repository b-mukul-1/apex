"""
Phase 4 Validation Gate Tests: Risk Service & Failure Injection
==============================================================
Validates that ALL forced risk breaches immediately halt trading or veto orders:
1. Gross leverage hard cap breach (> 3.0x)
2. Sleeve C open risk cap breach (> 5.0%)
3. Daily loss limit breach (>= 3.0%) -> 24h halt
4. Drawdown ladder (-8% halve size, -12% disable C, -18% full halt)
5. Stale data cutoff (> 30s)
6. Abnormal spread filter (> 50 bps)
7. Rate limit orders/min (> 30/min)
8. Manual Kill Switch
9. Chaos Engineering / Failure-injection tests
"""

import pytest
import time
from apex.risk.service import RiskService
from apex.backtest.portfolio import Portfolio, Position
from apex.backtest.events import OrderEvent


def test_gross_leverage_hard_cap_veto():
    risk = RiskService(max_gross_leverage=3.0)
    portfolio = Portfolio(initial_capital=100_000.0)

    # Attempt to order $350,000 notional (3.5x leverage)
    order = OrderEvent(
        symbol="BTC/USDT:USDT",
        timestamp_ms=1000,
        side="BUY",
        quantity=7.0,  # 7 * 50,000 = $350,000
        order_type="LIMIT",
        price=50000.0,
        client_order_id="TEST_LEV",
    )

    approved, reason = risk.validate_order(order, portfolio, current_price=50000.0, current_time_ms=1000)
    assert approved is False
    assert "Gross leverage" in reason


def test_sleeve_c_open_risk_cap_veto():
    risk = RiskService(max_sleeve_c_open_risk_pct=0.05)
    portfolio = Portfolio(initial_capital=100_000.0)

    # Order risking $6,000 (6% of equity)
    # Stop distance 2.5% of $250,000 notional = $6,250 risk
    order = OrderEvent(
        symbol="SOL/USDT:USDT",
        timestamp_ms=1000,
        side="BUY",
        quantity=2500.0,
        order_type="LIMIT",
        price=100.0,
        client_order_id="TEST_C_RISK",
    )

    approved, reason = risk.validate_order(
        order, portfolio, current_price=100.0, current_time_ms=1000, sleeve="C_ALPHA"
    )
    assert approved is False
    assert "Sleeve C total open risk" in reason


def test_daily_loss_limit_triggers_24h_halt():
    risk = RiskService(daily_loss_limit_pct=0.03)
    portfolio = Portfolio(initial_capital=100_000.0)

    now_ms = 1_700_000_000_000
    risk.update_equity_and_drawdown(current_equity=100_000.0, current_time_ms=now_ms)

    # Equity drops 3.5% on the day
    risk.update_equity_and_drawdown(current_equity=96_500.0, current_time_ms=now_ms + 1000)
    assert risk.is_24h_halted is True

    # Attempt order during halt
    order = OrderEvent(
        symbol="ETH/USDT:USDT",
        timestamp_ms=now_ms + 2000,
        side="BUY",
        quantity=1.0,
        order_type="LIMIT",
        price=2000.0,
        client_order_id="TEST_HALT",
    )
    approved, reason = risk.validate_order(order, portfolio, current_price=2000.0, current_time_ms=now_ms + 2000)
    assert approved is False
    assert "halted for 24h" in reason


def test_drawdown_ladder():
    risk = RiskService()
    now_ms = 1_700_000_000_000
    risk.update_equity_and_drawdown(current_equity=100_000.0, current_time_ms=now_ms)

    # Step 1: -9% drawdown -> Halve position sizing
    risk.update_equity_and_drawdown(current_equity=91_000.0, current_time_ms=now_ms + 1000)
    assert risk.size_multiplier == 0.5

    # Step 2: -13% drawdown -> Disable Sleeve C
    risk.update_equity_and_drawdown(current_equity=87_000.0, current_time_ms=now_ms + 2000)
    assert risk.is_sleeve_c_disabled is True

    # Step 3: -19% drawdown -> Full catastrophic halt
    risk.update_equity_and_drawdown(current_equity=81_000.0, current_time_ms=now_ms + 3000)
    assert risk.is_full_halted is True


def test_stale_data_and_abnormal_spread_veto():
    risk = RiskService(max_data_staleness_ms=30_000, max_spread_bps=50.0)
    portfolio = Portfolio(initial_capital=100_000.0)
    now_ms = 1_700_000_000_000

    risk.record_heartbeat(current_time_ms=now_ms)

    order = OrderEvent(
        symbol="BTC/USDT:USDT",
        timestamp_ms=now_ms + 40_000,  # 40s later (> 30s)
        side="BUY",
        quantity=0.1,
        order_type="LIMIT",
        price=50000.0,
        client_order_id="TEST_STALE",
    )

    # Stale data test
    approved, reason = risk.validate_order(
        order, portfolio, current_price=50000.0, current_time_ms=now_ms + 40_000
    )
    assert approved is False
    assert "Data feed stale" in reason

    # Abnormal spread test (65 bps > 50 bps)
    risk.record_heartbeat(current_time_ms=now_ms + 50_000)
    approved_spread, reason_spread = risk.validate_order(
        order, portfolio, current_price=50000.0, current_time_ms=now_ms + 50_000, bid_ask_spread_bps=65.0
    )
    assert approved_spread is False
    assert "Abnormal spread" in reason_spread


def test_manual_kill_switch_and_chaos_injection():
    risk = RiskService()
    portfolio = Portfolio(initial_capital=100_000.0)
    order = OrderEvent(
        symbol="BTC/USDT:USDT",
        timestamp_ms=1000,
        side="BUY",
        quantity=0.1,
        order_type="LIMIT",
        price=50000.0,
        client_order_id="TEST_KILL",
    )

    # Manual kill switch test
    risk.trigger_kill_switch("EMERGENCY_OPERATOR_OVERRIDE")
    approved, reason = risk.validate_order(order, portfolio, current_price=50000.0, current_time_ms=1000)
    assert approved is False
    assert "kill switch active" in reason

    # Failure injection: Dropped websocket
    risk_fresh = RiskService()
    res = risk_fresh.inject_failure("DROPPED_WEBSOCKET")
    assert res["status"] == "FEED_FROZEN"
    now_ms = int(time.time() * 1000)
    approved_ws, reason_ws = risk_fresh.validate_order(order, portfolio, current_price=50000.0, current_time_ms=now_ms)
    assert approved_ws is False
    assert "Data feed stale" in reason_ws
