"""
Arbitrage Detector Module for CryptoLab

Implements the Bellman-Ford algorithm from scratch to detect negative-weight
cycles in directed weighted graphs and reconstruct profitable cryptocurrency
arbitrage cycles.

No third-party black-box cycle detection libraries are used; the relaxation
and cycle-extraction logic is implemented directly using Python loops.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class ArbitrageResult:
    """
    Structured outcome of the Bellman-Ford arbitrage detection algorithm.

    Attributes:
        has_arbitrage (bool): True if a valid negative-weight cycle was detected.
        cycle (Optional[List[str]]): Ordered list of currency symbols representing
            the cycle, starting and ending with the same currency (e.g. ['BTC', 'ETH', 'USDT', 'BTC']).
        log_weight_sum (Optional[float]): The sum of logarithmic edge weights along the cycle (< 0).
        rate_product (Optional[float]): The product of original exchange rates along the cycle (> 1).
        description (str): Human-readable summary of the detection result.
    """

    has_arbitrage: bool
    cycle: Optional[List[str]] = None
    log_weight_sum: Optional[float] = None
    rate_product: Optional[float] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to a plain dictionary representation."""
        return {
            "has_arbitrage": self.has_arbitrage,
            "cycle": self.cycle,
            "log_weight_sum": self.log_weight_sum,
            "rate_product": self.rate_product,
            "description": self.description,
        }


def detect_arbitrage(graph: Any, tolerance: float = 1e-9) -> ArbitrageResult:
    """
    Detect whether a negative-weight cycle (arbitrage opportunity) exists
    anywhere in the directed graph using a custom Bellman-Ford implementation.

    Features:
    - Supports disconnected components by initializing all vertex distances to 0.0.
    - Uses custom Python relaxation loops (no third-party cycle detection functions).
    - Backtracks predecessor pointers to reliably reconstruct the exact directed cycle.
    - Validates all cycle edges and verifies rate product > 1 before reporting.

    Args:
        graph: NetworkX DiGraph produced by src.graph_builder.
        tolerance: Numerical tolerance for floating-point comparisons (default 1e-9).

    Returns:
        ArbitrageResult: Comprehensive result containing detection flag, reconstructed cycle,
            weight sum, and rate product.
    """
    if graph is None or graph.number_of_nodes() < 2 or graph.number_of_edges() < 2:
        return ArbitrageResult(
            has_arbitrage=False,
            cycle=None,
            log_weight_sum=None,
            rate_product=None,
            description="Graph has insufficient vertices or edges to form an arbitrage cycle.",
        )

    vertices: List[str] = list(graph.nodes())
    num_vertices: int = len(vertices)

    # 1. Initialize distances to 0.0 for ALL vertices.
    # Conceptually, this is equivalent to adding a virtual source node connected to
    # every vertex with 0-weight edges. It guarantees that negative cycles in any
    # disconnected component are reachable and detectable without choosing an arbitrary source.
    distance: Dict[str, float] = {v: 0.0 for v in vertices}
    predecessor: Dict[str, Optional[str]] = {v: None for v in vertices}

    # Extract all directed edges as (source, target, weight) tuples
    edges: List[Tuple[str, str, float]] = []
    for u, v, data in graph.edges(data=True):
        weight = data.get("weight")
        if weight is None:
            raise ValueError(f"Edge ({u}, {v}) is missing required 'weight' attribute.")
        edges.append((u, v, float(weight)))

    # 2. Relax edges |V| - 1 times
    # In a graph with no negative cycles, the shortest path between any two vertices
    # contains at most |V| - 1 edges.
    for _ in range(num_vertices - 1):
        updated = False
        for u, v, weight in edges:
            if distance[u] + weight < distance[v] - tolerance:
                distance[v] = distance[u] + weight
                predecessor[v] = u
                updated = True

        # Early termination: if no edge relaxed in a pass, shortest paths have converged
        if not updated:
            return ArbitrageResult(
                has_arbitrage=False,
                cycle=None,
                log_weight_sum=None,
                rate_product=None,
                description="No arbitrage opportunity detected (shortest paths converged).",
            )

    # 3. Pass |V|: Detect negative-weight cycles
    # If any edge can still be relaxed after |V| - 1 passes, a negative cycle exists.
    for u, v, weight in edges:
        if distance[u] + weight < distance[v] - tolerance:
            # Record predecessor update for the relaxing edge
            predecessor[v] = u

            # Extract cycle from predecessor pointers
            candidate_cycle = _extract_cycle(predecessor, v, num_vertices)
            if candidate_cycle:
                validation = _validate_and_evaluate_cycle(graph, candidate_cycle, tolerance)
                if validation is not None:
                    log_weight_sum, rate_product = validation
                    cycle_str = " -> ".join(candidate_cycle)
                    return ArbitrageResult(
                        has_arbitrage=True,
                        cycle=candidate_cycle,
                        log_weight_sum=log_weight_sum,
                        rate_product=rate_product,
                        description=(
                            f"Profitable arbitrage opportunity detected along cycle: {cycle_str}. "
                            f"Gross rate product: {rate_product:.6f} "
                            f"(logarithmic weight sum: {log_weight_sum:.6f})."
                        ),
                    )

    return ArbitrageResult(
        has_arbitrage=False,
        cycle=None,
        log_weight_sum=None,
        rate_product=None,
        description="No arbitrage opportunity detected (no negative-weight cycle found).",
    )


def _extract_cycle(predecessor: Dict[str, Optional[str]], start_vertex: str, num_vertices: int) -> Optional[List[str]]:
    """
    Reconstruct a directed cycle from the predecessor map.

    To ensure entry into the cycle, we first step backwards |V| times along
    predecessor pointers. Once inside the cycle, we record vertices until
    the cycle repeats.

    Args:
        predecessor: Mapping from vertex to its predecessor.
        start_vertex: The vertex where relaxation succeeded on the |V|-th pass.
        num_vertices: Total number of vertices in the graph.

    Returns:
        Optional[List[str]]: Ordered cycle starting and ending with the same vertex,
            e.g. ['BTC', 'ETH', 'USDT', 'BTC'], or None if extraction fails.
    """
    curr: Optional[str] = start_vertex

    # Step backwards |V| times to guarantee entering the negative cycle
    for _ in range(num_vertices):
        if curr is None or curr not in predecessor:
            return None
        curr = predecessor[curr]

    if curr is None:
        return None

    # Step backwards from curr to collect the cycle vertices
    cycle_start: str = curr
    cycle_backwards: List[str] = [cycle_start]
    step = predecessor.get(cycle_start)

    visited: Set[str] = {cycle_start}
    while step != cycle_start:
        if step is None or step not in predecessor:
            return None
        if step in visited:
            # A sub-cycle was encountered; trim to that sub-cycle
            cycle_backwards.append(step)
            break
        visited.add(step)
        cycle_backwards.append(step)
        step = predecessor.get(step)

    cycle_backwards.append(cycle_start)

    # Predecessor tracing goes backwards (target -> source); reverse to get forward directed order
    forward_cycle = list(reversed(cycle_backwards))

    # Standardize: Ensure first and last vertices are identical
    if forward_cycle[0] != forward_cycle[-1]:
        # If trimming occurred, align start and end
        first_node = forward_cycle[0]
        if first_node in forward_cycle[1:]:
            idx = forward_cycle[1:].index(first_node) + 1
            forward_cycle = forward_cycle[: idx + 1]
        else:
            return None

    return forward_cycle


def _validate_and_evaluate_cycle(
    graph: Any, cycle: List[str], tolerance: float = 1e-9
) -> Optional[Tuple[float, float]]:
    """
    Validate that every edge in the reconstructed cycle exists in the graph,
    and calculate the exact logarithmic weight sum and exchange rate product.

    Args:
        graph: Directed graph containing edge attributes 'rate' and 'weight'.
        cycle: List of vertex symbols forming a closed walk (e.g. ['BTC', 'ETH', 'BTC']).
        tolerance: Numerical threshold for profitability verification.

    Returns:
        Optional[Tuple[float, float]]: (log_weight_sum, rate_product) if valid
            and profitable, otherwise None.
    """
    if len(cycle) < 3 or cycle[0] != cycle[-1]:
        return None

    log_weight_sum = 0.0
    rate_product = 1.0

    for i in range(len(cycle) - 1):
        u = cycle[i]
        v = cycle[i + 1]

        # Verify that the directed edge actually exists in the graph
        if not graph.has_edge(u, v):
            return None

        edge_data = graph[u][v]
        rate = edge_data.get("rate")
        weight = edge_data.get("weight")

        if rate is None or weight is None:
            return None

        log_weight_sum += float(weight)
        rate_product *= float(rate)

    # A profitable cycle MUST satisfy both:
    # 1. Total log weight < 0
    # 2. Product of exchange rates > 1
    if log_weight_sum < -tolerance and rate_product > 1.0 + tolerance:
        return log_weight_sum, rate_product

    return None
