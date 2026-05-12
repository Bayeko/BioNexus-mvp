"""Multi-vendor LIMS push demo (FL Basel-ready).

Boots the BioNexus chain, creates a single Measurement, and shows that
ALL 5 connectors (Veeva + Empower + LabWare + STARLIMS + Benchling)
push it to the unified mock server in parallel.

Usage (3 terminals, all from bionexus-platform/backend/ with the venv active):

  # 1) Unified mock LIMS server
  $ python manage.py lims_mock_server

  # 2) (this script's env)
  $ export VEEVA_MODE=mock VEEVA_INTEGRATION_ENABLED=true \\
           VEEVA_BASE_URL=http://localhost:8001/veeva \\
           VEEVA_SHARED_SECRET=demo
  $ export EMPOWER_MODE=mock EMPOWER_INTEGRATION_ENABLED=true \\
           EMPOWER_BASE_URL=http://localhost:8001/empower \\
           EMPOWER_SHARED_SECRET=demo
  $ export LABWARE_MODE=mock LABWARE_INTEGRATION_ENABLED=true \\
           LABWARE_BASE_URL=http://localhost:8001/labware \\
           LABWARE_SHARED_SECRET=demo
  $ export STARLIMS_MODE=mock STARLIMS_INTEGRATION_ENABLED=true \\
           STARLIMS_BASE_URL=http://localhost:8001/starlims \\
           STARLIMS_SHARED_SECRET=demo
  $ export BENCHLING_MODE=mock BENCHLING_INTEGRATION_ENABLED=true \\
           BENCHLING_BASE_URL=http://localhost:8001/benchling \\
           BENCHLING_SHARED_SECRET=demo

  # 3) Run the demo
  $ python demo_lims.py
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.conf import settings  # noqa: E402

from core.models import Tenant  # noqa: E402
from modules.instruments.models import Instrument  # noqa: E402
from modules.measurements.models import Measurement  # noqa: E402
from modules.samples.models import Sample  # noqa: E402
from modules.integrations.veeva.models import IntegrationPushLog  # noqa: E402


VENDORS = ["veeva", "empower", "labware", "starlims", "benchling"]


def _stage(title: str) -> None:
    print("-" * 70)
    print(f"  {title}")
    print("-" * 70)


def _check_settings() -> None:
    enabled = []
    for v in VENDORS:
        prefix = v.upper()
        if str(getattr(settings, f"{prefix}_MODE", "disabled")).lower() == "mock":
            if bool(getattr(settings, f"{prefix}_INTEGRATION_ENABLED", False)):
                enabled.append(v)
    if not enabled:
        print("ERROR: no vendor is configured for mock mode. See script docstring.")
        sys.exit(1)
    print(f"  Active vendors (mock): {', '.join(enabled)}")


def _ensure_chain():
    tenant, _ = Tenant.objects.get_or_create(name="LBN-Demo-MultiLims")
    instrument, _ = Instrument.objects.get_or_create(
        serial_number="HPLC-FLBASEL-2",
        defaults={
            "name": "Agilent 1290 — Multi-LIMS Demo",
            "instrument_type": "HPLC",
            "connection_type": "rs232",
            "status": "online",
        },
    )
    sample, _ = Sample.objects.get_or_create(
        sample_id="QC-FLB-200",
        defaults={
            "instrument": instrument,
            "batch_number": "LOT-2026-05",
            "status": "in_progress",
            "created_by": "OP-007",
        },
    )
    return tenant, instrument, sample


def _create_measurement(sample, instrument) -> Measurement:
    m = Measurement.objects.create(
        sample=sample,
        instrument=instrument,
        parameter="Caffeine",
        value=Decimal("99.82"),
        unit="%",
        measured_at=datetime.now(timezone.utc),
    )
    print(f"  created Measurement#{m.id}: {m.parameter}={m.value}{m.unit}")
    return m


def _wait_for_pushes(measurement_id: int, min_per_vendor: int = 1, timeout_s: float = 6.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        vendors_with_rows = set(
            IntegrationPushLog.objects
            .filter(source_measurement_id=measurement_id)
            .values_list("vendor", flat=True)
        )
        if len(vendors_with_rows) >= min_per_vendor * len(VENDORS):
            return
        time.sleep(0.2)


def _show_log(measurement_id: int) -> None:
    rows = (
        IntegrationPushLog.objects
        .filter(source_measurement_id=measurement_id)
        .order_by("vendor")
    )
    print(f"  {rows.count()} push log row(s) for Measurement#{measurement_id}:")
    for r in rows:
        print(
            f"    [{r.vendor:<10}] -> {r.target_object_id or '-':<20} "
            f"status={r.status:<10} http={r.http_status or '-':<4} attempts={r.attempts}"
        )


def main() -> None:
    _stage("Configuration")
    _check_settings()

    _stage("BioNexus chain setup")
    tenant, instrument, sample = _ensure_chain()
    print(f"  Tenant: {tenant.name} | Instrument: {instrument.name} | Sample: {sample.sample_id}")

    _stage("Capture 1 measurement (fires all enabled vendor pushes)")
    m = _create_measurement(sample, instrument)

    _stage("Wait briefly for pushes")
    _wait_for_pushes(m.id)

    _stage("BioNexus IntegrationPushLog (one row per vendor per measurement)")
    _show_log(m.id)

    _stage("Done.")


if __name__ == "__main__":
    main()
