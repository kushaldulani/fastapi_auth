"""
Test API endpoints using httpx AsyncClient.

This tests the HTTP layer, ensuring endpoints work correctly.
"""

import asyncio

from httpx import ASGITransport, AsyncClient

from fastapi_auth.core.database import engine
from fastapi_auth.main import app
from fastapi_auth.models.base import Base
from fastapi_auth.models import user, token_blacklist, user_session  # noqa: F401


# ============================================================================
# Setup & Teardown
# ============================================================================

async def setup_database():
    """Create all tables before tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def cleanup_database():
    """Clean up after tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ============================================================================
# Test 1: Health Check
# ============================================================================

async def test_health_check(client: AsyncClient):
    """Test root health check endpoint."""
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)

    response = await client.get("/")
    print(f"\n✓ GET / status: {response.status_code}")
    print(f"✓ Response: {response.json()}")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    print("\n✅ Health check works!")


# ============================================================================
# Test 2: POST /auth/register
# ============================================================================

async def test_register_user(client: AsyncClient):
    """Test user registration endpoint."""
    print("\n" + "=" * 60)
    print("TEST 2: POST /auth/register")
    print("=" * 60)

    response = await client.post(
        "/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "SecurePass123!",
        },
    )

    print(f"\n✓ Status: {response.status_code}")
    data = response.json()
    print(f"✓ User created: {data['user']['email']}")
    print(f"✓ User ID: {data['user']['id']}")
    print(f"✓ Access token: {data['tokens']['access_token'][:30]}...")

    assert response.status_code == 201
    assert data["user"]["email"] == "testuser@example.com"
    assert data["tokens"]["access_token"]

    print("\n✅ User registration works!")
    return data


#  ============================================================================
# Test 3: Duplicate Registration
# ============================================================================

async def test_duplicate_registration(client: AsyncClient):
    """Test that duplicate email is rejected."""
    print("\n" + "=" * 60)
    print("TEST 3: Duplicate Email Rejection")
    print("=" * 60)

    response = await client.post(
        "/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "AnotherPass123!",
        },
    )

    print(f"\n✓ Status: {response.status_code}")
    print(f"✓ Error: {response.json()['detail']}")

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

    print("\n✅ Duplicate email rejection works!")


# ============================================================================
# Test 4: POST /auth/login
# ============================================================================

async def test_login_user(client: AsyncClient):
    """Test user login endpoint."""
    print("\n" + "=" * 60)
    print("TEST 4: POST /auth/login")
    print("=" * 60)

    response = await client.post(
        "/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "SecurePass123!",
        },
    )

    print(f"\n✓ Status: {response.status_code}")
    data = response.json()
    print(f"✓ User: {data['user']['email']}")
    print(f"✓ Access token: {data['tokens']['access_token'][:30]}...")

    assert response.status_code == 200
    assert data["user"]["email"] == "testuser@example.com"
    assert data["tokens"]["access_token"]

    print("\n✅ User login works!")
    return data


# ============================================================================
# Test 5: Wrong Password
# ============================================================================

async def test_wrong_password(client: AsyncClient):
    """Test login with wrong password."""
    print("\n" + "=" * 60)
    print("TEST 5: Wrong Password")
    print("=" * 60)

    response = await client.post(
        "/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "WrongPassword123!",
        },
    )

    print(f"\n✓ Status: {response.status_code}")
    print(f"✓ Error: {response.json()['detail']}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

    print("\n✅ Wrong password rejection works!")


# ============================================================================
# Test 6: POST /auth/refresh
# ============================================================================

async def test_refresh_token(client: AsyncClient):
    """Test token refresh endpoint."""
    print("\n" + "=" * 60)
    print("TEST 6: POST /auth/refresh")
    print("=" * 60)

    # First, login to get tokens
    login_response = await client.post(
        "/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "SecurePass123!",
        },
    )
    refresh_token = login_response.json()["tokens"]["refresh_token"]
    print(f"\n✓ Got refresh token: {refresh_token[:30]}...")

    # Use refresh token to get new access token
    response = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    print(f"\n✓ Status: {response.status_code}")
    data = response.json()
    print(f"✓ New access token: {data['access_token'][:30]}...")

    assert response.status_code == 200
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"

    print("\n✅ Token refresh works!")


# ============================================================================
# Main Test Runner
# ============================================================================

async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TESTING API ENDPOINTS")
    print("=" * 60)

    try:
        # Setup
        print("\n🔧 Setting up test database...")
        await setup_database()
        print("✅ Database ready")

        # Create async client
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver"
        ) as client:
            # Run tests
            await test_health_check(client)
            await test_register_user(client)
            await test_duplicate_registration(client)
            await test_login_user(client)
            await test_wrong_password(client)
            await test_refresh_token(client)

        # Summary
        print("\n" + "=" * 60)
        print("✅ ALL API TESTS PASSED!")
        print("=" * 60)
        print("\nKey Learnings:")
        print("1. Registration creates user and returns tokens")
        print("2. Duplicate emails are rejected (400)")
        print("3. Login verifies credentials and returns tokens")
        print("4. Wrong credentials return 401 error")
        print("5. Token refresh generates new access token")

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
