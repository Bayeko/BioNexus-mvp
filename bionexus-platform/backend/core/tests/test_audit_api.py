from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.audit import AuditTrail
from core.models import AuditLog


class AuditLogAPITest(TestCase):
    """Integration tests for the read-only Audit Trail endpoint."""

    def setUp(self):
        self.client = APIClient()
        # Create some audit records
        self.log1 = AuditTrail.record(
            entity_type="Instrument",
            entity_id=1,
            operation="CREATE",
            changes={"name": {"before": None, "after": "pH Meter"}},
            snapshot_before={},
            snapshot_after={"name": "pH Meter"},
        )
        self.log2 = AuditTrail.record(
            entity_type="Sample",
            entity_id=10,
            operation="CREATE",
            changes={"sample_id": {"before": None, "after": "SMP-001"}},
            snapshot_before={},
            snapshot_after={"sample_id": "SMP-001"},
        )

    def test_list_audit_logs(self):
        response = self.client.get("/api/audit/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_get_audit_log_detail(self):
        response = self.client.get(f"/api/audit/{self.log1.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["entity_type"], "Instrument")
        self.assertEqual(response.data["operation"], "CREATE")
        self.assertTrue(len(response.data["signature"]) == 64)

    def test_filter_by_entity_type(self):
        response = self.client.get("/api/audit/?entity_type=Sample")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["entity_type"], "Sample")

    def test_filter_by_operation(self):
        response = self.client.get("/api/audit/?operation=CREATE")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_read_only_rejects_post(self):
        response = self.client.post("/api/audit/", {"entity_type": "Hack"}, format="json")
        self.assertEqual(response.status_code, 405)

    def test_read_only_rejects_delete(self):
        response = self.client.delete(f"/api/audit/{self.log1.pk}/")
        self.assertEqual(response.status_code, 405)

    def test_signature_chain_present(self):
        """Records of the same entity_type chain via previous_signature."""
        log3 = AuditTrail.record(
            entity_type="Instrument",
            entity_id=2,
            operation="CREATE",
            changes={"name": {"before": None, "after": "HPLC"}},
            snapshot_before={},
            snapshot_after={"name": "HPLC"},
        )
        response = self.client.get(f"/api/audit/{log3.pk}/")
        self.assertEqual(response.data["previous_signature"], self.log1.signature)
