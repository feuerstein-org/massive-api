"""Package allows for querying the Massive API using an async interface."""

from massive_api.api.dividends import Dividend, DividendsApi
from massive_api.api.reference import (
    ReferenceApi,
    Ticker,
    TickerChange,
    TickerEvent,
    TickerEvents,
    TickerOverview,
)
from massive_api.api.splits import Split, SplitsApi
from massive_api.base import BaseMassiveApi, MassiveApiConfig
from massive_api.client import MassiveApi
from massive_api.exceptions import (
    AuthenticationError,
    MassiveApiError,
    MassiveApiHTTPError,
    MaxRetriesExceededError,
    NotFoundError,
    ServerError,
)
from massive_api.params import (
    AdjustmentType,
    DistributionType,
    DividendFrequency,
    DividendSortField,
    Locale,
    Market,
    Order,
    SplitSortField,
    TickerEventType,
    TickerSortField,
)
from massive_api.utils import build_query_params, gather_bounded

__all__ = (
    "AdjustmentType",
    "AuthenticationError",
    "BaseMassiveApi",
    "DistributionType",
    "Dividend",
    "DividendFrequency",
    "DividendSortField",
    "DividendsApi",
    "Locale",
    "Market",
    "MassiveApi",
    "MassiveApiConfig",
    "MassiveApiError",
    "MassiveApiHTTPError",
    "MaxRetriesExceededError",
    "NotFoundError",
    "Order",
    "ReferenceApi",
    "ServerError",
    "Split",
    "SplitSortField",
    "SplitsApi",
    "Ticker",
    "TickerChange",
    "TickerEvent",
    "TickerEventType",
    "TickerEvents",
    "TickerOverview",
    "TickerSortField",
    "build_query_params",
    "gather_bounded",
)
