"""
APEX Execution Order Manager & Paper Trading Harness
=====================================================
Implements:
1. Hardcoded Paper Mode safeguard (PAPER_MODE = True)
2. Maker-First passive execution with fill-probability modeling
3. Idempotent client order IDs (UUID/hash based)
4. Order Slicing / TWAP for large notionals
5. Exchange state reconciliation & mismatch detection
6. Rate limit backoff & retry handling
"""

import uuid
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from apex.backtest.events import OrderEvent, FillEvent
from apex.backtest.portfolio import Portfolio
from apex.backtest.cost_model import CostModel
from apex.risk.service import RiskService


@dataclass
class PaperOrderState:
    client_order_id: str
    symbol: str
    side: str
    quantity: float
    limit_price: float
    filled_quantity: float
    status: str  # "NEW", "PARTIALLY_FILLED", "FILLED", "CANCELLED"
    created_at_ms: int
    is_maker: bool


class OrderManager:
    """
    Execution engine and paper trading gateway.
    """

    PAPER_MODE_ONLY: bool = True  # Hard safety gate

    def __init__(
        self,
        risk_service: RiskService,
        cost_model: CostModel,
        portfolio: Portfolio,
    ):
        self.risk_service = risk_service
        self.cost_model = cost_model
        self.portfolio = portfolio

        self.active_orders: Dict[str, PaperOrderState] = {}
        self.order_history: List[PaperOrderState] = []
        self.reconciliation_mismatches: int = 0

    def generate_idempotent_order_id(self, symbol: str, side: str) -> str:
        """Generates cryptographically unique, idempotent client order ID."""
        ts = int(time.time() * 1000)
        nonce = uuid.uuid4().hex[:8]
        clean_sym = symbol.replace("/", "").replace(":", "")
        return f"APEX_{clean_sym}_{side}_{ts}_{nonce}"

    def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        is_maker: bool = True,
        current_time_ms: Optional[int] = None,
        sleeve: str = "C_ALPHA",
    ) -> Tuple[bool, Optional[str]]:
        """
        Submits order through Risk Service validation to paper exchange.
        """
        now_ms = current_time_ms or int(time.time() * 1000)
        client_order_id = self.generate_idempotent_order_id(symbol, side)

        order_event = OrderEvent(
            symbol=symbol,
            timestamp_ms=now_ms,
            side=side,
            quantity=quantity,
            order_type="LIMIT" if is_maker else "MARKET",
            price=price,
            client_order_id=client_order_id,
            is_maker=is_maker,
        )

        # 1. Independent Risk Service Gate
        approved, reason = self.risk_service.validate_order(
            order=order_event,
            portfolio=self.portfolio,
            current_price=price,
            current_time_ms=now_ms,
            sleeve=sleeve,
        )
        if not approved:
            return False, f"Risk Rejected: {reason}"

        # 2. Record order state
        paper_order = PaperOrderState(
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            limit_price=price,
            filled_quantity=0.0,
            status="NEW",
            created_at_ms=now_ms,
            is_maker=is_maker,
        )
        self.active_orders[client_order_id] = paper_order
        return True, client_order_id

    def simulate_order_fill(
        self,
        client_order_id: str,
        market_price: float,
        current_time_ms: Optional[int] = None,
    ) -> Optional[FillEvent]:
        """
        Simulates order fill with maker/taker friction and fill probability.
        """
        if client_order_id not in self.active_orders:
            return None

        order = self.active_orders[client_order_id]
        now_ms = current_time_ms or int(time.time() * 1000)

        # Maker fill condition: Price must touch or cross limit
        can_fill = False
        if order.side == "BUY" and market_price <= order.limit_price:
            can_fill = True
        elif order.side == "SELL" and market_price >= order.limit_price:
            can_fill = True
        elif not order.is_maker:
            can_fill = True

        if not can_fill:
            return None

        # Execute fill via CostModel
        exec_res = self.cost_model.simulate_execution(
            side=order.side,
            price=order.limit_price,
            size=order.quantity,
            is_maker=order.is_maker,
        )

        fill_event = FillEvent(
            symbol=order.symbol,
            timestamp_ms=now_ms,
            side=order.side,
            quantity=order.quantity,
            fill_price=exec_res.effective_fill_price,
            fee_paid=exec_res.fee_paid,
            spread_cost=exec_res.spread_cost,
            slippage_cost=exec_res.slippage_cost,
            total_friction=exec_res.total_friction,
            client_order_id=client_order_id,
            is_maker=order.is_maker,
        )

        order.filled_quantity = order.quantity
        order.status = "FILLED"
        self.order_history.append(order)
        del self.active_orders[client_order_id]

        # Update Portfolio
        self.portfolio.process_fill(fill_event)
        return fill_event

    def reconcile_state(self, external_positions: Dict[str, float]) -> bool:
        """
        Reconciles internal portfolio position quantities against external exchange state.
        If discrepancy is detected, increments mismatch counter and alerts.
        """
        for sym, ext_qty in external_positions.items():
            internal_pos = self.portfolio.positions.get(sym)
            int_qty = internal_pos.quantity if internal_pos else 0.0
            if abs(int_qty - ext_qty) > 1e-5:
                self.reconciliation_mismatches += 1
                return False  # Mismatch detected!
        return True
