# BioNexus Security Architecture

## Phase 3: Identity & Isolation (21 CFR Part 11 + RGPD)

### Overview

This document describes the security hardening for BioNexus MVP, implementing:
- **JWT Authentication** for API access control
- **Multi-Tenant Isolation** for laboratory separation
- **Role-Based Access Control (RBAC)** with fine-grained permissions
- **Mandatory User Attribution** in all audit trails

---

## 1. JWT Authentication

### Flow

```
┌─────────────────┐
│  Frontend/CLI   │
└────────┬────────┘
         │ POST /api/auth/login
         │ {"username": "john.doe", "password": "secret"}
         ↓
┌──────────────────────────┐
│  login_view              │
│  - Authenticate user     │
│  - Check is_active       │
│  - Check tenant_id       │
└────────┬─────────────────┘
         │ Generate tokens
         ↓
┌──────────────────────────┐
│  JWTService.generate_    │
│  tokens(user)            │
└────────┬─────────────────┘
         │ Return access + refresh
         ↓
┌──────────────────────┐
│ {                    │
│   "access": "...",   │ ← 15 min lifetime
│   "refresh": "...",  │ ← 7 day lifetime
│   "user_id": 123,    │
│   "tenant_id": 456   │
│ }                    │
└──────────────────────┘
```

### Token Structure

**Access Token (short-lived)**
```json
{
  "user_id": 123,
  "tenant_id": 456,
  "username": "john.doe",
  "email": "john@lab.local",
  "role": "lab_technician",
  "permissions": ["sample:view", "sample:create", "protocol:view"],
  "exp": 1708000000,
  "iat": 1707999100,
  "type": "access"
}
```

**Refresh Token (long-lived)**
```json
{
  "user_id": 123,
  "tenant_id": 456,
  "token_id": "random_secure_id",
  "exp": 1708604400,
  "iat": 1707999100,
  "type": "refresh"
}
```

### Implementation

- **Algorithm**: HS256 (HMAC with SHA-256)
- **Secret**: Django `SECRET_KEY` (must be unique per environment)
- **Access Token Lifetime**: 15 minutes
- **Refresh Token Lifetime**: 7 days

---

## 2. Multi-Tenant Isolation

### Data Model

```
Tenant (Laboratory)
├── id (PK)
├── name (unique)
├── slug (unique)
└── is_active

User
├── id (PK)
├── username
├── email
├── tenant_id (FK) ← Mandatory, defines data isolation boundary
└── role_id (FK)

Sample, Protocol (and other data models)
├── ... existing fields ...
├── tenant_id (FK) ← Must be added to all data models
└── is_deleted (for soft delete)
```

### Isolation Strategy

Every query MUST filter by `tenant_id`:

```python
# ❌ WRONG - Would return samples from all tenants
samples = Sample.objects.all()

# ✅ CORRECT - Filters by authenticated user's tenant
samples = Sample.objects.filter(tenant_id=request.auth_user['tenant_id'])
```

### Implementation in Repositories

```python
class SampleRepository:
    @staticmethod
    def get_all(tenant_id: int) -> QuerySet[Sample]:
        return Sample.objects.filter(
            tenant_id=tenant_id,
            is_deleted=False
        )

    @staticmethod
    def get_by_id(tenant_id: int, sample_id: int) -> Sample | None:
        try:
            return Sample.objects.get(
                pk=sample_id,
                tenant_id=tenant_id,  # ← Critical: enforce isolation
                is_deleted=False
            )
        except Sample.DoesNotExist:
            return None
```

### Enforcement Points

1. **HTTP Layer** (`@tenant_context` decorator):
   - Extracts `tenant_id` from JWT
   - Injects into `request.tenant_id`

2. **Service Layer**:
   - Passes `tenant_id` to repository methods
   - Services never assume global data access

3. **Repository Layer**:
   - ALWAYS filters by `tenant_id` at query time
   - Prevents accidental cross-tenant data leaks

---

## 3. Role-Based Access Control (RBAC)

### Permission Model

```
Role
├── ADMIN
├── PRINCIPAL_INVESTIGATOR
├── LAB_TECHNICIAN
├── AUDITOR (read-only)
└── VIEWER (read-only)

Permission
├── sample:view
├── sample:create
├── sample:update
├── sample:delete
├── protocol:view
├── protocol:create
├── protocol:update
├── protocol:delete
├── audit:view
├── audit:export
├── user:manage
└── role:manage

RolePermission (join table)
└── Defines which permissions each role has
```

### Standard Role Assignments

| Role | Permissions |
|------|-------------|
| **ADMIN** | All permissions |
| **PRINCIPAL_INVESTIGATOR** | Create/view samples, create/view protocols, view audit |
| **LAB_TECHNICIAN** | Create/update samples, view protocols, view audit |
| **AUDITOR** | View samples/protocols/audit (read-only) |
| **VIEWER** | View samples/protocols (read-only) |

### Implementation

**Decorator-based permission checking:**
```python
@permission_required(Permission.SAMPLE_DELETE)
def delete_sample(request, sample_id):
    # Only users with "sample:delete" permission can execute
    sample = SampleService.delete_sample(sample_id)
    return Response({"id": sample_id}, status=204)
```

**User permission checking:**
```python
user.has_permission("sample:delete")  # → bool
user.get_permissions()  # → ["sample:view", "sample:create", ...]
```

---

## 4. Mandatory User Attribution in Audit Trail

### Change: user_id is NOW REQUIRED

**Before (MVP 1):**
```python
AuditTrail.record(
    entity_type="Sample",
    entity_id=1,
    operation="CREATE",
    changes={...},
    snapshot_before={},
    snapshot_after={...},
    user_id=None,  # ← Optional, would default to NULL
    user_email=None
)
```

**After (MVP 2 - Secure):**
```python
AuditTrail.record(
    entity_type="Sample",
    entity_id=1,
    operation="CREATE",
    changes={...},
    snapshot_before={},
    snapshot_after={...},
    user_id=123,  # ← MANDATORY (raised ValueError if missing)
    user_email="john.doe@lab.local"  # ← MANDATORY
)
```

### Enforcement

```python
def record(
    entity_type: str,
    entity_id: int,
    operation: str,
    changes: dict,
    snapshot_before: dict,
    snapshot_after: dict,
    user_id: int,  # ← Type hint: no default, no None
    user_email: str,  # ← Type hint: no default, no None
) -> AuditLog:
    if not user_id:
        raise ValueError(
            "user_id is mandatory for audit trail (21 CFR Part 11). "
            "All operations must be performed by authenticated users."
        )
    if not user_email:
        raise ValueError(
            "user_email is mandatory for audit trail (21 CFR Part 11)."
        )
```

### Audit Trail Enrichment

Every `AuditLog` now MUST contain:
```json
{
  "entity_type": "Sample",
  "entity_id": 1,
  "operation": "CREATE",
  "user_id": 123,  ← ✅ Mandatory
  "user_email": "john.doe@lab.local",  ← ✅ Mandatory
  "timestamp": "2026-02-17T15:30:00",
  "changes": {...},
  "signature": "a1b2c3d4...",
  "previous_signature": "...e5f6g7h8"
}
```

---

## 5. Certified Audit Export

### Feature: Tamper-Proof Audit Report

Instead of a simple CSV dump, BioNexus generates **certified audit exports** that include:

1. **Complete Audit Trail**
   - All mutations for selected entity type
   - With before/after snapshots

2. **Chain Integrity Verification**
   - Recalculates all signatures
   - Detects if any record was modified
   - Reports tampering immediately

3. **Digital Signature**
   - Signs the entire export with Django's SECRET_KEY
   - Verifies export hasn't been post-modified

4. **Metadata**
   - Export timestamp
   - Exporting user ID
   - Tenant ID
   - Record count

### Example Export

```json
{
  "export_id": "audit-export-2026-02-17-12345",
  "timestamp": "2026-02-17T15:45:00Z",
  "exported_by": {
    "user_id": 456,
    "username": "auditor@lab.local"
  },
  "tenant_id": 123,
  "entity_type": "Sample",
  "entity_count": 47,
  "chain_verification": {
    "is_intact": true,
    "records_verified": 47,
    "message": "Chain integrity verified for 47 records"
  },
  "records": [
    {
      "id": 1,
      "entity_id": 1,
      "operation": "CREATE",
      "user_id": 789,
      "user_email": "john@lab.local",
      "timestamp": "2026-01-15T09:00:00Z",
      "changes": {...},
      "signature": "a1b2c3..."
    },
    ...
  ],
  "export_signature": "sha256_of_entire_export_...",
  "export_valid": true
}
```

---

## 6. Implementation Roadmap

### Phase 2.1: Core Auth (DONE ✅)
- [x] JWT service (token generation/verification)
- [x] User/Role/Permission models
- [x] Auth decorators
- [x] Login/logout endpoints
- [x] Multi-tenant User model

### Phase 2.2: Data Isolation (IN PROGRESS 🔄)
- [ ] Add `tenant_id` ForeignKey to Sample, Protocol, and all data models
- [ ] Update repositories to filter by `tenant_id`
- [ ] Update services to pass `tenant_id` through
- [ ] Add migration for tenant_id field
- [ ] Update views with `@tenant_context` decorator

### Phase 2.3: Audit Integration (PENDING)
- [ ] Update service layer to capture `request.auth_user` context
- [ ] Pass `user_id`, `user_email` from request to AuditTrail.record()
- [ ] Add tests for mandatory user attribution
- [ ] Fix existing tests to provide valid user_id

### Phase 2.4: Certified Export (PENDING)
- [ ] Create AuditExport model
- [ ] Implement chain verification endpoint
- [ ] Create certified PDF/JSON export generator
- [ ] Add permission checks (`audit:export`)

---

## 7. Security Best Practices

### Do's ✅
- Always pass `tenant_id` to repository methods
- Always check permissions with `@permission_required` decorator
- Always require authentication with `@authenticate_required`
- Always log user actions to AuditLog with user_id
- Always verify refresh tokens are still valid
- Always rotate refresh tokens after use

### Don'ts ❌
- Don't query data without filtering by `tenant_id`
- Don't assume user_id in AuditTrail (now mandatory)
- Don't skip permission checks for "internal" operations
- Don't expose raw database records to unauthenticated requests
- Don't re-use access tokens after they expire
- Don't store passwords in plain text (use Django's hashers)

---

## 8. Compliance Mapping

### 21 CFR Part 11 Requirements

| Requirement | Implementation |
|-------------|-----------------|
| **Audit trail** | AuditLog with signatures + mandatory user_id |
| **Immutability** | AuditLog.save() enforces signature validation |
| **Authenticity** | JWT tokens + user_id in every mutation |
| **Integrity** | SHA-256 signature chaining |
| **Non-repudiation** | user_id + timestamp + operation |
| **Access control** | RBAC with permissions |
| **Identification** | User model with email + tenant |

### RGPD Requirements

| Right | Implementation |
|------|-----------------|
| **Right to be forgotten** | Soft delete with audit trail |
| **Accountability** | Complete audit log with timestamps |
| **Data minimization** | Only store necessary fields |
| **Purpose limitation** | RBAC limits data access |
| **Confidentiality** | JWT + HTTPS (enforced in prod) |

---

## 9. Configuration

### Django Settings
```python
# core/settings.py
AUTH_USER_MODEL = "core.User"

# JWT
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_LIFETIME = 15  # minutes
JWT_REFRESH_TOKEN_LIFETIME = 7   # days
```

### Environment Variables
```bash
# Required for production
DJANGO_SECRET_KEY="long-random-string-min-50-chars"
DJANGO_DEBUG="false"
DJANGO_ALLOWED_HOSTS="lab.example.com,api.lab.example.com"
```

---

## 10. Testing

### Test Fixtures
```python
from core.tests.fixtures import (
    create_test_tenant,
    create_test_user,
    create_test_role,
    create_test_permissions,
    assign_permissions_to_role
)

# In test setup:
tenant = create_test_tenant()
role = create_test_role(Role.LAB_TECHNICIAN)
user = create_test_user(tenant=tenant, role=role)
permissions = create_test_permissions()
assign_permissions_to_role(role, [Permission.SAMPLE_VIEW])
```

### Testing Authentication
```python
def test_login():
    response = client.post("/api/auth/login", {
        "username": "john.doe",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data
```

### Testing RBAC
```python
@permission_required(Permission.SAMPLE_DELETE)
def delete_sample(request, sample_id):
    ...

# Should fail for users without permission
response = client.delete(f"/api/samples/{sample_id}/")
assert response.status_code == 403
```

---

## Next Steps

1. **Add tenant_id to existing models** (Sample, Protocol, etc.)
2. **Update repositories** to filter by tenant_id
3. **Update views** to use @tenant_context and @authenticate_required
4. **Test multi-tenant isolation** thoroughly
5. **Implement certified export** endpoint
6. **Update API documentation** with authentication requirements

---

**Document Version**: 1.0 (MVP 2)
**Last Updated**: 2026-02-17
**Status**: Architecture Defined, Implementation In Progress
