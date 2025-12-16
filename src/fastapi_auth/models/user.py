"""
User model - represents a user in our system.

This is the SIMPLEST possible user model:
- id: Primary key
- email: Login identifier (unique)
- hashed_password: Password (never store plain text!)
- is_active: Can user login?
- created_at, updated_at: From TimestampMixin
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin  # Use relative import


class User(Base, TimestampMixin):
    """
    User model.

    Becomes table "users" in database with columns:
    - id (primary key, auto-increment)
    - email (unique, indexed)
    - hashed_password
    - is_active
    - created_at (auto-set)
    - updated_at (auto-updated)
    """

    # Table name in database
    __tablename__ = "users"

    # Primary key (auto-increment integer)
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Email (unique, used for login)
    # index=True makes lookups fast (SELECT * FROM users WHERE email = ...)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    # Hashed password (NEVER store plain password!)
    # We'll use bcrypt to hash this
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Is user active? (can they login?)
    # Default True = new users can login immediately
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Is user an admin? (elevated privileges)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Has user verified their email?
    # Default False = users need to verify email after registration
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


    def __repr__(self) -> str:
        """String representation (helpful for debugging)."""
        return f"<User(id={self.id}, email={self.email})>"
