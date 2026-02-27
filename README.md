# BioNexus MVP

## Overview

**BioNexus MVP** is a **GxP-compliant laboratory data management platform** designed for FDA-regulated labs. It enforces **21 CFR Part 11** and **ALCOA+** compliance through immutable audit trails, cryptographic chain verification, and double-authentication certification.

### Core Workflow

1. **Upload** — User uploads a CSV/PDF data file
2. **Parse** — AI parser extracts structured data with a confidence score
3. **Review** — User reviews in a split-view (original file + validation form), making corrections tracked with full provenance
4. **Verify** — Chain integrity is verified every 30s via SHA-256 signature chaining
5. **Certify** — User certifies the report with double authentication (password + OTP)
6. **Report** — A tamper-proof certified report is generated with SHA-256 signature

---

## Tech Stack

| Layer          | Technology                                           |
|----------------|------------------------------------------------------|
| **Backend**    | Django 5.2, Django REST Framework, Python 3.11       |
| **Frontend**   | React 18, React Router v6, TypeScript (partial), Vite 5 |
| **Database**   | PostgreSQL (production) / SQLite (development)       |
| **Auth**       | JWT (15min access / 7d refresh), OTP for certification |
| **Testing**    | pytest (backend), Vitest + React Testing Library (frontend) |
| **Infra**      | Docker Compose, GitHub Actions CI                    |

---

## Project Structure

```
BioNexus-mvp/
├── bionexus-platform/
│   ├── docker-compose.yml              # Orchestrates all services
│   ├── backend/
│   │   ├── manage.py                   # Django CLI entry point
│   │   ├── requirements.txt
│   │   ├── core/                       # Core Django app
│   │   │   ├── models.py              # 13 models (AuditLog, Tenant, User, ParsedData, etc.)
│   │   │   ├── api_views.py           # REST endpoints for parsing/validation
│   │   │   ├── auth_views.py          # Login/logout endpoints
│   │   │   ├── jwt_service.py         # JWT token management
│   │   │   ├── audit.py               # Immutable audit trail (SHA-256 chain)
│   │   │   ├── parsing_service.py     # File parsing & data extraction
│   │   │   ├── parsing_schemas.py     # Pydantic validation schemas
│   │   │   ├── reporting_service.py   # Certified report generation
│   │   │   ├── execution_service.py   # Protocol execution tracking
│   │   │   └── tests/                 # Backend unit tests
│   │   └── modules/
│   │       ├── samples/               # Sample CRUD with soft-delete
│   │       └── protocols/             # Protocol CRUD with soft-delete
│   └── frontend/
│       ├── package.json
│       └── src/
│           ├── main.jsx               # React DOM mount point
│           ├── App.jsx                # Root component with BrowserRouter
│           ├── routes.jsx             # Route definitions
│           ├── config.ts              # Feature flags & compliance settings
│           ├── components/
│           │   └── ParsingValidation/ # Split-view UI components
│           │       ├── ParsingValidationComponent.tsx
│           │       ├── DynamicFormBuilder.tsx
│           │       ├── RawFileViewer.tsx
│           │       ├── CorrectionTracker.tsx
│           │       ├── ChainIntegrityBadge.tsx
│           │       └── CertificationModal.tsx
│           ├── services/              # API clients (parsing, integrity, crypto)
│           └── __tests__/             # Frontend tests
├── conftest.py                        # Pytest configuration
├── DOCUMENTATION.md                   # Full technical documentation (FR)
├── QUICK_START.md                     # Quick start guide with workflow examples
└── WINDOWS_SETUP.md                   # Windows installation guide
```

---

## Main Entry Points

| Entry Point            | Path                                          | Purpose                                           |
|------------------------|-----------------------------------------------|---------------------------------------------------|
| **Django manage.py**   | `bionexus-platform/backend/manage.py`         | Backend CLI (`runserver`, `migrate`, etc.)         |
| **React main.jsx**     | `bionexus-platform/frontend/src/main.jsx`     | Frontend DOM mount                                |
| **Docker Compose**     | `bionexus-platform/docker-compose.yml`        | Orchestrates backend (:8000), frontend (:3000), Postgres (:5432) |

---

## API Surface

| Domain             | Endpoints                                                  |
|--------------------|------------------------------------------------------------|
| **Auth**           | `POST /auth/login/`, `/auth/logout/`, `/auth/refresh/`    |
| **Samples**        | CRUD at `/api/samples/`                                    |
| **Protocols**      | CRUD at `/api/protocols/`                                  |
| **Parsing**        | Upload, review, validate, sign, PDF at `/api/parsing/`     |
| **Executions**     | Tracking protocol runs at `/api/executions/`               |
| **Audit**          | Chain verification at `/api/audit/verify-chain/`           |
| **Reports**        | Certified PDFs at `/api/reports/{id}/pdf/`                 |

---

## Key Data Models

- **AuditLog** — Immutable audit records with SHA-256 chain signatures
- **Tenant** — Multi-tenant organization/laboratory isolation
- **User** — Custom user model with role-based access (admin, PI, lab tech, auditor, viewer)
- **RawFile** — Immutable uploaded file storage with SHA-256 hash
- **ParsedData** — AI-extracted data with state machine (pending → validated → certified)
- **CorrectionTracker** — Provenance for every user correction (field, before/after, reason, timestamp)
- **ExecutionLog / ExecutionStep** — Protocol execution tracking with measurements
- **Equipment** — Lab equipment registry with calibration tracking
- **CertifiedReport** — Final immutable report with cryptographic signature
- **Sample** / **Protocol** — Core lab entities with soft-delete for audit compliance

---

## Compliance & Security

- **21 CFR Part 11** — Immutable audit trail, electronic signatures, user identification
- **ALCOA+** — Attributable, Legible, Contemporaneous, Original, Accurate, Complete, Consistent, Enduring, Available
- **Chain Integrity** — SHA-256 signature chaining across all audit records; tampering breaks the chain and triggers alerts
- **Double Authentication** — Password re-entry + OTP required for report certification
- **Soft Delete** — Data is never physically deleted; all deletions are reversible and auditable

---

## Installation

### Via Docker

```bash
cd bionexus-platform
docker compose up --build
```

- Backend: http://localhost:8000/
- Frontend: http://localhost:3000/

### Manual Installation

#### Backend (Django)

```bash
cd bionexus-platform/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

API available at http://127.0.0.1:8000/

#### Frontend (React)

```bash
cd bionexus-platform/frontend
npm install
npm run start
```

UI available at http://localhost:3000/

---

## Tests

- **Backend**: from `bionexus-platform/backend`, run `pytest`
- **Frontend**: from `bionexus-platform/frontend`, run `npm test`

---

## Contributing

1. Create a `feature/...` branch for each feature or fix.
2. Submit a Pull Request to `main` with a concise description.
3. Ensure all tests pass before requesting review.

---

## License

TBD (e.g. MIT, Apache 2.0, etc.)
