from django.test import TestCase
from rest_framework.test import APIClient

from modules.instruments.models import Instrument


class InstrumentAPITest(TestCase):
    """Integration tests for Instrument endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "name": "pH Meter 3000",
            "instrument_type": "pH meter",
            "serial_number": "PH-001-2024",
            "connection_type": "RS232",
            "status": "online",
        }

    def test_create_instrument(self):
        response = self.client.post("/api/instruments/", self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "pH Meter 3000")
        self.assertEqual(response.data["serial_number"], "PH-001-2024")
        self.assertEqual(response.data["connection_type"], "RS232")

    def test_list_instruments(self):
        self.client.post("/api/instruments/", self.payload, format="json")
        response = self.client.get("/api/instruments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_get_instrument_detail(self):
        created = self.client.post("/api/instruments/", self.payload, format="json")
        pk = created.data["id"]
        response = self.client.get(f"/api/instruments/{pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "pH Meter 3000")

    def test_update_instrument(self):
        created = self.client.post("/api/instruments/", self.payload, format="json")
        pk = created.data["id"]
        response = self.client.patch(
            f"/api/instruments/{pk}/", {"status": "offline"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "offline")

    def test_soft_delete_instrument(self):
        created = self.client.post("/api/instruments/", self.payload, format="json")
        pk = created.data["id"]
        response = self.client.delete(f"/api/instruments/{pk}/")
        self.assertEqual(response.status_code, 204)
        # Should not appear in list
        list_resp = self.client.get("/api/instruments/")
        self.assertEqual(len(list_resp.data), 0)
        # But still exists in DB with is_deleted=True
        inst = Instrument.objects.get(pk=pk)
        self.assertTrue(inst.is_deleted)

    def test_create_duplicate_serial_number_fails(self):
        self.client.post("/api/instruments/", self.payload, format="json")
        response = self.client.post("/api/instruments/", self.payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_missing_required_field_fails(self):
        response = self.client.post(
            "/api/instruments/", {"name": "Missing Fields"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
