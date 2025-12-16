"""
Models package.

DO NOT import model classes here to avoid circular imports!

Usage:
    from fastapi_auth.models.base import Base, TimestampMixin
    from fastapi_auth.models.user import User
"""

# Only export the names, don't import the classes
# This prevents automatic imports when someone imports from this package
__all__ = ["Base", "TimestampMixin", "User"]
