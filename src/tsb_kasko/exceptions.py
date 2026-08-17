"""Exception hierarchy raised by the TSB kasko client.

Every error originating from this package derives from :class:`TsbKaskoError`,
so callers can catch a single base class when they do not need to tell transport
failures apart from protocol or validation failures.
"""

from __future__ import annotations


class TsbKaskoError(Exception):
    """Base class for every error raised by this package."""


class TsbRequestError(TsbKaskoError):
    """Raised when a TSB endpoint is unreachable or answers with a failing status.

    Attributes:
        status_code: HTTP status code returned by the server, when available.
        url: The absolute URL that produced the failure.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        url: str | None = None,
    ) -> None:
        """Initialise the error.

        Args:
            message: Human readable description of the failure.
            status_code: HTTP status code returned by the server, when available.
            url: The absolute URL that produced the failure.
        """
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class TsbServiceError(TsbKaskoError):
    """Raised when TSB answers successfully but reports an error in the envelope.

    The service returns HTTP 200 with ``HasError`` set to true for domain level
    problems, so this is distinct from :class:`TsbRequestError`.
    """


class TsbParseError(TsbKaskoError):
    """Raised when a TSB response cannot be decoded into the expected structure."""


class TsbNotFoundError(TsbKaskoError):
    """Raised when a lookup completes successfully but matches no record."""
