"""
Graph Builder Module for CryptoLab

Constructs directed weighted graphs from cryptocurrency exchange rates.
Transforms multiplicative exchange rates into additive edge weights using
the negative natural logarithm:

    weight(u, v) = -ln(rate(u, v))

This transformation maps the problem of finding a profitable arbitrage cycle
(product of rates > 1) to detecting a negative-weight cycle (sum of weights < 0)
in a directed graph.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import networkx as nx
except ImportError:
    nx = None

from src.exchange_rates import ConversionRate, get_sample_rates, validate_rates


def calculate_log_weight(rate: Any) -> float:
    """
    Calculate the logarithmic edge weight for an exchange rate.

    Formula:
        weight = -ln(rate)

    Properties:
        - If rate > 1.0: weight is negative (< 0)
        - If rate == 1.0: weight is zero (0.0)
        - If 0.0 < rate < 1.0: weight is positive (> 0)

    Args:
        rate: Numeric exchange rate (> 0).

    Returns:
        float: Calculated negative natural log weight.

    Raises:
        TypeError: If rate is a boolean or non-numeric type.
        ValueError: If rate is non-finite (NaN, Inf) or <= 0.
    """
    # Reject boolean explicitly (in Python, bool is a subclass of int)
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        raise TypeError(f"Exchange rate must be numeric (int or float), got {type(rate).__name__}")

    if math.isnan(rate) or math.isinf(rate):
        raise ValueError(f"Exchange rate must be finite (not NaN or Inf), got {rate}")

    if rate <= 0.0:
        raise ValueError(
            f"Exchange rate must be strictly positive (> 0) to compute logarithmic weight, got {rate}"
        )

    # Avoid -0.0 floating-point quirk when rate is exactly 1.0
    if rate == 1.0:
        return 0.0

    return -math.log(float(rate))


def build_graph(rates: Optional[Iterable[Any]] = None) -> Any:
    """
    Construct a NetworkX directed graph (DiGraph) from conversion rates.

    - Vertices represent cryptocurrencies (e.g., 'BTC', 'ETH', 'USDT').
    - Directed edges represent available conversion paths.
    - Each edge stores two key attributes:
        - 'rate': the original positive conversion rate (float).
        - 'weight': the negative natural log weight, -ln(rate) (float).

    Args:
        rates: Optional iterable of ConversionRate objects, dicts, or tuples.
               If None, retrieves sample simulated rates via get_sample_rates().

    Returns:
        nx.DiGraph: The constructed directed weighted graph.

    Raises:
        ImportError: If NetworkX is not installed in the environment.
        TypeError: If rates or elements within rates have invalid types.
        ValueError: If rates contain invalid or non-positive values.
    """
    if nx is None:
        raise ImportError(
            "NetworkX is required to build directed graphs. "
            "Please install it using 'pip install networkx' or 'pip install -r requirements.txt'."
        )

    # If no rates provided, load the simulated test dataset from exchange_rates
    if rates is None:
        rates = get_sample_rates()

    # Validate all incoming rates using the exchange_rates module
    validated_rates: List[ConversionRate] = validate_rates(rates)

    graph = nx.DiGraph()

    for item in validated_rates:
        source = item.source
        target = item.target
        rate_val = item.rate
        log_weight = calculate_log_weight(rate_val)

        # Add directed edge with both the original rate and calculated log weight
        graph.add_edge(source, target, rate=rate_val, weight=log_weight)

    return graph


def get_graph_summary(graph: Any) -> Dict[str, Any]:
    """
    Return a structured summary of the graph's vertices, edges, and attributes.

    Args:
        graph: NetworkX DiGraph instance.

    Returns:
        Dict[str, Any]: Dictionary with vertex count, edge count, nodes, and edge records.
    """
    edges_info: List[Dict[str, Any]] = []
    for u, v, data in graph.edges(data=True):
        edges_info.append({
            "source": u,
            "target": v,
            "rate": data.get("rate"),
            "weight": data.get("weight"),
        })

    return {
        "num_vertices": graph.number_of_nodes(),
        "num_edges": graph.number_of_edges(),
        "vertices": sorted(list(graph.nodes())),
        "edges": edges_info,
    }
