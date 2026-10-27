"""
CryptoLab — Cryptocurrency Arbitrage Detection Dashboard

An interactive Discrete Mathematics simulation and research laboratory
demonstrating cryptocurrency arbitrage detection using directed graph theory,
negative-weight cycle detection (Bellman-Ford algorithm), and transaction-fee simulation.

DISCLAIMER: All exchange rates and scenarios in this application are illustrative,
simulated data for educational purposes only. No live market feeds, wallets,
or real financial trading are involved.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import pandas as pd
except ImportError:
    pd = None

import plotly.graph_objects as go
import streamlit as st

from src.arbitrage_detector import ArbitrageResult, detect_arbitrage
from src.exchange_rates import (
    SIMULATION_DISCLAIMER,
    ConversionRate,
    get_arbitrage_sample_rates,
    get_fee_consumed_sample_rates,
    get_inr_arbitrage_sample_rates,
    get_sample_rates,
    validate_conversion_rate,
)
from src.graph_builder import build_graph, calculate_log_weight
from src.profit_calculator import ProfitResult, calculate_profit


# ==============================================================================
# Helper Functions: Data Formatting & Resilient Table Display
# ==============================================================================

def render_table(headers: List[str], rows: List[List[Any]]) -> None:
    """
    Render a clean, responsive HTML table in Streamlit.
    Provides a resilient table viewer that operates independently of
    platform-specific compiled C-extension policies.
    """
    if pd is not None:
        try:
            df = pd.DataFrame(rows, columns=headers)
            st.dataframe(df, use_container_width=True)
            return
        except Exception:
            pass

    # HTML table fallback
    header_html = "".join(
        f'<th style="padding: 10px 14px; text-align: left; font-weight: 600; '
        f'border-bottom: 2px solid rgba(128, 128, 128, 0.3);">{h}</th>'
        for h in headers
    )

    body_rows: List[str] = []
    for idx, row in enumerate(rows):
        bg = 'background-color: rgba(128, 128, 128, 0.05);' if idx % 2 == 1 else ''
        cells = "".join(
            f'<td style="padding: 8px 14px; border-bottom: 1px solid rgba(128, 128, 128, 0.15);">{cell}</td>'
            for cell in row
        )
        body_rows.append(f'<tr style="{bg}">{cells}</tr>')

    table_html = (
        '<div style="overflow-x: auto; margin: 12px 0; border-radius: 8px; '
        'border: 1px solid rgba(128, 128, 128, 0.2);">'
        '<table style="width: 100%; border-collapse: collapse; font-family: -apple-system, '
        'BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; font-size: 0.92rem;">'
        f'<thead><tr style="background-color: rgba(128, 128, 128, 0.12);">{header_html}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)


# ==============================================================================
# Helper Functions: Plotly Directed Graph Visualization
# ==============================================================================

def create_directed_network_figure(
    graph: Any,
    highlight_cycle: Optional[List[str]] = None,
) -> go.Figure:
    """
    Generate an interactive Plotly visualization for the directed currency graph.

    - Vertices arranged in a clear circular layout with currency badges.
    - Directed curved edges with distinct arrow annotations indicating conversion direction.
    - Rate annotations positioned along each edge.
    - If a profitable cycle is passed, its edges and vertices are prominently highlighted.
    """
    fig = go.Figure()

    if graph is None or graph.number_of_nodes() == 0:
        fig.add_annotation(
            text="Currency graph is empty. Please add exchange rate pairs to visualize the network.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="#888888"),
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=450,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        return fig

    nodes = sorted(list(graph.nodes()))
    num_nodes = len(nodes)

    # Compute 2D coordinates using circular layout
    coords: Dict[str, Tuple[float, float]] = {}
    radius = 1.0
    for idx, node in enumerate(nodes):
        angle = 2.0 * math.pi * idx / num_nodes
        coords[node] = (radius * math.cos(angle), radius * math.sin(angle))

    # Identify cycle edges for accent highlighting
    cycle_edge_set = set()
    if highlight_cycle and len(highlight_cycle) >= 3:
        for i in range(len(highlight_cycle) - 1):
            cycle_edge_set.add((highlight_cycle[i], highlight_cycle[i + 1]))

    # Draw directed edges
    annotations = []
    for u, v, data in graph.edges(data=True):
        x0, y0 = coords[u]
        x1, y1 = coords[v]
        rate = data.get("rate", 1.0)
        weight = data.get("weight", 0.0)

        is_cycle_edge = (u, v) in cycle_edge_set

        # Color and line width
        edge_color = "#00C853" if is_cycle_edge else "rgba(100, 149, 237, 0.45)"
        edge_width = 3.5 if is_cycle_edge else 1.5

        # Compute curvature so bidirectional edges (u -> v and v -> u) separate cleanly
        dx = x1 - x0
        dy = y1 - y0
        dist = math.hypot(dx, dy)
        if dist == 0:
            continue

        # Perpendicular unit normal vector (curves to the right of direction of travel)
        nx = -dy / dist
        ny = dx / dist
        curvature_offset = 0.16
        xc = (x0 + x1) / 2.0 + curvature_offset * nx
        yc = (y0 + y1) / 2.0 + curvature_offset * ny

        # Quadratic Bezier curve points: B(t) = (1-t)^2 P0 + 2(1-t)t Pc + t^2 P1
        curve_pts = 25
        curve_x: List[float] = []
        curve_y: List[float] = []
        for step in range(curve_pts + 1):
            t = step / curve_pts
            bx = ((1.0 - t) ** 2) * x0 + 2.0 * (1.0 - t) * t * xc + (t ** 2) * x1
            by = ((1.0 - t) ** 2) * y0 + 2.0 * (1.0 - t) * t * yc + (t ** 2) * y1
            curve_x.append(bx)
            curve_y.append(by)

        hover_info = (
            f"<b>{u} ➔ {v}</b><br>"
            f"Rate: {rate:.6f}<br>"
            f"Log Weight: {weight:.6f}<br>"
            f"{'★ PART OF ARBITRAGE CYCLE' if is_cycle_edge else ''}"
        )

        fig.add_trace(
            go.Scatter(
                x=curve_x,
                y=curve_y,
                mode="lines",
                line=dict(color=edge_color, width=edge_width),
                hoverinfo="text",
                text=hover_info,
                showlegend=False,
            )
        )

        # Draw directed arrowhead near target vertex (at t ≈ 0.88)
        arrow_t = 0.88
        ax_pt = ((1.0 - arrow_t) ** 2) * x0 + 2.0 * (1.0 - arrow_t) * arrow_t * xc + (arrow_t ** 2) * x1
        ay_pt = ((1.0 - arrow_t) ** 2) * y0 + 2.0 * (1.0 - arrow_t) * arrow_t * yc + (arrow_t ** 2) * y1

        prev_t = 0.80
        prev_x = ((1.0 - prev_t) ** 2) * x0 + 2.0 * (1.0 - prev_t) * prev_t * xc + (prev_t ** 2) * x1
        prev_y = ((1.0 - prev_t) ** 2) * y0 + 2.0 * (1.0 - prev_t) * prev_t * yc + (prev_t ** 2) * y1

        annotations.append(
            dict(
                x=ax_pt,
                y=ay_pt,
                ax=prev_x,
                ay=prev_y,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.4 if is_cycle_edge else 1.0,
                arrowwidth=2.5 if is_cycle_edge else 1.2,
                arrowcolor=edge_color,
            )
        )

        # Rate label near the apex of the curve (t ≈ 0.50)
        mid_x = xc
        mid_y = yc
        rate_str = f"{rate:.4g}"
        annotations.append(
            dict(
                x=mid_x,
                y=mid_y,
                text=rate_str,
                showarrow=False,
                font=dict(
                    size=10,
                    color="#00C853" if is_cycle_edge else "#B0BEC5",
                ),
                bgcolor="rgba(20, 24, 33, 0.85)",
                bordercolor=edge_color if is_cycle_edge else "rgba(100, 149, 237, 0.3)",
                borderwidth=1,
                borderpad=2,
            )
        )

    # Draw vertices
    node_x = [coords[n][0] for n in nodes]
    node_y = [coords[n][1] for n in nodes]

    cycle_nodes_set = set(highlight_cycle) if highlight_cycle else set()
    node_colors = [
        "#00C853" if n in cycle_nodes_set else "#1E88E5"
        for n in nodes
    ]

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            marker=dict(
                size=44,
                color=node_colors,
                line=dict(color="#FFFFFF", width=2),
                opacity=0.95,
            ),
            text=nodes,
            textposition="middle center",
            textfont=dict(size=12, color="#FFFFFF", family="Arial Black, sans-serif"),
            hoverinfo="text",
            hovertext=[f"Currency Vertex: <b>{n}</b>" for n in nodes],
            showlegend=False,
        )
    )

    fig.update_layout(
        annotations=annotations,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=540,
        margin=dict(l=30, r=30, t=30, b=30),
        plot_bgcolor="rgba(0, 0, 0, 0)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
    )

    return fig


# ==============================================================================
# Main Streamlit Application
# ==============================================================================

def main() -> None:
    st.set_page_config(
        page_title="CryptoLab — Arbitrage Detection",
        page_icon="🪙",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --------------------------------------------------------------------------
    # Session State Initialization
    # --------------------------------------------------------------------------
    if "rates" not in st.session_state:
        st.session_state["rates"] = get_arbitrage_sample_rates()

    if "current_preset" not in st.session_state:
        st.session_state["current_preset"] = "arbitrage"

    # --------------------------------------------------------------------------
    # Header & Project Overview
    # --------------------------------------------------------------------------
    st.title("🪙 CryptoLab — Cryptocurrency Arbitrage Detection")
    st.markdown(
        "**Discrete Mathematics & Graph Theory Laboratory** • "
        "*Simulating negative-weight cycle detection using the Bellman–Ford algorithm*"
    )

    # Prominent simulation disclaimer
    st.warning(
        f"⚠️ **{SIMULATION_DISCLAIMER}** "
        "This research tool demonstrates theoretical graph modeling and algorithm analysis; "
        "it does not connect to live trading APIs or execute actual financial transactions."
    )

    with st.expander("ℹ️ Project Overview & Graph Theoretical Methodology", expanded=False):
        st.markdown(
            r"""
            ### What is Cryptocurrency Arbitrage?
            **Arbitrage** is the simultaneous conversion of capital across multiple currencies
            to exploit pricing discrepancies and yield a risk-free gain. In foreign exchange
            and cryptocurrency markets, this often occurs across three or more assets as **triangular**
            or **multi-hop arbitrage**.

            ### The Graph Theory Transformation
            1. **Directed Currency Digraph:** Each cryptocurrency is modeled as a vertex $v \in V$,
               and each executable conversion is modeled as a directed edge $(u, v) \in E$ with conversion rate $R_{u,v} > 0$.
            2. **Multiplicative Arbitrage Condition:** A closed directed cycle $C = (c_0, c_1, \dots, c_k = c_0)$
               is profitable if and only if the product of its conversion rates exceeds unity:
               $$\prod_{i=1}^k R_i > 1.0$$
            3. **Logarithmic Edge Weights:** Standard shortest-path algorithms require additive edge weights.
               Taking the negative natural logarithm of both sides transforms multiplication into addition:
               $$\prod_{i=1}^k R_i > 1.0 \iff \sum_{i=1}^k -\ln(R_i) < 0.0$$
            4. **Equivalence Theorem:** A profitable arbitrage cycle exists **if and only if** the directed graph
               contains a **negative-weight cycle** with edge weights $w(u, v) = -\ln(R_{u,v})$.
            5. **Bellman-Ford Algorithm:** We execute a custom Bellman-Ford detector in $\mathcal{O}(|V| \cdot |E|)$ time
               with multi-component zero-initialization to identify and reconstruct profitable cycles.
            """
        )

    # --------------------------------------------------------------------------
    # Sidebar: Exchange Rate Manager
    # --------------------------------------------------------------------------
    st.sidebar.header("⚙️ Exchange Rate Manager")

    st.sidebar.markdown("#### Preset Simulated Datasets")
    preset_options = [
        "Triangular Arbitrage (+2.5% Gross)",
        "Indian Market INR Arbitrage (+2.27% Gross)",
        "Fee-Consumed Opportunity (+0.5% Gross)",
        "Market Equilibrium (No Arbitrage)",
    ]

    current_idx = 0
    if st.session_state["current_preset"] == "inr_arbitrage":
        current_idx = 1
    elif st.session_state["current_preset"] == "fee_consumed":
        current_idx = 2
    elif st.session_state["current_preset"] == "equilibrium":
        current_idx = 3

    preset_choice = st.sidebar.radio(
        "Load Preset Market Scenario:",
        options=preset_options,
        index=current_idx,
    )

    col_btn1, col_btn2 = st.sidebar.columns(2)
    with col_btn1:
        if st.button("📥 Apply Preset", use_container_width=True):
            if "Indian" in preset_choice or "INR" in preset_choice:
                st.session_state["rates"] = get_inr_arbitrage_sample_rates()
                st.session_state["current_preset"] = "inr_arbitrage"
                st.sidebar.success("Loaded Indian Market INR arbitrage dataset (+2.27%).")
            elif "Triangular" in preset_choice:
                st.session_state["rates"] = get_arbitrage_sample_rates()
                st.session_state["current_preset"] = "arbitrage"
                st.sidebar.success("Loaded triangular arbitrage dataset (+2.5%).")
            elif "Fee-Consumed" in preset_choice:
                st.session_state["rates"] = get_fee_consumed_sample_rates()
                st.session_state["current_preset"] = "fee_consumed"
                st.sidebar.success("Loaded fee-consumed dataset (+0.5%).")
            else:
                st.session_state["rates"] = get_sample_rates()
                st.session_state["current_preset"] = "equilibrium"
                st.sidebar.success("Loaded equilibrium dataset.")
            st.rerun()

    with col_btn2:
        if st.button("🔄 Reset Default", use_container_width=True):
            st.session_state["rates"] = get_arbitrage_sample_rates()
            st.session_state["current_preset"] = "arbitrage"
            st.sidebar.info("Reset to default rates.")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Add or Update Conversion Rate")

    with st.sidebar.form("add_rate_form", clear_on_submit=False):
        new_source = st.text_input("Source Currency (e.g. BTC):", value="").strip().upper()
        new_target = st.text_input("Target Currency (e.g. ETH):", value="").strip().upper()
        new_rate_str = st.text_input("Exchange Rate (units of target per source):", value="").strip()
        submit_rate = st.form_submit_button("➕ Save Conversion Rate", use_container_width=True)

        if submit_rate:
            if not new_source or not new_target:
                st.error("Both Source and Target currency symbols are required.")
            elif new_source == new_target:
                st.error("Self-conversion is not permitted (Source and Target must differ).")
            else:
                try:
                    parsed_rate = float(new_rate_str)
                    if parsed_rate <= 0 or math.isnan(parsed_rate) or math.isinf(parsed_rate):
                        st.error("Exchange rate must be a finite, strictly positive number (> 0).")
                    else:
                        validated_rate = validate_conversion_rate(
                            new_source, new_target, parsed_rate
                        )
                        # Replace existing edge or append new
                        updated_rates = [
                            r for r in st.session_state["rates"]
                            if not (r.source == validated_rate.source and r.target == validated_rate.target)
                        ]
                        updated_rates.append(validated_rate)
                        st.session_state["rates"] = updated_rates
                        st.session_state["current_preset"] = "custom"
                        st.success(f"Added rate: 1 {new_source} = {parsed_rate} {new_target}")
                        st.rerun()
                except (ValueError, TypeError) as err:
                    st.error(f"Invalid rate: {err}")
                except Exception as err:
                    st.error(f"Error saving conversion rate: {err}")

    # Build graph from current session state rates
    current_rates: List[ConversionRate] = st.session_state["rates"]
    graph = build_graph(current_rates)

    # Run Bellman-Ford arbitrage detector
    arb_result: ArbitrageResult = detect_arbitrage(graph)

    # --------------------------------------------------------------------------
    # Main Dashboard Tabs
    # --------------------------------------------------------------------------
    tab_overview, tab_graph, tab_detector, tab_profit, tab_math = st.tabs(
        [
            "📊 Exchange Rates",
            "🕸️ Network Digraph",
            "🔍 Bellman–Ford Detection",
            "💰 Profit & Fee Simulator",
            "📐 Mathematical Framework",
        ]
    )

    # ==========================================================================
    # Tab 1: Exchange Rates Table
    # ==========================================================================
    with tab_overview:
        st.subheader("Current Directed Exchange Rates")
        st.caption(
            "Each row represents an executable directed edge from a Source currency to a Target currency. "
            "Edge weights are computed via $w(u, v) = -\\ln(\\text{rate})$."
        )

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Total Currencies (|V|)", graph.number_of_nodes())
        with col_m2:
            st.metric("Directed Conversions (|E|)", graph.number_of_edges())
        with col_m3:
            st.metric(
                "Arbitrage Status",
                "Opportunity Detected" if arb_result.has_arbitrage else "Equilibrium (No Arbitrage)",
            )

        # Build table rows
        rate_headers = ["Source", "➔", "Target", "Conversion Rate", "Log Weight: -ln(Rate)"]
        rate_rows = []
        for r in current_rates:
            w = calculate_log_weight(r.rate)
            rate_rows.append([
                r.source,
                "➔",
                r.target,
                f"{r.rate:.6f}",
                f"{w:+.6f}",
            ])

        render_table(rate_headers, rate_rows)

    # ==========================================================================
    # Tab 2: Directed Graph Visualization
    # ==========================================================================
    with tab_graph:
        st.subheader("Directed Currency Network Visualization")
        st.caption(
            "Interactive Plotly representation of the currency digraph. "
            "Directed curved arrows indicate conversion flow. "
            "If an arbitrage cycle is detected, cycle vertices and directed edges are highlighted in green."
        )

        cycle_to_highlight = arb_result.cycle if arb_result.has_arbitrage else None
        fig = create_directed_network_figure(graph, highlight_cycle=cycle_to_highlight)
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================================================
    # Tab 3: Arbitrage Detection Results
    # ==========================================================================
    with tab_detector:
        st.subheader("Bellman–Ford Negative-Weight Cycle Detection")

        if arb_result.has_arbitrage and arb_result.cycle:
            st.success("🎯 **Arbitrage Opportunity Identified!** A directed negative-weight cycle exists.")

            cycle_str = " ➔ ".join(arb_result.cycle)
            st.markdown(f"### Cycle Path: `{cycle_str}`")

            col_a1, col_a2, col_a3, col_a4 = st.columns(4)
            with col_a1:
                st.metric("Gross Rate Product", f"{arb_result.rate_product:.6f}")
            with col_a2:
                gross_gain = (arb_result.rate_product - 1.0) * 100.0  # type: ignore
                st.metric("Gross Yield", f"{gross_gain:+.4f}%")
            with col_a3:
                st.metric("Log Weight Sum", f"{arb_result.log_weight_sum:.6f}")
            with col_a4:
                st.metric("Conversions (Hops)", len(arb_result.cycle) - 1)

            st.markdown("#### Directed Cycle Trade Breakdown")
            cycle_headers = ["Step", "From", "➔", "To", "Exchange Rate", "Logarithmic Weight"]
            cycle_rows = []
            for i in range(len(arb_result.cycle) - 1):
                u = arb_result.cycle[i]
                v = arb_result.cycle[i + 1]
                edge_rate = graph[u][v]["rate"]
                edge_weight = graph[u][v]["weight"]
                cycle_rows.append([
                    f"Hop {i + 1}",
                    u,
                    "➔",
                    v,
                    f"{edge_rate:.6f}",
                    f"{edge_weight:+.6f}",
                ])
            render_table(cycle_headers, cycle_rows)

            st.info(
                "💡 **Market Reality Notice:** The detected negative cycle represents a **theoretical gross candidate**. "
                "In live trading environments, exchange fees, order book slippage, and execution latency "
                "compound across hops and may eliminate net profitability."
            )
        else:
            st.info(
                "⚖️ **No Arbitrage Opportunity Detected.**\n\n"
                "The currency graph contains no negative-weight cycles. "
                "All shortest paths converged within $|V| - 1$ relaxation passes, "
                "confirming that the market exchange rates are in mathematical equilibrium."
            )

    # ==========================================================================
    # Tab 4: Profit & Fee Simulator
    # ==========================================================================
    with tab_profit:
        st.subheader("Arbitrage Profit & Transaction-Fee Simulator")
        st.caption(
            "Simulates multi-hop capital compounding and step-by-step transaction fee deductions "
            "for the detected closed arbitrage cycle."
        )

        if not arb_result.has_arbitrage or not arb_result.cycle:
            st.warning(
                "⚠️ **Simulation Unavailable:** No closed arbitrage cycle was detected in the current currency graph. "
                "Please select the **'Triangular Arbitrage'** preset in the sidebar or input exchange rates "
                "that form an arbitrage opportunity (rate product $> 1.0$) to enable the simulator."
            )
        else:
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                initial_capital = st.number_input(
                    f"Initial Capital ({arb_result.cycle[0]}):",
                    min_value=0.01,
                    max_value=1_000_000.0,
                    value=1000.0,
                    step=100.0,
                )
            with col_p2:
                default_fee = 0.20 if st.session_state["current_preset"] == "fee_consumed" else 0.10
                trade_fee_percent = st.slider(
                    "Transaction Fee per Conversion (%):",
                    min_value=0.0,
                    max_value=3.0,
                    value=default_fee,
                    step=0.01,
                    format="%.2f%%",
                )

            # Execute profit calculator
            profit_res: ProfitResult = calculate_profit(
                graph=graph,
                cycle=arb_result.cycle,
                initial_investment=initial_capital,
                fee_percent=trade_fee_percent,
            )

            # Breakeven fee calculation: (1 - f*)^k = 1 / Product
            k_hops = profit_res.num_conversions
            breakeven_fee = (1.0 - (1.0 / arb_result.rate_product) ** (1.0 / k_hops)) * 100.0  # type: ignore

            # Summary Metrics
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric("Initial Capital", f"{profit_res.initial_investment:,.4f} {profit_res.start_currency}")
            with m_col2:
                st.metric(
                    "Gross Final Amount",
                    f"{profit_res.gross_final_amount:,.4f} {profit_res.start_currency}",
                    delta=f"{profit_res.gross_return_percent:+.2f}%",
                )
            with m_col3:
                delta_color = "normal" if profit_res.is_profitable else "inverse"
                st.metric(
                    "Net Final (After Fees)",
                    f"{profit_res.net_final_amount:,.4f} {profit_res.start_currency}",
                    delta=f"{profit_res.net_return_percent:+.4f}%",
                    delta_color=delta_color,
                )
            with m_col4:
                st.metric("Breakeven Fee Threshold", f"{breakeven_fee:.4f}% / hop")

            if profit_res.is_profitable:
                st.success(
                    f"✅ **Net Profitable Arbitrage!** After deducting {trade_fee_percent:.2f}% per conversion, "
                    f"net profit is **{profit_res.net_profit:+.4f} {profit_res.start_currency}** "
                    f"({profit_res.net_return_percent:+.4f}% net return)."
                )
            else:
                st.error(
                    f"❌ **Net Loss:** Transaction fees ({trade_fee_percent:.2f}% per hop) exceeded the "
                    f"breakeven threshold of {breakeven_fee:.4f}%, turning theoretical gross profit into a "
                    f"net loss of **{profit_res.net_profit:+.4f} {profit_res.start_currency}** "
                    f"({profit_res.net_return_percent:+.4f}% net loss)."
                )

            st.markdown("#### Step-by-Step Conversion Audit")
            step_headers = [
                "Step",
                "Conversion",
                "Input Amount",
                "Rate",
                "Gross Received",
                f"Fee Deducted ({trade_fee_percent:.2f}%)",
                "Net Retained Amount",
            ]
            step_rows = []
            for s in profit_res.steps:
                step_rows.append([
                    f"Hop {s.step_number}",
                    f"{s.from_currency} ➔ {s.to_currency}",
                    f"{s.amount_in:,.4f} {s.from_currency}",
                    f"{s.rate:.6f}",
                    f"{s.gross_amount_out:,.4f} {s.to_currency}",
                    f"{s.fee_amount:,.4f} {s.to_currency}",
                    f"{s.net_amount_out:,.4f} {s.to_currency}",
                ])
            render_table(step_headers, step_rows)

            st.caption(
                "🔬 **Hypothetical Simulation Disclaimer:** This simulator assumes full immediate fills "
                "at quoted prices with zero slippage. In production markets, exchange withdrawal fees, "
                "order book depth limitations, and blockchain gas costs also apply."
            )

    # ==========================================================================
    # Tab 5: Mathematical Framework
    # ==========================================================================
    with tab_math:
        st.subheader("Mathematical Framework & Algorithmic Foundations")

        st.markdown(
            r"""
            ### 1. Directed Weighted Graphs
            In discrete mathematics, currency exchange networks are modeled as a **directed graph** $G = (V, E)$:
            - **Vertices ($V$):** Distinct currencies or digital tokens (e.g., BTC, ETH, USDT).
            - **Edges ($E$):** Directed pairs $(u, v)$ indicating that currency $u$ can be converted directly into currency $v$.
            - **Conversion Rate ($R_{u,v}$):** Multiplicative factor such that $1 \text{ unit of } u = R_{u,v} \text{ units of } v$.

            ---

            ### 2. Multiplicative to Additive Mapping
            A directed cycle $C = (c_0, c_1, \dots, c_k = c_0)$ represents an arbitrage opportunity if:
            $$\prod_{i=1}^k R_{c_{i-1}, c_i} > 1.0$$

            Standard shortest path algorithms (Dijkstra, Bellman-Ford) compute path lengths by **adding** edge weights,
            not multiplying them. By taking the negative natural logarithm ($\ln$):
            $$\ln\left(\prod_{i=1}^k R_i\right) > \ln(1.0) = 0 \iff \sum_{i=1}^k \ln(R_i) > 0$$

            Multiplying the entire inequality by $-1$ reverses the comparison:
            $$\sum_{i=1}^k \left(-\ln(R_i)\right) < 0.0$$

            Therefore, by defining edge weights as:
            $$w(u, v) = -\ln(R_{u,v})$$
            every profitable arbitrage cycle maps **isomorphically** to a **negative-weight cycle** in the digraph.

            ---

            ### 3. Bellman–Ford Algorithm & Negative Cycle Detection
            The Bellman–Ford algorithm solves the shortest paths problem in $\mathcal{O}(|V| \cdot |E|)$ time:
            1. **Multi-Component Distance Initialization:**
               $$d[v] = 0.0 \quad \forall v \in V$$
               Initializing all distances to $0.0$ conceptually creates a virtual source connected to every vertex with zero-weight edges,
               guaranteeing detection across disconnected subgraphs without arbitrary source selection.
            2. **Relaxation Loop ($|V| - 1$ passes):**
               For each directed edge $(u, v) \in E$:
               $$\text{if } d[u] + w(u, v) < d[v]: \quad d[v] = d[u] + w(u, v), \quad \pi[v] = u$$
            3. **Negative Cycle Verification (Pass $|V|$):**
               In a cycle-free graph, all shortest paths contain at most $|V| - 1$ edges. If any edge can *still* relax on pass $|V|$,
               a negative-weight cycle is guaranteed to exist by the Pigeonhole Principle.
            4. **Predecessor Backtracking:**
               To extract the exact cycle, backtrack $|V|$ times along predecessor pointers $\pi$ to enter the cycle,
               then trace backwards until the cycle repeats, and reverse the sequence to obtain the forward trade path.

            ---

            ### 4. Fee-Adjusted Profit Model
            At each conversion hop $i$, a transaction fee percentage $f \in [0, 100)\%$ is deducted from the received currency:
            $$A_i = A_{i-1} \times R_i \times \left(1 - \frac{f}{100}\right)$$

            Compounding across all $k$ hops:
            $$A_{\text{net}} = A_0 \times \left(\prod_{i=1}^k R_i\right) \times \left(1 - \frac{f}{100}\right)^k$$

            **Breakeven Fee Threshold ($f^*$):**
            Setting $A_{\text{net}} = A_0$ yields:
            $$f^* = \left[1 - \left(\frac{1}{\prod_{i=1}^k R_i}\right)^{1/k}\right] \times 100\%$$

            ---

            ### 5. Model Assumptions and Real-World Limitations
            The simulation model in CryptoLab is an idealized educational laboratory. Production trading systems encounter:
            1. **Slippage:** Orders are assumed to fill at the exact quoted spot rate; large orders in real markets walk the order book, worsening average execution prices.
            2. **Liquidity Constraints:** Quoted rates assume infinite top-of-book liquidity. Real markets have finite depth per price level.
            3. **Withdrawal Charges:** Transferring funds between centralized exchanges incurs flat or percentage withdrawal fees.
            4. **Network Gas Fees:** On-chain decentralized exchange (DEX) swaps incur blockchain transaction fees that are independent of trade volume.
            """
        )


if __name__ == "__main__":
    main()
