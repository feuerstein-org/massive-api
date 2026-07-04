"""
Exception hierarchy for massive_api operational errors.

These are distinct from input-validation errors (which raise the built-in ValueError)
and from pydantic.ValidationError raised by validated list methods. Catch MassiveApiError
to handle any operational failure the client raises at request time.
"""

HTTP_TOO_MANY_REQUESTS = 429


class MassiveApiError(Exception):
    """Base class for all massive_api runtime errors."""


class MaxRetriesExceededError(MassiveApiError):
    """
    Raised when a request keeps returning 429 (Too Many Requests) past `max_retries`.

    The originating aiohttp.ClientResponseError is preserved on `__cause__`.
    """

    def __init__(self, retries: int, status: int = HTTP_TOO_MANY_REQUESTS) -> None:
        """Record the retry count and HTTP status that led to the failure."""
        self.retries = retries
        self.status = status
        super().__init__(f"Maximum retries ({retries}) exceeded after repeated {status} responses")
