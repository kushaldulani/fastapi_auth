"""
Configuration management using Pydantic Settings.

This is the SIMPLEST possible configuration:
- Reads from .env file automatically
- Validates settings (type checking)
- Provides one global 'settings' object

Usage in other files:
    from fastapi_auth.core.config import settings
    print(settings.DATABASE_URL)
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic automatically:
    1. Reads from .env file
    2. Converts types (str to int, str to bool, etc.)
    3. Validates required fields
    """

    # Database
    DATABASE_URL: str  # Required - will error if not set

    # Security
    SECRET_KEY: str  # Required - used to sign JWT tokens

    # JWT Token Expiry
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived (15 minutes)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30    # Long-lived (30 days)

    # Application
    DEBUG: bool = False  # Default to False for safety

    class Config:
        """
        Pydantic config - tells it where to find .env file.
        """
        env_file = ".env"  # Look for .env in project root
        case_sensitive = True  # DATABASE_URL != database_url


# Create a single global instance
# Import this in other files: from fastapi_auth.core.config import settings
settings = Settings()
