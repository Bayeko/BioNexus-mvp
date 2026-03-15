"""Demo-friendly parsing views (no auth required).

Smart Parser endpoints:
- Upload file -> store with SHA-256 hash
- Parse CSV/text content -> extract equipment & sample records
- List pending validations
- Validate/reject with human corrections
"""

import csv
import hashlib
import io
import json
import re
import uuid

from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.models import RawFile, ParsedData, Tenant, AuditLog


def _get_demo_tenant():
    """Get or create demo tenant for unauthenticated access."""
    tenant, _ = Tenant.objects.get_or_create(
        slug="demo-lab",
        defaults={"name": "Demo Lab"},
    )
    return tenant


def _create_audit_entry(**kwargs):
    """Create an AuditLog entry with proper timestamp and signature chain."""
    now = timezone.now()
    last = AuditLog.objects.order_by('-id').values_list('signature', flat=True).first()
    sig = AuditLog.calculate_signature(
        previous_signature=last,
        entity_type=kwargs['entity_type'],
        entity_id=kwargs['entity_id'],
        operation=kwargs['operation'],
        changes=kwargs.get('changes', {}),
        timestamp=now.isoformat(),
    )
    entry = AuditLog(
        timestamp=now,
        signature=sig,
        previous_signature=last,
        **kwargs,
    )
    entry._skip_validation = True
    entry.save()
    return entry


# ---------------------------------------------------------------------------
# Smart Parser: real content-based extraction
# ---------------------------------------------------------------------------

# Known instrument type patterns detected from column headers or metadata
INSTRUMENT_PATTERNS: dict[str, dict] = {
    "hplc": {
        "keywords": ["retention_time", "peak_area", "peak_height", "rt_min",
                      "area_mau", "hplc", "chromatograph", "column_id"],
        "type": "hplc",
        "name": "HPLC Analysis System",
        "location": "Analytical Chemistry Lab",
    },
    "spectrophotometer": {
        "keywords": ["wavelength", "absorbance", "transmittance", "optical_density",
                      "od_", "nm", "spectro", "uv_vis", "a260", "a280"],
        "type": "spectrophotometer",
        "name": "UV-Vis Spectrophotometer",
        "location": "QC Lab",
    },
    "pcr": {
        "keywords": ["ct_value", "cycle_threshold", "ct", "cq", "tm",
                      "melting_temp", "pcr", "amplification", "target_gene"],
        "type": "pcr_thermocycler",
        "name": "Real-Time PCR System",
        "location": "Molecular Biology Lab",
    },
    "ph_meter": {
        "keywords": ["ph", "ph_value", "conductivity", "mv", "electrode",
                      "buffer", "calibration"],
        "type": "ph_meter",
        "name": "pH Meter",
        "location": "General Lab",
    },
    "balance": {
        "keywords": ["weight", "mass", "tare", "net_weight", "gross_weight",
                      "balance", "weigh"],
        "type": "other",
        "name": "Analytical Balance",
        "location": "Weighing Room",
    },
}

# Column name aliases → canonical sample field names
SAMPLE_FIELD_MAP: dict[str, str] = {
    "sample_id": "sample_id",
    "sampleid": "sample_id",
    "sample": "sample_id",
    "id": "sample_id",
    "sample_name": "name",
    "samplename": "name",
    "name": "name",
    "description": "name",
    "sample_type": "type",
    "sampletype": "type",
    "type": "type",
    "matrix": "type",
    "operator": "collected_by",
    "analyst": "collected_by",
    "collected_by": "collected_by",
    "technician": "collected_by",
    "user": "collected_by",
    "temp": "storage_temperature",
    "temperature": "storage_temperature",
    "storage_temp": "storage_temperature",
    "storage_temperature": "storage_temperature",
    "quantity": "quantity",
    "volume": "quantity",
    "amount": "quantity",
    "qty": "quantity",
    "unit": "quantity_unit",
    "quantity_unit": "quantity_unit",
}

# Valid sample types recognized by the system
VALID_SAMPLE_TYPES = {"blood", "plasma", "serum", "urine", "tissue", "dna", "rna", "other"}


def _normalize_header(header: str) -> str:
    """Normalize a CSV header to a comparable key."""
    return re.sub(r'[^a-z0-9]', '_', header.strip().lower()).strip('_')


def _detect_delimiter(text: str) -> str:
    """Auto-detect CSV delimiter from first lines."""
    first_lines = text.split('\n', 5)[:5]
    joined = '\n'.join(first_lines)
    for delim in ['\t', ';', ',', '|']:
        if delim in joined:
            try:
                reader = csv.reader(io.StringIO(joined), delimiter=delim)
                rows = list(reader)
                if len(rows) >= 2 and len(rows[0]) >= 2:
                    return delim
            except csv.Error:
                continue
    return ','


def _parse_csv_content(content_text: str) -> dict:
    """Parse CSV/TSV content and extract real data.

    Returns dict with equipment_records, sample_records,
    extraction_warnings, and confidence metadata.
    """
    warnings = []
    equipment_records = []
    sample_records = []
    matched_fields = 0
    total_fields = 0

    if not content_text or not content_text.strip():
        return {
            "equipment_records": [],
            "sample_records": [],
            "extraction_warnings": ["File is empty or unreadable"],
            "_confidence": 0.1,
        }

    # --- Parse metadata lines (key: value before the CSV table) ---
    metadata: dict[str, str] = {}
    lines = content_text.strip().split('\n')
    csv_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            csv_start = i + 1
            continue
        # Metadata line: "Key: Value" or "Key = Value" (max 2 parts)
        meta_match = re.match(r'^([A-Za-z_][A-Za-z0-9_ ]{0,30})\s*[:=]\s*(.+)$', stripped)
        if meta_match:
            key = _normalize_header(meta_match.group(1))
            val = meta_match.group(2).strip()
            metadata[key] = val
            csv_start = i + 1
        else:
            break  # hit the CSV header row

    # --- Detect instrument from metadata ---
    instrument_type_info = None
    meta_text = ' '.join(metadata.values()).lower() + ' ' + ' '.join(metadata.keys()).lower()
    for inst_key, info in INSTRUMENT_PATTERNS.items():
        for kw in info["keywords"]:
            if kw in meta_text:
                instrument_type_info = info
                break
        if instrument_type_info:
            break

    # --- Parse CSV data ---
    csv_text = '\n'.join(lines[csv_start:])
    if not csv_text.strip():
        warnings.append("No tabular data found after metadata")
        return {
            "equipment_records": [],
            "sample_records": [],
            "extraction_warnings": warnings,
            "_confidence": 0.15,
        }

    delimiter = _detect_delimiter(csv_text)
    try:
        reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)
        if not reader.fieldnames:
            warnings.append("Could not detect column headers")
            return {
                "equipment_records": [],
                "sample_records": [],
                "extraction_warnings": warnings,
                "_confidence": 0.15,
            }
    except csv.Error as e:
        warnings.append(f"CSV parsing error: {e}")
        return {
            "equipment_records": [],
            "sample_records": [],
            "extraction_warnings": warnings,
            "_confidence": 0.1,
        }

    raw_headers = list(reader.fieldnames)
    norm_headers = [_normalize_header(h) for h in raw_headers]

    # --- Detect instrument from headers if not found in metadata ---
    if not instrument_type_info:
        all_headers_str = ' '.join(norm_headers)
        best_score = 0
        for inst_key, info in INSTRUMENT_PATTERNS.items():
            score = sum(1 for kw in info["keywords"] if kw in all_headers_str)
            if score > best_score:
                best_score = score
                instrument_type_info = info
        if best_score == 0:
            warnings.append(
                "Could not auto-detect instrument type from column headers: "
                + ", ".join(raw_headers)
            )

    # --- Map columns to sample fields ---
    col_mapping: dict[int, str] = {}  # index -> canonical field name
    measurement_cols: list[int] = []  # indices of numeric data columns
    for i, nh in enumerate(norm_headers):
        if nh in SAMPLE_FIELD_MAP:
            col_mapping[i] = SAMPLE_FIELD_MAP[nh]
            matched_fields += 1
        total_fields += 1

    # Identify measurement/data columns (not mapped to sample fields)
    for i, nh in enumerate(norm_headers):
        if i not in col_mapping:
            measurement_cols.append(i)

    # --- Extract rows ---
    rows_parsed = 0
    rows_skipped = 0
    for row_dict in reader:
        row_values = list(row_dict.values())
        if not any(v and v.strip() for v in row_values):
            continue  # skip empty rows

        sample: dict = {}
        for idx, field_name in col_mapping.items():
            raw_val = row_values[idx].strip() if idx < len(row_values) and row_values[idx] else ""
            if not raw_val:
                continue

            if field_name == "storage_temperature":
                try:
                    sample[field_name] = float(re.sub(r'[^\d.\-]', '', raw_val))
                except (ValueError, IndexError):
                    warnings.append(f"Row {rows_parsed+1}: invalid temperature '{raw_val}'")
            elif field_name == "quantity":
                try:
                    sample[field_name] = float(re.sub(r'[^\d.]', '', raw_val))
                except (ValueError, IndexError):
                    pass
            elif field_name == "type":
                normalized_type = raw_val.lower().strip()
                if normalized_type in VALID_SAMPLE_TYPES:
                    sample[field_name] = normalized_type
                else:
                    sample[field_name] = "other"
                    if rows_parsed == 0:
                        warnings.append(
                            f"Sample type '{raw_val}' not in standard types, mapped to 'other'"
                        )
            else:
                sample[field_name] = raw_val

        # Ensure required fields have values
        if "sample_id" not in sample:
            sample["sample_id"] = f"SPL-{uuid.uuid4().hex[:6].upper()}"
        if "name" not in sample:
            # Use first non-mapped value or generate
            for idx in measurement_cols:
                if idx < len(row_values) and row_values[idx] and row_values[idx].strip():
                    sample["name"] = f"Measurement: {raw_headers[idx]}"
                    break
            if "name" not in sample:
                sample["name"] = f"Sample row {rows_parsed + 1}"
        if "type" not in sample:
            sample["type"] = "other"

        sample_records.append(sample)
        rows_parsed += 1

    if rows_parsed == 0:
        warnings.append("No data rows could be extracted from the file")

    # --- Build equipment record from detected instrument + metadata ---
    eq_record = {
        "equipment_id": metadata.get("instrument_id",
                        metadata.get("equipment_id",
                        f"EQ-{uuid.uuid4().hex[:6].upper()}")),
        "name": metadata.get("instrument_name",
                metadata.get("instrument",
                instrument_type_info["name"] if instrument_type_info else "Unknown Instrument")),
        "type": instrument_type_info["type"] if instrument_type_info else "other",
        "location": metadata.get("location",
                    metadata.get("lab",
                    instrument_type_info["location"] if instrument_type_info else "Laboratory")),
        "serial_number": metadata.get("serial_number",
                         metadata.get("serial", "")),
        "status": "active",
    }
    equipment_records.append(eq_record)

    # --- Calculate real confidence score ---
    confidence = _calculate_confidence(
        instrument_detected=instrument_type_info is not None,
        matched_fields=matched_fields,
        total_fields=total_fields,
        rows_parsed=rows_parsed,
        warnings_count=len(warnings),
        has_metadata=len(metadata) > 0,
    )

    return {
        "equipment_records": equipment_records,
        "sample_records": sample_records,
        "extraction_warnings": warnings,
        "_confidence": confidence,
        "_stats": {
            "rows_parsed": rows_parsed,
            "rows_skipped": rows_skipped,
            "columns_detected": len(raw_headers),
            "columns_mapped": matched_fields,
            "instrument_detected": instrument_type_info is not None,
            "metadata_fields": len(metadata),
        },
    }


def _calculate_confidence(
    instrument_detected: bool,
    matched_fields: int,
    total_fields: int,
    rows_parsed: int,
    warnings_count: int,
    has_metadata: bool,
) -> float:
    """Calculate a real confidence score based on parsing quality.

    Score breakdown:
    - Instrument detection:  +0.25
    - Column mapping ratio:  up to +0.30
    - Data rows found:       up to +0.20
    - Metadata present:      +0.10
    - Warning penalty:       -0.05 per warning (max -0.20)
    """
    score = 0.15  # base score for successfully parsing a file

    if instrument_detected:
        score += 0.25

    if total_fields > 0:
        mapping_ratio = matched_fields / total_fields
        score += 0.30 * mapping_ratio

    if rows_parsed >= 5:
        score += 0.20
    elif rows_parsed >= 1:
        score += 0.10

    if has_metadata:
        score += 0.10

    penalty = min(warnings_count * 0.05, 0.20)
    score -= penalty

    return round(max(0.05, min(score, 0.99)), 2)


def _smart_parse(filename: str, content_text: str) -> tuple[dict, float]:
    """Smart Parser: detect format and extract real data from file content.

    Returns (extraction_data, confidence_score).
    """
    lower = filename.lower()

    # Route to appropriate parser based on file extension / content
    if lower.endswith('.csv') or lower.endswith('.tsv') or lower.endswith('.txt'):
        result = _parse_csv_content(content_text)
    elif ',' in content_text or '\t' in content_text or ';' in content_text:
        # Try CSV parsing for files without extension
        result = _parse_csv_content(content_text)
    else:
        # Fallback: try CSV anyway, if that fails return empty
        result = _parse_csv_content(content_text)

    confidence = result.pop("_confidence", 0.5)
    stats = result.pop("_stats", {})

    # Add stats as a non-intrusive info warning
    if stats and stats.get("rows_parsed", 0) > 0:
        result["extraction_warnings"].insert(0,
            f"Parsed {stats['rows_parsed']} rows, "
            f"{stats['columns_mapped']}/{stats['columns_detected']} columns mapped, "
            f"instrument {'detected' if stats['instrument_detected'] else 'not detected'}"
        )

    return result, confidence


@csrf_exempt
@require_http_methods(["GET"])
def parsing_list(request):
    """List all ParsedData records."""
    state_filter = request.GET.get("state", "")

    qs = ParsedData.objects.select_related("raw_file").order_by("-extracted_at")
    if state_filter:
        qs = qs.filter(state=state_filter)

    results = []
    for pd in qs[:50]:
        results.append({
            "id": pd.id,
            "filename": pd.raw_file.filename if pd.raw_file else "unknown",
            "file_hash": (pd.raw_file.file_hash[:12] + "...") if pd.raw_file else "",
            "state": pd.state,
            "extraction_model": pd.extraction_model,
            "extraction_confidence": float(pd.extraction_confidence),
            "extracted_data": pd.parsed_json,
            "confirmed_data": pd.confirmed_json,
            "validation_notes": pd.validation_notes or "",
            "extracted_at": pd.extracted_at.isoformat() if pd.extracted_at else None,
            "validated_at": pd.validated_at.isoformat() if pd.validated_at else None,
        })

    return JsonResponse(results, safe=False)


@csrf_exempt
@require_http_methods(["GET"])
def parsing_detail(request, pk):
    """Get single ParsedData with full details."""
    try:
        pd = ParsedData.objects.select_related("raw_file").get(pk=pk)
    except ParsedData.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    return JsonResponse({
        "id": pd.id,
        "filename": pd.raw_file.filename if pd.raw_file else "unknown",
        "file_hash": pd.raw_file.file_hash if pd.raw_file else "",
        "file_size": pd.raw_file.file_size if pd.raw_file else 0,
        "mime_type": pd.raw_file.mime_type if pd.raw_file else "",
        "state": pd.state,
        "extraction_model": pd.extraction_model,
        "extraction_confidence": float(pd.extraction_confidence),
        "extracted_data": pd.parsed_json,
        "confirmed_data": pd.confirmed_json,
        "validation_notes": pd.validation_notes or "",
        "extracted_at": pd.extracted_at.isoformat() if pd.extracted_at else None,
        "validated_at": pd.validated_at.isoformat() if pd.validated_at else None,
    })


@csrf_exempt
@require_http_methods(["POST"])
def parsing_upload(request):
    """Upload file and run simulated AI extraction.

    Accepts multipart/form-data with 'file' field.
    Returns the newly created ParsedData record.
    """
    if not request.FILES.get("file"):
        return JsonResponse({"error": "No file uploaded"}, status=400)

    uploaded = request.FILES["file"]
    file_content = uploaded.read()
    filename = uploaded.name
    mime_type = uploaded.content_type or "application/octet-stream"
    file_hash = hashlib.sha256(file_content).hexdigest()

    tenant = _get_demo_tenant()

    # Check duplicate
    existing_rf = RawFile.objects.filter(file_hash=file_hash).first()
    if existing_rf:
        existing_pd = ParsedData.objects.filter(raw_file=existing_rf).first()
        if existing_pd:
            return JsonResponse({
                "id": existing_pd.id,
                "duplicate": True,
                "message": "File already uploaded (hash: " + file_hash[:12] + "...)",
            }, status=200)

    # Create RawFile
    raw_file = RawFile.objects.create(
        tenant=tenant,
        user=None,
        filename=filename,
        file_content=file_content,
        file_hash=file_hash,
        file_size=len(file_content),
        mime_type=mime_type,
    )

    # Smart Parser: real content-based extraction
    try:
        content_text = file_content.decode("utf-8", errors="replace")
    except Exception:
        content_text = ""

    parsed_result, confidence = _smart_parse(filename, content_text)

    # Create ParsedData
    parsed_data = ParsedData.objects.create(
        raw_file=raw_file,
        tenant=tenant,
        parsed_json=parsed_result,
        extraction_confidence=confidence,
        extraction_model="BioNexus Smart Parser v1.0",
        state=ParsedData.PENDING,
    )

    # Audit trail
    _create_audit_entry(
        entity_type="ParsedData",
        entity_id=parsed_data.id,
        operation="CREATE",
        changes={"state": {"before": None, "after": "pending"}},
        snapshot_before={},
        snapshot_after={"filename": filename, "file_hash": file_hash[:12]},
        user_email="demo@bionexus.local",
    )

    return JsonResponse({
        "id": parsed_data.id,
        "filename": filename,
        "file_hash": file_hash[:12] + "...",
        "state": parsed_data.state,
        "extraction_confidence": confidence,
        "extracted_data": parsed_result,
        "message": "File uploaded and Smart Parser extraction complete. Awaiting human review.",
    }, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def parsing_validate(request, pk):
    """Validate (approve) a ParsedData record with optional corrections."""
    try:
        pd = ParsedData.objects.get(pk=pk)
    except ParsedData.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if pd.state != ParsedData.PENDING:
        return JsonResponse(
            {"error": "Cannot validate: current state is '" + pd.state + "'"},
            status=400,
        )

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        body = {}

    confirmed_data = body.get("confirmed_data", pd.parsed_json)
    notes = body.get("validation_notes", "")

    pd.state = ParsedData.VALIDATED
    pd.confirmed_json = confirmed_data
    pd.validated_at = timezone.now()
    pd.validation_notes = notes
    pd.save(update_fields=[
        "state", "confirmed_json", "validated_at", "validation_notes",
    ])

    _create_audit_entry(
        entity_type="ParsedData",
        entity_id=pd.id,
        operation="UPDATE",
        changes={"state": {"before": "pending", "after": "validated"}},
        snapshot_before={"state": "pending"},
        snapshot_after={"state": "validated", "notes": notes},
        user_email="demo@bionexus.local",
    )

    return JsonResponse({
        "id": pd.id,
        "state": pd.state,
        "validated_at": pd.validated_at.isoformat(),
        "message": "Parsing validated successfully.",
    })


@csrf_exempt
@require_http_methods(["POST"])
def parsing_reject(request, pk):
    """Reject a ParsedData record."""
    try:
        pd = ParsedData.objects.get(pk=pk)
    except ParsedData.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if pd.state != ParsedData.PENDING:
        return JsonResponse(
            {"error": "Cannot reject: current state is '" + pd.state + "'"},
            status=400,
        )

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        body = {}

    reason = body.get("reason", "Rejected by reviewer")

    pd.state = ParsedData.REJECTED
    pd.validation_notes = reason
    pd.validated_at = timezone.now()
    pd.save(update_fields=["state", "validation_notes", "validated_at"])

    _create_audit_entry(
        entity_type="ParsedData",
        entity_id=pd.id,
        operation="UPDATE",
        changes={"state": {"before": "pending", "after": "rejected"}},
        snapshot_before={"state": "pending"},
        snapshot_after={"state": "rejected", "reason": reason},
        user_email="demo@bionexus.local",
    )

    return JsonResponse({
        "id": pd.id,
        "state": pd.state,
        "message": "Parsing rejected.",
    })

