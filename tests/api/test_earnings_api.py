"""Test Earnings API."""

from datetime import datetime
from typing import Any

import pytest
from conftest import MockApiFactory
from pytest_mock import MockerFixture

import eodhd_py.api.earnings
from eodhd_py.api.earnings import EarningsApi

MOCK_EARNINGS_RESPONSE = {
    "type": "Earnings",
    "description": "Historical and upcoming Earnings",
    "from": "2018-12-02",
    "to": "2018-12-06",
    "earnings": [
        {
            "code": "AAPL.US",
            "report_date": "2018-12-02",
            "date": "2018-09-30",
            "before_after_market": "AfterMarket",
            "currency": "USD",
            "actual": 2.91,
            "estimate": 2.78,
            "difference": 0.13,
            "percent": 4.6763,
        },
        {
            "code": "MSFT.US",
            "report_date": "2018-12-03",
            "date": "2018-09-30",
            "before_after_market": "BeforeMarket",
            "currency": "USD",
            "actual": 1.14,
            "estimate": 1.09,
            "difference": 0.05,
            "percent": 4.5872,
        },
    ],
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("test_case"),
    [
        {
            "symbols": None,
            "from_date": None,
            "to_date": None,
            "expected_params": {},
        },
        {
            "symbols": None,
            "from_date": datetime(2023, 1, 1),
            "to_date": datetime(2023, 12, 31),
            "expected_params": {"from": "2023-01-01", "to": "2023-12-31"},
        },
        {
            "symbols": None,
            "from_date": datetime(2020, 1, 1),
            "to_date": None,
            "expected_params": {"from": "2020-01-01"},
        },
        {
            "symbols": None,
            "from_date": None,
            "to_date": datetime(2024, 6, 30),
            "expected_params": {"to": "2024-06-30"},
        },
        {
            "symbols": ["AAPL.US", "MSFT.US", "AI.PA"],
            "from_date": None,
            "to_date": None,
            "expected_params": {"symbols": "AAPL.US,MSFT.US,AI.PA"},
        },
        {
            "symbols": ["AAPL.US"],
            "from_date": datetime(2023, 1, 1),
            "to_date": datetime(2023, 12, 31),
            "expected_params": {"symbols": "AAPL.US", "from": "2023-01-01", "to": "2023-12-31"},
        },
    ],
)
async def test_parameters(mock_api_factory: MockApiFactory, test_case: dict[str, Any]) -> None:
    """Test EarningsApi business logic with various parameter combinations."""
    api, mock_make_request = mock_api_factory.create(
        EarningsApi,
        mock_response_data=MOCK_EARNINGS_RESPONSE,
    )

    await api.get_earnings(
        symbols=test_case["symbols"],
        from_date=test_case["from_date"],
        to_date=test_case["to_date"],
        df_output=False,
    )

    mock_make_request.assert_called_once_with("calendar/earnings", params=test_case["expected_params"], df_output=False)


@pytest.mark.asyncio
async def test_returns_earnings_array(mock_api_factory: MockApiFactory) -> None:
    """Test that EarningsApi extracts earnings array from response."""
    api, _ = mock_api_factory.create(
        EarningsApi,
        mock_response_data=MOCK_EARNINGS_RESPONSE,
    )

    result = await api.get_earnings(df_output=False)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["code"] == "AAPL.US"
    assert result[1]["code"] == "MSFT.US"


@pytest.mark.asyncio
async def test_handles_empty_earnings(mock_api_factory: MockApiFactory) -> None:
    """Test that EarningsApi handles empty earnings array."""
    api, _ = mock_api_factory.create(
        EarningsApi,
        mock_response_data={"type": "Earnings", "earnings": []},
    )

    result = await api.get_earnings(df_output=False)

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_function_calls_validators(mocker: MockerFixture, mock_api_factory: MockApiFactory) -> None:
    """Test that EarningsApi calls validation functions for symbols."""
    spy_validate_normalize_symbol = mocker.spy(eodhd_py.api.earnings, "validate_normalize_symbol")

    api, _ = mock_api_factory.create(
        EarningsApi,
        mock_response_data=MOCK_EARNINGS_RESPONSE,
    )
    await api.get_earnings(symbols=["AAPL.US", "MSFT.US"], df_output=False)

    assert spy_validate_normalize_symbol.call_count == 2
    spy_validate_normalize_symbol.assert_any_call("AAPL.US")
    spy_validate_normalize_symbol.assert_any_call("MSFT.US")
