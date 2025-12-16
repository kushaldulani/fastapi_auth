"""
Pydantic schemas for authentication.

Schemas define the shape of data coming IN (requests) and going OUT (responses).
They provide automatic validation and documentation.
"""

from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Request Schemas (Data coming IN from client)
# ============================================================================

class UserRegister(BaseModel):
    """
    Data needed to register a new user.

    Example:
        {
            "email": "user@example.com",
            "password": "SecurePass123!"
        }
    """

    email: EmailStr  # Validates email format automatically
    password: str = Field(
        min_length=8,
        max_length=100,
        description="Password must be 8-100 characters",
    )


class UserLogin(BaseModel):
    """
    Data needed to log in.

    Example:
        {
            "email": "user@example.com",
            "password": "SecurePass123!"
        }
    """

    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """
    Data needed to refresh access token.

    Example:
        {
            "refresh_token": "eyJhbGc..."
        }
    """

    refresh_token: str


# ============================================================================
# Response Schemas (Data going OUT to client)
# ============================================================================

class TokenResponse(BaseModel):
    """
    JWT tokens returned after login or registration.

    Example:
        {
            "access_token": "eyJhbGc...",
            "refresh_token": "eyJhbGc...",
            "token_type": "bearer"
        }
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """
    Public user data (never include password hash!).

    Example:
        {
            "id": 123,
            "email": "user@example.com",
            "is_active": true,
            "is_admin": false,
            "email_verified": false
        }
    """

    id: int
    email: str
    is_active: bool
    is_admin: bool
    email_verified: bool

    class Config:
        # Allow creating from ORM models (User instance → UserResponse)
        from_attributes = True
