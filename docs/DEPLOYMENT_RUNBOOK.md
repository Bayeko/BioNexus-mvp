# Labionexus Deployment Runbook

**Document ID** : LBN-OPS-DEPLOY-001 (INTERNAL track)
**Version** : 0.1 DRAFT
**Date** : 2026-05-11
**Classification** : INTERNAL · Operations
**Target deployment time** : ≤ 8 weeks from sales handover to production go-live

---

## 1. Purpose

Standardise the deployment of the Labionexus Platform at a new client site. The runbook defines seven phases, their owners, their time targets, the artifacts each produces, and the known bottlenecks. It is the operational counterpart to the customer-facing `CUSTOMER_ONBOARDING_GUIDE.md`.

## 2. The seven phases at a glance

| # | Phase | Owner | Target duration | Critical path ? |
|---|-------|-------|-----------------|------------------|
| 1 | Sales handover and kickoff scheduling | Founder | 3 business days | No |
| 2 | URS workshop and Risk Assessment | Founder + Client QC Manager | 1 week | **Yes** |
| 3 | Hardware shipping and on-site installation | Founder remote + Client IT | 1 week | Partial |
| 4 | Instrument registration and parser binding | Founder + Client Lab Tech | 1 week | **Yes** |
| 5 | IQ / OQ / PQ execution | Founder + Client QA | 2 weeks | **Yes** |
| 6 | UAT and operator training | Client QC + Founder | 1 week | No |
| 7 | Go-live and 2-week hypercare | Founder | 1 week kickoff + 2 weeks monitoring | No |

**Nominal total** : 7 weeks of deployment + 2 weeks of hypercare (hypercare overlaps with go-live and is not counted in the 8-week target).

## 3. Phase-by-phase detail

### Phase 1 — Sales handover and kickoff scheduling

**Trigger** : signed Master Service Agreement and signed Statement of Work.
**Goal** : transition from sales to delivery with no information loss, and lock the date for Phase 2.

**Activities** :
- Sales-to-delivery handover meeting (internal, 60 min). Walkthrough of the `SALES_HANDOVER_CHECKLIST.md` filled during sales.
- Send the client the URS-001 questionnaire template and request the 5 raw instrument output files agreed during discovery.
- Confirm dates for Phase 2 workshop, target within 5 business days of handover.

**Artifacts produced** :
- Filled `SALES_HANDOVER_CHECKLIST.md` (internal)
- URS-001 questionnaire template sent (external)

**Common failure** : sales did not collect raw output files during discovery. Mitigation : the sales checklist makes this a closed item before deal signature.

### Phase 2 — URS workshop and Risk Assessment

**Trigger** : Phase 1 closed.
**Goal** : produce the site-specific URS and the Risk Assessment that scope the qualification effort.

**Activities** :
- 2-hour URS workshop with the client QC Manager and Lab IT.
- Risk Assessment session (60 min) using the Vendor Qualification Package risk template.
- Founder drafts the URS-001 site-specific and RA-001 documents within 3 business days of the workshop.

**Artifacts produced** :
- URS-001 site-specific (CONFIDENTIAL, shared with client for sign-off)
- RA-001 Risk Assessment (CONFIDENTIAL)

**Common failure** : client cannot align stakeholders in the workshop window. Mitigation : offer 3 alternative slots upfront, escalate to client sponsor by day 5.

### Phase 3 — Hardware shipping and on-site installation

**Trigger** : URS sign-off OR Phase 2 day 5 (whichever is earlier — the Box can be installed in parallel with URS finalisation).
**Goal** : the Labionexus Box is physically connected at the client site and visible to the platform.

**Activities** :
- Box ships to site (Swiss origin warehouse target after deal 1 to avoid customs delay).
- Client Lab IT racks the Box and provides outbound HTTPS to `api.bionexus.io`.
- Founder runs a remote 30-min config session : platform pairing, NTP sync, smoke test on `/healthz`.

**Artifacts produced** :
- Shipping confirmation
- Network and time sync verification screenshot

**Common failure** : customs delay on cross-border shipments. Mitigation : pre-position 1 spare Box in CH warehouse after deal 1.

### Phase 4 — Instrument registration and parser binding

**Trigger** : Box online and `/healthz` green.
**Goal** : each in-scope instrument is registered in the platform with its `InstrumentConfig`, parser_type, and threshold rules.

**Activities** :
- For each instrument : register via `/api/instruments/`, attach `InstrumentConfig` (parser_type from registry, required_metadata_fields, thresholds).
- Connect the instrument physically (RS232 or USB) and verify a real reading reaches `/api/measurements/` with the expected metadata bound into the SHA-256 hash.

**Artifacts produced** :
- Instrument registration log per instrument (saved as an audit trail extract)

**Common failure** : instrument output format differs from the parser spec. Mitigation : the 5 raw output files collected during sales discovery are run through the parser registry BEFORE the on-site visit, so the mismatch is detected and a parser update is shipped.

### Phase 5 — IQ / OQ / PQ execution

**Trigger** : Phase 4 closed.
**Goal** : produce the qualification evidence required by GAMP 5 Cat 4 Configured Product, site-specific portion only (the platform-validation portion is amortised across all clients).

**Activities** :
- **IQ** (Installation Qualification) : verify the installed configuration matches URS-001. Output : IQ report signed by client QA.
- **OQ** (Operational Qualification) : run the operational test protocol against the installed system. Output : OQ report.
- **PQ** (Performance Qualification) : the lab runs 20 real samples through the system end to end, including e-signature flow. Output : PQ report with signed sample-by-sample evidence.

**Artifacts produced** :
- IQ-001 site, OQ-001 site, PQ-001 site reports (CONFIDENTIAL, classified per QMS framework)
- Updated RTM-001 site-specific traceability matrix linking URS items to test evidence

**Common failure** : environmental differences between dev assumptions and the client lab (e.g. specific RS232 cable types, locale formatting on a balance display). Mitigation : the standard layer test scripts cover the platform-wide cases ; only the site-specific deltas need new scripts, which is GAMP 5 Cat 4 by design.

### Phase 6 — UAT and operator training

**Trigger** : PQ signed.
**Goal** : the lab operators can perform the day-to-day workflow without founder assistance, and the training is documented for the audit trail.

**Activities** :
- Train at least 3 operators (rotating shifts).
- Each operator runs 5 real captures with full metadata.
- Document training in the user record (date, content, operator name, trainer name).

**Artifacts produced** :
- Training record per operator
- UAT sign-off by client QC Manager

**Common failure** : operators not available because of competing priorities. Mitigation : lock UAT dates in Phase 1.

### Phase 7 — Go-live and hypercare

**Trigger** : UAT sign-off.
**Goal** : first production data is captured and the founder is on tight monitoring for 2 weeks.

**Activities** :
- Flip the client from staging environment to production tenant.
- Daily 15-min check-in for the first 10 business days.
- Weekly audit trail integrity check (using `AuditTrail.verify_chain_integrity`).
- After 2 weeks, transition to standard support.

**Artifacts produced** :
- Go-live confirmation email
- First weekly audit chain verification report

**Common failure** : a regression in Phase 7 affects the audit trail chain, which is a P0 incident. Mitigation : the `/healthz` audit_trail check and the weekly chain verification are designed to catch this within 24 hours.

## 4. Time-tracking and baseline collection

From deal 1 onward, log start and end timestamps for each phase as audit trail entries. After 3 deals, compute the actual median duration per phase. This becomes the D10 (deployment time) production baseline. If any phase consistently exceeds its target, it is treated as a structural defect and prioritised for process improvement in the next quarterly review.

## 5. Promotion path to QMS

This runbook stays at version 0.x INTERNAL until :

- At least 1 deployment has been completed end to end using it, AND
- The post-deployment review confirms the runbook reflected reality, AND
- The external QA reviewer has reviewed the document and the deployment evidence.

At that point, bump to v1.0 and promote to `SOP-DEPLOY-001` under the QMS track (CONFIDENTIAL classification).

## 6. Changelog

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-05-11 | Initial INTERNAL draft. Seven-phase decomposition, target durations, common failure mitigations. |
