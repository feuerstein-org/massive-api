"""Test fixtures for API client tests."""

import random
import string
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, TypeVar

import pytest
from pytest_mock import MockerFixture

from massive_api.base import BaseMassiveApi, MassiveApiConfig


def generate_random_api_key() -> str:
    """Generate a random non-empty API key."""
    chars = string.ascii_letters + string.digits
    length = random.randint(16, 32)
    return "".join(random.choice(chars) for _ in range(length))


@dataclass
class MockApiConfig:
    """Shared configuration for all API mocking."""

    api_key: str = "test"
    # Records returned by a mocked `_get_all_pages` (list endpoints).
    mock_pages: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    # `results` object returned by a mocked `_make_request` (single-record endpoints).
    mock_results: dict[str, Any] = field(default_factory=dict[str, Any])


T = TypeVar("T", bound=BaseMassiveApi)


class MockApiFactory:
    """
    Factory for testing subclasses that inherit from BaseMassiveApi.

    Creates real instances but mocks the base I/O methods (`_get_all_pages` and
    `_make_request`) so endpoint business logic can be tested without HTTP.
    """

    def __init__(self, mocker: MockerFixture) -> None:
        """Initialize with pytest-mock's mocker fixture."""
        self.mocker = mocker

    def create(
        self,
        api_class: type[T],
        config: MockApiConfig | None = None,
        **kwargs: Any,
    ) -> tuple[T, SimpleNamespace]:
        """
        Create a mock instance of any API subclass.

        kwargs will be passed to MockApiConfig if config is None.

        Returns the instance and a namespace with `._get_all_pages` and `._make_request` mocks.
        """
        if config is None:
            config = MockApiConfig(**kwargs)

        real_config = MassiveApiConfig(api_key=config.api_key)
        instance = api_class(config=real_config)

        mock_get_all_pages = self.mocker.AsyncMock(return_value=config.mock_pages)
        mock_make_request = self.mocker.AsyncMock(return_value={"results": config.mock_results})

        instance._get_all_pages = mock_get_all_pages
        instance._make_request = mock_make_request

        return instance, SimpleNamespace(get_all_pages=mock_get_all_pages, request_json=mock_make_request)


@pytest.fixture
def mock_api_factory(mocker: MockerFixture) -> MockApiFactory:
    """For integration testing of subclasses."""
    return MockApiFactory(mocker)


@pytest.fixture
def test_config() -> MassiveApiConfig:
    """Provide a pre-configured MassiveApiConfig with standard test values."""
    return MassiveApiConfig(
        api_key=generate_random_api_key(),
        rate_limit_max_sleep=60,
    )


def with_defaults(params: dict[str, str], defaults: dict[str, str]) -> dict[str, str]:
    """Expected wire params: the SDK's always-sent defaults, overridden by anything the test specifies."""
    return {**defaults, **params}
