"""
Simple test to verify database connection works.
Run this with: uv run python test_database.py
"""

import asyncio

from sqlalchemy import text

from src.fastapi_auth.core.database import AsyncSessionLocal, engine


async def test_connection():
    """Test basic database connection."""
    print("🔌 Testing database connection...\n")

    # Test 1: Can we connect?
    try:
        async with engine.begin() as conn:
            # Execute a simple query
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL!")
            print(f"   Version: {version[:50]}...\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

    # Test 2: Can we create a session?
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"✅ Session created successfully!")
            print(f"   Database: {db_name}\n")
    except Exception as e:
        print(f"❌ Session creation failed: {e}")
        return False

    # Test 3: Can we execute a simple query?
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1 + 1 as result"))
            value = result.scalar()
            print(f"✅ Query execution works!")
            print(f"   1 + 1 = {value}\n")
    except Exception as e:
        print(f"❌ Query execution failed: {e}")
        return False

    print("🎉 All database tests passed!")
    print("✨ Your database connection is working perfectly!")
    return True


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_connection())
