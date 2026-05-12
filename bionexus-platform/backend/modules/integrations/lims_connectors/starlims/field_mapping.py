"""BioNexus Measurement -> STARLIMS REST ``TestResult`` payload."""

from __future__ import annotations

from typing import Any


def measurement_to_test_result(measurement: Any) -> dict:
    context = _get_context(measurement)
    return {
        "sample": getattr(measurement.sample, "sample_id", "") or "",
        "batch": getattr(context, "lot_number", "") or "",
        "test": measurement.parameter,
        "value": str(measurement.value),
        "units": measurement.unit,
        "method": getattr(context, "method", "") or "",
        "operator": getattr(context, "operator", "") or "",
        "tested_at": (
            measurement.measured_at.isoformat() if measurement.measured_at else ""
        ),
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
