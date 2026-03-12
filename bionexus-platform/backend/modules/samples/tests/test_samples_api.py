from django.test import TestCase
from rest_framework.test import APIClient

from modules.instruments.models import Instrument
from modules.samples.models import Sample


class SampleAPITest(TestCase):
    """Integration tests for Sample endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.instrument = Instrument.objects.create(
            name="Spectrophotometer",
            instrument_type="spectrophotometer",
            serial_number="SPEC-001",
            connection_type="USB",
        )
        self.payload = {
            "sample_id": "SMP-2024-001",
            "instrument": self.instrument.pk,
            "batch_number": "BATCH-001",
            "status": "pending",
            "created_by": "lab_tech_1",
        }

    def test_create_sample(self):
        response = self.client.post("/api/samples/", self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["sample_id"], "SMP-2024-001")
        self.assertEqual(response.data["batch_number"], "BATCH-001")

    def test_list_samples(self):
        self.client.post("/api/samples/", self.payload, format="json")
        response = self.client.get("/api/samples/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_get_sample_detail(self):
        created = self.client.post("/api/samples/", self.payload, format="json")
        pk = created.data["id"]
        response = self.client.get(f"/api/samples/{pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sample_id"], "SMP-2024-001")

    def test_update_sample_status(self):
        created = self.client.post("/api/samples/", self.payload, format="json")
        pk = created.data["id"]
        response = self.client.patch(
            f"/api/samples/{pk}/", {"status": "in_progress"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "in_progress")

    def test_soft_delete_sample(self):
        created = self.client.post("/api/samples/", self.payload, format="json")
        pk = created.data["id"]
        response = self.client.delete(f"/api/samples/{pk}/")
        self.assertEqual(response.status_code, 204)
        # Not in list
        list_resp = self.client.get("/api/samples/")
        self.assertEqual(len(list_resp.data), 0)
        # Still in DB
        sample = Sample.objects.get(pk=pk)
        self.assertTrue(sample.is_deleted)

    def test_filter_by_status(self):
        self.client.post("/api/samples/", self.payload, format="json")
        payload2 = {**self.payload, "sample_id": "SMP-2024-002", "status": "completed"}
        self.client.post("/api/samples/", payload2, format="json")
        response = self.client.get("/api/samples/?status=pending")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], "pending")

    def test_create_duplicate_sample_id_fails(self):
        self.client.post("/api/samples/", self.payload, format="json")
        response = self.client.post("/api/samples/", self.payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_missing_required_field_fails(self):
        response = self.client.post(
            "/api/samples/", {"sample_id": "SMP-X"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
