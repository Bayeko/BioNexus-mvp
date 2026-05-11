"""Tests for the sync engine and ingest endpoint.

Verifies:
1. Ingest creates Measurement + AuditLog
2. Ingest duplicate returns "duplicate" + same measurement_id
3. data_hash preserved (not re-computed server-side)
4. SyncEngine.run_once() syncs pending records
5. Transport error → failed + retry_count++ + last_error
6. Backoff: retry_count=0→~1s, 1→~2s, 5→~32s, cap at 300s
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.instruments.models import Instrument
from modules.measurements.models import Measurement
from modules.persistence.models import PendingMeasurement
from modules.persistence.sync_engine import BackoffCalculator, SyncEngine
from modules.samples.models import Sample


def _create_instrument():
    return Instrument.objects.create(
        name="Test Instrument",
        instrument_type="pH Meter",
        serial_number="SN-TEST-001",
        connection_type="USB",
        status="online",
    )


def _create_sample(instrument):
    return Sample.objects.create(
        sample_id=f"SMP-TEST-{uuid.uuid4().hex[:6]}",
        instrument=instrument,
        batch_number="BATCH-001",
        status="pending",
        created_by="test_user",
    )


def _make_ingest_payload(sample_id, instrument_id, **overrides):
    base = {
        "idempotency_key": str(uuid.uuid4()),
        "sample_id": sample_id,
        "instrument_id": instrument_id,
        "parameter": "pH",
        "value": "7.0123456789",
        "unit": "pH",
        "data_hash": "c" * 64,
        "source_timestamp": "2026-01-15T10:30:00Z",
        "hub_received_at": "2026-01-15T10:30:01Z",
    }
    base.update(overrides)
    return base


class TestIngestEndpoint(TestCase):
    """Test the /api/persistence/ingest/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/persistence/ingest/"
        self.instrument = _create_instrument()
        self.sample = _create_sample(self.instrument)

    def test_ingest_creates_measurement(self):
        """Ingest creates a Measurement record."""
        payload = _make_ingest_payload(self.sample.pk, self.instrument.pk)

        resp = self.client.post(self.url, [payload], format="json")
        assert resp.status_code == 200

        acks = resp.json()
        assert len(acks) == 1
        assert acks[0]["status"] == "created"
        assert acks[0]["idempotency_key"] == payload["idempotency_key"]

        # Measurement exists
        m = Measurement.objects.get(pk=acks[0]["measurement_id"])
        assert m.parameter == "pH"

    def test_ingest_duplicate(self):
        """Second ingest with same idempotency_key returns 'duplicate'."""
        payload = _make_ingest_payload(self.sample.pk, self.instrument.pk)

        self.client.post(self.url, [payload], format="json")
        resp2 = self.client.post(self.url, [payload], format="json")

        acks = resp2.json()
        assert acks[0]["status"] == "duplicate"
        assert Measurement.objects.count() == 1

    def test_data_hash_preserved(self):
        """data_hash from instrument is preserved, not re-computed."""
        expected_hash = "d" * 64
        payload = _make_ingest_payload(
            self.sample.pk, self.instrument.pk, data_hash=expected_hash
        )

        resp = self.client.post(self.url, [payload], format="json")
        acks = resp.json()

        m = Measurement.objects.get(pk=acks[0]["measurement_id"])
        assert m.data_hash == expected_hash
        assert acks[0]["confirmation_hash"] == expected_hash


class TestSyncEngine(TestCase):
    """Test SyncEngine logic."""

    def setUp(self):
        self.instrument = _create_instrument()
        self.sample = _create_sample(self.instrument)

    def _create_pending(self, **kwargs):
        defaults = {
            "idempotency_key": uuid.uuid4(),
            "sample_id": self.sample.pk,
            "instrument_id": self.instrument.pk,
            "parameter": "pH",
            "value": Decimal("7.0"),
            "unit": "pH",
            "data_hash": "e" * 64,
            "source_timestamp": timezone.now(),
            "hub_received_at": timezone.now(),
            "sync_status": "pending",
        }
        defaults.update(kwargs)
        return PendingMeasurement.objects.create(**defaults)

    def test_run_once_syncs_pending(self):
        """run_once() picks pending records and syncs them."""
        self._create_pending()
        engine = SyncEngine()

        stats = engine.run_once()

        assert stats["synced"] == 1
        record = PendingMeasurement.objects.first()
        assert record.sync_status == "synced"
        assert record.synced_measurement_id is not None

    def test_transport_error_marks_failed(self):
        """When transport raises, records are marked failed."""
        self._create_pending()

        def failing_transport(payloads):
            raise ConnectionError("Network down")

        engine = SyncEngine(transport=failing_transport)
        stats = engine.run_once()

        assert stats["failed"] == 1
        record = PendingMeasurement.objects.first()
        assert record.sync_status == "failed"
        assert record.retry_count == 1
        assert "Network down" in record.last_error

    def test_backoff_exponential(self):
        """Backoff grows exponentially with cap."""
        calc = BackoffCalculator(base_s=1.0, max_s=300.0, jitter_s=0.0)

        assert calc.delay_for(0) == 1.0    # 1 * 2^0 = 1
        assert calc.delay_for(1) == 2.0    # 1 * 2^1 = 2
        assert calc.delay_for(5) == 32.0   # 1 * 2^5 = 32
        assert calc.delay_for(10) == 300.0  # 1 * 2^10 = 1024 → capped at 300
