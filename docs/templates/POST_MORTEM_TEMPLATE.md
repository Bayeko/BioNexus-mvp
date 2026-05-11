# Post-mortem — `{{INCIDENT_ID}}` : `{{ONE_LINE_TITLE}}`

**Classification** : INTERNAL · Operations
**Status** : DRAFT / SIGNED-OFF
**Author** : {{AUTHOR_NAME}}
**Date** : {{POST_MORTEM_DATE}}
**Linked incident ticket** : {{TICKET_URL}}
**Severity** : P0 / P1 / P2 / P3
**Customers affected** : `{{CLIENT_LIST_OR_NONE}}`

---

## 1. Executive summary

One paragraph, three sentences max. Written so a non-technical reader (client QA, external reviewer) understands what happened, what was impacted, and what we are doing about it.

## 2. Impact

- **Duration** : from `{{START_UTC}}` to `{{END_UTC}}` (total `{{DURATION}}`).
- **What clients could not do** : one sentence describing the user-visible failure.
- **Data integrity** : intact / at risk / lost. If "at risk" or "lost", describe scope precisely.
- **Audit trail** : intact / broken. If broken, link to verification command output.
- **Service tier affected** : Critical / Important / Functional / Edge resilience.
- **Monthly SLA impact** : `{{MINUTES}}` minutes of downtime contribute to the monthly calculation.

## 3. Timeline (UTC)

| Time | Actor | Event |
|------|-------|-------|
| `{{TS}}` | system | First Sentry alert fires (`severity:p1`) |
| `{{TS}}` | founder | Acknowledged alert |
| `{{TS}}` | founder | Classified as Pn |
| `{{TS}}` | founder | First client email sent (template `pN-{lang}.md`) |
| `{{TS}}` | founder | Hypothesis A : `{{HYPOTHESIS_A}}` |
| `{{TS}}` | founder | Hypothesis A invalidated by `{{EVIDENCE}}` |
| `{{TS}}` | founder | Mitigation applied : `{{ACTION}}` |
| `{{TS}}` | system | UptimeRobot back to UP |
| `{{TS}}` | founder | Second client email sent (resolution) |

## 4. Root cause analysis (5 whys)

Start from the user-visible symptom. Each "why" must be backed by evidence (log line, metric chart, code reference). Stop when you hit either a fixable cause or a structural decision worth documenting.

1. **Why did `{{SYMPTOM}}` happen ?** → because `{{CAUSE_1}}`. Evidence : `{{EVIDENCE_1}}`.
2. **Why did `{{CAUSE_1}}` happen ?** → because `{{CAUSE_2}}`. Evidence : `{{EVIDENCE_2}}`.
3. **Why did `{{CAUSE_2}}` happen ?** → because `{{CAUSE_3}}`. Evidence : `{{EVIDENCE_3}}`.
4. **Why did `{{CAUSE_3}}` happen ?** → because `{{CAUSE_4}}`. Evidence : `{{EVIDENCE_4}}`.
5. **Why did `{{CAUSE_4}}` happen ?** → root cause : `{{ROOT_CAUSE}}`.

## 5. What went well

Two or three things the team or the system did right. Be honest. This section calibrates the team for the next incident.

- ...
- ...

## 6. What went badly

Two or three things that delayed detection, classification, mitigation, or communication. Avoid blame ; focus on systems and processes.

- ...
- ...

## 7. Corrective and preventive actions (CAPA)

Each action has an owner, a due date, and a tracked ticket.

| ID | Type (corrective / preventive) | Action | Owner | Due | Ticket |
|----|-------------------------------|--------|-------|-----|--------|
| CA-01 | Corrective | `{{ACTION}}` | `{{OWNER}}` | `{{DUE}}` | `{{TICKET}}` |
| PA-01 | Preventive | `{{ACTION}}` | `{{OWNER}}` | `{{DUE}}` | `{{TICKET}}` |

For P0, at least one preventive action MUST be filed.

## 8. Regulatory context

- Annex 11 section applicable : `{{e.g. 12.3, 16}}`
- 21 CFR Part 11 section applicable : `{{e.g. 11.10(a), 11.10(g)}}`
- Was a deviation report required ? Yes / No. If yes, link the deviation document.

## 9. Communication audit

| Time | Channel | Recipients | Template used | Notes |
|------|---------|------------|---------------|-------|
| `{{TS}}` | Email | `{{CLIENT_LIST}}` | `pN-fr.md` / `pN-en.md` | Acknowledgement |
| `{{TS}}` | Status page | Public | Automatic | Initial incident creation |
| `{{TS}}` | Email | `{{CLIENT_LIST}}` | Resolution (custom) | Full resolution sent |

## 10. Sign-off

- [ ] Founder : Amir Messadene · `{{DATE}}`
- [ ] External QA reviewer (P0 only) : Johannes Eberhardt · `{{DATE}}`

---

*This document is INTERNAL. Sharing externally requires founder approval and may need redaction of internal hostnames, log excerpts, and contractor names.*
