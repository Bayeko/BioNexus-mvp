# BioNexus Security Assessment Playbook

## Document Information

**Document ID:** BNX-SEC-001
**Version:** 1.0
**Status:** Approved — Active Security Program
**Date:** 2026-02-28
**Prepared by:** BioNexus Security Team
**Review Cycle:** Annual (or following any significant security event)
**Classification:** Confidential — Internal Use / Controlled Distribution to Customers

---

## Table of Contents

1. [Purpose and Audience](#1-purpose-and-audience)
2. [Threat Model — STRIDE Analysis](#2-threat-model--stride-analysis)
3. [Attack Surface Inventory](#3-attack-surface-inventory)
4. [Security Controls Matrix](#4-security-controls-matrix)
5. [Penetration Testing Program](#5-penetration-testing-program)
6. [Pen Test Scenarios](#6-pen-test-scenarios)
7. [Vulnerability Management](#7-vulnerability-management)
8. [Incident Response Plan](#8-incident-response-plan)
9. [Security Monitoring](#9-security-monitoring)
10. [BioNexus Box Device Security](#10-bionexus-box-device-security)
11. [Third-Party Risk Management](#11-third-party-risk-management)
12. [Compliance Alignment](#12-compliance-alignment)
13. [Customer Security FAQ](#13-customer-security-faq)
14. [Appendix: Pre-Deployment Security Checklist](#14-appendix-pre-deployment-security-checklist)

---

## 1. Purpose and Audience

### 1.1 Why This Document Exists

BioNexus operates in GxP-regulated pharmaceutical and biotechnology environments where a security breach is not merely a business risk — it is a regulatory compliance event. Under 21 CFR Part 11, EU Annex 11, and GAMP5, BioNexus must demonstrate that its computer systems are secure, validated, and that audit trail integrity is continuously protected.

This document serves two distinct but overlapping purposes:

**Internal Security Program Guide**
This is the operational reference for BioNexus's security team. It defines the threat model, attack surface, security controls, pen test program, vulnerability management SLAs, incident response procedures, and monitoring strategy. It is the authoritative source for how BioNexus secures its SaaS platform and hardware devices.

**Customer-Facing Security Posture Document**
Enterprise pharma customers conduct formal infosec reviews as part of their vendor qualification process. Quality and IT security teams at customer sites require evidence that BioNexus meets their information security standards before approving BioNexus for GxP use. This document provides pre-answered responses to the most common enterprise security questionnaire questions and can be shared under NDA with qualified customer reviewers.

### 1.2 Audience

| Audience | Use |
|----------|-----|
| BioNexus Security / Engineering | Operational security program guidance |
| BioNexus QA | Compliance evidence for supplier assessments |
| Customer IT Security / CISO | Vendor security review and qualification |
| Customer QA / Validation | GxP computer system validation (CSV) dossier |
| Third-Party Pen Testers | Rules of engagement and scope definition |
| BioNexus Leadership | Risk awareness and investment prioritization |

### 1.3 Scope

This playbook covers the complete BioNexus platform:

- **GCP Cloud Backend**: Cloud Run (Django REST API), Cloud SQL (PostgreSQL), Cloud Storage (GCS), Cloud Armor WAF, Secret Manager, IAM
- **BioNexus Box**: Raspberry Pi CM4 / industrial SBC edge gateway device at customer lab sites
- **Communication Channels**: HTTPS/TLS between BioNexus Box and GCP, browser to GCP; RS232/USB between lab instruments and BioNexus Box
- **User Interfaces**: React SPA dashboard, Django admin interface, management console
- **CI/CD Pipeline**: GitHub, GitHub Actions, Cloud Build, Artifact Registry
- **Third-Party Integrations**: GCP services, AI parsing providers, Python package dependencies

---

## 2. Threat Model — STRIDE Analysis

STRIDE is applied across the five primary BioNexus components: the Django REST API, the PostgreSQL database, the BioNexus Box hardware gateway, the GCP infrastructure layer, and the user interface.

### 2.1 STRIDE Overview

| Threat Category | Definition | BioNexus Risk |
|----------------|------------|---------------|
| **S**poofing | Attacker impersonates a legitimate user or device | HIGH — device impersonation could inject fabricated instrument data into the audit trail |
| **T**ampering | Unauthorized modification of data | CRITICAL — audit trail tampering would invalidate regulatory compliance |
| **R**epudiation | Denying having performed an action | HIGH — user denying data modifications triggers audit investigation overhead |
| **I**nformation Disclosure | Unauthorized access to data | HIGH — instrument data, protocols, and tenant configurations are proprietary |
| **D**enial of Service | Making a system unavailable | MEDIUM — lab instruments cannot upload during outage; local buffering mitigates to 8h |
| **E**levation of Privilege | Gaining unauthorized permissions | HIGH — cross-tenant access or role escalation bypasses all access controls |

### 2.2 Threat Analysis by Component

#### 2.2.1 Django REST API

| STRIDE | Specific Threat | Likelihood | Impact | Existing Mitigations |
|--------|----------------|------------|--------|----------------------|
| Spoofing | Forged JWT token used to authenticate as another user | Low | Critical | JWT signature verification, HS256 with 50+ char secret, 15-minute expiry |
| Spoofing | Refresh token stolen and replayed after expiry | Low | High | 7-day expiry, token_id rotation on refresh, HTTPS-only |
| Spoofing | BioNexus Box impersonated via stolen API key | Low | Critical | API key stored encrypted on device; TLS cert pinning |
| Tampering | Injection of malicious SQL via API parameters | Low | Critical | Django ORM parameterized queries, Cloud Armor SQLi rules |
| Tampering | Mass assignment of protected model fields | Low | High | Django REST Framework explicit serializer fields, no wildcard serializers |
| Repudiation | User denies creating or modifying a record | Very Low | High | Mandatory user_id + user_email on all AuditLog entries; ValueError on missing |
| Information Disclosure | Unauthenticated access to API endpoints | Low | Critical | `@authenticate_required` decorator on all non-public endpoints |
| Information Disclosure | Cross-tenant data leak via missing tenant_id filter | Medium | Critical | `@tenant_context` decorator; repository layer always filters by tenant_id |
| Information Disclosure | Stack traces exposed in error responses | Low | Medium | DEBUG=False in production; custom error handlers return generic messages |
| Denial of Service | API flooded with unauthenticated requests | Medium | Medium | Cloud Armor rate limiting 100 req/min/IP, DDoS protection |
| Denial of Service | Resource exhaustion via large file uploads | Low | Medium | Request size limits enforced at LB and Django middleware |
| Elevation of Privilege | RBAC bypass — accessing endpoint without required permission | Low | High | `@permission_required` decorator enforced at view layer |
| Elevation of Privilege | Vertical privilege escalation — technician to admin | Very Low | Critical | Permissions defined in DB, not JWT; permission checks live server-side |

#### 2.2.2 PostgreSQL Database (Cloud SQL)

| STRIDE | Specific Threat | Likelihood | Impact | Existing Mitigations |
|--------|----------------|------------|--------|----------------------|
| Spoofing | Application connecting to wrong database instance | Very Low | High | Cloud SQL Auth Proxy with Workload Identity; no password in connection string |
| Tampering | Direct audit_log table UPDATE/DELETE | Very Low | Critical | PostgreSQL Row Level Security: INSERT-only policy for app role; UPDATE/DELETE denied |
| Tampering | Django migration dropping audit_log or altering columns | Low | Critical | Deletion protection on Cloud SQL; migration review gate in CI |
| Repudiation | Claim audit records are fabricated | Very Low | High | SHA-256 signature chain; export signature; chain verification endpoint |
| Information Disclosure | Database credential exposure | Very Low | Critical | Secrets in Secret Manager; no plaintext passwords in config or environment files |
| Information Disclosure | Network sniffing of database traffic | Very Low | High | Private VPC only; Cloud SQL has no public IP; SSL enforced |
| Denial of Service | Long-running queries blocking connection pool | Low | Medium | 30-second statement timeout; query insights monitoring |
| Elevation of Privilege | App database user granted DDL permissions | Very Low | High | Application user role: SELECT, INSERT, UPDATE on application tables; no CREATE/DROP |

#### 2.2.3 BioNexus Box (Hardware Gateway)

| STRIDE | Specific Threat | Likelihood | Impact | Existing Mitigations |
|--------|----------------|------------|--------|----------------------|
| Spoofing | Rogue device substituted using same device_id | Low | Critical | API key is device-specific and encrypted; Phase 2: mTLS with TPM-resident cert |
| Spoofing | API key brute-forced | Very Low | Critical | 256-bit random key; rate limiting on authentication endpoint |
| Tampering | Local SQLite queue modified before upload | Low | High | packet_sha256 verified on upload; mismatch triggers rejection and flagging |
| Tampering | Firmware replaced with malicious version | Low | Critical | Ed25519 signed firmware bundles; dm-verity protected root filesystem; secure boot (Phase 2) |
| Tampering | Instrument configuration file modified | Low | Medium | config.yaml changes logged in local audit log; version tracked in cloud registry |
| Repudiation | Deny a device sent specific data | Very Low | Medium | batch_sha256, packet_sha256 are cryptographic commitments |
| Information Disclosure | API key extracted from device | Low | Critical | AES-256 encrypted secrets file; LUKS2 encrypted data partition |
| Information Disclosure | Instrument data extracted from local queue | Low | High | LUKS2 encryption; TPM-sealed key (Phase 2) |
| Information Disclosure | SSH session eavesdropped | Very Low | Medium | SSH key-based auth; TLS on all communications; management IP allowlist |
| Denial of Service | Network disconnection causing data loss | Medium | High | 7-day local buffer; store-and-forward; gap detection on reconnect |
| Denial of Service | Device power cycling / physical sabotage | Low | High | SQLite WAL with synchronous=FULL; power loss recovery on boot |
| Elevation of Privilege | SSH as root to gain full device control | Low | Critical | Root SSH disabled; BioNexus services run as unprivileged `bionexus` user |
| Elevation of Privilege | Exploit in Python bionexus-agent process | Very Low | High | Process runs as UID 999; nftables blocks unexpected outbound; minimal installed packages |

#### 2.2.4 GCP Infrastructure Layer

| STRIDE | Specific Threat | Likelihood | Impact | Existing Mitigations |
|--------|----------------|------------|--------|----------------------|
| Spoofing | Compromised CI/CD pipeline deploys malicious image | Low | Critical | Workload Identity Federation; no service account keys; manual approval gate for production |
| Tampering | Direct modification of GCS audit export objects | Very Low | Critical | GCS retention policies (7-year locked); object versioning; export signature validation |
| Tampering | Terraform state manipulation to change IAM bindings | Very Low | High | Terraform state in GCS with versioning; access restricted to infra SA |
| Repudiation | No record of who accessed infrastructure | Very Low | Medium | Cloud Audit Logs capture all IAM, API, and data access events |
| Information Disclosure | GCS bucket with public access | Very Low | Critical | uniform_bucket_level_access = true; no allUsers or allAuthenticatedUsers bindings |
| Information Disclosure | Secrets in environment variables or logs | Very Low | Critical | Secrets from Secret Manager only; log_level = info (no debug in production) |
| Denial of Service | Cloud Run scaled to 0, cold start under attack | Low | Medium | minScale = 1; Cloud Armor rate limiting before traffic reaches Cloud Run |
| Elevation of Privilege | Service account key file exfiltration | Very Low | Critical | No service account key files; Workload Identity only |
| Elevation of Privilege | IAM privilege escalation via overly permissive roles | Very Low | High | No owner/editor roles; resource-scoped bindings; IAM Recommender reviews |

#### 2.2.5 User Interface (React SPA / Browser)

| STRIDE | Specific Threat | Likelihood | Impact | Existing Mitigations |
|--------|----------------|------------|--------|----------------------|
| Spoofing | Session hijacking via XSS stealing JWT from localStorage | Medium | High | JWT in httpOnly cookies (planned); Cloud Armor XSS rules |
| Tampering | CSRF attack — forging authenticated requests | Low | High | Django CSRF middleware; SameSite cookie attribute; CORS policy |
| Tampering | DOM-based XSS via malicious instrument data rendered | Low | Medium | React's default HTML escaping; Content Security Policy header |
| Information Disclosure | Sensitive data in browser history / logs | Low | Low | No PII in BioNexus; instrument data pseudonymized by sample ID |
| Information Disclosure | Clickjacking embedding BioNexus in iframe | Very Low | Low | X-Frame-Options: DENY header; Content Security Policy frame-ancestors: none |
| Denial of Service | Browser-side resource exhaustion from large dataset rendering | Low | Low | Pagination enforced on all list API endpoints |

---

## 3. Attack Surface Inventory

### 3.1 Public Network Endpoints

| Endpoint | Protocol | Authentication | Purpose | Exposure |
|----------|----------|----------------|---------|----------|
| `https://api.bionexus.io/api/auth/login` | HTTPS POST | None (credential submission) | User authentication | Public internet |
| `https://api.bionexus.io/api/auth/refresh` | HTTPS POST | Refresh JWT | Token refresh | Public internet |
| `https://api.bionexus.io/api/health/` | HTTPS GET | None | Load balancer health probe | Public internet |
| `https://api.bionexus.io/api/v1/*` | HTTPS | Bearer JWT | All application API endpoints | Public internet (JWT-gated) |
| `https://api.bionexus.io/api/v1/ingest/readings/` | HTTPS POST | Device API key + X-Device-ID | BioNexus Box data ingestion | Public internet (device key-gated) |
| `https://api.bionexus.io/api/v1/devices/heartbeat/` | HTTPS POST | Device API key | BioNexus Box heartbeat | Public internet (device key-gated) |
| `https://app.bionexus.io/` | HTTPS | None (SPA shell) | React SPA delivery | Public internet |
| `https://api.bionexus.io/admin/` | HTTPS | Django superuser credentials | Django admin interface | Public internet — RESTRICT IN PRODUCTION |

**Django Admin Note**: The `/admin/` path MUST be moved to a non-guessable path (e.g., `/internal/mgmt-a7f3b2/`) and restricted by Cloud Armor IP allowlist to BioNexus management IP ranges. Exposure of the default `/admin/` path is a pre-deployment security requirement.

### 3.2 Internal Network Interfaces

| Interface | Protocol | Exposure | Authentication |
|-----------|----------|----------|----------------|
| Cloud SQL Unix socket | PostgreSQL over Unix socket | VPC-private only; Cloud Run only | Cloud SQL Auth Proxy + Workload Identity |
| Cloud SQL Private IP (10.0.2.x) | PostgreSQL TCP | VPC-private only | SSL + password |
| Cloud Run to Cloud SQL | Cloud SQL Auth Proxy | VPC Connector only | IAM Workload Identity |
| Cloud Run to Secret Manager | HTTPS | GCP internal APIs | Workload Identity |
| Cloud Run to GCS | HTTPS | GCP internal APIs | Workload Identity |
| Cloud Run to Cloud Tasks | HTTPS | GCP internal APIs | Workload Identity |

### 3.3 BioNexus Box Physical and Network Interfaces

| Interface | Protocol | Exposure | Authentication |
|-----------|----------|----------|----------------|
| RS232 DB9 ports (x2) | Serial RS232 | Physical lab access | None (physical security relies on lab access controls) |
| USB-A ports (x2) | USB serial | Physical lab access | None |
| Ethernet ETH-1 (RJ45) | TCP/IP | Lab network segment | — |
| SSH (TCP 22) | SSH | Lab network segment; allowlisted | Key-based auth (ED25519/RSA-4096); no password auth |
| HDMI port | DisplayPort (sealed) | Physical — port sealed | N/A — disabled in device tree, port sealed with tamper-evident label |
| Hardware reset button | Physical | Recessed; requires pin | Physical access; event logged to cloud |

**Box Outbound Connections (nftables allowlist):**
- HTTPS TCP 443 → `api.bionexus.io` only
- NTP UDP 123 → configured NTP servers
- DNS UDP/TCP 53 → configured resolvers

All other outbound traffic is blocked by nftables rules.

### 3.4 CI/CD Pipeline Interfaces

| Interface | Authentication | Access Granted |
|-----------|----------------|----------------|
| GitHub repository | GitHub SSO + MFA enforced | Source code, Actions secrets |
| GitHub Actions → GCP | Workload Identity Federation (OIDC) | Staging: Cloud Build trigger |
| GitHub Actions → GCP (prod) | Workload Identity Federation (OIDC) + manual approval | Production: Cloud Build trigger |
| Cloud Build → Artifact Registry | Service account (bionexus-cloudbuild-sa) | Push Docker images |
| Cloud Build → Cloud Run | Service account | Deploy new revisions |
| Cloud Build → Cloud SQL | Service account via proxy | Run Django migrations |

### 3.5 Third-Party Integrations

| Integration | Data Shared | Authentication | Data Direction |
|-------------|-------------|----------------|----------------|
| GCP Cloud SQL | Instrument readings, audit logs, user data | Cloud SQL Auth Proxy + IAM | Bidirectional |
| GCP Cloud Storage | Raw instrument files, audit exports | IAM Workload Identity | Upload from backend |
| GCP Secret Manager | Secret values | IAM Workload Identity | Read-only from backend |
| GCP Cloud Tasks | Job queue payloads | IAM Workload Identity | Enqueue from backend |
| GCP Cloud Armor | No data stored | N/A | Inline WAF inspection |
| AI Parsing Provider (future) | Anonymized instrument data snippets | API key | Outbound |
| SendGrid (email) | Alert notifications, report delivery emails | API key | Outbound |
| Firebase Hosting | React SPA static assets | Service account | Deploy from CI/CD |

### 3.6 Administrative Interfaces

| Interface | Location | Authentication | Restriction |
|-----------|----------|----------------|-------------|
| GCP Console | `console.cloud.google.com` | Google SSO + enforced MFA | Authorized BioNexus engineers only; IAM-gated |
| Django Admin | `https://api.bionexus.io/admin/` (must be relocated) | Django superuser | IP allowlist + strong credentials |
| Cloud SQL direct access | Via Cloud SQL Auth Proxy | Proxy IAM + DB password | Break-glass only; time-limited IAM condition |
| BioNexus Box SSH | Device IP, port 22 | SSH key (ED25519) | BioNexus management IP range only |
| Box Management Console (Cloud) | Management plane endpoint | JWT + admin role | BioNexus admin role required |

---

## 4. Security Controls Matrix

### 4.1 Controls Mapped to Threats

| Threat Category | Threat | Control | Implementation |
|----------------|--------|---------|----------------|
| Spoofing — Users | JWT token forgery | JWT signature verification | HS256 with minimum 50-char SECRET_KEY; signature checked on every request |
| Spoofing — Users | Session hijacking | Short-lived access tokens | 15-minute access token expiry; refresh rotation |
| Spoofing — Devices | Rogue BioNexus Box | Device API key authentication | 256-bit random key, encrypted at rest on device |
| Spoofing — Devices | mTLS impersonation (Phase 2) | X.509 device certificates | TPM-resident private key; BioNexus internal CA; OCSP revocation |
| Tampering — Audit Trail | AuditLog record modification | PostgreSQL RLS | INSERT-only policy; no UPDATE/DELETE for application role |
| Tampering — Audit Trail | Audit trail chain integrity | SHA-256 hash chaining | Each AuditLog.signature covers previous_signature; chain verification endpoint |
| Tampering — Data in Transit | MITM modification of API traffic | TLS 1.3 | TLS 1.3 enforced; TLS 1.2 AEAD fallback; TLS 1.0/1.1 disabled |
| Tampering — Box Data | Local queue manipulation | SHA-256 packet hashing | raw_sha256 + packet_sha256 computed on Box; verified on ingestion |
| Tampering — Firmware | Malicious firmware update | Ed25519 firmware signing | All firmware bundles signed; signature verified before installation |
| Tampering — Web | SQL injection | WAF + ORM | Cloud Armor sqli-v33-stable rules; Django ORM parameterized queries always |
| Tampering — Web | XSS | WAF + React escaping | Cloud Armor xss-v33-stable rules; React default HTML escaping; CSP header |
| Tampering — Web | CSRF | CSRF middleware | Django CSRF middleware; SameSite=Strict cookie; CORS allowlist |
| Repudiation | User denying actions | Mandatory user attribution | user_id + user_email mandatory on AuditLog.record(); ValueError raised if absent |
| Repudiation | Export integrity | Export signing | SHA-256 signature over entire export payload; export_signature in every certified export |
| Information Disclosure — Cross-tenant | Tenant data leakage | Multi-tenant isolation | tenant_id FK on all data models; @tenant_context decorator; repository-layer filter |
| Information Disclosure — Secrets | Credential exposure | Secret Manager | All secrets in GCP Secret Manager; no hardcoded secrets; no secrets in git |
| Information Disclosure — Network | Traffic interception | TLS everywhere | HTTPS enforced end-to-end; HTTP → HTTPS redirect at load balancer; HSTS header |
| Information Disclosure — Database | Database credential exposure | Cloud SQL Auth Proxy + IAM | No database password in environment for Cloud Run; Unix socket via proxy |
| Information Disclosure — Files | GCS unauthorized access | IAM + bucket policy | uniform_bucket_level_access; no allUsers; signed URLs for Box uploads (15-min expiry) |
| Denial of Service | API flooding | Rate limiting + WAF | Cloud Armor: 100 req/min/IP on /api/*; DDoS adaptive protection |
| Denial of Service — Box | Network outage | Store-and-forward | Local SQLite queue; 7-day buffer at standard sampling rates; backlog upload on reconnect |
| Elevation of Privilege — Vertical | Role escalation | RBAC + server-side permission checks | 5 roles; permissions stored in database; @permission_required enforced at view layer |
| Elevation of Privilege — Horizontal | Cross-tenant access | Tenant isolation | @tenant_context; tenant_id always required; no global queryset access in application code |
| Elevation of Privilege — Infrastructure | Overprivileged GCP service accounts | IAM least privilege | No owner/editor roles; resource-scoped bindings; Workload Identity; no SA key files |

### 4.2 Defense-in-Depth Architecture

```
[Internet / Lab Network]
         │
[Cloud Armor WAF]          ← Layer 1: DDoS, SQLi, XSS, rate limiting
         │
[TLS 1.3 Termination]      ← Layer 2: Encryption in transit
         │
[JWT / API Key Auth]       ← Layer 3: Identity verification
         │
[@tenant_context]          ← Layer 4: Tenant isolation enforcement
         │
[@permission_required]     ← Layer 5: RBAC permission enforcement
         │
[Repository Layer filter]  ← Layer 6: Always-on tenant_id query filter
         │
[PostgreSQL RLS]           ← Layer 7: Database-level audit immutability
         │
[SHA-256 Chain]            ← Layer 8: Cryptographic integrity verification
```

---

## 5. Penetration Testing Program

### 5.1 Program Overview

BioNexus conducts formal penetration testing as part of its security program. In GxP-regulated environments, penetration testing serves as both a security control and a compliance artifact referenced in Computer System Validation (CSV) documentation and supplier qualification assessments.

### 5.2 Testing Schedule

| Test Type | Frequency | Trigger |
|-----------|-----------|---------|
| Full External Pen Test (API + Web) | Annually | Scheduled; calendar Q2 each year |
| BioNexus Box Device Assessment | Annually | Aligned with external pen test |
| Internal Pen Test (infrastructure + IAM) | Semi-annually | Scheduled Q1 and Q3 |
| Code Security Review (manual) | Per major release | Any release tagged as MAJOR or MINOR |
| Automated SAST | Every CI build | Triggered by every pull request and branch push |
| Automated DAST | Weekly | Scheduled against staging environment |
| Dependency Vulnerability Scan | Daily | Scheduled; automated via Dependabot + pip-audit |

### 5.3 Scope Definition

#### 5.3.1 In-Scope (External Pen Test)

- `https://api.bionexus.io` — all API endpoints including `/api/v1/*`, `/api/auth/*`, `/admin/`
- `https://app.bionexus.io` — React SPA frontend
- BioNexus Box device (physical device or identical production image in isolated test environment)
- BioNexus Box → GCP communication channel (tested against staging environment)
- Staging GCP environment: `bionexus-staging` project (NOT production)
- CI/CD pipeline security review (GitHub Actions, Cloud Build — configuration review, not active exploitation)

#### 5.3.2 Out-of-Scope

- GCP underlying infrastructure (Google's responsibility; covered by GCP's own pen testing and third-party audits)
- Customer lab network infrastructure
- Customer IT systems
- Production Cloud SQL instance (test against staging only)
- Production GCS buckets (use staging buckets only)
- Third-party instrument manufacturers' systems
- Social engineering / phishing tests (require separate authorization and HR involvement)
- Physical penetration of BioNexus offices

#### 5.3.3 Staging Environment for Testing

All active exploitation tests MUST target the staging environment (`bionexus-staging` GCP project). The staging environment is a production-equivalent configuration with:

- Identical Django codebase
- Identical Cloud Armor rules
- Test tenant data only (no real customer data)
- Identical Box firmware on test device
- Separated database (no production data)

### 5.4 Rules of Engagement

```
PENETRATION TEST RULES OF ENGAGEMENT
BioNexus MVP — Version 1.0

1. AUTHORIZATION: Testing is authorized only against the specifically named
   in-scope systems listed in Section 5.3.1. Written authorization signed
   by BioNexus CISO/CTO is required before testing begins.

2. ENVIRONMENT: Active exploitation ONLY against staging environment
   (bionexus-staging). Production systems may be passively enumerated
   (DNS, certificate transparency, public headers) but not actively exploited.

3. TIMING: Testing windows must be agreed in advance. Notify BioNexus
   security team at least 48 hours before beginning active exploitation.
   Default testing window: Monday–Thursday, 09:00–17:00 CET.

4. DATA: No real customer data to be accessed, extracted, or stored.
   If real data is inadvertently encountered, stop immediately and notify
   BioNexus security within 1 hour.

5. DESTRUCTIVE ACTIONS: No destructive actions (data deletion, database
   corruption, firmware bricking) without explicit written approval per action.
   Denial-of-service testing only with advance notice and time limits (max 15 min).

6. REPORTING: Preliminary findings within 5 business days of test completion.
   Final report within 20 business days. Report format: executive summary +
   technical findings with CVSS scoring + remediation recommendations.

7. CONFIDENTIALITY: All findings are confidential. NDA required. Findings
   not to be shared with third parties without written consent.

8. ESCALATION: Critical findings (CVSS ≥ 9.0) to be communicated within
   24 hours via secure channel (encrypted email or Signal).

9. COMPLIANCE NOTE: Findings and remediation status may be referenced in
   GxP compliance documentation. Pen test report may be shared under NDA
   with customer qualification teams.
```

### 5.5 Pen Test Firm Qualification Criteria

Preferred pen test providers must demonstrate:

- Experience with GxP-regulated SaaS environments (pharmaceutical / biotech)
- Experience with IoT / embedded device security (for BioNexus Box assessment)
- OSCP or CREST-certified testers on the engagement
- Verifiable references from comparable engagements
- Ability to provide findings in a format suitable for GxP audit packages

---

## 6. Pen Test Scenarios

### 6.1 Authentication Bypass Attempts

| ID | Test Case | Method | Expected Result | Notes |
|----|-----------|--------|-----------------|-------|
| AUTH-01 | Login with no credentials | POST /api/auth/login with empty body | HTTP 400 | Validate error message reveals no info about valid users |
| AUTH-02 | Login with valid username, invalid password | Repeated attempts | HTTP 401; no lockout bypass | Verify account lockout after N attempts |
| AUTH-03 | Brute-force login endpoint | 1000 requests/min | HTTP 429 from Cloud Armor after 100 req/min | Rate limiting verification |
| AUTH-04 | Use expired access token | Token with exp in past | HTTP 401 | No grace period |
| AUTH-05 | Manipulate JWT payload without re-signing | Decode JWT, change role, re-encode with original header | HTTP 401 | Signature mismatch |
| AUTH-06 | JWT algorithm confusion (HS256 vs RS256) | Submit token with `"alg": "none"` | HTTP 401 | Algorithm forced to HS256 only |
| AUTH-07 | Refresh token replay after use | Use same refresh token twice | Second use: HTTP 401 | Token rotation must invalidate old token |
| AUTH-08 | Refresh token from different tenant | Use tenant A's refresh token against tenant B's user | HTTP 401 | Tenant_id claim must match |
| AUTH-09 | JWT secret brute force (offline) | Attempt to crack JWT signature | Should be computationally infeasible | Validates SECRET_KEY entropy |
| AUTH-10 | Password reset token replay | Use password reset link twice | Second use: HTTP 410 or 401 | Single-use token enforcement |
| AUTH-11 | Device API key replay from different IP | Use valid Box API key from non-Box IP | Should function (no IP binding in MVP) | Note for Phase 2 IP binding |
| AUTH-12 | Missing Authorization header | Call protected endpoint without header | HTTP 401 | No fallback to anonymous access |

### 6.2 RBAC Escalation

#### Horizontal Escalation (Cross-Tenant)

| ID | Test Case | Method | Expected Result |
|----|-----------|--------|-----------------|
| RBAC-H01 | Access another tenant's samples | Authenticate as Tenant A user; GET /api/v1/samples/ with Tenant B sample IDs in query params | HTTP 404 (not 403 — don't reveal existence) |
| RBAC-H02 | Direct object reference — tenant B sample | GET /api/v1/samples/{tenant_b_sample_id}/ with Tenant A JWT | HTTP 404 |
| RBAC-H03 | Modify tenant B's audit log via export | POST /api/v1/audit/export/ with tenant_id=B in body while authenticated as Tenant A | Rejected; only Tenant A exports returned |
| RBAC-H04 | Register instrument under different tenant | POST /api/v1/instruments/ with tenant_id=B in body | Instrument created under Tenant A regardless of body; or HTTP 403 |
| RBAC-H05 | Access tenant B via BioNexus Box API key | POST /api/v1/ingest/readings/ with Tenant B tenant_id in payload while using Tenant A device key | HTTP 403 — device registered to Tenant A only |
| RBAC-H06 | Enumerate tenant IDs | Test sequential integer IDs in API paths | HTTP 404 for all other tenants' resources |

#### Vertical Escalation (Role Elevation)

| ID | Test Case | Method | Expected Result |
|----|-----------|--------|-----------------|
| RBAC-V01 | Lab Technician attempts user management | POST /api/v1/users/ while authenticated as LAB_TECHNICIAN | HTTP 403 — `user:manage` permission required |
| RBAC-V02 | Viewer attempts to delete a sample | DELETE /api/v1/samples/{id}/ as VIEWER | HTTP 403 — `sample:delete` permission required |
| RBAC-V03 | AUDITOR attempts to create a sample | POST /api/v1/samples/ as AUDITOR | HTTP 403 — `sample:create` permission required |
| RBAC-V04 | Manipulate role in JWT payload | Change `"role": "lab_technician"` to `"role": "admin"` in JWT | HTTP 401 — JWT signature invalid |
| RBAC-V05 | Permission elevation via API | PATCH /api/v1/users/{id}/ to change own role | HTTP 403 — `role:manage` permission required |
| RBAC-V06 | Access audit export as non-AUDITOR | GET /api/v1/audit/export/ as LAB_TECHNICIAN | HTTP 403 — `audit:export` permission required |

### 6.3 Audit Trail Tampering

| ID | Test Case | Method | Expected Result |
|----|-----------|--------|-----------------|
| AUDIT-01 | Direct DELETE on AuditLog record | SQL DELETE against audit_log table via application user | PostgreSQL RLS denies; Django ORM would also not expose this endpoint |
| AUDIT-02 | Direct UPDATE on AuditLog record | SQL UPDATE against audit_log table via application user | PostgreSQL RLS denies |
| AUDIT-03 | API audit log modification | PATCH /api/v1/audit/{id}/ | HTTP 405 Method Not Allowed — no update endpoint |
| AUDIT-04 | Signature chain manipulation | Modify a record in staging DB, run chain verification | Chain verification reports tampering; is_intact = false |
| AUDIT-05 | Replay attack — duplicate operation | POST same sample creation request twice | Second creates a new record; audit trail shows both; no silently discarded duplicate |
| AUDIT-06 | Inject null user_id | Craft API request that results in AuditLog.record() with user_id=None | ValueError raised; operation rejected entirely |
| AUDIT-07 | Export modification | Download certified audit export, modify a field, re-upload | export_signature verification fails; export_valid = false |
| AUDIT-08 | Timestamp manipulation on BioNexus Box | Manually set Box system clock backward; inject readings | Backend NTP comparison flags timestamp anomaly; readings flagged for review |

### 6.4 SQL Injection

| ID | Test Case | Method | Expected Result |
|----|-----------|--------|-----------------|
| SQLI-01 | Classic SQL injection in query params | `GET /api/v1/samples/?search=' OR 1=1--` | HTTP 403 from Cloud Armor; or if bypassed, Django ORM returns empty queryset |
| SQLI-02 | Second-order SQL injection | Create sample with name `'; DROP TABLE samples; --`; then retrieve | Data stored as string; never executed as SQL |
| SQLI-03 | Blind time-based SQL injection | `search='; SELECT SLEEP(5)--` equivalents for PostgreSQL | HTTP 403 from Cloud Armor; Cloud Armor sqli rules fire |
| SQLI-04 | JSON injection in structured fields | POST body with `{"sample_id": "'; DROP TABLE audit_log;--"}` | Django serializer rejects or stores as string; parameterized query prevents execution |
| SQLI-05 | Out-of-band SQL injection (DNS) | Inject `; COPY (SELECT '') TO PROGRAM 'nslookup attacker.com'` | PostgreSQL role has no SUPERUSER; COPY TO PROGRAM denied |

### 6.5 XSS and CSRF

| ID | Test Case | Method | Expected Result |
|----|-----------|--------|-----------------|
| XSS-01 | Stored XSS via sample name | Create sample with name `<script>alert(1)</script>` | Stored as literal string; React escapes on render; no alert in browser |
| XSS-02 | Stored XSS via instrument name | Same with instrument name field | Same |
| XSS-03 | Reflected XSS via error message | Submit invalid data; check if input reflected in error | Error messages use generic text; no input reflection |
| XSS-04 | DOM-based XSS via URL hash | Navigate to `app.bionexus.io/#<script>alert(1)</script>` | React Router handles; no DOM manipulation |
| CSRF-01 | Cross-origin state change | Craft cross-origin form POST to /api/v1/samples/ from attacker.com | Django CSRF middleware blocks; Origin header checked |
| CSRF-02 | CORS bypass | Request from unauthorized origin with credentials | CORS policy allows only `app.bionexus.io`; other origins rejected |
| CSRF-03 | SameSite cookie bypass | Craft top-level navigation + state change | SameSite=Strict prevents cookie inclusion from cross-site requests |

### 6.6 BioNexus Box Device Compromise Scenarios

| ID | Test Case | Method | Expected Result |
|----|-----------|--------|-----------------|
| BOX-01 | SSH brute force | Attempt SSH password login to Box | Rejected; password auth disabled |
| BOX-02 | SSH with unauthorized key | Attempt SSH with non-authorized key | Rejected; only authorized keys in ~/.ssh/authorized_keys |
| BOX-03 | Physical extraction of API key | Remove device from enclosure; attempt to read api_key.enc | File is AES-256 encrypted; brute force infeasible without device serial + provisioning secret |
| BOX-04 | USB boot mode firmware replacement | Attempt to reflash eMMC via USB boot mode | Requires physical access + BioNexus provisioning credentials; no SD card slot |
| BOX-05 | Malicious firmware via OTA | Craft unsigned firmware bundle; attempt to push via management plane | Ed25519 signature verification fails; bundle rejected |
| BOX-06 | Man-in-the-middle of Box → API channel | MITM attack against HTTPS connection | TLS certificate pinning detects cert mismatch; connection refused; alert sent |
| BOX-07 | Inject fake instrument readings | Send forged data to ingestion endpoint | packet_sha256 mismatch (no Box key to sign); rejected as tampered |
| BOX-08 | Local queue manipulation | Modify /var/lib/bionexus/queue.db directly | packet_sha256 verified on upload; modified records rejected with HTTP 422 |
| BOX-09 | Network policy bypass | Attempt outbound connection to non-allowlisted IP from Box | nftables blocks; connection dropped |
| BOX-10 | dm-verity bypass | Mount root filesystem as read-write; modify files | dm-verity detects hash mismatch on next read; system alerts |
| BOX-11 | Physical tamper attempt | Open enclosure without authorization | Tamper-evident seals broken; chassis intrusion switch (if present) triggers audit log event |
| BOX-12 | Rogue Box replacement | Replace device with identical hardware but no valid API key | New device has no registered device_id or API key; all requests return HTTP 401 |

### 6.7 API Abuse

| ID | Test Case | Method | Expected Result |
|----|-----------|--------|-----------------|
| API-01 | Rate limit bypass via IP rotation | Rotate source IPs to exceed 100 req/min limit | Each IP individually rate-limited; if using same JWT, may also apply user-level limit |
| API-02 | Parameter pollution | `/api/v1/samples/?tenant_id=B&tenant_id=A` | Framework takes first or last; not both; no cross-tenant access |
| API-03 | Mass assignment via extra body fields | POST body with `{"admin": true, "role": "admin"}` | Serializer explicitly-defined fields; extra fields silently ignored |
| API-04 | Oversized request body | POST with 100 MB body to API | Request size limit (e.g., 10 MB max) rejects; HTTP 413 |
| API-05 | Slow POST (slowloris) | Extremely slow POST body | Cloud Armor / Load Balancer timeout terminates after 60 seconds |
| API-06 | IDOR in paginated list | GET /api/v1/samples/?page=999999 | HTTP 404 or empty results; no error or data leak |
| API-07 | HTTP verb tampering | Use PATCH instead of PUT; use OPTIONS for enumeration | Unexpected verbs: HTTP 405; OPTIONS: CORS preflight only |
| API-08 | JWT in query parameter | `/api/v1/samples/?token=<jwt>` | Token only accepted in Authorization header; query param ignored |
| API-09 | Content-Type bypass | Send JSON payload with Content-Type: text/plain | Django rejects; HTTP 400 or 415 |
| API-10 | Nested object depth bomb | JSON with 1000+ levels of nesting | JSON parser depth limit or timeout |

### 6.8 Data Exfiltration

| ID | Test Case | Method | Expected Result |
|----|-----------|--------|-----------------|
| EXFIL-01 | Bulk export of all samples | GET /api/v1/samples/?page_size=99999 | page_size capped at configured maximum (e.g., 100); pagination required |
| EXFIL-02 | Audit log bulk export without permission | GET /api/v1/audit/ as LAB_TECHNICIAN | HTTP 403 — `audit:view` permission required |
| EXFIL-03 | GCS signed URL abuse | Obtain a signed URL; share with unauthorized party; attempt use after expiry | Signed URL expires after 15 minutes; HTTP 403 after expiry |
| EXFIL-04 | Cross-tenant data via audit export | Authenticated as Tenant A; export audit logs for Tenant B IDs | tenant_id filter ensures only Tenant A records returned |
| EXFIL-05 | Server-Side Request Forgery (SSRF) | POST payload with URL pointing to GCP metadata server (`169.254.169.254`) | Django should not fetch arbitrary URLs; if it does, metadata server should be blocked by VPC |
| EXFIL-06 | Log injection to exfiltrate data | Inject newlines + log statements into API fields to smuggle data into logs | Data stored as literals; no log injection via instrument data fields |

---

## 7. Vulnerability Management

### 7.1 Scanning Tools

| Tool | Target | Frequency | Automation |
|------|--------|-----------|------------|
| **pip-audit** | Python dependencies in requirements.txt | Every PR + daily | GitHub Actions + scheduled Cloud Build |
| **Dependabot** | Python packages + Docker base image | Daily | GitHub native; auto-PRs for patch updates |
| **Trivy** | Docker container image (OS packages + Python) | Every build in CI | Cloud Build step before push |
| **Bandit** | Django Python source code (SAST) | Every PR | GitHub Actions |
| **OWASP Dependency-Check** | Full dependency tree | Weekly | Scheduled |
| **ZAP (DAST)** | Live staging API | Weekly | Scheduled GitHub Actions against staging |
| **gcloud asset inventory** | GCP IAM bindings, bucket policies, firewall rules | Weekly | Scheduled; alerts on policy deviations |
| **Secret scanning** | GitHub repository | Every push | GitHub Advanced Security |
| **Manual pen test** | Full platform | Annually + per Section 5.2 schedule | External firm |

### 7.2 Severity Classification (CVSS 3.1)

| Severity | CVSS Score Range | Definition |
|----------|------------------|------------|
| **Critical** | 9.0 – 10.0 | Remote code execution, authentication bypass, full audit trail compromise, cross-tenant data access |
| **High** | 7.0 – 8.9 | Privilege escalation, partial audit trail access, individual tenant data exposure, device compromise |
| **Medium** | 4.0 – 6.9 | Information disclosure of non-sensitive metadata, service disruption affecting individual users |
| **Low** | 0.1 – 3.9 | Minor information disclosure, non-exploitable misconfigurations |

### 7.3 Remediation SLA

| Severity | SLA | Process | Regulatory Note |
|----------|-----|---------|-----------------|
| **Critical** | 24 hours | Immediate escalation to engineering lead; emergency patch; out-of-cycle deployment via hotfix pipeline | Must be documented in incident log; GxP systems: customer notification within 24h |
| **High** | 7 days | Priority backlog item; dedicated sprint; deployment within SLA | May trigger GxP change control notification to customers |
| **Medium** | 30 days | Standard backlog; scheduled release | Included in next release notes |
| **Low** | 90 days | Technical debt backlog; addressed in quarterly sweep | No customer notification required |

**GxP Exception**: Any vulnerability that affects audit trail integrity, authentication bypass, or cross-tenant data access is treated as Critical regardless of CVSS score.

### 7.4 Remediation Verification

After remediation:
1. Developer verifies fix with unit test covering the vulnerability scenario
2. Code review by second engineer confirms fix
3. Pen tester (or internal red team) re-tests the specific finding
4. QA confirms regression tests pass
5. Vulnerability closed in tracking system with evidence of fix
6. For Critical/High: evidence of fix added to vulnerability management register for customer audit

### 7.5 Vulnerability Disclosure Policy

BioNexus accepts responsible disclosure from external security researchers. Researchers should report findings to `security@bionexus.io` (encrypted via published PGP key). BioNexus commits to:

- Acknowledge receipt within 48 hours
- Provide status update within 7 days
- Credit the researcher in release notes (if desired) upon fix publication
- No legal action against researchers following this policy in good faith

---

## 8. Incident Response Plan

### 8.1 Incident Response Team

| Role | Responsibility | Primary Contact |
|------|----------------|-----------------|
| Incident Commander | Coordinate response; make decisions; customer communication | CTO |
| Security Lead | Technical investigation; containment actions | Head of Engineering |
| QA/Compliance Lead | GxP regulatory impact assessment; audit documentation | QA Director |
| Customer Success | Customer communication; tenant notifications | Customer Success Manager |
| GMP4U (Johannes Eberhardt) | CSV/qualification specialist; regulatory guidance for GxP incidents | GMP4U contact |

### 8.2 Incident Severity Levels

| Level | Criteria | Response Time |
|-------|----------|---------------|
| **P1 — Critical** | Data breach (any tenant data confirmed or suspected exfiltrated); audit trail compromise; active exploitation confirmed; all tenants affected | Immediate (24/7); 1-hour response |
| **P2 — High** | Potential data breach under investigation; single tenant affected; significant service degradation; device compromise | Business hours + on-call; 4-hour response |
| **P3 — Medium** | Suspected vulnerability; minor service disruption; no confirmed data access | Next business day; 24-hour response |
| **P4 — Low** | Security misconfiguration; informational finding; no active exploitation | 3-day response |

### 8.3 Generic Incident Response Phases

```
PHASE 1: DETECTION (0–30 min)
────────────────────────────
1. Alert received (Cloud Monitoring / customer report / pen test finding)
2. Initial triage: confirm alert is genuine (not false positive)
3. Assign severity level (P1–P4)
4. Notify Incident Commander
5. Open incident ticket in tracking system
6. Create dedicated incident Slack channel (#incident-YYYY-MM-DD)

PHASE 2: CONTAINMENT (30 min – 4h for P1)
──────────────────────────────────────────
1. Identify affected systems and data
2. Isolate: revoke credentials, disable affected endpoints, block IPs
3. Preserve evidence: snapshot Cloud Logging, export audit trail before any changes
4. Activate break-glass procedures if needed (time-limited IAM access)
5. Notify affected tenants (P1: within 2h; P2: within 8h)

PHASE 3: ERADICATION (4h – 72h)
────────────────────────────────
1. Identify root cause (code vulnerability, misconfiguration, credential compromise, device compromise)
2. Develop and test fix
3. Deploy fix to staging; verify
4. Deploy to production via hotfix pipeline (P1: bypass staging hold; emergency approval)
5. Verify fix in production

PHASE 4: RECOVERY (ongoing)
────────────────────────────
1. Restore affected services to normal operation
2. Monitor for recurrence (heightened alert thresholds for 72h)
3. Verify audit trail integrity (run chain verification for affected tenants)
4. Confirm no data exfiltration occurred (review GCS access logs, audit logs)
5. Restore any revoked credentials (with rotation)

PHASE 5: POST-MORTEM (within 14 days of resolution)
────────────────────────────────────────────────────
1. Timeline of events (when detected, when contained, when resolved)
2. Root cause analysis (5-whys)
3. Customer impact assessment (data affected, duration)
4. Action items with owners and due dates
5. Regulatory documentation (GxP deviation report if required)
6. Update this playbook if new scenarios identified
```

### 8.4 Specific Scenario: Data Breach (Tenant Data Exfiltrated)

**Definition**: Confirmed or suspected unauthorized access to instrument data, audit logs, or user information belonging to one or more tenants.

```
Step 1: DETECT
- Alert source: anomalous Cloud Logging patterns, customer report, Cloud Armor alert
- Confirm: review Cloud Audit Logs for unauthorized GetObject / SQL queries
- Classify: which tenant(s), what data, what volume

Step 2: CONTAIN
- Immediately rotate JWT SECRET_KEY (forces all active sessions to expire)
- Revoke the specific credential / API key used in the breach
- Block attacker IP at Cloud Armor (emergency rule: deny specific IP ranges)
- If via BioNexus Box compromise: revoke device API key immediately
- Preserve: export Cloud Logging for the breach window before taking further action

Step 3: ASSESS
- Enumerate data accessed (Cloud Storage access logs + PostgreSQL audit logs)
- Identify if PII was accessed (Note: BioNexus handles pseudonymized sample IDs,
  not PII — regulatory risk is reduced but still present)
- Determine if audit trail integrity was affected

Step 4: NOTIFY
- Internal: within 1 hour (CTO, QA, Engineering)
- Affected customer QA/IT: within 2 hours of P1 classification
- GDPR: if personal data affected (GDPR Art. 33: within 72h of awareness)
- Regulatory: if data integrity compromise affects validated system,
  customer may need to file deviation report with their regulatory body

Step 5: REMEDIATE
- Fix root cause vulnerability
- Audit trail impact: if any AuditLog records are confirmed tampered,
  document in GxP deviation report; hash chain re-verification
- Customer qualification: if customer's GxP system is affected,
  coordinate with GMP4U on CSV impact assessment
```

### 8.5 Specific Scenario: Audit Trail Compromise

**Definition**: AuditLog records have been modified, deleted, or the SHA-256 chain is broken.

```
Step 1: DETECT
- Automated: chain verification endpoint reports is_intact=false
- Manual: auditor reports discrepancies in audit trail during review
- Monitoring: alert on AuditLog record count unexpectedly decreasing

Step 2: IMMEDIATE ACTIONS
- Lock the affected tenant's audit trail: disable all write operations temporarily
- Snapshot current database state to GCS (timestamped)
- Run full chain verification; document which records are affected and which are intact
- DO NOT attempt to repair chain — corrupted records are evidence

Step 3: ROOT CAUSE
- Check PostgreSQL audit logs for unauthorized UPDATE/DELETE (should be denied by RLS)
- Check if application-level compromise allowed bypass of RLS
- Check for unauthorized admin access or database admin operations

Step 4: GxP IMPACT
- Any confirmed audit trail corruption in a GxP system is a regulatory deviation
- Customer QA must be notified immediately
- A GxP deviation report must be filed documenting:
  - What records were affected (entity type, ID range, time range)
  - What data was contained in affected records
  - Whether the data integrity was recoverable from backup
  - Root cause and corrective action

Step 5: RECOVERY
- If backup available and less than RPO (1h): restore from Cloud SQL PITR
- After restore: re-verify chain integrity
- Document backup restoration in audit trail for restored data
- Validate with customer QA before returning system to GxP use
```

### 8.6 Specific Scenario: BioNexus Box Device Compromise

**Definition**: A BioNexus Box device has been physically tampered with, its API key stolen, firmware replaced, or is being used to inject fabricated data.

```
Step 1: DETECT
- dm-verity failure reported in heartbeat (dm_verity_ok=false)
- Firmware version mismatch between reported and expected
- Unexpected data patterns: readings outside normal ranges for instrument type
- Physical: customer reports broken tamper seals or missing device
- packet_sha256 mismatches on ingestion (potential queue tampering)

Step 2: IMMEDIATE ACTIONS
- QUARANTINE: immediately revoke the device's API key
  (Management plane: set device status=QUARANTINED; reject all API requests from device_id)
- PRESERVE: export all readings from this device for the past 30 days for investigation
- ALERT: notify customer QA/IT of device quarantine

Step 3: DATA INTEGRITY ASSESSMENT
- Run packet_sha256 verification on all readings from device post-compromise window
- Identify any readings with hash mismatches (fabricated / tampered readings)
- Mark affected readings in the database with status=INVESTIGATION_HOLD
- Do NOT delete readings — they are evidence

Step 4: GxP IMPACT
- Any fabricated or tampered instrument data in a GxP system invalidates those test results
- Customer QA must assess which analytical results in their LIMS/release records
  were based on potentially compromised data
- Affected batch records may need re-testing

Step 5: DEVICE REPLACEMENT
- Provision a new BioNexus Box for the customer site
- Customer performs IQ/OQ on new device before returning to GxP use
- Old device: returned to BioNexus for forensic analysis (chain of custody documented)

Step 6: LESSONS LEARNED
- If physical access was the attack vector: assess physical security at customer site
- If firmware was replaced: accelerate secure boot implementation (Phase 2)
- If API key was stolen: accelerate mTLS with TPM implementation (Phase 2)
```

---

## 9. Security Monitoring

### 9.1 What Is Monitored

#### 9.1.1 Application-Level Events

| Event | Source | Log Location | Alert? |
|-------|--------|--------------|--------|
| Failed login attempts | Django auth view | Cloud Logging | Yes — >10 failures/user/15min |
| Successful logins from new IP | Django auth view | Cloud Logging | Yes — first login from geolocation |
| JWT validation failures | JWT middleware | Cloud Logging | Yes — >50/hour |
| Permission denied (403) | RBAC decorator | Cloud Logging | Yes — >20/user/hour |
| Cross-tenant access attempts | tenant_context decorator | Cloud Logging | Yes — always |
| Audit log chain verification failure | Chain verifier | Cloud Logging | Yes — always (P1) |
| AuditLog creation rate anomaly | Application metrics | Cloud Monitoring | Yes — >3 std deviations |
| BioNexus Box auth failure | Ingestion view | Cloud Logging | Yes — >5 device failures/hour |
| BioNexus Box offline | Heartbeat timeout | Cloud Monitoring | Yes — 5 min (WARNING), 30 min (CRITICAL) |
| dm-verity failure | Box heartbeat | Cloud Logging | Yes — always (P1 Security Alert) |
| Firmware version mismatch | Box heartbeat | Cloud Logging | Yes — always |
| packet_sha256 mismatch on ingestion | Ingestion view | Cloud Logging | Yes — always (possible data tampering) |

#### 9.1.2 Infrastructure-Level Events

| Event | Source | Log Location | Alert? |
|-------|--------|--------------|--------|
| Cloud SQL admin login | Cloud Audit Logs | Cloud Logging | Yes — always (break-glass scenario) |
| Secret Manager secret access | Cloud Audit Logs | Cloud Logging | Yes — outside expected service accounts |
| GCS bucket policy change | Cloud Audit Logs | Cloud Logging | Yes — always |
| IAM policy change | Cloud Audit Logs | Cloud Logging | Yes — always |
| New service account key created | Cloud Audit Logs | Cloud Logging | Yes — always (should never happen) |
| Cloud Run image deployed | Cloud Audit Logs | Cloud Logging | Yes — deployment record |
| Artifact Registry image pushed | Cloud Audit Logs | Cloud Logging | Yes — production images |
| Cloud Armor rule triggered (deny) | Cloud Armor logs | Cloud Logging | Aggregated — >100 denies/hour |
| Cloud SQL deletion protection override | Cloud Audit Logs | Cloud Logging | Yes — always (P1) |

#### 9.1.3 Network-Level Events

| Event | Source | Alert? |
|-------|--------|--------|
| DDoS traffic spike | Cloud Armor adaptive protection | Yes — when mitigation activates |
| Rate limit threshold exceeded | Cloud Armor | Yes — if sustained >5 minutes |
| TLS handshake failures | Load Balancer logs | Yes — sustained anomaly |
| Unexpected geographic traffic (geo-blocking violation) | Cloud Armor | Yes — if geo-blocking enabled |

### 9.2 Alerting Thresholds and Response

| Alert | Threshold | Severity | Response |
|-------|-----------|----------|----------|
| Failed logins per user | >10 in 15 minutes | P3 | Investigate; consider temporary account lock |
| Failed logins per IP | >50 in 15 minutes | P2 | Block IP in Cloud Armor; investigate |
| Permission denied rate | >50 in 1 hour from single user | P3 | Investigate for RBAC bypass attempts |
| Cross-tenant access attempt | Any | P2 | Immediate investigation |
| Audit chain integrity failure | Any | P1 | Immediate P1 incident response |
| dm-verity failure on any Box | Any | P1 | Quarantine device; immediate P1 response |
| BioNexus Box offline >30 min | Any | P2 | Notify customer; investigate |
| Secret accessed outside expected SA | Any | P2 | Investigate; rotate secret |
| IAM policy change | Any | P2 | Review change; verify authorized |
| Service account key created | Any | P1 | Should never happen; immediate investigation |

### 9.3 Log Retention

| Log Type | Retention Period | Storage | Reason |
|----------|-----------------|---------|--------|
| Cloud Logging (application logs) | 365 days | Cloud Logging | GxP regulatory requirement |
| Cloud Audit Logs (admin activity) | 400 days | Cloud Logging | GxP + SOC 2 |
| Cloud Audit Logs (data access) | 365 days | Cloud Logging | GDPR + GxP |
| PostgreSQL query logs | 365 days | Cloud Logging | GxP audit evidence |
| Cloud Armor request logs | 90 days | Cloud Logging | Security investigations |
| BioNexus Box local audit logs | 30 days on device; 365 days in Cloud | Cloud Logging | Forensic investigation support |
| AuditLog records (database) | 7 years minimum | PostgreSQL + GCS export | 21 CFR Part 11 / EU Annex 11 |

### 9.4 SIEM Integration (Planned)

Current state: All logs centralized in Cloud Logging with custom alert policies.

**Phase 2 SIEM target**: Export Cloud Logging to a SIEM (Chronicle Security Operations, Splunk, or equivalent) for:

- Correlation of events across application + infrastructure + device layers
- User behavior analytics (UBA) to detect anomalous access patterns
- Pre-built GxP compliance dashboards (audit trail health, access anomalies)
- Long-term security event retention (7 years, aligned with audit trail)
- Integration with customer's corporate SIEM for enterprise tenants (via log forwarding)

---

## 10. BioNexus Box Device Security

### 10.1 Firmware Security Architecture

#### Firmware Signing (Current — Phase 1)

Every firmware bundle distributed to BioNexus Box devices is:

1. **Ed25519 signed** by the BioNexus Firmware Signing Key
2. **SHA-256 checksummed** (bundle integrity)
3. **Version-embedded** (semantic version in bundle manifest)
4. **Staged rollout** (5% → 25% → 100% of devices; 24-hour hold between stages)

Firmware verification on the device:

```python
# Pseudocode — bionexus-updater verification
def verify_firmware_bundle(bundle_path: str, bundle_sig_path: str) -> bool:
    public_key = load_ed25519_public_key("/etc/bionexus/firmware-signing-public.pem")
    bundle_bytes = Path(bundle_path).read_bytes()
    signature = Path(bundle_sig_path).read_bytes()
    try:
        public_key.verify(signature, bundle_bytes)  # Raises InvalidSignature on failure
        computed_sha256 = hashlib.sha256(bundle_bytes).hexdigest()
        expected_sha256 = load_expected_sha256(bundle_path)
        return computed_sha256 == expected_sha256
    except InvalidSignature:
        logger.critical("FIRMWARE SIGNATURE VERIFICATION FAILED — bundle rejected")
        alert_operations("firmware_verification_failed")
        return False
```

#### Secure Boot (Phase 2 Roadmap)

For CM4 platform:
- Custom bootloader verification using RPi EEPROM
- dm-verity on root filesystem (read-only, hash verified on every block read)
- LUKS2 data partition with TPM-sealed key (PCR-based sealing)
- If dm-verity detects corruption: device halts and alerts operations

For industrial x86 platforms (Advantech, Kontron):
- Full UEFI Secure Boot with BioNexus-enrolled Machine Owner Key (MOK)
- TPM 2.0 PCR measurements for full measured boot

### 10.2 Physical Tamper Detection

| Threat Vector | Mitigation | Status |
|---------------|-----------|--------|
| USB port attack surface | Unused USB ports physically blocked; HDMI port sealed + disabled in device tree | Implemented |
| SD card replacement | No SD card slot on production CM4 carrier board; eMMC only | Implemented |
| Drive extraction + data theft | LUKS2 encryption on /var/lib/bionexus data partition | Implemented |
| Enclosure opening | Tamper-evident screws + optional chassis intrusion switch wired to GPIO | Implemented (seals); GPIO intrusion (optional) |
| Physical reset abuse | Recessed pin-reset button; reset event logged to cloud audit trail before reboot | Implemented |
| Device replacement | mTLS device certificate — rogue device cannot obtain valid CA cert (Phase 2) | Phase 2 |

**Physical Seal Inspection Protocol**: Customers performing GxP validation (IQ) must photograph and document tamper-evident seal status. Any broken seals must be reported to BioNexus immediately. Replacement seals are provided with a chain-of-custody form.

### 10.3 Device Certificate Lifecycle

#### Certificate Issuance

- Each device receives a unique X.509 certificate issued by the BioNexus Internal CA
- Certificate includes: device UUID (CN), tenant ID (SAN), site ID (SAN), issue date, serial number
- Certificate stored in TPM non-volatile memory (Phase 2); encrypted file (Phase 1)
- Private key: TPM-resident, never exported (Phase 2); encrypted file (Phase 1)

#### Certificate Validity and Rotation

| Parameter | Value |
|-----------|-------|
| Validity period | 2 years |
| Renewal trigger | 30 days before expiry (automated alert) |
| Rotation process | Management plane pushes new cert to Box; old cert revoked on successful rotation |
| Revocation mechanism | OCSP (Phase 2); management plane API key revocation (Phase 1) |
| Emergency revocation | Immediate via management plane; device_id blocked in registry |

#### Certificate Revocation Scenarios

| Scenario | Action |
|----------|--------|
| Device reported stolen or missing | Immediate revocation; device_id blocked |
| Device returned for RMA | Revocation before return shipment |
| Certificate expiry | Automated renewal 30 days prior |
| Suspected key compromise | Emergency revocation + replacement provisioning |
| Tenant offboarding | All tenant devices revoked; devices decommissioned |

### 10.4 Device Decommissioning Procedure

When a BioNexus Box is decommissioned (customer contract ends, hardware failure, RMA):

```
1. CLOUD ACTIONS (BioNexus staff):
   a. Set device status = DECOMMISSIONED in device registry
   b. Revoke device API key immediately
   c. Revoke device certificate (Phase 2)
   d. Archive device's historical data under tenant record
   e. Record decommissioning in cloud audit trail (entity: BoxDevice, op: DECOMMISSION)
   f. Retain data in Cloud SQL/GCS per retention policy (7 years for GxP data)

2. DEVICE ACTIONS (performed at customer site or upon device return):
   a. Export any remaining queue data (last local readings not yet uploaded)
   b. bionexus-config decommission → performs:
      - Zero-wipe data partition (/var/lib/bionexus) using shred
      - Rotate LUKS key (makes existing data unrecoverable)
      - Write decommission record to local audit log
      - POST final heartbeat to cloud with status=DECOMMISSIONED
   c. Physically remove tamper-evident seals and document
   d. Document decommissioning in customer's IQ/qualification records

3. HARDWARE DISPOSAL:
   a. If device is being scrapped: NIST 800-88 media sanitization (eMMC cryptographic erase)
   b. If device is being redeployed to another customer: full factory reset + reprovisioning
   c. Document disposal method in decommissioning record
```

### 10.5 SSH Key Management for Remote Diagnostics

| Parameter | Value |
|-----------|-------|
| Algorithm | ED25519 (preferred) or RSA-4096 |
| Key rotation | Monthly |
| Keys authorized | BioNexus support engineers only; individual named keys |
| Access restrictions | Source IP restricted to BioNexus management IP range via nftables |
| Session recording | SSH sessions logged via `script` to `/var/log/bionexus/ssh-sessions/` and uploaded to Cloud on session end |
| Break-glass | Emergency access keys stored in GCP Secret Manager; rotated after every use |

---

## 11. Third-Party Risk Management

### 11.1 Google Cloud Platform

**Assessment**: GCP holds SOC 1/2/3 Type II, ISO 27001, ISO 27017, ISO 27018, CSA STAR Level 2, FedRAMP High. GCP's compliance reports are available via the GCP Compliance Reports Manager.

**Dependency risk**: BioNexus is heavily dependent on GCP. A GCP regional failure would affect API availability, but:
- Cloud SQL HA provides automatic failover within `europe-west3` (<60s)
- Cross-region Cloud SQL replica in `europe-west4` for DR
- BioNexus Box local buffer provides 7+ days of data continuity during outage
- RTO < 15 minutes for Cloud Run (deployable from Artifact Registry to any region)

**Data processing agreement**: GCP Data Processing Addendum (DPA) signed; required for GDPR compliance.

**GAMP5 assessment**: GCP infrastructure is Category 1 (infrastructure). No custom GCP qualification required; GCP's certifications are referenced in BioNexus's CSV documentation as supplier qualification evidence.

### 11.2 AI Parsing Providers (Future Integration)

When AI parsing is integrated:

- **Data minimization**: Only instrument data snippets (no user data, no PII) sent to AI provider
- **Provider selection criteria**: SOC 2 Type II required; data processing agreement required; EU data residency option required for EU customers
- **Data sent**: Anonymized instrument output strings only; no sample IDs, no operator names, no lot numbers
- **Contractual controls**: AI provider must not use BioNexus customer data for model training
- **Fallback**: If AI provider is unavailable, fall back to rule-based parsers; no data loss

### 11.3 Python Package Dependencies

**Risk**: Supply chain attacks via malicious PyPI packages (dependency confusion, typosquatting, compromised maintainer accounts).

**Mitigations**:

| Control | Implementation |
|---------|----------------|
| Pinned dependencies | requirements.txt pins exact versions (not ranges) for all packages |
| Hash verification | `pip install --require-hashes` enforced in production Dockerfile |
| Dependency audit | pip-audit runs on every PR and daily in CI |
| Dependabot | Automated PRs for security patches; reviewed before merge |
| Trivy image scan | Container image scanned for known CVEs before every push to Artifact Registry |
| Private package mirror | Planned: Artifact Registry Python mirror to prevent typosquatting |
| Minimal dependencies | requirements.txt reviewed quarterly; unused packages removed |

**Critical packages and their security track record**:

| Package | Purpose | Security Notes |
|---------|---------|----------------|
| Django | Core web framework | Major LTS support; security advisories prompt patching |
| djangorestframework | REST API | Stable; security issues rare and promptly patched |
| psycopg2 | PostgreSQL driver | Low-level driver; minimal attack surface |
| PyJWT | JWT handling | pip-audit checks for JWT CVEs; algorithm restriction enforced |
| cryptography | Crypto primitives | Actively maintained; pip-audit essential |
| gunicorn | WSGI server | Low CVE history; process isolation reduces blast radius |

### 11.4 GitHub and CI/CD Supply Chain

| Risk | Mitigation |
|------|------------|
| Compromised GitHub Actions | Pin actions to specific commit SHA (not branch/tag); use trusted actions only |
| Secrets in CI/CD | Workload Identity Federation; no long-lived credentials in GitHub Secrets |
| Malicious PR from external contributor | Branch protection: all PRs require review; external contributors cannot trigger production deploys |
| Artifact Registry image tampering | Image digest pinning in Cloud Run deployment; Artifact Registry vulnerability scanning |

### 11.5 Vendor Assessment Cadence

| Vendor Category | Assessment Frequency | Method |
|-----------------|---------------------|--------|
| Critical infrastructure (GCP) | Annually | Review updated GCP compliance reports from Compliance Reports Manager |
| AI parsing provider | Before onboarding + annually | Security questionnaire + SOC 2 review |
| Pen test firm | Before each engagement | Qualification criteria check (Section 5.5) |
| SendGrid / email provider | Annually | SOC 2 review |

---

## 12. Compliance Alignment

### 12.1 21 CFR Part 11 §11.10 Security Requirements

| §11.10 Clause | Requirement | BioNexus Implementation | Evidence |
|---------------|-------------|-------------------------|----------|
| §11.10(a) | Validation of systems to ensure accuracy, reliability, consistent intended performance, and the ability to discern invalid or altered records | IQ/OQ/PQ qualification package; automated test suite; DAST; pen test program | System Validation Plan (BNX-VAL-001); pen test report |
| §11.10(b) | Ability to generate accurate and complete copies of records | Certified audit export endpoint; JSON + future PDF; chain verification in export | Certified export API documentation; export signature |
| §11.10(c) | Protection of records to enable accurate and ready retrieval | GCS retention policies (7-year); Cloud SQL deletion protection; PITR backups | GCS Terraform config; Cloud SQL backup configuration |
| §11.10(d) | Limiting system access to authorized individuals | JWT authentication; RBAC with 5 roles; @authenticate_required; @permission_required | SECURITY_ARCHITECTURE.md; test suite |
| §11.10(e) | Use of operational system checks to enforce permitted sequencing of steps | Sequential workflow enforced (sample states); audit trail records each state transition | Application state machine documentation |
| §11.10(f) | Use of authority checks to ensure only authorized individuals can use the system | JWT + RBAC; role permissions table; server-side enforcement | Permission model; RBAC implementation |
| §11.10(g) | Use of device checks to determine validity of data input | SHA-256 packet hashing on Box; signature chain on API; batch_sha256 verification | Box architecture; ingestion view |
| §11.10(h) | Device checks to ensure the device is functioning correctly | Box heartbeat + dm-verity reporting; system health checks | Box architecture; monitoring documentation |
| §11.10(j) | Training of individuals responsible for developing, maintaining, or using electronic record/electronic signature systems | Documented in HR training records | Training records (maintained separately) |
| §11.10(k) | Establishment of and adherence to written policies | This document + SECURITY_ARCHITECTURE.md | All referenced docs |
| §11.50 | Signed records shall contain the printed name of the signer | user_id + user_email mandatory on all AuditLog records | AuditLog model; ValueError enforcement |
| §11.70 | Electronic signatures shall be permanently linked to respective records | SHA-256 signature covers entity_type + entity_id + operation + user_id + timestamp + changes | AuditLog.signature computation |

### 12.2 EU Annex 11 Alignment

| EU Annex 11 Clause | Requirement | BioNexus Implementation |
|-------------------|-------------|-------------------------|
| §4.1 — Risk management | Risk assessment for computerized systems | STRIDE threat model (this document); risk register |
| §4.4 — Supplier assessment | Evaluation of suppliers | GCP compliance reports; third-party risk (Section 11) |
| §7.1 — Data integrity | Data should be protected against accidental deletion or modification | GCS object versioning + retention policies; Cloud SQL deletion protection; PostgreSQL RLS |
| §7.2 — Data availability | Appropriate disaster recovery | Cloud SQL HA + cross-region replica; Cloud Run multi-region deployable; GCS dual-region |
| §8.1 — Audit trail | Record all GxP-relevant operations | AuditLog with mandatory user attribution; SHA-256 chain |
| §8.2 — Audit trail review | Regular review of audit trails | AUDITOR role with audit:view/export permissions; monitoring dashboards |
| §9.1 — Change management | Formal change control | Conventional commit workflow; CI/CD pipeline with approval gate; change log |
| §12.1 — Security | Physical and logical access controls | RBAC; JWT; TLS; physical Box security; GCP IAM |
| §12.2 — Password policies | Use of passwords or other access controls | JWT with 15-min expiry; refresh rotation; password hashing (Django PBKDF2) |

### 12.3 GAMP5 Alignment

| GAMP5 Area | Requirement | BioNexus Implementation |
|------------|-------------|-------------------------|
| Chapter 5 — Category 4/5 | Software lifecycle documentation for configured and custom software | SECURITY_ARCHITECTURE.md; validation plan; test suite |
| Chapter 9 — Supplier assessment | Qualification of GCP, third-party tools | Section 11 of this document; GCP DPA |
| Chapter 10 — Project management | Structured project delivery | Sprint priorities; documented architecture |
| Appendix D4 — Infrastructure | IQ/OQ for infrastructure components | GCP_CLOUD_ARCHITECTURE.md; Terraform as infrastructure-as-code |

### 12.4 GDPR Alignment

| GDPR Principle | Implementation | Note |
|----------------|----------------|------|
| Lawful basis | Processing based on contract (B2B SaaS agreement) | Customer data processing agreement required |
| Data minimization | No PII in instrument data; pseudonymized sample IDs only | No-PII policy enforced |
| Purpose limitation | RBAC limits data access; data used only for instrument integration | Enforced technically |
| Storage limitation | GCS lifecycle policies; Cloud SQL PITR 7-day retention | 7-year minimum for GxP data |
| Security | Encryption in transit + at rest; access controls | TLS; LUKS2; Cloud SQL SSL |
| Data subject rights | Soft delete; audit trail for accountability | GDPR compliance mapping in SECURITY_ARCHITECTURE.md |
| Accountability | Audit logs; DPA with GCP; this document | Cloud Audit Logs; AuditLog |
| Data residency | All production data in `europe-west3` (Frankfurt) | Terraform region config |
| DPA with processor | GCP DPA signed | Required before going live |

### 12.5 How This Security Program Satisfies Common Customer Infosec Requirements

| Customer Requirement | BioNexus Implementation |
|---------------------|-------------------------|
| Annual penetration testing | Section 5: annual external pen test + semi-annual internal; reports available under NDA |
| Vulnerability management with SLAs | Section 7: Critical 24h, High 7d, Medium 30d, Low 90d |
| Incident response plan | Section 8: documented IRP with specific GxP scenarios |
| Access control (RBAC) | 5 roles; JWT; server-side enforcement; mandatory user attribution |
| Encryption at rest | Cloud SQL encryption; GCS object encryption; LUKS2 on Box |
| Encryption in transit | TLS 1.3 everywhere; no plaintext protocols |
| Multi-factor authentication | GCP Console: enforced MFA for all GCP users; Django user accounts: TOTP 2FA planned |
| Audit logging | AuditLog + Cloud Audit Logs + application logs; 365 days minimum; 7 years for GxP records |
| Data backup | Cloud SQL daily backups + PITR 7 days; GCS versioning; cross-region replica |
| Disaster recovery | Cloud SQL cross-region replica; RTO <15 min; RPO <1h |
| SOC 2 compliance | GCP SOC 2 Type II; BioNexus SOC 2 Type II in scope for 2027 |
| Data residency | All production data in EU (Frankfurt, europe-west3) |

---

## 13. Customer Security FAQ

This section provides pre-answered responses to the most common questions from pharma/biotech enterprise infosec reviewers. These answers may be shared verbatim in security questionnaires.

---

**Q: Does BioNexus have a current SOC 2 report?**

A: BioNexus is an early-stage company and does not yet hold a SOC 2 Type II certification. Our hosting provider, Google Cloud Platform, holds SOC 2 Type II. GCP's SOC 2 report is available via the GCP Compliance Reports Manager. BioNexus is targeting SOC 2 Type II readiness for 2027 as a defined milestone in our security roadmap. In the interim, BioNexus provides this Security Assessment Playbook as a comprehensive security posture document, and all security controls described herein can be evidenced via technical demonstration and configuration review.

---

**Q: Where is customer data stored?**

A: All production data is stored in Google Cloud Platform's `europe-west3` region (Frankfurt, Germany). This is enforced at the Terraform infrastructure level. Data residency is pinned and cannot be changed without an explicit infrastructure change. For customers requiring non-EU residency, BioNexus can provision a separate GCP project in the appropriate region (e.g., `us-central1` for US-only requirements). No data from EU customers is processed or stored outside the EU without customer consent.

---

**Q: How is data encrypted?**

A: Data is encrypted at multiple layers:
- **In transit**: TLS 1.3 for all communications (browser to API, BioNexus Box to API). TLS 1.2 with AEAD ciphers permitted as fallback. No plaintext protocols.
- **At rest — Cloud SQL**: Google-managed encryption (AES-256) at the storage layer; additionally, SSL enforced for all database connections.
- **At rest — Cloud Storage**: Google-managed encryption (AES-256) at the object level; versioning and retention policies prevent modification or deletion.
- **At rest — BioNexus Box**: LUKS2 AES-256-XTS encryption on the data partition (`/var/lib/bionexus`). Device secrets (API keys, certificates) are additionally encrypted with AES-256-GCM.
- **Secrets**: All application secrets (JWT signing key, database password, API keys) are stored in GCP Secret Manager; never in source code, environment files, or Docker images.

---

**Q: How does BioNexus ensure audit trail integrity?**

A: BioNexus implements a multi-layer audit trail integrity strategy:
1. **SHA-256 hash chaining**: Each AuditLog record's signature covers the previous record's signature, creating a chain. Any modification of any historical record breaks the chain and is detected by the chain verification endpoint.
2. **Mandatory user attribution**: All audit records require a valid `user_id` and `user_email`. Operations without authenticated user context are rejected with a ValueError. This satisfies 21 CFR Part 11 §11.50 requirements for signed records.
3. **Database-level write protection**: PostgreSQL Row Level Security (RLS) is applied to the `audit_log` table. The application database user has INSERT-only permission. UPDATE and DELETE are denied at the database level, even if application code were compromised.
4. **GCS export immutability**: Certified audit exports are written to Google Cloud Storage with retention policies preventing deletion for 7 years. After the validation phase, the retention policy is locked (WORM).
5. **Continuous verification**: The chain verification endpoint can be called at any time to verify the integrity of the entire audit trail for a tenant.

---

**Q: What is the multi-tenancy isolation model?**

A: BioNexus uses logical multi-tenancy on shared GCP infrastructure. Tenant isolation is enforced at three layers:
1. **JWT layer**: Each authenticated request carries a `tenant_id` claim in the JWT. The `@tenant_context` decorator extracts and validates this claim on every request.
2. **Application layer**: The `SampleRepository`, `ProtocolRepository`, and all data repositories always include `WHERE tenant_id = <authenticated_tenant_id>` in every query. No cross-tenant query is possible through the application API.
3. **GCS layer**: Object paths include the tenant ID prefix (`tenants/{tenant_id}/...`). IAM and signed URL scoping enforces this at the storage layer.

Physical data isolation (separate Cloud SQL instances per tenant) is available as a premium offering for customers with the strictest data segregation requirements.

---

**Q: What access controls exist for BioNexus staff to access customer data?**

A: BioNexus staff cannot access customer data without explicit authorization:
- Production Cloud SQL access requires Cloud SQL Auth Proxy with time-limited IAM conditions (break-glass access). All access is logged in Cloud Audit Logs.
- No BioNexus engineer has standing access to production data. Access requires a support ticket, manager approval, and time-limited IAM condition.
- GCS bucket access is similarly time-limited and logged.
- All staff access to GCP is via Google SSO with enforced MFA.
- The BioNexus Box has no BioNexus staff access by default. SSH access requires a key exchange and is restricted to the BioNexus management IP range. All SSH sessions are logged.

---

**Q: Does BioNexus conduct penetration testing?**

A: Yes. BioNexus conducts annual external penetration tests of the API, web application, and BioNexus Box device, plus semi-annual internal infrastructure assessments. Tests are conducted by qualified third-party firms (OSCP/CREST-certified testers). Pen test reports are available for review under NDA as part of supplier qualification. Findings are tracked and remediated per the SLAs defined in Section 7 of this document.

---

**Q: What is BioNexus's vulnerability disclosure policy?**

A: BioNexus maintains a responsible disclosure policy. Security researchers may report vulnerabilities to `security@bionexus.io`. BioNexus acknowledges within 48 hours and provides status updates within 7 days. We do not take legal action against good-faith researchers. Critical findings are remediated within 24 hours of confirmation.

---

**Q: What is BioNexus's data breach notification process?**

A: In the event of a confirmed or suspected data breach affecting customer data:
- BioNexus notifies affected customers within 2 hours of a P1 classification.
- GDPR Article 33 notifications (to relevant supervisory authority) are filed within 72 hours of awareness if personal data is affected.
- For GxP-regulated data: BioNexus coordinates with the customer's QA team on the regulatory impact assessment and required deviation documentation.
- BioNexus maintains cyber liability insurance covering breach notification costs and regulatory penalties.

---

**Q: What happens to my data if I terminate the BioNexus contract?**

A: Upon contract termination:
1. A certified audit export of all your tenant's data is generated and provided to you within 30 days.
2. Your tenant's active data is soft-deleted from live systems within 30 days of contract end.
3. Data is retained in backup storage per the GxP regulatory minimum (7 years for QC instrument data) unless you provide a regulatory justification for earlier deletion.
4. All BioNexus Box devices assigned to your tenant are remotely decommissioned (API key revocation, device quarantine) and returned for sanitization per NIST 800-88.
5. GCP logs referencing your data are retained per the log retention policy and are not accessible to other tenants.

---

**Q: Is BioNexus Box data secure while offline?**

A: Yes. When the BioNexus Box is offline (no internet connection), instrument data continues to be captured and stored locally:
- The local SQLite queue uses WAL mode with `PRAGMA synchronous=FULL` to survive power loss.
- The data partition is LUKS2 AES-256-XTS encrypted. Data cannot be read without the encryption key, which is tied to the device's hardware identity.
- Each reading is SHA-256 hashed at capture time. When connectivity is restored, the backend verifies these hashes. Any modification of locally stored data is detectable and causes the affected reading to be rejected and flagged for investigation.
- The store-and-forward buffer holds approximately 7 days of data at standard instrument sampling rates.

---

**Q: How does BioNexus handle firmware updates on the BioNexus Box in a validated GxP environment?**

A: Firmware updates are managed under change control:
1. Each firmware release is Ed25519 signed by an authorized BioNexus firmware signing officer.
2. Staged rollout: 5% of devices → 25% → 100%, with 24-hour holds between stages.
3. The Box verifies the firmware signature before installation; unsigned firmware is rejected.
4. A/B partitioning with automatic rollback: if the new firmware fails, the device automatically reverts to the previous version.
5. For customers under validated computer systems, the management plane supports an `is_update_held` flag that prevents automatic updates. Firmware updates require explicit customer QA approval before deployment. Update deployment is recorded in the cloud audit trail.

---

## 14. Appendix: Pre-Deployment Security Checklist

This checklist must be completed and signed off before any BioNexus environment is promoted to production or made available to paying customers. It serves as the security gate for production readiness and is a GxP qualification artifact.

---

### 14.1 GCP Infrastructure Checklist

- [ ] **VPC and Networking**: Cloud SQL has no public IP (`ipv4_enabled = false`); all resources use private VPC; no resources have public IPs except the Global Load Balancer
- [ ] **Cloud Armor**: WAF policy deployed; SQLi and XSS rules active; rate limiting at 100 req/min/IP; BioNexus Box IP allowlist configured for ingestion endpoint
- [ ] **TLS**: SSL policy enforces TLS 1.2 minimum with MODERN cipher profile; HTTP→HTTPS redirect active; HSTS header configured
- [ ] **IAM**: No service accounts hold `roles/owner` or `roles/editor`; Workload Identity Federation configured; no service account key files exist; resource-scoped IAM bindings in use
- [ ] **Secret Manager**: All secrets stored in Secret Manager; no secrets in source code, Docker images, or environment files; data access audit logging enabled for Secret Manager
- [ ] **Cloud SQL**: Deletion protection enabled; PostgreSQL audit flags active (log_connections, log_disconnections, log_lock_waits); RLS applied to audit_log table (INSERT-only for app user)
- [ ] **Cloud SQL RLS**: `INSERT`-only policy verified for `bionexus_app_user` on `audit_log` table; no UPDATE/DELETE policies defined
- [ ] **GCS**: All buckets have `uniform_bucket_level_access = true`; no `allUsers` or `allAuthenticatedUsers` bindings; retention policies applied; versioning enabled on all buckets
- [ ] **Cloud Build**: Production deployment requires manual approval in GitHub Environments; no automatic production deployment on push
- [ ] **Artifact Registry**: Vulnerability scanning enabled; image tag immutability enabled; access restricted to CI/CD service account only

### 14.2 Django Application Checklist

- [ ] **DEBUG=False**: `DJANGO_DEBUG=false` in production environment variables
- [ ] **SECRET_KEY**: 50+ character random string from Secret Manager; unique to production; not the default or development value
- [ ] **ALLOWED_HOSTS**: Explicitly set to production domain(s) only; no wildcard `*`
- [ ] **HTTPS enforcement**: `SECURE_SSL_REDIRECT = True`; `SECURE_HSTS_SECONDS` configured; `SESSION_COOKIE_SECURE = True`; `CSRF_COOKIE_SECURE = True`
- [ ] **Admin path**: Django admin relocated from `/admin/` to non-guessable path; Cloud Armor IP allowlist applied to admin path
- [ ] **JWT secret**: Separate, high-entropy JWT signing key; different from Django SECRET_KEY; stored in Secret Manager
- [ ] **Password hashing**: Django's PBKDF2 with SHA-256 (default); no custom or weaker hashers
- [ ] **CORS**: `CORS_ALLOWED_ORIGINS` explicitly set to `https://app.bionexus.io` only; no `CORS_ALLOW_ALL_ORIGINS = True`
- [ ] **CSRF**: Django CSRF middleware active; `SameSite=Strict` on CSRF cookie
- [ ] **Security headers**: X-Frame-Options: DENY; X-Content-Type-Options: nosniff; Referrer-Policy: strict-origin; CSP header configured
- [ ] **Authentication**: `@authenticate_required` on all non-public API endpoints (verified by code review)
- [ ] **RBAC**: `@permission_required` on all permission-gated endpoints (verified by test suite)
- [ ] **Tenant isolation**: `@tenant_context` on all tenant-data-returning endpoints; all repository methods filter by `tenant_id` (verified by test suite)
- [ ] **Audit trail**: AuditLog.record() called for all CREATE/UPDATE/DELETE operations; user_id and user_email mandatory
- [ ] **Paginated responses**: All list endpoints are paginated; `page_size` has enforced maximum
- [ ] **Request size limits**: Maximum request body size configured

### 14.3 BioNexus Box Checklist

- [ ] **OS hardening**: Unused services removed (Avahi, Bluetooth, triggerhappy); only `bionexus`, `sshd`, `nftables`, and core system services running
- [ ] **SSH**: Password authentication disabled; root login disabled; only authorized BioNexus ED25519/RSA-4096 keys in authorized_keys; source IP restriction applied
- [ ] **nftables**: Outbound allowlist active (HTTPS 443 to api.bionexus.io, NTP 123, DNS 53 only); all other outbound blocked; no inbound except SSH from management IP range
- [ ] **LUKS2**: Data partition (`/var/lib/bionexus`) encrypted; encryption key derived from device serial + provisioning secret (Phase 1) or TPM-sealed (Phase 2)
- [ ] **Device identity**: device_id registered in cloud device registry; API key provisioned and stored encrypted; api_key_hash stored in cloud (SHA-256 of key, not the key itself)
- [ ] **Certificate pinning**: GCP backend TLS certificate SHA-256 digest configured in `uplink.cert_pin_sha256`; pinning active (connection refused on mismatch)
- [ ] **Firmware signature**: Firmware signing public key present at `/etc/bionexus/firmware-signing-public.pem`; signature verification enabled in updater
- [ ] **Tamper-evident seals**: Applied to all enclosure screws; photographed and documented in IQ package
- [ ] **HDMI**: Port sealed with tamper-evident label; disabled in device tree overlay (`dtoverlay=disable-hdmi`)
- [ ] **Hardware watchdog**: Enabled and configured; bionexus-agent confirms watchdog heartbeat
- [ ] **NTP**: Synchronized; drift within 2 seconds; NTP sync failure alerting active
- [ ] **Auto-updates**: OS security updates via `unattended-upgrades` active
- [ ] **bionexus-agent**: Running as `bionexus` user (UID 999); not root; confirmed via `ps aux`
- [ ] **Queue integrity**: SQLite WAL mode active (`PRAGMA journal_mode=WAL`); synchronous=FULL; integrity check passes on startup

### 14.4 CI/CD Pipeline Checklist

- [ ] **No hardcoded secrets**: Repository secret scanning active (GitHub Advanced Security); no secrets in git history (verify with `git log --all -p | grep -i password`)
- [ ] **Pinned Actions**: All GitHub Actions workflow actions pinned to specific commit SHA
- [ ] **Workload Identity**: No long-lived service account keys in GitHub Secrets; Workload Identity Federation configured
- [ ] **Branch protection**: `main` branch requires PR approval; no force pushes; status checks required
- [ ] **Production gate**: Manual approval required in GitHub Environments for production deployment
- [ ] **Container scanning**: Trivy runs on every Docker image build; builds fail on Critical vulnerabilities

### 14.5 Compliance and Documentation Checklist

- [ ] **Pen test**: Current annual pen test completed; no open Critical or High findings; report available
- [ ] **Vulnerability scan**: No open Critical vulnerabilities in pip-audit, Trivy, or DAST results
- [ ] **Incident response**: IRP team contacts updated and confirmed; escalation channels tested
- [ ] **Monitoring**: Cloud Monitoring alerts active for all thresholds in Section 9.2; alert destinations confirmed (PagerDuty/email)
- [ ] **Log retention**: Cloud Audit Logs data access enabled for Cloud SQL and Secret Manager; 365-day retention configured
- [ ] **GCP DPA**: GCP Data Processing Addendum signed; stored in compliance records
- [ ] **Customer DPA**: Customer-facing data processing agreement template reviewed by legal
- [ ] **Audit trail RLS**: Verified by running `EXPLAIN ANALYZE DELETE FROM audit_log WHERE id=1` as app user — should fail with RLS policy violation
- [ ] **Chain verification**: Run `/api/v1/audit/verify/` against a populated staging tenant; `is_intact=true` confirmed

---

**Checklist Sign-Off**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Engineering Lead | | | |
| QA Director | | | |
| Security Lead | | | |
| CTO | | | |

This checklist must be completed for each environment promotion (staging → production) and retained as a qualification artifact in the project's CSV documentation.

---

**Document Version**: 1.0
**Last Updated**: 2026-02-28
**Review Cycle**: Annual (or after any P1 security incident)
**Owner**: BioNexus Security Team
**Classification**: Confidential — Internal Use / Controlled Distribution to Customers Under NDA
