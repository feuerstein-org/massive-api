"""Tests for UserApi endpoint class."""

import pytest
from conftest import MockApiFactory

from eodhd_py.api.user import UserApi


@pytest.mark.asyncio
async def test_get_user_info(mock_api_factory: MockApiFactory) -> None:
    """Test UserApi.get_user_info method."""
    mock_response = {
        "name": "Test User",
        "email": "test@example.com",
        "subscriptionType": "All-in-One",
        "paymentMethod": "Not Available",
        "apiRequests": 1234,
        "apiRequestsDate": "2025-11-14",
        "dailyRateLimit": 100000,
        "extraLimit": 0,
        "inviteToken": None,
        "inviteTokenClicked": 0,
        "subscriptionMode": "demo",
        "canManageOrganizations": False,
    }

    api, mock_make_request = mock_api_factory.create(UserApi, mock_response_data=mock_response)

    result = await api.get_user_info()

    # Verify the request was made correctly
    mock_make_request.assert_called_once_with("user", df_output=False)

    # Verify the response matches what we expect
    assert result == mock_response
    assert result["name"] == "Test User"
    assert result["email"] == "test@example.com"
    assert result["subscriptionType"] == "All-in-One"
    assert result["apiRequests"] == 1234
    assert result["dailyRateLimit"] == 100000


@pytest.mark.asyncio
async def test_get_user_info_no_parameters(mock_api_factory: MockApiFactory) -> None:
    """Test that get_user_info calls the correct endpoint."""
    api, mock_make_request = mock_api_factory.create(UserApi, mock_response_data={})

    await api.get_user_info()

    mock_make_request.assert_called_once_with("user", df_output=False)
