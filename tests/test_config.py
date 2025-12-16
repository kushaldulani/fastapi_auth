"""
Simple test to verify our config is working.
Run this with: uv run python test_config.py
"""

from fastapi_auth.core.config import settings

print("🔧 Testing Configuration...\n")

# Test 1: Can we read DATABASE_URL?
print(f"✅ DATABASE_URL: {settings.DATABASE_URL}")

# Test 2: Can we read SECRET_KEY?
print(f"✅ SECRET_KEY: {settings.SECRET_KEY[:10]}... (hidden for security)")

# Test 3: Are integers parsed correctly?
print(f"✅ ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} (type: {type(settings.ACCESS_TOKEN_EXPIRE_MINUTES).__name__})")

# Test 4: Are booleans parsed correctly?
print(f"✅ DEBUG: {settings.DEBUG} (type: {type(settings.DEBUG).__name__})")

print("\n🎉 Config is working! All settings loaded successfully!")
