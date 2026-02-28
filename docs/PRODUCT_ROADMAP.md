# BioNexus Product Roadmap

## Document Information

**Document ID:** BNX-ROADMAP-001
**Version:** 1.0
**Status:** Active — Strategic Reference
**Date:** 2026-02-28
**Horizon:** February 2026 — December 2027+
**Prepared by:** BioNexus Product & Engineering
**Review Partner:** GMP4U (Johannes Eberhardt) — CSV/Qualification Specialist
**Audience:** Investors, Customers, Engineering Team, Regulatory Partners

---

## Table of Contents

1. [Vision Statement](#1-vision-statement)
2. [Current State — MVP](#2-current-state--mvp)
3. [Phase 1 — MVP Hardening (Q1–Q2 2026)](#3-phase-1--mvp-hardening-q1q2-2026)
4. [Phase 2 — Market Ready (Q3–Q4 2026)](#4-phase-2--market-ready-q3q4-2026)
5. [Phase 3 — Growth (H1 2027)](#5-phase-3--growth-h1-2027)
6. [Phase 4 — Scale (H2 2027+)](#6-phase-4--scale-h2-2027)
7. [Technical Debt & Infrastructure](#7-technical-debt--infrastructure)
8. [Compliance Milestones](#8-compliance-milestones)
9. [Partnership & Ecosystem](#9-partnership--ecosystem)
10. [Success Metrics](#10-success-metrics)
11. [Risks & Dependencies](#11-risks--dependencies)

---

## 1. Vision Statement

**BioNexus will become the operating system for the regulated laboratory — the layer between instrument hardware and the cloud that makes every measurement attributable, immutable, and audit-ready by default.**

Today, QC laboratories in pharma and biotech SMBs face a problem that is simultaneously mundane and catastrophic: laboratory instruments produce data that scientists manually transcribe onto paper, then re-enter into spreadsheets or legacy LIMS. This creates transcription errors, violates 21 CFR Part 11, exposes companies to FDA warning letters, and costs tens of thousands of dollars per GMP incident. Enterprise LIMS vendors offer a solution — but demand 12–18 months and six-figure implementation fees that smaller labs cannot justify.

BioNexus eliminates this gap. By combining a Plug and Play hardware gateway (the BioNexus Box) with a purpose-built GxP cloud platform, BioNexus compresses instrument-to-cloud data integration from 12 months to one day. No transcription. No paper. No guesswork about compliance.

**North Star:** By the end of 2027, BioNexus is the standard integration layer for QC labs with 2–25 instruments in the pharmaceutical and biotechnology SMB segment across North America and Europe, connecting 500+ instruments and recognized by CSV/qualification specialists as a pre-validated, audit-ready platform.

---

## 2. Current State — MVP

**As of February 2026, what exists and what is its status:**

### 2.1 What Is Built and Functional

| Component | Status | Notes |
|---|---|---|
| Django REST API backend | Working | Python 3.12, Django 4.2, DRF |
| PostgreSQL database (dev: SQLite) | Partial | SQLite in dev, PostgreSQL targeted for prod |
| JWT authentication (access + refresh tokens) | Working | 15-min access, 7-day refresh, HS256 |
| Role-Based Access Control (RBAC) | Architecture complete, implementation in progress | 5 roles: ADMIN, PI, LAB_TECHNICIAN, AUDITOR, VIEWER |
| Multi-tenant data model | Architecture defined, migration pending | Tenant isolation at repository layer |
| SHA-256 immutable audit trail | Working | Signature-chained AuditLog; tampering detection operational |
| File upload and AI-assisted parsing | Working | PDF/CSV ingestion, Pydantic schema validation |
| Human review / correction workflow | Working | ParsedData state machine: PENDING → VALIDATED → CERTIFIED |
| Double-authentication certification | Working | Password re-entry + OTP; creates immutable CertifiedReport |
| Correction tracker | Working | Every field change logged with before/after and reason |
| Chain integrity verification | Working | Background 30-second chain re-verification |
| Certified report export (PDF + JSON) | Working (prototype) | SHA-256 signed PDF with QR code |
| Protocol execution logs | Working | Step-by-step execution recording with measurements |
| React frontend (prototype) | Partial | Login, dashboard, parsing/validation split view; not production-ready |
| BioNexus Box hardware | Architecture documented | Hardware spec defined; no production units exist yet |
| GCP cloud deployment | Not yet | Currently local development only |
| CI/CD pipeline | Not yet | No automated test pipeline |
| Monitoring / alerting | Not yet | No observability stack |

### 2.2 Data Models Implemented

- `AuditLog` — immutable, SHA-256 chained, mandatory user attribution
- `ParsedData` — file parsing output with state machine (raw → parsed → validated → certified)
- `RawFile` — immutable source file record with SHA-256 hash
- `CorrectionTracker` — field-level correction history with reason
- `CertifiedReport` — immutable signed report record
- `ExecutionLog` / `ExecutionStep` — protocol execution journal
- `Tenant` / `User` / `Role` / `Permission` — multi-tenant RBAC foundation

### 2.3 Key Architectural Decisions Already Made

- **No-Trust AI Pipeline**: AI-extracted data enters as `PENDING` and requires mandatory human review before use — no auto-acceptance
- **Immutability Enforced at Code Level**: `AuditTrail.record()` raises `ValueError` if `user_id` is absent; records cannot be modified after creation
- **ALCOA+ Compliance by Design**: Attributable, Legible, Contemporaneous, Original, Accurate, Complete, Consistent, Enduring, Available — mapped to specific model fields and service behaviors (see PARSING_ARCHITECTURE.md)
- **Multi-Tenant from Day One**: All data models carry `tenant_id`; repository layer enforces isolation

### 2.4 What Is Prototype / Incomplete

- Frontend React application is a functional prototype, not production-hardened
- Multi-tenant `tenant_id` migration on Sample and Protocol models is pending
- Certified PDF export is functional but needs template refinement and QR code verification tooling
- No real BioNexus Box hardware exists — the architecture document (BNX-HW-001) is complete, prototyping not yet started
- OTP delivery uses stub/email; SMS integration (Twilio) is pending
- Test coverage is partial; no CI pipeline enforces it

---

## 3. Phase 1 — MVP Hardening (Q1–Q2 2026)

**Theme: Make what exists production-grade and complete the core compliance loop.**

The goal of Phase 1 is not to add features — it is to make the existing features solid enough that the first real customer can use the system without risk. Every item in this phase serves reliability, security, or compliance.

### 3.1 Timeline

```
Q1 2026 (Feb–Mar)                Q2 2026 (Apr–Jun)
|--------------------------------|--------------------------------|
| Complete RBAC + tenant isolation| GCP deployment (staging)       |
| Sample tracking CRUD + audit   | CI/CD pipeline live            |
| Audit trail immutability tests | Frontend v1 (usable, not pretty)|
| PostgreSQL migration in prod   | OTP via email + SMS            |
| Error handling & input validation| Monitoring (Cloud Monitoring)  |
| API pagination on all list views| Basic onboarding flow          |
|                                | Internal alpha with GMP4U      |
```

### 3.2 Backend Priorities

**Sample Tracking API (Current Sprint)**
- `GET/POST /api/samples/` — list and create samples with tenant isolation
- `GET/PUT/DELETE /api/samples/{id}/` — retrieve, update (audited), soft-delete
- Mandatory audit trail entry on every mutation
- Full pagination on list views (cursor-based for audit log)
- Input validation at serializer level with meaningful error messages

**Complete RBAC Enforcement**
- Apply `@permission_required` decorator to every view that mutates data
- Apply `@tenant_context` decorator to every view that reads data
- Enforce `tenant_id` FK on Sample, Protocol, ExecutionLog — migration and backfill
- Add integration tests that prove cross-tenant data leakage is impossible

**Audit Trail Hardening**
- Enforce chain signature verification on every `AuditLog.save()` — reject writes that break the chain
- Add `GET /api/integrity/check/` endpoint visible to AUDITOR and ADMIN roles only
- Add automated daily chain integrity check as a scheduled task (Cloud Scheduler)
- Certified export: tamper-proof JSON + PDF with embedded SHA-256 chain

**Infrastructure**
- Migrate from SQLite to PostgreSQL (GCP Cloud SQL)
- Environment variable management via GCP Secret Manager — no hardcoded credentials anywhere
- HTTPS enforced; HTTP redirected; HSTS headers set
- CORS locked to specific allowed origins

### 3.3 Frontend Priorities (v1 — Functional, Not Beautiful)

- Login flow with JWT token management and auto-refresh
- Dashboard: sample count, pending validations, chain integrity status badge
- Parsing/Validation split view (already prototyped — harden and fix edge cases)
- Audit log viewer: filterable by entity, user, date range, operation
- Role-aware navigation: AUDITOR sees read-only views, ADMIN sees management panels
- Certified report download (PDF)

### 3.4 Testing Targets

| Area | Target Coverage |
|---|---|
| API endpoints (happy path + error) | 100% of endpoints have both test types |
| RBAC permission checks | All 12 permissions tested with authorized and unauthorized users |
| Tenant isolation | Explicit cross-tenant access attempt tests — must return 403/404 |
| Audit trail chain | Unit test for chain tamper detection |
| Parsing workflow | Full integration test: upload → parse → validate → certify |

### 3.5 Phase 1 Exit Criteria

- All tests pass in CI on every pull request
- System runs on GCP (Cloud Run + Cloud SQL + Cloud Storage)
- At least one GMP4U review session completed on the audit trail and RBAC design
- Zero hardcoded secrets in any committed code
- API response time under 300ms at p95 for all read endpoints

---

## 4. Phase 2 — Market Ready (Q3–Q4 2026)

**Theme: First real customers, first real hardware, first real revenue.**

Phase 2 is about crossing from prototype to product. By the end of Q4 2026, BioNexus should have at least two paying pilot customers, a production-ready BioNexus Box, instrument parsers for the five most common analyzer types in QC labs, and a GMP4U-reviewed qualification package that gives customers what they need to validate the system under GAMP5.

### 4.1 Timeline

```
Q3 2026 (Jul–Sep)                Q4 2026 (Oct–Dec)
|--------------------------------|--------------------------------|
| BioNexus Box v1 prototypes     | BioNexus Box v1 production run |
| Instrument parsers: 5 types    | First customer deployment       |
| Customer onboarding flow       | GMP4U qualification package v1 |
| Instrument registration API    | Pilot customer feedback loop   |
| Alert & monitoring service     | MRR target: EUR 3,000/month    |
| Setup fee billing integration  |                                |
| Instrument status dashboard    |                                |
```

### 4.2 BioNexus Box v1

Based on the hardware architecture document (BNX-HW-001):

**Hardware Specification (Production Target)**
- Platform: Industrial SBC (Raspberry Pi CM4 or equivalent industrial-grade module)
- Interfaces: 2x RS232 (DB9), 2x USB-A, 1x Ethernet (RJ45), 1x Wi-Fi (optional)
- Storage: 32GB eMMC (OS + local buffer) + MicroSD slot for expansion
- Enclosure: DIN-rail mountable (35mm) or bench-top; IP40 rated; -10°C to 50°C operating range
- Power: 12–24V DC, 10W typical
- Security: Secure boot, encrypted storage, device-unique certificate (X.509), TPM 2.0 module

**Software on Box**
- BioNexus Edge Agent (Python, systemd service): RS232/USB data capture → local SQLite buffer → HTTPS upload to GCP
- Store-and-forward: up to 7 days of data buffered locally if internet connectivity is lost
- Firmware OTA update: signed firmware packages verified before installation
- Health heartbeat: Box sends status ping every 60 seconds; cloud marks instrument offline if 5 pings missed

**Provisioning Flow (Same-Day Installation Target)**
1. Customer receives Box pre-loaded with BioNexus Edge Agent
2. Customer plugs RS232 cable into instrument, Ethernet into lab switch
3. Customer navigates to `setup.bionexus.io` on any browser on the same network
4. Box auto-discovers and displays activation code
5. BioNexus technician (remote) completes cloud registration: tenant, instrument type, parser assignment
6. First data packet arrives in cloud within 5 minutes of activation

### 4.3 Instrument Parsers — Top 5 Analyzer Types

Priority order based on QC lab frequency in pharma/biotech SMBs:

| Priority | Instrument Type | Example Models | Output Format | Parser Complexity |
|---|---|---|---|---|
| 1 | pH / Conductivity Meter | Mettler Toledo SevenExcellence, Sartorius | RS232 ASCII, CSV | Low |
| 2 | Dissolution Tester | Agilent 708-DS, Hanson SR8Plus | RS232 proprietary, CSV | Medium |
| 3 | Spectrophotometer / UV-Vis | Thermo Fisher GENESYS, Shimadzu UV-1900 | RS232, ASCII fixed-width | Medium |
| 4 | Analytical Balance | Mettler Toledo XPR, Sartorius Quintix | RS232 SBI protocol | Low |
| 5 | HPLC Data Terminal Output | Agilent OpenLAB, Waters Empower (print-to-serial) | ASCII report format | High |

Each parser is a Python module registered in the BioNexus parser registry. Parsers:
- Accept raw bytes from the Edge Agent
- Return a `BatchExtractionResult` dict validated against Pydantic schema
- Are versioned: each parser has a version string stored with every parsed record
- Support test mode: can be run against a sample file without live instrument

### 4.4 Customer Onboarding Flow

**Pre-Sale (Qualification Stage)**
- BioNexus Box demo kit available for 30-day proof-of-concept loan
- Onboarding checklist provided to customer's IT/QA team (network requirements, RS232 cable specs, firewall rules)
- GMP4U CSV readiness assessment available as add-on service

**Technical Onboarding (Day 1)**
- Box shipped pre-configured with customer's tenant ID
- Remote installation session (1 hour maximum): Box + instrument + cloud registration
- Instrument-specific parser configured and tested with live data
- First audit log entry confirmed with customer's QA representative present

**QA Onboarding (Week 1–2)**
- BioNexus provides GAMP5 Supplier Assessment document (BNX-COMP-001)
- GMP4U delivers User Requirements Specification (URS) template
- IQ/OQ execution: Installation Qualification and Operational Qualification protocol documents provided; customer executes with BioNexus support
- PQ (Performance Qualification): customer-led; BioNexus provides evidence package

### 4.5 GMP4U Qualification Package v1

Deliverables provided to every paying customer:

| Document | Owner | Description |
|---|---|---|
| Supplier Assessment | BioNexus | GxP supplier self-assessment per GAMP5 Chapter 3 |
| System Description | BioNexus | Functional and technical description of platform |
| Risk Assessment | BioNexus | ICH Q9 risk assessment; FMEA for data integrity risks |
| Installation Qualification (IQ) Protocol | BioNexus | Step-by-step IQ with expected results and acceptance criteria |
| Operational Qualification (OQ) Protocol | BioNexus | OQ test scripts covering all critical functions |
| 21 CFR Part 11 Compliance Matrix | BioNexus | Requirement-by-requirement mapping |
| EU Annex 11 Compliance Matrix | BioNexus | Requirement-by-requirement mapping |
| ALCOA+ Mapping | BioNexus | Field-level traceability to ALCOA+ principles |
| Audit Trail Summary | BioNexus | Specification of all audited events |
| URS Template | GMP4U | Customer-specific user requirements |
| CSV Review Checklist | GMP4U | GMP4U-branded review checklist for CSV auditors |

### 4.6 Billing Integration

- Setup fee: EUR 2,500–5,000 per customer (one-time; covers Box hardware + remote installation + qualification package)
- Monthly SaaS: EUR 150–300 per instrument per month (tiered: 1–5 instruments, 6–15, 16+)
- Invoicing via Stripe or similar; subscription management automated
- Usage dashboard: customer can see instrument count and billing estimate in real time

### 4.7 Phase 2 Exit Criteria

- Minimum 2 paying pilot customers with installed BioNexus Box hardware
- At least 5 instrument types have validated parsers (tested against real instrument output)
- GMP4U qualification package delivered and reviewed by at least one customer QA team
- MRR >= EUR 3,000/month
- Box uptime >= 99% (excluding planned maintenance) measured over 30 consecutive days
- Zero data integrity incidents (chain corruption, cross-tenant leakage)

---

## 5. Phase 3 — Growth (H1 2027)

**Theme: Build the platform that can scale from 2 customers to 20+, and introduce the analytics that make BioNexus indispensable.**

### 5.1 Timeline

```
Jan 2027          Feb 2027          Mar 2027          Apr 2027          May 2027          Jun 2027
|-----------------|-----------------|-----------------|-----------------|-----------------|---------|
| Multi-tenant    | Analytics       | Expanded parsers| LIMS API        | Mobile app      | ERP API |
| SaaS hardening  | dashboard v1    | (15+ types)     | integrations    | (read-only)     | pilots  |
| Automated       | Trend analysis  | Parser          | HL7/FHIR        |                 |         |
| onboarding      | OOT detection   | marketplace v1  | connector       |                 |         |
```

### 5.2 Multi-Tenant SaaS Hardening

- **Customer Admin Portal**: Each customer tenant has an admin user who can manage their own users, roles, and instrument registrations without contacting BioNexus support
- **Tenant Provisioning Automation**: New customer tenant creation fully automated; no manual database operations required
- **Subscription Tiers**: Free trial (30 days, 1 instrument), Standard (1–5 instruments), Professional (6–15), Enterprise (15+)
- **Usage Metering**: Instrument-months metered automatically; overage alerts; billing auto-adjusts at month end
- **Data Retention Policies**: Configurable per tenant; default 7 years (21 CFR Part 11 requirement); archival to cold storage (GCP Coldline) after 2 years active retention

### 5.3 Advanced Analytics Dashboard

The analytics dashboard addresses a capability gap versus enterprise LIMS: not just data capture, but insight.

**Key Features:**
- **Trend Analysis per Instrument**: Plot any measured parameter over time (e.g., pH readings, dissolution values, balance weighings) — identify drift before it becomes an OOS event
- **Out-of-Specification (OOS) / Out-of-Trend (OOT) Detection**: Configurable control limits per instrument/parameter; automated flag when readings exceed Shewhart control chart boundaries
- **Audit Trail Analytics**: Who makes the most corrections? Which instruments generate the most rejected parsings? Operational health at a glance
- **Compliance Score Dashboard**: Real-time GxP compliance score per instrument, per tenant; exportable for regulatory inspection readiness
- **Instrument Uptime Reports**: Availability by instrument, by site, by month; exportable for maintenance qualification records

**Technology:**
- Backend: Time-series data stored in PostgreSQL with proper indexing; aggregation queries via Django ORM
- Frontend: React + Recharts / Plotly for charting
- Export: CSV and PDF export for all dashboard views; all exports carry SHA-256 signature

### 5.4 Expanded Instrument Support (15+ Types)

By end of H1 2027, support the following analyzer categories:

| Category | Instrument Examples | Total Types |
|---|---|---|
| pH / Conductivity / Dissolved O2 | Mettler Toledo, Sartorius, Thermo Orion | 3 |
| Dissolution Testing | Agilent, Hanson, Sotax, Erweka | 4 |
| Spectrophotometry (UV-Vis, NIR) | Shimadzu, Thermo, Jasco, PerkinElmer | 4 |
| Analytical Balances | Mettler Toledo, Sartorius, Ohaus | 3 |
| HPLC Print-to-Serial / Data Terminal | Agilent, Waters, Shimadzu | 3 |
| Karl Fischer Titrators | Mettler Toledo C20, Metrohm | 2 |
| Viscometers | Brookfield, Anton Paar | 2 |
| Particle Size Analyzers | Malvern Mastersizer, Beckman Coulter | 2 |
| Osmometers | Gonotec, Advanced Instruments | 1 |
| Total Organic Carbon (TOC) Analyzers | Shimadzu TOC-L, GE Sievers | 1 |

**Parser Marketplace (v1):**
- BioNexus publishes a parser registry: each parser has a name, version, instrument models supported, and test dataset
- Customers can request new parsers via support ticket; BioNexus delivers within 30 business days
- Partner labs can contribute parsers (reviewed and signed by BioNexus before publication)

### 5.5 API Integrations

**LIMS Integration**
- REST API connector for common LIMS platforms (LabWare, STARLIMS, LabVantage, Labguru)
- Bi-directional: BioNexus can receive sample IDs from LIMS and return parsed instrument results
- Data mapping layer: LIMS field names mapped to BioNexus schema; configurable per tenant
- Authentication: OAuth 2.0 client credentials flow for system-to-system integration

**ERP Integration (Pilot)**
- SAP S/4HANA and Microsoft Dynamics 365 connector pilots with 2 customers
- Use case: instrument maintenance schedules from ERP → BioNexus instrument status; BioNexus OOS events → ERP deviation records

**HL7/FHIR (Research)**
- Initial feasibility assessment for labs operating adjacent to clinical environments
- Not a core priority but tracked for future expansion into clinical trial site monitoring

### 5.6 Mobile Monitoring App (Read-Only)

- iOS and Android app (React Native)
- Functionality: instrument status at-a-glance, recent audit log entries, OOS alerts, chain integrity status
- Strictly read-only — no data entry, no certification actions (21 CFR Part 11 electronic signature requirements are not met on mobile in v1)
- Push notifications: instrument goes offline, OOS event detected, audit chain integrity check failed

### 5.7 Phase 3 Exit Criteria

- 15+ paying customers
- 15+ instrument parser types available and validated
- Analytics dashboard live and used by >50% of customers weekly
- At least one LIMS integration live in production with a real customer
- MRR >= EUR 30,000/month
- Mobile app published on App Store and Google Play

---

## 6. Phase 4 — Scale (H2 2027+)

**Theme: Enterprise-grade platform, formal certifications, international expansion, and edge intelligence on the Box.**

### 6.1 Timeline

```
H2 2027                                    2028+
|------------------------------------------|------------------------------|
| SSO/SAML enterprise auth                 | International expansion      |
| Custom workflow engine                   | ISO 27001 certification       |
| EU Annex 11 formal certification process | Channel partner program       |
| Edge AI on BioNexus Box                  | Instrument manufacturer OEM   |
| Parser marketplace (open ecosystem)      | partnerships                  |
| White-label / OEM packaging              |                               |
```

### 6.2 Enterprise Features

**Single Sign-On (SSO) / SAML 2.0**
- Integration with corporate identity providers: Okta, Azure AD, Google Workspace, ADFS
- SCIM provisioning: user accounts automatically created/deactivated based on IdP group membership
- Audit trail entry for every SSO login event with identity provider session ID
- Required by enterprise procurement teams; gates entry into 500+ employee organizations

**Custom Workflow Engine**
- Visual workflow builder: QA managers configure approval chains without code
- Example workflows: instrument results require Principal Investigator review before certification; OOS results automatically route to Lab Director + QA Manager
- Webhook triggers: workflow events emit HTTPS webhooks for integration with LIMS/ERP/ticketing systems
- All workflow states are recorded in the immutable audit trail

**Advanced RBAC — Attribute-Based Access Control (ABAC)**
- Access policies based on combinations of role, instrument type, sample type, and time-of-day
- Example: Lab Technician A can only certify data from instruments in Lab Room 3; Auditor B can only view records from Q3 2025 onwards
- Policy language: JSON-based, stored and versioned in the database

**Advanced Reporting**
- Regulatory inspection report generator: one-click export of all records for a date range, formatted for FDA 483 response or EMA inspection readiness
- Trend report PDF: compliance score history, OOS event history, correction frequency — formatted for Annual Product Review (APR)
- Configurable report templates: customer QA can add their logo, document number, version history

### 6.3 EU Annex 11 Formal Certification Process

EU Annex 11 does not provide a formal "certification" body in the way ISO does — compliance is demonstrated during regulatory inspections. However, BioNexus will pursue:

- **Third-Party Audit**: Engage a recognized GxP IT auditor (e.g., GAMP Community of Practice member firm) to conduct a formal Annex 11 gap assessment and issue a conformity statement
- **GAMP5 Category 4 Package**: Full Software Development Lifecycle (SDLC) documentation package qualifying BioNexus as a GAMP5 Category 4 Configured Product
- **Qualified GxP Cloud**: Formalize GCP (Google Cloud Platform) qualification documentation per Annex 11 Clause 3.4 (Infrastructure Qualification)
- **Reference Customer Qualification**: Assist a pilot customer through a full IQ/OQ/PQ cycle and document the execution records as a reference model for all future customers
- This formal package will be marketed as the "BioNexus Validated Package" — a premium tier offering that reduces customer validation effort by 70%

### 6.4 Edge AI on BioNexus Box

Move AI-assisted parsing from the cloud to the edge device:

- **On-Device Small Language Model**: Lightweight model (GGUF format, quantized to run on ARM Cortex-A72 or similar) handles initial data extraction locally
- **Benefits**:
  - No raw instrument data leaves the customer network until it is already structured — significant advantage for sensitive manufacturing environments
  - Faster feedback loop: extraction happens in < 1 second at the instrument, not a round-trip to GCP
  - Offline AI extraction: Box can fully parse and structure data during internet outages; uploads structured data when connectivity restores
- **Compliance**: On-device AI output is still subject to Pydantic schema validation and mandatory human review upon upload — the no-trust pipeline is preserved regardless of extraction location

### 6.5 Instrument Manufacturer Partnerships (OEM)

- Target 2–3 instrument manufacturers for OEM partnerships by end of 2027
- **Partnership model**: Manufacturer bundles BioNexus Box hardware + firmware with new instrument shipments; BioNexus software is co-branded or white-labeled; manufacturer includes BioNexus connectivity as a product feature
- **Revenue split**: BioNexus receives SaaS subscription revenue; manufacturer charges incremental hardware fee
- **Target manufacturers**: Mid-tier dissolution tester manufacturers (Hanson, Sotax) and analytical balance manufacturers (Ohaus, Adam Equipment) are most accessible — tier 1 (Mettler Toledo, Agilent) require longer sales cycles

### 6.6 Parser Marketplace (Open Ecosystem)

- BioNexus publishes a formal parser SDK: Python package, documentation, test harness, submission process
- Third parties (instrument manufacturers, LIMS integrators, independent labs) can develop and publish parsers
- Revenue model: BioNexus takes 20% revenue share on third-party parsers sold through the marketplace
- Quality control: every submitted parser passes automated validation (schema compliance, test dataset pass rate >= 99%) and BioNexus security review before publication
- Parsers are cryptographically signed by BioNexus before being deployed to customer Boxes

### 6.7 International Expansion

- **Phase 4a (H2 2027)**: France, Germany, Netherlands — EU GMP markets; leverage GMP4U network for market entry; multi-language UI (EN/FR/DE)
- **Phase 4b (2028)**: UK (post-Brexit MHRA alignment), Switzerland (Swissmedic)
- **Phase 4c (2028+)**: North America scale (US FDA-regulated customers in pharma manufacturing); Canada (Health Canada); Japan (PMDA) feasibility study

**Localization Requirements:**
- UI language: EN, FR, DE (Phase 4a); additional languages on demand
- Regulatory document templates: jurisdiction-specific (FDA vs EMA vs MHRA formatting)
- Data residency: GCP multi-region with EU data residency option for EU customers (GDPR Article 46 compliance)
- Currency: EUR (primary), GBP, USD, CHF

### 6.8 Phase 4 Exit Criteria

- SSO/SAML live with at least 3 enterprise customers
- EU Annex 11 third-party conformity statement obtained
- ISO 27001 certification in progress (scope defined, audit scheduled)
- At least 1 OEM partnership agreement signed with an instrument manufacturer
- BioNexus operating in at least 3 countries
- MRR >= EUR 150,000/month
- 500+ instruments connected across all tenants

---

## 7. Technical Debt & Infrastructure

Items to address continuously across all phases. Assigned to phases where they become critical.

### 7.1 Test Coverage (Phase 1 Priority)

| Area | Current State | Target | Phase |
|---|---|---|---|
| API endpoint happy-path tests | Partial | 100% of endpoints | Phase 1 |
| API endpoint error/edge tests | Partial | 100% of endpoints | Phase 1 |
| RBAC permission tests | Architecture only | All 12 permissions, all 5 roles | Phase 1 |
| Tenant isolation tests | None | Explicit cross-tenant attack tests | Phase 1 |
| Audit chain tamper detection | Unit test exists | Integration test in full workflow | Phase 1 |
| Parsing workflow end-to-end | Partial | Upload → parse → validate → certify | Phase 1 |
| BioNexus Box Edge Agent | None | RS232 capture, buffer, upload | Phase 2 |
| Parser validation tests | Per-parser | 99% pass rate on reference datasets | Phase 2 |
| Performance / load tests | None | 100 concurrent users, p95 < 500ms | Phase 3 |
| Security penetration test | None | Annual external pen test | Phase 3 |

### 7.2 CI/CD Pipeline (Phase 1 Priority)

Target stack:
- **Version control**: GitHub (current)
- **CI**: GitHub Actions — run tests, linting (flake8, mypy), security scan (Bandit) on every pull request; block merge on failure
- **CD**: GitHub Actions → GCP Cloud Build → Cloud Run (staging) on merge to `main`; manual promotion gate to production
- **Container registry**: GCP Artifact Registry
- **Infrastructure as Code**: Terraform for GCP resources (Cloud Run, Cloud SQL, Cloud Storage, Secret Manager, Cloud Scheduler)
- **Database migrations**: Django `manage.py migrate` run as a Cloud Build step before new container revision receives traffic

### 7.3 Monitoring & Observability (Phase 1–2)

| Layer | Tool | Key Metrics |
|---|---|---|
| Application performance | GCP Cloud Monitoring + Cloud Trace | Request latency p50/p95/p99; error rate; DB query time |
| Error tracking | Sentry (self-hosted or cloud) | Exception rate; new error types; regression detection |
| Audit chain health | Custom: Cloud Scheduler daily job | Chain verification result; corrupted record count |
| BioNexus Box health | Heartbeat API + Cloud Monitoring | Box online/offline; last packet received; buffer fill % |
| Uptime | GCP Uptime Checks | API availability; alert PagerDuty if > 1 min downtime |
| Security | GCP Security Command Center | Vulnerability findings; IAM anomaly detection |

**Alert escalation:**
- P1 (data integrity breach, chain corruption, production outage): PagerDuty → on-call engineer within 5 minutes
- P2 (Box offline > 1 hour, error rate spike): Slack alert + email to customer success
- P3 (performance degradation, test failure in CI): Slack alert to engineering channel

### 7.4 Documentation Translation (Phase 4)

For EU market entry (Phase 4a), the following documents require professional translation to French and German:

| Document | EN Available | FR | DE | Priority |
|---|---|---|---|---|
| User Interface | Phase 1 | Phase 4 | Phase 4 | High |
| User Manual / Help | Phase 2 | Phase 4 | Phase 4 | High |
| IQ/OQ Protocol Templates | Phase 2 | Phase 4a | Phase 4a | Critical |
| 21 CFR Part 11 / Annex 11 Matrix | Phase 1 | Phase 4 | Phase 4 | High |
| Onboarding Guides | Phase 2 | Phase 4 | Phase 4 | Medium |
| API Documentation | Phase 1 | Phase 4 | Phase 4 | Low |

**Translation approach**: Professional technical translation firm with life sciences specialization (not AI-only translation); all regulatory documents reviewed by GMP4U or local CSV specialist before distribution.

### 7.5 Database Scalability Path

| Phase | Database Config | Rationale |
|---|---|---|
| Phase 1 | Cloud SQL PostgreSQL 14, 2 vCPU, 8GB RAM, single region | Sufficient for < 5 customers, < 1M audit records |
| Phase 2 | Cloud SQL PostgreSQL 14, 4 vCPU, 16GB RAM, automated backups, read replica | 10–20 customers, daily backup verification |
| Phase 3 | Cloud SQL PostgreSQL 15, 8 vCPU, 32GB RAM, multi-zone HA, connection pooling (PgBouncer) | 50+ customers, < 5ms read latency target |
| Phase 4 | Cloud SQL Enterprise Plus or AlloyDB, multi-region, automated failover | 200+ customers, 99.99% availability SLA |

Audit log archival: records older than 2 years exported to GCP Cloud Storage (Coldline) as signed JSON archives; verifiable on-demand without impacting production DB size.

---

## 8. Compliance Milestones

### 8.1 Timeline Overview

```
2026 Q1  2026 Q2  2026 Q3  2026 Q4  2027 Q1  2027 Q2  2027 H2  2028+
   |        |        |        |        |        |        |        |
   |--GxP Compliance Master Doc (done)          |        |        |
   |--21 CFR Part 11 Self-Assessment-----------|        |        |
   |        |--GAMP5 Docs Package v1------------|        |        |
   |        |        |--First IQ/OQ Execution--|        |        |
   |        |        |        |--GMP4U Qual Package v1  |        |
   |        |        |        |        |--EU Annex 11 Gap Assessment
   |        |        |        |        |        |--3rd Party Audit|
   |        |        |        |        |        |        |--ISO 27001 Scoping
   |        |        |        |        |        |        |        |--ISO 27001 Cert
```

### 8.2 Milestone Details

| Milestone | Target Date | Owner | Description |
|---|---|---|---|
| GxP Compliance Master Document | Done (Feb 2026) | BioNexus + GMP4U | BNX-COMP-001 — regulatory framework, ALCOA+ mapping, 21 CFR / Annex 11 matrices |
| 21 CFR Part 11 Self-Assessment | Q1 2026 | BioNexus Engineering | Internal gap assessment against all Part 11 requirements; tracked in compliance backlog |
| GAMP5 SDLC Documentation Package v1 | Q2 2026 | BioNexus + GMP4U | Software category classification (Cat 4), risk assessment, change control procedure |
| First IQ/OQ Protocol Execution | Q3 2026 | BioNexus (customer-assisted) | Execute IQ/OQ with pilot customer #1; produce executed protocol records |
| GMP4U Qualification Package v1 | Q4 2026 | GMP4U primary | Full customer-facing validation package: IQ/OQ/PQ templates, URS, CSV checklist |
| EU Annex 11 Gap Assessment | Q1 2027 | BioNexus + GMP4U | Line-by-line Annex 11 gap analysis vs. platform capabilities; remediation plan |
| Third-Party GxP Audit | Q2 2027 | External auditor | Formal audit by GAMP COP member firm; conformity statement issued |
| ISO 27001 Scoping | H2 2027 | BioNexus + external consultant | Define ISMS scope; gap assessment; project plan for certification |
| ISO 27001 Certification | 2028 | BioNexus + certification body | Stage 1 + Stage 2 audit; certificate issued |
| GAMP5 Full Validation Package v2 | 2028 | BioNexus + GMP4U | Updated package incorporating all Phase 2–3 features; PQ reference dataset included |

### 8.3 21 CFR Part 11 — Current Compliance Status

| Requirement | Status | Gap / Action |
|---|---|---|
| Audit trail with timestamps | Implemented | Continuous chain verification scheduled job needed (Phase 1) |
| Audit trail cannot be modified | Implemented | Signature chain enforced at code level |
| User attribution mandatory | Implemented | ValueError raised if user_id absent |
| Electronic signatures unique to one individual | Implemented | Password + OTP double authentication |
| Electronic signatures linked to record | Implemented | Signature stored in CertifiedReport with report_hash |
| Access controls / role enforcement | In Progress | RBAC architecture complete; enforcement decorators being applied (Phase 1) |
| System validates permissible steps | Implemented | ParsedData state machine enforces PENDING → VALIDATED → CERTIFIED sequence |
| Audit trail available for inspection | Implemented | GET /api/auditlog/ with full filter parameters |
| Records retrievable for FDA review | Implemented | JSON export endpoint; PDF with embedded SHA-256 |
| Computer-generated timestamps | Implemented | Django `auto_now_add` UTC timestamps; not user-settable |
| Periodic system testing | Not yet | Scheduled chain integrity check (Phase 1) |
| Training records | Not yet | User training documentation and tracking (Phase 2) |
| Disaster recovery | Not yet | Backup verification and DR runbook (Phase 2) |

---

## 9. Partnership & Ecosystem

### 9.1 GMP4U — Primary Regulatory Partner

**Johannes Eberhardt / GMP4U** is a CSV and qualification specialist and the foundational regulatory partnership for BioNexus.

| Period | Collaboration Activities |
|---|---|
| Q1–Q2 2026 | Review of audit trail design, RBAC model, and electronic signature implementation against 21 CFR Part 11; feedback incorporated into Phase 1 hardening |
| Q3–Q4 2026 | Co-develop GMP4U Qualification Package v1; joint delivery to pilot customers; GMP4U on-site for first IQ/OQ execution |
| H1 2027 | EU Annex 11 gap assessment; adapt qualification package for EU market; co-present at GAMP COP regional event |
| H2 2027 | Third-party audit support; develop Performance Qualification (PQ) reference dataset; expand to additional instrument types |
| 2028+ | Ongoing: quarterly review of compliance documentation as platform evolves; support for customer regulatory inspections |

**Commercial Structure**: GMP4U may participate in a referral/reseller arrangement — GMP4U refers pharma/biotech clients to BioNexus as part of CSV engagements; BioNexus refers customers requiring qualification support to GMP4U. Revenue share or referral fee to be formalized by Q3 2026.

### 9.2 Potential Channel Partnerships

| Partner Type | Target | Value to BioNexus | Timeline |
|---|---|---|---|
| LIMS Resellers / Integrators | Companies that implement LabWare, STARLIMS in SMB market | Access to customers who cannot afford full LIMS; BioNexus as a bridge/complementary product | Phase 3 |
| Lab Equipment Distributors | Regional distributors of analytical instruments (EU + North America) | Bundled hardware + BioNexus Box; foot in door at instrument purchase | Phase 2–3 |
| GxP Consulting Firms | Validation and CSV consultancies beyond GMP4U | They recommend BioNexus during client CSV engagements | Phase 2 |
| CRO/CMO Facility Networks | Contract research and manufacturing organizations with multiple sites | Multi-site deployment; high instrument count per customer | Phase 3–4 |

### 9.3 Instrument Manufacturer Partnerships

Target manufacturers for OEM or certified integration agreements:

| Manufacturer | Instruments | Priority | Approach |
|---|---|---|---|
| Hanson Research | Dissolution testers | High | OEM bundle: Box sold with Hanson instruments |
| Sartorius | Balances, bioreactors, pH meters | High | Certified integration; Sartorius data API if available |
| Ohaus | Analytical balances | Medium | OEM bundle; lower price point, high volume |
| Anton Paar | Viscometers, density meters | Medium | Certified parser; premium market |
| Mettler Toledo | Full range (balance, pH, dissolution, thermal) | Long-term | Enterprise partnership; longer sales cycle but highest volume |
| Agilent Technologies | HPLC, dissolution, UV-Vis | Long-term | OEM partnership; significant TAM expansion |

**Partnership development timeline**: Identify and approach Hanson and Ohaus by Q4 2026; target signed OEM agreement with at least one manufacturer by H2 2027.

---

## 10. Success Metrics

### 10.1 KPIs by Phase

| Metric | Phase 1 (Q2 2026) | Phase 2 (Q4 2026) | Phase 3 (Q2 2027) | Phase 4 (Q4 2027) |
|---|---|---|---|---|
| **Instruments Connected** | 0 (dev/test only) | 10–20 | 100+ | 500+ |
| **Paying Customers** | 0 (alpha testing) | 2–5 pilots | 15–30 | 50+ |
| **MRR** | EUR 0 | EUR 3,000–8,000 | EUR 30,000–60,000 | EUR 150,000+ |
| **Instrument Parser Types** | 0 (cloud parsing only) | 5 | 15 | 25+ |
| **Platform Uptime** | N/A (dev) | >= 99% | >= 99.5% | >= 99.9% |
| **BioNexus Box Units Deployed** | 0 | 5–10 | 50+ | 200+ |
| **GMP4U Qual Packages Delivered** | 0 | 2–5 | 15+ | 50+ |
| **Test Coverage (backend API)** | 80%+ | 90%+ | 90%+ | 95%+ |
| **Audit Chain Integrity** | 100% (zero corruptions) | 100% | 100% | 100% |
| **Mean Time to Install (Box)** | N/A | < 4 hours | < 2 hours | < 1 hour |
| **Customer Onboarding Time** | N/A | < 2 weeks | < 1 week | < 3 days |
| **Net Promoter Score (NPS)** | N/A | > 30 | > 40 | > 50 |
| **Compliance Score (avg per instrument)** | N/A | > 85% | > 90% | > 95% |

### 10.2 Engineering Health Metrics (Tracked Continuously)

| Metric | Target |
|---|---|
| CI pipeline pass rate (last 30 days) | >= 95% |
| Mean time to resolve P1 incident | < 4 hours |
| Deployment frequency | >= 1 per week (Phase 1+) |
| Change failure rate | < 5% of deployments require rollback |
| Audit chain integrity check (daily scheduled job) | 0 corruption events |
| API p95 latency (read endpoints) | < 300ms |
| API p95 latency (write/certification endpoints) | < 1000ms |

### 10.3 Compliance Metrics

| Metric | Target |
|---|---|
| 21 CFR Part 11 self-assessment pass rate | 100% of applicable requirements addressed |
| Audit trail completeness (records with user attribution) | 100% |
| OTP expiry enforcement | 100% (zero OTP re-use events) |
| Cross-tenant data leakage incidents | 0 per year |
| Security vulnerability mean time to patch (critical) | < 48 hours |
| Customer IQ/OQ success rate | 100% (all IQ/OQ executions accepted by customer QA) |

---

## 11. Risks & Dependencies

### 11.1 Risk Register

| Risk | Probability | Impact | Phase Affected | Mitigation |
|---|---|---|---|---|
| **BioNexus Box hardware prototype delays** | High | High | Phase 2 | Begin hardware prototyping in Q1 2026 in parallel with software; identify CM partner early; have SBC-based prototype (Raspberry Pi CM4) ready for Q2 testing |
| **RS232 instrument variability** | High | Medium | Phase 2 | Build parser test framework with reference capture files; test parsers against physical instruments before customer deployment; maintain version registry per instrument model |
| **Slow customer validation cycles** | High | Medium | Phase 2–3 | GMP4U qualification package accelerates IQ/OQ; provide executed reference protocol; offer BioNexus-assisted IQ/OQ execution service to remove burden from customer |
| **Regulatory framework change** | Low | High | All | Monitor FDA and EMA guidance updates; GMP4U partnership provides early awareness; design for extensibility not hard-coded regulatory assumptions |
| **Security breach / data integrity incident** | Low | Critical | All | SHA-256 chain makes tampering detectable; multi-tenant isolation enforced at DB level; annual pen test from Phase 3; ISO 27001 from Phase 4 |
| **Key person dependency (GMP4U)** | Medium | High | Phase 2–3 | Formalize engagement with contract; build BioNexus internal GxP competency in parallel; identify secondary CSV consultancy by end of Phase 2 |
| **GCP cost overrun** | Medium | Medium | Phase 2+ | Cost budget alerts in GCP Billing; right-size Cloud SQL; implement Cloud Storage tiering (Coldline for old audit records); review monthly |
| **Parser quality failures at customer site** | Medium | High | Phase 2 | Every parser ships with a test dataset and automated validation; customer acceptance test of parser against their instrument before go-live; 30-day warranty period |
| **Competition from enterprise LIMS** | Low | Medium | Phase 3–4 | BioNexus is not competing for enterprise LIMS replacement; complementary positioning; speed and price differentiation protect SMB segment; monitor if LabWare/Benchling enter SMB market with lighter offerings |
| **Multi-tenant isolation failure** | Low | Critical | Phase 1+ | Explicit cross-tenant attack tests in test suite; tenant_id enforced at repository layer, not just service layer; quarterly security review of isolation controls |
| **React frontend performance on large audit trails** | Medium | Medium | Phase 2+ | Cursor-based pagination on all list views; virtual scrolling in audit log table; lazy load chart data; server-side aggregation for analytics |
| **OTP delivery failure (email/SMS)** | Medium | Medium | Phase 2+ | Fallback: if SMS fails, offer email OTP; retry with exponential backoff; alert on OTP delivery failure rate > 1%; monitor Twilio reliability |

### 11.2 Critical Path Dependencies

```
Phase 1 completion
     |
     +---> PostgreSQL on GCP (required before any customer data)
     +---> RBAC enforcement complete (required before multi-user customers)
     +---> CI/CD pipeline (required before hardware development)
     |
Phase 2 start
     |
     +---> Hardware prototype (CM for Box must be identified by end of Phase 1)
     +---> 5 validated parsers (requires physical instruments for testing — sourcing needed)
     +---> GMP4U qualification package (requires Phase 1 audit trail stable)
     +---> Billing system (required before first paid invoice)
     |
Phase 3 start
     |
     +---> Customer admin portal (required before > 10 customers — manual onboarding does not scale)
     +---> LIMS API (requires at least 1 LIMS partnership agreement signed)
     +---> Analytics backend (requires time-series data from > 5 deployed instruments)
     |
Phase 4 start
     |
     +---> SSO/SAML (requires Phase 3 multi-tenant hardening complete)
     +---> EU Annex 11 formal audit (requires 12+ months of production operation history)
     +---> OEM partnership (requires Phase 2 Box hardware production-ready)
```

### 11.3 Go / No-Go Gates

| Gate | Criteria | Consequence of Failure |
|---|---|---|
| Phase 1 → Phase 2 | All Phase 1 exit criteria met; GCP deployment live; GMP4U review completed | Extend Phase 1; delay hardware development |
| Phase 2 → Phase 3 | >= 2 paying customers; >= 1 Box deployed; GMP4U qual package delivered | Delay Phase 3 features; focus on closing first customers |
| Phase 3 → Phase 4 | >= 15 customers; >= 1 LIMS integration live; MRR >= EUR 30,000 | Delay enterprise/SSO features; focus on growth efficiency |
| ISO 27001 scope | >= 50 customers or any EU customer with contractual security requirement | Begin scoping earlier; cannot delay beyond H2 2027 for EU expansion |

---

## Appendix A — Visual Timeline

```
2026                                              2027                           2028+
Q1       Q2       Q3       Q4       Q1       Q2       H2
|--------|--------|--------|--------|--------|--------|--------|--------->

PHASE 1: MVP HARDENING
|================|
 RBAC, audit trail, PostgreSQL, CI/CD, React v1, GCP deploy

         PHASE 2: MARKET READY
         |================|
          Box hardware, 5 parsers, pilot customers, qual package, billing

                           PHASE 3: GROWTH
                           |================|
                            Multi-tenant SaaS, analytics, 15+ parsers,
                            LIMS integration, mobile app

                                             PHASE 4: SCALE
                                             |========================|-->
                                              SSO, EU Annex 11, ISO 27001,
                                              edge AI, OEM, marketplace,
                                              international

COMPLIANCE TRACK
|--GxP Master Doc (done)
|--21 CFR Self-Assessment--|
         |--GAMP5 Docs v1--|
                  |--IQ/OQ Execution--|
                           |--Qual Package v1--|
                                    |--Annex 11 Gap--|
                                             |--3rd Party Audit--|
                                                      |--ISO 27001 Scoping--|-->

GMP4U COLLABORATION
|==Design Review==|==Qual Package Dev==|==EU Market Prep==|==Ongoing======>

REVENUE TRACK
|--EUR 0--|--EUR 3K MRR--|--EUR 30K MRR--|--EUR 150K MRR-->
```

---

## Appendix B — Competitive Positioning by Phase

| Phase | BioNexus Position | Key Differentiator vs. Competitors |
|---|---|---|
| Phase 1–2 | "The fastest path to compliant instrument data capture for QC labs that can't afford a LIMS" | Same-day install vs. 12-month enterprise implementation; EUR 300/instrument/month vs. EUR 50,000+ LIMS |
| Phase 3 | "The connected QC lab platform — instrument data, analytics, and audit trail in one place" | Integrated hardware + analytics vs. Benchling (no hardware) or LabWare (no Plug & Play) |
| Phase 4 | "The validated GxP data infrastructure for regulated labs" | Formally validated, certified, and supported at enterprise scale with OEM hardware options |

---

*Document Version: 1.0 | Status: Active | Last Updated: 2026-02-28*
*Next Review: 2026-06-30 (end of Phase 1)*
*Owner: BioNexus Product & Engineering | Review Partner: GMP4U (Johannes Eberhardt)*
