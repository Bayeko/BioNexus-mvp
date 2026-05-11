# Labionexus Platform Service Level Agreement

**Document ID** : LBN-OPS-SLA-001
**Version** : 1.0
**Date** : 2026-05-11
**Classification** : EXTERNAL · Client-Facing

---

## 1. Purpose

This document defines the availability targets, measurement methodology, and remedies that apply to the Labionexus Platform when delivered as a hosted service to a paying client. It complements (and is overridden by) any signed Master Service Agreement.

## 2. Scope

The Service Level Agreement applies to :

1. The Labionexus cloud platform endpoints hosted by Labionexus.
2. The data capture pipeline from the Labionexus Box (gateway) to the cloud audit trail.

The Agreement does NOT cover :

* Client network outages, client firewall changes, or client identity provider downtime.
* Third-party LIMS / QMS endpoints that the platform pushes data to (those are governed by the third-party vendor's own SLA).
* Scheduled maintenance windows announced at least 48 hours in advance.
* Force majeure events as defined in the Master Service Agreement.

## 3. Service tiers and targets

| Tier | Definition | Availability target | Latency target | Measurement window |
|------|------------|---------------------|----------------|--------------------|
| Critical | Data capture endpoint `POST /api/persistence/capture/` returns a 2xx response | 99.5 percent monthly | 95th percentile under 5 seconds | Rolling 30 days |
| Important | Read endpoints `/api/measurements/`, `/api/samples/`, `/api/instruments/` return a 2xx response | 99.0 percent monthly | 95th percentile under 2 seconds | Rolling 30 days |
| Functional | Web UI loads, electronic signature flow completes end to end | 98.0 percent monthly | 95th percentile under 4 seconds (full page) | Rolling 30 days |
| Edge resilience | The Box continues to capture and queue data when the cloud is unreachable, and synchronises after recovery | 100 percent (architectural) | Recovery within 5 minutes of cloud reachability | Per incident |

## 4. Measurement methodology

Availability is measured by automated synthetic probes that issue a request every 5 minutes against the public endpoint set listed in Section 3, from at least one external monitoring location. A check counts as failed when :

* The HTTP response code is 5xx, or
* The connection times out after 30 seconds, or
* The response body does not match the expected health signature.

Three consecutive failed checks count as a single downtime event. Time-to-recovery is measured from the first failed check until two consecutive successful checks.

Monthly availability is computed as :

```
availability = 1 - (downtime_minutes / total_minutes_in_month)
```

A monthly availability report is shared with the client within the first 5 business days of the following month.

## 5. Status communication

The Labionexus status page is published at a stable URL provided at deployment and is updated automatically by the monitoring stack. The client receives :

* An automatic email when a critical-tier incident is declared.
* A second email when the incident is resolved.
* A post-mortem within 5 business days when a critical-tier incident exceeds the latency target for more than 30 minutes.

## 6. Service credits

When monthly availability for the Critical tier falls below the target, the client is eligible for a service credit on the following month's invoice :

| Monthly Critical availability | Service credit |
|-------------------------------|----------------|
| Below 99.5 percent and at or above 99.0 percent | 5 percent |
| Below 99.0 percent and at or above 98.0 percent | 10 percent |
| Below 98.0 percent | 20 percent |

Credits are not cumulative across tiers and do not exceed 20 percent of any single monthly fee. The client must request the credit within 30 days of the report being shared.

## 7. Exclusions in detail

The following are explicitly excluded from availability calculations :

* Client-requested feature rollouts or migrations during agreed-upon change windows.
* Outages caused by client misconfiguration, including but not limited to firewall blocks, expired client certificates, or revoked client API keys.
* Outages caused by the client exceeding documented rate limits.
* Outages caused by upstream cloud provider events (the platform inherits the underlying provider's SLA for those minutes).

## 8. Regulatory context

This Agreement is consistent with EU GMP Annex 11 Section 16 (Business Continuity) and 21 CFR Part 11 Sections 11.10(a) and 11.10(g) (operational system controls). The audit trail (Annex 11 Section 12) remains intact during all availability events thanks to the Box-side write-ahead log, which preserves chain of custody even during full cloud outages.

## 9. Changes to this policy

Material changes to availability targets or measurement methodology will be communicated to the client at least 30 days in advance. The version and date at the top of this document indicate the last update.

## 10. Contact

For questions about this Service Level Agreement or to request a service credit, contact your Labionexus account representative.

---

*Document classification : EXTERNAL · Client-Facing. May be shared with prospects during discovery and qualification.*
