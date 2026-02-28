# Data Retention, Backup & Disaster Recovery Policy
## BioNexus Platform — GxP Data Governance Reference

---

**Document ID:** BNX-DR-001
**Version:** 1.0
**Status:** Approved for Distribution
**Effective Date:** 2026-02-28
**Review Due Date:** 2027-02-28
**Prepared by:** BioNexus Engineering & Quality Team
**Review Partner:** GMP4U (Johannes Eberhardt) — CSV/Qualification Specialist
**Classification:** Regulatory Affairs — Restricted Distribution

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Regulatory Requirements](#2-regulatory-requirements)
3. [Data Classification](#3-data-classification)
4. [Retention Schedule](#4-retention-schedule)
5. [Data Lifecycle Management](#5-data-lifecycle-management)
6. [Backup Strategy](#6-backup-strategy)
7. [Recovery Point Objectives (RPO)](#7-recovery-point-objectives-rpo)
8. [Recovery Time Objectives (RTO)](#8-recovery-time-objectives-rto)
9. [Disaster Recovery Procedures](#9-disaster-recovery-procedures)
10. [Business Continuity](#10-business-continuity)
11. [BioNexus Box Resilience](#11-bionexus-box-resilience)
12. [Testing and Validation](#12-testing-and-validation)
13. [Data Destruction](#13-data-destruction)
14. [Roles and Responsibilities](#14-roles-and-responsibilities)
15. [Policy Review and Change Management](#15-policy-review-and-change-management)
16. [Document Control and Revision History](#16-document-control-and-revision-history)

---

## 1. Purpose and Scope

### 1.1 Purpose

This policy establishes the data retention schedules, backup procedures, and disaster recovery (DR) requirements for the BioNexus platform. It defines binding obligations for BioNexus Engineering and Operations in managing data through its complete lifecycle — from creation through active use, archival, and destruction — in a manner that satisfies applicable regulatory requirements and protects the interests of regulated-industry customers.

The policy also defines formal Recovery Point Objectives (RPO) and Recovery Time Objectives (RTO) by failure scenario, and provides step-by-step operational runbooks for each defined disaster recovery scenario.

### 1.2 Scope

This policy applies to:

| Scope Item | Description |
|---|---|
| **Systems covered** | BioNexus Cloud Platform (GCP: Cloud Run, Cloud SQL PostgreSQL 15, Cloud Storage, Secret Manager); BioNexus Box hardware gateway device; BioNexus CI/CD pipeline (GitHub Actions, Cloud Build, Artifact Registry) |
| **Data covered** | All data generated, processed, stored, or transmitted by the BioNexus platform, including raw instrument files, parsed data records, audit trail logs, certified reports, user and tenant records, and system configuration data |
| **Environments** | Production (`bionexus-prod`, `europe-west3`); Disaster Recovery (`europe-west4`); Staging (`bionexus-staging`) |
| **Personnel** | BioNexus Engineering team, DevOps/SRE function, Quality Assurance, and all third-party sub-processors with access to BioNexus production systems |
| **Customers** | All tenants operating under regulated conditions, including pharmaceutical and biotechnology customers subject to 21 CFR Part 11, EU GMP Annex 11, and GDPR |

### 1.3 Exclusions

This policy does not govern:

- Customer-side data copies or exports that customers retain on their own infrastructure.
- Development or local developer environments (not containing production data).
- Staging environment data where no production or patient-adjacent data has been introduced.

---

## 2. Regulatory Requirements

### 2.1 21 CFR Part 11 (FDA — Electronic Records and Electronic Signatures)

21 CFR Part 11 applies to electronic records created, modified, maintained, archived, retrieved, or transmitted under FDA regulations (21 CFR Parts 210, 211, 820, and others). For BioNexus customers subject to cGMP:

| Requirement | Regulatory Reference | Implication for BioNexus |
|---|---|---|
| Records must be protected to enable accurate and ready retrieval throughout the retention period | §11.10(c) | All data retained in actively restorable form for the full applicable retention period; no format degradation over time |
| Audit trails must be computer-generated and time-stamped | §11.10(e) | `AuditLog` records must be retained and restorable; SHA-256 chain integrity must survive backup and restoration |
| Copies of records must be produced in human-readable and electronic form on request | §11.10(b) | Certified reports (PDF and JSON) and audit exports must remain retrievable throughout the retention period |
| Electronic records subject to inspection must be available to FDA | §11.10(e), §211.180(e) | GxP data must be accessible during an inspection period that extends beyond primary retention |

**FDA-relevant retention obligations under 21 CFR Part 211 (cGMP for finished pharmaceuticals):**

| Record Type | Minimum Retention Period | Regulatory Basis |
|---|---|---|
| Batch production and control records | 1 year after expiry date of batch, or minimum 3 years after release | 21 CFR §211.180(a) |
| Laboratory records | Same as above | 21 CFR §211.180(b) |
| Complaint files | 1 year after expiry, or 3 years after distribution | 21 CFR §211.198(b) |
| System audit trails | Life of the product + 1 year (industry practice aligns with batch records) | §11.10(e) + §211.180 |

In practice, most BioNexus customers in pharma SMBs retain GxP electronic records for **15 years** to cover long-shelf-life products plus safety margins, aligning with the longest product lifecycle + 1 year rule.

### 2.2 EU GMP Annex 11 (EMA — Computerised Systems)

EU GMP Annex 11 governs computerised systems used in GMP-regulated activities within the EU. Relevant retention and continuity provisions:

| Annex 11 Ref | Requirement | BioNexus Obligation |
|---|---|---|
| §7.1 | Data should be secured against deliberate or accidental deletion or modification | GCS object versioning, Cloud SQL deletion protection, immutable `AuditLog` model |
| §7.2 | Data should be regularly backed up | Daily automated Cloud SQL backups, continuous PITR, GCS versioning |
| §11 (Periodic evaluation) | Systems should be periodically evaluated to confirm validated state | DR drills, backup restoration tests, integrity verification — all documented |
| §16 (Business continuity) | Availability of alternative arrangements for systems not available | BioNexus Box local buffer (8 hours), cloud DR plan, manual fallback procedures |
| §17 (Archiving) | Data archived to alternative media must have evidence of validation | Lifecycle-tiered GCS storage, integrity re-verification on restoration |

**EU GMP retention expectations (Annex 11 + EudraLex Volume 4):**

| Record Type | Minimum Retention | Regulatory Basis |
|---|---|---|
| Batch records (EU) | 1 year post-expiry or 5 years post-batch release (whichever is longer) | EudraLex Vol. 4, Annex 11 §17 + Chapter 4 |
| QC laboratory data | 5 years after batch release | EudraLex Vol. 4, Chapter 6 |
| Audit trail data | For the lifetime of records to which it relates | Annex 11 §9 |
| GMP documentation generally | Minimum 5 years; clinical-grade product 15 years | EudraLex Vol. 4, Chapter 4.12 |

### 2.3 GDPR (EU General Data Protection Regulation — 2016/679)

GDPR applies to personal data of EU data subjects processed by BioNexus in the course of providing its service. BioNexus enforces a **no-PII policy for instrument and sample data** — sample identifiers are pseudonymised codes, not patient identifiers. However, user account data (name, email, role) constitutes personal data.

| GDPR Requirement | Article | BioNexus Obligation |
|---|---|---|
| Personal data must not be kept longer than necessary for the purpose | Art. 5(1)(e) — Storage limitation | User accounts must be reviewed and deprovisioned upon termination; data destruction schedule applies to personal data |
| Right to erasure ("right to be forgotten") | Art. 17 | Erasure of user personal data from non-GxP records where no retention obligation applies; GxP records containing user attribution cannot be erased where regulatory retention obligations override (see Section 13.4) |
| Data must be processed with appropriate security | Art. 5(1)(f), Art. 32 | Encryption at rest (AES-256, GCP-managed), encryption in transit (TLS 1.2+), access controls, pseudonymisation |
| Data subject access requests | Art. 15 | BioNexus can export all personal data associated with a user on request |
| Breach notification | Art. 33 | Breach notification to supervisory authority within 72 hours of awareness |

### 2.4 GAMP5 — Data Lifecycle Management

GAMP5 (2nd Edition, 2022) guidance on data governance reinforces that GxP computerised systems must manage data with documented lifecycle controls from creation through to disposal. Key obligations from the GAMP5 data lifecycle perspective:

- Retention periods must be based on regulatory requirements plus risk assessment.
- Archive media must be validated for readability over the full retention period.
- Data destroyed must be done in a controlled, documented manner.
- Business continuity procedures must be in place and tested.

### 2.5 Industry Best Practice Summary

| Standard / Guidance | Minimum GxP Audit Log Retention | Raw Instrument Data | Certified Reports |
|---|---|---|---|
| 21 CFR Part 11 + Part 211 (FDA) | Product lifecycle + 1 year (min. 3 years; effectively 15 years for long-shelf-life products) | 10 years minimum | 15 years |
| EU Annex 11 + EudraLex Vol. 4 | Lifetime of records they pertain to (effectively 15 years) | 5–15 years | 15 years |
| WHO TRS 996 Annex 5 | Lifetime of the product | Lifetime of the product | Lifetime of the product |
| ISPE GAMP5 | Risk-based, but not less than regulatory minimum | Risk-based | Risk-based |
| **BioNexus Policy (conservative)** | **15 years** | **10 years** | **15 years** |

BioNexus adopts the most conservative applicable standard as the floor for all retention periods to ensure global customer compliance.

---

## 3. Data Classification

All data processed or stored by BioNexus is classified into one of four tiers based on its regulatory significance, sensitivity, and the consequences of loss or corruption.

### 3.1 Classification Tiers

| Classification | Definition | Integrity Requirement | Availability Requirement | Example Data |
|---|---|---|---|---|
| **Critical GxP** | Data whose loss, corruption, or inaccessibility would constitute a regulatory violation, endanger product quality, or invalidate an electronic record under 21 CFR Part 11 or EU Annex 11 | Immutable; SHA-256 chain integrity; cryptographic audit trail | Must survive full regional outage; restorable within RTO | Audit trail (`AuditLog`), certified reports (`CertifiedReport`), raw instrument files (`RawFile`) with file hash |
| **Operational GxP** | Data that supports GxP processes but is not itself a regulatory record; corruption or loss would disrupt operations and require investigation | Must be restorable to last backup; point-in-time recovery capability required | Must be restorable within RTO for operational continuity | Parsed data records (`ParsedData`), sample records (`Sample`), instrument registration records, tenant configuration |
| **System** | Infrastructure and configuration data whose loss would impair the ability to operate or recover the platform | Must be version-controlled and restorable | Must be available for DR reconstruction | Terraform state, Docker images, Secret Manager secrets (references), CI/CD configuration, Cloud Logging data |
| **Transient** | Data that is temporary by design and has no long-term retention requirement | Not required to survive system restarts | Recreatable on demand | JWT tokens, OTP codes, Cloud Tasks queue messages, Cloud Run container memory state |

### 3.2 Data Inventory by Classification

| Data Type | Storage System | Classification | Sensitivity |
|---|---|---|---|
| `AuditLog` records (SHA-256 chain) | Cloud SQL (PostgreSQL) | Critical GxP | High |
| `CertifiedReport` (certified records + PDF) | Cloud SQL + GCS (`bionexus-audit-exports-prod`) | Critical GxP | High |
| `RawFile` (binary instrument data + SHA-256 hash) | Cloud SQL (metadata) + GCS (`bionexus-raw-data-prod`) | Critical GxP | High |
| `ParsedData` (parsed JSON, corrections) | Cloud SQL | Operational GxP | Medium |
| `Sample` and `Protocol` records | Cloud SQL | Operational GxP | Medium |
| `User`, `Role`, `Permission` records | Cloud SQL | Operational GxP + Personal Data (GDPR) | High |
| `Tenant` configuration | Cloud SQL | Operational GxP | Medium |
| `OTP` records (hashed, time-limited) | Cloud SQL | Transient | Low |
| Active JWT tokens (in-memory) | Cloud Run instance memory | Transient | Low |
| Cloud SQL transaction logs (PITR) | Cloud SQL managed backups | System | High |
| Cloud SQL automated backups (daily) | Cloud SQL managed backups | System | High |
| GCS audit log export sink | Cloud Logging (`bionexus-audit-logs` bucket) | Critical GxP | High |
| Application logs (Django structured JSON) | Cloud Logging | System | Medium |
| Terraform state | GCS (`bionexus-terraform-state`) | System | High |
| Docker container images | GCP Artifact Registry | System | Medium |
| Secret Manager secrets (values) | GCP Secret Manager | System | Critical |
| BioNexus Box local SQLite buffer | BioNexus Box device (local storage) | Critical GxP (pending sync) | High |
| BioNexus Box firmware and configuration | BioNexus Box device (flash storage) | System | Medium |

---

## 4. Retention Schedule

All retention periods are calculated from the **date of record creation** unless otherwise specified. Where multiple regulatory requirements apply, the most conservative (longest) period governs.

### 4.1 Master Retention Schedule

| Data Type | Classification | Retention Period | Justification | Primary Storage | Archive Storage | Deletion Mechanism |
|---|---|---|---|---|---|---|
| **AuditLog records** | Critical GxP | **15 years** | 21 CFR §211.180 + EU Annex 11 §9: retention for lifetime of records to which they pertain; product lifecycle + 1 year (conservative floor 15 years) | Cloud SQL (PostgreSQL) — active | Cloud Logging dedicated audit bucket (7 years); Cloud SQL PITR (7 days rolling) | Soft delete only; hard delete prohibited |
| **CertifiedReport (record + metadata)** | Critical GxP | **15 years** | 21 CFR §211.180; EU GMP Vol. 4 Chapter 4.12; WHO TRS 996 — certified records must be available for product lifetime | Cloud SQL (PostgreSQL) | GCS `bionexus-audit-exports-prod` (NEARLINE after 1 year, COLDLINE after 5 years) | No deletion permitted during retention; locked GCS retention policy |
| **CertifiedReport PDF files** | Critical GxP | **15 years** | Same as above; PDF is the human-readable form of the electronic record per §11.10(b) | GCS `bionexus-audit-exports-prod` | Same bucket, COLDLINE storage class | GCS locked retention policy (WORM) |
| **RawFile binary content** | Critical GxP | **10 years** | 21 CFR §211.180; ALCOA+ Original principle: first record must be preserved; instrument raw data supports retrospective investigation | GCS `bionexus-raw-data-prod` | GCS object lifecycle → NEARLINE at 1 year, COLDLINE at 5 years | GCS retention policy enforced; deletion only after 10-year period expires |
| **RawFile SHA-256 hash metadata** | Critical GxP | **15 years** | Hash metadata required to verify integrity of archived raw files throughout their retention period; must outlive the raw file itself | Cloud SQL (PostgreSQL) | As part of Cloud SQL backups | Soft delete only |
| **ParsedData records** | Operational GxP | **10 years** | Supports investigation of certified reports; provides context for correction history | Cloud SQL (PostgreSQL) | Cloud SQL PITR + daily backups | Soft delete (`is_deleted=True`); no hard delete during retention |
| **CorrectionTracker records** | Critical GxP | **15 years** | Correction history is an integral part of the audit trail per EU Annex 11 §9 and 21 CFR §11.10(e); records all human interventions in AI-extracted data | Cloud SQL (PostgreSQL) | Cloud SQL backups | Soft delete only; no hard delete |
| **Sample records** | Operational GxP | **10 years** | Supports traceability of certified data back to source sample | Cloud SQL (PostgreSQL) | Cloud SQL backups | Soft delete; no hard delete during retention |
| **Instrument registration records** | Operational GxP | **10 years** | Instrument identity required for audit trail context throughout product lifecycle | Cloud SQL (PostgreSQL) | Cloud SQL backups | Soft delete; no hard delete during retention |
| **User account records (personal data)** | Operational GxP + GDPR | **Tenure + 3 years** (GxP attribution requirement) or until GDPR erasure if no GxP obligation applies | User identity must be retained as long as audit trail records referencing that user are in retention; `user_id` and `user_email` in `AuditLog` constitute attribution data | Cloud SQL (PostgreSQL) | Cloud SQL backups | See Section 13.4 — GDPR vs. GxP conflict resolution |
| **Tenant configuration records** | Operational GxP | **Tenure + 3 years** | Required to interpret audit records in context of that tenant's configuration at time of record | Cloud SQL (PostgreSQL) | Cloud SQL backups | Hard delete only after 3-year post-offboarding period |
| **OTP records** | Transient | **30 days after use** | Short-term retention allows forensic investigation of suspicious authentication events; no ongoing compliance requirement | Cloud SQL (PostgreSQL) | None | Django management command: delete used OTPs older than 30 days |
| **JWT tokens (refresh, revoked)** | Transient | **90 days after expiry** | Token revocation list supports security investigation; no compliance requirement beyond that | Cloud SQL (if blacklisted) | None | Automated cleanup task |
| **Cloud SQL automated backups** | System | **7 days (rolling)** | PITR coverage window; aligned with DR RPO targets | Cloud SQL managed backup storage | N/A | Auto-deleted by Cloud SQL service |
| **Cloud SQL PITR transaction logs** | System | **7 days (rolling)** | Supports point-in-time recovery within the DR RPO window | Cloud SQL managed backup storage | N/A | Auto-deleted by Cloud SQL service |
| **Cloud Audit Logs (GCP Admin Activity)** | System | **400 days** (GCP default; extended per Section 6) | Supports supplier assessment and security investigations; EU Annex 11 §3 cloud infrastructure auditability | Cloud Logging `_Default` bucket | Dedicated `bionexus-audit-logs` log bucket (7 years for Django audit logger) | Auto-deleted per bucket retention configuration |
| **Application logs (Django INFO/WARNING)** | System | **365 days** | Incident investigation; operational troubleshooting | Cloud Logging `_Default` bucket | None | Auto-deleted per bucket retention configuration |
| **Bionexus audit logs (Django `bionexus.audit` logger)** | Critical GxP | **7 years** | Secondary copy of GxP audit events in immutable Cloud Logging sink; supports auditor read-only access via Cloud Logging | Cloud Logging `bionexus-audit-logs` bucket (europe-west3) | N/A (immutable sink) | Automatic per 2555-day bucket retention |
| **Docker container images** | System | **90 days or 30 most recent tags** | Supports rollback and forensic investigation of deployed versions | GCP Artifact Registry (`europe-west3`) | None | Artifact Registry lifecycle policy |
| **Terraform state files** | System | **Indefinite** (infrastructure lifecycle) | Required to manage infrastructure; deletion of state without associated infrastructure destruction causes unmanaged resources | GCS `bionexus-backups-prod` (dual-region `eur4`) | N/A | Manual deletion only, after infrastructure retirement |
| **Secret Manager secret versions** | System | **90 days after rotation** (disabled versions) | Supports rollback after problematic rotation; brief window for investigation | GCP Secret Manager | N/A | Manual deletion after 90-day hold |
| **BioNexus Box local SQLite buffer** | Critical GxP (transient) | **Until confirmed sync to cloud + 30 days** | Local buffer data is the authoritative source until cloud acknowledgment is received; 30-day hold allows reconciliation | BioNexus Box local storage (SQLite) | None | Automated purge after cloud sync acknowledgment + 30 days |
| **BioNexus Box sync reconciliation logs** | Operational GxP | **1 year** | Supports investigation of data gaps or sync failures | Cloud SQL (ingestion audit records) | Cloud SQL backups | Soft delete |
| **CI/CD build logs (Cloud Build)** | System | **365 days** | Supports change control audit trail; evidences deployment steps for GxP change management | Cloud Logging (Cloud Build logs) | None | Auto-deleted per log retention policy |

### 4.2 Retention Period Summary

| Classification | Shortest Retention | Standard Retention | Longest Retention |
|---|---|---|---|
| Critical GxP | 7 years (log sink secondary copy) | 10 years (raw files) | 15 years (audit trail, certified reports) |
| Operational GxP | 10 years | 10 years | 15 years (user attribution records) |
| System | 7 days (rolling PITR) | 365 days | Indefinite (Terraform state) |
| Transient | 30 days | 90 days | Not retained beyond defined period |

---

## 5. Data Lifecycle Management

### 5.1 Lifecycle Stages

All BioNexus data passes through defined lifecycle stages. The stage governs storage tier, access controls, and applicable controls.

```
CREATION
    │
    ▼
ACTIVE USE          Storage: Cloud SQL STANDARD / GCS STANDARD
    │               Access: Full read/write per RBAC
    │               Integrity: SHA-256 monitored continuously
    │
    ▼ (after 1 year)
NEAR-LINE ARCHIVE   Storage: GCS NEARLINE (raw data files, audit exports)
    │               Access: Read-only via audit:view permission
    │               Cost: ~40% reduction vs. STANDARD
    │
    ▼ (after 5 years)
COLD ARCHIVE        Storage: GCS COLDLINE
    │               Access: Requires break-glass request; retrieval latency accepted
    │               Cost: ~80% reduction vs. STANDARD
    │
    ▼ (at retention period end)
DESTRUCTION         Secure deletion per Section 13
                    Documented in destruction register
```

### 5.2 Active Use Phase

| Activity | Description | Controls |
|---|---|---|
| Record creation | Data written to Cloud SQL and/or GCS with SHA-256 hash; `AuditLog` record created | `AuditTrail.record()` enforces `user_id` and `timestamp`; hash computed on write |
| Read/Query | Accessed via authenticated API endpoints with RBAC enforcement | All queries filtered by `tenant_id`; access logged |
| Modification | Restricted per data classification; GxP records support only append or soft-delete | `AuditLog` captures `snapshot_before` and `snapshot_after`; immutable records reject `UPDATE` via PostgreSQL RLS |
| Monitoring | Chain integrity check runs continuously; custom metric `bionexus/audit_chain_intact` reported to Cloud Monitoring | `GET /api/integrity/check/` endpoint; Cloud Scheduler nightly sweep |

### 5.3 Archival Phase

Data transitions to archival storage automatically via GCS lifecycle rules (configured in Terraform). Archival does not change the logical record in Cloud SQL — it affects only the GCS object storage tier for file objects.

| Trigger | GCS Action | Effect on Access |
|---|---|---|
| Raw data file age >= 365 days | SetStorageClass to NEARLINE | Read access unchanged; retrieval latency negligible (milliseconds); write latency unchanged |
| Raw data file age >= 1825 days (5 years) | SetStorageClass to COLDLINE | Read access unchanged; no minimum storage duration penalty after 90 days |
| Raw data file age >= 3650 days (10 years) | Manual review + deletion per destruction process | Require destruction authorisation (Section 13) |

Cloud SQL data does not move to a different storage tier automatically — it remains on SSD storage in the production instance. For long-term historical data beyond the active window, a periodic export to GCS Coldline via `pg_dump` may be performed as an additional archival copy (see Section 6.5).

### 5.4 Destruction Phase

Data destruction is governed by Section 13 of this policy. Destruction occurs only after:

1. Retention period has been confirmed as expired against the creation date.
2. A second independent reviewer has confirmed no ongoing regulatory hold or litigation hold applies.
3. Destruction is authorised by the Data Governance Owner.
4. Destruction is logged in the destruction register (Section 13.5).

---

## 6. Backup Strategy

### 6.1 Backup Overview

BioNexus employs a layered backup strategy covering all Critical GxP and System data. Backups are maintained across multiple geographic locations within the EU to ensure data residency compliance.

| Backup Layer | Technology | Frequency | Scope | Location |
|---|---|---|---|---|
| **Automated database backup** | Cloud SQL managed backups | Daily at 03:00 UTC | Full PostgreSQL instance snapshot | `europe-west3` |
| **Point-in-time recovery (PITR)** | Cloud SQL transaction log streaming | Continuous (near-real-time) | All committed transactions | `europe-west3` |
| **Cross-region DR replica** | Cloud SQL read replica (asynchronous) | Near-real-time (< 1 minute lag typical) | Full database replication | `europe-west4` |
| **GCS object versioning** | GCS native versioning | On every object write | All GCS bucket objects (`bionexus-raw-data-prod`, `bionexus-audit-exports-prod`) | `europe-west3` |
| **GCS dual-region backups** | GCS `eur4` dual-region bucket | Near-real-time (GCS replication) | Terraform state, manual DB dumps | `europe-west3` + `europe-west4` |
| **Cloud Logging archival** | Log sink to `bionexus-audit-logs` bucket | Real-time log streaming | `bionexus.audit` Django logger events | `europe-west3` |
| **Application container images** | Artifact Registry | On every CI/CD build | Immutable Docker image tags | `europe-west3` |

### 6.2 Cloud SQL Automated Backups

Cloud SQL automated backups are configured with the following parameters:

| Parameter | Value | Rationale |
|---|---|---|
| Backup start time | 03:00 UTC | Off-peak for EU lab operations; minimises impact on active users |
| Backup frequency | Daily (1 backup per day) | Satisfies RPO for T4 (data corruption) scenario; regulatory minimum for GxP systems |
| Retained backups | 7 | Provides 7-day recovery window; aligns with 7-day PITR window |
| PITR transaction log retention | 7 days | Enables recovery to any point within 7 days; supports the RPO ≤ 24 hours target for T4 |
| Backup location | `europe-west3` | EU data residency maintained |
| Deletion protection | Enabled (`deletion_protection = true` in Terraform) | Prevents accidental instance deletion; requires Terraform state modification to remove |
| SSL enforcement | `ENCRYPTED_ONLY` | Backup data transfers are encrypted in transit |

**Terraform configuration (extract):**

```hcl
backup_configuration {
  enabled                        = true
  start_time                     = "03:00"
  point_in_time_recovery_enabled = true
  transaction_log_retention_days = 7
  backup_retention_settings {
    retained_backups = 7
    retention_unit   = "COUNT"
  }
}
```

### 6.3 GCS Object Versioning

Object versioning is enabled on all production GCS buckets. Versioning ensures that overwriting or deleting an object retains the previous version, satisfying EU Annex 11 §7.1 (data protected against accidental deletion or modification).

| Bucket | Versioning | Retention Policy | Retention Lock Status |
|---|---|---|---|
| `bionexus-raw-data-prod` | Enabled | 5 years (157,680,000 seconds) — current configuration; policy review target is 10 years | Locked after validation completion |
| `bionexus-audit-exports-prod` | Enabled | 7 years (220,752,000 seconds) — current configuration; policy review target is 15 years | Locked after validation completion |
| `bionexus-backups-prod` | Enabled | 365 days, then auto-delete | Not locked (system data) |

> **Action Required:** The `bionexus-raw-data-prod` retention policy must be updated from 5 years to **10 years** (315,360,000 seconds) and the `bionexus-audit-exports-prod` from 7 years to **15 years** (473,040,000 seconds) in Terraform, and the policies must be locked (`is_locked = true`) following successful production validation. This is a Terraform change control item. See Section 15.3 for change triggers.

**Lifecycle tiers for raw data files:**

| Age Threshold | Action | Storage Class | Monthly Cost per TB |
|---|---|---|---|
| 0–365 days | Active | STANDARD | ~$20 |
| 365–1825 days (1–5 years) | SetStorageClass | NEARLINE | ~$10 |
| 1825+ days (5+ years) | SetStorageClass | COLDLINE | ~$4 |

### 6.4 Cross-Region Replication

The Cloud SQL DR replica in `europe-west4` (Netherlands) replicates all committed transactions from the primary instance in `europe-west3` (Frankfurt). This provides:

- **Near-real-time failover capability**: The replica typically lags primary by less than 1 minute under normal load.
- **EU data residency maintained**: Both regions are within the EU; GDPR and EU Annex 11 data sovereignty is not compromised.
- **Manual promotion only**: The replica is configured with `failover_target = false`. Automatic promotion is disabled to protect the audit trail — automatic promotion in a GxP context requires a human decision to ensure the replica state is confirmed before it becomes authoritative. This is consistent with EU Annex 11 §16 requirements for controlled business continuity procedures.

**Replication lag monitoring:**

```bash
# Monitor replication lag on DR replica
gcloud sql instances describe bionexus-db-prod-replica \
  --format="value(replicaConfiguration.replicaLagMs)"
```

Alert policy: If replication lag exceeds 5 minutes, a Cloud Monitoring alert is triggered and sent to the on-call engineer and DevOps distribution list.

### 6.5 Manual Database Export (Supplementary Archival)

In addition to automated backups, a weekly manual export is performed to the `bionexus-backups-prod` dual-region bucket. This provides a human-verifiable, portable snapshot independent of the Cloud SQL managed backup service:

```bash
# Weekly export (Cloud Scheduler → Cloud Build trigger)
gcloud sql export sql bionexus-db-prod \
  gs://bionexus-backups-prod/db-exports/$(date +%Y-%m-%d)/bionexus-prod.sql.gz \
  --database=bionexus \
  --offload
```

These exports are retained for 365 days per the `bionexus-backups-prod` lifecycle rule.

### 6.6 Backup Integrity Verification

Backup integrity is verified on a defined schedule to confirm that backups are restorable and that the SHA-256 chain survives the backup and restore process.

| Verification Activity | Frequency | Method | Success Criteria | Owner |
|---|---|---|---|---|
| Cloud SQL backup restoration test | Quarterly | Restore most recent backup to a named `bionexus-db-restore-test` instance; run `python manage.py check` and `GET /api/integrity/check/` | `manage.py check` passes with zero issues; chain integrity returns `is_valid: true`; record count matches production | DevOps Lead |
| GCS object versioning verification | Monthly | Retrieve a non-current version of a known raw data file; verify SHA-256 hash matches the stored hash in Cloud SQL | Hashes match; file is readable | DevOps Lead |
| PITR restoration test | Semi-annually | Restore to a specific point in time 24 hours prior to test; verify specific known record exists in correct state | Known record present; state matches expected; audit trail intact | DevOps Lead |
| DR replica promotion simulation | Annually | Full DR drill — see Section 12 | All RTO/RPO targets met; chain integrity confirmed | Engineering Lead + QA |
| Backup encryption verification | Annually | Confirm TLS on backup transport; confirm GCP AES-256 encryption at rest | No plaintext backup observed; GCP compliance documentation confirms encryption | DevOps Lead |

All verification activities must be documented with the date of test, tester identity, test outcome, and any deviations. Documentation is stored in the DR verification log (see Section 12.4).

---

## 7. Recovery Point Objectives (RPO)

The RPO defines the maximum acceptable data loss measured in time. It answers the question: "How much data can we afford to lose?"

### 7.1 RPO by Data Category

| Data Category | RPO | Justification |
|---|---|---|
| **AuditLog (Critical GxP)** | **0 seconds** | Audit records must not be lost. The SHA-256 chain makes any gap immediately detectable. Cloud SQL HA with synchronous replication within `europe-west3` zones guarantees zero data loss for zone failures. For region failure, the cross-region replica lag (typically < 1 minute) defines the practical RPO; any records in-flight during a region failure must be reconciled via BioNexus Box re-sync or manual entry. |
| **CertifiedReport (Critical GxP)** | **0 seconds** | A certified report, once created, is an electronic record under 21 CFR Part 11. Its loss would be a regulatory violation. Cloud SQL HA and GCS dual-write (database + GCS object) provide the zero-RPO guarantee for zone failures. |
| **RawFile (Critical GxP)** | **< 1 hour** | Raw files are uploaded to GCS and the hash recorded in Cloud SQL. A GCS write is acknowledged before the upload is considered complete. The RPO for a region failure is bounded by the Cloud SQL cross-region replication lag (< 1 minute typical; up to 1 hour under degraded conditions). |
| **ParsedData (Operational GxP)** | **< 1 hour** | Parsed data in `PENDING` state can be re-derived from the raw file if lost. Certified data has RPO 0 (covered by CertifiedReport). PITR provides < 1 hour recovery. |
| **Sample and Instrument records (Operational GxP)** | **< 1 hour** | Replicated to DR replica. PITR provides sub-hour recovery. |
| **User accounts and RBAC (Operational GxP)** | **< 1 hour** | As above. PITR provides sub-hour recovery. |
| **System configuration (Terraform state)** | **< 24 hours** | Stored in dual-region GCS bucket. Weekly manual export provides an additional recovery point. Loss of Terraform state does not affect data — it affects infrastructure management capability only. |
| **BioNexus Box local buffer** | **0 seconds** (device-side) | The BioNexus Box local SQLite buffer is the authoritative source of data captured during a cloud outage. The device retains data until cloud sync acknowledgment is received. Data is never deleted from the device before confirmed cloud receipt. |

### 7.2 RPO Tradeoffs

| Scenario | Practical RPO | Explanation |
|---|---|---|
| Zone failure within `europe-west3` | **0** | Cloud SQL HA uses synchronous replication within the region; standby promotes within 60 seconds with zero data loss |
| Full `europe-west3` region failure | **< 1 minute** (typical) / **< 1 hour** (degraded) | Cross-region replica asynchronous replication; lag is typically < 1 minute but can be up to 1 hour under heavy write load |
| Cloud SQL corruption (malicious or software bug) | **< 24 hours** | PITR allows recovery to any second within the past 7 days; practical RPO is up to 24 hours to identify a clean recovery point |
| GCS object deletion or corruption | **0** | GCS object versioning means previous versions are always available; locked retention policy prevents deletion |

---

## 8. Recovery Time Objectives (RTO)

The RTO defines the maximum acceptable time from the moment of a failure event until full service is restored. It answers the question: "How long can we be down?"

### 8.1 RTO by Failure Scenario

| Tier | Failure Scenario | RTO Target | Justification |
|---|---|---|---|
| **T1** | Bad deployment (Cloud Run revision failure) | **< 5 minutes** | Traffic rollback to previous Cloud Run revision via `gcloud run services update-traffic`; no data recovery required; fully automated or one-command manual |
| **T2** | Single availability zone failure within `europe-west3` | **< 10 minutes** | Cloud SQL HA automatic failover (< 60 seconds); Cloud Run continues serving from remaining zones; no manual intervention required |
| **T3** | Full `europe-west3` region outage | **< 4 hours** | Requires manual DR procedure: DR replica promotion (< 15 minutes), Cloud Run deployment in `europe-west4` (< 15 minutes), DNS update propagation (< 5 minutes), validation and smoke testing (< 30 minutes); 4-hour target accounts for human decision-making and coordination |
| **T4** | Cloud SQL data corruption (application bug, ransomware) | **< 8 hours** | Requires isolation, corruption extent assessment (1–2 hours), PITR clone and validation (1–2 hours), application cutover and re-validation (1–2 hours); 8-hour target accounts for GxP-required validation steps before returning to service |
| **T5** | GCS data corruption or accidental mass deletion | **< 4 hours** | Object versioning means rollback is a bucket-level operation; recovery time is dominated by identifying the affected objects and confirming restoration |
| **T6** | Secret Manager unavailability | **< 30 minutes** | Secrets are cached in Cloud Run container environment on startup; running instances continue operating. New instance starts may fail until Secret Manager recovers. Manual injection of secrets to Cloud Run service definition as a break-glass procedure can restore new instance startups. |
| **T7** | BioNexus Box cloud connectivity loss | **N/A (offline-tolerant)** | The BioNexus Box continues operating with local data buffering for up to 8 hours. This is a degraded mode, not a failure scenario. See Section 11. |
| **T8** | Complete platform loss (multi-region, multi-service) | **< 24 hours** | Worst-case scenario: full rebuild in `europe-west4` from backups + container images; 24-hour target accounts for full IaC deployment, data restoration, integrity validation, and GxP documentation of the recovery |

### 8.2 RTO Constraints for GxP Environments

Before returning a recovered system to service in a GxP environment, the following must be confirmed and documented regardless of how quickly the technical recovery is achieved:

| Validation Step | Requirement | Responsible Role |
|---|---|---|
| Chain integrity verification | `GET /api/integrity/check/` returns `is_valid: true` for all tenants | DevOps Lead |
| Record count reconciliation | Post-recovery record counts match pre-failure counts (or discrepancy is documented and root-caused) | DevOps Lead + QA Lead |
| Audit trail gap assessment | Any period of data loss is formally identified, the gap is characterised, and an incident report is raised | QA Lead |
| Customer notification | Affected tenants are notified of the outage, duration, and any data impact | Customer Success Lead |
| Regulatory impact assessment | QA Lead assesses whether the incident requires customer notification for regulatory purposes (e.g., GxP deviation report) | QA Lead |

---

## 9. Disaster Recovery Procedures

The following runbooks define step-by-step procedures for each defined failure scenario. All actions must be logged in the incident management system (e.g., PagerDuty incident) with timestamps and responsible engineer identified for each step.

### 9.1 Tier 1 Runbook: Bad Deployment Rollback (RTO < 5 minutes)

**Trigger conditions:** Smoke test failure after deployment; elevated error rate post-deployment; `GET /api/health/` returning non-200; customer reports of service degradation immediately following a deployment.

**Pre-requisites:** Access to GCP Console or `gcloud` CLI with `roles/run.developer` on `bionexus-prod`.

| Step | Action | Command / Verification |
|---|---|---|
| 1 | Declare incident in PagerDuty. Assign incident commander. | PagerDuty → New Incident → "T1: Bad deployment" |
| 2 | Identify current and previous revision names | `gcloud run revisions list --service=bionexus-api --region=europe-west3 --sort-by="~metadata.creationTimestamp" --limit=5` |
| 3 | Route 100% of traffic to the previous stable revision | `gcloud run services update-traffic bionexus-api --region=europe-west3 --to-revisions=<PREVIOUS_REVISION_NAME>=100` |
| 4 | Verify health endpoint returns 200 | `curl -sf https://api.bionexus.io/api/health/` |
| 5 | Verify no audit trail integrity degradation | `curl -H "Authorization: Bearer <TOKEN>" https://api.bionexus.io/api/integrity/check/` — confirm `is_valid: true` |
| 6 | Confirm with customer success that service is restored | Slack / email notification to Customer Success team |
| 7 | Investigate failed revision. Do not redeploy until root cause is identified and fixed. | Review Cloud Logging for the failed revision; `gcloud logging read 'resource.type="cloud_run_revision"'` |
| 8 | Close incident. Log in DR verification register. | PagerDuty → Resolve; update DR log with date, duration, action taken |

**No data recovery required for T1.** The rollback only changes traffic routing; no database changes occur.

### 9.2 Tier 2 Runbook: Zone Failure (RTO < 10 minutes)

**Trigger conditions:** Cloud Monitoring alerts for Cloud SQL instance unavailability; Cloud Run instances in one zone unable to connect to database.

**This scenario is largely automated.** Cloud SQL HA automatically promotes the standby instance within 60 seconds. The runbook documents the monitoring and confirmation steps.

| Step | Action | Command / Verification |
|---|---|---|
| 1 | Acknowledge PagerDuty alert. Do not attempt manual intervention. | Allow Cloud SQL HA failover to proceed automatically |
| 2 | Monitor failover completion | `gcloud sql operations list --instance=bionexus-db-prod --filter="operationType=FAILOVER"` — wait for `DONE` |
| 3 | Verify database connectivity from Cloud Run | `curl -H "Authorization: Bearer <TOKEN>" https://api.bionexus.io/api/health/` — confirm `db: ok` |
| 4 | Check for any failed requests during failover window | Cloud Logging: `resource.type="cloud_run_revision" AND severity=ERROR AND timestamp >= "<failover_start_time>"` |
| 5 | Verify audit trail integrity post-failover | `GET /api/integrity/check/` — confirm `is_valid: true` |
| 6 | Verify Cloud SQL is now in the secondary zone | `gcloud sql instances describe bionexus-db-prod --format="value(gceZone)"` |
| 7 | Close incident. Document failover event in change control log. | The zone failure event itself must be recorded in the GxP change log as a system event |

**Data loss for T2: Zero.** Cloud SQL HA uses synchronous replication.

### 9.3 Tier 3 Runbook: Full Region Failover to `europe-west4` (RTO < 4 hours)

**Trigger conditions:** GCP Status Dashboard confirms `europe-west3` regional degradation affecting Cloud SQL and/or Cloud Run; BioNexus API has been unreachable for more than 15 minutes from multiple monitor locations; Cloud SQL primary and replica in same region are both unreachable.

**Pre-requisites:** `bionexus-db-prod-replica` is operational in `europe-west4`; Cloud Run image is available in Artifact Registry; pre-provisioned DR load balancer IP exists in `europe-west4`.

| Step | Est. Duration | Action | Command / Verification |
|---|---|---|---|
| 1 | 5 min | Declare major incident. Notify incident commander, engineering lead, QA lead, customer success. Open dedicated incident Slack channel `#incident-<date>`. | PagerDuty → P1 incident; Slack notification to `#engineering-oncall` |
| 2 | 5 min | Confirm `europe-west3` regional failure via GCP Status Dashboard. Do not initiate failover for transient availability issues (< 15 minutes). | https://status.cloud.google.com — confirm status for `europe-west3` |
| 3 | 5 min | Assess DR replica status and replication lag | `gcloud sql instances describe bionexus-db-prod-replica --format="value(state,replicaConfiguration.replicaLagMs)"` — confirm `RUNNABLE` |
| 4 | 10 min | **Promote DR replica to standalone primary** (irreversible action — confirm with engineering lead before executing) | `gcloud sql instances promote-replica bionexus-db-prod-replica` — wait for `DONE` |
| 5 | 5 min | Verify promoted instance is writable and database is intact | `cloud-sql-proxy bionexus-prod:europe-west4:bionexus-db-prod-replica &` then `psql -h localhost -U bionexus -d bionexus -c "SELECT COUNT(*) FROM audit_log;"` |
| 6 | 5 min | Update Secret Manager connection string to point to DR instance | `gcloud secrets versions add bionexus-cloud-sql-connection --data-file=<(echo -n "bionexus-prod:europe-west4:bionexus-db-prod-replica")` |
| 7 | 15 min | Deploy Cloud Run service to `europe-west4` using last known-good image | `gcloud run deploy bionexus-api --image=europe-west3-docker.pkg.dev/bionexus-prod/bionexus/api:latest --region=europe-west4 --set-cloudsql-instances=bionexus-prod:europe-west4:bionexus-db-prod-replica` |
| 8 | 5 min | Verify Cloud Run health in DR region | `curl -sf https://<DR_CLOUD_RUN_URL>/api/health/` — confirm 200 |
| 9 | 5 min | Update Cloud DNS to point `api.bionexus.io` to DR load balancer IP | `gcloud dns record-sets update api.bionexus.io. --type=A --zone=bionexus-zone --rttl=60 --rrdatas=<DR_LB_IP>` |
| 10 | 10 min | Wait for DNS propagation and verify end-to-end from external monitor | `curl -sf https://api.bionexus.io/api/health/` from external monitor |
| 11 | 15 min | **GxP validation: Verify audit trail chain integrity** | `GET /api/integrity/check/` for all active tenants — confirm `is_valid: true` for all |
| 12 | 5 min | Notify customers of degraded operation mode and estimated recovery window | Customer email via customer success; update status page |
| 13 | Ongoing | Monitor DR region operation; maintain incident ticket until primary region recovery | Cloud Monitoring dashboards; custom metrics |
| **Primary region recovery (when `europe-west3` recovers):** | | | |
| 14 | 30 min | Assess data written to DR database since failover | `SELECT COUNT(*), MAX(timestamp) FROM audit_log WHERE timestamp > '<failover_time>'` |
| 15 | 30 min | Re-sync data: export DR delta to `europe-west3` primary candidate | `pg_dump --data-only --table=<table> bionexus | psql -h <primary-candidate> bionexus` — for each affected table |
| 16 | 15 min | Re-verify chain integrity after re-sync | `GET /api/integrity/check/` — confirm `is_valid: true` |
| 17 | 5 min | Update DNS back to primary region load balancer | Reverse of Step 9 |
| 18 | 5 min | Decommission DR Cloud Run service | `gcloud run services delete bionexus-api --region=europe-west4` |
| 19 | 30 min | Post-incident review; update DR runbook if gaps identified | QA Lead drafts incident report; root cause analysis within 5 business days |

### 9.4 Tier 4 Runbook: Data Corruption Recovery (RTO < 8 hours)

**Trigger conditions:** `GET /api/integrity/check/` returns `is_valid: false` with `corrupted_records`; application-layer data validation fails unexpectedly; suspected ransomware or malicious insider; Cloud Monitoring alert for `bionexus/audit_chain_intact = false`.

**Critical principle:** Do not attempt to "repair" corrupted audit trail records. The SHA-256 chain is forensic evidence. Any modification constitutes additional tampering. The correct response is to isolate, recover to a clean point, and document the gap.

| Step | Est. Duration | Action | Command / Verification |
|---|---|---|---|
| 1 | 5 min | Declare security incident. Notify engineering lead, QA lead, and (if external threat suspected) CISO/management. | PagerDuty → P0 incident; notify management chain |
| 2 | 15 min | **Immediately restrict write access to the database.** Move Cloud Run to read-only mode or take it offline to prevent further corruption. | `gcloud run services update bionexus-api --region=europe-west3 --set-env-vars MAINTENANCE_MODE=true` — or take service offline |
| 3 | 30 min | Preserve evidence: export current database state before any recovery action | `gcloud sql export sql bionexus-db-prod gs://bionexus-backups-prod/incident/$(date +%Y%m%d-%H%M)/pre-recovery-snapshot.sql.gz --database=bionexus --offload` |
| 4 | 60 min | Identify corruption extent: which records are corrupted, earliest corrupted timestamp | `GET /api/integrity/check/` — note `corrupted_records` IDs and timestamps; query: `SELECT MIN(timestamp) FROM audit_log WHERE id IN (<corrupted_ids>)` |
| 5 | 15 min | Identify clean recovery point: select PITR timestamp 30 minutes before earliest corruption timestamp | `RECOVERY_TIME = <earliest_corrupted_timestamp> - 30 minutes` |
| 6 | 30 min | Create PITR clone of the production database | `gcloud sql instances clone bionexus-db-prod bionexus-db-recovery --point-in-time="<RECOVERY_TIME>"` |
| 7 | 30 min | Validate recovery instance: check record counts, chain integrity, known data points | `cloud-sql-proxy bionexus-prod:europe-west3:bionexus-db-recovery &` then `GET /api/integrity/check/` against recovery instance |
| 8 | 30 min | Assess data gap: identify all records created/modified between `RECOVERY_TIME` and corruption detection time | Query the original (pre-recovery) snapshot for records in this window that are not corrupted |
| 9 | 60 min | Manual reconciliation: restore valid data from gap period from the pre-recovery snapshot where recoverable; document any irrecoverable records as a GxP data gap | QA Lead must review and authorise each record restoration; each restoration must be logged in the incident record |
| 10 | 30 min | Redirect application to recovery database instance | Update Cloud SQL Auth Proxy connection name; restart Cloud Run instances |
| 11 | 30 min | Re-verify chain integrity end-to-end on restored instance | `GET /api/integrity/check/` — all tenants must return `is_valid: true` |
| 12 | 15 min | Restore service to users | Remove maintenance mode; verify health check |
| 13 | 5 days | Root cause analysis; regulatory assessment; customer notification if data gap affects their GxP records | QA Lead authors incident report; customer notification per GDPR Art. 33 if personal data involved |

### 9.5 Tier 5 Runbook: GCS Object Corruption or Deletion (RTO < 4 hours)

**Trigger conditions:** File hash verification failure (`FileHasher.verify_integrity()` returns `False`); mass deletion of GCS objects detected; GCS retention policy violation alert.

| Step | Est. Duration | Action |
|---|---|---|
| 1 | 5 min | Identify affected objects: list objects with missing or non-current states | `gcloud storage objects list gs://bionexus-raw-data-prod --all-versions --format="table(name,generation,timeCreated,timeDeleted)"` |
| 2 | 15 min | Restore non-current (previous) versions of affected objects | `gcloud storage cp gs://bionexus-raw-data-prod/<object>#<previous_generation> gs://bionexus-raw-data-prod/<object>` |
| 3 | 30 min | Verify restored files against SHA-256 hashes in Cloud SQL | `FileHasher.verify_integrity(raw_file_id)` for each restored file |
| 4 | 30 min | Audit who performed the deletion and from where | Cloud Audit Logs: `resource.type="gcs_bucket" AND protoPayload.methodName="storage.objects.delete"` |
| 5 | 30 min | If locked retention policy was circumvented, treat as a security incident; escalate | Notify security team; preserve all audit evidence |
| 6 | 30 min | Document in incident report; assess regulatory impact | QA Lead: if a certified report's underlying raw file was unrecoverable, this constitutes a GxP data integrity event |

---

## 10. Business Continuity

### 10.1 Impact Assessment

The following table assesses the business and regulatory impact of BioNexus platform downtime on customer laboratory operations.

| Downtime Duration | Operational Impact | Regulatory Impact | Customer Mitigation |
|---|---|---|---|
| **< 1 hour** | BioNexus Box buffers data locally (8-hour capacity). Lab work continues. No new data visible in dashboard. | Minimal; no regulatory record is lost if outage resolves within buffer window. | None required. Automatic sync on recovery. |
| **1–8 hours** | BioNexus Box continues buffering. Dashboard inaccessible. New certifications blocked. Access to historical data blocked. | Moderate; if a certification was urgently required, it must wait. Time-sensitive review cycles may be delayed. | Manual paper-based review fallback (see Section 10.3). |
| **8–24 hours** | BioNexus Box buffer approaches capacity (at 8 hours). Risk of data loss from instruments if buffer fills. Manual intervention required on-site. | High; potential for data loss from instruments. Regulatory investigation required if data is lost. | Manual data collection procedures at lab site; BioNexus Box alert triggers at 80% buffer utilisation. |
| **> 24 hours** | Significant operational disruption. Manual operations fully required for new data. Historical data inaccessible. | Critical; formal deviation report likely required by customer QA. | Full manual fallback (see Section 10.3); BioNexus incident report to customers; potential regulatory reporting obligation for customers. |

### 10.2 Service Level Commitments

| Service | Target Availability | Measurement Period |
|---|---|---|
| BioNexus API (`api.bionexus.io`) | 99.9% (< 8.7 hours downtime per year) | Calendar month |
| BioNexus Dashboard (`app.bionexus.io`) | 99.9% | Calendar month |
| Data ingestion endpoint (`/api/ingestion/`) | 99.95% (< 4.4 hours downtime per year) | Calendar month |
| BioNexus Box local buffer | 100% (device-side; independent of cloud) | N/A |

These commitments are supported by the underlying GCP SLAs:
- Cloud Run: 99.95% monthly uptime SLA
- Cloud SQL (Regional HA): 99.95% monthly uptime SLA
- Cloud Storage: 99.95% monthly uptime SLA

### 10.3 Manual Fallback Procedures

When BioNexus is unavailable and lab operations cannot be suspended, the following manual fallback procedures apply. These are interim procedures only and do not satisfy electronic record requirements — all data collected manually must be entered into BioNexus and subjected to the full audit trail review process when the system is restored.

| Fallback Procedure | Applicability | Steps |
|---|---|---|
| **Manual instrument data collection** | When BioNexus Box buffer is full or device is unavailable | Lab personnel print or save instrument output locally; attach handwritten date/time, operator ID, and instrument ID; retain in designated paper backup log |
| **Manual sample tracking** | When sample tracking module is unavailable | Use pre-printed sample tracking log sheets; capture sample ID, instrument ID, operator, date/time, result (if applicable), and any deviations |
| **Deferred certification** | When certification workflow is unavailable | Delay the certification event; document the reason for delay in a deviation or lab notebook entry; proceed with certification via BioNexus as soon as service is restored |
| **Audit log access for inspection** | When dashboard is unavailable during an inspection | Contact BioNexus support; BioNexus can provide a direct data export from Cloud SQL or Cloud Logging for the inspected period via `bionexus-audit-reader-sa` read-only access |

### 10.4 Communication Plan

The following communication plan applies for any outage affecting production service:

| Outage Duration | Internal Actions | Customer Actions |
|---|---|---|
| **0–15 minutes** | Engineering on-call acknowledges alert; investigates; no external communication required unless user-visible impact confirmed | None |
| **15 minutes – 1 hour** | Engineering lead informed; incident ticket opened; customer success on standby | Status page updated ("Investigating issue with...") |
| **1–4 hours** | Management informed; customer success lead engaged; regular internal updates every 30 minutes | Customer notification email within 30 minutes of confirmed impact; status page updated every 30 minutes |
| **> 4 hours** | Executive escalation; regulatory assessment initiated by QA lead | Individual customer notification for all affected tenants; estimated restoration time; description of data impact (if any) |
| **Post-resolution** | Post-incident review within 5 business days; root cause report | Post-incident summary sent to customers within 3 business days; include root cause, corrective actions, and any data impact |

**Communication channels:**
- Status page: `status.bionexus.io` (maintained by Customer Success)
- Customer email: via customer success distribution list
- Internal: PagerDuty + Slack `#engineering-oncall`

---

## 11. BioNexus Box Resilience

### 11.1 Local Buffer Architecture

The BioNexus Box hardware gateway contains a local SQLite database buffer capable of storing up to 8 hours of instrument data at typical laboratory throughput. The buffer provides continuity of data capture during cloud outages, network interruptions, and scheduled maintenance windows.

| Buffer Characteristic | Value | Notes |
|---|---|---|
| Buffer storage capacity | 8 hours at typical throughput | Actual capacity depends on instrument data volume; alert triggered at 80% capacity |
| Buffer storage technology | SQLite (local flash storage on BioNexus Box) | Not affected by cloud availability |
| Data classification during buffering | Critical GxP (pending sync) | Treated as primary source until cloud acknowledgment received |
| Retry logic | Exponential backoff; maximum retry window 72 hours | After 72 hours without cloud connectivity, alert escalates to customer and BioNexus support |
| Data integrity in buffer | SHA-256 hash computed at capture time | Hash computed on the device before transmission; cloud verifies hash on receipt |
| Buffer overflow behaviour | Alert sent to lab (email/SMS) at 80% capacity; at 100% oldest unsynced records are flagged (not deleted) and manual intervention is required | No silent data loss; overflow is a visible alert condition |

### 11.2 Data Integrity Guarantees

The BioNexus Box maintains the following data integrity guarantees independent of cloud connectivity:

| Guarantee | Mechanism |
|---|---|
| Capture integrity | SHA-256 hash computed at point of RS232/USB capture; hash is part of the buffered record |
| Transmission integrity | mTLS connection with cloud API; data transmitted only over authenticated, encrypted channel |
| No-delete-before-sync | BioNexus Box firmware prohibits deletion of buffered records before receiving a cloud acknowledgment (`HTTP 200` with transaction reference) |
| Ordered delivery | Records transmitted in capture order; cloud API validates sequence; out-of-order records trigger reconciliation |
| Duplicate prevention | Cloud API performs idempotent ingestion; duplicate records (same device ID + timestamp + hash) are silently deduplicated and acknowledged |

### 11.3 Sync Reconciliation After Cloud Outage

When cloud connectivity is restored after an outage, the BioNexus Box initiates a sync reconciliation process:

| Reconciliation Step | Description | Responsible Component |
|---|---|---|
| 1. Queue flush | BioNexus Box transmits all buffered records in capture order via the Cloud Tasks ingestion queue | BioNexus Box firmware |
| 2. Cloud ingestion | Each record is processed via the standard ingestion pipeline: SHA-256 hash verified; `RawFile` created; `AuditLog` record created with original capture timestamp | Cloud API + Cloud Tasks |
| 3. Acknowledgment | Cloud API returns HTTP 200 with `transaction_id` for each successfully ingested record | Cloud API |
| 4. Buffer clear | BioNexus Box marks record as synced; record retained in local buffer for 30 days (minimum) before local deletion | BioNexus Box firmware |
| 5. Reconciliation report | Cloud API generates a sync reconciliation summary: records received, hashes verified, gaps (if any) | Cloud API → audit log |
| 6. Gap detection | If a gap in capture timestamps is detected (e.g., instrument was producing data but BioNexus Box was offline), the system flags the gap in the audit trail; a human must review and authorise the gap record | QA review workflow |

### 11.4 BioNexus Box Failure Scenarios

| Scenario | Data Risk | Mitigation |
|---|---|---|
| BioNexus Box power failure during capture | Records in RAM (not yet written to SQLite) may be lost | Firmware writes to SQLite before acknowledging capture from instrument; RAM-to-disk latency is < 100ms |
| BioNexus Box hardware failure | Records in local SQLite buffer may be inaccessible | Support procedure: replace device; recover SQLite backup from device storage; manually upload to cloud via support portal |
| BioNexus Box firmware corruption | Device may not boot; buffer inaccessible | Hardware replacement; SQLite file can be extracted from flash storage directly if device can be partially booted |
| BioNexus Box network failure (cloud unreachable) | No impact while buffer has capacity | Buffer + retry logic provide 72-hour resilience window |

---

## 12. Testing and Validation

### 12.1 DR Drill Schedule

Disaster recovery capabilities must be tested on a defined schedule. Testing evidence must be retained as part of the system's ongoing validation record (EU Annex 11 §11 — Periodic evaluation).

| Test Activity | Frequency | Scope | Documentation Required |
|---|---|---|---|
| **T1 rollback drill** | Monthly (aligned with production deploy schedule) | Simulate a bad deployment by deploying a known-broken revision; verify rollback completes within RTO | Test report with date, tester, revision IDs, time to rollback, outcome |
| **Cloud SQL backup restoration test** | Quarterly | Restore most recent daily backup to a test instance; run chain integrity check; verify record counts | Restoration test report signed by DevOps Lead |
| **PITR restoration test** | Semi-annually | Restore to a specified point in time 24 hours prior; verify specific known records exist in correct state | PITR test report signed by DevOps Lead |
| **Full DR drill (T3: Region failover)** | Annually | Execute full T3 runbook in a controlled test environment (do not use production data; use staging environment mirroring production architecture) | Full DR drill report; deviations recorded; runbook updated if gaps found; QA sign-off |
| **BioNexus Box offline/sync test** | Quarterly | Simulate cloud outage for 4 hours during a test window; confirm Box buffers correctly; confirm sync reconciliation on restoration | Sync reconciliation report; hash verification outcome |
| **Backup integrity verification** | Monthly | Verify SHA-256 hash of a sample of backed-up GCS objects against Cloud SQL metadata | Verification log with sample set, hash match results, outcome |
| **Encryption verification** | Annually | Confirm all backup transports use TLS; confirm GCP AES-256 at-rest encryption for all data stores | Encryption verification checklist signed by DevOps Lead |
| **Destruction process test** | Annually | Execute test destruction of a designated test tenant's data per Section 13; verify data is removed and destruction is logged | Destruction test report signed by QA Lead |

### 12.2 Test Scenarios and Success Criteria

| Scenario | Test Method | Pass Criteria |
|---|---|---|
| T1: Deployment rollback | Deploy revision with `GET /api/health/` returning 503; execute rollback; measure elapsed time | Health check returns 200 within 5 minutes of rollback initiation; chain integrity returns `is_valid: true` |
| T2: Zone failure | Simulate via Cloud SQL maintenance failover (test window only) | Cloud SQL failover completes within 60 seconds; application reconnects within 2 minutes; zero data loss confirmed |
| T3: Region failover | Execute full T3 runbook in staging environment with production-mirror architecture | All runbook steps complete within 4-hour RTO target; chain integrity confirmed; DNS resolves to DR endpoint |
| T4: Data corruption | Manually corrupt a single `AuditLog` record in a test instance; execute T4 runbook | `integrity/check/` detects corruption; PITR recovery restores to clean state; chain integrity confirms `is_valid: true` post-recovery |
| Backup restoration | Restore previous day's Cloud SQL backup to test instance | Record counts match; chain integrity passes; Django `manage.py check` returns no errors |
| PITR recovery | Restore to 24 hours ago in test instance | Specific known test records present in exact state at recovery point; no records present that were created after recovery point |
| Box sync reconciliation | Disconnect Box from network for 4 hours; reconnect; monitor sync | All buffered records transmitted; all hashes verified; reconciliation report shows zero gaps; buffer correctly cleared |

### 12.3 DR Drill Documentation Requirements

Each DR drill must be documented with the following information:

| Field | Required Information |
|---|---|
| Drill date and time | UTC start and end time |
| Drill type | T1 / T2 / T3 / T4 / Backup restoration / BioNexus Box sync |
| Participants | Name, role, and organisation of all participants |
| Scope | What was tested; what was explicitly out of scope |
| Steps executed | Each runbook step with actual elapsed time and outcome (PASS / FAIL / DEVIATION) |
| Deviations | Any step that did not meet success criteria; root cause and corrective action |
| RTO achieved | Actual time from failure declaration to restored service |
| RPO achieved | Actual data loss (if any) |
| Chain integrity result | Output of `GET /api/integrity/check/` after recovery |
| QA sign-off | QA Lead signature and date |
| Runbook updates | Whether any runbook updates were made as a result; version number |

Documentation is stored in: `docs/dr-drills/<year>/<drill-date>-<drill-type>-report.md` in the BioNexus repository (or equivalent document management system).

### 12.4 DR Verification Register

A DR verification register must be maintained as a single-page summary of all DR testing activities. The register is reviewed at each annual policy review. Template:

| Date | Activity | Tester | RTO Achieved | RPO Achieved | Outcome | Deviations | Corrective Actions |
|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | T1 rollback drill | [Name] | [minutes] | N/A | PASS | None | None |
| YYYY-MM-DD | Backup restoration test | [Name] | [hours] | < 24h | PASS | [describe] | [describe] |
| ... | ... | ... | ... | ... | ... | ... | ... |

---

## 13. Data Destruction

### 13.1 General Destruction Principles

Data destruction must be:

- **Authorised**: Approved by the Data Governance Owner and confirmed by QA Lead before execution.
- **Complete**: All copies, backups, and replicas must be addressed. Destruction of the primary record alone is not sufficient.
- **Verified**: Post-destruction confirmation must be performed to verify the data is no longer retrievable.
- **Documented**: Logged in the destruction register with sufficient detail to demonstrate compliance in a regulatory inspection.
- **Irreversible**: Secure deletion methods must be used (see Section 13.3).

### 13.2 Destruction Triggers

| Trigger | Data Scope | Authority Required |
|---|---|---|
| Retention period expiry | All records of the specific data type for which the retention period has elapsed | Data Governance Owner + QA Lead |
| Tenant offboarding | All non-GxP data for the offboarding tenant; GxP data follows Section 13.4 | Data Governance Owner + QA Lead + Customer authorisation |
| GDPR right to erasure (Art. 17) | Personal data of the requesting data subject where no overriding retention obligation applies | Data Governance Owner; QA Lead confirms no GxP retention conflict |
| Security incident (compromised data) | Data confirmed to be subject to a security breach, where destruction serves data minimisation | CISO / Engineering Lead + Data Governance Owner |
| Regulatory hold release | Data held beyond normal retention due to litigation or regulatory inquiry; destruction authorised when hold is formally released | Legal counsel + Data Governance Owner |

### 13.3 Secure Deletion Methods

| Data Location | Deletion Method | Verification |
|---|---|---|
| **Cloud SQL (PostgreSQL) records** | Hard `DELETE` SQL statement (for data where soft delete has already been applied and retention has expired); followed by `VACUUM` to reclaim storage | Query post-deletion to confirm zero rows returned for deleted IDs |
| **Cloud SQL long-term (retention-expired)** | PostgreSQL `DELETE` + `VACUUM FULL` for tables where bulk historical data is being pruned | Record count pre/post deletion; QA review of deletion scope |
| **GCS objects** | `gcloud storage rm gs://<bucket>/<object>` — only after retention lock has expired or been released per approved process; GCS's server-side deletion uses crypto-erasure (key rotation + object deletion) | Confirm object is no longer listed; confirm deletion in GCS Audit Logs |
| **Cloud Logging log entries** | Log bucket deletion (entire bucket) or log sink reconfiguration; individual log entry deletion is not supported by GCP — retention period expiry triggers automatic deletion | Confirm bucket retention settings; no individual entry deletion capability |
| **Secret Manager** | Destroy secret version: `gcloud secrets versions destroy <VERSION> --secret=<SECRET>` | Confirm version status is `DESTROYED` |
| **Artifact Registry images** | `gcloud artifacts docker images delete` | Confirm image is no longer listed |
| **BioNexus Box local SQLite** | Secure erase of SQLite database file on device; factory reset for device decommissioning | Device factory reset verification procedure |

### 13.4 GDPR Right to Erasure vs. GxP Retention Conflict Resolution

This section governs the specific conflict that arises when a data subject (a BioNexus user) submits a GDPR Art. 17 right to erasure request, but their personal data (user ID, email) appears in GxP-retained audit trail records.

**Resolution framework:**

| Data Location | GDPR Art. 17 Applicability | Disposition |
|---|---|---|
| `AuditLog.user_email` and `user_id` | **Does NOT apply** | Art. 17(3)(b) exempts personal data whose erasure would conflict with legal obligations. GxP retention obligations under 21 CFR Part 11 and EU GMP Annex 11 constitute a legal obligation. The audit trail record cannot be modified — modifying it would break the SHA-256 chain and constitute a regulatory violation. |
| `CertifiedReport.certified_by` (FK to User) | **Does NOT apply** | Same legal basis as above. The certification is an electronic signature record under 21 CFR §11.50; it cannot be modified. |
| `User` account record (login credentials, personal profile) | **Applies with constraints** | The `User` record must be retained as long as any `AuditLog` record references the `user_id`. However, the account can be **deactivated** (`is_active=False`) immediately, preventing future login, while the identity record is retained for the required period. After the retention period of all referencing records expires, the `User` record may be hard-deleted. |
| Marketing or operational communications data (if any) | **Applies without constraint** | Any personal data held for non-regulatory purposes (e.g., customer contact records not embedded in the GxP system) must be erased without delay upon valid Art. 17 request. |

**Response process for Art. 17 requests:**

1. Data Governance Owner confirms receipt within 2 business days.
2. QA Lead reviews audit trail for referencing records and confirms retention status.
3. Response to data subject within 30 days (GDPR statutory deadline):
   - If only non-GxP data exists: confirm erasure of all applicable data.
   - If GxP data exists: explain the legal basis (Art. 17(3)(b)), confirm deactivation of account, confirm erasure of all non-GxP personal data, and provide estimated date when GxP retention will expire.
4. Log the request and response in the data subject request register.

### 13.5 Tenant Offboarding Data Handling

When a BioNexus customer (tenant) terminates their contract, the following data disposition procedure applies:

| Phase | Timeline | Action |
|---|---|---|
| **Offboarding notice** | T+0 (contract termination notice) | Data Governance Owner notified; freeze on new data deletion; customer notified of data export window |
| **Data export window** | T+0 to T+30 days | Customer may request full data export (all `CertifiedReport` PDFs, JSON exports, audit logs); BioNexus provides export package including SHA-256 verification hashes |
| **Non-GxP data deletion** | T+30 days | Soft-delete all non-GxP operational data; delete user accounts (deactivate immediately; hard-delete after Art. 17 analysis); delete tenant configuration |
| **GxP data retention** | T+30 days to retention period expiry | GxP records (`AuditLog`, `CertifiedReport`, `RawFile`, `ParsedData`) retained per Section 4.1 for the applicable retention period, even after contract termination. These records are placed in an isolated, read-only tenant state. Storage costs for retained GxP data are the responsibility of BioNexus (accounted for in service pricing). |
| **Retention expiry** | At individual record retention expiry | Records deleted per Section 13.3; logged in destruction register |
| **Destruction confirmation** | Within 10 business days of last destruction event | Destruction certificate issued to former customer on request |

### 13.6 Destruction Register

A destruction register must be maintained. Each entry must contain:

| Field | Description |
|---|---|
| Record ID | Unique identifier for the destruction event |
| Date of destruction | UTC date and time |
| Data type | Category of data destroyed (e.g., `AuditLog` records, `RawFile` objects) |
| Tenant | Tenant to which the data belonged |
| Record count | Number of records / objects destroyed |
| Date range | Earliest and latest creation date of destroyed records |
| Retention period applied | Which retention period was applied (e.g., "15 years from creation; created 2010-01-01; expired 2025-01-01") |
| Destruction method | Method used per Section 13.3 |
| Verification | Post-deletion verification result |
| Authorising officer | Name and role of Data Governance Owner who approved destruction |
| QA confirmation | Name and role of QA Lead who confirmed regulatory compliance |

---

## 14. Roles and Responsibilities

### 14.1 Role Matrix

| Role | Individual / Team | Primary Responsibilities |
|---|---|---|
| **Data Governance Owner** | Engineering Lead | Owns this policy; authorises data destruction; approves changes to retention schedules; escalation point for GDPR Art. 17 requests and data conflicts |
| **DevOps Lead** | Senior DevOps/SRE Engineer | Executes backup strategy; owns DR runbooks; executes and documents DR drills; monitors replication health; owns Cloud SQL and GCS backup configuration |
| **QA Lead** | Quality Assurance Lead | Confirms GxP retention obligations before any destruction; reviews DR drill reports; signs off on chain integrity confirmations; owns regulatory impact assessments post-incident |
| **Incident Commander** | On-call engineer (rotated) | Declares and manages incidents per runbooks; coordinates cross-functional response; owns incident ticket |
| **Customer Success Lead** | Customer Success function | Communicates outage status to customers; manages customer notifications; coordinates data export requests during offboarding |
| **CISO** | Security function | Escalation point for security incidents; authorises security-related destruction; owns encryption and access control review |
| **GMP4U (External)** | Johannes Eberhardt — CSV/Qualification Specialist | External advisor for GxP compliance review of this policy; reviewer of DR drill reports as part of periodic system review |

### 14.2 Responsibility Assignment Matrix (RACI)

| Activity | Data Governance Owner | DevOps Lead | QA Lead | Incident Commander | Customer Success |
|---|---|---|---|---|---|
| Backup configuration and monitoring | A | R | I | I | I |
| DR drill execution | A | R | C | R | I |
| DR drill documentation | I | R | A | C | I |
| Incident declaration | I | I | I | R | I |
| Region failover execution | A | R | C | R | I |
| Data corruption investigation | A | R | R | R | I |
| Customer outage communication | I | I | C | C | R |
| Retention period review | R | I | C | I | I |
| Destruction authorisation | R | I | A | I | I |
| Destruction execution | I | R | C | I | I |
| Destruction register maintenance | R | C | C | I | I |
| GDPR Art. 17 response | R | I | C | I | I |
| Tenant offboarding data handling | R | C | A | I | R |
| Policy annual review | R | C | C | I | I |

*R = Responsible; A = Accountable; C = Consulted; I = Informed*

### 14.3 On-Call Responsibilities

| Rotation | Coverage | Escalation Path |
|---|---|---|
| Engineering on-call (primary) | 24/7 via PagerDuty | Acknowledges alerts within 15 minutes; resolves or escalates within 30 minutes |
| Engineering Lead (secondary) | 24/7 business days; on-call for P0/P1 off-hours | Escalated by primary on-call for T3/T4 scenarios or multi-hour P1 incidents |
| QA Lead | Business hours; on-call for P0 incidents | Escalated by Engineering Lead for GxP data integrity events |

---

## 15. Policy Review and Change Management

### 15.1 Annual Review Schedule

This policy must be reviewed at least annually. The review is due by **2027-02-28** for the 2026 version.

Annual review activities:

| Activity | Description | Owner |
|---|---|---|
| Regulatory landscape review | Confirm no new regulatory requirements have changed minimum retention periods or DR obligations | QA Lead + GMP4U |
| Retention schedule validation | Confirm actual retention periods configured in GCS, Cloud SQL, and Cloud Logging match this policy's Schedule (Section 4) | DevOps Lead |
| Backup configuration review | Confirm backup frequencies, retention, and replication are operating as configured; review any alerts or failures from the past year | DevOps Lead |
| DR drill record review | Review DR verification register; confirm all required drills were completed; assess outcomes and any unresolved deviations | QA Lead |
| RTO/RPO achievability review | Confirm that actual DR drill results demonstrate RTO/RPO targets are achievable; update targets if architecture has changed | Engineering Lead |
| Destruction register review | Confirm all destruction events were authorised and documented; confirm no records were destroyed before their retention period expired | Data Governance Owner + QA Lead |
| Sub-processor review | Confirm GCP sub-processor agreements are current; confirm no changes to GCP data residency for BioNexus resources | Data Governance Owner |
| Policy document update | Update document version, effective date, and any changed sections; route for approval | Data Governance Owner |

### 15.2 Unscheduled Review Triggers

The following events trigger an immediate unscheduled review and potential update of this policy:

| Trigger | Urgency | Responsible |
|---|---|---|
| Change in applicable regulation (new FDA guidance, EU GMP revision, GDPR implementing regulation) | Within 30 days of effective date of regulatory change | QA Lead + Data Governance Owner |
| Material change to BioNexus architecture (new data stores, new geographic regions, new data types) | Before the architectural change is deployed to production | Engineering Lead + DevOps Lead |
| DR drill failure (RTO or RPO target not met) | Within 10 business days of drill | Engineering Lead |
| Data loss event (any actual data loss, even partially recovered) | Within 5 business days of incident resolution | Data Governance Owner + QA Lead |
| Security incident affecting backup or archival systems | Within 5 business days of incident resolution | CISO + Data Governance Owner |
| Addition of a new country-specific regulatory customer (new national requirements) | Before customer goes live | QA Lead |
| Retention policy lock (transitioning GCS retention policy to locked/WORM state) | Before lock is applied | DevOps Lead + QA Lead; lock is a one-way, irreversible change |

### 15.3 Change Control for Policy Updates

All changes to this policy, including updates to retention periods, RTO/RPO targets, and runbook modifications, must be managed through BioNexus change control:

1. **Change request**: Document the proposed change, the rationale, and the regulatory impact assessment.
2. **Review**: Data Governance Owner and QA Lead review; GMP4U consulted for changes with regulatory impact.
3. **Approval**: Data Governance Owner signs off on the new version.
4. **Implementation**: Any configuration changes (GCS retention periods, Cloud SQL backup settings, etc.) are implemented via Terraform and reviewed in a pull request before applying to production.
5. **Communication**: Affected customers are notified of changes that affect their regulatory obligations (e.g., reduction in retention period would require customer acknowledgment).
6. **Document update**: This policy is updated to a new version number and the revision history (Section 16) is updated.

---

## 16. Document Control and Revision History

### 16.1 Document Approval

| Role | Name | Signature | Date |
|---|---|---|---|
| Prepared by | BioNexus Engineering & Quality Team | [signature] | 2026-02-28 |
| Reviewed by | GMP4U — Johannes Eberhardt (CSV/Qualification Specialist) | [signature] | [date] |
| Approved by | Data Governance Owner | [signature] | [date] |

### 16.2 Revision History

| Version | Date | Author | Change Description | Change Control Ref |
|---|---|---|---|---|
| 1.0 | 2026-02-28 | BioNexus Engineering & Quality Team | Initial policy creation | BNX-CC-DR-001 |

### 16.3 Related Documents

| Document | Document ID | Location |
|---|---|---|
| GCP Cloud Architecture & Deployment Guide | BNX-INFRA-001 | `docs/GCP_CLOUD_ARCHITECTURE.md` |
| GxP Compliance Master Document | BNX-COMP-001 | `docs/GxP_COMPLIANCE_MASTER.md` |
| Security Architecture | N/A | `bionexus-platform/SECURITY_ARCHITECTURE.md` |
| System Validation Plan (IQ/OQ/PQ) | BNX-VAL-001 | `docs/SYSTEM_VALIDATION_PLAN.md` |
| Customer Onboarding & Admin Guide | BNX-OPS-001 | `docs/CUSTOMER_ONBOARDING_GUIDE.md` |

### 16.4 Definitions and Abbreviations

| Term | Definition |
|---|---|
| **ALCOA+** | Attributable, Legible, Contemporaneous, Original, Accurate + Complete, Consistent, Enduring, Available — the data integrity framework adopted by global GxP regulators |
| **CSV** | Computerized System Validation — the documented process of verifying that a computerized system consistently does what it is intended to do |
| **DR** | Disaster Recovery — the process of restoring IT services and data following a disruptive event |
| **GAMP5** | Good Automated Manufacturing Practice, 5th Edition — ISPE industry guidance for GxP computerized systems |
| **GCS** | Google Cloud Storage — GCP object storage service |
| **GDPR** | General Data Protection Regulation (EU) 2016/679 |
| **GxP** | Good x Practice — regulatory framework governing pharmaceutical manufacturing (GMP), laboratory (GLP), and clinical (GCP) activities |
| **PITR** | Point-in-Time Recovery — the ability to restore a database to its state at any given moment within the recovery window |
| **RPO** | Recovery Point Objective — the maximum acceptable amount of data loss measured in time |
| **RTO** | Recovery Time Objective — the maximum acceptable time from failure event to service restoration |
| **SHA-256** | Secure Hash Algorithm 256-bit — cryptographic hash function used by BioNexus to verify data integrity via an immutable chain |
| **WORM** | Write Once, Read Many — a storage policy that prevents modification or deletion of data once written; implemented via locked GCS retention policies |

---

*End of Document*

*Document ID: BNX-DR-001 | Version 1.0 | Effective Date: 2026-02-28*
