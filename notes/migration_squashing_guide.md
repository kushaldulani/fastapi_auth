# Migration Squashing Guide

## Why Squash Migrations?

After months/years of development, you might have:
- 100+ migration files
- Slow `alembic upgrade` from scratch
- Hard to understand project history

**Solution:** Combine old migrations into a single "baseline" migration.

---

## When to Squash:

✅ **Good times:**
- After a major release (v1.0, v2.0)
- When onboarding new team members (simpler history)
- Before deploying to new environments
- When you have 100+ migrations

❌ **Bad times:**
- When databases are in production (risky!)
- Mid-development (confusing for team)
- When you need to rollback old changes

---

## How to Squash Migrations:

### Step 1: Export Current Schema

```bash
# Generate SQL for current database state
alembic upgrade head --sql > schema_baseline.sql

# OR use pg_dump for PostgreSQL
docker exec fastapi_auth_db pg_dump -U postgres \
  --schema-only fastapi_auth > schema_baseline.sql
```

### Step 2: Backup Everything

```bash
# Backup migrations
cp -r migrations/versions migrations/versions.backup

# Backup database
docker exec fastapi_auth_db pg_dump -U postgres \
  fastapi_auth > backup_$(date +%Y%m%d).sql
```

### Step 3: Create Baseline Migration

```bash
# Delete old migrations (keep backup!)
rm migrations/versions/*.py

# Clear alembic version
psql -U postgres -d fastapi_auth -c "DELETE FROM alembic_version;"

# Create new baseline from current models
alembic revision --autogenerate -m "baseline schema v1.0"

# This creates ONE migration with ALL current tables
```

### Step 4: Test on Fresh Database

```bash
# Create test database
createdb fastapi_auth_test

# Apply baseline migration
DATABASE_URL=postgresql://...fastapi_auth_test \
  alembic upgrade head

# Verify schema matches production
pg_dump --schema-only fastapi_auth > prod_schema.sql
pg_dump --schema-only fastapi_auth_test > test_schema.sql
diff prod_schema.sql test_schema.sql
```

### Step 5: Update Production Databases

```bash
# Mark existing production DB as "already migrated"
# DO NOT run `alembic upgrade` on prod!
alembic stamp head

# Future deploys will use the new baseline
```

---

## Example: Squashing Our Migrations

**Before:**
```
migrations/versions/
├── 001_create_users_table.py
├── 002_add_email_verified.py
├── 003_add_full_name.py
├── 004_remove_full_name.py
└── ... (100 more files)
```

**After:**
```
migrations/versions/
├── squash_v1_baseline.py  # Single file with all tables
└── 005_new_feature.py     # New migrations continue here
```

**Baseline migration contains:**
```python
def upgrade():
    # Creates ALL tables at once
    op.create_table('users', ...)
    op.create_table('sessions', ...)
    op.create_table('permissions', ...)
    # etc.
```

---

## Strategy for Growing Projects:

### Approach 1: Periodic Squashing
```
Squash every major version:
├── v1.0: 1 baseline + 0 migrations
├── v1.x: 1 baseline + 50 migrations
├── v2.0: 1 new baseline (squash v1.x)
├── v2.x: 1 baseline + 30 migrations
└── v3.0: 1 new baseline (squash v2.x)
```

### Approach 2: Keep Recent, Archive Old
```
migrations/
├── versions/
│   ├── baseline_v2.py          # Latest baseline
│   ├── 2024_01_add_sso.py      # Recent (keep)
│   ├── 2024_02_add_mfa.py      # Recent (keep)
│   └── ...
└── archived/
    ├── old_migrations_v1.tar.gz  # Archive for reference
    └── README.md                 # How to use if needed
```

### Approach 3: Use Branches
```
git branch archive-pre-v2-migrations
# Delete old migrations from main
git checkout main
# Keep old history in branch if needed
```

---

## Automation Example:

```bash
#!/bin/bash
# squash_migrations.sh

echo "🔄 Starting migration squash..."

# 1. Backup
echo "📦 Creating backups..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp -r migrations/versions $BACKUP_DIR/
pg_dump -U postgres fastapi_auth > $BACKUP_DIR/database.sql

# 2. Count migrations
MIGRATION_COUNT=$(ls migrations/versions/*.py | wc -l)
echo "📊 Found $MIGRATION_COUNT migrations"

if [ $MIGRATION_COUNT -lt 50 ]; then
    echo "⏭️  Less than 50 migrations, skipping squash"
    exit 0
fi

# 3. Create baseline
echo "🏗️  Creating baseline migration..."
rm migrations/versions/*.py
alembic revision --autogenerate -m "baseline_$(date +%Y%m%d)"

echo "✅ Squash complete! Review the new migration before deploying."
```

---

## Pro Tips:

### 1. Document Squash Events
```python
# migrations/versions/baseline_v2_20240101.py
"""
Baseline migration for v2.0

This migration squashes 150 previous migrations from v1.0-v1.9.
Previous migration history archived in: migrations/archived/v1_history.tar.gz

Schema includes:
- Users and authentication
- Multi-tenancy
- RBAC permissions
- Audit logs

Created: 2024-01-01
Previous head: abc123def456
"""
```

### 2. Use Migration Naming Convention
```
migrations/versions/
├── 0001_baseline_v1.py
├── 0050_add_feature.py
├── 0100_baseline_v2.py  # Squashed at migration 100
├── 0150_add_another.py
└── 0200_baseline_v3.py  # Squashed at migration 200
```

### 3. Test Squashed Migrations
```bash
# Always test on fresh database!
docker-compose up -d postgres-test
alembic upgrade head
# Run full test suite
pytest
# Compare schema with production
```

---

## Troubleshooting Squashed Migrations:

### Problem: "Can't locate revision"
```bash
# Old production DB references old migration
ERROR: Can't locate revision 'abc123'

# Solution: Stamp to new baseline
alembic stamp head --purge
```

### Problem: Schema mismatch after squash
```bash
# Baseline doesn't match actual schema

# Solution: Use actual pg_dump
pg_dump --schema-only fastapi_auth > actual_schema.sql
# Manually write migration to match actual state
```

---

## When NOT to Squash:

❌ **Don't squash if:**
1. Multiple devs actively working (confusing!)
2. Need to rollback to old versions
3. Debugging historical issues
4. Can't test on fresh database first

✅ **Alternative: Keep migrations, optimize differently:**
- Use `--sql` flag for faster deploys
- Pre-bake database images
- Snapshot databases at major versions
