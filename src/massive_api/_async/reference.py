"""Reference endpoints: tickers, ticker overview, and ticker events."""

from massive_api._async._generated.ticker_events import TickerEventsApiBase
from massive_api._async._generated.ticker_overview import TickerOverviewApiBase
from massive_api._async._generated.tickers import TickersApiBase


class ReferenceApi(TickersApiBase, TickerOverviewApiBase, TickerEventsApiBase):
    """
    The reference endpoints, grouped as one accessor.

    Three generated request layers composed into the single class this client has always
    exposed. Grouping is the client's choice, so it lives here rather than in the manifest.
    """
