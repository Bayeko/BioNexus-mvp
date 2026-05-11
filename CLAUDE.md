# CLAUDE.md — BioNexus MVP

## Project Overview
BioNexus is a SaaS + hardware platform for laboratory instrument data integration, compliance, and traceability. It combines a physical gateway device ("BioNexus Box") with a cloud-based platform that captures, stores (SHA-256), and audits data from laboratory analyzers in GxP-regulated environments.

## Tech Stack
- **Backend:** Django REST Framework (Python 3.12+)
- **Frontend:** React (planned)
- **Database:** PostgreSQL
- **Cloud:** Google Cloud Platform
- **Hardware Interface:** RS232/USB via BioNexus Box gateway
- **Auth:** JWT-based authentication
- **Compliance:** 21 CFR Part 11, GAMP5, EU Annex 11

## Architecture
[Lab Instruments] → RS232/USB → [BioNexus Box] → HTTPS → [GCP Backend]
                                                            ├── Django REST API
                                                            ├── PostgreSQL (Audit Trail)
                                                            ├── SHA-256 Data Integrity
                                                            └── React Dashboard (planned)

## Key Concepts
- **Audit Trail**: Immutable log of all data transactions, compliant with 21 CFR Part 11
- **BioNexus Box**: Plug & Play hardware gateway connecting lab instruments to cloud
- **Data Integrity**: SHA-256 hashing ensures no data tampering
- **No PII Policy**: System handles pseudonymized sample IDs only, never patient data
- **GxP Compliance**: All features designed for pharmaceutical/biotech regulatory requirements

## Current Sprint Priorities
1. Sample tracking API endpoints (CRUD + audit trail)
2. Instrument registration & status monitoring
3. Audit trail immutability enforcement
4. User authentication with role-based access control

## Code Standards
- Python: PEP 8, type hints on all functions
- Django: Fat models, thin views. Business logic in model methods or services.
- API: RESTful conventions. All endpoints return JSON. Paginated list responses.
- Testing: Every endpoint needs at least one happy-path and one error test
- Security: No hardcoded secrets. Use environment variables.
- Commits: Conventional commits (feat:, fix:, docs:, refactor:)

## Business Context
- **Target customers**: QC labs in pharma/biotech SMBs (50-500 employees)
- **Competitors**: LabWare LIMS, STARLIMS, Benchling
- **Differentiator**: Plug & Play hardware + SaaS vs. 12-month enterprise implementations
- **Partnership**: GMP4U (Johannes Eberhardt) — CSV/qualification specialist
- **Revenue model**: Setup fee + monthly SaaS subscription per instrument

## Commands
python manage.py runserver    # Run dev server
python manage.py test         # Run tests
python manage.py migrate      # Run migrations
