"""EOD Historical Data API endpoint."""

from datetime import datetime
from typing import Literal, overload

import pandas as pd

from eodhd_py.base import BaseEodhdApi
from eodhd_py.utils import validate_interval, validate_normalize_symbol, validate_order


class EodHistoricalApi(BaseEodhdApi):
    """EodHistoricalApi endpoint class."""

    @overload
    async def get_eod_data(
        self,
        symbol: str,
        interval: str = "d",
        order: str = "a",
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: Literal[True] = ...,
    ) -> pd.DataFrame: ...

    @overload
    async def get_eod_data(
        self,
        symbol: str,
        interval: str = "d",
        order: str = "a",
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: Literal[False] = ...,
    ) -> list[dict[str, str | int]]: ...

    async def get_eod_data(
        self,
        symbol: str,
        interval: str = "d",
        order: str = "a",
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: bool = True,
    ) -> list[dict[str, str | int]] | pd.DataFrame:
        """
        Get EOD data for a supplied symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            interval: Data interval ("d"=daily, "w"=weekly, "m"=monthly)
            order: Order of data ("a"=ascending, "d"=descending)
            from_date: Start date for data
            to_date: End date for data
            df_output: If True (default), return pandas DataFrame. If False, return dict.

        Returns:
            JSON response as a dictionary or pandas DataFrame (based on df_output setting)

        """
        # Parameter aliasing for backend compatibility
        period = interval

        params = {
            "period": period,
            "order": order,
        }

        symbol = validate_normalize_symbol(symbol)
        validate_order(order)
        validate_interval(period, data_type="eod")

        if from_date is not None:
            params["from"] = from_date.strftime("%Y-%m-%d")
        if to_date is not None:
            params["to"] = to_date.strftime("%Y-%m-%d")

        return await self._make_request(f"eod/{symbol}", params=params, df_output=df_output)
