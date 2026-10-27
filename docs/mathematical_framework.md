# Mathematical Framework: Cryptocurrency Arbitrage Detection via Graph Theory

This document outlines the formal mathematical formulation, graph theoretical modeling, algorithmic foundations, and complexity analysis for the **CryptoLab** arbitrage detection project.

---

## 1. Problem Formulation and Definitions

### 1.1 Directed Graphs
In discrete mathematics, a **directed graph** (or *digraph*) is an ordered pair:
$$G = (V, E)$$
where:
- $V = \{c_1, c_2, \dots, c_n\}$ represents the set of **vertices** (currencies or tokens, e.g., BTC, ETH, USD, EUR).
- $E \subseteq V \times V$ represents the set of **directed edges** (ordered pairs $(u, v)$ denoting an executable exchange from currency $u$ to currency $v$).

### 1.2 Exchange Rates
Each directed edge $(u, v) \in E$ is associated with a strictly positive conversion rate $R_{u,v} \in \mathbb{R}^+$:
$$\text{Units of } v = \text{Units of } u \times R_{u,v}$$

### 1.3 Cycles and Arbitrage
- **Directed Walk:** An alternating sequence of vertices and edges $(v_0, e_1, v_1, \dots, e_k, v_k)$ where $e_i = (v_{i-1}, v_i)$.
- **Directed Cycle:** A closed walk $(v_0, v_1, \dots, v_k = v_0)$ where $k \ge 2$ and vertices $v_0, \dots, v_{k-1}$ are distinct.
- **Arbitrage Opportunity:** A directed cycle $C = (v_0, v_1, \dots, v_k = v_0)$ such that the product of exchange rates along the cycle exceeds unity:
$$\prod_{i=0}^{k-1} R_{v_i, v_{i+1}} > 1$$

Executing conversions along cycle $C$ yields a riskless gain: starting with $1$ unit of currency $v_0$, an agent finishes with $\prod_{i=0}^{k-1} R_{v_i, v_{i+1}} > 1$ units of $v_0$.

---

## 2. Mathematical Transformation: Multiplicative to Additive Weights

### 2.1 Motivation
Standard shortest-path algorithms (such as Dijkstra or Bellman–Ford) operate on **additive edge weights** to minimize path sums, rather than maximizing products of positive real numbers.

### 2.2 Logarithmic Mapping
Using the monotonic properties of the natural logarithm ($\ln$):
$$\prod_{i=0}^{k-1} R_{v_i, v_{i+1}} > 1 \iff \ln\left(\prod_{i=0}^{k-1} R_{v_i, v_{i+1}}\right) > \ln(1)$$

$$\sum_{i=0}^{k-1} \ln(R_{v_i, v_{i+1}}) > 0$$

Multiplying both sides by $-1$ reverses the inequality:
$$\sum_{i=0}^{k-1} \left(-\ln(R_{v_i, v_{i+1}})\right) < 0$$

### 2.3 Edge Weight Definition
Define the weight function $w: E \to \mathbb{R}$ by:
$$w(u, v) = -\ln(R_{u,v})$$

### 2.4 Theorem (Equivalence of Arbitrage and Negative-Weight Cycles)
> **Theorem:** A directed cycle $C$ represents an arbitrage opportunity if and only if $C$ is a negative-weight cycle in the weighted directed graph $G = (V, E, w)$:
> $$\sum_{(u,v) \in C} w(u, v) < 0 \iff \prod_{(u,v) \in C} R_{u,v} > 1$$

Exchange rates multiply around a cycle, while logarithms convert that multiplication into addition:
- **Product of cycle rates:** $r_1 \times r_2 \times \dots \times r_k$
- **Sum of edge weights:** $-\ln(r_1) - \ln(r_2) - \dots - \ln(r_k)$
- **Conclusion:** Therefore, any directed cycle with a conversion rate product strictly greater than $1$ ($\prod_{i=1}^k r_i > 1$) yields a negative total logarithmic weight ($\sum_{i=1}^k -\ln(r_i) < 0$).

### 2.5 Mathematical Condition vs. Real-World Trading Profitability
It is crucial to distinguish the **theoretical mathematical condition** from **actual market profitability**:
- **Frictionless Mathematical Arbitrage:** The condition $\prod r_i > 1 \iff \sum w_i < 0$ assumes ideal zero-friction markets with instantaneous trade execution.
- **Practical Market Reality:** In real cryptocurrency exchanges, theoretical arbitrage gains may be diminished or entirely wiped out by:
  1. **Exchange Fees:** Maker and taker fees (typically $0.05\% - 0.2\%$ per trade) compound over each hop of the cycle:
     $$\text{Effective Yield} = \prod_{i=1}^k \left(r_i \cdot (1 - \text{fee}_i)\right)$$
  2. **Network/Gas Fees:** Transferring funds across on-chain pools incurs fixed blockchain gas costs.
  3. **Order Book Depth & Slippage:** Larger trade volumes exhaust top-of-book liquidity, shifting execution prices unfavorably.
  4. **Latency Risk:** Price disparities can close within milliseconds before all transactions in a cycle confirm.

Thus, detecting a negative-weight cycle is a mathematically necessary prerequisite, but real-world execution requires net returns to surpass all cumulative market frictions.


---

## 3. Algorithm: Custom Bellman–Ford Negative Cycle Detection

### 3.1 Overview and Objective
The **Bellman–Ford algorithm** is a dynamic programming algorithm that solves the shortest paths problem in directed graphs containing real-valued edge weights (both positive and negative). In **CryptoLab**, we utilize Bellman–Ford not merely to compute distances, but specifically as an **arbitrage detector** capable of discovering negative-weight cycles anywhere in the currency network.

### 3.2 Distance Initialization for Multi-Component Graphs
In standard single-source shortest path problems, distances are initialized to:
$$d[s] = 0, \quad d[v] = +\infty \quad (\forall v \ne s)$$

However, a currency exchange graph may contain multiple **disconnected components** or subgraphs unreachable from an arbitrary starting vertex $s$. To solve this without adding an artificial super-source vertex:
$$\mathbf{d[v] = 0.0 \quad \forall v \in V}$$

**Why Zero Initialization Works:**
1. Conceptually, setting $d[v] = 0$ for all $v \in V$ is equivalent to attaching an imaginary source $s^*$ with directed edges $(s^*, v)$ of weight $0$ to every vertex.
2. Because there are no incoming edges to $s^*$, $s^*$ can never be part of any cycle.
3. Every vertex in every disconnected component becomes reachable at distance 0.
4. If a negative cycle exists anywhere, traversing its edges will continuously decrease distance values below zero ($0 + w < 0$), guaranteeing detection regardless of the component in which it resides.

### 3.3 The Relaxation Process
The core operation of Bellman–Ford is **edge relaxation**. For any directed edge $(u, v) \in E$ with logarithmic weight $w(u, v) = -\ln(R_{u,v})$:
$$\text{if } d[u] + w(u, v) < d[v]:$$
$$d[v] = d[u] + w(u, v)$$
$$\pi[v] = u$$
where:
- $d[v]$ represents the currently known shortest path estimate to $v$.
- $\pi[v]$ records the **predecessor** of vertex $v$ along this candidate shortest path.

In each complete pass, Bellman–Ford relaxes every directed edge $(u, v) \in E$. After $k$ relaxation passes, $d[v]$ represents the minimum weight of any walk to $v$ containing at most $k$ edges.

### 3.4 Why Relaxation on Pass $|V|$ Proves a Negative Cycle
A fundamental theorem of graph theory states:
> **Theorem:** In any directed graph with $|V|$ vertices, any simple path (a path with no repeated vertices) contains at most $|V| - 1$ edges.

- If a graph contains **no negative-weight cycles**, all shortest paths are simple paths. Therefore, the distance values $d[v]$ must completely converge within $|V| - 1$ passes.
- On the **$|V|$-th pass**, we test every edge $(u, v) \in E$ once more:
  $$\text{if } d[u] + w(u, v) < d[v] - \epsilon:$$
- If any distance can *still* be reduced on pass $|V|$, the shortest path to $v$ must contain at least $|V|$ edges.
- By the **Pigeonhole Principle**, any walk of $|V|$ edges across $|V|$ distinct vertices must visit at least one vertex more than once, forming a cycle.
- Because this cycle reduced the total distance, the sum of weights around this cycle must be strictly negative:
  $$\sum_{e \in C} w(e) < 0$$

### 3.5 Negative Cycle Reconstruction Mechanism
When an edge $(u, v)$ relaxes on the $|V|$-th pass:
1. Vertex $v$ is either directly part of the negative cycle or is reachable from it.
2. To guarantee reaching a vertex on the cycle, we backtrack along predecessor pointers $\pi$:
   $$\text{curr} = v; \quad \text{repeat } |V| \text{ times: } \text{curr} = \pi[\text{curr}]$$
   Because the longest branch leading into a cycle is at most $|V| - 1$ edges, backtracking $|V|$ steps guarantees that $\text{curr}$ lies strictly on the cycle.
3. From $\text{curr}$, we trace predecessors backwards until $\text{curr}$ is visited a second time:
   $$C_{\text{backwards}} = [\text{curr}, \pi[\text{curr}], \pi[\pi[\text{curr}]], \dots, \text{curr}]$$
4. Reversing $C_{\text{backwards}}$ yields the forward sequence of currency trades:
   $$C = [v_0, v_1, v_2, \dots, v_k = v_0]$$
5. Each directed hop $(v_i, v_{i+1})$ is validated against the actual graph edges.

### 3.6 Negative Weight Sum vs. Gross Exchange Rate Product
The relationship between our graph transformation and financial arbitrage is exact:
- **Total Logarithmic Weight:**
  $$W(C) = \sum_{i=0}^{k-1} w(v_i, v_{i+1}) = \sum_{i=0}^{k-1} \left(-\ln(R_{v_i, v_{i+1}})\right) = -\ln\left(\prod_{i=0}^{k-1} R_{v_i, v_{i+1}}\right)$$
- **Arbitrage Condition:**
  $$W(C) < 0 \iff -\ln\left(\prod_{i=0}^{k-1} R_{v_i, v_{i+1}}\right) < 0 \iff \ln\left(\prod_{i=0}^{k-1} R_{v_i, v_{i+1}}\right) > 0 \iff \prod_{i=0}^{k-1} R_{v_i, v_{i+1}} > 1.0$$
- If $\prod R_i > 1$, executing the trades around cycle $C$ increases capital, yielding a theoretical gross profit factor of $\prod R_i$.

---

## 4. Complexity Analysis

| Dimension | Complexity | Theoretical Explanation |
| :--- | :--- | :--- |
| **Time Complexity** | $\mathcal{O}(\|V\| \cdot \|E\|)$ | The algorithm performs $|V| - 1$ relaxation passes followed by 1 verification pass. Each pass scans all $\|E\|$ directed edges in $\mathcal{O}(\|E\|)$ time. Cycle reconstruction takes $\mathcal{O}(\|V\|)$ time. In a dense currency market where every pair is tradable, $\|E\| \le \|V\|(\|V\| - 1) \implies \mathcal{O}(\|V\|^3)$. |
| **Space Complexity** | $\mathcal{O}(\|V\| + \|E\|)$ | Requires $\mathcal{O}(\|V\|)$ space for the distance table $d$ and predecessor table $\pi$, plus $\mathcal{O}(\|V\| + \|E\|)$ space for storing the directed graph adjacency structures. |


---

## 5. Worked Example (Triangular Arbitrage Placeholder)

### 5.1 Currency Network
Consider 3 currencies: **USD**, **EUR**, **BTC** ($|V| = 3$).

| From / To | USD | EUR | BTC |
| :--- | :--- | :--- | :--- |
| **USD** | $1.0000$ | $0.9200$ | $0.000015$ |
| **EUR** | $1.0870$ | $1.0000$ | $0.000017$ |
| **BTC** | $68000.00$ | $62500.00$ | $1.0000$ |

### 5.2 Cycle Traversal: USD $\to$ EUR $\to$ BTC $\to$ USD
1. **USD $\to$ EUR:** $R_{USD, EUR} = 0.9200 \implies w(USD, EUR) = -\ln(0.9200) \approx 0.08338$
2. **EUR $\to$ BTC:** $R_{EUR, BTC} = 0.000017 \implies w(EUR, BTC) = -\ln(0.000017) \approx 10.98229$
3. **BTC $\to$ USD:** $R_{BTC, USD} = 68000.00 \implies w(BTC, USD) = -\ln(68000) \approx -11.12726$

### 5.3 Verification
- **Product of rates:**
  $$0.9200 \times 0.000017 \times 68000.00 = 1.06352 > 1.0 \quad (+6.35\% \text{ gain})$$
- **Sum of negative log weights:**
  $$0.08338 + 10.98229 - 11.12726 = -0.06159 < 0$$
Since the sum of edge weights is strictly negative, a negative cycle is detected, confirming the arbitrage opportunity.

---

## 6. Profit and Transaction-Fee Mathematical Framework

### 6.1 Gross Returns Formulation
Let $A_0$ denote the initial investment capital denominated in the starting currency $c_0$ of a detected arbitrage cycle $C = (c_0, c_1, \dots, c_k = c_0)$.

In a zero-fee environment, capital compounds multiplicatively across each of the $k$ directed conversion edges:
$$A_{\text{gross}} = A_0 \times \prod_{i=1}^k R_{c_{i-1}, c_i}$$

- **Gross Profit:**
  $$\Pi_{\text{gross}} = A_{\text{gross}} - A_0 = A_0 \left(\prod_{i=1}^k R_i - 1\right)$$
- **Gross Return Percentage:**
  $$\rho_{\text{gross}} = \left(\frac{\Pi_{\text{gross}}}{A_0}\right) \times 100\% = \left(\prod_{i=1}^k R_i - 1\right) \times 100\%$$

### 6.2 Fee-Adjusted Net Conversion Model
In cryptocurrency spot markets, a trading fee $f \in [0, 100)\%$ is deducted from the destination currency received at each trade hop.

For conversion step $i$ converting amount $A_{i-1}$ of currency $c_{i-1}$ to currency $c_i$:
1. **Gross Amount Received:**
   $$G_i = A_{i-1} \times R_i$$
2. **Fee Deducted:**
   $$\text{Fee}_i = G_i \times \left(\frac{f}{100}\right)$$
3. **Net Amount Retained:**
   $$A_i = G_i - \text{Fee}_i = A_{i-1} \times R_i \times \left(1 - \frac{f}{100}\right)$$

Compounding across all $k$ hops yields the **Net Final Amount**:
$$A_{\text{net}} = A_0 \times \prod_{i=1}^k \left(R_i \cdot \left(1 - \frac{f}{100}\right)\right) = A_0 \cdot \left(\prod_{i=1}^k R_i\right) \cdot \left(1 - \frac{f}{100}\right)^k$$

- **Net Profit:**
  $$\Pi_{\text{net}} = A_{\text{net}} - A_0$$
- **Net Return Percentage:**
  $$\rho_{\text{net}} = \left(\frac{A_{\text{net}} - A_0}{A_0}\right) \times 100\% = \left[\left(\prod_{i=1}^k R_i\right)\left(1 - \frac{f}{100}\right)^k - 1\right] \times 100\%$$

### 6.3 Gross Arbitrage vs. Net Profitability & Breakeven Analysis
- **Gross Arbitrage Exists:**
  $$\prod_{i=1}^k R_i > 1.0 \iff \sum_{i=1}^k -\ln(R_i) < 0$$
- **Net Profitability Achieved:**
  $$\prod_{i=1}^k \left(R_i \cdot \left(1 - \frac{f}{100}\right)\right) > 1.0 \iff \left(1 - \frac{f}{100}\right)^k \cdot \prod_{i=1}^k R_i > 1.0$$
- **Breakeven Fee Threshold ($f^*$):**
  The maximum fee percentage per hop before net profit drops to zero:
  $$\left(1 - \frac{f^*}{100}\right)^k = \frac{1}{\prod_{i=1}^k R_i} \implies f^* = \left[1 - \left(\frac{1}{\prod_{i=1}^k R_i}\right)^{1/k}\right] \times 100\%$$
  - If $f < f^*$: The cycle is net profitable ($\Pi_{\text{net}} > 0$).
  - If $f = f^*$: The cycle breaks even ($\Pi_{\text{net}} = 0$).
  - If $f > f^*$: The gross arbitrage opportunity is converted into a net loss ($\Pi_{\text{net}} < 0$).

### 6.4 Worked Numerical Example
Consider an arbitrage cycle $C = (\text{BTC} \to \text{ETH} \to \text{USDT} \to \text{BTC})$ with initial capital $A_0 = 1.0 \text{ BTC}$:

- $R_1 (\text{BTC} \to \text{ETH}) = 20.5$
- $R_2 (\text{ETH} \to \text{USDT}) = 3000.0$
- $R_3 (\text{USDT} \to \text{BTC}) = \frac{1}{60000.0} \approx 0.000016667$
- Gross Rate Product: $20.5 \times 3000.0 \times \frac{1}{60000.0} = \mathbf{1.025}$ ($+2.50\%$ gross profit)

#### Execution Steps with $0.10\%$ Fee ($f = 0.10\%$, retention factor $= 0.999$):
| Step | Conversion | Input Amount | Rate | Gross Out | Fee Paid ($0.1\%$) | Net Out |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | BTC $\to$ ETH | $1.000000 \text{ BTC}$ | $20.50$ | $20.500000 \text{ ETH}$ | $0.020500 \text{ ETH}$ | $20.479500 \text{ ETH}$ |
| **2** | ETH $\to$ USDT | $20.479500 \text{ ETH}$ | $3000.00$ | $61,438.500000 \text{ USDT}$ | $61.438500 \text{ USDT}$ | $61,377.061500 \text{ USDT}$ |
| **3** | USDT $\to$ BTC | $61,377.061500 \text{ USDT}$ | $\frac{1}{60000}$ | $1.022951 \text{ BTC}$ | $0.001023 \text{ BTC}$ | $\mathbf{1.021928 \text{ BTC}}$ |

- **Net Profit:** $1.021928 - 1.000000 = \mathbf{+0.021928 \text{ BTC}}$ ($\mathbf{+2.1928\% \text{ net return}}$).

#### Impact of Higher Fees:
- **At $f = 1.00\%$:** Retention factor is $(0.99)^3 \approx 0.970299$.
  $$A_{\text{net}} = 1.0 \times 1.025 \times 0.970299 \approx \mathbf{0.994556 \text{ BTC}} \implies \mathbf{-0.5444\% \text{ net loss}}.$$
- **Breakeven Fee ($f^*$):**
  $$f^* = \left[1 - \left(\frac{1}{1.025}\right)^{1/3}\right] \times 100\% \approx \mathbf{0.8197\% \text{ per trade}}.$$

### 6.5 Model Assumptions and Real-World Limitations
> **Academic and Simulation Scope:** The mathematical simulator implemented in `src/profit_calculator.py` is intentionally designed as an idealized, deterministic conversion model for educational and research analysis. In live production trading systems, several critical market frictions must be considered.
>
> Specifically, the simplified simulator model does **NOT** include:
> 1. **Slippage:** The model assumes transactions execute exactly at the quoted conversion rate regardless of capital size. In live markets, sizable orders exhaust the best bid/ask quotes and walk the order book, resulting in unfavorable average execution prices (price slippage).
> 2. **Liquidity Constraints:** The model assumes unbounded (infinite) market depth at the top of the book. In reality, available volume at a specific rate is finite, limiting the maximum profitable capital that can be deployed through any single cycle.
> 3. **Withdrawal Charges:** Centralized exchanges typically assess fixed or tiered cryptocurrency withdrawal fees when moving funds between platforms or into self-custodial wallets. These discrete costs are omitted from the per-conversion percentage model.
> 4. **Network Gas Fees:** On-chain arbitrage executed across decentralized exchanges (DEXs) or cross-chain bridges incurs variable blockchain transaction costs (gas fees, priority fees, and contract execution overhead) that are independent of trade size and can easily outweigh gross arbitrage profits.
> 5. **Execution Latency and Front-Running:** Sequential multi-leg execution introduces latency risk: prices may shift between hops before all transactions confirm, or transactions may be front-run / sandwiched by Maximal Extractable Value (MEV) searcher bots.


