"""Tests for audit trail functionality in Protocols module."""

from django.test import TestCase

from core.audit import AuditTrail
from core.models import AuditLog
from modules.protocols.services import ProtocolService


class ProtocolAuditTrailTest(TestCase):
    """Tests for audit trail recording during Protocol mutations."""

    def setUp(self):
        self.service = ProtocolService()

    def test_create_records_audit_log(self):
        """Creating a protocol records an AuditLog with CREATE operation."""
        data = {
            "title": "DNA Extraction",
            "description": "Standard protocol",
            "steps": "Step 1: collect sample",
        }
        protocol = self.service.create_protocol(data)

        logs = AuditLog.objects.filter(entity_type="Protocol", entity_id=protocol.id)
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertEqual(log.operation, AuditLog.CREATE)
        self.assertIn("title", log.changes)

    def test_delete_records_soft_delete_audit(self):
        """Deleting a protocol records a DELETE operation (soft delete)."""
        protocol = self.service.create_protocol(
            {"title": "Protocol to Delete", "description": "", "steps": ""}
        )

        self.service.delete_protocol(protocol.id)

        logs = AuditLog.objects.filter(
            entity_type="Protocol", entity_id=protocol.id, operation=AuditLog.DELETE
        )
        self.assertEqual(logs.count(), 1)

        # Verify soft delete
        from modules.protocols.models import Protocol

        deleted = Protocol.objects.get(pk=protocol.id)
        self.assertTrue(deleted.is_deleted)
        self.assertIsNotNone(deleted.deleted_at)
