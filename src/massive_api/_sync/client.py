"""The blocking Massive API client."""

from typing import Self

from spitzeisen import ClientConfig

from massive_api._sync.aggregates import AggregatesApiSync
from massive_api._sync.dividends import DividendsApiSync
from massive_api._sync.reference import ReferenceApiSync
from massive_api._sync.splits import SplitsApiSync
from massive_api.config import massive_config


class MassiveApiSync:
    """
    Massive API client.

    Pass either a `ClientConfig` or an api_key. Endpoints hang off properties:
    `api.reference_api.get_all_tickers()`, `api.splits_api.get_splits()`. Every endpoint
    instance shares this client's transport and rate limiter.
    """

    def __init__(self, config: ClientConfig | None = None, api_key: str | None = None) -> None:
        """Initialise from a config or an api_key; one of the two is required."""
        if config is not None:
            self.config = config
        elif api_key:
            self.config = massive_config(api_key)
        else:
            msg = "Neither a valid config nor a valid API key was passed."
            raise ValueError(msg)
        self._endpoints: dict[str, object] = {}

    def __enter__(self) -> Self:
        """Register this client as a holder of the shared transport."""
        self.config.acquire()
        return self

    def __exit__(self, *args: object) -> None:
        """Release the shared transport, closing it once the last holder exits."""
        if self.config.release():
            self.config.transport.close()  # type: ignore[union-attr]

    def _endpoint[T](self, cls: type[T]) -> T:
        """One instance per endpoint class, built on first use and reused after."""
        if cls.__name__ not in self._endpoints:
            self._endpoints[cls.__name__] = cls(self.config)  # type: ignore[call-arg]
        return self._endpoints[cls.__name__]  # type: ignore[return-value]

    @property
    def reference_api(self) -> ReferenceApiSync:
        """Tickers, ticker overview and ticker events."""
        return self._endpoint(ReferenceApiSync)

    @property
    def splits_api(self) -> SplitsApiSync:
        """Stock splits."""
        return self._endpoint(SplitsApiSync)

    @property
    def dividends_api(self) -> DividendsApiSync:
        """Cash dividends."""
        return self._endpoint(DividendsApiSync)

    @property
    def aggregates_api(self) -> AggregatesApiSync:
        """Custom OHLCV aggregate bars."""
        return self._endpoint(AggregatesApiSync)
