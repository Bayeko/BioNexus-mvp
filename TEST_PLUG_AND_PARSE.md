# 🧪 Test: Plug-and-Parse Data Capture

## Comment tester que les données sont bien capturées

### Run the Test
```bash
cd /home/user/BioNexus-mvp/bionexus-platform/backend
python test_plug_and_parse_workflow.py
```

### Résultats Attendus

#### ✅ Scenario 1: First Upload
```
CSV File Columns:  ["Temp_C", "Sample_ID", "Vol_uL", "Status", "WeirdField"]
Incoming Data:     {"Temp_C": 37.5, "Sample_ID": "SAMPLE-001", "Vol_uL": 100.5, "Status": "success"}

↓ AI Recognition (avec confidence scores)

AI Suggestions:
  ✓ Sample_ID    → sample_id      (80% confiance)
  ✓ Status       → status         (100% confiance)
  ⚠ Temp_C       → needs mapping  (0% without help)
  ⚠ Vol_uL       → needs mapping  (0% without help)
  ⚠ WeirdField   → IGNORED        (0% confiance)

↓ User Confirms in UI

Saved to TenantConnectorProfile:
{
  "Temp_C": "temperature",
  "Sample_ID": "sample_id",
  "Vol_uL": "volume",
  "Status": "status"
}

↓ Data Transformed & Saved

RawFile:
  - ID: 1
  - filename: hamilton_run_001.csv
  - file_content: Binary (preserved for audit)
  - file_hash: abc123def456 (integrity proof)

ParsedData:
  - ID: 1
  - state: "validated"
  - parsed_json: {
      "temperature": 37.5,
      "sample_id": "SAMPLE-001",
      "volume": 100.5,
      "status": "success"
    }
  - extraction_confidence: 0.85
  - validated_by: test_user
  - confirmed_json: {...}  ← **AUDIT TRAIL SAVED**
```

#### ✅ Scenario 2: Second Upload (No Re-Asking!)
```
CSV File Columns:  ["Temp_C", "Sample_ID", "Vol_uL", "Status"]
Incoming Data:     {"Temp_C": 38.2, "Sample_ID": "SAMPLE-002", "Vol_uL": 95.3, "Status": "success"}

↓ System fetches TenantConnectorProfile for this tenant

Saved Profile Found:
  machine_instance_name: "Hamilton-Lab1"
  column_mapping: {
    "Temp_C": "temperature",
    "Sample_ID": "sample_id",
    "Vol_uL": "volume",
    "Status": "status"
  }
  confirmed_by: test_user
  confirmed_at: 2026-02-26 08:31:27

↓ **AUTOMATICALLY APPLY MAPPING** (no user interaction!)

Data Transformed:
{
  "temperature": 38.2,
  "sample_id": "SAMPLE-002",
  "volume": 95.3,
  "status": "success"
}

↓ Data Saved

RawFile:
  - ID: 2
  - filename: hamilton_run_002.csv

ParsedData:
  - ID: 2
  - state: "validated"
  - extraction_confidence: 0.88
  - confirmed_json: {...}  ← **2 ROWS IN DB NOW**
```

---

## Database Verification

After running the test, you can verify the data in the database:

```bash
python manage.py shell

# Check 1: TenantConnectorProfile (saved mappings)
from core.models import TenantConnectorProfile
profile = TenantConnectorProfile.objects.first()
print(f"Machine: {profile.machine_instance_name}")
print(f"Mapping: {profile.column_mapping}")
print(f"Confirmed by: {profile.confirmed_by.username}")
# Output:
# Machine: Hamilton-Lab1
# Mapping: {'Temp_C': 'temperature', 'Sample_ID': 'sample_id', 'Vol_uL': 'volume', 'Status': 'status'}
# Confirmed by: test_user

# Check 2: RawFile (original files preserved)
from core.models import RawFile
for rf in RawFile.objects.all():
    print(f"File: {rf.filename}, Size: {rf.file_size}, Hash: {rf.file_hash[:8]}...")
# Output:
# File: hamilton_run_001.csv, Size: 56, Hash: abc123de...
# File: hamilton_run_002.csv, Size: 48, Hash: abc123de...

# Check 3: ParsedData (transformed data)
from core.models import ParsedData
for pd in ParsedData.objects.all():
    print(f"ID: {pd.id}, State: {pd.state}")
    print(f"  Data: {pd.confirmed_json}")
    print(f"  Confidence: {pd.extraction_confidence}")
# Output:
# ID: 1, State: validated
#   Data: {'temperature': 37.5, 'sample_id': 'SAMPLE-001', 'volume': 100.5, 'status': 'success'}
#   Confidence: 0.85
# ID: 2, State: validated
#   Data: {'temperature': 38.2, 'sample_id': 'SAMPLE-002', 'volume': 95.3, 'status': 'success'}
#   Confidence: 0.88
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER UPLOADS CSV                         │
│         Columns: Temp_C, Sample_ID, Vol_uL, Status          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────┐
        │  AI MAPPING ENGINE (Recognizes)      │
        │  - "Temp_C" → "temperature" (0%)     │
        │  - "Sample_ID" → "sample_id" (80%)   │
        │  - "Vol_uL" → "volume" (0%)          │
        │  - "Status" → "status" (100%)        │
        └──────────────────┬───────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │  USER CONFIRMS MAPPINGS IN UI        │
        │  (Or AI auto-applies if high conf)   │
        │  ✓ Temp_C → temperature              │
        │  ✓ Sample_ID → sample_id             │
        │  ✓ Vol_uL → volume                   │
        │  ✓ Status → status                   │
        └──────────────────┬───────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌─────────────┐ ┌──────────────┐ ┌──────────────┐
    │  RawFile    │ │ TenantConnector│ │  ParsedData │
    │ (Original)  │ │   Profile      │ │ (Transformed)
    │             │ │ (Saved mapping)│ │ (Validated) │
    │ - content   │ │                │ │             │
    │ - hash      │ │ - column_      │ │ - json      │
    │ - filename  │ │   mapping      │ │ - state     │
    │ - size      │ │ - confirmed_by │ │ - hash      │
    └─────────────┘ │ - confirmed_at │ └──────────────┘
                    │ - is_active    │
                    └────────────────┘
                           │
                    ┌──────▼──────┐
                    │  DATABASE   │
                    │             │
                    │ ✓ Auditable │
                    │ ✓ Traceable │
                    │ ✓ Compliant │
                    └─────────────┘

NEXT UPLOAD WITH SAME MACHINE:
===============================

User uploads another CSV
    ↓
System checks TenantConnectorProfile (found!)
    ↓
AUTO-APPLY SAVED MAPPING (instant, no waiting)
    ↓
Data transformed & saved to ParsedData
    ↓
✅ DONE! Zero user re-confirmation needed!
```

---

## What Gets Stored

### Table: `core_rawfile`
```sql
SELECT * FROM core_rawfile WHERE tenant_id=1;

ID | filename              | file_hash    | file_size | mime_type | storage_backend | tenant_id | user_id
---|-----------------------|--------------|-----------|-----------|-----------------|-----------|--------
1  | hamilton_run_001.csv | abc123de...  | 56        | text/csv  | local           | 1         | 1
2  | hamilton_run_002.csv | abc123de...  | 48        | text/csv  | local           | 1         | 1
```

**Why?** Original files preserved for 21 CFR Part 11 compliance. NEVER deleted.

### Table: `core_tenantconnectorprofile`
```sql
SELECT * FROM core_tenantconnectorprofile WHERE tenant_id=1;

ID | tenant_id | connector_id | machine_instance_name | column_mapping | confirmed_by_id | is_active
---|-----------|--------------|----------------------|----------------|-----------------|----------
1  | 1         | 1            | Hamilton-Lab1        | {...}          | 1               | True
```

**Why?** Saved mapping applied to all future uploads. No re-configuration needed.

### Table: `core_parseddata`
```sql
SELECT * FROM core_parseddata WHERE tenant_id=1;

ID | raw_file_id | tenant_id | parsed_json | state     | extraction_confidence | validated_by_id
---|-------------|-----------|-------------|-----------|---------------------|----------------
1  | 1           | 1         | {...}      | validated | 0.85                | 1
2  | 2           | 1         | {...}      | validated | 0.88                | 1
```

**Why?** Transformed data stored with state tracking and confidence scores.

---

## Key Assertions (What the test verifies)

✅ **Data Captured Correctly**
- Incoming CSV columns recognized
- Mappings saved per tenant/machine
- Data transformed using saved mappings

✅ **AI Works**
- High-confidence fields recognized (100%, 80%)
- Low-confidence fields flag for manual review
- Unknown fields ignored

✅ **Plug-and-Play Works**
- Second upload auto-mapped (no re-asking!)
- Same transformation applied
- Saved profile reused

✅ **Audit Trail**
- RawFile stored (immutable)
- ParsedData stored (with validation info)
- TenantConnectorProfile tracks who confirmed
- All timestamps recorded

✅ **Database Integrity**
- No data loss
- All records linked correctly
- Relationships maintain referential integrity

---

## Next: API Test

To test the API endpoints:

```bash
# Start Django
python manage.py runserver

# In another terminal, test the endpoints
curl http://localhost:8000/api/connectors/
curl -X POST http://localhost:8000/api/mappings/suggest/ \
  -H "Content-Type: application/json" \
  -d '{"incoming_columns": ["Temp_C", "Sample_ID", "Vol_uL"]}'
```

See [PLUG_AND_PARSE.md](../PLUG_AND_PARSE.md) for full API documentation.

