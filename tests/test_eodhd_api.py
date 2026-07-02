"""Tests for the EodhdApi class."""

from unittest.mock import MagicMock, patch

import pytest

from eodhd_py.client import EodhdApi


@pytest.mark.asyncio
async def test_eod_historical_api_property_caching() -> None:
    """Test that eod_historical_api property caches instances correctly."""
    with patch("eodhd_py.client.EodHistoricalApi") as mock_eod_class:
        mock_instance = MagicMock()
        mock_eod_class.return_value = mock_instance
        mock_eod_class.__name__ = "EodHistoricalApi"

        api = EodhdApi()

        first_result = api.eod_historical_api

        # Verify the instance was created with the correct config
        mock_eod_class.assert_called_once_with(api.config)
        assert first_result is mock_instance

        # Second access should return the same cached instance
        second_result = api.eod_historical_api

        assert first_result is second_result
        assert mock_eod_class.call_count == 1  # Class instantiated only once


@pytest.mark.asyncio
async def test_eod_historical_api_with_config_object() -> None:
    """Test eod_historical_api property when EodhdApi is initialized with config object."""
    with (
        patch("eodhd_py.client.EodHistoricalApi") as mock_eod_class,
        patch("eodhd_py.base.EodhdApiConfig", autospec=True) as mock_config_class,
    ):
        mock_instance = MagicMock()
        mock_eod_class.return_value = mock_instance
        mock_eod_class.__name__ = "EodHistoricalApi"

        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Initialize with config object
        config = mock_config_class()
        api = EodhdApi(config=config)

        # Access the property
        result = api.eod_historical_api

        # Verify EodHistoricalApi was instantiated with the provided config
        mock_eod_class.assert_called_once_with(config)
        assert result is mock_instance
