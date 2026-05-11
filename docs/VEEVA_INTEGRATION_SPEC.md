# Veeva Vault QMS Integration Specification

**Document ID** : LBN-INT-VEEVA-001 (INTERNAL track)
**Version** : 0.1 DRAFT
**Date** : 2026-05-11
**Classification** : INTERNAL · Engineering
**Target ship window** : Q3 2026 (post FL Basel + post first deal)

---

## 1. Why Veeva first

Per the D6 baseline (2026-05-11), Veeva Vault QMS is the strategically chosen first LIMS / QMS connector because :

- **Modern API surface**: REST + OAuth2 + VQL (Vault Query Language). No SOAP, no COM bridge. Fastest time-to-functional integration of the four candidate systems (Veeva / LabWare / STARLIMS / Empower).
- **Fastest build estimate**: 2 to 3 weeks per the D6 effort matrix. Empower is 4 to 6 weeks. LabWare is 3 to 4 weeks. STARLIMS is 4 to 5 weeks.
- **Highest growth trajectory in target ICP**: Vault QMS is becoming the new standard for mid-pharma quality systems. Owning an early integration positions Labionexus as a Vault-native option.
- **Demo asset value**: even before signing a Vault-using client, the integration becomes a credible answer to "do you connect to our QMS ?" during discovery.

## 2. Scope of v1 (this spec)

The v1 integration provides a one-way push of measurement events from Labionexus to Veeva Vault QMS, with audit trail attachment. Full bidirectional sync is out of scope for v1.

**In scope** :
- OAuth2 authentication against a Veeva Vault sandbox tenant
- Push of `Measurement` records into the `quality_event__v` Vault object
- Push of the relevant `CertifiedReport` PDF as a Vault `document__v` attachment
- HMAC-SHA256 signature on the outbound payload (defense in depth on top of TLS)
- Retry with exponential backoff and dead-letter queue
- One field mapping profile per client tenant (multi-profile defer)

**Explicitly out of scope for v1** :
- Veeva to Labionexus pull (we only push)
- Multi-tenant Vault credentials in a single Labionexus deployment (one client = one Vault tenant)
- VQL-driven dynamic queries on the Vault side
- Sample lifecycle synchronization (samples stay master-of-record in Labionexus)
- Production tenant qualifications (sandbox only until first client requires production)

## 3. Architecture

```
Labionexus Box  ─►  Labionexus SaaS (Django)  ─►  Veeva Vault QMS (sandbox)
                          │
                          ├── Measurement created (signal)
                          │
                          ▼
                    VeevaPushService (background task)
                          │
                          ├── Refresh OAuth token if expired
                          ├── Map fields per VeevaConnection.field_mapping_json
                          ├── POST to /api/v23.1/objects/quality_event__v
                          ├── Attach CertifiedReport PDF
                          └── Write AuditLog entry with response payload
```

Every push event is recorded in the Labionexus `AuditLog` chain as an entry of type `VeevaPush` (operation `CREATE`). The Vault response identifier is captured in `snapshot_after` so the chain of custody is auditable from Box capture all the way to Vault ingest.

## 4. Data model (proposed)

A new Django model `VeevaConnection` per client tenant :

| Field | Type | Notes |
|-------|------|-------|
| `tenant_id` | FK or string | one connection per Labionexus tenant |
| `sandbox_url` | URL | e.g. `https://xyz.veevavault.com` |
| `client_id` | CharField | OAuth2 client ID |
| `client_secret_enc` | EncryptedTextField | AES-encrypted at rest |
| `access_token_enc` | EncryptedTextField | refreshed automatically |
| `refresh_token_enc` | EncryptedTextField | |
| `token_expires_at` | DateTime | UTC |
| `field_mapping_json` | JSONField | see Section 5 |
| `is_active` | Boolean | soft disable |
| `created_at` / `updated_at` | DateTime | |

Field mappings are stored as JSON, not as a separate table, to keep the v1 footprint small and allow per-client customization without migrations.

## 5. Field mapping prototype (v1)

The default mapping for the v1 prototype is hardcoded as follows, then overridable per `VeevaConnection.field_mapping_json` :

| Labionexus field | Veeva field | Direction |
|------------------|-------------|-----------|
| `Measurement.id` (as string with prefix `LBN-M-`) | `name__v` | push |
| `Measurement.parameter` | `parameter__c` | push |
| `Measurement.value` (as string) | `result_value__c` | push |
| `Measurement.unit` | `result_unit__c` | push |
| `Measurement.measured_at` | `event_date__v` | push |
| `MeasurementContext.operator` | `reported_by__v` | push |
| `MeasurementContext.lot_number` | `lot__c` | push |
| `MeasurementContext.method` | `method__c` | push |
| `Measurement.data_hash` | `integrity_hash__c` | push |
| `AuditLog.signature` (latest for this entity) | `audit_signature__c` | push |
| `CertifiedReport.pdf` (if any) | `document__v` (attached) | push |

`__v` suffix = Veeva standard fields. `__c` suffix = Vault custom fields the client must create in their tenant. The integration emits the list of required custom fields as part of the connection wizard.

## 6. Authentication flow

1. Admin enters Vault sandbox URL + client_id + client_secret in the Labionexus admin UI (`/admin/integrations/veeva/connect`).
2. Labionexus redirects to the Vault OAuth authorization endpoint.
3. Vault redirects back with an authorization code.
4. Labionexus exchanges the code for an access token + refresh token, encrypted at rest.
5. The "Test connection" button on the admin UI calls a Vault read-only endpoint (e.g. `/api/v23.1/objects/document__v` with `LIMIT 1`) to confirm credentials are live.

Token rotation : the push service checks `token_expires_at` before every batch and refreshes if within 5 minutes of expiry. Failed refresh raises a P1 incident (per `incident-response-runbook.md`).

## 7. Error handling

| Scenario | Behaviour |
|----------|-----------|
| Vault returns 401 | Refresh token, retry once, then mark `VeevaConnection.is_active=False` and raise P1 |
| Vault returns 4xx (validation) | Record in dead-letter queue, do not retry. Surface in admin UI. |
| Vault returns 5xx | Retry with exponential backoff (1s, 2s, 4s, ...) up to 5 minutes |
| Network timeout | Same as 5xx |
| Connection refused | Same as 5xx, raise P2 alert after 3 failed batches |

Every error is logged in the `AuditLog` with `operation='ERROR'` for the `VeevaPush` entity type.

## 8. Compliance considerations

- **21 CFR Part 11 §11.10 (attribution)** : every push event carries the originating operator ID (`reported_by__v`) so the Vault audit trail attributes the data correctly.
- **21 CFR Part 11 §11.10(g) (electronic signature linkage)** : the `audit_signature__c` field carries the latest AuditLog signature for the entity, providing a verifiable link back into the Labionexus chain.
- **Annex 11 §7.1 (data exchange)** : the push payload includes the SHA-256 `integrity_hash__c` so receiving systems can verify data has not been altered in transit.
- **Annex 11 §12.3 (audit trail)** : the chain of custody is documented end to end. A Vault auditor can take any quality_event record, copy the integrity_hash, and ask Labionexus to verify the matching audit chain segment.

## 9. Demo narrative (for the discovery call)

> "Today our system captures from your instruments, hashes every reading with the operator and lot context, e-signs, and stores the audit chain. Our Veeva Vault QMS connector then pushes each quality event into your Vault tenant with the exact same integrity hash attached. If your auditor pulls the record from Vault three years from now, they can verify it matches the original capture byte for byte, all the way back to the balance reading on the bench."

## 10. Build plan (post FL Basel)

The full build (Bucket 2 in the D6-D10 plan) is decomposed into 9 atomic tasks T13 through T21 :

- T13 `VeevaConnection` Django model + migration
- T14 OAuth2 dance handler + encrypted token storage
- T15 `veeva_field_mapper.py` field mapping service
- T16 `veeva_pusher.py` push service with retry
- T17 Admin UI `/admin/integrations/veeva/connect` + Test Connection button
- T18 E2E test: capture → AuditLog → e-sig → Veeva push (sandbox real call)
- T19 Add Veeva card to `Integrations.jsx` with status `available`
- T20 Record Loom demo 3 to 5 min (Scenario B: HPLC OOS → Veeva)
- T21 Bump this document to v1.0 and reclassify to EXTERNAL after demo recorded

This spec is itself task T0 of that plan, shipped pre-emptively so the sales conversation can reference "we have it spec'd" rather than wait for code.

## 11. Changelog

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-05-11 | Initial INTERNAL draft. Scope locked to one-way push, sandbox only, single tenant per Labionexus deployment. |
