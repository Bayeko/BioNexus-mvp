"""Demo-friendly parsing views (no auth required).

Simplified endpoints for the AI parsing workflow demo:
- Upload file -> store with SHA-256 hash
- Simulate AI extraction -> create ParsedData(PENDING)
- List pending validations
- Validate/reject with human corrections
"""

import hashlib
import json
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
    # Get previous signature for chain
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


def _simulate_ai_extraction(filename, content_text):
    """Simulate AI extraction from file content.

    In production this would call GPT-4-turbo. For demo, generates
    realistic-looking extracted data based on file content.
    """
    equipment_records = []
    sample_records = []
    warnings = []

    lower = filename.lower()
    if "spectro" in lower or "uv" in lower:
        equipment_records.append({
            "equipment_id": "SPEC-" + uuid.uuid4().hex[:6].upper(),
            "name": "UV-Vis Spectrophotometer",
            "type": "spectrophotometer",
            "location": "Lab Room 101",
            "serial_number": "SN-" + uuid.uuid4().hex[:8].upper(),
            "status": "active",
        })
        sample_records.append({
            "sample_id": "SPL-" + uuid.uuid4().hex[:6].upper(),
            "name": "Protein concentration assay",
            "type": "serum",
            "collected_by": "Lab Technician",
            "storage_temperature": 4.0,
            "quantity": 2.5,
            "quantity_unit": "mL",
        })
    elif "pcr" in lower:
        equipment_records.append({
            "equipment_id": "PCR-" + uuid.uuid4().hex[:6].upper(),
            "name": "Real-Time PCR System",
            "type": "pcr_thermocycler",
            "location": "Molecular Biology Lab",
            "serial_number": "SN-" + uuid.uuid4().hex[:8].upper(),
            "status": "active",
        })
        sample_records.extend([
            {
                "sample_id": "SPL-" + uuid.uuid4().hex[:6].upper(),
                "name": "Patient DNA sample",
                "type": "blood",
                "collected_by": "Dr. Smith",
                "storage_temperature": -20.0,
                "quantity": 0.5,
                "quantity_unit": "mL",
            },
            {
                "sample_id": "SPL-" + uuid.uuid4().hex[:6].upper(),
                "name": "Control DNA",
                "type": "plasma",
                "collected_by": "Lab Technician",
                "storage_temperature": -20.0,
                "quantity": 0.1,
                "quantity_unit": "mL",
            },
        ])
    elif "hplc" in lower:
        equipment_records.append({
            "equipment_id": "HPLC-" + uuid.uuid4().hex[:6].upper(),
            "name": "HPLC Analysis System",
            "type": "hplc",
            "location": "Analytical Chemistry Lab",
            "serial_number": "SN-" + uuid.uuid4().hex[:8].upper(),
            "status": "active",
        })
        sample_records.append({
            "sample_id": "SPL-" + uuid.uuid4().hex[:6].upper(),
            "name": "Compound purity analysis",
            "type": "tissue",
            "collected_by": "Analyst Johnson",
            "storage_temperature": -80.0,
            "quantity": 10.0,
            "quantity_unit": "mg",
        })
    else:
        equipment_records.append({
            "equipment_id": "EQ-" + uuid.uuid4().hex[:6].upper(),
            "name": "Laboratory Instrument",
            "type": "ph_meter",
            "location": "General Lab",
            "serial_number": "SN-" + uuid.uuid4().hex[:8].upper(),
            "status": "active",
        })
        sample_records.append({
            "sample_id": "SPL-" + uuid.uuid4().hex[:6].upper(),
            "name": "Analysis sample",
            "type": "serum",
            "collected_by": "Lab Operator",
            "storage_temperature": 4.0,
            "quantity": 1.0,
            "quantity_unit": "mL",
        })
        warnings.append(
            "Generic extraction - filename did not match known instrument patterns"
        )

    if content_text and len(content_text) < 50:
        warnings.append("File content is very short - extraction confidence reduced")

    return {
        "equipment_records": equipment_records,
        "sample_records": sample_records,
        "extraction_warnings": warnings,
    }


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

    # Simulate AI extraction
    try:
        content_text = file_content.decode("utf-8", errors="replace")
    except Exception:
        content_text = ""

    ai_data = _simulate_ai_extraction(filename, content_text)
    confidence = 0.92 if not ai_data.get("extraction_warnings") else 0.78

    # Create ParsedData
    parsed_data = ParsedData.objects.create(
        raw_file=raw_file,
        tenant=tenant,
        parsed_json=ai_data,
        extraction_confidence=confidence,
        extraction_model="gpt-4-turbo (simulated)",
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
        "extracted_data": ai_data,
        "message": "File uploaded and AI extraction complete. Awaiting human review.",
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

