"""End-to-end test: creating a Measurement fires the Veeva push signal.

Uses a real Django ORM (via @pytest.mark.django_db) + a patched
build_client_from_settings so no real HTTP is involved.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from modules.integrations.veeva.client import PushResult
from modules.integrations.veeva.models import IntegrationPushLog


@pytest.fixture
def setup_db():
    """Create the minimum BioNexus chain (tenant → instrument → sample) for a Measurement."""
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


def _ok_client(vault_id: str = "VVQE-XYZ"):
    client = MagicMock()
    client.mode = "mock"
    client.push_quality_event.return_value = PushResult(
        ok=True, http_status=201, vault_id=vault_id
    )
    return client


@pytest.mark.django_db
class TestPostSaveSignal:
    def test_disabled_integration_does_not_push(self, setup_db, settings):
        settings.VEEVA_INTEGRATION_ENABLED = False
        from modules.measurements.models import Measurement

        Measurement.objects.create(
            sample=setup_db["sample"],
            instrument=setup_db["instrument"],
            parameter="pH",
            value=Decimal("7.42"),
            unit="pH",
            measured_at=datetime.now(timezone.utc),
        )
        assert IntegrationPushLog.objects.count() == 0

    def test_mode_disabled_does_not_push(self, setup_db, settings):
        settings.VEEVA_INTEGRATION_ENABLED = True
        settings.VEEVA_MODE = "disabled"
        from modules.measurements.models import Measurement

        Measurement.objects.create(
            sample=setup_db["sample"],
            instrument=setup_db["instrument"],
            parameter="pH",
            value=Decimal("7.42"),
            unit="pH",
            measured_at=datetime.now(timezone.utc),
        )
        assert IntegrationPushLog.objects.count() == 0

    def test_enabled_signal_creates_push_log(self, setup_db, settings):
        settings.VEEVA_INTEGRATION_ENABLED = True
        settings.VEEVA_MODE = "mock"
        settings.VEEVA_BASE_URL = "http://localhost:8001"
        settings.VEEVA_SHARED_SECRET = "test-secret-32-bytes-aaaaaaaaaaaa"

        from modules.measurements.models import Measurement

        with patch(
            "modules.integrations.veeva.service.build_client_from_settings",
            return_value=_ok_client(vault_id="VVQE-FROMSIGNAL"),
        ):
            m = Measurement.objects.create(
                sample=setup_db["sample"],
                instrument=setup_db["instrument"],
                parameter="pH",
                value=Decimal("7.42"),
                unit="pH",
                measured_at=datetime.now(timezone.utc),
            )

        logs = IntegrationPushLog.objects.filter(source_measurement_id=m.id)
        assert logs.count() == 1
        log = logs.first()
        assert log.status == IntegrationPushLog.STATUS_SUCCESS
        assert log.target_object_id == "VVQE-FROMSIGNAL"

    def test_update_does_not_trigger_second_push(self, setup_db, settings):
        settings.VEEVA_INTEGRATION_ENABLED = True
        settings.VEEVA_MODE = "mock"
        settings.VEEVA_BASE_URL = "http://localhost:8001"
        settings.VEEVA_SHARED_SECRET = "test-secret-32-bytes-aaaaaaaaaaaa"

        from modules.measurements.models import Measurement

        with patch(
            "modules.integrations.veeva.service.build_client_from_settings",
            return_value=_ok_client(),
        ):
            m = Measurement.objects.create(
                sample=setup_db["sample"],
                instrument=setup_db["instrument"],
                parameter="pH",
                value=Decimal("7.42"),
                unit="pH",
                measured_at=datetime.now(timezone.utc),
            )
            # Save again (e.g. to recompute hash). Signal must not fire push again.
            m.save()

        # Either 1 (only the create) — never 2.
        assert IntegrationPushLog.objects.filter(source_measurement_id=m.id).count() == 1

    def test_client_exception_does_not_break_measurement_save(
        self, setup_db, settings
    ):
        """Vault transport error must not poison the BioNexus write path."""
        settings.VEEVA_INTEGRATION_ENABLED = True
        settings.VEEVA_MODE = "mock"
        settings.VEEVA_BASE_URL = "http://localhost:8001"
        settings.VEEVA_SHARED_SECRET = "test-secret-32-bytes-aaaaaaaaaaaa"

        from modules.measurements.models import Measurement

        broken_client = MagicMock()
        broken_client.mode = "mock"
        broken_client.push_quality_event.side_effect = RuntimeError("network down")

        with patch(
            "modules.integrations.veeva.service.build_client_from_settings",
            return_value=broken_client,
        ):
            m = Measurement.objects.create(
                sample=setup_db["sample"],
                instrument=setup_db["instrument"],
                parameter="pH",
                value=Decimal("7.42"),
                unit="pH",
                measured_at=datetime.now(timezone.utc),
            )

        # The Measurement still landed in the DB.
        assert Measurement.objects.filter(id=m.id).exists()
