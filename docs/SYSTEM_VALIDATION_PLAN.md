# System Validation Plan
## BioNexus Platform — Computerized System Validation

---

**Document ID:** BNX-VAL-001
**Version:** 1.0
**Status:** Approved for Release
**Classification:** Quality & Regulatory Affairs — Restricted Distribution
**Date:** 2026-02-28
**Prepared by:** BioNexus Engineering & Regulatory Team
**CSV Specialist:** GMP4U (Johannes Eberhardt)
**Review Cycle:** Annual or upon significant change

---

## Document Control

### Approval Table

| Role | Name | Title | Signature | Date |
|------|------|-------|-----------|------|
| Document Author | BioNexus Regulatory Team | Regulatory Affairs Lead | ____________ | ____________ |
| System Owner | [Customer System Owner] | [Title] | ____________ | ____________ |
| Quality Assurance | [Customer QA Manager] | QA Manager | ____________ | ____________ |
| CSV Specialist | Johannes Eberhardt | GMP4U — CSV Lead | ____________ | ____________ |
| IT Representative | [Customer IT Lead] | IT Systems Administrator | ____________ | ____________ |
| Validation Sponsor | [Sponsor Name] | [Title / VP Quality] | ____________ | ____________ |

### Revision History

| Version | Date | Author | Description of Change | Reviewed By |
|---------|------|--------|----------------------|-------------|
| 0.1 | 2026-01-15 | BioNexus Reg. Team | Initial draft for internal review | Internal |
| 0.2 | 2026-02-01 | BioNexus Reg. Team | Incorporated GMP4U review comments; expanded IQ/OQ test cases | J. Eberhardt / GMP4U |
| 1.0 | 2026-02-28 | BioNexus Reg. Team | Approved final version for customer distribution | GMP4U; QA |

### Related Documents

| Document ID | Title | Version |
|-------------|-------|---------|
| BNX-COMP-001 | GxP Compliance Master Document | 1.0 |
| BNX-HW-001 | BioNexus Box Hardware Architecture | 1.0 |
| BNX-SEC-001 | BioNexus Security Architecture | 1.0 |
| BNX-GCP-001 | GCP Cloud Architecture & Deployment Guide | 1.0 |
| BNX-URS-001 | User Requirements Specification | 1.0 |
| BNX-FS-001 | Functional Specification | 1.0 |
| BNX-DS-001 | Design Specification | 1.0 |
| BNX-RA-001 | Risk Assessment (FMEA) | 1.0 |

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [System Description](#2-system-description)
3. [Regulatory Basis](#3-regulatory-basis)
4. [Validation Strategy](#4-validation-strategy)
5. [Roles and Responsibilities](#5-roles-and-responsibilities)
6. [Validation Lifecycle](#6-validation-lifecycle)
7. [User Requirements Specification (URS)](#7-user-requirements-specification-urs)
8. [Functional Specification (FS)](#8-functional-specification-fs)
9. [Design Specification (DS)](#9-design-specification-ds)
10. [Installation Qualification (IQ)](#10-installation-qualification-iq)
11. [Operational Qualification (OQ)](#11-operational-qualification-oq)
12. [Performance Qualification (PQ)](#12-performance-qualification-pq)
13. [Traceability Matrix](#13-traceability-matrix)
14. [Risk Assessment](#14-risk-assessment)
15. [Deviation and CAPA Handling](#15-deviation-and-capa-handling)
16. [Validation Summary Report Template](#16-validation-summary-report-template)
17. [Periodic Review](#17-periodic-review)
18. [Change Control](#18-change-control)
19. [Appendices](#19-appendices)

---

## 1. Purpose and Scope

### 1.1 Purpose

This System Validation Plan (SVP) defines the strategy, methodology, responsibilities, and protocols for the computerized system validation (CSV) of the BioNexus Platform. The plan establishes a structured, risk-based approach consistent with GAMP5 Second Edition guidelines and applicable regulatory requirements.

This document serves as the master reference for all validation activities and provides the framework GMP4U uses to deliver qualification packages to BioNexus customers operating in GxP-regulated environments (pharmaceutical manufacturing, biotechnology QC, clinical laboratory, and medical device sectors).

### 1.2 Scope

This validation plan covers all components of the BioNexus system that are GxP-critical:

**In Scope:**
- BioNexus SaaS Platform (cloud-hosted Django REST API, PostgreSQL database, GCS object storage)
- BioNexus Box hardware gateway (firmware, embedded software, device provisioning)
- Audit trail subsystem (immutable SHA-256 chained log, certified export)
- Role-Based Access Control (RBAC) and authentication subsystem (JWT, 5-role model)
- Electronic signature and certification subsystem (double-authentication certification)
- ALCOA+ data parsing pipeline (instrument data ingestion, normalization, integrity verification)
- Multi-tenant data isolation infrastructure
- GCP infrastructure components (Cloud Run, Cloud SQL, GCS, Secret Manager) in their configured state

**Out of Scope:**
- Development and test environments (separate qualification not required for non-production systems)
- Laboratory instruments connected to the BioNexus Box (instrument qualification is the customer's responsibility)
- Customer LIMS or ERP systems receiving data from BioNexus API integrations
- Network infrastructure between the BioNexus Box and customer firewall (customer IT responsibility)
- GCP platform services as commercial off-the-shelf infrastructure (covered by supplier qualification per GAMP5)

### 1.3 System Boundaries

```
+----------------------+     RS232/USB      +------------------+     HTTPS/TLS 1.3    +------------------------+
|                      |                    |                  |                      |                        |
|  Lab Instruments     +------------------>+  BioNexus Box    +--------------------->+  BioNexus GCP Platform |
|  (Out of scope)      |                    |  (In scope)      |                      |  (In scope)            |
|                      |                    |                  |                      |                        |
+----------------------+                    +------------------+                      +------------------------+
         ^                                         ^                                           ^
         |                                         |                                           |
  [Instrument Vendor               [BioNexus Box Firmware            [BioNexus SaaS Platform
   Qualification]                   IQ/OQ/PQ covered here]           IQ/OQ/PQ covered here]
```

### 1.4 Validation Objectives

1. Demonstrate that the BioNexus Platform consistently performs its intended GxP-critical functions within specified parameters.
2. Provide documented evidence that the system meets all applicable regulatory requirements (21 CFR Part 11, EU Annex 11, GAMP5).
3. Establish a defensible, auditable qualification package suitable for regulatory inspection.
4. Enable GMP4U to deliver standardized qualification services to BioNexus customer sites.

---

## 2. System Description

### 2.1 BioNexus Platform Overview

BioNexus is a SaaS + hardware platform designed to eliminate manual transcription of laboratory instrument data in GxP-regulated environments. The system captures raw instrument output at the source, creates cryptographically verified immutable records, and provides an audit-ready data trail compliant with 21 CFR Part 11 and EU Annex 11.

**Primary Use Cases:**
- Automated, real-time capture of analytical instrument results (dissolution, HPLC, UV-Vis, pH, balances, KF titrators)
- Immutable, timestamped electronic records with SHA-256 data integrity protection
- Compliant electronic audit trail with mandatory user attribution
- Role-based access control for regulated laboratory environments
- Multi-tenant isolation for laboratory data segregation
- Certified audit export for regulatory submission support

### 2.2 System Components

#### 2.2.1 BioNexus Box (Hardware Gateway)

| Attribute | Specification |
|-----------|---------------|
| Platform | Raspberry Pi CM4 (primary); Advantech ARK-1124H / Moxa UC-8112A (industrial alternative) |
| OS | Debian 12 Linux (64-bit, hardened) |
| Interfaces | RS232 (DB9, 2 native ports), USB-A (CDC-ACM, FTDI, CH340), Ethernet (Gigabit) |
| Software | bionexus-agent (Python 3.12): Collector Service + Uplink Agent |
| Local Storage | SQLite WAL-mode queue (/var/lib/bionexus/queue.db) |
| Security | TLS 1.3 outbound, certificate pinning, device identity certificate (mTLS) |
| Offline Operation | Store-and-forward buffer (configurable retention, default 30 days) |
| Integrity | SHA-256 hash of raw instrument bytes; SHA-256 packet hash before upload |

#### 2.2.2 BioNexus SaaS Platform (Cloud Backend)

| Component | Technology | Purpose |
|-----------|------------|---------|
| API Layer | Django REST Framework (Python 3.12) on GCP Cloud Run | REST API, business logic, validation |
| Database | PostgreSQL 15 on GCP Cloud SQL | Primary data store, audit trail |
| Object Storage | GCP Cloud Storage (GCS) | Raw instrument file archival |
| Secrets Management | GCP Secret Manager | API keys, database credentials |
| Container Registry | GCP Artifact Registry | Docker image management |
| Monitoring | GCP Cloud Monitoring + Cloud Logging | Observability, alerting |
| Authentication | JWT (HS256, 15-min access / 7-day refresh) | User authentication |
| Authorization | RBAC (5 roles: Admin, Principal Investigator, Lab Technician, Auditor, Viewer) | Permission enforcement |

#### 2.2.3 Audit Trail Subsystem

The audit trail is the core GxP-critical function of the platform:

- Every create, update, and delete operation on GxP-relevant data generates an immutable `AuditLog` record
- Each record contains: `entity_type`, `entity_id`, `operation`, `user_id` (mandatory), `user_email` (mandatory), `timestamp`, `changes` (before/after snapshots), `signature` (SHA-256), `previous_signature` (chain link)
- SHA-256 signature chains records together; tampering with any record breaks the chain and is detected on verification
- Certified audit exports include chain verification results and are signed with the platform's master key
- `user_id` and `user_email` are mandatory fields; a `ValueError` is raised if missing (system-level enforcement)

#### 2.2.4 GAMP5 Classification

| Component | GAMP5 Category | Rationale |
|-----------|---------------|-----------|
| BioNexus SaaS Platform | Category 5 (Custom Software) | Custom-developed, no commercial equivalent |
| BioNexus Box Firmware | Category 5 (Custom Software) | Custom embedded software |
| GCP Cloud Run, Cloud SQL, GCS | Category 3 (Non-Configured Products) | Managed infrastructure, configured not customized |
| Raspberry Pi CM4 / OS | Category 3 | Commercial hardware/OS, hardened configuration only |
| PostgreSQL | Category 3 | Open-source DBMS, standard configuration |

---

## 3. Regulatory Basis

### 3.1 Applicable Regulations and Guidelines

| Regulation / Guideline | Applicability | Key Requirements |
|------------------------|---------------|-----------------|
| **21 CFR Part 11** (FDA, USA) | Mandatory for US pharma/biotech customers | Electronic records, electronic signatures, audit trails, system controls |
| **EU GMP Annex 11** (EMA) | Mandatory for EU pharma/biotech customers | Computerized systems, data integrity, change control, periodic review |
| **GAMP5 (2nd Ed., 2022)** | Industry best practice; referenced by FDA and EMA | Risk-based validation, V-Model, supplier qualification, CSV lifecycle |
| **ICH Q9 (R1)** | Quality risk management methodology | FMEA-based risk assessment, risk-based decisions |
| **ICH Q10** | Pharmaceutical Quality System | Change control, CAPA, continual improvement |
| **PIC/S PI 011-3** | GMP guidance for computerized systems | Broadly aligns with EU Annex 11; referenced by non-EU regulators |
| **ALCOA+ Principles** | Data integrity framework (WHO, FDA, EMA guidance) | Attributable, Legible, Contemporaneous, Original, Accurate + Complete, Consistent, Enduring, Available |
| **ISO/IEC 27001** | Information security (referenced) | Data security controls, access management |
| **GDPR / RGPD** | EU data protection | Data minimization, pseudonymization, right to erasure |

### 3.2 21 CFR Part 11 Requirements Mapping Summary

| 21 CFR Part 11 Section | Requirement | BioNexus Implementation |
|------------------------|-------------|-------------------------|
| §11.10(a) | System validation | This document (BNX-VAL-001) |
| §11.10(b) | Accurate and complete copies | Certified audit export (JSON + PDF) |
| §11.10(c) | Record protection | SHA-256 chaining, PostgreSQL on Cloud SQL |
| §11.10(d) | Limiting system access | RBAC (5 roles), JWT authentication |
| §11.10(e) | Audit trails | Immutable AuditLog with mandatory user attribution |
| §11.10(f) | Operational system checks | Input validation, business rule enforcement in API layer |
| §11.10(g) | Authority checks | @permission_required decorator on every GxP endpoint |
| §11.10(h) | Device checks | BioNexus Box device certificates (mTLS) |
| §11.10(i) | Education, training | Customer training program (separate document) |
| §11.10(j) | Account management | Admin role manages user accounts; audit-logged |
| §11.10(k) | Documentation controls | Change control process (Section 18 of this document) |
| §11.50 | Signature manifestations | User ID, timestamp, meaning of signature |
| §11.70 | Signature/record linking | JWT claim links signature to audit record |
| §11.100 | General e-signature requirements | Unique user ID + password + role |
| §11.200 | E-signature components | Username + password (first signing); re-authentication for double-auth certification |

### 3.3 EU Annex 11 Mapping Summary

| Annex 11 Section | Requirement | BioNexus Implementation |
|-----------------|-------------|-------------------------|
| 1 | Risk Management | ICH Q9 FMEA (Section 14 of this document) |
| 4.1–4.8 | Validation | IQ/OQ/PQ protocols (Sections 10–12) |
| 5 | Data | PostgreSQL primary; GCS backup; SHA-256 integrity |
| 7 | Data Storage | Cloud SQL automated backups; point-in-time recovery |
| 8 | Printouts | Certified audit export (human-readable + machine-verifiable) |
| 9 | Audit Trail | Immutable AuditLog; records who, what, when, why |
| 10 | Change and Configuration Management | Change control SOP (Section 18) |
| 11 | Periodic Evaluation | Annual periodic review (Section 17) |
| 12 | Security | JWT + RBAC + HTTPS + GCP IAM |
| 14 | Electronic Signature | Double-authentication certification feature |
| 17 | Archiving | GCS cold storage; 10-year retention policy |

---

## 4. Validation Strategy

### 4.1 V-Model Approach

BioNexus validation follows the GAMP5 V-Model, which maps each specification document to a corresponding qualification activity:

```
Requirements Phase              Test Phase
-------------------             -------------------

User Requirements           ←→  Performance Qualification (PQ)
Specification (URS)             [End-to-end workflows; user acceptance]

Functional Specification    ←→  Operational Qualification (OQ)
(FS)                            [Functional testing of all GxP features]

Design Specification        ←→  Installation Qualification (IQ)
(DS)                            [Infrastructure verification; config checks]

                    BUILD / CODE
                    (Implementation)
```

### 4.2 Risk-Based Validation Extent

Per GAMP5 Second Edition, the extent of validation activities is commensurate with the risk of the function to product quality and patient safety. BioNexus applies the following risk-based framework:

| Risk Level | Definition | Validation Approach |
|------------|------------|---------------------|
| **Critical** | Direct impact on data integrity, audit trail, e-signatures, access control | Full IQ + OQ + PQ; formal test protocols; independent review |
| **Major** | Indirect impact; could affect GxP data if failed | IQ + OQ testing; sampling-based PQ |
| **Minor** | No GxP impact; administrative or cosmetic function | IQ verification only; documented rationale |

**Functions classified as Critical for BioNexus:**
- Audit trail creation and chaining (SHA-256 signature verification)
- RBAC enforcement (unauthorized access prevention)
- Electronic signature / double-authentication certification
- Data integrity verification (SHA-256 hash validation)
- BioNexus Box data capture with hash generation
- Certified audit export with chain verification
- Multi-tenant data isolation

**Functions classified as Major:**
- User account management
- Instrument registration and status monitoring
- Parsing pipeline (ALCOA+ normalization)
- Offline buffer and store-and-forward
- Alert and notification system

**Functions classified as Minor:**
- Dashboard UI display
- Report formatting preferences
- User profile management

### 4.3 Supplier Qualification

GCP infrastructure components (Cloud Run, Cloud SQL, GCS, Secret Manager) are classified as GAMP5 Category 3. Supplier qualification evidence includes:

| Supplier | Product | Evidence Type | Evidence Location |
|----------|---------|---------------|-------------------|
| Google Cloud Platform | Cloud Run, Cloud SQL, GCS | SOC 2 Type II Report; ISO 27001 certificate; FedRAMP authorization | GCP Compliance Center |
| Raspberry Pi Ltd | CM4 hardware | CE/FCC declaration; datasheet | BioNexus supplier file |
| Advantech | ARK-1124H | CE/FCC declaration; IEC 60068 test reports | BioNexus supplier file |

Supplier qualification documentation is maintained in the BioNexus Supplier Qualification File (BNX-SQ-001) and is reviewed annually or upon significant supplier change.

### 4.4 Configuration Management and Baseline

Prior to IQ execution, a validated baseline must be established and documented:

- Software version: documented in BNX-DS-001
- Database schema version: captured via Django migration state
- BioNexus Box firmware version: captured from device registry
- GCP infrastructure configuration: captured via Terraform state file and Infrastructure-as-Code repository
- Test environment confirmation: confirmation that qualification is performed on the production system or on a production-equivalent validated environment

---

## 5. Roles and Responsibilities

### 5.1 Validation Team

| Role | Responsible Party | Responsibilities |
|------|-------------------|-----------------|
| **Validation Sponsor** | Customer VP Quality / Site Head | Authorizes validation activities; provides resources; final approval authority |
| **System Owner** | Customer QC Laboratory Manager | Defines user requirements; accepts system; owns periodic review; approves change control |
| **Quality Assurance (QA)** | Customer QA Manager | Reviews and approves all validation documents; verifies compliance; witnesses critical tests; manages deviations and CAPAs |
| **CSV Specialist** | GMP4U (Johannes Eberhardt) | Authors and executes IQ/OQ/PQ protocols; provides regulatory expertise; manages traceability matrix; final validation summary report |
| **IT Representative** | Customer IT Systems Admin | Executes IQ infrastructure tests; manages network configuration; documents IT controls |
| **BioNexus Technical Lead** | BioNexus Engineering | Provides design documentation (DS, FS); supports IQ/OQ/PQ execution; resolves technical deviations; provides system access |
| **End Users (Testers)** | Lab Technicians, PI, Auditors | Execute PQ test cases in real operational scenarios; provide user acceptance sign-off |
| **Instrument Specialist** | Customer or BioNexus | Supports BioNexus Box IQ; verifies instrument connectivity during OQ/PQ |

### 5.2 Signature Requirements

All qualification documents requiring signature must be signed by:
- Tester: person who executed the test case
- Reviewer: QA representative or CSV Specialist
- Approver: System Owner or Validation Sponsor (for summary documents)

Electronic or wet-ink signatures are acceptable; if electronic signatures are used for validation documents, they must comply with 21 CFR Part 11 §11.50.

---

## 6. Validation Lifecycle

### 6.1 Lifecycle Phases

```
Phase 1: Planning
├── Issue this Validation Plan (BNX-VAL-001)
├── Define validation scope and risk assessment
├── Assemble validation team
├── Establish test environment
└── Schedule validation activities

Phase 2: Specification
├── User Requirements Specification (URS) — BNX-URS-001
├── Functional Specification (FS) — BNX-FS-001
└── Design Specification (DS) — BNX-DS-001

Phase 3: Installation Qualification (IQ)
├── Infrastructure verification
├── Software installation verification
├── Configuration verification
└── Document verification

Phase 4: Operational Qualification (OQ)
├── Functional testing (all GxP-critical features)
├── Negative/boundary testing
├── Security testing
└── Integration testing

Phase 5: Performance Qualification (PQ)
├── End-to-end workflow testing
├── Concurrent user testing
├── Stress and load testing
└── User Acceptance Testing (UAT)

Phase 6: Validation Summary Report
├── Compile all qualification results
├── Document and resolve all deviations
├── QA review and approval
└── System Owner acceptance

Phase 7: System Release
└── System approved for GxP use

Phase 8: Post-Validation
├── Change control (Section 18)
├── Annual periodic review (Section 17)
└── Requalification as required
```

### 6.2 Entry and Exit Criteria

| Phase | Entry Criteria | Exit Criteria |
|-------|---------------|---------------|
| IQ | Signed Validation Plan; DS approved; system deployed to production environment | All IQ test cases executed; all deviations documented; IQ sign-off obtained |
| OQ | IQ complete and signed; all IQ deviations resolved or risk-accepted | All OQ test cases executed; pass rate meets acceptance threshold; all critical deviations resolved |
| PQ | OQ complete and signed; end users available; production data available | All PQ test cases executed; user acceptance sign-off obtained; all deviations resolved |
| Summary Report | All IQ/OQ/PQ complete; all deviations closed or risk-accepted with QA approval | Validation Summary Report signed by QA, System Owner, and Validation Sponsor |

### 6.3 Acceptance Threshold

- **Critical test cases:** 100% pass rate required. Any failure is a Critical Deviation requiring resolution and retest before proceeding.
- **Major test cases:** 100% pass rate required. Failures are Major Deviations; resolution may allow conditional progression with QA approval.
- **Minor test cases:** 95% pass rate acceptable. Failures documented as Minor Deviations; may be accepted with documented rationale.

---

## 7. User Requirements Specification (URS)

*Note: The full URS is maintained in BNX-URS-001. This section provides a structured summary of key URS items used for traceability purposes.*

### 7.1 Functional Requirements

| URS ID | Category | Requirement | Priority |
|--------|----------|-------------|----------|
| URS-F-001 | Data Capture | The system shall capture raw instrument data from RS232 and USB-serial interfaces without manual transcription | Critical |
| URS-F-002 | Data Capture | The system shall support a minimum of 6 instrument categories: dissolution, HPLC, UV-Vis, pH/conductivity, balance, KF titrator | Critical |
| URS-F-003 | Data Integrity | The system shall generate a SHA-256 hash of all captured raw instrument bytes at the point of capture | Critical |
| URS-F-004 | Data Integrity | The system shall maintain an immutable audit trail; no record shall be modifiable or deletable after creation | Critical |
| URS-F-005 | Audit Trail | The system shall record all create, update, and delete operations on GxP-relevant data with user attribution, timestamp, and before/after data snapshots | Critical |
| URS-F-006 | Audit Trail | The system shall chain audit records using SHA-256 signatures such that tampering with any record is detectable | Critical |
| URS-F-007 | Audit Trail | The system shall provide certified audit exports that include chain integrity verification results | Critical |
| URS-F-008 | Access Control | The system shall enforce Role-Based Access Control with a minimum of 5 roles: Admin, Principal Investigator, Lab Technician, Auditor, Viewer | Critical |
| URS-F-009 | Access Control | The system shall enforce unique user identification; shared accounts are not permitted | Critical |
| URS-F-010 | Authentication | The system shall authenticate users via username and password; accounts shall be locked after configurable failed attempts | Critical |
| URS-F-011 | E-Signatures | The system shall support electronic certification (double-authentication) of GxP records by authorized users | Critical |
| URS-F-012 | Multi-Tenancy | The system shall provide complete data isolation between tenant (laboratory) accounts | Critical |
| URS-F-013 | Offline Operation | The BioNexus Box shall buffer instrument data locally during network outages and synchronize upon reconnection without data loss | Major |
| URS-F-014 | Parsing | The system shall parse raw instrument output and normalize it to a structured format per ALCOA+ principles | Major |
| URS-F-015 | Instrument Management | The system shall support registration and status monitoring of connected instruments | Major |
| URS-F-016 | Reporting | The system shall provide paginated, filterable access to all audit trail records | Major |
| URS-F-017 | User Management | The Admin role shall be able to create, modify, disable, and audit user accounts | Major |

### 7.2 Compliance Requirements

| URS ID | Regulation | Requirement | Priority |
|--------|------------|-------------|----------|
| URS-C-001 | 21 CFR Part 11 §11.10(e) | Audit trail must capture who (user ID + email), what (operation + data), and when (timestamp) | Critical |
| URS-C-002 | 21 CFR Part 11 §11.10(d) | System access must be limited to authorized individuals | Critical |
| URS-C-003 | 21 CFR Part 11 §11.200 | Electronic signatures must be unique to one individual and not reusable by another | Critical |
| URS-C-004 | EU Annex 11 §9 | Audit trail must be available for the lifetime of the records and be readable throughout that period | Critical |
| URS-C-005 | EU Annex 11 §12 | System must prevent unauthorized access using physical and logical controls | Critical |
| URS-C-006 | ALCOA+ | All captured data must be Attributable, Legible, Contemporaneous, Original, and Accurate | Critical |
| URS-C-007 | EU Annex 11 §7 | Data must be backed up regularly; backup integrity must be verified | Critical |
| URS-C-008 | 21 CFR Part 11 §11.10(c) | System must protect records to enable their accurate and ready retrieval throughout the records retention period | Critical |

### 7.3 Performance Requirements

| URS ID | Requirement | Acceptance Criterion |
|--------|-------------|---------------------|
| URS-P-001 | API response time for read operations | 95th percentile response time < 2 seconds under normal load |
| URS-P-002 | API response time for write operations | 95th percentile response time < 3 seconds under normal load |
| URS-P-003 | BioNexus Box data upload latency | Captured readings uploaded within 30 seconds of capture under connected conditions |
| URS-P-004 | Concurrent users | System must support a minimum of 20 concurrent authenticated users per tenant without degradation |
| URS-P-005 | Audit trail query performance | Audit trail queries for up to 10,000 records must return within 5 seconds |
| URS-P-006 | System availability | Platform uptime of >= 99.5% measured monthly (excluding planned maintenance) |
| URS-P-007 | Data retention | Audit trail records retained for a minimum of 10 years |

### 7.4 Security Requirements

| URS ID | Requirement | Acceptance Criterion |
|--------|-------------|---------------------|
| URS-S-001 | All API communications must be encrypted | TLS 1.2 minimum; TLS 1.3 preferred; no unencrypted HTTP accepted |
| URS-S-002 | Passwords must be stored using industry-standard hashing | Django's PBKDF2 hasher; no plain-text storage verifiable |
| URS-S-003 | Session tokens must expire automatically | Access tokens expire in 15 minutes; refresh tokens in 7 days |
| URS-S-004 | Cross-tenant data access must be prevented at all layers | HTTP, service, and database layers each enforce tenant_id filtering |
| URS-S-005 | BioNexus Box must authenticate to the cloud platform via device certificate | mTLS with unique device certificate per Box unit |

---

## 8. Functional Specification (FS)

*Note: The full FS is maintained in BNX-FS-001. This section provides a URS-mapped summary of key functional behaviors.*

### 8.1 FS Summary — URS Mapping

| FS ID | URS Ref | System Function | Description |
|-------|---------|-----------------|-------------|
| FS-001 | URS-F-001, URS-F-003 | Instrument Data Capture | bionexus-collector daemon reads RS232/USB ports, applies parser, computes SHA-256(raw_bytes), writes to local queue |
| FS-002 | URS-F-003, URS-F-006 | Data Integrity — Hash Chaining | Each AuditLog record contains `signature = SHA256(entity_type + entity_id + operation + timestamp + changes + previous_signature)` |
| FS-003 | URS-F-004, URS-C-001 | Immutable Audit Trail | AuditLog.save() raises ValidationError if any existing record's signature does not match; delete operations are prohibited at the database and API level |
| FS-004 | URS-F-005, URS-C-001 | Mandatory User Attribution | AuditTrail.record() raises ValueError if user_id or user_email is not provided; enforced at the service layer |
| FS-005 | URS-F-007 | Certified Audit Export | GET /api/v1/audit/export/ triggers chain verification, generates JSON export with chain_verification block, signs export with HMAC-SHA256 |
| FS-006 | URS-F-008, URS-C-002 | RBAC Enforcement | @permission_required decorator enforces permission at every endpoint; 403 returned for unauthorized access |
| FS-007 | URS-F-009, URS-F-010 | Authentication | POST /api/auth/login returns JWT access (15 min) + refresh (7 days); incorrect credentials return 401; account lockout after N failures |
| FS-008 | URS-F-011 | Electronic Certification | Certification endpoint requires re-authentication (password confirmation) before writing certification record to audit trail |
| FS-009 | URS-F-012, URS-S-004 | Multi-Tenant Isolation | @tenant_context decorator injects tenant_id from JWT; all repository queries filter by tenant_id; cross-tenant access returns 404 |
| FS-010 | URS-F-013 | Offline Store-and-Forward | Uplink Agent polls SQLite queue; on network failure, increments retry_count with exponential backoff; no data loss on power cycle (WAL + synchronous=FULL) |
| FS-011 | URS-F-014 | ALCOA+ Parsing Pipeline | Parser base class defines contract; per-instrument parser modules normalize raw bytes to ParsedReading JSON schema; parsing errors logged without data loss |
| FS-012 | URS-F-015 | Instrument Management | Instrument registration API stores device metadata, parser assignment, and last-heartbeat timestamp; status (ONLINE/OFFLINE/ERROR) derived from heartbeat age |
| FS-013 | URS-F-017 | User Management | Admin-only endpoints: POST/PATCH/DELETE /api/v1/users/; all user management operations written to audit trail |

---

## 9. Design Specification (DS)

*Note: The full DS is maintained in BNX-DS-001. This section provides a FS-mapped summary of key design decisions.*

### 9.1 DS Summary — FS Mapping

| DS ID | FS Ref | Design Decision | Implementation Detail |
|-------|--------|-----------------|-----------------------|
| DS-001 | FS-001 | Serial Port Collection | pyserial library; per-instrument threads; InstrumentCollector class with exponential-backoff reconnect |
| DS-002 | FS-002 | SHA-256 Chaining Algorithm | `hashlib.sha256()` applied to concatenated string of audit fields + previous_signature; genesis record uses '0' * 64 as previous_signature |
| DS-003 | FS-003 | Immutability Enforcement | Django AuditLog model overrides save() with signature validation; database-level: no DELETE permission granted to application DB user; UPDATE restricted to status fields only |
| DS-004 | FS-004 | User Attribution Enforcement | Service-layer AuditTrail.record() method signature: user_id: int, user_email: str (no defaults); raise ValueError if falsy |
| DS-005 | FS-005 | Certified Export Implementation | AuditExportService recalculates all signatures in memory; exports JSON including chain_verification dict; signs with HMAC-SHA256 keyed to Django SECRET_KEY |
| DS-006 | FS-006 | RBAC Implementation | Role, Permission, RolePermission models; @permission_required(Permission.X) decorator on every view function; permission cache per request |
| DS-007 | FS-007 | JWT Authentication | JWTService.generate_tokens(user) returns {access, refresh, user_id, tenant_id}; HS256 algorithm; access token 15 min; refresh token 7 days; refresh tokens stored hashed in DB |
| DS-008 | FS-008 | Double-Authentication Certification | Certification endpoint validates password via authenticate(username, password); on success, writes CertificationEvent to AuditLog with operation='CERTIFY' |
| DS-009 | FS-009 | Multi-Tenant Architecture | User.tenant_id FK (mandatory); all data models carry tenant_id FK; BaseRepository.get_queryset() always applies filter(tenant_id=tenant_id) |
| DS-010 | FS-010 | SQLite WAL Queue | schema: reading_queue table; PRAGMA synchronous=FULL; PRAGMA journal_mode=WAL; status state machine: PENDING → UPLOADING → UPLOADED / FAILED |
| DS-011 | FS-011 | Parser Architecture | /opt/bionexus/parsers/ directory; BaseParser abstract class with parse(raw_bytes) → ParsedReading | None; instrument assignment in /etc/bionexus/instruments.yaml |
| DS-012 | FS-012 | Instrument Registry | Instrument model: device_id, serial_number, parser_module, tenant_id, last_heartbeat_at, status; heartbeat endpoint POST /api/v1/devices/{id}/heartbeat/ |
| DS-013 | FS-013 | User Management API | /api/v1/users/ CRUD; Admin role only via @permission_required(Permission.USER_MANAGE); all operations audit-logged |

### 9.2 Infrastructure Design

| DS ID | Component | Design | GxP Relevance |
|-------|-----------|--------|--------------|
| DS-I-001 | Database | Cloud SQL PostgreSQL 15; private IP; automated backups (daily, 7-day retention); point-in-time recovery enabled | Data persistence; recovery from corruption |
| DS-I-002 | API Hosting | Cloud Run (serverless containers); minimum 1 instance always warm; autoscaling 1–10 instances | Availability; scalability |
| DS-I-003 | Secrets | GCP Secret Manager; all credentials injected as environment variables at runtime; no secrets in source code or images | Security; auditability |
| DS-I-004 | Logging | GCP Cloud Logging; structured JSON logs; 365-day retention minimum; export to GCS for long-term archival | Audit; troubleshooting |
| DS-I-005 | Networking | VPC with private subnets; Cloud SQL on private IP; Cloud Run in VPC connector; no direct internet → DB path | Data isolation |
| DS-I-006 | TLS | All public endpoints enforce HTTPS; TLS 1.2 minimum, TLS 1.3 preferred; HSTS headers | Encryption in transit |

---

## 10. Installation Qualification (IQ)

### 10.1 IQ Purpose

The Installation Qualification provides documented evidence that the BioNexus system components have been correctly installed and configured in the production environment according to approved specifications.

### 10.2 IQ Prerequisites

Before executing IQ:
- [ ] Production environment deployed and accessible
- [ ] DS (BNX-DS-001) approved and available
- [ ] GCP project provisioned; Terraform state applied
- [ ] BioNexus Box units provisioned with assigned device certificates
- [ ] Test user accounts created (one per role)
- [ ] QA representative and CSV Specialist available to witness critical tests

### 10.3 IQ Test Cases — Infrastructure

---

**IQ-001: GCP Cloud Run Service Verification**

| Field | Value |
|-------|-------|
| Test ID | IQ-001 |
| Test Name | Cloud Run Service Verification |
| Category | Infrastructure |
| Risk Level | Major |
| DS Reference | DS-I-002 |
| Tester | IT Representative / BioNexus Technical Lead |
| Reviewer | CSV Specialist |

**Objective:** Verify that the BioNexus API service is deployed to GCP Cloud Run with the correct container image version and configuration.

**Test Steps:**
1. Access GCP Console → Cloud Run → bionexus-api service
2. Record the deployed container image tag (must match BNX-DS-001 baseline version)
3. Record minimum instance count (must be >= 1)
4. Record maximum instance count (must be 1–10 per specification)
5. Confirm service URL uses HTTPS only (no HTTP listener enabled)
6. Execute: `curl -I https://api.bionexus.io/api/v1/health/` and record HTTP response code and server headers

**Acceptance Criteria:**
- Container image tag matches approved version in DS
- Minimum instances >= 1
- Maximum instances <= 10
- Health endpoint returns HTTP 200
- Response is served over HTTPS (TLS); no HTTP redirect accepted as pass

**Results:** Pass [ ] / Fail [ ] / N/A [ ]
**Actual Result:** ____________________________________________
**Tester Signature:** _________________________ Date: ___________
**Reviewer Signature:** ______________________ Date: ___________

---

**IQ-002: Cloud SQL Database Verification**

| Field | Value |
|-------|-------|
| Test ID | IQ-002 |
| Test Name | Cloud SQL PostgreSQL Instance Verification |
| Category | Infrastructure |
| Risk Level | Critical |
| DS Reference | DS-I-001 |

**Objective:** Verify that the PostgreSQL database instance is correctly configured with appropriate backup and recovery settings.

**Test Steps:**
1. Access GCP Console → Cloud SQL → bionexus-db instance
2. Record PostgreSQL version (must be 15.x)
3. Confirm instance is on a private IP (no public IP exposed)
4. Verify automated backups are enabled
5. Record backup retention period (must be >= 7 days)
6. Confirm point-in-time recovery (PITR) is enabled
7. Record database flags: `log_connections = on`, `log_disconnections = on`
8. Verify application database user has no DROP or DELETE TABLE privileges (execute `\dp` in psql and record result)

**Acceptance Criteria:**
- PostgreSQL version is 15.x
- No public IP assigned to instance
- Automated backups enabled with retention >= 7 days
- PITR enabled
- Required logging flags set
- Application user has no DDL privileges

**Results:** Pass [ ] / Fail [ ] / N/A [ ]
**Actual Result:** ____________________________________________
**Tester Signature:** _________________________ Date: ___________
**Reviewer Signature:** ______________________ Date: ___________

---

**IQ-003: GCS Backup and Archival Bucket Verification**

| Field | Value |
|-------|-------|
| Test ID | IQ-003 |
| Test Name | Cloud Storage Bucket Configuration |
| Category | Infrastructure |
| Risk Level | Major |
| DS Reference | DS-I-001 |

**Objective:** Verify GCS buckets for audit export archival are configured with correct retention and access controls.

**Test Steps:**
1. Access GCP Console → Cloud Storage → bionexus-audit-archive bucket
2. Confirm bucket is NOT publicly accessible (Uniform access control; no allUsers ACL)
3. Record Object Versioning status (must be Enabled)
4. Record Retention Policy (must be >= 10 years / 3650 days)
5. Confirm bucket is in an approved GCP region (record region)
6. Verify CMEK (customer-managed encryption key) or Google-managed encryption is documented

**Acceptance Criteria:**
- Bucket is private (no public access)
- Object versioning enabled
- Retention policy >= 10 years
- Encryption method documented

**Results:** Pass [ ] / Fail [ ] / N/A [ ]
**Tester Signature:** _________________________ Date: ___________
**Reviewer Signature:** ______________________ Date: ___________

---

**IQ-004: Secret Manager Verification**

| Field | Value |
|-------|-------|
| Test ID | IQ-004 |
| Test Name | GCP Secret Manager Configuration |
| Category | Security |
| Risk Level | Critical |
| DS Reference | DS-I-003 |

**Objective:** Verify that all application secrets are stored in GCP Secret Manager and are not hardcoded in application configuration or source code.

**Test Steps:**
1. Access GCP Console → Secret Manager; list all secrets
2. Confirm the following secrets exist: `django-secret-key`, `db-password`, `jwt-secret-key`, `box-device-ca-cert`
3. Confirm no secret values are present in Cloud Run environment variable definitions in plain text (check Cloud Run revision configuration)
4. Confirm Cloud Run service account has secretmanager.versions.access permission for required secrets only
5. Verify source code repository: execute `grep -r "SECRET_KEY\|DB_PASSWORD" /opt/bionexus/` on a running container instance and confirm only environment variable references are present (no hardcoded values)

**Acceptance Criteria:**
- All required secrets present in Secret Manager
- No plaintext secrets in Cloud Run environment variable definitions
- Least-privilege IAM for secret access
- No hardcoded secrets in application code

**Results:** Pass [ ] / Fail [ ] / N/A [ ]
**Tester Signature:** _________________________ Date: ___________
**Reviewer Signature:** ______________________ Date: ___________

---

**IQ-005: TLS / HTTPS Configuration Verification**

| Field | Value |
|-------|-------|
| Test ID | IQ-005 |
| Test Name | TLS Encryption Configuration |
| Category | Security |
| Risk Level | Critical |
| DS Reference | DS-I-006 |

**Objective:** Verify that all API communications are encrypted using TLS 1.2 or higher.

**Test Steps:**
1. Execute `testssl.sh https://api.bionexus.io` or equivalent and record supported TLS versions
2. Confirm TLS 1.0 and TLS 1.1 are NOT supported (must return connection refused or handshake failure)
3. Confirm TLS 1.2 is supported
4. Confirm TLS 1.3 is supported
5. Record cipher suites in use; confirm no weak ciphers (RC4, 3DES, NULL) are offered
6. Verify HSTS header is present in API response: `Strict-Transport-Security: max-age=31536000`
7. Confirm HTTP to HTTPS redirect is active (port 80 redirects to 443)

**Acceptance Criteria:**
- TLS 1.0 and 1.1 disabled
- TLS 1.2 and 1.3 enabled
- No weak cipher suites
- HSTS header present
- HTTP → HTTPS redirect enforced

**Results:** Pass [ ] / Fail [ ] / N/A [ ]
**Tester Signature:** _________________________ Date: ___________
**Reviewer Signature:** ______________________ Date: ___________

---

**IQ-006: Database Schema Verification**

| Field | Value |
|-------|-------|
| Test ID | IQ-006 |
| Test Name | Django Migration State Verification |
| Category | Software Installation |
| Risk Level | Critical |
| DS Reference | DS-003, DS-009 |

**Objective:** Verify that the production database schema matches the approved DS baseline.

**Test Steps:**
1. Connect to production Django application shell
2. Execute `python manage.py showmigrations` and capture full output
3. Compare output against the approved migration baseline in BNX-DS-001
4. Execute `python manage.py migrate --check` and confirm exit code is 0 (no unapplied migrations)
5. Verify AuditLog table structure: confirm presence of columns `entity_type`, `entity_id`, `operation`, `user_id`, `user_email`, `timestamp`, `changes`, `signature`, `previous_signature`
6. Verify `user_id` column is NOT NULL constrained at the database level

**Acceptance Criteria:**
- All migrations applied (showmigrations shows [X] for all)
- `--check` exits with code 0
- AuditLog table contains all required columns
- `user_id` is NOT NULL at database level

**Results:** Pass [ ] / Fail [ ] / N/A [ ]
**Tester Signature:** _________________________ Date: ___________
**Reviewer Signature:** ______________________ Date: ___________

---

**IQ-007: BioNexus Box Hardware Verification**

| Field | Value |
|-------|-------|
| Test ID | IQ-007 |
| Test Name | BioNexus Box Physical and Firmware Verification |
| Category | Hardware Installation |
| Risk Level | Critical |
| DS Reference | DS-011, BNX-HW-001 |

**Objective:** Verify that BioNexus Box unit is correctly installed, powered, and running the approved firmware version.

**Test Steps (per Box unit — repeat for each installed unit):**
1. Record BioNexus Box serial number and device ID from the label affixed to the enclosure
2. Confirm device is powered (Power LED is solid green)
3. Confirm device is network connected (Network LED is solid blue)
4. SSH to device (or via BioNexus management console): execute `cat /etc/bionexus/device_id` and record output
5. Execute `bionexus-agent --version` and record firmware version (must match DS baseline)
6. Execute `systemctl status bionexus-agent` and confirm service is active (running)
7. Execute `systemctl status bionexus-watchdog` and confirm service is active (running)
8. Verify device certificate is present: `ls -la /etc/bionexus/certs/device.crt` (must exist and be non-zero)
9. Execute `openssl x509 -in /etc/bionexus/certs/device.crt -noout -subject` and record device CN (must match device ID)
10. Confirm RS232 or USB port cable connection to instrument is physically secure

**Acceptance Criteria:**
- Device serial number matches customer asset register
- Power and Network LEDs indicate normal operation
- Device ID matches cloud registration record
- Firmware version matches DS baseline
- bionexus-agent and bionexus-watchdog services active
- Device certificate present with correct CN
- Physical cable connections secure

**Results:** Pass [ ] / Fail [ ] / N/A [ ]
**Device Serial Number:** ________________________
**Device ID:** ________________________
**Firmware Version:** ________________________
**Tester Signature:** _________________________ Date: ___________
**Reviewer Signature:** ______________________ Date: ___________

---

**IQ-008: RBAC Configuration Verification**

| Field | Value |
|-------|-------|
| Test ID | IQ-008 |
| Test Name | Role and Permission Configuration |
| Category | Software Configuration |
| Risk Level | Critical |
| DS Reference | DS-006 |

**Objective:** Verify that the 5 RBAC roles are correctly configured in the production system with the defined permission sets.

**Test Steps:**
1. Access Django admin or execute database query: `SELECT role, name FROM core_role ORDER BY name;` — record all roles
2. For each role, query assigned permissions: confirm the following assignments:
   - **ADMIN**: all 12 permissions
   - **PRINCIPAL_INVESTIGATOR**: sample:view, sample:create, protocol:view, protocol:create, audit:view
   - **LAB_TECHNICIAN**: sample:view, sample:create, sample:update, protocol:view, audit:view
   - **AUDITOR**: sample:view, protocol:view, audit:view, audit:export
   - **VIEWER**: sample:view, protocol:view
3. Confirm no additional roles exist beyond the 5 defined roles
4. Record permission assignments against DS specification

**Acceptance Criteria:**
- Exactly 5 roles configured
- Each role has exactly the defined permissions per DS
- No undocumented roles or permissions present

**Results:** Pass [ ] / Fail [ ] / N/A [ ]
**Tester Signature:** _________________________ Date: ___________
**Reviewer Signature:** ______________________ Date: ___________

---

**IQ-009: Document Verification**

| Field | Value |
|-------|-------|
| Test ID | IQ-009 |
| Test Name | Validation Documentation Completeness Check |
| Category | Documentation |
| Risk Level | Major |

**Objective:** Verify that all required validation documentation is present, approved, and controlled.

**Test Steps:**
1. Verify BNX-VAL-001 (this document) is signed and version-controlled
2. Verify BNX-COMP-001 (GxP Compliance Master) is available and approved
3. Verify BNX-HW-001 (Hardware Architecture) is available and approved
4. Verify BNX-SEC-001 (Security Architecture) is available and approved
5. Confirm all documents have document IDs, version numbers, and approval signatures
6. Confirm training records for all validation team members are available

**Acceptance Criteria:**
- All 6 listed documents present with approval signatures
- Training records available for all testers

**Results:** Pass [ ] / Fail [ ] / N/A [ ]
**Tester Signature:** _________________________ Date: ___________
**Reviewer Signature:** ______________________ Date: ___________

---

**IQ-010: GCP Logging and Monitoring Verification**

| Field | Value |
|-------|-------|
| Test ID | IQ-010 |
| Test Name | Logging and Monitoring Configuration |
| Category | Infrastructure |
| Risk Level | Major |
| DS Reference | DS-I-004 |

**Objective:** Verify that application logging, audit logging, and alerting are correctly configured.

**Test Steps:**
1. Access GCP Console → Cloud Logging → Log Explorer
2. Execute a test API call and confirm structured log entry appears in Cloud Logging within 60 seconds
3. Verify log entries contain: timestamp, service, request_id, user_id (where applicable), status_code
4. Confirm log retention is set to >= 365 days
5. Access GCP Console → Cloud Monitoring → Alert Policies; confirm alerts exist for: API error rate > 5%, Cloud Run CPU > 80%, Cloud SQL storage > 80%
6. Confirm alert notifications are configured to reach operations team

**Acceptance Criteria:**
- API calls produce structured log entries
- Log entries contain required fields
- Log retention >= 365 days
- Minimum 3 alert policies configured
- Alert notifications are routed correctly

**Results:** Pass [ ] / Fail [ ] / N/A [ ]
**Tester Signature:** _________________________ Date: ___________
**Reviewer Signature:** ______________________ Date: ___________

---

### 10.4 IQ Summary

| Test ID | Test Name | Result | Deviation Ref |
|---------|-----------|--------|--------------|
| IQ-001 | Cloud Run Service Verification | | |
| IQ-002 | Cloud SQL Database Verification | | |
| IQ-003 | GCS Bucket Configuration | | |
| IQ-004 | Secret Manager Configuration | | |
| IQ-005 | TLS Configuration | | |
| IQ-006 | Database Schema Verification | | |
| IQ-007 | BioNexus Box Verification | | |
| IQ-008 | RBAC Configuration | | |
| IQ-009 | Document Verification | | |
| IQ-010 | Logging and Monitoring | | |

**IQ Overall Result:** Pass [ ] / Fail [ ] / Conditional Pass [ ]
**IQ Sign-Off:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| CSV Specialist | | | |
| QA Representative | | | |
| System Owner | | | |

---

## 11. Operational Qualification (OQ)

### 11.1 OQ Purpose

The Operational Qualification provides documented evidence that the BioNexus system operates correctly within the defined functional parameters. OQ focuses on testing all GxP-critical features, including boundary conditions and negative test cases, to demonstrate that the system performs as specified in the Functional Specification.

### 11.2 OQ Prerequisites

- IQ completed and signed with all critical deviations resolved
- Test user accounts available for each of the 5 RBAC roles
- Test instrument (or simulator) connected to BioNexus Box
- Test data sets prepared (valid and invalid instrument outputs)
- Test environment is production or validated production equivalent

---

**OQ-001: User Authentication — Successful Login**

| Field | Value |
|-------|-------|
| Test ID | OQ-001 |
| Test Name | Successful User Authentication |
| Category | Authentication |
| Risk Level | Critical |
| FS Reference | FS-007 |
| URS Reference | URS-F-010, URS-C-002 |

**Objective:** Verify that a valid user can authenticate and receive JWT tokens.

**Test Steps:**
1. POST to `/api/auth/login/` with valid credentials: `{"username": "test.technician", "password": "ValidPass123!"}`
2. Record HTTP response code
3. Record response body fields: `access`, `refresh`, `user_id`, `tenant_id`, `role`
4. Verify access token expiry is 15 minutes from issuance (decode JWT and inspect `exp` claim)
5. Verify refresh token expiry is 7 days from issuance

**Expected Result:** HTTP 200; response contains `access` and `refresh` tokens; `exp` claims match specification

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-002: User Authentication — Invalid Credentials**

| Field | Value |
|-------|-------|
| Test ID | OQ-002 |
| Test Name | Authentication Rejection — Invalid Password |
| Category | Authentication — Negative |
| Risk Level | Critical |
| FS Reference | FS-007 |

**Objective:** Verify that invalid credentials are rejected and do not produce tokens.

**Test Steps:**
1. POST to `/api/auth/login/` with invalid password: `{"username": "test.technician", "password": "WrongPass"}`
2. Record HTTP response code
3. Confirm response body does NOT contain `access` or `refresh` fields
4. Confirm response body contains an error message

**Expected Result:** HTTP 401; no tokens returned; error message present

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-003: Authentication — Expired Token Rejection**

| Field | Value |
|-------|-------|
| Test ID | OQ-003 |
| Test Name | Expired Access Token Rejection |
| Category | Authentication — Negative |
| Risk Level | Critical |
| FS Reference | FS-007 |

**Objective:** Verify that expired JWT access tokens are rejected.

**Test Steps:**
1. Obtain a valid access token via successful login (OQ-001)
2. Wait for access token to expire (15 minutes) OR use a known-expired test token with past `exp` claim
3. Make an authenticated API call using the expired token in the Authorization header
4. Record HTTP response code and response body

**Expected Result:** HTTP 401; response indicates token expired; no data returned

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-004: RBAC — Permission Enforcement (Lab Technician cannot delete)**

| Field | Value |
|-------|-------|
| Test ID | OQ-004 |
| Test Name | RBAC Permission Enforcement — Unauthorized Operation |
| Category | Access Control |
| Risk Level | Critical |
| FS Reference | FS-006 |
| URS Reference | URS-F-008, URS-C-002 |

**Objective:** Verify that a user with Lab Technician role cannot perform delete operations.

**Test Steps:**
1. Authenticate as test user with LAB_TECHNICIAN role
2. Create a test sample: POST `/api/v1/samples/` — record sample ID
3. Attempt to delete the sample: DELETE `/api/v1/samples/{id}/` using Lab Technician token
4. Record HTTP response code
5. Verify sample still exists: GET `/api/v1/samples/{id}/` — record response

**Expected Result:** DELETE returns HTTP 403; sample remains accessible via GET

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-005: RBAC — Auditor Cannot Write**

| Field | Value |
|-------|-------|
| Test ID | OQ-005 |
| Test Name | RBAC Permission Enforcement — Auditor Read-Only |
| Category | Access Control |
| Risk Level | Critical |
| FS Reference | FS-006 |

**Objective:** Verify that an Auditor role user cannot create or modify data.

**Test Steps:**
1. Authenticate as test user with AUDITOR role
2. Attempt to create a sample: POST `/api/v1/samples/` with valid payload
3. Record HTTP response code
4. Attempt to update a protocol: PATCH `/api/v1/protocols/{id}/` with valid payload
5. Record HTTP response code

**Expected Result:** Both attempts return HTTP 403; no data created or modified

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-006: RBAC — Cross-Tenant Data Access Prevention**

| Field | Value |
|-------|-------|
| Test ID | OQ-006 |
| Test Name | Multi-Tenant Isolation — Cross-Tenant Access Prevention |
| Category | Access Control / Data Isolation |
| Risk Level | Critical |
| FS Reference | FS-009 |
| URS Reference | URS-F-012, URS-S-004 |

**Objective:** Verify that an authenticated user cannot access data belonging to a different tenant.

**Test Steps:**
1. Authenticate as user from Tenant A (test.admin.a@testa.com); create a sample — record sample ID
2. Authenticate as user from Tenant B (test.admin.b@testb.com)
3. Attempt to access Tenant A's sample: GET `/api/v1/samples/{tenant_a_sample_id}/` using Tenant B's token
4. Record HTTP response code
5. List all samples for Tenant B: GET `/api/v1/samples/` — confirm Tenant A's sample ID does not appear in results

**Expected Result:** Step 3 returns HTTP 404; Tenant A sample does not appear in Tenant B's sample list

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-007: Audit Trail — Record Creation on Sample Create**

| Field | Value |
|-------|-------|
| Test ID | OQ-007 |
| Test Name | Audit Trail Creation — Sample Create Operation |
| Category | Audit Trail |
| Risk Level | Critical |
| FS Reference | FS-003, FS-004 |
| URS Reference | URS-F-005, URS-C-001 |

**Objective:** Verify that creating a sample generates an audit trail record with all required fields.

**Test Steps:**
1. Authenticate as test Lab Technician; record user_id
2. Create a sample: POST `/api/v1/samples/` with `{"sample_id": "QC-2026-TEST-001", "matrix": "plasma", "status": "RECEIVED"}`
3. Record the sample's primary key from the response
4. As an Auditor, retrieve the audit trail for this sample: GET `/api/v1/audit/?entity_type=Sample&entity_id={id}`
5. Record the audit log entry fields: `entity_type`, `entity_id`, `operation`, `user_id`, `user_email`, `timestamp`, `changes`, `signature`, `previous_signature`

**Expected Result:**
- One audit record with `operation=CREATE`
- `entity_type=Sample`, `entity_id` matches created sample
- `user_id` matches authenticated Lab Technician's ID
- `user_email` is populated
- `timestamp` is within 1 second of the creation time
- `signature` is a 64-character hexadecimal string (SHA-256)
- `previous_signature` is populated (genesis or previous record's signature)
- `changes` contains `snapshot_after` with the sample data

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-008: Audit Trail — Immutability Enforcement**

| Field | Value |
|-------|-------|
| Test ID | OQ-008 |
| Test Name | Audit Trail Immutability |
| Category | Audit Trail — Critical |
| Risk Level | Critical |
| FS Reference | FS-003 |
| URS Reference | URS-F-004, URS-C-004 |

**Objective:** Verify that audit trail records cannot be modified or deleted through the API or database.

**Test Steps:**
1. Using the audit record created in OQ-007, attempt to modify it via the API: PATCH `/api/v1/audit/{id}/` with `{"operation": "MODIFIED"}` — record response
2. Attempt to delete the audit record via the API: DELETE `/api/v1/audit/{id}/` — record response
3. [Database-level test — requires DBA access] Attempt to execute: `UPDATE core_auditlog SET operation='TAMPERED' WHERE id={id};` — record psql response
4. [Database-level test] Attempt to execute: `DELETE FROM core_auditlog WHERE id={id};` — record psql response

**Expected Result:**
- API PATCH returns HTTP 405 (Method Not Allowed) or 403
- API DELETE returns HTTP 405 or 403
- Database UPDATE returns permission denied error (application user has no UPDATE on audit columns)
- Database DELETE returns permission denied error

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-009: Audit Trail — SHA-256 Chain Integrity Verification**

| Field | Value |
|-------|-------|
| Test ID | OQ-009 |
| Test Name | Audit Trail SHA-256 Chain Integrity |
| Category | Audit Trail — Critical |
| Risk Level | Critical |
| FS Reference | FS-002, FS-005 |
| URS Reference | URS-F-006 |

**Objective:** Verify that the SHA-256 audit chain is intact and that the chain verification function detects tampering.

**Test Steps:**
1. Create 3 sample records sequentially to generate at least 3 audit log entries
2. Request certified audit export: GET `/api/v1/audit/export/?entity_type=Sample` using Auditor account
3. Record `chain_verification.is_intact` value from response (must be `true`)
4. Record `chain_verification.records_verified` count (must match entity_count)
5. [Integrity test — QA-witnessed, DBA-executed] In a test-only scenario (must NOT be performed in a live production audit trail — use a staging environment if available): manually alter one audit log record's `changes` field at the database level, then re-run the export
6. Record the chain verification result after tampering (must report `is_intact: false` and identify the tampered record)

**Expected Result:**
- Unmodified chain: `chain_verification.is_intact = true`
- After tampering: `chain_verification.is_intact = false`; tampered record identified

*Note: Step 5/6 should be performed in a dedicated test instance, not in the production audit trail. Document the test environment used.*

**Actual Result:** ____________________________________________
**Test Environment for Tampering Test:** ________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________
**QA Witness Signature:** ____________________ Date: ___________

---

**OQ-010: Electronic Certification (Double-Authentication)**

| Field | Value |
|-------|-------|
| Test ID | OQ-010 |
| Test Name | Electronic Certification — Double Authentication |
| Category | Electronic Signatures |
| Risk Level | Critical |
| FS Reference | FS-008 |
| URS Reference | URS-F-011, URS-C-003 |

**Objective:** Verify that the electronic certification feature requires re-authentication before writing a certification event.

**Test Steps:**
1. Authenticate as a Principal Investigator; navigate to a completed sample result
2. Initiate certification: POST `/api/v1/samples/{id}/certify/` with `{"password": "ValidPass123!", "meaning": "I certify this result is accurate and complete"}`
3. Record HTTP response code and response body
4. Verify a certification audit record was created: GET `/api/v1/audit/?entity_type=Sample&entity_id={id}&operation=CERTIFY`
5. Confirm the certification audit record contains the `meaning` field
6. Attempt the same certification with an incorrect password: POST `/api/v1/samples/{id}/certify/` with `{"password": "WrongPass", "meaning": "..."}`
7. Record HTTP response code (must be 401); confirm no certification audit record was created

**Expected Result:**
- Valid certification: HTTP 200; certification audit record created with operation=CERTIFY, user_id, user_email, meaning, timestamp
- Invalid password: HTTP 401; no certification record created

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-011: BioNexus Box — Instrument Data Capture and Upload**

| Field | Value |
|-------|-------|
| Test ID | OQ-011 |
| Test Name | BioNexus Box Data Capture and Cloud Upload |
| Category | Hardware Integration |
| Risk Level | Critical |
| FS Reference | FS-001 |
| URS Reference | URS-F-001, URS-F-003 |

**Objective:** Verify that the BioNexus Box correctly captures instrument data, computes SHA-256, and uploads to the cloud backend.

**Test Steps:**
1. Confirm BioNexus Box is connected and services are running (per IQ-007)
2. Trigger a test output from the connected instrument (or inject test data via serial port simulator)
3. Monitor BioNexus Box local queue: `sqlite3 /var/lib/bionexus/queue.db "SELECT * FROM reading_queue ORDER BY id DESC LIMIT 1;"`
4. Record: `raw_sha256`, `parsed_json`, `packet_sha256`, `status` (should be PENDING initially, then UPLOADED)
5. Wait up to 60 seconds; verify record status changes to UPLOADED
6. Query the BioNexus cloud API: GET `/api/v1/readings/?instrument_id={id}&limit=1` — record the reading in cloud
7. Verify the `sha256_hash` field in the cloud record matches the `packet_sha256` from the Box queue
8. Verify the `raw_sha256` is preserved in the cloud record

**Expected Result:**
- Reading appears in local queue with PENDING status within 30 seconds
- Status transitions to UPLOADED within 60 seconds
- Reading appears in cloud API with matching SHA-256 hash
- `raw_sha256` preserved end-to-end

**Actual Result:** ____________________________________________
**Local Queue sha256:** ________________________
**Cloud Record sha256:** ________________________
**Match:** Yes [ ] / No [ ]
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-012: BioNexus Box — Offline Store-and-Forward**

| Field | Value |
|-------|-------|
| Test ID | OQ-012 |
| Test Name | BioNexus Box Offline Store-and-Forward |
| Category | Hardware Integration — Offline Mode |
| Risk Level | Major |
| FS Reference | FS-010 |
| URS Reference | URS-F-013 |

**Objective:** Verify that the BioNexus Box buffers data during network outage and synchronizes upon reconnection without data loss.

**Test Steps:**
1. Confirm Box is online and operational
2. Disconnect the Box from the network (unplug Ethernet cable or block network via firewall rule)
3. Trigger 5 instrument readings over 5 minutes
4. Verify all 5 readings are present in local SQLite queue with status=PENDING
5. Reconnect the network
6. Wait up to 5 minutes; verify all 5 readings reach status=UPLOADED in local queue
7. Confirm all 5 readings appear in the cloud API
8. Confirm SHA-256 hashes match for each reading

**Expected Result:**
- All 5 readings captured locally during network outage
- All 5 readings uploaded successfully after reconnection
- No readings lost; SHA-256 hashes preserved

**Actual Result:** ____________________________________________
**Readings buffered offline:** ____/5
**Readings uploaded after reconnect:** ____/5
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-013: Data Parsing — ALCOA+ Compliance Verification**

| Field | Value |
|-------|-------|
| Test ID | OQ-013 |
| Test Name | ALCOA+ Data Parsing Verification |
| Category | Data Integrity |
| Risk Level | Major |
| FS Reference | FS-011 |
| URS Reference | URS-F-014, URS-C-006 |

**Objective:** Verify that the parsing pipeline produces attributable, contemporaneous, and accurate structured data from raw instrument output.

**Test Steps:**
1. Inject known test data for the connected instrument type (e.g., dissolution tester ASCII output with known values)
2. Retrieve the parsed reading from the cloud API
3. Verify each ALCOA+ attribute:
   - **Attributable**: `instrument_id` field correctly identifies the source instrument
   - **Legible**: `parsed_json` produces human-readable structured data; no garbled characters
   - **Contemporaneous**: `captured_at` timestamp in reading is within 5 seconds of the test injection time
   - **Original**: `raw_bytes_b64` field contains the Base64-encoded original instrument bytes
   - **Accurate**: Parsed numeric values match the known test input values (e.g., if test input was 98.1%, parsed value must be 98.1, not 98 or 98.10001)

**Acceptance Criteria:** All 5 ALCOA attributes verified for the test reading

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-014: Audit Trail Export — Certified Export Function**

| Field | Value |
|-------|-------|
| Test ID | OQ-014 |
| Test Name | Certified Audit Export |
| Category | Audit Trail |
| Risk Level | Critical |
| FS Reference | FS-005 |
| URS Reference | URS-F-007 |

**Objective:** Verify that the certified audit export function produces a complete, verifiable export with correct metadata.

**Test Steps:**
1. Authenticate as Auditor role user
2. Request audit export: GET `/api/v1/audit/export/?entity_type=Sample`
3. Record the full response; verify presence of all required fields:
   - `export_id`: unique identifier
   - `timestamp`: export generation time
   - `exported_by.user_id`: matches Auditor's user ID
   - `tenant_id`: matches Auditor's tenant
   - `entity_count`: non-zero integer
   - `chain_verification.is_intact`: true
   - `chain_verification.records_verified`: matches entity_count
   - `records`: array with all audit entries
   - `export_signature`: HMAC-SHA256 signature string
   - `export_valid`: true
4. Attempt the same export as a Lab Technician (who has audit:view but not audit:export) — verify HTTP 403

**Expected Result:** Export contains all required fields; chain is intact; Lab Technician receives 403

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-015: User Account Management — Admin Creates User**

| Field | Value |
|-------|-------|
| Test ID | OQ-015 |
| Test Name | User Account Management — Create User |
| Category | User Management |
| Risk Level | Major |
| FS Reference | FS-013 |
| URS Reference | URS-F-017 |

**Objective:** Verify that an Admin can create user accounts and that the action is audit-logged.

**Test Steps:**
1. Authenticate as Admin role user
2. Create a new user: POST `/api/v1/users/` with `{"username": "new.tester", "email": "new.tester@lab.com", "role": "LAB_TECHNICIAN", "password": "TempPass123!"}`
3. Record HTTP response code and new user ID
4. Verify new user can log in: POST `/api/auth/login/` with new credentials
5. Verify user creation is logged in audit trail: GET `/api/v1/audit/?entity_type=User&entity_id={new_user_id}`
6. Attempt the same user creation as a Lab Technician (who lacks user:manage) — verify HTTP 403

**Expected Result:** User created; can authenticate; creation is audit-logged; Lab Technician receives 403

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-016: User Account Management — Disable/Deactivate User**

| Field | Value |
|-------|-------|
| Test ID | OQ-016 |
| Test Name | User Account Management — Deactivate User |
| Category | User Management — Access Revocation |
| Risk Level | Critical |
| FS Reference | FS-013 |
| URS Reference | URS-F-017, URS-C-002 |

**Objective:** Verify that deactivated user accounts cannot authenticate.

**Test Steps:**
1. Authenticate as Admin; deactivate the test user from OQ-015: PATCH `/api/v1/users/{id}/` with `{"is_active": false}`
2. Record HTTP response code (must be 200)
3. Attempt to log in as the deactivated user: POST `/api/auth/login/` with their credentials
4. Record HTTP response code (must be 401 or 403)
5. Verify deactivation is recorded in audit trail

**Expected Result:** HTTP 401 or 403 on login attempt for deactivated user; audit log records the deactivation event

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-017: Token Refresh Flow**

| Field | Value |
|-------|-------|
| Test ID | OQ-017 |
| Test Name | JWT Refresh Token Flow |
| Category | Authentication |
| Risk Level | Major |
| FS Reference | FS-007 |

**Objective:** Verify that a valid refresh token can generate a new access token and that used/invalid refresh tokens are rejected.

**Test Steps:**
1. Authenticate; record access and refresh tokens
2. Use refresh token: POST `/api/auth/refresh/` with `{"refresh": "<refresh_token>"}`
3. Record new access token; confirm it is different from the original
4. Use the new access token for an authenticated API call; verify HTTP 200
5. Attempt to reuse the original refresh token after it has been consumed; record response (should be 401)

**Expected Result:** New access token issued on valid refresh; consumed refresh token is rejected

**Actual Result:** ____________________________________________
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**OQ-018: Audit Trail — Mandatory User Attribution Enforcement**

| Field | Value |
|-------|-------|
| Test ID | OQ-018 |
| Test Name | Mandatory User Attribution in Audit Trail |
| Category | Audit Trail — Compliance |
| Risk Level | Critical |
| FS Reference | FS-004 |
| URS Reference | URS-C-001 |

**Objective:** Verify that the system cannot create audit records without user attribution.

**Test Steps:**
1. Review the AuditTrail.record() service method in code (documentation review)
2. Confirm `user_id` and `user_email` parameters have no default values and raise ValueError if not provided (code inspection)
3. Verify that every API endpoint that modifies GxP data passes the authenticated user's `user_id` and `user_email` to AuditTrail.record()
4. Execute a sample creation as an authenticated user; retrieve the audit record; confirm `user_id` is not null and not zero

**Acceptance Criteria:**
- Code inspection confirms ValueError raised if user_id is missing
- Every audit record for GxP operations contains a non-null user_id
- No audit records with null user_id exist in the production database (SQL check: `SELECT COUNT(*) FROM core_auditlog WHERE user_id IS NULL`)

**Actual Result:** ____________________________________________
**Null user_id records:** ______ (must be 0)
**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

### 11.3 OQ Summary

| Test ID | Test Name | Risk Level | Result | Deviation Ref |
|---------|-----------|-----------|--------|--------------|
| OQ-001 | Successful User Authentication | Critical | | |
| OQ-002 | Authentication Rejection — Invalid Password | Critical | | |
| OQ-003 | Expired Token Rejection | Critical | | |
| OQ-004 | RBAC — Lab Technician Cannot Delete | Critical | | |
| OQ-005 | RBAC — Auditor Read-Only | Critical | | |
| OQ-006 | Multi-Tenant Isolation | Critical | | |
| OQ-007 | Audit Trail Creation on Sample Create | Critical | | |
| OQ-008 | Audit Trail Immutability | Critical | | |
| OQ-009 | SHA-256 Chain Integrity | Critical | | |
| OQ-010 | Electronic Certification | Critical | | |
| OQ-011 | Box Data Capture and Upload | Critical | | |
| OQ-012 | Box Offline Store-and-Forward | Major | | |
| OQ-013 | ALCOA+ Parsing Verification | Major | | |
| OQ-014 | Certified Audit Export | Critical | | |
| OQ-015 | Admin Creates User | Major | | |
| OQ-016 | Deactivate User | Critical | | |
| OQ-017 | JWT Refresh Token Flow | Major | | |
| OQ-018 | Mandatory User Attribution | Critical | | |

**OQ Overall Result:** Pass [ ] / Fail [ ] / Conditional Pass [ ]
**OQ Sign-Off:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| CSV Specialist | | | |
| QA Representative | | | |
| System Owner | | | |

---

## 12. Performance Qualification (PQ)

### 12.1 PQ Purpose

The Performance Qualification provides documented evidence that the BioNexus system performs consistently and reliably under real-world operational conditions, using actual instrument data, real laboratory workflows, and representative user loads.

### 12.2 PQ Prerequisites

- OQ completed and signed; all critical deviations resolved
- End users (Lab Technicians, PIs, Auditors) available and trained
- At least one actual laboratory instrument connected to a BioNexus Box
- Production instrument data available (or validated test data representative of production)
- PQ period of minimum 10 business days (2 calendar weeks) of operational use

---

**PQ-001: End-to-End Dissolution Testing Workflow**

| Field | Value |
|-------|-------|
| Test ID | PQ-001 |
| Test Name | End-to-End Dissolution Test Workflow |
| Category | Workflow |
| Risk Level | Critical |
| URS Reference | URS-F-001–F-007, URS-C-006 |

**Objective:** Verify the complete workflow from dissolution instrument data capture through audit-ready record creation under real laboratory conditions.

**Workflow Steps:**
1. Lab Technician authenticates with their own credentials
2. Dissolution tester runs and outputs results via RS232 to BioNexus Box
3. BioNexus Box captures data, computes SHA-256, uploads to cloud
4. Lab Technician verifies the reading appears in the BioNexus dashboard within 60 seconds
5. Lab Technician reviews the parsed data against the instrument printout — confirms values match
6. Principal Investigator logs in and certifies the result using double-authentication
7. Auditor logs in and reviews the audit trail for the result
8. Auditor requests certified audit export; verifies chain integrity is intact

**Acceptance Criteria:**
- Data appears in cloud within 60 seconds of instrument output
- Parsed values match instrument printout values exactly
- Audit trail contains CREATE, CERTIFY events with correct user attribution
- Certified export chain is intact

**Number of Dissolution Runs Tested:** ______ (minimum 5)
**Results Summary:** ____________________________________
**Pass [ ] / Fail [ ]**
**Lab Technician Sign-Off:** ______________________ Date: ___________
**PI Sign-Off:** ______________________ Date: ___________
**QA Witness:** ______________________ Date: ___________

---

**PQ-002: Concurrent User Load Test**

| Field | Value |
|-------|-------|
| Test ID | PQ-002 |
| Test Name | Concurrent User Performance Test |
| Category | Performance |
| Risk Level | Major |
| URS Reference | URS-P-004 |

**Objective:** Verify that the system maintains acceptable response times with 20 concurrent authenticated users.

**Test Steps:**
1. Using a load testing tool (Locust, k6, or equivalent), configure 20 virtual users executing authenticated API calls
2. Simulate a mixed workload: 60% read operations (GET samples, GET audit), 30% write operations (POST samples), 10% admin operations
3. Run the load test for 15 minutes
4. Record: average response time, 95th percentile response time, error rate, requests per second
5. Verify no data integrity issues during concurrent writes (no duplicate audit records, correct SHA-256 chains)

**Acceptance Criteria:**
- 95th percentile API response time < 2 seconds (reads) and < 3 seconds (writes)
- Error rate < 1%
- No data integrity violations (audit chain intact after test)

**Results:**
- Avg response time (reads): ________ ms
- 95th pct response time (reads): ________ ms (target: < 2000 ms)
- Avg response time (writes): ________ ms
- 95th pct response time (writes): ________ ms (target: < 3000 ms)
- Error rate: ________% (target: < 1%)

**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________
**QA Witness:** ______________________ Date: ___________

---

**PQ-003: Continuous Operation — 10-Day Monitoring**

| Field | Value |
|-------|-------|
| Test ID | PQ-003 |
| Test Name | Continuous Operational Monitoring — 10 Business Days |
| Category | Performance / Availability |
| Risk Level | Major |
| URS Reference | URS-P-006 |

**Objective:** Verify system availability and reliability over a 10-business-day operational period.

**Monitoring Period:** ______________ to ______________

**Daily Checklist (complete each business day):**

| Day | Date | All Instruments Online | Audit Trail Intact | Readings Uploaded (Count) | Any Errors/Deviations | Reviewed By |
|-----|------|----------------------|--------------------|--------------------------|----------------------|-------------|
| 1 | | [ ] | [ ] | | | |
| 2 | | [ ] | [ ] | | | |
| 3 | | [ ] | [ ] | | | |
| 4 | | [ ] | [ ] | | | |
| 5 | | [ ] | [ ] | | | |
| 6 | | [ ] | [ ] | | | |
| 7 | | [ ] | [ ] | | | |
| 8 | | [ ] | [ ] | | | |
| 9 | | [ ] | [ ] | | | |
| 10 | | [ ] | [ ] | | | |

**Acceptance Criteria:**
- System available on all 10 business days (planned maintenance windows excluded and documented)
- All instrument readings uploaded successfully (< 0.1% transmission failures)
- No audit trail integrity failures
- All errors documented and addressed

**Total Readings Captured:** ________ | **Total Uploaded:** ________ | **Upload Rate:** ________%
**Availability:** ________% (target >= 99.5% excl. maintenance)

**Pass [ ] / Fail [ ]**
**System Owner Sign-Off:** ______________________ Date: ___________

---

**PQ-004: Audit Trail Retention and Retrieval Test**

| Field | Value |
|-------|-------|
| Test ID | PQ-004 |
| Test Name | Audit Trail Query Performance and Retrieval |
| Category | Performance / Compliance |
| Risk Level | Major |
| URS Reference | URS-P-005, URS-P-007, URS-C-004 |

**Objective:** Verify that audit trail records are retrievable within performance targets and that the system handles large data sets correctly.

**Test Steps:**
1. Verify the total count of audit log records in the production database
2. Execute audit trail query for the busiest entity type with maximum expected record count: GET `/api/v1/audit/?entity_type=Sample&limit=10000` — record response time
3. Request certified audit export for the full available period — record response time and record count
4. Verify paginated responses work correctly for > 1,000 records
5. Verify records are accessible and human-readable (not encoded or compressed in a way that prevents inspection)

**Acceptance Criteria:**
- Query for up to 10,000 records completes within 5 seconds
- Certified export for > 1,000 records completes within 30 seconds
- Pagination works correctly (next/previous links valid)
- Records are human-readable

**Query Response Time:** ________ seconds (target: < 5 s)
**Export Response Time:** ________ seconds

**Pass [ ] / Fail [ ]**
**Tester Signature:** _________________________ Date: ___________

---

**PQ-005: User Acceptance Test (UAT) — End User Sign-Off**

| Field | Value |
|-------|-------|
| Test ID | PQ-005 |
| Test Name | User Acceptance Testing |
| Category | UAT |
| Risk Level | Critical |

**Objective:** Obtain formal acceptance from end users that the system meets their operational requirements.

**UAT Criteria:** End users confirm the system is fit for GxP use in their laboratory.

| User Role | Name | Statement | Signature | Date |
|-----------|------|-----------|-----------|------|
| Lab Technician | | "I confirm the system captures and stores instrument data correctly and the audit trail accurately reflects my actions." | | |
| Principal Investigator | | "I confirm the certification function works correctly and the audit trail provides an accurate record of all analytical operations." | | |
| Auditor | | "I confirm the audit trail and export functions provide a complete, tamper-evident record suitable for regulatory inspection." | | |
| QA Manager | | "I confirm the system meets GxP compliance requirements as defined in BNX-VAL-001." | | |

**Overall UAT Result:** Accepted [ ] / Conditionally Accepted [ ] / Rejected [ ]
**Conditions (if applicable):** ____________________________________________

---

### 12.3 PQ Summary

| Test ID | Test Name | Result | Deviation Ref |
|---------|-----------|--------|--------------|
| PQ-001 | End-to-End Dissolution Workflow | | |
| PQ-002 | Concurrent User Load Test | | |
| PQ-003 | 10-Day Continuous Monitoring | | |
| PQ-004 | Audit Trail Retention and Retrieval | | |
| PQ-005 | User Acceptance Testing | | |

**PQ Overall Result:** Pass [ ] / Fail [ ] / Conditional Pass [ ]
**PQ Sign-Off:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| CSV Specialist | | | |
| QA Representative | | | |
| System Owner | | | |
| Validation Sponsor | | | |

---

## 13. Traceability Matrix

*This matrix demonstrates end-to-end traceability from User Requirements through to Qualification testing. URS items not listed here are covered in the full URS-FS-DS traceability workbook (BNX-TM-001).*

### 13.1 Traceability Matrix — Key Examples

| URS ID | URS Requirement (Summary) | FS ID | FS Function | DS ID | DS Implementation | IQ Test | OQ Test | PQ Test |
|--------|--------------------------|-------|-------------|-------|-------------------|---------|---------|---------|
| URS-F-001 | Capture instrument data without manual transcription | FS-001 | Instrument Data Capture | DS-001 | pyserial-based Collector Service | IQ-007 | OQ-011 | PQ-001 |
| URS-F-003 | SHA-256 hash of raw instrument bytes at capture | FS-001 | Hash at capture | DS-001 | SHA-256 in collector before queue write | IQ-007 | OQ-011 | PQ-001 |
| URS-F-004 | Immutable audit trail | FS-003 | Audit Immutability | DS-003 | save() override + DB privilege restriction | IQ-006 | OQ-008 | PQ-003 |
| URS-F-005 | Audit trail with user attribution | FS-004 | Mandatory Attribution | DS-004 | ValueError on missing user_id | IQ-006 | OQ-007, OQ-018 | PQ-001 |
| URS-F-006 | SHA-256 chain — tampering detectable | FS-002 | Hash Chaining | DS-002 | previous_signature in chain | IQ-006 | OQ-009 | PQ-003 |
| URS-F-007 | Certified audit export | FS-005 | Certified Export | DS-005 | AuditExportService + HMAC signature | IQ-010 | OQ-014 | PQ-004 |
| URS-F-008 | RBAC with 5 roles | FS-006 | RBAC Enforcement | DS-006 | @permission_required decorator | IQ-008 | OQ-004, OQ-005 | PQ-002 |
| URS-F-009 | Unique user identification | FS-007 | Authentication | DS-007 | Unique username constraint in DB | IQ-008 | OQ-001, OQ-002 | PQ-005 |
| URS-F-010 | Username/password authentication | FS-007 | JWT Authentication | DS-007 | JWTService.generate_tokens() | IQ-005 | OQ-001, OQ-002, OQ-003 | PQ-005 |
| URS-F-011 | Electronic certification / double-auth | FS-008 | E-Certification | DS-008 | /certify/ endpoint + re-authentication | IQ-008 | OQ-010 | PQ-001 |
| URS-F-012 | Multi-tenant data isolation | FS-009 | Tenant Isolation | DS-009 | tenant_id FK on all models; BaseRepository | IQ-006 | OQ-006 | PQ-002 |
| URS-F-013 | Offline buffer without data loss | FS-010 | Store-and-Forward | DS-010 | SQLite WAL; synchronous=FULL | IQ-007 | OQ-012 | PQ-003 |
| URS-F-014 | ALCOA+ parsing | FS-011 | ALCOA+ Parsing | DS-011 | BaseParser; per-instrument parsers | IQ-007 | OQ-013 | PQ-001 |
| URS-C-001 | Who/what/when in audit trail | FS-003, FS-004 | Audit attribution | DS-003, DS-004 | AuditLog model fields | IQ-006 | OQ-007, OQ-018 | PQ-001 |
| URS-C-003 | E-signatures unique per individual | FS-008 | E-Certification | DS-008 | Username uniqueness + re-auth | IQ-008 | OQ-010 | PQ-005 |
| URS-S-001 | All communications encrypted | — | TLS enforcement | DS-I-006 | Cloud Run HTTPS-only; TLS 1.2 minimum | IQ-005 | OQ-011 | PQ-002 |
| URS-S-004 | No cross-tenant data access | FS-009 | Tenant Isolation | DS-009 | Three-layer tenant_id filtering | IQ-006 | OQ-006 | PQ-002 |
| URS-P-004 | 20 concurrent users | — | Scalability | DS-I-002 | Cloud Run autoscaling 1–10 instances | IQ-001 | — | PQ-002 |
| URS-P-006 | >= 99.5% availability | — | Availability | DS-I-002 | Cloud Run + Cloud SQL HA | IQ-001, IQ-002 | — | PQ-003 |

---

## 14. Risk Assessment

### 14.1 Risk Assessment Methodology

Risk assessment is conducted per ICH Q9 (R1) using a Failure Mode and Effects Analysis (FMEA) approach. Risk is quantified as:

**Risk Priority Number (RPN) = Severity (S) × Occurrence (O) × Detectability (D)**

| Score | Severity (S) | Occurrence (O) | Detectability (D) |
|-------|-------------|----------------|-------------------|
| 1 | Negligible — no GxP impact | Very unlikely (< 1 per year) | Highly detectable — automatic alert |
| 2 | Minor — low GxP impact | Unlikely (1–2 per year) | Easily detectable — routine check |
| 3 | Moderate — potential data integrity impact | Possible (monthly) | Moderately detectable — manual review |
| 4 | Major — likely regulatory non-compliance | Frequent (weekly) | Difficult to detect — requires investigation |
| 5 | Critical — patient safety / data falsification | Very frequent (daily) | Not detectable without specific test |

**Risk Acceptance Criteria:**
- RPN 1–9: Acceptable — monitor
- RPN 10–19: Moderate — mitigate where practical
- RPN 20–44: High — mitigation required before release
- RPN >= 45: Critical — must mitigate to < 20 before release

### 14.2 FMEA Risk Register

| Risk ID | Function | Failure Mode | Potential Effect | S | O | D | RPN | Mitigation | Residual RPN | Verification |
|---------|----------|--------------|-----------------|---|---|---|-----|------------|-------------|-------------|
| RA-001 | Audit Trail — SHA-256 Chain | Audit record tampered after creation | Data integrity loss; regulatory non-compliance; undetected falsification | 5 | 2 | 1 | 10 | SHA-256 chain detected by chain verification; DB privilege restriction prevents modification | 2 | OQ-008, OQ-009 |
| RA-002 | User Attribution | Audit record created without user_id | 21 CFR Part 11 violation; non-attributable record | 5 | 2 | 2 | 20 | ValueError enforced at service layer; NOT NULL at DB level | 5 | OQ-018 |
| RA-003 | RBAC | Permission bypass — unauthorized user accesses GxP data | Unauthorized data access; data integrity risk | 5 | 2 | 2 | 20 | @permission_required on all endpoints; 403 enforcement tested; multi-layer defense | 4 | OQ-004, OQ-005 |
| RA-004 | Multi-Tenant Isolation | Cross-tenant data leak | Data breach; regulatory violation; customer confidentiality | 5 | 2 | 2 | 20 | Three-layer tenant_id filtering (HTTP, service, repository); tested in OQ-006 | 4 | OQ-006 |
| RA-005 | BioNexus Box — Data Capture | Serial port disconnects; data not captured | Missing instrument readings; data gaps in audit trail | 4 | 3 | 2 | 24 | Exponential backoff reconnect; error logged and reported; instrument status monitoring | 8 | OQ-011 |
| RA-006 | Offline Store-and-Forward | SQLite corruption on power loss | Loss of locally buffered readings | 4 | 2 | 2 | 16 | WAL mode + synchronous=FULL prevents corruption; tested in OQ-012; 30-day buffer capacity | 4 | OQ-012 |
| RA-007 | Authentication | JWT secret key compromise | Unauthorized access as any user; complete system compromise | 5 | 1 | 3 | 15 | Secret stored in GCP Secret Manager; not in code or environment; access limited by IAM | 5 | IQ-004 |
| RA-008 | Electronic Certification | Certification signed without re-authentication | Non-compliant e-signature; 21 CFR Part 11 §11.200 violation | 5 | 2 | 2 | 20 | Double-authentication enforced in certify endpoint; password verification before writing record | 4 | OQ-010 |
| RA-009 | Data Parsing | Parser produces incorrect numeric values | Inaccurate data in GxP record; ALCOA+ violation (Accurate) | 5 | 2 | 3 | 30 | Parser unit tests with known-value test vectors; OQ-013 verification with real instrument | 10 | OQ-013 |
| RA-010 | TLS/HTTPS | Man-in-the-middle attack on API traffic | Data interception; integrity compromise | 5 | 1 | 2 | 10 | TLS 1.3; certificate pinning on Box; HSTS on API; verified in IQ-005 | 2 | IQ-005 |
| RA-011 | Audit Export | Export generated with broken chain undetected | Regulatory submission based on tampered data | 5 | 1 | 1 | 5 | Chain verification run at export time; is_intact field in export | 2 | OQ-014 |
| RA-012 | Cloud SQL Availability | Database outage causes API unavailability | System unavailable; data capture halted (Box buffers) | 4 | 1 | 1 | 4 | Cloud SQL HA; automated failover; Box offline buffering provides 30-day tolerance | 2 | PQ-003 |
| RA-013 | Token Expiry | Stale access tokens used after role change | User retains permissions they no longer have (15 min max) | 3 | 2 | 2 | 12 | 15-minute access token lifetime limits exposure; token revocation on account deactivation | 6 | OQ-016, OQ-017 |
| RA-014 | Firmware Update | Malicious or untested firmware deployed to Box | Data capture failure; integrity loss; security compromise | 5 | 1 | 2 | 10 | OTA updates signed; update requires authenticated management session; rollback capability | 4 | IQ-007 |
| RA-015 | Change Control | Undocumented system change bypasses validation | System operates outside validated state; audit finding | 5 | 2 | 3 | 30 | Change control SOP (Section 18); all production changes require QA approval; immutable infrastructure | 6 | Section 18 |

### 14.3 Risk Acceptance Summary

All risks with initial RPN >= 20 have been mitigated to residual RPN < 20:
- RA-002, RA-003, RA-004, RA-008, RA-009, RA-015: Initial RPN >= 20; mitigated to < 10
- No Critical risks (RPN >= 45) identified

No risks require further action before system release. All mitigations are verified through the IQ/OQ/PQ protocols referenced in the Risk Register.

---

## 15. Deviation and CAPA Handling

### 15.1 Definition of a Validation Deviation

A validation deviation is any departure from the written test procedure or any test result that does not meet the defined acceptance criteria during IQ, OQ, or PQ execution.

Deviations are NOT failures of the system per se — they may be the result of:
- Test script errors (incorrect expected result documented)
- Environmental or configuration issues (not a system defect)
- Genuine system defects requiring correction

### 15.2 Deviation Classification

| Classification | Definition | Required Response |
|---------------|------------|------------------|
| **Critical** | Test failure directly related to a GxP-critical function (audit trail, RBAC, e-signature, data integrity) | Halt testing of dependent test cases; immediate QA notification; root cause analysis (RCA) required; retesting mandatory before progression |
| **Major** | Test failure that could indirectly affect GxP data; any security-related failure | QA notification within 24 hours; RCA required; retesting required; QA approval to proceed |
| **Minor** | Cosmetic, documentation, or non-GxP functional failure | Document and resolve; QA review at phase close; may proceed with documented risk acceptance |

### 15.3 Deviation Handling Process

```
Test Executed
    |
Test Passes? ─── Yes ───> Record Pass; Continue
    |
   No
    |
    ├── Stop Execution of Affected Test Case
    ├── Document Deviation (use Deviation Report template — Appendix C)
    ├── Notify QA Representative
    ├── Classify Deviation (Critical / Major / Minor)
    |
    ├── [Critical/Major] Perform Root Cause Analysis
    |       ├── Identify: Was it a test script error, environment issue, or system defect?
    |       ├── Document findings in Deviation Report
    |       └── Implement correction
    |
    ├── Implement Corrective Action
    |       ├── Fix system defect (if applicable) — requires BioNexus approval + change control
    |       ├── Correct test script (if documentation error)
    |       └── Resolve environment issue
    |
    ├── QA Reviews and Approves Deviation Report
    |
    ├── Retest (for Critical/Major deviations)
    |       └── Document retest result in original Deviation Report
    |
    └── QA Signs Off on Deviation Resolution
```

### 15.4 CAPA Requirements

For any **Critical** deviation or recurring **Major** deviations (same failure mode appearing 2+ times), a formal CAPA (Corrective and Preventive Action) must be initiated:

- **Corrective Action**: What was done to fix the current failure?
- **Root Cause**: Why did the failure occur? (Use 5-Why or fishbone analysis)
- **Preventive Action**: What systemic change prevents recurrence?
- **Effectiveness Check**: How will we verify the CAPA worked?
- **Timeline**: CAPAs for Critical deviations must be resolved before validation is declared complete

CAPA records are maintained in the customer's quality management system. BioNexus Engineering supports CAPA resolution for system-related defects.

### 15.5 Deviation Report Template

See Appendix C for the Deviation Report template (BNX-DEV-TEMPLATE).

---

## 16. Validation Summary Report Template

*The completed Validation Summary Report (BNX-VAL-001-SR) is generated upon completion of all IQ/OQ/PQ phases. This section provides the template.*

---

**VALIDATION SUMMARY REPORT**
**BioNexus Platform**

**Document ID:** BNX-VAL-001-SR
**Validation Plan Reference:** BNX-VAL-001 v1.0
**Customer Site:** ____________________________________________
**BioNexus Platform Version:** ________________________________
**BioNexus Box Firmware Version:** ___________________________
**Qualification Period:** _________________ to _________________
**CSV Specialist:** Johannes Eberhardt / GMP4U

---

### 16.1 Qualification Activities Summary

| Phase | Start Date | End Date | Tests Executed | Tests Passed | Tests Failed | Deviations Opened | Deviations Closed |
|-------|-----------|---------|----------------|-------------|-------------|------------------|------------------|
| IQ | | | 10 | | | | |
| OQ | | | 18 | | | | |
| PQ | | | 5 | | | | |
| **TOTAL** | | | **33** | | | | |

### 16.2 Deviation Summary

| Deviation ID | Phase | Classification | Brief Description | Resolution | Status |
|-------------|-------|---------------|-------------------|------------|--------|
| | | | | | |

### 16.3 Qualification Conclusion

Based on the execution of IQ/OQ/PQ protocols against BioNexus Platform version [____] installed at [Customer Site], it is concluded that:

[ ] **The BioNexus Platform is QUALIFIED for GxP use** as defined in the scope of BNX-VAL-001. All critical and major test cases passed. All deviations have been resolved and closed. The system may be released for regulated use.

[ ] **The BioNexus Platform is CONDITIONALLY QUALIFIED** for GxP use, subject to resolution of the following open items: ______________________

[ ] **The BioNexus Platform is NOT QUALIFIED**. The following critical issues require resolution and retesting: ______________________

### 16.4 Post-Validation Requirements

- [ ] Periodic Review scheduled for: ______________________ (12 months from qualification date)
- [ ] Change control process communicated to System Owner
- [ ] Training records updated for all qualified users
- [ ] Validation documentation archived in: ______________________

### 16.5 Approval Signatures

| Role | Name | Signature | Date |
|------|------|-----------|------|
| CSV Specialist (GMP4U) | Johannes Eberhardt | | |
| QA Manager | | | |
| System Owner | | | |
| Validation Sponsor | | | |

---

## 17. Periodic Review

### 17.1 Purpose

Periodic Review provides documented evidence that the BioNexus system remains in a validated state throughout its operational life. Per EU Annex 11 §11, computerized systems should be evaluated periodically to confirm their validated state has been maintained.

### 17.2 Periodic Review Schedule

| Review Type | Frequency | Trigger |
|-------------|-----------|---------|
| Full Periodic Review | Annual (12 months from last review/qualification) | Scheduled |
| Triggered Review | As needed | Significant change, incident, or regulatory change |
| Continuous Monitoring Review | Monthly | Automated monitoring report reviewed by System Owner |

### 17.3 Periodic Review Scope

The annual Periodic Review must assess:

1. **Change History**: All changes made since the previous review (system version, infrastructure, configuration). Confirm all changes went through change control and were appropriately validated.

2. **Incident and Deviation Review**: All system incidents, deviations, and CAPAs. Confirm all are resolved. Identify trends.

3. **Audit Trail Integrity**: Run chain verification on a representative sample of audit records. Confirm `chain_verification.is_intact = true`.

4. **User Access Review**: Review all active user accounts and their roles. Confirm accounts for former employees are deactivated. Confirm role assignments remain appropriate.

5. **Backup and Recovery**: Confirm database backups completed successfully during the review period. Optionally test restore to a non-production environment.

6. **Security Review**: Review GCP security logs for anomalous access patterns. Confirm SSL certificates valid. Review any security advisories for Django, PostgreSQL, and OS.

7. **Performance Review**: Review API response time trends. Confirm no degradation beyond acceptance thresholds.

8. **Regulatory Change Assessment**: Review any new or amended regulations (21 CFR Part 11, EU Annex 11, GAMP5) that may require system changes.

9. **Supplier Review**: Confirm GCP remains compliant (SOC 2 Type II, ISO 27001). Review any GCP service changes that may affect the validated state.

### 17.4 Revalidation Criteria

A full or partial revalidation (OQ/PQ) is required if the Periodic Review identifies:

- A critical GxP function has been materially changed (see Change Control, Section 18)
- Audit trail integrity check fails
- A security breach or confirmed unauthorized access has occurred
- Regulatory changes require new or modified controls
- Multiple major incidents in the review period suggesting systematic failure

### 17.5 Periodic Review Report

The Periodic Review produces a Periodic Review Report (BNX-PRR-001) documenting all findings, conclusions, and any required corrective actions. The report is reviewed and approved by QA and the System Owner.

---

## 18. Change Control

### 18.1 Purpose

Change Control ensures that any modification to the validated BioNexus system is assessed for impact on the validated state, appropriately tested, and documented before implementation in production.

### 18.2 Types of Changes

| Change Type | Examples | Process |
|-------------|----------|---------|
| **Major Change** | New GxP-critical feature; change to audit trail logic; RBAC model change; new instrument parser for new instrument category; database schema change affecting GxP data | Full change control with impact assessment, OQ retesting of affected functions, QA approval before deployment |
| **Minor Change** | Bug fix not affecting GxP functions; UI cosmetic change; performance optimization; non-GxP model field addition | Abbreviated change control; regression test confirmation; QA review (not full OQ) |
| **Emergency Change** | Security patch; critical bug fix affecting system availability | Emergency change control with retrospective documentation; same impact assessment requirements; QA notified within 24 hours |
| **Infrastructure Change** | GCP region migration; Cloud SQL version upgrade; Cloud Run revision update | Supplier assessment update; IQ re-verification for affected components; OQ if functional behavior may be affected |

### 18.3 Change Control Process

```
1. CHANGE REQUEST
   ├── Requestor submits Change Request Form (Appendix D)
   ├── Describes: what is changing, why, and scope
   └── Assigns Change Category (Major / Minor / Emergency)

2. IMPACT ASSESSMENT
   ├── System Owner + QA + BioNexus Technical Lead assess:
   │   ├── GxP impact: Does this affect any GxP-critical function?
   │   ├── Validation impact: Does this change the validated state?
   │   ├── Regulatory impact: Does this require regulatory notification?
   │   └── Testing requirements: What IQ/OQ/PQ tests must be re-executed?
   └── Impact Assessment documented in Change Request

3. APPROVAL
   ├── Minor changes: QA Manager approval
   ├── Major changes: QA Manager + System Owner + Validation Sponsor approval
   └── Emergency: verbal approval + retrospective documentation

4. IMPLEMENTATION
   ├── Changes implemented in non-production environment first
   ├── Testing performed per Impact Assessment
   └── BioNexus Engineering deploys to production (via CI/CD with approval gate)

5. POST-IMPLEMENTATION VERIFICATION
   ├── Smoke test of changed and adjacent functions
   ├── Affected IQ/OQ test cases re-executed
   └── System Owner confirms production system operational

6. DOCUMENTATION CLOSURE
   ├── Change Request marked complete with results
   ├── Relevant design documents updated (DS, FS updated if needed)
   ├── Traceability Matrix updated
   └── Validation Summary Report addendum created if required
```

### 18.4 Version Control

All BioNexus software versions are managed in Git with semantic versioning (MAJOR.MINOR.PATCH). Production deployments are always from a tagged, immutable release. The production version is recorded in the IQ documentation and must match the approved DS baseline.

Infrastructure changes are managed via Terraform with state files under version control. Infrastructure changes require peer review and approval gate before apply.

---

## 19. Appendices

### Appendix A: Test Case Template

---

**TEST CASE: [XX-NNN]**

| Field | Value |
|-------|-------|
| Test ID | [Phase]-[NNN] (e.g., OQ-001) |
| Test Name | [Descriptive name] |
| Phase | IQ / OQ / PQ |
| Category | [Authentication / Audit Trail / RBAC / Hardware / etc.] |
| Risk Level | Critical / Major / Minor |
| FS Reference | [FS-XXX] |
| DS Reference | [DS-XXX] |
| URS Reference | [URS-X-XXX] |
| Prerequisites | [What must be in place before this test] |
| Test Data | [Specific data inputs, user accounts, configurations needed] |
| Tester | [Role responsible for execution] |
| Reviewer | [CSV Specialist or QA] |

**Objective:** [Single sentence describing what this test demonstrates]

**Test Steps:**
1. [Step 1 — specific, unambiguous instruction]
2. [Step 2]
3. [Step N]

**Expected Result:** [Precise statement of what must be observed to pass]

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

**Actual Result:** _______________________________________

**Result:** Pass [ ] / Fail [ ] / N/A [ ]

**Deviation Reference (if failed):** _______________________

**Tester:** _________________________ **Date:** ____________
**Reviewer:** _______________________ **Date:** ____________

---

### Appendix B: Approval and Sign-Off Form

---

**QUALIFICATION PHASE SIGN-OFF**

**System:** BioNexus Platform
**Phase:** IQ [ ] / OQ [ ] / PQ [ ]
**Validation Plan Reference:** BNX-VAL-001 v1.0
**Customer Site:** ____________________________________________
**Platform Version:** ________________________________________

**Summary:**
- Total test cases executed: ________
- Passed: ________
- Failed: ________
- N/A: ________
- Open deviations: ________
- Closed deviations: ________

**Conclusion:**

This phase of qualification has been completed. All deviations have been documented, assessed, and resolved (or risk-accepted with QA approval). The system has [ has not ] demonstrated the required performance for this qualification phase.

**Approval to proceed to next phase:** Yes [ ] / No [ ] / N/A (final phase) [ ]

| Role | Name | Signature | Date |
|------|------|-----------|------|
| CSV Specialist (GMP4U) | Johannes Eberhardt | | |
| QA Representative | | | |
| System Owner | | | |

---

### Appendix C: Deviation Report Template

---

**VALIDATION DEVIATION REPORT**

**Document ID:** BNX-DEV-[YYYY]-[NNN]
**Validation Plan:** BNX-VAL-001 v1.0
**Date Raised:** ___________________

**Section 1: Deviation Description**

| Field | Value |
|-------|-------|
| Test Case ID | [e.g., OQ-009] |
| Test Case Name | |
| Phase | IQ / OQ / PQ |
| Deviation Date | |
| Raised By | |
| Classification | Critical / Major / Minor |

**Description of Deviation:**
[Describe exactly what was observed versus what was expected. Include actual test results, error messages, screenshots or logs as attachments.]

**Expected Result:**

**Actual Result:**

---

**Section 2: Immediate Impact Assessment**

**GxP Impact:** Does this deviation affect a GxP-critical function?
Yes [ ] / No [ ]

**If Yes, describe the potential patient safety or data integrity impact:**

**Can qualification proceed while this deviation is open?**
Yes [ ] / No [ ] / With conditions: _______________________

---

**Section 3: Root Cause Analysis** *(required for Critical and Major deviations)*

**Root Cause Category:**
- [ ] Test script error (incorrect expected result documented)
- [ ] Environmental / configuration issue
- [ ] System defect (software or hardware)
- [ ] Test data issue
- [ ] Other: ________________________

**Root Cause Description:**

**5-Why Analysis (if system defect):**
1. Why did the failure occur?
2. Why did that happen?
3. Why did that happen?
4. Why did that happen?
5. Root cause:

---

**Section 4: Corrective Action**

**Action Taken:**

**Action Completed By:** ___________________ **Date:** ___________

**Configuration / Code Change Reference (if applicable):**

---

**Section 5: Retesting**

**Retest Required:** Yes [ ] / No [ ]

**Retest Method:** Full retest of test case [ ] / Partial retest [ ] / Regression test only [ ]

**Retest Date:** ___________________
**Retest Result:** Pass [ ] / Fail [ ]

**Retest Performed By:** ___________________
**Retest Reviewed By:** ___________________

---

**Section 6: Preventive Action** *(required for Critical deviations)*

**Preventive Action:**

**Effectiveness Check:**

**Target Completion Date:**

---

**Section 7: Closure**

**Deviation Status:** Open [ ] / Closed [ ] / Risk-Accepted [ ]

**Risk Acceptance Rationale (if applicable):**

**Closed By (QA):** _________________________ **Date:** ___________

---

### Appendix D: Change Request Form Template

---

**CHANGE REQUEST FORM**

**Document ID:** BNX-CR-[YYYY]-[NNN]
**Date Submitted:** ___________________

**Section 1: Change Description**

| Field | Value |
|-------|-------|
| Change Title | |
| Requested By | |
| System Component Affected | BioNexus SaaS Platform [ ] / BioNexus Box Firmware [ ] / GCP Infrastructure [ ] / Configuration Only [ ] |
| Change Category | Major [ ] / Minor [ ] / Emergency [ ] |
| Planned Implementation Date | |
| Software Version (current) | |
| Software Version (proposed) | |

**Description of Change:**

**Reason for Change / Business Justification:**

---

**Section 2: GxP Impact Assessment**

**Does this change affect any GxP-critical function?** Yes [ ] / No [ ]

| GxP Function | Affected? | Notes |
|-------------|----------|-------|
| Audit Trail (creation, chaining, immutability) | Y [ ] N [ ] | |
| RBAC / Permission Enforcement | Y [ ] N [ ] | |
| Electronic Signature / Certification | Y [ ] N [ ] | |
| Data Integrity (SHA-256 hashing) | Y [ ] N [ ] | |
| Authentication / Access Control | Y [ ] N [ ] | |
| Multi-Tenant Isolation | Y [ ] N [ ] | |
| BioNexus Box Data Capture | Y [ ] N [ ] | |
| Audit Export / Chain Verification | Y [ ] N [ ] | |

**Validation Impact:**

**Required Testing:**
- [ ] IQ re-verification (which tests): ____________________
- [ ] OQ re-testing (which tests): ____________________
- [ ] PQ re-testing (which tests): ____________________
- [ ] No qualification testing required (rationale): ____________________

---

**Section 3: Approvals**

| Role | Approval | Signature | Date |
|------|----------|-----------|------|
| QA Manager | Approve [ ] / Reject [ ] / Defer [ ] | | |
| System Owner | Approve [ ] / Reject [ ] / Defer [ ] | | |
| Validation Sponsor *(Major changes only)* | Approve [ ] / Reject [ ] / Defer [ ] | | |

**Change Reference (Jira/GitHub issue or equivalent):** ___________________

---

### Appendix E: Glossary

| Term | Definition |
|------|------------|
| **ALCOA+** | Data integrity principle: Attributable, Legible, Contemporaneous, Original, Accurate; extended by Complete, Consistent, Enduring, Available |
| **Audit Trail** | Secure, computer-generated, time-stamped record that allows reconstruction of the course of events relating to the creation, modification, or deletion of an electronic record |
| **BioNexus Box** | Proprietary hardware gateway device that connects laboratory instruments (RS232/USB) to the BioNexus cloud platform |
| **CAPA** | Corrective Action and Preventive Action |
| **CSV** | Computerized System Validation |
| **DS** | Design Specification — describes how the system is built |
| **Electronic Record** | Any combination of text, graphics, data, audio, pictorial, or other information representation created, modified, maintained, archived, retrieved, or distributed by a computer system |
| **Electronic Signature** | Computer data compilation of any symbol or series of symbols executed, adopted, or authorized by an individual to be the legally binding equivalent of the individual's handwritten signature |
| **FS** | Functional Specification — describes what the system does |
| **FMEA** | Failure Mode and Effects Analysis |
| **GAMP5** | Good Automated Manufacturing Practice, 5th edition (ISPE) — industry standard for computerized system validation in regulated environments |
| **GCP** | Google Cloud Platform |
| **GxP** | Collective term for Good Manufacturing Practice (GMP), Good Laboratory Practice (GLP), Good Clinical Practice (GCP) |
| **ICH Q9** | International Council for Harmonisation guidance on Quality Risk Management |
| **IQ** | Installation Qualification — documents that the system has been correctly installed |
| **JWT** | JSON Web Token — compact, self-contained means for securely transmitting authentication information |
| **mTLS** | Mutual TLS — both client and server authenticate each other via certificates |
| **OQ** | Operational Qualification — documents that the system operates as intended |
| **PQ** | Performance Qualification — documents that the system consistently performs within specification in real-world conditions |
| **RBAC** | Role-Based Access Control |
| **RPN** | Risk Priority Number = Severity × Occurrence × Detectability |
| **SHA-256** | Secure Hash Algorithm (256-bit) — cryptographic hash function used for data integrity verification |
| **SVP** | System Validation Plan (this document) |
| **URS** | User Requirements Specification — describes what the user needs the system to do |
| **V-Model** | Validation lifecycle model linking specification documents to corresponding qualification activities |
| **WAL** | Write-Ahead Log — SQLite journaling mode that provides data integrity on power loss |
| **21 CFR Part 11** | FDA regulation governing electronic records and electronic signatures in regulated industries |
| **EU Annex 11** | European GMP Annex 11 — guidance on computerized systems in pharmaceutical manufacturing |

---

*End of Document*

---

**Document Control Footer**

| Attribute | Value |
|-----------|-------|
| Document ID | BNX-VAL-001 |
| Title | System Validation Plan — BioNexus Platform |
| Version | 1.0 |
| Status | Approved |
| Date | 2026-02-28 |
| Classification | Quality & Regulatory Affairs — Restricted Distribution |
| Owner | BioNexus Regulatory Affairs Team |
| CSV Partner | GMP4U (Johannes Eberhardt) |
| Next Review Date | 2027-02-28 |

*This document is controlled under the BioNexus Document Management System. Printed copies are uncontrolled. Always verify against the current electronic version before use.*
