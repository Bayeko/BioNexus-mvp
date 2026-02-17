"""Tests for audit trail functionality in Samples module.

Verifies that:
- Every mutation (CREATE, UPDATE, DELETE) is recorded
- Signatures form an unbreakable cryptographic chain
- Tampering detection works
- Soft delete preserves audit history
"""

from django.test import TestCase
from django.utils import timezone

from core.audit import AuditTrail
from core.models import AuditLog
from modules.samples.services import SampleService


class SampleAuditTrailTest(TestCase):
    """Tests for audit trail recording during Sample mutations."""

    def setUp(self):
        self.service = SampleService()

    def test_create_records_audit_log(self):
        """Creating a sample records an AuditLog with CREATE operation."""
        data = {
            "name": "Sample A",
            "sample_type": "blood",
            "received_at": timezone.now(),
            "location": "Freezer 1",
        }
        sample = self.service.create_sample(data)

        logs = AuditLog.objects.filter(entity_type="Sample", entity_id=sample.id)
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertEqual(log.operation, AuditLog.CREATE)
        self.assertEqual(log.entity_type, "Sample")
        self.assertIn("name", log.changes)
        self.assertEqual(log.changes["name"]["after"], "Sample A")

    def test_update_records_audit_log_with_changes(self):
        """Updating a sample records an AuditLog with changed fields."""
        # Create
        sample = self.service.create_sample(
            {
                "name": "Original",
                "sample_type": "blood",
                "received_at": timezone.now(),
                "location": "Freezer 1",
            }
        )

        # Update
        self.service.update_sample(sample.id, {"name": "Updated"})

        logs = AuditLog.objects.filter(
            entity_type="Sample", entity_id=sample.id, operation=AuditLog.UPDATE
        )
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertEqual(log.changes["name"]["before"], "Original")
        self.assertEqual(log.changes["name"]["after"], "Updated")

    def test_delete_records_soft_delete_audit(self):
        """Deleting a sample records a DELETE operation (soft delete)."""
        sample = self.service.create_sample(
            {
                "name": "To Delete",
                "sample_type": "blood",
                "received_at": timezone.now(),
                "location": "Freezer 1",
            }
        )

        self.service.delete_sample(sample.id)

        logs = AuditLog.objects.filter(
            entity_type="Sample", entity_id=sample.id, operation=AuditLog.DELETE
        )
        self.assertEqual(logs.count(), 1)

        # Verify soft delete (data still in DB)
        from modules.samples.models import Sample

        deleted = Sample.objects.get(pk=sample.id)
        self.assertTrue(deleted.is_deleted)
        self.assertIsNotNone(deleted.deleted_at)


class AuditChainIntegrityTest(TestCase):
    """Tests for cryptographic chain integrity."""

    def test_signature_chain_forms_correctly(self):
        """Creating multiple records forms a valid signature chain."""
        trail = AuditTrail()

        # Create first record
        log1 = trail.record(
            entity_type="TestEntity",
            entity_id=1,
            operation="CREATE",
            changes={"field": {"before": None, "after": "value1"}},
            snapshot_before={},
            snapshot_after={"field": "value1"},
        )
        self.assertIsNone(log1.previous_signature)

        # Create second record
        log2 = trail.record(
            entity_type="TestEntity",
            entity_id=2,
            operation="CREATE",
            changes={"field": {"before": None, "after": "value2"}},
            snapshot_before={},
            snapshot_after={"field": "value2"},
        )
        # Second record should chain to first
        self.assertEqual(log2.previous_signature, log1.signature)

        # Create third record
        log3 = trail.record(
            entity_type="TestEntity",
            entity_id=3,
            operation="CREATE",
            changes={"field": {"before": None, "after": "value3"}},
            snapshot_before={},
            snapshot_after={"field": "value3"},
        )
        self.assertEqual(log3.previous_signature, log2.signature)

    def test_chain_verification_passes_for_intact_chain(self):
        """verify_chain_integrity returns True for an unmodified chain."""
        trail = AuditTrail()

        # Create a few records
        for i in range(3):
            trail.record(
                entity_type="TestEntity",
                entity_id=i,
                operation="CREATE",
                changes={"field": {"before": None, "after": f"value{i}"}},
                snapshot_before={},
                snapshot_after={"field": f"value{i}"},
            )

        is_valid, message = trail.verify_chain_integrity("TestEntity")
        self.assertTrue(is_valid, f"Chain verification failed: {message}")

    def test_chain_verification_detects_tampering(self):
        """verify_chain_integrity detects if a record was modified."""
        trail = AuditTrail()

        # Create records
        log1 = trail.record(
            entity_type="TamperTest",
            entity_id=1,
            operation="CREATE",
            changes={"field": {"before": None, "after": "value1"}},
            snapshot_before={},
            snapshot_after={"field": "value1"},
        )

        log2 = trail.record(
            entity_type="TamperTest",
            entity_id=2,
            operation="CREATE",
            changes={"field": {"before": None, "after": "value2"}},
            snapshot_before={},
            snapshot_after={"field": "value2"},
        )

        # Tamper with log1's changes (simulating DB-level modification)
        log1.changes = {"field": {"before": None, "after": "TAMPERED"}}
        log1._skip_validation = True  # Bypass signature check for tampering test
        log1.save()

        # Verification should detect the tampering
        is_valid, message = trail.verify_chain_integrity("TamperTest")
        self.assertFalse(is_valid)
        self.assertIn("Tampering detected", message)


class AuditHistoryTest(TestCase):
    """Tests for retrieving audit history."""

    def setUp(self):
        self.service = SampleService()

    def test_get_entity_history_returns_all_mutations(self):
        """get_entity_history returns all operations for an entity in order."""
        sample = self.service.create_sample(
            {
                "name": "Audit History Test",
                "sample_type": "blood",
                "received_at": timezone.now(),
                "location": "Freezer 1",
            }
        )

        # Make some mutations
        self.service.update_sample(sample.id, {"name": "Updated 1"})
        self.service.update_sample(sample.id, {"location": "Freezer 2"})

        history = AuditTrail.get_entity_history("Sample", sample.id)

        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].operation, AuditLog.CREATE)
        self.assertEqual(history[1].operation, AuditLog.UPDATE)
        self.assertEqual(history[2].operation, AuditLog.UPDATE)
