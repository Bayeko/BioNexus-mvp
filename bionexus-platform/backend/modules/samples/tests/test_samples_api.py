from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient


class SampleAPITest(TestCase):
    """Integration tests for Sample endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_sample_crud_operations(self):
        payload = {
            "name": "Sample A",
            "type": "blood",
            "received_at": timezone.now().isoformat(),
            "location": "Freezer 1",
        }

        response = self.client.post("/api/samples/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        sample_id = response.data["id"]

        response = self.client.get(f"/api/samples/{sample_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Sample A")

        response = self.client.patch(
            f"/api/samples/{sample_id}/", {"name": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated")

        response = self.client.delete(f"/api/samples/{sample_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            self.client.get(f"/api/samples/{sample_id}/").status_code, 404
        )
