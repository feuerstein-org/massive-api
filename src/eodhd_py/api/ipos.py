"""IPOs API endpoint."""

from datetime import datetime
from typing import Any, Literal, overload

import pandas as pd

from eodhd_py.base import BaseEodhdApi


class IposApi(BaseEodhdApi):
    """IposApi endpoint class for historical and upcoming IPO data."""

    @overload
    async def get_ipos(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: Literal[True] = ...,
    ) -> pd.DataFrame: ...

    @overload
    async def get_ipos(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: Literal[False] = ...,
    ) -> list[dict[str, Any]]: ...

    async def get_ipos(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: bool = True,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        """
        Get historical and upcoming IPO data.

        Can be queried by date window. Without dates, default window is "today + 7 days".

        Args:
            from_date: Start date for data (default: today). Uses filing_date for filtering.
            to_date: End date for data (default: today + 7 days). Uses filing_date for filtering.
            df_output: If True (default), return pandas DataFrame. If False, return list of dicts.

        Returns:
            IPO data containing:
            - code: Ticker in EODHD format
            - name: Company name (or null)
            - exchange: Listing exchange (or null)
            - currency: Trading currency (or null)
            - start_date: Expected/effective first trading date (or null)
            - filing_date: Initial filing date (or null)
            - amended_date: Latest amended filing date (or null)
            - price_from: Lower end of indicated price range (0 if not provided)
            - price_to: Upper end of indicated price range (0 if not provided)
            - offer_price: Final priced offer (0 if not priced yet)
            - shares: Shares offered (0 if not provided)
            - deal_type: Lifecycle state (e.g., "Filed", "Expected", "Amended", "Priced")

        """
        params: dict[str, str] = {}

        if from_date is not None:
            params["from"] = from_date.strftime("%Y-%m-%d")
        if to_date is not None:
            params["to"] = to_date.strftime("%Y-%m-%d")

        response: dict[str, Any] = await self._make_request("calendar/ipos", params=params, df_output=False)

        # The API returns a wrapper object with an "ipos" array
        ipos_data: list[dict[str, Any]] = response.get("ipos", [])

        if df_output:
            return pd.DataFrame(ipos_data)

        return ipos_data
