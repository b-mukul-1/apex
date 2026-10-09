"""
APEX Cost Model & Execution Friction Simulator
==============================================
Implements institutional-grade friction modeling for crypto perpetuals and spot:
1. Tiered Maker / Taker fee schedules
2. Half-spread crosses
3. Size-dependent market impact (square-root / Kyle-Almgren-Chriss model)
4. Directional funding payments / receipts on perpetuals
5. Spot borrow / financing rates
6. Simulated network & retail execution latency (100 - 300 ms)
7. Strict 2x Cost Stress Testing Gate
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class FeeTier:
    maker_rate: float  # e.g. 0.0002 (0.02% = 2 bps)
    taker_rate: float  # e.g. 0.0005 (0.05% = 5 bps)
    name: str = "Standard Retail Tier 1"


@dataclass
class ExecutionResult:
    intended_price: float
    effective_fill_price: float
    order_size: float
    gross_notional: float
    net_notional: float
    fee_paid: float
    spread_cost: float
    slippage_cost: float
    total_friction: float
    latency_delay_ms: float
    is_maker: bool


class CostModel:
    """
    Simulates all frictions encountered in live crypto trading.
    Mandatory Gate: All strategies must remain net profitable when cost_multiplier=2.0.
    """

    def __init__(
        self,
        fee_tier: Optional[FeeTier] = None,
        base_half_spread_bps: float = 2.0,       # 2 bps default for liquid perps
        impact_coefficient: float = 0.10,        # Kyle's lambda / square-root impact constant
        latency_ms_min: float = 100.0,           # 100ms retail baseline
        latency_ms_max: float = 300.0,           # 300ms retail upper bound
        annual_borrow_rate: float = 0.08,        # 8% annual borrow cost for spot margin
        cost_multiplier: float = 1.0,            # 1.0 for normal, 2.0 for Phase Gate tests
    ):
        self.fee_tier = fee_tier or FeeTier(maker_rate=0.0002, taker_rate=0.0005)
        self.base_half_spread_bps = base_half_spread_bps
        self.impact_coefficient = impact_coefficient
        self.latency_ms_min = latency_ms_min
        self.latency_ms_max = latency_ms_max
        self.annual_borrow_rate = annual_borrow_rate
        self.cost_multiplier = cost_multiplier

    def get_stress_model(self, multiplier: float = 2.0) -> "CostModel":
        """Returns a 2x cost model for gate validation testing."""
        return CostModel(
            fee_tier=FeeTier(
                maker_rate=self.fee_tier.maker_rate * multiplier,
                taker_rate=self.fee_tier.taker_rate * multiplier,
                name=f"{self.fee_tier.name} (x{multiplier} Stress)",
            ),
            base_half_spread_bps=self.base_half_spread_bps * multiplier,
            impact_coefficient=self.impact_coefficient * multiplier,
            latency_ms_min=self.latency_ms_min * multiplier,
            latency_ms_max=self.latency_ms_max * multiplier,
            annual_borrow_rate=self.annual_borrow_rate * multiplier,
            cost_multiplier=multiplier,
        )

    def sample_latency_ms(self, seed: Optional[int] = None) -> float:
        """Samples realistic retail WebSocket/REST network + matching engine latency."""
        rng = np.random.default_rng(seed)
        # Uniform or right-skewed lognormal distribution between min and max
        return float(rng.uniform(self.latency_ms_min, self.latency_ms_max))

    def estimate_market_impact_bps(
        self,
        order_notional: float,
        daily_volume_usd: float = 50_000_000.0,
        volatility_daily: float = 0.03,
    ) -> float:
        """
        Calculates non-linear square-root market impact:
        Impact = gamma * sigma * sqrt(OrderSize / DailyVolume)
        """
        participation_rate = max(order_notional / max(daily_volume_usd, 1e-6), 0.0)
        # Impact in percentage
        impact_pct = self.impact_coefficient * volatility_daily * np.sqrt(participation_rate)
        # Convert to bps and scale by cost multiplier
        impact_bps = impact_pct * 10_000.0 * self.cost_multiplier
        return max(float(impact_bps), 0.0)

    def calculate_funding_payment(
        self,
        position_notional: float,
        funding_rate_8h: float,
        is_long: bool,
    ) -> float:
        """
        Calculates 8-hour perpetual funding payment:
        - If funding_rate > 0: Long pays Short.
        - If funding_rate < 0: Short pays Long.
        Returns net cost to the trader (positive = expense, negative = yield received).
        """
        # Cash flow: long pays when funding > 0, so cost is +notional * rate
        # short pays when funding < 0, so cost is -notional * (-rate) = +notional * rate... wait:
        # Long payout: Long pays (funding_rate * notional).
        # Short payout: Short receives (funding_rate * notional), which is negative cost (income).
        cost = (position_notional * funding_rate_8h) if is_long else (-position_notional * funding_rate_8h)
        return float(cost)

    def simulate_execution(
        self,
        side: str,  # "BUY" or "SELL"
        price: float,
        size: float,
        is_maker: bool = False,
        daily_volume_usd: float = 50_000_000.0,
        volatility_daily: float = 0.03,
        seed: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Simulates fill price, fees, spread, and slippage for an order.
        """
        gross_notional = price * size
        direction = 1.0 if side.upper() == "BUY" else -1.0

        # 1. Spread cost
        # If taker, cross the spread: pay half-spread
        # If maker, passive limit order at or inside book: 0 spread penalty
        spread_bps = (self.base_half_spread_bps * self.cost_multiplier) if not is_maker else 0.0
        spread_cost_usd = gross_notional * (spread_bps / 10_000.0)

        # 2. Slippage / Market Impact
        # Taker orders incur non-linear impact; maker orders incur adverse selection
        slippage_bps = self.estimate_market_impact_bps(gross_notional, daily_volume_usd, volatility_daily)
        if is_maker:
            # Maker adverse selection is approximately 25-50% of taker impact
            slippage_bps *= 0.35
        slippage_cost_usd = gross_notional * (slippage_bps / 10_000.0)

        # Total price adjustment
        total_price_slippage = price * ((spread_bps + slippage_bps) / 10_000.0)
        effective_fill_price = price + (direction * total_price_slippage)

        # 3. Exchange Fee
        fee_rate = (self.fee_tier.maker_rate if is_maker else self.fee_tier.taker_rate) * self.cost_multiplier
        fee_paid = (effective_fill_price * size) * fee_rate

        total_friction = spread_cost_usd + slippage_cost_usd + fee_paid
        net_notional = (effective_fill_price * size) + (fee_paid if side.upper() == "BUY" else -fee_paid)
        latency_delay = self.sample_latency_ms(seed)

        return ExecutionResult(
            intended_price=price,
            effective_fill_price=effective_fill_price,
            order_size=size,
            gross_notional=gross_notional,
            net_notional=net_notional,
            fee_paid=fee_paid,
            spread_cost=spread_cost_usd,
            slippage_cost=slippage_cost_usd,
            total_friction=total_friction,
            latency_delay_ms=latency_delay,
            is_maker=is_maker,
        )
