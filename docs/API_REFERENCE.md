# BioNexus API Reference

**Version:** 1.0
**Base URL:** `https://api.bionexus.io`
**Last Updated:** 2026-02-28
**Status:** Authoritative — single source of truth for all API integrators

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Versioning Strategy](#3-versioning-strategy)
4. [Common Patterns](#4-common-patterns)
5. [Rate Limiting](#5-rate-limiting)
6. [Endpoints by Domain](#6-endpoints-by-domain)
   - [6.1 Auth](#61-auth)
   - [6.2 Samples](#62-samples)
   - [6.3 Protocols](#63-protocols)
   - [6.4 Data Ingestion — Raw Files](#64-data-ingestion--raw-files)
   - [6.5 Parsing & Validation](#65-parsing--validation)
   - [6.6 Execution Logs](#66-execution-logs)
   - [6.7 Certification & Reports](#67-certification--reports)
   - [6.8 Audit Trail](#68-audit-trail)
   - [6.9 Administration](#69-administration)
7. [Webhook & Event System](#7-webhook--event-system)
8. [Error Codes](#8-error-codes)
9. [SDK & Integration Guide](#9-sdk--integration-guide)
10. [OpenAPI / Swagger](#10-openapi--swagger)
11. [Changelog](#11-changelog)

---

## 1. Overview

### Design Principles

BioNexus follows these API design principles:

- **RESTful**: Resource-oriented URL design. Nouns in URLs, HTTP verbs for actions.
- **JSON everywhere**: All request and response bodies are `application/json` unless otherwise noted (file uploads use `multipart/form-data`).
- **21 CFR Part 11 compliant**: Every mutating operation is attributed to an authenticated user and recorded in the immutable audit trail.
- **Tenant-scoped by default**: All data queries are automatically filtered to the authenticated user's tenant. Cross-tenant access is impossible by design.
- **ALCOA+ data integrity**: SHA-256 hash chaining on audit records. Any tampering is cryptographically detectable.
- **Human-in-the-loop**: AI-parsed data is never accepted automatically. It is always gated behind explicit human validation before entering the system.
- **Soft-delete only**: No data is ever permanently deleted. Deletion is a logical flag. The audit trail is preserved.
- **Idempotent GETs**: All GET requests are safe and idempotent.
- **Consistent error shape**: All errors return `{"error": "...", "code": "ERR_CODE", "details": {...}}`.

### Base URL

| Environment | Base URL |
|---|---|
| Production | `https://api.bionexus.io` |
| Staging | `https://staging-api.bionexus.io` |
| Local development | `http://localhost:8000` |

All endpoints are under the `/api/` path prefix.

### Content Types

| Direction | Content-Type |
|---|---|
| Request (JSON) | `application/json` |
| Request (file upload) | `multipart/form-data` |
| Response | `application/json` |
| Report PDF download | `application/pdf` |
| Raw file download | Varies by MIME type of uploaded file |

### Pagination Format

All list responses are paginated:

```json
{
  "count": 47,
  "next": "https://api.bionexus.io/api/samples/?page=2&page_size=20",
  "previous": null,
  "results": [...]
}
```

Default `page_size` is `20`. Maximum `page_size` is `100`.

---

## 2. Authentication

### Overview

BioNexus uses JWT (JSON Web Tokens) with:
- **Algorithm**: HS256 (HMAC with SHA-256)
- **Access token lifetime**: 15 minutes
- **Refresh token lifetime**: 7 days
- **Token rotation**: Refresh tokens are rotated on use

### Authentication Header

All authenticated endpoints require:

```
Authorization: Bearer <access_token>
```

### Token Structure

**Access Token Payload (decoded)**

```json
{
  "user_id": 123,
  "tenant_id": 456,
  "username": "john.doe",
  "email": "john@lab.local",
  "role": "lab_technician",
  "permissions": [
    "sample:view",
    "sample:create",
    "sample:update",
    "protocol:view"
  ],
  "exp": 1708000000,
  "iat": 1707999100,
  "type": "access"
}
```

**Refresh Token Payload (decoded)**

```json
{
  "user_id": 123,
  "tenant_id": 456,
  "token_id": "random_secure_id_32_bytes",
  "exp": 1708604400,
  "iat": 1707999100,
  "type": "refresh"
}
```

### Authentication Errors

| Scenario | Status | Response |
|---|---|---|
| Missing Authorization header | `401` | `{"error": "Authentication required", "code": "ERR_AUTH_MISSING"}` |
| Malformed Bearer token | `401` | `{"error": "Invalid token format", "code": "ERR_TOKEN_INVALID"}` |
| Expired access token | `401` | `{"error": "Token expired", "code": "ERR_TOKEN_EXPIRED"}` |
| Tampered/invalid signature | `401` | `{"error": "Token signature invalid", "code": "ERR_TOKEN_SIGNATURE"}` |
| Wrong token type (refresh used as access) | `401` | `{"error": "Invalid token type", "code": "ERR_TOKEN_TYPE"}` |
| User account deactivated | `403` | `{"error": "User account is inactive", "code": "ERR_USER_INACTIVE"}` |
| Insufficient role/permission | `403` | `{"error": "Permission denied", "code": "ERR_PERMISSION_DENIED"}` |

### Token Lifecycle

```
1. POST /api/auth/login/         → Receive access + refresh tokens
2. Include access token in requests (expires in 15 min)
3. POST /api/auth/refresh/       → Exchange refresh token for new access token
4. POST /api/auth/logout/        → Invalidate refresh token server-side
```

---

## 3. Versioning Strategy

### URL-Based Versioning

BioNexus uses URL path versioning:

```
/api/v1/samples/
/api/v2/samples/   (future)
```

The current stable version is `v1`. During the MVP phase, endpoints are served under `/api/` without an explicit version prefix for brevity. All current routes are `v1` equivalent. Explicit `/api/v1/` routing will be introduced before general availability.

### Deprecation Policy

1. A minimum of **6 months notice** is given before any endpoint is deprecated.
2. Deprecated endpoints return a `Sunset` header with the removal date:
   ```
   Sunset: 2026-12-31T00:00:00Z
   Deprecation: true
   Link: <https://docs.bionexus.io/api/v2/migration>; rel="successor-version"
   ```
3. Deprecated endpoints continue to function until the sunset date.
4. Breaking changes (field removal, type change, semantic change) are only introduced in a new major version.

### Backward Compatibility Rules

Non-breaking changes that may occur without a version bump:

- Adding new optional fields to response objects
- Adding new optional query parameters
- Adding new endpoints
- Adding new values to enum fields not used in strict matching
- Performance improvements that do not change the API contract

Breaking changes that require a major version bump:

- Removing or renaming fields in request or response bodies
- Changing field types
- Removing endpoints
- Changing HTTP methods on existing endpoints
- Changing authentication requirements
- Changing pagination behavior

### API Stability Labels

| Label | Meaning |
|---|---|
| **Stable** | No breaking changes without a major version bump |
| **Beta** | May change with notice; suitable for integration testing |
| **Experimental** | Subject to change without notice; do not use in production |

All endpoints in this document are **Stable** unless marked otherwise.

---

## 4. Common Patterns

### Pagination

Use `page` and `page_size` query parameters on all list endpoints:

```
GET /api/samples/?page=2&page_size=50
```

| Parameter | Default | Max | Description |
|---|---|---|---|
| `page` | `1` | — | Page number (1-indexed) |
| `page_size` | `20` | `100` | Items per page |

### Filtering

Filterable list endpoints accept field-based query parameters:

```
GET /api/samples/?sample_type=blood&location=Lab-A
GET /api/auditlog/?entity_type=ParsedData&operation=UPDATE
GET /api/auditlog/?date_from=2026-01-01&date_to=2026-02-28
```

Dates use ISO 8601 format (`YYYY-MM-DD` or full timestamp).

### Ordering

Use the `ordering` query parameter with a field name. Prefix with `-` for descending:

```
GET /api/samples/?ordering=-received_at
GET /api/auditlog/?ordering=timestamp
```

### Tenant Scoping

Every authenticated request is automatically scoped to the user's tenant. The `tenant_id` is extracted from the JWT access token claim and applied to all database queries. You never need to pass `tenant_id` explicitly in request bodies or query parameters — it is enforced server-side.

Attempting to access resources belonging to another tenant returns `404 Not Found` (not `403`) to prevent tenant enumeration.

### Soft Deletes

BioNexus never permanently deletes data. A `DELETE` request sets `is_deleted = true` and records the deletion in the audit trail. Deleted records are excluded from list responses unless you pass `?include_deleted=true` (Admin only).

### Timestamps

All timestamps are UTC ISO 8601:

```
2026-02-17T14:35:22Z
```

### Error Response Format

All error responses follow this structure:

```json
{
  "error": "Human-readable error message",
  "code": "ERR_MACHINE_READABLE_CODE",
  "details": {
    "field": "Additional context (optional)"
  }
}
```

Validation errors from DRF serializers return field-level detail:

```json
{
  "error": "Validation failed",
  "code": "ERR_VALIDATION",
  "details": {
    "name": ["This field is required."],
    "sample_type": ["Value 'unknown' is not a valid choice."]
  }
}
```

---

## 5. Rate Limiting

### Per-Role Rate Limits

Rate limits are enforced per authenticated user (not per IP):

| Role | Sustained (per minute) | Burst (per second) |
|---|---|---|
| Admin | 600 requests/min | 30 req/sec |
| Principal Investigator | 300 requests/min | 20 req/sec |
| Lab Technician | 200 requests/min | 15 req/sec |
| Auditor | 120 requests/min | 10 req/sec |
| Viewer | 60 requests/min | 5 req/sec |
| Unauthenticated | 10 requests/min | 2 req/sec |

File upload endpoints (`POST /api/rawfiles/`) have a separate limit:

| Role | Max uploads per hour |
|---|---|
| Admin | 200 |
| Principal Investigator | 100 |
| Lab Technician | 50 |

### Rate Limit Headers

Every response includes:

```
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 197
X-RateLimit-Reset: 1708000060
```

When the rate limit is exceeded:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 23
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1708000060

{
  "error": "Rate limit exceeded",
  "code": "ERR_RATE_LIMIT",
  "details": {
    "retry_after_seconds": 23
  }
}
```

---

## 6. Endpoints by Domain

---

### 6.1 Auth

#### POST /api/auth/login/

Authenticates a user and returns JWT tokens. Login events are recorded in the audit trail with IP address.

**Required role:** None (public endpoint)

**Request body:**

```json
{
  "username": "john.doe",
  "password": "SecurePass123!",
  "tenant_slug": "acme-labs"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | Yes | Username within the tenant |
| `password` | string | Yes | User's password |
| `tenant_slug` | string | No | Tenant slug (inferred from username if unique) |

**Response `200 OK`:**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": 123,
  "tenant_id": 456,
  "username": "john.doe",
  "role": "lab_technician"
}
```

**Status codes:**

| Code | Meaning |
|---|---|
| `200` | Authenticated successfully |
| `400` | Missing username or password |
| `401` | Invalid credentials |
| `403` | User account is inactive |

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "john.doe", "password": "SecurePass123!", "tenant_slug": "acme-labs"}'
```

---

#### POST /api/auth/refresh/

Exchanges a valid refresh token for a new access token.

**Required role:** None (public endpoint)

**Request body:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response `200 OK`:**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": 123,
  "tenant_id": 456,
  "username": "john.doe",
  "role": "lab_technician"
}
```

**Status codes:**

| Code | Meaning |
|---|---|
| `200` | New tokens issued |
| `400` | Missing refresh token |
| `401` | Invalid or expired refresh token |
| `401` | User not found |

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}'
```

---

#### POST /api/auth/logout/

Revokes the current session. The refresh token is invalidated server-side. The logout event is recorded in the audit trail.

**Required role:** Any authenticated user

**Request body:** None

**Response `200 OK`:**

```json
{
  "message": "Logged out successfully"
}
```

**Status codes:**

| Code | Meaning |
|---|---|
| `200` | Logged out successfully |
| `401` | Not authenticated |

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/auth/logout/ \
  -H "Authorization: Bearer <access_token>"
```

---

#### POST /api/auth/verify-password/

Re-verifies a user's password for sensitive operations (such as the certification double-auth step). Does not issue new tokens.

**Required role:** Any authenticated user

**Request body:**

```json
{
  "password": "SecurePass123!"
}
```

**Response `200 OK`:**

```json
{
  "valid": true
}
```

**Status codes:**

| Code | Meaning |
|---|---|
| `200` | Password verified |
| `400` | Missing password |
| `401` | Incorrect password |

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/auth/verify-password/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"password": "SecurePass123!"}'
```

---

### 6.2 Samples

Sample objects represent biological specimens processed in the laboratory. All samples are tenant-scoped and soft-deleted for audit compliance.

**Sample object:**

```json
{
  "id": 42,
  "name": "Sample-2026-001",
  "sample_type": "blood",
  "received_at": "2026-02-17T09:00:00Z",
  "location": "Freezer-A, Rack-3, Position-12"
}
```

**`sample_type` allowed values:** `blood`, `plasma`, `serum`, `urine`, `tissue`, `dna`, `rna`, `other`

---

#### GET /api/samples/

Returns a paginated list of active samples for the authenticated tenant.

**Required role:** Any authenticated user
**Required permission:** `sample:view`

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `page` | integer | Page number |
| `page_size` | integer | Items per page (max 100) |
| `sample_type` | string | Filter by sample type |
| `location` | string | Filter by location (partial match) |
| `ordering` | string | Field to order by (prefix `-` for descending) |
| `include_deleted` | boolean | Include soft-deleted samples (Admin only) |

**Response `200 OK`:**

```json
{
  "count": 47,
  "next": "https://api.bionexus.io/api/samples/?page=2",
  "previous": null,
  "results": [
    {
      "id": 42,
      "name": "Sample-2026-001",
      "sample_type": "blood",
      "received_at": "2026-02-17T09:00:00Z",
      "location": "Freezer-A, Rack-3, Position-12"
    }
  ]
}
```

**curl example:**

```bash
curl -X GET "https://api.bionexus.io/api/samples/?sample_type=blood&page=1" \
  -H "Authorization: Bearer <access_token>"
```

---

#### POST /api/samples/

Creates a new sample. An audit log entry (operation: `CREATE`) is recorded automatically.

**Required role:** Lab Technician, Principal Investigator, Admin
**Required permission:** `sample:create`

**Request body:**

```json
{
  "name": "Sample-2026-002",
  "sample_type": "plasma",
  "received_at": "2026-02-17T10:30:00Z",
  "location": "Freezer-B, Rack-1, Position-4"
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `name` | string | Yes | max 255 chars |
| `sample_type` | string | Yes | Must be one of allowed values |
| `received_at` | datetime | Yes | ISO 8601 UTC |
| `location` | string | Yes | max 255 chars |

**Response `201 Created`:**

```json
{
  "id": 43,
  "name": "Sample-2026-002",
  "sample_type": "plasma",
  "received_at": "2026-02-17T10:30:00Z",
  "location": "Freezer-B, Rack-1, Position-4"
}
```

**Status codes:**

| Code | Meaning |
|---|---|
| `201` | Sample created |
| `400` | Validation error |
| `403` | Insufficient permissions |

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/samples/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sample-2026-002",
    "sample_type": "plasma",
    "received_at": "2026-02-17T10:30:00Z",
    "location": "Freezer-B, Rack-1, Position-4"
  }'
```

---

#### GET /api/samples/{id}/

Retrieves a single sample by ID.

**Required role:** Any authenticated user
**Required permission:** `sample:view`

**Response `200 OK`:**

```json
{
  "id": 42,
  "name": "Sample-2026-001",
  "sample_type": "blood",
  "received_at": "2026-02-17T09:00:00Z",
  "location": "Freezer-A, Rack-3, Position-12"
}
```

**Status codes:**

| Code | Meaning |
|---|---|
| `200` | Sample found |
| `404` | Sample not found or belongs to another tenant |

**curl example:**

```bash
curl -X GET https://api.bionexus.io/api/samples/42/ \
  -H "Authorization: Bearer <access_token>"
```

---

#### PUT /api/samples/{id}/

Full update of a sample. All fields must be provided. An audit log entry (operation: `UPDATE`) is recorded automatically.

**Required role:** Lab Technician, Principal Investigator, Admin
**Required permission:** `sample:update`

**Request body:** Same as POST (all fields required)

**Response `200 OK`:** Updated sample object

**curl example:**

```bash
curl -X PUT https://api.bionexus.io/api/samples/42/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sample-2026-001",
    "sample_type": "blood",
    "received_at": "2026-02-17T09:00:00Z",
    "location": "Freezer-A, Rack-3, Position-05"
  }'
```

---

#### PATCH /api/samples/{id}/

Partial update. Only include fields to change.

**Required role:** Lab Technician, Principal Investigator, Admin
**Required permission:** `sample:update`

**Request body (partial):**

```json
{
  "location": "Freezer-A, Rack-3, Position-05"
}
```

**Response `200 OK`:** Updated sample object

**curl example:**

```bash
curl -X PATCH https://api.bionexus.io/api/samples/42/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"location": "Freezer-A, Rack-3, Position-05"}'
```

---

#### DELETE /api/samples/{id}/

Soft-deletes a sample. The sample is marked `is_deleted=true` and removed from list responses. An audit log entry (operation: `DELETE`) is recorded automatically. Data is never physically removed.

**Required role:** Principal Investigator, Admin
**Required permission:** `sample:delete`

**Response `204 No Content`:** Empty body

**Status codes:**

| Code | Meaning |
|---|---|
| `204` | Deleted successfully |
| `404` | Sample not found |
| `403` | Insufficient permissions |

**curl example:**

```bash
curl -X DELETE https://api.bionexus.io/api/samples/42/ \
  -H "Authorization: Bearer <access_token>"
```

---

### 6.3 Protocols

Protocol objects represent laboratory procedures (DNA extraction, PCR, ELISA, etc.) that can be executed against samples.

**Protocol object:**

```json
{
  "id": 7,
  "title": "DNA Extraction v1.0",
  "description": "Standard DNA extraction using QIAamp kit",
  "steps": "1. Add lysis buffer\n2. Incubate at 56°C for 10 min\n3. Centrifuge at 8000 RPM\n4. Wash with buffer\n5. Elute in 100μL TE buffer"
}
```

All Protocol CRUD endpoints follow the same pattern as Samples. The required permission prefix is `protocol:*`.

---

#### GET /api/protocols/

Returns all active protocols for the tenant.

**Required permission:** `protocol:view`

**curl example:**

```bash
curl -X GET https://api.bionexus.io/api/protocols/ \
  -H "Authorization: Bearer <access_token>"
```

---

#### POST /api/protocols/

Creates a new protocol.

**Required permission:** `protocol:create`

**Request body:**

```json
{
  "title": "DNA Extraction v1.1",
  "description": "Updated extraction protocol with new buffer formulation",
  "steps": "1. Add lysis buffer...\n2. ..."
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `title` | string | Yes | max 255 chars |
| `description` | string | No | Free text |
| `steps` | string | No | Free text (structured format recommended) |

**Response `201 Created`:** Protocol object

---

#### GET /api/protocols/{id}/

Retrieves a single protocol.

**Required permission:** `protocol:view`

---

#### PUT /api/protocols/{id}/

Full update of a protocol.

**Required permission:** `protocol:update`

---

#### PATCH /api/protocols/{id}/

Partial update of a protocol.

**Required permission:** `protocol:update`

---

#### DELETE /api/protocols/{id}/

Soft-deletes a protocol. An audit log entry is recorded.

**Required permission:** `protocol:delete`

---

### 6.4 Data Ingestion — Raw Files

RawFiles represent uploaded instrument output files (CSV, PDF, JSON). Once stored, a RawFile is **immutable**. Its SHA-256 hash is computed on upload and stored permanently. Any subsequent tampering is detectable.

Files with identical content (same SHA-256 hash) return the existing record rather than creating a duplicate.

**RawFile object:**

```json
{
  "id": 11,
  "filename": "equipment_inventory_2026-02.csv",
  "file_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
  "file_size": 24576,
  "mime_type": "text/csv",
  "uploaded_at": "2026-02-17T10:30:00Z",
  "uploaded_by": "john.doe",
  "tenant_id": 456,
  "is_deleted": false
}
```

---

#### POST /api/rawfiles/

Uploads a raw instrument output file. The SHA-256 hash is computed server-side and stored. An audit log entry (operation: `CREATE`) is recorded.

**Required role:** Lab Technician, Principal Investigator, Admin

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | The file to upload (CSV, PDF, JSON) |

**Allowed MIME types:** `text/csv`, `application/pdf`, `application/json`
**Maximum file size:** 100 MB

**Response `201 Created`:**

```json
{
  "id": 11,
  "filename": "equipment_inventory_2026-02.csv",
  "file_hash": "a1b2c3d4...",
  "file_size": 24576,
  "mime_type": "text/csv",
  "uploaded_at": "2026-02-17T10:30:00Z",
  "is_duplicate": false
}
```

If the file already exists (same hash), returns the existing record with `"is_duplicate": true` and `200 OK`.

**Status codes:**

| Code | Meaning |
|---|---|
| `201` | File stored, new record |
| `200` | File already exists (duplicate by hash), existing record returned |
| `400` | Missing file, unsupported MIME type, or file too large |
| `403` | Insufficient permissions |

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/rawfiles/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/equipment_inventory.csv"
```

---

#### GET /api/rawfiles/

Lists all raw files uploaded by the tenant.

**Required role:** Any authenticated user

**Query parameters:**

| Parameter | Description |
|---|---|
| `mime_type` | Filter by MIME type |
| `ordering` | Order by `uploaded_at`, `filename`, `file_size` |

**Response `200 OK`:** Paginated list of RawFile objects

---

#### GET /api/rawfiles/{id}/

Retrieves metadata for a single raw file.

**Response `200 OK`:** RawFile object

---

#### GET /api/rawfiles/{id}/content/

Downloads the actual file content. Returns the binary file with the original MIME type.

**Required role:** Any authenticated user

**Response:** Binary file with headers:
```
Content-Type: text/csv
Content-Disposition: inline; filename="equipment_inventory_2026-02.csv"
X-File-Hash: a1b2c3d4...
```

**curl example:**

```bash
curl -X GET https://api.bionexus.io/api/rawfiles/11/content/ \
  -H "Authorization: Bearer <access_token>" \
  -o equipment_inventory.csv
```

---

#### POST /api/rawfiles/{id}/verify/

Verifies that the stored file has not been tampered with by recomputing the SHA-256 hash and comparing against the stored value.

**Required role:** Auditor, Admin

**Response `200 OK`:**

```json
{
  "file_id": 11,
  "stored_hash": "a1b2c3d4...",
  "computed_hash": "a1b2c3d4...",
  "is_intact": true,
  "verified_at": "2026-02-17T15:00:00Z"
}
```

If `is_intact` is `false`, the system has detected tampering and will alert administrators.

---

### 6.5 Parsing & Validation

The parsing workflow follows ALCOA+ principles. AI extraction is a proposal only. No data enters the system without explicit human authorization.

**ParsedData states:**

| State | Description |
|---|---|
| `pending` | AI extraction complete, awaiting human review |
| `validated` | Human has confirmed (with or without corrections) |
| `rejected` | Human has rejected the extraction |
| `superseded` | Replaced by a newer parsing of the same file |

**ParsedData object:**

```json
{
  "id": 5,
  "state": "pending",
  "extraction_model": "gpt-4-turbo",
  "extraction_confidence": 0.94,
  "extracted_data": {
    "equipment_records": [...],
    "sample_records": [...],
    "extraction_warnings": []
  },
  "confirmed_data": null,
  "corrections": [],
  "created_at": "2026-02-17T10:30:15Z",
  "validated_at": null,
  "validated_by_id": null
}
```

---

#### GET /api/parsing/

Lists all ParsedData records for the tenant.

**Required role:** Any authenticated user

**Query parameters:**

| Parameter | Description |
|---|---|
| `state` | Filter by state (`pending`, `validated`, `rejected`) |
| `ordering` | Order by `created_at`, `state` |

**Response `200 OK`:** Paginated list of ParsedData objects

**curl example:**

```bash
curl -X GET "https://api.bionexus.io/api/parsing/?state=pending" \
  -H "Authorization: Bearer <access_token>"
```

---

#### GET /api/parsing/{id}/

Returns full details for a ParsedData record including extracted data, corrections, and chain status.

**Required role:** Any authenticated user

**Response `200 OK`:** Full ParsedData object

**curl example:**

```bash
curl -X GET https://api.bionexus.io/api/parsing/5/ \
  -H "Authorization: Bearer <access_token>"
```

---

#### POST /api/parsing/{id}/validate/

Submits human review of AI-extracted data. The user can accept as-is or provide corrections. This is the critical gate that authorizes data acceptance. An audit log entry with full before/after snapshots is recorded (operation: `UPDATE`, state: `PENDING` → `VALIDATED`).

**Required role:** Lab Technician, Principal Investigator, Admin

**Request body:**

```json
{
  "confirmed_data": {
    "equipment_records": [
      {
        "equipment_id": "EQ-2026-001",
        "equipment_name": "Centrifuge Model X2000R",
        "equipment_type": "centrifuge",
        "location": "Lab-A, Bench 3",
        "status": "operational",
        "notes": ""
      }
    ],
    "sample_records": [],
    "extraction_warnings": [],
    "_notes_equipment_name": "Corrected typo: X2000 → X2000R"
  },
  "validation_notes": "Verified against physical equipment list. One typo corrected."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `confirmed_data` | object | Yes | The final data to accept. Must conform to `BatchExtractionResult` schema. Prefix field notes with `_notes_<field_name>` to record correction reasons in audit trail. |
| `validation_notes` | string | No | Overall validation comment for the audit trail |

**Response `200 OK`:** Updated ParsedData object (state: `validated`)

```json
{
  "id": 5,
  "state": "validated",
  "extraction_model": "gpt-4-turbo",
  "extraction_confidence": 0.94,
  "extracted_data": {...},
  "confirmed_data": {...},
  "corrections": [
    {
      "field": "equipment_name",
      "original": "Centrifuge Model X2000",
      "corrected": "Centrifuge Model X2000R",
      "notes": "Corrected typo: X2000 → X2000R"
    }
  ],
  "validated_at": "2026-02-17T10:35:00Z",
  "validated_by_id": 456
}
```

**Status codes:**

| Code | Meaning |
|---|---|
| `200` | Validated successfully |
| `400` | Data does not conform to extraction schema, or state is not `pending` |
| `403` | Insufficient permissions |

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/parsing/5/validate/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "confirmed_data": {
      "equipment_records": [...],
      "sample_records": [],
      "extraction_warnings": []
    },
    "validation_notes": "Verified and corrected typos"
  }'
```

---

#### POST /api/parsing/{id}/reject/

Rejects the AI extraction. The ParsedData state is set to `rejected`. An audit log entry is recorded with the rejection reason. The original RawFile remains intact and can be re-parsed.

**Required role:** Lab Technician, Principal Investigator, Admin

**Request body:**

```json
{
  "rejection_reason": "Too many extraction errors. File format does not match expected schema."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `rejection_reason` | string | Yes | Reason for rejection (audit trail) |

**Response `200 OK`:**

```json
{
  "id": 5,
  "state": "rejected",
  "rejection_reason": "Too many extraction errors. File format does not match expected schema.",
  "validated_at": "2026-02-17T10:35:00Z",
  "validated_by_id": 456
}
```

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/parsing/5/reject/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"rejection_reason": "File format mismatch. Re-upload required."}'
```

---

#### GET /api/parsing/{id}/corrections/

Returns the detailed correction history for a ParsedData record, derived from the audit trail.

**Required role:** Any authenticated user

**Response `200 OK`:**

```json
{
  "total": 2,
  "corrections": [
    {
      "field": "equipment_name",
      "from": "Centrifuge Model X2000",
      "to": "Centrifuge Model X2000R",
      "reason": "Corrected typo: X2000 → X2000R",
      "corrected_by": "jane.smith@lab.local",
      "corrected_at": "2026-02-17T10:35:00Z"
    }
  ]
}
```

**curl example:**

```bash
curl -X GET https://api.bionexus.io/api/parsing/5/corrections/ \
  -H "Authorization: Bearer <access_token>"
```

---

#### GET /api/parsing/{id}/rawfile/

Returns the raw source file associated with this ParsedData record. Returns binary file content.

**Required role:** Any authenticated user

**Response:** Binary file with original MIME type and filename as Content-Disposition header.

**curl example:**

```bash
curl -X GET https://api.bionexus.io/api/parsing/5/rawfile/ \
  -H "Authorization: Bearer <access_token>" \
  -o original_file.csv
```

---

### 6.6 Execution Logs

ExecutionLogs record the running of a protocol against samples on laboratory equipment. Each execution may have multiple steps.

**ExecutionLog states:** `running`, `completed`, `error`, `validated`

**ExecutionLog object:**

```json
{
  "id": 1,
  "protocol": {
    "id": 7,
    "title": "DNA Extraction v1.0"
  },
  "equipment": {
    "id": 3,
    "name": "Centrifuge Eppendorf 5810R"
  },
  "started_by": "john.doe",
  "started_at": "2026-02-17T14:30:00Z",
  "completed_at": "2026-02-17T15:45:00Z",
  "status": "completed",
  "notes": "Batch 2026-02-17, standard protocol",
  "steps": [...]
}
```

---

#### GET /api/executions/

Lists all execution logs for the tenant.

**Required role:** Any authenticated user

**Query parameters:**

| Parameter | Description |
|---|---|
| `status` | Filter by status |
| `protocol_id` | Filter by protocol |
| `ordering` | Order by `started_at` (default: `-started_at`) |

**Response `200 OK`:** Paginated list of ExecutionLog summaries

**curl example:**

```bash
curl -X GET "https://api.bionexus.io/api/executions/?status=completed" \
  -H "Authorization: Bearer <access_token>"
```

---

#### POST /api/executions/

Starts a new protocol execution. An audit log entry is recorded.

**Required role:** Lab Technician, Principal Investigator, Admin

**Request body:**

```json
{
  "protocol_id": 7,
  "equipment_id": 3,
  "started_at": "2026-02-17T14:30:00Z",
  "notes": "Batch 2026-02-17, standard protocol"
}
```

**Response `201 Created`:** ExecutionLog object (status: `running`)

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/executions/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol_id": 7,
    "equipment_id": 3,
    "started_at": "2026-02-17T14:30:00Z",
    "notes": "Standard protocol run"
  }'
```

---

#### GET /api/executions/{id}/

Returns full details for an execution log including all steps.

**Required role:** Any authenticated user

**Response `200 OK`:** Full ExecutionLog with nested steps

---

#### POST /api/executions/{id}/step/

Records the completion of an execution step. Links the step to a sample and optionally to a ParsedData record.

**Required role:** Lab Technician, Principal Investigator, Admin

**Request body:**

```json
{
  "protocol_step_number": 1,
  "sample_id": 42,
  "parsed_data_id": 5,
  "is_valid": true,
  "validation_notes": "Result within expected range"
}
```

**Response `201 Created`:**

```json
{
  "id": 10,
  "execution_id": 1,
  "protocol_step_number": 1,
  "sample_id": 42,
  "parsed_data_id": 5,
  "is_valid": true,
  "validation_notes": "Result within expected range"
}
```

---

#### PATCH /api/executions/{id}/

Updates execution status. Used to mark an execution as `completed` or to set `validated_by`.

**Required role:** Lab Technician, Principal Investigator, Admin

**Request body:**

```json
{
  "status": "completed",
  "completed_at": "2026-02-17T15:45:00Z"
}
```

---

### 6.7 Certification & Reports

CertifiedReports are the final, auditor-ready documents generated from completed ExecutionLogs. A report cannot be generated if the audit chain is corrupted. Report signing uses double authentication (password re-entry + optional OTP) to satisfy 21 CFR Part 11 non-repudiation requirements.

**CertifiedReport states:** `pending`, `certified`, `revoked`

**CertifiedReport object:**

```json
{
  "id": 42,
  "state": "certified",
  "execution_log_id": 1,
  "certified_by": "jane.smith@lab.local",
  "certified_at": "2026-02-17T16:00:00Z",
  "report_hash": "abc123def456...",
  "pdf_filename": "execution_1_2026-02-17T16:00:00.pdf",
  "pdf_size": 45678,
  "chain_integrity_verified": true,
  "chain_verification_details": {
    "is_valid": true,
    "total_records": 42,
    "verified_records": 42,
    "corrupted_records": []
  }
}
```

---

#### GET /api/reports/

Lists all certified reports for the tenant.

**Required role:** Any authenticated user

**Query parameters:**

| Parameter | Description |
|---|---|
| `state` | Filter by state |
| `ordering` | Order by `certified_at` |

**Response `200 OK`:** Paginated list of CertifiedReport summaries

**curl example:**

```bash
curl -X GET https://api.bionexus.io/api/reports/ \
  -H "Authorization: Bearer <access_token>"
```

---

#### POST /api/reports/

Generates a new certified report for an execution. This triggers:
1. Audit chain integrity verification for the tenant
2. PDF generation (falls back to text if PDF library unavailable)
3. SHA-256 hash of the report content
4. Audit log recording of the generation event

The report generation will fail with `409 Conflict` if the audit chain is corrupted.

**Required role:** Principal Investigator, Admin

**Request body:**

```json
{
  "execution_log_id": 1,
  "notes": "Routine QC batch certification for auditor submission"
}
```

**Response `201 Created`:** CertifiedReport object (state: `certified` or `revoked`)

**Status codes:**

| Code | Meaning |
|---|---|
| `201` | Report generated successfully |
| `400` | Execution log not found or not in `completed`/`validated` state |
| `403` | Insufficient permissions |
| `409` | Audit chain corrupted — report cannot be certified |

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/reports/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"execution_log_id": 1, "notes": "QC batch 2026-02-17 certification"}'
```

---

#### GET /api/reports/{id}/

Retrieves full report details including chain verification information.

**Required role:** Any authenticated user

**Response `200 OK`:** Full CertifiedReport object

---

#### POST /api/reports/{id}/sign/

Double-authentication certification signing. This endpoint requires:
1. Password re-entry (forces explicit re-authentication)
2. Optional OTP code (if MFA is enabled for the tenant)

The signing event is recorded as a special `SIGN` operation in the audit trail with full non-repudiation metadata.

**Required role:** Principal Investigator, Admin

**Request body:**

```json
{
  "password": "SecurePass123!",
  "otp_code": "123456",
  "notes": "All data verified. Report certified for external audit submission."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `password` | string | Yes | User's current password (re-authentication) |
| `otp_code` | string | Conditional | Required if MFA is enabled for tenant |
| `notes` | string | No | Certification statement for audit trail |

**Response `200 OK`:**

```json
{
  "id": 42,
  "state": "certified",
  "certified_by": "jane.smith",
  "certified_at": "2026-02-17T16:00:00Z",
  "message": "Report certified and signed for audit submission"
}
```

**Status codes:**

| Code | Meaning |
|---|---|
| `200` | Report signed and certified |
| `400` | Report already certified or in wrong state |
| `401` | Password verification failed |
| `401` | Invalid or expired OTP |
| `403` | Insufficient permissions |

Note: Failed password attempts are recorded in the audit trail.

**curl example:**

```bash
curl -X POST https://api.bionexus.io/api/reports/42/sign/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "SecurePass123!",
    "otp_code": "123456",
    "notes": "Certified following full QC review."
  }'
```

---

#### GET /api/reports/{id}/pdf/

Downloads the certified PDF report with embedded SHA-256 hash, audit trail summary, and chain verification proof.

**Required role:** Any authenticated user

**Response:** PDF binary (`application/pdf`)

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="execution_1_certified.pdf"
X-Report-Hash: abc123def456...
```

**curl example:**

```bash
curl -X GET https://api.bionexus.io/api/reports/42/pdf/ \
  -H "Authorization: Bearer <access_token>" \
  -o certified_report_42.pdf
```

---

#### POST /api/reports/{id}/verify/

Re-verifies the integrity of a certified report. Recomputes the audit chain and confirms the report hash still matches the stored PDF.

**Required role:** Auditor, Principal Investigator, Admin

**Response `200 OK`:**

```json
{
  "report_id": 42,
  "is_valid": true,
  "chain_verified": true,
  "all_corrections_logged": true,
  "report_hash_matches": true,
  "verified_at": "2026-02-17T17:00:00Z"
}
```

---

### 6.8 Audit Trail

The audit trail is immutable. Records are created automatically by the system and cannot be modified or deleted via the API. The SHA-256 chain linking ensures any tampering with historical records is immediately detectable.

**AuditLog operations:** `CREATE`, `UPDATE`, `DELETE`, `LOGIN`, `LOGOUT`, `SIGN`

**AuditLog object:**

```json
{
  "id": 456,
  "entity_type": "ParsedData",
  "entity_id": 5,
  "operation": "UPDATE",
  "timestamp": "2026-02-17T10:35:00Z",
  "user_id": 456,
  "user_email": "jane.smith@lab.local",
  "changes": {
    "state": {
      "before": "pending",
      "after": "validated"
    },
    "corrections_count": {
      "before": 0,
      "after": 1
    }
  },
  "snapshot_before": {
    "state": "pending"
  },
  "snapshot_after": {
    "state": "validated",
    "corrections": [...],
    "validation_notes": "Verified against physical equipment list."
  },
  "signature": "abc123def456...",
  "previous_signature": "xyz789uvw123..."
}
```

---

#### GET /api/auditlog/

Queries the audit trail with optional filters. All results are scoped to the authenticated user's tenant.

**Required role:** Any authenticated user
**Required permission:** `audit:view`

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `entity_type` | string | Filter by entity (`Sample`, `ParsedData`, `CertifiedReport`, `User`, `RawFile`, `ExecutionLog`) |
| `entity_id` | integer | Filter by entity primary key |
| `operation` | string | Filter by operation (`CREATE`, `UPDATE`, `DELETE`, `LOGIN`, `LOGOUT`, `SIGN`) |
| `user_id` | integer | Filter by user who performed the action |
| `date_from` | date | Filter from date (ISO 8601: `YYYY-MM-DD`) |
| `date_to` | date | Filter to date (ISO 8601: `YYYY-MM-DD`) |
| `ordering` | string | Order by `timestamp` (default) |

**Response `200 OK`:**

```json
{
  "count": 42,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 456,
      "entity_type": "ParsedData",
      "entity_id": 5,
      "operation": "UPDATE",
      "timestamp": "2026-02-17T10:35:00Z",
      "user_email": "jane.smith@lab.local",
      "changes": {...},
      "signature": "abc123...",
      "previous_signature": "xyz789..."
    }
  ]
}
```

**curl example:**

```bash
curl -X GET "https://api.bionexus.io/api/auditlog/?entity_type=ParsedData&entity_id=5" \
  -H "Authorization: Bearer <access_token>"
```

---

#### GET /api/auditlog/{id}/

Retrieves a single audit log entry with full snapshot data.

**Required role:** Any authenticated user
**Required permission:** `audit:view`

**Response `200 OK`:** Full AuditLog object including `snapshot_before` and `snapshot_after`

**curl example:**

```bash
curl -X GET https://api.bionexus.io/api/auditlog/456/ \
  -H "Authorization: Bearer <access_token>"
```

---

#### GET /api/integrity/check/

Performs a full audit chain integrity verification for the tenant. Walks all audit records, recomputes every SHA-256 signature, and reports any tampering.

**Required role:** Auditor, Principal Investigator, Admin

**Response `200 OK`:**

```json
{
  "is_valid": true,
  "total_records": 42,
  "verified_records": 42,
  "corrupted_records": [],
  "chain_integrity_ok": true,
  "safe_to_export": true,
  "checked_at": "2026-02-17T17:00:00Z"
}
```

If tampering is detected:

```json
{
  "is_valid": false,
  "total_records": 42,
  "verified_records": 39,
  "corrupted_records": [
    {
      "id": 28,
      "error": "Signature mismatch: expected abc123..., got def456..."
    }
  ],
  "chain_integrity_ok": false,
  "safe_to_export": false,
  "checked_at": "2026-02-17T17:00:00Z"
}
```

**curl example:**

```bash
curl -X GET https://api.bionexus.io/api/integrity/check/ \
  -H "Authorization: Bearer <access_token>"
```

---

#### GET /api/auditlog/export/

Generates a certified audit trail export. The export includes:
- All audit records for the tenant (within date range)
- Chain integrity verification results
- A digital signature of the entire export payload
- Export metadata (timestamp, exporter, record count)

**Required role:** Auditor, Admin
**Required permission:** `audit:export`

**Query parameters:**

| Parameter | Description |
|---|---|
| `entity_type` | Limit export to one entity type |
| `date_from` | Export from date |
| `date_to` | Export to date |
| `format` | `json` (default) or `csv` |

**Response `200 OK`:**

```json
{
  "export_id": "audit-export-2026-02-17-a1b2c3",
  "timestamp": "2026-02-17T17:00:00Z",
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
  "records": [...],
  "export_signature": "sha256_of_entire_export...",
  "export_valid": true
}
```

**curl example:**

```bash
curl -X GET "https://api.bionexus.io/api/auditlog/export/?entity_type=Sample&date_from=2026-01-01" \
  -H "Authorization: Bearer <access_token>" \
  -o audit_export.json
```

---

### 6.9 Administration

Administration endpoints require Admin role. They manage users, roles, and tenant configuration.

---

#### GET /api/admin/users/

Lists all users in the tenant.

**Required role:** Admin
**Required permission:** `user:manage`

**Response `200 OK`:**

```json
{
  "count": 5,
  "results": [
    {
      "id": 123,
      "username": "john.doe",
      "email": "john@lab.local",
      "role": "lab_technician",
      "is_active": true,
      "last_login_ip": "192.168.1.100",
      "tenant_id": 456
    }
  ]
}
```

---

#### POST /api/admin/users/

Creates a new user in the tenant.

**Required role:** Admin
**Required permission:** `user:manage`

**Request body:**

```json
{
  "username": "alice.jones",
  "email": "alice@lab.local",
  "password": "TempPass123!",
  "role": "lab_technician",
  "first_name": "Alice",
  "last_name": "Jones"
}
```

**Response `201 Created`:** User object (without password)

---

#### PATCH /api/admin/users/{id}/

Updates a user. Used for role assignment, activation, and profile updates.

**Required role:** Admin
**Required permission:** `user:manage`

**Request body (partial):**

```json
{
  "role": "principal_investigator",
  "is_active": true
}
```

**Allowed role values:** `admin`, `principal_investigator`, `lab_technician`, `auditor`, `viewer`

**Response `200 OK`:** Updated user object

---

#### DELETE /api/admin/users/{id}/

Deactivates a user (soft delete — sets `is_active = false`). The user cannot log in. Audit trail for their past actions is preserved.

**Required role:** Admin
**Required permission:** `user:manage`

**Response `204 No Content`**

---

#### GET /api/admin/roles/

Lists all available roles and their permissions.

**Required role:** Admin
**Required permission:** `role:manage`

**Response `200 OK`:**

```json
[
  {
    "name": "admin",
    "display_name": "Administrator",
    "permissions": [
      "sample:view", "sample:create", "sample:update", "sample:delete",
      "protocol:view", "protocol:create", "protocol:update", "protocol:delete",
      "audit:view", "audit:export",
      "user:manage", "role:manage"
    ]
  },
  {
    "name": "lab_technician",
    "display_name": "Lab Technician",
    "permissions": [
      "sample:view", "sample:create", "sample:update",
      "protocol:view",
      "audit:view"
    ]
  }
]
```

---

#### GET /api/admin/tenant/

Returns configuration and metadata for the current tenant.

**Required role:** Admin

**Response `200 OK`:**

```json
{
  "id": 456,
  "name": "ACME Pharma QC Lab",
  "slug": "acme-pharma",
  "is_active": true,
  "created_at": "2025-11-01T00:00:00Z",
  "user_count": 5,
  "sample_count": 1200,
  "audit_records_count": 4872
}
```

---

#### PATCH /api/admin/tenant/

Updates tenant configuration.

**Required role:** Admin

**Request body:**

```json
{
  "name": "ACME Pharma QC Lab - Site A",
  "mfa_required": true
}
```

---

## 7. Webhook & Event System

**Status: Planned (Beta — available in v1.1)**

BioNexus will support an outbound webhook system for real-time event notifications to integrated LIMS and downstream systems.

### Planned Webhook Events

| Event | Trigger |
|---|---|
| `rawfile.uploaded` | A new file is uploaded via `POST /api/rawfiles/` |
| `parsing.created` | AI extraction completes, ParsedData is in `pending` state |
| `parsing.validated` | Human validates a ParsedData record |
| `parsing.rejected` | Human rejects a ParsedData record |
| `execution.started` | An ExecutionLog is created with status `running` |
| `execution.completed` | An ExecutionLog transitions to `completed` |
| `report.certified` | A CertifiedReport is signed and certified |
| `audit.integrity_failure` | Chain integrity check detects tampering |
| `user.login` | A user logs in |
| `user.login_failed` | A login attempt fails (security monitoring) |

### Webhook Payload Format

All webhook payloads will follow this structure:

```json
{
  "event": "parsing.validated",
  "event_id": "evt_a1b2c3d4e5f6",
  "timestamp": "2026-02-17T10:35:00Z",
  "tenant_id": 456,
  "api_version": "1.0",
  "data": {
    "id": 5,
    "state": "validated",
    "validated_by_id": 456,
    "validated_at": "2026-02-17T10:35:00Z"
  }
}
```

### Webhook Security

Webhooks will be signed with HMAC-SHA256 using a shared secret:

```
X-BioNexus-Signature: sha256=abc123def456...
X-BioNexus-Timestamp: 1708000000
```

Consumers must verify the signature before processing.

### Configuration

Webhook endpoints will be configurable via:
```
POST /api/admin/webhooks/
{
  "url": "https://your-lims.example.com/bionexus-events",
  "events": ["parsing.validated", "report.certified"],
  "secret": "your_shared_secret"
}
```

---

## 8. Error Codes

### Authentication & Authorization Errors

| Code | HTTP Status | Description |
|---|---|---|
| `ERR_AUTH_MISSING` | `401` | Authorization header not provided |
| `ERR_TOKEN_INVALID` | `401` | Token cannot be decoded |
| `ERR_TOKEN_EXPIRED` | `401` | Access token has expired |
| `ERR_TOKEN_SIGNATURE` | `401` | Token signature does not match |
| `ERR_TOKEN_TYPE` | `401` | Wrong token type (e.g., refresh used as access) |
| `ERR_USER_INACTIVE` | `403` | User account is deactivated |
| `ERR_PERMISSION_DENIED` | `403` | User lacks required permission |
| `ERR_TENANT_INACTIVE` | `403` | Tenant account is deactivated |

### Input Validation Errors

| Code | HTTP Status | Description |
|---|---|---|
| `ERR_VALIDATION` | `400` | One or more fields failed validation |
| `ERR_MISSING_FIELD` | `400` | Required field not provided |
| `ERR_INVALID_TYPE` | `400` | Field value has wrong type |
| `ERR_INVALID_ENUM` | `400` | Enum value not in allowed list |
| `ERR_INVALID_DATE` | `400` | Date/timestamp not in ISO 8601 format |
| `ERR_FILE_TOO_LARGE` | `400` | Uploaded file exceeds 100 MB limit |
| `ERR_UNSUPPORTED_MIME` | `400` | File MIME type not allowed |

### Resource Errors

| Code | HTTP Status | Description |
|---|---|---|
| `ERR_NOT_FOUND` | `404` | Resource does not exist or belongs to another tenant |
| `ERR_ALREADY_EXISTS` | `409` | Resource with this identifier already exists |
| `ERR_STATE_TRANSITION` | `400` | Invalid state transition (e.g., certifying a non-validated record) |

### Parsing & Validation Errors

| Code | HTTP Status | Description |
|---|---|---|
| `ERR_SCHEMA_VIOLATION` | `400` | AI-extracted data does not match Pydantic schema |
| `ERR_EXTRA_FIELDS` | `400` | AI output contains fields not in the allowed schema |
| `ERR_PARSE_STATE_INVALID` | `400` | ParsedData is not in `pending` state |
| `ERR_CONFIRM_SCHEMA_INVALID` | `400` | Human-confirmed data does not match schema |

### Certification Errors

| Code | HTTP Status | Description |
|---|---|---|
| `ERR_AUTH_FAILED` | `401` | Password re-verification failed during certification |
| `ERR_OTP_INVALID` | `401` | OTP code is invalid or expired |
| `ERR_CHAIN_CORRUPTED` | `409` | Audit chain integrity compromised — certification blocked |
| `ERR_REPORT_ALREADY_CERTIFIED` | `409` | Report has already been certified |
| `ERR_REPORT_REVOKED` | `409` | Report has been revoked due to chain corruption |

### Audit Trail Errors

| Code | HTTP Status | Description |
|---|---|---|
| `ERR_USER_ATTRIBUTION_MISSING` | `500` | Internal: audit trail called without user context (should never reach client) |
| `ERR_CHAIN_VERIFICATION_FAILED` | `500` | Chain verification produced unexpected error |

### Rate Limiting Errors

| Code | HTTP Status | Description |
|---|---|---|
| `ERR_RATE_LIMIT` | `429` | Rate limit exceeded |

### Server Errors

| Code | HTTP Status | Description |
|---|---|---|
| `ERR_INTERNAL` | `500` | Unexpected server error |
| `ERR_PDF_GENERATION` | `500` | PDF report generation failed (fallback to text report) |

---

## 9. SDK & Integration Guide

### How LIMS Systems and Partners Integrate

BioNexus is designed as a data integrity layer that sits between laboratory instruments and your existing LIMS. The recommended integration pattern is:

```
[Lab Instrument] → [BioNexus Box / Manual Upload] → [BioNexus API]
                                                          ↓
                                              [Webhook → Your LIMS]
```

For partners such as CSV/qualification specialists (GMP4U), the typical workflow is:

1. Instrument generates a CSV/PDF output file.
2. The BioNexus Box (or a manual upload via the React dashboard) sends the file to `POST /api/rawfiles/`.
3. The AI extraction pipeline parses the file and creates a `ParsedData` record (state: `pending`).
4. A Lab Technician or PI reviews the parsed data in the dashboard (or via API) and calls `POST /api/parsing/{id}/validate/`.
5. A PI or QA officer generates a certified report via `POST /api/reports/` and signs it with `POST /api/reports/{id}/sign/`.
6. The audit trail is available for export via `GET /api/auditlog/export/` for inspector submission.

### Python Integration Example

```python
import requests

BASE_URL = "https://api.bionexus.io"

class BioNexusClient:
    def __init__(self, username: str, password: str, tenant_slug: str):
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        self._authenticate(username, password, tenant_slug)

    def _authenticate(self, username: str, password: str, tenant_slug: str) -> None:
        response = self.session.post(f"{BASE_URL}/api/auth/login/", json={
            "username": username,
            "password": password,
            "tenant_slug": tenant_slug,
        })
        response.raise_for_status()
        tokens = response.json()
        self.session.headers["Authorization"] = f"Bearer {tokens['access']}"
        self._refresh_token = tokens["refresh"]

    def refresh_access_token(self) -> None:
        """Call before the 15-minute access token expires."""
        response = self.session.post(f"{BASE_URL}/api/auth/refresh/", json={
            "refresh": self._refresh_token,
        })
        response.raise_for_status()
        tokens = response.json()
        self.session.headers["Authorization"] = f"Bearer {tokens['access']}"
        self._refresh_token = tokens["refresh"]

    def upload_file(self, filepath: str) -> dict:
        """Upload a raw instrument output file."""
        with open(filepath, "rb") as f:
            response = self.session.post(
                f"{BASE_URL}/api/rawfiles/",
                files={"file": (filepath.split("/")[-1], f)},
                headers={"Content-Type": None},  # Let requests set multipart header
            )
        response.raise_for_status()
        return response.json()

    def list_pending_validations(self) -> list:
        """Get all ParsedData records awaiting human review."""
        response = self.session.get(f"{BASE_URL}/api/parsing/?state=pending")
        response.raise_for_status()
        return response.json()["results"]

    def validate_parsing(self, parsed_data_id: int, confirmed_data: dict, notes: str = "") -> dict:
        """Validate AI-extracted data with optional corrections."""
        response = self.session.post(
            f"{BASE_URL}/api/parsing/{parsed_data_id}/validate/",
            json={"confirmed_data": confirmed_data, "validation_notes": notes},
        )
        response.raise_for_status()
        return response.json()

    def certify_report(self, report_id: int, password: str, notes: str = "") -> dict:
        """Sign and certify a report (double-auth)."""
        response = self.session.post(
            f"{BASE_URL}/api/reports/{report_id}/sign/",
            json={"password": password, "notes": notes},
        )
        response.raise_for_status()
        return response.json()

    def export_audit_trail(self, entity_type: str, date_from: str, date_to: str) -> dict:
        """Export the certified audit trail for a date range."""
        response = self.session.get(
            f"{BASE_URL}/api/auditlog/export/",
            params={"entity_type": entity_type, "date_from": date_from, "date_to": date_to},
        )
        response.raise_for_status()
        return response.json()


# Usage example
client = BioNexusClient("john.doe", "SecurePass123!", "acme-labs")

# Upload instrument output
raw_file = client.upload_file("/data/spectrophotometer_output_2026-02-17.csv")
print(f"Uploaded: {raw_file['file_hash']}")

# Check for pending validations
pending = client.list_pending_validations()
for item in pending:
    print(f"Pending validation: ParsedData ID {item['id']}, confidence: {item['extraction_confidence']}")
```

### curl Examples (Complete Workflow)

```bash
# 1. Authenticate
TOKEN=$(curl -s -X POST https://api.bionexus.io/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "john.doe", "password": "SecurePass123!", "tenant_slug": "acme-labs"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access'])")

# 2. Upload a raw file
curl -X POST https://api.bionexus.io/api/rawfiles/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@equipment_output.csv"

# 3. List pending validations
curl -X GET "https://api.bionexus.io/api/parsing/?state=pending" \
  -H "Authorization: Bearer $TOKEN"

# 4. Validate parsing (ParsedData ID = 5)
curl -X POST https://api.bionexus.io/api/parsing/5/validate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirmed_data": {
      "equipment_records": [...],
      "sample_records": [],
      "extraction_warnings": []
    },
    "validation_notes": "Verified and approved"
  }'

# 5. Generate a certified report (ExecutionLog ID = 1)
curl -X POST https://api.bionexus.io/api/reports/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"execution_log_id": 1, "notes": "QC batch certification"}'

# 6. Sign the report (Report ID = 42, double-auth)
curl -X POST https://api.bionexus.io/api/reports/42/sign/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "SecurePass123!", "notes": "Certified for audit"}'

# 7. Download the certified PDF
curl -X GET https://api.bionexus.io/api/reports/42/pdf/ \
  -H "Authorization: Bearer $TOKEN" \
  -o certified_report.pdf

# 8. Check chain integrity
curl -X GET https://api.bionexus.io/api/integrity/check/ \
  -H "Authorization: Bearer $TOKEN"

# 9. Export audit trail
curl -X GET "https://api.bionexus.io/api/auditlog/export/?entity_type=ParsedData&date_from=2026-02-01" \
  -H "Authorization: Bearer $TOKEN" \
  -o audit_export.json
```

### Integration Notes

- **Token refresh**: Access tokens expire in 15 minutes. Implement token refresh logic in your integration. A good pattern is to refresh proactively when the token is within 2 minutes of expiry.
- **Idempotent file uploads**: If you upload the same file twice (same SHA-256), you will receive `200 OK` with the existing RawFile record. You do not need to deduplicate on your side.
- **Tenant isolation**: Your `tenant_id` is baked into the JWT. You never need to pass it in request bodies. Do not build multi-tenant logic on the client side.
- **Audit trail immutability**: Do not attempt to modify or delete audit records via the API or database. Any tampering will be detected by the SHA-256 chain and will block report certification.
- **Soft deletes**: When you delete a sample or protocol, the data is not removed. Your integration should handle the case where a `GET` returns a soft-deleted object if you pass `include_deleted=true`.

---

## 10. OpenAPI / Swagger

**Status: Planned (v1.1)**

BioNexus will generate an OpenAPI 3.1 specification using `drf-spectacular`. This will provide:

- Machine-readable API schema (`/api/schema/`)
- Swagger UI (`/api/docs/`)
- ReDoc UI (`/api/redoc/`)
- Downloadable YAML/JSON schema for SDK generation

To add `drf-spectacular` to the project:

```python
# In settings.py
INSTALLED_APPS = [
    ...
    "drf_spectacular",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "BioNexus API",
    "DESCRIPTION": "GxP-compliant SaaS API for lab instrument data integration",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/",
}
```

```python
# In urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
```

Until the auto-generated schema is available, this document is the authoritative API reference.

---

## 11. Changelog

### API Version 1.0 — 2026-02-28 (Initial Release)

**Auth**
- `POST /api/auth/login/` — JWT login with audit trail
- `POST /api/auth/refresh/` — Token refresh with rotation
- `POST /api/auth/logout/` — Session invalidation
- `POST /api/auth/verify-password/` — Password re-verification for sensitive operations

**Samples**
- `GET/POST /api/samples/` — List and create
- `GET/PUT/PATCH/DELETE /api/samples/{id}/` — CRUD with audit trail and soft delete

**Protocols**
- `GET/POST /api/protocols/` — List and create
- `GET/PUT/PATCH/DELETE /api/protocols/{id}/` — CRUD with audit trail and soft delete

**Data Ingestion**
- `POST /api/rawfiles/` — Immutable file upload with SHA-256 hashing
- `GET /api/rawfiles/` — List uploaded files
- `GET /api/rawfiles/{id}/` — File metadata
- `GET /api/rawfiles/{id}/content/` — File download
- `POST /api/rawfiles/{id}/verify/` — Hash integrity check

**Parsing & Validation**
- `GET /api/parsing/` — List ParsedData records
- `GET /api/parsing/{id}/` — ParsedData detail
- `POST /api/parsing/{id}/validate/` — Human validation with corrections
- `POST /api/parsing/{id}/reject/` — Human rejection
- `GET /api/parsing/{id}/corrections/` — Correction history
- `GET /api/parsing/{id}/rawfile/` — Source file download

**Execution Logs**
- `GET/POST /api/executions/` — List and create
- `GET/PATCH /api/executions/{id}/` — Detail and update
- `POST /api/executions/{id}/step/` — Record step completion

**Certification & Reports**
- `GET/POST /api/reports/` — List and generate
- `GET /api/reports/{id}/` — Report detail
- `POST /api/reports/{id}/sign/` — Double-auth certification signing
- `GET /api/reports/{id}/pdf/` — PDF download
- `POST /api/reports/{id}/verify/` — Re-verify integrity

**Audit Trail**
- `GET /api/auditlog/` — Query with filters
- `GET /api/auditlog/{id}/` — Single entry
- `GET /api/auditlog/export/` — Certified export
- `GET /api/integrity/check/` — Full chain verification

**Administration**
- `GET/POST /api/admin/users/` — User management
- `PATCH/DELETE /api/admin/users/{id}/` — User update and deactivation
- `GET /api/admin/roles/` — Role and permission listing
- `GET/PATCH /api/admin/tenant/` — Tenant configuration

### Upcoming in v1.1

- Explicit `/api/v1/` version prefix
- OpenAPI schema (`/api/schema/`, `/api/docs/`)
- Webhook registration and delivery
- Equipment CRUD endpoints (`/api/equipment/`)
- OTP management endpoints (`/api/auth/otp/`)
- Bulk sample import endpoint
- Full-text search on audit trail

---

**Document maintained by:** BioNexus Engineering
**Compliance note:** This document is subject to change control. All API changes with compliance impact must be reviewed against 21 CFR Part 11 requirements before deployment.
