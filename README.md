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
├── requirements.txt                # Initial project dependencies
├── README.md                       # Project documentation and theoretical overview
├── .gitignore                      # Python and environment ignore rules
├── src/
│   ├── __init__.py                 # Package marker
│   ├── exchange_rates.py           # Rate matrix representation and validation
│   ├── graph_builder.py            # Digraph construction with negative log weights
│   ├── arbitrage_detector.py       # Custom Bellman-Ford negative cycle detection
│   └── profit_calculator.py        # Arbitrage return and step execution calculations
├── tests/
│   ├── __init__.py                 # Test package marker
│   └── test_arbitrage_detector.py  # Unit tests for arbitrage detection
└── docs/
    └── mathematical_framework.md   # Mathematical equations, proofs, and examples
```

---

## 🛠️ Planned Core Modules

- **`src/exchange_rates.py`:** Stores and validates conversion matrices and currency pairs.
- **`src/graph_builder.py`:** Maps exchange rate data to directed graphs with weights $w(u, v) = -\ln(R_{u,v})$.
- **`src/arbitrage_detector.py`:** Implements our custom Bellman–Ford algorithm to identify negative cycles and extract cycle paths.
- **`src/profit_calculator.py`:** Computes compounding yields and percentage returns from detected cycles.
- **`app.py`:** Streamlit-based graphical interface for interactive matrix inputs, graph visualization, and detection execution.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+ installed

### Setup (When Ready)
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

---

## ⚠️ Scope and Academic Notice

This project is built strictly for educational and analytical purposes as part of a Discrete Mathematics course. It does not connect to live exchanges, execute real trades, require API keys, or provide financial advice.