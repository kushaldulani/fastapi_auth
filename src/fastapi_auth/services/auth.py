"""
Authentication service.

Business logic for user registration, login, and token management.
This is the layer between API endpoints and the database.
"""

from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import (
    AuthenticationError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from ..core.security import (
    create_access_token,
    create_refresh_token,
    hash_jti,
    hash_password,
    verify_password,
)
from ..models.user import User
from ..models.user_session import UserSession
from ..schemas.auth import TokenResponse, UserLogin, UserRegister


# ============================================================================
# Registration
# ============================================================================

async def register_user(
    db: AsyncSession,
    user_data: UserRegister,
) -> tuple[User, TokenResponse]:
    """
    Register a new user.

    Steps:
    1. Check if email already exists
    2. Hash the password
    3. Create user in database
    4. Generate JWT tokens
    5. Return user and tokens

    Args:
        db: Database session
        user_data: Registration data (email, password)

    Returns:
        Tuple of (User, TokenResponse)

    Raises:
        UserAlreadyExistsError: If email already registered

    Example:
        user, tokens = await register_user(db, UserRegister(
            email="test@example.com",
            password="SecurePass123!"
        ))
    """

    # Step 1: Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise UserAlreadyExistsError(f"User with email {user_data.email} already exists")

    # Step 2: Hash password
    hashed_password = hash_password(user_data.password)

    # Step 3: Create user
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True,
        is_admin=False,  # Regular user (not admin)
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)  # Get the ID and timestamps

    # Step 4: Generate tokens
    token_data = {"user_id": new_user.id, "email": new_user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Step 5: Create session for this device/login
    # Decode both tokens to get their JTIs
    access_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
    refresh_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])

    access_jti = access_payload["jti"]
    refresh_jti = refresh_payload["jti"]

    session = UserSession(
        user_id=new_user.id,
        access_token_jti_hash=hash_jti(access_jti),
        refresh_token_jti_hash=hash_jti(refresh_jti),
        previous_refresh_token_jti_hash=None,  # First login, no previous
        device_info=None,  # TODO: Extract from User-Agent header
    )
    db.add(session)
    await db.commit()

    tokens = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )

    return new_user, tokens


# ============================================================================
# Login
# ============================================================================

async def login_user(
    db: AsyncSession,
    credentials: UserLogin,
) -> tuple[User, TokenResponse]:
    """
    Log in an existing user.

    Steps:
    1. Find user by email
    2. Verify password
    3. Check if user is active
    4. Generate JWT tokens
    5. Return user and tokens

    Args:
        db: Database session
        credentials: Login credentials (email, password)

    Returns:
        Tuple of (User, TokenResponse)

    Raises:
        UserNotFoundError: If email doesn't exist
        AuthenticationError: If password is wrong or user is inactive

    Example:
        user, tokens = await login_user(db, UserLogin(
            email="test@example.com",
            password="SecurePass123!"
        ))
    """

    # Step 1: Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundError(f"No user found with email {credentials.email}")

    # Step 2: Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise AuthenticationError("Invalid password")

    # Step 3: Check if user is active
    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    # Step 4: Generate tokens
    token_data = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Step 5: Create session for this device/login
    # Decode both tokens to get their JTIs
    access_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
    refresh_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])

    access_jti = access_payload["jti"]
    refresh_jti = refresh_payload["jti"]

    session = UserSession(
        user_id=user.id,
        access_token_jti_hash=hash_jti(access_jti),
        refresh_token_jti_hash=hash_jti(refresh_jti),
        previous_refresh_token_jti_hash=None,  # New login, no previous
        device_info=None,  # TODO: Extract from User-Agent header
    )
    db.add(session)
    await db.commit()

    tokens = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )

    return user, tokens


# ============================================================================
# Token Refresh
# ============================================================================

async def refresh_access_token(
    db: AsyncSession,
    user_id: int,
) -> str:
    """
    Create a new access token for a user.

    This is called when the access token expires but the refresh token is still valid.

    Args:
        db: Database session
        user_id: User ID from the refresh token

    Returns:
        New access token

    Raises:
        UserNotFoundError: If user doesn't exist
        AuthenticationError: If user is inactive

    Example:
        new_access_token = await refresh_access_token(db, user_id=123)
    """

    # Find user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found")

    # Check if user is still active
    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    # Generate new access token
    token_data = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(token_data)

    return access_token


# ============================================================================
# User Lookup
# ============================================================================

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """
    Get a user by their ID.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        User instance or None if not found

    Example:
        user = await get_user_by_id(db, user_id=123)
        if user:
            print(f"Found: {user.email}")
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    Get a user by their email.

    Args:
        db: Database session
        email: User email

    Returns:
        User instance or None if not found

    Example:
        user = await get_user_by_email(db, "test@example.com")
        if user:
            print(f"Found user ID: {user.id}")
    """
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()
