"""Main Massive API client."""

from typing import Self, cast

from massive_api.api.reference import ReferenceApi
from massive_api.api.splits import SplitsApi
from massive_api.base import BaseMassiveApi, MassiveApiConfig


class MassiveApi:
    """
    Massive API Client Class

    This class is the main entry point for interacting with the Massive REST API.
    Either pass a MassiveApiConfig object or an api_key string to the constructor.

    After instantiation, access specific API endpoints via properties,
    e.g. `api.reference_api.get_all_tickers()` or `api.splits_api.get_splits()`.
    """

    def __init__(self, config: MassiveApiConfig | None = None, api_key: str | None = None) -> None:
        """Initialize the MassiveApi client with either a config or an api_key."""
        if config is not None:
            self.config = config
        elif api_key:
            self.config = MassiveApiConfig(api_key=api_key)
        else:
            msg = "Neither a valid config nor a valid API key was passed."
            raise ValueError(msg)
        self._endpoint_instances: dict[str, BaseMassiveApi] = {}

    async def __aenter__(self) -> Self:
        """Enter the asynchronous context manager."""
        self.config.increment_session_ref()
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore # noqa: ANN002
        """Exit the asynchronous context manager and close session if no other instances are using it."""
        self.config.decrement_session_ref()
        if self.config.should_close_session() and not self.config.session.closed:
            await self.config.session.close()

    def _get_endpoint(self, endpoint_class: type[BaseMassiveApi]) -> BaseMassiveApi:
        """Generic endpoint getter"""
        key = endpoint_class.__name__
        if key not in self._endpoint_instances:
            self._endpoint_instances[key] = endpoint_class(self.config)
        return self._endpoint_instances[key]

    @property
    def reference_api(self) -> ReferenceApi:
        """ReferenceApi client (all-tickers, ticker-overview, ticker-events)."""
        return cast("ReferenceApi", self._get_endpoint(ReferenceApi))

    @property
    def splits_api(self) -> SplitsApi:
        """SplitsApi client."""
        return cast("SplitsApi", self._get_endpoint(SplitsApi))
