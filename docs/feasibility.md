# APEX Feasibility and Mathematical Truth Document

## 1. Executive Summary & Objective

**Target Stated by Owner:** 20% to 30% daily return.  
**System Status & Classification:** **Aspirational Tail Outcome**. Under no circumstances is this figure treated as an operating quota, baseline expectation, or reason to violate strict risk controls.

This document sets down the mathematical realities, compounding arithmetic, information theory limits, and institutional empirical evidence regarding ultra-high-frequency and multi-signal algorithmic trading. The purpose of this document is to ensure absolute intellectual honesty, protect principal capital, and establish clear validation gates.

---

## 2. The Compounding Math: Geometric Proof of Physical Impossibility of Sustained Daily 20-30%

Compounding a daily return $r$ over $N = 365$ trading days per year yields an annualized growth factor of:
$$G = (1 + r)^{365}$$

Let us calculate $G$ for the target rates:
- At **20% per day** ($r = 0.20$):
  $$(1 + 0.20)^{365} \approx 1.20^{365} \approx 1.095 \times 10^{29}$$
  If an account starts with **$1,000**, after 1 year the theoretical balance would be:
  $$\$1,000 \times 10^{29} = \$10^{32}$$
  *(For perspective, total global wealth is approximately $\$4.5 \times 10^{14}$, and the entire world GDP is $\sim \$10^{14}$. \$10^{32}$ is a quadrillion times the total wealth of human civilization).*

- At **30% per day** ($r = 0.30$):
  $$(1 + 0.30)^{365} \approx 1.30^{365} \approx 7.02 \times 10^{41}$$

### Economic Constraint: Market Capacity and Impact Decay
Even if a microscopic strategy could yield +20% on $1,000 in a day with no slippage on illiquid meme coins, liquidity limits and square-root market impact ($\Delta P \propto \sigma \sqrt{\frac{Q}{V}}$) prevent scaling. Above $50,000 to $500,000 position sizes in crypto perps, market impact eats alpha rapidly.

---

## 3. Risk-Adjusted Returns & Kelly Criterion Derivation

### 3.1 Sharpe Ratio Requirement
Assuming zero risk-free rate for daily calculation, with daily standard deviation $\sigma_d$:
$$\text{Daily Sharpe} = \frac{\mu_d}{\sigma_d}$$
$$\text{Annualized Sharpe} = \text{Daily Sharpe} \times \sqrt{365}$$

Suppose an aggressive system operates with daily volatility $\sigma_d = 3.0\%$ (which is already high, implying frequent daily drawdowns of 6-9%):
- To achieve $\mu_d = 20\%$ with $\sigma_d = 3.0\%$:
  $$\text{Daily Sharpe} = \frac{20\%}{3.0\%} \approx 6.67$$
  $$\text{Annualized Sharpe} = 6.67 \times \sqrt{365} \approx 6.67 \times 19.10 \approx 127.4$$
- Even if daily volatility were permitted to explode to $\sigma_d = 15\%$ (which implies imminent ruin within weeks):
  $$\text{Daily Sharpe} = \frac{20\%}{15\%} \approx 1.33$$
  $$\text{Annualized Sharpe} = 1.33 \times \sqrt{365} \approx 25.4$$
- Under optimal continuous Kelly criterion:
  $$f^* = \frac{\mu}{\sigma^2} \implies g^* = \frac{1}{2}\left(\frac{\mu}{\sigma}\right)^2 = \frac{1}{2} \text{Sharpe}^2$$
  To compound at continuous growth $g^* = 20\%/\text{day} = 7300\%/\text{year}$, the annualized Sharpe required is:
  $$\text{Sharpe} = \sqrt{2 \times 73} = \sqrt{146} \approx 12.1$$
  *(Even Renaissance Technologies' Medallion Fund, the most successful quant fund in human history, operates at an annualized net Sharpe around ~3.5 to 4.0 before fees, and ~2.0 to 2.5 after fees)*.

### 3.2 Realistic Retail Benchmarks
For an elite, battle-tested retail/prop crypto systematic engine net of maker/taker fees, funding, and realistic slippage:
- **Net Annualized Sharpe:** $1.5 - 3.0$
- **Expected Average Daily Return:** $0.05\% - 0.40\%$ (translating to $+20\% - 300\%$ annualized return net of costs)
- **Max Expected Drawdown:** $10\% - 25\%$
- **Tail Positive Days:** $+5\% - 30\%$ occur exclusively during violent regime shifts, liquidation cascades, or volatility breakout squeezes where convex trailing stops capture outsized multi-asset trends.

---

## 4. The Path to Tail Convexity: How +20-30% Days Occur Legally

A +20% account day can occur without suicide-leverage through **asymmetric payoff convexity**:
1. **Capital Allocation:**
   - Sleeve A (Carry / Basis): 40-50% capital at 1-2x leverage (steady, delta-neutral yield).
   - Sleeve B (Trend): 20-30% capital at $\le 2$x leverage (volatility-targeted multi-day trend).
   - Sleeve C (Multi-Signal Alpha): 15-25% capital at $\le 3$x leverage (isolated margin, stop loss limited to max 5% total portfolio risk).
2. **Convex Mechanics:**
   - If Sleeve C has 5 open positions, each risking $0.8\%$ of total equity ($4\%$ total open risk), with initial stop loss at $1R$.
   - During a massive liquidation cascade or regime squeeze (e.g., Nov 2022 FTX collapse, Mar 2020 crash, or massive pump), multiple positions break into explosive runners.
   - Using volatility/structure trailing stops (e.g. Chandelier / ATR trails) rather than fixed take-profits, runner positions can yield $4R$ to $8R$ payoffs.
   - $5 \times 5R \times 0.8\% = +20\%$ portfolio gain on that single day.
3. **The Asymmetry:**
   - **Downside is capped:** Strict stops limit the day's loss to max $3\%$ (daily risk limit halts C).
   - **Upside is unconstrained:** Volatility expansions create positive fat tails.

---

## 5. Non-Negotiable Operational Commitments

1. **Never raise leverage or widen stops** to chase the owner's aspirational target.
2. **Never suppress losing trades or variants** from research logs.
3. **Report Deflated Sharpe Ratio (DSR) and Probability of Backtest Overfitting (PBO)** on every strategy ensemble to adjust for multiple hypothesis testing.
4. **Assume any backtest showing net Sharpe $> 3.0$ or win rate $> 70\%$ contains a lookahead bug or cost distortion** until exhaustively audited.
5. **Phase Gates are binding:** No trading code progresses to paper or live execution without passing all preceding validation gates.
