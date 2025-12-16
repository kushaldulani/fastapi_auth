# Step 6: Authentication Service (Business Logic)

## What We Built

Created the **authentication service layer** with:
1. **User registration** - create users with hashed passwords
2. **User login** - verify credentials and issue tokens
3. **Token refresh** - get new access tokens
4. **User lookup** - find users by ID or email
5. **Pydantic schemas** - validate requests and format responses
6. **Custom exceptions** - clear error handling
7. **JWT with JTI** - unique token identifiers for security

---

## Files Created

### 1. [src/fastapi_auth/schemas/auth.py](../src/fastapi_auth/schemas/auth.py)

Pydantic schemas for request/response validation.

**Request Schemas** (data coming IN):
```python
class UserRegister(BaseModel):
    email: EmailStr  # Validates email format automatically
    password: str = Field(min_length=8, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str
```

**Response Schemas** (data going OUT):
```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_admin: bool
    email_verified: bool

    class Config:
        from_attributes = True  # Allows: UserResponse.model_validate(user_object)
```

### 2. [src/fastapi_auth/services/auth.py](../src/fastapi_auth/services/auth.py)

Business logic for authentication.

**Custom Exceptions**:
```python
class AuthenticationError(Exception):
    """Wrong password, inactive user, etc"""

class UserAlreadyExistsError(Exception):
    """Email already registered"""

class UserNotFoundError(Exception):
    """User doesn't exist"""
```

**Main Functions**:
```python
async def register_user(db: AsyncSession, user_data: UserRegister) -> tuple[User, TokenResponse]:
    # 1. Check if email exists
    # 2. Hash password
    # 3. Create user in database
    # 4. Generate tokens
    # 5. Return user + tokens

async def login_user(db: AsyncSession, credentials: UserLogin) -> tuple[User, TokenResponse]:
    # 1. Find user by email
    # 2. Verify password
    # 3. Check if active
    # 4. Generate tokens
    # 5. Return user + tokens

async def refresh_access_token(db: AsyncSession, user_id: int) -> str:
    # 1. Find user
    # 2. Check if active
    # 3. Generate new access token
    # 4. Return token

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    # Find and return user by ID

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    # Find and return user by email
```

### 3. [tests/test_auth_service.py](../tests/test_auth_service.py)

Comprehensive test suite covering all scenarios.

**Tests:**
1. User registration - creates user with hashed password and tokens
2. Duplicate email prevention - rejects existing emails
3. User login - verifies credentials and returns tokens
4. Wrong password rejection - fails authentication
5. Non-existent user - handles gracefully
6. Token refresh - generates new access tokens
7. Get user by ID - lookup functionality
8. Get user by email - lookup functionality

---

## Key Concepts Learned

### 1. **Service Layer Pattern**

**Three-layer architecture:**
```
API Endpoints (routes/)
    ↓
Business Logic (services/)  ← We're here!
    ↓
Database (models/)
```

**Why services?**
- **Separation of concerns**: Business logic separate from HTTP handling
- **Reusability**: Same service function can be used from multiple endpoints
- **Testability**: Easy to test without HTTP requests
- **Clean code**: Endpoints stay thin, logic stays in services

**Example:**
```python
# In API endpoint (later):
@router.post("/register")
async def register_endpoint(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    try:
        user, tokens = await register_user(db, user_data)  # Call service
        return {"user": UserResponse.model_validate(user), "tokens": tokens}
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 2. **Pydantic Schemas for Validation**

**Automatic validation:**
```python
# This FAILS automatically (invalid email):
UserRegister(email="not-an-email", password="test1234")
# → ValidationError: value is not a valid email address

# This FAILS automatically (password too short):
UserRegister(email="test@example.com", password="short")
# → ValidationError: ensure this value has at least 8 characters
```

**Benefits:**
- **Type safety**: IDE autocomplete + type checking
- **Automatic validation**: No manual checks needed
- **API documentation**: FastAPI auto-generates OpenAPI docs from schemas
- **Clear contracts**: Request/response shapes are explicit

### 3. **Custom Exceptions for Flow Control**

**Why custom exceptions?**

Makes error handling clearer:
```python
# Good (with custom exceptions):
try:
    user, tokens = await register_user(db, user_data)
    return {"success": True, "tokens": tokens}
except UserAlreadyExistsError:
    return {"success": False, "error": "Email already registered"}
except Exception:
    return {"success": False, "error": "Server error"}

# Bad (without custom exceptions):
user, tokens = await register_user(db, user_data)
if user is None:  # Why is it None? Password wrong? User exists? Server error?
    return {"success": False, "error": "Something went wrong"}
```

### 4. **JWT with JTI (JWT ID)**

**What is JTI?**
- `jti` = "JWT ID" (unique identifier for each token)
- Every token gets a UUID4 (e.g., "a3f2d8c4-1234-5678-...")
- Makes every token unique, even with identical data

**Why JTI?**

1. **Token uniqueness**: Even tokens created at same second are different
   ```python
   token1 = create_access_token({"user_id": 1})  # jti: abc-123
   token2 = create_access_token({"user_id": 1})  # jti: def-456
   # Different tokens!
   ```

2. **Token revocation** (future feature with Redis):
   ```python
   # Store JTI in Redis when token is created
   redis.setex(f"jti:{jti}", 900, "valid")  # 900 seconds = 15 min

   # On logout, revoke token
   redis.delete(f"jti:{jti}")

   # On validation, check if revoked
   if not redis.exists(f"jti:{jti}"):
       raise TokenRevokedError()
   ```

3. **Security**: Prevents replay attacks and enables token tracking

**Current implementation:**
```python
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({
        "exp": expire_time,
        "iat": datetime.utcnow(),
        "type": "access",
        "jti": str(uuid.uuid4()),  # ← Unique ID
    })
    return jwt.encode(to_encode, SECRET_KEY)
```

### 5. **Password Flow**

**Registration:**
```
User enters: "MyPassword123!"
    ↓
hash_password() → "$2b$12$abc..." (60 chars, bcrypt)
    ↓
Save to database: hashed_password column
    ↓
NEVER store plain password!
```

**Login:**
```
User enters: "MyPassword123!"
    ↓
Get hashed_password from database: "$2b$12$abc..."
    ↓
verify_password(plain, hashed) → True/False
    ↓
If True: Generate tokens
If False: Raise AuthenticationError
```

### 6. **Tuple Returns**

**Why return tuples?**
```python
user, tokens = await register_user(db, user_data)
# vs
result = await register_user(db, user_data)
user = result.user
tokens = result.tokens
```

**Benefits:**
- **Simple**: No need for custom result classes
- **Clear**: Explicit unpacking shows what you get
- **Pythonic**: Common pattern in Python

**When tuple is good:**
- 2-3 related values
- Clear meaning from context
- Function name makes it obvious

**When to use a class instead:**
- Many return values (4+)
- Need to add fields later
- Values aren't always related

---

## Production Best Practices

### 1. **Error Messages**

**Security consideration:**
```python
# Good (doesn't reveal if email exists):
except UserNotFoundError:
    raise HTTPException(401, "Invalid credentials")
except AuthenticationError:
    raise HTTPException(401, "Invalid credentials")

# Bad (reveals if email is registered):
except UserNotFoundError:
    raise HTTPException(404, "Email not found")  # ← Attackers learn this!
except AuthenticationError:
    raise HTTPException(401, "Wrong password")
```

For registration, it's OK to say "email already exists" because users need to know.

### 2. **Database Sessions**

**Pattern we use:**
```python
async with AsyncSessionLocal() as db:
    try:
        user, tokens = await register_user(db, user_data)
        # If no errors, changes are committed
    except Exception:
        # If error, changes are rolled back automatically

# Session closes automatically after `with` block
```

**Why this works:**
- Automatic cleanup (no leaked connections)
- Automatic rollback on errors
- Clear scope (session lifetime is obvious)

### 3. **Token Generation Timing**

**We generate tokens immediately after registration/login:**
```python
# After creating user or verifying login:
token_data = {"user_id": user.id, "email": user.email}
access_token = create_access_token(token_data)
refresh_token = create_refresh_token(token_data)
```

**Why include email in token?**
- Fast user info without database lookup
- Useful for logging/debugging
- No sensitive data (email is not secret)

**Don't include:**
- Passwords (obviously!)
- Sensitive personal data
- Data that changes often (use user_id to look up fresh data)

### 4. **Checking User Status**

**Always check is_active:**
```python
if not user.is_active:
    raise AuthenticationError("User account is inactive")
```

**This allows:**
- Banning users without deleting data
- Temporary suspensions
- Account recovery flows

---

## Test Results

All 8 tests passed! ✅

**Test 1: User Registration**
- Creates user with ID, email, hashed password
- Sets is_active=True, email_verified=False, is_admin=False
- Generates access + refresh tokens
- Password is hashed (60 chars, bcrypt)

**Test 2: Duplicate Email**
- First registration succeeds
- Second with same email raises UserAlreadyExistsError

**Test 3: User Login**
- Finds user by email
- Verifies password
- Returns user + tokens

**Test 4: Wrong Password**
- Raises AuthenticationError
- Doesn't reveal if email exists

**Test 5: Non-Existent User**
- Raises UserNotFoundError
- Graceful handling

**Test 6: Token Refresh**
- Generates new access token
- Token is different (unique JTI)
- Contains correct user_id

**Test 7: Get User by ID**
- Finds existing user
- Returns None for non-existent ID

**Test 8: Get User by Email**
- Finds existing user
- Returns None for non-existent email

---

## What We Learned from Questions

### Q: "If we don't write email_verified=False, default it'll be false?"

**A: Yes!** When you set `default=False` in the model:
```python
email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
```

You DON'T need to pass it when creating:
```python
# This works (email_verified defaults to False):
user = User(email="test@example.com", hashed_password="...")

# This also works (explicit):
user = User(email="test@example.com", email_verified=False, ...)
```

**Defaults are applied:**
- By SQLAlchemy when creating the object
- By the database when inserting the row
- Both levels ensure the default is set

### Q: "Where are we adding JTI?"

**A: In the JWT token creation!** JTI is added to the token payload:
```python
to_encode.update({
    "jti": str(uuid.uuid4()),  # Unique ID for this specific token
})
```

**This makes every token unique**, even if created with same data at same time.

**Future use:** When we add Redis, JTI enables token revocation (logout).

### Q: "Do websearch for production grade JWT"

**A: Done!** Key production practices we implemented:
1. **JTI for uniqueness** - Every token gets UUID4
2. **Token types** - Distinguish access vs refresh
3. **Expiration times** - Short access (15 min), long refresh (30 days)
4. **Standard claims** - exp, iat, jti, type
5. **Preparation for revocation** - JTI ready for Redis blocklist

---

## Common Patterns

### Pattern 1: Try-Except in Services

```python
async def register_user(db, user_data):
    # Check if user exists
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise UserAlreadyExistsError(f"User with email {user_data.email} already exists")

    # Continue with registration...
```

**Caller handles exception:**
```python
try:
    user, tokens = await register_user(db, user_data)
    return success_response(user, tokens)
except UserAlreadyExistsError as e:
    return error_response(str(e), status_code=400)
```

### Pattern 2: SQLAlchemy Query → One or None

```python
result = await db.execute(select(User).where(User.email == email))
user = result.scalar_one_or_none()  # Returns User or None

if user:
    # User exists
else:
    # User doesn't exist
```

**Never use:**
```python
user = result.scalar_one()  # Raises exception if not found!
```

### Pattern 3: Refresh Pattern

```python
db.add(new_user)
await db.commit()
await db.refresh(new_user)  # ← Gets auto-generated ID and timestamps

# Now new_user.id is populated!
```

---

## Next Steps

Now that we have the business logic layer, we can build:

**Step 7: API Endpoints (Routes)**
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get tokens
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user info

**Step 8: Authentication Dependency**
- Create `get_current_user()` dependency
- Extract and validate JWT from Authorization header
- Use in protected endpoints

**Step 9: Protected Routes**
- Example: `GET /users/me` (requires authentication)
- Example: `PUT /users/me` (update profile)
- Show how to use `current_user: User = Depends(get_current_user)`

---

## Summary

**What we accomplished:**
- ✅ Pydantic schemas for validation
- ✅ Service layer with business logic
- ✅ User registration with password hashing
- ✅ User login with credential verification
- ✅ Token generation (with JTI for uniqueness)
- ✅ Token refresh functionality
- ✅ User lookup functions
- ✅ Custom exceptions for clear error handling
- ✅ Comprehensive test coverage

**Key takeaways:**
1. Service layer keeps business logic separate from HTTP handling
2. Pydantic schemas provide automatic validation
3. Custom exceptions make error handling clear
4. JTI makes tokens unique and enables future revocation
5. Always check user.is_active before allowing actions
6. Never store plain passwords - always hash with bcrypt
7. Return both user and tokens for convenience

**Ready for next step:**
We have the complete business logic! Now we can create API endpoints that use these service functions to handle HTTP requests.
