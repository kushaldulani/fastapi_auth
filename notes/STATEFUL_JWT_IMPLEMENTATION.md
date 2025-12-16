# Stateful JWT Implementation - Session-Based Token Security

## Overview

This FastAPI authentication system implements a **stateful JWT approach** for production-grade token security. Unlike traditional stateless JWTs, we track both access and refresh tokens in the database, enabling immediate revocation and comprehensive session management.

## Architecture

### Core Security Features

1. **JTI Hashing (SHA-256)** - JWT IDs are hashed before database storage
2. **Dual Token Tracking** - Both access and refresh token JTIs stored per session
3. **Immediate Revocation** - Access tokens can be invalidated instantly (not waiting for expiration)
4. **Token Rotation** - Each refresh generates new access AND refresh tokens
5. **Theft Detection** - Detects token reuse and revokes all user sessions
6. **Multi-Device Sessions** - Track separate sessions across different devices

## Database Schema

### UserSession Table

```sql
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,

    -- SHA-256 hash of current access token's JTI (checked on every API request)
    access_token_jti_hash VARCHAR(64) NOT NULL,

    -- SHA-256 hash of current refresh token's JTI (used during token rotation)
    refresh_token_jti_hash VARCHAR(64) NOT NULL UNIQUE,

    -- SHA-256 hash of previous refresh token's JTI (for theft detection)
    previous_refresh_token_jti_hash VARCHAR(64),

    -- Session status: 'active', 'revoked', 'expired'
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    device_info VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Indexes for fast lookups
    INDEX (user_id),
    INDEX (access_token_jti_hash),
    INDEX (refresh_token_jti_hash),
    INDEX (previous_refresh_token_jti_hash),
    INDEX (status)
);
```

### TokenBlacklist Table

```sql
CREATE TABLE token_blacklist (
    jti_hash VARCHAR(64) PRIMARY KEY,  -- SHA-256 hash of JTI
    user_id INTEGER NOT NULL,
    blacklisted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reason VARCHAR(50)  -- 'rotated', 'security_breach_reuse', 'logout'
);
```

## Authentication Flow

### 1. Login/Registration

```python
# User logs in or registers
# Step 1: Generate both access and refresh tokens with unique JTIs
access_token = create_access_token({"user_id": user.id, "email": user.email})
refresh_token = create_refresh_token({"user_id": user.id, "email": user.email})

# Step 2: Decode tokens to extract JTIs
access_jti = jwt.decode(access_token)["jti"]
refresh_jti = jwt.decode(refresh_token)["jti"]

# Step 3: Hash JTIs with SHA-256
access_token_jti_hash = hash_jti(access_jti)  # sha256(access_jti).hexdigest()
refresh_token_jti_hash = hash_jti(refresh_jti)

# Step 4: Create session record
session = UserSession(
    user_id=user.id,
    access_token_jti_hash=access_token_jti_hash,
    refresh_token_jti_hash=refresh_token_jti_hash,
    previous_refresh_token_jti_hash=None,  # First login
    status='active'
)
db.add(session)
db.commit()

# Step 5: Return tokens to client
return {
    "access_token": access_token,
    "refresh_token": refresh_token
}
```

### 2. Protected API Requests

```python
# Client sends: Authorization: Bearer <access_token>

# Step 1: Verify token signature and expiration
payload = jwt.decode(access_token, SECRET_KEY, algorithms=["HS256"])

# Step 2: Extract JTI and hash it
access_jti = payload["jti"]
access_token_jti_hash = hash_jti(access_jti)

# Step 3: Check if session is active (STATEFUL CHECK)
session = db.query(UserSession).filter(
    UserSession.user_id == payload["user_id"],
    UserSession.access_token_jti_hash == access_token_jti_hash,
    UserSession.status == 'active'  # ← Immediate revocation capability!
).first()

if not session:
    raise HTTPException(401, "Token revoked or invalid")

# Step 4: Proceed with request
return current_user
```

**Key Benefits:**
- Even if access token hasn't expired, we can revoke it by setting `status='revoked'`
- No need to wait for token expiration
- Perfect for logout, security breach, or admin actions

### 3. Token Refresh (with Rotation)

```python
# Client sends refresh_token to /auth/refresh

# Step 1: Verify refresh token signature
payload = jwt.decode(refresh_token, SECRET_KEY)

# Step 2: Extract and hash JTI
current_refresh_jti = payload["jti"]
current_refresh_jti_hash = hash_jti(current_refresh_jti)

# Step 3: Find active session with this refresh token
session = db.query(UserSession).filter(
    UserSession.refresh_token_jti_hash == current_refresh_jti_hash,
    UserSession.status == 'active'
).first()

if session:
    # ✅ VALID REFRESH - First time using this token

    # Generate NEW tokens
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    # Extract new JTIs
    new_access_jti_hash = hash_jti(jwt.decode(new_access_token)["jti"])
    new_refresh_jti_hash = hash_jti(jwt.decode(new_refresh_token)["jti"])

    # Update session: current → previous, new → current
    session.previous_refresh_token_jti_hash = session.refresh_token_jti_hash
    session.refresh_token_jti_hash = new_refresh_jti_hash
    session.access_token_jti_hash = new_access_jti_hash
    session.last_used_at = datetime.now(timezone.utc)

    # Blacklist old refresh token for audit trail
    blacklist = TokenBlacklist(
        jti_hash=current_refresh_jti_hash,
        user_id=user_id,
        expires_at=payload["exp"],
        reason='rotated'
    )
    db.add(blacklist)
    db.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token
    }
```

### 4. Theft Detection (Token Reuse)

```python
# Step 3 continued: Check if token matches PREVIOUS refresh token
if not session:
    # Check previous_refresh_token_jti_hash
    reused_session = db.query(UserSession).filter(
        UserSession.previous_refresh_token_jti_hash == current_refresh_jti_hash
    ).first()

    if reused_session:
        # 🚨 SECURITY BREACH! Someone used an old/rotated token
        # This means: attacker has the token and already used it

        # RESPONSE: Revoke ALL user's sessions
        db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).update({
            "status": "revoked"
        })

        # Blacklist token with reason
        blacklist = TokenBlacklist(
            jti_hash=current_refresh_jti_hash,
            user_id=user_id,
            expires_at=payload["exp"],
            reason='security_breach_reuse'
        )
        db.add(blacklist)
        db.commit()

        # TODO: Send security alert email to user
        # TODO: Log security event for admin review

        raise HTTPException(
            401,
            "Security breach detected. All tokens revoked. Please login again."
        )
```

**Why This Works:**
1. Normal flow: Token is in `refresh_token_jti_hash` (valid)
2. After rotation: Old token moves to `previous_refresh_token_jti_hash` (grace period)
3. If previous token used again: **THEFT DETECTED** → Revoke everything

### 5. Logout

```python
@router.post("/auth/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Logout user by revoking current session."""

    # Extract access token JTI
    access_token = credentials.credentials
    payload = jwt.decode(access_token, SECRET_KEY, algorithms=["HS256"])
    access_jti_hash = hash_jti(payload["jti"])

    # Find and revoke session
    await db.execute(
        update(UserSession)
        .where(UserSession.access_token_jti_hash == access_jti_hash)
        .values(status="revoked")
    )
    await db.commit()

    return {"message": "Logged out successfully"}
```

**Immediate Effect:**
- Next API request with that access token will fail (even if not expired)
- Session status check in `get_current_user` dependency catches it

## Security Properties

### 1. Database Breach Protection
- **Problem**: If database is compromised, attacker gets JTIs
- **Solution**: We hash JTIs with SHA-256 before storage
- **Result**: Attacker cannot reconstruct original JWT from hash

### 2. Token Theft Detection
- **Problem**: Attacker steals refresh token and uses it
- **Solution**: Track previous token for one rotation cycle
- **Result**: If previous token is reused → detected as theft → revoke all sessions

### 3. Immediate Revocation
- **Problem**: Traditional JWT works until expiration (even if user logged out)
- **Solution**: Check `status='active'` on every API request
- **Result**: Logout/revocation takes effect immediately

### 4. Multi-Device Support
- **Problem**: User logs in from phone and laptop
- **Solution**: Separate `UserSession` record per login
- **Result**: Can view/manage sessions per device, revoke individually or all at once

### 5. Audit Trail
- **Problem**: Need to track why tokens were blacklisted
- **Solution**: `TokenBlacklist.reason` field ('rotated', 'security_breach_reuse', 'logout')
- **Result**: Security team can review incidents

## Trade-offs

### Stateful vs Stateless JWT

| Aspect | Stateless JWT | Stateful JWT (This Implementation) |
|--------|---------------|-----------------------------------|
| **Database hits** | None (only signature verification) | Every request (session lookup) |
| **Revocation** | Not possible (wait for expiration) | Immediate (set status='revoked') |
| **Theft detection** | Not possible | Detects token reuse |
| **Multi-device** | Not tracked | Full visibility and control |
| **Scalability** | Excellent (no DB) | Good (indexed lookups, caching possible) |
| **Security** | Good | Excellent |

### Performance Considerations

1. **Database Load**
   - Every API request queries `user_sessions` table
   - Mitigations: Indexed columns, Redis caching, read replicas

2. **Token Rotation**
   - Generates 2 new JWTs per refresh
   - Acceptable: Refresh happens ~every 15 minutes (not every request)

3. **Table Growth**
   - `user_sessions`: One row per active session (bounded by concurrent users)
   - `token_blacklist`: Grows with rotations (cleanup expired tokens periodically)

## Future Enhancements

### 1. Session Management UI
```python
@router.get("/auth/sessions")
async def list_sessions(current_user: User = Depends(get_current_user)):
    """List all active sessions for current user."""
    sessions = await db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.status == 'active'
    ).all()

    return [{
        "session_id": s.id,
        "device_info": s.device_info,
        "created_at": s.created_at,
        "last_used_at": s.last_used_at
    } for s in sessions]

@router.post("/auth/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user)
):
    """Revoke a specific session (e.g., "Sign out from other device")."""
    await db.execute(
        update(UserSession)
        .where(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id
        )
        .values(status="revoked")
    )
    await db.commit()
    return {"message": "Session revoked"}
```

### 2. Redis Caching
```python
# Cache active session lookups
@lru_cache(ttl=60)  # Cache for 1 minute
async def get_session_by_access_jti_hash(access_jti_hash: str):
    return await db.query(UserSession).filter(
        UserSession.access_token_jti_hash == access_jti_hash,
        UserSession.status == 'active'
    ).first()
```

### 3. Security Alerts
```python
async def send_security_alert(user_id: int):
    """Email user about token theft detection."""
    user = await get_user_by_id(user_id)
    await send_email(
        to=user.email,
        subject="Security Alert: Suspicious Activity Detected",
        body="""
        We detected suspicious activity on your account (token reuse).
        All sessions have been logged out for your protection.
        Please login again and change your password if you didn't initiate this.
        """
    )
```

### 4. Cleanup Job
```python
# Periodic task (run daily via cron/celery)
async def cleanup_expired_tokens():
    """Remove expired entries from token_blacklist."""
    now = datetime.now(timezone.utc)

    result = await db.execute(
        delete(TokenBlacklist).where(TokenBlacklist.expires_at < now)
    )
    await db.commit()

    print(f"Cleaned up {result.rowcount} expired blacklist entries")
```

## Testing the Implementation

### Test Case 1: Normal Flow
```bash
# 1. Login
curl -X POST http://localhost:8003/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Response: { "access_token": "...", "refresh_token": "..." }

# 2. Use access token
curl -X GET http://localhost:8003/auth/hello \
  -H "Authorization: Bearer <access_token>"

# Response: { "message": "Hello, test@example.com!" }

# 3. Refresh tokens
curl -X POST http://localhost:8003/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'

# Response: { "access_token": "...", "refresh_token": "..." }
# Note: Old access_token is now INVALID (revoked via session update)
```

### Test Case 2: Token Theft Detection
```bash
# 1. Login and get tokens
# 2. Refresh tokens (get new access + refresh)
# 3. Try using OLD refresh token again

curl -X POST http://localhost:8003/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<old_refresh_token>"}'

# Response: 401 Unauthorized
# "Security breach detected. All tokens revoked. Please login again."

# 4. Verify ALL sessions revoked
curl -X GET http://localhost:8003/auth/hello \
  -H "Authorization: Bearer <new_access_token>"

# Response: 401 Unauthorized (session status = 'revoked')
```

### Test Case 3: Immediate Logout
```bash
# 1. Login and get access_token
# 2. Logout (sets session status='revoked')
# 3. Try using access_token (even if not expired)

curl -X GET http://localhost:8003/auth/hello \
  -H "Authorization: Bearer <access_token>"

# Response: 401 Unauthorized
# "Token session is invalid or has been revoked. Please login again."
```

## Files Modified

1. **`src/fastapi_auth/models/user_session.py`** - Session model with 3 JTI hash columns
2. **`src/fastapi_auth/models/token_blacklist.py`** - Blacklist model with hashed JTI
3. **`src/fastapi_auth/core/security.py`** - Added `hash_jti()` function
4. **`src/fastapi_auth/services/auth.py`** - Updated login/register to store both token JTIs
5. **`src/fastapi_auth/api/dependencies.py`** - Updated `get_current_user` to check session status
6. **`src/fastapi_auth/api/routes/auth.py`** - Updated refresh endpoint with new logic
7. **`migrations/versions/014585e6af90_*.py`** - Migration for updated schema

## References

- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [RFC 7519 - JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [OAuth 2.0 Token Revocation](https://datatracker.ietf.org/doc/html/rfc7009)
- [Refresh Token Rotation Best Practices](https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation)

---

**Implementation Date**: December 2025
**Status**: ✅ Production Ready
**Security Level**: High
