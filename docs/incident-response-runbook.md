# Incident Response Runbook — Labionexus Platform

**Document ID** : LBN-OPS-IR-001 (INTERNAL track)
**Version** : 0.1 DRAFT
**Date** : 2026-05-11
**Classification** : INTERNAL · Operations
**Status** : v0.1 working document — promote to SOP-IR-001 (QMS) after two real incidents handled and reviewed by external QA reviewer

---

## 1. Goal

Restore service quickly, communicate clearly with affected clients, and leave a credible written record of what happened. MTTR target ≤ 4 hours for critical incidents.

## 2. Severity matrix

| Sev | Definition | MTTR target | Client communication |
|-----|------------|-------------|----------------------|
| **P0 — GxP breach** | Data integrity at risk, audit trail tampering, lost captured data, e-signature bypass | 1 h triage / 4 h resolution / post-mortem within 48 h | Client + external QA reviewer within 2 h |
| **P1 — Production down** | SaaS endpoint returning 5xx, Box unable to sync for > 30 min, authentication broken for all users | 2 h | Client within 4 h |
| **P2 — Degraded** | Slow responses (> p95 SLA), partial feature failure, single Box offline, single instrument disconnected | 8 business hours | Client next business day |
| **P3 — Minor** | Cosmetic bug, documentation gap, low-impact regression | 5 business days | Next release notes |

When in doubt, classify one level higher than your first instinct.

## 3. The four phases

### Phase 1 — Detect

Sources :
- Sentry alert (severity tag drives the rule)
- UptimeRobot alert email or SMS
- Client report (email, phone, Slack channel)
- Internal observation during dev work

**Acknowledge within** : 15 min business hours · 1 h off-hours for P0/P1 · next business day for P2/P3.

The acknowledgement is recorded as a timestamp in the incident ticket. No analysis required at this stage — just "I see it, I am on it".

### Phase 2 — Triage

1. **Classify severity** using the matrix in Section 2.
2. **Open an incident ticket** (Linear or GitHub Issue), title format : `INC-YYYYMMDD-NN — <one-line summary>`.
3. **Notify affected clients** per the matrix. Use the pre-written templates in `docs/templates/incident-emails/` so the first message goes out in under 15 min.
4. **Page external QA reviewer** (Johannes Eberhardt) for P0 incidents only. Phone is in the personal contacts vault.

### Phase 3 — Mitigate

Goal : stop the bleeding. Order of preference :

1. **Rollback** to the last known good release.
2. **Feature flag off** the suspected component.
3. **Scale up** if the cause is capacity (Cloud Run instance count, DB connection pool).
4. **Manual workaround** if 1 to 3 are not applicable. Document exactly what you did.

Log every action with a UTC timestamp inside the incident ticket. The ticket is the canonical timeline.

### Phase 4 — Root cause + post-mortem

For P0 and P1, within 48 hours of resolution :

1. Run a 5-whys analysis on the incident timeline.
2. Fill `docs/templates/POST_MORTEM_TEMPLATE.md` and commit it to `docs/post-mortems/INC-YYYYMMDD-NN.md`.
3. Identify at least one Corrective Action (fix the immediate cause) and one Preventive Action (reduce the probability of recurrence). File both as tracked tickets.
4. Sign-off : founder always. External QA reviewer (Johannes) for P0 only.

## 4. Communication discipline

- First message under 30 min for P0, under 1 h for P1, regardless of how much you know. "We are investigating" is fine — silence is not.
- Use the pre-written client templates in `docs/templates/incident-emails/` to avoid drafting during stress.
- Status page is the source of truth. Every email points back to it.
- Never speculate about root cause in client communication before the post-mortem is signed off.

## 5. Solo-founder constraints and mitigations

Being always-on-call is fragile. Pre-arranged mitigations :

- **Status page auto-updates** : monitoring stack writes directly. No manual update during incident.
- **Pre-written templates** : 8 emails ready (4 severity × 2 languages). Edit only the specifics during incident.
- **Johannes as P0 escalation** : paid engagement, not a free favour. Confirmed escalation path.
- **No-call windows** : declare them in advance via the status page (e.g. "scheduled maintenance every Tuesday 22:00 to 23:00 Europe/Zurich"). During these windows P2 SLA targets do not apply.

## 6. Promotion path to QMS

This runbook stays at version 0.x INTERNAL until :

- At least 2 real incidents have been handled end to end using it, AND
- The post-mortems show the runbook itself did not need substantial rework, AND
- The external QA reviewer has reviewed the document and the two post-mortems.

At that point, bump to v1.0 and promote to `SOP-IR-001` under the QMS track (CONFIDENTIAL classification) with controlled change management. Avoid premature polish drift — the runbook must earn its way into the QMS.

## 7. Contacts (redacted in version-controlled file)

| Role | Name | Where to find contact details |
|------|------|--------------------------------|
| Founder | Amir Messadene | Personal contacts vault |
| External QA reviewer | Johannes Eberhardt (GMP4U) | Personal contacts vault |
| Cloud provider escalation | GCP Premium Support (if subscribed) | GCP console |

The actual phone numbers and emails are kept out of this version-controlled file. They live in the personal contacts vault, accessible offline on the founder's primary device.

## 8. Changelog

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-05-11 | Initial INTERNAL draft. Severity matrix, four-phase loop, comms discipline. |
