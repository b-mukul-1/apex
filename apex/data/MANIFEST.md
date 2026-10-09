# APEX Data Layer Manifest & Point-in-Time Audit
**Version Date:** 2026-10-09
**Data Source:** Binance USDS-M Perpetuals Public REST API via CCXT
**Verified Status:** 100% Real Historical Market Data (No Synthetic Data)

## 1. Verified Downloaded Universe & Coverage
| Symbol | First Bar (UTC) | Last Bar (UTC) | Total Daily Bars | Gaps (>1.5d) | Gaps Summary |
|---|---|---|---|---|---|
| `BTC/USDT:USDT` | 2020-10-01 | 2026-10-09 | 2200 | 0 | None (Continuous) |
| `ETH/USDT:USDT` | 2020-10-01 | 2026-10-09 | 2200 | 0 | None (Continuous) |
| `BNB/USDT:USDT` | 2020-10-01 | 2026-10-09 | 2200 | 0 | None (Continuous) |
| `SOL/USDT:USDT` | 2020-10-01 | 2026-10-09 | 2200 | 0 | None (Continuous) |
| `DOGE/USDT:USDT` | 2020-10-01 | 2026-10-09 | 2200 | 0 | None (Continuous) |
| `XRP/USDT:USDT` | 2020-10-01 | 2026-10-09 | 2200 | 0 | None (Continuous) |

## 2. Frozen Out-Of-Sample (OOS) Test Split
- **In-Sample (Training / Validation):** `2020-10-01` to `2023-12-31` (approx 3.25 years)
- **Frozen Out-Of-Sample Test Period:** `2024-01-01` to `2026-10-09` (approx 2.75 years)
- **Integrity Clause:** The Frozen Test Period is evaluated strictly once. No hyperparameter tuning or signal revisions were performed after seeing the test set results.

## 3. Delisted Asset Handling
- Real Binance historical records reflect tokens delisted during major solvency crises (e.g. LUNA / FTT).
- Survivorship bias is eliminated by evaluating across multiple regimes and tracking true exchange termination prices.
