"""
Test authentication service.

This tests the business logic for:
1. User registration
2. User login
3. Token refresh
4. Error handling (duplicate users, wrong passwords, etc)
"""

import asyncio

import pytest
from sqlalchemy import select

from fastapi_auth.core.database import AsyncSessionLocal, engine
from fastapi_auth.models.base import Base
from fastapi_auth.models.user import User
from fastapi_auth.schemas.auth import UserLogin, UserRegister
from fastapi_auth.services.auth import (
    AuthenticationError,
    UserAlreadyExistsError,
    UserNotFoundError,
    get_user_by_email,
    get_user_by_id,
    login_user,
    refresh_access_token,
    register_user,
)


# ============================================================================
# Setup & Teardown
# ============================================================================

async def setup_database():
    """Create all tables before tests."""
    async with engine.begin() as conn:
        # Drop all tables first (clean slate)
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def cleanup_database():
    """Clean up after tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ============================================================================
# Test 1: User Registration
# ============================================================================

async def test_register_user():
    """Test successful user registration."""
    print("\n" + "=" * 60)
    print("TEST 1: User Registration")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # Register a new user
        user_data = UserRegister(
            email="test@example.com",
            password="SecurePass123!"
        )

        user, tokens = await register_user(db, user_data)

        # Verify user was created
        print(f"\n✓ User created:")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Active: {user.is_active}")
        print(f"  Email verified: {user.email_verified}")

        assert user.id is not None, "User should have an ID"
        assert user.email == "test@example.com", "Email should match"
        assert user.is_active is True, "User should be active"
        assert user.email_verified is False, "Email not verified yet"

        # Verify password is hashed (not plain text)
        print(f"\n✓ Password hashed:")
        print(f"  Hash: {user.hashed_password[:30]}...")
        assert user.hashed_password != "SecurePass123!", "Password should be hashed"
        assert len(user.hashed_password) == 60, "Bcrypt hash should be 60 chars"

        # Verify tokens were generated
        print(f"\n✓ Tokens generated:")
        print(f"  Access token: {tokens.access_token[:30]}...")
        print(f"  Refresh token: {tokens.refresh_token[:30]}...")
        print(f"  Token type: {tokens.token_type}")

        assert tokens.access_token, "Access token should be generated"
        assert tokens.refresh_token, "Refresh token should be generated"
        assert tokens.token_type == "bearer", "Token type should be bearer"

    print("\n✅ User registration works correctly!")


# ============================================================================
# Test 2: Duplicate Email
# ============================================================================

async def test_duplicate_email():
    """Test registering with an existing email fails."""
    print("\n" + "=" * 60)
    print("TEST 2: Duplicate Email Prevention")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # First registration succeeds
        user_data = UserRegister(
            email="duplicate@example.com",
            password="Password123!"
        )
        user1, _ = await register_user(db, user_data)
        print(f"\n✓ First user created: {user1.email}")

        # Second registration with same email should fail
        try:
            await register_user(db, user_data)
            assert False, "Should have raised UserAlreadyExistsError"
        except UserAlreadyExistsError as e:
            print(f"✓ Duplicate email rejected: {e}")

    print("\n✅ Duplicate email prevention works!")


# ============================================================================
# Test 3: User Login
# ============================================================================

async def test_login_user():
    """Test successful user login."""
    print("\n" + "=" * 60)
    print("TEST 3: User Login")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # First, register a user
        register_data = UserRegister(
            email="login@example.com",
            password="MyPassword123!"
        )
        registered_user, _ = await register_user(db, register_data)
        print(f"\n✓ User registered: {registered_user.email}")

        # Now try to log in
        login_data = UserLogin(
            email="login@example.com",
            password="MyPassword123!"
        )
        user, tokens = await login_user(db, login_data)

        print(f"\n✓ Login successful:")
        print(f"  User ID: {user.id}")
        print(f"  Email: {user.email}")

        assert user.id == registered_user.id, "Should be the same user"
        assert tokens.access_token, "Should get access token"
        assert tokens.refresh_token, "Should get refresh token"

    print("\n✅ User login works correctly!")


# ============================================================================
# Test 4: Wrong Password
# ============================================================================

async def test_wrong_password():
    """Test login with wrong password fails."""
    print("\n" + "=" * 60)
    print("TEST 4: Wrong Password Rejection")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # Register a user
        register_data = UserRegister(
            email="wrongpass@example.com",
            password="CorrectPassword123!"
        )
        await register_user(db, register_data)
        print(f"\n✓ User registered")

        # Try to login with wrong password
        login_data = UserLogin(
            email="wrongpass@example.com",
            password="WrongPassword123!"
        )

        try:
            await login_user(db, login_data)
            assert False, "Should have raised AuthenticationError"
        except AuthenticationError as e:
            print(f"✓ Wrong password rejected: {e}")

    print("\n✅ Wrong password rejection works!")


# ============================================================================
# Test 5: User Not Found
# ============================================================================

async def test_user_not_found():
    """Test login with non-existent email fails."""
    print("\n" + "=" * 60)
    print("TEST 5: Non-Existent User Rejection")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        login_data = UserLogin(
            email="doesnotexist@example.com",
            password="SomePassword123!"
        )

        try:
            await login_user(db, login_data)
            assert False, "Should have raised UserNotFoundError"
        except UserNotFoundError as e:
            print(f"✓ Non-existent user rejected: {e}")

    print("\n✅ User not found handling works!")


# ============================================================================
# Test 6: Token Refresh
# ============================================================================

async def test_refresh_token():
    """Test refreshing access token."""
    print("\n" + "=" * 60)
    print("TEST 6: Token Refresh")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # Register a user
        register_data = UserRegister(
            email="refresh@example.com",
            password="Password123!"
        )
        user, tokens = await register_user(db, register_data)
        print(f"\n✓ User registered with ID: {user.id}")
        print(f"  Original access token: {tokens.access_token[:30]}...")

        # Refresh the access token
        new_access_token = await refresh_access_token(db, user.id)
        print(f"\n✓ New access token: {new_access_token[:30]}...")

        assert new_access_token, "Should generate new access token"
        assert new_access_token != tokens.access_token, "Should be a different token"

    print("\n✅ Token refresh works!")


# ============================================================================
# Test 7: Get User by ID
# ============================================================================

async def test_get_user_by_id():
    """Test looking up user by ID."""
    print("\n" + "=" * 60)
    print("TEST 7: Get User by ID")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # Register a user
        register_data = UserRegister(
            email="lookup@example.com",
            password="Password123!"
        )
        registered_user, _ = await register_user(db, register_data)
        print(f"\n✓ User registered with ID: {registered_user.id}")

        # Look up by ID
        found_user = await get_user_by_id(db, registered_user.id)
        print(f"✓ Found user: {found_user.email}")

        assert found_user is not None, "Should find user"
        assert found_user.id == registered_user.id, "IDs should match"
        assert found_user.email == "lookup@example.com", "Email should match"

        # Try non-existent ID
        not_found = await get_user_by_id(db, 99999)
        print(f"✓ Non-existent ID returns: {not_found}")
        assert not_found is None, "Should return None for non-existent ID"

    print("\n✅ Get user by ID works!")


# ============================================================================
# Test 8: Get User by Email
# ============================================================================

async def test_get_user_by_email():
    """Test looking up user by email."""
    print("\n" + "=" * 60)
    print("TEST 8: Get User by Email")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # Register a user
        register_data = UserRegister(
            email="findme@example.com",
            password="Password123!"
        )
        registered_user, _ = await register_user(db, register_data)
        print(f"\n✓ User registered: {registered_user.email}")

        # Look up by email
        found_user = await get_user_by_email(db, "findme@example.com")
        print(f"✓ Found user with ID: {found_user.id}")

        assert found_user is not None, "Should find user"
        assert found_user.email == "findme@example.com", "Email should match"

        # Try non-existent email
        not_found = await get_user_by_email(db, "notfound@example.com")
        print(f"✓ Non-existent email returns: {not_found}")
        assert not_found is None, "Should return None for non-existent email"

    print("\n✅ Get user by email works!")


# ============================================================================
# Main Test Runner
# ============================================================================

async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TESTING AUTHENTICATION SERVICE")
    print("=" * 60)

    try:
        # Setup
        print("\n🔧 Setting up test database...")
        await setup_database()
        print("✅ Database ready")

        # Run tests
        await test_register_user()
        await test_duplicate_email()
        await test_login_user()
        await test_wrong_password()
        await test_user_not_found()
        await test_refresh_token()
        await test_get_user_by_id()
        await test_get_user_by_email()

        # Summary
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nKey Learnings:")
        print("1. Registration creates user + generates tokens")
        print("2. Duplicate emails are rejected")
        print("3. Login verifies password and generates tokens")
        print("4. Wrong passwords are rejected")
        print("5. Non-existent users are handled gracefully")
        print("6. Token refresh creates new access tokens")
        print("7. User lookup by ID and email works")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print("\n🔧 Cleaning up test database...")
        await cleanup_database()
        await engine.dispose()
        print("✅ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
