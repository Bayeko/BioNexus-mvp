"""End-to-end signal tests for all 4 LIMS connectors.

Verifies that:
  - When VENDOR_INTEGRATION_ENABLED + VENDOR_MODE=mock, creating a
    Measurement fires a push and produces an IntegrationPushLog row
    with the right ``vendor`` field
  - When disabled, no row is produced for that vendor
  - All 4 vendors can be active simultaneously and produce 4 distinct
    log rows for one Measurement
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from modules.integrations.base.client import PushResult
from modules.integrations.veeva.models import IntegrationPushLog


@pytest.fixture
def setup_db():
    from core.models import Tenant
    from modules.instruments.models import Instrument
    from modules.samples.models import Sample

    tenant = Tenant.objects.create(name="LBN-Test")
    instrument = Instrument.objects.create(
        name="HPLC-001",
        instrument_type="HPLC",
        serial_number="HPLC-001",
        connection_type="rs232",
        status="online",
    )
    sample = Sample.objects.create(
        sample_id="QC-100",
        instrument=instrument,
        batch_number="LOT-2026-04",
        status="in_progress",
        created_by="OP-042",
    )
    return {"tenant": tenant, "instrument": instrument, "sample": sample}


def _ok_client():
    client = MagicMock()
    client.mode = "mock"
    client.push_object.return_value = PushResult(
        ok=True, http_status=201, vault_id="MOCK-XYZ"
    )
    return client


VENDOR_PARAMS = [
    # (settings prefix, build_client patch target, expected vendor field)
    (
        "EMPOWER",
        "modules.integrations.lims_connectors.empower.service.build_empower_client",
        "empower",
    ),
    (
        "LABWARE",
        "modules.integrations.lims_connectors.labware.service.build_labware_client",
        "labware",
    ),
    (
        "STARLIMS",
        "modules.integrations.lims_connectors.starlims.service.build_starlims_client",
        "starlims",
    ),
    (
        "BENCHLING",
        "modules.integrations.lims_connectors.benchling.service.build_benchling_client",
        "benchling",
    ),
]


@pytest.mark.django_db
class TestPerVendorSignal:
    @pytest.mark.parametrize("prefix,patch_target,vendor", VENDOR_PARAMS)
    def test_enabled_vendor_creates_log_row(
        self, setup_db, settings, prefix, patch_target, vendor
    ):
        setattr(settings, f"{prefix}_INTEGRATION_ENABLED", True)
        setattr(settings, f"{prefix}_MODE", "mock")
        setattr(settings, f"{prefix}_BASE_URL", "http://localhost:8001")
        setattr(settings, f"{prefix}_SHARED_SECRET", "secret-32bytes-aaaaaaaaaaaaa")

        # All OTHER vendors disabled.
        for other in [p for p, _, _ in VENDOR_PARAMS if p != prefix]:
            setattr(settings, f"{other}_INTEGRATION_ENABLED", False)
        # Veeva off too.
        settings.VEEVA_INTEGRATION_ENABLED = False

        from modules.measurements.models import Measurement

        with patch(patch_target, return_value=_ok_client()):
            m = Measurement.objects.create(
                sample=setup_db["sample"],
                instrument=setup_db["instrument"],
                parameter="Caffeine",
                value=Decimal("99.82"),
                unit="%",
                measured_at=datetime.now(timezone.utc),
            )

        logs = IntegrationPushLog.objects.filter(
            source_measurement_id=m.id, vendor=vendor
        )
        assert logs.count() == 1
        assert logs.first().status == IntegrationPushLog.STATUS_SUCCESS
        assert logs.first().target_object_id == "MOCK-XYZ"

    @pytest.mark.parametrize("prefix,patch_target,vendor", VENDOR_PARAMS)
    def test_disabled_vendor_produces_no_row(
        self, setup_db, settings, prefix, patch_target, vendor
    ):
        for p, _, _ in VENDOR_PARAMS:
            setattr(settings, f"{p}_INTEGRATION_ENABLED", False)
        settings.VEEVA_INTEGRATION_ENABLED = False

        from modules.measurements.models import Measurement

        Measurement.objects.create(
            sample=setup_db["sample"],
            instrument=setup_db["instrument"],
            parameter="Caffeine",
            value=Decimal("99.82"),
            unit="%",
            measured_at=datetime.now(timezone.utc),
        )

        assert IntegrationPushLog.objects.filter(vendor=vendor).count() == 0


@pytest.mark.django_db
class TestAllVendorsActiveSimultaneously:
    def test_one_measurement_fires_four_pushes(self, setup_db, settings):
        """All 4 LIMS connectors enabled together → 4 distinct log rows."""
        for prefix, _, _ in VENDOR_PARAMS:
            setattr(settings, f"{prefix}_INTEGRATION_ENABLED", True)
            setattr(settings, f"{prefix}_MODE", "mock")
            setattr(settings, f"{prefix}_BASE_URL", "http://localhost:8001")
            setattr(settings, f"{prefix}_SHARED_SECRET", "s-32bytes-aaaaaaaaaaaaaaa")
        settings.VEEVA_INTEGRATION_ENABLED = False

        from modules.measurements.models import Measurement

        with patch(
            "modules.integrations.lims_connectors.empower.service.build_empower_client",
            return_value=_ok_client(),
        ), patch(
            "modules.integrations.lims_connectors.labware.service.build_labware_client",
            return_value=_ok_client(),
        ), patch(
            "modules.integrations.lims_connectors.starlims.service.build_starlims_client",
            return_value=_ok_client(),
        ), patch(
            "modules.integrations.lims_connectors.benchling.service.build_benchling_client",
            return_value=_ok_client(),
        ):
            m = Measurement.objects.create(
                sample=setup_db["sample"],
                instrument=setup_db["instrument"],
                parameter="Caffeine",
                value=Decimal("99.82"),
                unit="%",
                measured_at=datetime.now(timezone.utc),
            )

        rows = IntegrationPushLog.objects.filter(source_measurement_id=m.id)
        vendors_pushed = {r.vendor for r in rows}
        assert vendors_pushed == {"empower", "labware", "starlims", "benchling"}
        assert rows.count() == 4
        assert all(r.status == IntegrationPushLog.STATUS_SUCCESS for r in rows)
