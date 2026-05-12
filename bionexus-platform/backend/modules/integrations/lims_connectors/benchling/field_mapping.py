"""BioNexus Measurement -> Benchling API v2 ``ResultRow`` payload.

Benchling structures laboratory data via Result Tables driven by
configurable Schemas. Each result row references a schema_id and
populates field values. We rely on ``BENCHLING_RESULT_SCHEMA_ID`` from
the env to point at the customer's BioNexus result schema.
"""

from __future__ import annotations

import os
from typing import Any


def measurement_to_result_row(measurement: Any) -> dict:
    context = _get_context(measurement)
    schema_id = os.environ.get(
        "BENCHLING_RESULT_SCHEMA_ID", "sch_bnx_default"
    )
    return {
        "schemaId": schema_id,
        "fields": {
            "sampleId": {"value": getattr(measurement.sample, "sample_id", "") or ""},
            "parameter": {"value": measurement.parameter},
            "value": {"value": str(measurement.value)},
            "unit": {"value": measurement.unit},
            "method": {"value": getattr(context, "method", "") or ""},
            "operator": {"value": getattr(context, "operator", "") or ""},
            "lotNumber": {"value": getattr(context, "lot_number", "") or ""},
            "measuredAt": {"value": (
                measurement.measured_at.isoformat() if measurement.measured_at else ""
            )},
            "instrumentSerial": {
                "value": getattr(measurement.instrument, "serial_number", "") or ""
            },
            "sourceHash": {"value": measurement.data_hash},
        },
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
