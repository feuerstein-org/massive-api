"""Test Dividends API."""

from datetime import datetime
from typing import Any

import pytest
from conftest import MockApiFactory
from pytest_mock import MockerFixture

import eodhd_py.api.dividends
from eodhd_py.api.dividends import DividendsApi


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("test_case"),
    [
        {
            "symbol": "AAPL.US",
            "from_date": None,
            "to_date": None,
            "expected_params": {},
        },
        {
            "symbol": "MSFT.US",
            "from_date": datetime(2023, 1, 1),
            "to_date": datetime(2023, 12, 31),
            "expected_params": {"from": "2023-01-01", "to": "2023-12-31"},
        },
        {
            "symbol": "NVDA.US",
            "from_date": datetime(2020, 1, 1),
            "to_date": None,
            "expected_params": {"from": "2020-01-01"},
        },
        {
            "symbol": "TSLA.US",
            "from_date": None,
            "to_date": datetime(2024, 6, 30),
            "expected_params": {"to": "2024-06-30"},
        },
    ],
)
async def test_parameters(mock_api_factory: MockApiFactory, test_case: dict[str, Any]) -> None:
    """Test DividendsApi business logic with various parameter combinations."""
    api, mock_make_request = mock_api_factory.create(
        DividendsApi,
        mock_response_data=[
            {
                "date": "2012-08-09",
                "declarationDate": "2012-07-24",
                "recordDate": "2012-08-13",
                "paymentDate": "2012-08-16",
                "period": "Quarterly",
                "value": 0.0946,
                "unadjustedValue": 2.6488,
                "currency": "USD",
            }
        ],
    )

    await api.get_dividends(
        symbol=test_case["symbol"],
        from_date=test_case["from_date"],
        to_date=test_case["to_date"],
        df_output=False,
    )

    mock_make_request.assert_called_once_with(
        f"div/{test_case['symbol']}", params=test_case["expected_params"], df_output=False
    )


@pytest.mark.asyncio
async def test_function_calls_validators(mocker: MockerFixture, mock_api_factory: MockApiFactory) -> None:
    """Test that DividendsApi calls validation functions."""
    spy_validate_normalize_symbol = mocker.spy(eodhd_py.api.dividends, "validate_normalize_symbol")

    api, _ = mock_api_factory.create(DividendsApi)
    await api.get_dividends(symbol="AAPL.US", df_output=False)

    spy_validate_normalize_symbol.assert_called_once_with("AAPL.US")
