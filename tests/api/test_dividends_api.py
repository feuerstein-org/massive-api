"""Test Dividends API."""

from datetime import date
from typing import Any

import pytest
from conftest import MockApiFactory, with_defaults
from pydantic import ValidationError

from massive_api.api.dividends import Dividend, DividendsApi

# The SDK always sends these unless the call overrides them.
DEFAULT_PARAMS = {"sort": "ticker.asc", "limit": "5000"}

SAMPLE_DIVIDEND = {
    "cash_amount": 0.26,
    "currency": "USD",
    "declaration_date": "2025-07-31",
    "distribution_type": "recurring",
    "ex_dividend_date": "2025-08-11",
    "frequency": 4,
    "historical_adjustment_factor": 0.997899,
    "id": "Ed2c9da60abda1e3f0e99a43f6465863c",
    "pay_date": "2025-08-14",
    "record_date": "2025-08-11",
    "split_adjusted_cash_amount": 0.26,
    "ticker": "AAPL",
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "expected_params"),
    [
        ({}, {}),  # Test default params
        ({"ticker": "AAPL"}, {"ticker": "AAPL"}),
        # tickers joins into a comma-separated `ticker.any_of`.
        ({"tickers": ["AAPL", "MSFT"]}, {"ticker.any_of": "AAPL,MSFT"}),
        (
            {"ticker_gte": "A", "ticker_lt": "B"},
            {"ticker.gte": "A", "ticker.lt": "B"},
        ),
        (
            {"ex_dividend_date_gte": "2025-01-01", "ex_dividend_date_lte": "2025-12-31"},
            {
                "ex_dividend_date.gte": "2025-01-01",
                "ex_dividend_date.lte": "2025-12-31",
            },
        ),
        (
            {"ex_dividend_date_gt": "2025-01-01", "ex_dividend_date_lt": "2025-12-31"},
            {
                "ex_dividend_date.gt": "2025-01-01",
                "ex_dividend_date.lt": "2025-12-31",
            },
        ),
        # Exact frequency is validated against the documented cadences; ranges pass through.
        ({"frequency": 4}, {"frequency": "4"}),
        (
            {"frequency_gte": 1, "frequency_lte": 12},
            {"frequency.gte": "1", "frequency.lte": "12"},
        ),
        # distribution_types joins into a comma-separated `distribution_type.any_of`.
        (
            {"distribution_types": ["special", "supplemental"]},
            {"distribution_type.any_of": "special,supplemental"},
        ),
        # `sort` + `order` fold into a single `sort=field.direction` (no `order` on the wire).
        (
            {"sort": "ex_dividend_date", "order": "desc"},
            {"sort": "ex_dividend_date.desc"},
        ),
        # `order` defaults to "asc" when only `sort` is given.
        ({"sort": "ticker"}, {"sort": "ticker.asc"}),
        ({"max_results": 25}, {"limit": "25"}),
    ],
)
async def test_dividends_parameters(
    mock_api_factory: MockApiFactory,
    kwargs: dict[str, Any],
    expected_params: dict[str, str],
) -> None:
    """get_dividends builds the correct endpoint, params, and results cap."""
    api, mocks = mock_api_factory.create(DividendsApi, mock_pages=[SAMPLE_DIVIDEND])

    result = await api.get_dividends(**kwargs)

    mocks.get_all_pages.assert_called_once_with(
        "stocks/v1/dividends",
        with_defaults(expected_params, DEFAULT_PARAMS),
        max_results=kwargs.get("max_results"),
    )
    assert len(result) == 1
    assert isinstance(result[0], Dividend)


@pytest.mark.asyncio
async def test_dividends_raw_returns_untouched_records(mock_api_factory: MockApiFactory) -> None:
    """get_dividends_raw returns the untouched page dicts (no model conversion)."""
    api, mocks = mock_api_factory.create(DividendsApi, mock_pages=[SAMPLE_DIVIDEND])

    result = await api.get_dividends_raw(ticker="AAPL")

    mocks.get_all_pages.assert_called_once_with(
        "stocks/v1/dividends",
        with_defaults({"ticker": "AAPL"}, DEFAULT_PARAMS),
        max_results=None,
    )
    assert result == [SAMPLE_DIVIDEND]


@pytest.mark.asyncio
async def test_dividends_parses_typed_fields(mock_api_factory: MockApiFactory) -> None:
    """A valid record parses into precise types (dates, distribution_type enum, floats)."""
    api, _ = mock_api_factory.create(DividendsApi, mock_pages=[SAMPLE_DIVIDEND])

    dividend = (await api.get_dividends())[0]

    assert dividend.ticker == "AAPL"
    assert dividend.ex_dividend_date == date(2025, 8, 11)
    assert dividend.declaration_date == date(2025, 7, 31)
    assert dividend.record_date == date(2025, 8, 11)
    assert dividend.pay_date == date(2025, 8, 14)
    assert dividend.distribution_type == "recurring"
    assert dividend.frequency == 4
    assert dividend.cash_amount == 0.26
    assert dividend.split_adjusted_cash_amount == 0.26
    assert dividend.historical_adjustment_factor == 0.997899
    assert dividend.currency == "USD"


@pytest.mark.asyncio
async def test_dividends_tolerates_missing_optional_fields(mock_api_factory: MockApiFactory) -> None:
    """Announcement/payment metadata may be absent; the record still validates."""
    core_only = {
        "ticker": "AAPL",
        "ex_dividend_date": "2025-08-11",
        "cash_amount": 0.26,
        "distribution_type": "recurring",
        "frequency": 4,
    }
    api, _ = mock_api_factory.create(DividendsApi, mock_pages=[core_only])

    dividend = (await api.get_dividends(on_validation_error="raise"))[0]

    assert dividend.declaration_date is None
    assert dividend.pay_date is None
    assert dividend.historical_adjustment_factor is None


@pytest.mark.parametrize(
    "bad_record",
    [
        {**SAMPLE_DIVIDEND, "distribution_type": "bonus"},  # not a DistributionType
        {**SAMPLE_DIVIDEND, "ex_dividend_date": "not-a-date"},  # unparseable date
        {**SAMPLE_DIVIDEND, "cash_amount": "a lot"},  # not a number
        {k: v for k, v in SAMPLE_DIVIDEND.items() if k != "ticker"},  # missing required ticker
    ],
)
@pytest.mark.asyncio
async def test_dividends_rejects_invalid_records(
    mock_api_factory: MockApiFactory,
    bad_record: dict[str, Any],
) -> None:
    """The hardened Dividend model raises on an invalid/missing core field under 'raise' mode."""
    api, _ = mock_api_factory.create(DividendsApi, mock_pages=[bad_record])

    with pytest.raises(ValidationError):
        await api.get_dividends(on_validation_error="raise")


@pytest.mark.parametrize(
    "bad_params",
    [
        {"order": "dec"},  # not an Order ("asc"/"desc")
        {"sort": "cash_amount"},  # not a DividendSortField
        {"frequency": 5},  # not a documented payout cadence
        {"distribution_types": ["bonus"]},  # not a DistributionType
        {"distribution_types": "recurring"},  # must be a list, not a bare string
        {"ex_dividend_date": "not-a-date"},  # unparseable date
        {"ex_dividend_date_gte": "2025-13-01"},  # out-of-range month
        {"max_results": 0},  # must be a positive integer
        {"max_results": -5},  # must be a positive integer
    ],
)
@pytest.mark.asyncio
async def test_dividends_rejects_invalid_parameters(
    mock_api_factory: MockApiFactory,
    bad_params: dict[str, Any],
) -> None:
    """An invalid query parameter raises before any request is made."""
    api, _ = mock_api_factory.create(DividendsApi)

    with pytest.raises(ValueError):  # noqa: PT011
        await api.get_dividends(**bad_params, on_validation_error="raise")
