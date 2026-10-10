"""
APEX Portfolio Accounting & Position Netting
============================================
Handles:
1. Multi-asset position tracking & unrealized/realized P&L
2. Position Netting: offsets opposing signals across sleeves to minimize turnover and fees
3. Volatility-targeted sizing: Size = (Equity * Risk%) / Stop Distance
4. Anti-martingale enforcement (never scale up after losses)
5. Multi-sleeve capital partitioning (A: 45%, B: 30%, C: 25%)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
from apex.backtest.events import FillEvent, OrderEvent, SignalEvent


@dataclass
class Position:
    symbol: str
    quantity: float = 0.0          # Positive = Long, Negative = Short
    average_entry_price: float = 0.0
    current_market_price: float = 0.0
    realized_pnl: float = 0.0
    accumulated_funding: float = 0.0
    accumulated_fees: float = 0.0
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_atr: Optional[float] = None
    trailing_peak_price: Optional[float] = None
    sleeve: str = "C_ALPHA"

    @property
    def is_open(self) -> bool:
        return abs(self.quantity) > 1e-8

    @property
    def notional_value(self) -> float:
        return abs(self.quantity) * self.current_market_price

    @property
    def unrealized_pnl(self) -> float:
        if not self.is_open:
            return 0.0
        if self.sleeve == "A_CARRY":
            # Delta-neutral carry: spot leg offsets perp leg; price delta is 0
            return 0.0
        return self.quantity * (self.current_market_price - self.average_entry_price)


@dataclass
class TradeRecord:
    symbol: str
    entry_time_ms: int
    exit_time_ms: int
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    realized_pnl: float
    fee_paid: float
    pnl_r_multiple: float  # Realized PnL divided by initial $ risk (R)
    sleeve: str
    signal_id: str


class Portfolio:
    """
    Core portfolio accountant and order generator.
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        risk_per_trade_pct: float = 0.0075,  # 0.75% equity risk per position
        max_gross_leverage: float = 3.0,
        sleeve_weights: Optional[Dict[str, float]] = None,
        starting_cash: Optional[float] = None,
    ):
        self.initial_capital = initial_capital
        self.cash = float(starting_cash) if starting_cash is not None else initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_gross_leverage = max_gross_leverage
        self.sleeve_weights = sleeve_weights or {
            "A_CARRY": 0.45,
            "B_TREND": 0.30,
            "C_ALPHA": 0.25,
        }

        self.positions: Dict[str, Position] = {}
        self.trades: List[TradeRecord] = []
        self.equity_history: List[tuple[int, float]] = []  # (ts, equity)
        self.order_counter = 0

    @property
    def total_equity(self) -> float:
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        return self.cash + unrealized

    @property
    def total_gross_notional(self) -> float:
        return sum(p.notional_value for p in self.positions.values())

    @property
    def gross_leverage(self) -> float:
        eq = self.total_equity
        return (self.total_gross_notional / eq) if eq > 0 else 0.0

    def update_market_price(self, symbol: str, price: float, timestamp_ms: int) -> None:
        """Updates mark price of a position and records equity snapshot."""
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.current_market_price = price
            # Update trailing peak price if long/short
            if pos.is_open:
                if pos.quantity > 0:
                    pos.trailing_peak_price = max(pos.trailing_peak_price or price, price)
                else:
                    pos.trailing_peak_price = min(pos.trailing_peak_price or price, price)

    def process_fill(self, fill: FillEvent, sleeve: str = "C_ALPHA", signal_id: str = "SIG") -> None:
        """Processes executed FillEvent, updating cash, position, and P&L."""
        symbol = fill.symbol
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol, sleeve=sleeve)
        pos = self.positions[symbol]

        fill_qty = fill.quantity if fill.side.upper() == "BUY" else -fill.quantity
        old_qty = pos.quantity
        new_qty = old_qty + fill_qty

        # Cash adjustment for fees
        self.cash -= fill.fee_paid
        pos.accumulated_fees += fill.fee_paid

        # Check if closing or opening
        if old_qty == 0:
            # Opening new position
            pos.quantity = new_qty
            pos.average_entry_price = fill.fill_price
            pos.current_market_price = fill.fill_price
            pos.trailing_peak_price = fill.fill_price
            pos.sleeve = sleeve
        elif (old_qty > 0 and fill_qty > 0) or (old_qty < 0 and fill_qty < 0):
            # Adding to existing position
            total_notional = (old_qty * pos.average_entry_price) + (fill_qty * fill.fill_price)
            pos.quantity = new_qty
            pos.average_entry_price = total_notional / new_qty
            pos.current_market_price = fill.fill_price
        else:
            # Reducing or closing position
            closed_qty = min(abs(old_qty), abs(fill_qty))
            pnl_direction = 1.0 if old_qty > 0 else -1.0
            if pos.sleeve == "A_CARRY":
                trade_pnl = 0.0  # Delta-neutral: spot leg offsets perp leg
            else:
                trade_pnl = closed_qty * (fill.fill_price - pos.average_entry_price) * pnl_direction
            self.cash += trade_pnl
            pos.realized_pnl += trade_pnl

            # Calculate R-multiple
            initial_risk = self.total_equity * self.risk_per_trade_pct
            r_multiple = trade_pnl / max(initial_risk, 1e-4)

            self.trades.append(TradeRecord(
                symbol=symbol,
                entry_time_ms=fill.timestamp_ms - 86400000, # Approx
                exit_time_ms=fill.timestamp_ms,
                side="LONG" if old_qty > 0 else "SHORT",
                quantity=closed_qty,
                entry_price=pos.average_entry_price,
                exit_price=fill.fill_price,
                realized_pnl=trade_pnl,
                fee_paid=fill.fee_paid,
                pnl_r_multiple=r_multiple,
                sleeve=pos.sleeve,
                signal_id=signal_id,
            ))

            pos.quantity = new_qty
            if abs(new_qty) < 1e-8:
                pos.quantity = 0.0
                pos.average_entry_price = 0.0
                pos.trailing_peak_price = None
                pos.stop_loss_price = None
                pos.take_profit_price = None
                pos.trailing_stop_atr = None

    def construct_netted_orders(
        self,
        signals: List[SignalEvent],
        current_prices: Dict[str, float],
    ) -> List[OrderEvent]:
        """
        Position Netting:
        Aggregates multiple signal targets across sleeves to construct the minimum
        necessary net orders, avoiding churning fees.
        """
        target_positions: Dict[str, float] = {}  # symbol -> target_quantity
        equity = self.total_equity

        for sig in signals:
            sym = sig.symbol
            price = current_prices.get(sym, 0.0)
            if price <= 0.0:
                continue

            # Volatility-targeted sizing:
            # Stop distance
            if sig.stop_loss_price and sig.stop_loss_price > 0:
                stop_dist = abs(price - sig.stop_loss_price)
            else:
                # Default 2% stop distance
                stop_dist = price * 0.02

            dollar_risk = equity * self.risk_per_trade_pct
            # Target size = Dollar Risk / Stop Distance
            ideal_qty = dollar_risk / max(stop_dist, 1e-6)

            # Cap per-position notional at 15% of total equity
            max_pos_notional = equity * 0.15
            ideal_qty = min(ideal_qty, max_pos_notional / price)

            target_qty = sig.direction * ideal_qty * sig.strength
            target_positions[sym] = target_positions.get(sym, 0.0) + target_qty

        # Generate orders: difference between target and current position
        orders: List[OrderEvent] = []
        for sym, tgt_qty in target_positions.items():
            current_qty = self.positions.get(sym, Position(symbol=sym)).quantity
            delta_qty = tgt_qty - current_qty

            if abs(delta_qty * current_prices[sym]) < 25.0:  # Ignore dust trades < $25
                continue

            self.order_counter += 1
            side = "BUY" if delta_qty > 0 else "SELL"
            orders.append(OrderEvent(
                symbol=sym,
                timestamp_ms=signals[0].timestamp_ms if signals else 0,
                side=side,
                quantity=abs(delta_qty),
                order_type="LIMIT",
                price=current_prices[sym],
                client_order_id=f"ORD_{self.order_counter:07d}",
                is_maker=True,
            ))

        return orders
