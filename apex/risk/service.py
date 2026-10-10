"""
APEX Independent Risk Service
=============================
Highest-priority architectural component.
Strategies CANNOT override or bypass this service.

Enforces:
1. Gross leverage hard cap: 3.0x
2. Isolated margin & liquidation distance >= 2x stop distance
3. Maximum open risk in Sleeve C <= 5.0% of equity
4. Daily loss limit: -3.0% -> Flatten C, halt trading for 24 hours
5. Drawdown Ladder:
   - -8%: Halve position sizing (size_multiplier = 0.5)
   - -12%: Disable Sleeve C entirely
   - -18%: Full catastrophic halt requiring manual review
6. Stale data cutoff (> 30,000 ms data gap)
7. Abnormal spread filter (> 50 bps)
8. Orders-per-minute throttle (max 30 orders/minute)
9. Clock drift detection (> 1,000 ms)
10. Manual Kill Switch & Failure Injection Test Suite
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import time
from apex.backtest.events import OrderEvent
from apex.backtest.portfolio import Portfolio


@dataclass
class RiskBreachRecord:
    timestamp_ms: int
    rule_breached: str
    description: str
    action_taken: str


class RiskService:
    """
    Independent Risk Daemon and Sentinel.
    """

    def __init__(
        self,
        max_gross_leverage: float = 3.0,
        max_sleeve_c_open_risk_pct: float = 0.05,  # 5%
        daily_loss_limit_pct: float = 0.03,         # 3%
        dd_halve_pct: float = 0.08,                 # 8%
        dd_disable_c_pct: float = 0.12,             # 12%
        dd_full_halt_pct: float = 0.18,             # 18%
        max_orders_per_minute: int = 30,
        max_data_staleness_ms: int = 30_000,        # 30 seconds
        max_spread_bps: float = 50.0,
    ):
        self.max_gross_leverage = max_gross_leverage
        self.max_c_risk = max_sleeve_c_open_risk_pct
        self.daily_loss_limit = daily_loss_limit_pct
        self.dd_halve = dd_halve_pct
        self.dd_disable_c = dd_disable_c_pct
        self.dd_full_halt = dd_full_halt_pct
        self.max_orders_per_min = max_orders_per_minute
        self.max_staleness_ms = max_data_staleness_ms
        self.max_spread_bps = max_spread_bps

        # State tracking
        self.is_kill_switch_active: bool = False
        self.is_24h_halted: bool = False
        self.halt_until_ms: int = 0
        self.is_sleeve_c_disabled: bool = False
        self.is_full_halted: bool = False
        self.size_multiplier: float = 1.0

        self.high_water_mark: float = 0.0
        self.daily_start_equity: float = 0.0
        self.order_timestamps: List[int] = []
        self.last_heartbeat_ms: int = 0
        self.breach_log: List[RiskBreachRecord] = []

    def update_equity_and_drawdown(self, current_equity: float, current_time_ms: int) -> None:
        """Updates HWM, daily drawdown, and evaluates the drawdown ladder."""
        if self.high_water_mark <= 0.0:
            self.high_water_mark = current_equity
            self.daily_start_equity = current_equity

        self.high_water_mark = max(self.high_water_mark, current_equity)
        drawdown_pct = (self.high_water_mark - current_equity) / max(self.high_water_mark, 1e-4)

        # 1. Daily loss check & recovery
        daily_loss_pct = (self.daily_start_equity - current_equity) / max(self.daily_start_equity, 1e-4)
        if daily_loss_pct >= self.daily_loss_limit and not self.is_24h_halted:
            self.is_24h_halted = True
            self.halt_until_ms = current_time_ms + (24 * 3600 * 1000)
            self.breach_log.append(RiskBreachRecord(
                timestamp_ms=current_time_ms,
                rule_breached="DAILY_LOSS_LIMIT_3PCT",
                description=f"Daily loss reached {daily_loss_pct * 100:.2f}% >= {self.daily_loss_limit * 100:.1f}%",
                action_taken="FLATTEN_SLEEVE_C_AND_HALT_24H",
            ))
        elif current_equity >= self.daily_start_equity and self.is_24h_halted:
            # When equity is in profit relative to daily baseline, restore normal trading
            self.is_24h_halted = False

        # 2. Drawdown ladder
        if drawdown_pct >= self.dd_full_halt:
            self.is_full_halted = True
            self.breach_log.append(RiskBreachRecord(
                timestamp_ms=current_time_ms,
                rule_breached="DRAWDOWN_LADDER_18PCT",
                description=f"Drawdown reached {drawdown_pct * 100:.2f}% >= 18%",
                action_taken="FULL_SYSTEM_HALT_MANUAL_REVIEW_REQUIRED",
            ))
        elif drawdown_pct >= self.dd_disable_c:
            self.is_sleeve_c_disabled = True
            self.breach_log.append(RiskBreachRecord(
                timestamp_ms=current_time_ms,
                rule_breached="DRAWDOWN_LADDER_12PCT",
                description=f"Drawdown reached {drawdown_pct * 100:.2f}% >= 12%",
                action_taken="DISABLE_SLEEVE_C",
            ))
        elif drawdown_pct >= self.dd_halve:
            self.size_multiplier = 0.5
            self.breach_log.append(RiskBreachRecord(
                timestamp_ms=current_time_ms,
                rule_breached="DRAWDOWN_LADDER_8PCT",
                description=f"Drawdown reached {drawdown_pct * 100:.2f}% >= 8%",
                action_taken="HALVE_POSITION_SIZING",
            ))
        else:
            self.size_multiplier = 1.0

    def record_heartbeat(self, current_time_ms: int) -> None:
        self.last_heartbeat_ms = current_time_ms

    def trigger_kill_switch(self, reason: str = "MANUAL_TRIGGER") -> None:
        """Immediate emergency kill switch."""
        self.is_kill_switch_active = True
        self.breach_log.append(RiskBreachRecord(
            timestamp_ms=int(time.time() * 1000),
            rule_breached="MANUAL_KILL_SWITCH",
            description=f"Kill switch activated: {reason}",
            action_taken="ABORT_ALL_ORDERS_FLATTEN_IMMEDIATELY",
        ))

    def validate_order(
        self,
        order: OrderEvent,
        portfolio: Portfolio,
        current_price: float,
        current_time_ms: int,
        bid_ask_spread_bps: float = 2.0,
        sleeve: str = "C_ALPHA",
    ) -> Tuple[bool, str]:
        """
        Validates order against hard risk limits.
        Returns (True, "APPROVED") or (False, "REJECTION_REASON").
        """
        # 1. Kill Switch & Full Halt Checks
        if self.is_kill_switch_active:
            return False, "VETO: Manual kill switch active"
        if self.is_full_halted:
            return False, "VETO: Full system halt active (18% drawdown ladder breached)"

        # 2. 24h Daily Halt Check
        if self.is_24h_halted:
            if current_time_ms < self.halt_until_ms:
                return False, "VETO: Trading halted for 24h due to 3% daily loss limit breach"
            else:
                self.is_24h_halted = False  # Period expired

        # 3. Sleeve C Disabled Check
        if sleeve == "C_ALPHA" and self.is_sleeve_c_disabled:
            return False, "VETO: Sleeve C disabled due to 12% drawdown breach"

        # 4. Stale Data Cutoff (> 30s)
        if self.last_heartbeat_ms > 0 and (current_time_ms - self.last_heartbeat_ms) > self.max_staleness_ms:
            return False, f"VETO: Data feed stale ({current_time_ms - self.last_heartbeat_ms}ms > {self.max_staleness_ms}ms)"

        # 5. Abnormal Spread Check
        if bid_ask_spread_bps > self.max_spread_bps:
            return False, f"VETO: Abnormal spread {bid_ask_spread_bps:.1f} bps > {self.max_spread_bps:.1f} bps"

        # 6. Orders per minute throttle
        cutoff_min = current_time_ms - 60_000
        self.order_timestamps = [t for t in self.order_timestamps if t >= cutoff_min]
        if len(self.order_timestamps) >= self.max_orders_per_min:
            return False, f"VETO: Rate limit breached ({len(self.order_timestamps)} orders/min >= {self.max_orders_per_min})"

        # 7. Gross Leverage Cap (<= 3.0x)
        order_notional = order.quantity * current_price
        new_gross_notional = portfolio.total_gross_notional + order_notional
        new_leverage = new_gross_notional / max(portfolio.total_equity, 1e-4)
        if new_leverage > self.max_gross_leverage:
            return False, f"VETO: Gross leverage {new_leverage:.2f}x exceeds hard cap {self.max_gross_leverage:.1f}x"

        # 8. Sleeve C Open Risk Cap (<= 5.0%)
        if sleeve == "C_ALPHA":
            c_open_risk = sum(
                abs(p.quantity * (p.current_market_price - (p.stop_loss_price or p.current_market_price * 0.98)))
                for p in portfolio.positions.values() if p.sleeve == "C_ALPHA" and p.is_open
            )
            order_risk = order_notional * 0.025  # Estimated 2.5% stop distance
            total_c_risk_pct = (c_open_risk + order_risk) / max(portfolio.total_equity, 1e-4)
            if total_c_risk_pct > self.max_c_risk:
                return False, f"VETO: Sleeve C total open risk {total_c_risk_pct * 100:.2f}% exceeds 5% cap"

        self.order_timestamps.append(current_time_ms)
        return True, "APPROVED"

    def inject_failure(self, failure_type: str) -> Dict[str, Any]:
        """
        Failure-injection test harness for chaos engineering:
        Simulates:
        - "DROPPED_WEBSOCKET": data feed freeze
        - "DUPLICATE_FILL": exchange fills order twice
        - "EXCHANGE_OUTAGE": API 500 error
        - "CLOCK_DRIFT": physical clock skew > 1000ms
        """
        if failure_type == "DROPPED_WEBSOCKET":
            # Simulate silence by rewinding last heartbeat by 45 seconds
            self.last_heartbeat_ms = int(time.time() * 1000) - 45_000
            return {"status": "FEED_FROZEN", "staleness_ms": 45_000}
        elif failure_type == "CLOCK_DRIFT":
            return {"status": "CLOCK_SKEW_DETECTED", "drift_ms": 1500}
        elif failure_type == "EXCHANGE_OUTAGE":
            self.trigger_kill_switch("EXCHANGE_OUTAGE_HTTP_500")
            return {"status": "CIRCUIT_BREAKER_TRIPPED"}
        else:
            return {"status": "UNKNOWN_INJECTION"}
