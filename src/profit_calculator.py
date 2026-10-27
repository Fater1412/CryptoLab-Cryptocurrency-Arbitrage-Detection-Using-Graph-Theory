"""
Profit Calculator Module for CryptoLab

Calculates step-by-step conversion amounts, compounding gross yields,
fee-adjusted net proceeds, and percentage profits for detected arbitrage cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Sequence


@dataclass(frozen=True)
class TradeStep:
    """
    Represents a single conversion hop in an arbitrage cycle execution.

    Attributes:
        step_number (int): 1-indexed conversion step number.
        from_currency (str): Currency being converted from.
        to_currency (str): Currency being converted into.
        rate (float): Executed conversion exchange rate.
        amount_in (float): Input amount of from_currency at this step.
        gross_amount_out (float): Amount of to_currency received before fee.
        fee_amount (float): Fee deducted in units of to_currency.
        net_amount_out (float): Net amount of to_currency received after fee.
        cumulative_gross_amount (float): Theoretical amount if zero fees were deducted.
    """

    step_number: int
    from_currency: str
    to_currency: str
    rate: float
    amount_in: float
    gross_amount_out: float
    fee_amount: float
    net_amount_out: float
    cumulative_gross_amount: float

    @property
    def amount_after_conversion(self) -> float:
        """Net amount retained in target currency after fee deduction at this step."""
        return self.net_amount_out

    def to_dict(self) -> Dict[str, Any]:
        """Convert trade step to dictionary representation."""
        return {
            "step_number": self.step_number,
            "from_currency": self.from_currency,
            "to_currency": self.to_currency,
            "rate": self.rate,
            "amount_in": self.amount_in,
            "gross_amount_out": self.gross_amount_out,
            "fee_amount": self.fee_amount,
            "net_amount_out": self.net_amount_out,
            "amount_after_conversion": self.amount_after_conversion,
            "cumulative_gross_amount": self.cumulative_gross_amount,
        }


@dataclass(frozen=True)
class ProfitResult:
    """
    Comprehensive result of an arbitrage cycle profit and fee calculation.

    Attributes:
        cycle (List[str]): Sequence of currency symbols in the cycle.
        initial_investment (float): Starting capital amount in cycle[0].
        start_currency (str): The starting and finishing currency symbol.
        num_conversions (int): Number of conversion trades in the cycle.
        fee_percent (float): Deducted fee percentage per trade (e.g., 0.1 for 0.1%).
        steps (List[TradeStep]): Detailed breakdown for each conversion step.
        gross_final_amount (float): Final capital before any transaction fees.
        net_final_amount (float): Final capital after applying transaction fees.
        gross_profit (float): Gross profit or loss (gross_final_amount - initial_investment).
        net_profit (float): Net profit or loss (net_final_amount - initial_investment).
        gross_return_percent (float): Percentage return before fees.
        net_return_percent (float): Percentage return after fees.
        is_profitable (bool): True if net_profit > 0.
        description (str): Human-readable summary of the calculation.
    """

    cycle: List[str]
    initial_investment: float
    start_currency: str
    num_conversions: int
    fee_percent: float
    steps: List[TradeStep]
    gross_final_amount: float
    net_final_amount: float
    gross_profit: float
    net_profit: float
    gross_return_percent: float
    net_return_percent: float
    is_profitable: bool
    description: str

    @property
    def conversion_count(self) -> int:
        """Total number of conversion steps in the cycle (alias for num_conversions)."""
        return self.num_conversions

    @property
    def final_amount_after_fees(self) -> float:
        """Final capital after applying transaction fees (alias for net_final_amount)."""
        return self.net_final_amount

    @property
    def conversion_amounts(self) -> List[float]:
        """Amounts retained after each conversion step in sequence."""
        return [step.net_amount_out for step in self.steps]

    def to_dict(self) -> Dict[str, Any]:
        """Convert profit result to a dictionary representation."""
        return {
            "cycle": self.cycle,
            "initial_investment": self.initial_investment,
            "start_currency": self.start_currency,
            "num_conversions": self.num_conversions,
            "conversion_count": self.conversion_count,
            "fee_percent": self.fee_percent,
            "steps": [step.to_dict() for step in self.steps],
            "conversion_amounts": self.conversion_amounts,
            "gross_final_amount": self.gross_final_amount,
            "net_final_amount": self.net_final_amount,
            "final_amount_after_fees": self.final_amount_after_fees,
            "gross_profit": self.gross_profit,
            "net_profit": self.net_profit,
            "gross_return_percent": self.gross_return_percent,
            "net_return_percent": self.net_return_percent,
            "is_profitable": self.is_profitable,
            "description": self.description,
        }


def calculate_profit(
    graph: Any,
    cycle: Sequence[str],
    initial_investment: float = 1000.0,
    fee_percent: float = 0.0,
) -> ProfitResult:
    """
    Calculate gross and fee-adjusted net profits for an arbitrage cycle.

    Fee Convention:
        The fee is deducted from the received destination currency at each conversion hop:
            gross_received = current_balance * rate
            fee_deducted = gross_received * (fee_percent / 100.0)
            net_received = gross_received - fee_deducted = gross_received * (1.0 - fee_percent / 100.0)

    Args:
        graph: NetworkX DiGraph containing edge 'rate' attributes.
        cycle: Sequence of currency symbols forming a closed cycle (e.g. ['BTC', 'ETH', 'USDT', 'BTC']).
        initial_investment: Strictly positive starting capital in cycle[0] (default 1000.0).
        fee_percent: Configurable fee percentage per conversion, between 0.0 and < 100.0 (default 0.0%).

    Returns:
        ProfitResult: Full calculation breakdown including step-by-step amounts,
            gross/net proceeds, and profit percentages.

    Raises:
        TypeError: If input types are invalid (e.g. booleans, non-numeric amounts, invalid graph).
        ValueError: If amounts are non-positive, fees are out of bounds, or cycle/edge is invalid.
    """
    _validate_investment(initial_investment)
    _validate_fee_percent(fee_percent)
    _validate_cycle_structure(cycle)
    _validate_graph_and_edges(graph, cycle)

    cycle_list: List[str] = list(cycle)
    num_conversions: int = len(cycle_list) - 1
    start_currency: str = cycle_list[0]

    current_gross: float = float(initial_investment)
    current_net: float = float(initial_investment)
    fee_fraction: float = float(fee_percent) / 100.0

    steps: List[TradeStep] = []

    for i in range(num_conversions):
        u = cycle_list[i]
        v = cycle_list[i + 1]

        rate_val = float(graph[u][v]["rate"])

        # 1. Zero-fee cumulative tracking
        cumulative_gross = current_gross * rate_val
        current_gross = cumulative_gross

        # 2. Fee-deducted actual execution tracking
        step_amount_in = current_net
        step_gross_out = step_amount_in * rate_val
        step_fee = step_gross_out * fee_fraction
        step_net_out = step_gross_out - step_fee
        current_net = step_net_out

        steps.append(
            TradeStep(
                step_number=i + 1,
                from_currency=u,
                to_currency=v,
                rate=rate_val,
                amount_in=step_amount_in,
                gross_amount_out=step_gross_out,
                fee_amount=step_fee,
                net_amount_out=step_net_out,
                cumulative_gross_amount=cumulative_gross,
            )
        )

    gross_final_amount = current_gross
    net_final_amount = current_net

    gross_profit = gross_final_amount - initial_investment
    net_profit = net_final_amount - initial_investment

    gross_return_percent = (gross_profit / initial_investment) * 100.0
    net_return_percent = (net_profit / initial_investment) * 100.0

    is_profitable = net_profit > 0.0

    cycle_str = " -> ".join(cycle_list)
    desc = (
        f"Cycle {cycle_str} executed with {initial_investment:.4f} {start_currency}. "
        f"Gross return: {gross_return_percent:+.4f}% ({gross_profit:+.4f} {start_currency}). "
        f"Net return after {fee_percent:.2f}% fee/hop: {net_return_percent:+.4f}% ({net_profit:+.4f} {start_currency})."
    )

    return ProfitResult(
        cycle=cycle_list,
        initial_investment=float(initial_investment),
        start_currency=start_currency,
        num_conversions=num_conversions,
        fee_percent=float(fee_percent),
        steps=steps,
        gross_final_amount=gross_final_amount,
        net_final_amount=net_final_amount,
        gross_profit=gross_profit,
        net_profit=net_profit,
        gross_return_percent=gross_return_percent,
        net_return_percent=net_return_percent,
        is_profitable=is_profitable,
        description=desc,
    )


def _validate_investment(amount: Any) -> None:
    """Validate initial investment amount."""
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise TypeError(f"Initial investment must be numeric (int or float), got {type(amount).__name__}")
    if math.isnan(amount) or math.isinf(amount):
        raise ValueError(f"Initial investment must be finite, got {amount}")
    if amount <= 0.0:
        raise ValueError(f"Initial investment must be strictly positive (> 0), got {amount}")


def _validate_fee_percent(fee: Any) -> None:
    """Validate fee percentage per conversion."""
    if isinstance(fee, bool) or not isinstance(fee, (int, float)):
        raise TypeError(f"Fee percentage must be numeric (int or float), got {type(fee).__name__}")
    if math.isnan(fee) or math.isinf(fee):
        raise ValueError(f"Fee percentage must be finite, got {fee}")
    if fee < 0.0:
        raise ValueError(f"Fee percentage cannot be negative, got {fee}")
    if fee >= 100.0:
        raise ValueError(f"Fee percentage must be strictly less than 100%, got {fee}")


def _validate_cycle_structure(cycle: Any) -> None:
    """Validate structure of the proposed cycle."""
    if isinstance(cycle, (str, bytes)) or not isinstance(cycle, (list, tuple)):
        raise TypeError(f"Cycle must be a list or tuple of currency symbols, got {type(cycle).__name__}")
    if len(cycle) < 3:
        raise ValueError(f"Cycle must contain at least 3 elements (e.g. ['A', 'B', 'A']), got {len(cycle)}")
    for sym in cycle:
        if isinstance(sym, bool) or not isinstance(sym, str):
            raise TypeError(f"All currency symbols in cycle must be strings, got {type(sym).__name__}")
        if not sym.strip():
            raise ValueError(f"All currency symbols in cycle must be non-empty strings, got '{sym}'")
    if cycle[0] != cycle[-1]:
        raise ValueError(
            f"Cycle must be closed (start and end with same currency), got start '{cycle[0]}' and end '{cycle[-1]}'"
        )


def _validate_graph_and_edges(graph: Any, cycle: Sequence[str]) -> None:
    """
    Validate that graph is a valid directed graph instance and every directed edge
    in the cycle exists with a valid positive numeric 'rate'.
    """
    if graph is None or not hasattr(graph, "has_edge"):
        raise TypeError(
            f"Graph must be a valid directed graph instance with 'has_edge' method, got {type(graph).__name__}"
        )

    for i in range(len(cycle) - 1):
        u = cycle[i]
        v = cycle[i + 1]

        if not graph.has_edge(u, v):
            raise ValueError(f"Cycle edge ({u} -> {v}) does not exist in the currency graph.")

        try:
            edge_data = graph[u][v]
        except (KeyError, TypeError, IndexError) as err:
            raise ValueError(f"Unable to access edge data for ({u} -> {v}): {err}") from err

        if not hasattr(edge_data, "get"):
            raise ValueError(f"Graph edge ({u} -> {v}) attributes must be dictionary-like.")

        rate = edge_data.get("rate")
        if rate is None:
            raise ValueError(f"Graph edge ({u} -> {v}) is missing required 'rate' attribute.")
        if isinstance(rate, bool) or not isinstance(rate, (int, float)):
            raise TypeError(f"Graph edge ({u} -> {v}) 'rate' must be numeric, got {type(rate).__name__}")
        if math.isnan(rate) or math.isinf(rate):
            raise ValueError(f"Graph edge ({u} -> {v}) 'rate' must be finite, got {rate}")
        if rate <= 0.0:
            raise ValueError(f"Graph edge ({u} -> {v}) 'rate' must be strictly positive (> 0), got {rate}")
