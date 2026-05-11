"""Tests for congestion control and clock drift detection.

Verifies:
1. Slow server response → batch size halved
2. Fast server response → batch size doubled
3. Burst limit respected (never > max_burst_per_minute)
4. Clock drift calculated correctly
5. Drift flagged when exceeding threshold
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.instruments.models import Instrument
from modules.persistence.sync_engine import CongestionController
from modules.samples.models import Sample


class TestCongestionController(TestCase):
    """Test adaptive batch sizing and burst limiting."""

    def test_slow_response_halves_batch(self):
        """Server response > server_slow_ms → batch size halved."""
        ctrl = CongestionController(
            initial_batch_size=40,
            server_slow_ms=2000,
            server_fast_ms=500,
        )

        ctrl.adjust(3000)  # 3s → slow
        assert ctrl.current_batch_size == 20

    def test_fast_response_doubles_batch(self):
        """Server response < server_fast_ms → batch size doubled."""
        ctrl = CongestionController(
            initial_batch_size=20,
            server_slow_ms=2000,
            server_fast_ms=500,
            max_batch_size=100,
        )

        ctrl.adjust(200)  # 200ms → fast
        assert ctrl.current_batch_size == 40

    def test_batch_size_clamped(self):
        """Batch size never exceeds max or drops below min."""
        ctrl = CongestionController(
            initial_batch_size=5,
            min_batch_size=5,
            max_batch_size=100,
            server_slow_ms=2000,
            server_fast_ms=500,
        )

        # Try to halve below min
        ctrl.adjust(5000)
        assert ctrl.current_batch_size == 5  # clamped at min

        # Double repeatedly toward max
        ctrl.current_batch_size = 60
        ctrl.adjust(100)  # fast → double
        assert ctrl.current_batch_size == 100  # clamped at max

    def test_burst_limit_respected(self):
        """next_batch_size returns 0 when burst budget exhausted."""
        ctrl = CongestionController(
            initial_batch_size=50,
            max_burst_per_minute=200,
        )

        # Simulate sending 200 records
        ctrl.record_sent(200)

        # Next batch should be 0 (burst exhausted)
        assert ctrl.next_batch_size() == 0

    def test_burst_resets_after_minute(self):
        """Burst counter resets after 60 seconds."""
        ctrl = CongestionController(
            initial_batch_size=50,
            max_burst_per_minute=200,
        )

        ctrl.record_sent(200)
        assert ctrl.next_batch_size() == 0

        # Simulate minute passing
        ctrl._minute_start -= 61
        assert ctrl.next_batch_size() == 50


class TestClockDrift(TestCase):
    """Test clock drift detection via the ingest endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/persistence/ingest/"
        self.instrument = Instrument.objects.create(
            name="Drift Test Instrument",
            instrument_type="pH Meter",
            serial_number="SN-DRIFT-001",
            connection_type="USB",
            status="online",
        )
        self.sample = Sample.objects.create(
            sample_id="SMP-DRIFT-001",
            instrument=self.instrument,
            batch_number="BATCH-001",
            status="pending",
            created_by="test_user",
        )

    def test_clock_drift_calculated(self):
        """clock_drift_ms is returned in ACK."""
        payload = {
            "idempotency_key": str(uuid.uuid4()),
            "sample_id": self.sample.pk,
            "instrument_id": self.instrument.pk,
            "parameter": "pH",
            "value": "7.0",
            "unit": "pH",
            "data_hash": "f" * 64,
            "source_timestamp": "2026-01-15T10:30:00Z",
            "hub_received_at": "2026-01-15T10:30:01Z",
        }

        resp = self.client.post(self.url, [payload], format="json")
        acks = resp.json()

        assert "clock_drift_ms" in acks[0]
        assert isinstance(acks[0]["clock_drift_ms"], int)

    def test_drift_flagged_when_exceeds_threshold(self):
        """drift_flagged=True when |drift| > threshold."""
        # hub_received_at far in the past → large drift
        payload = {
            "idempotency_key": str(uuid.uuid4()),
            "sample_id": self.sample.pk,
            "instrument_id": self.instrument.pk,
            "parameter": "pH",
            "value": "7.0",
            "unit": "pH",
            "data_hash": "f" * 64,
            "source_timestamp": "2020-01-01T00:00:00Z",
            "hub_received_at": "2020-01-01T00:00:01Z",
        }

        resp = self.client.post(self.url, [payload], format="json")
        acks = resp.json()

        # Drift should be huge (years) → flagged
        assert acks[0]["drift_flagged"] is True
        assert abs(acks[0]["clock_drift_ms"]) > 5000
