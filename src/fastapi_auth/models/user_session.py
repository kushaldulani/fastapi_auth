"""
User session model - tracks active tokens across multiple devices.

This enables:
- Multi-device support (track which devices are logged in)
- Token revocation per device or all devices
- Security breach response (revoke all sessions)
- Session management UI (show user their active sessions)
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.constant import SessionStatus
from .base import Base


class UserSession(Base):
    """
    Tracks active user sessions/tokens across devices.

    STATEFUL JWT APPROACH - Full control over token lifecycle:
    - Stores BOTH access and refresh token JTIs (hashed)
    - Enables immediate revocation on logout
    - Tracks token reuse for security breach detection

    Each row = one active session with both access and refresh tokens.

    When access token expires:
    - Client uses refresh token to get new access token
    - We update access_token_jti_hash with new value

    When refresh token is used (token rotation):
    1. Move refresh_token_jti_hash to previous_refresh_token_jti_hash
    2. Update refresh_token_jti_hash with new token
    3. Update access_token_jti_hash with new access token
    4. This allows us to detect if old refresh token is reused (theft)

    When user logs out or breach detected:
    - Set status='revoked'
    - Both access AND refresh tokens become immediately invalid
    - Keep session for audit trail (not deleted)

    Table: user_sessions
    Columns:
    - id: Auto-increment primary key
    - user_id: Which user owns this session
    - access_token_jti_hash: SHA-256 hash of CURRENT access token's JTI
    - refresh_token_jti_hash: SHA-256 hash of CURRENT refresh token's JTI
    - previous_refresh_token_jti_hash: SHA-256 hash of PREVIOUS refresh token's JTI (theft detection)
    - status: active/revoked/expired
    - device_info: Optional device/browser info
    - created_at: When session started
    - last_used_at: When session was last active
    """

    __tablename__ = "user_sessions"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Which user owns this session
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)

    # SHA-256 hash of current ACCESS token's JTI (64 hex chars)
    # Checked on every API request for immediate revocation capability
    access_token_jti_hash: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )

    # SHA-256 hash of current REFRESH token's JTI (64 hex chars)
    # We hash it so even if DB is compromised, tokens can't be stolen
    refresh_token_jti_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    # SHA-256 hash of PREVIOUS refresh token's JTI
    # Used to detect token reuse (theft detection)
    previous_refresh_token_jti_hash: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )

    # Session status: active, revoked, expired
    status: Mapped[str] = mapped_column(
        String(20), default=SessionStatus.ACTIVE.value, index=True, nullable=False
    )

    # Optional: Device/browser info for user to identify their sessions
    # Example: "Chrome on Windows", "Safari on iPhone", etc.
    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # When this session started (first login)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # When refresh token was last used/rotated
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<UserSession(id={self.id}, user_id={self.user_id}, device={self.device_info})>"
