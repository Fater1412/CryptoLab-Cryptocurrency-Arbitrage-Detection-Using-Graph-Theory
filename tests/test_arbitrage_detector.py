"""
Unit Tests for Arbitrage Detector Module

Tests custom Bellman-Ford negative-weight cycle detection, predecessor backtracking,
cycle edge validation, and multi-component graph support using Python's built-in unittest.
"""

import math
import unittest
import networkx as nx

from src.arbitrage_detector import ArbitrageResult, detect_arbitrage
from src.exchange_rates import get_arbitrage_sample_rates, get_sample_rates
from src.graph_builder import build_graph


class TestArbitrageDetector(unittest.TestCase):
    """Test suite for the Bellman-Ford negative-weight cycle detector."""

    def _create_graph(self, rates: list[tuple[str, str, float]]) -> nx.DiGraph:
        """Helper to build a small DiGraph directly with rates and negative log weights."""
        graph = nx.DiGraph()
        for u, v, r in rates:
            w = 0.0 if r == 1.0 else -math.log(r)
            graph.add_edge(u, v, rate=r, weight=w)
        return graph

    def test_1_graph_with_no_negative_cycle(self) -> None:
        """Verify that a market graph in equilibrium contains no negative cycles."""
        # Multi-currency network in exact equilibrium (no arbitrage possible)
        rates = [
            ("USD", "EUR", 0.90),
            ("EUR", "USD", 1.0 / 0.90),
            ("EUR", "GBP", 0.80),
            ("GBP", "EUR", 1.0 / 0.80),
            ("USD", "GBP", 0.72),
            ("GBP", "USD", 1.0 / 0.72),
        ]
        graph = self._create_graph(rates)
        result = detect_arbitrage(graph)

        self.assertIsInstance(result, ArbitrageResult)
        self.assertFalse(result.has_arbitrage)
        self.assertIsNone(result.cycle)
        self.assertIsNone(result.log_weight_sum)
        self.assertIsNone(result.rate_product)
        self.assertIn("No arbitrage opportunity detected", result.description)

        # Also test on baseline sample market rates
        sample_graph = build_graph(get_sample_rates())
        sample_result = detect_arbitrage(sample_graph)
        self.assertFalse(sample_result.has_arbitrage)

    def test_2_clearly_profitable_cycle_product_greater_than_one(self) -> None:
        """Verify detection and recovery of a profitable triangular arbitrage opportunity."""
        # Cycle: BTC -> ETH -> USDT -> BTC
        # Rates: 20.5 * 3000 * (1/60000) = 1.025 (> 1.0)
        rates = [
            ("BTC", "ETH", 20.5),
            ("ETH", "USDT", 3000.0),
            ("USDT", "BTC", 1.0 / 60000.0),
            ("ETH", "BTC", 1.0 / 20.5),
            ("USDT", "ETH", 1.0 / 3000.0),
            ("BTC", "USDT", 60000.0),
        ]
        graph = self._create_graph(rates)
        result = detect_arbitrage(graph)

        self.assertTrue(result.has_arbitrage)
        self.assertIsNotNone(result.cycle)
        self.assertEqual(result.cycle[0], result.cycle[-1])  # type: ignore
        self.assertAlmostEqual(result.rate_product, 1.025, places=5)  # type: ignore
        self.assertLess(result.log_weight_sum, 0.0)  # type: ignore
        self.assertAlmostEqual(result.log_weight_sum, -math.log(1.025), places=5)  # type: ignore

        # Verify against graph created from get_arbitrage_sample_rates()
        arb_graph = build_graph(get_arbitrage_sample_rates())
        arb_result = detect_arbitrage(arb_graph)
        self.assertTrue(arb_result.has_arbitrage)
        self.assertAlmostEqual(arb_result.rate_product, 1.025, places=5)  # type: ignore

    def test_3_unprofitable_cycle_product_less_than_one(self) -> None:
        """A cycle whose conversion rates product is < 1 has positive weight and must not be flagged."""
        # Cycle: A -> B -> C -> A
        # Rates: 0.5 * 0.5 * 0.5 = 0.125 (< 1.0)
        # Log weight sum: -ln(0.125) = +2.079 > 0 (positive cycle)
        rates = [
            ("A", "B", 0.5),
            ("B", "C", 0.5),
            ("C", "A", 0.5),
        ]
        graph = self._create_graph(rates)
        result = detect_arbitrage(graph)

        self.assertFalse(result.has_arbitrage)
        self.assertIsNone(result.cycle)

    def test_4_neutral_cycle_product_equals_one(self) -> None:
        """A cycle whose rate product equals 1.0 has total weight 0.0 and must not be flagged."""
        # Cycle: A -> B -> C -> A
        # Rates: 2.0 * 3.0 * (1/6) = 1.0
        # Log weight sum: -ln(2) - ln(3) - ln(1/6) = 0.0
        rates = [
            ("A", "B", 2.0),
            ("B", "C", 3.0),
            ("C", "A", 1.0 / 6.0),
        ]
        graph = self._create_graph(rates)
        result = detect_arbitrage(graph)

        self.assertFalse(result.has_arbitrage)
        self.assertIsNone(result.cycle)

    def test_5_negative_cycle_in_disconnected_component(self) -> None:
        """Verify that a negative cycle is detected even in a completely isolated disconnected component."""
        # Component 1: {A, B, C} in equilibrium (weights = 0)
        # Component 2: {X, Y, Z} has a profitable cycle (product = 2.0)
        rates = [
            # Component 1
            ("A", "B", 1.0),
            ("B", "C", 1.0),
            ("C", "A", 1.0),
            # Component 2 (isolated)
            ("X", "Y", 2.0),
            ("Y", "Z", 2.0),
            ("Z", "X", 0.5),  # 2.0 * 2.0 * 0.5 = 2.0 (> 1)
        ]
        graph = self._create_graph(rates)
        result = detect_arbitrage(graph)

        self.assertTrue(result.has_arbitrage)
        self.assertIsNotNone(result.cycle)
        self.assertEqual(result.cycle[0], result.cycle[-1])  # type: ignore

        # The detected cycle must belong to the isolated component {X, Y, Z}
        self.assertTrue(set(result.cycle).issubset({"X", "Y", "Z"}))  # type: ignore
        self.assertAlmostEqual(result.rate_product, 2.0, places=5)  # type: ignore
        self.assertAlmostEqual(result.log_weight_sum, -math.log(2.0), places=5)  # type: ignore

    def test_6_empty_or_trivial_graph(self) -> None:
        """Verify handling of graphs with 0 or 1 vertices/edges."""
        # Empty graph
        empty_graph = nx.DiGraph()
        res_empty = detect_arbitrage(empty_graph)
        self.assertFalse(res_empty.has_arbitrage)

        # Single vertex, no edges
        single_vertex = nx.DiGraph()
        single_vertex.add_node("BTC")
        res_single = detect_arbitrage(single_vertex)
        self.assertFalse(res_single.has_arbitrage)

        # Two vertices, single directed edge (no cycle)
        two_nodes_one_edge = nx.DiGraph()
        two_nodes_one_edge.add_edge("BTC", "ETH", rate=20.0, weight=-math.log(20.0))
        res_path = detect_arbitrage(two_nodes_one_edge)
        self.assertFalse(res_path.has_arbitrage)

    def test_7_cycle_reconstruction_and_directed_edge_validation(self) -> None:
        """Verify that reconstructed cycles use real directed edges and match calculations."""
        # 4-currency cycle: BTC -> ETH -> SOL -> USDT -> BTC
        # Rates: 20 * 20 * 160 * (1/60000) = 64000 / 60000 = 1.066667
        rates = [
            ("BTC", "ETH", 20.0),
            ("ETH", "SOL", 20.0),
            ("SOL", "USDT", 160.0),
            ("USDT", "BTC", 1.0 / 60000.0),
            # Distractor edges
            ("USDT", "ETH", 1.0 / 3000.0),
            ("ETH", "BTC", 0.05),
        ]
        graph = self._create_graph(rates)
        result = detect_arbitrage(graph)

        self.assertTrue(result.has_arbitrage)
        cycle = result.cycle
        self.assertIsNotNone(cycle)
        self.assertGreaterEqual(len(cycle), 4)  # type: ignore
        self.assertEqual(cycle[0], cycle[-1])  # type: ignore

        # Validate that every hop in the cycle is an actual directed edge in the graph
        actual_product = 1.0
        actual_weight_sum = 0.0
        for i in range(len(cycle) - 1):  # type: ignore
            u = cycle[i]  # type: ignore
            v = cycle[i + 1]  # type: ignore
            self.assertTrue(graph.has_edge(u, v), f"Directed edge ({u}, {v}) must exist in graph")
            edge_data = graph[u][v]
            actual_product *= edge_data["rate"]
            actual_weight_sum += edge_data["weight"]

        self.assertAlmostEqual(actual_product, result.rate_product, places=6)  # type: ignore
        self.assertAlmostEqual(actual_weight_sum, result.log_weight_sum, places=6)  # type: ignore
        self.assertGreater(actual_product, 1.0)
        self.assertLess(actual_weight_sum, 0.0)

    def test_result_to_dict_serialization(self) -> None:
        """Verify that ArbitrageResult serializes to a clean dictionary."""
        result = ArbitrageResult(
            has_arbitrage=True,
            cycle=["BTC", "ETH", "USDT", "BTC"],
            log_weight_sum=-0.02469,
            rate_product=1.025,
            description="Arbitrage found",
        )
        as_dict = result.to_dict()
        self.assertEqual(as_dict["has_arbitrage"], True)
        self.assertEqual(as_dict["cycle"], ["BTC", "ETH", "USDT", "BTC"])
        self.assertEqual(as_dict["rate_product"], 1.025)


if __name__ == "__main__":
    unittest.main()
