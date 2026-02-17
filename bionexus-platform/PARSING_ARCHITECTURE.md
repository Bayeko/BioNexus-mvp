# BioNexus Parsing Service - Architecture Document

## Overview

The ParsingService implements ALCOA+ compliance for file ingestion and data extraction, with three critical guardrails:

1. **Immutability**: Files are hashed (SHA-256) and never modified
2. **Validation**: All AI output is validated against strict Pydantic schemas
3. **Human Authorization**: No data accepted without explicit human review

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FILE UPLOAD                           │
│  User uploads file → SHA-256 hash → Immutable record    │
│  (RawFile model, file_hash unique)                      │
└────────────────┬────────────────────────────────────────┘
                 │ AUDIT: "RawFile CREATE"
                 ↓
┌─────────────────────────────────────────────────────────┐
│                AI EXTRACTION                            │
│  AI model (GPT-4, Claude) parses file                   │
│  Output stored as-is in ParsedData.parsed_json          │
│  State: PENDING (awaiting human review)                 │
└────────────────┬────────────────────────────────────────┘
                 │ AUDIT: "ParsedData CREATE"
                 ↓
┌─────────────────────────────────────────────────────────┐
│           SCHEMA VALIDATION (GATEKEEPER)                │
│  Pydantic validates against strict schema              │
│  ❌ Extra fields FORBIDDEN (no hallucinations)         │
│  ✅ Type enforcement (coercion disabled)               │
│  ✅ Regex patterns for enums                           │
│  ✅ Date/timestamp validation (ISO 8601)               │
└────────────────┬────────────────────────────────────────┘
                 │ Validation ERROR → Workflow stops
                 │ Validation OK → Proceed to review
                 ↓
┌─────────────────────────────────────────────────────────┐
│          HUMAN REVIEW & AUTHORIZATION                   │
│  Validator reads AI extraction                         │
│  Options:                                               │
│  - ✅ Accept AI data as-is                            │
│  - ✅ Accept with corrections (confirmed_json)         │
│  - ❌ Reject (requires reason)                        │
└────────────────┬────────────────────────────────────────┘
                 │ AUDIT: "ParsedData UPDATE"
                 │ (state: PENDING → VALIDATED/REJECTED)
                 ↓
┌─────────────────────────────────────────────────────────┐
│          CONFIRMED DATA STORED                          │
│  ParsedData.confirmed_json = human-approved data       │
│  Now ready for downstream processing                    │
│  (Sample creation, Equipment registration, etc.)        │
└─────────────────────────────────────────────────────────┘
```

---

## Data Models

### RawFile (Immutable Source)
```python
RawFile
├── id (PK)
├── tenant_id (FK) ← Multi-tenant isolation
├── user_id (FK) ← Who uploaded
├── filename: str
├── file_content: binary ← Complete, never modified
├── file_hash: str ← SHA-256 (unique, indexed)
├── file_size: int
├── mime_type: str
├── uploaded_at: datetime (auto_now_add) ← Contemporaneous
├── is_deleted: bool ← Soft delete only
└── CreatedAt Audit Trail ✓
```

### ParsedData (Awaiting Validation)
```python
ParsedData
├── id (PK)
├── raw_file_id (FK → RawFile)
├── tenant_id (FK)
├──
├── AI Extraction:
│   ├── extracted_at: datetime
│   ├── parsed_json: dict ← Raw AI output (not yet valid)
│   ├── extraction_confidence: float (0.0 to 1.0)
│   └── extraction_model: str (gpt-4, claude-3, etc.)
│
├── Validation State:
│   ├── state: enum [PENDING, VALIDATED, REJECTED, SUPERSEDED]
│   ├── validated_by_id (FK → User)
│   ├── validated_at: datetime
│   └── validation_notes: str
│
└── Confirmed Data:
    └── confirmed_json: dict ← Human-approved data
        (null until validated)
```

---

## Pydantic Schemas (Strict Validation)

### EquipmentData Schema
```python
EquipmentData(
    equipment_id: str,         # min_length=1, max_length=100
    equipment_name: str,       # 1-255 chars
    equipment_type: str,       # pattern: centrifuge|spectrophotometer|...
    location: str,             # 1-255 chars
    serial_number: Optional[str],
    purchase_date: Optional[str],  # ISO 8601 (YYYY-MM-DD)
    last_maintenance: Optional[str],
    status: str,               # pattern: operational|maintenance|broken|decommissioned
    notes: str,                # max 1000 chars
)

# CRITICAL: extra="forbid" → ❌ REJECT unknown fields
# This prevents AI hallucinations (e.g., made-up "warranty_expiry" field)
```

### SampleData Schema
```python
SampleData(
    sample_id: str,           # Unique ID
    sample_name: str,         # 1-255 chars
    sample_type: str,         # pattern: blood|plasma|serum|...
    collected_at: str,        # ISO 8601 timestamp
    collected_by: Optional[str],
    storage_temperature: Optional[int],  # -196°C to 25°C
    storage_location: Optional[str],
    quantity: Optional[float],  # > 0
    quantity_unit: str,       # pattern: ml|mg|µl|g|other
    notes: str,
)
```

### BatchExtractionResult (Container)
```python
BatchExtractionResult(
    equipment_records: list[EquipmentData],     # max 1000 items
    sample_records: list[SampleData],           # max 1000 items
    extraction_warnings: list[str],             # AI warnings (informational)
)
```

---

## ParsingService Methods

### 1. upload_file()
```python
ParsingService.upload_file(
    tenant: Tenant,
    user: User,
    filename: str,
    file_content: bytes,
    mime_type: str,
) → RawFile
```

**Actions:**
- Compute SHA-256 hash
- Create RawFile record (immutable)
- Record audit log

**Audit Trail:**
```
Entity: RawFile
Operation: CREATE
User: who uploaded
Changes: {
  "filename": {"before": null, "after": "equipment.csv"},
  "file_hash": {"before": null, "after": "a1b2c3..."}
}
```

---

### 2. parse_file()
```python
ParsingService.parse_file(
    raw_file: RawFile,
    ai_extracted_data: dict,  # Raw output from GPT-4, Claude, etc.
    model_name: str = "gpt-4-turbo",
    confidence_score: float = 0.9,
) → ParsedData
```

**Actions:**
1. Accept AI output as-is (no processing)
2. Validate against BatchExtractionResult schema
   - If INVALID → raise ValidationError (workflow stops)
   - If VALID → continue
3. Create ParsedData(state=PENDING)
4. Record audit log

**Critical Point:**
- AI output is NOT trusted until human review
- Validation catches schema violations early
- Audit trail records the attempted extraction (even if invalid)

**Audit Trail:**
```
Entity: ParsedData
Operation: CREATE
User: who uploaded file
Changes: {
  "state": {"before": null, "after": "PENDING"},
  "schema_valid": {"before": null, "after": true}
}
```

---

### 3. validate_and_confirm()
```python
ParsingService.validate_and_confirm(
    parsed_data: ParsedData,
    validator_user: User,  # Must have "audit:validate" permission
    confirmed_json: Optional[dict] = None,  # Human corrections
    validation_notes: str = "",
) → ParsedData
```

**Actions:**
1. If confirmed_json is None → use AI data as-is
2. Final schema validation on confirmed_json
3. Update ParsedData.state = VALIDATED
4. Record who approved and when
5. Record audit log

**This is the GATE:**
- Only data approved here enters the system
- Human is responsible for accuracy
- Non-repudiation: user_id + timestamp in audit trail

**Audit Trail:**
```
Entity: ParsedData
Operation: UPDATE
User: who validated
Changes: {
  "state": {"before": "PENDING", "after": "VALIDATED"},
  "validated_by_id": {"before": null, "after": 456}
}
```

---

### 4. reject_parsing()
```python
ParsingService.reject_parsing(
    parsed_data: ParsedData,
    validator_user: User,
    rejection_reason: str,  # "Invalid format", "Too many errors", etc.
) → ParsedData
```

**Actions:**
1. Set state = REJECTED
2. Record validator and reason
3. Record audit log

**Workflow ends here:**
- File can be re-uploaded for re-parsing
- Original RawFile remains intact

---

## ALCOA+ Compliance

| ALCOA+ Principle | Implementation |
|------------------|-----------------|
| **Attributable** | User ID + email in audit trail for every operation |
| **Legible** | Pydantic schemas ensure data is readable + typed |
| **Contemporaneous** | uploaded_at, extracted_at, validated_at timestamps |
| **Original** | SHA-256 file hash + immutable RawFile record |
| **Accurate** | Strict schema validation (no extra fields, type enforcement) |
| **Complete** | Full file content preserved, audit trail for every step |
| **Consistent** | Same schema used for all extractions of same file type |
| **Enduring** | Immutable storage (soft delete only, never modified) |
| **Available** | File content + audit trail always retrievable |

---

## Security Patterns

### ✅ Prevents AI Hallucinations
```python
# Pydantic with extra="forbid"
# If AI outputs: {"equipment_id": "...", "warranty_expiry": "2026-02-17"}
# → ValidationError: Extra field "warranty_expiry" not permitted

# Forces AI to extract ONLY schema-defined fields
```

### ✅ Detects Tampering
```python
# RawFile.file_hash (SHA-256)
# If someone modifies the file in the database:
FileHasher.verify_integrity(modified_content, stored_hash)  # → False
```

### ✅ Enforces Human Review
```python
# ParsedData starts in PENDING state
# Cannot be used for Sample creation until state=VALIDATED
# Requires explicit user authorization
```

### ✅ Complete Audit Trail
```python
# Every operation: CREATE file → PARSE (extract) → VALIDATE (authorize)
# Each step recorded with: user_id, timestamp, before/after state
# Signature chain ensures no record tampering
```

---

## Data Flow Example

```
1. USER UPLOADS FILE
   Lab technician uploads "equipment_inventory_2026-02.csv"

   AuditLog:
   - Entity: RawFile
   - Op: CREATE
   - User: john.doe@lab.local (ID 123)
   - Timestamp: 2026-02-17T10:30:00Z
   - File hash: a1b2c3d4...

2. AI EXTRACTION
   GPT-4-turbo parses CSV and extracts:
   {
     "equipment_records": [
       {
         "equipment_id": "EQ-2026-001",
         "equipment_name": "Centrifuge Model X2000",
         "equipment_type": "centrifuge",
         "location": "Lab-A, Bench 3",
         "status": "operational"
       }
     ],
     "sample_records": [],
     "extraction_warnings": []
   }

   ParsedData created (state=PENDING)

   AuditLog:
   - Entity: ParsedData
   - Op: CREATE
   - User: john.doe@lab.local (123)
   - Timestamp: 2026-02-17T10:30:15Z

3. HUMAN VALIDATION
   Lab manager jane.smith@lab.local (ID 456) reviews
   - Reads AI extraction
   - Verifies against physical equipment list
   - Finds typo: "Model X2000" should be "Model X2000R"
   - Confirms with correction

   ParsedData.state = VALIDATED
   ParsedData.confirmed_json = {...corrected...}
   ParsedData.validated_by_id = 456
   ParsedData.validated_at = 2026-02-17T10:35:00Z

   AuditLog:
   - Entity: ParsedData
   - Op: UPDATE
   - User: jane.smith@lab.local (456)
   - Timestamp: 2026-02-17T10:35:00Z
   - Changes: {state: PENDING→VALIDATED}

4. DOWNSTREAM PROCESSING
   CreateEquipmentService can now:
   - Read confirmed_json
   - Create Equipment record with validated data
   - Know EXACTLY who approved it (auditable)
```

---

## Integration with Other Services

### With SampleService
```python
# When creating sample from parsed data:
confirmed_json = parsed_data.confirmed_json
sample = SampleService.create_sample({
    "name": confirmed_json["sample_records"][0]["sample_name"],
    "sample_type": confirmed_json["sample_records"][0]["sample_type"],
    # All fields pre-validated ✓
})
```

### With AuditTrail
```python
# Every parsing step recorded:
AuditTrail.record(
    entity_type="RawFile" or "ParsedData",
    entity_id=...,
    operation="CREATE" or "UPDATE",
    changes={...},
    user_id=...,  # MANDATORY
    user_email=...,  # MANDATORY
)
```

---

## Test Coverage

### FileHasher Tests
- ✅ Consistent hash for same content
- ✅ Different hash for different content
- ✅ Integrity verification passes for matching hash
- ✅ Integrity verification fails for tampered content

### FileUpload Tests
- ✅ File upload creates RawFile record
- ✅ File hash is stored and verified
- ✅ Duplicate file returns existing record
- ✅ Upload creates audit log

### Validation Tests
- ✅ Valid data passes schema
- ✅ Invalid equipment_type rejected
- ✅ Missing required fields rejected
- ✅ Extra fields forbidden (hallucination prevention)
- ✅ Invalid date format rejected

### Workflow Tests
- ✅ Complete workflow: upload → parse → validate
- ✅ Rejection workflow: upload → parse → reject
- ✅ Audit trail recorded for all steps

---

## Configuration

### Django Settings
```python
# core/settings.py
INSTALLED_APPS = [..., "pydantic"]

PARSING = {
    "MAX_FILE_SIZE": 100 * 1024 * 1024,  # 100 MB
    "ALLOWED_MIME_TYPES": ["text/csv", "application/pdf", "application/json"],
    "EXTRACTION_TIMEOUT": 60,  # seconds
}
```

---

## Production Deployment Checklist

- [ ] RawFile.file_content stored in S3/Azure Blob (not inline)
- [ ] Implement file signing (HMAC-SHA256 on file_hash)
- [ ] Add extraction timeout (prevent hanging on large files)
- [ ] Implement extraction queue (Celery, RQ)
- [ ] Add file virus scanning (ClamAV, Windows Defender API)
- [ ] Add extraction rate limiting (max 10 per user per hour)
- [ ] Implement notification for pending validations
- [ ] Add dashboard showing extraction status
- [ ] Backup and disaster recovery for RawFile content
- [ ] Compliance audit: verify all files have audit trail

---

**Document Version**: 1.0
**Status**: Architecture Complete, Implementation In Progress
**Next**: Complete database migrations and run full test suite
