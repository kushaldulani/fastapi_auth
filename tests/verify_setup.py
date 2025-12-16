#!/usr/bin/env python3
"""
Verification script to check all dependencies are installed correctly.
This helps us catch any installation issues early.
"""

def verify_imports():
    """Test importing all critical dependencies."""
    print("🔍 Verifying dependencies...\n")

    tests = []

    # Test 1: FastAPI
    try:
        import fastapi
        print(f"✅ FastAPI {fastapi.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"❌ FastAPI: {e}")
        tests.append(False)

    # Test 2: SQLAlchemy
    try:
        import sqlalchemy
        print(f"✅ SQLAlchemy {sqlalchemy.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"❌ SQLAlchemy: {e}")
        tests.append(False)

    # Test 3: Asyncpg
    try:
        import asyncpg
        print(f"✅ Asyncpg {asyncpg.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"❌ Asyncpg: {e}")
        tests.append(False)

    # Test 4: Pydantic
    try:
        import pydantic
        print(f"✅ Pydantic {pydantic.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"❌ Pydantic: {e}")
        tests.append(False)

    # Test 5: Passlib (password hashing)
    try:
        from passlib.context import CryptContext
        # Test bcrypt is available (use shorter test password to avoid bcrypt limitations)
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        test_hash = pwd_context.hash("test123")
        verified = pwd_context.verify("test123", test_hash)
        if verified:
            print(f"✅ Passlib with bcrypt (hash & verify working)")
        else:
            print(f"⚠️  Passlib: hash created but verification failed")
        tests.append(verified)
    except Exception as e:
        print(f"❌ Passlib: {e}")
        tests.append(False)

    # Test 6: Python-JOSE (JWT)
    try:
        from jose import jwt
        # Test JWT creation
        token = jwt.encode({"test": "data"}, "secret", algorithm="HS256")
        print(f"✅ Python-JOSE (JWT token: {token[:30]}...)")
        tests.append(True)
    except ImportError as e:
        print(f"❌ Python-JOSE: {e}")
        tests.append(False)

    # Test 7: Pytest
    try:
        import pytest
        print(f"✅ Pytest {pytest.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"❌ Pytest: {e}")
        tests.append(False)

    # Test 8: Alembic
    try:
        import alembic
        print(f"✅ Alembic {alembic.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"❌ Alembic: {e}")
        tests.append(False)

    # Summary
    print("\n" + "="*50)
    passed = sum(tests)
    total = len(tests)

    if passed == total:
        print(f"🎉 All {total} dependency checks passed!")
        print("✨ Your environment is ready for development!")
        return True
    else:
        print(f"⚠️  {passed}/{total} checks passed, {total - passed} failed")
        print("Please fix the failed imports before continuing.")
        return False


if __name__ == "__main__":
    import sys
    success = verify_imports()
    sys.exit(0 if success else 1)
