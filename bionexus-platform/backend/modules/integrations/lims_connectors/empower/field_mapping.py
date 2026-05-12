"""BioNexus Measurement -> Waters Empower Web API ``Result`` payload.

Empower stores HPLC/UPLC results as ``Result`` objects nested under a
``Sample`` within a ``Sample Set``. For the push-only v1 this connector
implements, we send each measurement as a standalone ``Result`` row
with sample/method references; binding it to an existing Empower
``Sample Set`` is a v2 concern.
"""

from __future__ import annotations

from typing import Any


def measurement_to_result(measurement: Any) -> dict:
    """Empower ``Result`` payload shape.

    Reference: Empower Web API (Waters) — Result resource POST. Field
    names follow Empower's camelCase convention.
    """
    context = _get_context(measurement)
    return {
        "sampleName": getattr(measurement.sample, "sample_id", "") or "",
        "method": getattr(context, "method", "") or "",
        "peakName": measurement.parameter,
        "area": str(measurement.value),
        "amount": str(measurement.value),
        "unit": measurement.unit,
        "injection": "1",
        "measuredAt": (
            measurement.measured_at.isoformat() if measurement.measured_at else ""
        ),
        "operator": getattr(context, "operator", "") or "",
        "lotNumber": getattr(context, "lot_number", "") or "",
        "sourceHash": measurement.data_hash,
        "instrumentSerial": getattr(measurement.instrument, "serial_number", "") or "",
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
