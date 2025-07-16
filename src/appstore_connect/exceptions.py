"""
Exception classes for appstore-connect-client.
"""


class AppStoreConnectError(Exception):
    """Base exception class for App Store Connect API errors."""

    pass


class AuthenticationError(AppStoreConnectError):
    """Raised when authentication fails."""

    pass


class RateLimitError(AppStoreConnectError):
    """Raised when rate limits are exceeded."""

    pass


class ValidationError(AppStoreConnectError):
    """Raised when request validation fails."""

    pass


class NotFoundError(AppStoreConnectError):
    """Raised when requested resource is not found."""

    pass


class PermissionError(AppStoreConnectError):
    """Raised when insufficient permissions for operation."""

    pass


class ServerError(AppStoreConnectError):
    """Raised when server returns 5xx error."""

    pass
