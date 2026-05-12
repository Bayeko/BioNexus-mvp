"""BioNexus → Veeva Vault field mapping (LBN-INT-VEEVA-001 §5).

This module is the *single* place where the BioNexus internal data model
is translated into the shape Veeva Vault accepts. Keeping it isolated
makes it cheap to:
  - Adapt to per-customer mapping profiles later (one mapping function
    becomes one mapping class)
  - Pin the mapping under tests so regulatory regression is detectable
  - Diff the mapping against the spec without spelunking through the
    push pipeline

This module performs **no I/O** and has **no Django ORM dependencies**
beyond reading attributes off model instances — that keeps it testable
in isolation and safe to call from anywhere in the push pipeline.
"""

from __future__ import annotations

from typing import Any


def measurement_to_quality_event(measurement: Any) -> dict:
    """Translate a :class:`Measurement` into a Vault ``quality_event__v`` payload.

    Spec mapping (LBN-INT-VEEVA-001 §5, v0.1 DRAFT):

      ===========================  ====================================
      BioNexus attribute            Vault field
      ===========================  ====================================
      measurement.parameter         parameter__v
      measurement.value             value__v          (string form)
      measurement.unit              unit__v
      measurement.measured_at       measured_at__v    (ISO-8601 UTC)
      measurement.data_hash         source_hash__v    (SHA-256 hex)
      measurement.sample.barcode    sample_external_id__v
      context.operator              reported_by__v
      context.lot_number            lot__v
      context.method                method__v
      context.sample_id             sample_alias__v
      instrument.serial_number      instrument__v
      ===========================  ====================================

    Missing optional fields (no operator, no lot, etc.) become empty
    strings rather than being absent, so the Vault schema validation
    receives a stable shape regardless of how much context BioNexus
    captured. Vault rejects extra fields by default, so we send
    *exactly* the fields above — no debug clutter.

    The ``__v`` suffix is Veeva's convention for custom-field-on-standard-
    object. The standard object type is ``quality_event__v`` itself.
    """
    context = _get_context(measurement)
    instrument = measurement.instrument
    sample = measurement.sample

    return {
        # Core measurement
        "parameter__v": measurement.parameter,
        "value__v": str(measurement.value),
        "unit__v": measurement.unit,
        "measured_at__v": (
            measurement.measured_at.isoformat() if measurement.measured_at else ""
        ),
        # Integrity proof
        "source_hash__v": measurement.data_hash,
        # Sample linkage — BioNexus uses ``sample_id`` (business identifier
        # like "SMP-2024-001"); older drafts of the spec called this
        # ``barcode``, kept here as a fallback if a downstream model adds
        # one.
        "sample_external_id__v": (
            getattr(sample, "sample_id", "")
            or getattr(sample, "barcode", "")
            or ""
        ),
        # Operator + lot + method (pulled from context if present)
        "reported_by__v": getattr(context, "operator", "") or "",
        "lot__v": getattr(context, "lot_number", "") or "",
        "method__v": getattr(context, "method", "") or "",
        "sample_alias__v": getattr(context, "sample_id", "") or "",
        # Instrument provenance
        "instrument__v": getattr(instrument, "serial_number", "") or "",
    }


def report_to_document(report: Any) -> dict:
    """Translate a :class:`CertifiedReport` into a Vault ``document__v`` metadata payload.

    The PDF itself is uploaded as a multipart attachment by the client;
    this function returns only the JSON metadata that accompanies it.

    Spec mapping (LBN-INT-VEEVA-001 §5):

      =========================  ===========================
      BioNexus attribute          Vault document field
      =========================  ===========================
      report.id                   external_id__v
      report.title                name__v
      report.signed_by            signed_by__v
      report.signed_at            signed_at__v (ISO-8601)
      report.signature_hash       signature_hash__v
      report.tenant.name          source_system__v
      =========================  ===========================
    """
    return {
        "external_id__v": f"BNX-RPT-{report.id}",
        "name__v": getattr(report, "title", "") or f"BioNexus Certified Report #{report.id}",
        "signed_by__v": getattr(report, "signed_by", "") or "",
        "signed_at__v": (
            report.signed_at.isoformat()
            if getattr(report, "signed_at", None)
            else ""
        ),
        "signature_hash__v": getattr(report, "signature_hash", "") or "",
        "source_system__v": (
            getattr(getattr(report, "tenant", None), "name", "") or "BioNexus"
        ),
    }


def _get_context(measurement: Any) -> Any:
    """Return the related :class:`MeasurementContext` or a stub with empty fields.

    Measurement.context is OneToOne, so accessing a non-existent reverse
    relation would raise ``DoesNotExist``. Rather than scatter try/except
    through the mapping, we centralize the "no context" fallback here.
    """
    try:
        return measurement.context
    except Exception:
        return _EmptyContext()


class _EmptyContext:
    """Stand-in for a missing MeasurementContext.

    All string fields default to empty strings so the mapping output
    stays a stable shape even when no context was captured.
    """

    operator = ""
    lot_number = ""
    method = ""
    sample_id = ""
