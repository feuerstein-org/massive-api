"""
Models that describe the payload differently from the way the vendor ships it.

Everything here reshapes across fields, which is the one thing a schema cannot express
and a generator therefore cannot reproduce. Per-field quirks — a renamed key, an epoch
timestamp — are declared in spec/manifest.yaml instead and generated; see models/_generated.py.
"""

import datetime as dt

from pydantic import AliasPath, Field
from spitzeisen import VendorModel

from massive_api.params import Locale, Market  # noqa: TC001 - pydantic needs these at runtime


class TickerOverview(VendorModel):
    """Detailed company/ticker information from the Ticker Overview endpoint."""

    ticker: str
    name: str
    market: Market
    locale: Locale
    active: bool
    currency_name: str
    type: str | None = None
    primary_exchange: str | None = None
    cik: str | None = None
    composite_figi: str | None = None
    market_cap: float | None = None
    total_employees: int | None = None
    weighted_shares_outstanding: int | None = None
    share_class_shares_outstanding: int | None = None
    share_class_figi: str | None = None
    round_lot: int | None = None
    sic_code: str | None = None
    sic_description: str | None = None
    homepage_url: str | None = None
    description: str | None = None
    phone_number: str | None = None
    # Flattened from the nested `address` object in the response.
    address1: str | None = Field(default=None, validation_alias=AliasPath("address", "address1"))
    address2: str | None = Field(default=None, validation_alias=AliasPath("address", "address2"))
    city: str | None = Field(default=None, validation_alias=AliasPath("address", "city"))
    state: str | None = Field(default=None, validation_alias=AliasPath("address", "state"))
    postal_code: str | None = Field(default=None, validation_alias=AliasPath("address", "postal_code"))
    # Flattened from the nested `branding` object in the response.
    icon_url: str | None = Field(default=None, validation_alias=AliasPath("branding", "icon_url"))
    logo_url: str | None = Field(default=None, validation_alias=AliasPath("branding", "logo_url"))
    list_date: dt.date | None = None
    delisted_utc: dt.datetime | None = None
    last_updated_utc: dt.datetime | None = None
    ticker_root: str | None = None
    ticker_suffix: str | None = None
