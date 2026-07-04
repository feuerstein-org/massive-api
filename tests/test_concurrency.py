"""Test the bounded-concurrency fan-out helper."""

import asyncio

import pytest

from massive_api.utils import gather_bounded


@pytest.mark.asyncio
async def test_gather_bounded_returns_ordered_results() -> None:
    """Test results come back in input order regardless of completion order."""

    async def worker(value: int) -> int:
        await asyncio.sleep((10 - value) * 0.001)
        return value

    results = await gather_bounded(4, *(worker(i) for i in range(10)))

    assert results == list(range(10))


@pytest.mark.asyncio
async def test_gather_bounded_respects_limit() -> None:
    """Test that no more than `limit` coroutines run concurrently."""
    active = 0
    max_active = 0

    async def worker(value: int) -> int:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return value

    limit = 3
    await gather_bounded(limit, *(worker(i) for i in range(12)))

    assert max_active <= limit


@pytest.mark.asyncio
async def test_gather_bounded_rejects_invalid_limit() -> None:
    """Test that a limit below 1 raises ValueError."""

    async def worker() -> int:
        return 1

    coro = worker()
    with pytest.raises(ValueError, match="limit must be >= 1"):
        await gather_bounded(0, coro)
    coro.close()
