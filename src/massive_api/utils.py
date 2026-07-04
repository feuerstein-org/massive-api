"""General helpers for building requests and running bounded-concurrency fan-outs."""

import asyncio
from collections.abc import Awaitable, Mapping, Sequence
from datetime import date, datetime
from typing import Any, get_args


def coerce_choice(value: str | None, literal: Any, param_name: str) -> str | None:
    """
    Validate `value` against the members of a Literal type.

    Returns the value unchanged, or None if it is None. Raises ValueError (listing the
    allowed values) when `value` is not one of the Literal's members.
    """
    if value is None:
        return None
    allowed: tuple[str, ...] = get_args(literal)
    if value not in allowed:
        joined = ", ".join(allowed)
        msg = f"Invalid {param_name} {value!r}. Allowed values: {joined}."
        raise ValueError(msg)
    return value


def coerce_choices(values: Sequence[str] | None, literal: Any, param_name: str) -> str | None:
    """
    Validate a list of Literal members and join them into a comma-separated string.

    Used for the API's `<field>.any_of` multi-value filters. Returns None for a None or
    empty list. Raises ValueError (listing the allowed values) if any element is invalid.
    """
    if not values:
        return None
    allowed: tuple[str, ...] = get_args(literal)
    invalid = [value for value in values if value not in allowed]
    if invalid:
        joined = ", ".join(allowed)
        msg = f"Invalid {param_name} {invalid!r}. Allowed values: {joined}."
        raise ValueError(msg)
    return ",".join(values)


def coerce_date(value: str | date | datetime | None, param_name: str) -> str | None:
    """
    Normalize a date value to a "YYYY-MM-DD" string.

    Accepts a date/datetime object or an ISO date string. Returns None if `value` is
    None. Raises ValueError when a string is not a valid ISO date.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        msg = f"Invalid {param_name} {value!r}. Expected an ISO date (YYYY-MM-DD)."
        raise ValueError(msg) from None


def coerce_max_results(value: int | None, param_name: str = "max_results") -> int | None:
    """
    Validate a client-side `max_results` cap is a positive integer.

    There is no API-imposed ceiling: the cap may span many pages. Returns the value
    unchanged, or None (meaning "no cap"). Raises ValueError if < 1.
    """
    if value is None:
        return None
    if value < 1:
        msg = f"Invalid {param_name} {value}. Must be >= 1."
        raise ValueError(msg)
    return value


def resolve_page_size(max_results: int | None, api_max: int) -> int:
    """
    Choose the effective per-request page size.

    Always requests `api_max` (fewest requests), shrinking to `max_results` when that cap
    is smaller so the final page is not over-fetched. Assumes `max_results` is validated.
    """
    if max_results is None:
        return api_max
    return min(api_max, max_results)


def build_query_params(raw: Mapping[str, Any]) -> dict[str, str]:
    """
    Build a query-parameter dict, dropping None values and normalizing types.

    Booleans become "true"/"false", dates/datetimes become "YYYY-MM-DD", and everything
    else is stringified.
    """
    params: dict[str, str] = {}
    for key, value in raw.items():
        if value is None:
            continue
        if isinstance(value, bool):
            params[key] = "true" if value else "false"
        elif isinstance(value, datetime):
            params[key] = value.strftime("%Y-%m-%d")
        elif isinstance(value, date):
            params[key] = value.isoformat()
        else:
            params[key] = str(value)
    return params


async def gather_bounded[T](limit: int = 50, *awaitables: Awaitable[T]) -> list[T]:
    """
    Run `awaitables` concurrently with at most `limit` in flight at once.

    Use this to saturate the shared rate limiter (e.g. fetching minute bars for
    ~10k tickers) without spawning an unbounded number of coroutines. Results are
    returned in the same order as the inputs.
    """
    if limit < 1:
        msg = "limit must be >= 1"
        raise ValueError(msg)
    semaphore = asyncio.Semaphore(limit)

    async def _run(awaitable: Awaitable[T]) -> T:
        async with semaphore:
            return await awaitable

    return await asyncio.gather(*(_run(awaitable) for awaitable in awaitables))
