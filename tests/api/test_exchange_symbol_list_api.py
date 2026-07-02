"""Test Exchange Symbol List API."""

from typing import Any

import pytest
from conftest import MockApiFactory

from eodhd_py.api.exchange_symbol_list import ExchangeSymbolListApi


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("test_case"),
    [
        {
            "exchange_code": "US",
            "delisted": False,
            "type": None,
            "expected_params": {},
        },
        {
            "exchange_code": "LSE",
            "delisted": True,
            "type": None,
            "expected_params": {"delisted": "1"},
        },
        {
            "exchange_code": "XETRA",
            "delisted": False,
            "type": "common_stock",
            "expected_params": {"type": "common_stock"},
        },
        {
            "exchange_code": "NYSE",
            "delisted": True,
            "type": "etf",
            "expected_params": {"delisted": "1", "type": "etf"},
        },
        {
            "exchange_code": "WAR",
            "delisted": False,
            "type": "preferred_stock",
            "expected_params": {"type": "preferred_stock"},
        },
        {
            "exchange_code": "NASDAQ",
            "delisted": False,
            "type": "fund",
            "expected_params": {"type": "fund"},
        },
    ],
)
async def test_parameters(mock_api_factory: MockApiFactory, test_case: dict[str, Any]) -> None:
    """Test ExchangeSymbolListApi business logic with various parameter combinations."""
    api, mock_make_request = mock_api_factory.create(
        ExchangeSymbolListApi,
        mock_response_data=[
            {
                "Code": "CDR",
                "Name": "CD PROJEKT SA",
                "Country": "Poland",
                "Exchange": "WAR",
                "Currency": "PLN",
                "Type": "Common Stock",
                "Isin": "PLOPTTC00011",
            },
            {
                "Code": "PKN",
                "Name": "PKN Orlen SA",
                "Country": "Poland",
                "Exchange": "WAR",
                "Currency": "PLN",
                "Type": "Common Stock",
                "Isin": "PLPKN0000018",
            },
        ],
    )

    await api.get_exchange_symbols(
        exchange_code=test_case["exchange_code"],
        delisted=test_case["delisted"],
        type=test_case["type"],
        df_output=False,
    )

    mock_make_request.assert_called_once_with(
        f"exchange-symbol-list/{test_case['exchange_code']}",
        params=test_case["expected_params"],
        df_output=False,
    )
