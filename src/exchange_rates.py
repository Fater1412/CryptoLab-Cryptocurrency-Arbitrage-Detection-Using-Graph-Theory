"""
Exchange Rates Module for CryptoLab

Provides data structures, validation logic, and simulated datasets
for directed cryptocurrency exchange rates.

NOTE: All datasets in this module contain illustrative, simulated rates
for educational and testing purposes only. No live market data or exchange
connections are used.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple


# Clear disclaimer labeling sample data as simulated
SIMULATION_DISCLAIMER: str = (
    "SIMULATED DATA: These exchange rates are illustrative examples "
    "for educational and testing purposes only, not live market data."
)


@dataclass(frozen=True)
class ConversionRate:
    """
    Represents a directed conversion rate from a source cryptocurrency to a target cryptocurrency.

    A rate of 2.0 means 1 unit of source currency converts to 2.0 units of target currency.

    Attributes:
        source (str): Source cryptocurrency symbol (e.g., 'BTC').
        target (str): Target cryptocurrency symbol (e.g., 'ETH').
        rate (float): Positive numeric exchange rate (> 0).
    """

    source: str
    target: str
    rate: float

    def __post_init__(self) -> None:
        """Validate and normalize fields upon initialization."""
        clean_source, clean_target = _validate_symbols(self.source, self.target)
        clean_rate = _validate_rate_value(self.rate)

        # Update attributes in frozen dataclass
        object.__setattr__(self, "source", clean_source)
        object.__setattr__(self, "target", clean_target)
        object.__setattr__(self, "rate", clean_rate)

    def __iter__(self):
        """Allow tuple-like unpacking: `source, target, rate = conversion_rate`."""
        yield self.source
        yield self.target
        yield self.rate

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of the conversion rate."""
        return {
            "source": self.source,
            "target": self.target,
            "rate": self.rate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversionRate":
        """
        Create a ConversionRate instance from a dictionary.

        Args:
            data: Dictionary containing 'source', 'target', and 'rate' keys.
        """
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        if "source" not in data or "target" not in data or "rate" not in data:
            raise ValueError("Dictionary must contain 'source', 'target', and 'rate' keys")
        return cls(source=data["source"], target=data["target"], rate=data["rate"])


def _validate_symbols(source: Any, target: Any) -> Tuple[str, str]:
    """Validate and normalize source and target cryptocurrency symbols."""
    if not isinstance(source, str):
        raise TypeError(f"Source cryptocurrency symbol must be a string, got {type(source).__name__}")
    if not isinstance(target, str):
        raise TypeError(f"Target cryptocurrency symbol must be a string, got {type(target).__name__}")

    clean_source = source.strip().upper()
    clean_target = target.strip().upper()

    if not clean_source:
        raise ValueError("Source cryptocurrency symbol cannot be missing or empty.")
    if not clean_target:
        raise ValueError("Target cryptocurrency symbol cannot be missing or empty.")
    if clean_source == clean_target:
        raise ValueError(
            f"Self-conversion is not permitted: source '{clean_source}' and target '{clean_target}' are identical."
        )

    return clean_source, clean_target


def _validate_rate_value(rate: Any) -> float:
    """Validate that the conversion rate is a strictly positive, finite numeric value."""
    # In Python, bool is a subclass of int, so reject booleans explicitly
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        raise TypeError(f"Exchange rate must be a numeric value (int or float), got {type(rate).__name__}")

    if math.isnan(rate) or math.isinf(rate):
        raise ValueError(f"Exchange rate must be finite (not NaN or Inf), got {rate}")

    if rate <= 0.0:
        raise ValueError(f"Exchange rate must be strictly positive (> 0), got {rate}")

    return float(rate)


def validate_conversion_rate(source: Any, target: Any, rate: Any) -> ConversionRate:
    """
    Validate parameters and return a normalized ConversionRate instance.

    Args:
        source: Source currency symbol (e.g. 'BTC').
        target: Target currency symbol (e.g. 'ETH').
        rate: Numeric exchange rate (> 0).

    Returns:
        ConversionRate: Validated ConversionRate instance.
    """
    return ConversionRate(source=source, target=target, rate=rate)


def validate_rates(rates: Iterable[Any]) -> List[ConversionRate]:
    """
    Validate an iterable of conversion rates.

    Supports:
    - ConversionRate instances
    - Dictionaries with 'source', 'target', and 'rate' keys
    - 3-element tuples or lists: (source, target, rate)

    Args:
        rates: Iterable containing conversion rate records.

    Returns:
        List[ConversionRate]: Validated list of ConversionRate objects.
    """
    validated: List[ConversionRate] = []
    for item in rates:
        if isinstance(item, ConversionRate):
            validated.append(item)
        elif isinstance(item, dict):
            validated.append(ConversionRate.from_dict(item))
        elif isinstance(item, (tuple, list)) and len(item) == 3:
            validated.append(ConversionRate(source=item[0], target=item[1], rate=item[2]))
        else:
            raise TypeError(
                f"Rate item must be a ConversionRate, dict, or (source, target, rate) tuple, got {type(item).__name__}"
            )
    return validated


def get_available_currencies(rates: Sequence[ConversionRate]) -> List[str]:
    """
    Extract a sorted list of unique currency symbols from a sequence of conversion rates.

    Args:
        rates: Sequence of ConversionRate objects.

    Returns:
        List[str]: Alphabetically sorted unique currency symbols.
    """
    currencies: Set[str] = set()
    for rate in rates:
        currencies.add(rate.source)
        currencies.add(rate.target)
    return sorted(currencies)


# ============================================================================
# Simulated Datasets for Testing & Demonstration (NOT live market data)
# ============================================================================

# Baseline simulated rates with direct and reciprocal conversions across 4 currencies
_SIMULATED_RATES_DATA: Tuple[Tuple[str, str, float], ...] = (
    ("BTC", "USDT", 60000.0),
    ("USDT", "BTC", 1.0 / 60000.0),
    ("ETH", "USDT", 3000.0),
    ("USDT", "ETH", 1.0 / 3000.0),
    ("SOL", "USDT", 150.0),
    ("USDT", "SOL", 1.0 / 150.0),
    ("BTC", "ETH", 20.0),
    ("ETH", "BTC", 0.05),
    ("ETH", "SOL", 20.0),
    ("SOL", "ETH", 0.05),
    ("BTC", "SOL", 400.0),
    ("SOL", "BTC", 0.0025),
)

# Simulated rates containing an intentional triangular arbitrage opportunity
# Cycle: BTC -> ETH -> USDT -> BTC
# Rates:
#   BTC -> ETH: 20.5 (1 BTC yields 20.5 ETH)
#   ETH -> USDT: 3000.0 (20.5 ETH yields 61,500 USDT)
#   USDT -> BTC: 1 / 60000.0 (61,500 USDT yields 1.025 BTC -> +2.5% profit)
_SIMULATED_ARBITRAGE_RATES_DATA: Tuple[Tuple[str, str, float], ...] = (
    ("BTC", "ETH", 20.5),
    ("ETH", "USDT", 3000.0),
    ("USDT", "BTC", 1.0 / 60000.0),
    ("USDT", "ETH", 1.0 / 3000.0),
    ("ETH", "BTC", 1.0 / 20.5),
    ("BTC", "USDT", 60000.0),
)


def get_sample_rates() -> List[ConversionRate]:
    """
    Retrieve a sample dataset of simulated conversion rates for testing.

    DISCLAIMER: These rates are illustrative and synthetic, not live market data.

    Returns:
        List[ConversionRate]: Validated sample conversion rates.
    """
    return [
        ConversionRate(source=src, target=tgt, rate=r)
        for src, tgt, r in _SIMULATED_RATES_DATA
    ]


def get_arbitrage_sample_rates() -> List[ConversionRate]:
    """
    Retrieve a simulated dataset containing an intentional triangular
    arbitrage opportunity (BTC -> ETH -> USDT -> BTC with +2.5% theoretical return).

    DISCLAIMER: These rates are illustrative and synthetic, not live market data.

    Returns:
        List[ConversionRate]: Validated sample conversion rates with an arbitrage cycle.
    """
    return [
        ConversionRate(source=src, target=tgt, rate=r)
        for src, tgt, r in _SIMULATED_ARBITRAGE_RATES_DATA
    ]
