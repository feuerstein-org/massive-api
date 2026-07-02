"""Exchanges API endpoint."""

from typing import Literal, overload

import pandas as pd

from eodhd_py.base import BaseEodhdApi


class ExchangesApi(BaseEodhdApi):
    """ExchangesApi endpoint class."""

    @overload
    async def get_exchanges(
        self,
        df_output: Literal[True] = ...,
    ) -> pd.DataFrame: ...

    @overload
    async def get_exchanges(
        self,
        df_output: Literal[False] = ...,
    ) -> list[dict[str, str]]: ...

    async def get_exchanges(
        self,
        df_output: bool = True,
    ) -> list[dict[str, str]] | pd.DataFrame:
        """
        Get the list of supported exchanges.

        Args:
            df_output: If True (default), return pandas DataFrame. If False, return list of dicts.

        Returns:
            Exchange data containing:
            - Name: Full name of the exchange
            - Code: Exchange code used in EODHD APIs
            - OperatingMIC: MIC codes for operating venues
            - Country: Country where the exchange operates
            - Currency: Default trading currency
            - CountryISO2: ISO2 country code
            - CountryISO3: ISO3 country code

        Note:
            The API returns not only stock exchanges but also several other asset classes:
            - EUFUND: Europe Fund Virtual Exchange
            - CC: Cryptocurrencies
            - FOREX: Currency market
            - GBOND: Government Bonds
            - MONEY: Reference Rates & Benchmarks

        """
        return await self._make_request("exchanges-list", df_output=df_output)
