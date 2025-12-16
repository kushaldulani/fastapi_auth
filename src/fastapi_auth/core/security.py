"""
Security utilities for authentication.

This module provides:
1. Password hashing (bcrypt)
2. JWT token creation (access & refresh)
3. JWT token validation
4. JTI hashing for secure token storage

SIMPLE & PRODUCTION-READY!
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings


# ============================================================================
# Password Hashing (Bcrypt)
# ============================================================================

# Create password context with bcrypt
# cost factor=12 (default) - good balance of security & speed
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain password using bcrypt.

    Args:
        password: Plain text password (e.g., "mypassword123")

    Returns:
        Hashed password (e.g., "$2b$12$KIXqX5g...")

    Example:
        hashed = hash_password("test123")
        # → "$2b$12$KIXqX5g..." (60 characters)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Password to check (e.g., "test123")
        hashed_password: Hash to check against (e.g., "$2b$12$...")

    Returns:
        True if password matches, False otherwise

    Example:
        hashed = hash_password("test123")
        verify_password("test123", hashed)  # → True
        verify_password("wrong", hashed)     # → False
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT Token Creation
# ============================================================================

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Access tokens are SHORT-LIVED (default: 15 minutes).
    Used for API requests.

    Args:
        data: Payload to encode (e.g., {"user_id": 1, "email": "user@example.com"})
        expires_delta: Custom expiration time (optional)

    Returns:
        JWT token string

    Example:
        token = create_access_token({"user_id": 1})
        # → "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add standard JWT claims
    to_encode.update({
        "exp": expire,  # Expiration time
        "iat": datetime.now(timezone.utc),  # Issued at
        "type": "access",  # Token type
        "jti": str(uuid.uuid4()),  # JWT ID (unique identifier for this token)
    })

    # Create and sign the token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT refresh token.

    Refresh tokens are LONG-LIVED (default: 30 days).
    Used to get new access tokens without re-login.

    Args:
        data: Payload to encode (e.g., {"user_id": 1})
        expires_delta: Custom expiration time (optional)

    Returns:
        JWT token string

    Example:
        token = create_refresh_token({"user_id": 1})
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",  # Token type (important!)
        "jti": str(uuid.uuid4()),  # JWT ID (unique identifier for this token)
    })

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


# ============================================================================
# JWT Token Validation
# ============================================================================

def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.

    Checks:
    - Token is properly formatted
    - Signature is valid
    - Token hasn't expired

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid, None if invalid

    Example:
        payload = decode_token(token)
        if payload:
            user_id = payload["user_id"]
        else:
            # Invalid token
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        # Token is invalid, expired, or tampered with
        return None


def verify_access_token(token: str) -> dict[str, Any] | None:
    """
    Verify an access token specifically.

    Checks:
    - Token is valid (signature, expiration)
    - Token type is "access"

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid access token, None otherwise

    Example:
        payload = verify_access_token(token)
        if payload:
            user_id = payload["user_id"]
        else:
            raise HTTPException(401, "Invalid token")
    """
    payload = decode_token(token)

    # Check token type
    if payload and payload.get("type") == "access":
        return payload

    return None


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    """
    Verify a refresh token specifically.

    Checks:
    - Token is valid
    - Token type is "refresh"

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid refresh token, None otherwise
    """
    payload = decode_token(token)

    # Check token type
    if payload and payload.get("type") == "refresh":
        return payload

    return None


# ============================================================================
# Token Utilities
# ============================================================================

def hash_jti(jti: str) -> str:
    """
    Hash a JTI (JWT ID) for secure storage.

    We hash JTI before storing in database so even if database is compromised,
    the actual tokens cannot be reconstructed.

    Uses SHA-256 (fast, secure, deterministic).

    Args:
        jti: JWT ID (UUID string like "a1b2c3d4-...")

    Returns:
        64-character hex string (SHA-256 hash)

    Example:
        jti = "a1b2c3d4-e5f6-4789-0abc-def123456789"
        hash_jti(jti)  # → "5d41402abc4b2a76b9719d911017c592..."
    """
    return hashlib.sha256(jti.encode()).hexdigest()


def get_token_expiration(token: str) -> datetime | None:
    """
    Get expiration time from token without validating.

    Useful for displaying "token expires in X minutes" to user.

    Args:
        token: JWT token string

    Returns:
        Expiration datetime if token is decodable, None otherwise
    """
    try:
        # Decode WITHOUT verification (just to read expiration)
        # Note: python-jose still requires the key parameter, but we disable verification
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_signature": False, "verify_exp": False}
        )
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp)
    except JWTError:
        pass

    return None
