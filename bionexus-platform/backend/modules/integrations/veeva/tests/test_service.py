"""Tests for the high-level push service + idempotency.

These exercise the full path: domain object → mapping → log row →
client → log row update. The client is a stub that lets each test pin
exactly the response shape it cares about.
"""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from modules.integrations.veeva.client import DisabledVeevaClient, PushResult
from modules.integrations.veeva.models import IntegrationPushLog
from modules.integrations.veeva.service import push_measurement, push_report


@pytest.fixture
def measurement():
    return SimpleNamespace(
        id=42,
        parameter="pH",
        value=Decimal("7.42"),
        unit="pH",
        measured_at=datetime(2026, 4, 23, 10, 0, 0, tzinfo=timezone.utc),
        data_hash="a" * 64,
        sample=SimpleNamespace(barcode="QC-100"),
        instrument=SimpleNamespace(serial_number="HPLC-001"),
        context=SimpleNamespace(
            operator="OP-042",
            lot_number="LOT-2026-04",
            method="USP <621>",
            sample_id="ALIAS-QC-100",
        ),
    )


@pytest.fixture
def report():
    return SimpleNamespace(
        id=7,
        title="QC Release Report — Lot LOT-2026-04",
        signed_by="qp@lbn.ch",
        signed_at=datetime(2026, 4, 23, 12, 0, 0, tzinfo=timezone.utc),
        signature_hash="b" * 64,
        tenant=SimpleNamespace(name="Lab BioNexus AG"),
    )


def _ok_client(vault_id: str = "VVQE-001234"):
    client = MagicMock()
    client.mode = "mock"
    client.push_quality_event.return_value = PushResult(
        ok=True, http_status=201, vault_id=vault_id
    )
    client.push_document.return_value = PushResult(
        ok=True, http_status=201, vault_id="VVDOC-005678"
    )
    return client


def _failing_client(status: int = 500, error: str = "HTTP 500"):
    client = MagicMock()
    client.mode = "mock"
    client.push_quality_event.return_value = PushResult(
        ok=False, http_status=status, error=error
    )
    client.push_document.return_value = PushResult(
        ok=False, http_status=status, error=error
    )
    return client


# ---------------------------------------------------------------------------
# push_measurement happy path
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPushMeasurementHappyPath:
    def test_creates_log_row_on_success(self, measurement):
        record = push_measurement(measurement, client=_ok_client())

        assert isinstance(record, IntegrationPushLog)
        assert record.status == IntegrationPushLog.STATUS_SUCCESS
        assert record.target_object_id == "VVQE-001234"
        assert record.target_object_type == IntegrationPushLog.TARGET_QUALITY_EVENT
        assert record.source_measurement_id == 42
        assert record.attempts == 1
        assert record.http_status == 201
        assert record.payload_hash and len(record.payload_hash) == 64
        assert record.last_error == ""
        assert record.succeeded_at is not None

    def test_logs_mode_at_push_time(self, measurement, settings):
        settings.VEEVA_MODE = "mock"
        record = push_measurement(measurement, client=_ok_client())
        assert record.mode == "mock"

    def test_payload_hash_is_deterministic(self, measurement):
        r1 = push_measurement(measurement, client=_ok_client())
        # Second push of same measurement → should hit the idempotency check
        # and return the existing successful row unchanged.
        r2 = push_measurement(measurement, client=_ok_client())
        assert r1.id == r2.id
        assert r2.attempts == 1, "dedupe should not increment attempts"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestIdempotency:
    def test_success_row_short_circuits_retry(self, measurement):
        ok = _ok_client()
        r1 = push_measurement(measurement, client=ok)
        assert ok.push_quality_event.call_count == 1

        r2 = push_measurement(measurement, client=ok)
        assert r1.id == r2.id
        # Client must NOT be called again — Vault already has the object.
        assert ok.push_quality_event.call_count == 1

    def test_failed_row_increments_attempts_on_retry(self, measurement):
        fail = _failing_client(status=500)
        r1 = push_measurement(measurement, client=fail)
        assert r1.status == IntegrationPushLog.STATUS_FAILED
        assert r1.attempts == 1

        r2 = push_measurement(measurement, client=fail)
        # Same row, attempts bumped.
        assert r1.id == r2.id
        assert r2.attempts == 2
        assert r2.status == IntegrationPushLog.STATUS_FAILED

    def test_different_measurements_get_different_log_rows(self, measurement):
        ok = _ok_client(vault_id="VVQE-A")
        r1 = push_measurement(measurement, client=ok)

        measurement2 = SimpleNamespace(**measurement.__dict__)
        measurement2.id = 99
        measurement2.value = Decimal("8.00")  # different payload
        ok2 = _ok_client(vault_id="VVQE-B")
        r2 = push_measurement(measurement2, client=ok2)

        assert r1.id != r2.id
        assert r1.payload_hash != r2.payload_hash


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPushMeasurementFailure:
    def test_5xx_marks_failed(self, measurement):
        record = push_measurement(measurement, client=_failing_client(status=503))
        assert record.status == IntegrationPushLog.STATUS_FAILED
        assert record.http_status == 503
        assert "500" in record.last_error or "HTTP" in record.last_error

    def test_4xx_marks_failed(self, measurement):
        record = push_measurement(
            measurement, client=_failing_client(status=400, error="HTTP 400")
        )
        assert record.status == IntegrationPushLog.STATUS_FAILED
        assert record.http_status == 400

    def test_disabled_client_records_skip(self, measurement):
        record = push_measurement(measurement, client=DisabledVeevaClient())
        assert record.status == IntegrationPushLog.STATUS_FAILED
        assert "disabled" in record.last_error.lower()
        assert record.http_status is None


# ---------------------------------------------------------------------------
# push_report
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPushReport:
    def test_creates_document_log_row(self, report):
        record = push_report(report, b"%PDF-1.4 ...", client=_ok_client())
        assert record.target_object_type == IntegrationPushLog.TARGET_DOCUMENT
        assert record.target_object_id == "VVDOC-005678"
        assert record.source_report_id == 7
        assert record.status == IntegrationPushLog.STATUS_SUCCESS

    def test_dedupe_on_same_report(self, report):
        ok = _ok_client()
        r1 = push_report(report, b"%PDF-A", client=ok)
        r2 = push_report(report, b"%PDF-A", client=ok)
        assert r1.id == r2.id
        assert ok.push_document.call_count == 1
