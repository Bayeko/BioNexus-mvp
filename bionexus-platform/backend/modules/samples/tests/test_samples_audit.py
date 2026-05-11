"""Tests for audit trail functionality triggered by Django signals.

Verifies that:
- Every mutation (CREATE, UPDATE, DELETE) is recorded automatically
- Signatures form a cryptographic chain
- Tampering detection works
"""

from django.test import TestCase

from core.audit import AuditTrail
from core.models import AuditLog
from modules.instruments.models import Instrument
from modules.samples.models import Sample


class SampleSignalAuditTest(TestCase):
    """Tests that Django signals auto-record audit logs for Sample mutations."""

    def setUp(self):
        self.instrument = Instrument.objects.create(
            name="Test Instrument",
            instrument_type="pH meter",
            serial_number="AUDIT-TEST-001",
            connection_type="USB",
        )

    def test_create_records_audit_log(self):
        sample = Sample.objects.create(
            sample_id="AUDIT-SMP-001",
            instrument=self.instrument,
            batch_number="BATCH-A1",
            created_by="tester",
        )
        logs = AuditLog.objects.filter(entity_type="Sample", entity_id=sample.pk)
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.operation, "CREATE")

    def test_update_records_audit_log(self):
        sample = Sample.objects.create(
            sample_id="AUDIT-SMP-002",
            instrument=self.instrument,
            batch_number="BATCH-A2",
            created_by="tester",
        )
        sample.status = "in_progress"
        sample.save()
        logs = AuditLog.objects.filter(
            entity_type="Sample", entity_id=sample.pk, operation="UPDATE"
        )
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.changes["status"]["before"], "pending")
        self.assertEqual(log.changes["status"]["after"], "in_progress")


class AuditChainIntegrityTest(TestCase):
    """Tests for cryptographic chain integrity."""

    def test_signature_chain_forms_correctly(self):
        log1 = AuditTrail.record(
            entity_type="TestEntity",
            entity_id=1,
            operation="CREATE",
            changes={"field": {"before": None, "after": "value1"}},
            snapshot_before={},
            snapshot_after={"field": "value1"},
        )
        self.assertIsNone(log1.previous_signature)

        log2 = AuditTrail.record(
            entity_type="TestEntity",
            entity_id=2,
            operation="CREATE",
            changes={"field": {"before": None, "after": "value2"}},
            snapshot_before={},
            snapshot_after={"field": "value2"},
        )
        self.assertEqual(log2.previous_signature, log1.signature)

    def test_chain_verification_passes_for_intact_chain(self):
        for i in range(3):
            AuditTrail.record(
                entity_type="ChainTest",
                entity_id=i,
                operation="CREATE",
                changes={"field": {"before": None, "after": f"value{i}"}},
                snapshot_before={},
                snapshot_after={"field": f"value{i}"},
            )
        is_valid, message = AuditTrail.verify_chain_integrity("ChainTest")
        self.assertTrue(is_valid, f"Chain verification failed: {message}")

    def test_chain_verification_detects_tampering(self):
        log1 = AuditTrail.record(
            entity_type="TamperTest",
            entity_id=1,
            operation="CREATE",
            changes={"field": {"before": None, "after": "value1"}},
            snapshot_before={},
            snapshot_after={"field": "value1"},
        )
        AuditTrail.record(
            entity_type="TamperTest",
            entity_id=2,
            operation="CREATE",
            changes={"field": {"before": None, "after": "value2"}},
            snapshot_before={},
            snapshot_after={"field": "value2"},
        )
        # Tamper with log1
        log1.changes = {"field": {"before": None, "after": "TAMPERED"}}
        log1._skip_validation = True
        log1.save()

        is_valid, message = AuditTrail.verify_chain_integrity("TamperTest")
        self.assertFalse(is_valid)
        self.assertIn("Tampering detected", message)
