"""
Unit Tests for Exchange Rates Module

Tests for data representation, validation constraints, and sample rate retrieval
using Python's built-in unittest framework.
"""

import math
import unittest

from src.exchange_rates import (
    ConversionRate,
    SIMULATION_DISCLAIMER,
    get_arbitrage_sample_rates,
    get_available_currencies,
    get_sample_rates,
    validate_conversion_rate,
    validate_rates,
)


class TestConversionRate(unittest.TestCase):
    """Test suite for ConversionRate dataclass and validation rules."""

    def test_valid_conversion_rate(self) -> None:
        """Verify that valid rates are stored accurately with normalized symbols."""
        rate = ConversionRate(source="btc", target="eth", rate=20.0)
        self.assertEqual(rate.source, "BTC")
        self.assertEqual(rate.target, "ETH")
        self.assertEqual(rate.rate, 20.0)

    def test_whitespace_stripping_and_uppercasing(self) -> None:
        """Ensure currency symbols are trimmed of whitespace and converted to uppercase."""
        rate = ConversionRate(source="  sol  ", target="\tusdt\n", rate=150)
        self.assertEqual(rate.source, "SOL")
        self.assertEqual(rate.target, "USDT")
        self.assertEqual(rate.rate, 150.0)
        self.assertIsInstance(rate.rate, float)

    def test_tuple_unpacking(self) -> None:
        """Verify that ConversionRate can be unpacked directly like a 3-tuple."""
        rate = ConversionRate(source="BTC", target="USDT", rate=60000.0)
        source, target, value = rate
        self.assertEqual(source, "BTC")
        self.assertEqual(target, "USDT")
        self.assertEqual(value, 60000.0)

    def test_to_and_from_dict(self) -> None:
        """Verify serialization to and from dictionary representations."""
        rate = ConversionRate(source="ETH", target="USDT", rate=3000.0)
        as_dict = rate.to_dict()
        self.assertEqual(as_dict, {"source": "ETH", "target": "USDT", "rate": 3000.0})

        recreated = ConversionRate.from_dict(as_dict)
        self.assertEqual(rate, recreated)

    def test_from_dict_invalid(self) -> None:
        """Verify errors when converting from malformed dictionaries."""
        with self.assertRaises(TypeError):
            ConversionRate.from_dict("not-a-dict")  # type: ignore

        with self.assertRaises(ValueError):
            ConversionRate.from_dict({"source": "BTC", "target": "ETH"})  # missing 'rate'

    def test_reject_zero_rate(self) -> None:
        """Ensure a conversion rate of 0.0 is rejected."""
        with self.assertRaises(ValueError) as context:
            ConversionRate(source="BTC", target="USDT", rate=0.0)
        self.assertIn("strictly positive", str(context.exception))

    def test_reject_negative_rate(self) -> None:
        """Ensure negative rates are rejected."""
        with self.assertRaises(ValueError) as context:
            ConversionRate(source="BTC", target="USDT", rate=-1.5)
        self.assertIn("strictly positive", str(context.exception))

    def test_reject_self_conversion(self) -> None:
        """Ensure converting a currency to itself is rejected."""
        with self.assertRaises(ValueError) as context:
            ConversionRate(source="BTC", target="BTC", rate=1.0)
        self.assertIn("Self-conversion is not permitted", str(context.exception))

        # Check case-insensitivity
        with self.assertRaises(ValueError):
            ConversionRate(source="btc", target="BTC", rate=1.0)

    def test_reject_missing_or_empty_symbol(self) -> None:
        """Ensure empty, whitespace-only, or missing symbols are rejected."""
        with self.assertRaises(ValueError):
            ConversionRate(source="", target="ETH", rate=20.0)

        with self.assertRaises(ValueError):
            ConversionRate(source="BTC", target="   ", rate=20.0)

        with self.assertRaises(TypeError):
            ConversionRate(source=None, target="ETH", rate=20.0)  # type: ignore

        with self.assertRaises(TypeError):
            ConversionRate(source="BTC", target=None, rate=20.0)  # type: ignore

    def test_reject_non_numeric_rate(self) -> None:
        """Ensure non-numeric types (strings, booleans, None) are rejected."""
        # String instead of float/int
        with self.assertRaises(TypeError):
            ConversionRate(source="BTC", target="ETH", rate="20.0")  # type: ignore

        # Boolean (subclass of int in Python)
        with self.assertRaises(TypeError):
            ConversionRate(source="BTC", target="ETH", rate=True)  # type: ignore

        # None
        with self.assertRaises(TypeError):
            ConversionRate(source="BTC", target="ETH", rate=None)  # type: ignore

    def test_reject_non_finite_rate(self) -> None:
        """Ensure non-finite rates (NaN, infinity) are rejected."""
        with self.assertRaises(ValueError) as context_nan:
            ConversionRate(source="BTC", target="ETH", rate=float("nan"))
        self.assertIn("finite", str(context_nan.exception))

        with self.assertRaises(ValueError) as context_inf:
            ConversionRate(source="BTC", target="ETH", rate=float("inf"))
        self.assertIn("finite", str(context_inf.exception))

        with self.assertRaises(ValueError) as context_ninf:
            ConversionRate(source="BTC", target="ETH", rate=float("-inf"))
        self.assertIn("finite", str(context_ninf.exception))


class TestValidationFunctions(unittest.TestCase):
    """Test suite for helper validation functions."""

    def test_validate_conversion_rate(self) -> None:
        """Verify helper validate_conversion_rate creates valid instances."""
        rate = validate_conversion_rate("ETH", "BTC", 0.05)
        self.assertIsInstance(rate, ConversionRate)
        self.assertEqual(rate.source, "ETH")
        self.assertEqual(rate.target, "BTC")
        self.assertEqual(rate.rate, 0.05)

    def test_validate_rates_heterogeneous_input(self) -> None:
        """Verify validate_rates handles ConversionRate objects, dicts, and tuples."""
        raw_input = [
            ConversionRate(source="BTC", target="USDT", rate=60000.0),
            {"source": "ETH", "target": "USDT", "rate": 3000.0},
            ("SOL", "USDT", 150.0),
        ]
        validated = validate_rates(raw_input)
        self.assertEqual(len(validated), 3)
        for item in validated:
            self.assertIsInstance(item, ConversionRate)

        self.assertEqual(validated[0].source, "BTC")
        self.assertEqual(validated[1].source, "ETH")
        self.assertEqual(validated[2].source, "SOL")

    def test_validate_rates_invalid_item(self) -> None:
        """Verify that an invalid item in the collection raises an error."""
        raw_input = [
            ("BTC", "USDT", 60000.0),
            "invalid_item_format",
        ]
        with self.assertRaises(TypeError):
            validate_rates(raw_input)

    def test_get_available_currencies(self) -> None:
        """Verify extraction of unique sorted currency symbols."""
        rates = [
            ConversionRate("SOL", "USDT", 150.0),
            ConversionRate("BTC", "ETH", 20.0),
            ConversionRate("ETH", "USDT", 3000.0),
        ]
        currencies = get_available_currencies(rates)
        self.assertEqual(currencies, ["BTC", "ETH", "SOL", "USDT"])


class TestSampleDatasets(unittest.TestCase):
    """Test suite for simulated test datasets."""

    def test_sample_rates_validity(self) -> None:
        """Verify that all default sample rates are valid, positive, and non-empty."""
        sample_rates = get_sample_rates()
        self.assertGreater(len(sample_rates), 0)
        self.assertIn("SIMULATED DATA", SIMULATION_DISCLAIMER)

        currencies = get_available_currencies(sample_rates)
        self.assertIn("BTC", currencies)
        self.assertIn("ETH", currencies)
        self.assertIn("USDT", currencies)

        for rate in sample_rates:
            self.assertIsInstance(rate, ConversionRate)
            self.assertGreater(rate.rate, 0.0)
            self.assertTrue(math.isfinite(rate.rate))
            self.assertNotEqual(rate.source, rate.target)

    def test_arbitrage_sample_rates_validity(self) -> None:
        """Verify that the simulated arbitrage dataset is valid and contains expected pairs."""
        arb_rates = get_arbitrage_sample_rates()
        self.assertGreater(len(arb_rates), 0)

        # Check that the intentional triangle exists: BTC -> ETH -> USDT -> BTC
        rate_map = {(r.source, r.target): r.rate for r in arb_rates}
        self.assertIn(("BTC", "ETH"), rate_map)
        self.assertIn(("ETH", "USDT"), rate_map)
        self.assertIn(("USDT", "BTC"), rate_map)

        # Compute cycle product: 20.5 * 3000 * (1/60000) = 1.025 (> 1.0)
        product = rate_map[("BTC", "ETH")] * rate_map[("ETH", "USDT")] * rate_map[("USDT", "BTC")]
        self.assertAlmostEqual(product, 1.025, places=5)
        self.assertGreater(product, 1.0)


if __name__ == "__main__":
    unittest.main()
