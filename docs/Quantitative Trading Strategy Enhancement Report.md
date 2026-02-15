# **Strategic Quantitative Portfolio Modernization: From Heuristic Algorithms to Regime-Adaptive Systems**

## **1\. Executive Summary**

The landscape of quantitative trading has undergone a fundamental structural shift in the post-2020 era. Strategies that defined the "Quant 1.0" epoch—characterized by static rules, simple heuristics (like moving average crossovers), and single-factor dependance—are seeing their alpha decay rapidly due to crowding, high-frequency arbitrage, and the convergence of asset correlations during liquidity events. The mandate for this report is to evaluate the current portfolio architecture—comprising **On-Line Moving Average Reversion (OLMAR)**, **Dual Momentum**, **Hierarchical Risk Parity (HRP)**, and the **Quallamaggie Swing Strategy**—and to propose a rigorous modernization roadmap.

The audit reveals a portfolio that is robust by historical standards but vulnerable to specific modern market pathologies. The reliance on **Dual Momentum** exposes the fund to significant "momentum crash" risk due to its inherent long-beta bias during bull markets. The **OLMAR** implementation, while mathematically elegant, often relies on single-period mean reversion assumptions that fail during strong autocorrelation regimes (trending markets). Furthermore, the portfolio currently lacks a dedicated mechanism to harvest the **Variance Risk Premium (VRP)**—the structural tendency of implied volatility to exceed realized volatility—which serves as a critical return smoother during the sideways markets where trend-following strategies stagnate.

The recommendations detailed in this exhaustive report propose a transition toward a "Quant 2.0" architecture. This evolution is defined by three strategic pillars: **Alpha Purity**, **Structural Arbitrage**, and **Regime Adaptation**.

**Core Recommendations:**

1. **Transition to Residual Momentum:** The Dual Momentum framework should be upgraded to **Residual Momentum**. By calculating momentum based on the idiosyncratic residuals of a Fama-French factor regression rather than total returns, we isolate the pure behavioral anomaly of price persistence while neutralizing exposure to market beta, size, and value factors. This dramatically improves the Sharpe ratio and reduces drawdown risk during factor rotations.  
2. **Implementation of Modern Statistical Arbitrage:** The mean reversion engine must evolve from univariate price-action models (OLMAR) to a multivariate **Statistical Arbitrage** framework. This involves utilizing **DBSCAN** density-based clustering for unsupervised universe selection and **Kalman Filters** for dynamic beta estimation, moving beyond the rigid and overcrowded sector-based pairs trading of the past.  
3. **Systematic Volatility Harvesting:** To diversify the return stream, the portfolio should incorporate **Short Volatility** strategies (e.g., Delta-Hedged Iron Condors or trend-filtered SVXY allocations). This component monetizes the fear premium in the options market, providing liquidity and returns when directional alpha sources are dormant.  
4. **Regime-Based Allocation via HMM:** Static asset allocation should be replaced with a dynamic system governed by **Hidden Markov Models (HMM)**. By inferring the latent market state (e.g., Low Volatility Bull vs. High Volatility Chop), the system can probabilistically tilt capital toward the strategies most likely to perform, rather than maintaining a fixed exposure to failing strategies.  
5. **Meta-Labeling for Discretionary Signals:** The Quallamaggie Swing strategy, currently a discretionary or semi-systematic breakout approach, should be augmented with **Meta-Labeling**. A secondary machine learning layer (Random Forest) will be trained to predict the *probability of trade success* given the market context, filtering out high-probability failures that human intuition often misses.

This report provides the theoretical underpinning, empirical evidence, and implementation mechanics for each of these upgrades, designed to transform the current strategy set into an institutional-grade, regime-adaptive quantitative fund.

## ---

**2\. Part I: Diagnostic Analysis of the Current Alpha Engine**

Before integrating new strategies, it is essential to dissect the theoretical mechanics and latent risks of the existing portfolio. The current codebase typically implements these strategies as distinct, standalone silos. The "Quant 2.0" approach requires viewing them as interacting components of a unified risk surface.

### **2.1 OLMAR: The Limitations of Single-Period Reversion**

**On-Line Moving Average Reversion (OLMAR)** is a portfolio selection algorithm rooted in the concept that prices revert to a moving average. In its standard implementation (as seen in the provided codebase context and Li et al., 2012), OLMAR assumes that the expected price relative for the next period is the inverse of the current trend relative to a moving average.

#### **2.1.1 Theoretical Mechanics**

OLMAR operates on the "reversion to the mean" principle. If the current price $p\_t$ is significantly lower than the moving average $\\bar{p}\_t$ (e.g., SMA or EMA), the algorithm hypothesizes a high expected return as the price "snaps back."

$$x\_{t+1} \= \\underset{x \\in \\Delta\_m}{\\text{argmin}} \\frac{1}{2} \\|x \- x\_t\\|^2 \\quad \\text{s.t.} \\quad \\bar{p}\_{t+1} \\cdot x \\geq \\epsilon$$

The algorithm solves an optimization problem to rebalance the portfolio $x$ such that the expected wealth growth exceeds a threshold $\\epsilon$.

#### **2.1.2 Vulnerability Analysis**

While OLMAR is computationally efficient and performs well in oscillating markets, it suffers from two critical flaws documented in recent literature 1:

* **The Single-Period Fallacy:** OLMAR is a "greedy" algorithm. It assumes reversion will happen *in the next period*. In strong trending markets (autocorrelation \> 0), prices continue to diverge from the mean for extended periods. OLMAR essentially keeps "catching the falling knife," rebalancing into losers aggressively as they drop further. In a prolonged crash (like 2008 or 2022), this can lead to catastrophic drawdowns before the mean reversion occurs.  
* **Transaction Cost Blindness:** The "On-Line" nature implies frequent rebalancing—often daily. The theoretical alpha of OLMAR degrades significantly when realistic slippage and commission costs are applied, as the algorithm often chases small reversions that are consumed by the bid-ask spread.3

### **2.2 Dual Momentum: The Hidden Beta Risk**

**Dual Momentum**, popularized by Gary Antonacci, combines **Relative Momentum** (buying the best performer among assets) and **Absolute Momentum** (moving to cash if the asset's trend is negative).

#### **2.2.1 Theoretical Mechanics**

The strategy typically ranks a universe (e.g., US Stocks, International Stocks, Bonds) based on 12-month returns.

1. **Relative Test:** Compare $R\_{US}$ vs. $R\_{Intl}$. Select the winner.  
2. **Absolute Test:** Is $R\_{Winner} \> R\_{Bill}$ (or is $R\_{Winner} \> 0$)?  
   * If Yes: Go Long Winner.  
   * If No: Go Long Aggregate Bonds / Cash.

#### **2.2.2 Vulnerability Analysis**

The primary weakness of Dual Momentum is its reliance on **Total Return** as the sorting metric.

* **Beta Contamination:** In a strong bull market, the assets with the highest total returns are often those with the highest Beta (sensitivity to the market). The strategy essentially becomes a "leveraged beta" trade.  
* **Momentum Crashes:** When the market regime shifts from Bull to Bear, high-beta stocks crash the hardest. Because the formation period is long (12 months), the "winner" status persists even as the asset collapses. The strategy stays long high-beta assets during the initial, most violent phase of a correction before the Absolute Momentum filter triggers a switch to cash. This results in the "W-shaped" recovery problem where the strategy gets whipsawed.4

### **2.3 Quallamaggie Swing: Discretionary Limitations**

The **Quallamaggie** strategy focuses on **Episodic Pivots (EP)** and high-momentum breakouts from consolidation patterns (flags, pennants), confirmed by high relative volume.6

#### **2.3.1 Theoretical Mechanics**

This is a **Trend Following** strategy applied to the micro-structure of breakouts. It relies on:

* **Catalyst:** Earnings or news causing a gap up.  
* **Continuation:** Buying the consolidation break.  
* **Explosiveness:** Targeting stocks capable of moving 30-50% in weeks.

#### **2.3.2 Vulnerability Analysis**

* **False Positive Rate:** In choppy or bearish markets (high volatility regimes), breakouts tend to fail ("squat") immediately. A purely rule-based implementation of Quallamaggie patterns without regime awareness leads to a "death by a thousand cuts" scenario, where the strategy takes small losses repeatedly on failed breakouts.  
* **Survivorship Bias:** Identifying these setups historically is prone to bias; backtests often look better than reality because they fail to account for the liquidity constraints of entering micro-cap breakouts or the "gap-and-crap" phenomenon prevalent in algorithmic markets.6

### **2.4 HRP: The Risk Allocation Engine**

**Hierarchical Risk Parity (HRP)** applies graph theory (single-linkage clustering) to sort the covariance matrix and allocates capital recursively.9

#### **2.4.1 Vulnerability Analysis**

While HRP is superior to Mean-Variance Optimization (MVO) because it doesn't require matrix inversion (avoiding instability), it has limitations:

* **Single Linkage Chaining:** The clustering algorithm can create long, meaningless chains of assets if the data is noisy.  
* **Recursive Bisection:** Once the tree is built, HRP splits risk top-down. If the top-level split is suboptimal, the error propagates down to all individual asset weights. It does not optimize *within* the clusters effectively, merely allocating based on inverse variance.10

## ---

**3\. Part II: The Evolution of Momentum Strategies**

To mitigate the "Beta Risk" of Dual Momentum, the portfolio must transition to **Residual Momentum**. This represents the cutting edge of factor-based trend following.

### **3.1 Residual Momentum: Isolating the Signal**

Standard momentum strategies ask: "Which stock went up the most?"  
Residual momentum asks: "Which stock went up the most, relative to what its risk exposure implies?"

#### **3.1.1 Mathematical Formulation**

The core idea is to strip out the returns attributable to common risk factors (Market, Size, Value) to uncover the idiosyncratic price momentum.

Step 1: The Factor Model  
For each asset $i$ in the universe, we estimate the following regression over a rolling window (typically 36 months):

$$R\_{i,t} \= \\alpha\_i \+ \\beta\_{MKT} MKT\_t \+ \\beta\_{SMB} SMB\_t \+ \\beta\_{HML} HML\_t \+ \\epsilon\_{i,t}$$

* $R\_{i,t}$: Excess return of asset $i$ at time $t$.  
* $MKT\_t, SMB\_t, HML\_t$: Returns of the Fama-French 3 factors.  
* $\\epsilon\_{i,t}$: The **residual return**—the unexplained portion.

Step 2: The Residual Score  
We do not use the raw sum of residuals, as this would favor volatile stocks. Instead, we standardize the cumulative residual return by its volatility. The ranking signal $S\_i$ at time $t$ is:

$$S\_i \= \\frac{\\sum\_{k=1}^{12} \\epsilon\_{i, t-k}}{\\sigma\_{\\epsilon\_i}}$$

where $\\sigma\_{\\epsilon\_i}$ is the standard deviation of the residuals over the formation period.

#### **3.1.2 Empirical Advantages**

Research by Blitz, Huij, and Martens (2011) and subsequent studies 12 demonstrate that Residual Momentum:

1. **Doubles the Sharpe Ratio:** By removing the noisy market beta, the signal-to-noise ratio of the ranking metric improves drastically.  
2. **Eliminates Crash Risk:** Since the strategy is not structurally long high-beta stocks, it does not suffer the massive drawdowns seen in standard momentum during market reversals (e.g., 2009). The correlation to the broad market is significantly lower.  
3. **Consistency:** It performs more consistently across different market caps and sectors, as it doesn't just pick the "riskiest" sector of the moment.

**Recommendation:** Modify the existing Dual Momentum codebase to fetch Fama-French factor data (daily/monthly). Replace the simple 12-month ROC (Rate of Change) calculation with the Residual Score calculation defined above.

### **3.2 Volatility Scaling: The Risk Control Overlay**

Momentum strategies exhibit time-varying volatility. To target a constant risk profile and avoid being forced out of positions at the bottom of a drawdown, **Volatility Scaling** is mandatory.

Mechanism:  
Instead of a fixed capital allocation (e.g., 100% equity), the exposure level is dynamic.

$$w\_t \= \\text{min}\\left(MaxLev, \\frac{\\sigma\_{target}}{\\hat{\\sigma}\_{t-1}}\\right)$$

* $\\sigma\_{target}$: The desired annualized volatility (e.g., 12%).  
* $\\hat{\\sigma}\_{t-1}$: The realized volatility of the momentum portfolio (e.g., 6-month EWMA).

**Insight:** This mechanism naturally reduces exposure when markets become turbulent (often preceding a crash) and increases exposure in calm, trending markets. This "risk-managed momentum" has been shown to significantly reduce kurtosis (fat tails) and improve long-term geometric returns.4

## ---

**4\. Part III: Next-Generation Mean Reversion (Statistical Arbitrage)**

The move from OLMAR to **Statistical Arbitrage (Stat Arb)** represents a shift from "betting on price" to "betting on structure."

### **4.1 Unsupervised Learning for Universe Selection**

Traditional pairs trading relies on predefined sectors (e.g., General Motors vs. Ford). This is brittle; companies evolve, and sector classifications (GICS) are often outdated or too broad.

#### **4.1.1 Dimensionality Reduction (PCA)**

Before looking for pairs, we reduce the noise in the universe (e.g., S\&P 500\) using **Principal Component Analysis (PCA)**.

* **Process:** We extract the top $K$ principal components (eigenvectors) that explain \~90% of the variance in the returns matrix.  
* **Output:** Each stock is now represented by a vector of factor loadings rather than a time series of prices. This captures its "DNA"—how it reacts to interest rates, oil, growth, etc..15

#### **4.1.2 Density-Based Clustering (DBSCAN/OPTICS)**

We apply **DBSCAN** (Density-Based Spatial Clustering of Applications with Noise) to these factor loading vectors.

* **Why DBSCAN?** Unlike K-Means, which forces every stock into a cluster (creating "garbage" clusters), DBSCAN identifies core samples of high density and expands clusters from them. It labels unique stocks as "noise" (-1).  
* **Strategic Value:** We only trade pairs found within valid DBSCAN clusters. This guarantees that the assets are fundamentally similar in their risk exposures, even if they belong to different industries (e.g., an airline and a cruise line might cluster together due to oil/consumer sensitivity). This reveals "hidden" pairs that are less crowded by retail traders.15

### **4.2 Dynamic Hedging with Kalman Filters**

Once a pair is identified (Stock A and Stock B), the standard approach trades the spread $S\_t \= P\_A \- \\beta P\_B$, where $\\beta$ is fixed (OLS regression over 1 year).  
The Problem: The relationship ($\\beta$) changes over time. A static $\\beta$ leads to "divergence risk"—trading a spread that is widening not because of noise, but because the structural relationship has broken.

#### **4.2.1 The Kalman Filter Model**

We model the hedge ratio $\\beta\_t$ as a "hidden state" that evolves over time.  
State Equation (Random Walk):

$$\\beta\_t \= \\beta\_{t-1} \+ w\_t, \\quad w\_t \\sim N(0, Q)$$  
**Observation Equation (Regression):**

$$y\_t \= x\_t \\beta\_t \+ \\epsilon\_t, \\quad \\epsilon\_t \\sim N(0, R)$$

* $y\_t$: Price of Stock A.  
* $x\_t$: Price of Stock B.

At each time step $t$, the Kalman Filter performs a **Predict** and **Update** cycle.

1. **Predict:** Estimate the prior state $\\beta\_{t|t-1}$.  
2. **Update:** Observe the actual prices. Calculate the measurement residual (error). Update the estimate $\\beta\_{t|t}$ based on the Kalman Gain (which balances the uncertainty of the model vs. the uncertainty of the measurement).

**Implementation Benefit:** The Kalman Filter allows the hedge ratio to adapt instantly to new information. If the relationship shifts, the $\\beta$ adjusts, neutralizing the spread. This transforms the strategy from a directional bet on a broken pair into a pure arbitrage of the residual noise.17

### **4.3 Liquidity Provision Strategies**

Complementing the "structural" mean reversion of pairs is the "liquidity" mean reversion of single stocks. Based on Jurek and Yang (2007) 19, this strategy acts as a market maker of last resort.

* **Signal:** High **Relative Volume (RVOL)** \+ Extreme Price Move \+ **No News**.  
* **Logic:** If a stock drops 5% on 5x volume with no news, it is likely a forced liquidation (margin call or fund redemption). The price impact is temporary.  
* **Execution:** Place passive limit orders to capture the spread, capitalizing on the "snap back" when the selling pressure abates.

## ---

**5\. Part IV: Volatility as a Strategic Asset**

A "Modern" portfolio is incomplete without exposure to the **Variance Risk Premium (VRP)**. The VRP is the compensation investors receive for selling insurance (options) against market turbulence.

### **5.1 The Variance Risk Premium (VRP) Explained**

Empirically, **Implied Volatility (IV)** \> **Realized Volatility (RV)** in 85-90% of observed periods.

* **The Buyer:** Typically hedging equity portfolios (long puts). They are willing to pay a premium (negative expected return) for peace of mind.  
* **The Seller:** By systematically selling this insurance, the portfolio collects a "yield" that is structurally positive and uncorrelated to equity beta.20

### **5.2 Systematic Short Volatility Strategies**

We recommend two complementary approaches to harvest VRP:

#### **5.2.1 Systematic Iron Condors**

The Iron Condor is a defined-risk strategy that profits from the market staying within a range.

* **Structure:** Sell OTM Put, Sell OTM Call. Buy further OTM Put, Buy further OTM Call (Wings).  
* **Selection:**  
  * **Underlying:** SPX (Section 1256 tax treatment, cash settled) or SPY/IWM.  
  * **Delta:** Sell 15-20 Delta (approx. 1 standard deviation). Buy 5-10 Delta.  
  * **Tenor:** 45 Days to Expiration (DTE). Research shows this part of the term structure offers the best trade-off between Theta decay (income) and Gamma risk (price sensitivity).21  
* **Management:**  
  * **Profit Taker:** Close at 50% of max profit. This significantly increases the win rate and capital turnover.  
  * **Stop Loss:** Close if the credit received expands to 2x-3x (depending on backtest calibration).  
  * **Filter:** Do not enter if VIX is extremely low (\<12, low premium) or extremely high (\>35, unpredictable moves).22

#### **5.2.2 The VIX Roll-Down (SVXY)**

For a more liquid, linear implementation, the **ProShares Short VIX Short-Term Futures ETF (SVXY)** can be used.

* **Mechanism:** SVXY shorts the front two months of VIX futures. When the VIX term structure is in **Contango** (Future \> Spot), the futures roll down towards the spot price as they approach expiration. SVXY captures this roll yield.  
* **Critical Risk Control:** SVXY must *never* be held blindly.  
  * **The Term Structure Signal:** Hold SVXY *only* when VIX 1-Month Future \< VIX 3-Month Future (Contango).  
  * **The Panic Signal:** If VIX Spot \> SMA(VIX, 200), move to cash.  
  * This logic prevents the strategy from holding short volatility exposure during spikes like "Volmageddon" (Feb 2018).23

### **5.3 Tail Risk Hedging: The "Seatbelt"**

To safely allocate significant capital to Residual Momentum and Short Volatility, the portfolio requires a hedge that exhibits **convexity** during crashes.

* **Instrument:** Deep OTM VIX Calls (e.g., 2-month expiry, Delta 20).  
* **Why VIX Calls?** During a crash, equity correlation goes to 1, and diversification fails. VIX calls, however, benefit from the "Vol of Vol." As the market crashes, volatility rises, and the *volatility of volatility* rises, expanding the premium of these options exponentially.  
* **Cost of Carry:** Allocate a fixed budget (e.g., 1% of AUM per year) to purchase these calls. This is a sunk cost. The goal is not profit, but to dampen portfolio drawdowns, preventing the "ruin" of the compounding strategies.25

## ---

**6\. Part V: Portfolio Architecture & Risk Management**

Strategies are just tools; the **Architecture** is the craftsman. The final recommendation is to wrap these strategies in a regime-aware allocation framework.

### **6.1 Hidden Markov Models (HMM) for Regime Detection**

Markets switch between regimes (e.g., Calm Bull, Volatile Bear, Sideways Chop). Strategies have specific "failure modes" aligned with these regimes.

* **Momentum** fails in **Sideways/Chop**.  
* **Mean Reversion** fails in **Trending/Bull**.  
* **Short Volatility** fails in **Volatile Bear**.

HMM Implementation:  
We train a Gaussian HMM on the returns of the SPY. The model infers the unobservable "Hidden State" $S\_t$.

* **Input:** Daily Returns, Range volatility.  
* **Output:** Probability vector, e.g., $$.

Dynamic Allocation Rule:  
Instead of fixed weights, the portfolio weights $W$ become a function of the state probabilities:

$$W\_{strategy} \= \\sum\_{i=1}^{K} P(State=i) \\times W\_{strategy|i}$$

* *If P(Bull) is high:* Overweight Residual Momentum & Short Volatility.  
* *If P(Chop) is high:* Overweight Stat Arb (Pairs) & Iron Condors.  
* If P(Bear) is high: Overweight Cash & Tail Hedge.  
  This probabilistic shifting minimizes "regime mismatch" drawdowns.27

### **6.2 Nested Clustered Optimization (NCO)**

The current HRP algorithm is a good start, but **Nested Clustered Optimization (NCO)** is the superior evolution.

* **The HRP Flaw:** HRP's recursive bisection does not distinguish between inter-cluster and intra-cluster noise.  
* **The NCO Fix:**  
  1. **Cluster:** Use the same linkage trees to identify clusters.  
  2. **Inner Optimization:** Optimize weights *within* each cluster (e.g., using Minimum Variance). This handles the specific idiosyncratic risks of that cluster's assets.  
  3. Outer Optimization: Treat each cluster as a "synthetic asset" and optimize weights between clusters.  
     This two-step process yields more robust diversification and lower turnover than standard HRP.10

### **6.3 Meta-Labeling for Quallamaggie Swing**

The Quallamaggie strategy is highly effective but prone to false positives. **Meta-Labeling** applies a secondary ML model to "grade" the discretionary signals.

1. **Primary Model:** The Quallamaggie Rules (Breakout \+ Volume). Output: Binary Signal (Trade Opportunity).  
2. **Meta Model:** A Random Forest Classifier.  
   * **Features:** Volatility (VIX), Distance from MA, Sector Momentum, Bid-Ask Spread, Time of Day.  
   * **Label:** Did the trade profit? (1/0).  
3. **Operation:** When the Primary Model signals a trade, the Meta Model estimates the *probability of success*. If Probability \> Threshold (e.g., 0.65), the trade is taken; otherwise, it is skipped. This filters out the "technically correct but contextually wrong" trades.30

## ---

**7\. Part VI: Implementation Roadmap**

The transformation from the current state to the recommended "Quant 2.0" state should be phased.

### **Phase 1: Strategy Hardening (Months 1-3)**

* **Refactor Momentum:** Replace the Dual Momentum Total Return logic with Residual Momentum using a rolling 3-year regression against Fama-French factors.  
* **Pairs Trading Pilot:** Implement the DBSCAN clustering script to visualize market clusters. Run paper trades on Kalman Filter spreads within these clusters.

### **Phase 2: Volatility & Regime Integration (Months 3-6)**

* **Deploy Short Vol:** Allocate a small portion (10%) to the Systematic Iron Condor strategy on SPX.  
* **Build HMM:** Train the HMM model on historical data to identify regimes. Begin logging regime states alongside strategy performance to validate correlations.

### **Phase 3: AI & Optimization (Months 6+)**

* **Meta-Labeling:** Begin collecting feature data on every Quallamaggie trade setup. Train the Random Forest once 500+ samples are collected.  
* **Switch to NCO:** Replace the HRP allocation engine with NCO for final portfolio weightings.

### **Summary Comparison Table**

| Feature | Current Portfolio (Quant 1.0) | Recommended Portfolio (Quant 2.0) |
| :---- | :---- | :---- |
| **Momentum** | Dual Momentum (Total Return) | **Residual Momentum (Idiosyncratic)** |
| **Mean Reversion** | OLMAR (Single-Period Price) | **Stat Arb (DBSCAN \+ Kalman Filters)** |
| **Volatility** | None (Implicit Short via Swing) | **Systematic Iron Condors / SVXY** |
| **Selection** | Sector-Based / Manual | **Unsupervised Clustering (DBSCAN)** |
| **Sizing** | HRP (Recursive Bisection) | **NCO (Nested Clustered Optimization)** |
| **Regime** | Static Allocation | **HMM Probabilistic Switching** |
| **Risk** | Diversification | **Tail Risk Hedging (Convexity)** |

This modernized architecture moves beyond simple heuristics, leveraging the full spectrum of statistical and machine learning tools available to the modern quantitative trader. It prioritizes the purity of the signal (Residuals), the dynamism of the relationship (Kalman), and the adaptability of the allocation (HMM), ensuring resilience in an increasingly complex market environment.

#### **Works cited**

1. Detecting Short-Term Mean Reverting Phenomenon in the Stock Market and OLMAR Method | Request PDF \- ResearchGate, accessed on December 26, 2025, [https://www.researchgate.net/publication/326078639\_Detecting\_Short-Term\_Mean\_Reverting\_Phenomenon\_in\_the\_Stock\_Market\_and\_OLMAR\_Method](https://www.researchgate.net/publication/326078639_Detecting_Short-Term_Mean_Reverting_Phenomenon_in_the_Stock_Market_and_OLMAR_Method)  
2. On-Line Portfolio Selection with Moving Average Reversion, accessed on December 26, 2025, [https://icml.cc/2012/papers/168.pdf](https://icml.cc/2012/papers/168.pdf)  
3. Genetic Mean Reversion Strategy for Online Portfolio Selection with Transaction Costs, accessed on December 26, 2025, [https://www.mdpi.com/2227-7390/10/7/1073](https://www.mdpi.com/2227-7390/10/7/1073)  
4. Risk-managed residual momentum: Evidence from US \- Aaltodoc, accessed on December 26, 2025, [https://aaltodoc.aalto.fi/bitstreams/5735c930-793b-4ec7-92db-f29e7f122f27/download](https://aaltodoc.aalto.fi/bitstreams/5735c930-793b-4ec7-92db-f29e7f122f27/download)  
5. Time Series and Dual Momentum for Individual Stocks \- CXO Advisory, accessed on December 26, 2025, [https://www.cxoadvisory.com/momentum-investing/time-series-and-dual-momentum-for-individual-stocks/](https://www.cxoadvisory.com/momentum-investing/time-series-and-dual-momentum-for-individual-stocks/)  
6. Deep Dive into Kristjan Kullamägi's Swing Trading Strategies: An In-Depth Guide \- Medium, accessed on December 26, 2025, [https://medium.com/@refikberkol/deep-dive-into-kristjan-kullam%C3%A4gis-swing-trading-strategies-an-in-depth-guide-7872e7f1a0cb](https://medium.com/@refikberkol/deep-dive-into-kristjan-kullam%C3%A4gis-swing-trading-strategies-an-in-depth-guide-7872e7f1a0cb)  
7. Mastering the Qullamaggie Episodic Pivot Setup: A Flexible Stock Screening Approach, accessed on December 26, 2025, [https://www.chartmill.com/documentation/stock-screener/technical-analysis-trading-strategies/494-Mastering-the-Qullamaggie-Episodic-Pivot-Setup-A-Flexible-Stock-Screening-Approach](https://www.chartmill.com/documentation/stock-screener/technical-analysis-trading-strategies/494-Mastering-the-Qullamaggie-Episodic-Pivot-Setup-A-Flexible-Stock-Screening-Approach)  
8. Episodic Pivot: The Most Powerful Setup Explained \- Analyzing Alpha, accessed on December 26, 2025, [https://analyzingalpha.com/episodic-pivot](https://analyzingalpha.com/episodic-pivot)  
9. Hierarchical Clustering in Risk-Based Portfolio Construction \- DiVA portal, accessed on December 26, 2025, [https://www.diva-portal.org/smash/get/diva2:1609991/FULLTEXT01.pdf](https://www.diva-portal.org/smash/get/diva2:1609991/FULLTEXT01.pdf)  
10. Nested Clusters Optimization \- skfolio, accessed on December 26, 2025, [https://skfolio.org/auto\_examples/clustering/plot\_4\_nco.html](https://skfolio.org/auto_examples/clustering/plot_4_nco.html)  
11. HRP \- Recursive Bisection \- Why bisect instead of cut based on subset? : r/quant \- Reddit, accessed on December 26, 2025, [https://www.reddit.com/r/quant/comments/171oihj/hrp\_recursive\_bisection\_why\_bisect\_instead\_of\_cut/](https://www.reddit.com/r/quant/comments/171oihj/hrp_recursive_bisection_why_bisect_instead_of_cut/)  
12. Residual momentum \- IDEAS/RePEc, accessed on December 26, 2025, [https://ideas.repec.org/a/eee/empfin/v18y2011i3p506-521.html](https://ideas.repec.org/a/eee/empfin/v18y2011i3p506-521.html)  
13. Residual Momentum \- RePub, Erasmus University Repository, accessed on December 26, 2025, [https://repub.eur.nl/pub/22252/ResidualMomentum-2011.pdf](https://repub.eur.nl/pub/22252/ResidualMomentum-2011.pdf)  
14. Volatility Scaling for Momentum Strategies? \- CXO Advisory, accessed on December 26, 2025, [https://www.cxoadvisory.com/volatility-effects/volatility-scaling-for-momentum-strategies/](https://www.cxoadvisory.com/volatility-effects/volatility-scaling-for-momentum-strategies/)  
15. Machine Learning for Trading Pairs Selection \- Hudson & Thames, accessed on December 26, 2025, [https://hudsonthames.org/employing-machine-learning-for-trading-pairs-selection/](https://hudsonthames.org/employing-machine-learning-for-trading-pairs-selection/)  
16. ML Based Pairs Selection — arbitragelab 1.0.0 documentation, accessed on December 26, 2025, [https://hudson-and-thames-arbitragelab.readthedocs-hosted.com/en/latest/ml\_approach/ml\_based\_pairs\_selection.html](https://hudson-and-thames-arbitragelab.readthedocs-hosted.com/en/latest/ml_approach/ml_based_pairs_selection.html)  
17. Research/Analysis/02 Kalman Filter Based Pairs Trading.ipynb at master \- GitHub, accessed on December 26, 2025, [https://github.com/QuantConnect/Research/blob/master/Analysis/02%20Kalman%20Filter%20Based%20Pairs%20Trading.ipynb](https://github.com/QuantConnect/Research/blob/master/Analysis/02%20Kalman%20Filter%20Based%20Pairs%20Trading.ipynb)  
18. Dynamic Hedge Ratio Between ETF Pairs Using the Kalman Filter \- QuantStart, accessed on December 26, 2025, [https://www.quantstart.com/articles/Dynamic-Hedge-Ratio-Between-ETF-Pairs-Using-the-Kalman-Filter/](https://www.quantstart.com/articles/Dynamic-Hedge-Ratio-Between-ETF-Pairs-Using-the-Kalman-Filter/)  
19. Optimizing Sparse Mean-Reverting Portfolio \- arXiv, accessed on December 26, 2025, [https://arxiv.org/pdf/2406.17155](https://arxiv.org/pdf/2406.17155)  
20. Volatility Risk Premium Effect \- Quantpedia, accessed on December 26, 2025, [https://quantpedia.com/strategies/volatility-risk-premium-effect](https://quantpedia.com/strategies/volatility-risk-premium-effect)  
21. Iron Condor options strategy \- Fidelity Investments, accessed on December 26, 2025, [https://www.fidelity.com/viewpoints/active-investor/iron-condor-strategy](https://www.fidelity.com/viewpoints/active-investor/iron-condor-strategy)  
22. The Iron Condor Strategy: A Guide to Options Trading Neutral Markets | Market Insights, accessed on December 26, 2025, [https://www.tradestation.com/insights/2025/10/28/iron-condor-strategy-for-trading-neutral-markets-tradestation/](https://www.tradestation.com/insights/2025/10/28/iron-condor-strategy-for-trading-neutral-markets-tradestation/)  
23. Using SVXY to Capture the Volatility Risk Premium \- CXO Advisory, accessed on December 26, 2025, [https://www.cxoadvisory.com/volatility-effects/using-svxy-to-capture-the-volatility-risk-premium/](https://www.cxoadvisory.com/volatility-effects/using-svxy-to-capture-the-volatility-risk-premium/)  
24. the value of short volatility strategies | gmo, accessed on December 26, 2025, [https://www.gmo.com/globalassets/articles/insights/global-equity/2018/ncvl\_value-of-short-volatility-strategies\_2-18.pdf](https://www.gmo.com/globalassets/articles/insights/global-equity/2018/ncvl_value-of-short-volatility-strategies_2-18.pdf)  
25. The Art of Hedging | Risk Management Newsletter \- SOA, accessed on December 26, 2025, [https://www.soa.org/globalassets/assets/library/newsletters/risk-management-newsletter/2015/august/jrm-2015-iss33-lerner-metli.pdf](https://www.soa.org/globalassets/assets/library/newsletters/risk-management-newsletter/2015/august/jrm-2015-iss33-lerner-metli.pdf)  
26. Tail risk hedging with VIX Calls \- Stanford University, accessed on December 26, 2025, [http://stanford.edu/class/msande448/2021/Final\_reports/gr7.pdf](http://stanford.edu/class/msande448/2021/Final_reports/gr7.pdf)  
27. Market Regime using Hidden Markov Model \- QuantInsti Blog, accessed on December 26, 2025, [https://blog.quantinsti.com/regime-adaptive-trading-python/](https://blog.quantinsti.com/regime-adaptive-trading-python/)  
28. Intraday Application of Hidden Markov Models \- QuantConnect.com, accessed on December 26, 2025, [https://www.quantconnect.com/research/17900/intraday-application-of-hidden-markov-models/](https://www.quantconnect.com/research/17900/intraday-application-of-hidden-markov-models/)  
29. Exploration of Hierarchical Clustering in Long-Only Risk-Based Portfolio Optimization \- Research@CBS, accessed on December 26, 2025, [https://research-api.cbs.dk/ws/portalfiles/portal/62178444/879726\_Master\_Thesis\_Nima\_Daniel\_15736.pdf](https://research-api.cbs.dk/ws/portalfiles/portal/62178444/879726_Master_Thesis_Nima_Daniel_15736.pdf)  
30. Meta Labeling (A Toy Example) \- Hudson & Thames, accessed on December 26, 2025, [https://hudsonthames.org/meta-labeling-a-toy-example/](https://hudsonthames.org/meta-labeling-a-toy-example/)  
31. Meta-Labeling \- Wikipedia, accessed on December 26, 2025, [https://en.wikipedia.org/wiki/Meta-Labeling](https://en.wikipedia.org/wiki/Meta-Labeling)