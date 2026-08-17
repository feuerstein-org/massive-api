"""
Test fixtures.

The request path itself — retries, rate limiting, pagination, validation modes — belongs to
spitzeisen and is tested there; its pytest plugin supplies `mock_api_factory`, `router` and
the transport fixtures automatically. What is left here is the vocabulary these tests already
used, mapped onto the plugin so the endpoint tests read the same as before.
"""

import random
import string
from typing import Any

import pytest
from spitzeisen import ClientConfig
from spitzeisen.testing import MockApiConfig, MockApiFactory

from massive_api.config import massive_config


def generate_random_api_key() -> str:
    """Generate a random non-empty API key."""
    chars = string.ascii_letters + string.digits
    length = random.randint(16, 32)
    return "".join(random.choice(chars) for _ in range(length))


class MassiveMockApiFactory(MockApiFactory):
    """
    The plugin's factory, speaking this suite's argument names.

    Endpoint tests were written against `mock_pages`/`mock_results`; the framework calls the
    same things `pages`/`result`. Translating here keeps those tests unchanged.
    """

    def create(self, api_class: Any, config: MockApiConfig | None = None, **kwargs: Any) -> tuple[Any, Any]:
        """Build an endpoint instance with its request path stubbed."""
        if config is None:
            config = MockApiConfig(
                base_url="https://api.massive.com",
                pages=kwargs.pop("mock_pages", []),
                # Single-resource endpoints unwrap the envelope themselves, so the stub has
                # to return one — these tests supply just the inner object.
                result={"results": kwargs.pop("mock_results", None)},
                **kwargs,
            )
        instance, mocks = super().create(api_class, config)
        # These tests know the single-resource stub as `request_json`; the plugin calls it
        # `request`. Expose both so the test bodies stay as they were.
        mocks.request_json = mocks.request
        return instance, mocks


@pytest.fixture
def mock_api_factory(mocker: object) -> MassiveMockApiFactory:
    """Build endpoint instances with their request path stubbed out."""
    return MassiveMockApiFactory(mocker)


@pytest.fixture
def test_config() -> ClientConfig:
    """A configuration with standard test values."""
    return massive_config(generate_random_api_key(), rate_limit_max_sleep=60)


def with_defaults(params: dict[str, str], defaults: dict[str, str]) -> dict[str, str]:
    """Expected wire params: the SDK's always-sent defaults, overridden by anything the test specifies."""
    return {**defaults, **params}


def assert_endpoint_call(mock: Any, path: str, params: dict[str, str], **kwargs: Any) -> None:
    """
    Assert an endpoint asked the request path for `path` with `params`.

    The first argument is an `EndpointSpec` rather than a bare string now, so these tests
    check the path it carries instead of comparing the whole object — which is what they were
    really asserting all along.
    """
    spec, actual_params = mock.call_args.args[:2]
    call_kwargs: dict[str, Any] = dict(mock.call_args.kwargs)
    # Path placeholders travel separately now rather than being interpolated into an endpoint
    # string, so fill them back in to compare against the URL these tests were written around.
    placeholders = {name for _, name, _, _ in string.Formatter().parse(str(spec.path)) if name}
    path_values: dict[str, Any] = {key: call_kwargs.pop(key) for key in list(call_kwargs) if key in placeholders}

    assert spec.path.format(**path_values) == path
    assert actual_params == params
    assert call_kwargs == kwargs
