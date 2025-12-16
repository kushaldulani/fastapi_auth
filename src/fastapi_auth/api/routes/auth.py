"""
Authentication API endpoints.

Routes:
- POST /auth/register - Register new user
- POST /auth/login - Login and get tokens
- POST /auth/refresh - Refresh access token
- GET /auth/me - Get current user info
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.database import get_db
from ...core.security import create_access_token, create_refresh_token, hash_jti, verify_refresh_token
from ...models.token_blacklist import TokenBlacklist
from ...models.user_session import UserSession
from ...schemas.auth import RefreshTokenRequest, TokenResponse, UserLogin, UserRegister, UserResponse
from ...services.auth import (
    AuthenticationError,
    UserAlreadyExistsError,
    UserNotFoundError,
    get_user_by_id,
    login_user,
    register_user,
)
from ..dependencies import get_current_user
from ...models.user import User

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# POST /auth/register - Register New User
# ============================================================================

@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password. Returns user data and JWT tokens.",
)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.

    - **email**: Valid email address (will be validated)
    - **password**: Password (8-100 characters)

    Returns:
    - User information (id, email, is_active, etc.)
    - Access token (15 min expiry)
    - Refresh token (30 day expiry)
    """
    try:
        user, tokens = await register_user(db, user_data)

        return {
            "user": UserResponse.model_validate(user),
            "tokens": tokens,
        }

    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# POST /auth/login - Login User
# ============================================================================

@router.post(
    "/login",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate with email and password. Returns user data and JWT tokens.",
)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email and password.

    - **email**: Your email address
    - **password**: Your password

    Returns:
    - User information
    - Access token (15 min expiry)
    - Refresh token (30 day expiry)
    """
    try:
        user, tokens = await login_user(db, credentials)

        return {
            "user": UserResponse.model_validate(user),
            "tokens": tokens,
        }

    except (UserNotFoundError, AuthenticationError):
        # Don't reveal whether email exists (security best practice)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# POST /auth/refresh - Refresh Access Token
# ============================================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh tokens (with rotation)",
    description="Get new access AND refresh tokens. Old refresh token becomes invalid (security best practice).",
)
async def refresh_token_endpoint(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh tokens with rotation + session-based security.

    Security features:
    1. Token rotation (new access AND refresh tokens on each refresh)
    2. Hashed JTI storage (database breach protection)
    3. Theft detection (checks if token matches current OR previous)
    4. Full revocation (revokes ALL user sessions on breach)
    5. Immediate access token invalidation (stateful JWT approach)

    Flow:
    - Client sends refresh token
    - We check if JTI matches current session's refresh_token_jti_hash (valid)
    - If JTI matches previous_refresh_token_jti_hash → THEFT! Revoke all sessions
    - If valid, generate new tokens and update BOTH access_token_jti_hash and refresh_token_jti_hash
    """
    # Verify the refresh token
    payload = verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_refresh_jti = payload.get("jti")
    user_id = payload.get("user_id")
    current_refresh_jti_hash = hash_jti(current_refresh_jti)

    # Find session by current refresh_token_jti_hash
    result = await db.execute(
        select(UserSession).where(
            UserSession.refresh_token_jti_hash == current_refresh_jti_hash,
            UserSession.status == "active"
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        # Token not in current sessions, check if it's a previous token (REUSE!)
        result = await db.execute(
            select(UserSession).where(
                UserSession.previous_refresh_token_jti_hash == current_refresh_jti_hash
            )
        )
        reused_session = result.scalar_one_or_none()

        if reused_session:
            # 🚨 TOKEN REUSE DETECTED! Someone used old/previous token
            # This means attacker has the token and already used it

            # SECURITY RESPONSE: Revoke ALL user's sessions (set status='revoked')
            await db.execute(
                update(UserSession)
                .where(UserSession.user_id == user_id)
                .values(status="revoked")
            )

            # Blacklist this token for audit
            blacklist_entry = TokenBlacklist(
                jti_hash=current_refresh_jti_hash,
                user_id=user_id,
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                reason="security_breach_reuse",
            )
            db.add(blacklist_entry)
            await db.commit()

            # TODO: Send security alert email
            # TODO: Log security event

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security breach detected. All tokens revoked. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Token not found at all (revoked or invalid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user
    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate new tokens (rotation)
    token_data = {"user_id": user.id, "email": user.email}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    # Decode both new tokens to get their JTIs
    new_access_payload = jwt.decode(new_access_token, settings.SECRET_KEY, algorithms=["HS256"])
    new_refresh_payload = jwt.decode(new_refresh_token, settings.SECRET_KEY, algorithms=["HS256"])

    new_access_jti_hash = hash_jti(new_access_payload["jti"])
    new_refresh_jti_hash = hash_jti(new_refresh_payload["jti"])

    # Update session: current becomes previous, new becomes current
    session.previous_refresh_token_jti_hash = session.refresh_token_jti_hash  # Store current as previous
    session.refresh_token_jti_hash = new_refresh_jti_hash  # Update to new refresh token
    session.access_token_jti_hash = new_access_jti_hash  # Update to new access token
    session.last_used_at = datetime.now(timezone.utc)

    # Blacklist old refresh token for audit
    blacklist_entry = TokenBlacklist(
        jti_hash=current_refresh_jti_hash,
        user_id=user_id,
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        reason="rotated",
    )
    db.add(blacklist_entry)
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


# ============================================================================
# GET /auth/me - Get Current User (Protected Route)
# ============================================================================

# TODO: This will be implemented in Step 8 with get_current_user dependency
# @router.get("/me", response_model=UserResponse)
# async def get_me(current_user: User = Depends(get_current_user)):
#     """Get current user information."""
#     return current_user


# ============================================================================
# GET /auth/hello - Protected Test Endpoint
# ============================================================================

@router.get(
    "/hello",
    response_model=dict,
    summary="Protected Hello Endpoint",
    description="Test endpoint to verify access token authentication works.",
)
async def hello(current_user: User = Depends(get_current_user)):
    """
    Protected endpoint that requires valid access token.

    This endpoint demonstrates:
    1. Bearer token authentication
    2. Automatic token validation
    3. User extraction from token

    How to use in Swagger:
    1. Register/Login to get access_token
    2. Click "Authorize" button (top right)
    3. Enter: Bearer <your_access_token>
    4. Try this endpoint!

    Returns:
        Greeting message with user info
    """
    return {
        "message": f"Hello, {current_user.email}!",
        "user_id": current_user.id,
        "is_active": current_user.is_active,
        "is_admin": current_user.is_admin,
    }
