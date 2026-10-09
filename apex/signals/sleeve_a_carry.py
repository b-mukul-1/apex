"""
APEX Sleeve A: Delta-Neutral Perpetual Carry & Basis Yield
==========================================================
Hypothesis:
    Perpetual contracts consistently trade at an annualized funding premium to spot
    due to persistent retail long bias and leverage demand. By systematically shorting
    high-funding perpetuals while holding spot (or synthetic delta-neutral long), the
    portfolio captures pure carry yield while eliminating directional market beta.

Horizon:
    8 hours to multi-week (rebalanced as funding regimes evolve).

Inputs:
    - 8h Funding Rate
    - Mark Price vs Index Price basis
    - Spot borrow interest rate (annualized ~8%)
    - Transaction fee amortization hurdle

Expected Sign:
    Positive yield when Funding Rate > Hurdle Rate.
    Flat / exit when Funding Rate turns negative or falls below fee hurdle.

Capital & Leverage Constraints:
    - Capital allocation: 40% - 50%
    - Max leverage: 1.0x - 2.0x
"""

from typing import List, Dict, Optional
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio


class SleeveACarryStrategy:
    """
    Automated carry harvester with strict cost-gate enforcement.
    """

    def __init__(
        self,
        min_annualized_funding_hurdle: float = 0.08,  # 8% annualized minimum
        funding_exit_threshold: float = 0.00,        # Exit if funding <= 0%
        target_allocation: float = 0.45,             # 45% of total portfolio
    ):
        self.sleeve_id = "A_CARRY"
        self.min_annualized_hurdle = min_annualized_funding_hurdle
        self.funding_exit_threshold = funding_exit_threshold
        self.target_allocation = target_allocation

        # Convert annualized hurdle to 8-hour hurdle: hurdle_8h = hurdle_annual / (365 * 3)
        self.hurdle_8h = self.min_annualized_hurdle / (365.0 * 3.0)

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        """
        Evaluates funding rate and mark basis at bar close.
        Emits delta-neutral carry signals.
        """
        # Exclude delisted tokens
        if bar.is_delisted:
            return []

        # Only operate on liquid benchmark perps
        if not (bar.symbol.startswith("BTC") or bar.symbol.startswith("ETH")):
            return []

        signals: List[SignalEvent] = []
        funding = bar.funding_rate_8h

        current_pos = portfolio.positions.get(bar.symbol)
        is_already_short = current_pos and current_pos.is_open and current_pos.quantity < 0 and current_pos.sleeve == self.sleeve_id

        # In delta-neutral carry, if funding > hurdle, we short perp (and hold spot)
        # In single perp representation with funding cash flow, Short Perp earns funding when funding > 0
        if funding >= self.hurdle_8h:
            if not is_already_short:
                # Enter carry harvest
                signals.append(SignalEvent(
                    symbol=bar.symbol,
                    timestamp_ms=bar.timestamp_ms,
                    sleeve=self.sleeve_id,
                    signal_id="CARRY_HARVEST",
                    direction=-1.0,  # Short perp to capture positive funding
                    strength=0.5,    # Conservative sizing (1x delta-neutral)
                    stop_loss_price=bar.close * 1.50, # Hedged by spot; disaster stop only
                    expected_edge_bps=funding * 10_000.0,
                ))
        elif funding <= self.funding_exit_threshold:
            if is_already_short:
                # Funding collapsed or flipped negative: Flatten to avoid paying carry
                signals.append(SignalEvent(
                    symbol=bar.symbol,
                    timestamp_ms=bar.timestamp_ms,
                    sleeve=self.sleeve_id,
                    signal_id="CARRY_FLATTEN",
                    direction=0.0,  # Flat
                    strength=0.0,
                    expected_edge_bps=0.0,
                ))

        return signals
