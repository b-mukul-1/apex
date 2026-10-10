"""
Unit Tests for Advanced Institutional Algos:
1. Dynamic Profit Ratchet
2. BTC Macro Regime Filter
3. 8-Hour Funding Arbitrage Harvester
"""

import pytest
import numpy as np

from apex.risk.profit_ratchet import ProfitRatchet
from apex.signals.btc_regime import BtcRegimeFilter
from apex.signals.funding_harvester import FundingHarvester
from apex.data.store import MarketBar, PointInTimeStore


def test_profit_ratchet_activation_and_trail():
    ratchet = ProfitRatchet(initial_capital=100_000.0, activation_hurdle_pct=0.015, trail_pullback_pct=0.015)
    
    # 1. Under hurdle: standby
    rep1 = ratchet.update(100_500.0)
    assert not rep1.is_ratchet_active
    assert not rep1.should_harvest
    assert rep1.locked_profit_amount == 0.0

    # 2. Crosses +4% ($104,000): Ratchet engages and locks +$2,800 floor
    rep2 = ratchet.update(104_000.0)
    assert rep2.is_ratchet_active
    assert rep2.locked_profit_amount >= 2800.0
    assert not rep2.should_harvest

    # 3. Pulls back below trailing floor (e.g. down to $102,000): Harvest triggered!
    rep3 = ratchet.update(102_000.0)
    assert rep3.should_harvest


def test_btc_regime_filter():
    store = PointInTimeStore()
    now_ms = 1_700_000_000_000
    
    # Construct 30 bars of rising BTC
    bars = []
    base_px = 80_000.0
    for i in range(30):
        mb = MarketBar(
            symbol="BTC/USDT:USDT",
            timestamp_ms=now_ms + (i * 3600_000),
            open=base_px + (i * 200),
            high=base_px + (i * 200) + 100,
            low=base_px + (i * 200) - 50,
            close=base_px + (i * 200) + 50,
            volume=500.0,
            funding_rate_8h=0.0001,
        )
        bars.append(mb)
    store.add_bars("BTC/USDT:USDT", bars)

    btc_filter = BtcRegimeFilter()
    rep = btc_filter.evaluate(store, current_time_ms=bars[-1].timestamp_ms)
    assert rep.regime == "BULL_EXPANSION"
    assert rep.altcoin_long_allowed is True
    assert rep.altcoin_size_multiplier == 1.0


def test_funding_harvester():
    store = PointInTimeStore()
    now_ms = 1_700_000_000_000
    
    # Add symbol with high funding rate (0.02% per 8h = 21.9% APR)
    mb = MarketBar(
        symbol="SOL/USDT:USDT",
        timestamp_ms=now_ms,
        open=150.0,
        high=152.0,
        low=149.0,
        close=151.0,
        volume=1000.0,
        funding_rate_8h=0.0002,
    )
    store.add_bars("SOL/USDT:USDT", [mb])

    harvester = FundingHarvester(min_annualized_apr=0.12)
    rep = harvester.evaluate(store, ["SOL/USDT:USDT"], current_time_ms=now_ms)
    assert len(rep.top_opportunities) == 1
    assert rep.top_opportunities[0].recommended_side == "SHORT"
    assert rep.top_opportunities[0].annualized_apr > 20.0


def test_portfolio_starting_cash_restoration():
    from apex.backtest.portfolio import Portfolio
    # Ensure starting cash restores previous profit without changing initial baseline
    portfolio = Portfolio(initial_capital=100_000.0, starting_cash=104_065.87)
    assert portfolio.initial_capital == 100_000.0
    assert portfolio.cash == 104_065.87
    assert portfolio.total_equity == 104_065.87


def test_session_state_persistence_cycle(tmp_path):
    from apex.execution.live_paper_runner import LivePaperSession
    state_file = str(tmp_path / "test_session_state.json")

    # 1. Initialize session with starting cash
    session = LivePaperSession(
        initial_capital=100_000.0,
        starting_cash=104_065.87,
        state_file=state_file,
    )
    assert session.portfolio.total_equity == 104_065.87
    assert session.profit_ratchet.is_active is True
    assert session.profit_ratchet.ratchet_floor >= 102_800.0

    # 2. Persist state
    session.persist_state()

    # 3. Spin up fresh session and verify state restores
    resumed_session = LivePaperSession(
        initial_capital=100_000.0,
        state_file=state_file,
    )
    assert resumed_session.portfolio.total_equity == 104_065.87
    assert resumed_session.profit_ratchet.peak_equity == 104_065.87
    assert resumed_session.profit_ratchet.is_active is True
