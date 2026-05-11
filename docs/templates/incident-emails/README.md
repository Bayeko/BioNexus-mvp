# Incident Email Templates

**Classification** : EXTERNAL (sent to clients)
**Style constraints** : strict no em-dash, no en-dash, no pricing. Brand canonical : Labionexus.

Eight templates total : 4 severities × 2 languages (FR, EN).

| Severity | French | English |
|----------|--------|---------|
| P0 GxP breach | `p0-fr.md` | `p0-en.md` |
| P1 Production down | `p1-fr.md` | `p1-en.md` |
| P2 Degraded | `p2-fr.md` | `p2-en.md` |
| P3 Minor | `p3-fr.md` | `p3-en.md` |

## Usage

Each template has placeholders in `{{ALL_CAPS}}` format that you fill at incident time. Total fill time should be under 5 minutes per template.

Standard placeholders :
- `{{CLIENT_NAME}}` : client organisation name
- `{{INCIDENT_ID}}` : `INC-YYYYMMDD-NN`
- `{{INCIDENT_TIME_UTC}}` : ISO-8601 timestamp of detection
- `{{IMPACT_SUMMARY}}` : one sentence describing what the client cannot do
- `{{STATUS_PAGE_URL}}` : per-client status page URL
- `{{ETA_NEXT_UPDATE}}` : when you will send the next message (always overcommit by 30 min)
- `{{FOUNDER_NAME}}` : signing name and contact line

## When to send each template

Send the matching severity template at the **first acknowledgement** of the incident. Follow up with a tailored resolution or post-mortem message later. Do not modify the severity wording in the template.
