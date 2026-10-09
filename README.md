# APEX: Adaptive Multi-Signal Crypto Trading System

APEX is an institutional-grade, multi-sleeve quantitative trading system built with **Python 3.12** and **NautilusTrader 1.231.0**, optimized for Binance USDS-M Perpetuals.

---

## 🏛️ Architecture Overview

The system operates across three orthogonal strategy sleeves coordinated through an independent **Risk Sentinel**:

1. **Sleeve A (45% Allocation) - Delta-Neutral Funding Carry:**
   - Harvests positive perpetual funding premiums while eliminating directional market beta.
   - Enforces 8% annual hurdle rate and basis tracking error bounds.

2. **Sleeve B (30% Allocation) - Multi-Timeframe Trend Following:**
   - Captures medium-term directional momentum via ATR channels and dynamic trailing stops.
   - Convex right-tail payoff structure with volatility-targeted sizing.

3. **Sleeve C (25% Allocation) - Multi-Signal Alpha Ensemble:**
   - 10 orthogonal structural market signals: Volatility Squeeze, Cross-Sectional Momentum, Funding Crowding, Order Book Imbalance, Liquidity Shock Reversion, BTC Lead-Lag, Term Structure Basis, VWAP Deviation, Event Momentum, and Cross-Exchange Dislocation.
   - Filtered through a Regime Classifier, Meta-Labeling probability filter, and Cost-Aware Gate (Forecast > 2x Cost).

4. **Risk Sentinel (Highest Architectural Priority):**
   - Independent risk daemon with veto power over all orders.
   - Gross leverage hard cap: **3.0x**.
   - 24-hour daily loss limit: **-3.0%**.
   - Drawdown Ladder: Halve sizing at -8%, disable Sleeve C at -12%, full halt at -18%.
   - Stale quote cutoffs (<30s) and abnormal spread filters (<50 bps).
   - Remote Emergency Kill Switch.

---

## 📊 Live Web Dashboard (Vercel Ready)

Located in [`web/`](./web): A Next.js 16 App Router interface featuring:
- Cyber-fintech dark theme with glassmorphic cards and glowing status indicators.
- Live Account Equity & 24h P&L metrics.
- Interactive SVG equity progression chart.
- Real-time active position matrix and recent trades ledger.
- 8 Risk Sentinel indicators.
- Remote emergency kill switch with confirmation PIN.

---

## 🚀 Running 24/7 in the Cloud

APEX separates the **24/7 Execution Engine** from the **Frontend Web Dashboard**:

1. **Deploy Frontend to Vercel:**
   ```bash
   cd web
   npx vercel
   ```
2. **Deploy 24/7 Engine to Railway or Render:**
   - Connect this GitHub repository.
   - Deploy using the included [`Dockerfile`](./Dockerfile) or [`railway.json`](./railway.json).
   - Set environment variables:
     ```env
     BINANCE_TESTNET=true
     BINANCE_API_KEY=your_key
     BINANCE_API_SECRET=your_secret
     VERCEL_WEBHOOK_URL=https://your-app.vercel.app/api/telemetry
     ```
3. Power down your laptop—the cloud worker executes 24/7 and streams live metrics to your Vercel URL.

---

## 🧪 Testing & Empirical Validation

Tested against 100% real historical Binance perpetual data (2020-2026, 2,200 continuous daily candles per pair across BTC, ETH, SOL, BNB, DOGE, XRP):

```bash
# Activate virtual environment
source .venv/bin/activate

# Run full test suite (23 passing tests)
pytest tests/ -v

# Run real historical out-of-sample backtest
python apex/reports/run_real_backtest_and_report.py
```
