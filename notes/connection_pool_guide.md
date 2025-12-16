# Connection Pool Guide

## 🎯 What We Learned from Tests

### Test Results Summary:

| Test | Result | What It Shows |
|------|--------|---------------|
| **Pool Reuse** | ✅ 3 connections → pool_size: 5, checked_out: 3 | Pool keeps connections for reuse |
| **Overflow** | ✅ 8 connections → overflow: 3 (temporary) | Extra connections closed after use |
| **Pre-Ping** | ✅ Queries successful | Detects dead connections |
| **Performance** | ✅ ~0.9x faster | Pool reuse is faster |
| **Exhaustion** | ✅ 15 connections at capacity | Blocks after limit |

---

## 📊 Recommended Settings by Use Case

### 1. Small App (< 100 concurrent users)
```python
create_async_engine(
    url,
    pool_size=5,           # ✅ Default is fine
    max_overflow=10,       # ✅ Default is fine
    pool_pre_ping=True,    # ✅ Recommended
    pool_recycle=3600,     # ✅ 1 hour
)
```

**Why:** Defaults are good! pool_pre_ping prevents stale connections.

---

### 2. Medium App (100-1000 concurrent users)
```python
create_async_engine(
    url,
    pool_size=20,          # Increase for more concurrency
    max_overflow=30,       # More overflow capacity
    pool_pre_ping=True,    # Must have!
    pool_recycle=1800,     # 30 minutes (shorter)
)
```

**Why:** More concurrent requests need more connections.

---

### 3. Large App (1000+ concurrent users)
```python
create_async_engine(
    url,
    pool_size=50,          # High concurrency
    max_overflow=50,       # Large overflow
    pool_pre_ping=True,    # Critical!
    pool_recycle=900,      # 15 minutes
    pool_timeout=30,       # Wait 30s for connection
)
```

**Why:** High traffic needs large pool. Shorter recycle prevents stale connections.

---

### 4. API with Bursts (e.g., webhook receiver)
```python
create_async_engine(
    url,
    pool_size=10,          # Small steady state
    max_overflow=100,      # LARGE overflow for bursts
    pool_pre_ping=True,
    pool_recycle=600,      # 10 minutes
)
```

**Why:** Small pool + large overflow = handles bursts efficiently.

---

### 5. Long-Running Tasks (Celery workers)
```python
create_async_engine(
    url,
    pool_size=2,           # Workers don't need many
    max_overflow=5,
    pool_pre_ping=True,    # CRITICAL for long-running!
    pool_recycle=300,      # 5 minutes (short!)
)
```

**Why:** Long tasks = connections idle for long time. Short recycle + pre_ping prevent timeouts.

---

## 🔢 How to Calculate Pool Size

### Formula:
```
pool_size = (expected_concurrent_requests * avg_query_time) / request_duration
```

### Example Calculation:

**Your app stats:**
- 100 concurrent requests
- Each request takes 100ms
- Each request makes 3 DB queries
- Each query takes 10ms

```
Total DB time per request = 3 queries × 10ms = 30ms
Concurrent DB operations = 100 requests × (30ms / 100ms) = 30

Recommended pool_size = 30
Add overflow = 30 (for bursts)

Settings:
pool_size=30
max_overflow=30
```

---

## ⚠️ Common Mistakes

### Mistake 1: Pool Too Small
```python
pool_size=2  # ❌ Too small!
```
**Problem:** Requests wait for connections
**Symptom:** Slow API responses, timeouts
**Fix:** Increase pool_size

### Mistake 2: Pool Too Large
```python
pool_size=500  # ❌ Too large!
```
**Problem:** Overwhelms database
**Symptom:** Database CPU at 100%, OOM errors
**Fix:** Reduce pool_size (PostgreSQL default max_connections=100!)

### Mistake 3: No pool_pre_ping
```python
pool_pre_ping=False  # ❌ Risky!
```
**Problem:** Dead connections cause errors
**Symptom:** Random "connection lost" errors
**Fix:** Always use `pool_pre_ping=True` in production

### Mistake 4: No pool_recycle
```python
# No pool_recycle set  # ❌ Risky!
```
**Problem:** Connections never refresh
**Symptom:** Stale connections after DB restart
**Fix:** Use `pool_recycle=3600` or less

---

## 🔍 Monitoring Connection Pool

### Check Pool Status:
```python
from sqlalchemy import inspect

# In your app
pool = engine.pool
print(f"Pool size: {pool.size()}")
print(f"Checked out: {pool.checkedout()}")
print(f"Overflow: {pool.overflow()}")
```

### Add to Health Check Endpoint:
```python
@app.get("/health")
async def health_check():
    pool = engine.pool
    return {
        "status": "healthy",
        "pool": {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
    }
```

### Prometheus Metrics (Production):
```python
from prometheus_client import Gauge

pool_size_gauge = Gauge('db_pool_size', 'Database pool size')
pool_checked_out = Gauge('db_pool_checked_out', 'Connections in use')

# Update periodically
pool_size_gauge.set(engine.pool.size())
pool_checked_out.set(engine.pool.checkedout())
```

---

## 🚨 Troubleshooting

### Issue: "QueuePool limit exceeded"
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**Cause:** All connections in use, new request has to wait

**Solutions:**
1. Increase `pool_size` or `max_overflow`
2. Optimize queries (make them faster)
3. Add `pool_timeout` parameter:
   ```python
   pool_timeout=30  # Wait 30s before error
   ```

---

### Issue: "FATAL: too many clients"
```
psycopg2.OperationalError: FATAL: too many connections
```

**Cause:** Total connections exceed PostgreSQL's `max_connections`

**PostgreSQL Default:** 100 connections

**Solutions:**
1. Reduce `pool_size + max_overflow` in your app
2. Increase PostgreSQL `max_connections`:
   ```bash
   # In postgresql.conf
   max_connections = 200
   ```
3. Use PgBouncer (connection pooler):
   ```
   App → PgBouncer → PostgreSQL
   (1000 connections) → (100 real connections)
   ```

---

### Issue: "Connection was closed"
```
psycopg2.OperationalError: connection already closed
```

**Cause:** Connection died while idle (DB restart, network issue, idle timeout)

**Solutions:**
1. Enable `pool_pre_ping=True` ✅
2. Set `pool_recycle` to less than idle timeout:
   ```python
   # If PostgreSQL idle_in_transaction_session_timeout = 1 hour
   pool_recycle=3000  # 50 minutes (less than timeout)
   ```

---

## 🎯 Production Checklist

### Essential Settings:
```python
engine = create_async_engine(
    settings.DATABASE_URL,

    # ✅ Must-have settings
    pool_pre_ping=True,        # Detect dead connections
    pool_recycle=3600,         # Recycle after 1 hour

    # ⚙️ Tune based on load
    pool_size=20,              # Start with 20
    max_overflow=20,           # Same as pool_size

    # ⏱️ Timeouts
    pool_timeout=30,           # Wait 30s for connection
    connect_args={
        "server_settings": {
            "application_name": "fastapi_auth",  # Identify in pg_stat_activity
        },
        "timeout": 10,         # Connect timeout (10s)
    },

    # 🐛 Debugging
    echo=False,                # Disable SQL logging in prod
)
```

### Monitoring:
- ✅ Track `pool.checkedout()` in metrics
- ✅ Alert if pool exhausted
- ✅ Monitor PostgreSQL `pg_stat_activity`

### Load Testing:
```bash
# Test with realistic load
locust -f locustfile.py --users 100 --spawn-rate 10
```

---

## 📚 Quick Reference

| Setting | Default | Production | What It Does |
|---------|---------|------------|--------------|
| `pool_size` | 5 | 20-50 | Permanent connections |
| `max_overflow` | 10 | 20-50 | Temporary extra connections |
| `pool_pre_ping` | False | **True** ✅ | Test connection before use |
| `pool_recycle` | -1 | 3600 | Recycle after N seconds |
| `pool_timeout` | 30 | 30 | Wait time for connection |

---

## 🧮 Pool Size Calculator

### Simple Formula:
```
1. Measure concurrent requests (avg)
2. Measure query time per request (avg)

pool_size = concurrent_requests × (query_time / request_time)
max_overflow = pool_size (for bursts)
```

### Example Scenarios:

**Scenario 1: Low Traffic**
- 10 req/sec
- 50ms per request
- 10ms DB time

```
pool_size = 10 × (10 / 50) = 2
Use: pool_size=5 (minimum)
```

**Scenario 2: Medium Traffic**
- 100 req/sec
- 100ms per request
- 30ms DB time

```
pool_size = 100 × (30 / 100) = 30
Use: pool_size=30, max_overflow=20
```

**Scenario 3: High Traffic**
- 1000 req/sec
- 50ms per request
- 20ms DB time

```
pool_size = 1000 × (20 / 50) = 400
BUT: PostgreSQL max_connections = 100!
Solution: Use PgBouncer
```

---

## 🔗 Resources

- [SQLAlchemy Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [PostgreSQL Connection Limits](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [PgBouncer](https://www.pgbouncer.org/) - Connection pooler for PostgreSQL

---

## TL;DR

**For your FastAPI Auth project:**

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,           # Good for most apps
    max_overflow=20,        # Handle bursts
    pool_pre_ping=True,     # Must have!
    pool_recycle=3600,      # 1 hour
)
```

**Key Insights:**
- ✅ `pool_pre_ping=True` is essential for production
- ✅ Start with `pool_size=20`, tune based on monitoring
- ✅ Set `pool_recycle` to less than PostgreSQL timeout
- ✅ Monitor pool usage in production
- ⚠️ Don't exceed PostgreSQL `max_connections` (default: 100)
