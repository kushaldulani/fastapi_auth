"""
Constants and enums for FastAPI authentication system.

This module contains all constant values, enums, and configuration
values used throughout the application.
"""

from enum import Enum


# ============================================================================
# Session Status Enum
# ============================================================================

class SessionStatus(str, Enum):
    """User session status values."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


# ============================================================================
# Token Blacklist Reasons Enum
# ============================================================================

class BlacklistReason(str, Enum):
    """Reasons for adding token to blacklist."""

    ROTATED = "rotated"  # Token was rotated during refresh
    SECURITY_BREACH_REUSE = "security_breach_reuse"  # Token reuse detected
    LOGOUT = "logout"  # User logged out
    ADMIN_REVOKE = "admin_revoke"  # Admin revoked token
    EXPIRED = "expired"  # Token expired naturally


# ============================================================================
# Database Column Names (for consistency)
# ============================================================================

class TokenBlacklistColumns:
    """Column names for token_blacklist table."""

    JTI_HASH = "jti_hash"
    REFRESH_JTI_HASH = "refresh_jti_hash"  # Alias for clarity
    USER_ID = "user_id"
    BLACKLISTED_AT = "blacklisted_at"
    EXPIRES_AT = "expires_at"
    REASON = "reason"


class UserSessionColumns:
    """Column names for user_sessions table."""

    ID = "id"
    USER_ID = "user_id"
    ACCESS_TOKEN_JTI_HASH = "access_token_jti_hash"
    REFRESH_TOKEN_JTI_HASH = "refresh_token_jti_hash"
    PREVIOUS_REFRESH_TOKEN_JTI_HASH = "previous_refresh_token_jti_hash"
    STATUS = "status"
    DEVICE_INFO = "device_info"
    CREATED_AT = "created_at"
    LAST_USED_AT = "last_used_at"


# ============================================================================
# JWT Token Types
# ============================================================================

class TokenType(str, Enum):
    """JWT token types."""

    ACCESS = "access"
    REFRESH = "refresh"
