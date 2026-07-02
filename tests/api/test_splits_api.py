"""Test Splits API."""

from datetime import datetime
from typing import Any

import pytest
from conftest import MockApiFactory
from pytest_mock import MockerFixture

import eodhd_py.api.splits
from eodhd_py.api.splits import SplitsApi


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
    """Test SplitsApi business logic with various parameter combinations."""
    api, mock_make_request = mock_api_factory.create(
        SplitsApi,
        mock_response_data=[
            {
                "date": "1987-06-16",
                "split": "2.000000/1.000000",
            },
            {
                "date": "2000-06-21",
                "split": "2.000000/1.000000",
            },
            {
                "date": "2020-08-31",
                "split": "4.000000/1.000000",
            },
        ],
    )

    await api.get_splits(
        symbol=test_case["symbol"],
        from_date=test_case["from_date"],
        to_date=test_case["to_date"],
        df_output=False,
    )

    mock_make_request.assert_called_once_with(
        f"splits/{test_case['symbol']}", params=test_case["expected_params"], df_output=False
    )


@pytest.mark.asyncio
async def test_function_calls_validators(mocker: MockerFixture, mock_api_factory: MockApiFactory) -> None:
    """Test that SplitsApi calls validation functions."""
    spy_validate_normalize_symbol = mocker.spy(eodhd_py.api.splits, "validate_normalize_symbol")

    api, _ = mock_api_factory.create(SplitsApi)
    await api.get_splits(symbol="AAPL.US", df_output=False)

    spy_validate_normalize_symbol.assert_called_once_with("AAPL.US")
