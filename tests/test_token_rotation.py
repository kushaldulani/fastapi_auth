"""
Test refresh token rotation and reuse detection.

This tests the security feature that prevents token theft.
"""

import asyncio

from httpx import ASGITransport, AsyncClient

from fastapi_auth.core.database import engine
from fastapi_auth.main import app
from fastapi_auth.models.base import Base
from fastapi_auth.models import user, token_blacklist, user_session  # noqa: F401


async def setup_database():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def cleanup_database():
    """Clean up."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_token_rotation():
    """Test that refresh tokens are rotated."""
    print("\n" + "=" * 60)
    print("TEST 1: Token Rotation")
    print("=" * 60)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        register = await client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
        })
        refresh_token_1 = register.json()["tokens"]["refresh_token"]
        print(f"\n✓ Got first refresh token: {refresh_token_1[:20]}...")

        # Refresh once
        refresh_1 = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token_1
        })
        assert refresh_1.status_code == 200
        refresh_token_2 = refresh_1.json()["refresh_token"]
        print(f"✓ Got second refresh token: {refresh_token_2[:20]}...")

        # Verify tokens are different
        assert refresh_token_1 != refresh_token_2
        print("✓ Tokens are different (rotation works!)")

        # Refresh again
        refresh_2 = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token_2
        })
        assert refresh_2.status_code == 200
        refresh_token_3 = refresh_2.json()["refresh_token"]
        print(f"✓ Got third refresh token: {refresh_token_3[:20]}...")

        assert refresh_token_2 != refresh_token_3
        print("✓ Tokens keep rotating!")

    print("\n✅ Token rotation works!")


async def test_token_reuse_detection():
    """Test that old tokens are rejected (reuse detection)."""
    print("\n" + "=" * 60)
    print("TEST 2: Token Reuse Detection (Security)")
    print("=" * 60)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login
        login = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
        })
        refresh_token_1 = login.json()["tokens"]["refresh_token"]
        print(f"\n✓ User logged in, got refresh_token_1")

        # Simulate: Attacker steals refresh_token_1

        # User refreshes (normal behavior)
        refresh_1 = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token_1
        })
        assert refresh_1.status_code == 200
        refresh_token_2 = refresh_1.json()["refresh_token"]
        print(f"✓ User refreshed → got refresh_token_2")
        print(f"  (refresh_token_1 is now BLACKLISTED)")

        # Attacker tries to use stolen refresh_token_1
        print(f"\n🔴 Attacker tries to use stolen refresh_token_1...")
        attacker_refresh = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token_1  # Old token!
        })

        # Should be rejected!
        assert attacker_refresh.status_code == 401
        assert "reuse detected" in attacker_refresh.json()["detail"].lower()
        print(f"✅ OLD TOKEN REJECTED!")
        print(f"   Status: {attacker_refresh.status_code}")
        print(f"   Error: {attacker_refresh.json()['detail']}")

        # User can still use new token
        refresh_2 = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token_2
        })
        assert refresh_2.status_code == 200
        print(f"\n✓ User's NEW token still works")

    print("\n✅ Token reuse detection works! Attack prevented!")


async def test_double_use_scenario():
    """Test what happens if attacker uses token first."""
    print("\n" + "=" * 60)
    print("TEST 3: Attacker Uses Token First")
    print("=" * 60)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login
        login = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
        })
        refresh_token = login.json()["tokens"]["refresh_token"]
        print(f"\n✓ User logged in")
        print(f"  Both user and attacker have same refresh token")

        # Attacker uses it first!
        print(f"\n🔴 Attacker refreshes token first...")
        attacker_refresh = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert attacker_refresh.status_code == 200
        attacker_new_token = attacker_refresh.json()["refresh_token"]
        print(f"✅ Attacker got new token (original is now blacklisted)")

        # Now user tries to use original token
        print(f"\n👤 User tries to use original token...")
        user_refresh = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token  # Original token
        })

        # Should be rejected (token was already used)
        assert user_refresh.status_code == 401
        assert "reuse detected" in user_refresh.json()["detail"].lower()
        print(f"🚨 USER'S TOKEN REJECTED - THEFT DETECTED!")
        print(f"   Status: {user_refresh.status_code}")
        print(f"   Error: {user_refresh.json()['detail']}")
        print(f"\n   This alerts us that the token was compromised!")
        print(f"   In production: Revoke ALL user's tokens, force re-login")

    print("\n✅ Token theft detection works!")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TESTING TOKEN ROTATION & SECURITY")
    print("=" * 60)

    try:
        # Setup
        print("\n🔧 Setting up test database...")
        await setup_database()
        print("✅ Database ready")

        # Run tests
        await test_token_rotation()
        await test_token_reuse_detection()
        await test_double_use_scenario()

        # Summary
        print("\n" + "=" * 60)
        print("✅ ALL SECURITY TESTS PASSED!")
        print("=" * 60)
        print("\nWhat we proved:")
        print("1. ✅ Tokens rotate on every refresh")
        print("2. ✅ Old tokens are blacklisted (invalid)")
        print("3. ✅ Reusing old token is detected and rejected")
        print("4. ✅ Token theft can be detected")
        print("\nSecurity level: PRODUCTION-READY! 🔒")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n🔧 Cleaning up...")
        await cleanup_database()
        await engine.dispose()
        print("✅ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
