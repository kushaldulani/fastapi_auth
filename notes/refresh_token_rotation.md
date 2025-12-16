# Refresh Token Rotation - Security Best Practice

## What is Refresh Token Rotation?

**Instead of:**
```
POST /auth/refresh
Request: { "refresh_token": "old_token" }
Response: { "access_token": "new_access" }  // old refresh token still valid
```

**We do:**
```
POST /auth/refresh
Request: { "refresh_token": "old_token" }
Response: {
    "access_token": "new_access",
    "refresh_token": "new_refresh"  // ← Old token becomes INVALID
}
```

---

## Why is This More Secure?

### 1. **Detects Token Theft**

**Scenario: Attacker steals refresh token**

```
Timeline WITHOUT Rotation:
Day 1: User logs in → refresh_token_A (valid 30 days)
Day 5: Attacker steals refresh_token_A
Day 6-30: BOTH user and attacker can use refresh_token_A
         → System cannot detect theft! 😱

Timeline WITH Rotation:
Day 1: User logs in → refresh_token_A
Day 5: Attacker steals refresh_token_A
Day 6: User refreshes → gets refresh_token_B (A is now INVALID)
Day 7: Attacker tries refresh_token_A → REJECTED! ✅
```

### 2. **Limits Damage Window**

**Without Rotation:**
- Stolen refresh token works for 30 days
- Attacker has 30 days to exploit

**With Rotation:**
- Stolen token only works until next refresh
- Typically 15 minutes (access token expiry)
- Damage window: 15 min vs 30 days!

### 3. **Enables Theft Detection**

```python
# When old token is used after rotation:
if old_jti_in_blacklist:
    # Someone is using a revoked token!
    # This means BOTH tokens are compromised

    # Revoke ALL user's tokens
    revoke_all_user_tokens(user_id)

    # Force re-login
    # Alert security team
    log_security_event("Token reuse detected", user_id)
```

---

## Implementation

### Current Code (Simple Version)

```python
@router.post("/refresh")
async def refresh_token_endpoint(request: RefreshTokenRequest, db: AsyncSession):
    # Verify old refresh token
    payload = verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(401, "Invalid refresh token")

    # Get user
    user = await get_user_by_id(db, payload["user_id"])

    # Generate NEW tokens (both access AND refresh)
    token_data = {"user_id": user.id, "email": user.email}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)  # ← Rotation!

    # TODO: Add old token to blacklist (when we add Redis)
    # This makes it truly invalid

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )
```

### With Redis (Future Enhancement)

```python
@router.post("/refresh")
async def refresh_token_endpoint(request: RefreshTokenRequest, db, redis):
    # Verify old refresh token
    payload = verify_refresh_token(request.refresh_token)
    old_jti = payload["jti"]

    # Check if old token was already used (reuse detection)
    if redis.exists(f"blacklist:{old_jti}"):
        # Token reuse detected! Compromised!
        await revoke_all_user_tokens(redis, payload["user_id"])
        raise HTTPException(401, "Token reuse detected - all tokens revoked")

    # Generate new tokens
    new_access_token = create_access_token(...)
    new_refresh_token = create_refresh_token(...)
    new_jti = jwt.decode(new_refresh_token)["jti"]

    # Blacklist old refresh token (30 day TTL matching token expiry)
    redis.setex(
        f"blacklist:{old_jti}",
        30 * 24 * 60 * 60,  # 30 days
        "revoked"
    )

    # Whitelist new refresh token
    redis.setex(
        f"refresh:{new_jti}",
        30 * 24 * 60 * 60,
        payload["user_id"]
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )
```

---

## Security Benefits Summary

| Feature | Without Rotation | With Rotation |
|---------|------------------|---------------|
| **Stolen token validity** | 30 days | ~15 minutes |
| **Theft detection** | ❌ No | ✅ Yes (with Redis) |
| **Damage limitation** | High | Low |
| **Automatic revocation** | ❌ No | ✅ Yes |
| **Replay attack prevention** | ❌ No | ✅ Yes |

---

## Client-Side Implementation

**Frontend must update stored refresh token:**

```javascript
// BAD: Don't do this
async function refreshTokens() {
    const oldRefreshToken = localStorage.getItem('refresh_token');
    const response = await fetch('/auth/refresh', {
        body: JSON.stringify({ refresh_token: oldRefreshToken })
    });
    const data = await response.json();

    // ❌ Forgot to update refresh token!
    setAccessToken(data.access_token);
    // Old refresh token won't work next time!
}

// GOOD: Update both tokens
async function refreshTokens() {
    const oldRefreshToken = localStorage.getItem('refresh_token');
    const response = await fetch('/auth/refresh', {
        body: JSON.stringify({ refresh_token: oldRefreshToken })
    });
    const data = await response.json();

    // ✅ Update BOTH tokens
    setAccessToken(data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);  // ← Important!
}
```

---

## Trade-offs

### Pros ✅
- Much better security
- Detects token theft
- Industry best practice (OAuth 2.1 standard)
- Limits attack window

### Cons ❌
- Slightly more complex (but worth it!)
- Client must handle rotation
- Requires storage (Redis) for full security
- More database/Redis calls

---

## Industry Adoption

**Who uses refresh token rotation:**
- Google OAuth 2.0
- Auth0
- Okta
- Microsoft Azure AD
- GitHub
- All major OAuth providers

**OAuth 2.1 Specification:**
> "Authorization servers MUST rotate refresh tokens on each use or implement sender-constrained refresh tokens."

---

## Our Implementation Status

✅ **Currently Implemented:**
- Generate new refresh token on each refresh
- Return both access + refresh tokens
- Unique JTI for each token

🔄 **Coming Soon (with Redis):**
- Blacklist old refresh tokens
- Detect token reuse
- Auto-revoke on suspicious activity

---

## Testing

```python
async def test_refresh_token_rotation(client):
    # Login
    login = await client.post("/auth/login", json={...})
    refresh_token_1 = login.json()["tokens"]["refresh_token"]

    # First refresh
    refresh_1 = await client.post("/auth/refresh", json={
        "refresh_token": refresh_token_1
    })
    refresh_token_2 = refresh_1.json()["refresh_token"]

    # Verify tokens are different (rotation happened)
    assert refresh_token_1 != refresh_token_2

    # Try to use old token (should fail with Redis)
    refresh_old = await client.post("/auth/refresh", json={
        "refresh_token": refresh_token_1  # Old token
    })
    # With Redis: assert refresh_old.status_code == 401
    # Without Redis: Still works (but less secure)
```

---

## Summary

**Refresh token rotation is a critical security feature that:**

1. Makes stolen tokens expire in ~15 minutes instead of 30 days
2. Enables detection of token theft
3. Follows OAuth 2.1 security best practices
4. Requires minimal frontend changes

**When to skip rotation:**
- Never! Always implement it for production apps
- Only exception: Internal tools with low security requirements

**Next steps:**
1. ✅ Implemented token rotation
2. 🔄 Add Redis for blacklisting (Step 9+)
3. 🔄 Add reuse detection
4. 🔄 Add security monitoring/alerts
