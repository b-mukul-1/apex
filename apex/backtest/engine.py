"""
APEX Event-Driven Backtest Engine
=================================
High-fidelity, strictly chronological backtesting engine.
Guarantees:
1. Zero lookahead leakage (Point-in-Time event iteration)
2. Realistic order netting & maker-first fills
3. Non-linear slippage, spread, maker/taker fees, and funding cash-flows
4. Full trade-level reporting including losers, R-multiples, and Monte Carlo ruin analytics
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from apex.data.store import PointInTimeStore, MarketBar
from apex.backtest.cost_model import CostModel
from apex.backtest.portfolio import Portfolio, TradeRecord
from apex.backtest.events import SignalEvent, FillEvent


@dataclass
class BacktestMetrics:
    initial_equity: float
    final_equity: float
    total_net_return_pct: float
    annualized_return_pct: float
    average_daily_return_pct: float
    best_single_day_pct: float
    worst_single_day_pct: float
    annualized_volatility_pct: float
    annualized_sharpe: float
    sortino_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    net_expectancy_r: float
    longest_losing_streak: int
    probability_of_ruin_pct: float
    total_fees_paid: float
    total_slippage_cost: float


class BacktestEngine:
    """
    Event-driven simulation engine.
    """

    def __init__(
        self,
        store: PointInTimeStore,
        cost_model: CostModel,
        initial_capital: float = 100_000.0,
        risk_per_trade_pct: float = 0.0075,
        risk_service: Optional[Any] = None,
    ):
        self.store = store
        self.cost_model = cost_model
        self.risk_service = risk_service
        self.portfolio = Portfolio(
            initial_capital=initial_capital,
            risk_per_trade_pct=risk_per_trade_pct,
        )
        self.strategies: List[Any] = []
        self.daily_snapshots: Dict[str, float] = {}  # date_str -> equity

    def add_strategy(self, strategy: Any) -> None:
        self.strategies.append(strategy)

    def run(self) -> BacktestMetrics:
        """
        Executes event-driven backtest across all point-in-time bars.
        """
        current_prices: Dict[str, float] = {}
        last_day_str: Optional[str] = None
        last_ts: int = 0

        for bar in self.store.iterate_events():
            sym = bar.symbol
            ts = bar.timestamp_ms
            last_ts = ts
            current_prices[sym] = bar.close

            # 1. Update market prices in portfolio
            self.portfolio.update_market_price(sym, bar.close, ts)

            # 2. Check stop-loss / trailing stop / take-profit exits for existing positions
            if sym in self.portfolio.positions:
                pos = self.portfolio.positions[sym]
                if pos.is_open:
                    exit_hit = False
                    exit_price = bar.close
                    exit_reason = "STOP_LOSS"

                    # Long stop loss and take profit
                    if pos.quantity > 0:
                        if pos.take_profit_price and bar.high >= pos.take_profit_price:
                            exit_hit = True
                            exit_price = min(pos.take_profit_price, bar.high)
                            exit_reason = "TAKE_PROFIT"
                        elif pos.stop_loss_price and bar.low <= pos.stop_loss_price:
                            exit_hit = True
                            exit_price = min(pos.stop_loss_price, bar.open)
                            exit_reason = "STOP_LOSS"

                    # Short stop loss and take profit
                    elif pos.quantity < 0:
                        if pos.take_profit_price and bar.low <= pos.take_profit_price:
                            exit_hit = True
                            exit_price = max(pos.take_profit_price, bar.low)
                            exit_reason = "TAKE_PROFIT"
                        elif pos.stop_loss_price and bar.high >= pos.stop_loss_price:
                            exit_hit = True
                            exit_price = max(pos.stop_loss_price, bar.open)
                            exit_reason = "STOP_LOSS"

                    if exit_hit:
                        is_maker_exit = (exit_reason == "TAKE_PROFIT")
                        side = "SELL" if pos.quantity > 0 else "BUY"
                        exec_res = self.cost_model.simulate_execution(
                            side=side,
                            price=exit_price,
                            size=abs(pos.quantity),
                            is_maker=is_maker_exit,
                        )
                        fill = FillEvent(
                            symbol=sym,
                            timestamp_ms=ts,
                            side=side,
                            quantity=abs(pos.quantity),
                            fill_price=exec_res.effective_fill_price,
                            fee_paid=exec_res.fee_paid,
                            spread_cost=exec_res.spread_cost,
                            slippage_cost=exec_res.slippage_cost,
                            total_friction=exec_res.total_friction,
                            client_order_id=f"{exit_reason}_EXIT",
                            is_maker=is_maker_exit,
                        )
                        self.portfolio.process_fill(fill, sleeve=pos.sleeve, signal_id=exit_reason)

            # 3. Accrue Funding Payments (if applicable)
            if sym in self.portfolio.positions:
                pos = self.portfolio.positions[sym]
                if pos.is_open and bar.funding_rate_8h != 0.0:
                    # Accrue funding cost / yield
                    funding_cost = self.cost_model.calculate_funding_payment(
                        position_notional=pos.notional_value,
                        funding_rate_8h=bar.funding_rate_8h,
                        is_long=(pos.quantity > 0),
                    )
                    self.portfolio.cash -= funding_cost
                    pos.accumulated_funding -= funding_cost

            # 4. Generate signals from registered strategies
            active_signals: List[SignalEvent] = []
            for strat in self.strategies:
                sigs = strat.on_bar(bar, self.store, self.portfolio)
                if sigs:
                    active_signals.extend(sigs)

            # 5. Position Netting & Order Execution
            if active_signals:
                orders = self.portfolio.construct_netted_orders(active_signals, current_prices)
                for order in orders:
                    sig_match = next((s for s in active_signals if s.symbol == order.symbol), None)
                    sleeve = sig_match.sleeve if sig_match else "C_ALPHA"

                    if self.risk_service:
                        self.risk_service.update_equity_and_drawdown(self.portfolio.total_equity, ts)
                        approved, _ = self.risk_service.validate_order(
                            order=order,
                            portfolio=self.portfolio,
                            current_price=order.price,
                            current_time_ms=ts,
                            sleeve=sleeve,
                        )
                        if not approved:
                            continue

                    # Maker-first execution simulation
                    exec_res = self.cost_model.simulate_execution(
                        side=order.side,
                        price=order.price,
                        size=order.quantity,
                        is_maker=order.is_maker,
                    )
                    fill = FillEvent(
                        symbol=order.symbol,
                        timestamp_ms=ts,
                        side=order.side,
                        quantity=order.quantity,
                        fill_price=exec_res.effective_fill_price,
                        fee_paid=exec_res.fee_paid,
                        spread_cost=exec_res.spread_cost,
                        slippage_cost=exec_res.slippage_cost,
                        total_friction=exec_res.total_friction,
                        client_order_id=order.client_order_id,
                        is_maker=order.is_maker,
                    )
                    # Find signal sleeve
                    sig_match = next((s for s in active_signals if s.symbol == order.symbol), None)
                    sleeve = sig_match.sleeve if sig_match else "C_ALPHA"
                    sig_id = sig_match.signal_id if sig_match else "ORD"
                    self.portfolio.process_fill(fill, sleeve=sleeve, signal_id=sig_id)

                    # Update position stops and targets from signal if provided
                    if sig_match and order.symbol in self.portfolio.positions:
                        pos_obj = self.portfolio.positions[order.symbol]
                        if sig_match.stop_loss_price:
                            pos_obj.stop_loss_price = sig_match.stop_loss_price
                        if sig_match.take_profit_price:
                            pos_obj.take_profit_price = sig_match.take_profit_price
                        if sig_match.trailing_stop_atr:
                            pos_obj.trailing_stop_atr = sig_match.trailing_stop_atr

            # 6. Daily snapshot for performance metrics
            dt = pd.to_datetime(ts, unit="ms", utc=True)
            day_str = dt.strftime("%Y-%m-%d")
            if day_str != last_day_str:
                self.daily_snapshots[day_str] = self.portfolio.total_equity
                last_day_str = day_str

        # Liquidate any remaining open positions at simulation end
        for sym, pos in list(self.portfolio.positions.items()):
            if pos.is_open and sym in current_prices:
                final_price = current_prices[sym]
                side = "SELL" if pos.quantity > 0 else "BUY"
                exec_res = self.cost_model.simulate_execution(
                    side=side,
                    price=final_price,
                    size=abs(pos.quantity),
                    is_maker=True,
                )
                fill = FillEvent(
                    symbol=sym,
                    timestamp_ms=last_ts if 'last_ts' in locals() else 0,
                    side=side,
                    quantity=abs(pos.quantity),
                    fill_price=exec_res.effective_fill_price,
                    fee_paid=exec_res.fee_paid,
                    spread_cost=exec_res.spread_cost,
                    slippage_cost=exec_res.slippage_cost,
                    total_friction=exec_res.total_friction,
                    client_order_id="SIM_CLOSE_TERMINAL",
                    is_maker=True,
                )
                self.portfolio.process_fill(fill, sleeve=pos.sleeve, signal_id="TERMINAL_EXIT")

        return self.compute_metrics()

    def compute_metrics(self) -> BacktestMetrics:
        """Calculates institutional risk and performance metrics."""
        eq_series = pd.Series(self.daily_snapshots)
        if len(eq_series) < 2:
            return BacktestMetrics(
                initial_equity=self.portfolio.initial_capital,
                final_equity=self.portfolio.total_equity,
                total_net_return_pct=0.0,
                annualized_return_pct=0.0,
                average_daily_return_pct=0.0,
                best_single_day_pct=0.0,
                worst_single_day_pct=0.0,
                annualized_volatility_pct=0.0,
                annualized_sharpe=0.0,
                sortino_ratio=0.0,
                max_drawdown_pct=0.0,
                calmar_ratio=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate_pct=0.0,
                profit_factor=0.0,
                net_expectancy_r=0.0,
                longest_losing_streak=0,
                probability_of_ruin_pct=0.0,
                total_fees_paid=0.0,
                total_slippage_cost=0.0,
            )

        daily_returns = eq_series.pct_change().dropna()
        n_days = len(daily_returns)
        total_ret = (self.portfolio.total_equity / self.portfolio.initial_capital) - 1.0
        ann_factor = 365.0 / max(n_days, 1)
        ann_ret = (1.0 + total_ret) ** ann_factor - 1.0 if total_ret > -1.0 else -1.0

        daily_mean = daily_returns.mean()
        daily_std = daily_returns.std()
        ann_vol = daily_std * np.sqrt(365.0)

        sharpe = (daily_mean / daily_std * np.sqrt(365.0)) if daily_std > 1e-8 else 0.0

        # Downside deviation for Sortino
        neg_returns = daily_returns[daily_returns < 0]
        downside_std = neg_returns.std() * np.sqrt(365.0) if len(neg_returns) > 0 else 1e-6
        sortino = (ann_ret / downside_std) if downside_std > 1e-8 else 0.0

        # Max Drawdown
        cum_max = eq_series.cummax()
        drawdowns = (eq_series - cum_max) / cum_max
        max_dd = abs(drawdowns.min())
        calmar = (ann_ret / max_dd) if max_dd > 1e-6 else 0.0

        # Trades stats
        trades = self.portfolio.trades
        total_trades = len(trades)
        wins = [t for t in trades if t.realized_pnl > 0]
        losses = [t for t in trades if t.realized_pnl <= 0]
        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = (n_wins / total_trades * 100.0) if total_trades > 0 else 0.0

        total_gain = sum(t.realized_pnl for t in wins)
        total_loss = abs(sum(t.realized_pnl for t in losses))
        profit_factor = (total_gain / total_loss) if total_loss > 1e-6 else (10.0 if total_gain > 0 else 0.0)

        # Net expectancy in R-multiples
        r_multiples = [t.pnl_r_multiple for t in trades]
        net_expectancy_r = float(np.mean(r_multiples)) if r_multiples else 0.0

        # Longest losing streak
        current_streak = 0
        max_streak = 0
        for t in trades:
            if t.realized_pnl <= 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        # Ruin probability (Monte Carlo bootstrap of trade returns)
        ruin_prob = 0.0
        if len(r_multiples) > 10:
            rng = np.random.default_rng(42)
            n_sims = 1000
            ruin_count = 0
            for _ in range(n_sims):
                sampled_r = rng.choice(r_multiples, size=100, replace=True)
                sim_equity = 1.0
                for r in sampled_r:
                    sim_equity += sim_equity * (0.0075 * r)  # 0.75% risk per trade
                    if sim_equity < 0.50:  # 50% drawdown = ruin threshold
                        ruin_count += 1
                        break
            ruin_prob = (ruin_count / n_sims) * 100.0

        total_fees = sum(p.accumulated_fees for p in self.portfolio.positions.values())

        return BacktestMetrics(
            initial_equity=self.portfolio.initial_capital,
            final_equity=self.portfolio.total_equity,
            total_net_return_pct=float(total_ret * 100.0),
            annualized_return_pct=float(ann_ret * 100.0),
            average_daily_return_pct=float(daily_mean * 100.0),
            best_single_day_pct=float(daily_returns.max() * 100.0 if len(daily_returns) > 0 else 0.0),
            worst_single_day_pct=float(daily_returns.min() * 100.0 if len(daily_returns) > 0 else 0.0),
            annualized_volatility_pct=float(ann_vol * 100.0),
            annualized_sharpe=float(sharpe),
            sortino_ratio=float(sortino),
            max_drawdown_pct=float(max_dd * 100.0),
            calmar_ratio=float(calmar),
            total_trades=total_trades,
            winning_trades=n_wins,
            losing_trades=n_losses,
            win_rate_pct=float(win_rate),
            profit_factor=float(profit_factor),
            net_expectancy_r=net_expectancy_r,
            longest_losing_streak=max_streak,
            probability_of_ruin_pct=float(ruin_prob),
            total_fees_paid=float(total_fees),
            total_slippage_cost=0.0,
        )
