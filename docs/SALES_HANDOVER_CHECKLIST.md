# Sales-to-Delivery Handover Checklist

**Document ID** : LBN-SALES-HANDOVER-001 (INTERNAL track)
**Version** : 0.1 DRAFT
**Date** : 2026-05-11
**Classification** : INTERNAL · Sales + Operations
**Purpose** : Lock the prerequisites for a successful deployment BEFORE the deal closes, and trigger Phase 1 of the deployment runbook with no information loss.

---

## How to use this checklist

Fill this form during sales discovery and qualification. Every item must be a closed yes / no by the time the Statement of Work is signed. Open items at signature are the leading indicator of a slipped Phase 2 workshop and a slipped 8-week deployment target.

---

## Section A — Client identity and stakeholders

- [ ] Legal entity name : `____________________________________`
- [ ] Billing entity (if different) : `____________________________________`
- [ ] Site address(es) where the Labionexus Box will be installed : `____________________________________`
- [ ] Primary contact (operational lead) name + email + phone : `____________________________________`
- [ ] QC Manager name + email : `____________________________________`
- [ ] Lab IT Admin name + email : `____________________________________`
- [ ] QA Sign-off authority name + email : `____________________________________`
- [ ] Procurement / Purchasing contact (for invoice routing) : `____________________________________`

## Section B — Regulatory profile

- [ ] Regulatory frameworks in scope at this site (tick all that apply) :
  - [ ] EU GMP Annex 11
  - [ ] 21 CFR Part 11 (FDA)
  - [ ] ICH Q10
  - [ ] PIC/S PI 041-1
  - [ ] Other : `____________________________________`
- [ ] Most recent internal or regulatory audit on this site (year + outcome) : `____________________________________`
- [ ] Next planned external audit (date if known) : `____________________________________`
- [ ] Existing electronic signature standard in use : `____________________________________`

## Section C — Instruments in scope

For each instrument planned to connect (repeat the block per instrument) :

- [ ] Instrument 1 : make + model + serial = `____________________________________`
  - [ ] Connection type : RS232 / USB / Ethernet / WiFi
  - [ ] Parser type from our registry (or "new parser needed") : `____________________________________`
  - [ ] Required metadata fields per `InstrumentConfig` : `____________________________________`
  - [ ] **Raw output sample collected** (5 files, attached or shared via secure link) : Yes / No

> Closing rule : if **Raw output sample collected = No** for any instrument, the SOW must include a 1-week pre-deployment parser verification phase BEFORE Phase 2 kicks off.

## Section D — Existing systems

- [ ] LIMS in use (vendor + version) : `____________________________________`
- [ ] LIMS interface needed in scope ? Yes / No. If yes : `____________________________________`
- [ ] QMS in use (vendor + version) : `____________________________________`
- [ ] QMS interface needed in scope ? Yes / No. If yes : `____________________________________`
- [ ] Identity provider for SSO (Okta, Azure AD, other) : `____________________________________`
- [ ] Network constraints (proxy, allow-list, MTLS) : `____________________________________`

## Section E — Commercial terms

- [ ] Statement of Work signed (date) : `__________`
- [ ] Master Service Agreement signed (date) : `__________`
- [ ] Number of instruments included : `_____`
- [ ] Deployment phase scope (full 7-phase runbook ? partial ?) : `____________________________________`
- [ ] Hypercare scope confirmed (default 2 weeks) : Yes / No / Custom : `__________`
- [ ] Service Level Agreement version acknowledged : `____________________________________`

## Section F — Schedule

- [ ] Phase 2 URS workshop date locked : `__________`
- [ ] Three alternative slots offered to the client : Yes / No
- [ ] Hardware shipping window (Phase 3) : `__________` to `__________`
- [ ] UAT date window (Phase 6) : `__________` to `__________`
- [ ] Go-live target date (Phase 7 trigger) : `__________`

## Section G — Risks flagged during sales

Write down everything the sales team learned that the delivery team should not have to rediscover :

- ...
- ...
- ...

## Section H — Handover meeting

- [ ] Internal handover meeting scheduled within 5 business days of SOW signature : `__________`
- [ ] All sections A through G reviewed live with delivery owner
- [ ] Action items captured in `INC` / `TASK` tickets

## Sign-off

- [ ] Sales owner : `____________________` · `__________`
- [ ] Delivery owner : `____________________` · `__________`

---

*Closed items only. Any blank line above is a leading indicator that Phase 2 will slip. Do not skip.*
