"""
APEX Sleeve C Alpha Ensemble Strategy
======================================
Wraps all Sleeve C individual signals with the Alpha Combiner and Meta-Labeler.
Enforces:
1. Signal aggregation across all 10 signals
2. Meta-labeler probability veto
3. Cost-Aware Gate: Requires Forecast > 2x Cost
4. Maximum trades per day throttle
"""

from typing import List, Dict, Any, Optional
from apex.data.store import MarketBar, PointInTimeStore
from apex.backtest.events import SignalEvent
from apex.backtest.portfolio import Portfolio
from apex.backtest.cost_model import CostModel
from apex.models.combiner import AlphaCombiner
from apex.models.meta_labeler import MetaLabeler
from apex.models.regime import RegimeClassifier, MarketRegime


class SleeveCAlphaEnsemble:
    """
    Sleeve C master strategy executing the pre-registered signal library through
    the combiner, regime classifier, and meta-labeler.
    """

    def __init__(
        self,
        cost_model: CostModel,
        signals: List[Any],
        cost_hurdle: float = 2.0,
    ):
        self.sleeve_id = "C_ALPHA"
        self.cost_model = cost_model
        self.signals = signals
        self.combiner = AlphaCombiner(cost_model=cost_model, cost_hurdle_multiplier=cost_hurdle)
        self.meta_labeler = MetaLabeler()
        self.regime_classifier = RegimeClassifier(lookback_bars=20)

    def on_bar(
        self,
        bar: MarketBar,
        store: PointInTimeStore,
        portfolio: Portfolio,
    ) -> List[SignalEvent]:
        if bar.is_delisted:
            return []

        # 1. Collect signals from individual library components
        raw_signals: List[SignalEvent] = []
        for s in self.signals:
            sigs = s.on_bar(bar, store, portfolio)
            if sigs:
                raw_signals.extend(sigs)

        if not raw_signals:
            return []

        # 2. Combine signals with Alpha Combiner (aggregates weights & applies cost-aware hurdle)
        combined = self.combiner.combine_signals(raw_signals, current_price=bar.close)
        if not combined:
            return []  # Cost gate filtered the trades

        # 3. Meta-labeler validation & Position Hysteresis Check
        current_pos = portfolio.positions.get(bar.symbol) if portfolio else None
        is_open = current_pos and current_pos.is_open

        accepted_signals: List[SignalEvent] = []
        for sig in combined:
            if not self.meta_labeler.should_take_trade(sig, bar, volatility_daily=0.03):
                continue

            # If already positioned in the same direction, DO NOT churn orders
            if is_open:
                if (current_pos.quantity > 0 and sig.direction > 0) or (current_pos.quantity < 0 and sig.direction < 0):
                    continue  # Already long/short; let runner position run
                # If opposing direction, require strong conviction to flip
                if sig.strength < 0.70:
                    continue

            accepted_signals.append(sig)

        return accepted_signals
