"""Tests for API cost mapping."""

import pytest

from eodhd_py.api.costs import ENDPOINT_COSTS, get_endpoint_cost


@pytest.mark.parametrize(
    ("endpoint", "expected_cost"),
    [
        ("eod/AAPL", 1),
        ("eod/AAPL.US", 1),
        ("eod/TSLA.US", 1),
        ("intraday/AAPL", 5),
        ("intraday/TSLA.US", 5),
        ("intraday/MSFT.US", 5),
        ("user", 0),
        ("EOD/AAPL", 1),
        ("INTRADAY/TSLA", 5),
        ("USER", 0),
        ("/eod/AAPL", 1),  # Test leading slash
        ("/intraday/TSLA/", 5),  # Test leading and trailing slash
        ("fundamentals/AAPL", 1),  # Test unknown endpoint (defaults to 1)
        ("options/AAPL", 1),  # Test unknown endpoint (defaults to 1)
    ],
)
def test_get_endpoint_cost(endpoint: str, expected_cost: int) -> None:
    """Test that get_endpoint_cost returns the correct cost for various endpoints."""
    assert get_endpoint_cost(endpoint) == expected_cost


def test_endpoint_costs_constant() -> None:
    """Test that ENDPOINT_COSTS contains expected keys."""
    assert "eod" in ENDPOINT_COSTS
    assert "intraday" in ENDPOINT_COSTS
    assert "user" in ENDPOINT_COSTS
