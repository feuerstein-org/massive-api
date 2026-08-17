"""
An async and blocking Python client for the Massive financial-data REST API.

`MassiveApi` is awaitable and `MassiveApiSync` blocks; the two have the same methods and the
same models. Endpoint modules are generated from Massive's OpenAPI document plus
`spec/manifest.yaml` — see the README for how to regenerate them.

Operational errors are spitzeisen's, re-exported here so that catching them never requires
importing the framework or the HTTP library underneath it.
"""

from spitzeisen import gather_bounded, map_bounded
from spitzeisen.exceptions import (
    AuthenticationError,
    HTTPError,
    MaxRetriesExceededError,
    NotFoundError,
    ServerError,
    SpitzeisenError,
    TransportError,
)
from spitzeisen.params import build_query_params

from massive_api._async.aggregates import AggregatesApi
from massive_api._async.client import MassiveApi
from massive_api._async.dividends import DividendsApi
from massive_api._async.reference import ReferenceApi
from massive_api._async.splits import SplitsApi
from massive_api._sync.aggregates import AggregatesApiSync
from massive_api._sync.client import MassiveApiSync
from massive_api._sync.dividends import DividendsApiSync
from massive_api._sync.reference import ReferenceApiSync
from massive_api._sync.splits import SplitsApiSync
from massive_api.config import massive_config
from massive_api.models import (
    AdjustmentType,
    Bar,
    DistributionType,
    Dividend,
    DividendFrequency,
    DividendSortField,
    Locale,
    Market,
    Order,
    Split,
    SplitSortField,
    Ticker,
    TickerChange,
    TickerEvent,
    TickerEvents,
    TickerEventType,
    TickerOverview,
    TickerSortField,
    Timespan,
)

# The configuration used to be a class; it is a factory now, but the call is unchanged
# (`MassiveApiConfig(api_key=...)`), so existing consumers need no edit.
MassiveApiConfig = massive_config

# The client's own vocabulary for operational failures. These are aliases rather than
# subclasses, so `except MassiveApiError` and `except SpitzeisenError` catch the same objects.
MassiveApiError = SpitzeisenError
MassiveApiHTTPError = HTTPError

__all__ = (
    "AdjustmentType",
    "AggregatesApi",
    "AggregatesApiSync",
    "AuthenticationError",
    "Bar",
    "DistributionType",
    "Dividend",
    "DividendFrequency",
    "DividendSortField",
    "DividendsApi",
    "DividendsApiSync",
    "Locale",
    "Market",
    "MassiveApi",
    "MassiveApiConfig",
    "MassiveApiError",
    "MassiveApiHTTPError",
    "MassiveApiSync",
    "MaxRetriesExceededError",
    "NotFoundError",
    "Order",
    "ReferenceApi",
    "ReferenceApiSync",
    "ServerError",
    "Split",
    "SplitSortField",
    "SplitsApi",
    "SplitsApiSync",
    "Ticker",
    "TickerChange",
    "TickerEvent",
    "TickerEventType",
    "TickerEvents",
    "TickerOverview",
    "TickerSortField",
    "Timespan",
    "TransportError",
    "build_query_params",
    "gather_bounded",
    "map_bounded",
    "massive_config",
)
