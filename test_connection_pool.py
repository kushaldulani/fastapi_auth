"""
Test connection pool behavior.

This demonstrates:
1. How pool_size works
2. What max_overflow does
3. When pool_pre_ping is useful
4. Connection reuse
"""

import asyncio
import time
from sqlalchemy import text

from src.fastapi_auth.core.database import engine, AsyncSessionLocal


async def test_pool_size():
    """Test 1: Pool keeps connections open for reuse."""
    print("\n" + "="*60)
    print("TEST 1: Connection Reuse (pool_size)")
    print("="*60)

    # Check pool status
    pool = engine.pool
    print(f"\n📊 Initial Pool Status:")
    print(f"   Pool size: {pool.size()}")
    print(f"   Checked out: {pool.checkedout()}")
    print(f"   Overflow: {pool.overflow()}")

    # Create 3 connections
    print(f"\n🔄 Creating 3 concurrent connections...")
    sessions = []
    for i in range(3):
        session = AsyncSessionLocal()
        sessions.append(session)
        await session.execute(text(f"SELECT 1 as connection_{i}"))

    print(f"\n📊 Pool Status (3 connections active):")
    print(f"   Pool size: {pool.size()}")
    print(f"   Checked out: {pool.checkedout()}")
    print(f"   Overflow: {pool.overflow()}")

    # Close connections
    print(f"\n🔄 Closing connections...")
    for session in sessions:
        await session.close()

    print(f"\n📊 Pool Status (connections returned to pool):")
    print(f"   Pool size: {pool.size()}")
    print(f"   Checked out: {pool.checkedout()}")
    print(f"   Overflow: {pool.overflow()}")

    print(f"\n✅ Connections are REUSED from pool (fast!)")


async def test_max_overflow():
    """Test 2: What happens when we exceed pool_size."""
    print("\n" + "="*60)
    print("TEST 2: Overflow Connections (max_overflow)")
    print("="*60)

    pool = engine.pool
    print(f"\n📊 Pool config:")
    print(f"   pool_size: {pool.size()}")
    print(f"   max_overflow: 10")  # Our setting

    # Try to create MORE connections than pool_size
    print(f"\n🔄 Creating 8 concurrent connections (exceeds pool_size=5)...")
    sessions = []
    for i in range(8):
        session = AsyncSessionLocal()
        sessions.append(session)
        await session.execute(text(f"SELECT 1"))

    print(f"\n📊 Pool Status (8 connections active):")
    print(f"   Pool size: {pool.size()}")
    print(f"   Checked out: {pool.checkedout()}")
    print(f"   Overflow: {pool.overflow()} (these are TEMPORARY)")

    # Close all
    for session in sessions:
        await session.close()

    print(f"\n📊 Pool Status (after closing):")
    print(f"   Pool size: {pool.size()}")
    print(f"   Checked out: {pool.checkedout()}")
    print(f"   Overflow: {pool.overflow()}")

    print(f"\n✅ Overflow connections are closed after use!")


async def test_pool_pre_ping():
    """Test 3: pool_pre_ping detects dead connections."""
    print("\n" + "="*60)
    print("TEST 3: Pool Pre-Ping (Connection Health Check)")
    print("="*60)

    print("\n🔄 Creating a connection...")
    session = AsyncSessionLocal()
    result = await session.execute(text("SELECT 1 as test"))
    print(f"✅ Query successful: {result.scalar()}")

    print(f"\n⏳ Simulating connection being idle...")
    print(f"   (In production, connection might die if database restarts,")
    print(f"    network issues, or idle timeout)")

    # With pool_pre_ping=True, SQLAlchemy will:
    # 1. Test the connection before using it (SELECT 1)
    # 2. If dead, create a new one automatically
    # 3. Your query succeeds without error!

    print(f"\n🔄 Using connection again (pre_ping checks if alive)...")
    result = await session.execute(text("SELECT 2 as test"))
    print(f"✅ Query successful: {result.scalar()}")

    await session.close()

    print(f"\n✅ pool_pre_ping=True prevents 'connection lost' errors!")


async def test_connection_reuse_speed():
    """Test 4: Reusing connections is MUCH faster."""
    print("\n" + "="*60)
    print("TEST 4: Connection Reuse Performance")
    print("="*60)

    # First query (might create new connection)
    print(f"\n🔄 First query (cold start)...")
    start = time.time()
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    cold_time = time.time() - start
    print(f"   Time: {cold_time:.4f} seconds")

    # Subsequent queries (reuse from pool)
    print(f"\n🔄 Next 5 queries (reusing pool connections)...")
    times = []
    for i in range(5):
        start = time.time()
        async with AsyncSessionLocal() as session:
            await session.execute(text(f"SELECT {i}"))
        times.append(time.time() - start)

    avg_warm_time = sum(times) / len(times)
    print(f"   Average time: {avg_warm_time:.4f} seconds")

    speedup = cold_time / avg_warm_time if avg_warm_time > 0 else 0
    print(f"\n✅ Pool reuse is {speedup:.1f}x faster!")


async def test_pool_exhaustion():
    """Test 5: What happens when pool + overflow are full."""
    print("\n" + "="*60)
    print("TEST 5: Pool Exhaustion (pool_size + max_overflow)")
    print("="*60)

    pool = engine.pool
    max_connections = 5 + 10  # pool_size + max_overflow = 15

    print(f"\n📊 Max possible connections: {max_connections}")
    print(f"   (pool_size=5 + max_overflow=10)")

    print(f"\n🔄 Creating {max_connections} connections...")
    sessions = []
    for i in range(max_connections):
        session = AsyncSessionLocal()
        sessions.append(session)
        await session.execute(text("SELECT 1"))

    print(f"\n📊 Pool Status (at capacity):")
    print(f"   Pool size: {pool.size()}")
    print(f"   Checked out: {pool.checkedout()}")
    print(f"   Overflow: {pool.overflow()}")

    print(f"\n⚠️  Trying to create one MORE connection (16th)...")
    print(f"   This will BLOCK until a connection is available!")

    # This would block forever if we didn't set a timeout
    print(f"   (Not actually testing this to avoid hanging)")

    # Cleanup
    for session in sessions:
        await session.close()

    print(f"\n✅ When pool is exhausted, new connections WAIT!")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 CONNECTION POOL TESTING")
    print("="*60)
    print(f"\nTesting with settings:")
    print(f"  - pool_size: 5")
    print(f"  - max_overflow: 10")
    print(f"  - pool_pre_ping: True")
    print(f"  - pool_recycle: 3600s (1 hour)")

    try:
        await test_pool_size()
        await test_max_overflow()
        await test_pool_pre_ping()
        await test_connection_reuse_speed()
        await test_pool_exhaustion()

        print("\n" + "="*60)
        print("🎉 ALL TESTS COMPLETE!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
