"""
Test parameter hardening: value coercion, date normalization, and paging bounds.

Static type checking rejects invalid Literal values at the call site; these tests cover
the runtime safety net (for dynamic/untyped inputs) and the coercion of dates, page sizes,
and result caps.
"""

from datetime import date, datetime

import pytest

from massive_api.params import AdjustmentType, DividendFrequency, Market, SplitSortField
from massive_api.utils import (
    build_query_params,
    coerce_choice,
    coerce_choices,
    coerce_date,
    coerce_max_results,
    coerce_sort,
    resolve_page_size,
)


def test_coerce_choice() -> None:
    """A value that is a member of the Literal passes through unchanged."""
    assert coerce_choice("stocks", Market, "market") == "stocks"
    assert coerce_choice("crypto", Market, "market") == "crypto"
    assert coerce_choice(None, Market, "market") is None

    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        coerce_choice("bogus", Market, "market")
    assert "Invalid market 'bogus'" in str(exc_info.value)
    assert "Allowed values: stocks, crypto" in str(exc_info.value)


def test_coerce_choice_int_literal() -> None:
    """Int-valued Literals validate the same way as string ones."""
    assert coerce_choice(4, DividendFrequency, "frequency") == 4
    assert coerce_choice(0, DividendFrequency, "frequency") == 0
    assert coerce_choice(None, DividendFrequency, "frequency") is None

    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        coerce_choice(5, DividendFrequency, "frequency")
    assert "Invalid frequency 5" in str(exc_info.value)
    assert "Allowed values: 0, 1, 2, 3, 4, 12" in str(exc_info.value)


def test_coerce_sort() -> None:
    """Fold sort and order into `field.direction`; order defaults to asc, None sort wins."""
    assert coerce_sort("ticker", "desc", SplitSortField) == "ticker.desc"
    assert coerce_sort("ticker", None, SplitSortField) == "ticker.asc"
    assert coerce_sort(None, None, SplitSortField) is None

    # A valid order with no sort field is a caller error: direction has nothing to order by.
    with pytest.raises(ValueError, match="order requires sort"):
        coerce_sort(None, "desc", SplitSortField)

    with pytest.raises(ValueError, match="Invalid sort"):
        coerce_sort("bogus", None, SplitSortField)
    # order is validated even without a sort field, to fail fast on bad input.
    with pytest.raises(ValueError, match="Invalid order"):
        coerce_sort(None, "bogus", SplitSortField)


def test_coerce_choices() -> None:
    """A list of valid members joins into a comma-separated string; None/empty -> None."""
    assert coerce_choices(["forward_split", "stock_dividend"], AdjustmentType, "x") == "forward_split,stock_dividend"
    assert coerce_choices(None, AdjustmentType, "x") is None
    assert coerce_choices([], AdjustmentType, "x") is None

    with pytest.raises(ValueError, match="Invalid adjustment_types"):
        coerce_choices(["forward_split", "bogus"], AdjustmentType, "adjustment_types")


def test_coerce_date_normalizes_inputs() -> None:
    """Strings, dates, and datetimes all normalize to YYYY-MM-DD."""
    assert coerce_date("2024-01-01", "date") == "2024-01-01"
    assert coerce_date(date(2024, 1, 1), "date") == "2024-01-01"
    assert coerce_date(datetime(2024, 1, 1, 15, 30, tzinfo=None), "date") == "2024-01-01"
    assert coerce_date(None, "date") is None

    with pytest.raises(ValueError, match="Expected an ISO date"):
        coerce_date("01/02/2024", "date")


def test_coerce_max_results_requires_positive() -> None:
    """max_results must be >= 1 (no upper bound); None means 'no cap'."""
    assert coerce_max_results(10_000) == 10_000
    assert coerce_max_results(None) is None

    with pytest.raises(ValueError, match="Must be >= 1"):
        coerce_max_results(0)


def test_resolve_page_size() -> None:
    """Page size defaults to the API max and shrinks to a smaller max_results."""
    assert resolve_page_size(None, 1000) == 1000  # default: API max
    assert resolve_page_size(10, 1000) == 10  # capped to a smaller max_results
    assert resolve_page_size(10_000, 1000) == 1000  # never above the API max


def test_build_query_params_normalizes_dates_and_bools() -> None:
    """build_query_params stringifies bools and date/datetime objects."""
    params = build_query_params(
        {
            "active": True,
            "day": date(2024, 1, 2),
            "ts": datetime(2024, 1, 2, 9, 0, tzinfo=None),
            "n": 5,
            "skip": None,
        },
    )
    assert params == {"active": "true", "day": "2024-01-02", "ts": "2024-01-02", "n": "5"}
