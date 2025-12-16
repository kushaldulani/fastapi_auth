"""
Token blacklist model.

Stores revoked/used refresh tokens to prevent reuse.
JTI is stored as SHA-256 hash for security (database breach protection).
When we scale, we can migrate this to Redis for better performance.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TokenBlacklist(Base):
    """
    Blacklisted refresh tokens.

    When a refresh token is used, we add its JTI hash here.
    This prevents the old token from being reused (token rotation).

    SECURITY: We store SHA-256 hash of JTI, not plain JTI.
    This way, even if database is compromised, tokens can't be reconstructed.

    Future: Migrate to Redis for better performance at scale.
    """

    __tablename__ = "token_blacklist"

    # Use JTI hash as primary key (64 hex chars from SHA-256)
    jti_hash: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)

    # User who owned this token (for security auditing)
    user_id: Mapped[int] = mapped_column(index=True)

    # When was this token blacklisted
    blacklisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # When does this token expire (for cleanup)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Reason for blacklisting (optional, for debugging)
    reason: Mapped[str] = mapped_column(
        String(50),
        default="rotated",
        nullable=False,
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<TokenBlacklist(jti_hash={self.jti_hash[:8]}..., user_id={self.user_id})>"
