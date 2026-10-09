"""
APEX Meta-Labeler (Lopez de Prado Framework)
=============================================
Secondary model that decides whether to execute or veto a primary trading signal.
Features:
- Volatility regime (ATR / standard deviation)
- Funding rate divergence
- Signal strength & historical hit rate
- Market regime classification
"""

from typing import List, Optional
import numpy as np
from sklearn.linear_model import LogisticRegression
from apex.backtest.events import SignalEvent
from apex.data.store import MarketBar


class MetaLabeler:
    """
    Evaluates primary signals and computes execution probability.
    Vetoes trades if P(Success) < threshold (default 0.55).
    """

    def __init__(self, confidence_threshold: float = 0.55):
        self.threshold = confidence_threshold
        self.classifier = LogisticRegression()
        self.is_fitted = False

    def fit_meta_model(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fits binary logistic meta-classifier on in-sample historical signals."""
        if len(X) < 40:
            return
        self.classifier.fit(X, y)
        self.is_fitted = True

    def should_take_trade(
        self,
        signal: SignalEvent,
        bar: MarketBar,
        volatility_daily: float,
    ) -> bool:
        """
        Determines whether to take the primary signal or pass.
        If not fitted, applies heuristic gate (filters during extreme high vol or stale edge).
        """
        if not self.is_fitted:
            # Rule-based fallback: filter out low-strength signals during extreme volatility spikes
            if volatility_daily > 0.08 and signal.strength < 0.70:
                return False
            # Check edge hurdle
            if signal.expected_edge_bps < 15.0:
                return False
            return True

        # Extract feature vector
        features = np.array([[
            signal.strength,
            signal.expected_edge_bps,
            volatility_daily,
            bar.funding_rate_8h * 10_000.0,
        ]])

        prob_win = float(self.classifier.predict_proba(features)[0, 1])
        return prob_win >= self.threshold
