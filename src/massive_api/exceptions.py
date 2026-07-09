"""
Exception hierarchy for massive_api operational errors.

These are distinct from input-validation errors (which raise the built-in ValueError)
and from pydantic.ValidationError raised by validated list methods. Catch MassiveApiError
to handle any operational failure the client raises at request time.

HTTP error responses are wrapped in a MassiveApiHTTPError subclass so callers never have to
reach for the underlying transport library (aiohttp) to branch on failures. The originating
aiohttp.ClientResponseError is always preserved on `__cause__`.
"""

import aiohttp

HTTP_TOO_MANY_REQUESTS = 429
HTTP_NOT_FOUND = 404
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_SERVER_ERROR_MIN = 500


class MassiveApiError(Exception):
    """Base class for all massive_api runtime errors."""


class MassiveApiHTTPError(MassiveApiError):
    """
    Raised for an HTTP error response from the Massive API.

    Carries the HTTP `status` and server `message`. The originating
    aiohttp.ClientResponseError is preserved on `__cause__`. Subclasses distinguish the
    common failure categories (authentication, not-found, server error); any other status
    surfaces as a plain MassiveApiHTTPError.
    """

    def __init__(self, status: int, message: str = "") -> None:
        """Record the HTTP status and server-supplied message."""
        self.status = status
        self.message = message
        detail = f": {message}" if message else ""
        super().__init__(f"Massive API request failed with status {status}{detail}")


class AuthenticationError(MassiveApiHTTPError):
    """Raised on HTTP 401/403 responses (missing/invalid key or insufficient entitlement)."""


class NotFoundError(MassiveApiHTTPError):
    """Raised on HTTP 404 responses (the requested resource does not exist)."""


class ServerError(MassiveApiHTTPError):
    """Raised on HTTP 5xx responses (a fault on the Massive API side)."""


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


def http_error_from_response(error: aiohttp.ClientResponseError) -> MassiveApiHTTPError:
    """Map an aiohttp.ClientResponseError to the most specific MassiveApiHTTPError subclass."""
    status = error.status
    message = error.message or ""
    if status in (HTTP_UNAUTHORIZED, HTTP_FORBIDDEN):
        return AuthenticationError(status, message)
    if status == HTTP_NOT_FOUND:
        return NotFoundError(status, message)
    if status >= HTTP_SERVER_ERROR_MIN:
        return ServerError(status, message)
    return MassiveApiHTTPError(status, message)
