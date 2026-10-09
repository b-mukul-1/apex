# APEX Data Layer Manifest & Point-in-Time Audit

**Version Date:** 2026-10-09  
**Specification:** APEX Section 2 & 1.3  

---

## 1. Data Universe & Survivorship-Bias Safeguards

### Active Universe (Liquid Perpetuals & Spot)
The active research and execution universe comprises the top 20 to 40 liquid perpetual contracts and spot pairs across Binance, Bybit, OKX, and Deribit (options IV):
- **Core Benchmarks:** BTC/USDT:USDT, ETH/USDT:USDT, SOL/USDT:USDT
- **Liquid Layer-1 / DeFi / Perps:** BNB, XRP, DOGE, ADA, AVAX, LINK, SUI, NEAR, APT, ARB, OP, INJ, TIA, RENDER, FET, PEPE, WIF, FTM/S
- **Total Universe:** 30 perpetual symbols + 10 primary spot pairs.

### Historical Delisted Symbols (Mandatory Anti-Survivorship Bias)
To prevent survivorship bias (where testing only current survivors inflates Sharpe by 40-70%), historical datasets **MUST** include symbols that collapsed, were liquidated, or were delisted during the 2020-2026 testing window:
1. **LUNA / UST (Terra):** Delisted May 2022 (algorithmic stablecoin depeg and death spiral)
2. **FTT (FTX Token):** Collapsed / Delisted Nov 2022 (exchange insolvency)
3. **SRM (Serum):** Delisted Nov 2022
4. **VGX (Voyager):** Collapsed July 2022
5. **CEL (Celsius):** Collapsed June 2022
6. **MULTI (Multichain):** Delisted July 2023 (bridge exploit)

---

## 2. Granularity & Feed Types

| Data Type | Primary Source | Granularity | Point-in-Time Timestamp Rule |
|---|---|---|---|
| **Candles (OHLCV)** | CCXT (Binance/Bybit/OKX REST & WS) | 1s, 1m, 5m, 15m, 1h, 4h, 1d | Bar close timestamp $T_{close}$. Signal can only evaluate at $T_{close} + \delta t$ (latency buffer $\ge 100$ms). |
| **Trades (Tick-by-Tick)** | WebSocket / Archive CSV | Tick millisecond | Sequenced by exchange matching engine timestamp $T_{match}$. |
| **L2 Order Book Snapshots** | CCXT.pro / Tardis / Level 2 Store | 100ms / 500ms snapshots (Top 20 bids/asks) | Sequenced by receipt timestamp $T_{recv} \ge T_{ex}$. |
| **Funding Rates & Mark/Index** | CCXT / Exchange REST | 8-hour / 1-hour / 4-hour settlement | Historical payment timestamps; rate known at start of funding window or settled at end. |
| **Open Interest & Liquidations** | Exchange WebSocket / CCXT derivatives | 5m snapshots & tick events | Stored point-in-time; no forward backfill. |
| **Options Implied Volatility (IV)** | Deribit API / Tardis DVOL | 1h snapshots | DVOL and ATM IV term structures timestamped at collection time. |

---

## 3. Historical Windows & Regime Representation (4+ Years Minimum)

The backtest suite spans 4+ years (2020-10 to 2026-10), containing verified historical macro and crypto regimes:
1. **Regime 1: Bull Run & Retail Euphoria** (Oct 2020 - May 2021) — High volatility, extreme positive funding, massive momentum payoffs.
2. **Regime 2: May 2021 Liquidation Crash & Summer Chop** (May 2021 - Sep 2021) — -50% flash crash, cascading margin liquidations, basis collapse.
3. **Regime 3: Fall 2021 Peak & Bear Market Inception** (Oct 2021 - May 2022) — Double-top ATH followed by persistent downtrends.
4. **Regime 4: 2022 Cascading Crises (LUNA/3AC/FTX)** (May 2022 - Dec 2022) — LUNA death spiral, Celsius/3AC bankruptcies, FTX collapse, negative funding spikes.
5. **Regime 5: 2023 Deep Chop & Recovery** (Jan 2023 - Oct 2023) — Low volatility, tight spreads, high false breakout rate.
6. **Regime 6: 2024-2026 ETF Inflows, Halving & Institutional Expansion** (Nov 2023 - Oct 2026) — Structural ETF flows, higher depth, lower retail noise.

---

## 4. Point-in-Time (PIT) Integrity Rules

1. **No Forward Peeking:** Data timestamps represent the physical time an event was published to the websocket or REST API.
2. **Feature Computation Lag:** Any feature computed on bar $k$ (which spans $[t_0, t_1]$) is strictly indexed at $t_1$. Orders generated from bar $k$ can only execute at $t \ge t_1 + \text{latency}$.
3. **Data Gaps & Missingness:** Missing periods are forward-filled for state, but volume is set to 0. Gaps $> 30$ seconds trigger a stale-data alert and inhibit signal generation.
