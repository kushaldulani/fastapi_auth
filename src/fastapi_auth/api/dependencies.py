"""
API dependencies for authentication.

This module provides FastAPI dependencies for protecting routes.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.constant import SessionStatus
from ..core.database import get_db
from ..core.security import hash_jti, verify_access_token
from ..models.user import User
from ..models.user_session import UserSession
from ..services.auth import get_user_by_id

# HTTP Bearer token authentication scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current user from access token.

    This is a FastAPI dependency that:
    1. Extracts Bearer token from Authorization header
    2. Verifies the token signature and expiration
    3. Checks if session is still active (not revoked)
    4. Gets user from database
    5. Returns User object

    Security checks:
    - Token signature valid
    - Token not expired
    - Session status is 'active' (not 'revoked')
    - User exists and is active

    Usage:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}

    Args:
        credentials: HTTPBearer automatically extracts token from header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException 401: If token invalid, session revoked, or user not found
    """
    token = credentials.credentials

    # Step 1: Verify token signature and expiration
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 2: Extract user_id and jti from token
    user_id = payload.get("user_id")
    jti = payload.get("jti")

    if not user_id or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 3: Check if access token's session is active (STATEFUL JWT)
    # Hash the access token's JTI to look up in database
    access_token_jti_hash = hash_jti(jti)

    # Check if this access token JTI belongs to an active session
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.access_token_jti_hash == access_token_jti_hash,
            UserSession.status == SessionStatus.ACTIVE.value
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        # Session not found or revoked (logout/security breach)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token session is invalid or has been revoked. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 4: Get user from database
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 5: Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
