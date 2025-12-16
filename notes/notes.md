🎓 Step 1: Understanding the Project Setup
What We're Building
We're creating a reusable authentication library that any FastAPI app can plug into. Think of it like installing pip install fastapi-auth and getting login/logout/permissions out of the box.
Why This Structure?
fastapi_auth/
├── pyproject.toml          # Modern Python packaging (replaces setup.py)
├── src/
│   └── fastapi_auth/       # Our package (importable as: from fastapi_auth import ...)
└── tests/                  # Tests live outside src/ (best practice)
Why src/ layout?
Prevents accidentally importing uninstalled code during development
Forces you to test the installed version, not local files
Industry standard for Python packages
Dependencies We'll Use (and Why)
Let me explain each dependency:
Core Framework
fastapi = "^0.115.0"        # Web framework (you know this)
uvicorn = "^0.32.0"         # ASGI server to run FastAPI
pydantic = "^2.0"           # Data validation (FastAPI uses this)
pydantic-settings = "^2.0"  # For environment-based config (.env files)
Database
sqlalchemy = "^2.0"         # ORM (Object-Relational Mapping)
asyncpg = "^0.30.0"         # PostgreSQL driver (async version)
alembic = "^1.13"           # Database migrations (tracks schema changes)
Why async? FastAPI is async by default. Using async database operations means you won't block other requests while waiting for DB queries. What's an ORM? Instead of writing SQL:
INSERT INTO users (email, password) VALUES ('user@example.com', 'hashed...');
You write Python:
user = User(email="user@example.com", password="hashed...")
db.add(user)
await db.commit()
What's Alembic? It tracks database schema changes:
Version 1: Create users table
Version 2: Add email_verified column
Version 3: Create user_sessions table
You can upgrade/downgrade database versions easily.
Security
passlib[bcrypt] = "^1.7.4"            # Password hashing
python-jose[cryptography] = "^3.3.0"  # JWT token creation/validation
Why passlib + bcrypt?
Bcrypt is slow on purpose (prevents brute-force attacks)
Has built-in salt (random data added to passwords)
Industry standard
Why python-jose?
Creates/validates JWT tokens
Handles signing (so tokens can't be tampered with)
Testing
pytest = "^8.0"             # Test framework
pytest-asyncio = "^0.24"    # Support for async tests
httpx = "^0.27"             # Async HTTP client (for testing API endpoints)
The Plan for Step 1
We'll:
✅ Create the folder structure
✅ Set up pyproject.toml (defines our package + dependencies)
✅ Install dependencies with uv
✅ Verify everything installed correctly
🤔 Quick Concept Check
Before we proceed, let me make sure we're aligned: Question 1: Why are we using asyncpg instead of regular psycopg2? <details> <summary>Answer</summary> Because FastAPI is async. While one request waits for database, another request can be processed. Synchronous drivers would block the entire server. </details> Question 2: What's the difference between fastapi and uvicorn? <details> <summary>Answer</summary> - `fastapi` = Framework (defines routes, handles requests) - `uvicorn` = Server (actually runs the app, handles networking) </details> Question 3: Why separate src/fastapi_auth/ from the root? <details> <summary>Answer</summary> So tests import the *installed* package, not local files. Catches import issues early. </details>
---

## Step 2: Configuration ✅

**What we did:**
- Created `.env.example` (template) and `.env` (actual secrets)
- Created `src/fastapi_auth/core/config.py` (reads settings)
- Generated a secure SECRET_KEY with `openssl rand -hex 32`
- Tested config with a simple script

**Code we wrote (super simple!):**
```python
# src/fastapi_auth/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str           # Required
    SECRET_KEY: str             # Required
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    DEBUG: bool = False

    class Config:
        env_file = ".env"

settings = Settings()  # One global instance
```

**That's it! Only 15 lines.**

### Key learnings:

**Why environment variables?**
- Dev needs: `DATABASE_URL=localhost`, `DEBUG=true`
- Production needs: `DATABASE_URL=prod-server`, `DEBUG=false`
- Same code, different config!

**How it works:**
1. Pydantic looks for `.env` file
2. Reads `DATABASE_URL=postgresql://...`
3. Converts to correct type (str → str, "15" → int, "true" → bool)
4. Validates required fields (crashes if SECRET_KEY missing)

**Usage in other files:**
```python
from fastapi_auth.core.config import settings
print(settings.DATABASE_URL)  # Easy!
```

**Why this is simple:**
- ✅ One line import, one line usage
- ✅ Type-safe (autocomplete works)
- ✅ No manual file reading/parsing
- ✅ Validated automatically

---

## Questions I Can Now Answer:

**Q: Why not just hardcode DATABASE_URL?**
A: Different environments need different values. Also, secrets shouldn't be in git.

**Q: What does BaseSettings do?**
A: Reads `.env`, validates types, gives autocomplete.

**Q: What's SECRET_KEY for?**
A: Signing JWT tokens (like a password for tokens). Must be random and secret.

**Q: Why .env.example AND .env?**
A: `.env.example` = template (goes in git), `.env` = real secrets (stays local)

**Q: What if .env has a value that's also in the Settings class with a default?**
A: `.env` value ALWAYS wins. Default is only used if .env doesn't have it.

---

## Step 3: Database Connection ✅

**What we did:**
- Created `docker-compose.yml` (runs PostgreSQL in Docker)
- Created `src/fastapi_auth/core/database.py` (≈70 lines)
- Fixed port conflict (local PostgreSQL on 5432, Docker on 5433)
- Tested connection successfully

**Code we wrote (super simple!):**
```python
# src/fastapi_auth/core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# 1. Create engine (connection pool)
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

# 2. Create session factory
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)

# 3. Base class for all models
Base = declarative_base()

# 4. Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session  # Give to route, auto-cleanup after
```

**That's the core! Everything else is helpers.**

### Key learnings:

**Docker Compose commands:**
```bash
docker-compose up -d      # Start PostgreSQL (background)
docker-compose down       # Stop and remove
docker-compose ps         # Check status
docker-compose logs -f    # View logs
```

**Persistent storage:**
- Volume `postgres_data` stores data
- Data survives container restarts
- Managed by Docker automatically

**Simple mental model:**
- **Engine** = Phone book (connection pool, create once)
- **Session** = Phone call (one conversation with DB)
- **get_db()** = Automatic cleanup (closes session after use)
- **Base** = Parent class for all our models (User, Session, etc)

**Async SQLAlchemy:**
```python
# With async, while waiting for DB:
async with AsyncSessionLocal() as session:
    result = await session.execute(query)  # Other requests can run here!
```

**Why async?**
- Request A waits for DB → Server handles Request B
- Without async → Server blocked, Request B has to wait

**Port conflict fix:**
- Local PostgreSQL: `localhost:5432`
- Docker PostgreSQL: `localhost:5433`
- Both can run at the same time!

---

## Questions I Can Now Answer:

**Q: Why Docker Compose instead of installing PostgreSQL?**
A: Same environment for everyone, easy start/stop, no system-wide installation.

**Q: What's a "volume" in Docker?**
A: Persistent storage that survives container restarts. Like a virtual hard drive.

**Q: Why `async with`?**
A: Creates resource, uses it, automatically cleans up. No manual session.close() needed.

**Q: What's the difference between engine and session?**
A: Engine = connection pool (create once). Session = individual conversation (one per request).

**Q: Why `Base = declarative_base()`?**
A: All our models inherit from this. SQLAlchemy uses it to track models and create tables.

**Q: What does `yield session` do in get_db()?**
A: Gives session to route, pauses, waits for route to finish, then continues to cleanup.