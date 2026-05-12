"""End-to-end Veeva mock demo for FL Basel.

Run AFTER starting the mock Vault server (`python manage.py veeva_mock_server`)
and the BioNexus backend with VEEVA_MODE=mock + VEEVA_INTEGRATION_ENABLED=true.

What it does:
  1. Creates a minimum Tenant -> Instrument -> Sample chain in BioNexus
  2. Inserts a few Measurements (which fires the post_save signal)
  3. Sleeps briefly to let the pushes complete
  4. Pulls the IntegrationPushLog rows back and prints them
  5. Pulls the mock Vault's view of the world and prints what landed there

Usage (from bionexus-platform/backend/, with the venv active):
  $ export VEEVA_MODE=mock VEEVA_INTEGRATION_ENABLED=true \
           VEEVA_BASE_URL=http://localhost:8001 \
           VEEVA_SHARED_SECRET=demo-secret-32bytes-aaaaaaaaaaaaa
  $ python manage.py veeva_mock_server &   # in another terminal
  $ python demo_veeva.py
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

import requests  # noqa: E402
from django.conf import settings  # noqa: E402

from core.models import Tenant  # noqa: E402
from modules.instruments.models import Instrument  # noqa: E402
from modules.measurements.models import Measurement  # noqa: E402
from modules.samples.models import Sample  # noqa: E402
from modules.integrations.veeva.models import IntegrationPushLog  # noqa: E402


SEPARATOR = "-" * 70


def _stage(title: str) -> None:
    print(SEPARATOR)
    print(f"  {title}")
    print(SEPARATOR)


def _check_settings() -> None:
    if str(getattr(settings, "VEEVA_MODE", "disabled")).lower() != "mock":
        print(
            "ERROR: VEEVA_MODE is not 'mock'. Set VEEVA_MODE=mock and "
            "VEEVA_INTEGRATION_ENABLED=true before running this demo."
        )
        sys.exit(1)
    if not getattr(settings, "VEEVA_INTEGRATION_ENABLED", False):
        print("ERROR: VEEVA_INTEGRATION_ENABLED is false.")
        sys.exit(1)


def _ensure_chain():
    tenant, _ = Tenant.objects.get_or_create(name="LBN-Demo")
    instrument, _ = Instrument.objects.get_or_create(
        serial_number="HPLC-FLBASEL",
        defaults={
            "name": "Agilent 1260 — Demo",
            "instrument_type": "HPLC",
            "connection_type": "rs232",
            "status": "online",
        },
    )
    sample, _ = Sample.objects.get_or_create(
        sample_id="QC-FLB-100",
        defaults={
            "instrument": instrument,
            "batch_number": "LOT-2026-04",
            "status": "in_progress",
            "created_by": "OP-042",
        },
    )
    return tenant, instrument, sample


def _create_measurements(sample, instrument) -> list[Measurement]:
    """Insert 3 measurements — each fires the Veeva push signal."""
    readings = [
        ("Caffeine", Decimal("99.8"), "%"),
        ("Aspirin", Decimal("0.18"), "%"),
        ("Impurity_A", Decimal("0.04"), "%"),
    ]
    created = []
    now = datetime.now(timezone.utc)
    for parameter, value, unit in readings:
        m = Measurement.objects.create(
            sample=sample,
            instrument=instrument,
            parameter=parameter,
            value=value,
            unit=unit,
            measured_at=now,
        )
        created.append(m)
        print(f"  created Measurement#{m.id}: {parameter}={value}{unit}")
    return created


def _wait_for_pushes(min_count: int, timeout_s: float = 5.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        n = IntegrationPushLog.objects.filter(
            status=IntegrationPushLog.STATUS_SUCCESS
        ).count()
        if n >= min_count:
            return
        time.sleep(0.2)


def _show_push_log() -> None:
    rows = IntegrationPushLog.objects.all().order_by("-created_at")[:10]
    print(f"  {len(rows)} push log entr{'y' if len(rows) == 1 else 'ies'}:")
    for r in rows:
        print(
            f"    #{r.id} M#{r.source_measurement_id} -> "
            f"{r.target_object_type} {r.target_object_id or '-'} "
            f"status={r.status} http={r.http_status} attempts={r.attempts}"
        )


def _show_vault_state() -> None:
    try:
        resp = requests.get(
            settings.VEEVA_BASE_URL.rstrip("/")
            + "/api/v23.1/vobjects/quality_event__v",
            timeout=5,
        )
    except Exception as exc:
        print(f"  Cannot reach mock Vault: {exc}")
        return
    if not resp.ok:
        print(f"  Mock Vault returned HTTP {resp.status_code}")
        return
    data = resp.json()
    print(f"  Mock Vault holds {len(data)} quality_event__v object(s):")
    for obj in data[:10]:
        payload = obj.get("payload", {})
        print(
            f"    {obj['id']:<20} "
            f"param={payload.get('parameter__v'):<12} "
            f"value={payload.get('value__v'):<8} "
            f"lot={payload.get('lot__v')}"
        )


def main() -> None:
    _check_settings()

    _stage("Step 1: BioNexus chain setup")
    tenant, instrument, sample = _ensure_chain()
    print(f"  Tenant: {tenant.name} | Instrument: {instrument.name} | Sample: {sample.sample_id}")

    _stage("Step 2: Capture 3 measurements (fires Veeva push signal)")
    measurements = _create_measurements(sample, instrument)

    _stage("Step 3: Wait briefly for pushes")
    _wait_for_pushes(min_count=len(measurements))

    _stage("Step 4: BioNexus push log (audit trail of every attempt)")
    _show_push_log()

    _stage("Step 5: Mock Vault contents (what actually landed there)")
    _show_vault_state()

    _stage("Done.")


if __name__ == "__main__":
    main()
