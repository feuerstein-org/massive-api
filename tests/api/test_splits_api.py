"""Test Splits API."""

from datetime import date
from typing import Any

import pytest
from conftest import MockApiFactory
from pydantic import ValidationError

from massive_api.api.splits import Split, SplitsApi

SAMPLE_SPLIT = {
    "ticker": "AAPL",
    "execution_date": "2020-08-31",
    "split_from": 1,
    "split_to": 4,
    "adjustment_type": "forward_split",
    "historical_adjustment_factor": 0.25,
    "id": "E123",
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "expected_params"),
    [
        # Every call sends the page-size `limit`, defaulting to the API maximum (5000).
        ({}, {"limit": "5000"}),
        ({"ticker": "AAPL"}, {"ticker": "AAPL", "limit": "5000"}),
        (
            {"execution_date_gte": "2020-01-01", "execution_date_lte": "2020-12-31"},
            {"execution_date.gte": "2020-01-01", "execution_date.lte": "2020-12-31", "limit": "5000"},
        ),
        (
            {"execution_date_gt": "2020-01-01", "execution_date_lt": "2020-12-31"},
            {"execution_date.gt": "2020-01-01", "execution_date.lt": "2020-12-31", "limit": "5000"},
        ),
        # `sort` + `order` fold into a single `sort=field.direction` (no `order` on the wire).
        (
            {"adjustment_types": ["reverse_split"], "order": "desc", "sort": "execution_date"},
            {"adjustment_type.any_of": "reverse_split", "sort": "execution_date.desc", "limit": "5000"},
        ),
        # `order` defaults to "asc" when only `sort` is given.
        ({"sort": "ticker"}, {"sort": "ticker.asc", "limit": "5000"}),
        # adjustment_types joins into a comma-separated `adjustment_type.any_of`.
        (
            {"adjustment_types": ["forward_split", "reverse_split"]},
            {"adjustment_type.any_of": "forward_split,reverse_split", "limit": "5000"},
        ),
        ({"max_results": 25}, {"limit": "25"}),
    ],
)
async def test_splits_parameters(
    mock_api_factory: MockApiFactory,
    kwargs: dict[str, Any],
    expected_params: dict[str, str],
) -> None:
    """get_splits builds the correct endpoint, params, and results cap."""
    api, mocks = mock_api_factory.create(SplitsApi, mock_pages=[SAMPLE_SPLIT])

    result = await api.get_splits(**kwargs)

    mocks.get_all_pages.assert_called_once_with(
        "stocks/v1/splits",
        expected_params,
        max_results=kwargs.get("max_results"),
    )
    assert len(result) == 1
    assert isinstance(result[0], Split)


@pytest.mark.asyncio
async def test_splits_raw_returns_untouched_records(mock_api_factory: MockApiFactory) -> None:
    """get_splits_raw returns the untouched page dicts (no model conversion)."""
    api, mocks = mock_api_factory.create(SplitsApi, mock_pages=[SAMPLE_SPLIT])

    result = await api.get_splits_raw(ticker="AAPL")

    mocks.get_all_pages.assert_called_once_with(
        "stocks/v1/splits",
        {"ticker": "AAPL", "limit": "5000"},
        max_results=None,
    )
    assert result == [SAMPLE_SPLIT]


@pytest.mark.asyncio
async def test_splits_parses_typed_fields(mock_api_factory: MockApiFactory) -> None:
    """A valid record parses into precise types (date, adjustment_type enum, floats)."""
    api, _ = mock_api_factory.create(SplitsApi, mock_pages=[SAMPLE_SPLIT])

    split = (await api.get_splits())[0]

    assert split.ticker == "AAPL"
    assert split.execution_date == date(2020, 8, 31)
    assert split.adjustment_type == "forward_split"
    assert split.historical_adjustment_factor == 0.25
    assert split.split_from == 1.0
    assert split.split_to == 4.0


@pytest.mark.parametrize(
    "bad_record",
    [
        {**SAMPLE_SPLIT, "adjustment_type": "sideways_split"},  # not an AdjustmentType
        {**SAMPLE_SPLIT, "execution_date": "not-a-date"},  # unparseable date
        {k: v for k, v in SAMPLE_SPLIT.items() if k != "id"},  # missing required id
    ],
)
@pytest.mark.asyncio
async def test_splits_rejects_invalid_records(
    mock_api_factory: MockApiFactory,
    bad_record: dict[str, Any],
) -> None:
    """The hardened Split model raises on an invalid/missing field under 'raise' mode."""
    api, _ = mock_api_factory.create(SplitsApi, mock_pages=[bad_record])

    with pytest.raises(ValidationError):
        await api.get_splits(on_validation_error="raise")


@pytest.mark.parametrize(
    "bad_params",
    [
        {"order": "dec"},  # not an Order ("asc"/"desc")
        {"sort": "volume"},  # not a SplitSortField
        {"adjustment_types": ["sideways_split"]},  # not an AdjustmentType
        {"adjustment_types": "forward_split"},  # must be a list, not a bare string
        {"execution_date": "not-a-date"},  # unparseable date
        {"execution_date_gte": "2020-13-01"},  # out-of-range month
        {"max_results": 0},  # must be a positive integer
        {"max_results": -5},  # must be a positive integer
    ],
)
@pytest.mark.asyncio
async def test_splits_rejects_invalid_parameters(
    mock_api_factory: MockApiFactory,
    bad_params: dict[str, Any],
) -> None:
    """An invalid query parameter raises before any request is made."""
    api, _ = mock_api_factory.create(SplitsApi)

    with pytest.raises(ValueError):  # noqa: PT011
        await api.get_splits(**bad_params, on_validation_error="raise")
