"""Tests for the /healthz liveness endpoint.

Covers :
- 200 + ``ok`` on healthy baseline (clean DB, no audit, empty queue)
- Stable response shape (probe contracts rely on it)
- 503 + ``error`` when DB connection is broken
- 503 + ``degraded`` when persistence queue has failed rows
- Audit trail freshness reported when AuditLog has entries
- Probe is publicly accessible (no auth required)
"""

from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from core.audit import AuditTrail
from modules.persistence.models import PendingMeasurement


class HealthzShapeTest(TestCase):
    """Response shape and HTTP semantics."""

    def setUp(self) -> None:
        self.client = APIClient()

    def test_healthz_returns_200_on_clean_baseline(self) -> None:
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")

    def test_healthz_response_shape_is_stable(self) -> None:
        response = self.client.get("/healthz")
        self.assertIn("status", response.data)
        self.assertIn("version", response.data)
        self.assertIn("timestamp", response.data)
        self.assertIn("checks", response.data)
        for key in ("database", "audit_trail", "persistence_queue"):
            self.assertIn(key, response.data["checks"])

    def test_healthz_trailing_slash_also_works(self) -> None:
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)

    def test_healthz_is_publicly_accessible(self) -> None:
        """No authentication required for probes."""
        client = APIClient()
        # Explicitly do NOT authenticate
        client.credentials()
        response = client.get("/healthz")
        self.assertEqual(response.status_code, 200)


class HealthzChecksTest(TestCase):
    """Individual subsystem checks reflect reality."""

    def setUp(self) -> None:
        self.client = APIClient()

    def test_database_check_includes_latency(self) -> None:
        response = self.client.get("/healthz")
        db = response.data["checks"]["database"]
        self.assertEqual(db["status"], "ok")
        self.assertIn("latency_ms", db)
        self.assertGreaterEqual(db["latency_ms"], 0)

    def test_audit_trail_check_reports_no_writes_when_empty(self) -> None:
        response = self.client.get("/healthz")
        audit = response.data["checks"]["audit_trail"]
        self.assertEqual(audit["status"], "ok")
        self.assertIsNone(audit["last_write"])

    def test_audit_trail_check_reports_last_write_when_present(self) -> None:
        AuditTrail.record(
            entity_type="Probe",
            entity_id=1,
            operation="CREATE",
            changes={},
            snapshot_before={},
            snapshot_after={"probe": "healthz-test"},
        )
        response = self.client.get("/healthz")
        audit = response.data["checks"]["audit_trail"]
        self.assertEqual(audit["status"], "ok")
        self.assertIsNotNone(audit["last_write"])

    def test_persistence_queue_warns_on_failed_rows(self) -> None:
        """A failed row should flip the queue check to 'warn' and degrade overall."""
        from django.utils import timezone

        PendingMeasurement.objects.create(
            sample_id=1, instrument_id=1,
            parameter="weight", value="1.0", unit="g",
            data_hash="0" * 64,
            source_timestamp=timezone.now(),
            hub_received_at=timezone.now(),
            sync_status="failed",
        )
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["status"], "degraded")
        queue = response.data["checks"]["persistence_queue"]
        self.assertEqual(queue["status"], "warn")
        self.assertEqual(queue["failed"], 1)


class HealthzFailureModeTest(TestCase):
    """Errors in a check propagate to a 503 response."""

    def test_db_failure_returns_503(self) -> None:
        client = APIClient()
        with mock.patch("core.health_views._check_database") as fake:
            fake.return_value = {"status": "error", "error": "connection refused"}
            response = client.get("/healthz")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["status"], "error")
        self.assertEqual(response.data["checks"]["database"]["status"], "error")
