"""
Field types for values the vendor encodes in ways pydantic cannot infer.

These are pointed at from `spec/manifest.yaml` via `type_overrides`, so a per-field quirk is
declared once here rather than hand-written into a model. They live in this client rather than
in spitzeisen: another vendor's "timestamp" may well mean something else.
"""

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BeforeValidator


def _from_epoch_millis(value: Any) -> Any:
    """
    Read a Unix *millisecond* timestamp as a UTC datetime.

    Pydantic's own int-to-datetime coercion assumes seconds, so a bare integer would be
    misread by three orders of magnitude. Booleans are passed through untouched because
    `bool` is a subclass of `int` and would otherwise be silently converted.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    return value


EpochMillis = Annotated[datetime, BeforeValidator(_from_epoch_millis)]
