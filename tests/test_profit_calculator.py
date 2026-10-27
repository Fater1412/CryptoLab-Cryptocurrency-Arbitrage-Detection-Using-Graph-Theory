"""
Unit Tests for Profit Calculator Module

Tests step-by-step conversion tracking, fee deduction conventions,
net profitability, input validations, and cycle integrity using Python's built-in unittest.
"""

import math
import unittest
import networkx as nx

from src.arbitrage_detector import detect_arbitrage
from src.exchange_rates import get_arbitrage_sample_rates
from src.graph_builder import build_graph
from src.profit_calculator import ProfitResult, TradeStep, calculate_profit


class TestProfitCalculator(unittest.TestCase):
    """Test suite for calculate_profit function and profit data models."""

    def setUp(self) -> None:
        """Construct standard test graph with intentional triangular arbitrage."""
        # Cycle: BTC -> ETH -> USDT -> BTC
        # Rates: 20.5 * 3000 * (1/60000) = 1.025 (gross +2.5% profit)
        self.graph = nx.DiGraph()
        self.graph.add_edge("BTC", "ETH", rate=20.5, weight=-math.log(20.5))
        self.graph.add_edge("ETH", "USDT", rate=3000.0, weight=-math.log(3000.0))
        self.graph.add_edge("USDT", "BTC", rate=1.0 / 60000.0, weight=-math.log(1.0 / 60000.0))
        self.cycle = ["BTC", "ETH", "USDT", "BTC"]

    def test_1_profitable_cycle_without_fees(self) -> None:
        """Verify gross and net returns match when fee is 0.0%."""
        initial = 10.0
        result = calculate_profit(self.graph, self.cycle, initial_investment=initial, fee_percent=0.0)

        self.assertIsInstance(result, ProfitResult)
        self.assertEqual(result.initial_investment, 10.0)
        self.assertEqual(result.start_currency, "BTC")
        self.assertEqual(result.num_conversions, 3)
        self.assertEqual(result.conversion_count, 3)
        self.assertEqual(result.fee_percent, 0.0)

        # Expected: 10 * 1.025 = 10.25 BTC
        self.assertAlmostEqual(result.gross_final_amount, 10.25, places=6)
        self.assertAlmostEqual(result.net_final_amount, 10.25, places=6)
        self.assertAlmostEqual(result.final_amount_after_fees, 10.25, places=6)
        self.assertAlmostEqual(result.gross_profit, 0.25, places=6)
        self.assertAlmostEqual(result.net_profit, 0.25, places=6)
        self.assertAlmostEqual(result.gross_return_percent, 2.5, places=4)
        self.assertAlmostEqual(result.net_return_percent, 2.5, places=4)
        self.assertTrue(result.is_profitable)

    def test_2_profitable_cycle_with_moderate_fees(self) -> None:
        """Verify fee deduction at each step reduces net profit while remaining positive."""
        initial = 10.0
        fee_percent = 0.1  # 0.1% per trade
        result = calculate_profit(self.graph, self.cycle, initial_investment=initial, fee_percent=fee_percent)

        # Gross is still +2.5%
        self.assertAlmostEqual(result.gross_final_amount, 10.25, places=6)
        self.assertAlmostEqual(result.gross_return_percent, 2.5, places=4)

        # Net factor = 1.025 * (1 - 0.001)^3 = 1.025 * 0.999^3 = 1.025 * 0.997002999 = 1.021928074
        expected_net_final = 10.0 * 1.025 * (0.999 ** 3)
        self.assertAlmostEqual(result.net_final_amount, expected_net_final, places=6)
        self.assertAlmostEqual(result.final_amount_after_fees, expected_net_final, places=6)
        self.assertLess(result.net_final_amount, result.gross_final_amount)
        self.assertGreater(result.net_profit, 0.0)
        self.assertTrue(result.is_profitable)
        self.assertAlmostEqual(result.net_return_percent, (expected_net_final - 10.0) / 10.0 * 100.0, places=4)

    def test_3_fee_that_eliminates_gross_profit(self) -> None:
        """Verify that an exact fee threshold brings net return to approximately 0%."""
        # Gross multiplier M = 1.025. Over 3 hops, (1 - f)^3 = 1 / 1.025 => f = 1 - (1/1.025)^(1/3)
        zero_profit_fee = (1.0 - (1.0 / 1.025) ** (1.0 / 3.0)) * 100.0
        result = calculate_profit(self.graph, self.cycle, initial_investment=100.0, fee_percent=zero_profit_fee)

        self.assertAlmostEqual(result.net_final_amount, 100.0, places=5)
        self.assertAlmostEqual(result.final_amount_after_fees, 100.0, places=5)
        self.assertAlmostEqual(result.net_profit, 0.0, places=5)
        self.assertAlmostEqual(result.net_return_percent, 0.0, places=4)
        self.assertFalse(result.is_profitable)

    def test_4_fee_that_turns_gross_profit_into_net_loss(self) -> None:
        """A fee exceeding the breakeven rate must result in a net loss despite gross arbitrage."""
        # 1.0% fee per hop: (0.99)^3 = 0.970299; 1.025 * 0.970299 = 0.994556 (< 1.0)
        result = calculate_profit(self.graph, self.cycle, initial_investment=1000.0, fee_percent=1.0)

        # Gross was profitable
        self.assertGreater(result.gross_profit, 0.0)
        self.assertAlmostEqual(result.gross_return_percent, 2.5, places=4)

        # Net is a loss
        self.assertLess(result.net_profit, 0.0)
        self.assertLess(result.net_return_percent, 0.0)
        self.assertFalse(result.is_profitable)
        expected_net_final = 1000.0 * 1.025 * (0.99 ** 3)
        self.assertAlmostEqual(result.net_final_amount, expected_net_final, places=4)
        self.assertAlmostEqual(result.final_amount_after_fees, expected_net_final, places=4)

    def test_5_invalid_investment_amounts(self) -> None:
        """Reject 0, negative, non-numeric, or non-finite investment values."""
        with self.assertRaises(ValueError):
            calculate_profit(self.graph, self.cycle, initial_investment=0.0)

        with self.assertRaises(ValueError):
            calculate_profit(self.graph, self.cycle, initial_investment=-50.0)

        with self.assertRaises(TypeError):
            calculate_profit(self.graph, self.cycle, initial_investment="1000")  # type: ignore

        with self.assertRaises(TypeError):
            calculate_profit(self.graph, self.cycle, initial_investment=True)  # type: ignore

        with self.assertRaises(ValueError):
            calculate_profit(self.graph, self.cycle, initial_investment=float("nan"))

        with self.assertRaises(ValueError):
            calculate_profit(self.graph, self.cycle, initial_investment=float("inf"))

    def test_6_invalid_fee_percentages(self) -> None:
        """Reject negative fees, fees >= 100%, non-numeric, or non-finite fees."""
        with self.assertRaises(ValueError):
            calculate_profit(self.graph, self.cycle, fee_percent=-0.1)

        with self.assertRaises(ValueError):
            calculate_profit(self.graph, self.cycle, fee_percent=100.0)

        with self.assertRaises(ValueError):
            calculate_profit(self.graph, self.cycle, fee_percent=105.0)

        with self.assertRaises(TypeError):
            calculate_profit(self.graph, self.cycle, fee_percent="0.2")  # type: ignore

        with self.assertRaises(TypeError):
            calculate_profit(self.graph, self.cycle, fee_percent=False)  # type: ignore

        with self.assertRaises(ValueError):
            calculate_profit(self.graph, self.cycle, fee_percent=float("nan"))

        with self.assertRaises(ValueError):
            calculate_profit(self.graph, self.cycle, fee_percent=float("inf"))

    def test_7_invalid_or_non_closed_cycles(self) -> None:
        """Reject unclosed cycles, cycles that are too short, or non-string symbols."""
        # Non-closed cycle (start != end)
        with self.assertRaises(ValueError):
            calculate_profit(self.graph, ["BTC", "ETH", "USDT"])

        # Cycle too short (< 3 items)
        with self.assertRaises(ValueError):
            calculate_profit(self.graph, ["BTC", "BTC"])

        # Empty cycle
        with self.assertRaises(ValueError):
            calculate_profit(self.graph, [])

        # Non-sequence
        with self.assertRaises(TypeError):
            calculate_profit(self.graph, 12345)  # type: ignore

        # Empty currency symbol in cycle
        with self.assertRaises(ValueError):
            calculate_profit(self.graph, ["BTC", "   ", "BTC"])

        # Non-string currency symbol in cycle
        with self.assertRaises(TypeError):
            calculate_profit(self.graph, ["BTC", 123, "BTC"])  # type: ignore

        # Boolean currency symbol in cycle
        with self.assertRaises(TypeError):
            calculate_profit(self.graph, ["BTC", True, "BTC"])  # type: ignore

    def test_8_missing_directed_edge_in_graph(self) -> None:
        """Reject cycle if any consecutive pair of vertices has no edge in the graph."""
        broken_cycle = ["BTC", "DOGE", "BTC"]
        with self.assertRaises(ValueError) as ctx:
            calculate_profit(self.graph, broken_cycle)
        self.assertIn("does not exist", str(ctx.exception))

    def test_9_multi_step_amount_calculations(self) -> None:
        """Verify accurate intermediate amounts at every conversion hop."""
        initial = 2.0  # 2 BTC
        fee_percent = 0.2  # 0.2% per hop (factor = 0.998)
        result = calculate_profit(self.graph, self.cycle, initial_investment=initial, fee_percent=fee_percent)

        self.assertEqual(len(result.steps), 3)
        self.assertEqual(result.conversion_count, 3)

        # Step 1: BTC -> ETH (rate = 20.5)
        step1 = result.steps[0]
        self.assertEqual(step1.step_number, 1)
        self.assertEqual(step1.from_currency, "BTC")
        self.assertEqual(step1.to_currency, "ETH")
        self.assertEqual(step1.amount_in, 2.0)
        self.assertAlmostEqual(step1.gross_amount_out, 41.0)  # 2 * 20.5
        self.assertAlmostEqual(step1.fee_amount, 41.0 * 0.002)
        expected_net_1 = 41.0 * 0.998
        self.assertAlmostEqual(step1.net_amount_out, expected_net_1)
        self.assertAlmostEqual(step1.amount_after_conversion, expected_net_1)
        self.assertAlmostEqual(step1.cumulative_gross_amount, 41.0)

        # Step 2: ETH -> USDT (rate = 3000.0)
        step2 = result.steps[1]
        self.assertEqual(step2.step_number, 2)
        self.assertEqual(step2.from_currency, "ETH")
        self.assertEqual(step2.to_currency, "USDT")
        self.assertAlmostEqual(step2.amount_in, expected_net_1)
        expected_gross_2 = expected_net_1 * 3000.0
        self.assertAlmostEqual(step2.gross_amount_out, expected_gross_2)
        self.assertAlmostEqual(step2.fee_amount, expected_gross_2 * 0.002)
        expected_net_2 = expected_gross_2 * 0.998
        self.assertAlmostEqual(step2.net_amount_out, expected_net_2)
        self.assertAlmostEqual(step2.amount_after_conversion, expected_net_2)
        self.assertAlmostEqual(step2.cumulative_gross_amount, 41.0 * 3000.0)

        # Step 3: USDT -> BTC (rate = 1/60000.0)
        step3 = result.steps[2]
        self.assertEqual(step3.step_number, 3)
        self.assertEqual(step3.from_currency, "USDT")
        self.assertEqual(step3.to_currency, "BTC")
        self.assertAlmostEqual(step3.amount_in, expected_net_2)
        expected_gross_3 = expected_net_2 / 60000.0
        self.assertAlmostEqual(step3.gross_amount_out, expected_gross_3)
        self.assertAlmostEqual(step3.fee_amount, expected_gross_3 * 0.002)
        expected_net_3 = expected_gross_3 * 0.998
        self.assertAlmostEqual(step3.net_amount_out, expected_net_3)
        self.assertAlmostEqual(step3.amount_after_conversion, expected_net_3)
        self.assertAlmostEqual(result.net_final_amount, expected_net_3)
        self.assertAlmostEqual(result.final_amount_after_fees, expected_net_3)

        # Verify conversion_amounts property
        self.assertEqual(result.conversion_amounts, [expected_net_1, expected_net_2, expected_net_3])

    def test_10_missing_or_invalid_edge_rates(self) -> None:
        """Reject graphs where directed edges lack valid positive numeric rates."""
        # Edge missing 'rate' key
        g_missing = nx.DiGraph()
        g_missing.add_edge("BTC", "ETH", weight=-1.0)
        g_missing.add_edge("ETH", "USDT", rate=3000.0, weight=-1.0)
        g_missing.add_edge("USDT", "BTC", rate=1.0 / 60000.0, weight=-1.0)
        with self.assertRaises(ValueError) as ctx:
            calculate_profit(g_missing, self.cycle)
        self.assertIn("missing required 'rate'", str(ctx.exception))

        # Edge with non-positive rate
        g_non_pos = nx.DiGraph()
        g_non_pos.add_edge("BTC", "ETH", rate=0.0)
        g_non_pos.add_edge("ETH", "USDT", rate=3000.0)
        g_non_pos.add_edge("USDT", "BTC", rate=1.0 / 60000.0)
        with self.assertRaises(ValueError) as ctx:
            calculate_profit(g_non_pos, self.cycle)
        self.assertIn("strictly positive", str(ctx.exception))

        # Edge with negative rate
        g_neg = nx.DiGraph()
        g_neg.add_edge("BTC", "ETH", rate=-20.5)
        g_neg.add_edge("ETH", "USDT", rate=3000.0)
        g_neg.add_edge("USDT", "BTC", rate=1.0 / 60000.0)
        with self.assertRaises(ValueError) as ctx:
            calculate_profit(g_neg, self.cycle)
        self.assertIn("strictly positive", str(ctx.exception))

        # Edge with boolean rate
        g_bool = nx.DiGraph()
        g_bool.add_edge("BTC", "ETH", rate=True)
        g_bool.add_edge("ETH", "USDT", rate=3000.0)
        g_bool.add_edge("USDT", "BTC", rate=1.0 / 60000.0)
        with self.assertRaises(TypeError) as ctx:
            calculate_profit(g_bool, self.cycle)
        self.assertIn("must be numeric", str(ctx.exception))

        # Edge with non-finite rate (NaN)
        g_nan = nx.DiGraph()
        g_nan.add_edge("BTC", "ETH", rate=float("nan"))
        g_nan.add_edge("ETH", "USDT", rate=3000.0)
        g_nan.add_edge("USDT", "BTC", rate=1.0 / 60000.0)
        with self.assertRaises(ValueError) as ctx:
            calculate_profit(g_nan, self.cycle)
        self.assertIn("finite", str(ctx.exception))

    def test_11_invalid_graph_object(self) -> None:
        """Reject non-graph objects passed as graph argument."""
        with self.assertRaises(TypeError):
            calculate_profit(None, self.cycle)  # type: ignore

        with self.assertRaises(TypeError):
            calculate_profit("not_a_graph", self.cycle)  # type: ignore

        with self.assertRaises(TypeError):
            calculate_profit(42, self.cycle)  # type: ignore

    def test_12_longer_arbitrage_cycle(self) -> None:
        """Verify calculation for a 4-hop arbitrage cycle."""
        # BTC -> ETH -> SOL -> USDT -> BTC
        g4 = nx.DiGraph()
        g4.add_edge("BTC", "ETH", rate=20.0)
        g4.add_edge("ETH", "SOL", rate=15.0)
        g4.add_edge("SOL", "USDT", rate=210.0)
        # 20 * 15 * 210 = 63000 USDT. Returning to BTC at 1/60000 => 63000/60000 = 1.05 (+5%)
        g4.add_edge("USDT", "BTC", rate=1.0 / 60000.0)
        cycle4 = ["BTC", "ETH", "SOL", "USDT", "BTC"]

        initial = 5.0
        fee_percent = 0.1
        result = calculate_profit(g4, cycle4, initial_investment=initial, fee_percent=fee_percent)

        self.assertEqual(result.num_conversions, 4)
        self.assertEqual(result.conversion_count, 4)
        self.assertEqual(len(result.steps), 4)

        # Gross: 5.0 * 1.05 = 5.25 BTC
        self.assertAlmostEqual(result.gross_final_amount, 5.25, places=6)
        self.assertAlmostEqual(result.gross_return_percent, 5.0, places=4)

        # Net: 5.0 * 1.05 * (0.999^4)
        expected_net = 5.0 * 1.05 * (0.999 ** 4)
        self.assertAlmostEqual(result.net_final_amount, expected_net, places=6)
        self.assertTrue(result.is_profitable)

    def test_13_end_to_end_integration_with_detector(self) -> None:
        """Integration test: use actual modules to build graph, detect arbitrage, and simulate profit."""
        rates = get_arbitrage_sample_rates()
        graph = build_graph(rates)
        arb_res = detect_arbitrage(graph)

        self.assertTrue(arb_res.has_arbitrage)
        self.assertIsNotNone(arb_res.cycle)
        self.assertIsNotNone(arb_res.rate_product)
        self.assertGreater(arb_res.rate_product, 1.0)

        initial = 1000.0
        fee_pct = 0.05
        profit_res = calculate_profit(graph, arb_res.cycle, initial_investment=initial, fee_percent=fee_pct)

        self.assertEqual(profit_res.cycle, arb_res.cycle)
        self.assertEqual(profit_res.num_conversions, len(arb_res.cycle) - 1)
        self.assertEqual(profit_res.conversion_count, len(arb_res.cycle) - 1)

        # Gross amount must equal initial * rate_product (using actual graph edge rates)
        expected_gross = initial * arb_res.rate_product
        self.assertAlmostEqual(profit_res.gross_final_amount, expected_gross, places=5)
        self.assertAlmostEqual(profit_res.gross_return_percent, (arb_res.rate_product - 1.0) * 100.0, places=3)

    def test_14_result_to_dict_and_property_aliases(self) -> None:
        """Verify that ProfitResult and TradeStep serialize to dictionaries properly with all aliases."""
        result = calculate_profit(self.graph, self.cycle, initial_investment=100.0, fee_percent=0.1)
        d = result.to_dict()

        self.assertIsInstance(d, dict)
        self.assertIn("steps", d)
        self.assertEqual(len(d["steps"]), 3)
        self.assertEqual(d["start_currency"], "BTC")
        self.assertEqual(d["fee_percent"], 0.1)
        self.assertEqual(d["conversion_count"], 3)
        self.assertEqual(d["num_conversions"], 3)
        self.assertEqual(d["final_amount_after_fees"], d["net_final_amount"])
        self.assertEqual(len(d["conversion_amounts"]), 3)

        # Check step dictionary
        step0_dict = d["steps"][0]
        self.assertEqual(step0_dict["from_currency"], "BTC")
        self.assertEqual(step0_dict["to_currency"], "ETH")
        self.assertEqual(step0_dict["amount_after_conversion"], step0_dict["net_amount_out"])


if __name__ == "__main__":
    unittest.main()

