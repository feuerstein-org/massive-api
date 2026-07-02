"""Intraday Historical Data API endpoint."""

from datetime import datetime
from typing import Literal, overload

import pandas as pd

from eodhd_py.base import BaseEodhdApi
from eodhd_py.utils import validate_interval, validate_normalize_symbol


class IntradayHistoricalApi(BaseEodhdApi):
    """
    IntradayHistoricalApi endpoint class.

    Provides access to EODHD's Intraday Historical Data API endpoint,
    which returns historical intraday data for stocks with various time
    intervals (1m, 5m, 1h) and supports date range filtering.

    This class inherits from BaseEodhdApi and follows the same patterns
    as other endpoint classes in the library.
    """

    @overload
    async def get_intraday_data(
        self,
        symbol: str,
        interval: str = "5m",
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        split_dt: bool = False,
        df_output: Literal[True] = ...,
    ) -> pd.DataFrame: ...

    @overload
    async def get_intraday_data(
        self,
        symbol: str,
        interval: str = "5m",
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        split_dt: bool = False,
        df_output: Literal[False] = ...,
    ) -> list[dict[str, str | int]]: ...

    async def get_intraday_data(
        self,
        symbol: str,
        interval: str = "5m",
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        split_dt: bool = False,
        df_output: bool = True,
    ) -> list[dict[str, str | int]] | pd.DataFrame:
        """
        Get intraday historical data for a supplied symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            interval: Time interval ("1m", "5m", "1h")
            from_date: Start date for data
            to_date: End date for data
            split_dt: If True, splits date and time into separate fields in the output
            df_output: If True (default), return pandas DataFrame. If False, return dict.

        Returns:
            JSON response as a dictionary or pandas DataFrame (based on df_output setting)

        Raises:
            ValueError: If symbol or interval parameters are invalid
            aiohttp.ClientError: If the HTTP request fails

        """
        params = {
            "interval": interval,
        }

        # Validate parameters
        symbol = validate_normalize_symbol(symbol)
        validate_interval(interval, data_type="intraday")

        if from_date is not None:
            params["from"] = from_date.strftime("%Y-%m-%d")
        if to_date is not None:
            params["to"] = to_date.strftime("%Y-%m-%d")
        if split_dt:
            params["split-dt"] = "1"

        return await self._make_request(f"intraday/{symbol}", params=params, df_output=df_output)
