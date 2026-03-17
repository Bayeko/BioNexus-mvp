# BioNexus Platform
**GxP-compliant laboratory instrument data capture and audit trail automation.**
BioNexus captures laboratory instrument data, validates it through a human-in-the-loop workflow, and produces certified reports with electronic signatures — all backed by an immutable SHA-256 audit chain.
Built for pharmaceutical, biotech, and CRO/CMO quality control laboratories operating under 21 CFR Part 11, EU GMP Annex 11, and GAMP5.
---
## Key Features
| Feature | Description | Compliance |
|---------|-------------|------------|
| **Smart Parser** | Upload instrument files (CSV, text) → automatic detection of instrument type → structured data extraction | ALCOA+ Accurate |
| **Human Validation** | AI-assisted parsing with mandatory human review (PENDING → VALIDATED / REJECTED) | EU Annex 11 cl.6 |
| **SHA-256 Audit Trail** | Every mutation recorded with cryptographic signature chaining. Immutable, read-only API. Tamper detection. | 21 CFR Part 11 §11.10(e) |
| **Electronic Signatures** | TOTP 2FA + password re-verification + structured signature meaning (5 values) | 21 CFR Part 11 Subpart C |
| **RBAC** | 5 roles: admin, principal_investigator, lab_technician, auditor (read-only), viewer (read-only) | 21 CFR Part 11 §11.10(d,g) |
| **Certified Reports** | PDF generation with chain integrity verification. Corrupted chain = report blocked. | 21 CFR Part 11 §11.10(b) |
| **Protocol Execution** | Step-by-step protocol tracking with data linking and orphan detection | ALCOA+ Complete |
| **Offline Persistence** | Write-Ahead Log (WAL) with SyncEngine, exponential backoff, congestion control | ALCOA+ Enduring |
| **3-Layer Timestamps** | source_timestamp (instrument) + hub_received_at (gateway) + server_received_at (cloud) | ALCOA+ Contemporaneous |
---
## Architecture
```
Instrument File (CSV/text)
        |
        v
  +---------------+
  |  Smart Parser  |  <- Pattern detection (HPLC, pH, balance, spectro, PCR)
  |  + SHA-256     |  <- Hash computed at upload (immutable)
  +-------+-------+
          v
  +---------------+
  |  Human         |  <- PENDING -> VALIDATED or REJECTED
  |  Validation    |  <- Corrections tracked in audit trail
  +-------+-------+
          v
  +---------------+
  |  Protocol      |  <- Step-by-step execution tracking
  |  Execution     |  <- Orphan detection + retroactive linking
  +-------+-------+
          v
  +---------------+
  |  Certified     |  <- Chain integrity verified before generation
  |  Report        |  <- E-signature: password + TOTP + meaning
  +---------------+
          |
          v
  Immutable SHA-256 Audit Trail (every step recorded)
```
---
## Test Coverage
**124 tests** (120 backend + 4 frontend), executed automatically on every commit via GitHub Actions.
| Category | Tests | Coverage |
|----------|-------|----------|
| Parsing + Data Integrity | 15 | SHA-256 hashing, file upload, schema validation, tamper detection |
| Execution Tracking | 12 | Protocol steps, data linking, orphan detection |
| Reporting + Certification | 12 | PDF generation, chain verification, immutability |
| E-Signature + TOTP | 10 | 2FA, signature meaning, signing workflow |
| Auth + JWT + RBAC | 9 | Tokens, role permissions, inactive users |
| Sample API + Audit | 13 | CRUD, audit trail, SHA-256 chain verification |
| Protocol API + Service | 10 | CRUD, validation, audit log |
| Instrument API | 7 | CRUD, serial number uniqueness, soft delete |
| Measurement API | 7 | CRUD, filters, data hash integrity |
| Audit Trail API | 7 | Read-only enforcement, filters, chain signature |
| Offline Persistence (WAL) | 5 | Local capture, idempotency, hash preservation |
| Sync Engine | 6 | Ingest, dedup, retry, backoff |
| Congestion Control | 7 | Adaptive batch, burst limit, clock drift detection |
| Frontend | 4 | Dashboard, Instruments, Audit pages render |
| **TOTAL** | **124** | **100% pass rate** |
---
## Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend API | Django REST Framework (Python 3.12) |
| Frontend | React 18 + TypeScript + Vite |
| Database | PostgreSQL 15+ |
| Authentication | JWT (access + refresh tokens) + TOTP 2FA (pyotp) |
| Data Validation | Pydantic (strict mode, extra="forbid") |
| Integrity | SHA-256 (hashlib) |
| PDF Reports | ReportLab |
| CI/CD | GitHub Actions (pytest + vitest on every push) |
| API Docs | Swagger UI via drf-spectacular |
---
## Quick Start
### Backend
```bash
cd bionexus-platform/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python create_demo_user.py
python manage.py runserver
```
- API: http://localhost:8000/
- Swagger: http://localhost:8000/api/docs/
- Demo login: `demo_user` / `DemoPassword123!`
### Frontend
```bash
cd bionexus-platform/frontend
npm install
npm run start
```
- Dashboard: http://localhost:3000/
### Run Tests
```bash
# Backend (120 tests)
cd bionexus-platform/backend
pytest -q
# Frontend (4 tests)
cd bionexus-platform/frontend
npm test
```
---
## QMS Documentation
| Document | Reference | Description |
|----------|-----------|-------------|
| SDLC Policy | LBN-SDLC-001 | Software Development Lifecycle (V-Model GAMP5, 3 pillars, Change Control) |
| GxP Compliance Master | LBN-GXP-001 | 21 CFR Part 11 + EU Annex 11 + ALCOA+ conformity matrix |
| System Validation Plan | LBN-VAL-001 | IQ/OQ/PQ protocols, 138 test cases, deviation management |
| Data Capture Architecture | LBN-ARCH-003-CURRENT | Current architecture (file upload -> parsing -> validation) |
| Plug & Play Architecture | LBN-ARCH-003 | Target architecture (BioNexus Box -> auto-detection -> parsers) |
| Box Hardware Architecture | LBN-HW-001 | Raspberry Pi gateway, WAL, SyncEngine, 3-layer timestamps |
---
## Regulatory Alignment
| Standard | Coverage |
|----------|----------|
| FDA 21 CFR Part 11 | Electronic records, electronic signatures, audit trail, access control |
| EU GMP Annex 11 | Computerised systems validation, data storage, change control, security |
| ISPE GAMP5 2nd Ed. | Category 5 custom software, V-Model, risk-based validation |
| FDA CSA 2025 | Computer Software Assurance, risk-based testing approach |
| ICH Q9 / Q10 | Quality Risk Management, Pharmaceutical Quality System |
| PIC/S PI 011-3 | ALCOA+ data integrity principles |
---
## Project Structure
```
bionexus-platform/
  backend/
    core/                    # Core platform
      models.py              # AuditLog, RawFile, ParsedData, CertifiedReport, RBAC
      audit.py               # SHA-256 signature chaining
      api_views.py           # E-signature (TOTP + meaning)
      parsing_service.py     # File upload + hash
      parsing_schemas.py     # Pydantic strict schemas
      reporting_service.py   # PDF certified reports
      tests/                 # 63 core tests
    modules/
      instruments/           # Instrument CRUD + audit (7 tests)
      measurements/          # Measurement CRUD + hash (7 tests)
      samples/               # Sample CRUD + chain verification (13 tests)
      protocols/             # Protocol CRUD + service (10 tests)
      persistence/           # WAL, SyncEngine, Congestion (18 tests)
    requirements.txt
  frontend/
    src/
      App.jsx
      routes.jsx
      __tests__/             # 4 frontend tests
    package.json
  .github/workflows/ci.yml  # CI: pytest + vitest on every push
```
---
## License
Proprietary — Lab BioNexus. All rights reserved.
---
## Contact
**Amir Messadene** — Founder, Lab BioNexus
- Background: Biotechnology Engineering (Lonza, Roche)
- Email: messadene.amir@gmail.com
