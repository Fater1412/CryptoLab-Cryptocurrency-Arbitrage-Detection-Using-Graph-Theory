# CryptoLab — Cryptocurrency Arbitrage Detection

A Discrete Mathematics project exploring graph theory applications in financial modeling. CryptoLab models cryptocurrency exchange markets as directed weighted graphs and detects profitable triangular and polygonal arbitrage opportunities using negative-weight cycle detection algorithms.

---

## 🎯 Project Objective

The primary objective of **CryptoLab** is to demonstrate how core concepts from **Discrete Mathematics**—specifically directed graphs, logarithmic reductions, and shortest-path algorithms—solve the real-world problem of currency arbitrage detection.

Arbitrage occurs when discrepancies in exchange rates across different currency pairs allow a trader to execute a sequence of trades starting and ending with the same currency, resulting in a net profit without market risk.

---

## 📐 Connection to Discrete Mathematics

This project bridges fundamental mathematical theory and computational implementation:

1. **Directed Graphs ($G = (V, E)$):**
   - **Vertices ($V$):** Distinct cryptocurrencies or fiat currencies (e.g., BTC, ETH, SOL, USD).
   - **Directed Edges ($E$):** Tradable conversion paths between currencies. An edge $(u, v)$ with exchange rate $R_{u,v}$ represents converting 1 unit of $u$ into $R_{u,v}$ units of $v$.

2. **Walks, Paths, and Directed Cycles:**
   - An arbitrage cycle is a closed directed cycle $C = (v_0, v_1, \dots, v_k = v_0)$ where:
     $$\prod_{i=0}^{k-1} R_{v_i, v_{i+1}} > 1$$

3. **Logarithmic Transformation (Product $\to$ Sum Reduction):**
   - Standard path algorithms find minimum *sums* of edge weights, while arbitrage seeks to maximize the *product* of conversion rates.
   - Taking the natural logarithm transforms multiplication into addition:
     $$\ln\left(\prod R_i\right) = \sum \ln(R_i) > 0$$
   - Multiplying by $-1$ reverses the inequality:
     $$\sum -\ln(R_i) < 0$$
   - Assigning edge weights $w(u, v) = -\ln(R_{u,v})$ reduces the arbitrage detection problem to finding a **negative-weight cycle** in a directed graph.

4. **Bellman–Ford Algorithm:**
   - Unlike Dijkstra's algorithm (which requires non-negative weights), Bellman–Ford can handle negative edge weights.
   - Running $|V| - 1$ edge relaxation passes computes shortest paths; a relaxation on the $|V|$-th pass reveals the presence of a negative cycle, allowing the precise arbitrage sequence to be reconstructed.

> **Note:** As an educational project, the core Bellman–Ford algorithm and cycle reconstruction logic are implemented directly from scratch rather than relying on library black boxes.

---

## 📁 Project Structure

```text
CryptoLab/
├── app.py                          # Streamlit interactive dashboard entry point
├── requirements.txt                # Project dependencies (streamlit, pandas, networkx, plotly)
├── README.md                       # Project documentation and theoretical overview
├── .gitignore                      # Python and environment ignore rules
├── src/
│   ├── __init__.py                 # Package marker
│   ├── exchange_rates.py           # Rate dataclasses, validation, and simulated sample datasets
│   ├── graph_builder.py            # Digraph construction with negative log weights (-ln R)
│   ├── arbitrage_detector.py       # Custom Bellman-Ford negative-weight cycle detection
│   └── profit_calculator.py        # Compounding yields, step audit, and fee simulation
├── tests/
│   ├── __init__.py                 # Test package marker
│   ├── test_exchange_rates.py      # Unit tests for rates and validation
│   ├── test_graph_builder.py       # Unit tests for digraph construction and log weights
│   ├── test_arbitrage_detector.py  # Unit tests for Bellman-Ford cycle detection
│   └── test_profit_calculator.py   # Unit tests for profit and transaction-fee simulator
└── docs/
    └── mathematical_framework.md   # Mathematical equations, proofs, and examples
```

---

## 🛠️ Implemented Core Modules

- **`src/exchange_rates.py`:** Provides the `ConversionRate` dataclass, symbol validation, and simulated exchange rate datasets.
- **`src/graph_builder.py`:** Constructs directed weighted graphs (NetworkX `DiGraph`) with original conversion rates and negative logarithmic edge weights $w(u, v) = -\ln(R_{u,v})$.
- **`src/arbitrage_detector.py`:** Implements our custom Bellman–Ford algorithm from scratch with multi-component zero-initialization, edge relaxation, and predecessor backtracking to recover directed cycles.
- **`src/profit_calculator.py`:** Simulates multi-hop capital compounding across detected cycles, deducting per-hop transaction fees and calculating gross/net profit, net returns, and breakeven fee thresholds ($f^*$).
- **`app.py`:** Interactive Streamlit web dashboard with Plotly network digraph visualization, an exchange rate manager, real-time cycle detection, and fee simulation.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+ installed

### Setup & Installation
1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Streamlit dashboard:
   ```bash
   streamlit run app.py
   ```
   Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🧪 Running Unit Tests

The test suite is built entirely with Python's standard `unittest` framework and requires no third-party test runners:

```bash
# Run all project tests with discovery
python -m unittest discover tests -v

# Run individual test modules
python -m unittest tests/test_exchange_rates.py -v
python -m unittest tests/test_graph_builder.py -v
python -m unittest tests/test_arbitrage_detector.py -v
python -m unittest tests/test_profit_calculator.py -v
```

---

## ⚠️ Scope, Assumptions, and Real-World Limitations

This project is built strictly for educational and analytical purposes as part of a Discrete Mathematics course.

- **Simulated Data:** All exchange rates provided or demonstrated in this repository are illustrative, simulated data. The project does not connect to live exchanges, execute real trades, or require API keys.
- **Simplified Simulation Model:** In production markets, real-world execution is subject to market frictions not included in this educational model:
  1. **Slippage:** Real orders walk the order book, shifting execution prices unfavorably.
  2. **Liquidity Depth:** Quoted rates assume infinite liquidity; actual order book volume is finite.
  3. **Withdrawal Fees:** Moving assets across exchanges incurs flat or percentage withdrawal charges.
  4. **Network Gas Fees:** On-chain decentralized exchange swaps incur variable blockchain transaction fees independent of trade volume.