"""Main EODHD API client."""

from typing import Self, cast

from eodhd_py.api.dividends import DividendsApi
from eodhd_py.api.earnings import EarningsApi
from eodhd_py.api.eod_historical import EodHistoricalApi
from eodhd_py.api.exchange_symbol_list import ExchangeSymbolListApi
from eodhd_py.api.exchanges import ExchangesApi
from eodhd_py.api.intraday_historical import IntradayHistoricalApi
from eodhd_py.api.ipos import IposApi
from eodhd_py.api.splits import SplitsApi
from eodhd_py.api.user import UserApi
from eodhd_py.base import BaseEodhdApi, EodhdApiConfig


class EodhdApi:
    """
    EODHD API Client Class

    This class serves as the main entry point for interacting with various EODHD API endpoints.
    Either pass a EodhdApiConfig object or an api_key string to the constructor.

    After instantiation, access specific API endpoints via properties.
    E.g. `api.eod_historical_api`.
    """

    def __init__(self, config: EodhdApiConfig | None = None, api_key: str = "demo") -> None:
        """Initialize the EodhdApi client with either a config or an api_key."""
        self.config = config or EodhdApiConfig(api_key=api_key)
        self._endpoint_instances: dict[str, BaseEodhdApi] = {}

    async def __aenter__(self) -> Self:
        """Enter the asynchronous context manager."""
        # Increment reference count for session usage
        self.config.increment_session_ref()
        return self

    # TODO: handle exceptions
    async def __aexit__(self, *args) -> None:  # type: ignore # noqa: ANN002
        """Exit the asynchronous context manager and close session if no other instances are using it."""
        # Decrement reference count
        self.config.decrement_session_ref()
        # Only close session when no more references exist
        if self.config.should_close_session() and not self.config.session.closed:
            await self.config.session.close()

    def _get_endpoint(self, endpoint_class: type[BaseEodhdApi]) -> BaseEodhdApi:
        """Generic endpoint getter to reduce boilerplate."""
        key = endpoint_class.__name__
        if key not in self._endpoint_instances:
            self._endpoint_instances[key] = endpoint_class(self.config)
        return self._endpoint_instances[key]

    @property
    def eod_historical_api(self) -> EodHistoricalApi:
        """EodHistoricalApi client."""
        return cast("EodHistoricalApi", self._get_endpoint(EodHistoricalApi))

    @property
    def intraday_historical_api(self) -> IntradayHistoricalApi:
        """IntradayHistoricalApi client."""
        return cast("IntradayHistoricalApi", self._get_endpoint(IntradayHistoricalApi))

    @property
    def user_api(self) -> UserApi:
        """UserApi client."""
        return cast("UserApi", self._get_endpoint(UserApi))

    @property
    def dividends_api(self) -> DividendsApi:
        """DividendsApi client."""
        return cast("DividendsApi", self._get_endpoint(DividendsApi))

    @property
    def splits_api(self) -> SplitsApi:
        """SplitsApi client."""
        return cast("SplitsApi", self._get_endpoint(SplitsApi))

    @property
    def earnings_api(self) -> EarningsApi:
        """EarningsApi client."""
        return cast("EarningsApi", self._get_endpoint(EarningsApi))

    @property
    def exchanges_api(self) -> ExchangesApi:
        """ExchangesApi client."""
        return cast("ExchangesApi", self._get_endpoint(ExchangesApi))

    @property
    def ipos_api(self) -> IposApi:
        """IposApi client."""
        return cast("IposApi", self._get_endpoint(IposApi))

    @property
    def exchange_symbol_list_api(self) -> ExchangeSymbolListApi:
        """ExchangeSymbolListApi client."""
        return cast("ExchangeSymbolListApi", self._get_endpoint(ExchangeSymbolListApi))
