# Lab BioNexus — context.md

## Project meta

- **Repo**: `C:\Users\LENOVO\BioNexus-mvp` (Windows clone of `Bayeko/BioNexus-mvp` on GitHub)
- **Branch**: `main` (10 latest CI runs RED — root cause fixed locally, not yet pushed)
- **Founder**: Bayeko / Amir Messadene (solo, pre-revenue)
- **Stack**: Django 5.2 + DRF (backend), React 18 + Vite 5 (frontend), Python 3.12 + Node 24 LTS (just installed), SQLite dev / Postgres prod
- **Test status (local)**: 192 backend + 76 box + 16 frontend = 284 passed
- **Local venv**: `C:\Users\LENOVO\BioNexus-mvp\.venv` (Python 3.12.10)
- **Compliance scope**: 21 CFR Part 11, GAMP5, EU Annex 11 — every change has audit/validation weight

## Current phase

Phase 4 — Code (COMPLETED 2026-05-12, multi-LIMS suite)
411 tests green (395 backend+box + 16 frontend).

Previously: Mock Vault solo (completed earlier same day, 384 tests).

## Active task

**LBN-INT-VEEVA-001 — Veeva Vault QMS integration: partner program signup + integration design**

User goal (two-step):
1. Sign up for the Veeva Product Partner program (free, gets us a Vault sandbox eventually)
2. Once sandbox arrives (weeks/months later), code the integration per [docs/VEEVA_INTEGRATION_SPEC.md](docs/VEEVA_INTEGRATION_SPEC.md) v0.1 DRAFT

### Recon findings (2026-05-12)

- Signup form lives at https://www.veeva.com/meet-veeva/partners/become-a-partner/
- The form itself is **minimal** — 2 visible dropdowns:
  - "What kind of partner are you interested in becoming?" → option **"Product"** is the right choice
  - "Which region is your business primarily in?" → option **"Europe"**
- The form likely also collects standard contact fields (name, email, company, phone) — WebFetch did not extract them but inquiry forms always have these
- Submitting the form is **just an inquiry trigger**. Veeva replies manually (1-8 weeks typical for ISV partner programs). Sandbox is NOT automatic — it follows a human conversation about the business case.
- Veeva also runs a separate **AI Partner Program** (https://www.veeva.com/meet-veeva/partners/ai/) which explicitly grants "Veeva Vault software and Veeva Vault Direct Data API access" — only relevant if LBN positions as AI-adjacent. Currently the spec is QMS integration, not AI, so Product Partner is correct.

### Problem statement

There are actually three sub-tasks being conflated:

1. **The form click** — trivial. Two dropdowns + contact info. Manual user fill is faster than launching a Chrome MCP agent.
2. **The follow-up conversation with Veeva** — non-trivial, requires Amir to articulate the LBN business case in an email exchange with a real human at Veeva. No MCP can do this.
3. **The integration code** — premature to design until we know whether Veeva approves and on what tier. Different tiers may grant different sandbox capabilities (full Vault QMS vs. limited).

### GxP/QMS implications

- The signup itself has no GxP weight (no code, no validation).
- The future integration code WILL touch 21 CFR Part 11 §11.10 attribution (HMAC signing, audit chain push). When designing Phase 2 later, treat as GAMP5 Cat 5 (custom software) requiring formal validation.

### Design notes — Mock Vault for FL Basel demo (Phase 2)

**Decision (2026-05-12)**: Build Mock Vault NOW (before Veeva responds). Reasons:
- FL Basel will likely arrive before Veeva approval (4-8wk lead time on partner programs)
- Demo asset has standalone value: "yes we have Veeva integration, here it is in action"
- Mock written against the spec is straight-line portable to real sandbox (swap base URL, swap auth scheme)
- Cost of being wrong: low — code lives behind a feature flag (`VEEVA_INTEGRATION_ENABLED=false` by default)

**Architecture — Strategy pattern with 3 clients behind a single interface:**

```
backend/modules/integrations/
└── veeva/
    ├── __init__.py
    ├── apps.py
    ├── client.py             # Abstract VeevaClient + Mock/Sandbox/Prod impls
    ├── field_mapping.py      # Measurement → quality_event__v JSON
    ├── signing.py            # HMAC-SHA256 outbound signature
    ├── retry.py              # Exponential backoff + DLQ
    ├── models.py             # IntegrationPushLog (audit trail of every push)
    ├── service.py            # High-level push_measurement(m), push_report(r)
    ├── signals.py            # post_save(Measurement) → service.push_measurement()
    ├── views.py              # GET /api/integrations/veeva/log/ + /status/
    ├── urls.py
    ├── management/
    │   └── commands/
    │       └── veeva_mock_server.py   # Standalone HTTP mock Vault on :8001
    └── tests/
        ├── test_client_mock.py
        ├── test_field_mapping.py
        ├── test_signing.py
        ├── test_retry.py
        └── test_push_integration.py   # End-to-end signal → push
```

**Mode selection via env:**
- `VEEVA_MODE=disabled` (default, prod-safe) — no-op, no network
- `VEEVA_MODE=mock` — points at `http://localhost:8001` (the mock server)
- `VEEVA_MODE=sandbox` — points at real sandbox URL when we have one (`VEEVA_SANDBOX_URL`)
- `VEEVA_MODE=prod` — production (intentionally hard to enable: needs `VEEVA_PROD_CONFIRMED=true` too)

**Mock server contract** (loosely follows real Veeva REST v23.1):
- `POST /api/v23.1/auth` → returns fake `sessionId`
- `POST /api/v23.1/vobjects/quality_event__v` → returns `{ id: "VVQE-<uuid>", responseStatus: "SUCCESS" }`
- `POST /api/v23.1/objects/documents` → returns `{ id: "VVDOC-<uuid>", responseStatus: "SUCCESS" }`
- Failure injection via `VEEVA_MOCK_FAIL_RATE=0.0..1.0` (default 0) for demoing retry
- Persists pushed objects to a sqlite file in `/tmp/veeva_mock/` so the demo can show "objects received"

**Field mapping** (from spec [docs/VEEVA_INTEGRATION_SPEC.md](docs/VEEVA_INTEGRATION_SPEC.md)):
| BioNexus | Vault object/field | Direction |
|---|---|---|
| Measurement (value, unit, parameter, source_timestamp) | `quality_event__v` core fields | push |
| Operator ID (pseudonymized) | `reported_by__v` | push |
| Lot number | `lot__v` | push |
| AuditLog SHA-256 chain entry | embedded in payload `audit_chain__v` | push |
| CertifiedReport PDF | `document__v` attachment | push |

**Audit trail**: every push attempt → `IntegrationPushLog` row → also emits a Django signal that adds an `AuditLog` entry (so SHA-256 chain captures the push fact).

**Frontend Design — Integrations.jsx Veeva card refresh:**
- New status: `mock_active` (badge: amber "MOCK MODE — not connected to production Vault")
- Add "Live push log" panel showing last 10 push attempts (status, target object ID, timestamp, latency)
- Per skill `references/frontend-react-tailwind.md` direction: refined-industrial — fixed-width hash columns, monospace IDs, no slop gradients

**What is explicitly OUT OF SCOPE for this iteration:**
- Production Veeva pushes (gated)
- Multi-tenant Vault credentials per BioNexus tenant (one client = one Vault tenant for v1, per spec §2)
- Bidirectional sync (spec is push-only)
- VQL queries
- Frontend "Setup wizard" for mapping profiles

### Plan — Mock Vault build (Phase 3)

Atomic steps. Each is one commit-sized unit with an explicit verification criterion.

1. **Create app skeleton** `backend/modules/integrations/__init__.py` and `backend/modules/integrations/veeva/{__init__,apps}.py`. Register in `INSTALLED_APPS`. Verify: `python manage.py check` passes.
2. **`IntegrationPushLog` model** with fields: tenant, target_object_type, target_object_id (nullable until response), source_measurement_id, payload_hash, http_status, response_id, error, attempts, mode, created_at. Migration. Verify: `python manage.py makemigrations integrations_veeva` produces a migration that applies cleanly.
3. **`signing.py`** — HMAC-SHA256 of canonical JSON payload, with `compute_signature(payload: dict, secret: str) -> str`. Unit tests covering: deterministic output, secret-sensitive output, payload-canonical (key order independence). Verify: `pytest backend/modules/integrations/veeva/tests/test_signing.py` green.
4. **`field_mapping.py`** — `measurement_to_quality_event(m: Measurement) -> dict` mapping per the table above. Pure function. Tests: golden-file style, asserts every spec field is present. Verify: `pytest .../test_field_mapping.py` green.
5. **`client.py`** abstract `VeevaClient` + `MockVeevaClient` (HTTP). Methods: `authenticate()`, `push_quality_event(payload, signature)`, `push_document(file, metadata)`. Mock client uses real HTTP via `requests` against `VEEVA_BASE_URL`. Tests use `requests-mock` or hit a launched mock server fixture. Verify: tests green.
6. **`retry.py`** — Exponential backoff with jitter, max 5 retries, DLQ to `IntegrationPushLog.error`. Tests: retries on 5xx, gives up on 4xx, exponential delay correct. Verify: `pytest .../test_retry.py` green.
7. **`service.py`** — `push_measurement(measurement: Measurement) -> IntegrationPushLog` orchestrating field_mapping → signing → client.push → log. Idempotency via measurement.data_hash. Verify: integration test.
8. **`signals.py`** — `post_save(Measurement)` → if `VEEVA_INTEGRATION_ENABLED` → service.push_measurement async (queued; no DB transaction blocking). Wire into `apps.py:ready()`. Verify: end-to-end test creates Measurement, asserts IntegrationPushLog row.
9. **Mock server** — `manage.py veeva_mock_server` Django command running `http.server` on :8001. Endpoints: `/api/v23.1/auth` (returns sessionId), `/api/v23.1/vobjects/quality_event__v` (returns VV ID), `/api/v23.1/objects/documents` (returns VVDOC ID). Failure injection via `VEEVA_MOCK_FAIL_RATE`. Persists to sqlite at `/tmp/veeva_mock/objects.db`. Verify: manual curl smoke test.
10. **Views + URLs** — `GET /api/integrations/veeva/log/?limit=50` listing push log, `GET /api/integrations/veeva/status/` returning current mode + counts. Wire into `core/urls.py`. Verify: `pytest .../test_views.py`.
11. **Frontend — Integrations.jsx update** — Veeva card status `mock_active` (amber MOCK MODE badge), with embedded push log panel fetching `/api/integrations/veeva/log/`. Per skill frontend guide: monospace IDs, fixed-width columns, no decorative gradients, status colors WCAG AA. Verify: vitest still green + manual browser check.
12. **Settings additions** — `VEEVA_MODE`, `VEEVA_BASE_URL`, `VEEVA_SHARED_SECRET`, `VEEVA_INTEGRATION_ENABLED`, `VEEVA_MOCK_FAIL_RATE` in `core/settings.py` reading from env with sane defaults. Add to `.env.example`. Verify: server starts, `/api/integrations/veeva/status/` returns expected JSON.
13. **README + spec linkage** — Add "Veeva Vault Integration" section to README. Update [docs/VEEVA_INTEGRATION_SPEC.md](docs/VEEVA_INTEGRATION_SPEC.md) §3 "Architecture" with the actual landing code paths.
14. **Demo script** — `bionexus-platform/box/demo_veeva.py` (or similar): captures a measurement, shows the push request flying, shows the IntegrationPushLog entry, shows the AuditLog chain advance. Verify: runs end-to-end on fresh checkout.
15. **Full test suite check** — backend + box + frontend all green. Verify: 284+ tests still pass (modulo new tests added by this work).

**Estimated size**: ~1500-2000 lines of code, 30+ tests, ~1 working day. Each step is small enough to commit independently.

**Step-touching-GxP-locked-code flag**: Steps 7, 8 (signals, service) touch the Measurement post-save path which is in the audit chain. Must NOT break the existing chain — verified by re-running existing `test_audit_api.py` after step 8.

## Decisions log (append-only)

- **2026-05-12** — Chose Veeva Product Partner program (not AI Partner program). Rationale: LBN positioning is QMS integration via API, not GenAI-on-Vault. Product Partner has tiers Gold/Silver/Base/Integration; entry is "Integration Partner" tier.
- **2026-05-12** — Chose to NOT pay for Vault Developer Edition. Rationale: spec target is Q3 2026 post-first-deal; building Veeva integration before a client demands it inverts the order. Free sandbox via partner program is the right path.
- **2026-05-12** — Decided that the signup form is too small (2 dropdowns) to justify launching a Chrome MCP browser agent. Manual fill by Amir (30s) is more efficient. MCP agent reserved for the real grunt work (later).
- **2026-05-12** — Build Mock Vault now (before real sandbox arrives). Strategy pattern (mock/sandbox/prod clients behind one interface), feature-flag gated, with a Django management command that runs a standalone HTTP mock server on :8001. Lets us demo Veeva integration at FL Basel without depending on Veeva approval timing.
- **2026-05-12** — Mock Vault lives in `backend/modules/integrations/veeva/` (new Django app under modules/). Adds an `IntegrationPushLog` model so every push event is captured in the SHA-256 audit chain — preserves the GxP audit trail discipline even in mock mode.
- **2026-05-12** — User picked Option C (build full LIMS suite mocks) against my recommendation (Option A: just abstract + wait for customer signal). Acknowledged: more code surface to maintain, mappings are speculative. Will mitigate by (a) generalizing the Veeva infra into `BaseLimsConnector` so each new vendor reuses 80%+ of code, (b) marking every connector clearly as `mock_active` so we never claim production support without sandbox testing.

## Open questions / Parked

- **Q1 (BLOCKING — see clarifying question below)**: Does Amir want me to launch a Chrome agent to fill a 2-field form, OR is he OK clicking submit himself in 30 seconds? My strong recommendation is manual.
- **Q2 (PARKED, post-Veeva-reply)**: Which Veeva sandbox tier does the partner-program approval grant? Determines what we can build.
- **Q3 (PARKED, design-phase)**: Mock Vault server first (for FL Basel demo without real sandbox) vs. wait for real sandbox? My current lean is: build the mock now, port to real sandbox when it arrives.

## Outcomes (this session)

- **Multi-LIMS connector suite COMPLETE** (Option C executed against my Option A recommendation):
  - New `modules/integrations/base/` package: `BaseLimsClient` + `DisabledLimsClient` + `HttpLimsClient` + `build_client` factory, shared `signing.py`, shared `service.push_to_vendor`, parameterized mock handler with vendor registry.
  - Veeva refactored to inherit from `base/` (100/100 Veeva tests still green after refactor).
  - 4 new vendor modules under `modules/integrations/lims_connectors/{empower,labware,starlims,benchling}/` — each ~250 LOC (client + field_mapping + service + signals + mock_routes).
  - Unified mock server: one `python manage.py lims_mock_server` command serves all 5 vendor flavours on `:8001` (paths under `/veeva`, `/empower`, `/labware`, `/starlims`, `/benchling`).
  - `IntegrationPushLog` gained a `vendor` field (migration 0002) — one table for all 5 vendors.
  - Settings + `.env.example` for every vendor (`<VENDOR>_MODE`, `<VENDOR>_INTEGRATION_ENABLED`, `<VENDOR>_BASE_URL`, `<VENDOR>_SHARED_SECRET`, vendor-specific auth tokens).
  - Frontend `Integrations.jsx`: added STARLIMS card (was missing entirely), bumped Empower/LabWare/STARLIMS/Benchling to `mock_active`, generalized `LimsPushLogPanel` (`vendor` prop) so every vendor's card has its own filtered live push log.
  - `/api/integrations/veeva/{status,log}/` endpoints now accept `?vendor=<name>` filter.
  - `demo_lims.py`: single Measurement → 4 simultaneous pushes (one per vendor) demonstrated end-to-end.
- **Test growth**: 384 → 411 tests (+27 new; +25 lims_connectors + 2 view filter tests).

### Previously this day:

- **Mock Vault build COMPLETE** — all 15 plan steps shipped:
  - New Django app `modules.integrations.veeva/` (~1100 LOC code + tests)
  - `IntegrationPushLog` model + migration applied
  - `signing.py` (HMAC-SHA256 canonical JSON) + 19 tests
  - `field_mapping.py` (Measurement → quality_event__v) + 13 tests
  - `client.py` (Disabled/Mock/Sandbox/Prod clients via factory) + 20 tests
  - `retry.py` (exponential backoff + DLQ) + 25 tests
  - `service.py` (push orchestration + idempotency via payload_hash) + 11 tests
  - `signals.py` (post_save Measurement → Veeva push) + 5 e2e tests
  - `manage.py veeva_mock_server` (stdlib HTTP mock Vault on :8001) — smoke tested
  - `/api/integrations/veeva/{status,log}/` endpoints + 7 view tests
  - Frontend Veeva card: live MOCK MODE badge + 5s-refreshing push log table
  - Settings + `.env.example` with VEEVA_MODE/INTEGRATION_ENABLED/BASE_URL/SHARED_SECRET/MOCK_FAIL_RATE
  - README "Veeva Vault QMS integration" section
  - `demo_veeva.py` end-to-end demo runnable for FL Basel
- **All tests green**: 368 backend+box passed, 16 frontend passed = 384 total

## Recent outcomes (rolling, last ~5)

- **2026-05-12** — Added `WatersEmpowerParser` + `DissolutionASCIIParser` to [bionexus-platform/box/box_collector.py](bionexus-platform/box/box_collector.py) with 19 tests. All green.
- **2026-05-12** — Deleted dead code: `backend/modules/persistence/parsers/{mettler_sics,sartorius_sbi}.py` (unused, marked PROTOTYPE).
- **2026-05-12** — Identified root cause of CI red on `main` (10+ runs): both `conftest.py` files called `migrate()` at import, racing pytest-django's DB blocker. Fixed locally.
- **2026-05-12** — Fixed `Routes.test.jsx` assertion (`/audit log/i` → `/audit trail/i` matching the actual page heading per 21 CFR Part 11 terminology).
- **2026-05-12** — Corrected README misclaim about "TypeScript (partial)" frontend — no `.ts`/`.tsx` files exist; updated Tech Stack and Project Structure sections.

## Archive pointer

(none yet — file is fresh and well under 400 lines)
