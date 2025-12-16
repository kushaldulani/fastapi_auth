"""
Base model and mixins for all database models.

This keeps our code DRY (Don't Repeat Yourself).
Instead of adding created_at/updated_at to every model,
we create a mixin that all models can inherit.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ============================================================================
# Base class for all models
# ============================================================================
class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    All models inherit from this.
    """
    pass


# ============================================================================
# Timestamp Mixin (created_at, updated_at)
# ============================================================================
class TimestampMixin:
    """
    Adds created_at and updated_at to any model.

    Usage:
        class User(Base, TimestampMixin):
            # Your fields here
            pass

        # Now User automatically has:
        # - created_at (set when row is created)
        # - updated_at (updated on every change)
    """

    # created_at: automatically set when row is inserted
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # Database sets this automatically
        nullable=False,
    )

    # updated_at: automatically updated when row is modified
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # Set on creation
        onupdate=func.now(),  # Update on every change
        nullable=False,
    )
