from django.test import TestCase
from rest_framework.test import APIClient


class ProtocolAPITest(TestCase):
    """Integration tests for Protocol endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_protocol_crud_operations(self):
        payload = {
            "title": "DNA Extraction",
            "description": "Basic protocol",
            "steps": "Step 1",
        }

        response = self.client.post("/api/protocols/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        protocol_id = response.data["id"]

        response = self.client.get(f"/api/protocols/{protocol_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "DNA Extraction")

        response = self.client.patch(
            f"/api/protocols/{protocol_id}/", {"title": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Updated")

        response = self.client.delete(f"/api/protocols/{protocol_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            self.client.get(f"/api/protocols/{protocol_id}/").status_code, 404
        )
