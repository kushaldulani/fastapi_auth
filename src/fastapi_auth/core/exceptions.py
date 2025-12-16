"""
Custom exceptions for FastAPI authentication system.

This module contains all custom exception classes used throughout
the application for better error handling and separation of concerns.
"""


# ============================================================================
# Authentication Exceptions
# ============================================================================

class AuthenticationError(Exception):
    """Raised when authentication fails (wrong password, invalid credentials, etc)."""

    pass


class UserAlreadyExistsError(Exception):
    """Raised when trying to register with an existing email."""

    pass


class UserNotFoundError(Exception):
    """Raised when user doesn't exist in the database."""

    pass


# ============================================================================
# Token/Session Exceptions
# ============================================================================

class TokenExpiredError(Exception):
    """Raised when JWT token has expired."""

    pass


class TokenInvalidError(Exception):
    """Raised when JWT token is malformed or has invalid signature."""

    pass


class SessionRevokedError(Exception):
    """Raised when user session has been revoked (logout, security breach, etc)."""

    pass


class TokenReuseDetectedError(Exception):
    """Raised when token reuse is detected (security breach)."""

    pass


# ============================================================================
# Authorization Exceptions
# ============================================================================

class PermissionDeniedError(Exception):
    """Raised when user doesn't have permission to access a resource."""

    pass


class InactiveUserError(Exception):
    """Raised when user account is inactive/disabled."""

    pass
