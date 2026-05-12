"""BioNexus Measurement -> LabWare LIMS REST ``Result`` payload.

LabWare LIMS exposes both SOAP and REST surfaces; the REST surface is
preferred for modern integrations. Object names follow LabWare's
table-oriented terminology (``ANALYSIS``, ``SAMPLE``, ``RESULT``).
"""

from __future__ import annotations

from typing import Any


def measurement_to_result(measurement: Any) -> dict:
    context = _get_context(measurement)
    return {
        "sample_id": getattr(measurement.sample, "sample_id", "") or "",
        "lot_no": getattr(context, "lot_number", "") or "",
        "analysis": getattr(context, "method", "") or "",
        "test_name": measurement.parameter,
        "result_value": str(measurement.value),
        "uom": measurement.unit,
        "tested_on": (
            measurement.measured_at.isoformat() if measurement.measured_at else ""
        ),
        "tested_by": getattr(context, "operator", "") or "",
        "instrument": getattr(measurement.instrument, "serial_number", "") or "",
        "source_hash": measurement.data_hash,
    }


def _get_context(measurement: Any) -> Any:
    try:
        return measurement.context
    except Exception:
        return _Empty()


class _Empty:
    operator = ""
    lot_number = ""
    method = ""
