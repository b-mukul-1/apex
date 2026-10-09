"""
APEX Event System
=================
Event hierarchies for the event-driven backtesting and live execution architecture.
"""

from dataclasses import dataclass
from typing import Optional
from apex.data.store import MarketBar


@dataclass
class MarketEvent:
    bar: MarketBar

    @property
    def timestamp_ms(self) -> int:
        return self.bar.timestamp_ms

    @property
    def symbol(self) -> str:
        return self.bar.symbol


@dataclass
class SignalEvent:
    symbol: str
    timestamp_ms: int
    sleeve: str              # "A_CARRY", "B_TREND", "C_ALPHA"
    signal_id: str           # e.g. "S01_VOL_SQUEEZE"
    direction: float         # +1.0 (Long), -1.0 (Short), 0.0 (Flat)
    strength: float = 1.0    # Normalized confidence [0.0, 1.0]
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_atr: Optional[float] = None
    expected_edge_bps: float = 0.0


@dataclass
class OrderEvent:
    symbol: str
    timestamp_ms: int
    side: str                # "BUY" or "SELL"
    quantity: float
    order_type: str          # "LIMIT" or "MARKET"
    price: float
    client_order_id: str
    is_maker: bool = True
    reduce_only: bool = False


@dataclass
class FillEvent:
    symbol: str
    timestamp_ms: int
    side: str
    quantity: float
    fill_price: float
    fee_paid: float
    spread_cost: float
    slippage_cost: float
    total_friction: float
    client_order_id: str
    is_maker: bool
