"""Tests for the MassiveApi client, endpoint wiring, and shared session behavior."""

import pytest

from massive_api.api.dividends import DividendsApi
from massive_api.api.reference import ReferenceApi
from massive_api.api.splits import SplitsApi
from massive_api.base import BaseMassiveApi, MassiveApiConfig
from massive_api.client import MassiveApi

API_ENDPOINTS = [
    ("reference_api", ReferenceApi),
    ("splits_api", SplitsApi),
    ("dividends_api", DividendsApi),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("config", "api_key", "error"),
    [
        (MassiveApiConfig(api_key="test"), "", None),
        (None, "test", None),
        (None, "", ValueError),
    ],
)
async def test_base_massive_api_init(
    config: MassiveApiConfig | None,
    api_key: str,
    error: type[ValueError] | None,
) -> None:
    """Test initialization of BaseMassiveApi with various config and api_key combinations."""
    if error:
        with pytest.raises(error, match="Either config or api_key must be provided"):
            BaseMassiveApi(config=config, api_key=api_key)
    else:
        api = BaseMassiveApi(config=config, api_key=api_key)
        assert api.config is not None
        assert api.session is not None
        assert api.BASE_URL == "https://api.massive.com"


@pytest.mark.asyncio
@pytest.mark.parametrize(("api_property_name", "api_class"), API_ENDPOINTS)
async def test_lazy_loading_property(api_property_name: str, api_class: type) -> None:
    """Test lazy loading and caching of API endpoint properties."""
    config = MassiveApiConfig(api_key="test")
    api = MassiveApi(config=config)

    assert api_class.__name__ not in api._endpoint_instances

    endpoint_instance = getattr(api, api_property_name)
    assert isinstance(endpoint_instance, api_class)
    assert api_class.__name__ in api._endpoint_instances

    # Second access returns the same cached instance.
    assert getattr(api, api_property_name) is endpoint_instance


@pytest.mark.asyncio
async def test_multiple_nested_context_managers() -> None:
    """Test that nested context managers share the session and manage ref count correctly."""
    config = MassiveApiConfig(api_key="test")

    assert config._session_ref_count == 0

    async with BaseMassiveApi(config=config) as api1:
        assert config._session_ref_count == 1
        assert not api1.config.session.closed

        async with MassiveApi(config=config) as api2:
            assert api1.config.session is api2.config.session
            assert config._session_ref_count == 2

        assert config._session_ref_count == 1
        assert not api1.config.session.closed

    assert config._session_ref_count == 0
    assert config.session.closed
