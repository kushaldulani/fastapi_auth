"""
Test password hashing and JWT token functions.

This verifies our security.py module works correctly:
1. Password hashing and verification
2. JWT token creation and validation
3. Token expiration handling
4. Token type differentiation (access vs refresh)
"""

import asyncio
from datetime import timedelta

from fastapi_auth.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiration,
    hash_password,
    verify_access_token,
    verify_password,
    verify_refresh_token,
)


async def test_password_hashing():
    """Test password hashing and verification."""
    print("\n" + "=" * 60)
    print("TEST 1: Password Hashing")
    print("=" * 60)

    # Test 1: Hash a password
    plain_password = "my_secure_password123!"
    hashed = hash_password(plain_password)

    print(f"✓ Plain password: {plain_password}")
    print(f"✓ Hashed password: {hashed[:60]}...")
    print(f"✓ Hash length: {len(hashed)} characters")

    # Test 2: Verify correct password
    is_valid = verify_password(plain_password, hashed)
    print(f"✓ Correct password verification: {is_valid}")
    assert is_valid, "Correct password should verify"

    # Test 3: Verify wrong password
    is_valid = verify_password("wrong_password", hashed)
    print(f"✓ Wrong password verification: {is_valid}")
    assert not is_valid, "Wrong password should not verify"

    # Test 4: Same password produces different hashes (salt)
    hashed2 = hash_password(plain_password)
    print(f"✓ Hash 1: {hashed[:30]}...")
    print(f"✓ Hash 2: {hashed2[:30]}...")
    print(f"✓ Hashes are different (salted): {hashed != hashed2}")
    assert hashed != hashed2, "Same password should produce different hashes"

    print("✅ All password tests passed!")


async def test_jwt_tokens():
    """Test JWT token creation and validation."""
    print("\n" + "=" * 60)
    print("TEST 2: JWT Token Creation")
    print("=" * 60)

    # Test 1: Create access token
    user_data = {"user_id": 123, "email": "test@example.com"}
    access_token = create_access_token(user_data)

    print(f"✓ User data: {user_data}")
    print(f"✓ Access token: {access_token[:50]}...")
    print(f"✓ Token length: {len(access_token)} characters")

    # Test 2: Decode access token
    payload = decode_token(access_token)
    print(f"✓ Decoded payload: {payload}")
    assert payload is not None, "Token should decode successfully"
    assert payload["user_id"] == 123, "User ID should match"
    assert payload["email"] == "test@example.com", "Email should match"
    assert payload["type"] == "access", "Token type should be 'access'"
    print("✓ Token contains correct data and type")

    # Test 3: Verify access token
    verified_payload = verify_access_token(access_token)
    print(f"✓ Verified access token: {verified_payload is not None}")
    assert verified_payload is not None, "Access token should verify"

    # Test 4: Create refresh token
    refresh_token = create_refresh_token(user_data)
    print(f"✓ Refresh token: {refresh_token[:50]}...")

    # Test 5: Verify refresh token
    refresh_payload = verify_refresh_token(refresh_token)
    print(f"✓ Verified refresh token: {refresh_payload is not None}")
    assert refresh_payload is not None, "Refresh token should verify"
    assert refresh_payload["type"] == "refresh", "Token type should be 'refresh'"

    print("✅ All JWT creation tests passed!")


async def test_token_type_validation():
    """Test that token type validation works correctly."""
    print("\n" + "=" * 60)
    print("TEST 3: Token Type Validation")
    print("=" * 60)

    user_data = {"user_id": 123}

    # Create both token types
    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token(user_data)

    # Test 1: Access token should NOT verify as refresh token
    result = verify_refresh_token(access_token)
    print(f"✓ Access token verified as refresh token: {result is not None}")
    assert result is None, "Access token should not verify as refresh token"

    # Test 2: Refresh token should NOT verify as access token
    result = verify_access_token(refresh_token)
    print(f"✓ Refresh token verified as access token: {result is not None}")
    assert result is None, "Refresh token should not verify as access token"

    print("✅ Token type validation works correctly!")


async def test_token_expiration():
    """Test token expiration handling."""
    print("\n" + "=" * 60)
    print("TEST 4: Token Expiration")
    print("=" * 60)

    user_data = {"user_id": 123}

    # Test 1: Create token that expires in 1 second
    short_token = create_access_token(user_data, expires_delta=timedelta(seconds=1))

    # Should be valid immediately
    payload = verify_access_token(short_token)
    print(f"✓ Token valid immediately: {payload is not None}")
    assert payload is not None, "Token should be valid immediately"

    # Get expiration time
    exp_time = get_token_expiration(short_token)
    print(f"✓ Token expiration time: {exp_time}")
    assert exp_time is not None, "Should get expiration time"

    # Wait for token to expire
    print("⏳ Waiting 2 seconds for token to expire...")
    await asyncio.sleep(2)

    # Should be invalid now
    payload = verify_access_token(short_token)
    print(f"✓ Token valid after expiration: {payload is not None}")
    assert payload is None, "Expired token should not verify"

    print("✅ Token expiration works correctly!")


async def test_invalid_tokens():
    """Test handling of invalid tokens."""
    print("\n" + "=" * 60)
    print("TEST 5: Invalid Token Handling")
    print("=" * 60)

    # Test 1: Completely invalid token
    invalid_token = "this.is.not.a.valid.token"
    payload = decode_token(invalid_token)
    print(f"✓ Invalid token decoded: {payload is not None}")
    assert payload is None, "Invalid token should return None"

    # Test 2: Tampered token (changed signature)
    valid_token = create_access_token({"user_id": 123})
    tampered_token = valid_token[:-10] + "tampered123"
    payload = decode_token(tampered_token)
    print(f"✓ Tampered token decoded: {payload is not None}")
    assert payload is None, "Tampered token should return None"

    # Test 3: Empty token
    payload = decode_token("")
    print(f"✓ Empty token decoded: {payload is not None}")
    assert payload is None, "Empty token should return None"

    print("✅ Invalid token handling works correctly!")


async def main():
    """Run all security tests."""
    print("\n" + "=" * 60)
    print("TESTING PASSWORD HASHING & JWT TOKENS")
    print("=" * 60)

    await test_password_hashing()
    await test_jwt_tokens()
    await test_token_type_validation()
    await test_token_expiration()
    await test_invalid_tokens()

    print("\n" + "=" * 60)
    print("✅ ALL SECURITY TESTS PASSED!")
    print("=" * 60)
    print("\nKey Learnings:")
    print("1. Bcrypt automatically salts passwords (same password → different hashes)")
    print("2. JWT tokens contain type field to distinguish access vs refresh")
    print("3. Expired tokens are automatically rejected")
    print("4. Invalid/tampered tokens return None (fail gracefully)")
    print("5. Token expiration is enforced by the JWT library")


if __name__ == "__main__":
    asyncio.run(main())
