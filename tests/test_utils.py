"""Tests for utility functions in eodhd_py.utils."""

import re

import pytest

from eodhd_py.utils import validate_interval, validate_normalize_symbol, validate_order


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("AAPL", "AAPL"),
        ("GOOG", "GOOG"),
        ("BRK.B.US", "BRK-B.US"),
        ("BRK-A", "BRK-A"),
        ("SPY", "SPY"),
    ],
)
def test_validate_normalize_symbol_valid(symbol: str, expected: str) -> None:
    """Test valid symbols."""
    assert validate_normalize_symbol(symbol) == expected


@pytest.mark.parametrize(
    ("symbol"),
    [
        "INVALID SYMBOL!",
        "",
        "A" * 49,  # Too long
        "symbol with spaces",
        "symbol@invalid",
    ],
)
def test_validate_normalize_symbol_invalid(symbol: str) -> None:
    """Test invalid symbols."""
    with pytest.raises(ValueError, match="Symbol is invalid"):
        validate_normalize_symbol(symbol)


@pytest.mark.parametrize("order", ["a", "d"])
def test_validate_order_valid(order: str) -> None:
    """Test valid order values."""
    assert validate_order(order) is True


@pytest.mark.parametrize(
    "order",
    [
        "x",
        "ascending",
        "descending",
        "A",
        "D",
    ],
)
def test_validate_order_invalid(order: str) -> None:
    """Test invalid order values."""
    with pytest.raises(ValueError, match=re.escape("Order must be 'a' (ascending) or 'd' (descending)")):
        validate_order(order)


@pytest.mark.parametrize("interval", ["1m", "5m", "1h"])
def test_validate_interval_intraday_valid(interval: str) -> None:
    """Test valid intraday interval values."""
    assert validate_interval(interval, data_type="intraday") is True


@pytest.mark.parametrize(
    "interval",
    ["1s", "10m", "2h", "1M", "5M", "1H", "", "d", "w", "m"],
)
def test_validate_interval_intraday_invalid(interval: str) -> None:
    """Test invalid intraday interval values."""
    with pytest.raises(ValueError, match=re.escape("Interval must be '1m', '5m', or '1h'")):
        validate_interval(interval, data_type="intraday")


@pytest.mark.parametrize("interval", ["d", "w", "m"])
def test_validate_interval_eod_valid(interval: str) -> None:
    """Test valid EOD interval values."""
    assert validate_interval(interval, data_type="eod") is True


@pytest.mark.parametrize(
    "interval",
    ["D", "W", "M", "daily", "weekly", "monthly", "", "1m", "5m", "1h"],
)
def test_validate_interval_eod_invalid(interval: str) -> None:
    """Test invalid EOD interval values."""
    with pytest.raises(ValueError, match=re.escape("Interval must be 'd' (daily), 'w' (weekly), or 'm' (monthly)")):
        validate_interval(interval, data_type="eod")


def test_validate_interval_invalid_data_type() -> None:
    """Test that invalid data_type raises ValueError."""
    with pytest.raises(ValueError, match=re.escape("Invalid data_type: invalid. Must be 'eod' or 'intraday'")):
        validate_interval("d", data_type="invalid")
