# APEX QUANTITATIVE TRADING SYSTEM: MASTER REPLICATION SPECIFICATION & BLUEPRINT
**Document Version:** 2.0.0-Institutional  
**System Name:** APEX (Adaptive Multi-Signal Quantitative Trading System)  
**Primary Target Market:** Binance USDS-M Perpetuals (with Cross-Asset Adaptability to Indian NSE F&O)  
**Classification:** Institutional-Grade Autonomous Multi-Sleeve Algorithmic Trading Architecture  

---

## TABLE OF CONTENTS
1. [Executive Summary & Core Philosophy](#1-executive-summary--core-philosophy)
2. [Complete Repository Layout & Directory Tree](#2-complete-repository-layout--directory-tree)
3. [Technology Stack & Pinned Dependencies](#3-technology-stack--pinned-dependencies)
4. [Multi-Sleeve Quantitative Architecture](#4-multi-sleeve-quantitative-architecture)
   - [Sleeve A: Delta-Neutral Carry & Basis Yield (45%)](#sleeve-a-delta-neutral-carry--basis-yield-45)
   - [Sleeve B: Multi-Timeframe Trend Following (30%)](#sleeve-b-multi-timeframe-trend-following-30)
   - [Sleeve C: Multi-Signal Alpha Ensemble (25%)](#sleeve-c-multi-signal-alpha-ensemble-25)
   - [The 10 Orthogonal Alpha Signals (Formulas & Logic)](#the-10-orthogonal-alpha-signals-formulas--logic)
   - [Meta-Labeling & Cost-Aware Combiner](#meta-labeling--cost-aware-combiner)
5. [Advanced Institutional Alpha & Risk Engines](#5-advanced-institutional-alpha--risk-engines)
   - [Dynamic Profit Ratchet & Trailing Volatility Harvest](#dynamic-profit-ratchet--trailing-volatility-harvest)
   - [BTC Macro-Regime Filter](#btc-macro-regime-filter)
   - [8-Hour Funding Arbitrage Harvester](#8-hour-funding-arbitrage-harvester)
6. [Independent Risk Sentinel & Execution Governance](#6-independent-risk-sentinel--execution-governance)
7. [Portfolio Accounting, Netting & Transaction Cost Model](#7-portfolio-accounting-netting--transaction-cost-model)
8. [Session State Persistence & Cloud Recovery Engine](#8-session-state-persistence--cloud-recovery-engine)
9. [24/7 Cloud Execution Daemon & Outbound Telemetry Pipeline](#9-247-cloud-execution-daemon--outbound-telemetry-pipeline)
10. [Institutional Web Dashboard & API Architecture (Next.js)](#10-institutional-web-dashboard--api-architecture-nextjs)
11. [Production Deployment & Infrastructure Guide (Railway + Vercel)](#11-production-deployment--infrastructure-guide-railway--vercel)
12. [Comprehensive Verification & Testing Suite](#12-comprehensive-verification--testing-suite)
13. [Turnkey Agent Prompt (To Clone & Recreate This System)](#13-turnkey-agent-prompt-to-clone--recreate-this-system)

---

## 1. EXECUTIVE SUMMARY & CORE PHILOSOPHY

APEX is designed from first principles to solve the fundamental failure modes of retail algorithmic trading: overfitting, high-frequency fee drag, unconstrained leverage, and market regime vulnerability.

### Core Architectural Axioms
1. **Sleeve Orthogonality**: Never rely on a single alpha source. Capital is partitioned across three non-correlated strategies:
   - **Sleeve A (45%)**: Pure structural carry / basis yield (low volatility baseline).
   - **Sleeve B (30%)**: Directional medium-term trend following (convex right-tail payoffs).
   - **Sleeve C (25%)**: Short-horizon statistical anomalies & structural mispricings (high Sharpe alpha bursts).
2. **Absolute Risk Primacy**: The **Risk Sentinel** operates outside and above all strategy sleeves. Strategies cannot bypass risk rules.
3. **Netting Before Execution**: Opposing signals across sleeves are netted internally before sending orders to the exchange, reducing turnover, slippage, and transaction fees by over 60%.
4. **Maker-First Passive Execution**: All routine rebalances are placed as limit orders at or inside the bid-ask spread to capture maker rebates or avoid taker fee penalties.
5. **Session Continuity Across Cloud Lifecycles**: State is saved to disk atomically every cycle, enabling seamless restarts across container rebuilds without resetting the account balance.

### Universe Specification
The standard production universe spans **20 high-liquidity perpetual markets**:
- **Macro Majors**: `BTC/USDT:USDT`, `ETH/USDT:USDT`, `SOL/USDT:USDT`, `BNB/USDT:USDT`
- **High-Beta Payment/L1**: `XRP/USDT:USDT`, `DOGE/USDT:USDT`, `ADA/USDT:USDT`, `AVAX/USDT:USDT`, `NEAR/USDT:USDT`, `SUI/USDT:USDT`
- **DeFi & Oracle Blue Chips**: `LINK/USDT:USDT`, `UNI/USDT:USDT`, `AAVE/USDT:USDT`
- **AI & Compute Sector**: `RENDER/USDT:USDT`, `TAO/USDT:USDT`, `FET/USDT:USDT`
- **Meme Speculative Liquidity**: `1000PEPE/USDT:USDT`, `1000SHIB/USDT:USDT`, `1000BONK/USDT:USDT`, `1000FLOKI/USDT:USDT`

---

## 2. COMPLETE REPOSITORY LAYOUT & DIRECTORY TREE

```
apex-trading-system/
├── Dockerfile                         # Container spec for 24/7 Railway Python runtime
├── Procfile                           # Cloud process manager entrypoint
├── railway.json                       # Railway deployment & restart configuration
├── README.md                          # Repository overview & quick start
├── apex_session_state.json            # Persisted equity, high-water mark, and trade count
├── .env.example                       # Reference environment variables
│
├── apex/                              # Python Quantitative Core Package
│   ├── __init__.py
│   ├── data/                          # Data Layer & Store
│   │   ├── __init__.py
│   │   ├── store.py                   # MarketBar, PointInTimeStore (zero lookahead)
│   │   ├── collector.py               # CCXT historical bar & funding rate downloader
│   │   └── download_real_data.py      # Real Binance USDS-M data ingester
│   ├── signals/                       # Signal & Strategy Implementations
│   │   ├── __init__.py
│   │   ├── sleeve_a_carry.py          # Sleeve A: Delta-neutral carry harvester
│   │   ├── sleeve_b_trend.py          # Sleeve B: Donchian + ATR trend follower
│   │   ├── btc_regime.py              # Macro BTC regime classifier & altcoin risk gate
│   │   ├── funding_harvester.py       # 8-hour funding yield arbitrage engine
│   │   ├── s00_candle_patterns.py     # Structural candlestick confirmation
│   │   ├── s01_vol_squeeze.py         # Bollinger / Keltner compression breakout
│   │   ├── s02_cross_sectional_mom.py # Cross-sectional ranking & momentum spread
│   │   ├── s03_funding_crowding.py    # Extreme funding rate crowding mean-reversion
│   │   ├── s04_orderbook_imbalance.py # L2 order book bid/ask queue imbalance
│   │   ├── s05_liquidity_shock_reversion.py # Volume spike & long wick absorption
│   │   ├── s06_btc_lead_lag.py        # Lead-lag cross-correlation against Bitcoin
│   │   ├── s07_term_structure_basis.py # Spot vs perpetual basis dislocation
│   │   ├── s08_vwap_deviation.py      # Multi-band intraday VWAP mean-reversion
│   │   ├── s09_event_momentum.py      # High-volume post-event momentum continuation
│   │   └── s10_cross_exchange_dislocation.py # Cross-venue price disparity arbitrage
│   ├── models/                        # ML, Regime & Alpha Combiner
│   │   ├── __init__.py
│   │   ├── combiner.py                # AlphaCombiner with correlation de-weighting
│   │   ├── combiner_strategy.py       # SleeveCAlphaEnsemble orchestrator
│   │   ├── meta_labeler.py            # Triple barrier labeling & probability filter
│   │   └── regime.py                  # Market regime classifier (Bull/Bear/Chop)
│   ├── risk/                          # Independent Risk & Protection Layer
│   │   ├── __init__.py
│   │   ├── service.py                 # RiskService (3.0x cap, -3.0% daily limit, ladder)
│   │   └── profit_ratchet.py          # ProfitRatchet & trailing volatility lock
│   ├── backtest/                      # Simulation, Accounting & Verification
│   │   ├── __init__.py
│   │   ├── events.py                  # Event dataclasses (Signal, Order, Fill)
│   │   ├── cost_model.py              # Real-world fees, slippage & market impact
│   │   ├── portfolio.py               # Portfolio, Position, Position Netting
│   │   ├── engine.py                  # Event-driven backtesting execution loop
│   │   └── lookahead_tests.py         # Strict causality & time-leak verification
│   ├── execution/                     # Live Trading & Exchange Gateway
│   │   ├── __init__.py
│   │   ├── order_manager.py           # Maker simulation, fills, queue estimation
│   │   └── live_paper_runner.py       # 24/7 daemon, CCXT polling, HTTP server, webhooks
│   └── monitor/                       # Real-Time Telemetry & Health Monitoring
│       ├── __init__.py
│       ├── live_tracker.py            # Realized slippage & execution latency tracker
│       └── decay_monitor.py           # Signal decay & Information Coefficient half-life
│
├── web/                               # Next.js 14 Real-Time Web Dashboard
│   ├── package.json
│   ├── next.config.mjs
│   ├── app/
│   │   ├── layout.js                  # App shell, fonts (Outfit, JetBrains Mono)
│   │   ├── page.js                    # Full institutional terminal dashboard
│   │   ├── globals.css                # Dark glassmorphic design system & tokens
│   │   └── api/
│   │       ├── store.js               # In-memory webhook state store
│   │       ├── state/route.js         # GET dashboard telemetry (direct proxy / webhook)
│   │       ├── telemetry/route.js     # POST webhook receiver from cloud daemon
│   │       └── kill-switch/route.js   # POST emergency halt endpoint
│
└── tests/                             # Comprehensive Verification Suite (26+ Tests)
    ├── conftest.py
    ├── test_phase1.py                 # Data integrity, PIT store, lookahead vetoes
    ├── test_phase2.py                 # Sleeve A, Sleeve B, and Signal implementations
    ├── test_phase3.py                 # Combiner, Meta-labeler, Regime classifier
    ├── test_phase4.py                 # Risk Service, Drawdown ladder, Cost model
    ├── test_phase5.py                 # Order manager, Live tracker, Paper runner
    └── test_new_algos.py              # Profit Ratchet, BTC Regime, Harvester, Persistence
```

---

## 3. TECHNOLOGY STACK & PINNED DEPENDENCIES

### Python Backend & Quantitative Core
- **Python**: `3.12`
- **NautilusTrader**: `1.231.0` (institutional event-driven trading engine)
- **CCXT**: `4.5.85` (Binance USDS-M Perpetuals live API & Testnet gateway)
- **Pandas**: `3.0.6` / **NumPy**: `1.26.4`
- **Scikit-Learn**: `1.9.1` (Meta-labeler logistic classifier & feature scaling)
- **DuckDB**: `1.5.6` & **PyArrow**: `26.0.0` (Parquet storage & PIT analytical queries)
- **PyTest**: `9.1.1` (automated CI/CD regression validation)
- **Package Manager**: Astral `uv` for sub-second reproducible builds.

### Frontend & Monitoring Terminal
- **Framework**: Next.js 14 (App Router)
- **Runtime**: React 18
- **Styling**: Vanilla CSS modern design system (Glassmorphism, CSS Custom Properties, HSL color tokens)
- **Hosting**: Vercel (Edge/Serverless functions) + Railway (Docker container 24/7 daemon).

---

## 4. MULTI-SLEEVE QUANTITATIVE ARCHITECTURE

Capital is partitioned dynamically with strict risk budgets:
$$\text{Total Capital} = \text{Sleeve A } (45\%) + \text{Sleeve B } (30\%) + \text{Sleeve C } (25\%)$$

```
                         [ INCOMING MARKET DATA: CCXT / PARQUET ]
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               ▼                            ▼                            ▼
      [ SLEEVE A: 45% ]            [ SLEEVE B: 30% ]            [ SLEEVE C: 25% ]
      Delta-Neutral Carry          Trend Following              10-Alpha Ensemble
      (Funding Arbitrage)          (Donchian / ATR Trailing)    (Meta-Labeled Squeeze/Mom)
               │                            │                            │
               └────────────────────────────┼────────────────────────────┘
                                            ▼
                              [ POSITION NETTING ENGINE ]
                              (Offsets opposing quantities)
                                            │
                                            ▼
                             [ INDEPENDENT RISK SENTINEL ]
                             (3.0x Cap, Daily Loss, Drawdown)
                                            │
                                            ▼
                             [ MAKER-FIRST ORDER MANAGER ]
                             (Passively routed to Binance)
```

---

### Sleeve A: Delta-Neutral Carry & Basis Yield (45%)
- **Economic Premise**: Perpetual contracts systematically trade at an annualized funding premium to spot due to persistent retail long leverage demand. Shorting high-funding perpetuals while holding spot captures pure carry yield with zero market beta.
- **Formulas**:
  $$\text{Hurdle Rate}_{8h} = \frac{\text{Annual Hurdle (8\%)}}{365 \times 3} \approx 0.0073\% \text{ per 8h}$$
  $$\text{Entry Condition}: \text{Funding Rate}_{8h} > \text{Hurdle Rate}_{8h} \quad \text{and} \quad \text{Basis Premium} \ge 0$$
  $$\text{Exit Condition}: \text{Funding Rate}_{8h} \le 0\%$$
- **Capital Rules**: 40–50% allocation, maximum 1.5x leverage.

---

### Sleeve B: Multi-Timeframe Trend Following (30%)
- **Economic Premise**: Momentum persists in crypto due to retail trend chasing, ETF inflows, and reflexive liquidity spirals. Volatility-targeted sizing inversely to ATR ensures equal risk contribution across quiet and volatile regimes.
- **Formulas**:
  $$\text{Donchian High} = \max(High_{t-19 \dots t}), \quad \text{Donchian Low} = \min(Low_{t-19 \dots t})$$
  $$\text{Trend Filter}: EMA_{50}$$
  $$\text{Long Trigger}: Close_t > \text{Donchian High} \quad \text{and} \quad Close_t > EMA_{50}$$
  $$\text{Short Trigger}: Close_t < \text{Donchian Low} \quad \text{and} \quad Close_t < EMA_{50}$$
  $$\text{Trailing Stop}: \text{Peak Price} \mp (2.0 \times ATR_{14})$$
  $$\text{Vol-Target Sizing}: Q = \frac{\text{Equity} \times 0.0075}{2.0 \times ATR_{14}}$$

---

### Sleeve C: Multi-Signal Alpha Ensemble (25%)
A library of 10 orthogonal signals evaluated simultaneously at each bar close:

#### The 10 Orthogonal Alpha Signals (Formulas & Logic)
1. **S01 — Volatility Compression Squeeze (`s01_vol_squeeze.py`)**:
   - Condition: Bollinger Bands (20, 2.0) contract entirely inside Keltner Channels (20, 1.5 ATR).
   - Breakout: Close breaks band with Volume Z-score $> 1.2$.
2. **S02 — Cross-Sectional Momentum (`s02_cross_sectional_mom.py`)**:
   - Calculates 72-hour return across the universe: $R_i = \frac{P_{t}}{P_{t-72}} - 1$.
   - Z-score relative strength: Long top quintile ($Z > +1.0$), Short bottom quintile ($Z < -1.0$).
3. **S03 — Funding Rate Crowding Reversal (`s03_funding_crowding.py`)**:
   - Identifies extreme sentiment overextension when rolling 14-day funding rate percentile $> 95\%$ (fade short) or $< 5\%$ (fade long).
4. **S04 — Order Book Queue Imbalance (`s04_orderbook_imbalance.py`)**:
   - Ratio of bid depth to ask depth:
     $$OFI = \frac{\sum Q_{bid} - \sum Q_{ask}}{\sum Q_{bid} + \sum Q_{ask}}$$
   - Trigger when $|OFI| > 0.40$.
5. **S05 — Liquidity Shock Reversion (`s05_liquidity_shock_reversion.py`)**:
   - Detects abnormal volume burst ($Volume > 3.0 \times \mu_V$) coupled with long wick rejection ($Wick > 2.0 \times Body$). Fades the wick.
6. **S06 — Bitcoin Lead-Lag Dislocation (`s06_btc_lead_lag.py`)**:
   - BTC leads altcoins by 1 to 4 hours. When BTC moves $> 2.0\%$ over 4h and altcoin has lagged ($< 0.5\%$), trades altcoin in the direction of BTC.
7. **S07 — Term Structure & Spot-Perp Basis (`s07_term_structure_basis.py`)**:
   - Evaluates $(Mark - Index) / Index$. Mean-reverts extreme basis dislocations ($Z > 2.5$).
8. **S08 — Multi-Band VWAP Deviation (`s08_vwap_deviation.py`)**:
   - Anchored intraday VWAP with 1.5, 2.0, and 2.5 standard deviation bands. Mean-reversion trigger when price breaches Band 2.0.
9. **S09 — Event Momentum Continuation (`s09_event_momentum.py`)**:
   - High-volume regime breaks with ATR expansion $> 2.5\times$ baseline. Enters directional momentum with tight trailing stops.
10. **S10 — Cross-Exchange Dislocation (`s10_cross_exchange_dislocation.py`)**:
    - Synthetic spread dislocation between reference spot and perp price.

#### Meta-Labeling & Cost-Aware Combiner
- **Alpha Combiner (`combiner.py`)**: Aggregates signals by normalizing weights through an inverse correlation matrix.
- **Cost-Aware Gate**:
  $$\text{Expected Forecast Return} > 2.0 \times (\text{Fee} + \text{Slippage})$$
  Rejects marginal signals where fee friction exceeds edge.
- **Meta-Labeling (`meta_labeler.py`)**: A secondary machine learning classifier trained via the **Triple Barrier Method** (Profit Target, Stop Loss, Max Holding Period). The base signal dictates *direction*; the meta-labeler predicts the *probability of reaching the profit barrier first*. Trades are executed only if:
  $$P(\text{Success}) > 0.55$$

---

## 5. ADVANCED INSTITUTIONAL ALPHA & RISK ENGINES

### Dynamic Profit Ratchet & Trailing Volatility Harvest
File: [`apex/risk/profit_ratchet.py`](file:///Users/mukulbhardwaj/bot/apex/risk/profit_ratchet.py)
- **Objective**: Prevents major unrealized account gains (+2%, +4%, etc.) from round-tripping into losses during violent macro reversals.
- **Milestone Ratchet Schedule**:
  - Gain $\ge +1.5\%$ $\rightarrow$ Locks Floor at $+0.8\%$
  - Gain $\ge +2.5\%$ $\rightarrow$ Locks Floor at $+1.5\%$
  - Gain $\ge +4.0\%$ $\rightarrow$ Locks Floor at $+2.8\%$
  - Gain $\ge +6.0\%$ $\rightarrow$ Locks Floor at $+4.5\%$
- **Trailing Harvest**: If marked-to-market equity declines by more than 1.5% from its peak, the ratchet signals immediate risk reduction to protect banked profit.

### BTC Macro-Regime Filter
File: [`apex/signals/btc_regime.py`](file:///Users/mukulbhardwaj/bot/apex/signals/btc_regime.py)
- **Objective**: Bitcoin dictates crypto macro liquidity. Altcoin longs are disastrous during Bitcoin distribution or breakdown regimes.
- **Logic**: Tracks BTC distance from its 20-period Exponential Moving Average ($EMA_{20}$):
  - **`BULL_EXPANSION`** ($BTC > EMA_{20} + 0.3\%$): Altcoin longs fully enabled (100% size).
  - **`NEUTRAL_CHOP`** (within $\pm 0.3\%$ of $EMA_{20}$): Moderate risk posture (70% size).
  - **`BEAR_DEFENSIVE`** ($BTC < EMA_{20} - 0.3\%$): Altcoin longs strictly vetoed (0% size).

### 8-Hour Funding Arbitrage Harvester
File: [`apex/signals/funding_harvester.py`](file:///Users/mukulbhardwaj/bot/apex/signals/funding_harvester.py)
- **Objective**: Continuously monitors funding rates across the 20-asset universe, calculates countdown to the next 8-hour payout window (00:00, 08:00, 16:00 UTC), and generates delta-neutral carry orders on coins offering $> 15\%$ annualized APR.

---

## 6. INDEPENDENT RISK SENTINEL & EXECUTION GOVERNANCE

File: [`apex/risk/service.py`](file:///Users/mukulbhardwaj/bot/apex/risk/service.py)

The Risk Sentinel operates with absolute veto power. It intercepts every order before transmission:

```
[ INCOMING ORDER EVENT ]
         │
         ▼
[ RULE 1: Gross Leverage <= 3.0x ] ───────────► REJECT if breached
         │
         ▼
[ RULE 2: Daily Loss <= -3.0% ] ──────────────► REJECT & 24H HALT
         │
         ▼
[ RULE 3: Drawdown Ladder Check ]
  ├── DD >= 8%:  Halve position size (0.5x)
  ├── DD >= 12%: Disable Sleeve C entirely
  └── DD >= 18%: Trigger full catastrophic shutdown
         │
         ▼
[ RULE 4: Data Staleness <= 30,000ms ] ───────► REJECT if feed stale
         │
         ▼
[ RULE 5: Bid-Ask Spread <= 50 bps ] ─────────► REJECT if spread abnormal
         │
         ▼
[ RULE 6: Throttle <= 30 orders/min ] ────────► REJECT if spamming
         │
         ▼
[ PASSED: Transmit to Exchange ]
```

---

## 7. PORTFOLIO ACCOUNTING, NETTING & TRANSACTION COST MODEL

### Position Netting Engine
File: [`apex/backtest/portfolio.py`](file:///Users/mukulbhardwaj/bot/apex/backtest/portfolio.py)
- If Sleeve A signals `SHORT 0.50 BTC` (carry hedge) and Sleeve B signals `LONG 0.70 BTC` (trend breakout), the netting engine computes:
  $$\text{Net Execution} = +0.70 - 0.50 = +0.20 \text{ BTC BUY}$$
- Eliminates $1.0 \text{ BTC}$ of redundant round-trip turnover.

### Realistic Transaction Cost Model
File: [`apex/backtest/cost_model.py`](file:///Users/mukulbhardwaj/bot/apex/backtest/cost_model.py)
- **Binance VIP0 USDS-M Fee Schedule**:
  - Maker Fee: $0.02\%$ (2.0 bps)
  - Taker Fee: $0.05\%$ (5.0 bps)
- **Market Impact**: Modeled via the square-root law of market impact:
  $$\text{Slippage (bps)} = 2.0 + 10.0 \times \sqrt{\frac{\text{Order Size}}{\text{Average Daily Volume}}}$$

---

## 8. SESSION STATE PERSISTENCE & CLOUD RECOVERY ENGINE

### The Problem Solved
Cloud host redeployments (e.g. Railway, Docker, Kubernetes) destroy in-memory container state, inadvertently resetting paper trading balances back to the initial baseline ($100,000.00).

### The Architecture
File: [`apex/execution/live_paper_runner.py`](file:///Users/mukulbhardwaj/bot/apex/execution/live_paper_runner.py) & [`apex_session_state.json`](file:///Users/mukulbhardwaj/bot/apex_session_state.json)

1. **State Schema (`apex_session_state.json`)**:
```json
{
  "initial_capital": 100000.0,
  "cash": 104065.87,
  "equity": 104065.87,
  "peak_equity": 104065.87,
  "ratchet_floor": 102800.0,
  "total_closed_trades": 18,
  "total_orders_filled": 64,
  "iteration_count": 4280,
  "timestamp": 1728559000
}
```
2. **Atomic Write Protocol**:
   State is serialized to a `.tmp` file and swapped atomically using `os.replace` to prevent corrupted reads during power failure.
3. **Bootstrapping Precedence on Boot**:
   - *Step 1*: Check for existing `apex_session_state.json`. If present, restore `cash`, `peak_equity`, and trade counts.
   - *Step 2*: If absent, inspect `STARTING_EQUITY` environment variable.
   - *Step 3*: Fall back to default initial baseline ($100,000.00).

---

## 9. 24/7 CLOUD EXECUTION DAEMON & OUTBOUND TELEMETRY PIPELINE

File: [`apex/execution/live_paper_runner.py`](file:///Users/mukulbhardwaj/bot/apex/execution/live_paper_runner.py)

### Execution Flow Every 5.0 Seconds
```
[ CYCLE TICK ]
  ├── 1. Fetch live 1h/15m OHLCV bars & funding rates via CCXT
  ├── 2. Update PointInTimeStore indicators
  ├── 3. Evaluate Sleeves A, B, C & Algos (Profit Ratchet, BTC Regime, Harvester)
  ├── 4. Generate SignalEvents & Net opposing quantities
  ├── 5. Filter through Risk Sentinel rules
  ├── 6. Simulate maker/taker order fills & record slippage/latency
  ├── 7. Save atomic state snapshot to apex_session_state.json
  └── 8. Push telemetry payload to Vercel dashboard webhook
```

### Embedded Status Server
Runs on `0.0.0.0:$PORT` (port 8080 default):
- `GET /api/state` or `/health`: Returns live JSON state, open positions, active orders, and risk sentinels.
- `POST /api/kill-switch`: Remotely cancels all open orders and sets kill-switch flag.

---

## 10. INSTITUTIONAL WEB DASHBOARD & API ARCHITECTURE (NEXT.JS)

Directory: `web/`

### Visual Tokens & Aesthetics (`web/app/globals.css`)
- **Theme**: Ultra-dark glassmorphic institutional terminal.
- **Colors**: Deep obsidian (`#08090d`), Glass border (`rgba(255, 255, 255, 0.08)`), Emerald gain (`#10b981`), Rose loss (`#f43f5e`), Cyan highlight (`#06b6d4`), Violet accent (`#8b5cf6`).
- **Typography**: `Outfit` for headers/KPIs, `JetBrains Mono` for tickers, numbers, and ledger entries.

### Dual-Source Telemetry Routing (`web/app/api/state/route.js`)
1. **Primary**: Inspects `store.js` for real-time state pushed outbound from the cloud bot via webhook.
2. **Secondary**: If no webhook received, proxies directly to Railway via `BOT_API_URL`.
3. **Tertiary**: Emits standby monitoring state if bot is undergoing container initialization.

### Key Terminal UI Components (`web/app/page.js`)
- **Top Utility Header**: 24/7 Cloud status badge, Exchange gateway mode (`BINANCE_FUTURES_TESTNET`), UTC clock, and Emergency Kill Switch button.
- **Unattended Mode Banner**: Reassurance indicator confirming bot runs in cloud independently of user laptop.
- **KPI Metrics Grid**:
  1. Total Account Equity (Live balance, Baseline, Net percentage).
  2. 24h Today P&L (Dollar gain/loss, Daily loss limit alert).
  3. Gross Portfolio Leverage (Real-time vs 3.0x Hard Cap).
  4. Current Drawdown (Drawdown percentage & Risk Ladder step).
- **Institutional Alpha Strip**:
  1. 💎 Profit Ratchet (Locked Floor, Peak Equity, Status).
  2. 🧭 BTC Macro-Regime Filter (BTC price, EMA20 distance, Altcoin sizing).
  3. ⏱️ 8h Funding Yield Harvester (Countdown to payout, APR yield).
- **Live Marked-to-Market Equity Chart**: 24-hour historical equity progression canvas.
- **Risk Sentinel Sentinels**: Status matrix of all 6 active circuit breakers.
- **Open Positions Table**: Multi-asset view showing Symbol, Sleeve, Side, Quantity, Mark Price, and Unrealized P&L.
- **Live Orders & Trade History**: Active limit orders and completed trades.
- **Rolling Terminal Console**: Monospaced terminal output streaming live bot cycle logs.

---

## 11. PRODUCTION DEPLOYMENT & INFRASTRUCTURE GUIDE (RAILWAY + VERCEL)

### Deploying the Cloud Backend (Railway)
1. Link your GitHub repository to Railway.
2. Select **Deploy from Dockerfile**.
3. Configure the following environment variables in Railway:
   ```env
   BINANCE_API_KEY=your_binance_key
   BINANCE_API_SECRET=your_binance_secret
   BINANCE_TESTNET=true
   POLL_INTERVAL=5.0
   PORT=8080
   INITIAL_CAPITAL=100000.00
   STARTING_EQUITY=104065.87
   APEX_STATE_FILE=apex_session_state.json
   VERCEL_WEBHOOK_URL=https://your-vercel-app.vercel.app/api/telemetry
   APEX_API_SECRET=your_secure_secret_token
   ```
4. Verify deployment logs: Engine will start on `0.0.0.0:8080` and log `Cycle #001`.

### Deploying the Dashboard (Vercel)
1. Import repository in Vercel.
2. Set **Root Directory** to `web`.
3. Framework Preset: **Next.js**.
4. Configure environment variables in Vercel:
   ```env
   BOT_API_URL=https://your-railway-app.up.railway.app
   APEX_API_SECRET=your_secure_secret_token
   ```
5. Deploy. The dashboard will automatically link with the cloud engine.

---

## 12. COMPREHENSIVE VERIFICATION & TESTING SUITE

Run all 26+ tests locally:
```bash
pytest tests/ -v
```

### Test Coverage Matrix
- `tests/test_phase1.py`: PointInTimeStore zero-lookahead verification, timestamp ordering, split/delisting safety.
- `tests/test_phase2.py`: Sleeve A carry hurdle tests, Sleeve B Donchian breakout & trailing stops, S01 squeeze calculation.
- `tests/test_phase3.py`: Alpha Combiner correlation weighting, Meta-labeler probability filtering, Regime classifier state switches.
- `tests/test_phase4.py`: Risk Service leverage cap enforcement, 24h loss limit halt, Drawdown ladder size halving, Cost model maker/taker fees.
- `tests/test_phase5.py`: Order manager simulation, maker queue priority, live vs backtest drift tracker.
- `tests/test_new_algos.py`: Profit Ratchet milestone triggers & trailing stops, BTC Regime altcoin sizing gates, 8h Funding Harvester countdown, and Session state disk persistence recovery.

---

## 13. TURNKEY AGENT PROMPT (TO CLONE & RECREATE THIS SYSTEM)

> **Copy-Paste Instructions**: Give the exact prompt below to any advanced AI coding agent (e.g. Antigravity, Claude, GPT-4) to instruct it to build the entire APEX system from scratch:

```markdown
You are an institutional quantitative trading systems architect. Your mission is to build the complete "APEX Adaptive Multi-Signal Quantitative Trading System" in Python 3.12 and Next.js 14, following strict institutional-grade specifications.

### Architecture Requirements:
1. Multi-Sleeve Portfolio:
   - Sleeve A (45%): Delta-Neutral Perpetual Carry Harvester (8% annual hurdle, basis tracking bounds).
   - Sleeve B (30%): Multi-Timeframe Trend Following (20-Donchian breakout, 50-EMA filter, 14-ATR trailing stop, vol-targeted sizing).
   - Sleeve C (25%): 10-Alpha Ensemble (S01 Vol Squeeze, S02 Cross-Sectional Mom, S03 Funding Crowding, S04 Orderbook Imbalance, S05 Liquidity Shock Reversion, S06 BTC Lead-Lag, S07 Basis Dislocation, S08 VWAP Deviation, S09 Event Momentum, S10 Cross-Exchange Dislocation).
   - Combiner: AlphaCombiner with correlation de-weighting, Meta-Labeler Triple Barrier classifier (p > 0.55), Cost-Aware Gate (Forecast > 2x Cost).
2. Institutional Extensions:
   - Dynamic Profit Ratchet (apex/risk/profit_ratchet.py): Locks profits at +1.5%, +2.5%, +4.0%, and +6.0% milestones, triggers harvest on 1.5% peak pullback.
   - BTC Macro-Regime Filter (apex/signals/btc_regime.py): Evaluates BTC vs EMA20; gates altcoin longs in BEAR_DEFENSIVE regimes.
   - 8h Funding Yield Harvester (apex/signals/funding_harvester.py): Scans 20 cryptos for > 15% APR carry and counts down to 00:00/08:00/16:00 UTC payouts.
3. Independent Risk Sentinel (apex/risk/service.py):
   - 3.0x Gross Leverage Hard Cap, -3.0% Daily Loss Limit (24h halt), Drawdown ladder (-8% halves size, -12% disables Sleeve C, -18% full halt), Stale quote filter (> 30s), Abnormal spread veto (> 50 bps).
4. Portfolio & Execution Engine:
   - Position Netting across sleeves before order routing.
   - Maker-first passive execution simulation with Binance VIP0 fees (Maker 2 bps, Taker 5 bps) and square-root slippage model.
   - Session State Persistence (apex_session_state.json): Saves cash, equity, and high-water mark every cycle to preserve balances across cloud restarts.
5. Cloud Daemon (apex/execution/live_paper_runner.py):
   - 24/7 CCXT polling loop on Binance USDS-M Perpetuals across 20 symbols.
   - Embedded HTTP server on port 8080 (/api/state, /api/kill-switch, /health).
   - Outbound telemetry webhook pushing JSON state to Next.js dashboard.
6. Institutional Web Dashboard (web/):
   - Next.js 14 App Router, dark glassmorphic CSS design system.
   - Displays Equity, 24h P&L, Leverage, Drawdown, Profit Ratchet strip, BTC Regime, 8h Funding Harvester, live Marked-to-Market equity curve, Risk Sentinel matrix, Open Positions table, Live Orders, and Terminal Logs.
   - Includes Emergency Kill Switch button with 'HALT' confirmation.
7. Verification:
   - Comprehensive PyTest suite covering all modules with 100% pass rate.
   - Dockerfile and railway.json for zero-touch cloud deployment.

Build the complete codebase systematically, ensure clean modular architecture, and write unit tests for each module.
```
