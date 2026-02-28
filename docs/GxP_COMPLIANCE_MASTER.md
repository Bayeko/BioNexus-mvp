# GxP Compliance Master Document
## BioNexus Platform — Regulatory & Validation Reference

---

**Document ID:** BNX-COMP-001
**Version:** 1.0
**Status:** Approved for Distribution
**Date:** 2026-02-28
**Prepared by:** BioNexus Engineering & Regulatory Team
**Review Partner:** GMP4U (Johannes Eberhardt) — CSV/Qualification Specialist
**Classification:** Regulatory Affairs — Restricted Distribution

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Regulatory Framework Overview](#2-regulatory-framework-overview)
3. [GAMP5 Software Category Classification](#3-gamp5-software-category-classification)
4. [21 CFR Part 11 Compliance Matrix](#4-21-cfr-part-11-compliance-matrix)
5. [EU Annex 11 Compliance Matrix](#5-eu-annex-11-compliance-matrix)
6. [ALCOA+ Data Integrity Mapping](#6-alcoa-data-integrity-mapping)
7. [Computerized System Validation (CSV) Strategy](#7-computerized-system-validation-csv-strategy)
8. [Qualification Approach (IQ/OQ/PQ Summary)](#8-qualification-approach-iqoqpq-summary)
9. [Electronic Signatures and Records](#9-electronic-signatures-and-records)
10. [Audit Trail Design](#10-audit-trail-design)
11. [Role-Based Access Control](#11-role-based-access-control)
12. [Change Control and Configuration Management](#12-change-control-and-configuration-management)
13. [Risk Assessment (per ICH Q9)](#13-risk-assessment-per-ich-q9)
14. [Supplier Assessment](#14-supplier-assessment)
15. [Glossary](#15-glossary)

---

## 1. Executive Summary

### 1.1 Platform Overview

BioNexus is a SaaS and hardware platform purpose-built for laboratory instrument data integration, compliance, and traceability in GxP-regulated pharmaceutical and biotechnology environments. The platform consists of two integrated components:

- **BioNexus Box**: A Plug and Play hardware gateway device that connects laboratory instruments (via RS232/USB) to the cloud platform. It eliminates the need for manual transcription of instrument output, capturing raw data at the source and transmitting it securely over HTTPS.
- **BioNexus Cloud Platform**: A Django REST Framework backend hosted on Google Cloud Platform (GCP), providing data intake, SHA-256 integrity verification, immutable audit logging, human review workflows, electronic signature certification, and role-based access control.

### 1.2 GxP Compliance Design Philosophy

BioNexus was designed from its initial architecture with regulatory compliance as a first-class requirement, not a post-hoc addition. Every major system design decision — from the SHA-256 signature chain to mandatory user attribution in the audit trail, from strict Pydantic schema validation to the double-authentication certification modal — exists to satisfy a specific regulatory requirement under 21 CFR Part 11, EU Annex 11, or GAMP5.

Key compliance design principles embedded in the platform:

- **Immutability by Default**: Audit log records cannot be modified. The SHA-256 hash chain ensures any tampering is immediately detectable across all downstream records.
- **No-Trust Data Pipeline**: AI-extracted data is never accepted automatically. It enters the system in a `PENDING` state and requires explicit human review and authorization before being usable.
- **Mandatory Attribution**: The `AuditTrail.record()` method raises a `ValueError` at the code level if `user_id` or `user_email` are not supplied. Attribution is not optional.
- **Separation of Duties**: Role-Based Access Control (RBAC) enforces that the user who executes an action cannot unilaterally authorize it, and read-only roles (AUDITOR, VIEWER) cannot mutate data.
- **Non-Repudiation**: Every data certification requires password re-entry and OTP verification, creating a non-repudiable electronic signature that cannot be disowned.

### 1.3 Target Regulatory Environment

BioNexus targets QC laboratories in pharmaceutical and biotechnology SMBs (50–500 employees) operating under:

- **US FDA**: 21 CFR Part 11 (Electronic Records and Electronic Signatures)
- **EU EMA**: Annex 11 to EU GMP Guide (Computerised Systems)
- **ICH**: Q9 (Quality Risk Management), Q10 (Pharmaceutical Quality System)
- **ISPE/GAMP**: GAMP5 (A Risk-Based Approach to Compliant GxP Computerized Systems)
- **WHO**: TRS 996 Annex 5 (Guidance on Good Data and Record Management Practices)

---

## 2. Regulatory Framework Overview

### 2.1 21 CFR Part 11 (FDA)

**Scope:** Applies to electronic records and electronic signatures created, modified, maintained, archived, retrieved, or transmitted under FDA regulations (21 CFR Parts 210, 211, 820, etc.).

**Key Requirements:**
- Systems must employ validated software with appropriate controls
- Audit trails must record who did what, when, and why, in a time-stamped, computer-generated manner
- Electronic signatures must be unique to one individual and must link to the associated electronic record
- Access controls must ensure only authorized personnel can use the system
- Operational system checks must enforce permissible sequencing of steps

**Applicability to BioNexus:** Any QC laboratory subject to cGMP (21 CFR Parts 210/211) that uses BioNexus to manage instrument data, sample tracking, or protocol execution records is subject to Part 11 for those electronic records.

### 2.2 EU GMP Annex 11 (EMA)

**Scope:** Applies to all forms of computerised systems used in GMP-regulated activities, including systems that replace paper-based operations.

**Key Requirements:**
- Risk management applied throughout system lifecycle
- Supplier and system validation evidence
- Data integrity: original records preserved, changes tracked
- Audit trails covering all GMP-relevant data and changes
- Business continuity: backup, recovery, disaster recovery procedures
- Periodic review of computerised systems to confirm validated status

**Applicability to BioNexus:** European pharmaceutical manufacturers using BioNexus must satisfy Annex 11 for the computerised system covering instrument data integration and electronic batch record support.

### 2.3 GAMP5

**Scope:** Industry guidance from ISPE providing a risk-based framework for the validation of computerized systems in regulated environments.

**Key Elements:**
- Software category classification (Categories 1–5) to determine validation effort
- V-Model validation lifecycle (URS → FS → DS → IQ → OQ → PQ)
- Risk-based approach: greater validation effort for higher-risk, higher-complexity systems
- Supplier assessment: understanding the supplier's development quality system

**Applicability to BioNexus:** BioNexus is subject to GAMP5 guidance both as a system being validated by customers (regulated users) and as a supplier building quality into the development lifecycle.

---

## 3. GAMP5 Software Category Classification

### 3.1 Classification Decision

| Category | Description | BioNexus Applicability |
|---|---|---|
| **1** | Infrastructure software (OS, middleware, network) | Not applicable to BioNexus application layer |
| **2** | (Retired in GAMP5 2nd Ed.) | N/A |
| **3** | Non-configured products (firmware, standard packages used as-is) | Not applicable — BioNexus is configurable |
| **4** | Configured products (commercial off-the-shelf configured to customer requirements) | Partially applicable — Django/PostgreSQL infrastructure components |
| **5** | Custom software (bespoke or custom-configured developed specifically for regulated use) | **Primary classification for BioNexus application** |

**BioNexus Classification: GAMP5 Category 5 — Custom Software**

### 3.2 Rationale for Category 5 Classification

BioNexus qualifies as Category 5 for the following reasons:

1. **Bespoke Development**: The BioNexus application (Django REST API, parsing pipeline, audit trail engine, RBAC framework, SHA-256 chain logic) is custom-developed software with no equivalent commercial off-the-shelf product.

2. **Configurable Business Logic**: The system allows customer-specific configuration of roles, permissions, tenant isolation boundaries, parsing schemas, and workflow parameters. This goes beyond Category 3 (no configuration) and Category 4 (standard configuration without custom code).

3. **GxP-Specific Design**: The system is explicitly designed and coded to satisfy GxP requirements (mandatory `user_id` in audit trail enforced at code level, `extra="forbid"` in Pydantic schemas to prevent hallucination of data, SHA-256 signature chaining for immutability). These are not incidental features of a generic platform.

4. **Custom Algorithm Implementation**: The SHA-256 chain integrity algorithm (`calculate_signature(previous_signature, audit_log_data)` in `core/utils/integrity.py`) is custom-coded business logic, not a configurable feature of underlying infrastructure.

### 3.3 Infrastructure Component Sub-Classification

The underlying infrastructure components that BioNexus depends upon carry their own GAMP5 classifications:

| Component | GAMP5 Category | Validation Approach |
|---|---|---|
| Python 3.12 runtime | Category 1 | Vendor qualification evidence (CPython, PSF) |
| Django 4.2 framework | Category 3 | Reference to published releases, security patch management |
| PostgreSQL database | Category 3 | Database configuration qualification |
| Google Cloud Platform | Category 3 | GCP compliance documentation (SOC 2, ISO 27001) |
| React 18 / TypeScript | Category 3 | Reference to published releases |

### 3.4 Validation Effort Implications

As a Category 5 system, BioNexus requires:

- Full lifecycle validation documentation (URS, FS, DS, IQ, OQ, PQ)
- Traceability matrix linking requirements to test scripts
- Source code review or equivalent oversight as part of supplier assessment
- Regression testing for all changes
- Change control with impact assessment and revalidation for significant changes
- Periodic review to confirm continued validated status

---

## 4. 21 CFR Part 11 Compliance Matrix

The following table maps each subsection of 21 CFR Part 11 to the specific BioNexus technical implementation that satisfies or addresses the requirement. Subsections are referenced as published in the CFR.

### 4.1 Subpart B — Electronic Records

#### §11.10 — Controls for Closed Systems

| Requirement Reference | Requirement Text (Summary) | BioNexus Implementation | Implementation Location | Status |
|---|---|---|---|---|
| §11.10(a) | System validation to ensure accuracy, reliability, and consistent intended performance | Full V-Model validation lifecycle; unit, integration, and E2E test suites; Django test framework used throughout | `python manage.py test`; test coverage in all app modules | Implemented |
| §11.10(b) | Ability to generate accurate and complete copies of records in human readable and electronic form | `GET /api/reports/{id}/` returns complete JSON; `GET /api/reports/{id}/pdf/` returns signed PDF with full audit chain | `core/api_views.py` — `ReportDetailView`, `ReportPDFView` | Implemented |
| §11.10(c) | Protection of records to enable accurate and ready retrieval throughout the retention period | Immutable `AuditLog` model (soft delete only, no hard deletion permitted); PostgreSQL persistent storage; GCP-hosted with backup capability | `AuditLog` model; `is_deleted` soft-delete pattern on all data models | Implemented |
| §11.10(d) | Limiting system access to authorized individuals | JWT-based authentication required for all API endpoints; `@authenticate_required` decorator; access token 15-minute lifetime | `SECURITY_ARCHITECTURE.md §1`; `core/decorators.py` | Implemented |
| §11.10(e) | Use of secure, computer-generated, time-stamped audit trails to independently record the date and time of operator entries and actions | `AuditLog` records every CREATE, UPDATE, DELETE, and SIGN operation with `timestamp` (UTC, `auto_now_add`), `user_id`, `user_email`, `operation`, `entity_type`, `entity_id`, `changes`, `snapshot_before`, `snapshot_after` | `AuditLog` Django model; `AuditTrail.record()` service method | Implemented |
| §11.10(e) (cont.) | Audit trail information to be available for review and copying by FDA | `GET /api/auditlog/` with filtering by `entity_type`, `entity_id`, `operation`, `date_from`; paginated response; exportable as JSON | `core/api_views.py` — `AuditLogListView` | Implemented |
| §11.10(f) | Use of operational system checks to enforce permissible sequencing of steps and events | `ParsedData` state machine enforces: `PENDING` → `VALIDATED` → (certified); cannot call `/sign/` endpoint without state `validated`; cannot create `CertifiedReport` without completed OTP verification | `ParsedData.state` field; `ParsedDataSignView.post()` gate logic | Implemented |
| §11.10(g) | Use of authority checks to ensure that only authorized individuals can use the system, electronically sign records, access the operation or device, alter a record, or perform the operation | RBAC with `@permission_required(Permission.X)` decorator; role-permission mapping enforced server-side; electronic signature requires password re-entry + OTP (not just session token) | `SECURITY_ARCHITECTURE.md §3`; `Permission` and `Role` models | Implemented |
| §11.10(h) | Use of device (e.g., terminal) checks to determine validity of input source | JWT token encodes `user_id`, `tenant_id`, `role`, `permissions`; refresh token rotation; access tokens expire in 15 minutes | `JWTService.generate_tokens()`; `SECURITY_ARCHITECTURE.md §1` | Implemented |
| §11.10(i) | Determination that persons who develop, maintain, or use electronic record/electronic signature systems have the education, training, and experience to perform their assigned tasks | Training requirements defined in Supplier Assessment (Section 14); operator training on RBAC role assignment; SOP for onboarding new users | Organizational controls; user management via ADMIN role | Procedural |
| §11.10(j) | Written policies that hold individuals accountable and responsible for actions initiated under their electronic signatures | Non-repudiable electronic signature: `user_id` mandatory in `AuditTrail.record()`; double-auth certification logged with `operation: "SIGN"` in `AuditLog` | `SECURITY_ARCHITECTURE.md §4`; `ParsedDataSignView` | Implemented |
| §11.10(k) | Use of appropriate controls over systems documentation including controls for the distribution of, access to, and use of documentation for system operation and maintenance | Documentation version control via Git; CLAUDE.md, SECURITY_ARCHITECTURE.md, PARSING_ARCHITECTURE.md maintained in repository; change control process (Section 12) | Git repository with conventional commits; access controlled via GitHub permissions | Implemented |

#### §11.30 — Controls for Open Systems

| Requirement Reference | Requirement Text (Summary) | BioNexus Implementation | Status |
|---|---|---|---|
| §11.30 | Additional controls for open systems including document encryption and use of digital signature standards | BioNexus operates as a closed system (authenticated users only, tenant-isolated); HTTPS enforced in production; JWT signing uses HS256 | Closed system controls applied; HTTPS configuration required in deployment |

#### §11.50 — Signature Manifestations

| Requirement Reference | Requirement Text (Summary) | BioNexus Implementation | Implementation Location | Status |
|---|---|---|---|---|
| §11.50(a)(1) | Printed name of the signer | `user_email` and `user_id` included in `AuditLog` SIGN record; `certified_by` field in `CertifiedReport` | `CertifiedReport.certified_by` FK; `AuditLog.user_email` | Implemented |
| §11.50(a)(2) | Date and time when signature was executed | `certified_at` timestamp in `CertifiedReport`; `timestamp` in `AuditLog` SIGN record | `CertifiedReport.certified_at`; `AuditLog.timestamp` | Implemented |
| §11.50(a)(3) | Meaning (purpose) associated with the signature | `operation: "SIGN"` in AuditLog; `notes` field captures the user's certification statement; explicit "I certify that all data is accurate" acknowledgment in UI | `CertificationModal` — Step 3; `AuditLog.operation` | Implemented |
| §11.50(b) | Signature manifestations are part of the human readable form of electronic records | PDF report includes: certified-by name, timestamp, SHA-256 report hash, QR code of hash, full correction history | `GET /api/reports/{id}/pdf/` | Implemented |

#### §11.70 — Signature/Record Linking

| Requirement Reference | Requirement Text (Summary) | BioNexus Implementation | Status |
|---|---|---|---|
| §11.70 | Electronic signatures must be linked to their respective electronic records such that the signature cannot be excised, copied, or transferred to falsify an electronic record | `AuditLog` SIGN record contains `entity_type: "CertifiedReport"` and `entity_id` linking it to the specific report; SHA-256 chain links all audit records; modifying the report invalidates the chain | Implemented |

### 4.2 Subpart C — Electronic Signatures

| Requirement Reference | Requirement Text (Summary) | BioNexus Implementation | Status |
|---|---|---|---|
| §11.100(a) | Each electronic signature shall be unique to one individual and shall not be reused or reassigned to anyone else | Each `User` has a unique `user_id`, `username`, and `email`; JWT tokens are user-specific; OTP is single-use and user-specific | Implemented |
| §11.100(b) | Organizations shall verify identity before assigning electronic signature | User creation requires ADMIN role; identity verification is an organizational SOP; email uniqueness enforced at model level | Procedural + technical enforcement |
| §11.100(c) | Persons using electronic signatures shall certify to FDA, prior to or at the time of use, that electronic signatures are intended to be equivalent to handwritten signatures | Customer organizational certification required; BioNexus provides the technical mechanism; explicit user acknowledgment during certification workflow | Customer SOP + BioNexus UI flow |
| §11.200(a)(1) | Electronic signatures employing at least two distinct identification components (e.g., password and token) | Double-authentication certification: Step 1 = password re-entry (`AuthService.verify_password()`), Step 2 = OTP verification (`OTP` model, single-use, 10-minute expiry) | `ParsedDataSignView`; `OTP` model; `CertificationModal` |
| §11.200(a)(2) | When an individual executes a series of signings during a single period of controlled system access, first signing uses all components, subsequent signings may use one component | Each certification event requires both components; session-based multi-signing with one factor is a configurable option per customer SOP | Configurable |
| §11.200(b) | Electronic signatures not based on biometrics shall employ at least two distinct identification components | Password + OTP satisfies this requirement | Implemented |
| §11.300(a) | Maintain the uniqueness of each combined identification code and password | Unique `username` enforced at database level; password hashing via Django's configurable hashers (PBKDF2-SHA256 by default) | Django `User` model constraints; `AUTH_USER_MODEL = "core.User"` |
| §11.300(b) | Ensure revisability of identification codes and passwords on a periodic basis | Password change capability via standard Django auth; password policy enforcement configurable | Procedural + Django auth framework |
| §11.300(c) | Use of transaction safeguards to prevent unauthorized use of passwords and/or identification codes | JWT access token expires in 15 minutes; refresh token expires in 7 days; token rotation on refresh; OTP single-use | `JWTService`; `OTP.used` flag |
| §11.300(d) | Testing devices, such as tokens or cards, for proper function | OTP validated via `OTP.objects.filter(code=otp_code, used=False, expires_at__gt=timezone.now())` | `ParsedDataSignView.post()` |
| §11.300(e) | Use of initial and periodic testing of devices, such as tokens or cards | OTP generation and delivery tested in test suite; unit tests for `OTPService` | Test coverage requirement |

---

## 5. EU Annex 11 Compliance Matrix

The following table maps each numbered point of EU GMP Annex 11 (current version) to BioNexus features and implementation details.

### 5.1 General and Principles

| Annex 11 Ref | Requirement Summary | BioNexus Implementation | Status |
|---|---|---|---|
| Principles | Risk management shall be applied throughout the lifecycle of the computerised system | ICH Q9 risk assessment performed (Section 13); GAMP5 Category 5 validation lifecycle; risk-based testing scope | Implemented |
| Principles | Supplier and customer should collaborate to ensure data integrity | BioNexus provides technical controls; customer is responsible for organizational controls (SOPs, training); GMP4U partnership provides CSV support | Shared responsibility model |

### 5.2 Project Phase

| Annex 11 Ref | Requirement Summary | BioNexus Implementation | Status |
|---|---|---|---|
| 1 (Validation) | Evidence of appropriate validation for all applicable systems | V-Model validation lifecycle (Section 7); IQ/OQ/PQ approach (Section 8); traceability matrix | In progress |
| 2 (Personnel) | Appropriate qualifications for all personnel involved in computerised systems | RBAC enforces role-appropriate access; ADMIN role required for user management; training documentation required | Procedural |
| 3 (Suppliers) | Quality system and audit trail capability of supplier | BioNexus Supplier Assessment (Section 14); Git-based change control; conventional commits; security architecture documentation | Implemented |
| 4.1 (Validation documents) | User requirements specification (URS) and risk assessment | URS maintained in project documentation; ICH Q9 risk assessment (Section 13) | In progress |
| 4.2 (Configuration) | Validation of configurable systems should include evidence that configuration matches approved specification | Deployment configuration captured in environment variables; settings documented and version-controlled | Implemented |
| 4.3 (Test environment) | Tests should be performed in a controlled environment | Separate development, staging, and production environments; test database isolation | Procedural |
| 4.4 (Data migration) | Data migration validated if data is migrated from a legacy system | Data migration scripts validated before execution; pre/post migration record counts verified | When applicable |
| 4.5 (System retirement) | System retirement strategy | Soft delete pattern preserves all records; data export capability before retirement | Partial |

### 5.3 Operational Phase

| Annex 11 Ref | Requirement Summary | BioNexus Implementation | Status |
|---|---|---|---|
| 5 (Data) | Data must be accurate, complete, current, consistent, and attributable | ALCOA+ enforcement (Section 6); SHA-256 integrity chain; mandatory `user_id` attribution | Implemented |
| 6 (Accuracy checks) | For critical data entered manually, additional checks required | Pydantic strict schema validation (`extra="forbid"`); type enforcement without coercion; regex pattern validation; human review gate for all AI-extracted data | Implemented |
| 7 (Data storage) | Data should be secured against deliberate or accidental modification | `AuditLog` immutability enforced at `save()` level; SHA-256 chain detects any modification; soft delete only | Implemented |
| 8 (Printouts) | Printouts should be signed, dated, and clearly identify the system | PDF reports include: certified-by, timestamp, SHA-256 hash, QR code, system identifier, GxP version | Implemented |
| 9 (Audit trails) | Consideration should be given to building into the system the creation of a record of all relevant changes and deletions | All CREATE, UPDATE, DELETE, and SIGN operations logged to `AuditLog` with mandatory `user_id`, `timestamp`, `changes` dict, `snapshot_before`, `snapshot_after`, SHA-256 signature | Implemented |
| 10 (Change and configuration management) | Procedures must be in place for the management of changes | Git-based change control with conventional commits; change impact assessment SOP; revalidation triggers (Section 12) | Implemented |
| 11 (Periodic evaluation) | Systems should be periodically evaluated to confirm they remain in a validated state | Periodic review SOP; SHA-256 chain integrity check API (`GET /api/integrity/check/`); automated continuous integrity monitoring | Implemented |
| 12 (Security) | Physical and logical controls to prevent unauthorized access | Multi-tenant isolation (`tenant_id` on all data models); RBAC; JWT authentication; HTTPS in production; no hardcoded secrets | Implemented |
| 13 (Incident management) | Procedure for reporting and managing deviations | Chain integrity tampering detection triggers alerts; deviation SOP required from customer; `corruption_detected` flag surfaces to UI | Partial |
| 14 (Electronic signature) | Requirements for electronic signatures in GxP environments | Double-auth certification (password + OTP); non-repudiable `AuditLog` SIGN record; `certified_by` linked to `User` record | Implemented |
| 15 (Batch release) | Where electronic batch records are used, controls to ensure only authorized users can release batches | `CertifiedReport` creation requires `permission: audit:export` and double authentication; state machine prevents premature certification | Implemented |
| 16 (Business continuity) | Alternative arrangements for systems unavailable | GCP infrastructure SLA; PostgreSQL backup procedures; disaster recovery plan required | Procedural |
| 17 (Archiving) | Data may be archived to alternative media provided validation is performed | Certified reports exportable as JSON and PDF; archive integrity verifiable via SHA-256 hash re-verification | Implemented |

---

## 6. ALCOA+ Data Integrity Mapping

ALCOA+ is the data integrity standard adopted by global regulators (FDA, EMA, WHO, MHRA) describing the required attributes of all GxP data. The following table maps each ALCOA+ principle to the specific BioNexus implementation in the parsing pipeline and audit trail.

### 6.1 ALCOA+ Principle Mapping

| ALCOA+ Principle | Definition | BioNexus Implementation | Technical Reference |
|---|---|---|---|
| **A — Attributable** | It must be possible to identify who created, changed, or deleted data and when | Every `AuditLog` record requires `user_id` (integer FK) and `user_email` (string) at code level; `ValueError` raised if either is absent; JWT token embeds `user_id` and `tenant_id` in every authenticated request | `AuditTrail.record()` — mandatory parameter enforcement; `SECURITY_ARCHITECTURE.md §4` |
| **L — Legible** | Records must be readable throughout the retention period | `AuditLog.changes` stored as structured JSON dict `{field: {before, after}}`; Pydantic schemas enforce typed, named fields; human-readable `user_email` alongside machine `user_id`; PDF export for human review | `ParsedData.confirmed_json`; `AuditLog.changes`; `GET /api/reports/{id}/pdf/` |
| **C — Contemporaneous** | Data must be recorded at the time it was generated | `RawFile.uploaded_at` uses `auto_now_add=True` (immutable on creation); `AuditLog.timestamp` uses `auto_now_add=True`; `ParsedData.extracted_at`, `validated_at`, `CertifiedReport.certified_at` all recorded at action time | Django model field `auto_now_add=True`; `PARSING_ARCHITECTURE.md §Data Models` |
| **O — Original** | The first record of the data or a certified true copy must be preserved | `RawFile` model stores complete binary `file_content` and computes `file_hash` (SHA-256) on upload; file is never modified; `FileHasher.verify_integrity()` can verify at any time; original AI output stored in `parsed_json` separately from `confirmed_json` | `RawFile.file_content`; `RawFile.file_hash`; `PARSING_ARCHITECTURE.md §1` |
| **A — Accurate** | Data must be correct and truthful, with errors corrected and retained | Strict Pydantic validation with `extra="forbid"` prevents hallucinated fields; type enforcement (coercion disabled); regex patterns validate enumerations; human must explicitly review and approve all AI-extracted data before it enters confirmed state; corrections tracked in `CorrectionTracker` with before/after and reason | `BatchExtractionResult` schema; `EquipmentData(extra="forbid")`; `PARSING_ARCHITECTURE.md §Pydantic Schemas` |
| **C — Complete** | All data must be present with no omissions | Full file content preserved in `RawFile.file_content`; `AuditLog` records `snapshot_before` and `snapshot_after` for every operation; no partial writes to confirmed data; validation gate prevents incomplete corrections from proceeding to certification | `AuditLog.snapshot_before/after`; state machine `PENDING → VALIDATED → certified` |
| **C — Consistent** | Data must be internally and externally consistent | Same Pydantic schema (`EquipmentData`, `SampleData`) applied to all extractions of same data type; `tenant_id` enforced on every query to prevent cross-tenant inconsistency; SHA-256 chain provides cross-record consistency verification | `SampleRepository.get_all(tenant_id)`; `BatchExtractionResult` uniform schema |
| **E — Enduring** | Records must remain intact and available for the defined retention period | Soft delete only (`is_deleted` flag, never `DELETE FROM`); `AuditLog` has no delete mechanism; `RawFile` and `CertifiedReport` are permanent records; retention period configurable per tenant | `is_deleted` pattern; `AuditLog` model without delete endpoint |
| **A — Available** | Data must be accessible and readable on demand | `GET /api/auditlog/` with filtering; `GET /api/reports/{id}/` for certified reports; `GET /api/integrity/check/` for real-time chain status; `GET /api/reports/{id}/pdf/` for human-readable export; chain integrity check runs every 30 seconds via frontend `useChainVerification` hook | All GET endpoints; `integrityService.checkChainIntegrity()` |

### 6.2 Data Integrity Workflow (ALCOA+ Perspective)

```
STEP 1: RAW DATA INGESTION
  Lab instrument output → RS232/USB → BioNexus Box → HTTPS → Platform
  [O] RawFile created: file_content (binary), file_hash (SHA-256), uploaded_at (UTC)
  [A] user_id of uploader recorded in AuditLog
  [C] uploaded_at set by system clock (auto_now_add)

STEP 2: AI EXTRACTION
  GPT-4/Claude parses RawFile content
  ParsedData.state = PENDING
  [A] parsed_json stored as-is (unmodified AI output)
  [A-ccurate] Pydantic validates: extra="forbid", type enforcement, regex
  [C] extracted_at recorded

STEP 3: HUMAN REVIEW GATE
  Human validator reviews parsed_json vs. original file
  [A-ttributable] validator user_id required
  Corrections tracked in CorrectionTracker: field, before, after, reason, who, when
  [L] CorrectionTracker provides legible audit of all human interventions
  [C] validated_at recorded

STEP 4: CONFIRMATION
  ParsedData.state = VALIDATED
  confirmed_json = human-approved data
  [C-omplete] All corrections documented; none skipped
  AuditLog: state transition recorded with user_id and timestamp

STEP 5: CERTIFICATION (ELECTRONIC SIGNATURE)
  Double-auth: password + OTP
  CertifiedReport created (immutable)
  [E] Certified report never deleted
  AuditLog: SIGN operation with full attribution
  SHA-256 hash of complete report stored in report_hash
```

---

## 7. Computerized System Validation (CSV) Strategy

### 7.1 V-Model Validation Lifecycle

BioNexus follows the GAMP5 V-Model lifecycle, aligning left-side specification documents with right-side verification activities:

```
LEFT SIDE (Specification)                    RIGHT SIDE (Verification)
─────────────────────────────────────────────────────────────────────
User Requirements Specification (URS)  ←──→  Performance Qualification (PQ)
         │                                              │
Functional Specification (FS)          ←──→  Operational Qualification (OQ)
         │                                              │
Design Specification (DS)              ←──→  Installation Qualification (IQ)
         │                                              │
         └──────────────── Coding & Unit Testing ───────┘
```

### 7.2 Validation Documents

| Document | Purpose | Responsible Party | Status |
|---|---|---|---|
| User Requirements Specification (URS) | Defines what the system must do from the user's perspective | Customer (regulated user) with BioNexus support | Template available |
| Functional Specification (FS) | Defines how the system will meet the URS | BioNexus | SECURITY_ARCHITECTURE.md, PARSING_ARCHITECTURE.md, DOCUMENTATION.md |
| Design Specification (DS) | Technical design details: data models, APIs, security | BioNexus | Contained in architecture documents |
| Installation Qualification (IQ) | Verifies system is installed correctly | Customer with BioNexus support | Protocol available |
| Operational Qualification (OQ) | Verifies system operates as specified | Customer with BioNexus support | Protocol available |
| Performance Qualification (PQ) | Verifies system performs in actual use conditions | Customer | Protocol available |
| Traceability Matrix | Links URS requirements to test scripts | BioNexus + Customer | In preparation |
| Validation Summary Report | Documents overall validation outcome | Customer | Post-execution |

### 7.3 Validation Scope Boundaries

**In Scope (BioNexus Application):**
- Authentication and session management (JWT, RBAC)
- Multi-tenant data isolation
- File upload and SHA-256 hashing
- AI parsing pipeline and Pydantic validation
- Human review and correction workflow
- Electronic signature certification (double-auth)
- Audit trail generation and SHA-256 chain integrity
- Report generation (PDF, JSON)
- API endpoints for all above functions
- Chain integrity monitoring and tampering detection

**In Scope (Infrastructure Qualification):**
- Django framework version and configuration
- PostgreSQL version and configuration
- GCP environment specification (compute, storage, networking)
- HTTPS/TLS certificate configuration

**Out of Scope (Customer Organizational Controls):**
- Standard Operating Procedures (SOPs) for system use
- User training and competence assessment
- Physical access controls to laboratory network
- Backup and disaster recovery procedures (customer-defined)
- AI model selection and validation (GPT-4, Claude — third-party)

### 7.4 Test Strategy

| Test Level | Description | Framework | Coverage Target |
|---|---|---|---|
| Unit Tests | Individual functions and methods | Django `TestCase`, `pytest` | 100% of service layer business logic |
| Integration Tests | Service + database interactions | Django test client | All repository methods, all API endpoints |
| E2E Tests | Full user workflow simulation | Cypress | All critical compliance workflows (upload → parse → validate → certify) |
| Security Tests | Authentication, RBAC, injection | Manual + automated | All permission boundaries |
| Integrity Tests | SHA-256 chain, tampering detection | `FileHasher` test suite | Hash verification pass/fail scenarios |
| Regression Tests | Post-change validation | Full test suite re-run | All tests pass before deployment |

### 7.5 Test Coverage for Compliance-Critical Functions

| Function | Test Scenario | Expected Result |
|---|---|---|
| `AuditTrail.record()` without `user_id` | Call with `user_id=None` | `ValueError` raised |
| SHA-256 chain integrity | Modify an `AuditLog` record directly in DB | `verify_chain_integrity()` returns `corrupted_records: [id]` |
| File hash verification | Modify `file_content` after upload | `FileHasher.verify_integrity()` returns `False` |
| Pydantic extra field rejection | Submit AI output with unknown field | `ValidationError` raised, workflow stops |
| OTP single-use enforcement | Attempt to reuse OTP | `OTP.objects.filter(used=False)` returns no result, authentication fails |
| Tenant isolation | Query Sample with wrong `tenant_id` | Returns `None` (not 403 — prevents tenant enumeration) |
| RBAC permission enforcement | Call delete endpoint with VIEWER role | HTTP 403 returned |
| State machine enforcement | Call `/sign/` on `PENDING` ParsedData | HTTP 400 or 422 returned |

---

## 8. Qualification Approach (IQ/OQ/PQ Summary)

### 8.1 Installation Qualification (IQ)

The IQ verifies that BioNexus has been correctly installed in the customer environment according to approved specifications.

**IQ Scope and Checks:**

| IQ Test ID | Check | Acceptance Criterion |
|---|---|---|
| IQ-001 | Python version verification | Python 3.12.x installed and `python --version` returns expected version |
| IQ-002 | Django version verification | `django.VERSION` returns 4.2.x |
| IQ-003 | PostgreSQL installation and connectivity | Django `migrate` completes without error; database tables created |
| IQ-004 | Environment variables present | All required variables (`DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_DEBUG=false`) present and non-empty |
| IQ-005 | HTTPS/TLS configuration | SSL certificate valid; HTTP requests redirect to HTTPS |
| IQ-006 | Authentication endpoint availability | `POST /api/auth/login/` returns 200 with valid credentials |
| IQ-007 | Database schema correctness | All expected tables present: `AuditLog`, `RawFile`, `ParsedData`, `CertifiedReport`, `User`, `Role`, `Permission`, `Tenant` |
| IQ-008 | File storage accessibility | Upload endpoint accepts files up to configured `MAX_FILE_SIZE` (100 MB) |
| IQ-009 | Audit trail recording | First `AuditLog` record created with valid `signature` field after initial operation |
| IQ-010 | Multi-tenant isolation | Two users from different tenants cannot access each other's data |

### 8.2 Operational Qualification (OQ)

The OQ verifies that BioNexus operates as designed across all specified functions and boundary conditions.

**OQ Scope and Checks:**

| OQ Test ID | Function | Test Action | Acceptance Criterion |
|---|---|---|---|
| OQ-001 | Authentication | Login with valid credentials | JWT access + refresh tokens returned; `user_id`, `tenant_id` in response |
| OQ-002 | Authentication | Login with invalid credentials | HTTP 401 returned; no tokens issued |
| OQ-003 | Authentication | Access protected endpoint without token | HTTP 401 returned |
| OQ-004 | RBAC | LAB_TECHNICIAN attempts sample delete | HTTP 403 returned |
| OQ-005 | RBAC | ADMIN performs all operations | All operations succeed |
| OQ-006 | File Upload | Upload valid CSV file | `RawFile` created; `file_hash` populated; `AuditLog` CREATE record created |
| OQ-007 | File Upload | Upload file with duplicate hash | Existing `RawFile` returned; no duplicate created |
| OQ-008 | Parsing | AI output with extra fields submitted | `ValidationError` raised; `ParsedData` not created |
| OQ-009 | Parsing | Valid AI output submitted | `ParsedData` created with `state=PENDING` |
| OQ-010 | Human Review | Validator approves with corrections | `ParsedData.state=VALIDATED`; corrections in `CorrectionTracker`; `AuditLog` UPDATE recorded |
| OQ-011 | Human Review | Validator rejects parsing | `ParsedData.state=REJECTED`; rejection reason in `AuditLog` |
| OQ-012 | Certification | Valid password + valid OTP | `CertifiedReport` created; `AuditLog` SIGN record created |
| OQ-013 | Certification | Invalid password | HTTP 401; no `CertifiedReport` created |
| OQ-014 | Certification | Expired OTP | HTTP 401; no `CertifiedReport` created |
| OQ-015 | Certification | Reused OTP | HTTP 401; OTP `used=True` prevents re-use |
| OQ-016 | Chain Integrity | Normal operation | `GET /api/integrity/check/` returns `is_valid: true` |
| OQ-017 | Chain Integrity | Tampered `AuditLog` record | `GET /api/integrity/check/` returns `corrupted_records: [id]`, `is_valid: false` |
| OQ-018 | Audit Export | Export with chain intact | Export includes `chain_verification: {is_intact: true}`; `export_signature` present |
| OQ-019 | Audit Log | All mandatory fields present | Every `AuditLog` has non-null `user_id`, `user_email`, `timestamp`, `signature` |
| OQ-020 | Tenant Isolation | User queries data from different tenant | Returns empty result; no cross-tenant data leak |

### 8.3 Performance Qualification (PQ)

The PQ verifies that BioNexus performs correctly in the customer's actual use environment with real users performing real tasks.

**PQ Scope:**

PQ is executed by the customer (regulated user) under GMP conditions, using actual or representative production data. BioNexus provides PQ protocol templates covering:

| PQ Area | Description |
|---|---|
| End-to-End Workflow | Complete workflow from instrument file upload through double-auth certification; executed by qualified personnel using production or qualified representative data |
| Audit Trail Completeness | Verification that all GMP-relevant data entries are captured in the audit trail; QA review of audit log for 30-day sample period |
| Report Integrity | Verification that exported PDF and JSON reports match audit trail content; SHA-256 hash verification of archived reports |
| User Access Review | Confirmation that all active users have appropriate roles; no unauthorized access identified |
| Chain Integrity | Execution of `GET /api/integrity/check/` on production audit trail; confirmation of zero corrupted records |
| System Performance | Response time under load; no data loss during concurrent operations |

---

## 9. Electronic Signatures and Records

### 9.1 Electronic Signature Architecture

BioNexus implements a two-factor electronic signature mechanism for data certification events, complying with 21 CFR §11.200(a) requirements for non-biometric signatures:

**Factor 1 — Knowledge (Password Re-entry)**
- User re-enters their password during the certification modal
- Password is verified server-side via `request.user.check_password(password)`
- This is a re-authentication event, not a session check — the existing JWT session is not sufficient
- Prevents rubber-stamping (user must actively engage with the certification)

**Factor 2 — Possession (One-Time Password)**
- OTP generated and delivered to the user (email or SMS via Twilio/AWS SNS in production)
- OTP is stored hashed in the `OTP` model with `expires_at` set to 10 minutes from generation
- `used` flag set to `True` immediately upon first use; subsequent use attempts rejected
- Filter: `OTP.objects.filter(user=request.user, code=otp_code, used=False, expires_at__gt=timezone.now())`

**Factor 3 — Acknowledgment (Explicit Consent)**
- Certification modal Step 3 presents an explicit statement: "I certify that all data is accurate and complete"
- User must check an acknowledgment checkbox before submission is enabled
- This models the intent requirement of §11.50(a)(3)

### 9.2 Signature Workflow

```
User clicks [CERTIFY FOR AUDIT]
        │
        ▼
CertificationModal — Step 1: Password Re-entry
        │ POST /api/auth/verify-password/
        │ {password: "****"}
        │ ← {valid: true}
        │
        ▼
CertificationModal — Step 2: OTP Entry
        │ (OTP delivered out-of-band)
        │
        ▼
CertificationModal — Step 3: Review and Confirm
        │ Checkbox: "I certify that all data is accurate"
        │
        ▼
POST /api/parsing/{id}/sign/
        │ {password: "****", otp_code: "123456", notes: "..."}
        │
        ▼
ParsedDataSignView.post()
        │ verify_password() → OK
        │ verify_otp() → OK, mark used=True
        │
        ▼
CertifiedReport created (immutable)
report_hash = SHA-256(cert_initial + report_data_json)
        │
        ▼
AuditLog.record(
    entity_type = "CertifiedReport",
    entity_id   = report.id,
    operation   = "SIGN",
    user_id     = request.user.id,  ← MANDATORY
    user_email  = request.user.email,
    timestamp   = timezone.now(),
    changes     = {},
    snapshot_after = {
        "report_id": report.id,
        "certification_method": "password+otp",
        "notes": notes
    }
)
```

### 9.3 Non-Repudiation

Non-repudiation is enforced through the following chain of evidence:

1. **User identity confirmed**: JWT token established identity at session start; password re-entry re-confirms at signing time
2. **Uniqueness of event**: OTP is single-use; the same signing event cannot be replicated by a replay attack
3. **Immutable record**: `AuditLog` SIGN record contains `user_id`, `user_email`, `timestamp`, SHA-256 `signature` — none of these can be changed without breaking the chain
4. **Cryptographic link**: The `CertifiedReport.report_hash` is calculated over the complete report content including the certifying user's identity; altering the certified-by field would change the hash

### 9.4 Electronic Records

All GxP-relevant records in BioNexus are electronic records subject to Part 11 and Annex 11 controls:

| Record Type | Model | Retention | Access Control |
|---|---|---|---|
| Raw instrument files | `RawFile` | Indefinite (soft delete) | Tenant-scoped; `sample:view` permission |
| Parsed data (AI extraction) | `ParsedData` | Indefinite | Tenant-scoped; `sample:view` permission |
| Corrections | `CorrectionTracker` | Indefinite | Tenant-scoped; `audit:view` permission |
| Audit log entries | `AuditLog` | Indefinite; no delete mechanism | Tenant-scoped; `audit:view` permission |
| Certified reports | `CertifiedReport` | Indefinite (immutable) | Tenant-scoped; `audit:export` permission |
| Execution logs | `ExecutionLog` | Indefinite | Tenant-scoped; `sample:view` permission |
| Execution steps | `ExecutionStep` | Indefinite | Tenant-scoped; `sample:view` permission |

---

## 10. Audit Trail Design

### 10.1 Audit Trail Overview

The BioNexus audit trail is an append-only, immutable ledger of all system operations that create, modify, or logically delete GxP-relevant data. It is implemented as the `AuditLog` Django model, with SHA-256 chaining to provide cryptographic evidence of record integrity.

### 10.2 AuditLog Data Model

```python
class AuditLog(models.Model):
    entity_type      : str        # "RawFile", "ParsedData", "CertifiedReport",
                                  # "Sample", "Protocol", "ExecutionLog", etc.
    entity_id        : int        # Primary key of the affected record
    operation        : str        # CREATE | UPDATE | DELETE | SIGN
    timestamp        : datetime   # UTC, auto_now_add=True (immutable after creation)
    user_id          : int        # Mandatory — FK to User; raises ValueError if absent
    user_email       : str        # Mandatory — human-readable identity
    changes          : dict       # {field_name: {before: value, after: value}}
    snapshot_before  : dict       # Complete record state before operation
    snapshot_after   : dict       # Complete record state after operation
    signature        : str        # SHA-256(previous_signature + json(this_record))
    previous_signature: str       # SHA-256 of immediately preceding AuditLog record
```

### 10.3 What Is Logged

| Event Category | Logged Events |
|---|---|
| Authentication | Login success; login failure; token refresh; logout |
| File Operations | File upload (`RawFile CREATE`); file hash verification; duplicate detection |
| Parsing | AI extraction (`ParsedData CREATE`); schema validation failure |
| Human Review | Correction added (`CorrectionTracker CREATE`); validation approved (`ParsedData UPDATE: PENDING→VALIDATED`); parsing rejected (`ParsedData UPDATE: PENDING→REJECTED`) |
| Certification | Electronic signature event (`CertifiedReport SIGN`); OTP issuance and use |
| Sample Management | Sample CREATE, UPDATE, DELETE (soft); protocol assignment |
| Administration | User creation/modification; role assignment; permission changes |
| Integrity Checks | Chain verification results; tampering detection events |

### 10.4 SHA-256 Chain Integrity Mechanism

The chain integrity mechanism ensures that no `AuditLog` record can be silently modified or deleted without detection.

**Chain Construction:**

```python
# core/utils/integrity.py

def calculate_signature(previous_signature: str, audit_log_data: dict) -> str:
    base = (previous_signature or "initial") + json.dumps(audit_log_data, sort_keys=True)
    return hashlib.sha256(base.encode()).hexdigest()
```

The chain is constructed as follows:
- `AuditLog[1].signature = SHA-256("initial" + json(log1_data))`
- `AuditLog[2].signature = SHA-256(AuditLog[1].signature + json(log2_data))`
- `AuditLog[N].signature = SHA-256(AuditLog[N-1].signature + json(logN_data))`

**Tamper Detection:**

If any record in the chain is modified, its signature will no longer match the expected value calculated from its predecessor. Moreover, all subsequent records will also fail validation because their `previous_signature` input is now invalid. A single point of tampering invalidates the entire tail of the chain from that point forward.

```python
def verify_chain_integrity() -> dict:
    audit_logs = AuditLog.objects.all().order_by('timestamp')
    previous_sig = "initial"
    corrupted = []
    for log in audit_logs:
        expected_sig = calculate_signature(previous_sig, {
            'entity_type': log.entity_type,
            'entity_id': log.entity_id,
            'operation': log.operation,
            'timestamp': str(log.timestamp),
            'changes': log.changes
        })
        if expected_sig != log.signature:
            corrupted.append(log.id)
        previous_sig = log.signature
    return {'is_valid': len(corrupted) == 0, 'corrupted_records': corrupted}
```

**Continuous Monitoring:**
- `GET /api/integrity/check/` can be called on demand
- Frontend `useChainVerification` hook polls every 30 seconds during active sessions
- `corruption_detected` flag surfaced to UI immediately upon detection
- In production: email alert to ADMIN users upon tampering detection

### 10.5 Audit Trail Export (Certified)

The certified audit export feature produces a tamper-proof export artifact suitable for regulatory submission or external audit:

```json
{
  "export_id": "audit-export-2026-02-28-12345",
  "timestamp": "2026-02-28T10:00:00Z",
  "exported_by": {"user_id": 456, "username": "auditor@lab.local"},
  "tenant_id": 123,
  "entity_type": "Sample",
  "entity_count": 47,
  "chain_verification": {
    "is_intact": true,
    "records_verified": 47,
    "message": "Chain integrity verified for 47 records"
  },
  "records": [...],
  "export_signature": "<sha256_of_entire_export>",
  "export_valid": true
}
```

Required permission: `audit:export` (ADMIN and AUDITOR roles only).

### 10.6 Audit Trail Retention

- **Minimum retention**: Configured per customer per applicable regulation (e.g., 1 year per 21 CFR 211.180(a) for API, up to batch disposition + 1 year; EU GMP Article 23: life of product + 1 year for medicinal products)
- **Deletion**: No hard delete exists in the system. The only mechanism is soft delete (`is_deleted=True`), which is itself logged in the `AuditLog`
- **Archiving**: Complete audit trail exportable as JSON for long-term archiving; SHA-256 hash allows integrity re-verification at any future date

---

## 11. Role-Based Access Control

### 11.1 Permission Model

BioNexus implements a granular, role-permission system. Permissions are assigned to roles, and roles are assigned to users. Individual permission overrides are not permitted — all access is role-derived.

**Defined Permissions:**

| Permission Code | Description |
|---|---|
| `sample:view` | Read access to Sample records |
| `sample:create` | Create new Sample records |
| `sample:update` | Modify existing Sample records |
| `sample:delete` | Soft-delete Sample records |
| `protocol:view` | Read access to Protocol records |
| `protocol:create` | Create new Protocol records |
| `protocol:update` | Modify Protocol records |
| `protocol:delete` | Soft-delete Protocol records |
| `audit:view` | Read access to AuditLog records |
| `audit:export` | Generate and download certified audit exports |
| `user:manage` | Create, modify, and deactivate Users |
| `role:manage` | Assign roles to Users |

### 11.2 Standard Roles and Permission Assignments

| Permission | ADMIN | PRINCIPAL_INVESTIGATOR | LAB_TECHNICIAN | AUDITOR | VIEWER |
|---|---|---|---|---|---|
| `sample:view` | Yes | Yes | Yes | Yes | Yes |
| `sample:create` | Yes | Yes | Yes | No | No |
| `sample:update` | Yes | Yes | Yes | No | No |
| `sample:delete` | Yes | No | No | No | No |
| `protocol:view` | Yes | Yes | Yes | Yes | Yes |
| `protocol:create` | Yes | Yes | No | No | No |
| `protocol:update` | Yes | Yes | No | No | No |
| `protocol:delete` | Yes | No | No | No | No |
| `audit:view` | Yes | Yes | Yes | Yes | No |
| `audit:export` | Yes | No | No | Yes | No |
| `user:manage` | Yes | No | No | No | No |
| `role:manage` | Yes | No | No | No | No |

### 11.3 Separation of Duties

Regulatory requirements mandate separation of duties to prevent a single individual from both executing and approving GxP-relevant operations. BioNexus enforces this through:

1. **Parsing Validation Gate**: A LAB_TECHNICIAN can upload files; a separate user with validation authorization must approve parsed data before it proceeds
2. **Certification Authorization**: Only users with double-authentication capability can create `CertifiedReport` records; the certifying user must be distinct from the system account in automated scenarios
3. **Audit Read-Only**: The AUDITOR role has read and export access but cannot modify any data — ensuring auditors cannot alter the records they are reviewing
4. **Admin/Operator Separation**: `user:manage` and `role:manage` permissions are restricted to ADMIN role; operational roles cannot promote themselves or create new privileged users

### 11.4 Multi-Tenant Isolation

Every user is assigned to exactly one `Tenant` (laboratory) at account creation. This assignment is immutable via normal operation — only ADMIN role users can manage tenant membership.

**Enforcement at every layer:**

```python
# HTTP Layer: @tenant_context decorator
request.tenant_id = jwt_payload['tenant_id']

# Service Layer: tenant_id passed explicitly
SampleService.get_samples(tenant_id=request.tenant_id)

# Repository Layer: mandatory filter
Sample.objects.filter(tenant_id=tenant_id, is_deleted=False)
```

Cross-tenant data access is architecturally impossible through the application layer — a compromised JWT from Tenant A cannot retrieve Tenant B's data because every query is hard-filtered by `tenant_id`.

### 11.5 RBAC Implementation

**Decorator-based enforcement:**
```python
@authenticate_required
@permission_required(Permission.SAMPLE_DELETE)
def delete_sample(request, sample_id):
    # Execution only reaches here if:
    # 1. Valid JWT present and not expired
    # 2. User is active (is_active=True)
    # 3. User's role includes sample:delete permission
    sample = SampleService.delete_sample(sample_id)
    return Response({"id": sample_id}, status=204)
```

**User permission check:**
```python
user.has_permission("sample:delete")  # → bool
user.get_permissions()                 # → ["sample:view", "sample:create", ...]
```

---

## 12. Change Control and Configuration Management

### 12.1 Change Categories

| Change Category | Description | Validation Impact |
|---|---|---|
| **Critical** | Changes to audit trail logic, SHA-256 chain algorithm, electronic signature mechanism, RBAC permission model, or data model affecting compliance records | Full regression test suite; formal change assessment; customer notification; requalification of affected OQ/PQ test cases |
| **Major** | New features, API endpoint changes, database schema migrations, dependency upgrades (Django, Python) | Regression testing; impact assessment; customer change notification; OQ test case update |
| **Minor** | Bug fixes, UI improvements, non-compliance documentation updates, configuration changes | Developer testing; code review; no formal requalification unless compliance-adjacent |
| **Emergency** | Security patches, critical bug fixes requiring immediate deployment | Expedited review; post-deployment documentation; retrospective impact assessment |

### 12.2 Change Control Process

**Step 1 — Change Request**
- All changes documented with unique ID, description, rationale, and risk classification
- Commit message follows conventional commits standard: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`

**Step 2 — Impact Assessment**
- Determine GAMP5 change category
- Identify affected system functions and validation tests
- Assess risk to data integrity, audit trail, electronic signatures, and access controls

**Step 3 — Review and Approval**
- Code review by at least one engineer not involved in the change
- QA review for compliance-adjacent changes
- For Critical changes: sign-off from regulatory/compliance function

**Step 4 — Testing**
- Unit tests added/updated for all changed logic
- Regression test suite executed
- Compliance-specific tests (chain integrity, RBAC, audit attribution) always included

**Step 5 — Deployment**
- Staged deployment: development → staging → production
- Post-deployment smoke test
- Chain integrity check immediately after deployment: `GET /api/integrity/check/`

**Step 6 — Documentation**
- Change captured in Git history with conventional commit message
- Validation documentation updated (traceability matrix, test scripts if affected)
- Customer change notification issued for Major and Critical changes

### 12.3 Configuration Management

**Version Control:**
- All application source code managed in Git (GitHub)
- Branching strategy: feature branches merged to `main` via pull request
- All commits require conventional commit format for traceability
- Tags applied for each production release

**Environment Configuration:**
- No hardcoded secrets; all configuration via environment variables
- Required variables: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- Environment-specific configuration not stored in source code
- Production environment configuration documented in deployment runbook

**Database Schema Management:**
- Django migrations track all schema changes
- Migrations reviewed for compliance impact before deployment
- No destructive migrations (DROP TABLE, DROP COLUMN) without formal data migration review
- Migration execution logged in deployment log

### 12.4 Software Version Tracking

| Component | Version Management | Pinning Strategy |
|---|---|---|
| BioNexus Application | Git tags (semantic versioning) | Source code pinned to release tag |
| Python | Specified in Dockerfile / `pyproject.toml` | Minor version pinned (e.g., 3.12.x) |
| Django | `requirements.txt` with pinned version | Exact version pinned |
| Dependencies | `requirements.txt` with pinned versions | All dependencies pinned |
| PostgreSQL | Docker image tag or cloud provider version | Major version pinned |
| Node.js / npm | `package.json` with `engines` field | Minor version pinned |

---

## 13. Risk Assessment (per ICH Q9)

### 13.1 Risk Management Framework

BioNexus applies ICH Q9 principles to risk identification, assessment, control, and communication throughout the system validation lifecycle. Risk is assessed on two dimensions:

- **Probability (P)**: Likelihood of the risk event occurring (1=Low, 2=Medium, 3=High)
- **Severity (S)**: Impact on data integrity, patient safety, or regulatory compliance (1=Low, 2=Medium, 3=High)
- **Risk Priority Number (RPN)**: P × S (range 1–9)

Risk levels: Low (RPN 1–2), Medium (RPN 3–4), High (RPN 6–9)

### 13.2 System Risk Assessment

| Risk ID | Risk Description | Probability | Severity | RPN | Risk Level | BioNexus Control | Residual Risk |
|---|---|---|---|---|---|---|---|
| R-001 | Unauthorized access to GxP records | 2 | 3 | 6 | High | JWT authentication + RBAC + multi-tenant isolation; access token 15-min expiry; `@authenticate_required` on all endpoints | Low |
| R-002 | Audit trail record tampering | 1 | 3 | 3 | Medium | SHA-256 chain; `AuditLog` immutability at model level; continuous chain verification; tampering detection alert | Low |
| R-003 | Repudiation of electronic signature | 1 | 3 | 3 | Medium | Double-auth (password + OTP); mandatory `user_id` in SIGN audit record; OTP single-use; `certification_method` recorded | Low |
| R-004 | AI extraction hallucination accepted as fact | 2 | 3 | 6 | High | Pydantic `extra="forbid"` rejects unknown fields; all AI output requires human review gate (PENDING state); corrections tracked | Low |
| R-005 | Data entered without attribution | 1 | 3 | 3 | Medium | `AuditTrail.record()` raises `ValueError` if `user_id` is None; JWT required on all endpoints; no anonymous data entry | Low |
| R-006 | Cross-tenant data leak | 1 | 3 | 3 | Medium | `tenant_id` FK enforced on all data models; all repository queries hard-filtered by `tenant_id`; `@tenant_context` decorator | Low |
| R-007 | Loss of GxP records due to system failure | 2 | 3 | 6 | High | GCP infrastructure with high availability; PostgreSQL backup; soft delete (no hard deletion); `RawFile.file_content` preserved | Medium |
| R-008 | Incorrect data validation by human reviewer | 3 | 2 | 6 | High | Correction tracker documents all changes; original data preserved in `parsed_json`; human reviewer `user_id` in audit log; procedural control via SOP | Medium |
| R-009 | System access after user departure | 2 | 2 | 4 | Medium | `is_active=False` flag immediately disables all authentication; refresh token invalidation; ADMIN manages user accounts | Low |
| R-010 | Unauthorized privilege escalation | 1 | 3 | 3 | Medium | `role:manage` restricted to ADMIN only; server-side permission enforcement; no client-side permission bypass | Low |
| R-011 | Time synchronization error affecting audit timestamps | 1 | 2 | 2 | Low | GCP server time synchronized via NTP; `auto_now_add` uses server time; no client-provided timestamps for audit records | Low |
| R-012 | SQL injection or code injection attack | 1 | 3 | 3 | Medium | Django ORM parameterized queries prevent SQL injection; Pydantic validation rejects unexpected input structure | Low |
| R-013 | Backup failure leading to record loss | 1 | 3 | 3 | Medium | GCP automated backups; backup verification procedures; disaster recovery plan required as customer SOP | Medium (procedural) |
| R-014 | Change to SHA-256 algorithm breaking existing chain | 1 | 3 | 3 | Medium | Algorithm changes classified as Critical (Section 12.1); full impact assessment required; chain re-verification post-change | Low |
| R-015 | OTP delivery failure preventing legitimate certification | 2 | 1 | 2 | Low | OTP backup delivery channel (email + SMS); OTP expiry is 10 minutes; administrator can reset OTP delivery | Low |

### 13.3 Residual Risk Acceptance

Risks rated as residual Medium after controls are applied (R-007: system failure; R-008: human error; R-013: backup failure) are accepted with the following conditions:

- **R-007**: Customer must implement and test a backup and restore procedure as a condition of production deployment. BioNexus provides architecture guidance.
- **R-008**: Human reviewer training and competence assessment SOP required. Split-view UI showing original vs. corrected data reduces likelihood of review errors.
- **R-013**: Customer disaster recovery SOP required. BioNexus provides data export capability to support recovery procedures.

---

## 14. Supplier Assessment

### 14.1 BioNexus as a Regulated Supplier

Under EU Annex 11 (Point 3) and GAMP5, regulated users must assess their software suppliers to verify that the supplier operates an appropriate quality system and can provide evidence of system reliability, change control, and technical competence.

This section documents what customers can expect from BioNexus as a supplier.

### 14.2 Development Quality System

| Quality System Element | BioNexus Practice |
|---|---|
| **Version Control** | Git (GitHub) with mandatory pull request reviews for all changes |
| **Change Control** | Conventional commits; categorized changes (feat/fix/refactor/docs/test); tagged releases |
| **Code Review** | Minimum one reviewer approval required before merge to `main` |
| **Testing** | Django test framework; unit, integration, E2E tests required for all features; "Every endpoint needs at least one happy-path and one error test" (CLAUDE.md) |
| **Security** | No hardcoded secrets; environment variables for all configuration; password hashing (PBKDF2-SHA256); JWT with appropriate lifetimes |
| **Documentation** | Architecture documentation maintained in repository (SECURITY_ARCHITECTURE.md, PARSING_ARCHITECTURE.md); CLAUDE.md for development standards |
| **Compliance by Design** | RBAC, audit trail, ALCOA+, SHA-256 chain, double-auth designed into initial architecture, not added post-hoc |
| **Type Safety** | PEP 8 compliance; type hints required on all functions; Pydantic strict validation for all data ingestion |

### 14.3 Evidence Available to Customers

BioNexus can provide the following documentation to support customer supplier qualification:

| Document | Availability |
|---|---|
| This GxP Compliance Master Document | Available |
| Security Architecture Document | Available |
| Parsing Architecture Document | Available |
| Product Documentation | Available |
| IQ/OQ/PQ Protocol Templates | Available upon request |
| Source code review access (NDA) | Available upon request |
| Penetration test reports | Available upon request (planned) |
| Third-party audit reports | Planned |
| SOC 2 Type II (GCP) | Via Google Cloud documentation |

### 14.4 GMP4U Partnership

BioNexus has established a validation partnership with **GMP4U (Johannes Eberhardt)**, a certified CSV/qualification specialist. GMP4U provides:

- Independent review of BioNexus validation documentation
- Development of customer-specific IQ/OQ/PQ protocols
- Qualification execution support and witnessing
- Regulatory audit support for customers
- Gap assessments for Part 11 and Annex 11 compliance

This partnership ensures customers have access to independent qualification expertise rather than relying solely on BioNexus self-attestation.

### 14.5 Subcontractors and Third-Party Components

| Component | Supplier | Qualification Notes |
|---|---|---|
| Google Cloud Platform | Google LLC | SOC 2 Type II, ISO 27001/27017/27018; infrastructure qualification documentation available from Google |
| PostgreSQL | PostgreSQL Global Development Group | Open-source; GAMP5 Category 3; installation qualification by customer |
| OpenAI GPT-4 (optional) | OpenAI | AI extraction only; all output subject to human review gate; OpenAI data processing agreement required |
| Anthropic Claude (optional) | Anthropic | AI extraction only; same controls as GPT-4; data processing agreement required |
| Twilio (OTP delivery) | Twilio Inc. | SOC 2 Type II; used for OTP delivery only; not in the data integrity critical path |

---

## 15. Glossary

| Term | Definition |
|---|---|
| **21 CFR Part 11** | United States Code of Federal Regulations, Title 21, Part 11. FDA regulation governing electronic records and electronic signatures in FDA-regulated industries. |
| **ALCOA+** | Data integrity acronym: Attributable, Legible, Contemporaneous, Original, Accurate, plus Complete, Consistent, Enduring, Available. Framework used by global regulators to define the required attributes of GxP data. |
| **Annex 11** | Annex 11 to the EU Guide to Good Manufacturing Practice. European regulation governing computerised systems used in GMP-regulated activities. |
| **Audit Trail** | A secure, computer-generated, time-stamped electronic record that allows reconstruction of the course of events relating to the creation, modification, or deletion of an electronic record. |
| **BioNexus Box** | The BioNexus hardware gateway device. Connects laboratory instruments to the BioNexus cloud platform via RS232/USB on the instrument side and HTTPS on the cloud side. |
| **CAPA** | Corrective Action and Preventive Action. A systematic process for addressing deviations and preventing recurrence. |
| **CertifiedReport** | The BioNexus model representing an immutable, digitally signed audit package created at the conclusion of the double-auth certification workflow. |
| **Change Control** | A formal process for managing changes to a validated system to ensure continued compliance and validated status. |
| **CSV** | Computerized System Validation. The documented process of demonstrating that a computerized system consistently produces results meeting pre-defined specifications and quality attributes. |
| **cGMP** | Current Good Manufacturing Practice. FDA regulations (21 CFR Parts 210/211) governing the methods, facilities, and controls for manufacturing drugs and biologics. |
| **Django REST Framework (DRF)** | The Python web framework used to build the BioNexus API backend. |
| **Double Authentication** | The BioNexus electronic signature mechanism requiring password re-entry plus OTP verification before a `CertifiedReport` can be created. Satisfies 21 CFR §11.200(a) two-component requirement. |
| **EU GMP** | European Union Good Manufacturing Practice. Regulatory guidance for pharmaceutical manufacturing in the European Economic Area. |
| **GAMP5** | Good Automated Manufacturing Practice, 5th Edition. ISPE guidance document providing a risk-based approach to compliant GxP computerized systems validation. |
| **GCP** | Google Cloud Platform. The cloud infrastructure provider hosting the BioNexus backend services. |
| **GxP** | Good Practice. Collective term for quality guidelines in pharmaceutical, biotechnology, and medical device industries (GMP, GLP, GCP, GDP). |
| **ICH Q9** | International Council for Harmonisation guideline on Quality Risk Management. Provides principles and tools for risk-based decision-making in pharmaceutical quality systems. |
| **ICH Q10** | International Council for Harmonisation guideline on Pharmaceutical Quality System. |
| **IQ** | Installation Qualification. Documented verification that a system has been installed correctly according to approved specifications. |
| **JWT** | JSON Web Token. The authentication mechanism used by BioNexus. Tokens are signed with HS256 (HMAC-SHA256) and contain `user_id`, `tenant_id`, `role`, and `permissions`. |
| **Multi-tenant** | Architecture in which multiple independent customers (tenants/laboratories) share the same application instance with strict data isolation between tenants. |
| **Non-repudiation** | The property that a person cannot deny having performed an action. In BioNexus, achieved through mandatory `user_id` attribution, OTP-verified electronic signatures, and SHA-256 chain linking the signature to the record. |
| **OQ** | Operational Qualification. Documented verification that a system operates as intended across all specified functional requirements. |
| **OTP** | One-Time Password. A time-limited, single-use authentication code used as the second factor in BioNexus electronic signatures. |
| **ParsedData** | The BioNexus model representing data extracted from a raw laboratory file by an AI model, pending human review and validation. |
| **Pydantic** | A Python data validation library used in BioNexus to enforce strict schema validation on all AI-extracted data. Configured with `extra="forbid"` to prevent acceptance of unknown fields. |
| **PQ** | Performance Qualification. Documented verification that a system consistently performs as intended in actual use conditions with real users and real data. |
| **RBAC** | Role-Based Access Control. An access control mechanism in which permissions are assigned to roles, and roles are assigned to users, rather than assigning permissions directly to individuals. |
| **RawFile** | The BioNexus model representing an original, unmodified laboratory instrument file. Stores complete binary content and SHA-256 hash; never modified after creation. |
| **SHA-256** | Secure Hash Algorithm 256-bit. The cryptographic hash function used in BioNexus for file integrity verification and audit trail chain integrity. A deterministic, one-way function producing a 256-bit (64 hexadecimal character) digest. |
| **SHA-256 Chain** | The BioNexus audit trail integrity mechanism in which each `AuditLog` record's `signature` is computed as `SHA-256(previous_record_signature + this_record_data)`, creating a linked chain where any modification to a record invalidates all subsequent records. |
| **SOP** | Standard Operating Procedure. A documented procedure describing how to perform a regulated activity. BioNexus provides technical controls; customers are responsible for associated SOPs. |
| **Tenant** | In BioNexus, a Tenant represents a single customer laboratory. All data (samples, protocols, audit logs) is isolated per tenant. |
| **URS** | User Requirements Specification. A document describing what a system must do from the user's perspective, independent of how it is implemented. |
| **V-Model** | A validation lifecycle model in which specification activities on the left are verified by testing activities on the right, with each specification level having a corresponding qualification/test level. |

---

## Document Control

| Field | Value |
|---|---|
| Document ID | BNX-COMP-001 |
| Version | 1.0 |
| Status | Draft — For QA Review |
| Created | 2026-02-28 |
| Next Review | 2027-02-28 |
| Author | BioNexus Engineering & Regulatory Team |
| Reviewer | GMP4U (Johannes Eberhardt) |
| Approver | [QA Director — Customer] |

**Change History:**

| Version | Date | Author | Description |
|---|---|---|---|
| 0.1 | 2026-02-28 | BioNexus Team | Initial draft |
| 1.0 | 2026-02-28 | BioNexus Team | First release for distribution |

---

*This document is intended for use by qualified regulatory affairs, quality assurance, and validation professionals in GxP-regulated environments. It describes the technical and procedural controls implemented in the BioNexus platform as of the document date. Customers are responsible for verifying applicability to their specific regulatory context and for implementing required organizational controls (SOPs, training, periodic review) as part of their own quality management system.*

*BioNexus is not a legal or regulatory advisor. This document does not constitute a compliance certification. Independent qualification by a qualified person is required prior to use in regulated production environments.*
