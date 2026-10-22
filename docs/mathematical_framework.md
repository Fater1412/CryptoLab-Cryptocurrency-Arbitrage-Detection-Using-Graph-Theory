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

## 3. Algorithm: Bellman–Ford Negative Cycle Detection

### 3.1 Overview
The **Bellman–Ford algorithm** solves the single-source shortest paths problem in directed graphs that may contain negative edge weights. If a graph contains no negative cycles reachable from the source, the shortest paths are guaranteed to converge after $|V| - 1$ relaxation passes.

If an edge can still be relaxed on the $|V|$-th pass, that edge belongs to or is reachable from a **negative-weight cycle** (an arbitrage opportunity).

### 3.2 Relaxation Step
For an edge $(u, v)$ with weight $w(u, v)$:
$$\text{if } d[u] + w(u, v) < d[v]:$$
$$d[v] = d[u] + w(u, v)$$
$$\pi[v] = u$$
where $d[v]$ is the estimated distance to vertex $v$, and $\pi[v]$ is the predecessor of $v$.

### 3.3 Negative Cycle Recovery
1. Run $|V| - 1$ passes of edge relaxations over all edges in $E$.
2. On pass $|V|$, check if any edge $(u, v)$ satisfies:
   $$d[u] + w(u, v) < d[v]$$
3. If such an edge is found, trace predecessors backwards $|V|$ steps to guarantee entry into the cycle, then collect vertices until the cycle repeats.

---

## 4. Complexity Analysis

| Metric | Complexity | Notes |
| :--- | :--- | :--- |
| **Time Complexity** | $\mathcal{O}(\|V\| \cdot \|E\|)$ | In a fully connected currency network with $N$ currencies, $\|E\| \le N(N - 1)$, yielding $\mathcal{O}(N^3)$. |
| **Space Complexity** | $\mathcal{O}(\|V\| + \|E\|)$ | Stores distance array $d$, predecessor array $\pi$, and the adjacency representation of $G$. |

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
