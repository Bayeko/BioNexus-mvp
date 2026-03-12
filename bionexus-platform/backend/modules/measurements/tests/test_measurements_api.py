from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.instruments.models import Instrument
from modules.measurements.models import Measurement
from modules.samples.models import Sample


class MeasurementAPITest(TestCase):
    """Integration tests for Measurement endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.instrument = Instrument.objects.create(
            name="HPLC System",
            instrument_type="HPLC",
            serial_number="HPLC-001",
            connection_type="Ethernet",
        )
        self.sample = Sample.objects.create(
            sample_id="SMP-MEAS-001",
            instrument=self.instrument,
            batch_number="BATCH-M1",
            created_by="lab_tech_1",
        )
        self.payload = {
            "sample": self.sample.pk,
            "instrument": self.instrument.pk,
            "parameter": "pH",
            "value": "7.4000000000",
            "unit": "pH",
            "measured_at": timezone.now().isoformat(),
        }

    def test_create_measurement(self):
        response = self.client.post("/api/measurements/", self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["parameter"], "pH")
        self.assertEqual(Decimal(response.data["value"]), Decimal("7.4"))
        # data_hash should be auto-computed
        self.assertTrue(len(response.data["data_hash"]) == 64)

    def test_list_measurements(self):
        self.client.post("/api/measurements/", self.payload, format="json")
        response = self.client.get("/api/measurements/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_get_measurement_detail(self):
        created = self.client.post("/api/measurements/", self.payload, format="json")
        pk = created.data["id"]
        response = self.client.get(f"/api/measurements/{pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["parameter"], "pH")

    def test_filter_by_instrument(self):
        self.client.post("/api/measurements/", self.payload, format="json")
        response = self.client.get(
            f"/api/measurements/?instrument={self.instrument.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_by_parameter(self):
        self.client.post("/api/measurements/", self.payload, format="json")
        response = self.client.get("/api/measurements/?parameter=pH")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        # Filter for non-existing parameter
        response = self.client.get("/api/measurements/?parameter=temperature")
        self.assertEqual(len(response.data), 0)

    def test_data_hash_integrity(self):
        """SHA-256 data hash is computed on creation and is deterministic."""
        resp1 = self.client.post("/api/measurements/", self.payload, format="json")
        hash1 = resp1.data["data_hash"]
        # Re-read from DB
        m = Measurement.objects.get(pk=resp1.data["id"])
        self.assertEqual(m.data_hash, hash1)
        self.assertEqual(len(hash1), 64)

    def test_create_missing_required_field_fails(self):
        response = self.client.post(
            "/api/measurements/", {"parameter": "pH"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
