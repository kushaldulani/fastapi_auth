"""Test if User model is registered with Base."""

from src.fastapi_auth.models.base import Base
import src.fastapi_auth.models  # noqa: F401

print("Registered tables in Base.metadata:")
for table_name in Base.metadata.tables:
    print(f"  - {table_name}")

if "users" in Base.metadata.tables:
    print("\n✅ User model is registered!")
    users_table = Base.metadata.tables["users"]
    print(f"\nColumns in 'users' table:")
    for column in users_table.columns:
        print(f"  - {column.name}: {column.type}")
else:
    print("\n❌ User model is NOT registered!")
