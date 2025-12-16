# Step 5: Password Security & JWT Tokens

## What We Built

Created the **security layer** for authentication with:
1. **Password hashing** using bcrypt
2. **JWT token creation** (access & refresh tokens)
3. **JWT token validation** with type checking
4. **Complete test suite** verifying all functionality

---

## Files Created

### 1. [src/fastapi_auth/core/security.py](../src/fastapi_auth/core/security.py)

The main security module with all authentication utilities.

**Password Hashing Functions:**
```python
hash_password(password: str) -> str
# Hashes password using bcrypt (cost factor 12)
# Returns 60-character hash like: $2b$12$KIXqX5g...

verify_password(plain_password: str, hashed_password: str) -> bool
# Verifies password against hash
# Returns True if match, False otherwise
```

**JWT Token Creation:**
```python
create_access_token(data: dict, expires_delta: timedelta | None = None) -> str
# Creates SHORT-LIVED token (15 min default)
# Adds: exp, iat, type="access"

create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str
# Creates LONG-LIVED token (30 days default)
# Adds: exp, iat, type="refresh"
```

**JWT Token Validation:**
```python
decode_token(token: str) -> dict | None
# Generic decoder - checks signature & expiration
# Returns payload or None if invalid

verify_access_token(token: str) -> dict | None
# Validates access tokens specifically
# Checks type="access"

verify_refresh_token(token: str) -> dict | None
# Validates refresh tokens specifically
# Checks type="refresh"

get_token_expiration(token: str) -> datetime | None
# Get expiration without validation
# Useful for displaying "expires in X minutes"
```

### 2. [tests/test_security.py](../tests/test_security.py)

Complete test suite covering:
- Password hashing and verification
- JWT token creation and decoding
- Token type differentiation (access vs refresh)
- Token expiration handling
- Invalid token handling (tampered, expired, malformed)

---

## Key Concepts Learned

### 1. **Bcrypt Password Hashing**

**Why bcrypt?**
- Specifically designed for password hashing
- Automatically salts passwords (same password → different hashes)
- Slow by design (prevents brute force attacks)
- Cost factor 12 = good balance of security & speed

**How it works:**
```python
# Hash password
hashed = hash_password("test123")
# → "$2b$12$KIXqX5g..." (60 chars)

# Verify password
verify_password("test123", hashed)  # → True
verify_password("wrong", hashed)    # → False
```

**Salt explanation:**
```python
hash1 = hash_password("test123")  # → $2b$12$abc...
hash2 = hash_password("test123")  # → $2b$12$xyz...
# Different hashes! Bcrypt adds random salt automatically
```

### 2. **JWT (JSON Web Token)**

**Structure:** `header.payload.signature`

**Example token:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6MTc2NTkxNTc1MSwiaWF0IjoxNzY1OTE0ODUxLCJ0eXBlIjoiYWNjZXNzIn0.signature
```

**Decoded payload:**
```json
{
  "user_id": 123,
  "email": "test@example.com",
  "exp": 1765915751,      // Expiration timestamp
  "iat": 1765914851,      // Issued at timestamp
  "type": "access"        // Token type
}
```

**Key features:**
- **Stateless:** No database lookup needed to validate
- **Signed:** Can't be tampered with (signature verification)
- **Self-contained:** Contains all needed user data
- **Expiring:** Automatically invalid after expiration

### 3. **Access vs Refresh Tokens**

**Access Token:**
- Short-lived (15 minutes)
- Used for API requests
- Type: "access"
- If compromised, expires quickly

**Refresh Token:**
- Long-lived (30 days)
- Used to get new access tokens
- Type: "refresh"
- Stored more securely (httpOnly cookie)

**Why both?**
```
User logs in
  ↓
Get access token (15 min) + refresh token (30 days)
  ↓
Use access token for API requests
  ↓
Access token expires after 15 min
  ↓
Use refresh token to get new access token
  ↓
Continue making API requests
  ↓
Refresh token expires after 30 days
  ↓
User must log in again
```

This provides better security:
- Access tokens in memory (not stored permanently)
- Refresh tokens in secure httpOnly cookies
- If access token is stolen, it expires in 15 minutes
- If refresh token is stolen, can be revoked in database

### 4. **Token Type Validation**

**Why check token type?**

Prevents security issues:
```python
# Bad: User sends refresh token to access-only endpoint
# System accepts it → refresh token exposed in logs/URLs

# Good: Type checking prevents this
verify_access_token(refresh_token)  # → None (rejected!)
```

**Implementation:**
```python
def verify_access_token(token: str) -> dict | None:
    payload = decode_token(token)

    # Check token type
    if payload and payload.get("type") == "access":
        return payload

    return None  # Wrong type or invalid token
```

---

## Test Results

All tests passed successfully:

**Test 1: Password Hashing**
- ✅ Hashes passwords to 60-character bcrypt strings
- ✅ Correct password verification works
- ✅ Wrong password verification fails
- ✅ Same password produces different hashes (salted)

**Test 2: JWT Token Creation**
- ✅ Creates valid JWT tokens with user data
- ✅ Tokens contain exp, iat, type fields
- ✅ Access and refresh tokens both work
- ✅ Payload decodes correctly

**Test 3: Token Type Validation**
- ✅ Access tokens don't verify as refresh tokens
- ✅ Refresh tokens don't verify as access tokens

**Test 4: Token Expiration**
- ✅ Fresh tokens verify successfully
- ✅ Can extract expiration time from token
- ✅ Expired tokens are rejected

**Test 5: Invalid Token Handling**
- ✅ Completely invalid tokens return None
- ✅ Tampered tokens (changed signature) return None
- ✅ Empty tokens return None

---

## Security Best Practices Implemented

1. **Password Security:**
   - Never store plain passwords
   - Use bcrypt with proper cost factor (12)
   - Automatic salting prevents rainbow table attacks

2. **JWT Security:**
   - Short expiration for access tokens (15 min)
   - Long expiration for refresh tokens (30 days)
   - Type field prevents token misuse
   - Signature validation prevents tampering

3. **Fail Gracefully:**
   - Invalid tokens return `None` (not exceptions)
   - Expired tokens automatically rejected
   - Type mismatches silently fail

4. **Settings from Environment:**
   - SECRET_KEY from .env (never hardcode!)
   - Token expiration configurable
   - Easy to change for different environments

---

## Production Notes

### Token Expiration Times

**Default settings:**
- Access token: 15 minutes
- Refresh token: 30 days

**Adjust based on your needs:**

**High-security apps (banking):**
```
ACCESS_TOKEN_EXPIRE_MINUTES=5    # 5 minutes
REFRESH_TOKEN_EXPIRE_DAYS=7      # 7 days
```

**Low-security apps (blogs):**
```
ACCESS_TOKEN_EXPIRE_MINUTES=60   # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS=90     # 3 months
```

### SECRET_KEY Security

**Critical!** The SECRET_KEY is used to sign JWT tokens.

**Requirements:**
- At least 32 bytes (256 bits)
- Cryptographically random
- Never commit to git
- Different for each environment (dev, staging, prod)

**Generate new key:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**If compromised:**
- All JWT tokens can be forged
- Must rotate key immediately
- All users must re-login

### Token Storage (Client-Side)

**Access tokens:**
- Store in memory (React state, variable)
- Never in localStorage (XSS vulnerable)
- Never in cookies without httpOnly

**Refresh tokens:**
- Store in httpOnly cookies (we'll implement this in next steps)
- Prevents JavaScript access (XSS safe)
- Automatically sent with requests

---

## Common Issues & Solutions

### Issue 1: "Token expired"
**Cause:** Access token expired (15 min passed)
**Solution:** Use refresh token to get new access token

### Issue 2: "Invalid signature"
**Cause:** Token was tampered with or SECRET_KEY changed
**Solution:** User must re-login

### Issue 3: Same password produces different hashes
**Cause:** Not an issue! Bcrypt automatically salts
**Solution:** This is correct behavior for security

### Issue 4: Token validation slow
**Cause:** Bcrypt verification is intentionally slow
**Solution:** This is good! Prevents brute force attacks

---

## Next Steps

Now that we have password hashing and JWT tokens working, we can build:

**Step 6: Authentication Service**
- Create `services/auth.py`
- Implement `register_user(email, password)`
- Implement `login(email, password)`
- Return access + refresh tokens

**Step 7: API Endpoints**
- POST `/auth/register` - Create new user
- POST `/auth/login` - Get tokens
- POST `/auth/refresh` - Get new access token
- POST `/auth/logout` - Revoke refresh token

**Step 8: Dependency for Protected Routes**
- Create `get_current_user()` dependency
- Extract token from Authorization header
- Validate and return user info
- Use in protected endpoints

---

## Code Quality Notes

**What makes this code production-ready:**

1. **Type hints everywhere:**
   ```python
   def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
   ```

2. **Comprehensive docstrings:**
   - What the function does
   - Parameters explained
   - Return value explained
   - Usage examples

3. **Fail gracefully:**
   - Returns `None` instead of raising exceptions
   - Easy to check: `if payload is None: return error`

4. **Configuration from environment:**
   - No hardcoded secrets
   - Easy to change per environment

5. **Tested thoroughly:**
   - All functions have test coverage
   - Edge cases tested (expired, invalid, tampered)

6. **Security by default:**
   - Proper bcrypt cost factor
   - Short access token expiration
   - Token type validation

---

## Summary

**What we accomplished:**
- ✅ Password hashing with bcrypt (automatic salting)
- ✅ JWT token creation (access & refresh)
- ✅ JWT token validation (type-aware)
- ✅ Token expiration handling
- ✅ Comprehensive test suite
- ✅ Production-ready security settings

**Key takeaways:**
1. Never store plain passwords - always hash with bcrypt
2. Use short-lived access tokens + long-lived refresh tokens
3. Always validate token type to prevent misuse
4. Fail gracefully (return None, not exceptions)
5. Keep SECRET_KEY secure and environment-specific

**Ready for next step:**
We can now build the authentication service that uses these security functions to register users and handle login!
