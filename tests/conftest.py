"""Test fixtures for API client tests."""

import random
import string
from dataclasses import dataclass
from typing import Any, TypeVar
from unittest.mock import AsyncMock

import aiohttp
import pytest
from pytest_mock import MockerFixture

from eodhd_py.base import BaseEodhdApi, EodhdApiConfig


def generate_random_api_key() -> str:
    """Generate a random API key matching [A-Za-z0-9.]{16,32}."""
    chars = string.ascii_letters + string.digits + "."
    length = random.randint(16, 32)
    return "".join(random.choice(chars) for _ in range(length))


@dataclass
class MockApiConfig:
    """Shared configuration for all API mocking."""

    api_key: str = "demo"
    close_session_on_aexit: bool = True
    # Test specific options
    mock_response_data: dict[str, Any] | None = None
    mock_status_code: int = 200
    mock_raise_for_status: bool = False


# Factories
T = TypeVar("T", bound=BaseEodhdApi)


class MockApiFactory:
    """
    Factory for testing subclasses that inherit from BaseEodhdApi.

    Creates real instances but mocks the _make_request method.
    Use this when testing EodHistoricalApi, etc.
    """

    def __init__(self, mocker: MockerFixture) -> None:
        """Initialize with pytest-mock's mocker fixture."""
        self.mocker = mocker

    def create(self, api_class: type[T], config: MockApiConfig | None = None, **kwargs: Any) -> tuple[T, AsyncMock]:
        """
        Create a mock instance of any API subclass.

        kwargs will be passed to config if config is None.
        """
        if config is None:
            config = MockApiConfig(**kwargs)

        # Create real config and instance
        real_config = EodhdApiConfig(api_key=config.api_key)
        instance = api_class(config=real_config)

        # Mock only _make_request
        mock_make_request = self.mocker.AsyncMock(return_value=config.mock_response_data or {})

        if config.mock_raise_for_status:
            mock_make_request.side_effect = aiohttp.ClientError("Mock error")

        instance._make_request = mock_make_request

        return instance, mock_make_request


# Fixtures
@pytest.fixture
def mock_api_factory(mocker: MockerFixture) -> MockApiFactory:
    """For integration testing of subclasses."""
    return MockApiFactory(mocker)


@pytest.fixture
def test_config() -> EodhdApiConfig:
    """
    Fixture providing a pre-configured EodhdApiConfig with standard test values.

    This eliminates the need to manually specify rate limits in every test.

    Examples:
        def test_something(test_config):
            api = BaseEodhdApi(config=test_config)
            # Rate limits are already configured

    """
    return EodhdApiConfig(
        api_key=generate_random_api_key(),
        daily_calls_rate_limit=50000,
        daily_remaining_limit=4000,
        minute_requests_rate_limit=100,
        minute_remaining_limit=50,
        extra_limit=10,
        # This is required because if CI runs shortly before midnight UTC,
        # tests may time out due to rate limit resets.
        daily_max_sleep=60,
        minute_max_sleep=60,
    )
