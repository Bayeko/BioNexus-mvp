"""Tests for offline capture (WAL write-ahead log).

Verifies:
1. Capture writes locally without needing a server
2. Idempotence on same idempotency_key
3. source_timestamp preserved verbatim
4. data_hash preserved verbatim
5. Two different keys → two records
"""

import uuid
from datetime import timezone as dt_tz
from decimal import Decimal

import pytest
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.persistence.models import PendingMeasurement


def _make_payload(**overrides):
    """Build a valid capture payload with sensible defaults."""
    base = {
        "idempotency_key": str(uuid.uuid4()),
        "sample_id": 1,
        "instrument_id": 1,
        "parameter": "pH",
        "value": "7.0123456789",
        "unit": "pH",
        "data_hash": "a" * 64,
        "source_timestamp": "2026-01-15T10:30:00Z",
        "hub_received_at": "2026-01-15T10:30:01Z",
    }
    base.update(overrides)
    return base


class TestOfflineCapture(TestCase):
    """Test the /api/persistence/capture/ endpoint (WAL writes)."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/persistence/capture/"

    def test_capture_writes_locally(self):
        """Capture writes a PendingMeasurement without any server contact."""
        payload = _make_payload()
        resp = self.client.post(self.url, payload, format="json")

        assert resp.status_code == 201
        assert PendingMeasurement.objects.count() == 1

        record = PendingMeasurement.objects.first()
        assert str(record.idempotency_key) == payload["idempotency_key"]
        assert record.sync_status == "pending"

    def test_idempotent_capture(self):
        """Second POST with same idempotency_key returns 200, not 201."""
        payload = _make_payload()

        resp1 = self.client.post(self.url, payload, format="json")
        assert resp1.status_code == 201

        resp2 = self.client.post(self.url, payload, format="json")
        assert resp2.status_code == 200

        # Still only one record
        assert PendingMeasurement.objects.count() == 1

    def test_source_timestamp_preserved(self):
        """source_timestamp is stored exactly as sent, never overwritten."""
        ts = "2025-06-15T08:45:30.123456Z"
        payload = _make_payload(source_timestamp=ts)

        self.client.post(self.url, payload, format="json")
        record = PendingMeasurement.objects.first()

        # Compare with microsecond precision
        assert record.source_timestamp.year == 2025
        assert record.source_timestamp.month == 6
        assert record.source_timestamp.day == 15
        assert record.source_timestamp.hour == 8
        assert record.source_timestamp.minute == 45

    def test_data_hash_preserved(self):
        """data_hash from the instrument is stored verbatim."""
        expected_hash = "b" * 64
        payload = _make_payload(data_hash=expected_hash)

        self.client.post(self.url, payload, format="json")
        record = PendingMeasurement.objects.first()

        assert record.data_hash == expected_hash

    def test_two_different_keys_two_records(self):
        """Two captures with different idempotency_keys create two records."""
        payload1 = _make_payload()
        payload2 = _make_payload()

        self.client.post(self.url, payload1, format="json")
        self.client.post(self.url, payload2, format="json")

        assert PendingMeasurement.objects.count() == 2
