"""Reference endpoints: tickers, ticker overview, and ticker events."""

from massive_api._sync._generated.ticker_events import TickerEventsApiSyncBase
from massive_api._sync._generated.ticker_overview import TickerOverviewApiSyncBase
from massive_api._sync._generated.tickers import TickersApiSyncBase


class ReferenceApiSync(TickersApiSyncBase, TickerOverviewApiSyncBase, TickerEventsApiSyncBase):
    """
    The reference endpoints, grouped as one accessor.

    Three generated request layers composed into the single class this client has always
    exposed. Grouping is the client's choice, so it lives here rather than in the manifest.
    """
