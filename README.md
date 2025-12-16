# FastAPI Auth - Complete Production-Ready Structure

## Overview
A modular, pluggable authentication and authorization system for FastAPI applications with multi-tenancy, MFA, OAuth, SSO, and comprehensive security features.

## Project Structure

```
fastapi_auth/
├── pyproject.toml                      # Package configuration (uv/pip)
├── alembic.ini                         # Alembic migration config
├── README.md                           # Package documentation
├── .env.example                        # Environment variables template
├── docker-compose.yml                  # Local development stack (Postgres, Redis)
├── .gitignore
│
├── src/
│   └── fastapi_auth/
│       ├── __init__.py                 # Public API exports
│       │
│       ├── core/                       # Core utilities and configuration
│       │   ├── __init__.py
│       │   ├── config.py               # Pydantic Settings (JWT, DB, email, etc)
│       │   ├── security.py             # Password hashing, JWT creation/validation
│       │   ├── database.py             # SQLAlchemy async engine and session
│       │   ├── exceptions.py           # Custom exceptions (AuthError, PermissionDenied, etc)
│       │   ├── constants.py            # Enums (LoginMethod, MFAType, TokenType, etc)
│       │   ├── audit_logger.py         # Structured security event logging
│       │   ├── password_policy.py      # Configurable password rules (NIST, PCI-DSS)
│       │   └── logging.py              # Structured logging config (JSON, correlation IDs)
│       │
│       ├── models/                     # SQLAlchemy models
│       │   ├── __init__.py
│       │   ├── base.py                 # Base model + mixins (TimestampMixin, TenantMixin)
│       │   ├── user.py                 # User, UserSession
│       │   ├── tenant.py               # Tenant, TenantMembership
│       │   ├── mfa.py                  # MFAMethod, MFABackupCode
│       │   ├── oauth.py                # OAuthConnection, OAuthState
│       │   ├── sso.py                  # SSOProvider, SSOConnection
│       │   ├── authz.py                # Permission, Role, RolePermission, TenantUserRole
│       │   ├── audit_log.py            # AuditLog (who did what, when, where)
│       │   ├── security_event.py       # SecurityEvent (failed logins, lockouts, etc)
│       │   ├── api_key.py              # APIKey (for M2M authentication)
│       │   ├── token_blacklist.py      # TokenBlacklist (revoked tokens)
│       │   └── password_reset.py       # PasswordResetToken (with expiry)
│       │
│       ├── schemas/                    # Pydantic request/response models
│       │   ├── __init__.py
│       │   ├── auth.py                 # RegisterRequest, LoginRequest, TokenResponse
│       │   ├── mfa.py                  # MFASetupRequest, MFAChallengeRequest
│       │   ├── oauth.py                # OAuthCallbackRequest, OAuthUserResponse
│       │   ├── tenant.py               # TenantCreate, MembershipResponse
│       │   ├── authz.py                # RoleCreate, PermissionResponse
│       │   ├── user.py                 # UserResponse, UserUpdateRequest (admin)
│       │   ├── api_key.py              # APIKeyCreate, APIKeyResponse
│       │   └── password.py             # PasswordResetRequest, PasswordResetConfirm
│       │
│       ├── services/                   # Business logic layer
│       │   ├── __init__.py
│       │   ├── auth.py                 # Core authentication (register, login, logout)
│       │   ├── session.py              # Session management (limits, rotation, device tracking)
│       │   ├── mfa.py                  # TOTP, backup codes, SMS (future)
│       │   ├── oauth.py                # OAuth flow (Google, GitHub, etc via authlib)
│       │   ├── sso.py                  # SAML/OIDC enterprise SSO
│       │   ├── tenant.py               # Tenant CRUD operations
│       │   ├── authz.py                # Authorization (RBAC + ABAC)
│       │   ├── password_reset.py       # Password reset flow (tokens, expiry, rate limits)
│       │   ├── email_verification.py   # Email verification flow
│       │   ├── account_lockout.py      # Brute-force protection
│       │   ├── user_management.py      # Admin user operations (deactivate, delete, etc)
│       │   ├── impersonation.py        # Admin "login as user" with audit trail
│       │   ├── api_key_service.py      # API key generation, rotation, revocation
│       │   └── device_management.py    # Device tracking and session management
│       │
│       ├── api/                        # FastAPI routes
│       │   ├── __init__.py
│       │   ├── deps.py                 # Reusable dependencies (get_current_user, get_db, etc)
│       │   ├── auth.py                 # POST /register, /login, /refresh, /logout, GET /me
│       │   ├── mfa.py                  # POST /mfa/setup, /mfa/verify, /mfa/backup-codes
│       │   ├── oauth.py                # GET /oauth/{provider}, /oauth/{provider}/callback
│       │   ├── sso.py                  # GET /sso/metadata, POST /sso/acs
│       │   ├── tenants.py              # CRUD /tenants, /tenants/{id}/members
│       │   ├── admin.py                # /admin/roles, /admin/permissions (RBAC management)
│       │   ├── users.py                # /admin/users (user management endpoints)
│       │   ├── password.py             # POST /forgot-password, /reset-password
│       │   └── api_keys.py             # CRUD /api-keys
│       │
│       ├── authz/                      # Authorization subsystem
│       │   ├── __init__.py
│       │   ├── dependencies.py         # require_permissions(), require_policy()
│       │   ├── context.py              # TenantContext, ResourceContext
│       │   ├── attribute_provider.py   # Dynamic attributes for ABAC (user.department, etc)
│       │   ├── permission_cache.py     # Redis cache for permission lookups
│       │   ├── policies/
│       │   │   ├── __init__.py
│       │   │   ├── base.py             # BasePolicy, PolicyRegistry
│       │   │   └── examples.py         # ProjectPolicy, DocumentPolicy (reference impl)
│       │   └── services/
│       │       ├── __init__.py
│       │       └── rbac.py             # Permission resolution logic
│       │
│       ├── middleware/                 # FastAPI middleware
│       │   ├── __init__.py
│       │   ├── rate_limit.py           # Rate limiting (redis-backed, per-user/IP)
│       │   ├── audit.py                # Security event logging middleware
│       │   ├── tenant_resolver.py      # Auto-detect tenant from request (URL/header)
│       │   └── metrics.py              # Prometheus metrics (login rate, failures, etc)
│       │
│       ├── integrations/               # External service integrations
│       │   ├── __init__.py
│       │   ├── email/
│       │   │   ├── __init__.py
│       │   │   ├── base.py             # Abstract EmailProvider interface
│       │   │   ├── smtp.py             # SMTP implementation
│       │   │   ├── sendgrid.py         # SendGrid provider
│       │   │   ├── ses.py              # AWS SES provider
│       │   │   └── templates/          # Jinja2 email templates
│       │   │       ├── verify_email.html
│       │   │       ├── reset_password.html
│       │   │       ├── mfa_setup.html
│       │   │       └── welcome.html
│       │   └── sms/
│       │       ├── __init__.py
│       │       ├── base.py             # Abstract SMSProvider interface
│       │       ├── twilio.py           # Twilio implementation
│       │       └── sns.py              # AWS SNS implementation
│       │
│       ├── events/                     # Event system
│       │   ├── __init__.py
│       │   ├── event_bus.py            # Pub/sub for auth events (user.created, login.failed)
│       │   ├── handlers.py             # Built-in event handlers
│       │   └── webhook_dispatcher.py   # Webhook delivery to external systems
│       │
│       └── utils/                      # Utility functions
│           ├── __init__.py
│           ├── validators.py           # Email, password strength validators
│           ├── tokens.py               # JWT utilities (decode, verify, extract claims)
│           ├── crypto.py               # Additional crypto (backup codes generation, etc)
│           └── correlation_id.py       # Request tracing and correlation IDs
│
├── migrations/                         # Alembic database migrations
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_tenancy.py
│   │   ├── 003_add_authz.py
│   │   ├── 004_add_mfa.py
│   │   └── ...
│   ├── env.py
│   └── script.py.mako
│
├── tests/                              # Test suite
│   ├── conftest.py                     # Pytest fixtures (db, client, auth tokens)
│   ├── factories.py                    # Test data factories (factory_boy)
│   │
│   ├── unit/                           # Unit tests (isolated, fast)
│   │   ├── test_security.py
│   │   ├── test_validators.py
│   │   ├── test_password_policy.py
│   │   ├── test_tokens.py
│   │   └── test_crypto.py
│   │
│   ├── integration/                    # Integration tests (with DB)
│   │   ├── test_auth_flow.py
│   │   ├── test_mfa_flow.py
│   │   ├── test_oauth_flow.py
│   │   ├── test_tenant_isolation.py
│   │   ├── test_password_reset.py
│   │   ├── test_email_verification.py
│   │   ├── test_authz.py
│   │   ├── test_session_limits.py
│   │   └── test_api_keys.py
│   │
│   ├── e2e/                            # End-to-end tests
│   │   └── test_complete_flows.py
│   │
│   └── performance/                    # Load/performance tests
│       └── load_tests.py               # Locust/K6 scripts
│
├── scripts/                            # Utility scripts
│   ├── seed_data.py                    # Seed dev environment with test data
│   ├── migrate_legacy_users.py         # Migration scripts for existing users
│   ├── rotate_secrets.py               # Secret rotation utilities
│   └── create_admin.py                 # Create initial admin user
│
├── docker/                             # Docker configuration
│   ├── Dockerfile                      # Production container image
│   ├── Dockerfile.dev                  # Development container
│   └── docker-compose.yml              # Full stack (app, postgres, redis)
│
└── examples/                           # Integration examples
    ├── basic_app.py                    # Minimal integration example
    ├── multi_tenant_app.py             # Multi-tenant app example
    ├── full_featured_app.py            # All features enabled
    ├── api_key_auth.py                 # M2M authentication example
    └── custom_policy.py                # Custom authorization policy example
```

---

## Phase-by-Phase Implementation Plan

### **Phase 1: Foundation + Core Security** (Week 1-2)
**Goal:** Basic authentication with password reset and email verification

**Deliverables:**
- Project setup (pyproject.toml, dependencies)
- Core utilities (config, security, database, exceptions, logging)
- Models: User, UserSession, AuditLog, PasswordResetToken
- Services: auth, password_reset, email_verification, account_lockout
- API: auth routes, password routes
- Email integration (SMTP provider)
- Tests + basic example app

**Tables:**
- `users`
- `user_sessions`
- `audit_logs`
- `password_reset_tokens`

---

### **Phase 2: Multi-Tenancy** (Week 2-3)
**Goal:** Tenant isolation and membership management

**Deliverables:**
- Models: Tenant, TenantMembership
- Services: tenant operations
- Middleware: tenant_resolver (URL/header-based)
- API: tenant CRUD, membership management
- Bootstrap: default tenant (id=1)
- Tests: tenant isolation

**Tables:**
- `tenants`
- `tenant_memberships`

---

### **Phase 3: RBAC (Role-Based Access Control)** (Week 3-4)
**Goal:** Role and permission management

**Deliverables:**
- Models: Permission, Role, RolePermission, TenantUserRole
- Services: RBAC service (permission resolution)
- Dependencies: `require_permissions()`
- API: admin routes (role/permission CRUD)
- Permission catalog seeding
- Tests: permission enforcement

**Tables:**
- `permissions`
- `roles`
- `role_permissions`
- `tenant_user_roles`

---

### **Phase 4: ABAC (Attribute-Based Access Control)** (Week 4-5)
**Goal:** Resource-level authorization policies

**Deliverables:**
- Policy framework (BasePolicy, PolicyRegistry)
- Attribute provider (dynamic attributes)
- Dependencies: `require_policy()`
- Example policies (ProjectPolicy, DocumentPolicy)
- Tests: policy enforcement

**No new tables** (logic layer only)

---

### **Phase 5: Production Hardening** (Week 5-6)
**Goal:** Security best practices and monitoring

**Deliverables:**
- Session limits (max concurrent sessions)
- Refresh token rotation + replay detection
- Rate limiting middleware (Redis)
- Prometheus metrics
- Device management
- Audit event expansion
- Tests: security scenarios

**Tables:**
- Enhanced `user_sessions` (device tracking)

---

### **Phase 6: MFA (Multi-Factor Authentication)** (Week 6-7)
**Goal:** TOTP and backup codes

**Deliverables:**
- Models: MFAMethod, MFABackupCode
- Services: MFA service (TOTP setup/verify)
- API: MFA routes
- Challenge flow (/login → /login/mfa)
- Step-up MFA for sensitive endpoints
- Update JWT `amr` claim
- Tests: MFA flows

**Tables:**
- `mfa_methods`
- `mfa_backup_codes`

---

### **Phase 7: OAuth Social Login** (Week 7-8)
**Goal:** Google, GitHub, etc. via OAuth 2.0

**Deliverables:**
- Models: OAuthConnection, OAuthState
- Services: OAuth service (authlib integration)
- API: OAuth routes (authorize, callback)
- Account linking (email matching)
- Tests: OAuth flows

**Tables:**
- `oauth_connections`
- `oauth_states`

---

### **Phase 8: Enterprise SSO** (Week 8-9)
**Goal:** SAML/OIDC for enterprise customers

**Deliverables:**
- Models: SSOProvider, SSOConnection
- Services: SSO service (SAML/OIDC)
- API: SSO routes (metadata, ACS)
- Per-tenant SSO configuration
- Tests: SSO flows

**Tables:**
- `sso_providers`
- `sso_connections`

---

### **Phase 9: API Keys (M2M Auth)** (Week 9-10)
**Goal:** Machine-to-machine authentication

**Deliverables:**
- Models: APIKey, TokenBlacklist
- Services: API key service (generate, rotate, revoke)
- API: API key CRUD
- Key hashing (bcrypt)
- Scoped permissions
- Tests: API key auth

**Tables:**
- `api_keys`
- `token_blacklist`

---

### **Phase 10: Advanced Features** (Week 10+)
**Goal:** Nice-to-have production features

**Deliverables:**
- User impersonation (admin feature)
- Permission caching (Redis)
- Event bus + webhooks
- SMS provider (for SMS-based MFA)
- Enhanced audit logging
- User management UI endpoints

**Tables:**
- As needed per feature

---

## Key Dependencies

### Core
- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **pydantic** - Data validation (V2)
- **pydantic-settings** - Configuration management

### Database
- **sqlalchemy** - ORM (2.0 with async)
- **asyncpg** - Async PostgreSQL driver
- **alembic** - Database migrations

### Security
- **passlib[bcrypt]** - Password hashing
- **python-jose[cryptography]** - JWT handling
- **pyotp** - TOTP for MFA
- **authlib** - OAuth/OIDC client

### Infrastructure
- **redis** - Session storage, caching, rate limiting
- **celery** - Background tasks (emails, webhooks)

### Integrations
- **httpx** - Async HTTP client (OAuth)
- **jinja2** - Email templates
- **sendgrid** / **boto3** - Email providers
- **twilio** - SMS provider

### Monitoring
- **prometheus-fastapi-instrumentator** - Metrics
- **structlog** - Structured logging

### Testing
- **pytest** - Test framework
- **pytest-asyncio** - Async test support
- **factory-boy** - Test data factories
- **httpx** - Test client

---

## Configuration

### Environment Variables (.env.example)

```bash
# Application
APP_NAME=FastAPI Auth
DEBUG=false
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fastapi_auth

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Email
EMAIL_PROVIDER=smtp  # smtp, sendgrid, ses
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@example.com

# OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# Security
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Session
MAX_SESSIONS_PER_USER=5
```

---

## Usage Example

### Basic Integration

```python
from fastapi import FastAPI, Depends
from fastapi_auth import (
    auth_router,
    require_permissions,
    get_current_user,
    init_db,
)
from fastapi_auth.models import User

app = FastAPI()

# Initialize database
@app.on_event("startup")
async def startup():
    await init_db()

# Include auth routes
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# Protected route with permission check
@app.get("/admin/users")
async def list_users(
    current_user: User = Depends(require_permissions("users.read"))
):
    return {"users": [...]}

# Simple auth check (no permission required)
@app.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"user": current_user}
```

### Multi-Tenant Integration

```python
from fastapi_auth import TenantContext, require_permissions

@app.get("/projects")
async def list_projects(
    tenant_ctx: TenantContext = Depends(require_permissions("projects.read")),
):
    # tenant_ctx.tenant_id is automatically resolved from URL/header
    # tenant_ctx.user contains the authenticated user
    # tenant_ctx.permissions contains resolved permissions
    return {"tenant_id": tenant_ctx.tenant_id, "projects": [...]}
```

---

## Testing Strategy

### Unit Tests
- Test individual functions in isolation
- Mock external dependencies
- Fast execution (< 1 second per test)

### Integration Tests
- Test with real database (test container)
- Test API endpoints end-to-end
- Verify database state changes

### E2E Tests
- Full user journeys (register → verify → login → use app)
- Multi-step flows (MFA, OAuth, password reset)

### Performance Tests
- Load testing (Locust/K6)
- Concurrent login stress tests
- Permission resolution performance

---

## Security Considerations

### Authentication
- ✅ Passwords hashed with bcrypt (cost factor 12)
- ✅ JWT access tokens (short-lived: 15min)
- ✅ Refresh token rotation (long-lived: 30 days)
- ✅ Refresh token replay detection
- ✅ Session revocation on logout
- ✅ Account lockout after failed attempts

### Authorization
- ✅ Tenant isolation (row-level security)
- ✅ RBAC with least privilege principle
- ✅ ABAC for resource-level checks
- ✅ Permission caching for performance

### Data Protection
- ✅ Sensitive data encrypted at rest
- ✅ TLS required in production
- ✅ Audit logging for security events
- ✅ GDPR compliance (data export/deletion)

### Monitoring
- ✅ Failed login tracking
- ✅ Suspicious activity detection
- ✅ Rate limiting per user/IP
- ✅ Metrics for security events

---

## Compliance

### OWASP Top 10
- ✅ A01: Broken Access Control → RBAC/ABAC
- ✅ A02: Cryptographic Failures → bcrypt, JWT
- ✅ A03: Injection → SQLAlchemy ORM
- ✅ A04: Insecure Design → Security by design
- ✅ A05: Security Misconfiguration → Secure defaults
- ✅ A07: Authentication Failures → MFA, lockout
- ✅ A08: Data Integrity Failures → Token signatures
- ✅ A09: Security Logging Failures → Audit logs

### Standards
- NIST 800-63B (password guidelines)
- PCI-DSS (for payment processing)
- SOC 2 Type II (audit trail)
- GDPR (data privacy)

---

## Contributing

See Phase implementation order above. Each phase is self-contained and can be developed/tested independently.

## License

[Your License Here]
