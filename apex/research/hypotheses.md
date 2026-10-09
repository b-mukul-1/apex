# APEX Pre-Registered Signal Hypotheses

**Version Date:** 2026-10-09  
**Status:** Pre-registered before backtest execution.  
**Rule:** Every signal tested must have an entry here with economic hypothesis, horizon, inputs, and expected sign. All variants and parameters tested must be logged. Tuning on test sets is strictly prohibited.

---

## Sleeve A: Delta-Neutral Carry & Basis Yield
### Hypothesis
- **Economic Mechanism:** Crypto perpetual contracts trade at an annualized funding premium due to persistent structural retail demand for leveraged longs. By holding spot (or synthetic long futures) and shorting perpetual contracts with positive funding, or trading basis term structure dislocations, the system captures a steady positive carry while remaining delta-neutral.
- **Horizon:** 8 hours to multi-day (rebalanced on funding intervals).
- **Inputs:** Perpetual funding rate, index price, mark price, spot price, annualized basis.
- **Expected Sign:** Positive spread return when Funding Rate > Borrow Cost + Transaction Fee Amortization.
- **Sizing & Capital:** 40% - 50% capital allocation, 1-2x leverage maximum.

---

## Sleeve B: Multi-Asset Trend Following
### Hypothesis
- **Economic Mechanism:** Crypto markets exhibit persistent medium-to-long term trends driven by macroeconomic liquidity cycles, institutional adoption waves, and reflexive feedback loops. Trend following with volatility targeting captures fat-tailed right-side moves while cutting losing trends early.
- **Horizon:** 4 hours to 1 day bars (holding period 2 days to 3 weeks).
- **Inputs:** 20-day / 50-day / 200-day EMA, ATR(14) for volatility targeting, Donchian channels, rolling breakout highs/lows.
- **Expected Sign:** Positive payoff on breakouts in direction of trend; cut at 1.5 - 2.0 ATR trailing stops.
- **Sizing & Capital:** 20% - 30% capital allocation, $\le 2$x leverage maximum.

---

## Sleeve C: Multi-Signal Alpha (Convex Upside Ensemble)

### Signal S01: Volatility Compression Breakout (Squeeze + Volume Surge)
- **Hypothesis:** When volatility compresses inside historical bands (Bollinger Bands contract inside Keltner Channels), liquidity providers pull back risk. A breakout accompanied by a 2x+ volume expansion indicates directional institutional aggression and momentum continuation.
- **Horizon:** 15m - 4h bars (holding 1h to 24h).
- **Inputs:** BB(20, 2), Keltner(20, 1.5), Volume 20-period Z-score, True Range.
- **Expected Sign:** Directional continuation (+1 for upward squeeze breakout, -1 for downward squeeze breakout).

### Signal S02: Cross-Sectional Momentum (BTC-Beta Hedged)
- **Hypothesis:** Altcoins that outperform the cross-sectional median over 1-7 days continue to exhibit relative strength due to capital rotation into leading ecosystems. Hedging the market beta against BTC isolates pure idiosyncratic momentum alpha.
- **Horizon:** 1d rebalanced, holding 1-5 days.
- **Inputs:** 3-day / 7-day relative returns, 30-day rolling beta to BTC, cross-sectional ranking.
- **Expected Sign:** Long top quintile, short bottom quintile (or beta hedge via short BTC perp).

### Signal S03: Funding & Open Interest Crowding / Liquidation Cascade Detection
- **Hypothesis:** Extreme annualized funding (>+50% or <-30%) combined with spiking open interest signifies over-leveraged retail positioning vulnerable to liquidity cascades. A sharp counter-trend price move triggers cascading margin calls, producing a high-velocity squeeze in the opposite direction.
- **Horizon:** 5m - 1h bars (holding 30m to 6h).
- **Inputs:** 8h funding rate, open interest 24h change, liquidation volume delta, basis deviation.
- **Expected Sign:** Mean-reversion / squeeze counter to crowded funding (+1 when crowded shorts get liquidated; -1 when crowded longs get liquidated).

### Signal S04: L2 Order-Flow Imbalance & Book Pressure
- **Hypothesis:** Significant depth imbalance in top 10 levels of the L2 order book combined with aggressive trade flow (buyer vs seller taker volume delta) indicates short-term order book sweeping that precedes immediate price drift over the next 1-15 minutes.
- **Horizon:** 1m - 15m.
- **Inputs:** Order book depth ratio ($Depth_{bid} - Depth_{ask}) / (Depth_{bid} + Depth_{ask}$), cumulative volume delta (CVD), micro-price.
- **Expected Sign:** Directional (+1 when bid imbalance and positive CVD, -1 when ask imbalance and negative CVD).

### Signal S05: Liquidity Shock Mean Reversion
- **Hypothesis:** Violent intraday price spikes caused by isolated market orders clearing thin books (flash spikes) result in transient price dislocations that rapidly revert to the pre-shock VWAP as liquidity replenishes.
- **Horizon:** 5m - 30m.
- **Inputs:** Rolling 30-minute VWAP, 3-sigma price deviation, sudden volume spike, subsequent spread normalization.
- **Expected Sign:** Contrarian reversion (-1 on extreme upside flash spike, +1 on extreme downside flash spike).

### Signal S06: BTC Lead / Altcoin Lag
- **Hypothesis:** High-liquidity price discovery occurs first in BTC/ETH perps before propagating to secondary altcoins. When BTC breaks a local key level with significant velocity, lagging altcoins follow with a 2 to 15 minute delay.
- **Horizon:** 5m - 15m.
- **Inputs:** BTC 5-minute return, Altcoin 5-minute return, cross-correlation latency profile.
- **Expected Sign:** Directional in direction of BTC shock (+1 if BTC popped and Altcoin has not yet moved).
- **Caveat:** High fee sensitivity; must only execute when expected lag move > 2x round-trip trading cost.

### Signal S07: Perpetual / Basis Term-Structure Dislocations
- **Hypothesis:** Calendar futures basis or spot-perp spreads occasionally widen beyond theoretical limits during intense market rallies or selloffs due to margin constraints. Once the immediate pressure abates, the basis mean-reverts to fair value.
- **Horizon:** 1h - 24h.
- **Inputs:** Spot price, perp price, 1-month / 3-month futures price, days to expiry.
- **Expected Sign:** Convergence of basis to carry arbitrage bounds.

### Signal S08: VWAP & Volume Profile Deviation
- **Hypothesis:** Intraday auctions rotate around the Volume-Weighted Average Price (VWAP) and Value Area High/Low (VAH/VAL). Deviation beyond 2 standard deviations in balanced regimes provides statistical mean-reversion, while acceptance outside the Value Area signals trend day expansion.
- **Horizon:** 15m - 4h.
- **Inputs:** Intraday anchored VWAP, 1st and 2nd standard deviation bands, Volume Profile Value Area (70% volume range).
- **Expected Sign:** Mean-reversion within range regime; breakout continuation within trend regime.

### Signal S09: Event & Unlock Momentum
- **Hypothesis:** Pre-announced token unlocks or protocol emissions introduce predictable structural supply overhangs. Shorting or avoiding longs 24-48 hours ahead of cliff unlocks captures systematic downward price drift.
- **Horizon:** 1d - 3d.
- **Inputs:** Token unlock schedule (cliff % of circulating supply), 30-day average volume, funding rate.
- **Expected Sign:** Directional short (-1) when cliff unlock > 2% of circulating market supply.

### Signal S10: Cross-Exchange Price Dislocations
- **Hypothesis:** Structural latency or localized liquidity shocks between major exchanges (e.g. Binance vs OKX vs Bybit) cause transient price dislocations of 5-20 bps.
- **Horizon:** 1m - 5m.
- **Inputs:** Top of book bid/ask from Venue A and Venue B.
- **Expected Sign:** Arbitrage convergence. Must strictly clear maker-taker fees and exchange latency boundaries.

---

## Control Group (Placebo / Benchmark Signals)
### Signal S00: Classic Candlestick & Geometric Chart Patterns
- **Hypothesis:** Standard textbook chart patterns (e.g. Doji, Hammer, Head & Shoulders, Bull Flag) are publicly known, heavily front-run, and lack independent predictive statistical edge after realistic trading costs (spread, fees, slippage).
- **Horizon:** 15m - 1h.
- **Inputs:** 3-bar candlestick morphology (Open, High, Low, Close).
- **Expected Sign / Result:** **Zero or negative net edge** after 2x cost model. Any backtest showing statistically significant positive edge on raw candlestick patterns without order flow or regime conditioning must be treated as overfitted.
