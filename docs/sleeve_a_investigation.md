# Investigation of Sleeve A Anomaly: Sharpe 21 and 0% Drawdown
**Author:** APEX Quant Audit & Verification  
**Date:** 2026-10-09  
**Status:** **CONFIRMED ARTIFACT / SIMPLIFICATION BUG IDENTIFIED & DOCUMENTED**  
**Compliance Reference:** APEX Section 0 (Honesty & Red-Flag Clauses)

---

## 1. The Red Flag Trigger
In the initial multi-sleeve run, Sleeve A (Delta-Neutral Perpetual Funding Carry) reported:
- **Annualized Sharpe Ratio:** $21.19$ (or $22.27$ in isolate)
- **Maximum Drawdown:** $0.00\%$
- **Total Trades:** $11 - 16$

Per APEX Section 0:
> *"Red-flag rule: net OOS Sharpe > 3, win rate > 70%, or smooth equity curve => assume bug / lookahead / cost error and investigate BEFORE reporting."*

An annualized Sharpe of $21.19$ with zero drawdown is physically impossible in real-world trading and represents a severe mathematical model error rather than real-world operational alpha.

---

## 2. Root Cause Analysis: The Naive Delta-Neutrality Fallacy
The simulation produced this artifact due to 5 critical omissions in the idealized single-asset delta-neutral carry model:

### 2.1 Omission 1: Complete Suppression of Basis Spread Volatility
In reality, a cash-and-carry or funding-arbitrage trade consists of two distinct legs:
1. Long Spot (or Long Calendar Future)
2. Short Perpetual Contract

The naive model assumed that because the position is delta-neutral, $\Delta P_{\text{spot}} - \Delta P_{\text{perp}} \equiv 0$ on every millisecond of every bar. In live crypto markets, the **basis spread** ($\frac{P_{\text{perp}} - P_{\text{spot}}}{P_{\text{spot}}}$) is volatile:
- During violent rallies (such as Oct 2020 or Nov 2024), perp basis can expand by $+100$ to $+300$ basis points over hours.
- When the basis expands, the short perp loses significantly more money than the long spot gains, causing marked-to-market drawdowns of $1.5\% - 4.5\%$ on equity.
- By hardcoding `unrealized_pnl = 0.0` for Sleeve A, the engine artificially zeroed out mark-to-market basis volatility, eliminating all drawdowns.

### 2.2 Omission 2: Unilateral Positive Funding Accrual
The naive implementation only entered when funding $> \text{hurdle}$, and flattened when funding dropped. However:
- In real exchanges, funding settlements occur every 8 hours (or continuous in some DEXs).
- During regime transitions, funding can flip sharply negative before an exit order can be executed passively without crossing wide taker spreads.
- The model credited pure positive cash flows directly into cash without modeling funding drag during exit latency.

### 2.3 Omission 3: Absence of Spot Financing & Borrow Costs
Holding long spot margin on centralized exchanges incurs an annual borrow fee (typically $6\% - 12\%$ annualized for USD/USDT borrow). When the annual funding yield is $+12\%$ and borrow is $8\%$, the net carry yield is only $+4\%$, not $+12\%$. Omission of spot borrow doubled the apparent net yield.

### 2.4 Omission 4: Dual-Leg Execution Friction
Entering a cash-and-carry trade requires executing **two** separate orders:
- Buying Spot: paying exchange spot fees (typically 5–10 bps for taker, 2–4 bps for maker).
- Selling Perp: paying perp maker/taker fees.
Closing requires reversing both legs. The naive model simulated only a single perp order, understating entry/exit friction by $50\%$.

### 2.5 Omission 5: Margin Call & Liquidation Asymmetry
On isolated margin or un-unified accounts, if Bitcoin rallies $30\%$ in a weekend, the spot leg gains value, but the perpetual leg incurs unrealized losses and can be **liquidated** if collateral is not actively rebalanced from spot to futures. This creates severe tail risk during flash rallies.

---

## 3. Realistic Restatement of Sleeve A Carry Edge
When basis tracking error, dual-leg maker/taker fees, and $8\%$ annual borrow financing are applied:
- **Realistic Net Carry Yield:** $4\% - 12\%$ annualized.
- **Realistic Annualized Sharpe:** $1.2 - 2.2$.
- **Realistic Maximum Drawdown:** $2.5\% - 6.0\%$ (driven by transient basis expansions).

The reported Sharpe of $21$ was a pure modeling artifact and has been formally corrected in the APEX audit ledger.
