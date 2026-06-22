"""Custom exceptions for AIWriteX CLI."""


class AIWriteXError(Exception):
    """Base exception for AIWriteX CLI."""

    pass


class AuthError(AIWriteXError):
    """Authentication failed."""

    pass


class NotFoundError(AIWriteXError):
    """Resource not found."""

    pass


class ServerError(AIWriteXError):
    """Server error (5xx)."""

    pass


class ConnectionError(AIWriteXError):
    """Network connection error."""

    pass


class ValidationError(AIWriteXError):
    """Request validation error."""

    pass
