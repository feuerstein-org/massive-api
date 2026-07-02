"""Test Exchanges API."""

import pytest
from conftest import MockApiFactory

from eodhd_py.api.exchanges import ExchangesApi


@pytest.mark.asyncio
async def test_get_exchanges(mock_api_factory: MockApiFactory) -> None:
    """Test ExchangesApi returns exchange list."""
    api, mock_make_request = mock_api_factory.create(
        ExchangesApi,
        mock_response_data=[
            {
                "Name": "USAStocks",
                "Code": "US",
                "OperatingMIC": "XNAS,XNYS",
                "Country": "USA",
                "Currency": "USD",
                "CountryISO2": "US",
                "CountryISO3": "USA",
            },
            {
                "Name": "LondonExchange",
                "Code": "LSE",
                "OperatingMIC": "XLON",
                "Country": "UK",
                "Currency": "GBP",
                "CountryISO2": "GB",
                "CountryISO3": "GBR",
            },
        ],
    )

    await api.get_exchanges(df_output=False)

    mock_make_request.assert_called_once_with("exchanges-list", df_output=False)


@pytest.mark.asyncio
async def test_get_exchanges_df_output(mock_api_factory: MockApiFactory) -> None:
    """Test ExchangesApi with DataFrame output."""
    api, mock_make_request = mock_api_factory.create(
        ExchangesApi,
        mock_response_data=[
            {
                "Name": "USAStocks",
                "Code": "US",
                "OperatingMIC": "XNAS,XNYS",
                "Country": "USA",
                "Currency": "USD",
                "CountryISO2": "US",
                "CountryISO3": "USA",
            },
        ],
    )

    await api.get_exchanges(df_output=True)

    mock_make_request.assert_called_once_with("exchanges-list", df_output=True)
