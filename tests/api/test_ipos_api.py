"""Test IPOs API."""

from datetime import datetime
from typing import Any

import pandas as pd
import pytest
from conftest import MockApiFactory

from eodhd_py.api.ipos import IposApi

MOCK_IPOS_RESPONSE = {
    "type": "IPOs",
    "description": "Historical and upcoming IPOs",
    "from": "2018-12-02",
    "to": "2018-12-06",
    "ipos": [
        {
            "code": "603629.SHG",
            "name": "Jiangsu Lettall Electronic Co Ltd",
            "exchange": "Shanghai",
            "currency": "CNY",
            "start_date": "2018-12-11",
            "filing_date": "2017-06-15",
            "amended_date": "2018-12-03",
            "price_from": 0,
            "price_to": 0,
            "offer_price": 0,
            "shares": 25000000,
            "deal_type": "Expected",
        },
        {
            "code": "SPK.MC",
            "name": "Solarpack Corporacion Tecnologica S.A",
            "exchange": "MCE",
            "currency": "EUR",
            "start_date": "2018-12-03",
            "filing_date": "2018-11-05",
            "amended_date": "2018-11-20",
            "price_from": 0,
            "price_to": 0,
            "offer_price": 0,
            "shares": 0,
            "deal_type": "Expected",
        },
    ],
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("test_case"),
    [
        {
            "from_date": None,
            "to_date": None,
            "expected_params": {},
        },
        {
            "from_date": datetime(2023, 1, 1),
            "to_date": datetime(2023, 12, 31),
            "expected_params": {"from": "2023-01-01", "to": "2023-12-31"},
        },
        {
            "from_date": datetime(2020, 1, 1),
            "to_date": None,
            "expected_params": {"from": "2020-01-01"},
        },
        {
            "from_date": None,
            "to_date": datetime(2024, 6, 30),
            "expected_params": {"to": "2024-06-30"},
        },
    ],
)
async def test_parameters(mock_api_factory: MockApiFactory, test_case: dict[str, Any]) -> None:
    """Test IposApi business logic with various parameter combinations."""
    api, mock_make_request = mock_api_factory.create(
        IposApi,
        mock_response_data=MOCK_IPOS_RESPONSE,
    )

    await api.get_ipos(
        from_date=test_case["from_date"],
        to_date=test_case["to_date"],
        df_output=False,
    )

    mock_make_request.assert_called_once_with("calendar/ipos", params=test_case["expected_params"], df_output=False)


@pytest.mark.asyncio
async def test_returns_ipos_array(mock_api_factory: MockApiFactory) -> None:
    """Test that IposApi extracts ipos array from response."""
    api, _ = mock_api_factory.create(
        IposApi,
        mock_response_data=MOCK_IPOS_RESPONSE,
    )

    result = await api.get_ipos(df_output=False)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["code"] == "603629.SHG"
    assert result[1]["code"] == "SPK.MC"


@pytest.mark.asyncio
async def test_handles_empty_ipos(mock_api_factory: MockApiFactory) -> None:
    """Test that IposApi handles empty ipos array."""
    api, _ = mock_api_factory.create(
        IposApi,
        mock_response_data={"type": "IPOs", "ipos": []},
    )

    result = await api.get_ipos(df_output=False)

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_returns_dataframe_by_default(mock_api_factory: MockApiFactory) -> None:
    """Test that IposApi returns DataFrame when df_output=True (default)."""
    api, _ = mock_api_factory.create(
        IposApi,
        mock_response_data=MOCK_IPOS_RESPONSE,
    )

    result = await api.get_ipos()

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert list(result["code"]) == ["603629.SHG", "SPK.MC"]
