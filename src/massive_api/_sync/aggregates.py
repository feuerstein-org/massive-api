"""Custom OHLCV aggregate bars."""

from datetime import date, datetime
from typing import Any

from massive_api._sync._generated.aggregates import AggregatesApiSyncBase
from massive_api.params import Timespan  # noqa: TC001 - part of the runtime signature

MIN_MULTIPLIER = 1


class AggregatesApiSync(AggregatesApiSyncBase):
    """
    Aggregates endpoint, with the one rule the vendor's schema does not state.

    A multiplier below 1 is rejected locally: the API answers it with an opaque error, and
    failing here names the argument instead.
    """

    def _check_multiplier(self, multiplier: int) -> None:
        if multiplier < MIN_MULTIPLIER:
            msg = f"Invalid multiplier {multiplier}. Must be >= {MIN_MULTIPLIER}."
            raise ValueError(msg)

    def get_custom_bars_raw(  # type: ignore[override]
        self,
        ticker: str,
        multiplier: int,
        timespan: Timespan,
        from_date: str | date | datetime,
        to_date: str | date | datetime,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Reject an impossible multiplier before spending a request on it."""
        self._check_multiplier(multiplier)
        return super().get_custom_bars_raw(ticker, multiplier, timespan, from_date, to_date, **kwargs)
