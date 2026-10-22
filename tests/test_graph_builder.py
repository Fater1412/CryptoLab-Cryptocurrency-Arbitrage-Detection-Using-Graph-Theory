"""
Unit Tests for Graph Builder Module

Tests for logarithmic edge weight calculation and NetworkX directed graph
construction using Python's built-in unittest framework.
"""

import math
import unittest

try:
    import networkx as nx
except ImportError:
    nx = None

from src.exchange_rates import ConversionRate, get_arbitrage_sample_rates, get_sample_rates
from src.graph_builder import build_graph, calculate_log_weight, get_graph_summary


class TestCalculateLogWeight(unittest.TestCase):
    """Test suite for calculate_log_weight function."""

    def test_rate_greater_than_one_negative_weight(self) -> None:
        """A conversion rate > 1 must produce a strictly negative edge weight (-ln(r) < 0)."""
        test_rates = [1.0001, 2.0, 15.0, 60000.0]
        for r in test_rates:
            weight = calculate_log_weight(r)
            self.assertLess(weight, 0.0, f"Expected weight < 0 for rate {r}, got {weight}")

    def test_rate_between_zero_and_one_positive_weight(self) -> None:
        """A conversion rate between 0 and 1 must produce a strictly positive edge weight (-ln(r) > 0)."""
        test_rates = [0.00001, 0.05, 0.5, 0.9999]
        for r in test_rates:
            weight = calculate_log_weight(r)
            self.assertGreater(weight, 0.0, f"Expected weight > 0 for rate {r}, got {weight}")

    def test_rate_equal_to_one_zero_weight(self) -> None:
        """A conversion rate of exactly 1.0 must produce a weight of 0.0."""
        weight = calculate_log_weight(1.0)
        self.assertEqual(weight, 0.0)

    def test_log_weight_mathematical_precision(self) -> None:
        """Verify that logarithmic weight equals -ln(rate) within floating-point tolerance."""
        test_cases = [
            (2.0, -math.log(2.0)),
            (math.e, -1.0),
            (1.0 / math.e, 1.0),
            (15.0, -math.log(15.0)),
            (60000.0, -math.log(60000.0)),
            (1.0 / 60000.0, -math.log(1.0 / 60000.0)),
        ]
        for rate, expected_weight in test_cases:
            actual_weight = calculate_log_weight(rate)
            self.assertAlmostEqual(actual_weight, expected_weight, places=7)

    def test_reject_zero_rate(self) -> None:
        """Ensure rate of 0.0 raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            calculate_log_weight(0.0)
        self.assertIn("strictly positive", str(ctx.exception))

    def test_reject_negative_rate(self) -> None:
        """Ensure negative rates raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            calculate_log_weight(-2.5)
        self.assertIn("strictly positive", str(ctx.exception))

    def test_reject_non_numeric_rate(self) -> None:
        """Ensure non-numeric types raise TypeError."""
        with self.assertRaises(TypeError):
            calculate_log_weight("15.0")  # type: ignore

        with self.assertRaises(TypeError):
            calculate_log_weight(True)  # type: ignore

        with self.assertRaises(TypeError):
            calculate_log_weight(None)  # type: ignore

    def test_reject_non_finite_rate(self) -> None:
        """Ensure NaN and infinity values raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_log_weight(float("nan"))

        with self.assertRaises(ValueError):
            calculate_log_weight(float("inf"))

        with self.assertRaises(ValueError):
            calculate_log_weight(float("-inf"))


@unittest.skipIf(nx is None, "NetworkX is not yet installed in this environment; awaiting approval to install requirements.txt")
class TestGraphBuilder(unittest.TestCase):
    """Test suite for NetworkX directed graph construction."""

    def test_graph_vertices_and_directed_edges(self) -> None:
        """Verify that vertices match currencies and directed edges exist."""
        graph = build_graph()
        self.assertTrue(graph.is_directed())

        expected_vertices = {"BTC", "ETH", "SOL", "USDT"}
        self.assertEqual(set(graph.nodes()), expected_vertices)

        # Check expected directed edges
        self.assertTrue(graph.has_edge("BTC", "USDT"))
        self.assertTrue(graph.has_edge("USDT", "BTC"))
        self.assertTrue(graph.has_edge("ETH", "USDT"))

        # Verify non-existent edge
        self.assertFalse(graph.has_edge("BTC", "XYZ"))

    def test_original_rates_preserved_on_edges(self) -> None:
        """Verify that original conversion rates are stored under 'rate' attribute."""
        graph = build_graph()
        btc_usdt_data = graph["BTC"]["USDT"]
        self.assertIn("rate", btc_usdt_data)
        self.assertEqual(btc_usdt_data["rate"], 60000.0)

        btc_eth_data = graph["BTC"]["ETH"]
        self.assertEqual(btc_eth_data["rate"], 20.0)

    def test_logarithmic_weights_stored_and_accurate(self) -> None:
        """Verify that logarithmic weights are stored under 'weight' attribute and mathematically sound."""
        graph = build_graph()

        # BTC -> USDT: rate 60000 (> 1) => negative weight
        btc_usdt = graph["BTC"]["USDT"]
        self.assertIn("weight", btc_usdt)
        self.assertLess(btc_usdt["weight"], 0.0)
        self.assertAlmostEqual(btc_usdt["weight"], -math.log(60000.0), places=7)

        # USDT -> BTC: rate 1/60000 (< 1) => positive weight
        usdt_btc = graph["USDT"]["BTC"]
        self.assertGreater(usdt_btc["weight"], 0.0)
        self.assertAlmostEqual(usdt_btc["weight"], -math.log(1.0 / 60000.0), places=7)

        # Net round-trip reciprocal weight sum should be 0.0
        round_trip_sum = btc_usdt["weight"] + usdt_btc["weight"]
        self.assertAlmostEqual(round_trip_sum, 0.0, places=7)

    def test_build_graph_with_custom_rates(self) -> None:
        """Verify building a graph with custom conversion rates."""
        custom_rates = [
            ConversionRate("BTC", "ETH", 15.0),
            ConversionRate("ETH", "USDT", 2500.0),
        ]
        graph = build_graph(custom_rates)
        self.assertEqual(set(graph.nodes()), {"BTC", "ETH", "USDT"})
        self.assertEqual(graph.number_of_edges(), 2)
        self.assertEqual(graph["BTC"]["ETH"]["rate"], 15.0)
        self.assertAlmostEqual(graph["BTC"]["ETH"]["weight"], -math.log(15.0), places=7)

    def test_arbitrage_cycle_negative_weight_sum(self) -> None:
        """Verify that an arbitrage cycle has a net negative total logarithmic weight."""
        arb_rates = get_arbitrage_sample_rates()
        graph = build_graph(arb_rates)

        # Cycle: BTC -> ETH -> USDT -> BTC
        w_btc_eth = graph["BTC"]["ETH"]["weight"]
        w_eth_usdt = graph["ETH"]["USDT"]["weight"]
        w_usdt_btc = graph["USDT"]["BTC"]["weight"]

        total_weight = w_btc_eth + w_eth_usdt + w_usdt_btc

        # Total weight must be strictly negative because rate product = 1.025 > 1.0
        self.assertLess(total_weight, 0.0)
        self.assertAlmostEqual(total_weight, -math.log(1.025), places=5)

    def test_get_graph_summary(self) -> None:
        """Verify structured graph summary dictionary output."""
        graph = build_graph()
        summary = get_graph_summary(graph)
        self.assertEqual(summary["num_vertices"], 4)
        self.assertGreater(summary["num_edges"], 0)
        self.assertEqual(summary["vertices"], ["BTC", "ETH", "SOL", "USDT"])
        self.assertIsInstance(summary["edges"], list)


if __name__ == "__main__":
    unittest.main()
